#!/usr/bin/env bash
# 生成「按 parser 分别重跑」的指令，可复制到终端逐条执行。
# 从项目根运行。默认参数与 run_re_run_benchmark.sh 一致。
# 用法: ./scripts/run_each_parser_rerun.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

FILE_LIST="${1:-benchmark/sampled/file_list.txt}"
CHECKPOINT="${2:-results/parser_benchmark_checkpoint_sampled.csv}"
RECHECK_OUT="${3:-results/parser_benchmark_recheck_sampled.csv}"
TABLE="${4:-results/parser_benchmark_table_sampled.csv}"
OUTPUT_DIR="${5:-results/summary}"

echo "# 从项目根执行；仅重跑 fail/timeout，成功写回主表。"
echo "# 第一条若要清空 recheck 再跑，在该条前加 --fresh。"
echo ""

echo "# z3"
echo "./scripts/run_re_run_benchmark.sh --only-parser z3 $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# cvc5"
echo "./scripts/run_re_run_benchmark.sh --only-parser cvc5 $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# smt-switch（跳过已知不支持的 QF_AX、QF_FP）"
echo "./scripts/run_re_run_benchmark.sh --only-parser smt-switch --exclude-theory smt-switch:QF_AX --exclude-theory smt-switch:QF_FP $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# pysmt（跳过已知不支持的 QF_FP）"
echo "./scripts/run_re_run_benchmark.sh --only-parser pysmt --exclude-theory pysmt:QF_FP $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# antlr4"
echo "./scripts/run_re_run_benchmark.sh --only-parser antlr4 $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# jsmtlib"
echo "./scripts/run_re_run_benchmark.sh --only-parser jsmtlib $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# native"
echo "./scripts/run_re_run_benchmark.sh --only-parser native $FILE_LIST $CHECKPOINT $RECHECK_OUT $TABLE $OUTPUT_DIR"
echo ""

echo "# 全部跑完后生成 summary 与 LaTeX 表："
echo "python3 scripts/gen_summary_table.py --input $TABLE --output-dir $OUTPUT_DIR"
echo "./scripts/gen_latex_frontend_table.sh $OUTPUT_DIR"
