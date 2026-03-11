#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 parser_benchmark_table.csv 中按 parser 收集 status=fail 的用例，便于排查原因并统计。

输入: results/parser_benchmark_table.csv（列: file, parser, status, time_ms, memory_kb, ast_nodes）
输出:
  - results/failures_by_parser/summary.csv          各 parser 的 fail/ok 数量与失败率
  - results/failures_by_parser/<parser>_failed.csv 该 parser 所有 fail 行（完整列）
  - results/failures_by_parser/<parser>_failed.txt  该 parser 所有 fail 的文件路径（一行一个，便于脚本用）

用法:
  python3 scripts/collect_failures_from_table.py
  python3 scripts/collect_failures_from_table.py --table results/parser_benchmark_table.csv --out-dir results/failures_by_parser
"""

from __future__ import print_function

import argparse
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = REPO_ROOT / "results" / "parser_benchmark_table.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "failures_by_parser"


def main():
    ap = argparse.ArgumentParser(
        description="从 parser_benchmark_table 中按 parser 收集 fail 用例并统计"
    )
    ap.add_argument(
        "--table",
        type=Path,
        default=DEFAULT_TABLE,
        help="长表 CSV 路径（默认 results/parser_benchmark_table.csv）",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="输出目录（默认 results/failures_by_parser）",
    )
    ap.add_argument(
        "--no-csv",
        action="store_true",
        help="不输出每个 parser 的 _failed.csv，只输出 _failed.txt 和 summary",
    )
    args = ap.parse_args()

    table_path = args.table.resolve()
    if not table_path.is_file():
        print("错误: 未找到表文件:", table_path, file=__import__("sys").stderr)
        raise SystemExit(1)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # parser -> total_count, fail_count, list of fail rows (dict)
    stats = {}
    fail_rows = {}  # parser -> [row_dict, ...]

    fieldnames = ["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"]

    with open(table_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            fieldnames = reader.fieldnames
        for row in reader:
            parser = (row.get("parser") or "").strip()
            status = (row.get("status") or "").strip().lower()
            if not parser:
                continue
            if parser not in stats:
                stats[parser] = {"total": 0, "fail": 0, "ok": 0}
            stats[parser]["total"] += 1
            if status == "fail":
                stats[parser]["fail"] += 1
                if parser not in fail_rows:
                    fail_rows[parser] = []
                fail_rows[parser].append(row)
            elif status == "ok":
                stats[parser]["ok"] += 1

    # 写入 summary.csv
    summary_path = args.out_dir / "summary.csv"
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["parser", "total", "ok", "fail", "fail_rate"])
        for parser in sorted(stats.keys()):
            s = stats[parser]
            total = s["total"]
            fail = s["fail"]
            ok = s["ok"]
            rate = f"{100.0 * fail / total:.2f}%" if total else "0%"
            w.writerow([parser, total, ok, fail, rate])
    print("已写入:", summary_path)

    # 每个 parser 写入 _failed.txt 和 _failed.csv
    for parser in sorted(fail_rows.keys()):
        rows = fail_rows[parser]
        base = args.out_dir / f"{parser}_failed"
        txt_path = base.with_suffix(".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write((row.get("file") or "") + "\n")
        print(f"  {parser}: {len(rows)} 条 fail -> {txt_path.name}")

        if not args.no_csv:
            csv_path = base.with_suffix(".csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(rows)

    # 打印统计表
    print("\n--- 统计 ---")
    print(f"{'parser':<12} {'total':>10} {'ok':>10} {'fail':>10} {'fail_rate':>10}")
    print("-" * 52)
    for parser in sorted(stats.keys()):
        s = stats[parser]
        total = s["total"]
        fail = s["fail"]
        ok = s["ok"]
        rate = f"{100.0 * fail / total:.2f}%" if total else "0%"
        print(f"{parser:<12} {total:>10} {ok:>10} {fail:>10} {rate:>10}")
    print("完成。")


if __name__ == "__main__":
    main()
