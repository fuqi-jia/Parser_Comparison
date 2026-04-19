#!/usr/bin/env bash
# 在 external/haskell-0.0.2 目录下使用 cabal 构建 smt-lib 库（无独立 parser 可执行文件时仅建库）
# 注意：smt-lib-0.0.2 的 alex 生成代码与 GHC 9.x 不兼容（Int#/Int16# 等），推荐用 GHC 8.10 构建。
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
# 若设置了 GHC_VERSION=8.10 或 8.10.7，且 ghcup 已安装该版本，则用其构建（避免 GHC 9.x 与 alex 生成代码不兼容）
RUN_CABAL() {
    cabal update && cabal configure && cabal build
}
if [ -n "${GHC_VERSION:-}" ] && command -v ghcup &>/dev/null; then
    case "$GHC_VERSION" in
        8.10|8.10.*)
             if ghcup list 2>/dev/null | grep -q "ghc-8.10.7"; then
                 echo "使用 GHC 8.10.7 构建（兼容 alex 生成代码）..."
                 export PATH="${HOME}/.local/bin:$PATH"
                 ghcup run ghc-8.10.7 -- bash -c "export PATH=\$HOME/.local/bin:\$PATH && cabal update && cabal configure && cabal build"
                 exit $?
             fi
             ;;
    esac
fi
# 默认用当前 PATH 的 GHC/cabal
echo "运行 cabal update..."
RUN_CABAL
echo "smt-lib 为库项目，无独立可执行文件。run.sh 可调用 ghci 或编写小型 main 解析脚本。"
