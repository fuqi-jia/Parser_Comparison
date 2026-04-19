#!/usr/bin/env bash
# 一键生成 SOMTParser vs 各 parser 的两两对比散点图（time / rss / nodes，共 18 张）
# 从项目根运行。输出目录默认 results/frontend_scatter，下含 time/ rss/ nodes/。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TABLE="${1:-results/parser_benchmark_table_sampled.csv}"
OUT_DIR="${2:-results/frontend_scatter}"

if [ ! -f "$TABLE" ]; then
    echo "错误: 主表不存在: $TABLE" >&2
    echo "用法: $0 [主表CSV] [输出目录]" >&2
    echo "默认: 主表=results/parser_benchmark_table_sampled.csv  输出=results/frontend_scatter" >&2
    exit 1
fi

echo "依赖: matplotlib (pip install matplotlib)"
echo "主表: $TABLE"
echo "输出: $OUT_DIR"
echo ""

# 优先用 python（conda 环境下通常带 matplotlib），否则用 python3
if command -v python &>/dev/null; then
    python scripts/plot_frontend_scatter.py --table "$TABLE" -o "$OUT_DIR"
else
    python3 scripts/plot_frontend_scatter.py --table "$TABLE" -o "$OUT_DIR"
fi

echo ""
echo "完成。图片在 $OUT_DIR/time/ $OUT_DIR/rss/ $OUT_DIR/nodes/"
