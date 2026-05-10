#!/usr/bin/env python3
"""Aggregate ``run_per_test.csv`` and ``run_meta.json`` into a run summary.

Outputs:
  * ``run_summary.csv`` -- one row per front-end with totals and category.
  * ``run_summary.md`` -- a Markdown rendering of the same data.

This script reads the per-test rows produced by ``run_all_adapters.py`` so it
can be re-run on its own after a hand-edit of the per-test CSV (for example,
during paper-table preparation).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def classify_failure(rows: list[dict]) -> str:
    if not rows:
        return "build_issue"
    statuses = [r["extraction_status"] for r in rows]
    if all(s == "not_implemented" for s in statuses):
        return "not_implemented"
    if all(r["test_pass"] == "true" for r in rows):
        return "ok"
    for r in rows:
        if r["test_pass"] == "true":
            continue
        s = r["extraction_status"]
        reason = (r.get("reason") or "").lower()
        if s == "error":
            if "parse" in reason:
                return "parser_api_issue"
            if "linear" in reason or "non-linear" in reason:
                return "typed_term_issue"
            if "numeric" in reason or "numeral" in reason:
                return "numeral_extraction_issue"
            return "rdl_backend_issue"
        if s == "unsupported" and r["expected"] != "unknown":
            return "boolean_structure_issue"
    return "rdl_backend_issue"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-test-csv", required=True)
    ap.add_argument("--meta-json", required=True)
    ap.add_argument("--out-summary-csv", required=True)
    ap.add_argument("--out-summary-md", required=True)
    args = ap.parse_args(argv)

    with open(args.per_test_csv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(args.meta_json) as fh:
        meta = json.load(fh)

    by_frontend: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_frontend[r["frontend"]].append(r)

    summary = []
    expected_by_test = {r["test"]: r["expected"] for r in rows}
    n_tests = len(set(r["test"] for r in rows))

    for spec in meta["adapters"]:
        name = spec["name"]
        spec_rows = by_frontend.get(name, [])
        if spec.get("status") == "not_implemented":
            tests_passed = 0
            adapter_status = "not_implemented"
            cat = "not_implemented"
        else:
            tests_passed = sum(1 for r in spec_rows if r["test_pass"] == "true")
            adapter_status = spec.get("adapter_status", "ok")
            cat = classify_failure(spec_rows) if adapter_status == "ok" else "build_issue"
        summary.append({
            "frontend": name,
            "label": spec.get("label", name),
            "adapter_status": adapter_status,
            "tests_total": n_tests or len(expected_by_test) or len(spec_rows),
            "tests_passed": tests_passed,
            "first_pass_success": "true" if tests_passed == (n_tests or 0) and tests_passed > 0 else "false",
            "adapter_loc": spec.get("adapter_loc", 0),
            "backend_loc": meta.get("backend_loc", 0),
            "failure_category": cat,
            "note": spec.get("note", ""),
        })

    fieldnames = ["frontend", "label", "adapter_status", "tests_total",
                  "tests_passed", "first_pass_success", "adapter_loc",
                  "backend_loc", "failure_category", "note"]
    out_csv = Path(args.out_summary_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary)

    n = n_tests or 0
    md = ["# RDL prototyping case study -- run summary\n",
          "\n",
          "Single deterministic run. ``not_implemented`` adapters are documented stubs; ",
          "their rows are recorded honestly and never marked as passing.\n",
          "\n",
          "| Front-end | Adapter | Tests passed | First pass | Adapter LoC | Backend LoC | Failure category | Note |\n",
          "| --- | --- | --- | --- | --- | --- | --- | --- |\n"]
    for s in summary:
        md.append(
            "| {label} | {status} | {tp}/{tot} | {fp} | {aloc} | {bloc} | {cat} | {note} |\n".format(
                label=s["label"],
                status=s["adapter_status"],
                tp=s["tests_passed"],
                tot=n,
                fp="yes" if s["first_pass_success"] == "true" else "no",
                aloc=s["adapter_loc"],
                bloc=s["backend_loc"],
                cat=s["failure_category"],
                note=(s["note"] or "").replace("|", "\\|"),
            )
        )
    md.append("\n")
    md.append("Fairness rule: every front-end was used as a parser / AST source only. "
              "Z3 and cvc5 built-in solvers were not invoked.\n")
    Path(args.out_summary_md).write_text("".join(md))

    print(f"Wrote {args.out_summary_csv}", file=sys.stderr)
    print(f"Wrote {args.out_summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
