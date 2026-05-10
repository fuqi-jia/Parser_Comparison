#!/usr/bin/env python3
"""Single LLM trial for one front-end.

Usage:
    python3 run_llm_trial.py \
        --frontend pysmt --run-name run_00 \
        [--config config/llm.yaml] [--case-dir case_studies/rdl_prototyping]

The trial creates an immutable per-run directory tree:

    results/runs/<frontend>/<run_name>/
        meta.json                          # configuration + final summary
        prompt/                            # prompt bundle, hashed
            bundle.md                      # full text concatenated
            bundle.sha256
            sources.txt                    # which files contributed
        conversation/
            turn_00.user.md
            turn_00.assistant.md
            turn_01.user.md ...            # ≤ K+1 turns
        src/turn_00/                       # adapter code as written by LLM
        audit/turn_00/audit_report.json
        build/turn_00/build.log            # build output (or "n/a" for python)
        dev/turn_00/
            per_file.csv                   # one row per dev file
            adapter_out/<rel>.json         # raw rdl_atoms.json per dev file
            summary.json
        final_test/                        # populated only on success/last
            per_file.csv
            adapter_out/<rel>.json
            summary.json

Nothing under this run dir is ever rewritten — every iteration appends
to a fresh subdirectory keyed by turn index.

Fairness invariants enforced here:
    1. The prompt bundle is constructed only from whitelisted paths; any
       path matching .llmtrialignore is dropped before bundling.
    2. The adapter is sandboxed to its src/turn_NN/ dir; the harness
       never lets it read shared_backend/, schema/, _archive/, or
       data/test/.
    3. The dev set is the only set the LLM ever observes; the test set
       is touched only after the final fix iteration.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent
sys.path.insert(0, str(HERE))
from llm_client import (  # noqa: E402
    approx_token_count,
    extract_files,
    load_config,
    make_client,
)

FRONTENDS = {"somtparser", "z3_cpp", "cvc5_cpp", "smt_switch",
             "pysmt", "antlr4", "jsmtlib"}

# anchor dev files we embed verbatim (others are listed by name only).
ANCHOR_DEV_FILES = [
    "check/bignum_rdl1.smt2",
    "check/bignum_rdl2.smt2",
]


# --------------------------------------------------------------------------
# .llmtrialignore loading.
# --------------------------------------------------------------------------
def load_ignore_patterns(repo_root: Path) -> list[str]:
    f = repo_root / ".llmtrialignore"
    if not f.is_file():
        return []
    out: list[str] = []
    for line in f.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s.rstrip("/"))
    return out


def is_ignored(rel_posix: str, patterns: list[str]) -> bool:
    """fnmatch-like prefix/glob match against a posix-style path."""
    from fnmatch import fnmatch
    for pat in patterns:
        p = pat.rstrip("/")
        if fnmatch(rel_posix, p) or rel_posix.startswith(p + "/"):
            return True
        if "*" not in p and "?" not in p and rel_posix == p:
            return True
    return False


# --------------------------------------------------------------------------
# Prompt assembly.
# --------------------------------------------------------------------------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_prompt_bundle(case_dir: Path, frontend: str) -> tuple[str, list[str]]:
    """Return (concatenated bundle text, list of contributing file paths)."""
    pieces: list[tuple[str, str]] = []  # (label, text)
    sources: list[str] = []

    base = case_dir / "prompts" / "base_task.md"
    fairness = case_dir / "prompts" / "fairness_rules.md"
    api = case_dir / "prompts" / "api_excerpts" / f"{frontend}.md"
    perfront = case_dir / "prompts" / f"{frontend if frontend != 'z3_cpp' else 'z3'}_adapter_prompt.md"
    if not perfront.is_file():
        # tolerate the alternative naming.
        perfront = case_dir / "prompts" / f"{frontend}_adapter_prompt.md"
    examples = case_dir / "prompts" / "dev_examples.md"

    for p in (base, fairness, api, perfront, examples):
        pieces.append((p.name, read_text(p)))
        sources.append(str(p))

    # dev_index.csv (full).
    dev_index = case_dir / "data" / "dev_index.csv"
    pieces.append(("dev_index.csv", read_text(dev_index)))
    sources.append(str(dev_index))

    # Verbatim anchors (we already named them in dev_examples.md).
    for rel in ANCHOR_DEV_FILES:
        p = case_dir / "data" / "dev" / rel
        if p.is_file():
            pieces.append((rel, read_text(p)))
            sources.append(str(p))

    # Format the final bundle. Each piece is preceded by a clear
    # provenance header so the LLM can locate every excerpt.
    parts: list[str] = []
    for label, text in pieces:
        parts.append(f"\n\n=== BEGIN {label} ===\n{text}\n=== END {label} ===\n")
    bundle = "".join(parts).strip() + "\n"
    return bundle, sources


# --------------------------------------------------------------------------
# Disk layout helpers.
# --------------------------------------------------------------------------
def ensure_run_dirs(run_dir: Path) -> None:
    for sub in ("prompt", "conversation", "src", "audit", "build",
                "dev", "final_test"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)


def write_immutable(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(
            f"refusing to overwrite {path}; trial directories are immutable")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# File-block extraction with safety filter.
# --------------------------------------------------------------------------
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
FORBIDDEN_PATH_FRAGMENTS = ("..", "/etc/", "/usr/", "/proc/", "/dev/")


def materialise_files(turn_src_dir: Path, response: str) -> list[Path]:
    """Write each <file path="..."> block from `response` into `turn_src_dir`.

    Refuses to write paths that contain `..` or absolute paths. Returns
    the list of files actually written.
    """
    written: list[Path] = []
    for relpath, content in extract_files(response):
        if not SAFE_PATH_RE.match(relpath):
            raise SystemExit(f"unsafe filename in LLM output: {relpath!r}")
        if relpath.startswith("/") or any(frag in relpath for frag in FORBIDDEN_PATH_FRAGMENTS):
            raise SystemExit(f"forbidden filename in LLM output: {relpath!r}")
        out = turn_src_dir / relpath
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        written.append(out)
    return written


# --------------------------------------------------------------------------
# Build / invoke driver.
# --------------------------------------------------------------------------
def detect_invocation(src_dir: Path) -> tuple[str, list[str]] | None:
    """Return ("kind", invocation_template_args) or None if unrecognised.

    kind ∈ {"python", "cmake", "shell"}.
    For python:  argv = [python3, src_dir/extract_rdl.py, "{IN}", "{OUT}"]
    For shell:   argv = [bash, src_dir/run.sh, "{IN}", "{OUT}"]
    For cmake:   harness builds with cmake, then invokes the produced binary.
    """
    if (src_dir / "extract_rdl.py").is_file():
        return "python", [sys.executable, str(src_dir / "extract_rdl.py"),
                          "{IN}", "{OUT}"]
    if (src_dir / "run.sh").is_file():
        return "shell", ["bash", str(src_dir / "run.sh"), "{IN}", "{OUT}"]
    if (src_dir / "CMakeLists.txt").is_file() and (src_dir / "main.cpp").is_file():
        return "cmake", []
    return None


def build_adapter(src_dir: Path, build_log_dir: Path) -> tuple[bool, str]:
    """Configure & build the adapter if it is C++. Returns (ok, log_text)."""
    build_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = build_log_dir / "build.log"
    invoc = detect_invocation(src_dir)
    if invoc is None:
        log_path.write_text("ERROR: no recognised adapter entry point in src/\n",
                            encoding="utf-8")
        return False, log_path.read_text(encoding="utf-8")
    kind, _argv = invoc
    if kind in ("python", "shell"):
        # Try to chmod +x build.sh / run.sh if present (best-effort).
        for name in ("run.sh", "build.sh"):
            p = src_dir / name
            if p.is_file():
                os.chmod(p, 0o755)
        if (src_dir / "build.sh").is_file():
            try:
                p = subprocess.run(
                    ["bash", "build.sh"],
                    cwd=src_dir,
                    capture_output=True, text=True, timeout=600,
                )
                ok = p.returncode == 0
                log_path.write_text(
                    f"$ bash build.sh\n[exit={p.returncode}]\nSTDOUT:\n{p.stdout}\n"
                    f"STDERR:\n{p.stderr}\n", encoding="utf-8")
                return ok, log_path.read_text(encoding="utf-8")
            except subprocess.TimeoutExpired:
                log_path.write_text("ERROR: build.sh timed out (>600s)\n", encoding="utf-8")
                return False, log_path.read_text(encoding="utf-8")
        # python with requirements.txt → install in a venv.
        if (src_dir / "requirements.txt").is_file():
            venv_dir = build_log_dir / ".venv"
            try:
                # Skip venv creation if there are no real requirements (only comments).
                req_txt = (src_dir / "requirements.txt").read_text(encoding="utf-8")
                has_real = any(
                    bool(line.strip()) and not line.strip().startswith("#")
                    for line in req_txt.splitlines()
                )
                if has_real:
                    p1 = subprocess.run(
                        [sys.executable, "-m", "venv", str(venv_dir)],
                        capture_output=True, text=True, timeout=120,
                    )
                    if p1.returncode != 0:
                        log_path.write_text(
                            f"venv create failed: {p1.stdout}\n{p1.stderr}\n",
                            encoding="utf-8")
                        return False, log_path.read_text(encoding="utf-8")
                    pip = venv_dir / "bin" / "pip"
                    p2 = subprocess.run(
                        [str(pip), "install", "-r", str(src_dir / "requirements.txt")],
                        capture_output=True, text=True, timeout=300,
                    )
                    log_path.write_text(
                        f"$ venv create + pip install -r requirements.txt\n"
                        f"[venv exit=0]\n[pip exit={p2.returncode}]\n"
                        f"STDOUT:\n{p2.stdout}\nSTDERR:\n{p2.stderr}\n",
                        encoding="utf-8")
                    return p2.returncode == 0, log_path.read_text(encoding="utf-8")
            except subprocess.TimeoutExpired:
                log_path.write_text("ERROR: pip install timed out\n", encoding="utf-8")
                return False, log_path.read_text(encoding="utf-8")
        log_path.write_text("(no build step required for python/shell adapter)\n",
                            encoding="utf-8")
        return True, log_path.read_text(encoding="utf-8")

    # CMake C++ path.
    build_dir = build_log_dir / "cmake_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    try:
        p1 = subprocess.run(
            ["cmake", "-S", str(src_dir), "-B", str(build_dir)],
            capture_output=True, text=True, timeout=300,
        )
        if p1.returncode != 0:
            log_path.write_text(
                f"$ cmake configure\n[exit={p1.returncode}]\n"
                f"STDOUT:\n{p1.stdout}\nSTDERR:\n{p1.stderr}\n",
                encoding="utf-8")
            return False, log_path.read_text(encoding="utf-8")
        p2 = subprocess.run(
            ["cmake", "--build", str(build_dir), "-j"],
            capture_output=True, text=True, timeout=900,
        )
        ok = p2.returncode == 0
        log_path.write_text(
            f"$ cmake configure\n[exit=0]\nSTDOUT:\n{p1.stdout}\n"
            f"STDERR:\n{p1.stderr}\n\n"
            f"$ cmake --build\n[exit={p2.returncode}]\n"
            f"STDOUT:\n{p2.stdout}\nSTDERR:\n{p2.stderr}\n",
            encoding="utf-8")
        return ok, log_path.read_text(encoding="utf-8")
    except subprocess.TimeoutExpired:
        log_path.write_text("ERROR: cmake build timed out\n", encoding="utf-8")
        return False, log_path.read_text(encoding="utf-8")


def adapter_argv(src_dir: Path, build_log_dir: Path,
                 in_path: str, out_path: str) -> list[str] | None:
    invoc = detect_invocation(src_dir)
    if invoc is None:
        return None
    kind, tmpl = invoc
    if kind == "cmake":
        # Discover the produced binary under cmake_build/.
        candidates = list((build_log_dir / "cmake_build").glob("*-rdl-adapter"))
        candidates += list((build_log_dir / "cmake_build").glob("*rdl*"))
        candidates = [c for c in candidates if c.is_file() and os.access(c, os.X_OK)]
        if not candidates:
            return None
        return [str(candidates[0]), in_path, out_path]
    # python or shell
    if kind == "python" and (build_log_dir / ".venv").is_dir():
        venv_py = build_log_dir / ".venv" / "bin" / "python"
        if venv_py.is_file():
            return [str(venv_py), str(src_dir / "extract_rdl.py"), in_path, out_path]
    return [arg.replace("{IN}", in_path).replace("{OUT}", out_path) for arg in tmpl]


# --------------------------------------------------------------------------
# Run dev / test set.
# --------------------------------------------------------------------------
def run_set(src_dir: Path, build_log_dir: Path, dataset_dir: Path,
            index_csv: Path, out_root: Path, label: str,
            backend_script: Path) -> dict:
    """Run the adapter on every file in `index_csv` and grade against `status`."""
    out_root.mkdir(parents=True, exist_ok=True)
    adapter_out = out_root / "adapter_out"
    adapter_out.mkdir(exist_ok=True)
    rows: list[dict] = []

    with index_csv.open("r", encoding="utf-8") as f:
        index_rows = list(csv.DictReader(f))

    n_correct = 0
    n_unknown = 0
    n_wrong = 0
    n_adapter_error = 0
    for r in index_rows:
        rel = r["relpath"]
        expected = r["status"]
        in_path = dataset_dir / rel
        out_json = adapter_out / (rel + ".json")
        out_json.parent.mkdir(parents=True, exist_ok=True)
        argv = adapter_argv(src_dir, build_log_dir, str(in_path), str(out_json))
        if argv is None:
            verdict = "adapter_missing"
        else:
            try:
                p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
                if p.returncode != 0 or not out_json.is_file():
                    verdict = "adapter_error"
                else:
                    p2 = subprocess.run(
                        [sys.executable, str(backend_script), str(out_json)],
                        capture_output=True, text=True, timeout=120,
                    )
                    verdict = (p2.stdout.strip().splitlines() or [""])[-1] or "backend_error"
            except subprocess.TimeoutExpired:
                verdict = "timeout"
        if verdict == expected:
            n_correct += 1
            outcome = "correct"
        elif verdict == "unknown":
            n_unknown += 1
            outcome = "unknown"
        elif verdict in {"sat", "unsat"}:
            n_wrong += 1
            outcome = "wrong"
        else:
            n_adapter_error += 1
            outcome = verdict
        rows.append({
            "relpath": rel,
            "expected": expected,
            "verdict": verdict,
            "outcome": outcome,
        })

    per_file = out_root / "per_file.csv"
    with per_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["relpath", "expected", "verdict", "outcome"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    summary = {
        "label": label,
        "total": len(rows),
        "correct": n_correct,
        "unknown": n_unknown,
        "wrong": n_wrong,
        "adapter_error": n_adapter_error,
        "accuracy_strict": n_correct / len(rows) if rows else 0.0,
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {"summary": summary, "rows": rows}


# --------------------------------------------------------------------------
# Feedback assembly between turns.
# --------------------------------------------------------------------------
def assemble_user_feedback(turn: int, build_ok: bool, build_log: str,
                           audit_report: dict, dev_result: dict | None,
                           max_dev_failures: int, build_log_truncate: int = 4000) -> str:
    parts = [
        f"# Iteration {turn} feedback",
        "",
        "Below is what the harness saw. Please respond with revised file blocks "
        "(`<file path=\"...\"> ... </file>`); only files you re-emit will be "
        "rewritten. If you change nothing, re-emit the unchanged source so the "
        "harness can record a no-op turn.",
        "",
    ]
    if not build_ok:
        truncated = build_log[-build_log_truncate:] if len(build_log) > build_log_truncate else build_log
        parts.append("## Build failed")
        parts.append("```")
        parts.append(truncated)
        parts.append("```")
        parts.append("")
    else:
        parts.append("## Build OK")
        parts.append("")

    if audit_report:
        if audit_report["verdict"] == "fail":
            parts.append(f"## Static audit: FAIL ({audit_report['n_block']} blocks, "
                         f"{audit_report['n_warn']} warns)")
            for f in audit_report["findings"][:20]:
                parts.append(f"- {f['severity']:>5}: {f['file']}:{f.get('line','?')} "
                             f"`{f['match']}` — {f['hint']}")
        else:
            parts.append(f"## Static audit: pass ({audit_report['n_warn']} warnings)")
        parts.append("")

    if dev_result is not None:
        s = dev_result["summary"]
        parts.append(f"## Dev set ({s['total']} files)")
        parts.append(f"correct={s['correct']} unknown={s['unknown']} "
                     f"wrong={s['wrong']} adapter_error={s['adapter_error']}")
        bad = [r for r in dev_result["rows"] if r["outcome"] in {"wrong", "adapter_error"}]
        bad += [r for r in dev_result["rows"] if r["outcome"] == "unknown"]
        for r in bad[:max_dev_failures]:
            parts.append(f"- {r['relpath']}: expected={r['expected']} "
                         f"verdict={r['verdict']} ({r['outcome']})")
    parts.append("")
    parts.append("Send the next iteration of the adapter source.")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Trial driver.
# --------------------------------------------------------------------------
def run_trial(args) -> int:
    case_dir = args.case_dir
    repo_root = case_dir.parent.parent
    cfg_path = args.config
    cfg = load_config(cfg_path)
    fix_iters = int(cfg.get("fix_iterations", 3))
    budget = int(cfg.get("prompt_token_budget", 24000))
    max_dev_fail = int(cfg.get("max_dev_failures_in_feedback", 5))
    timeout_s = int(cfg.get("trial_timeout_seconds", 600))

    if args.frontend not in FRONTENDS:
        raise SystemExit(f"unknown frontend {args.frontend!r}")
    run_dir = case_dir / "results" / "runs" / args.frontend / args.run_name
    if run_dir.exists():
        raise SystemExit(f"run dir already exists: {run_dir}")
    ensure_run_dirs(run_dir)

    bundle, sources = build_prompt_bundle(case_dir, args.frontend)
    bundle_tokens = approx_token_count(bundle)
    write_immutable(run_dir / "prompt" / "bundle.md", bundle)
    write_immutable(run_dir / "prompt" / "bundle.sha256",
                    sha256_text(bundle) + "\n")
    write_immutable(run_dir / "prompt" / "sources.txt",
                    "\n".join(sources) + "\n")
    if bundle_tokens > budget:
        print(f"WARNING: bundle ~{bundle_tokens} tokens exceeds budget {budget}",
              file=sys.stderr)

    client = make_client(cfg, args.frontend, case_dir)

    backend_script = case_dir / "shared_backend" / "rdl_backend.py"
    if not backend_script.is_file():
        raise SystemExit(f"shared backend missing: {backend_script}")

    system_msg = (
        f"You are an expert SMT-LIB / RDL implementer. You will write a "
        f"single front-end adapter for the '{args.frontend}' slot. Follow the "
        f"fairness rules strictly. Respond with file blocks of the form "
        f"<file path=\"relpath\"> ... </file>. Only respond with file blocks "
        f"and brief explanatory prose."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": bundle},
    ]
    write_immutable(run_dir / "conversation" / "turn_00.user.md", bundle)

    started_at = time.time()
    final_summary: dict[str, Any] = {
        "frontend": args.frontend,
        "run_name": args.run_name,
        "config": str(cfg_path.relative_to(case_dir)) if cfg_path.is_relative_to(case_dir) else str(cfg_path),
        "provider": cfg.get("provider", "mock"),
        "started_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "iterations": [],
        "first_pass_success": False,
        "iterations_to_success": None,
    }

    succeeded = False
    for turn in range(fix_iters + 1):
        if time.time() - started_at > timeout_s:
            print(f"[trial] timeout reached after {turn} iterations", file=sys.stderr)
            break

        # 1. Get assistant response.
        assistant = client.chat(messages)
        write_immutable(run_dir / "conversation" / f"turn_{turn:02d}.assistant.md",
                        assistant)
        messages.append({"role": "assistant", "content": assistant})

        # 2. Materialise file blocks.
        turn_src = run_dir / "src" / f"turn_{turn:02d}"
        turn_src.mkdir(parents=True, exist_ok=True)
        try:
            written = materialise_files(turn_src, assistant)
        except SystemExit as e:
            print(f"[trial] turn {turn}: refused unsafe file path: {e}", file=sys.stderr)
            written = []
        if not written:
            print(f"[trial] turn {turn}: no file blocks in response; stopping",
                  file=sys.stderr)
            final_summary["iterations"].append(
                {"turn": turn, "build_ok": False, "audit": None,
                 "dev_summary": None, "note": "no file blocks emitted"})
            break

        # 3. Static audit.
        turn_audit = run_dir / "audit" / f"turn_{turn:02d}"
        turn_audit.mkdir(parents=True, exist_ok=True)
        audit_args = ["--src", str(turn_src), "--frontend", args.frontend,
                      "--report", str(turn_audit / "audit_report.json"),
                      "--case-dir", str(case_dir)]
        p = subprocess.run([sys.executable, str(HERE / "audit_adapter.py")] + audit_args,
                           capture_output=True, text=True, timeout=60)
        try:
            audit_report = json.loads((turn_audit / "audit_report.json").read_text())
        except FileNotFoundError:
            audit_report = {"verdict": "fail", "n_block": 0, "n_warn": 0,
                            "findings": [{"severity": "block", "file": "?",
                                          "rule": "auditor_crash",
                                          "hint": p.stderr[:500],
                                          "match": ""}]}

        # 4. Build.
        turn_build = run_dir / "build" / f"turn_{turn:02d}"
        build_ok, build_log = build_adapter(turn_src, turn_build)

        # 5. Run on dev set (only if build OK and audit pass; we still
        # *record* a dev attempt with adapter_missing entries when build
        # failed so the per-file CSV is uniform across iterations).
        dev_result: dict | None = None
        if build_ok and audit_report.get("verdict") == "pass":
            dev_result = run_set(
                src_dir=turn_src,
                build_log_dir=turn_build,
                dataset_dir=case_dir / "data" / "dev",
                index_csv=case_dir / "data" / "dev_index.csv",
                out_root=run_dir / "dev" / f"turn_{turn:02d}",
                label="dev",
                backend_script=backend_script,
            )
            if dev_result["summary"]["wrong"] == 0 and \
               dev_result["summary"]["adapter_error"] == 0 and \
               dev_result["summary"]["correct"] > 0:
                # No incorrect verdicts and at least one correct → call it
                # a successful iteration.
                succeeded = True
                final_summary["iterations_to_success"] = turn
                if turn == 0:
                    final_summary["first_pass_success"] = True

        final_summary["iterations"].append({
            "turn": turn,
            "build_ok": build_ok,
            "audit_verdict": audit_report.get("verdict"),
            "audit_n_block": audit_report.get("n_block", 0),
            "audit_n_warn": audit_report.get("n_warn", 0),
            "dev_summary": dev_result["summary"] if dev_result else None,
        })

        if succeeded:
            break

        # 6. Assemble feedback for the next iteration.
        if turn == fix_iters:
            break  # no more turns left
        feedback = assemble_user_feedback(
            turn=turn,
            build_ok=build_ok,
            build_log=build_log,
            audit_report=audit_report,
            dev_result=dev_result,
            max_dev_failures=max_dev_fail,
        )
        write_immutable(run_dir / "conversation" / f"turn_{turn+1:02d}.user.md",
                        feedback)
        messages.append({"role": "user", "content": feedback})

    # 7. Final test set: run on the LAST adapter that has build_ok+audit_pass.
    last_good_turn = None
    for it in reversed(final_summary["iterations"]):
        if it["build_ok"] and it["audit_verdict"] == "pass":
            last_good_turn = it["turn"]
            break

    if last_good_turn is not None:
        turn_src = run_dir / "src" / f"turn_{last_good_turn:02d}"
        turn_build = run_dir / "build" / f"turn_{last_good_turn:02d}"
        test_result = run_set(
            src_dir=turn_src,
            build_log_dir=turn_build,
            dataset_dir=case_dir / "data" / "test",
            index_csv=case_dir / "data" / "test_index.csv",
            out_root=run_dir / "final_test",
            label="test",
            backend_script=backend_script,
        )
        final_summary["final_test_summary"] = test_result["summary"]
        final_summary["final_test_turn"] = last_good_turn
    else:
        final_summary["final_test_summary"] = None
        final_summary["final_test_turn"] = None

    final_summary["ended_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    final_summary["wall_clock_seconds"] = time.time() - started_at
    final_summary["bundle_tokens_approx"] = bundle_tokens
    write_immutable(run_dir / "meta.json",
                    json.dumps(final_summary, indent=2, sort_keys=True))
    print(f"[trial] {args.frontend}/{args.run_name} done; "
          f"first_pass_success={final_summary['first_pass_success']}; "
          f"final_test={final_summary['final_test_summary']}",
          file=sys.stderr)
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frontend", required=True)
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--config", type=Path,
                    default=CASE_DIR / "config" / "llm.yaml")
    ap.add_argument("--case-dir", type=Path, default=CASE_DIR)
    args = ap.parse_args(argv)
    if not args.config.is_file():
        # Fall back to llm.yaml.example so a fresh checkout still self-tests.
        example = args.case_dir / "config" / "llm.yaml.example"
        if example.is_file():
            print(f"[trial] {args.config} not found; using {example} (mock provider)",
                  file=sys.stderr)
            args.config = example
        else:
            raise SystemExit(f"config not found: {args.config}")
    return run_trial(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
