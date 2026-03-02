#!/usr/bin/env bash
# 仅重跑 checkpoint 中 status=fail/timeout 的 (file, parser)，用于纠正误判，并更新 summary
# 默认断点续跑：若 recheck_out 已存在则跳过已完成条。可加 --only-parser native 只重跑 native。
# 从项目根运行
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

RESUME=1
ONLY_PARSER=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --fresh) RESUME=0; shift ;;
        --only-parser) ONLY_PARSER="${2:-}"; shift 2 ;;
        *) break ;;
    esac
done
FILE_LIST="${1:-benchmark/sampled/file_list.txt}"
CHECKPOINT="${2:-results/parser_benchmark_checkpoint_sampled.csv}"
RECHECK_OUT="${3:-results/parser_benchmark_recheck_sampled.csv}"
TABLE="${4:-results/parser_benchmark_table_sampled.csv}"
OUTPUT_DIR="${5:-results/summary}"

if [ ! -f "$FILE_LIST" ]; then
    echo "错误: 未找到文件列表 $FILE_LIST" >&2
    echo "用法: $0 [--fresh] [--only-parser NAME] [file_list] [checkpoint] [recheck_out] [table] [output_dir]" >&2
    echo "  --fresh  从头开始（清空 recheck_out 再跑）；默认断点续跑" >&2
    echo "  --only-parser NAME  只重跑指定 parser（如 native）" >&2
    exit 1
fi
if [ ! -f "$CHECKPOINT" ]; then
    echo "错误: checkpoint 不存在: $CHECKPOINT" >&2
    exit 1
fi
if [ "$RESUME" -eq 0 ] && [ -f "$RECHECK_OUT" ]; then
    rm -f "$RECHECK_OUT"
    echo "已删除旧 recheck 文件，从头开始: $RECHECK_OUT"
fi

echo "文件列表: $FILE_LIST"
echo "checkpoint: $CHECKPOINT"
echo "重跑结果输出: $RECHECK_OUT"
if [ "$RESUME" -eq 1 ] && [ -f "$RECHECK_OUT" ]; then
    echo "断点续跑: 将跳过已有记录"
fi
[ -n "$ONLY_PARSER" ] && echo "仅重跑 parser: $ONLY_PARSER"
echo ""

EXTRA="--only-fail"
[ "$RESUME" -eq 1 ] && EXTRA="$EXTRA --resume"
[ -n "$ONLY_PARSER" ] && EXTRA="$EXTRA --only-parser $ONLY_PARSER"

python3 scripts/re_run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --checkpoint "$CHECKPOINT" \
    --recheck-out "$RECHECK_OUT" \
    $EXTRA

echo ""
echo "用重跑结果更新 summary（覆盖误判为 fail 的统计）:"
echo "  python3 scripts/gen_summary_table.py --input $TABLE --update-from-recheck $RECHECK_OUT --output-dir $OUTPUT_DIR"
