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

* The official SMT-LIB v2.6 grammar may not be in the repo. If it is
  not under `external/antlr4/`, generate one minimally large enough to
  parse QF_RDL atoms (assertions / `declare-fun` / numerals / signed
  numerals / parenthesised expressions). It is fine for the grammar to
  reject formulae outside QF_RDL — the adapter then emits
  `status: "unsupported"`.
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

* Java route: ship a `build.sh` that runs
  `antlr4 -Dlanguage=Java SMTLIBv2.g4` (use the antlr4 jar provided by
  the system PATH or vendored under `external/antlr4/`), then
  `javac` against that runtime, and a `run.sh` that invokes the
  resulting class with `java -cp ...`.
* Python route: `pip install antlr4-python3-runtime`, generate with
  `antlr4 -Dlanguage=Python3`, write a small `extract_rdl.py`, and
  have `run.sh` exec `python3 extract_rdl.py "$@"`.
