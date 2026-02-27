#!/usr/bin/env bash
# 在 external/haskell-0.0.2 目录下使用 cabal 构建 smt-lib 库（无独立 parser 可执行文件时仅建库）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if ! command -v cabal &>/dev/null; then
    echo "未找到 cabal，请安装 GHC/cabal (e.g. ghcup)" >&2
    exit 1
fi
if ! command -v alex &>/dev/null; then
    echo "未找到 alex（Haskell 词法生成器），smt-lib 构建需要。" >&2
    echo "安装: cabal install alex  或  Ubuntu/Debian: sudo apt install alex" >&2
    exit 1
fi
# 更新包索引，否则无法解析 polyparse 等依赖（需网络）
echo "运行 cabal update..."
cabal update
cabal configure
cabal build
echo "smt-lib 为库项目，无独立可执行文件。run.sh 可调用 ghci 或编写小型 main 解析脚本。"
