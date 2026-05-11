# Z3 (C++ AST) adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/z3_cpp.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** the harness will tell you a path of the form
  `case_studies/rdl_prototyping/results/runs/z3_cpp/run_NN/src/`. Write
  `main.cpp` and a `CMakeLists.txt` there.
* **Frontend identifier:** `"z3_cpp"`.
* **CMake target name:** `z3-rdl-adapter` (the harness greps the build
  dir for an executable matching `*-rdl-adapter`).
* **How the harness builds you:** Z3 ships **inside this repo** as a
  pre-built package. There is no system `find_package(Z3)` available
  and no `Z3Config.cmake`; use the harness-provided variables
  `Z3_INCLUDE_DIR` and `Z3_LIBRARY_DIR` (see `fairness_rules.md` §I).
  Shared libs live in `${Z3_LIBRARY_DIR}` (which is the prebuilt
  package's `bin/`, not `lib/`). The harness adds that directory to
  `LD_LIBRARY_PATH` at run time. Minimal example:

  ```cmake
  cmake_minimum_required(VERSION 3.10)
  project(z3_rdl_adapter CXX)
  set(CMAKE_CXX_STANDARD 17)
  add_executable(z3-rdl-adapter main.cpp)
  target_include_directories(z3-rdl-adapter PRIVATE "${Z3_INCLUDE_DIR}")
  target_link_directories(z3-rdl-adapter PRIVATE "${Z3_LIBRARY_DIR}")
  target_link_libraries(z3-rdl-adapter PRIVATE z3)
  ```

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and the cheat sheet in
`api_excerpts/z3_cpp.md`. Summary: `z3::context`, `parse_file` /
`parse_string`, `expr::decl()`, `decl_kind()`, `num_args()`, `arg(i)`,
`Z3_get_numeral_string`, `Z3_get_sort_kind`. **No** `z3::solver`,
`Z3_solver_check*`, `z3::optimize`, `z3::tactic::apply`,
`Z3_solver_get_model`, `Z3_model_eval`.

## Z3-specific subtleties

* Z3 internally normalises differences. `(- x y)` may show up as
  `Z3_OP_SUB` with two args, `Z3_OP_ADD` with `(* -1 y)` as the second
  child, or `Z3_OP_UMINUS` over a sub-expression — canonicalise all
  three.
* `Z3_OP_LE`, `LT`, `GE`, `GT` are the comparison kinds; `Z3_OP_EQ` is
  arithmetic equality (your adapter splits it into two `<=` constraints
  per `base_task.md`).
* Numeric literals are `Z3_NUMERAL_AST`. Use `Z3_get_numeral_string` to
  get the exact representation; do **not** call
  `Z3_get_numeral_double` (loses precision on big rationals — see
  `dev_examples.md` anchor 1).
* Reject the BV case explicitly: if `Z3_get_sort_kind` returns
  `Z3_BV_SORT` or `Z3_OP_BSUB` appears, emit
  `status: "unsupported"` with `reason: "bit-vector sub"`.

## Done criteria

1. `z3-rdl-adapter input.smt2 output.json` produces an `rdl_atoms.json`
   whose `frontend` field equals `"z3_cpp"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set agree with
   `data/dev_index.csv` for as many files as possible. Fairness rules
   are auditor-enforced; do not try to call `Z3_solver_check` or
   `Z3_simplify` even as a fallback.
