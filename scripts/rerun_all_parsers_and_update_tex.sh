#!/usr/bin/env bash
# 对每个 parser 分别 rerun（仅 fail/timeout），再合并 recheck、更新 summary、生成 frontend_table.tex
# 从项目根运行。默认断点续跑；加 --fresh 则清空 recheck 从头重跑。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FILE_LIST="${1:-benchmark/sampled/file_list.txt}"
CHECKPOINT="${2:-results/parser_benchmark_checkpoint_sampled.csv}"
RECHECK_OUT="${3:-results/parser_benchmark_recheck_sampled.csv}"
TABLE="${4:-results/parser_benchmark_table_sampled.csv}"
SUMMARY_DIR="${5:-results/summary}"

FRESH=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --fresh) FRESH="--fresh"; shift ;;
        *) break ;;
    esac
done

if [ ! -f "$FILE_LIST" ]; then
    echo "错误: 未找到文件列表 $FILE_LIST" >&2
    echo "用法: $0 [--fresh] [file_list] [checkpoint] [recheck_out] [table] [summary_dir]" >&2
    exit 1
fi
if [ ! -f "$CHECKPOINT" ]; then
    echo "错误: checkpoint 不存在: $CHECKPOINT" >&2
    exit 1
fi

# 从 checkpoint 取 parser 列表（与 benchmark 一致）
PARSERS=$(python3 -c "
import csv
from pathlib import Path
p = Path('$CHECKPOINT')
with p.open(encoding='utf-8') as f:
    r = csv.DictReader(f)
    parsers = sorted(set(row.get('parser','').strip() for row in r if (row.get('parser') or '').strip()))
print(' '.join(parsers))
")
if [ -z "$PARSERS" ]; then
    echo "错误: 未能从 checkpoint 读取 parser 列表" >&2
    exit 1
fi
echo "将依次 rerun 以下 parser: $PARSERS"
echo ""

# 1) 每个 parser 单独 rerun（断点续跑，只重跑 fail/timeout）
first=1
for p in $PARSERS; do
    if [ -n "$FRESH" ] && [ "$first" -eq 1 ]; then
        ./scripts/run_re_run_benchmark.sh $FRESH --only-parser "$p" "$FILE_LIST" "$CHECKPOINT" "$RECHECK_OUT" "$TABLE" "$SUMMARY_DIR"
        first=0
    else
        ./scripts/run_re_run_benchmark.sh --only-parser "$p" "$FILE_LIST" "$CHECKPOINT" "$RECHECK_OUT" "$TABLE" "$SUMMARY_DIR"
    fi
    echo ""
done

# 2) 用 recheck 覆盖长表统计，生成 summary
echo "用 recheck 更新 summary..."
python3 scripts/gen_summary_table.py --input "$TABLE" --update-from-recheck "$RECHECK_OUT" --output-dir "$SUMMARY_DIR"

# 3) 根据 summary 生成 LaTeX 前端表
echo "生成 frontend_table.tex..."
./scripts/gen_latex_frontend_table.sh "$SUMMARY_DIR"
echo "全部完成。summary 与 $SUMMARY_DIR/frontend_table.tex 已更新。"
