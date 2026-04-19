#!/usr/bin/env bash
# 从 parser_benchmark_table.csv 按 parser 收集 fail 用例并统计。
# 用法:
#   $0                    # 仅快速统计各 parser 的 fail 数量（纯 awk，不写文件）
#   $0 --collect         # 调用 Python 收集到 results/failures_by_parser/ 并写 summary + 各 parser 的 _failed.txt / _failed.csv
#   $0 --table <csv>     # 指定表文件（默认 results/parser_benchmark_table.csv）
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

TABLE="${TABLE:-results/parser_benchmark_table.csv}"
COLLECT=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --collect) COLLECT=1 ;;
        --table)   TABLE="$2"; shift ;;
        *)         echo "用法: $0 [--collect] [--table <csv>]" >&2; exit 1 ;;
    esac
    shift
done

if [ ! -f "$TABLE" ]; then
    echo "错误: 未找到表文件 $TABLE" >&2
    exit 1
fi

# 快速统计：各 parser 的 fail / ok 数量（跳过表头）
echo "=== 各 parser fail 数量（来自 $TABLE）==="
tail -n +2 "$TABLE" | awk -F',' '
  $2 == "" { next }
  { total[$2]++ }
  $3 == "fail" { fail[$2]++ }
  $3 == "ok"   { ok[$2]++ }
  END {
    printf "%-12s %10s %10s %10s %10s\n", "parser", "total", "ok", "fail", "fail_rate"
    for (p in total) {
      if (p == "parser") next
      f = fail[p]+0
      o = ok[p]+0
      t = total[p]
      rate = (t > 0) ? sprintf("%.2f%%", 100.0*f/t) : "0%"
      printf "%-12s %10d %10d %10d %10s\n", p, t, o, f, rate
    }
  }
' | sort -k1,1

if [ "$COLLECT" -eq 1 ]; then
    echo ""
    python3 scripts/collect_failures_from_table.py --table "$TABLE"
fi
