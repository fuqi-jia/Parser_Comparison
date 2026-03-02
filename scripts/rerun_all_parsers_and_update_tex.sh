#!/usr/bin/env bash
# 对每个 parser 分别 rerun（仅 fail/timeout），再合并 recheck、更新 summary、生成 frontend_table.tex
# 已知不支持的 (parser,theory) 默认不重跑：pysmt 不支持 QF_FP，smt-switch 不支持 QF_AX/QF_FP。
# 从项目根运行。默认断点续跑；加 --fresh 则清空 recheck 从头重跑。
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 已知不支持的 (parser,theory)，rerun 时跳过、不浪费时间
EXCLUDE_THEORY_DEFAULT="pysmt:QF_FP smt-switch:QF_AX smt-switch:QF_FP"

FRESH=""
CLEAN_UNSUPPORTED=""
EXCLUDE_PARSER=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --fresh) FRESH="--fresh"; shift ;;
        --clean-unsupported) CLEAN_UNSUPPORTED=1; shift ;;
        --exclude-parser) EXCLUDE_PARSER+=("${2:-}"); shift 2 ;;
        *) break ;;
    esac
done
FILE_LIST="${1:-benchmark/sampled/file_list.txt}"
CHECKPOINT="${2:-results/parser_benchmark_checkpoint_sampled.csv}"
RECHECK_OUT="${3:-results/parser_benchmark_recheck_sampled.csv}"
TABLE="${4:-results/parser_benchmark_table_sampled.csv}"
SUMMARY_DIR="${5:-results/summary}"

if [ ! -f "$FILE_LIST" ]; then
    echo "错误: 未找到文件列表 $FILE_LIST" >&2
    echo "用法: $0 [--fresh] [--clean-unsupported] [--exclude-parser NAME ...] [file_list] [checkpoint] [recheck_out] [table] [summary_dir]" >&2
    echo "  --fresh  清空 recheck 从头重跑" >&2
    echo "  --clean-unsupported  先删除已知不支持的 failure 目录（pysmt/QF_FP、smt-switch/QF_AX、smt-switch/QF_FP）" >&2
    echo "  --exclude-parser NAME  不重跑指定 parser（如 native），可多次" >&2
    exit 1
fi
if [ ! -f "$CHECKPOINT" ]; then
    echo "错误: checkpoint 不存在: $CHECKPOINT" >&2
    exit 1
fi

# 从 checkpoint 取 parser 列表（与 benchmark 一致），并排除 --exclude-parser
if [ ${#EXCLUDE_PARSER[@]} -eq 0 ]; then
    PARSERS=$(python3 -c "
import csv
from pathlib import Path
p = Path('$CHECKPOINT')
with p.open(encoding='utf-8') as f:
    r = csv.DictReader(f)
    parsers = sorted(set(row.get('parser','').strip() for row in r if (row.get('parser') or '').strip()))
print(' '.join(parsers))
")
else
    PARSERS=$(python3 -c "
import csv, sys
from pathlib import Path
p = Path('$CHECKPOINT')
with p.open(encoding='utf-8') as f:
    r = csv.DictReader(f)
    parsers = sorted(set(row.get('parser','').strip() for row in r if (row.get('parser') or '').strip()))
exclude = set(sys.argv[1:])
parsers = [x for x in parsers if x not in exclude]
print(' '.join(parsers))
" "${EXCLUDE_PARSER[@]}")
fi
if [ -z "$PARSERS" ]; then
    echo "错误: 未能从 checkpoint 读取 parser 列表或排除后为空" >&2
    exit 1
fi
[ ${#EXCLUDE_PARSER[@]} -gt 0 ] && echo "已排除 parser: ${EXCLUDE_PARSER[*]}"
echo "将依次 rerun 以下 parser: $PARSERS"
echo "排除 (parser,theory): $EXCLUDE_THEORY_DEFAULT"
echo ""

# 0) 可选：删除已知不支持的 failure 目录，避免把这些当“失败”展示
if [ -n "$CLEAN_UNSUPPORTED" ]; then
    echo "删除已知不支持的 failure 目录..."
    for entry in benchmark/failures/pysmt/QF_FP benchmark/failures/smt-switch/QF_AX benchmark/failures/smt-switch/QF_FP; do
        if [ -e "$entry" ]; then rm -rf "$entry"; echo "  已删: $entry"; fi
    done
    for f in benchmark/failures/pysmt/QF_FP.txt benchmark/failures/smt-switch/QF_AX.txt benchmark/failures/smt-switch/QF_FP.txt; do
        if [ -f "$f" ]; then rm -f "$f"; echo "  已删: $f"; fi
    done
    echo ""
fi

# 1) 每个 parser 单独 rerun（断点续跑，只重跑 fail/timeout；跳过已知不支持的 theory）
first=1
for p in $PARSERS; do
    EXCLUDE_ARGS=()
    for et in $EXCLUDE_THEORY_DEFAULT; do EXCLUDE_ARGS+=(--exclude-theory "$et"); done
    if [ -n "$FRESH" ] && [ "$first" -eq 1 ]; then
        ./scripts/run_re_run_benchmark.sh $FRESH --only-parser "$p" "${EXCLUDE_ARGS[@]}" "$FILE_LIST" "$CHECKPOINT" "$RECHECK_OUT" "$TABLE" "$SUMMARY_DIR"
        first=0
    else
        ./scripts/run_re_run_benchmark.sh --only-parser "$p" "${EXCLUDE_ARGS[@]}" "$FILE_LIST" "$CHECKPOINT" "$RECHECK_OUT" "$TABLE" "$SUMMARY_DIR"
    fi
    echo ""
done

# 2) 重跑成功已写回主表，直接按主表生成 summary
echo "按主表生成 summary..."
python3 scripts/gen_summary_table.py --input "$TABLE" --output-dir "$SUMMARY_DIR"

# 3) 根据 summary 生成 LaTeX 前端表
echo "生成 frontend_table.tex..."
./scripts/gen_latex_frontend_table.sh "$SUMMARY_DIR"
echo "全部完成。summary 与 $SUMMARY_DIR/frontend_table.tex 已更新。"
