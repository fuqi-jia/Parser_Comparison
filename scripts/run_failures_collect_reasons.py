#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行重跑「失败用例」列表中的 (file, parser)，从 smt_parser_comparison 的 stdout/stderr 提取错误原因，
规范化后按 parser 合并去重（set）：相同原因只保留一条，并记录出现次数与示例文件。

与 collect_failures_from_table 完全独立：输入来自 results/failures_by_parser/*_failed.txt 或
直接指定 CSV/列表；输出统一写到 results/failure_reasons/，不修改 failures_by_parser。

输出:
  results/failure_reasons/
    <parser>_reasons.json     # 每个原因一行摘要：reason -> { count, example_files[] }
    <parser>_reasons_summary.txt  # 可读：原因 + 出现次数 + 示例文件
    run_log.csv               # 原始 (file, parser, status, reason_raw) 便于排查
    run_log.jsonl             # 同上，每行一条 JSON（可选）

用法:
  python3 scripts/run_failures_collect_reasons.py --failures-dir results/failures_by_parser
  python3 scripts/run_failures_collect_reasons.py --table results/parser_benchmark_table.csv --out-dir results/failure_reasons -j 32
"""
from __future__ import print_function

import os
import re
import sys
import json
import csv
import argparse
import subprocess
import resource
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FAILURES_DIR = REPO_ROOT / "results" / "failures_by_parser"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "failure_reasons"
BINARY_NAMES = ["smt_parser_comparison", "build/smt_parser_comparison"]
PARSE_TIMEOUT_SEC = 10
PROCESS_TIMEOUT_SEC = PARSE_TIMEOUT_SEC + 5
DEFAULT_MEMORY_MB = 4096
MAX_REASON_LEN = 800
MAX_EXAMPLE_FILES = 3


def find_binary():
    for name in BINARY_NAMES:
        path = REPO_ROOT / name if not os.path.isabs(name) else Path(name)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    import shutil
    if shutil.which("smt_parser_comparison"):
        return "smt_parser_comparison"
    return None


def normalize_reason(raw):
    """
    规范化错误原因字符串，便于去重：去掉绝对路径、行号、多余空白，截断过长。
    """
    if not raw or not isinstance(raw, str):
        return "(empty)"
    s = raw.strip()
    # 去掉常见绝对路径（保留相对或占位）
    s = re.sub(r"/[^\s]+\.smt2?", "<file>", s)
    s = re.sub(r"/[^\s]+/", "/<path>/", s)
    # 行号、列号
    s = re.sub(r":\s*line\s+\d+", ": line <N>", s, flags=re.I)
    s = re.sub(r"line\s+\d+", "line <N>", s, flags=re.I)
    s = re.sub(r"\.py\"?,?\s*line\s+\d+", ".py line <N>", s)
    s = re.sub(r"([\"'])[^\"']*?\.py[\"']?\s*,?\s*line\s+\d+", r"\1<path>.py line <N>", s)
    # 文件:行:列 形式
    s = re.sub(r":(\d+):(\d+)", ":<N>:<N>", s)
    # 过长的数字（如内存字节数）替换，避免同一语义不同数字被拆成多类
    s = re.sub(r"\b\d{5,}\b", "<N>", s)
    # 多余空白
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > MAX_REASON_LEN:
        s = s[:MAX_REASON_LEN] + "..."
    return s or "(empty)"


def extract_error_from_output(stdout, stderr):
    """
    从 binary 的 stdout/stderr 提取错误信息。兼容：
      "  错误: xxx"
      "  错误信息:" 后多行 "    xxx"
    """
    text = (stdout or "") + "\n" + (stderr or "")
    lines = text.splitlines()
    err_lines = []
    in_err_block = False
    for line in lines:
        stripped = line.strip()
        if "  错误: " in line:
            err_lines.append(line.split("  错误: ", 1)[-1].strip())
        if "  错误信息:" in line or (in_err_block and line.startswith("    ") and line.strip()):
            if "  错误信息:" in line:
                in_err_block = True
                continue
            if in_err_block:
                if line.startswith("    "):
                    err_lines.append(line[4:].strip())
                else:
                    in_err_block = False
    # 超时、崩溃等
    if "命令执行超时" in text:
        err_lines.append("命令执行超时")
    if "解析器崩溃" in text or "信号 " in text:
        err_lines.append("解析器崩溃或信号终止")
    if "解析过程发生异常" in text or "解析过程发生未知异常" in text:
        err_lines.append("解析过程异常或崩溃")
    # 去重并合并
    seen = set()
    unique = []
    for e in err_lines:
        e = e.strip()
        if e and e not in seen:
            seen.add(e)
            unique.append(e)
    return " | ".join(unique) if unique else (text.strip()[:500] if text.strip() else "(无输出)")


def run_one_capture(binary, file_path, parser_name, timeout_sec, memory_mb):
    """
    执行一次 test，返回 (status, reason_raw, reason_normalized)。
    status: ok | fail | timeout | error
    """
    if not os.path.isfile(file_path):
        return "no_file", "文件不存在", normalize_reason("文件不存在")
    cmd = [binary, "test", "--file", file_path, "--parser", parser_name, "--timeout", str(timeout_sec)]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    _java_opts = (
        "-XX:ErrorFile=/dev/null "
        "-Xmx768m -Xms64m "
        "-XX:CompressedClassSpaceSize=128m "
        "-XX:ReservedCodeCacheSize=32m "
        "-XX:CICompilerCount=2"
    )
    if memory_mb and memory_mb <= 4096:
        env["JAVA_TOOL_OPTIONS"] = _java_opts
    else:
        try:
            env["JAVA_TOOL_OPTIONS"] = "-XX:ErrorFile=/dev/null"
        except Exception:
            pass
    try:
        if memory_mb and memory_mb > 0 and os.name == "posix":
            def set_limits():
                try:
                    as_bytes = memory_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (as_bytes, as_bytes))
                except (ValueError, resource.error):
                    pass
            proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env, preexec_fn=set_limits,
            )
        else:
            proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env,
            )
        try:
            stdout, stderr = proc.communicate(timeout=PROCESS_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return "timeout", "命令执行超时", normalize_reason("命令执行超时")
        reason_raw = extract_error_from_output(stdout, stderr)
        reason_norm = normalize_reason(reason_raw)
        # 判定 status
        status = "fail"
        full = (stdout or "") + "\n" + (stderr or "")
        if "解析状态:" in full or "结果:" in full:
            if "成功" in full and "失败" not in full:
                status = "ok"
            elif "超时" in full or "命令执行超时" in full:
                status = "timeout"
                reason_raw = "命令执行超时"
                reason_norm = normalize_reason(reason_raw)
        if proc.returncode != 0 and status == "ok":
            status = "fail"
        return status, reason_raw, reason_norm
    except Exception as e:
        msg = str(e)[:400]
        return "error", msg, normalize_reason(msg)


def load_tasks_from_failures_dir(failures_dir):
    """
    从 results/failures_by_parser/*_failed.txt 读取 (file_path, parser)。
    每行一个绝对路径或相对路径；parser 由文件名 antlr4_failed.txt -> antlr4 得到。
    """
    tasks = []
    failures_dir = Path(failures_dir)
    if not failures_dir.is_dir():
        return tasks
    for p in failures_dir.glob("*_failed.txt"):
        parser = p.stem.replace("_failed", "")
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                path = line.strip()
                if not path or path.startswith("#"):
                    continue
                if not Path(path).is_absolute():
                    path = str(REPO_ROOT / path)
                tasks.append((path, parser))
    return tasks


def load_tasks_from_table(table_csv):
    """从 parser_benchmark_table 中 status=fail 的行加载 (file, parser)。"""
    tasks = []
    path = Path(table_csv)
    if not path.is_file():
        return tasks
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").strip().lower() != "fail":
                continue
            file_path = (row.get("file") or "").strip()
            parser = (row.get("parser") or "").strip()
            if not file_path or not parser or parser == "parser":
                continue
            if not Path(file_path).is_absolute():
                file_path = str(REPO_ROOT / file_path)
            tasks.append((file_path, parser))
    return tasks


def main():
    ap = argparse.ArgumentParser(
        description="并行重跑失败用例，收集并合并（去重）每个 parser 的错误原因，写入 results/failure_reasons/"
    )
    ap.add_argument(
        "--failures-dir",
        type=Path,
        default=None,
        help="失败用例目录，内含 <parser>_failed.txt（每行一个文件路径）。与 --table 二选一",
    )
    ap.add_argument(
        "--table",
        type=Path,
        default=None,
        help="parser_benchmark_table.csv，从中取 status=fail 的 (file,parser)。与 --failures-dir 二选一",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="输出目录（默认 results/failure_reasons）",
    )
    ap.add_argument(
        "--jobs", "-j",
        type=int,
        default=16,
        help="并行任务数",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=PARSE_TIMEOUT_SEC,
        help="单次解析超时（秒）",
    )
    ap.add_argument(
        "--memory-mb",
        type=int,
        default=DEFAULT_MEMORY_MB,
    )
    ap.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="最多跑多少个 (file,parser)，用于试跑",
    )
    args = ap.parse_args()

    if args.failures_dir is not None and args.table is not None:
        print("请只指定 --failures-dir 或 --table 之一", file=sys.stderr)
        sys.exit(1)
    if args.failures_dir is not None:
        tasks = load_tasks_from_failures_dir(args.failures_dir)
        if not tasks:
            print("未从 --failures-dir 读到任何 (file, parser):", args.failures_dir, file=sys.stderr)
            sys.exit(1)
    elif args.table is not None:
        tasks = load_tasks_from_table(args.table)
        if not tasks:
            print("未从 --table 读到任何 fail 行:", args.table, file=sys.stderr)
            sys.exit(1)
    else:
        # 默认用 failures_by_parser
        tasks = load_tasks_from_failures_dir(DEFAULT_FAILURES_DIR)
        if not tasks:
            print("默认 failures_dir 为空，请先运行 collect_failures_from_table.py --collect 或指定 --failures-dir / --table", file=sys.stderr)
            sys.exit(1)

    if args.max_tasks is not None and args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]
        print("仅运行前 {} 个任务（--max-tasks）".format(len(tasks)), flush=True)

    binary = find_binary()
    if not binary:
        print("错误: 未找到 smt_parser_comparison", file=sys.stderr)
        sys.exit(1)

    args.out_dir = Path(args.out_dir).resolve()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # 并行执行
    jobs = max(1, min(args.jobs, len(tasks)))
    print("任务数: {}  并行度: {}  输出: {}".format(len(tasks), jobs, args.out_dir), flush=True)

    log_rows = []
    # parser -> reason_norm -> { count, example_files[] }
    by_parser_reason = defaultdict(lambda: defaultdict(lambda: {"count": 0, "example_files": []}))

    def run_task(t):
        file_path, parser = t
        return (file_path, parser) + run_one_capture(
            binary, file_path, parser, args.timeout, args.memory_mb
        )

    completed = 0
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_task = {executor.submit(run_task, t): t for t in tasks}
        for future in as_completed(future_to_task):
            file_path, parser_name = future_to_task[future]
            try:
                file_path, parser_name, status, reason_raw, reason_norm = future.result()
            except Exception as e:
                status, reason_raw, reason_norm = "error", str(e)[:300], normalize_reason(str(e))
            log_rows.append({
                "file": file_path,
                "parser": parser_name,
                "status": status,
                "reason_raw": reason_raw,
                "reason_normalized": reason_norm,
            })
            rec = by_parser_reason[parser_name][reason_norm]
            rec["count"] += 1
            if len(rec["example_files"]) < MAX_EXAMPLE_FILES:
                rec["example_files"].append(file_path)
            completed += 1
            if completed % 500 == 0 or completed == len(tasks):
                print("[{}/{}] 已完成".format(completed, len(tasks)), flush=True)

    # 写 run_log.csv
    log_csv = args.out_dir / "run_log.csv"
    with open(log_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "parser", "status", "reason_raw", "reason_normalized"])
        w.writeheader()
        w.writerows(log_rows)
    print("已写 run_log: {}".format(log_csv))

    # 按 parser 写 _reasons.json 和 _reasons_summary.txt（合并去重后的原因 set）
    for parser_name in sorted(by_parser_reason.keys()):
        reasons = by_parser_reason[parser_name]
        # reasons: reason_norm -> { count, example_files }
        out_json = args.out_dir / "{}_reasons.json".format(parser_name)
        out_txt = args.out_dir / "{}_reasons_summary.txt".format(parser_name)
        # JSON: 列表形态，每项 { "reason": norm, "count": n, "example_files": [...] }
        list_for_json = [
            {"reason": r, "count": rec["count"], "example_files": rec["example_files"]}
            for r, rec in reasons.items()
        ]
        list_for_json.sort(key=lambda x: -x["count"])
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(list_for_json, f, ensure_ascii=False, indent=2)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("# {} 失败原因汇总（去重后共 {} 类）\n\n".format(parser_name, len(reasons)))
            for item in list_for_json:
                f.write("## 出现次数: {}\n".format(item["count"]))
                f.write("原因: {}\n".format(item["reason"]))
                f.write("示例文件:\n")
                for ex in item["example_files"]:
                    f.write("  - {}\n".format(ex))
                f.write("\n")
        print("  {}: {} 类原因 -> {}  {}".format(parser_name, len(reasons), out_json.name, out_txt.name))
    print("完成。结果在 {}".format(args.out_dir))


if __name__ == "__main__":
    main()
