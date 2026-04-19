#!/usr/bin/env bash
# 在 external/smt-switch 目录下编译 smt_switch_parser（调用本目录 src，输出到 build/）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p build
cd build
if [ -f Makefile ]; then
    make -j"$(nproc 2>/dev/null || echo 1)"
else
    cmake ..
    make -j"$(nproc 2>/dev/null || echo 1)"
fi
echo "可执行文件: build/smt_switch_parser"
