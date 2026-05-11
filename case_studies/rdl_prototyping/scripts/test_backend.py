#!/usr/bin/env python3
"""Three-way self-test: Python backend, C++ backend, and the generator's
``*.expect`` files must agree on all 100 instances under ``data/synth/``.

Usage:

    python3 scripts/test_backend.py
    python3 scripts/test_backend.py --data data/synth --cpp shared_backend/cpp/build/rdl_backend

Exit code:

    0  every instance agreed three-way
    1  at least one disagreement; details printed
    2  setup error (missing binary / dataset)

The script also exercises ``check_rdl_json.py`` on each payload so we
catch JSON schema regressions while we are walking the tree anyway.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent
DEFAULT_DATA = CASE_DIR / "data" / "synth"
DEFAULT_CPP  = CASE_DIR / "shared_backend" / "cpp" / "build" / "rdl_backend"
DEFAULT_PY   = CASE_DIR / "shared_backend" / "rdl_backend.py"
DEFAULT_CHK  = CASE_DIR / "shared_backend" / "check_rdl_json.py"


def run_one(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--cpp",  type=Path, default=DEFAULT_CPP)
    ap.add_argument("--py",   type=Path, default=DEFAULT_PY)
    ap.add_argument("--checker", type=Path, default=DEFAULT_CHK)
    ap.add_argument("--quiet", action="store_true",
                    help="only print PASS/FAIL header and any disagreement rows")
    args = ap.parse_args(argv)

    if not args.cpp.is_file():
        print(f"FATAL: C++ backend binary not found at {args.cpp}.\n"
              f"Build it with: bash {args.cpp.parent.parent}/build.sh", file=sys.stderr)
        return 2
    if not args.py.is_file():
        print(f"FATAL: Python backend not found at {args.py}", file=sys.stderr)
        return 2
    if not args.data.is_dir():
        print(f"FATAL: synth dataset not found at {args.data}.\n"
              f"Generate it with: python3 scripts/gen_synth_rdl.py --force", file=sys.stderr)
        return 2

    payloads = sorted(args.data.glob("*.rdl_atoms.json"))
    if not payloads:
        print(f"FATAL: no *.rdl_atoms.json under {args.data}", file=sys.stderr)
        return 2

    fail_rows: list[dict] = []
    schema_failed: list[str] = []
    n_sat = n_unsat = 0
    for payload in payloads:
        name = payload.name.removesuffix(".rdl_atoms.json")
        expect_path = args.data / f"{name}.expect"
        if not expect_path.is_file():
            fail_rows.append({"name": name, "stage": "missing-expect"})
            continue
        expect = expect_path.read_text(encoding="utf-8").strip()

        # 1. JSON schema sanity (separate process to mirror harness usage)
        rc, _, err = run_one([sys.executable, str(args.checker), str(payload)])
        if rc != 0:
            schema_failed.append(f"{name}: {err}")
            fail_rows.append({"name": name, "stage": "schema",
                              "expect": expect, "py": None, "cpp": None})
            continue

        # 2. Python backend
        rc_py, py_out, py_err = run_one([sys.executable, str(args.py), str(payload)])
        py_verdict = py_out.splitlines()[-1] if py_out else ""

        # 3. C++ backend
        rc_cpp, cpp_out, cpp_err = run_one([str(args.cpp), str(payload)])
        cpp_verdict = cpp_out.splitlines()[-1] if cpp_out else ""

        if expect == "sat":
            n_sat += 1
        elif expect == "unsat":
            n_unsat += 1

        if py_verdict != expect or cpp_verdict != expect or py_verdict != cpp_verdict:
            fail_rows.append({
                "name": name, "stage": "verdict",
                "expect": expect, "py": py_verdict, "cpp": cpp_verdict,
                "py_err": py_err, "cpp_err": cpp_err,
            })
        elif not args.quiet:
            print(f"  OK  {name:<14} expect={expect}  py={py_verdict}  cpp={cpp_verdict}")

    n_total = len(payloads)
    n_fail = len(fail_rows)
    print()
    print("=" * 64)
    print(f"three-way self-test summary: {n_total - n_fail}/{n_total} passed "
          f"(sat={n_sat}, unsat={n_unsat})")
    if fail_rows:
        print(f"  {n_fail} disagreement(s):")
        for r in fail_rows:
            if r["stage"] == "verdict":
                print(f"    {r['name']:<14} expect={r['expect']:<5} py={r['py']:<7} cpp={r['cpp']:<7}")
                if r.get("py_err"):  print(f"      py.err: {r['py_err']}")
                if r.get("cpp_err"): print(f"      cpp.err: {r['cpp_err']}")
            else:
                print(f"    {r['name']:<14} stage={r['stage']}")
        return 1
    if schema_failed:
        for s in schema_failed:
            print(f"  schema-FAIL: {s}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
