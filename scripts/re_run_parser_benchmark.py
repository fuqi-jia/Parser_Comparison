#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新运行 parser benchmark：对每个 theory 的每个 benchmark、每个 parser 再跑一遍，
用于纠正因「首行非 JSON」（如 warning）被误判为 fail 的用例。

支持两种模式：
1. 全量重跑：对 file_list × parsers 全部再跑（默认）。
2. 仅重跑原失败：--only-fail，仅对 checkpoint 中 status=fail 的 (file, parser) 重跑。

输出为「重跑结果」CSV，与 checkpoint 同构：file, parser, status, time_ms, memory_kb, ast_nodes。
之后可用 gen_summary_table.py --update-from-recheck <本脚本输出> 将重跑结果合并回长表并重新生成 summary。

用法:
  python3 scripts/re_run_parser_benchmark.py --file-list benchmark/sampled/file_list.txt \\
      --checkpoint results/parser_benchmark_checkpoint_sampled.csv \\
      --recheck-out results/parser_benchmark_recheck_sampled.csv
  python3 scripts/re_run_parser_benchmark.py --only-fail --file-list ... --checkpoint ... --recheck-out ...
"""
from __future__ import print_function

import json
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
BINARY_NAMES = ["smt_parser_comparison", "build/smt_parser_comparison"]
WRAPPER_NAMES = ["build/smt_parser_wrapper", "smt_parser_wrapper"]
PARSE_TIMEOUT_SEC = 10
PROCESS_TIMEOUT_SEC = PARSE_TIMEOUT_SEC + 5
DEFAULT_MEMORY_MB = 4096


def find_wrapper():
    """查找 smt_parser_wrapper，用于 native 时直接调用、避免经 comparison 误判。"""
    for name in WRAPPER_NAMES:
        path = REPO_ROOT / name if not os.path.isabs(name) else Path(name)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    import shutil
    if shutil.which("smt_parser_wrapper"):
        return "smt_parser_wrapper"
    return None


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


def parse_test_output(stdout, stderr):
    """与 run_parser_benchmark.parse_test_output 一致：从 smt_parser_comparison 的 stdout 解析状态与指标。"""
    time_ms = memory_kb = ast_nodes = ""
    status = "fail"
    text = (stdout or "") + "\n" + (stderr or "")
    for line in text.splitlines():
        line = line.strip()
        if "解析状态:" in line or "结果:" in line:
            if "成功" in line:
                status = "ok"
            elif "超时" in line:
                status = "timeout"
            else:
                status = "fail"
        m = re.search(r"解析时间:\s*([\d.]+)\s*ms", line)
        if m:
            time_ms = m.group(1)
        m = re.search(r"内存使用:\s*(\d+)\s*KB", line)
        if m:
            memory_kb = m.group(1)
        m = re.search(r"AST节点数(?:量)?:\s*(\d+)", line)
        if m:
            ast_nodes = m.group(1)
    # 仅当明确是「命令执行超时」时才标为 timeout，避免被首行 "(超时: 10秒)" 误判
    if status != "timeout" and "命令执行超时" in text:
        status = "timeout"
        if not time_ms:
            time_ms = str(PARSE_TIMEOUT_SEC * 1000)
    return status, time_ms, memory_kb, ast_nodes


def _run_native_direct(file_path, timeout_sec):
    """直接调用 smt_parser_wrapper 并解析 JSON，与手动运行一致，避免 comparison 路径误判。"""
    wrapper = find_wrapper()
    if not wrapper:
        return "error", "", "", "未找到 smt_parser_wrapper"
    cmd = [wrapper, file_path] if os.path.isabs(file_path) else [wrapper, str(Path(file_path).resolve())]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec + 5,
        )
        raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
        # 从第一个 { 到匹配的 } 截取 JSON，兼容首行 warning
        start = raw.find("{")
        if start == -1:
            return "fail", "", "", "无 JSON 输出"
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    js = raw[start : i + 1]
                    break
        else:
            return "fail", "", "", "JSON 不完整"
        data = json.loads(js)
        ok = data.get("success", False)
        status = "ok" if ok else "fail"
        time_ms = str(data.get("parse_time", ""))
        mem = data.get("memory_usage") or data.get("peak_memory") or 0
        memory_kb = str(int(mem)) if mem else ""
        ast_nodes = str(int(data.get("ast_node_count", 0)))
        return status, time_ms, memory_kb, ast_nodes
    except subprocess.TimeoutExpired:
        return "timeout", str(timeout_sec * 1000), "", ""
    except Exception as e:
        return "error", "", "", str(e)[:200]


def run_one(binary, file_path, parser_name, timeout_sec, memory_mb):
    if not os.path.isfile(file_path):
        return "no_file", "", "", "文件不存在"
    # native 直接调 wrapper 并解析 JSON，与手动运行一致
    if parser_name == "native":
        return _run_native_direct(file_path, timeout_sec)
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
            proc = subprocess.run(
                cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                timeout=PROCESS_TIMEOUT_SEC, env=env, preexec_fn=set_limits
            )
        else:
            proc = subprocess.run(
                cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                timeout=PROCESS_TIMEOUT_SEC, env=env
            )
        status, time_ms, memory_kb, ast_nodes = parse_test_output(proc.stdout, proc.stderr)
        if proc.returncode != 0 and status == "ok":
            status = "fail"
        if not time_ms and "命令执行超时" in (proc.stderr or "") + (proc.stdout or ""):
            status = "timeout"
            time_ms = str(timeout_sec * 1000)
        return status, time_ms or "", memory_kb or "", ast_nodes or ""
    except subprocess.TimeoutExpired:
        return "timeout", str(timeout_sec * 1000), "", ""
    except Exception as e:
        return "error", "", "", str(e)[:200]


def main():
    ap = argparse.ArgumentParser(
        description="重新运行 parser benchmark（每 theory 每 benchmark 每 parser），输出重跑结果 CSV 供 gen_summary_table --update-from-recheck 合并"
    )
    ap.add_argument("--file-list", type=Path, required=True, help="一行一个 .smt2 路径（如 benchmark/sampled/file_list.txt）")
    ap.add_argument("--checkpoint", type=Path, default=None, help="现有 checkpoint，用于 --only-fail 时筛选待重跑对；全量重跑时可选")
    ap.add_argument("--recheck-out", type=Path, default=None, help="输出重跑结果 CSV（默认 results/parser_benchmark_recheck_sampled.csv）")
    ap.add_argument("--only-fail", action="store_true", help="仅重跑 checkpoint 中 status=fail 或 timeout 的 (file, parser)，用于纠正误判")
    ap.add_argument("--only-parser", type=str, action="append", default=None, metavar="NAME", help="只重跑指定 parser（可多次指定，如 --only-parser native）；不指定则重跑全部 parser")
    ap.add_argument("--resume", action="store_true", help="断点续跑：若 recheck-out 已存在则跳过已有 (file,parser)，只跑未完成的并追加写入")
    ap.add_argument("--timeout", type=int, default=PARSE_TIMEOUT_SEC)
    ap.add_argument("--memory-mb", type=int, default=DEFAULT_MEMORY_MB)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    def resolve_path(p):
        if p is None:
            return None
        p = Path(p)
        return p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()

    args.file_list = resolve_path(args.file_list)
    args.checkpoint = resolve_path(args.checkpoint)
    args.recheck_out = resolve_path(args.recheck_out) or (REPO_ROOT / "results" / "parser_benchmark_recheck_sampled.csv")

    binary = find_binary()
    if not binary:
        print("错误: 未找到 smt_parser_comparison", file=sys.stderr, flush=True)
        return 1
    all_parsers = get_parser_list(binary)
    if not all_parsers:
        all_parsers = ["native", "pysmt", "jsmtlib", "z3", "antlr4", "cvc5", "smt-switch"]
        print("警告: 使用默认 parser 列表", file=sys.stderr)
    if args.only_parser:
        parsers = [p for p in args.only_parser if p in all_parsers]
        if not parsers:
            print("错误: --only-parser 指定的 parser 不在列表中: {}".format(args.only_parser), file=sys.stderr, flush=True)
            return 1
        print("仅重跑 parser: {}".format(parsers), flush=True)
    else:
        parsers = all_parsers
    files = load_file_list(args.file_list)
    if not files:
        print("错误: --file-list 为空或文件不存在: {}".format(args.file_list), file=sys.stderr, flush=True)
        return 1

    if args.only_fail:
        _, checkpoint_rows = load_checkpoint(args.checkpoint)
        if not checkpoint_rows:
            print("错误: --only-fail 但 checkpoint 为空或不存在: {}".format(args.checkpoint), file=sys.stderr, flush=True)
            return 1
        # 重跑 fail 和 timeout，纠正误判（如首行非 JSON 导致 fail、提示里的「超时」导致误判 timeout）
        fail_or_timeout = {(r["file"], r["parser"]) for r in checkpoint_rows if (r.get("status") or "").strip().lower() in ("fail", "timeout")}
        todo = [(f, p) for f in files for p in parsers if (f, p) in fail_or_timeout]
        print("仅重跑原 fail/timeout: {} 条（来自 checkpoint）".format(len(todo)), flush=True)
    else:
        todo = [(f, p) for f in files for p in parsers]
        print("全量重跑: {} 文件 × {} 解析器 = {} 条".format(len(files), len(parsers), len(todo)), flush=True)

    # 断点续跑：从已有 recheck 文件加载已完成的 (file, parser)，只跑未完成的
    done_recheck = set()
    if args.resume and args.recheck_out.exists():
        try:
            with open(args.recheck_out, "r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    key = (row.get("file", ""), row.get("parser", ""))
                    if key[0] and key[1]:
                        done_recheck.add(key)
        except Exception:
            pass
        if done_recheck:
            todo = [(f, p) for f, p in todo if (f, p) not in done_recheck]
            print("断点续跑: 已跳过 {} 条，待跑 {} 条".format(len(done_recheck), len(todo)), flush=True)

    if args.dry_run:
        print("dry-run: 将运行 {} 条".format(len(todo)), flush=True)
        return 0
    if not todo:
        print("待跑 0 条（已全部完成），无需重跑。", flush=True)
        return 0

    args.recheck_out.parent.mkdir(parents=True, exist_ok=True)
    # 若只重跑部分 parser 且 recheck 已存在：保留“非本次要跑”的行，只删除并重跑 todo 中的 (file,parser)
    todo_set = set(todo)
    if args.only_parser and args.recheck_out.exists():
        kept = []
        try:
            with open(args.recheck_out, "r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                for row in r:
                    key = (row.get("file", ""), (row.get("parser") or "").strip())
                    if key not in todo_set:
                        kept.append(row)
        except Exception:
            kept = []
        with open(args.recheck_out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"])
            w.writeheader()
            w.writerows(kept)
        if kept:
            print("已保留 recheck 中 {} 条（仅移除本次待跑的 {} 条），将只替换 {} 的结果".format(len(kept), len(todo_set), parsers), flush=True)
    # 若未续跑且未做“保留”则先写表头；续跑则直接追加
    elif not (args.resume and args.recheck_out.exists()):
        with open(args.recheck_out, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(["file", "parser", "status", "time_ms", "memory_kb", "ast_nodes"])
    for i, (file_path, parser_name) in enumerate(todo):
        status, time_ms, memory_kb, ast_nodes = run_one(binary, file_path, parser_name, args.timeout, args.memory_mb)
        with open(args.recheck_out, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([file_path, parser_name, status, time_ms, memory_kb, ast_nodes])
            f.flush()
        print("[{}/{}] {} | {} -> {}  {} ms  {} KB  nodes={}".format(
            len(done_recheck) + i + 1, len(done_recheck) + len(todo), parser_name, Path(file_path).name[:40], status, time_ms, memory_kb, ast_nodes
        ), flush=True)

    print("重跑结果已写入: {}".format(args.recheck_out), flush=True)
    print("可用: python3 scripts/gen_summary_table.py --input results/parser_benchmark_table_sampled.csv --update-from-recheck {} --output-dir results/summary".format(args.recheck_out), flush=True)
    print("完成: {}".format(datetime.now().isoformat()), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
