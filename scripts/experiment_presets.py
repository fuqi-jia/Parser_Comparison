#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Named parameter bundles for long benchmark runs (e.g. SAT/SMT-COMP-scale artifacts).

These keys mirror the **common experiment settings** (time, memory, parallelism)
used across compare / round-trip / parse-vs-solve drivers — see README §1.

Usage: pass ``--preset NAME`` (alias ``--param NAME``) on any script that registers
the preset hook (currently ``run_parser_benchmark.py``, ``run_roundtrip_benchmark.py``,
``run_parse_vs_solve_benchmark.py``, ``run_native_z3_dual_path_benchmark.py``).
Explicit CLI flags always win over preset values.
"""
from __future__ import print_function

import argparse
import json
import sys

PRESETS = {
    "ase2026": {
        "_doc": (
            "Paper-style settings: 30 s per-instance parse cap, 4 GiB RLIMIT_AS, 32 workers "
            "for multi-parser benchmark + same-engine roundtrip (see run_parser_benchmark / "
            "run_roundtrip_benchmark). Z3 parse-vs-solve does NOT use that 30 s parse cap; it "
            "uses memory_mb + jobs from here, solve_timeout_ms inside Z3, and wall_timeout as "
            "the outer subprocess cap (must exceed solve budget; 720 s default for 600 s solve). "
            "dual_path_outer_sec caps the whole native_z3_dual_path child (two Z3 checks + dump)."
        ),
        # Shared across multi-parser benchmark + roundtrip (parse / roundtrip_tool)
        "timeout": 30,
        "memory_mb": 4096,
        "jobs": 32,
        # parse_vs_solve only (ignored by benchmark / roundtrip). Outer wall must allow solve.
        "solve_timeout_ms": 600000,
        "wall_timeout": 720,
        # native_z3_dual_path: subprocess wall (two solver.check + native dump; default >= 2× solve)
        "dual_path_outer_sec": 1500,
    },
}


def add_preset_arguments(parser):
    parser.add_argument(
        "--preset",
        "--param",
        dest="preset",
        metavar="NAME",
        default=None,
        help="Named parameter bundle (e.g. ase2026). See scripts/experiment_presets.py.",
    )


def require_known_preset(name):
    if name is None:
        return
    if name not in PRESETS:
        keys = ", ".join(sorted(PRESETS))
        print("error: unknown preset {!r}; known: {}".format(name, keys), file=sys.stderr)
        raise SystemExit(2)


def pick(name, key, cli_value, script_fallback):
    """Explicit CLI wins; then preset; then per-script fallback."""
    if cli_value is not None:
        return cli_value
    if name and name in PRESETS and key in PRESETS[name]:
        return PRESETS[name][key]
    return script_fallback


def main():
    ap = argparse.ArgumentParser(description="List or show experiment presets")
    ap.add_argument("action", nargs="?", default="list", choices=["list", "show"])
    ap.add_argument("name", nargs="?", default=None)
    args = ap.parse_args()
    if args.action == "list":
        for k in sorted(PRESETS):
            doc = PRESETS[k].get("_doc", "")
            print("{} — {}".format(k, doc))
        return 0
    if args.action == "show":
        if not args.name or args.name not in PRESETS:
            print("usage: experiment_presets.py show NAME", file=sys.stderr)
            return 1
        cfg = {a: b for a, b in PRESETS[args.name].items() if not a.startswith("_")}
        print(json.dumps(cfg, indent=2, sort_keys=True))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
