#!/usr/bin/env bash
# 在 external/jsmtlib 目录下运行：使用本目录的 classpath 运行 jsmtlib_parser，输出 JSON
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
SRC="jSMTLIB-0.9.10.1/SMT/src"
CP=".:$SRC"
if [ ! -d "$SRC" ]; then
    echo "未找到 $SRC，请先运行 build.sh 或放置 jSMTLIB 源码" >&2
    exit 1
fi
exec java -cp "$CP" jsmtlib_parser "$@"
