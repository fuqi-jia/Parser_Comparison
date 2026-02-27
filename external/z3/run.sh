#!/usr/bin/env bash
# 在 external/z3 目录下运行：使用本目录编译的 z3_parser 解析 SMT 文件，输出 JSON
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

EXE=""
if [ -x "z3_parser" ]; then
    EXE="./z3_parser"
elif [ -x "build/z3_parser" ]; then
    EXE="./build/z3_parser"
else
    echo "未找到 z3_parser，请在本目录执行 make 或 mkdir build && cd build && cmake .. && make" >&2
    exit 1
fi
exec $EXE "$@"
