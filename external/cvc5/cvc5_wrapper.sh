#!/bin/bash

# CVC5 Parser Wrapper Script
# 用法: ./cvc5_wrapper.sh <smt_file>

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSER_BINARY="$SCRIPT_DIR/cvc5_parser"

# 检查参数
if [ $# -ne 1 ]; then
    echo "用法: $0 <smt_file>" >&2
    echo "例如: $0 test.smt2" >&2
    exit 1
fi

SMT_FILE="$1"

# 检查文件是否存在
if [ ! -f "$SMT_FILE" ]; then
    echo "错误: 文件不存在: $SMT_FILE" >&2
    exit 1
fi

# 检查解析器二进制文件是否存在
if [ ! -f "$PARSER_BINARY" ]; then
    echo "错误: CVC5解析器未编译。请运行 'make' 编译解析器。" >&2
    echo "当前目录: $(pwd)" >&2
    echo "预期位置: $PARSER_BINARY" >&2
    echo "" >&2
    echo "编译步骤:" >&2
    echo "1. 安装CVC5库: sudo apt install libcvc5-dev cvc5" >&2
    echo "2. 运行 'make check-deps' 检查依赖" >&2
    echo "3. 运行 'make' 编译解析器" >&2
    exit 1
fi

# 检查解析器是否可执行
if [ ! -x "$PARSER_BINARY" ]; then
    echo "错误: CVC5解析器没有执行权限。" >&2
    echo "尝试修复: chmod +x $PARSER_BINARY" >&2
    chmod +x "$PARSER_BINARY" 2>/dev/null || {
        echo "无法设置执行权限，请手动执行: chmod +x $PARSER_BINARY" >&2
        exit 1
    }
fi

# 运行解析器
exec "$PARSER_BINARY" "$SMT_FILE" 