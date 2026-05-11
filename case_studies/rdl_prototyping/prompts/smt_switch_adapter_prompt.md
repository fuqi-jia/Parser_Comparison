# smt-switch adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/smt_switch.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/smt_switch/run_NN/src/`.
  Write `main.cpp` and a `CMakeLists.txt` there.
* **Frontend identifier:** `"smt_switch"`.
* **CMake target name:** `smt-switch-rdl-adapter` (the harness greps
  the build dir for an executable matching `*-rdl-adapter`).
* **How the harness builds you:** smt-switch ships **inside this repo**
  as a pre-built `.so` set under `${SMT_SWITCH_LIBRARY_DIR}`, with
  headers in `${SMT_SWITCH_INCLUDE_DIR}` (see `fairness_rules.md` §I).
  The cvc5 back-end of smt-switch is the only one this trial vendors
  (`libsmt-switch-cvc5.so`). Z3 / Boolector / MathSAT factories are
  **not** vendored and will fail to link. Skeleton:

  ```cmake
  cmake_minimum_required(VERSION 3.10)
  project(smt_switch_rdl_adapter CXX)
  set(CMAKE_CXX_STANDARD 17)
  add_executable(smt-switch-rdl-adapter main.cpp)
  target_include_directories(smt-switch-rdl-adapter PRIVATE
      "${SMT_SWITCH_INCLUDE_DIR}")
  target_link_directories(smt-switch-rdl-adapter PRIVATE
      "${SMT_SWITCH_LIBRARY_DIR}"
      "${SMT_SWITCH_CVC5_LIBRARY_DIR}")
  target_link_libraries(smt-switch-rdl-adapter PRIVATE
      smt-switch-cvc5 smt-switch)
  ```

  At run time the harness puts both library directories on
  `LD_LIBRARY_PATH` so `libsmt-switch*.so` resolve without rpaths.

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
* **Use the cvc5 back-end (`Cvc5SolverFactory`)** for parsing — that's
  the only solver factory whose `.so` is vendored. Asking for
  `Z3SolverFactory` will fail to link because `libsmt-switch-z3.so`
  is not present in `${SMT_SWITCH_LIBRARY_DIR}`.
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
