#!/usr/bin/env bash
# 一键：先从 parser_benchmark_table 收集各 parser 的失败用例，再并行重跑并收集/合并错误原因。
# 默认并行核数 100，可通过 -j 覆盖。
#
# 用法: $0 [--table CSV] [-j N]
#   --table  指定长表（默认 results/parser_benchmark_table.csv）
#   -j N     并行数（默认 100）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 默认并行核数（写死在脚本里，可用 -j 覆盖）
JOBS=100
TABLE="results/parser_benchmark_table.csv"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --table) TABLE="$2"; shift ;;
        -j)      JOBS="$2"; shift ;;
        *)       echo "用法: $0 [--table CSV] [-j N]" >&2; exit 1 ;;
    esac
    shift
done

if [ ! -f "$TABLE" ]; then
    echo "错误: 未找到表文件 $TABLE" >&2
    exit 1
fi

echo "===== 1/2 收集失败用例 -> results/failures_by_parser/ ====="
bash scripts/collect_failures_from_table.sh --collect --table "$TABLE"

echo ""
echo "===== 2/2 并行重跑并收集错误原因（-j $JOBS）-> results/failure_reasons/ ====="
bash scripts/run_failures_collect_reasons.sh --failures-dir results/failures_by_parser --out-dir results/failure_reasons -j "$JOBS"

echo ""
echo "一键完成。失败列表: results/failures_by_parser/  原因汇总: results/failure_reasons/"
