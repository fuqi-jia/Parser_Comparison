#!/usr/bin/env bash
# 一键收集各 parser 在各理论下的失败用例，写入 results/failures/<parser>/<理论>.txt
# 若存在 recheck 结果 CSV，默认会排除其中 status=ok 的条目（只保留真正仍失败的）。传 --no-exclude-recheck 可关闭。
# 从项目根或 scripts 目录运行均可
# 用法: $0 [--no-exclude-recheck] [logs目录] [输出目录]
# 默认: logs=results/logs_sampled  输出=benchmark/failures  使用 --exclude-recheck results/parser_benchmark_recheck_sampled.csv
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

RECHECK_CSV="results/parser_benchmark_recheck_sampled.csv"
NO_EXCLUDE=0
while [ "$#" -gt 0 ] && [ "$1" = "--no-exclude-recheck" ]; do
    NO_EXCLUDE=1
    shift
done
LOGS_DIR="${1:-results/logs_sampled}"
OUT_DIR="${2:-benchmark/failures}"

EXCLUDE_RECHECK=""
if [ "$NO_EXCLUDE" -eq 0 ] && [ -f "$RECHECK_CSV" ]; then
    EXCLUDE_RECHECK="--exclude-recheck $RECHECK_CSV"
fi

if [ ! -d "$LOGS_DIR" ]; then
    echo "错误: 未找到 log 目录 $LOGS_DIR" >&2
    echo "用法: $0 [--no-exclude-recheck] [logs目录] [输出目录]" >&2
    echo "默认: logs=results/logs_sampled  输出=benchmark/failures；若存在 $RECHECK_CSV 则排除其中 ok 的" >&2
    exit 1
fi

python3 scripts/collect_parser_failures.py --logs-dir "$LOGS_DIR" --out-dir "$OUT_DIR" $EXCLUDE_RECHECK
echo "完成。"
