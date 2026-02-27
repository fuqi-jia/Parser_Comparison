#!/usr/bin/env bash
# 一键：先编译所有 external parser，再构建主工程，最后用所有 parser 跑一个例子并检查结果（含 ast_node_count）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========== 1/3 编译 external 下所有 parser =========="
if [ -f "$PROJECT_ROOT/external/build_all_parsers.sh" ]; then
    "$PROJECT_ROOT/external/build_all_parsers.sh" || true
else
    echo "未找到 external/build_all_parsers.sh，跳过"
fi

echo ""
echo "========== 2/3 构建主工程 (smt_parser_comparison + smt_parser_wrapper) =========="
mkdir -p "$PROJECT_ROOT/build"
cd "$PROJECT_ROOT/build"
if [ ! -f Makefile ]; then
    cmake .. -DCMAKE_BUILD_TYPE=Release
fi
make -j"$(nproc 2>/dev/null || echo 1)"

echo ""
echo "========== 3/3 用所有 parser 跑示例并检查 (success / parse_time / ast_node_count) =========="
EXAMPLE="$PROJECT_ROOT/example.smt2"
if [ ! -f "$EXAMPLE" ]; then
    echo "未找到 example.smt2，使用 test/example.smt2（若存在）"
    EXAMPLE="$PROJECT_ROOT/test/example.smt2"
fi
if [ ! -f "$EXAMPLE" ]; then
    echo "错误: 未找到示例文件 example.smt2"
    exit 1
fi

# 从项目根目录运行，便于 resolveExternalPath 找到 external
cd "$PROJECT_ROOT"
"$PROJECT_ROOT/build/smt_parser_comparison" test --file "$EXAMPLE" --timeout 30

echo ""
echo "========== 完成 =========="
echo "若某 parser 失败或 ast_node_count 为 0，请检查该 parser 的 run 路径与 JSON 输出格式。"
