#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate native (SMTParser) ok/timeout/fail by theory from parser_benchmark_table.csv; optional round-trip merge."""
from __future__ import print_function

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def theory_from_benchmark_path(p):
    parts = Path(p).parts
    for x in parts:
        if x.startswith("QF_") and len(x) <= 16:
            return x
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--benchmark-csv",
        type=Path,
        default=REPO / "results" / "parser_benchmark_table.csv",
    )
    ap.add_argument(
        "--roundtrip-csv",
        type=Path,
        default=None,
        help="Optional; if omitted and results/roundtrip/roundtrip_table.csv exists, merge it automatically",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "results" / "robustness" / "robustness_summary.md",
    )
    args = ap.parse_args()

    bench = args.benchmark_csv.resolve()
    if not bench.is_file():
        print("error: benchmark CSV not found:", bench, file=sys.stderr)
        return 1

    # file -> {ok, timeout, fail} for native
    by_theory = defaultdict(lambda: {"ok": 0, "timeout": 0, "fail": 0, "other": 0})
    native_total = {"ok": 0, "timeout": 0, "fail": 0, "other": 0}

    with open(bench, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if (row.get("parser") or "").strip() != "native":
                continue
            fp = row.get("file") or ""
            st = (row.get("status") or "").strip().lower()
            th = theory_from_benchmark_path(fp)
            if st == "ok":
                by_theory[th]["ok"] += 1
                native_total["ok"] += 1
            elif st == "timeout":
                by_theory[th]["timeout"] += 1
                native_total["timeout"] += 1
            elif st == "fail":
                by_theory[th]["fail"] += 1
                native_total["fail"] += 1
            else:
                by_theory[th]["other"] += 1
                native_total["other"] += 1

    rt_by_theory = None
    rt_total = None
    if args.roundtrip_csv is not None:
        rt_path = args.roundtrip_csv.resolve()
        if not rt_path.is_file():
            print("warning: round-trip CSV not found, skipping merge:", rt_path, file=sys.stderr)
            rt_path = None
    else:
        cand = REPO / "results" / "roundtrip" / "roundtrip_table.csv"
        rt_path = cand if cand.is_file() else None

    if rt_path and rt_path.is_file():
        rt_by_theory = defaultdict(lambda: {"ok": 0, "mismatch": 0, "fail": 0, "timeout": 0})
        rt_total = {"ok": 0, "mismatch": 0, "fail": 0, "timeout": 0}
        with open(rt_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                fp = row.get("file") or ""
                st = (row.get("status") or "").strip().lower()
                th = theory_from_benchmark_path(fp)
                if st == "ok":
                    rt_by_theory[th]["ok"] += 1
                    rt_total["ok"] += 1
                elif st == "mismatch":
                    rt_by_theory[th]["mismatch"] += 1
                    rt_total["mismatch"] += 1
                elif st == "timeout":
                    rt_by_theory[th]["timeout"] += 1
                    rt_total["timeout"] += 1
                else:
                    rt_by_theory[th]["fail"] += 1
                    rt_total["fail"] += 1

    lines = [
        "## Native parser robustness by theory (SMTParser)",
        "",
        "Per-theory counts of native front-end outcomes (`ok`, `timeout`, `fail`, `other`) on the evaluated instances.",
        "",
        "### Overall totals",
        "",
    ]
    nt = sum(native_total.values())
    lines.append("| Metric | Count | Share |")
    lines.append("| --- | ---: | ---: |")
    for k in ("ok", "timeout", "fail", "other"):
        c = native_total[k]
        pct = (100.0 * c / nt) if nt else 0.0
        lines.append("| {} | {} | {:.4f}% |".format(k, c, pct))
    lines.append("")
    lines.append("### By theory family")
    lines.append("")
    hdr = "| Theory | ok | timeout | fail | other | total | fail%+timeout% |"
    sep = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    lines.append(hdr)
    lines.append(sep)
    for th in sorted(by_theory.keys()):
        b = by_theory[th]
        tot = sum(b.values())
        bad = b["fail"] + b["timeout"]
        pct = (100.0 * bad / tot) if tot else 0.0
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {:.4f}% |".format(
                th, b["ok"], b["timeout"], b["fail"], b["other"], tot, pct
            )
        )
    lines.append("")

    if rt_by_theory and rt_total:
        lines.append("### Round-trip side summary (when round-trip run is available)")
        lines.append("")
        lines.append("| Theory | roundtrip_ok | mismatch | fail | timeout |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for th in sorted(rt_by_theory.keys()):
            x = rt_by_theory[th]
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    th, x["ok"], x["mismatch"], x["fail"], x["timeout"]
                )
            )
        lines.append("")
        lines.append(
            "Round-trip totals: ok={} mismatch={} fail={} timeout={}".format(
                rt_total["ok"],
                rt_total["mismatch"],
                rt_total["fail"],
                rt_total["timeout"],
            )
        )
        lines.append("")

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
