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

* `jSMTLIB` ships the SMT-LIB v2.6 grammar as a bundled resource. Set
  `smt.smtConfig.smtlib = ".../bin/SMT-LIBv2.6"` to the path inside
  the vendored `external/jsmtlib/` install; if that fails to resolve,
  fall back to the `org.smtlib.SMT.smtlib2` static helper.
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

* `build.sh` should compile against the jars under
  `external/jsmtlib/lib/`. Avoid relying on Maven Central downloads
  during the trial.
* `run.sh` should set the `SMT_LIB2_GRAMMAR` environment variable (or
  pass `-D...`) to the bundled grammar path so jSMTLIB does not error
  on first parse.
