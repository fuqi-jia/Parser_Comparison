#!/usr/bin/env python3
"""Run N independent LLM trials for one or more front-ends.

Each trial gets its own immutable run dir under
``results/runs/<frontend>/run_NN/``. The campaign is incremental: if a
target run dir already exists, the campaign skips it (re-running by hand
requires deleting that dir first; the harness deliberately refuses to
overwrite).

Usage examples
--------------

Run 10 mock trials for pysmt only:

    python3 scripts/run_llm_campaign.py \
        --frontends pysmt --trials 10 \
        --config config/llm.yaml.example

Run 10 trials for every front-end with the production config:

    python3 scripts/run_llm_campaign.py \
        --config config/llm.yaml \
        --frontends all --trials 10
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent

ALL_FRONTENDS = ["somtparser", "z3_cpp", "cvc5_cpp", "smt_switch",
                 "pysmt", "antlr4", "jsmtlib"]


def run_one(frontend: str, run_name: str, config: Path) -> int:
    p = subprocess.run(
        [sys.executable, str(HERE / "run_llm_trial.py"),
         "--frontend", frontend,
         "--run-name", run_name,
         "--config", str(config),
         "--case-dir", str(CASE_DIR)],
    )
    return p.returncode


def expand_frontends(arg: Iterable[str]) -> list[str]:
    items = list(arg)
    if any(x.lower() == "all" for x in items):
        return list(ALL_FRONTENDS)
    out: list[str] = []
    for x in items:
        if x not in ALL_FRONTENDS:
            raise SystemExit(f"unknown frontend {x!r}; options: {ALL_FRONTENDS} or 'all'")
        out.append(x)
    return out or list(ALL_FRONTENDS)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frontends", nargs="+", default=["all"],
                    help=f"any of {ALL_FRONTENDS} or 'all'")
    ap.add_argument("--trials", type=int, default=10,
                    help="number of trials per front-end (default 10)")
    ap.add_argument("--config", type=Path,
                    default=CASE_DIR / "config" / "llm.yaml")
    ap.add_argument("--start", type=int, default=0,
                    help="first trial index (run_NN starts at this)")
    ap.add_argument("--stop-on-error", action="store_true",
                    help="abort the campaign on the first failing trial")
    args = ap.parse_args(argv)

    if not args.config.is_file():
        example = args.config.with_suffix(".yaml.example")
        if example.is_file():
            print(f"[campaign] {args.config} missing; using {example}", file=sys.stderr)
            args.config = example
        else:
            raise SystemExit(f"config {args.config} not found")

    frontends = expand_frontends(args.frontends)
    print(f"[campaign] front-ends: {frontends}; trials each: {args.trials}; "
          f"config: {args.config}", file=sys.stderr)

    n_started = 0
    n_skipped = 0
    n_failed = 0
    for fe in frontends:
        for i in range(args.start, args.start + args.trials):
            run_name = f"run_{i:02d}"
            run_dir = CASE_DIR / "results" / "runs" / fe / run_name
            if run_dir.exists():
                print(f"[campaign] skip existing {fe}/{run_name}", file=sys.stderr)
                n_skipped += 1
                continue
            rc = run_one(fe, run_name, args.config)
            if rc != 0:
                n_failed += 1
                print(f"[campaign] FAIL {fe}/{run_name} rc={rc}", file=sys.stderr)
                if args.stop_on_error:
                    return rc
            n_started += 1

    print(f"[campaign] done: started={n_started} skipped={n_skipped} failed={n_failed}",
          file=sys.stderr)
    return 1 if n_failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
