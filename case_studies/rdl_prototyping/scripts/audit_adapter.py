#!/usr/bin/env python3
"""Static fairness audit for an LLM-generated RDL adapter.

Inputs : a directory of adapter source (e.g. results/runs/<frontend>/run_NN/src/)
         the front-end name (must be one of the seven recognised slots)

Output : prints a JSON report to stdout and writes audit_report.json next
         to the source dir (in the run dir's audit/ folder if asked).

Pass criterion (exit code 0):
  - no forbidden symbol from the global blacklist appears in any source file,
  - no forbidden symbol from the front-end-specific blacklist appears,
  - no copy of v1 demo source is detected (rough hash overlap).
Else exit code 1.

This is intentionally a pure regex scan — it is cheap, deterministic, and
runs without compiling the adapter. The harness still pairs it with the
build + dev test loop; the audit alone is not sufficient evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Source extensions to scan (do not scan binaries, JSON, or build dirs).
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp",
    ".java", ".kt",
    ".py",
    ".rs",
    ".sh", ".bash",
    ".g4",
}

# Files / dirs ignored when scanning a run's src/ tree (build artifacts).
IGNORE_DIR_NAMES = {"build", "_build", ".cmake", "CMakeFiles", "__pycache__",
                    "target", "out", "dist", "node_modules", ".venv", "venv"}

# Recognised front-end slots.
FRONTENDS = {"somtparser", "z3_cpp", "cvc5_cpp", "smt_switch",
             "pysmt", "antlr4", "jsmtlib"}

# --------------------------------------------------------------------------
# Forbidden symbol catalogue.
# --------------------------------------------------------------------------
# Each entry is a tuple (regex, severity, hint). severity ∈ {"block","warn"}.
# The auditor fails on any "block" hit.
GLOBAL_FORBIDDEN: list[tuple[str, str, str]] = [
    # Network / shelling out to external solvers.
    (r"\b(?:requests|urllib2?|httpx)\b\.", "warn",
     "network calls have no business in an offline RDL adapter"),
    (r"\bsubprocess\.(?:run|Popen|check_output|call)\(",  "warn",
     "shelling out from the adapter is suspicious; the harness pipes the JSON itself"),
    (r"\bRuntime\.getRuntime\(\)\.exec\b",                 "warn",
     "shelling out from a JVM adapter is suspicious"),
    # Note: We deliberately do NOT block bare "check-sat" or "check_sat"
    # tokens here — adapters legitimately need to recognise the SMT-LIB
    # `(check-sat)` command in input files in order to ignore it. The
    # per-front-end rules below catch the real solver entry points
    # (`Z3_solver_check`, `pysmt.shortcuts.is_sat`, `cvc5::Solver::checkSat`,
    # …) which is what fairness actually cares about.
]

PER_FRONTEND_FORBIDDEN: dict[str, list[tuple[str, str, str]]] = {
    "z3_cpp": [
        (r"\bZ3_solver_check\b",                  "block", "Z3 solver entry"),
        (r"\bZ3_solver_check_assumptions\b",      "block", "Z3 solver entry"),
        (r"\bZ3_solver_get_model\b",              "block", "Z3 model API"),
        (r"\bZ3_model_eval\b",                    "block", "Z3 model API"),
        (r"\bZ3_mk_optimize\b",                   "block", "Z3 optimisation"),
        (r"\bZ3_tactic_apply\b",                  "block", "Z3 tactic"),
        (r"\bZ3_simplify\b",                      "block", "Z3 simplifier"),
        (r"\bZ3_eval_smtlib2_string\b",           "block", "Z3 driver loop"),
        (r"\bz3::solver\b",                       "block", "Z3 C++ solver"),
        (r"\bz3::optimize\b",                     "block", "Z3 C++ optimize"),
        (r"\bz3::tactic\b",                       "block", "Z3 C++ tactic"),
        (r"\bz3::model\b",                        "block", "Z3 C++ model"),
    ],
    "cvc5_cpp": [
        (r"\bcvc5::Solver\b",                     "block", "cvc5 solver"),
        (r"\bSolver::checkSat\b",                 "block", "cvc5 checkSat"),
        (r"\bSolver::getValue\b",                 "block", "cvc5 model"),
        (r"\bSolver::getModel\b",                 "block", "cvc5 model"),
        (r"\bSolver::simplify\b",                 "block", "cvc5 simplify"),
        (r"\bcvc5::Optimizer\b",                  "block", "cvc5 optimisation"),
        (r"\bcvc5::theory::arith::idl\b",         "block", "cvc5 IDL solver"),
    ],
    "smt_switch": [
        (r"\bSolver::check_sat\b",                "block", "smt-switch checkSat"),
        (r"\bSolver::check_sat_assuming\b",       "block", "smt-switch checkSat"),
        (r"\bSolver::get_value\b",                "block", "smt-switch model"),
        (r"\bSolver::get_model\b",                "block", "smt-switch model"),
    ],
    "pysmt": [
        (r"\bpysmt\.shortcuts\.Solver\b",         "block", "pySMT solver"),
        (r"\bpysmt\.shortcuts\.is_sat\b",         "block", "pySMT solver"),
        (r"\bpysmt\.shortcuts\.is_unsat\b",       "block", "pySMT solver"),
        (r"\bpysmt\.shortcuts\.get_model\b",      "block", "pySMT model"),
        (r"\bpysmt\.shortcuts\.simplify\b",       "block", "pySMT simplifier"),
        (r"\bfrom\s+pysmt\.solvers\b",            "block", "pySMT solver import"),
        (r"\bSolver\(\s*name\s*=",                "warn",  "pySMT solver constructor"),
    ],
    "somtparser": [
        # SOMTParser exposes a Solver API; the trial only allows Parser.
        (r"\bSolver\b\s*::\s*checkSat\b",         "block", "SOMTParser Solver entry"),
        (r"\bSolver\b\s*::\s*solve\b",            "block", "SOMTParser Solver entry"),
        (r"\bSolverBuilder\b",                    "block", "SOMTParser solver builder"),
        (r"\bOptimizer\b",                        "block", "SOMTParser Optimizer"),
    ],
    "antlr4": [
        # ANTLR has no SMT solver; fail loud on attempted shellouts.
        (r"\b(?:z3|cvc5|cvc4|mathsat|yices)\b",   "block",
         "antlr4 adapter must not depend on a back-end SMT solver"),
    ],
    "jsmtlib": [
        (r"\borg\.smtlib\.solvers\.",             "block", "jSMTLIB back-end shim"),
        (r"\bSMT::checkSat\b",                    "block", "jSMTLIB driver"),
    ],
}

# v1 demo digest set, populated lazily.
def _load_v1_digests(case_dir: Path) -> set[str]:
    archive = case_dir / "_archive" / "v1_demo"
    digests: set[str] = set()
    if not archive.is_dir():
        return digests
    for p in archive.rglob("*"):
        if p.suffix.lower() in SOURCE_EXTENSIONS and p.is_file():
            digests.add(_chunked_digest(p))
    return digests


def _chunked_digest(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def scan_file(path: Path, frontend: str) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [{"file": str(path), "severity": "warn",
                 "rule": "io",
                 "hint": f"cannot read file: {e}"}]
    findings: list[dict] = []
    rules = list(GLOBAL_FORBIDDEN) + PER_FRONTEND_FORBIDDEN.get(frontend, [])
    for pat, sev, hint in rules:
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append({
                "file": str(path),
                "line": line,
                "severity": sev,
                "rule": pat,
                "match": m.group(0),
                "hint": hint,
            })
    return findings


def iter_sources(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in IGNORE_DIR_NAMES for part in p.parts):
            continue
        if p.suffix.lower() in SOURCE_EXTENSIONS:
            yield p


def detect_v1_copy(root: Path, v1_digests: set[str]) -> list[dict]:
    if not v1_digests:
        return []
    findings: list[dict] = []
    for p in iter_sources(root):
        d = _chunked_digest(p)
        if d and d in v1_digests:
            findings.append({
                "file": str(p),
                "severity": "block",
                "rule": "v1_copy",
                "match": d[:16],
                "hint": "byte-identical copy of a file from _archive/v1_demo/",
            })
    return findings


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True,
                    help="adapter source dir to audit")
    ap.add_argument("--frontend", required=True,
                    help=f"front-end name, one of {sorted(FRONTENDS)}")
    ap.add_argument("--report", type=Path, default=None,
                    help="optional path to write the JSON report")
    ap.add_argument("--case-dir", type=Path,
                    default=Path(__file__).resolve().parent.parent,
                    help="case study root (for v1 demo digests)")
    args = ap.parse_args(argv)

    if args.frontend not in FRONTENDS:
        print(f"ERROR: unknown frontend {args.frontend!r}; expected one of "
              f"{sorted(FRONTENDS)}", file=sys.stderr)
        return 2
    if not args.src.is_dir():
        print(f"ERROR: src {args.src} not a directory", file=sys.stderr)
        return 2

    v1_digests = _load_v1_digests(args.case_dir)

    all_findings: list[dict] = []
    files_scanned = 0
    for p in iter_sources(args.src):
        files_scanned += 1
        all_findings.extend(scan_file(p, args.frontend))
    all_findings.extend(detect_v1_copy(args.src, v1_digests))

    n_block = sum(1 for f in all_findings if f["severity"] == "block")
    n_warn = sum(1 for f in all_findings if f["severity"] == "warn")
    verdict = "fail" if n_block > 0 else "pass"

    report = {
        "src": str(args.src),
        "frontend": args.frontend,
        "files_scanned": files_scanned,
        "n_block": n_block,
        "n_warn": n_warn,
        "verdict": verdict,
        "findings": all_findings,
    }

    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True),
                               encoding="utf-8")

    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
