#!/usr/bin/env bash
# 一键后台跑并行 benchmark（nohup &），默认 200 并行，断点续跑。
# 从项目根运行: ./scripts/run_parallel.sh
# 查看进度: tail -f results/benchmark_main.log
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 路径（可通过环境变量覆盖）
FILE_LIST="${FILE_LIST:-results/file_list.txt}"
BENCHMARK_DIR="${BENCHMARK_DIR:-benchmark/non-incremental}"
LOG_DIR="${LOG_DIR:-results/logs}"
MAIN_LOG="${MAIN_LOG:-results/benchmark_main.log}"
JOBS="${JOBS:-200}"

# 若默认 file_list 不存在，改用 sampled 列表（便于直接跑 sampled 场景）
if [ ! -f "$FILE_LIST" ] && [ -f "benchmark/sampled/file_list.txt" ]; then
    FILE_LIST="benchmark/sampled/file_list.txt"
    BENCHMARK_DIR="benchmark/sampled/files"
    echo "使用 sampled 文件列表: $FILE_LIST"
fi

if [ ! -f "$FILE_LIST" ]; then
    echo "错误: 未找到文件列表 $FILE_LIST" >&2
    echo "请先生成 file_list 或设置 FILE_LIST=path/to/file_list.txt" >&2
    exit 1
fi

mkdir -p results
mkdir -p "$LOG_DIR"

echo "========== 启动并行 Benchmark（nohup 后台） =========="
echo "  FILE_LIST:     $FILE_LIST"
echo "  BENCHMARK_DIR: $BENCHMARK_DIR"
echo "  LOG_DIR:       $LOG_DIR"
echo "  主日志:        $MAIN_LOG"
echo "  并行数:        $JOBS"
echo "  断点续跑:      --resume"
echo ""

PYTHONUNBUFFERED=1 nohup python3 scripts/run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --benchmark-dir "$BENCHMARK_DIR" \
    --timeout 10 \
    --memory-mb 4096 \
    --log-dir "$LOG_DIR" \
    --resume \
    -j "$JOBS" \
    >> "$MAIN_LOG" 2>&1 &

PID=$!
echo "$PID" > results/benchmark_parallel.pid
echo "已启动 PID=$PID"
echo ""
echo "查看进度: tail -f $MAIN_LOG"
echo "停止:     kill $PID 或 kill \$(cat results/benchmark_parallel.pid)"
echo "========== =========="
