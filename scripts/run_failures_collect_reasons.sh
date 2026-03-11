#!/usr/bin/env bash
# 并行重跑失败用例并收集、合并（去重）每个 parser 的错误原因，输出到 results/failure_reasons/。
# 与 collect_failures_from_table.* 独立，不修改 results/failures_by_parser/。
#
# 用法:
#   $0                           # 从 results/failures_by_parser/*_failed.txt 读入，默认 -j 16
#   $0 -j 32                     # 32 并行
#   $0 --table results/parser_benchmark_table.csv
#   $0 --max-tasks 100            # 试跑前 100 条
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FAILURES_DIR=""
TABLE=""
OUT_DIR="results/failure_reasons"
JOBS=16
MAX_TASKS=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --failures-dir) FAILURES_DIR="$2"; shift ;;
        --table)        TABLE="$2"; shift ;;
        --out-dir)      OUT_DIR="$2"; shift ;;
        -j|--jobs)      JOBS="$2"; shift ;;
        --max-tasks)    MAX_TASKS="$2"; shift ;;
        *)              echo "用法: $0 [--failures-dir DIR] [--table CSV] [--out-dir DIR] [-j N] [--max-tasks N]" >&2; exit 1 ;;
    esac
    shift
done

ARGS=("--out-dir" "$OUT_DIR" "-j" "$JOBS")
[ -n "$FAILURES_DIR" ] && ARGS+=("--failures-dir" "$FAILURES_DIR")
[ -n "$TABLE" ]        && ARGS+=("--table" "$TABLE")
[ -n "$MAX_TASKS" ]    && ARGS+=("--max-tasks" "$MAX_TASKS")

# 若未指定输入，默认用 failures_by_parser（脚本内部会读 DEFAULT_FAILURES_DIR）
if [ -z "$FAILURES_DIR" ] && [ -z "$TABLE" ]; then
    if [ ! -d "results/failures_by_parser" ]; then
        echo "未指定 --failures-dir 或 --table，且 results/failures_by_parser 不存在。请先运行: bash scripts/collect_failures_from_table.sh --collect" >&2
        exit 1
    fi
fi

python3 scripts/run_failures_collect_reasons.py "${ARGS[@]}"
echo "完成。查看 $OUT_DIR 下的 *_reasons.json 与 *_reasons_summary.txt"
