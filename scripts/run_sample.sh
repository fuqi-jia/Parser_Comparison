#!/usr/bin/env bash
# 在 benchmark/sampled/files 上运行 parser benchmark（使用 manifest 生成文件列表）
# 从项目根运行，或任意目录执行均可（会 cd 到项目根）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SAMPLED_DIR="benchmark/sampled"
FILE_LIST="$SAMPLED_DIR/file_list.txt"
BENCHMARK_DIR="$SAMPLED_DIR/files"
MANIFEST="$SAMPLED_DIR/manifest.csv"

if [ ! -f "$MANIFEST" ]; then
    echo "错误: 未找到 $MANIFEST，请先运行 scripts/sample_benchmarks.py --copy_files" >&2
    exit 1
fi
if [ ! -d "$BENCHMARK_DIR" ]; then
    echo "错误: 未找到 $BENCHMARK_DIR，请先运行 scripts/sample_benchmarks.py --copy_files" >&2
    exit 1
fi

echo "从 manifest 生成文件列表: $FILE_LIST"
python3 -c "
import csv
from pathlib import Path
manifest = Path('$MANIFEST').resolve()
with open(manifest, encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        print('benchmark/sampled/files/' + row['theory'] + '/' + row['relpath'])
" > "$FILE_LIST"
COUNT=$(wc -l < "$FILE_LIST")
echo "文件数: $COUNT"

echo ""
echo "运行 parser benchmark（sampled 子集）..."
python3 scripts/run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --benchmark-dir "$BENCHMARK_DIR" \
    --timeout 10 \
    --memory-mb 4096 \
    --checkpoint results/parser_benchmark_checkpoint_sampled.csv \
    --table results/parser_benchmark_table_sampled.csv \
    --table-wide results/parser_benchmark_table_wide_sampled.csv \
    --log-dir results/logs_sampled \
    "$@"

echo ""
echo "完成。checkpoint: results/parser_benchmark_checkpoint_sampled.csv  表: results/parser_benchmark_table_sampled.csv"
