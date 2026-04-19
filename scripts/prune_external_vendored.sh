#!/usr/bin/env bash
# Remove third-party trees under external/ that must not be copied to GitHub as full drops.
# Keeps wrapper Makefiles/CMakeLists.txt, driver sources, and READMEs; re-fetch with ./parser_comparison.sh prepare.
#
# Usage:
#   ./scripts/prune_external_vendored.sh          # dry-run (print only)
#   ./scripts/prune_external_vendored.sh --yes    # actually delete

set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL="$ROOT/external"
DRY=1
if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
  DRY=0
fi

rm_rf() {
  local p="$1"
  if [[ -e "$p" ]]; then
    if [[ "$DRY" -eq 1 ]]; then
      echo "[dry-run] rm -rf $p"
    else
      echo "[remove] $p"
      rm -rf "$p"
    fi
  fi
}

echo "Repository: $ROOT (dry-run=$DRY)"

# cvc5: prebuilt drops, full source unpack, local build, archives
for pat in \
  "$EXTERNAL/cvc5"/cvc5-Linux-* \
  "$EXTERNAL/cvc5"/cvc5-*-static \
  "$EXTERNAL/cvc5"/cvc5-cvc5-* \
  "$EXTERNAL/cvc5"/cvc5-install \
  "$EXTERNAL/cvc5/build"; do
  for p in $pat; do
    [[ -e "$p" ]] || continue
    rm_rf "$p"
  done
done
for f in "$EXTERNAL/cvc5"/*.tar.gz "$EXTERNAL/cvc5"/*.zip; do
  [[ -f "$f" ]] || continue
  rm_rf "$f"
done

# z3: released source/binary trees (not our Makefile / *.cpp)
if [[ -d "$EXTERNAL/z3" ]]; then
  while IFS= read -r -d '' p; do
    rm_rf "$p"
  done < <(find "$EXTERNAL/z3" -mindepth 1 -maxdepth 1 -type d -name 'z3-*' -print0 2>/dev/null || true)
  for f in "$EXTERNAL/z3"/*.tar.gz "$EXTERNAL/z3"/*.zip; do
    [[ -f "$f" ]] || continue
    rm_rf "$f"
  done
fi

# smt-switch: upstream tarball tree, build, archives, CVC5_HOME under src/
rm_rf "$EXTERNAL/smt-switch/build"
rm_rf "$EXTERNAL/smt-switch/src/cvc5"
for f in "$EXTERNAL/smt-switch/src"/*.zip; do
  [[ -f "$f" ]] || continue
  rm_rf "$f"
done
rm_rf "$EXTERNAL/smt-switch/smt-switch-1.0.6"
for f in "$EXTERNAL/smt-switch"/*.tar.gz "$EXTERNAL/smt-switch"/*.zip "$EXTERNAL/smt-switch"/*.tgz; do
  [[ -f "$f" ]] || continue
  rm_rf "$f"
done

# jSMTLIB: downloaded SDK
rm_rf "$EXTERNAL/jsmtlib/jSMTLIB-0.9.10.1"
for f in "$EXTERNAL/jsmtlib"/*.zip; do
  [[ -f "$f" ]] || continue
  rm_rf "$f"
done

# haskell / prolog: fetched content (keep run.sh / build.sh via parent dir)
if [[ -d "$EXTERNAL/haskell-0.0.2" ]]; then
  find "$EXTERNAL/haskell-0.0.2" -mindepth 1 -maxdepth 1 ! -name 'run.sh' ! -name 'build.sh' -print0 2>/dev/null | while IFS= read -r -d '' p; do
    rm_rf "$p"
  done
fi
rm_rf "$EXTERNAL/prolog-smtlib/prolog"
rm_rf "$EXTERNAL/prolog-smtlib/pack.pl"
rm_rf "$EXTERNAL/prolog-smtlib/README.md"

# antlr4: generated / downloaded (setup.sh repopulates)
if [[ -d "$EXTERNAL/antlr4_parser" ]]; then
  rm_rf "$EXTERNAL/antlr4_parser/gen"
  rm_rf "$EXTERNAL/antlr4_parser/smtlibv2-grammar"
  for f in "$EXTERNAL/antlr4_parser"/*.jar "$EXTERNAL/antlr4_parser"/*.zip; do
    [[ -f "$f" ]] || continue
    rm_rf "$f"
  done
fi

if [[ "$DRY" -eq 1 ]]; then
  echo ""
  echo "Dry-run only. Re-run with --yes to delete. Restore deps with: ./parser_comparison.sh prepare"
else
  echo ""
  echo "Done. Restore deps with: ./parser_comparison.sh prepare"
fi
echo ""
echo "To drop the same paths from the Git index only (keep local files, clean GitHub on next push):"
echo "  ./scripts/git_untrack_external_vendored.sh"
echo "  ./scripts/git_untrack_external_vendored.sh --yes"
