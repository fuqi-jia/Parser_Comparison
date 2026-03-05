#!/usr/bin/env bash
# 在 external/cvc5 下从源码构建 cvc5 并 install 到 cvc5-install，供 cvc5_parser 链接（适用于系统 glibc < 2.38 无法使用预编译包时）
# 依赖：cmake、g++/clang++、python3、bison、flex；可选 --auto-download 自动下载 GMP 等。
# 用法: ./scripts/build_cvc5_from_source.sh [并行数，默认 nproc]
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CVC5_ROOT="$REPO_ROOT/external/cvc5"
NPROC="${1:-$(nproc 2>/dev/null || echo 4)}"
INSTALL_PREFIX="$CVC5_ROOT/cvc5-install"

# 查找 cvc5 源码目录（下载解压后为 cvc5-cvc5-1.3.3 或类似）
SRC_DIR=""
for d in "$CVC5_ROOT"/cvc5-cvc5-*; do
  [ -d "$d" ] && [ -f "$d/configure.sh" ] && SRC_DIR="$d" && break
done
if [ -z "$SRC_DIR" ]; then
  echo "未找到 cvc5 源码目录（需含 configure.sh）。请先运行:"
  echo "  BUILD_CVC5_FROM_SOURCE=1 ./scripts/download.sh --parsers-only"
  echo "或从 https://github.com/cvc5/cvc5/archive/refs/tags/cvc5-1.3.3.tar.gz 下载解压到 $CVC5_ROOT/"
  exit 1
fi

echo "从源码构建 cvc5 -> $INSTALL_PREFIX（约需数分钟）"
echo "源码目录: $SRC_DIR"
cd "$SRC_DIR"
# --prefix 必须为绝对路径；--auto-download 自动下载 GMP/CaDiCaL 等
./configure.sh --prefix="$INSTALL_PREFIX" --auto-download production
cd build
make -j"$NPROC"
make install
echo "[OK] cvc5 已安装到 $INSTALL_PREFIX"
echo "请再执行: ./scripts/build_all_parsers.sh  以编译 cvc5_parser"
