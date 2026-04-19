#!/usr/bin/env bash
# Unified entry point for Parser_Comparison workflows.
# Usage: ./parser_comparison.sh <command> [arguments...]
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="${ROOT}/scripts"

usage() {
    sed 's/^    //' <<'EOF'
    Parser_Comparison — unified CLI

    Usage:
      ./parser_comparison.sh <command> [arguments...]

    Commands (extra args are forwarded to the underlying script):

      benchmark | bench
          Run the multi-parser parse-only benchmark.
          Same as: python3 scripts/run_parser_benchmark.py ...
          Example:
            ./parser_comparison.sh benchmark --file-list results/file_list.txt -j 64 --timeout 30

      plots
          Generate per-theory summaries, LaTeX front-end table, and scatter plots.
          Same as: ./scripts/gen_all_tables_and_plots.sh [optional-long-csv-path]
          Example:
            ./parser_comparison.sh plots
            ./parser_comparison.sh plots results/parser_benchmark_table.csv

      readme
          Build Markdown tables from results/summary/frontend_table.tex; also merges
          standalone experiment summaries into README (see markers there) and writes
          results/summary/readme_standalone_experiments.md.
          Same as: python3 scripts/gen_readme_tables.py ...
          Example:
            ./parser_comparison.sh readme
            ./parser_comparison.sh readme --readme README.md

      roundtrip
          SMTParser parse → dumpSMT2 → reparse batch run.
          Writes results/roundtrip/roundtrip_table.csv and roundtrip_summary.md.
          Same as: python3 scripts/run_roundtrip_benchmark.py ...
          Example:
            ./parser_comparison.sh roundtrip --file-list results/file_list.txt -j 32

      robustness
          Aggregate native status by theory (optional round-trip merge).
          Writes results/robustness/robustness_summary.md.
          Same as: python3 scripts/summarize_robustness.py ...
          Example:
            ./parser_comparison.sh robustness

      parse-vs-solve
          Z3 parse vs check_sat wall-clock benchmark.
          Writes results/parse_vs_solve/*.csv and parse_vs_solve_summary.md.
          Same as: python3 scripts/run_parse_vs_solve_benchmark.py ...
          Example:
            ./parser_comparison.sh parse-vs-solve --file-list results/file_list.txt -j 8

      sampled
          One-shot sampled pipeline (sample → bench → recheck → summary → LaTeX).
          Same as: ./scripts/run_sampled_full.sh ...
          Example:
            ./parser_comparison.sh sampled
            ./parser_comparison.sh sampled --fresh

      build-parsers
          Build all external parser drivers under external/.
          Same as: ./scripts/build_all_parsers.sh [optional-external-root]
          Example:
            ./parser_comparison.sh build-parsers

      download
          Download benchmarks / parser binaries (wrapper around scripts/download.sh).
          Example:
            ./parser_comparison.sh download --parsers-only

      summary
          Per-theory CSV/Markdown summary from a long benchmark table.
          Same as: python3 scripts/gen_summary_table.py ...
          Example:
            ./parser_comparison.sh summary --input results/parser_benchmark_table_sampled.csv

      sample
          Create or refresh sampled benchmark manifest/files.
          Same as: ./scripts/sample.sh ...
          Example:
            ./parser_comparison.sh sample

      help | -h | --help
          Show this message.

    Run from the repository root (or any directory — paths are resolved from this script).
EOF
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

CMD="$1"
shift

cd "${ROOT}" || exit 1

case "${CMD}" in
    benchmark|bench)
        exec python3 "${SCRIPTS}/run_parser_benchmark.py" "$@"
        ;;
    plots)
        exec bash "${SCRIPTS}/gen_all_tables_and_plots.sh" "$@"
        ;;
    readme)
        exec python3 "${SCRIPTS}/gen_readme_tables.py" "$@"
        ;;
    roundtrip)
        exec python3 "${SCRIPTS}/run_roundtrip_benchmark.py" "$@"
        ;;
    robustness)
        exec python3 "${SCRIPTS}/summarize_robustness.py" "$@"
        ;;
    parse-vs-solve|parse_vs_solve|z3-parse-solve)
        exec python3 "${SCRIPTS}/run_parse_vs_solve_benchmark.py" "$@"
        ;;
    sampled)
        exec bash "${SCRIPTS}/run_sampled_full.sh" "$@"
        ;;
    build-parsers|build_parsers)
        exec bash "${SCRIPTS}/build_all_parsers.sh" "$@"
        ;;
    download)
        exec bash "${SCRIPTS}/download.sh" "$@"
        ;;
    summary)
        exec python3 "${SCRIPTS}/gen_summary_table.py" "$@"
        ;;
    sample)
        exec bash "${SCRIPTS}/sample.sh" "$@"
        ;;
    help|-h|--help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown command: ${CMD}" >&2
        echo >&2
        usage >&2
        exit 1
        ;;
esac
