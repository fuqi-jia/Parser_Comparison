#!/usr/bin/env bash
# 在 external/jsmtlib 目录下编译 Java 解析器（需已存在 jSMTLIB-0.9.10.1 源码）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
SRC="jSMTLIB-0.9.10.1/SMT/src"
if [ ! -d "$SRC" ]; then
    echo "未找到 $SRC，请先放置 jSMTLIB 源码或解压 jSMTLIB-0.9.10.1" >&2
    exit 1
fi
javac -cp ".:$SRC" -d . "$SRC"/org/smtlib/*.java "$SRC"/org/smtlib/**/*.java 2>/dev/null || true
javac -cp ".:$SRC" -d . jsmtlib_parser.java 2>/dev/null || true
echo "若需完整编译，请参考 jSMTLIB 文档或使用 IDE 导出 jar 后放入本目录。"
