#!/usr/bin/env bash
# 一键生成：汇总表（按理论 .csv/.md）、LaTeX 前端表、散点图。
# 支持 sampled 表或全集表（自动从路径提取理论：sampled/files/ 或 non-incremental/）。
# 用法: $0 [长表CSV路径]
# 默认: 优先 results/parser_benchmark_table_sampled.csv，否则 results/parser_benchmark_table.csv
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TABLE="${1:-}"
if [ -z "$TABLE" ]; then
    if [ -f "results/parser_benchmark_table_sampled.csv" ]; then
        TABLE="results/parser_benchmark_table_sampled.csv"
    elif [ -f "results/parser_benchmark_table.csv" ]; then
        TABLE="results/parser_benchmark_table.csv"
    else
        echo "错误: 未找到长表。请指定 CSV 路径，或确保以下之一存在：" >&2
        echo "  results/parser_benchmark_table_sampled.csv" >&2
        echo "  results/parser_benchmark_table.csv" >&2
        echo "用法: $0 [长表CSV路径]" >&2
        exit 1
    fi
fi

if [ ! -f "$TABLE" ]; then
    echo "错误: 未找到输入文件 $TABLE" >&2
    exit 1
fi

SUMMARY_DIR="results/summary"
echo "=== 使用长表: $TABLE ==="
echo ""

echo ">>> 1/3 生成汇总表 (按理论 .csv + .md) -> $SUMMARY_DIR/"
"$SCRIPT_DIR/gen_summary_table.sh" "$TABLE" "$SUMMARY_DIR"
echo ""

echo ">>> 2/3 生成 LaTeX 前端表 -> $SUMMARY_DIR/frontend_table.tex"
"$SCRIPT_DIR/gen_latex_frontend_table.sh" "$SUMMARY_DIR"
echo ""

echo ">>> 3/3 生成散点图 (time/rss/nodes) -> results/frontend_scatter/"
"$SCRIPT_DIR/run_plot_frontend_scatter.sh" "$TABLE" "results/frontend_scatter"
echo ""

echo "全部完成。"
echo "  - 汇总: $SUMMARY_DIR/parser_summary_sampled_<理论>.csv/.md"
echo "  - LaTeX: $SUMMARY_DIR/frontend_table.tex"
echo "  - 散点图: results/frontend_scatter/time/ rss/ nodes/"
