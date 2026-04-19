#!/usr/bin/env bash
# 在 external/antlr4_parser 目录下运行：先 make 再 java -cp 运行 antlr4_parser，输出 JSON
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
[ -f antlr4_parser.class ] || make -j"$(nproc 2>/dev/null || echo 1)" 2>/dev/null || make
ANTLR4_JAR="antlr-4.13.2-complete.jar"
if [ ! -f "$ANTLR4_JAR" ]; then
    echo "未找到 $ANTLR4_JAR，请运行 make use-existing-jar JAR_PATH=... 或 make setup-antlr4" >&2
    exit 1
fi
exec java -cp ".:$ANTLR4_JAR" antlr4_parser "$@"
