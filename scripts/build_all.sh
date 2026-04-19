#!/usr/bin/env bash
# Full build: native CMake targets, then all external parser drivers.
# Extra arguments are passed only to the native cmake --build step (see build_native.sh).
# For flags or paths that apply only to external drivers, run build-external separately.
#
# Order: internal first, then external (same as two manual steps in sequence).

set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$ROOT/scripts"

bash "$SCRIPTS/build_native.sh" "$@"
exec bash "$SCRIPTS/build_all_parsers.sh"
