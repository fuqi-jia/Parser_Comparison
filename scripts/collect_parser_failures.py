#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 logs_sampled 中按 parser 和理论收集失败用例，将完整 log 行写入各 parser 目录下，
并把对应的 benchmark 文件复制到 <parser>/<理论>/ 目录，便于按文件名查找。

每个理论对应一个 log 文件：results/logs_sampled/<理论>.log
每行格式：[index/total] parser_name | filename -> ok|fail|timeout  time  memory  nodes=...

输出目录：
  benchmark/failures/<parser>/<理论>.txt   - 失败 log 行
  benchmark/failures/<parser>/<理论>/     - 复制过来的 benchmark 文件（与 log 中文件名对应）

用法:
  python3 scripts/collect_parser_failures.py
  python3 scripts/collect_parser_failures.py --logs-dir results/logs_sampled --out-dir benchmark/failures
  python3 scripts/collect_parser_failures.py --exclude-recheck results/parser_benchmark_recheck_sampled.csv   # 排除 recheck 中已为 ok 的
  # 默认会从 results/parser_benchmark_table_sampled.csv（与 summary 同源）补充 fail/timeout，保证与 summary 一致
"""

from __future__ import print_function

import argparse
import csv
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS_DIR = REPO_ROOT / "results" / "logs_sampled"
DEFAULT_OUT_DIR = REPO_ROOT / "benchmark" / "failures"
DEFAULT_FILE_LIST = REPO_ROOT / "benchmark" / "sampled" / "file_list.txt"
DEFAULT_TABLE_CSV = REPO_ROOT / "results" / "parser_benchmark_table_sampled.csv"

# 匹配 log 行： [n/m] parser | filename -> status ...
FAIL_LINE_RE = re.compile(
    r"^\[\d+/\d+\]\s+([^\s|]+)\s+\|\s+([^\s]+)\s+->\s+fail\s+", re.IGNORECASE
)
# 从文件路径提取理论：.../sampled/files/QF_AX/... -> QF_AX
THEORY_PATTERN = re.compile(r"sampled/files/([^/]+)/")


def build_theory_file_index(file_list_path, repo_root):
    """
    从 file_list.txt 构建 theory -> { basename -> 绝对路径 }。
    file_list 每行: benchmark/sampled/files/QF_AX/swap/xxx.smt2
    """
    index = {}
    with open(file_list_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            path = line.strip()
            if not path or path.startswith("#"):
                continue
            full = (repo_root / path).resolve() if not Path(path).is_absolute() else Path(path)
            # 从路径中取理论: benchmark/sampled/files/QF_AX/...
            parts = path.replace("\\", "/").split("/")
            if "files" in parts:
                i = parts.index("files")
                if i + 1 < len(parts):
                    theory = parts[i + 1]
                    basename = full.name
                    if theory not in index:
                        index[theory] = {}
                    index[theory][basename] = full
    return index


def resolve_file_for_theory(theory_index, log_filename):
    """
    根据 log 里的文件名（可能被截断）在 theory 索引里解析出完整路径。
    返回 Path 或 None。
    """
    log_filename = log_filename.strip()
    if not theory_index:
        return None
    # 精确匹配
    if log_filename in theory_index:
        return theory_index[log_filename]
    # 截断名：log 里是 "xxx." 形式，找 basename 以该前缀开头的文件
    if log_filename.endswith("."):
        prefix = log_filename[:-1]
        for basename, path in theory_index.items():
            if basename.startswith(prefix):
                return path
    # 或 log 名是某 basename 的前缀
    for basename, path in theory_index.items():
        if basename.startswith(log_filename) or log_filename.startswith(basename):
            return path
    return None


def extract_theory(file_path):
    """从 file 路径提取理论：.../sampled/files/QF_AX/... -> QF_AX"""
    path_str = str(file_path).replace("\\", "/")
    m = THEORY_PATTERN.search(path_str)
    return m.group(1) if m else "unknown"


def load_recheck_ok(recheck_path):
    """
    加载 recheck CSV，返回在 recheck 中 status=ok 的 (file, parser) 集合，用于排除误判。
    file 统一为绝对路径字符串以便与 resolve 后的路径比较。
    """
    ok_set = set()
    path = Path(recheck_path)
    if not path.is_file():
        return ok_set
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("status") or "").strip().lower() != "ok":
                    continue
                file_path = (REPO_ROOT / row["file"]).resolve() if row.get("file") else None
                parser = (row.get("parser") or "").strip()
                if file_path and parser:
                    ok_set.add((str(file_path), parser))
    except Exception:
        pass
    return ok_set


def load_recheck_fail_timeout(recheck_path):
    """
    加载 recheck CSV，返回在 recheck 中 status=fail 或 timeout 的 (file_path, parser, status) 列表，
    用于补充到失败收集（log 里可能没有或只标了 fail，recheck 里仍失败/超时的也要收进来）。
    """
    return _load_csv_fail_timeout(recheck_path)


def _load_csv_fail_timeout(csv_path):
    """从与 checkpoint/table 同构的 CSV 加载 status=fail 或 timeout 的 (file_path, parser, status)。"""
    out = []
    path = Path(csv_path)
    if not path.is_file():
        return out
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                s = (row.get("status") or "").strip().lower()
                if s not in ("fail", "timeout"):
                    continue
                file_path = (REPO_ROOT / row["file"]).resolve() if row.get("file") else None
                parser = (row.get("parser") or "").strip()
                if file_path and parser and file_path.exists():
                    out.append((file_path, parser, s))
    except Exception:
        pass
    return out


def collect_failures_from_log(log_path, theory_index_for_theory, recheck_ok=None):
    """
    从单个 theory 的 log 文件中收集各 parser 的失败行及 log 中的文件名。
    recheck_ok: 若提供，则 (resolved_file_path, parser) 在此集合中的条目会被排除（已重跑为 ok）。
    返回: { parser_name: [ (full_line, filename_from_log), ... ] }
    """
    by_parser = {}
    recheck_ok = recheck_ok or set()
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if " -> fail " not in line:
                continue
            m = FAIL_LINE_RE.match(line)
            if not m:
                continue
            parser_name = m.group(1).strip()
            filename_in_log = m.group(2).strip()
            if recheck_ok and theory_index_for_theory:
                resolved = resolve_file_for_theory(theory_index_for_theory, filename_in_log)
                if resolved:
                    key = (str(Path(resolved).resolve()), parser_name)
                    if key in recheck_ok:
                        continue
            if parser_name not in by_parser:
                by_parser[parser_name] = []
            # 条目格式 (log_line, filename_for_copy, optional_src_path)，无 src_path 时复制阶段用 theory 索引解析
            by_parser[parser_name].append((line, filename_in_log, None))
    return by_parser


def main():
    ap = argparse.ArgumentParser(
        description="按 parser 和理论收集失败用例，将完整 log 行写入 benchmark/failures/<parser>/<理论>.txt，并可选复制对应 benchmark 文件"
    )
    ap.add_argument(
        "--logs-dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help="存放各理论 log 的目录（如 results/logs_sampled）",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="输出根目录，下按 parser 建子目录（默认 benchmark/failures）",
    )
    ap.add_argument(
        "--file-list",
        type=Path,
        default=DEFAULT_FILE_LIST,
        help="benchmark 文件列表（默认 benchmark/sampled/file_list.txt），用于解析 log 文件名到路径",
    )
    ap.add_argument(
        "--no-copy",
        action="store_true",
        help="不复制 benchmark 文件，只生成 .txt",
    )
    ap.add_argument(
        "--exclude-recheck",
        type=Path,
        default=None,
        metavar="CSV",
        help="重跑结果 CSV（与 recheck 输出同构）：其中 status=ok 的 (file,parser) 将从本次收集中排除，避免把已纠正的误判当失败",
    )
    ap.add_argument(
        "--from-table",
        type=Path,
        default=None,
        metavar="CSV",
        help="长表 CSV（与 summary 同源）：从中读取 status=fail/timeout 的 (file,parser) 并加入失败收集，保证与 summary 一致；默认 results/parser_benchmark_table_sampled.csv（存在时自动用）",
    )
    args = ap.parse_args()

    if not args.logs_dir.is_dir():
        print("错误: log 目录不存在:", args.logs_dir, file=__import__("sys").stderr)
        raise SystemExit(1)

    # 构建 theory -> basename -> 绝对路径 索引（用于复制文件；exclude-recheck 时也需用于解析 log 文件名）
    theory_index = {}
    if args.file_list.exists():
        theory_index = build_theory_file_index(args.file_list, REPO_ROOT)
        if not args.no_copy:
            print("已加载 file_list，共", sum(len(v) for v in theory_index.values()), "个 benchmark 路径")
    elif not args.no_copy:
        print("未找到 file_list，将不复制 benchmark 文件:", args.file_list, file=__import__("sys").stderr)

    recheck_path = None
    if args.exclude_recheck is not None:
        recheck_path = (REPO_ROOT / args.exclude_recheck).resolve()
    recheck_ok = set()
    recheck_fail_timeout = []
    if recheck_path is not None and recheck_path.is_file():
        recheck_ok = load_recheck_ok(recheck_path)
        recheck_fail_timeout = load_recheck_fail_timeout(recheck_path)
        if recheck_ok:
            print("已加载 recheck：排除", len(recheck_ok), "条 status=ok", end="")
        if recheck_fail_timeout:
            print("；补充", len(recheck_fail_timeout), "条 status=fail/timeout 到失败收集")
        elif recheck_ok:
            print()
        if not recheck_ok and not recheck_fail_timeout:
            print("未从 recheck 中读到 ok 或 fail/timeout 记录:", recheck_path, file=__import__("sys").stderr)

    # 从 summary 所用的长表补充 fail/timeout（与 summary 统计一致，避免漏掉 log 里没有的）
    table_fail_timeout = []
    table_path = (REPO_ROOT / args.from_table).resolve() if args.from_table is not None else DEFAULT_TABLE_CSV.resolve()
    if table_path.is_file():
        table_fail_timeout = _load_csv_fail_timeout(table_path)
        if table_fail_timeout:
            print("已从长表补充", len(table_fail_timeout), "条 fail/timeout（与 summary 同源）:", table_path.name)

    # 所有理论 = 所有 .log 文件名（去掉 .log）
    log_files = sorted(args.logs_dir.glob("*.log"))
    if not log_files:
        print("未找到任何 .log 文件:", args.logs_dir, file=__import__("sys").stderr)
        raise SystemExit(1)

    # 全局按 parser -> theory -> [ (line, filename, optional_src_path) ]
    all_failures = {}
    seen_path_parser = set()  # (path_str, parser) 已收集，避免 log 与 recheck 重复

    for log_path in log_files:
        theory = log_path.stem  # 如 QF_AX
        theory_file_index = theory_index.get(theory, {}) if recheck_ok else None
        by_parser = collect_failures_from_log(log_path, theory_file_index, recheck_ok)
        for parser_name, entries in by_parser.items():
            if parser_name not in all_failures:
                all_failures[parser_name] = {}
            all_failures[parser_name][theory] = entries
            for e in entries:
                src = e[2] if len(e) >= 3 and e[2] is not None else resolve_file_for_theory(theory_index.get(theory, {}), e[1])
                if src is not None:
                    seen_path_parser.add((str(Path(src).resolve()), parser_name))

    def add_fail_timeout_entries(items, line_prefix="[recheck]", exclude_ok=None):
        exclude_ok = exclude_ok or set()
        for file_path, parser_name, status in items:
            key = (str(file_path.resolve()), parser_name)
            if key in exclude_ok:
                continue  # recheck 已纠正为 ok，不再当失败收集
            if key in seen_path_parser:
                continue
            seen_path_parser.add(key)
            theory = extract_theory(file_path)
            basename = file_path.name
            line = "{} {} | {} -> {}".format(line_prefix, parser_name, basename, status)
            entry = (line, basename, file_path)
            if parser_name not in all_failures:
                all_failures[parser_name] = {}
            if theory not in all_failures[parser_name]:
                all_failures[parser_name][theory] = []
            all_failures[parser_name][theory].append(entry)

    # 把 recheck 里仍为 fail/timeout 的也加入失败收集（且未在 log 中已收集）
    add_fail_timeout_entries(recheck_fail_timeout, "[recheck]")
    # 把长表里的 fail/timeout 也加入；若 recheck 里已为 ok 则跳过（以 recheck 为准，不再收集）
    add_fail_timeout_entries(table_fail_timeout, "[table]", exclude_ok=recheck_ok)

    # 写入 benchmark/failures/<parser>/<理论>.txt，并复制对应文件到 <parser>/<理论>/
    args.out_dir.mkdir(parents=True, exist_ok=True)
    total_txt = 0
    total_copied = 0
    missing = []
    for parser_name in sorted(all_failures.keys()):
        parser_dir = args.out_dir / parser_name
        parser_dir.mkdir(parents=True, exist_ok=True)
        for theory in sorted(all_failures[parser_name].keys()):
            entries = all_failures[parser_name][theory]
            lines = [e[0] for e in entries]
            out_path = parser_dir / f"{theory}.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                if lines:
                    f.write("\n")
            total_txt += 1
            # 复制对应 benchmark 文件：条目为 (line, filename, optional_src_path)
            theory_dir = parser_dir / theory
            if not args.no_copy:
                theory_file_index = theory_index.get(theory, {})
                theory_dir.mkdir(parents=True, exist_ok=True)
                for e in entries:
                    line, filename_in_log = e[0], e[1]
                    src = (e[2] if len(e) >= 3 and e[2] is not None else None) or resolve_file_for_theory(theory_file_index, filename_in_log)
                    if src is None:
                        missing.append((theory, filename_in_log))
                        continue
                    src = Path(src)
                    if not src.exists():
                        missing.append((theory, filename_in_log))
                        continue
                    dst = theory_dir / src.name
                    if not dst.exists() or dst.stat().st_mtime != src.stat().st_mtime:
                        shutil.copy2(src, dst)
                        total_copied += 1
            print(f"  {parser_name}/{theory}.txt: {len(lines)} 条失败", end="")
            if not args.no_copy and theory_index and theory in theory_index:
                print(f" -> 已同步到 {parser_name}/{theory}/", end="")
            print()
    print(f"\n已写入 {total_txt} 个 .txt 到 {args.out_dir}")
    if total_copied:
        print(f"已复制 {total_copied} 个 benchmark 文件到各 <parser>/<理论>/ 目录")
    if missing:
        print("未解析到路径的 log 文件名（共", len(missing), "条）:", missing[:5], "..." if len(missing) > 5 else "")


if __name__ == "__main__":
    main()
