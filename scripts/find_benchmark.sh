#!/usr/bin/env bash
# 按文件名在 benchmark 下查找 .smt2/.smt，打印相对路径。
# 用法: ./scripts/find_benchmark.sh <basename> [basename ...]
# 例:   ./scripts/find_benchmark.sh predicate_877.smt2
#       ./scripts/find_benchmark.sh dualexecution_affine.t1.i2.b87204b4.smt2
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
  while IFS= read -r -d '' path; do
    echo "$path"
    found=1
  done < <(find "$BENCH_DIR" -type f \( -name "*.smt2" -o -name "*.smt" \) -name "$name" -print0 2>/dev/null)
  if [ -z "$found" ]; then
    echo "未找到: $name" >&2
  fi
done
