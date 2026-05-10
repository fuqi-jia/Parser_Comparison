#!/usr/bin/env python3
"""Split QF_RDL into stratified dev / test / oversize / unlabeled buckets.

Inputs : data/qf_rdl_index.csv   (built by build_qf_rdl_index.py)
         data/qf_rdl_raw/        (extracted *.smt2 files)

Outputs: data/dev_index.csv         (dev set, ground-truth labelled)
         data/test_index.csv        (final test set, ground-truth labelled)
         data/oversize_index.csv    (excluded: file too big to bundle)
         data/unlabeled_index.csv   (excluded: status=unknown or unlabeled)
         data/dev/<family>/*.smt2   (physical copies; LLM may see these)
         data/test/<family>/*.smt2  (physical copies; LLM must NEVER see these)

Sampling: deterministic stratified sampling over (family, status) cells.
Every cell with >= 1 candidate contributes at least 1 dev example; the rest of
the dev quota is distributed proportionally to cell size with a deterministic
fractional remainder pass. seed=42 unless overridden.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = CASE_DIR / "data" / "qf_rdl_index.csv"
DEFAULT_RAW = CASE_DIR / "data" / "qf_rdl_raw"
DEFAULT_OUTDIR = CASE_DIR / "data"

GROUND_TRUTH_LABELS = {"sat", "unsat"}


def stratified_sample(rows: list[dict], n_dev: int, seed: int) -> tuple[list[dict], list[dict]]:
    """Return (dev_rows, test_rows) by stratified sampling on (family, status)."""
    rng = random.Random(seed)
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        cells[(r["family"], r["status"])].append(r)
    for cell in cells.values():
        cell.sort(key=lambda r: r["relpath"])
        rng.shuffle(cell)

    total = sum(len(c) for c in cells.values())
    if n_dev > total:
        raise SystemExit(f"n_dev={n_dev} exceeds candidate pool size {total}")
    if n_dev <= 0:
        return [], rows[:]

    cell_keys = sorted(cells.keys())
    quotas: dict[tuple[str, str], int] = {k: 0 for k in cell_keys}

    # Pass 1: at least 1 per non-empty cell, capped by cell size and remaining budget.
    remaining = n_dev
    for k in cell_keys:
        if remaining == 0:
            break
        if cells[k]:
            quotas[k] = 1
            remaining -= 1

    # Pass 2: proportional split of remainder by remaining capacity in each cell.
    if remaining > 0:
        capacities = {k: len(cells[k]) - quotas[k] for k in cell_keys}
        cap_total = sum(capacities.values())
        if cap_total == 0:
            # All cells already fully sampled; shouldn't really happen unless n_dev == total.
            pass
        else:
            ideals = {k: remaining * capacities[k] / cap_total for k in cell_keys}
            base = {k: int(math.floor(ideals[k])) for k in cell_keys}
            assigned = sum(base.values())
            leftover = remaining - assigned
            # Rank cells by fractional remainder, ties broken deterministically by key.
            ranked = sorted(
                cell_keys,
                key=lambda k: (-(ideals[k] - base[k]), k),
            )
            for k in ranked:
                if leftover == 0:
                    break
                if base[k] + 1 <= capacities[k]:
                    base[k] += 1
                    leftover -= 1
            for k in cell_keys:
                quotas[k] += base[k]

    # Build dev / test partitions.
    dev_rows: list[dict] = []
    test_rows: list[dict] = []
    for k in cell_keys:
        cell = cells[k]
        q = quotas[k]
        dev_rows.extend(cell[:q])
        test_rows.extend(cell[q:])
    dev_rows.sort(key=lambda r: r["relpath"])
    test_rows.sort(key=lambda r: r["relpath"])
    return dev_rows, test_rows


def write_csv(path: Path, rows: list[dict], extra_header: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["family", "relpath", "bytes", "n_asserts", "status", "oversize"]
    if extra_header:
        fieldnames = fieldnames + extra_header
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def physical_split(rows: list[dict], raw_root: Path, dest_root: Path) -> None:
    if dest_root.exists():
        shutil.rmtree(dest_root)
    dest_root.mkdir(parents=True)
    for r in rows:
        src = raw_root / r["relpath"]
        dst = dest_root / r["relpath"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("--n-dev", type=int, default=30, dest="n_dev")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    if not args.index.is_file():
        print(f"ERROR: index {args.index} not found. Run build_qf_rdl_index.py first.",
              file=sys.stderr)
        return 1
    if not args.raw.is_dir():
        print(f"ERROR: raw dir {args.raw} not found.", file=sys.stderr)
        return 1

    with args.index.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["bytes"] = int(r["bytes"])
        r["n_asserts"] = int(r["n_asserts"])
        r["oversize"] = int(r["oversize"])

    oversize = [r for r in rows if r["oversize"] == 1]
    rest = [r for r in rows if r["oversize"] == 0]
    unlabeled = [r for r in rest if r["status"] not in GROUND_TRUTH_LABELS]
    candidate = [r for r in rest if r["status"] in GROUND_TRUTH_LABELS]

    dev_rows, test_rows = stratified_sample(candidate, args.n_dev, args.seed)

    write_csv(args.outdir / "dev_index.csv", dev_rows)
    write_csv(args.outdir / "test_index.csv", test_rows)
    write_csv(args.outdir / "oversize_index.csv", oversize)
    write_csv(args.outdir / "unlabeled_index.csv", unlabeled)

    physical_split(dev_rows, args.raw, args.outdir / "dev")
    physical_split(test_rows, args.raw, args.outdir / "test")

    print(f"[split] candidate pool : {len(candidate)} files", file=sys.stderr)
    print(f"[split] dev set        : {len(dev_rows)} -> {args.outdir/'dev'}", file=sys.stderr)
    print(f"[split] test set       : {len(test_rows)} -> {args.outdir/'test'}", file=sys.stderr)
    print(f"[split] oversize       : {len(oversize)}", file=sys.stderr)
    print(f"[split] unlabeled      : {len(unlabeled)} (status not in {sorted(GROUND_TRUTH_LABELS)})",
          file=sys.stderr)
    print(f"[split] seed           : {args.seed}", file=sys.stderr)

    # Per-cell breakdown for the dev set so we can sanity-check stratification.
    dev_cells: dict[tuple[str, str], int] = defaultdict(int)
    for r in dev_rows:
        dev_cells[(r["family"], r["status"])] += 1
    print("[split] dev breakdown (family, status -> count):", file=sys.stderr)
    for k in sorted(dev_cells):
        print(f"          {k[0]:>40s} | {k[1]:>6s} | {dev_cells[k]:>3d}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
