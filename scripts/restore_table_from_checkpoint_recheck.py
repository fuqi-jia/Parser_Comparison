#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 checkpoint（全量基准）与 recheck（重跑结果）恢复主表。
主表若被误覆盖成少量行（例如只有 recheck 的几条），散点图会「无共同实例」或图不对；
用本脚本把 checkpoint 作为基准、用 recheck 覆盖对应 (file, parser)，写回主表。
"""
from pathlib import Path
import csv
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHECKPOINT = REPO_ROOT / "results" / "parser_benchmark_checkpoint_sampled.csv"
DEFAULT_RECHECK = REPO_ROOT / "results" / "parser_benchmark_recheck_sampled.csv"
DEFAULT_TABLE = REPO_ROOT / "results" / "parser_benchmark_table_sampled.csv"
FIELDNAMES = ["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="从 checkpoint + recheck 恢复主表")
    ap.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    ap.add_argument("--recheck", type=Path, default=DEFAULT_RECHECK)
    ap.add_argument("-o", "--table", type=Path, default=DEFAULT_TABLE, help="写回的主表路径")
    ap.add_argument("--dry-run", action="store_true", help="只打印将覆盖条数，不写文件")
    args = ap.parse_args()

    if not args.checkpoint.exists():
        print("错误: checkpoint 不存在", args.checkpoint, file=sys.stderr)
        return 1
    if not args.recheck.exists():
        print("错误: recheck 不存在", args.recheck, file=sys.stderr)
        return 1

    def norm_key(fpath, p):
        if not fpath or not p:
            return None
        try:
            return (str(Path(fpath).resolve()), p.strip())
        except Exception:
            return (fpath.strip(), p.strip())

    # 以 checkpoint 为基准行
    with open(args.checkpoint, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        base_fieldnames = reader.fieldnames or FIELDNAMES
        table_rows = list(reader)
    key_to_idx = {}       # (file_orig, parser) -> idx
    norm_to_rowkey = None  # 按需构建: (resolved_file, parser) -> (file_orig, parser)

    for idx, row in enumerate(table_rows):
        f = (row.get("file") or "").strip()
        p = (row.get("parser") or "").strip()
        if f and p:
            key_to_idx[(f, p)] = idx

    # recheck 覆盖：先按原始 path 匹配；若有未匹配的再构建 resolve 索引重试
    recheck_count = 0
    recheck_rows = []
    with open(args.recheck, "r", encoding="utf-8", newline="") as f:
        recheck_rows = list(csv.DictReader(f))
    unmatched = []
    for row in recheck_rows:
        fpath = (row.get("file") or "").strip()
        p = (row.get("parser") or "").strip()
        if not fpath or not p:
            continue
        row_key = (fpath, p)
        if row_key in key_to_idx:
            i = key_to_idx[row_key]
            table_rows[i]["status"] = (row.get("status") or "").strip()
            table_rows[i]["time_ms"] = (row.get("time_ms") or "").strip()
            table_rows[i]["memory_kb"] = (row.get("memory_kb") or "").strip()
            table_rows[i]["ast_nodes"] = (row.get("ast_nodes") or "").strip()
            recheck_count += 1
        else:
            unmatched.append((fpath, p, row))
    # 若有未匹配且路径可能不一致，用 resolve 索引再匹配一次
    if unmatched and key_to_idx:
        norm_to_rowkey = {}
        for (f, p) in key_to_idx:
            k = norm_key(f, p)
            if k:
                norm_to_rowkey[k] = (f, p)
        for fpath, p, row in unmatched:
            row_key = norm_to_rowkey.get(norm_key(fpath, p))
            if row_key is not None and row_key in key_to_idx:
                i = key_to_idx[row_key]
                table_rows[i]["status"] = (row.get("status") or "").strip()
                table_rows[i]["time_ms"] = (row.get("time_ms") or "").strip()
                table_rows[i]["memory_kb"] = (row.get("memory_kb") or "").strip()
                table_rows[i]["ast_nodes"] = (row.get("ast_nodes") or "").strip()
                recheck_count += 1

    print("基准行数: {}（来自 checkpoint）".format(len(table_rows)))
    print("recheck 覆盖条数: {}".format(recheck_count))
    if args.dry_run:
        print("(dry-run，未写入)")
        return 0
    args.table.parent.mkdir(parents=True, exist_ok=True)
    with open(args.table, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=base_fieldnames)
        w.writeheader()
        w.writerows(table_rows)
    print("已写入主表: {}".format(args.table))
    return 0


if __name__ == "__main__":
    sys.exit(main())
