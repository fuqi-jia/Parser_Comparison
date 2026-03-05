#!/usr/bin/env bash
# 停止 run_parallel.sh 启动的 benchmark：杀主进程及其进程组（子进程 cvc5_parser、java 等会一并退出）。
# 从项目根运行: ./scripts/kill.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PID_FILE="${PID_FILE:-results/benchmark_parallel.pid}"

if [ ! -f "$PID_FILE" ]; then
  echo "未找到 PID 文件: $PID_FILE（可能未启动过 run_parallel.sh）" >&2
  exit 1
fi

PID=$(cat "$PID_FILE")
if ! kill -0 "$PID" 2>/dev/null; then
  echo "进程 $PID 已不存在，删除 PID 文件"
  rm -f "$PID_FILE"
  exit 0
fi

echo "正在停止 benchmark（主进程 PID=$PID 及子进程）..."
# 先杀进程组（nohup 启动的 Python 通常是组长，子进程在同一组）
kill -TERM -"$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null

for _ in 1 2 3 4 5; do
  sleep 1
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "已退出"
    rm -f "$PID_FILE"
    exit 0
  fi
done

echo "SIGTERM 未退出，发送 SIGKILL..."
kill -KILL -"$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null
sleep 1
rm -f "$PID_FILE"
echo "已发送 SIGKILL，完成"
