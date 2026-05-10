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

      somt-experiments | somt-only
          Run only SOMTParser-side experiments (no other parser drivers): multi-parser benchmark with
          --only-parser native (forced last), then roundtrip, then robustness summary. Does not run
          parse-vs-solve, dual-path, or build-external. Extra args are passed to benchmark and roundtrip
          (same flags as those commands, e.g. --file-list, --preset sat2026, -j). Robustness uses default
          results/parser_benchmark_table.csv unless you re-run: ./parser_comparison.sh robustness --benchmark-csv ...
          Example:
            ./parser_comparison.sh somt-experiments --file-list results/file_list.txt --preset sat2026

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

      rdl-case-study | rdl_case_study
          [deprecated] v1 hand-written demo entry. Now a no-op that exits
          non-zero with a pointer to the v2 commands below.

      rdl-prepare-data
          Extract benchmark/QF_RDL.tar.zst, build the per-file index, and
          produce the deterministic dev/test split (seed=42, n_dev=30).
          Same as: ./case_studies/rdl_prototyping/scripts/extract_qf_rdl.sh
                && python3 .../scripts/build_qf_rdl_index.py
                && python3 .../scripts/split_dev_test.py
          Idempotent. Run once before any LLM trial.

      rdl-llm-campaign
          Run N independent LLM trials per front-end. Reads
          case_studies/rdl_prototyping/config/llm.yaml (provider=mock by
          default; copy llm.yaml.example to llm.yaml and set provider+API
          key to enable real LLMs).
          Same as: python3 .../scripts/run_llm_campaign.py ...
          Example:
            ./parser_comparison.sh rdl-llm-campaign \
                --frontends pysmt z3_cpp --trials 10

      rdl-aggregate
          Read every results/runs/<frontend>/run_NN/meta.json and write
          aggregate CSV + LaTeX/Markdown tables under
          case_studies/rdl_prototyping/results/aggregate/. Read-only with
          respect to runs/.

      rdl-audit
          Static fairness audit on a single adapter source dir. Useful
          when reviewing a trial by hand. Forwards to
          python3 .../scripts/audit_adapter.py
          Example:
            ./parser_comparison.sh rdl-audit \
                --src case_studies/rdl_prototyping/results/runs/pysmt/run_00/src/turn_00 \
                --frontend pysmt

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
    somt-experiments|somt-only)
        echo "== SOMTParser-only: benchmark (native) → roundtrip → robustness ==" >&2
        python3 "${SCRIPTS}/run_parser_benchmark.py" "$@" --only-parser native
        python3 "${SCRIPTS}/run_roundtrip_benchmark.py" "$@"
        python3 "${SCRIPTS}/summarize_robustness.py"
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
    rdl-case-study|rdl_case_study)
        cat >&2 <<'EOF'
[deprecated] rdl-case-study referred to the v1 demo (hand-written SOMTParser
adapter + 6 sanity tests). Those files now live under
case_studies/rdl_prototyping/_archive/v1_demo/ and are no longer wired into
the build or the harness, so the LLM trial in v2 cannot accidentally see
them.

Use these v2 commands instead:
  ./parser_comparison.sh rdl-prepare-data    # extract + index + dev/test split
  ./parser_comparison.sh rdl-llm-campaign    # run N trials per front-end
  ./parser_comparison.sh rdl-aggregate       # paper tables from results/runs/
  ./parser_comparison.sh rdl-audit           # static fairness audit
EOF
        exit 2
        ;;
    rdl-prepare-data|rdl_prepare_data)
        RDL_DIR="${ROOT}/case_studies/rdl_prototyping"
        echo "[rdl-prepare-data] extract -> index -> dev/test split" >&2
        bash    "${RDL_DIR}/scripts/extract_qf_rdl.sh" "$@"
        python3 "${RDL_DIR}/scripts/build_qf_rdl_index.py"
        python3 "${RDL_DIR}/scripts/split_dev_test.py"
        ;;
    rdl-llm-campaign|rdl_llm_campaign)
        exec python3 "${ROOT}/case_studies/rdl_prototyping/scripts/run_llm_campaign.py" "$@"
        ;;
    rdl-aggregate|rdl_aggregate)
        exec python3 "${ROOT}/case_studies/rdl_prototyping/scripts/aggregate_runs.py" "$@"
        ;;
    rdl-audit|rdl_audit)
        exec python3 "${ROOT}/case_studies/rdl_prototyping/scripts/audit_adapter.py" "$@"
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
