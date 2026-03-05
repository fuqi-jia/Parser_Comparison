#!/usr/bin/env bash
# 停止 run_parallel.sh 启动的 benchmark：先杀主进程，再按进程名清掉残留（python3、z3_parser、cvc5_parser 等）。
# 从项目根运行: ./scripts/kill.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PID_FILE="${PID_FILE:-results/benchmark_parallel.pid}"

# 若有 PID 文件，先杀主进程及进程组
if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "正在停止主进程 PID=$PID ..."
    kill -TERM -"$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null
    for _ in 1 2 3 4 5; do
      sleep 1
      kill -0 "$PID" 2>/dev/null || break
    done
    kill -KILL -"$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

# 按进程名强杀残留（benchmark 子进程）
_kill_by_name() {
  local name="$1"
  local pids
  pids=$(pidof "$name" 2>/dev/null) || true
  if [ -n "$pids" ]; then
    echo "kill -9 $name: $pids"
    kill -9 $pids 2>/dev/null || true
  fi
}

echo "按进程名清理残留..."
_kill_by_name python3
_kill_by_name z3_parser
_kill_by_name cvc5_parser
_kill_by_name smt_parser_comparison
_kill_by_name pysmt_parser
_kill_by_name antlr4_parser
_kill_by_name jsmtlib_parser
_kill_by_name native_parser
_kill_by_name prolog_smtlib_parser
_kill_by_name haskell_parser
_kill_by_name ocaml_parser
_kill_by_name smt_switch_parser
_kill_by_name smt_parser_wrapper
# 若有其他 parser 可执行名可在此追加，例如: _kill_by_name antlr4_parser

echo "完成"
