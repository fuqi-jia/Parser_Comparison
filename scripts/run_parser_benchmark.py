#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser benchmark 脚本：在 benchmark/non-incremental/ 下对所有 .smt2 跑所有 parser，
限制解析超时 10 秒、可选内存上限；支持断点续跑与增量写表。

用法:
  cd /mnt/d/D_Study/ISCAS/projects/SMT/Parser_Comparison
  python3 scripts/run_parser_benchmark.py                    # 10s 超时，4GB 内存上限
  python3 scripts/run_parser_benchmark.py --memory-mb 2048  # 2GB 内存上限
  python3 scripts/run_parser_benchmark.py --resume          # WSL 崩溃后再次运行，从 checkpoint 继续

断点续跑：再次执行同一命令即可，会跳过 results/parser_benchmark_checkpoint.csv 中已有的 (file, parser)。
若要重跑全部，请删除 results/parser_benchmark_checkpoint.csv 后再运行。
输出表：results/parser_benchmark_table.csv（长表）、results/parser_benchmark_table_wide.csv（宽表，每例每 parser 三列 time_ms, memory_kb, ast_nodes）。
若希望按理论分 log（避免单个 log 过大），可加 --log-dir results/logs，会生成 results/logs/QF_AX.log、results/logs/QF_BV.log 等。
"""

from __future__ import print_function

import os
import re
import sys
import csv
import argparse
import subprocess
import resource
from pathlib import Path
from datetime import datetime

# 默认配置
REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmark" / "non-incremental"
BINARY_NAMES = ["smt_parser_comparison", "build/smt_parser_comparison"]
PARSE_TIMEOUT_SEC = 10
PROCESS_TIMEOUT_SEC = PARSE_TIMEOUT_SEC + 5  # 子进程硬超时
DEFAULT_MEMORY_MB = 4096
CHECKPOINT_CSV = REPO_ROOT / "results" / "parser_benchmark_checkpoint.csv"
TABLE_CSV = REPO_ROOT / "results" / "parser_benchmark_table.csv"
TABLE_WIDE_CSV = REPO_ROOT / "results" / "parser_benchmark_table_wide.csv"


def find_binary():
    for name in BINARY_NAMES:
        path = REPO_ROOT / name if not os.path.isabs(name) else Path(name)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    # PATH
    import shutil
    if shutil.which("smt_parser_comparison"):
        return "smt_parser_comparison"
    return None


def get_parser_list(binary):
    try:
        out = subprocess.run(
            [binary, "list"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode != 0:
            return None
        # 格式: "- native (C++)" 等
        names = []
        for line in out.stdout.splitlines():
            m = re.match(r"^\s*-\s+(\S+)", line.strip())
            if m:
                names.append(m.group(1))
        return names if names else None
    except Exception:
        return None


def collect_smt2_files(benchmark_dir):
    if not benchmark_dir.is_dir():
        return []
    files = []
    for p in benchmark_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".smt2", ".smt", ".smtlib"):
            files.append(str(p.resolve()))
    return sorted(files)


def load_checkpoint(path):
    done = set()  # (file, parser)
    rows = []
    if not path.is_file():
        return done, rows
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                file_, parser = row.get("file"), row.get("parser")
                if file_ and parser:
                    done.add((file_, parser))
                    rows.append(row)
    except Exception:
        pass
    return done, rows


def append_checkpoint(path, file_, parser, status, time_ms, memory_kb, ast_nodes):
    write_header = not path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"])
        w.writerow([file_, parser, status, time_ms, memory_kb, ast_nodes])
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass


def parse_test_output(stdout, stderr):
    time_ms = ""
    memory_kb = ""
    ast_nodes = ""
    status = "fail"
    for line in (stdout or "").splitlines():
        line = line.strip()
        if "解析状态:" in line or "结果:" in line:
            status = "ok" if "成功" in line else "fail"
        m = re.search(r"解析时间:\s*([\d.]+)\s*ms", line)
        if m:
            time_ms = m.group(1)
        m = re.search(r"内存使用:\s*(\d+)\s*KB", line)
        if m:
            memory_kb = m.group(1)
        m = re.search(r"AST节点数(?:量)?:\s*(\d+)", line)
        if m:
            ast_nodes = m.group(1)
    return status, time_ms, memory_kb, ast_nodes


def run_one(binary, file_path, parser_name, timeout_sec, memory_mb):
    cmd = [binary, "test", "--file", file_path, "--parser", parser_name, "--timeout", str(timeout_sec)]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        if memory_mb and memory_mb > 0 and os.name == "posix":
            # 子进程内限制内存（仅 Linux/WSL）
            def set_limits():
                try:
                    limit = memory_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
                except (ValueError, resource.error):
                    pass
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=PROCESS_TIMEOUT_SEC,
                env=env,
                preexec_fn=set_limits,
            )
        else:
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=PROCESS_TIMEOUT_SEC,
                env=env,
            )
        status, time_ms, memory_kb, ast_nodes = parse_test_output(proc.stdout, proc.stderr)
        if proc.returncode != 0 and status == "ok":
            status = "fail"
        if not time_ms and "超时" in (proc.stderr or "") + (proc.stdout or ""):
            status = "timeout"
            time_ms = str(timeout_sec * 1000)
        return status, time_ms or "", memory_kb or "", ast_nodes or ""
    except subprocess.TimeoutExpired:
        return "timeout", str(timeout_sec * 1000), "", ""
    except Exception as e:
        return "error", "", "", str(e)[:200]


def get_theory_from_path(file_path, benchmark_dir):
    """从文件路径提取理论名，如 .../non-incremental/QF_AX/... -> QF_AX"""
    try:
        p = Path(file_path).resolve()
        b = Path(benchmark_dir).resolve()
        try:
            rel = p.relative_to(b)
        except ValueError:
            return "default"
        parts = rel.parts
        return parts[0] if parts else "default"
    except Exception:
        return "default"


def build_table_from_checkpoint(rows):
    if not rows:
        return [], []
    files = sorted({r["file"] for r in rows})
    parsers = sorted({r["parser"] for r in rows})
    key = lambda r: (r["file"], r["parser"])
    by_key = {key(r): r for r in rows}
    # 长表
    long_header = ["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"]
    long_rows = [long_header]
    for f in files:
        for p in parsers:
            r = by_key.get((f, p), {})
            long_rows.append([
                f, p,
                r.get("status", ""),
                r.get("time_ms", ""),
                r.get("memory_kb", ""),
                r.get("ast_nodes", ""),
            ])
    # 宽表：每行一个 file，每 parser 三列 time_ms, memory_kb, ast_nodes
    wide_header = ["file"] + [f"{p}_time_ms" for p in parsers] + [f"{p}_memory_kb" for p in parsers] + [f"{p}_ast_nodes" for p in parsers]
    wide_rows = [wide_header]
    for f in files:
        row = [f]
        for p in parsers:
            r = by_key.get((f, p), {})
            row.append(r.get("time_ms", ""))
        for p in parsers:
            r = by_key.get((f, p), {})
            row.append(r.get("memory_kb", ""))
        for p in parsers:
            r = by_key.get((f, p), {})
            row.append(r.get("ast_nodes", ""))
        wide_rows.append(row)
    return long_rows, wide_rows


def main():
    parser = argparse.ArgumentParser(description="Parser benchmark with 10s timeout, optional memory limit, checkpoint/resume")
    parser.add_argument("--benchmark-dir", type=Path, default=BENCHMARK_DIR, help="Root of benchmark .smt2 files")
    parser.add_argument("--timeout", type=int, default=PARSE_TIMEOUT_SEC, help="Parse timeout in seconds")
    parser.add_argument("--memory-mb", type=int, default=DEFAULT_MEMORY_MB, help="Memory limit in MB (0 = no limit)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint, skip done (file, parser)")
    parser.add_argument("--dry-run", action="store_true", help="Only list files and parsers, do not run")
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT_CSV, help="Checkpoint CSV path")
    parser.add_argument("--table", type=Path, default=TABLE_CSV, help="Output long table CSV")
    parser.add_argument("--table-wide", type=Path, default=TABLE_WIDE_CSV, help="Output wide table CSV")
    parser.add_argument("--log-dir", type=Path, default=None, help="Per-theory log dir (e.g. results/logs -> QF_AX.log, QF_BV.log)")
    args = parser.parse_args()

    benchmark_dir = args.benchmark_dir.resolve()
    binary = find_binary()
    if not binary:
        print("错误: 未找到 smt_parser_comparison，请在项目根目录 build 或设置 PATH", file=sys.stderr)
        sys.exit(1)

    parsers = get_parser_list(binary)
    if not parsers:
        print("警告: 无法获取 parser 列表，使用默认列表", file=sys.stderr)
        parsers = ["native", "pysmt", "jsmtlib", "z3", "antlr4", "cvc5", "smt-switch"]

    files = collect_smt2_files(benchmark_dir)
    if not files:
        print("错误: 在 {} 下未找到 .smt2/.smt 文件".format(benchmark_dir), file=sys.stderr)
        sys.exit(1)

    done, checkpoint_rows = load_checkpoint(args.checkpoint)
    if args.resume and checkpoint_rows:
        print("从 checkpoint 恢复，已完成 {} 条".format(len(checkpoint_rows)))

    total = len(files) * len(parsers)
    todo = [(f, p) for f in files for p in parsers if (f, p) not in done]
    print("benchmark 目录: {}".format(benchmark_dir))
    print("文件数: {}  解析器: {}  总任务: {}  待跑: {}".format(len(files), len(parsers), total, len(todo)))
    if args.dry_run:
        print("--dry-run: 不执行")
        return 0

    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
    for i, (file_path, parser_name) in enumerate(todo):
        status, time_ms, memory_kb, ast_nodes = run_one(
            binary, file_path, parser_name, args.timeout, args.memory_mb
        )
        append_checkpoint(args.checkpoint, file_path, parser_name, status, time_ms, memory_kb, ast_nodes)
        line = "[{}/{}] {} | {} -> {}  {} ms  {} KB  nodes={}".format(
            i + 1, len(todo), parser_name, Path(file_path).name[:40], status, time_ms, memory_kb, ast_nodes
        )
        print(line, flush=True)
        if args.log_dir:
            theory = get_theory_from_path(file_path, benchmark_dir)
            log_file = args.log_dir / "{}.log".format(theory)
            try:
                with open(log_file, "a", encoding="utf-8") as lf:
                    lf.write(line + "\n")
                    lf.flush()
            except Exception:
                pass

    # 重新加载完整 checkpoint 并写表
    _, all_rows = load_checkpoint(args.checkpoint)
    long_rows, wide_rows = build_table_from_checkpoint(all_rows)
    if long_rows:
        args.table.parent.mkdir(parents=True, exist_ok=True)
        with open(args.table, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(long_rows)
        print("长表已写: {}".format(args.table))
    if wide_rows:
        with open(args.table_wide, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(wide_rows)
        print("宽表已写: {}".format(args.table_wide))
    print("完成: {}".format(datetime.now().isoformat()))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
