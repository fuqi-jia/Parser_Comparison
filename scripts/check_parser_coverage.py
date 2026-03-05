#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查每个 parser 在主表里的覆盖是否完整：以 checkpoint 为「应有」基准，对比主表里实际有的 (file, parser)。
用于发现 rerun 后是否误删或缺失某些 parser 的结果（导致散点图 timeout 少、antlr4 等一个都没有）。
"""
from pathlib import Path
import csv
import sys

import re

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = REPO_ROOT / "results" / "parser_benchmark_table_sampled.csv"
DEFAULT_CHECKPOINT = REPO_ROOT / "results" / "parser_benchmark_checkpoint_sampled.csv"
DEFAULT_RECHECK = REPO_ROOT / "results" / "parser_benchmark_recheck_sampled.csv"
THEORY_PATTERN = re.compile(r"sampled/files/([^/]+)/")


def extract_theory(file_path):
    m = THEORY_PATTERN.search(str(file_path))
    return m.group(1) if m else "unknown"


def load_keys_and_status(path):
    """返回 (set of (file, parser), dict (file, parser) -> status)。路径保持 CSV 原样以与主表/checkpoint 一致。"""
    keys = set()
    status_map = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            fpath = (row.get("file") or "").strip()
            p = (row.get("parser") or "").strip()
            if not fpath or not p:
                continue
            key = (fpath, p)
            keys.add(key)
            status_map[key] = (row.get("status") or "").strip().lower()
    return keys, status_map


def main():
    import argparse
    ap = argparse.ArgumentParser(description="检查各 parser 在主表中的覆盖是否与 checkpoint 一致")
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE, help="主表 CSV")
    ap.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT, help="基准：应有 (file, parser) 的集合")
    ap.add_argument("--recheck", type=Path, default=None, help="若指定，同时统计 recheck 中各 parser 条数")
    ap.add_argument("--by-theory", action="store_true", help="对缺失条数>0 的 parser 按 theory 打印缺失分布")
    args = ap.parse_args()

    if not args.checkpoint.exists():
        print("错误: checkpoint 不存在", args.checkpoint, file=sys.stderr)
        return 1
    if not args.table.exists():
        print("错误: 主表不存在", args.table, file=sys.stderr)
        return 1

    exp_keys, _ = load_keys_and_status(args.checkpoint)
    act_keys, act_status = load_keys_and_status(args.table)

    # 按 parser 统计
    from collections import defaultdict
    exp_per_parser = defaultdict(set)
    for f, p in exp_keys:
        exp_per_parser[p].add((f, p))
    act_per_parser = defaultdict(set)
    for f, p in act_keys:
        act_per_parser[p].add((f, p))

    parsers = sorted(exp_per_parser.keys())
    recheck_per_parser = None
    if args.recheck and args.recheck.exists():
        recheck_keys, _ = load_keys_and_status(args.recheck)
        recheck_per_parser = defaultdict(int)
        for f, p in recheck_keys:
            recheck_per_parser[p] += 1

    print("基准: checkpoint = {} 条 (file, parser)".format(len(exp_keys)))
    print("主表: {} 条 (file, parser)".format(len(act_keys)))
    print("")
    print("{:<12} {:>8} {:>8} {:>8} {:>6} {:>6} {:>6} {:>6}  {}".format(
        "parser", "expected", "in_table", "missing", "ok", "timeout", "fail", "recheck", "备注"
    ))
    print("-" * 75)

    for p in parsers:
        exp_set = exp_per_parser[p]
        act_set = act_per_parser.get(p, set())
        missing = exp_set - act_set
        extra = act_set - exp_set
        n_ok = n_to = n_fail = n_other = 0
        for key in act_set:
            s = act_status.get(key, "")
            if s == "ok":
                n_ok += 1
            elif s == "timeout":
                n_to += 1
            elif s == "fail":
                n_fail += 1
            else:
                n_other += 1
        rec_str = str(recheck_per_parser.get(p, "")) if recheck_per_parser is not None else ""
        note = ""
        if missing:
            note = "缺 {} 条".format(len(missing))
        if extra:
            note = (note + " 多 {} 条".format(len(extra))) if note else "多 {} 条".format(len(extra))
        print("{:<12} {:>8} {:>8} {:>8} {:>6} {:>6} {:>6} {:>6}  {}".format(
            p, len(exp_set), len(act_set), len(missing), n_ok, n_to, n_fail, rec_str, note
        ))

    # 汇总缺失：列出缺失的 (file, parser) 数量超过 0 的 parser
    missing_any = [(p, exp_per_parser[p] - act_per_parser.get(p, set())) for p in parsers if exp_per_parser[p] - act_per_parser.get(p, set())]
    if missing_any:
        print("")
        print("存在缺失的 parser（expected 有、table 无）：")
        for p, mset in missing_any:
            print("  {} 缺 {} 条".format(p, len(mset)))
        if args.by_theory:
            print("")
            print("按 theory 的缺失分布（仅列缺失>0 的 parser）：")
            for p, mset in missing_any:
                by_th = defaultdict(int)
                for (f, _) in mset:
                    by_th[extract_theory(f)] += 1
                parts = ["{}:{}".format(th, c) for th, c in sorted(by_th.items(), key=lambda x: -x[1])]
                print("  {} -> {}".format(p, " | ".join(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
