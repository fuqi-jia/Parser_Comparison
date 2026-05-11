# jSMTLIB adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/jsmtlib.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/jsmtlib/run_NN/src/`.
  Write your Java sources, a `build.sh`, and a `run.sh` there. The
  harness invokes `bash run.sh input.smt2 output.json`.
* **Frontend identifier:** `"jsmtlib"`.

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/jsmtlib.md`. Summary:
the `org.smtlib.SMT` parser, the `org.smtlib.IExpr.*` AST hierarchy,
`ICommand` walking, `INumeral`/`IRational`/`IDecimal` numeral
accessors, `ISymbol`. **No** `org.smtlib.solvers.*`, no shelling out
to Z3/cvc5/Yices, no `SMT::checkSat`.

## jSMTLIB-specific subtleties

* The harness exports `JSMTLIB_ROOT` and `JSMTLIB_DIST_ROOT` (see
  `fairness_rules.md` §I). `JSMTLIB_DIST_ROOT` is the unpacked
  upstream distribution `jSMTLIB-0.9.10.1/` and ships the SMT-LIB v2.6
  grammar bundle plus the runtime jars. Build against these vendored
  jars to keep the trial hermetic; Maven Central is reachable but
  not part of the trial contract.
* Operators reach you as `IFcnExpr`, with `head().toString()` returning
  `"and"`, `"<="`, `"<"`, `">="`, `">"`, `"="`, `"-"`, `"+"`, `"*"`.
  Pattern-match on these strings; jSMTLIB does not normalise them
  further.
* Numeric literals come in as three subclasses: `INumeral` (integer),
  `IDecimal` (`1.5`-style), `IRational` (`(/ p q)`). Build a
  `Fraction`-parsable string from each and pass it through. Use
  `BigInteger.toString()` for `INumeral` — never `int` / `long`.

## Done criteria

1. `bash run.sh input.smt2 output.json` writes an `rdl_atoms.json`
   whose `frontend` field equals `"jsmtlib"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.

## Build hints

* `build.sh` should compile your `*.java` files against the jars
  under `${JSMTLIB_DIST_ROOT}/lib/` (or `${JSMTLIB_ROOT}/lib/`,
  whichever your `ls` finds them in). No network downloads are
  available.
* `run.sh` should set the grammar-resource path (e.g.
  `-Dsmt.smtConfig.smtlib="${JSMTLIB_DIST_ROOT}/bin/SMT-LIBv2.6"`) or
  fall back to `org.smtlib.SMT.smtlib2` so jSMTLIB does not error on
  first parse.
