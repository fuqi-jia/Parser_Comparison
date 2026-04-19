#!/usr/bin/env bash
# One-shot environment prep after cloning: git submodules + external deps + benchmarks.
# Does not compile (use: ./parser_comparison.sh build).
#
# All extra arguments are passed to scripts/download.sh (e.g. --parsers-only, --benchmark-only, --theories …).

set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v git &>/dev/null; then
  echo "error: git is required for submodule init" >&2
  exit 1
fi

if [[ -d "$ROOT/.git" ]] && [[ -f "$ROOT/.gitmodules" ]]; then
  echo "==> git submodule update --init --recursive"
  git submodule update --init --recursive
else
  echo "[skip] not a git checkout or no .gitmodules"
fi

echo "==> download.sh $*"
exec bash "$ROOT/scripts/download.sh" "$@"
