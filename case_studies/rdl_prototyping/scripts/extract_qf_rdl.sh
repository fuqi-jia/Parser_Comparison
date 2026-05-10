#!/usr/bin/env bash
# Extract benchmark/QF_RDL.tar.zst into
# case_studies/rdl_prototyping/data/qf_rdl_raw/<family>/*.smt2.
#
# Idempotent: if a sentinel file with the matching tar size already exists,
# the extraction is skipped. Override with --force.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TAR="${ROOT}/benchmark/QF_RDL.tar.zst"
OUT="${ROOT}/case_studies/rdl_prototyping/data/qf_rdl_raw"
SENTINEL="${OUT}/.extracted_from"

FORCE=0
for arg in "$@"; do
    case "$arg" in
        --force) FORCE=1 ;;
        -h|--help)
            sed -n '2,5p' "$0"
            exit 0
            ;;
        *)
            echo "unknown arg: $arg" >&2
            exit 2
            ;;
    esac
done

if [[ ! -f "${TAR}" ]]; then
    echo "ERROR: ${TAR} not found. Run ./parser_comparison.sh download first." >&2
    exit 1
fi

TAR_SIZE=$(stat -c%s "${TAR}" 2>/dev/null || stat -f%z "${TAR}")
TAR_FP="${TAR}@${TAR_SIZE}"

if [[ -f "${SENTINEL}" ]] && [[ "$(cat "${SENTINEL}")" == "${TAR_FP}" ]] && [[ "${FORCE}" -eq 0 ]]; then
    echo "[extract_qf_rdl] already extracted from ${TAR_FP}; skipping (use --force to redo)."
    exit 0
fi

mkdir -p "${OUT}"
if [[ "${FORCE}" -eq 1 ]]; then
    echo "[extract_qf_rdl] --force: wiping ${OUT}"
    find "${OUT}" -mindepth 1 -delete
fi

echo "[extract_qf_rdl] extracting ${TAR} -> ${OUT}"
# strip non-incremental/QF_RDL/ prefix so we get <family>/*.smt2 directly.
tar --use-compress-program=zstd -xf "${TAR}" -C "${OUT}" --strip-components=2

N=$(find "${OUT}" -name '*.smt2' | wc -l)
echo "[extract_qf_rdl] extracted ${N} files into ${OUT}"
echo "${TAR_FP}" > "${SENTINEL}"
