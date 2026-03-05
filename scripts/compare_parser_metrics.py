#!/usr/bin/env python3
"""
Compare SMTParser (native) vs competitors on instance-level data.
Metrics: time_ms, memory_mb, ast_nodes.
Competitors: Z3, cvc5, smt_switch, pysmt, antlr4, jsmtlib.
No aggregation by theory.
"""

import argparse
import csv
import math
import sys
from pathlib import Path

# SMTParser is "native" in the benchmark CSV
SMTPARSER_NAME = "native"

# CSV parser name -> display name
COMPETITORS = [
    ("z3", "Z3"),
    ("cvc5", "cvc5"),
    ("smt-switch", "smt_switch"),
    ("pysmt", "pysmt"),
    ("antlr4", "antlr4"),
    ("jsmtlib", "jsmtlib"),
]

METRICS = [
    ("time_ms", "time_ms", False),   # (csv_col, output_name, is_memory_mb)
    ("memory_mb", "memory_mb", False),
    ("ast_nodes", "ast_nodes", False),
]


def load_long_table(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def pivot_by_file(rows: list[dict]) -> dict[str, dict]:
    """Per file: { parser: { status, time_ms, memory_kb, ast_nodes } }."""
    by_file = {}
    for r in rows:
        f = r["file"].strip()
        parser = r["parser"].strip()
        status = r["status"].strip()
        try:
            time_ms = float(r["time_ms"])
            memory_kb = float(r["memory_kb"])
            ast_nodes = int(r["ast_nodes"])
        except (ValueError, KeyError):
            continue
        memory_mb = memory_kb / 1024.0
        if f not in by_file:
            by_file[f] = {}
        by_file[f][parser] = {
            "status": status,
            "time_ms": time_ms,
            "memory_kb": memory_kb,
            "memory_mb": memory_mb,
            "ast_nodes": ast_nodes,
        }
    return by_file


def compute_for_metric(
    by_file: dict,
    competitor_key: str,
    metric_key: str,
) -> dict:
    """
    metric_key one of: time_ms, memory_mb, ast_nodes.
    Returns dict with N_common, pct_better, median_ratio, mean_log10_ratio,
    timeout_only_smtparser, timeout_only_competitor, timeout_both.
    """
    n_common = 0
    better = 0
    ratios = []
    log10_ratios = []
    timeout_only_smtparser = 0
    timeout_only_competitor = 0
    timeout_both = 0

    for recs in by_file.values():
        native = recs.get(SMTPARSER_NAME)
        comp = recs.get(competitor_key)
        if not native or not comp:
            continue
        ns = native["status"]
        cs = comp["status"]

        # Timeout counts (instance-level)
        if ns == "timeout" and cs == "timeout":
            timeout_both += 1
        elif ns == "timeout" and cs == "ok":
            timeout_only_smtparser += 1
        elif ns == "ok" and cs == "timeout":
            timeout_only_competitor += 1

        # A) Both succeed
        if ns != "ok" or cs != "ok":
            continue
        n_common += 1
        v_n = native[metric_key]
        v_c = comp[metric_key]
        # Lower is better for all three metrics
        if v_n < v_c:
            better += 1
        # Ratios: competitor / SMTParser (only when both > 0 for ratio)
        if v_n > 0 and v_c >= 0:
            ratio = v_c / v_n
            ratios.append(ratio)
            if ratio > 0:
                log10_ratios.append(math.log10(ratio))

    pct_better = (100.0 * better / n_common) if n_common else float("nan")
    median_ratio = float("nan")
    if ratios:
        ratios_sorted = sorted(ratios)
        mid = len(ratios_sorted) // 2
        median_ratio = (
            ratios_sorted[mid]
            if len(ratios_sorted) % 2
            else (ratios_sorted[mid - 1] + ratios_sorted[mid]) / 2
        )
    mean_log10_ratio = (sum(log10_ratios) / len(log10_ratios)) if log10_ratios else float("nan")

    return {
        "N_common": n_common,
        "pct_better": pct_better,
        "median_ratio": median_ratio,
        "mean_log10_ratio": mean_log10_ratio,
        "timeout_only_smtparser": timeout_only_smtparser,
        "timeout_only_competitor": timeout_only_competitor,
        "timeout_both": timeout_both,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare SMTParser vs competitors (instance-level).")
    parser.add_argument(
        "csv",
        nargs="?",
        default="results/parser_benchmark_table_sampled.csv",
        help="Path to long-format benchmark CSV",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write summary CSV to this path (default: stdout)",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Omit header row in CSV output",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = Path(__file__).resolve().parent.parent / csv_path
    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    rows = load_long_table(str(csv_path))
    by_file = pivot_by_file(rows)

    # Build output rows: one per (metric, competitor)
    out_rows = []
    for metric_key, metric_label, _ in METRICS:
        for comp_key, comp_label in COMPETITORS:
            res = compute_for_metric(by_file, comp_key, metric_key)
            out_rows.append({
                "metric": metric_label,
                "competitor": comp_label,
                "N_common": res["N_common"],
                "pct_better": res["pct_better"],
                "median_ratio": res["median_ratio"],
                "mean_log10_ratio": res["mean_log10_ratio"],
                "timeout_only_smtparser": res["timeout_only_smtparser"],
                "timeout_only_competitor": res["timeout_only_competitor"],
                "timeout_both": res["timeout_both"],
            })

    fieldnames = [
        "metric", "competitor",
        "N_common", "pct_better", "median_ratio", "mean_log10_ratio",
        "timeout_only_smtparser", "timeout_only_competitor", "timeout_both",
    ]
    dest = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        w = csv.DictWriter(dest, fieldnames=fieldnames)
        if not args.no_header:
            w.writeheader()
        for r in out_rows:
            # Format floats for readability
            row = {k: r[k] for k in fieldnames}
            for k in ("pct_better", "median_ratio", "mean_log10_ratio"):
                v = row[k]
                if isinstance(v, float) and math.isfinite(v):
                    row[k] = round(v, 4)
            w.writerow(row)
    finally:
        if args.output:
            dest.close()

    # Also print a human-readable summary to stderr
    print("\n--- Summary (instance-level, no theory aggregation) ---", file=sys.stderr)
    for metric_key, metric_label, _ in METRICS:
        print(f"\nMetric: {metric_label}", file=sys.stderr)
        for comp_key, comp_label in COMPETITORS:
            res = compute_for_metric(by_file, comp_key, metric_key)
            print(
                f"  {comp_label}: N_common={res['N_common']}, "
                f"pct_better={res['pct_better']:.2f}%, "
                f"median_ratio={res['median_ratio']:.4f}, "
                f"mean_log10_ratio={res['mean_log10_ratio']:.4f}; "
                f"timeout: only_smtparser={res['timeout_only_smtparser']}, "
                f"only_competitor={res['timeout_only_competitor']}, "
                f"both={res['timeout_both']}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
