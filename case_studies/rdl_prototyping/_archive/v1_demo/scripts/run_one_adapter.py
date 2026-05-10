#!/usr/bin/env python3
"""Run a single adapter against the test suite and emit per-test results.

The adapter contract is uniform: an executable taking ``input.smt2``
``output.json`` arguments. The shared backend then turns ``output.json`` into
a ``sat / unsat / unknown`` verdict. Adapters MUST NOT call any built-in SMT
solver themselves.

Output format (CSV on stdout):

    test,extraction_status,reason,final_answer,expected,test_pass

with one row per test. The harness in ``run_all_adapters.py`` consumes this.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BACKEND = ROOT / "shared_backend" / "rdl_backend.py"
TESTS = ROOT / "tests"


def load_expected() -> dict[str, str]:
    out = {}
    with open(TESTS / "expected.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["test"]] = row["expected"].strip()
    return out


def run_adapter(adapter_cmd: list[str], smt_path: Path, out_json: Path, timeout: float) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            adapter_cmd + [str(smt_path), str(out_json)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (124, "", "adapter timed out")
    return (completed.returncode, completed.stdout, completed.stderr)


def run_backend(json_path: Path, timeout: float) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            [sys.executable, str(BACKEND), str(json_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ("unknown", "backend timed out")
    return (completed.stdout.strip() or "unknown", completed.stderr)


def classify_extraction(json_path: Path) -> tuple[str, str]:
    try:
        with open(json_path) as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return ("error", f"could not read adapter output: {exc}")
    status = payload.get("status", "")
    reason = payload.get("reason", "")
    if status not in {"ok", "unsupported", "error"}:
        return ("error", f"adapter wrote unknown status {status!r}")
    return (status, reason)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a single adapter on the test suite.")
    ap.add_argument("--adapter-cmd", required=True,
                    help="Quoted command-line for the adapter, e.g. \"./build_rdl/.../somt-rdl-adapter\".")
    ap.add_argument("--frontend", required=True, help="Identifier used in result rows.")
    ap.add_argument("--out-csv", help="Path to write per-test CSV; default stdout.")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args(argv)

    adapter_cmd = args.adapter_cmd.split()
    expected = load_expected()

    tmpdir = Path(tempfile.mkdtemp(prefix="rdl_run_"))
    rows = []
    for name in sorted(expected.keys()):
        smt = TESTS / f"{name}.smt2"
        out_json = tmpdir / f"{name}.json"
        rc, _stdout, stderr = run_adapter(adapter_cmd, smt, out_json, args.timeout)
        if rc not in (0,):
            extraction = "error"
            reason = (stderr.strip() or f"adapter exit code {rc}").splitlines()[0][:200]
            verdict = "unknown"
        else:
            extraction, reason = classify_extraction(out_json)
            verdict, _berr = run_backend(out_json, args.timeout)
        exp = expected[name]
        rows.append({
            "test": name,
            "extraction_status": extraction,
            "reason": reason,
            "final_answer": verdict,
            "expected": exp,
            "test_pass": "true" if verdict == exp else "false",
            "frontend": args.frontend,
        })

    fieldnames = ["frontend", "test", "extraction_status", "reason", "final_answer", "expected", "test_pass"]
    if args.out_csv:
        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        with open(args.out_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
