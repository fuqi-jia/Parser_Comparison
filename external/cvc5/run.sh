#!/usr/bin/env bash
# 在 external/cvc5 目录下运行：使用本目录中的 cvc5 二进制解析 SMT 文件
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CVC5_BIN=""
if [ -x "build/bin/cvc5" ]; then
    CVC5_BIN="build/bin/cvc5"
elif [ -x "bin/cvc5" ]; then
    CVC5_BIN="bin/cvc5"
else
    for d in cvc5-Linux-* cvc5-*-*; do
        if [ -d "$d" ] && [ -x "$d/bin/cvc5" ]; then
            CVC5_BIN="$d/bin/cvc5"
            break
        fi
    done
fi
if [ -z "$CVC5_BIN" ]; then
    CVC5_BIN="cvc5"
fi
exec "$CVC5_BIN" "$@"
