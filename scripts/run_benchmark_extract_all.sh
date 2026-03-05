#!/usr/bin/env bash
# 一键下载并解压 SMT-LIB benchmark 全部分区（--all-theories），并行解压。
# 从项目根运行: ./scripts/run_benchmark_extract_all.sh
# 可选: JOBS=200 ./scripts/run_benchmark_extract_all.sh  或  nohup ... &
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

JOBS="${JOBS:-200}"
echo "========== Benchmark 全部下载 + 解压（--all-theories, 解压并行数 $JOBS） =========="
"$SCRIPT_DIR/download.sh" --benchmark-only --all-theories --jobs "$JOBS"
echo "========== 完成 =========="
