#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parser benchmark：对 .smt2 列表跑所有 parser，10s 超时、可选内存上限，断点续跑。
用法:
  python3 scripts/run_parser_benchmark.py --benchmark-dir benchmark/non-incremental/_test_one
  python3 scripts/run_parser_benchmark.py --file-list results/file_list.txt --benchmark-dir benchmark/non-incremental
  --file-list: 一行一个 .smt2 路径，不扫描目录（适合几十 G 的 benchmark）
  --log-dir results/logs: 按理论分 log（仅若干 QF_*.log）。Java 崩溃转储统一写到 results/java_errors/
  PYTHONUNBUFFERED=1 nohup ... > results/benchmark_main.log 2>&1 &
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

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = REPO_ROOT / "benchmark" / "non-incremental"
BINARY_NAMES = ["smt_parser_comparison", "build/smt_parser_comparison"]
PARSE_TIMEOUT_SEC = 10
PROCESS_TIMEOUT_SEC = PARSE_TIMEOUT_SEC + 5
DEFAULT_MEMORY_MB = 4096
CHECKPOINT_CSV = REPO_ROOT / "results" / "parser_benchmark_checkpoint.csv"
TABLE_CSV = REPO_ROOT / "results" / "parser_benchmark_table.csv"
TABLE_WIDE_CSV = REPO_ROOT / "results" / "parser_benchmark_table_wide.csv"
REPLAY_POSITION_FILE = REPO_ROOT / "results" / "replay_position.txt"
REPLAY_INTERVAL = 1000
# 说明: 本脚本每完成 REPLAY_INTERVAL 条任务会覆盖写入 results/replay_position.txt；
# 项目根目录下的 replay_pid*.log 来自 Java/其他进程，非本脚本生成。

def find_binary():
    for name in BINARY_NAMES:
        path = REPO_ROOT / name if not os.path.isabs(name) else Path(name)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
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
        names = []
        for line in out.stdout.splitlines():
            m = re.match(r"^\s*-\s+(\S+)", line.strip())
            if m:
                names.append(m.group(1))
        return names if names else None
    except Exception:
        return None


def load_file_list(path):
    """按行读取路径，相对路径按 REPO_ROOT 解析。保持与 file_list 行顺序一致，不排序。"""
    path = Path(path).resolve()
    if not path.is_file():
        return None
    files = []
    root = REPO_ROOT.resolve()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                p = Path(line)
                if not p.is_absolute():
                    p = root / p
                files.append(str(p))
    return files if files else None


def collect_smt2_files(benchmark_dir):
    if not benchmark_dir.is_dir():
        return []
    files = []
    suffix_ok = (".smt2", ".smt", ".smtlib")
    for root, _, names in os.walk(benchmark_dir, topdown=True):
        for name in names:
            if name.lower().endswith(suffix_ok):
                files.append(str((Path(root) / name).resolve()))
    return sorted(files)


def load_checkpoint(path):
    done = set()
    rows = []
    if not path or not path.is_file():
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
    if not path:
        return
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


def get_theory_from_path(file_path, benchmark_dir):
    try:
        p = Path(file_path).resolve()
        b = Path(benchmark_dir).resolve()
        try:
            rel = p.relative_to(b)
        except ValueError:
            return "default"
        return rel.parts[0] if rel.parts else "default"
    except Exception:
        return "default"


def parse_test_output(stdout, stderr):
    time_ms = memory_kb = ast_nodes = ""
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
    if not os.path.isfile(file_path):
        return "no_file", "", "", "文件不存在"
    cmd = [binary, "test", "--file", file_path, "--parser", parser_name, "--timeout", str(timeout_sec)]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    # 4GB 地址空间时一律为所有子进程设置紧缩 JVM 参数，避免任一 Java parser 未命中列表仍 OOM；ErrorFile=/dev/null 避免写满磁盘
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
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                                  timeout=PROCESS_TIMEOUT_SEC, env=env, preexec_fn=set_limits)
        else:
            proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                                  timeout=PROCESS_TIMEOUT_SEC, env=env)
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


def build_table_from_checkpoint(rows):
    if not rows:
        return [], []
    files = sorted({r["file"] for r in rows})
    parsers = sorted({r["parser"] for r in rows})
    by_key = {(r["file"], r["parser"]): r for r in rows}
    long_header = ["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"]
    long_rows = [long_header]
    for f in files:
        for p in parsers:
            r = by_key.get((f, p), {})
            long_rows.append([f, p, r.get("status", ""), r.get("time_ms", ""), r.get("memory_kb", ""), r.get("ast_nodes", "")])
    wide_header = ["file"] + [f"{p}_time_ms" for p in parsers] + [f"{p}_memory_kb" for p in parsers] + [f"{p}_ast_nodes" for p in parsers]
    wide_rows = [wide_header]
    for f in files:
        row = [f]
        for p in parsers:
            row.append(by_key.get((f, p), {}).get("time_ms", ""))
        for p in parsers:
            row.append(by_key.get((f, p), {}).get("memory_kb", ""))
        for p in parsers:
            row.append(by_key.get((f, p), {}).get("ast_nodes", ""))
        wide_rows.append(row)
    return long_rows, wide_rows


