#!/usr/bin/env python3
"""Build a CSV index of every QF_RDL .smt2 file under data/qf_rdl_raw/.

Columns:
  family      first directory under qf_rdl_raw/ (e.g. sal, scheduling)
  relpath     path relative to qf_rdl_raw/
  bytes       file size on disk
  n_asserts   approximate assertion count (count of "(assert ")
  status      sat | unsat | unknown | unlabeled
  oversize    1 if bytes >= --oversize-bytes else 0

Output: case_studies/rdl_prototyping/data/qf_rdl_index.csv (overwrites).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RAW = CASE_DIR / "data" / "qf_rdl_raw"
DEFAULT_OUT = CASE_DIR / "data" / "qf_rdl_index.csv"

# Tolerant of whitespace, comments inside set-info, and trailing close-paren.
STATUS_RE = re.compile(
    r"\(\s*set-info\s+:status\s+(sat|unsat|unknown)\s*\)",
    re.IGNORECASE,
)
ASSERT_RE = re.compile(r"\(\s*assert\s")


def parse_one(path: Path, raw_root: Path, oversize_bytes: int) -> dict:
    rel = path.relative_to(raw_root)
    family = rel.parts[0] if len(rel.parts) > 1 else "_root"
    size = path.stat().st_size
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: cannot read {path}: {e}", file=sys.stderr)
        text = ""
    m = STATUS_RE.search(text)
    status = m.group(1).lower() if m else "unlabeled"
    n_asserts = len(ASSERT_RE.findall(text))
    return {
        "family": family,
        "relpath": rel.as_posix(),
        "bytes": size,
        "n_asserts": n_asserts,
        "status": status,
        "oversize": 1 if size >= oversize_bytes else 0,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=DEFAULT_RAW,
                    help=f"directory of extracted *.smt2 (default: {DEFAULT_RAW})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"output CSV (default: {DEFAULT_OUT})")
    ap.add_argument("--oversize-bytes", type=int, default=256 * 1024,
                    help="files >= this size are flagged oversize (default 256 KiB)")
    args = ap.parse_args(argv)

    if not args.raw.is_dir():
        print(f"ERROR: raw dir {args.raw} not found. Run extract_qf_rdl.sh first.", file=sys.stderr)
        return 1

    rows = []
    for p in sorted(args.raw.rglob("*.smt2")):
        rows.append(parse_one(p, args.raw, args.oversize_bytes))

    if not rows:
        print(f"ERROR: no *.smt2 found under {args.raw}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["family", "relpath", "bytes", "n_asserts", "status", "oversize"]
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Summary to stderr.
    fams: dict[str, dict[str, int]] = {}
    over = 0
    for r in rows:
        fams.setdefault(r["family"], {}).setdefault(r["status"], 0)
        fams[r["family"]][r["status"]] += 1
        over += r["oversize"]
    print(f"[index] wrote {args.out} ({len(rows)} files)", file=sys.stderr)
    for fam in sorted(fams):
        parts = ", ".join(f"{k}={v}" for k, v in sorted(fams[fam].items()))
        print(f"  {fam:>40s}: {parts}", file=sys.stderr)
    print(f"  oversize (>= {args.oversize_bytes} bytes): {over}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
