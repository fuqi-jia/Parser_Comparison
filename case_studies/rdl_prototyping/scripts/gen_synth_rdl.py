#!/usr/bin/env python3
"""Generate 100 synthetic conjunction-only QF_RDL instances with ground truth.

Each instance is dropped under ``data/synth/<name>.smt2`` together with:

  data/synth/<name>.smt2              standard SMT-LIB v2.6 file
  data/synth/<name>.rdl_atoms.json    normalised payload the backend consumes
  data/synth/<name>.expect            single-line "sat" / "unsat"

plus a top-level ``data/synth/synth_index.csv`` listing them in the same
shape as ``data/test_index.csv`` so the harness scoring script can reuse
the existing scan.

Design choices:

* **Fixed seed (2025).** Deterministic across runs; reviewers can re-run.
* **Two construction modes.**
    - ``sat`` instances are built from a concrete realisation
      ``x_i := v_i`` (random rationals); every emitted constraint
      ``x_lhs - x_rhs op c`` is required to hold on that realisation,
      guaranteeing satisfiability.
    - ``unsat`` instances inject a negative cycle into an otherwise
      consistent set: e.g. ``x_a - x_b <= b1``, ``x_b - x_c <= b2``,
      ``x_c - x_a <= b3`` with ``b1+b2+b3 < 0``. The remaining
      constraints are sampled like the sat case but on slightly perturbed
      variables so they are also consistent.
* **Size buckets.** 5 buckets (tiny / small / medium / large / edge),
  20+25+25+20+10 = 100 instances; sat/unsat split is roughly half-half
  per bucket. See `BUCKETS` below.
* **No reliance on any solver.** Generation is by construction; the
  expected verdict is determined before any backend is consulted. The
  self-test script (``test_backend.py``) is what then verifies the two
  backends agree with these labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent
DEFAULT_OUT = CASE_DIR / "data" / "synth"

# (bucket, n_total, n_vars_range, n_extra_constraints_range)
BUCKETS = [
    ("tiny",   20, (2, 4),   (0, 2)),
    ("small",  25, (4, 8),   (2, 6)),
    ("medium", 25, (8, 15),  (4, 12)),
    ("large",  20, (15, 25), (10, 20)),
    ("edge",   10, (3, 6),   (1, 4)),   # mix of strict, rationals, ZERO
]

OP_LE = ("<=", False)   # non-strict
OP_LT = ("<",  True)    # strict


@dataclass
class Constraint:
    lhs: str
    rhs: str
    bound: Fraction
    strict: bool   # True ⇔ "lhs - rhs < bound"
    source_str: str

    def as_smt(self) -> str:
        op = "<" if self.strict else "<="
        return f"({op} (- {self.lhs} {self.rhs}) {format_rational(self.bound)})"

    def as_atom_json(self) -> dict:
        return {
            "lhs": self.lhs,
            "rhs": self.rhs,
            "bound": format_rational(self.bound),
            "strict": self.strict,
            "source": self.source_str or self.as_smt(),
        }


def format_rational(q: Fraction) -> str:
    if q.denominator == 1:
        return str(q.numerator)
    return f"{q.numerator}/{q.denominator}"


def random_rational(rng: random.Random,
                    min_val: int = -10, max_val: int = 10,
                    allow_rational: bool = False) -> Fraction:
    if allow_rational and rng.random() < 0.4:
        num = rng.randint(min_val, max_val)
        den = rng.randint(1, 4)
        return Fraction(num, den)
    return Fraction(rng.randint(min_val, max_val))


def random_op(rng: random.Random, allow_strict: bool) -> tuple[str, bool]:
    if allow_strict and rng.random() < 0.25:
        return OP_LT
    return OP_LE


def gen_sat_instance(name: str, rng: random.Random,
                     n_vars: int, n_extra: int,
                     allow_strict: bool = False,
                     allow_rational: bool = False) -> tuple[list[str], list[Constraint]]:
    """Build a satisfiable instance by realising x_i := v_i, then sampling
    constraints that hold on that realisation."""
    variables = [f"x{i}" for i in range(1, n_vars + 1)]
    realisation: dict[str, Fraction] = {
        v: random_rational(rng, -20, 20, allow_rational=allow_rational)
        for v in variables
    }
    realisation["ZERO"] = Fraction(0)
    constraints: list[Constraint] = []

    # one constraint per variable (vs ZERO) so the formula is non-trivial
    for v in variables:
        op, strict = random_op(rng, allow_strict)
        diff = realisation[v] - realisation["ZERO"]
        slack = random_rational(rng, 0, 5, allow_rational=allow_rational)
        bound = diff + slack
        if strict and slack == 0:
            bound = bound + Fraction(1)  # ensure strict <
        constraints.append(Constraint(v, "ZERO", bound, strict, ""))
        if "ZERO" not in variables:
            pass

    # extra random pairwise constraints
    for _ in range(n_extra):
        a, b = rng.sample(variables, 2) if len(variables) >= 2 else (variables[0], variables[0])
        op, strict = random_op(rng, allow_strict)
        diff = realisation[a] - realisation[b]
        slack = random_rational(rng, 0, 5, allow_rational=allow_rational)
        bound = diff + slack
        if strict and slack == 0:
            bound = bound + Fraction(1)
        constraints.append(Constraint(a, b, bound, strict, ""))

    rng.shuffle(constraints)
    return variables, constraints


def gen_unsat_instance(name: str, rng: random.Random,
                       n_vars: int, n_extra: int,
                       allow_strict: bool = False,
                       allow_rational: bool = False) -> tuple[list[str], list[Constraint]]:
    """Build an unsat instance by injecting a negative cycle into an
    otherwise consistent set of constraints."""
    if n_vars < 2:
        n_vars = 2
    variables = [f"x{i}" for i in range(1, n_vars + 1)]
    realisation: dict[str, Fraction] = {
        v: random_rational(rng, -20, 20, allow_rational=allow_rational)
        for v in variables
    }
    realisation["ZERO"] = Fraction(0)
    constraints: list[Constraint] = []

    # pick cycle length 2..min(n_vars,4), pick distinct nodes
    cycle_len = rng.randint(2, min(n_vars, 4))
    nodes = rng.sample(variables, cycle_len)

    # Decide cycle weight: sum strictly < 0 (or sum == 0 with at least
    # one strict edge). Easier: pick each weight uniformly negative-ish
    # but force sum to be definitely negative.
    weights: list[Fraction] = []
    stricts: list[bool] = []
    for _ in range(cycle_len):
        w = random_rational(rng, -3, 3, allow_rational=allow_rational)
        weights.append(w)
        stricts.append(False)
    total = sum(weights, Fraction(0))
    if total >= 0:
        # subtract from the first edge to force negativity
        weights[0] = weights[0] - total - Fraction(1)
    # 25% of the time: make the bound zero-sum but with a strict edge ⇒ unsat
    # ONLY when allow_strict is true; otherwise skip.
    if allow_strict and rng.random() < 0.25:
        weights = [Fraction(0)] * cycle_len
        stricts[0] = True

    for k in range(cycle_len):
        a = nodes[k]
        b = nodes[(k + 1) % cycle_len]
        constraints.append(Constraint(a, b, weights[k], stricts[k], ""))

    # extra random pairwise constraints — sampled so they are consistent
    # with the realisation but NOT touching the negative cycle (so the
    # cycle remains the only unsat reason; the rest of the formula is
    # consistent on the realisation, which keeps the example tame).
    for _ in range(n_extra):
        a, b = rng.sample(variables, 2)
        # avoid touching cycle edges
        if cycle_len >= 2 and {a, b} == {nodes[0], nodes[1]}:
            continue
        op, strict = random_op(rng, allow_strict)
        diff = realisation[a] - realisation[b]
        slack = random_rational(rng, 0, 5, allow_rational=allow_rational)
        bound = diff + slack
        if strict and slack == 0:
            bound = bound + Fraction(1)
        constraints.append(Constraint(a, b, bound, strict, ""))

    rng.shuffle(constraints)
    return variables, constraints


def emit_smt2(out_path: Path, variables: list[str], constraints: list[Constraint],
              info_name: str) -> int:
    body: list[str] = [
        "; Auto-generated by gen_synth_rdl.py; do not hand-edit.",
        f"(set-info :smt-lib-version 2.6)",
        f"(set-info :category \"crafted\")",
        f"(set-info :source |gen_synth_rdl::{info_name}|)",
        "(set-logic QF_RDL)",
    ]
    for v in variables:
        body.append(f"(declare-fun {v} () Real)")
    # one conjunctive assertion
    if constraints:
        and_args = " ".join(c.as_smt() for c in constraints)
        if len(constraints) == 1:
            body.append(f"(assert {constraints[0].as_smt()})")
        else:
            body.append(f"(assert (and {and_args}))")
    body.append("(check-sat)")
    body.append("(exit)")
    text = "\n".join(body) + "\n"
    out_path.write_text(text, encoding="utf-8")
    # n_asserts is always 1 because we collapse into a single `(assert (and ...))`
    return 1


def emit_atoms_json(out_path: Path, variables: list[str], constraints: list[Constraint]) -> None:
    payload = {
        "status": "ok",
        "frontend": "synth_gen",
        "mode": "conjunction",
        "variables": sorted(set(variables) | {"ZERO"}),
        "constraints": [c.as_atom_json() for c in constraints],
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="output directory; default: data/synth/")
    ap.add_argument("--seed", type=int, default=2025)
    ap.add_argument("--force", action="store_true",
                    help="wipe the output directory before regenerating")
    args = ap.parse_args(argv)

    out_dir: Path = args.out
    if args.force and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    rows: list[dict] = []

    instance_idx = 0
    for bucket_name, n_total, vars_range, extra_range in BUCKETS:
        n_unsat = n_total // 2
        n_sat = n_total - n_unsat
        expected_seq = ["sat"] * n_sat + ["unsat"] * n_unsat
        rng.shuffle(expected_seq)
        for k, expect in enumerate(expected_seq):
            instance_idx += 1
            n_vars = rng.randint(*vars_range)
            n_extra = rng.randint(*extra_range)
            allow_strict = (bucket_name == "edge")
            allow_rational = (bucket_name == "edge")
            name = f"{bucket_name}_{k:02d}"
            if expect == "sat":
                variables, cs = gen_sat_instance(name, rng, n_vars, n_extra,
                                                  allow_strict, allow_rational)
            else:
                variables, cs = gen_unsat_instance(name, rng, n_vars, n_extra,
                                                    allow_strict, allow_rational)
            smt_path = out_dir / f"{name}.smt2"
            json_path = out_dir / f"{name}.rdl_atoms.json"
            exp_path = out_dir / f"{name}.expect"
            n_asserts = emit_smt2(smt_path, variables, cs, name)
            emit_atoms_json(json_path, variables, cs)
            exp_path.write_text(expect + "\n", encoding="utf-8")
            rows.append({
                "family":  "synth",
                "relpath": f"{name}.smt2",
                "bytes":   smt_path.stat().st_size,
                "n_asserts": n_asserts,
                "status":  expect,
                "oversize": 0,
                "bucket":  bucket_name,
                "n_vars":  len(variables) + 1,   # + ZERO
                "n_constraints": len(cs),
            })

    index_path = out_dir / "synth_index.csv"
    fieldnames = ["family", "relpath", "bytes", "n_asserts",
                  "status", "oversize", "bucket", "n_vars", "n_constraints"]
    with index_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"[gen_synth_rdl] wrote {len(rows)} instances under {out_dir}", file=sys.stderr)
    by_expect = {"sat": 0, "unsat": 0}
    for r in rows:
        by_expect[r["status"]] += 1
    print(f"[gen_synth_rdl] expected distribution: {by_expect}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
