#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 sampled benchmark 长表结果生成汇总表：按理论分组，每个理论一张表。
每表含：平均时间、平均内存峰值、节点个数、超时百分比、非超时失败百分比（支持率）。

理论从文件路径提取：.../sampled/files/<理论>/... 例如 QF_AX, QF_LRA。

输入: results/parser_benchmark_table_sampled.csv（或 --input 指定）
输出: results/summary/parser_summary_sampled_<理论>.csv 与 .md（默认 --output-dir results/summary）

用法:
  python3 scripts/gen_summary_table.py
  python3 scripts/gen_summary_table.py --input results/parser_benchmark_table_sampled.csv --output-dir results

弥补误判（用重跑结果更新长表后再生成 summary）:
  python3 scripts/gen_summary_table.py --input results/parser_benchmark_table_sampled.csv \\
      --update-from-recheck results/parser_benchmark_recheck_sampled.csv --output-dir results/summary
"""

from __future__ import print_function

import argparse
import csv
import re
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "results" / "parser_benchmark_table_sampled.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "summary"

# 从 file 路径提取理论：.../sampled/files/QF_AX/... -> QF_AX
THEORY_PATTERN = re.compile(r"sampled/files/([^/]+)/")


def extract_theory(file_path):
    m = THEORY_PATTERN.search(file_path)
    return m.group(1) if m else "unknown"


def build_summary_rows(by_parser):
    """给定 by_parser[parser] = { ok: [], timeout: [], fail: [] }，返回汇总行列表。"""
    rows = []
    for parser in sorted(by_parser.keys()):
        data = by_parser[parser]
        ok_list = data["ok"]
        timeout_list = data["timeout"]
        fail_list = data["fail"]
        total = len(ok_list) + len(timeout_list) + len(fail_list)
        if total == 0:
            continue

        median_time_ms = (
            statistics.median(r["time_ms"] for r in ok_list) if ok_list else None
        )
        avg_memory_kb = (
            sum(r["memory_kb"] for r in ok_list) / len(ok_list) if ok_list else None
        )
        avg_ast_nodes = (
            sum(r["ast_nodes"] for r in ok_list) / len(ok_list) if ok_list else None
        )
        timeout_pct = len(timeout_list) / total * 100.0
        fail_pct = len(fail_list) / total * 100.0
        support_pct = len(ok_list) / total * 100.0

        rows.append({
            "parser": parser,
            "total": total,
            "ok": len(ok_list),
            "timeout": len(timeout_list),
            "fail": len(fail_list),
            "median_time_ms": round(median_time_ms, 2) if median_time_ms is not None else "",
            "avg_memory_kb": round(avg_memory_kb, 2) if avg_memory_kb is not None else "",
            "avg_ast_nodes": round(avg_ast_nodes, 2) if avg_ast_nodes is not None else "",
            "timeout_pct": round(timeout_pct, 2),
            "fail_pct": round(fail_pct, 2),
            "support_pct": round(support_pct, 2),
        })
    return rows


def write_table_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "parser", "total", "ok", "timeout", "fail",
        "median_time_ms", "avg_memory_kb", "avg_ast_nodes",
        "timeout_pct", "fail_pct", "support_pct",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print("已写入:", path)


def write_table_md(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("| Parser | 中位时间(ms) | 平均内存(kB) | 平均节点数 | 超时(%) | 非超时失败(%) | 成功率(%) |\n")
        f.write("|--------|-------------|--------------|------------|---------|----------------|----------|\n")
        for r in rows:
            avg_t = r["median_time_ms"] if r["median_time_ms"] != "" else "-"
            avg_m = r["avg_memory_kb"] if r["avg_memory_kb"] != "" else "-"
            avg_n = r["avg_ast_nodes"] if r["avg_ast_nodes"] != "" else "-"
            f.write(
                f"| {r['parser']} | {avg_t} | {avg_m} | {avg_n} | "
                f"{r['timeout_pct']} | {r['fail_pct']} | {r['support_pct']} |\n"
            )
    print("已写入:", path)


def main():
    ap = argparse.ArgumentParser(
        description="从 sampled 长表按理论生成汇总表：每理论一表（平均时间、内存、节点数、超时%、非超时失败%）"
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="长表 CSV 路径（file, parser, status, time_ms, memory_kb, ast_nodes）",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="输出目录，每理论生成 parser_summary_sampled_<理论>.csv 与 .md",
    )
    ap.add_argument(
        "--no-md",
        action="store_true",
        help="不生成 Markdown 文件，仅生成 CSV",
    )
    ap.add_argument(
        "--update-from-recheck",
        type=Path,
        default=None,
        help="重跑结果 CSV（与 checkpoint 同构）：用其中 (file, parser) 覆盖 input 长表对应行后再生成 summary，用于纠正误判",
    )
    args = ap.parse_args()

    if not args.input.exists():
        print("错误: 输入文件不存在:", args.input, file=__import__("sys").stderr)
        raise SystemExit(1)

    # 读取长表
    input_rows = []
    with open(args.input, newline="", encoding="utf-8") as f:
        input_rows = list(csv.DictReader(f))

    # 若指定了重跑结果，用其覆盖长表中对应 (file, parser)
    if args.update_from_recheck is not None and args.update_from_recheck.exists():
        recheck_dict = {}
        with open(args.update_from_recheck, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row.get("file", ""), row.get("parser", ""))
                if key[0] and key[1]:
                    recheck_dict[key] = row
        replaced = 0
        for i, row in enumerate(input_rows):
            key = (row.get("file", ""), row.get("parser", ""))
            if key in recheck_dict:
                input_rows[i] = recheck_dict[key]
                replaced += 1
        print("已用重跑结果覆盖 {} 条记录（来自 {}）".format(replaced, args.update_from_recheck))

    # 按 (理论, parser) 分组：by_theory[theory][parser] = { ok, timeout, fail }
    by_theory = {}
    for row in input_rows:
        theory = extract_theory(row["file"])
        parser = row["parser"]
        if theory not in by_theory:
            by_theory[theory] = {}
        if parser not in by_theory[theory]:
            by_theory[theory][parser] = {"ok": [], "timeout": [], "fail": []}
        status = (row.get("status") or "").strip().lower()
        try:
            time_ms = float(row.get("time_ms") or 0)
            memory_kb = float(row.get("memory_kb") or 0)
            ast_nodes = int(row["ast_nodes"]) if (row.get("ast_nodes") or "").strip() else 0
        except (ValueError, KeyError):
            time_ms, memory_kb, ast_nodes = 0.0, 0.0, 0
        rec = {"time_ms": time_ms, "memory_kb": memory_kb, "ast_nodes": ast_nodes}
        if status == "ok":
            by_theory[theory][parser]["ok"].append(rec)
        elif status == "timeout":
            by_theory[theory][parser]["timeout"].append(rec)
        else:
            by_theory[theory][parser]["fail"].append(rec)

    # 每个理论生成一张表
    for theory in sorted(by_theory.keys()):
        rows = build_summary_rows(by_theory[theory])
        if not rows:
            continue
        base = args.output_dir / f"parser_summary_sampled_{theory}"
        write_table_csv(rows, base.with_suffix(".csv"))
        if not args.no_md:
            write_table_md(rows, base.with_suffix(".md"))


if __name__ == "__main__":
    main()
