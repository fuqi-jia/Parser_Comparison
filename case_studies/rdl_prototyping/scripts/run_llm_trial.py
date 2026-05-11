#!/usr/bin/env python3
"""Single LLM trial for one front-end.

Usage:
    python3 run_llm_trial.py \
        --frontend pysmt --run-name run_00 \
        [--config config/llm.yaml] [--case-dir case_studies/rdl_prototyping]

The trial creates an immutable per-run directory tree:

    results/runs/<frontend>/<run_name>/
        meta.json                          # configuration + final summary
                                           # (incl. tokens_total + per-turn usage)
        prompt/                            # prompt bundle, hashed
            bundle.md                      # full text concatenated
            bundle.sha256
            sources.txt                    # which files contributed
        conversation/
            turn_00.user.md
            turn_00.assistant.md
            turn_00.usage.json             # token usage + wall time for this turn
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
    prompt_stem = {
        "z3_cpp": "z3",
        "cvc5_cpp": "cvc5",
    }.get(frontend, frontend)
    perfront = case_dir / "prompts" / f"{prompt_stem}_adapter_prompt.md"
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
# Vendored dependency discovery.
#
# The repo ships every front-end's parser as a submodule or pre-built
# package under SOMTParser/ or external/<name>/. To keep the LLM trial
# fair across all front-ends, the harness probes those locations and
# (a) passes the resolved absolute paths to ``cmake configure`` as
#     -D<KEY>=<PATH> definitions, and
# (b) exports the same names as environment variables for build.sh /
#     run.sh / Python / Java adapters,
# (c) prepends every discovered shared-library directory to
#     ``LD_LIBRARY_PATH`` when invoking the produced adapter binary, so
#     the LLM never has to hard-code rpaths or assume a system install.
#
# Keys are only present if the underlying path actually exists, so a
# prompt can say "if Z3_ROOT is set, use ${Z3_ROOT}/include and
# ${Z3_ROOT}/bin; otherwise fall back to system z3".
# --------------------------------------------------------------------------
def discover_vendored_deps(repo_root: Path) -> dict[str, str]:
    """Return absolute-path string values for every vendored dep we can
    find under ``repo_root``. Missing paths are simply omitted."""
    deps: dict[str, str] = {"PARSER_COMPARISON_ROOT": str(repo_root)}

    somt = repo_root / "SOMTParser"
    if (somt / "CMakeLists.txt").is_file() and (somt / "include").is_dir():
        deps["SOMTPARSER_ROOT"] = str(somt)
        deps["SOMTPARSER_INCLUDE_DIR"] = str(somt / "include")

    # Z3: prefer the vendored pre-built glibc 2.39 package.
    z3_pkg = next(iter(sorted(
        (repo_root / "external" / "z3").glob("z3-*-x64-*"))), None)
    if z3_pkg and (z3_pkg / "include" / "z3++.h").is_file():
        deps["Z3_ROOT"] = str(z3_pkg)
        deps["Z3_INCLUDE_DIR"] = str(z3_pkg / "include")
        # Z3 ships its libs under bin/ in the prebuilt package, not lib/.
        lib_candidates = [z3_pkg / "bin", z3_pkg / "lib"]
        for lib_dir in lib_candidates:
            if any(lib_dir.glob("libz3*")):
                deps["Z3_LIBRARY_DIR"] = str(lib_dir)
                break

    # cvc5: vendored as the libcxx-static pre-built package; .a only.
    cvc5_pkg = repo_root / "external" / "cvc5" / "cvc5-Linux-x86_64-libcxx-static"
    if (cvc5_pkg / "include" / "cvc5" / "cvc5.h").is_file():
        deps["CVC5_ROOT"] = str(cvc5_pkg)
        deps["CVC5_INCLUDE_DIR"] = str(cvc5_pkg / "include")
        if any((cvc5_pkg / "lib").glob("libcvc5*")):
            deps["CVC5_LIBRARY_DIR"] = str(cvc5_pkg / "lib")

    # smt-switch: source tree under smt-switch-1.0.6/ and a sibling
    # build/ with .so artefacts produced by external/smt-switch/build.sh.
    ss_root = repo_root / "external" / "smt-switch"
    ss_src = ss_root / "smt-switch-1.0.6"
    if (ss_src / "include" / "smt.h").is_file():
        deps["SMT_SWITCH_ROOT"] = str(ss_root)
        deps["SMT_SWITCH_INCLUDE_DIR"] = str(ss_src / "include")
    ss_build = ss_root / "build" / "smt-switch-1.0.6"
    if (ss_build / "libsmt-switch.so").is_file():
        deps["SMT_SWITCH_LIBRARY_DIR"] = str(ss_build)
    ss_cvc5_solver = ss_build / "cvc5"
    if (ss_cvc5_solver / "libsmt-switch-cvc5.so").is_file():
        deps["SMT_SWITCH_CVC5_LIBRARY_DIR"] = str(ss_cvc5_solver)

    # ANTLR4 / jSMTLIB: vendored as ready-to-use class files and
    # grammar/Makefile/run.sh under external/<name>_parser/. The
    # adapter is free to either reuse those artefacts directly or
    # regenerate them; either way the path is available.
    antlr4 = repo_root / "external" / "antlr4_parser"
    if (antlr4 / "SMTLIBv2.g4").is_file():
        deps["ANTLR4_ROOT"] = str(antlr4)
    jsmtlib = repo_root / "external" / "jsmtlib"
    if (jsmtlib / "build.sh").is_file():
        deps["JSMTLIB_ROOT"] = str(jsmtlib)
        # The downloaded jSMTLIB-0.9.10.1 tree (jars + bundled grammar).
        for cand in jsmtlib.glob("jSMTLIB-*"):
            if cand.is_dir():
                deps["JSMTLIB_DIST_ROOT"] = str(cand)
                break

    return deps


def deps_cmake_defines(deps: dict[str, str]) -> list[str]:
    """Render `-DKEY=PATH` flags for cmake configure."""
    return [f"-D{k}={v}" for k, v in sorted(deps.items())]


def deps_subprocess_env(deps: dict[str, str]) -> dict[str, str]:
    """Build a subprocess env dict: parent env + dep vars + LD_LIBRARY_PATH.

    LD_LIBRARY_PATH is augmented with every discovered library dir so
    the produced adapter binary can dlopen libz3.so /
    libsmt-switch*.so at exec time without rpaths.
    """
    env = dict(os.environ)
    env.update(deps)
    extra_lib_dirs = [
        deps.get("Z3_LIBRARY_DIR"),
        deps.get("CVC5_LIBRARY_DIR"),
        deps.get("SMT_SWITCH_LIBRARY_DIR"),
        deps.get("SMT_SWITCH_CVC5_LIBRARY_DIR"),
    ]
    extra_lib_dirs = [d for d in extra_lib_dirs if d]
    if extra_lib_dirs:
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(extra_lib_dirs + (
            [existing] if existing else []))
    return env


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


def diagnose_missing_entry(src_dir: Path) -> str:
    """Return a descriptive build-error message for the LLM when no
    invocation can be detected in ``src_dir``. The message must be
    actionable so the LLM can self-correct on the next iteration."""
    files = sorted(
        p.relative_to(src_dir).as_posix()
        for p in src_dir.rglob("*") if p.is_file()
    )
    if not files:
        return (
            "ERROR: no files were emitted to src/. The LLM response "
            "contained no recognised file blocks. Please reply using "
            "either <file path=\"relpath\"> ... </file> XML blocks OR "
            "markdown-fenced code blocks whose first line is "
            "`# file: relpath` (or `// file: relpath` for C/C++/Java).\n"
        )
    has_main = (src_dir / "main.cpp").is_file()
    has_cmake = (src_dir / "CMakeLists.txt").is_file()
    if has_main and not has_cmake:
        return (
            "ERROR: src/ contains main.cpp but no CMakeLists.txt; the "
            "C++ harness requires BOTH files (the harness runs "
            "`cmake -S src -B build -D<vendored-dep>=<path> ... && "
            "cmake --build build -j`). Please re-emit a CMakeLists.txt "
            "that compiles main.cpp and links against the parser "
            "library you chose. Use the vendored CMake variables that "
            "the harness sets (e.g. ${SOMTPARSER_ROOT}, ${Z3_ROOT}, "
            "${CVC5_ROOT}, ${SMT_SWITCH_ROOT}); the JSON file "
            "`../prompt/vendored_deps.json` of this run lists which "
            "ones are actually populated.\n"
            f"Files currently in src/: {files}\n"
        )
    if has_cmake and not has_main:
        return (
            "ERROR: src/ contains CMakeLists.txt but no main.cpp. "
            "Please re-emit the C++ source file referenced by your "
            "CMakeLists.txt.\n"
            f"Files currently in src/: {files}\n"
        )
    java_files = [f for f in files if f.endswith(".java")]
    if java_files and not (src_dir / "build.sh").is_file():
        return (
            f"ERROR: src/ contains Java sources ({java_files}) but no "
            "build.sh. Please ship build.sh that compiles the Java "
            "code (e.g. `javac -d classes *.java`) and run.sh that "
            "invokes the adapter with `java ... \"$@\"`.\n"
            f"Files currently in src/: {files}\n"
        )
    if java_files and not (src_dir / "run.sh").is_file():
        return (
            f"ERROR: src/ contains Java sources ({java_files}) and "
            "build.sh but no run.sh. Please ship a run.sh that takes "
            "`input.smt2 output.json` arguments and invokes the "
            "compiled Java entry class.\n"
            f"Files currently in src/: {files}\n"
        )
    return (
        "ERROR: no recognised adapter entry point in src/.\n"
        "Expected one of:\n"
        "  * extract_rdl.py            (python path; "
        "harness runs `python3 extract_rdl.py IN OUT`)\n"
        "  * run.sh                    (shell path; "
        "build.sh optional, harness runs `bash run.sh IN OUT`)\n"
        "  * CMakeLists.txt + main.cpp (C++ path; "
        "harness runs cmake configure/build then exec the binary)\n"
        f"Files currently in src/: {files}\n"
    )


def build_adapter(src_dir: Path, build_log_dir: Path,
                  deps: dict[str, str] | None = None) -> tuple[bool, str]:
    """Configure & build the adapter if it is C++. Returns (ok, log_text).

    ``deps`` is the mapping returned by ``discover_vendored_deps``. Its
    keys are exposed both as CMake ``-D<KEY>=<PATH>`` definitions
    (for the cmake path) and as subprocess environment variables (for
    the shell / python path), plus an augmented ``LD_LIBRARY_PATH``
    that includes every vendored library directory.
    """
    deps = deps or {}
    env = deps_subprocess_env(deps)
    build_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = build_log_dir / "build.log"
    invoc = detect_invocation(src_dir)
    if invoc is None:
        msg = diagnose_missing_entry(src_dir)
        log_path.write_text(msg, encoding="utf-8")
        return False, msg
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
                    env=env,
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
                        env=env,
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
                        env=env,
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

    # CMake C++ path: pre-pend -D<KEY>=<PATH> for every vendored dep so
    # the adapter's CMakeLists.txt can rely on $SOMTPARSER_ROOT etc.
    build_dir = build_log_dir / "cmake_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    cfg_cmd = ["cmake", "-S", str(src_dir), "-B", str(build_dir)] \
              + deps_cmake_defines(deps)
    try:
        p1 = subprocess.run(
            cfg_cmd, env=env,
            capture_output=True, text=True, timeout=300,
        )
        if p1.returncode != 0:
            log_path.write_text(
                f"$ {' '.join(cfg_cmd)}\n[exit={p1.returncode}]\n"
                f"STDOUT:\n{p1.stdout}\nSTDERR:\n{p1.stderr}\n",
                encoding="utf-8")
            return False, log_path.read_text(encoding="utf-8")
        p2 = subprocess.run(
            ["cmake", "--build", str(build_dir), "-j"],
            env=env,
            capture_output=True, text=True, timeout=900,
        )
        ok = p2.returncode == 0
        log_path.write_text(
            f"$ {' '.join(cfg_cmd)}\n[exit=0]\nSTDOUT:\n{p1.stdout}\n"
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
            backend_bin: Path,
            deps: dict[str, str] | None = None) -> dict:
    """Run the adapter on every file in `index_csv` and grade against `status`.

    ``deps`` is threaded into the adapter's subprocess env so the
    binary/Python/Java entry point can dlopen vendored ``libz3.so`` /
    ``libsmt-switch.so`` / read ``$SOMTPARSER_ROOT`` at run time.

    ``backend_bin`` is the path to the C++ shared backend binary; we call
    it with a single positional arg (the path to the adapter's emitted
    ``rdl_atoms.json``) and read sat/unsat/unknown from stdout. See
    shared_backend/cpp/ for the implementation.
    """
    out_root.mkdir(parents=True, exist_ok=True)
    adapter_out = out_root / "adapter_out"
    adapter_out.mkdir(exist_ok=True)
    rows: list[dict] = []

    env = deps_subprocess_env(deps or {})

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
                p = subprocess.run(argv, env=env,
                                   capture_output=True, text=True, timeout=60)
                if p.returncode != 0 or not out_json.is_file():
                    verdict = "adapter_error"
                else:
                    p2 = subprocess.run(
                        [str(backend_bin), str(out_json)],
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

    # Pre-flight: build the prompt bundle and instantiate the client
    # BEFORE creating run_dir. Both can raise (e.g. missing prompt file,
    # missing API key), and we do not want a half-empty run_NN/ directory
    # littering results/runs/ when they do.
    bundle, sources = build_prompt_bundle(case_dir, args.frontend)
    bundle_tokens = approx_token_count(bundle)
    client = make_client(cfg, args.frontend, case_dir)

    # Shared backend (v2): C++ binary built once from shared_backend/cpp/.
    # The Python reference at shared_backend/rdl_backend.py is kept as a
    # spec, but the trial harness exclusively calls the compiled C++ binary
    # so verdicts are byte-for-byte deterministic across runs / machines.
    backend_bin = case_dir / "shared_backend" / "cpp" / "build" / "rdl_backend"
    if not backend_bin.is_file():
        raise SystemExit(
            f"shared backend C++ binary missing at {backend_bin}.\n"
            f"Build it once with: bash {backend_bin.parent.parent}/build.sh"
        )
    backend_sha256 = hashlib.sha256(backend_bin.read_bytes()).hexdigest()

    # Discover vendored parser dependencies in repo. These are then
    # injected into every cmake configure (-D<KEY>=<PATH>) and every
    # subprocess env (so build.sh / run.sh / adapter binary all see
    # the same paths). Recorded in meta.json for the paper.
    deps = discover_vendored_deps(repo_root)

    # All preconditions ok → commit to creating run_dir.
    ensure_run_dirs(run_dir)
    write_immutable(run_dir / "prompt" / "bundle.md", bundle)
    write_immutable(run_dir / "prompt" / "bundle.sha256",
                    sha256_text(bundle) + "\n")
    write_immutable(run_dir / "prompt" / "sources.txt",
                    "\n".join(sources) + "\n")
    write_immutable(run_dir / "prompt" / "vendored_deps.json",
                    json.dumps(deps, indent=2, sort_keys=True) + "\n")
    if bundle_tokens > budget:
        print(f"WARNING: bundle ~{bundle_tokens} tokens exceeds budget {budget}",
              file=sys.stderr)

    system_msg = (
        f"You are an expert SMT-LIB / RDL implementer. You will write a "
        f"single front-end adapter for the '{args.frontend}' slot. Follow "
        f"the fairness rules strictly. Respond with the adapter source code "
        f"as either <file path=\"relpath\"> ... </file> XML blocks OR "
        f"markdown-fenced code blocks whose first content line is "
        f"`# file: relpath` (or `// file: relpath` for C/C++/Java). Paths "
        f"are RELATIVE to the run's src/ directory; never prepend "
        f"`case_studies/`, `results/`, or absolute paths. Brief explanatory "
        f"prose is fine; everything outside recognised file blocks is "
        f"ignored."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": bundle},
    ]
    write_immutable(run_dir / "conversation" / "turn_00.user.md", bundle)

    started_at = time.time()
    tokens_total = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cache_hit_tokens": 0,
        "total_tokens": 0,
        "chat_seconds": 0.0,
        "n_chat_calls": 0,
        "n_chat_calls_with_usage": 0,
    }
    final_summary: dict[str, Any] = {
        "frontend": args.frontend,
        "run_name": args.run_name,
        "config": str(cfg_path.relative_to(case_dir)) if cfg_path.is_relative_to(case_dir) else str(cfg_path),
        "provider": cfg.get("provider", "mock"),
        "model": cfg.get("model", ""),
        "started_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "iterations": [],
        "tokens_total": tokens_total,
        "first_pass_success": False,
        "iterations_to_success": None,
        "vendored_deps": deps,
        "backend_path": str(backend_bin.relative_to(case_dir))
                        if backend_bin.is_relative_to(case_dir) else str(backend_bin),
        "backend_sha256": backend_sha256,
    }

    succeeded = False
    for turn in range(fix_iters + 1):
        if time.time() - started_at > timeout_s:
            print(f"[trial] timeout reached after {turn} iterations", file=sys.stderr)
            break

        # 1. Get assistant response.
        chat_t0 = time.time()
        assistant, usage = client.chat(messages)
        chat_seconds = time.time() - chat_t0
        write_immutable(run_dir / "conversation" / f"turn_{turn:02d}.assistant.md",
                        assistant)
        # Per-turn usage record — always written so paper tables can
        # tell mock turns (usage=null) from real-LLM turns.
        usage_record = {
            "turn": turn,
            "provider": cfg.get("provider", "mock"),
            "model": cfg.get("model", ""),
            "chat_seconds": chat_seconds,
            "usage": usage,
            "response_chars": len(assistant),
            "response_approx_tokens": approx_token_count(assistant),
            "messages_chars_in": sum(len(m.get("content", "")) for m in messages),
        }
        write_immutable(run_dir / "conversation" / f"turn_{turn:02d}.usage.json",
                        json.dumps(usage_record, indent=2, sort_keys=True))
        tokens_total["chat_seconds"] += chat_seconds
        tokens_total["n_chat_calls"] += 1
        if usage is not None:
            tokens_total["n_chat_calls_with_usage"] += 1
            for k in ("prompt_tokens", "completion_tokens",
                      "reasoning_tokens", "cache_hit_tokens", "total_tokens"):
                tokens_total[k] += int(usage.get(k, 0) or 0)
            # Length-truncation on a reasoning model means the chain-of-
            # thought ate the whole budget; flag it loudly so the user
            # bumps max_tokens before paying for another full campaign.
            if usage.get("finish_reason") == "length":
                print(f"[trial] WARNING: turn {turn} response was truncated "
                      f"(finish_reason='length'); raise max_tokens in llm.yaml "
                      f"and re-run. response_chars={len(assistant)}, "
                      f"completion_tokens={usage.get('completion_tokens')} "
                      f"(of which reasoning_tokens="
                      f"{usage.get('reasoning_tokens')})", file=sys.stderr)
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
            final_summary["iterations"].append({
                "turn": turn,
                "build_ok": False,
                "audit": None,
                "dev_summary": None,
                "note": "no file blocks emitted",
                "chat_seconds": chat_seconds,
                "usage": usage,
            })
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
        build_ok, build_log = build_adapter(turn_src, turn_build, deps=deps)

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
                backend_bin=backend_bin,
                deps=deps,
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
            "chat_seconds": chat_seconds,
            "usage": usage,
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
            backend_bin=backend_bin,
            deps=deps,
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
