# SOMTParser-specific adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/somtparser.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** the harness will tell you a path of the form
  `case_studies/rdl_prototyping/results/runs/somtparser/run_NN/src/`.
  Write `main.cpp` and a `CMakeLists.txt` there. Do not write anywhere
  else in the repo.
* **Frontend identifier:** `"somtparser"` (use this as the `frontend`
  field of every JSON output).
* **CMake target name:** `somtparser-rdl-adapter` (the harness greps
  the build dir for an executable matching `*-rdl-adapter`).
* **How the harness builds you:** in your `src/` directory, the
  harness runs `cmake -S . -B build -DSOMTPARSER_ROOT=<path> ...`
  with **no top-level CMake involvement**. The recommended pattern is
  to `add_subdirectory("${SOMTPARSER_ROOT}" "${CMAKE_BINARY_DIR}/somtparser_build")`
  in your own `CMakeLists.txt` so you pick up the `somtparser_static`
  target (which propagates `SOMTParser/include` as an include dir).
  See `fairness_rules.md` §I for the full list of variables the
  harness sets. Minimal example:

  ```cmake
  cmake_minimum_required(VERSION 3.10)
  project(somtparser_rdl_adapter CXX)
  set(CMAKE_CXX_STANDARD 17)
  add_subdirectory("${SOMTPARSER_ROOT}"
                   "${CMAKE_BINARY_DIR}/somtparser_build")
  add_executable(somtparser-rdl-adapter main.cpp)
  target_link_libraries(somtparser-rdl-adapter PRIVATE somtparser_static)
  ```

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and the cheat sheet in
`api_excerpts/somtparser.md`. Summary: parser, AST traversal, sort
queries, numeral introspection, `Parser::evaluate(term, model)` for
closed-term substitution. **No** `Solver`, `checkSat`, optimisation,
model API, or built-in DL/IDL/RDL theory entry points.

## SOMTParser-specific subtleties

* `Parser` returns `TermPtr` objects rooted at the assertion list. Walk
  with `getKind()` / `getChild(i)`; the kind enum lives in
  `somtparser/core/kind.h` (read it, do not paraphrase). Treat
  `Kind::AND` recursively until you hit a leaf comparison.
* `(- x y)` may arrive as a binary `Kind::SUB` *or* an n-ary
  `Kind::ADD` whose second child has been pre-multiplied by `(- 1)` —
  canonicalise both shapes into a single `lhs - rhs`.
* SOMTParser's numeral accessor returns the exact rational as text;
  pass it straight through to the JSON `bound` field (no `double`).

## Done criteria

1. `somtparser-rdl-adapter input.smt2 output.json` produces an
   `rdl_atoms.json` whose `frontend` field equals `"somtparser"`.
2. Running the harness on the dev set reports 0 audit violations.
3. The shared backend's verdicts on the dev set agree with the
   `status` column of `data/dev_index.csv` for as many files as
   possible. The trial is graded on first-pass success rate, fix-
   iterations to success, adapter SLOC, and final test-set pass rate
   (computed by the harness *after* the K-th fix iteration).
