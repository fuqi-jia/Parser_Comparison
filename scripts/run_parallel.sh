#!/usr/bin/env bash
# 一键后台跑并行 benchmark（nohup &），默认跑全集 benchmark/non-incremental，30 秒超时，断点续跑。
# 默认 JOBS=24，避免打满 CPU；需要更快可设 JOBS=64 等，勿在共享机上设过大（如 200）。
# 从项目根运行: ./scripts/run_parallel.sh
# 只跑单个 parser 并更新主表: PARSER=cvc5 ./scripts/run_parallel.sh
# 排除若干 parser（如先不跑 Java）: EXCLUDE_PARSER=antlr4,z3 ./scripts/run_parallel.sh
# 之后可用 PARSER=xxx 补跑被排除的 parser，结果会合并进同一主表。
# 查看进度: tail -f results/benchmark_main.log
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 路径（可通过环境变量覆盖）；默认使用全集 benchmark/non-incremental
FILE_LIST="${FILE_LIST:-results/file_list.txt}"
BENCHMARK_DIR="${BENCHMARK_DIR:-benchmark/non-incremental}"
LOG_DIR="${LOG_DIR:-results/logs}"
MAIN_LOG="${MAIN_LOG:-results/benchmark_main.log}"
JOBS="${JOBS:-200}"
TIMEOUT="${TIMEOUT:-30}"
# 只跑单个 parser 时设置，例如 PARSER=cvc5；结果会合并进主表
PARSER="${PARSER:-}"
# 排除若干 parser（逗号分隔），例如 EXCLUDE_PARSER=antlr4,z3 先不跑 Java 相关 parser
EXCLUDE_PARSER="${EXCLUDE_PARSER:-}"

# 若默认 file_list 不存在：先尝试从 benchmark 目录自动生成，否则改用 sampled 列表
if [ ! -f "$FILE_LIST" ]; then
  if [ "$FILE_LIST" = "results/file_list.txt" ] && [ -d "${BENCHMARK_DIR:-benchmark/non-incremental}" ]; then
    mkdir -p results
    echo "使用全集: 从 $BENCHMARK_DIR 生成文件列表 → $FILE_LIST"
    find "$BENCHMARK_DIR" -type f \( -name "*.smt2" -o -name "*.smt" \) | sort > "$FILE_LIST"
    COUNT=$(wc -l < "$FILE_LIST")
    echo "  共 $COUNT 个文件"
  fi
fi
if [ ! -f "$FILE_LIST" ] && [ -f "benchmark/sampled/file_list.txt" ]; then
    FILE_LIST="benchmark/sampled/file_list.txt"
    BENCHMARK_DIR="benchmark/sampled/files"
    echo "使用 sampled 文件列表: $FILE_LIST"
fi

if [ ! -f "$FILE_LIST" ]; then
    echo "错误: 未找到文件列表 $FILE_LIST" >&2
    echo "请任选其一：" >&2
    echo "  1) 确保存在 benchmark 目录后直接再运行本脚本（会从 benchmark/non-incremental 自动生成 file_list）" >&2
    echo "  2) 先跑抽样流程: ./scripts/run_sampled_full.sh（会生成 benchmark/sampled/file_list.txt）" >&2
    echo "  3) 手动生成: find benchmark/non-incremental -type f \\( -name '*.smt2' -o -name '*.smt' \\) | sort > results/file_list.txt" >&2
    echo "  4) 指定列表: FILE_LIST=path/to/file_list.txt ./scripts/run_parallel.sh" >&2
    exit 1
fi

mkdir -p results
mkdir -p "$LOG_DIR"

echo "========== 启动并行 Benchmark（nohup 后台） =========="
if [ "$BENCHMARK_DIR" = "benchmark/non-incremental" ]; then
  echo "  数据集:        全集 benchmark/non-incremental"
else
  echo "  数据集:        $BENCHMARK_DIR"
fi
echo "  FILE_LIST:     $FILE_LIST"
echo "  BENCHMARK_DIR: $BENCHMARK_DIR"
echo "  LOG_DIR:       $LOG_DIR"
echo "  主日志:        $MAIN_LOG"
echo "  并行数:        $JOBS"
echo "  超时(秒):     $TIMEOUT"
echo "  断点续跑:      --resume"
[ -n "$PARSER" ] && echo "  仅跑 parser:   $PARSER（结果合并进主表）"
[ -n "$EXCLUDE_PARSER" ] && echo "  排除 parser:   $EXCLUDE_PARSER"
echo ""

ONLY_PARSER_ARGS=""
[ -n "$PARSER" ] && ONLY_PARSER_ARGS="--only-parser $PARSER"

EXCLUDE_PARSER_ARGS=""
if [ -n "$EXCLUDE_PARSER" ]; then
  for p in $(echo "$EXCLUDE_PARSER" | tr ',' ' '); do
    p=$(echo "$p" | tr -d ' ')
    [ -n "$p" ] && EXCLUDE_PARSER_ARGS="$EXCLUDE_PARSER_ARGS --exclude-parser $p"
  done
fi

PYTHONUNBUFFERED=1 nohup python3 scripts/run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --benchmark-dir "$BENCHMARK_DIR" \
    --timeout "$TIMEOUT" \
    --memory-mb 4096 \
    --log-dir "$LOG_DIR" \
    --resume \
    $ONLY_PARSER_ARGS \
    $EXCLUDE_PARSER_ARGS \
    -j "$JOBS" \
    >> "$MAIN_LOG" 2>&1 &

PID=$!
echo "$PID" > results/benchmark_parallel.pid
echo "已启动 PID=$PID"
echo ""
echo "查看进度: tail -f $MAIN_LOG"
echo "停止:     kill $PID 或 kill \$(cat results/benchmark_parallel.pid)"
echo "========== =========="
