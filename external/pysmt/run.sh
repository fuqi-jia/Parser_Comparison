#!/usr/bin/env bash
# 在 external/pysmt 目录下运行：使用本目录的 pysmt_parser.py 解析 SMT 文件，输出 JSON
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" pysmt_parser.py "$@"
