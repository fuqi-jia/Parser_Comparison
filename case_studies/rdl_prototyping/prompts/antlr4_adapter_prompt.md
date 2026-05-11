# ANTLR4 grammar adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/antlr4.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/antlr4/run_NN/src/`. Write
  the grammar / runtime invocation there, plus a `build.sh` and
  `run.sh`. The harness invokes `bash run.sh input.smt2 output.json`.
* **Frontend identifier:** `"antlr4"`.

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/antlr4.md`. ANTLR is
just a parser generator — no SMT solver to call. Forbidden additions:
shelling out to Z3/cvc5/MathSAT, network calls, or embedding a SAT
solver.

## ANTLR-specific subtleties

* The harness exports `ANTLR4_ROOT=external/antlr4_parser/` (see
  `fairness_rules.md` §I). That directory ships the SMT-LIB v2.6
  grammar `SMTLIBv2.g4`, a pre-generated Java listener/lexer/parser
  set of `.java` and `.class` files, plus `lib/antlr-4.13.1-complete.jar`
  (or similar) and a `Makefile`. You can either reuse those generated
  artefacts directly or regenerate them.
* You implement *all* sort tracking, numeral parsing, and atom
  classification yourself: pySMT does it for you, ANTLR does not.
* Keep numerals as raw text and pass them through to the JSON `bound`
  field; do not call `Long.parseLong` on them — see anchor 1 in
  `dev_examples.md`.

## Done criteria

1. `bash run.sh input.smt2 output.json` writes an `rdl_atoms.json`
   whose `frontend` field equals `"antlr4"`.
2. The static auditor reports 0 violations (the auditor scans both
   Java and Python sources in your run dir).
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.

## Build hints

* **Java route (recommended, fully offline-friendly).** In `build.sh`
  use `${ANTLR4_ROOT}` to locate the antlr runtime jar and the
  pre-generated `.java` / `.class` files:
  `javac -cp "${ANTLR4_ROOT}/lib/antlr-*-complete.jar:${ANTLR4_ROOT}" \
   -d classes "${ANTLR4_ROOT}"/*.java *.java`
  Then in `run.sh`:
  `java -cp "classes:${ANTLR4_ROOT}:${ANTLR4_ROOT}/lib/antlr-*-complete.jar" Adapter "$@"`.
  Prefer this path — relying on the vendored runtime keeps the build
  hermetic and deterministic across re-runs.
* **Python route (alternative).** PyPI is reachable from the trial
  sandbox, so an `extract_rdl.py` + `requirements.txt` listing
  `antlr4-python3-runtime` works — but you must then regenerate the
  Python parser/lexer from `${ANTLR4_ROOT}/SMTLIBv2.g4`, since only
  the Java versions are pre-generated in the vendored tree.
