#!/usr/bin/env bash
# 按文件名在 benchmark 下查找 .smt2/.smt，打印相对路径。
# 先精确匹配，无结果时再按前缀匹配（便于处理日志里被截断的长文件名）。
# 用法: ./scripts/find_benchmark.sh <basename> [basename ...]
# 例:   ./scripts/find_benchmark.sh predicate_877.smt2
#       ./scripts/find_benchmark.sh CookSeeZuleger-2013TACAS-Fig7b_true-term
set -e
if [ $# -eq 0 ]; then
  echo "用法: $0 <basename> [basename ...]" >&2
  echo "例:   $0 predicate_877.smt2" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"
BENCH_DIR="${BENCH_DIR:-benchmark/non-incremental}"
if [ ! -d "$BENCH_DIR" ]; then
  BENCH_DIR="benchmark"
fi
for name in "$@"; do
  found=""
  # 先精确匹配
  while IFS= read -r -d '' path; do
    echo "$path"
    found=1
  done < <(find "$BENCH_DIR" -type f \( -name "*.smt2" -o -name "*.smt" \) -name "$name" -print0 2>/dev/null)
  # 无结果时再按前缀匹配（应对日志中名字被截断的情况）
  if [ -z "$found" ]; then
    while IFS= read -r -d '' path; do
      echo "$path"
      found=1
    done < <(find "$BENCH_DIR" -type f \( -name "*.smt2" -o -name "*.smt" \) -name "${name}*" -print0 2>/dev/null)
  fi
  if [ -z "$found" ]; then
    echo "未找到: $name" >&2
  fi
done
