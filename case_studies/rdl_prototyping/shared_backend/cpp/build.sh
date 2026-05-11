#!/usr/bin/env bash
# Build the C++ RDL backend (rdl_backend executable + unit tests).
#
# Usage:
#   bash build.sh [Debug|Release]
#
# Output:
#   build/rdl_backend       — CLI binary used by the trial harness
#   build/unit_bound        — unit test for Bound arithmetic
#   build/unit_solver       — unit test for Floyd-Warshall decision
#
# Re-running is idempotent; CMake reconfigures only when needed.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_TYPE="${1:-Release}"

cmake -S "$HERE" -B "$HERE/build" \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -G "Unix Makefiles"

cmake --build "$HERE/build" -j

echo
echo "[build.sh] running unit tests..."
ctest --test-dir "$HERE/build" --output-on-failure

echo
echo "[build.sh] binary at: $HERE/build/rdl_backend"
