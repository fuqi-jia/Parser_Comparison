#!/usr/bin/env bash
# 从 results/summary 的 parser_summary_sampled_*.md 生成 LaTeX 前端对比表 frontend_table.tex
# 表中最佳值会加粗：时间/内存/超时/失败取最小，节点数取最大。不含支持率。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SUMMARY_DIR="${1:-results/summary}"
OUTPUT="${2:-}"

if [ -n "$OUTPUT" ]; then
    python3 scripts/gen_latex_frontend_table.py --summary-dir "$SUMMARY_DIR" -o "$OUTPUT"
else
    python3 scripts/gen_latex_frontend_table.py --summary-dir "$SUMMARY_DIR"
fi
echo "完成。"
