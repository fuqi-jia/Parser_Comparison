#!/usr/bin/env python3
"""Read-only aggregator over results/runs/<frontend>/run_NN/meta.json.

Produces, under results/aggregate/:

    summary.csv             one row per (frontend, run_name)
    per_frontend.csv        one row per frontend with means / counts
    table_paper.tex         LaTeX longtable with the headline metrics
    table_paper.md          Markdown table for the README

Importantly, this script never writes anywhere under runs/ — every
file under runs/ is treated as immutable trial evidence.

Adapter SLOC is computed via scripts/loc_count.py over the LAST
turn of each run that satisfies build_ok and audit_pass; runs that
never reached such a state are reported as SLOC=0.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent
DEFAULT_RUNS = CASE_DIR / "results" / "runs"
DEFAULT_OUT = CASE_DIR / "results" / "aggregate"

LOC_SCRIPT = HERE / "loc_count.py"


def loc_for(src_dir: Path) -> int:
    if not src_dir.is_dir():
        return 0
    if not LOC_SCRIPT.is_file():
        # Fallback: count non-blank, non-comment lines for common languages.
        n = 0
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".py", ".cpp", ".c", ".h", ".hpp",
                                        ".java", ".kt", ".sh", ".g4"}:
                continue
            try:
                for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    s = ln.strip()
                    if s and not s.startswith(("#", "//", "/*", "*", "--")):
                        n += 1
            except OSError:
                continue
        return n
    try:
        p = subprocess.run([sys.executable, str(LOC_SCRIPT), str(src_dir)],
                           capture_output=True, text=True, timeout=60)
        return int((p.stdout.strip().split() or ["0"])[-1])
    except (subprocess.TimeoutExpired, ValueError):
        return 0


def find_last_good_src_dir(run_dir: Path, meta: dict) -> Path | None:
    for it in reversed(meta.get("iterations") or []):
        if it.get("build_ok") and it.get("audit_verdict") == "pass":
            tdir = run_dir / "src" / f"turn_{it['turn']:02d}"
            if tdir.is_dir():
                return tdir
    return None


def aggregate(runs_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not runs_dir.is_dir():
        return rows
    for fe_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        for run_dir in sorted(p for p in fe_dir.iterdir() if p.is_dir()):
            meta_path = run_dir / "meta.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            iters = meta.get("iterations") or []
            n_turns = len(iters)
            its_to_success = meta.get("iterations_to_success")
            first_pass = bool(meta.get("first_pass_success"))
            ft = meta.get("final_test_summary") or {}
            best_src = find_last_good_src_dir(run_dir, meta)
            sloc = loc_for(best_src) if best_src else 0
            tok = meta.get("tokens_total") or {}
            rows.append({
                "frontend": fe_dir.name,
                "run_name": run_dir.name,
                "provider": meta.get("provider", ""),
                "model": meta.get("model", ""),
                "first_pass_success": int(first_pass),
                "iterations_to_success": its_to_success
                    if its_to_success is not None else "",
                "n_turns": n_turns,
                "wall_clock_seconds": round(
                    float(meta.get("wall_clock_seconds") or 0.0), 2),
                "chat_seconds": round(float(tok.get("chat_seconds") or 0.0), 2),
                "bundle_tokens_approx": int(meta.get("bundle_tokens_approx") or 0),
                "prompt_tokens": int(tok.get("prompt_tokens") or 0),
                "completion_tokens": int(tok.get("completion_tokens") or 0),
                "reasoning_tokens": int(tok.get("reasoning_tokens") or 0),
                "cache_hit_tokens": int(tok.get("cache_hit_tokens") or 0),
                "total_tokens": int(tok.get("total_tokens") or 0),
                "n_chat_calls": int(tok.get("n_chat_calls") or 0),
                "n_chat_calls_with_usage": int(tok.get("n_chat_calls_with_usage") or 0),
                "test_total": int(ft.get("total") or 0),
                "test_correct": int(ft.get("correct") or 0),
                "test_unknown": int(ft.get("unknown") or 0),
                "test_wrong": int(ft.get("wrong") or 0),
                "test_adapter_error": int(ft.get("adapter_error") or 0),
                "test_accuracy_strict": round(
                    float(ft.get("accuracy_strict") or 0.0), 4),
                "adapter_sloc": sloc,
            })
    return rows


def per_frontend_summary(rows: list[dict]) -> list[dict]:
    by_fe: dict[str, list[dict]] = {}
    for r in rows:
        by_fe.setdefault(r["frontend"], []).append(r)
    out: list[dict] = []
    for fe in sorted(by_fe):
        bucket = by_fe[fe]
        n = len(bucket)
        successes = [r for r in bucket if r["first_pass_success"]]
        any_success = [r for r in bucket
                       if r["iterations_to_success"] not in ("", None)]
        accs = [r["test_accuracy_strict"] for r in bucket]
        slocs = [r["adapter_sloc"] for r in bucket if r["adapter_sloc"] > 0]
        wallclocks = [r["wall_clock_seconds"] for r in bucket]
        # Only count token usage from trials where at least one chat
        # call returned a real usage block (i.e. real-LLM runs); mock
        # runs contribute 0 to "with_usage" so means are not skewed.
        with_usage = [r for r in bucket if r.get("n_chat_calls_with_usage", 0) > 0]
        out.append({
            "frontend": fe,
            "n_trials": n,
            "n_trials_with_usage": len(with_usage),
            "first_pass_success_rate": round(len(successes) / n, 3) if n else 0.0,
            "any_success_rate": round(len(any_success) / n, 3) if n else 0.0,
            "mean_iters_to_success": round(
                statistics.mean(r["iterations_to_success"] for r in any_success),
                2) if any_success else 0.0,
            "mean_test_accuracy": round(statistics.mean(accs), 4) if accs else 0.0,
            "median_adapter_sloc": int(statistics.median(slocs)) if slocs else 0,
            "mean_wallclock_s": round(statistics.mean(wallclocks), 1) if wallclocks else 0.0,
            "mean_prompt_tokens": round(
                statistics.mean(r["prompt_tokens"] for r in with_usage), 1)
                if with_usage else 0.0,
            "mean_completion_tokens": round(
                statistics.mean(r["completion_tokens"] for r in with_usage), 1)
                if with_usage else 0.0,
            "mean_reasoning_tokens": round(
                statistics.mean(r["reasoning_tokens"] for r in with_usage), 1)
                if with_usage else 0.0,
            "mean_total_tokens": round(
                statistics.mean(r["total_tokens"] for r in with_usage), 1)
                if with_usage else 0.0,
        })
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _fmt_tokens(r: dict) -> str:
    """Compact "in / out / reason." for paper tables. Returns '-' if no usage."""
    if r.get("n_trials_with_usage", 0) == 0:
        return "-"
    return (f"{int(r['mean_prompt_tokens'])}/"
            f"{int(r['mean_completion_tokens'])}/"
            f"{int(r['mean_reasoning_tokens'])}")


def write_paper_tables(out_dir: Path, per_fe: list[dict]) -> None:
    md_lines = ["| frontend | trials | first-pass | any success | mean iters | "
                "test acc. | SLOC (median) | wallclock (s) | tokens (in/out/reason.) |",
                "|---|---|---|---|---|---|---|---|---|"]
    for r in per_fe:
        md_lines.append(
            f"| {r['frontend']} | {r['n_trials']} | "
            f"{r['first_pass_success_rate']:.2f} | "
            f"{r['any_success_rate']:.2f} | "
            f"{r['mean_iters_to_success']:.2f} | "
            f"{r['mean_test_accuracy']:.3f} | "
            f"{r['median_adapter_sloc']} | "
            f"{r['mean_wallclock_s']:.1f} | "
            f"{_fmt_tokens(r)} |"
        )
    (out_dir / "table_paper.md").write_text("\n".join(md_lines) + "\n",
                                            encoding="utf-8")

    tex = [
        r"\begin{tabular}{lrrrrrrrr}",
        r"\toprule",
        r"frontend & trials & first-pass & any-succ. & mean iters & "
        r"test acc. & SLOC (med.) & wallclock (s) & tokens (in/out/reason.) \\",
        r"\midrule",
    ]
    for r in per_fe:
        tex.append(
            f"{r['frontend'].replace('_', r'\_')} & {r['n_trials']} & "
            f"{r['first_pass_success_rate']:.2f} & "
            f"{r['any_success_rate']:.2f} & "
            f"{r['mean_iters_to_success']:.2f} & "
            f"{r['mean_test_accuracy']:.3f} & "
            f"{r['median_adapter_sloc']} & "
            f"{r['mean_wallclock_s']:.1f} & "
            f"{_fmt_tokens(r)} \\\\"
        )
    tex.append(r"\bottomrule")
    tex.append(r"\end{tabular}")
    (out_dir / "table_paper.tex").write_text("\n".join(tex) + "\n",
                                             encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rows = aggregate(args.runs)
    if not rows:
        print(f"WARNING: no runs found under {args.runs}", file=sys.stderr)

    summary_fields = ["frontend", "run_name", "provider", "model",
                      "first_pass_success", "iterations_to_success",
                      "n_turns", "wall_clock_seconds", "chat_seconds",
                      "bundle_tokens_approx",
                      "prompt_tokens", "completion_tokens",
                      "reasoning_tokens", "cache_hit_tokens",
                      "total_tokens", "n_chat_calls", "n_chat_calls_with_usage",
                      "test_total", "test_correct",
                      "test_unknown", "test_wrong", "test_adapter_error",
                      "test_accuracy_strict", "adapter_sloc"]
    per_fe = per_frontend_summary(rows)
    per_fe_fields = ["frontend", "n_trials", "n_trials_with_usage",
                     "first_pass_success_rate",
                     "any_success_rate", "mean_iters_to_success",
                     "mean_test_accuracy", "median_adapter_sloc",
                     "mean_wallclock_s",
                     "mean_prompt_tokens", "mean_completion_tokens",
                     "mean_reasoning_tokens", "mean_total_tokens"]

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "summary.csv", rows, summary_fields)
    write_csv(args.out / "per_frontend.csv", per_fe, per_fe_fields)
    write_paper_tables(args.out, per_fe)

    print(f"[aggregate] wrote {args.out / 'summary.csv'} ({len(rows)} rows)",
          file=sys.stderr)
    print(f"[aggregate] wrote {args.out / 'per_frontend.csv'} "
          f"({len(per_fe)} front-ends)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
