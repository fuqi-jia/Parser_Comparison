#!/usr/bin/env python3
"""Run every registered adapter and emit ``run_per_test.csv`` and ``run_meta.json``.

The orchestrator then delegates to ``score_runs.py`` and ``gen_table1.py`` to
produce ``run_summary.csv``, ``run_summary.md`` and ``table1.tex``. Adapters
that have not been implemented yet are recorded honestly as
``adapter_status=not_implemented``; their rows are never marked as passing.

v1 supports a single deterministic run. ``case_study_notes.md`` documents the
planned extension to N independent LLM-generated re-runs (under
``results/runs/{frontend}/run_NN``) for the paper's ``?/10`` Table 1.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TESTS = ROOT / "tests"
RESULTS = ROOT / "results"
RUN_ONE = HERE / "run_one_adapter.py"
LOC_COUNT = HERE / "loc_count.py"
SCORE_RUNS = HERE / "score_runs.py"
GEN_TABLE1 = HERE / "gen_table1.py"


@dataclass
class AdapterSpec:
    name: str
    label: str
    status: str  # "real" or "not_implemented"
    binary_relpath: str | None = None
    sources: list[str] = field(default_factory=list)
    note: str = ""


REGISTRY: list[AdapterSpec] = [
    AdapterSpec(
        name="somtparser",
        label="SOMTParser",
        status="real",
        binary_relpath="build_rdl/case_studies/rdl_prototyping/adapters/somtparser/somt-rdl-adapter",
        sources=[
            "case_studies/rdl_prototyping/adapters/somtparser/main.cpp",
            "case_studies/rdl_prototyping/adapters/somtparser/CMakeLists.txt",
        ],
    ),
    AdapterSpec(name="z3_cpp", label="Z3 (C++ AST)", status="not_implemented",
                note="Parse + AST traversal sufficient; check-sat must remain unused."),
    AdapterSpec(name="cvc5_cpp", label="cvc5 (C++ AST)", status="not_implemented",
                note="Same fairness rule as Z3: parse only."),
    AdapterSpec(name="smt_switch", label="smt-switch", status="not_implemented",
                note="Vendor-neutral term API; pick a parsing backend that does not solve."),
    AdapterSpec(name="pysmt", label="pySMT", status="not_implemented",
                note="Parse via SmtLibParser; do not call solve()."),
    AdapterSpec(name="antlr4", label="ANTLR4 grammar", status="not_implemented",
                note="Untyped CST; minimal symbol table needed for atom extraction."),
    AdapterSpec(name="jsmtlib", label="jSMTLIB", status="not_implemented",
                note="JVM front-end; subprocess and stream rdl_atoms.json."),
]


def loc(repo_root: Path, paths: list[str]) -> int:
    if not paths:
        return 0
    abs_paths = [str(repo_root / p) for p in paths]
    completed = subprocess.run(
        [sys.executable, str(LOC_COUNT), *abs_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return 0
    out_lines = [ln for ln in completed.stdout.splitlines() if ln.strip().isdigit()]
    return int(out_lines[-1]) if out_lines else 0


def backend_loc(repo_root: Path) -> int:
    return loc(repo_root, [
        "case_studies/rdl_prototyping/shared_backend/rdl_backend.py",
        "case_studies/rdl_prototyping/shared_backend/check_rdl_json.py",
    ])


def load_expected() -> dict[str, str]:
    out = {}
    with open(TESTS / "expected.csv", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["test"]] = row["expected"].strip()
    return out


def run_real_adapter(spec: AdapterSpec, repo_root: Path, timeout: float):
    binary = repo_root / spec.binary_relpath
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return None, "build_failed", f"binary not found at {binary}"
    cmd = [sys.executable, str(RUN_ONE),
           "--adapter-cmd", str(binary),
           "--frontend", spec.name,
           "--timeout", str(timeout)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None, "build_failed", completed.stderr.strip()[:300]
    rows = list(csv.DictReader(completed.stdout.splitlines()))
    return rows, "ok", ""


def synthesize_not_implemented(spec: AdapterSpec, expected: dict[str, str]) -> list[dict]:
    return [{
        "frontend": spec.name,
        "test": name,
        "extraction_status": "not_implemented",
        "reason": spec.note,
        "final_answer": "",
        "expected": expected[name],
        "test_pass": "false",
    } for name in sorted(expected.keys())]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=None,
                    help="Path to the Parser_Comparison repo root (defaults to ../../..).")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--out-dir", default=str(RESULTS))
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else ROOT.parent.parent.resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    expected = load_expected()

    all_rows: list[dict] = []
    meta_adapters: list[dict] = []
    for spec in REGISTRY:
        if spec.status == "real":
            rows, build_status, build_msg = run_real_adapter(spec, repo_root, args.timeout)
            if rows is None:
                rows = [{
                    "frontend": spec.name,
                    "test": name,
                    "extraction_status": "error",
                    "reason": build_msg,
                    "final_answer": "unknown",
                    "expected": expected[name],
                    "test_pass": "false",
                } for name in sorted(expected.keys())]
                adapter_status = "build_failed"
            else:
                adapter_status = build_status
            adapter_loc = loc(repo_root, spec.sources)
        else:
            rows = synthesize_not_implemented(spec, expected)
            adapter_status = "not_implemented"
            adapter_loc = 0
        all_rows.extend(rows)
        meta_adapters.append({
            "name": spec.name,
            "label": spec.label,
            "status": spec.status,
            "adapter_status": adapter_status,
            "adapter_loc": adapter_loc,
            "note": spec.note,
        })

    per_test_csv = out_dir / "run_per_test.csv"
    fieldnames = ["frontend", "test", "extraction_status", "reason",
                  "final_answer", "expected", "test_pass"]
    with open(per_test_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    meta_path = out_dir / "run_meta.json"
    with open(meta_path, "w") as fh:
        json.dump({
            "backend_loc": backend_loc(repo_root),
            "tests_total": len(expected),
            "adapters": meta_adapters,
        }, fh, indent=2)

    summary_csv = out_dir / "run_summary.csv"
    summary_md = out_dir / "run_summary.md"
    table_tex = out_dir / "table1.tex"

    score_rc = subprocess.run([
        sys.executable, str(SCORE_RUNS),
        "--per-test-csv", str(per_test_csv),
        "--meta-json", str(meta_path),
        "--out-summary-csv", str(summary_csv),
        "--out-summary-md", str(summary_md),
    ], check=False)
    if score_rc.returncode != 0:
        return 1

    table_rc = subprocess.run([
        sys.executable, str(GEN_TABLE1),
        "--summary-csv", str(summary_csv),
        "--out-tex", str(table_tex),
    ], check=False)
    if table_rc.returncode != 0:
        return 1

    real_specs = [m for m in meta_adapters if m["status"] == "real"]
    real_pass = 0
    real_total = 0
    for r in all_rows:
        if any(m["name"] == r["frontend"] for m in real_specs):
            real_total += 1
            if r["test_pass"] == "true":
                real_pass += 1
    print(f"Real-adapter test pass rate: {real_pass}/{real_total}", file=sys.stderr)
    print(f"Wrote {per_test_csv}", file=sys.stderr)
    print(f"Wrote {meta_path}", file=sys.stderr)
    return 0 if real_pass == real_total else 2


if __name__ == "__main__":
    sys.exit(main())
