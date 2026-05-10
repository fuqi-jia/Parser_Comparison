#!/usr/bin/env python3
"""Shared RDL backend for the front-end-prototyping case study.

The backend is intentionally tiny and self-contained so that every adapter is
compared against exactly the same RDL semantics and the same negative-cycle
implementation. Adapters MUST NOT invoke any built-in SMT solver; they only
produce ``rdl_atoms.json`` files conforming to ``schema/rdl_atoms.schema.json``.

Fragment supported in v1 (P0):

  * Conjunction-only QF_RDL.
  * Difference constraints ``x - y (op) c`` with ``op in {<, <=, >, >=, =}``.
  * Unary bounds ``x (op) c`` modelled with a special ``ZERO`` node.
  * Strict inequalities are tracked symbolically as ``(value, strict)`` pairs;
    no epsilon trick is used.

A constraint of the form ``lhs - rhs <= bound`` (or ``<``) is encoded as a
weighted directed edge ``rhs -> lhs`` with weight ``(bound, strict)``. The
formula is unsat iff the resulting graph contains a negative cycle, where a
cycle's accumulated weight ``(value, strict)`` is "negative" iff
``value < 0`` or (``value == 0`` and ``strict``).

Implementation note. With symbolic strict bounds, ``(0, True)`` is an additive
fixed point: ``(0, True) + (0, True) == (0, True)``. Bellman-Ford's relaxation
rule "relax until no edge improves" therefore fails to expose strict-zero
cycles (the distance simply stops decreasing). We use Floyd-Warshall instead,
which after termination yields ``dist[v][v]`` equal to the minimum bound of
any cycle through ``v``; we report ``unsat`` iff some such cycle is
``< (0, False)``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True)
class Bound:
    """Symbolic strict bound represented as ``(value, strict)``."""

    value: Fraction
    strict: bool

    def __add__(self, other: "Bound") -> "Bound":
        return Bound(self.value + other.value, self.strict or other.strict)

    def __lt__(self, other: "Bound") -> bool:
        if self.value != other.value:
            return self.value < other.value
        return self.strict and not other.strict

    def __le__(self, other: "Bound") -> bool:
        return self == other or self < other

    @property
    def is_negative(self) -> bool:
        # A bound is "negative" in the sense relevant to negative-cycle
        # detection: value < 0, or value == 0 with strict (strictly < 0).
        if self.value < 0:
            return True
        return self.value == 0 and self.strict


ZERO_BOUND = Bound(Fraction(0), False)
# Sentinel used as "no path yet"; chosen large enough that any realistic edge
# weight in a P0 RDL benchmark is smaller, while still being a real Fraction so
# that ``+`` works without special-casing.
INF_BOUND = Bound(Fraction(10**30), False)


def parse_bound_string(text: str) -> Fraction:
    """Parse a numeric literal as written by adapters.

    Accepted forms:
      * decimal integers and signed integers: ``3``, ``-2``
      * decimal fractions: ``3.5``, ``-0.25``
      * rationals: ``7/2``, ``-7/2``

    Adapters are expected to normalise SMT-LIB-specific shapes such as
    ``(- 5)`` and ``(/ 7 2)`` before serialising. We still defensively accept
    the most common subset.
    """

    s = text.strip()
    if not s:
        raise ValueError("empty numeric literal")
    # Fraction handles "3", "-2", "7/2" and "3.5" via the ``Fraction(str)`` ctor.
    return Fraction(s)


def load_rdl_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def collect_edges(payload: dict) -> tuple[list[str], list[tuple[str, str, Bound, str]]]:
    """Return ``(variables, edges)``.

    ``edges`` is a list of ``(src, dst, weight, source_string)`` tuples, where
    ``src -> dst`` carries weight ``weight`` and corresponds to the constraint
    ``dst - src (op) value``.
    """

    variables: list[str] = list(payload.get("variables") or [])
    var_set = set(variables)
    edges: list[tuple[str, str, Bound, str]] = []

    for raw in payload.get("constraints") or []:
        lhs = raw["lhs"]
        rhs = raw["rhs"]
        bound = parse_bound_string(str(raw["bound"]))
        strict = bool(raw["strict"])
        source = str(raw.get("source", ""))
        for v in (lhs, rhs):
            if v not in var_set:
                variables.append(v)
                var_set.add(v)
        edges.append((rhs, lhs, Bound(bound, strict), source))

    if "ZERO" not in var_set:
        # Always present; harmless if no unary bound used it.
        variables.append("ZERO")

    return variables, edges


def floyd_warshall_has_negative_cycle(
    variables: Iterable[str],
    edges: list[tuple[str, str, Bound, str]],
) -> bool:
    """Detect a negative cycle via all-pairs shortest paths.

    After Floyd-Warshall finishes, ``dist[v][v]`` is the minimum bound of any
    cycle through ``v`` (or the initial ``ZERO_BOUND`` if no shorter cycle was
    found). The formula is unsat iff some such cycle is strictly less than
    ``(0, False)`` under the lex bound ordering.
    """

    verts = list(variables)
    if not verts:
        return False

    idx = {v: i for i, v in enumerate(verts)}
    n = len(verts)

    dist = [[INF_BOUND] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = ZERO_BOUND
    for src, dst, w, _src_str in edges:
        i, j = idx[src], idx[dst]
        if w < dist[i][j]:
            dist[i][j] = w

    for k in range(n):
        dk = dist[k]
        for i in range(n):
            dik = dist[i][k]
            if dik == INF_BOUND:
                continue
            di = dist[i]
            for j in range(n):
                dkj = dk[j]
                if dkj == INF_BOUND:
                    continue
                cand = dik + dkj
                if cand < di[j]:
                    di[j] = cand

    for i in range(n):
        if dist[i][i] < ZERO_BOUND:
            return True
    return False


def decide(payload: dict) -> str:
    status = payload.get("status")
    if status == "unsupported":
        print(
            f"backend: unsupported input ({payload.get('reason', 'no reason given')})",
            file=sys.stderr,
        )
        return "unknown"
    if status == "error":
        print(
            f"backend: adapter error ({payload.get('reason', 'no reason given')})",
            file=sys.stderr,
        )
        return "unknown"
    if status != "ok":
        print(f"backend: unknown status field: {status!r}", file=sys.stderr)
        return "unknown"

    mode = payload.get("mode", "conjunction")
    if mode != "conjunction":
        print(
            f"backend: mode={mode!r} is not implemented in v1; only 'conjunction' is supported",
            file=sys.stderr,
        )
        return "unknown"

    variables, edges = collect_edges(payload)
    if not edges:
        return "sat"

    return "unsat" if floyd_warshall_has_negative_cycle(variables, edges) else "sat"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Shared RDL backend (P0 conjunction-only).")
    p.add_argument("rdl_atoms_json", help="Path to rdl_atoms.json")
    args = p.parse_args(argv)

    try:
        payload = load_rdl_json(args.rdl_atoms_json)
    except FileNotFoundError:
        print(f"backend: file not found: {args.rdl_atoms_json}", file=sys.stderr)
        print("unknown")
        return 1
    except json.JSONDecodeError as exc:
        print(f"backend: malformed json: {exc}", file=sys.stderr)
        print("unknown")
        return 1

    try:
        verdict = decide(payload)
    except (KeyError, ValueError, TypeError) as exc:
        print(f"backend: payload error: {exc}", file=sys.stderr)
        print("unknown")
        return 1

    print(verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
