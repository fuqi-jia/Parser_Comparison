#!/usr/bin/env bash
# Configure and build the repo-root CMake project (smt_parser_comparison, roundtrip_tool, …).
# Usage: from repo root, usually via ./parser_comparison.sh build-internal [args passed to cmake --build]
#
# Environment:
#   BUILD_DIR   Build tree (default: <repo>/build)

set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT/build}"

mkdir -p "$BUILD_DIR"
cmake -S "$ROOT" -B "$BUILD_DIR"

if [[ $# -gt 0 ]]; then
  exec cmake --build "$BUILD_DIR" -- "$@"
else
  exec cmake --build "$BUILD_DIR"
fi
