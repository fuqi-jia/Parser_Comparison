# cvc5 (C++ AST) adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/cvc5_cpp.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/cvc5_cpp/run_NN/src/`.
  Write `main.cpp` and a `CMakeLists.txt` there.
* **Frontend identifier:** `"cvc5_cpp"`.
* **CMake target name:** `cvc5-rdl-adapter`. Link against the vendored
  parser-only static libraries cvc5 ships under
  `external/cvc5/build/install/` (the trial assumes those have been
  built; do not modify `external/cvc5/`).

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/cvc5_cpp.md`. Summary:
`TermManager`, `cvc5::parser::Parser` (or the newer `InputParser`
wrapper), `Term::getKind()` / `getNumChildren()` / `operator[]`,
`Term::getRealValue()` / numeral string accessors, sort queries.
**No** `cvc5::Solver::checkSat`, `getValue`, `getModel`, `simplify`,
optimisation, or anything inside `cvc5::theory::arith::idl`.

## cvc5-specific subtleties

* Drive the parser with `appendIncrementalStringInput` +
  `parseAndExecute`, *or* use the `InputParser` wrapper if your cvc5
  version exposes it. Either is fine — pick one.
* `Term::getKind()` returns a `cvc5::Kind` enum (`AND`, `LEQ`, `LT`,
  `GEQ`, `GT`, `EQUAL`, `SUB`, `ADD`, `NEG`, `MULT`, `CONST_RATIONAL`,
  …). Treat both `SUB` and `ADD-with-NEG` shapes as a difference.
* `Term::getRealValue()` returns `(numerator, denominator)` as a
  `std::pair`. For literals that exceed `int64_t`, fall back to the
  string accessor so big-number anchors (see `dev_examples.md`)
  round-trip losslessly.
* Reject anything not declared as `Real` in QF_RDL — query
  `term.getSort().isReal()`.

## Done criteria

1. `cvc5-rdl-adapter input.smt2 output.json` produces an
   `rdl_atoms.json` whose `frontend` field equals `"cvc5_cpp"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.
