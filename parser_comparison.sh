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
          Optional --preset sat2026 fixes timeout/memory/jobs (see scripts/experiment_presets.py).
          Same as: python3 scripts/run_parser_benchmark.py ...
          Example:
            ./parser_comparison.sh benchmark --file-list results/file_list.txt --preset sat2026
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

      presets | preset-list
          List named parameter bundles (--preset / --param) for long runs.
          Same as: python3 scripts/experiment_presets.py list

      roundtrip
          Same-engine round-trip: SOMTParser → dumpSMT2 → SOMTParser reparse (not cross-parser).
          Writes results/roundtrip/roundtrip_table.csv and roundtrip_summary.md.
          Same as: python3 scripts/run_roundtrip_benchmark.py ...
          Example:
            ./parser_comparison.sh roundtrip --file-list results/file_list.txt -j 32
          Optional: --no-summary keeps roundtrip_summary.md unchanged until the run ends;
            then ./parser_comparison.sh roundtrip --finalize-summary

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

      dual-path | native-z3-dual-path
          SOMTParser dumpSMT2 + Z3 on original vs on dump; compare sat/unsat (unknown ignored for mismatch).
          Writes results/native_z3_dual_path/*.csv and native_z3_dual_path_summary.md.
          Needs native_z3_dual_path (build-internal with Z3). Same as: python3 scripts/run_native_z3_dual_path_benchmark.py ...
          Example:
            ./parser_comparison.sh dual-path --file-list results/file_list.txt --preset sat2026

      sampled
          One-shot sampled pipeline (sample → bench → recheck → summary → LaTeX).
          Same as: ./scripts/run_sampled_full.sh ...
          Example:
            ./parser_comparison.sh sampled
            ./parser_comparison.sh sampled --fresh

      build
          Build everything: native CMake targets then all external parser drivers.
          Same as: ./scripts/build_all.sh ...
          Extra arguments are forwarded only to the native cmake --build step.
          Example:
            ./parser_comparison.sh build
            ./parser_comparison.sh build --parallel 16

      build-internal
          CMake configure + build for this repo only (smt_parser_comparison, roundtrip_tool, …).
          Same as: ./scripts/build_native.sh ...
          Build directory defaults to build/; override with BUILD_DIR=/path.
          Extra arguments go to cmake --build (e.g. --parallel 8, --target roundtrip_tool).
          Example:
            ./parser_comparison.sh build-internal
            ./parser_comparison.sh build-internal --parallel 16

      build-external | build-parsers | build_parsers
          Build all external parser drivers under external/ (alias: build-parsers).
          Same as: ./scripts/build_all_parsers.sh [optional-external-root]
          Example:
            ./parser_comparison.sh build-external
            ./parser_comparison.sh build-parsers

      prepare
          After clone: init git submodules (e.g. SOMTParser) then run download.sh for all external deps + benchmarks.
          Same as: ./scripts/prepare.sh ...
          Pass-through flags match download.sh (--parsers-only, --benchmark-only, --theories …).
          Example:
            ./parser_comparison.sh prepare
            ./parser_comparison.sh prepare --parsers-only

      download
          Download benchmarks / parser binaries only (no submodule init). Prefer prepare on fresh clones.
          Example:
            ./parser_comparison.sh download --parsers-only

      git-untrack-vendored
          Remove vendored paths under external/ from Git tracking only (git rm --cached); local files stay.
          Dry-run by default; use --yes. Optional --sweep-ignored to also untrack tracked-but-ignored files.
          Same as: ./scripts/git_untrack_external_vendored.sh ...
          Example:
            ./parser_comparison.sh git-untrack-vendored
            ./parser_comparison.sh git-untrack-vendored --yes --sweep-ignored

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
    presets|preset-list)
        exec python3 "${SCRIPTS}/experiment_presets.py" list
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
    dual-path|dual_path|native-z3-dual-path|native_z3_dual_path)
        exec python3 "${SCRIPTS}/run_native_z3_dual_path_benchmark.py" "$@"
        ;;
    sampled)
        exec bash "${SCRIPTS}/run_sampled_full.sh" "$@"
        ;;
    build)
        exec bash "${SCRIPTS}/build_all.sh" "$@"
        ;;
    build-internal|build_internal)
        exec bash "${SCRIPTS}/build_native.sh" "$@"
        ;;
    build-external|build_external|build-parsers|build_parsers)
        exec bash "${SCRIPTS}/build_all_parsers.sh" "$@"
        ;;
    prepare)
        exec bash "${SCRIPTS}/prepare.sh" "$@"
        ;;
    download)
        exec bash "${SCRIPTS}/download.sh" "$@"
        ;;
    git-untrack-vendored|git_untrack_vendored)
        exec bash "${SCRIPTS}/git_untrack_external_vendored.sh" "$@"
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