def main():
    ap = argparse.ArgumentParser(description="Parser benchmark, 10s timeout, checkpoint/resume")
    ap.add_argument("--benchmark-dir", type=Path, default=BENCHMARK_DIR, help="Benchmark root (for scan or theory name)")
    ap.add_argument("--file-list", type=Path, default=None, help="One path per line, no scan")
    ap.add_argument("--timeout", type=int, default=PARSE_TIMEOUT_SEC)
    ap.add_argument("--memory-mb", type=int, default=DEFAULT_MEMORY_MB)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--checkpoint", type=Path, default=CHECKPOINT_CSV)
    ap.add_argument("--table", type=Path, default=TABLE_CSV)
    ap.add_argument("--table-wide", type=Path, default=TABLE_WIDE_CSV)
    ap.add_argument("--log-dir", type=Path, default=None)
    args = ap.parse_args()

    def resolve_path(p):
        if p is None:
            return None
        p = Path(p)
        return p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()

    if args.log_dir:
        args.log_dir = resolve_path(args.log_dir)
    args.checkpoint = resolve_path(args.checkpoint)
    args.table = resolve_path(args.table)
    args.table_wide = resolve_path(args.table_wide)
    benchmark_dir = resolve_path(args.benchmark_dir)

    binary = find_binary()
    if not binary:
        print("错误: 未找到 smt_parser_comparison", file=sys.stderr, flush=True)
        return 1
    print("binary: {}".format(binary), flush=True)

    parsers = get_parser_list(binary)
    if not parsers:
        parsers = ["native", "pysmt", "jsmtlib", "z3", "antlr4", "cvc5", "smt-switch"]
        print("警告: 使用默认 parser 列表", file=sys.stderr)
    print("parsers: {}".format(len(parsers)), flush=True)

    if args.file_list:
        args.file_list = resolve_path(args.file_list)
        print("正在加载 file-list: {} ...".format(args.file_list), flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        files = load_file_list(args.file_list)
        if not files:
            print("错误: --file-list 为空或文件不存在: {}".format(args.file_list), file=sys.stderr, flush=True)
            return 1
        print("从 file-list 加载 {} 个文件".format(len(files)), flush=True)
    else:
        if not benchmark_dir.is_dir():
            print("错误: benchmark 目录不存在: {}".format(benchmark_dir), file=sys.stderr, flush=True)
            return 1
        files = collect_smt2_files(benchmark_dir)
        if not files:
            print("错误: 未找到 .smt2 文件: {}".format(benchmark_dir), file=sys.stderr, flush=True)
            return 1
        print("扫描得到 {} 个文件".format(len(files)), flush=True)

    done, checkpoint_rows = load_checkpoint(args.checkpoint)
    # checkpoint 即重启点：存的是已完成的 (file, parser)，续跑时跳过这些；表按 (file, parser) 聚合，与运行顺序无关
    replay_path_resolved = resolve_path(REPLAY_POSITION_FILE)
    if args.resume and checkpoint_rows:
        print("从 checkpoint 恢复，已完成 {} 条".format(len(checkpoint_rows)), flush=True)
    total = len(files) * len(parsers)
    todo = [(f, p) for f in files for p in parsers if (f, p) not in done]
    print("文件数: {}  解析器: {}  总任务: {}  待跑: {}".format(len(files), len(parsers), total, len(todo)), flush=True)
    if args.dry_run:
        return 0

    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
    print("开始运行 {} 个任务（每完成一条会写 checkpoint 和 log）...".format(len(todo)), flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    for i, (file_path, parser_name) in enumerate(todo):
        status, time_ms, memory_kb, ast_nodes = run_one(binary, file_path, parser_name, args.timeout, args.memory_mb)
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
                    try:
                        os.fsync(lf.fileno())
                    except Exception:
                        pass
            except Exception as e:
                print("警告: 无法写入 {}: {}".format(log_file, e), file=sys.stderr, flush=True)
        # 每 1000 条写一次位置 replay，便于断点或查看进度（写入 results/replay_position.txt，非 replay_pid*.log）
        if (i + 1) % REPLAY_INTERVAL == 0:
            try:
                replay_path = replay_path_resolved
                replay_path.parent.mkdir(parents=True, exist_ok=True)
                with open(replay_path, "w", encoding="utf-8") as rf:
                    rf.write("completed_count={}\n".format(i + 1))
                    rf.write("total_todo={}\n".format(len(todo)))
                    rf.write("last_file={}\n".format(file_path))
                    rf.write("last_parser={}\n".format(parser_name))
                    rf.write("timestamp={}\n".format(datetime.now().isoformat()))
                    rf.flush()
                    try:
                        os.fsync(rf.fileno())
                    except Exception:
                        pass
            except Exception:
                pass

    _, all_rows = load_checkpoint(args.checkpoint)
    long_rows, wide_rows = build_table_from_checkpoint(all_rows)
    if long_rows:
        args.table.parent.mkdir(parents=True, exist_ok=True)
        with open(args.table, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(long_rows)
        print("长表: {}".format(args.table), flush=True)
    if wide_rows:
        args.table_wide.parent.mkdir(parents=True, exist_ok=True)
        with open(args.table_wide, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(wide_rows)
        print("宽表: {}".format(args.table_wide), flush=True)
    print("完成: {}".format(datetime.now().isoformat()), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
