#!/usr/bin/env bash
# Single entry point for the RDL prototyping case study.
#
#   1. Configures and builds case_studies/rdl_prototyping/adapters/somtparser
#      under build_rdl/, leaving the main build/ tree untouched.
#   2. Runs all registered adapters and writes
#      case_studies/rdl_prototyping/results/{run_per_test.csv,
#      run_meta.json, run_summary.csv, run_summary.md, table1.tex}.
#
# Existing parser_comparison.sh commands (benchmark, plots, build, …) are
# unaffected -- the case study only enables itself when -DBUILD_RDL_CASE_STUDY=ON
# is passed to CMake, which we do here in a separate build directory.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASE_DIR="$(cd "${HERE}/.." && pwd)"
REPO_ROOT="$(cd "${CASE_DIR}/../.." && pwd)"

BUILD_DIR="${REPO_ROOT}/build_rdl"
RESULTS_DIR="${CASE_DIR}/results"
ADAPTER_BIN="${BUILD_DIR}/case_studies/rdl_prototyping/adapters/somtparser/somt-rdl-adapter"

PYTHON="${PYTHON:-python3}"

echo "== rdl_prototyping reproduce =="
echo "REPO_ROOT     = ${REPO_ROOT}"
echo "BUILD_DIR     = ${BUILD_DIR}"
echo "RESULTS_DIR   = ${RESULTS_DIR}"
echo "PYTHON        = ${PYTHON}"

mkdir -p "${BUILD_DIR}" "${RESULTS_DIR}"

cd "${REPO_ROOT}"
echo
echo "-- Configuring (cmake -DBUILD_RDL_CASE_STUDY=ON) --"
cmake -S "${REPO_ROOT}" -B "${BUILD_DIR}" -DBUILD_RDL_CASE_STUDY=ON >/dev/null

echo "-- Building somt-rdl-adapter --"
cmake --build "${BUILD_DIR}" --target somt-rdl-adapter -j "$(nproc 2>/dev/null || echo 4)"

if [[ ! -x "${ADAPTER_BIN}" ]]; then
    echo "error: adapter binary missing: ${ADAPTER_BIN}" >&2
    exit 1
fi

echo
echo "-- Running all adapters --"
"${PYTHON}" "${HERE}/run_all_adapters.py" --repo-root "${REPO_ROOT}" --out-dir "${RESULTS_DIR}"

echo
echo "-- Generated outputs --"
ls -1 "${RESULTS_DIR}"

echo
echo "Done. See ${RESULTS_DIR}/run_summary.md for a human-readable summary"
echo "and ${RESULTS_DIR}/table1.tex for the LaTeX table."
