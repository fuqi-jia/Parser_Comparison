#!/usr/bin/env bash
# 在 external/smt-switch 目录下运行：使用本目录 build/smt_switch_parser 解析 SMT 文件，输出 JSON
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
EXE=""
if [ -x "build/smt_switch_parser" ]; then
    EXE="build/smt_switch_parser"
else
    for d in smt-switch-*/build; do
        if [ -x "$d/smt_switch_parser" ]; then
            EXE="$d/smt_switch_parser"
            break
        fi
    done
fi
if [ -z "$EXE" ]; then
    echo "未找到 smt_switch_parser，请运行 ./build.sh" >&2
    exit 1
fi
exec "$EXE" "$@"
