#!/usr/bin/env bash
# Stop tracking third-party trees under external/ while KEEPING local working-tree files.
# Use when large drops were accidentally committed: one commit + push removes them from GitHub's tree;
# your disk copy stays intact (--cached only touches the index).
#
# History: past commits still contain blobs until you rewrite history (git filter-repo / BFG).
#         For most teams, a follow-up "purge" on GitHub + LFS is optional; shrinking history needs filter-repo.
#
# Usage:
#   ./scripts/git_untrack_external_vendored.sh              # dry-run
#   ./scripts/git_untrack_external_vendored.sh --yes        # git rm --cached (local files unchanged)
#   ./scripts/git_untrack_external_vendored.sh --yes --sweep-ignored
#       Also untrack any tracked file under external/ that current .gitignore would ignore.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=1
SWEEP=0
for a in "$@"; do
  case "$a" in
    --yes|-y) DRY=0 ;;
    --sweep-ignored) SWEEP=1 ;;
  esac
done

if ! git -C "$ROOT" rev-parse --git-dir &>/dev/null; then
  echo "error: not a git repository: $ROOT" >&2
  exit 1
fi

TMP="$(mktemp)"
MERGED="$(mktemp)"
cleanup() { rm -f "$TMP" "$MERGED" "${SWEEP_TMP:-}"; }
trap cleanup EXIT

emit_paths() {
  # --- cvc5: keep CMakeLists.txt, cvc5_parser.cpp, run.sh, README.md
  if git -C "$ROOT" ls-files --error-unmatch -- external/cvc5/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/cvc5/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/cvc5/CMakeLists.txt|external/cvc5/cvc5_parser.cpp|external/cvc5/run.sh|external/cvc5/README.md) ;;
        external/cvc5/cvc5-Linux-*|external/cvc5/cvc5-*-static|external/cvc5/cvc5-*-static/*|\
        external/cvc5/cvc5-cvc5-*|external/cvc5/cvc5-cvc5-*/*|\
        external/cvc5/cvc5-install|external/cvc5/cvc5-install/*|\
        external/cvc5/build|external/cvc5/build/*|\
        external/cvc5/*.tar.gz|external/cvc5/*.zip)
          printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- z3: keep Makefile, *.cpp, run.sh, README at root of external/z3/
  if git -C "$ROOT" ls-files --error-unmatch -- external/z3/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/z3/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/z3/Makefile|external/z3/*.cpp|external/z3/run.sh|external/z3/README.md|external/z3/CMakeLists.txt) ;;
        external/z3/z3-*|external/z3/*.tar.gz|external/z3/*.zip)
          printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- smt-switch: keep wrapper tree; drop build, tarball, upstream unpack except patch CMakeLists
  if git -C "$ROOT" ls-files --error-unmatch -- external/smt-switch/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/smt-switch/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/smt-switch/smt-switch-1.0.6/CMakeLists.txt|external/smt-switch/smt-switch-1.0.6/cvc5/CMakeLists.txt) ;;
        external/smt-switch/build|external/smt-switch/build/*|\
        external/smt-switch/smt-switch-1.0.6/*|\
        external/smt-switch/src/cvc5|external/smt-switch/src/cvc5/*|\
        external/smt-switch/src/*.zip|\
        external/smt-switch/*.tar.gz|external/smt-switch/*.zip|external/smt-switch/*.tgz)
          printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- jsmtlib
  if git -C "$ROOT" ls-files --error-unmatch -- external/jsmtlib/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/jsmtlib/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/jsmtlib/jSMTLIB-*|external/jsmtlib/jSMTLIB-*/*|external/jsmtlib/*.zip)
          printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- haskell: keep run.sh, build.sh
  if git -C "$ROOT" ls-files --error-unmatch -- external/haskell-0.0.2/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/haskell-0.0.2/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/haskell-0.0.2/run.sh|external/haskell-0.0.2/build.sh) ;;
        *) printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- prolog: keep run.sh
  if git -C "$ROOT" ls-files --error-unmatch -- external/prolog-smtlib/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/prolog-smtlib/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/prolog-smtlib/run.sh) ;;
        external/prolog-smtlib/prolog|external/prolog-smtlib/prolog/*|\
        external/prolog-smtlib/pack.pl|external/prolog-smtlib/README.md)
          printf '%s\0' "$f" ;;
      esac
    done
  fi

  # --- antlr4
  if git -C "$ROOT" ls-files --error-unmatch -- external/antlr4_parser/ &>/dev/null; then
    git -C "$ROOT" ls-files -z -- external/antlr4_parser/ | while IFS= read -r -d '' f; do
      case "$f" in
        external/antlr4_parser/gen|external/antlr4_parser/gen/*|\
        external/antlr4_parser/smtlibv2-grammar|external/antlr4_parser/smtlibv2-grammar/*|\
        external/antlr4_parser/*.jar|external/antlr4_parser/*.zip)
          printf '%s\0' "$f" ;;
      esac
    done
  fi
}

emit_paths | sort -zu >"$TMP"

SWEEP_TMP=""
if [[ "$SWEEP" -eq 1 ]]; then
  SWEEP_TMP="$(mktemp)"
  trap 'rm -f "$TMP" "$MERGED" "$SWEEP_TMP"' EXIT
  git -C "$ROOT" ls-files -z -- external/ | while IFS= read -r -d '' f; do
    git -C "$ROOT" check-ignore -q -- "$f" 2>/dev/null && printf '%s\0' "$f" || true
  done >"$SWEEP_TMP"
  sort -zu "$TMP" "$SWEEP_TMP" -o "$MERGED"
  mv "$MERGED" "$TMP"
fi

n=0
while IFS= read -r -d '' _; do
  n=$((n + 1))
done <"$TMP" || true

if [[ "$n" -eq 0 ]]; then
  echo "Nothing to untrack (index already clean for these patterns)."
  exit 0
fi

echo "Paths to remove from Git index only (working tree unchanged): $n file(s)"
if [[ "$DRY" -eq 1 ]]; then
  tr '\0' '\n' <"$TMP" | head -n 200
  if [[ "$n" -gt 200 ]]; then
    echo "... ($((n - 200)) more; truncated)"
  fi
  echo ""
  echo "Dry-run. Re-run with: $0 --yes${SWEEP:+ --sweep-ignored}"
  echo "Then: git status && git commit -m \"chore: stop tracking external vendor drops\" && git push"
  echo "Optional deep clean of remote history: https://github.com/newren/git-filter-repo"
  exit 0
fi

xargs -0 -r git -C "$ROOT" rm --cached --ignore-unmatch -- <"$TMP"
echo ""
echo "Done. Local files are still on disk. Review and commit:"
echo "  git status"
echo "  git commit -m \"chore: stop tracking external vendor drops\""
echo "  git push"
