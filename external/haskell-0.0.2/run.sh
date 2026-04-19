#!/usr/bin/env bash
# 在 external/haskell-0.0.2 目录下运行：smt-lib 为库，此处用 ghci 读文件并解析（示例）
# 若需与对比工具一致输出 JSON，需在仓库内另写一 Haskell 可执行程序并在此调用
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ $# -lt 1 ]; then
    echo "用法: $0 <file.smt2>" >&2
    exit 1
fi
FILE="$1"
if ! command -v cabal &>/dev/null; then
    echo "未找到 cabal" >&2
    exit 1
fi
# 简单示例：用 runhaskell 或 ghci 加载库并解析（需项目提供 Main 或脚本）
echo "{\"success\":false,\"parse_time\":0,\"memory_usage\":0,\"ast_node_count\":0,\"errors\":[\"haskell smt-lib 为库，暂无独立 parser 可执行文件；请用 cabal build 并自行编写 main 或使用 run.sh 包装\"]}"
