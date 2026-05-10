#!/usr/bin/env python3
"""Lightweight SLOC counter used by the case-study scoring pipeline.

We avoid taking a hard dependency on cloc (it is not always installed);
instead we ship a small heuristic that strips C/C++/Python/shell line and
block comments and counts non-blank lines. This is good enough for
back-of-the-envelope adapter-vs-backend size comparisons, and we document
the heuristic explicitly in case_study_notes.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable


CXX_LIKE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
PY_EXTS = {".py"}
SH_EXTS = {".sh"}
COUNTED_EXTS = CXX_LIKE_EXTS | PY_EXTS | SH_EXTS | {".cmake", ""} | {".CMakeLists.txt"}


def _is_counted(path: str) -> bool:
    base = os.path.basename(path)
    if base == "CMakeLists.txt":
        return True
    _, ext = os.path.splitext(base)
    return ext in (CXX_LIKE_EXTS | PY_EXTS | SH_EXTS | {".cmake"})


def _strip_cxx_comments(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    in_block = False
    in_line = False
    in_string = False
    string_quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_block:
            if c == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
            if c == "\n":
                out.append(c)
            i += 1
            continue
        if in_line:
            if c == "\n":
                in_line = False
                out.append(c)
            i += 1
            continue
        if in_string:
            out.append(c)
            if c == "\\" and nxt:
                out.append(nxt)
                i += 2
                continue
            if c == string_quote:
                in_string = False
            i += 1
            continue
        if c == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        if c == "/" and nxt == "/":
            in_line = True
            i += 2
            continue
        if c == '"' or c == "'":
            in_string = True
            string_quote = c
            out.append(c)
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _strip_hash_comments(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        out_lines.append(line.split("#", 1)[0] if " #" in line else line)
    return "\n".join(out_lines)


def _count_nonblank(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def count_file(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0
    base = os.path.basename(path)
    _, ext = os.path.splitext(base)
    if ext in CXX_LIKE_EXTS:
        text = _strip_cxx_comments(text)
    elif ext in PY_EXTS or ext in SH_EXTS or ext == ".cmake" or base == "CMakeLists.txt":
        text = _strip_hash_comments(text)
    return _count_nonblank(text)


def walk(paths: Iterable[str]) -> list[str]:
    out = []
    for p in paths:
        if os.path.isfile(p):
            if _is_counted(p):
                out.append(p)
            continue
        if not os.path.isdir(p):
            continue
        for root, _dirs, files in os.walk(p):
            for fn in files:
                full = os.path.join(root, fn)
                if _is_counted(full):
                    out.append(full)
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Count SLOC for the case study.")
    ap.add_argument("paths", nargs="+", help="Files or directories to count.")
    ap.add_argument("--per-file", action="store_true", help="Print a line per file as well as a total.")
    args = ap.parse_args(argv)

    total = 0
    for f in walk(args.paths):
        c = count_file(f)
        if args.per_file:
            print(f"{c}\t{f}")
        total += c
    print(total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
