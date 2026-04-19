#!/usr/bin/env bash
# Run SOMTParser vs competitor metric comparison (instance-level).
# Usage: ./scripts/run_compare_metrics.sh [CSV_PATH] [OUTPUT_CSV]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CSV="${1:-$REPO_ROOT/results/parser_benchmark_table_sampled.csv}"
OUT="${2:-$REPO_ROOT/results/summary/parser_compare_metrics.csv}"

cd "$REPO_ROOT"
mkdir -p "$(dirname "$OUT")"

echo "Input CSV:  $CSV"
echo "Output CSV: $OUT"
echo ""

python3 "$SCRIPT_DIR/compare_parser_metrics.py" "$CSV" -o "$OUT"
echo ""
echo "Results written to: $OUT"
