#!/usr/bin/env bash
# 一键跑完 sampled 全流程：抽样(可选) → benchmark → recheck(fail/timeout) → summary → frontend_table.tex
# 从项目根运行。默认断点续跑；加 --fresh 则清空 checkpoint/recheck 从头重跑。
# 用法: ./scripts/run_sampled_full.sh [--fresh] [--skip-sample] [--clean-unsupported] [--exclude-parser NAME ...]
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 路径（与 run_sample.sh / rerun_all_parsers_and_update_tex.sh 一致）
SAMPLED_DIR="benchmark/sampled"
FILE_LIST="$SAMPLED_DIR/file_list.txt"
BENCHMARK_DIR="$SAMPLED_DIR/files"
MANIFEST="$SAMPLED_DIR/manifest.csv"
CHECKPOINT="results/parser_benchmark_checkpoint_sampled.csv"
TABLE="results/parser_benchmark_table_sampled.csv"
TABLE_WIDE="results/parser_benchmark_table_wide_sampled.csv"
RECHECK_OUT="results/parser_benchmark_recheck_sampled.csv"
SUMMARY_DIR="results/summary"
LOG_DIR="results/logs_sampled"

# 已知不支持的 (parser,theory)，recheck 时跳过
EXCLUDE_THEORY_DEFAULT="pysmt:QF_FP smt-switch:QF_AX smt-switch:QF_FP"

FRESH=""
SKIP_SAMPLE=""
CLEAN_UNSUPPORTED=""
EXCLUDE_PARSER=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --fresh)      FRESH=1; shift ;;
        --skip-sample) SKIP_SAMPLE=1; shift ;;
        --clean-unsupported) CLEAN_UNSUPPORTED=1; shift ;;
        --exclude-parser) EXCLUDE_PARSER+=("${2:-}"); shift 2 ;;
        *) echo "用法: $0 [--fresh] [--skip-sample] [--clean-unsupported] [--exclude-parser NAME ...]" >&2; exit 1 ;;
    esac
done

echo "========== 1) 抽样与文件列表 =========="
if [ -z "$SKIP_SAMPLE" ]; then
    if [ ! -f "$MANIFEST" ] || [ ! -d "$BENCHMARK_DIR" ]; then
        echo "未找到 $MANIFEST 或 $BENCHMARK_DIR，执行抽样..."
        ./scripts/sample.sh
    else
        echo "已存在 manifest 与 sampled/files，跳过抽样（可用 --skip-sample 显式跳过）"
    fi
else
    echo "已指定 --skip-sample，跳过抽样检查"
fi

if [ ! -f "$MANIFEST" ]; then
    echo "错误: 未找到 $MANIFEST，请先运行 ./scripts/sample.sh 或去掉 --skip-sample" >&2
    exit 1
fi
if [ ! -d "$BENCHMARK_DIR" ]; then
    echo "错误: 未找到 $BENCHMARK_DIR，请先运行 ./scripts/sample.sh" >&2
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

if [ -n "$FRESH" ]; then
    echo "========== --fresh: 清空 checkpoint / table / recheck =========="
    for f in "$CHECKPOINT" "$TABLE" "$TABLE_WIDE" "$RECHECK_OUT"; do
        if [ -f "$f" ]; then rm -f "$f"; echo "  已删: $f"; fi
    done
    echo ""
fi

if [ -n "$CLEAN_UNSUPPORTED" ]; then
    echo "========== --clean-unsupported: 删除已知不支持的 failure 目录 =========="
    for entry in benchmark/failures/pysmt/QF_FP benchmark/failures/smt-switch/QF_AX benchmark/failures/smt-switch/QF_FP; do
        if [ -e "$entry" ]; then rm -rf "$entry"; echo "  已删: $entry"; fi
    done
    for f in benchmark/failures/pysmt/QF_FP.txt benchmark/failures/smt-switch/QF_AX.txt benchmark/failures/smt-switch/QF_FP.txt; do
        if [ -f "$f" ]; then rm -f "$f"; echo "  已删: $f"; fi
    done
    echo ""
fi

echo "========== 2) Parser Benchmark（断点续跑） =========="
BENCHMARK_EXCLUDE=()
for p in "${EXCLUDE_PARSER[@]}"; do [ -n "$p" ] && BENCHMARK_EXCLUDE+=(--exclude-parser "$p"); done
python3 scripts/run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --benchmark-dir "$BENCHMARK_DIR" \
    --timeout 10 \
    --memory-mb 4096 \
    --checkpoint "$CHECKPOINT" \
    --table "$TABLE" \
    --table-wide "$TABLE_WIDE" \
    --log-dir "$LOG_DIR" \
    --resume \
    "${BENCHMARK_EXCLUDE[@]}"

if [ ! -f "$CHECKPOINT" ]; then
    echo "错误: benchmark 未产生 checkpoint: $CHECKPOINT" >&2
    exit 1
fi
echo ""

echo "========== 3) Recheck（仅重跑 fail/timeout，纠正误判） =========="
EXCLUDE_ARGS=()
for et in $EXCLUDE_THEORY_DEFAULT; do EXCLUDE_ARGS+=(--exclude-theory "$et"); done
for p in "${EXCLUDE_PARSER[@]}"; do [ -n "$p" ] && EXCLUDE_ARGS+=(--exclude-parser "$p"); done
python3 scripts/re_run_parser_benchmark.py \
    --file-list "$FILE_LIST" \
    --checkpoint "$CHECKPOINT" \
    --recheck-out "$RECHECK_OUT" \
    --table "$TABLE" \
    --only-fail \
    --resume \
    "${EXCLUDE_ARGS[@]}"
echo ""

echo "========== 4) Summary（重跑成功已写回主表，按主表生成） =========="
python3 scripts/gen_summary_table.py \
    --input "$TABLE" \
    --output-dir "$SUMMARY_DIR"
echo ""

echo "========== 5) LaTeX 前端表 =========="
./scripts/gen_latex_frontend_table.sh "$SUMMARY_DIR"
echo ""

echo "========== 完成 =========="
echo "  checkpoint: $CHECKPOINT"
echo "  长表:       $TABLE"
echo "  recheck:    $RECHECK_OUT"
echo "  summary:    $SUMMARY_DIR/"
echo "  LaTeX 表:   $SUMMARY_DIR/frontend_table.tex"
