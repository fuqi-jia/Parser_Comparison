#!/usr/bin/env bash
# 从 timeout.log 提取超时用例的文件名，在 benchmark 下解析路径，生成 benchmark 文件列表。
# 用法: ./scripts/collect_timeout_benchmark.sh [timeout.log] [output file_list.txt]
# 默认: timeout.log -> benchmark/timeout/file_list.txt
# 使用单次 find + awk 过滤，适合大 benchmark 目录。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

TIMEOUT_LOG="${1:-timeout.log}"
OUT_LIST="${2:-benchmark/timeout/file_list.txt}"
BENCH_DIR="${BENCH_DIR:-benchmark/non-incremental}"
[ ! -d "$BENCH_DIR" ] && BENCH_DIR="benchmark"

if [ ! -f "$TIMEOUT_LOG" ]; then
  echo "错误: 未找到 $TIMEOUT_LOG" >&2
  echo "用法: $0 [timeout.log] [output file_list.txt]" >&2
  exit 1
fi

# 提取 "native | BASENAME ->" 中的 BASENAME，去重、排序
names_file=$(mktemp)
trap 'rm -f "$names_file"' EXIT
sed -n 's/.*native | \([^[:space:]]*\)[[:space:]]*->.*/\1/p' "$TIMEOUT_LOG" | sort -u > "$names_file"
num_names=$(wc -l < "$names_file")

mkdir -p "$(dirname "$OUT_LIST")"

# 单次 find + awk：先精确匹配 basename，再前缀匹配（与 find_benchmark.sh 一致，应对截断文件名）
find "$BENCH_DIR" -type f \( -name "*.smt2" -o -name "*.smt" \) -print 2>/dev/null | \
  awk '
    FNR==NR { names[$0]=1; next }
    {
      path = $0
      b = path
      sub(".*/", "", b)
      if (b in names) { print path; next }
      for (n in names) if (n != b && index(b, n) == 1) { print path; break }
    }
  ' "$names_file" - | sort -u > "$OUT_LIST"
# 转为相对项目根路径（便于跨机器使用）
sed -i "s|^${ROOT}/||" "$OUT_LIST" 2>/dev/null || true

found_count=$(wc -l < "$OUT_LIST")
not_found=()
while IFS= read -r name; do
  # 认为“找到”：存在某路径的 basename 等于 name 或以 name 为前缀
  found=
  while IFS= read -r p; do
    b=$(basename "$p")
    if [[ "$b" == "$name" || "$b" == "$name"* ]]; then found=1; break; fi
  done < "$OUT_LIST"
  [[ -z "$found" ]] && not_found+=("$name")
done < "$names_file"

echo "从 $TIMEOUT_LOG 解析到 $num_names 个唯一文件名，找到 $found_count 个路径，未找到 ${#not_found[@]} 个。"
echo "已写入: $OUT_LIST"
if [ ${#not_found[@]} -gt 0 ]; then
  echo "未找到的文件名:" >&2
  printf '  %s\n' "${not_found[@]}" >&2
fi
