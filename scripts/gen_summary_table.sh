#!/usr/bin/env bash
# 一键生成 sampled 结果汇总表：平均时间、平均内存峰值、节点数、超时%、非超时失败%
# 从项目根或 scripts 目录运行均可
# 用法: $0 [长表CSV路径] [输出目录]
# 默认: 输入 results/parser_benchmark_table_sampled.csv  输出 results/summary/
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

INPUT="${1:-results/parser_benchmark_table_sampled.csv}"
OUTPUT_DIR="${2:-results/summary}"

if [ ! -f "$INPUT" ]; then
    echo "错误: 未找到输入文件 $INPUT" >&2
    echo "用法: $0 [长表CSV路径] [输出目录]" >&2
    echo "默认: 输入 results/parser_benchmark_table_sampled.csv  输出 results/summary/" >&2
    exit 1
fi

python3 scripts/gen_summary_table.py --input "$INPUT" --output-dir "$OUTPUT_DIR"
echo "完成。"
