# smt-switch adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/smt_switch.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/smt_switch/run_NN/src/`.
  Write `main.cpp` and a `CMakeLists.txt` there.
* **Frontend identifier:** `"smt_switch"`.
* **CMake target name:** `smt-switch-rdl-adapter`. Pick **one** back-end
  factory (`Cvc5SolverFactory` or `Z3SolverFactory`) for parsing only;
  link against the vendored `external/smt-switch/` static libs.

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/smt_switch.md`.
Summary: `SmtSolver` factory in *parser-only* mode, `SmtLibReader`
subclass, `Term::get_op()` (`smt::PrimOp`), `Term::begin()/end()`,
sort kind. **No** `Solver::check_sat`, `check_sat_assuming`,
`get_value`, `get_model`, `simplify`.

## smt-switch-specific subtleties

* The cleanest route is a small `SmtLibReader` subclass that overrides
  `assert(...)` to push terms into a vector, then walk that vector
  outside the reader.
* `Op` flattens many surface forms into a small set of `PrimOp`s
  (`Le`, `Lt`, `Ge`, `Gt`, `Equal`, `Plus`, `Minus`, `Negate`, `Mult`).
  Treat `Plus(x, Negate(y))` as `(- x y)`.
* Numerals reach you with `t->is_value()` true. Use `t->to_string()`
  and pass through; do not parse via `to_int()` for files in
  `dev_examples.md` anchor 1 (they overflow 64-bit ints).

## Done criteria

1. `smt-switch-rdl-adapter input.smt2 output.json` writes a valid
   `rdl_atoms.json` with `frontend: "smt_switch"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.
