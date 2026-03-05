#!/usr/bin/env bash
# 无 root 服务器环境一键准备：用 Conda 创建 Python+pysmt+Java 环境，便于跑 parser benchmark
# 用法: ./scripts/setup_server_env.sh
# 依赖: 无（若未装 conda 会提示下载 Miniconda 到 $HOME）
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_NAME="${SMTBENCH_ENV:-smtbench}"

echo "=============================================="
echo "  Parser_Comparison — 无 root 服务器环境准备"
echo "  REPO_ROOT = $REPO_ROOT"
echo "  Conda 环境名 = $ENV_NAME"
echo "=============================================="

# 检测 conda
CONDA_EXE=""
if command -v conda &>/dev/null; then
    CONDA_EXE="conda"
elif [ -x "$HOME/miniconda3/bin/conda" ]; then
    CONDA_EXE="$HOME/miniconda3/bin/conda"
elif [ -x "$HOME/anaconda3/bin/conda" ]; then
    CONDA_EXE="$HOME/anaconda3/bin/conda"
fi

if [ -z "$CONDA_EXE" ]; then
    echo "未检测到 conda。建议安装 Miniconda 到用户目录（无需 root）："
    echo "  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    echo "  bash Miniconda3-latest-Linux-x86_64.sh -b -p \"\$HOME/miniconda3\""
    echo "  \"\$HOME/miniconda3/bin/conda\" init bash"
    echo "  source ~/.bashrc   # 或重新登录"
    echo "然后重新执行: $0"
    exit 1
fi

# 创建环境（若不存在）
if ! "$CONDA_EXE" env list | grep -q "^${ENV_NAME} "; then
    echo "创建 Conda 环境: $ENV_NAME (Python 3.11)"
    "$CONDA_EXE" create -n "$ENV_NAME" python=3.11 -y
else
    echo "环境已存在: $ENV_NAME"
fi

# 安装 pysmt + OpenJDK（antlr4、jsmtlib 需要 Java）
echo "安装 pysmt 与 OpenJDK 17（conda-forge）..."
"$CONDA_EXE" install -n "$ENV_NAME" -c conda-forge pysmt openjdk=17 -y

# 可选：cmake + 编译器（若系统没有，用于 build_all_parsers.sh）
# 支持: ./setup_server_env.sh --with-cmake  或  INSTALL_CMAKE=1 ./setup_server_env.sh
if [ "${INSTALL_CMAKE:-0}" = "1" ] || [ "$1" = "--with-cmake" ]; then
    echo "安装 cmake 与 compilers（conda-forge）..."
    "$CONDA_EXE" install -n "$ENV_NAME" -c conda-forge cmake compilers -y
    echo "已安装。build 时请先: conda activate $ENV_NAME"
elif [ -t 0 ]; then
    read -p "是否安装 cmake 与编译器到该环境？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy] ]]; then
        "$CONDA_EXE" install -n "$ENV_NAME" -c conda-forge cmake compilers -y
        echo "已安装 cmake 与 compilers。build 时请先: conda activate $ENV_NAME"
    fi
fi

# 获取该环境的 python 路径（供 export PYTHON 用）
CONDA_PY="$("$CONDA_EXE" run -n "$ENV_NAME" which python 2>/dev/null || true)"
if [ -z "$CONDA_PY" ]; then
    CONDA_PREFIX="$("$CONDA_EXE" run -n "$ENV_NAME" printenv CONDA_PREFIX 2>/dev/null || true)"
    [ -n "$CONDA_PREFIX" ] && CONDA_PY="$CONDA_PREFIX/bin/python"
fi
if [ -z "$CONDA_PY" ]; then
    CONDA_PY="\$(conda run -n $ENV_NAME which python)"
fi

echo "=============================================="
echo "  下一步（在运行 benchmark 的 shell 中执行）"
echo "=============================================="
echo ""
echo "  1. 激活环境:"
echo "     conda activate $ENV_NAME"
echo ""
echo "  2. 让主程序用该环境的 Python 调 pysmt（必须）："
echo "     export PYTHON=\"$CONDA_PY\""
echo ""
echo "  3. 下载 parser 依赖（若尚未下载）:"
echo "     cd $REPO_ROOT && ./scripts/download.sh --parsers-only"
echo ""
echo "  4. 编译 C++ parser 与主程序:"
echo "     ./scripts/build_all_parsers.sh"
echo "     mkdir -p build && cd build && cmake .. && make -j\$(nproc)"
echo ""
echo "  5. 跑 sampled 全流程:"
echo "     cd $REPO_ROOT && ./scripts/run_sampled_full.sh"
echo ""
echo "  若用 nohup，建议在脚本开头写:"
echo "     export PYTHON=\"$CONDA_PY\""
echo ""
echo "详见: docs/server_setup_no_root.md"
echo "=============================================="
