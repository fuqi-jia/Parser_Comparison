# cvc5 (C++ AST) adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/cvc5_cpp.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/cvc5_cpp/run_NN/src/`.
  Write `main.cpp` and a `CMakeLists.txt` there.
* **Frontend identifier:** `"cvc5_cpp"`.
* **CMake target name:** `cvc5-rdl-adapter` (the harness greps the
  build dir for an executable matching `*-rdl-adapter`).
* **How the harness builds you:** cvc5 ships **inside this repo** as a
  pre-built static `libcxx-static` package whose `.a` archives
  reference LLVM `libc++` symbols (`std::__1::...`), **not** GNU
  `libstdc++`. Use the harness-provided `CVC5_INCLUDE_DIR` /
  `CVC5_LIBRARY_DIR` (see `fairness_rules.md` §I) and force the
  toolchain over to clang+libc++ inside your CMakeLists. The trial
  machine has `clang++ 18` and `libc++-18-dev` pre-installed.
  Skeleton:

  ```cmake
  cmake_minimum_required(VERSION 3.10)
  project(cvc5_rdl_adapter CXX)
  set(CMAKE_CXX_STANDARD 17)
  # MANDATORY for the libcxx-static prebuilt cvc5 in this repo:
  set(CMAKE_CXX_COMPILER clang++)
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
  set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")
  add_executable(cvc5-rdl-adapter main.cpp)
  target_include_directories(cvc5-rdl-adapter PRIVATE
      "${CVC5_INCLUDE_DIR}")
  target_link_directories(cvc5-rdl-adapter PRIVATE
      "${CVC5_LIBRARY_DIR}")
  target_link_libraries(cvc5-rdl-adapter PRIVATE
      cvc5parser cvc5 picpolyxx picpoly cadical gmpxx gmp)
  ```

  Skipping the `-stdlib=libc++` directives will give you cryptic
  `undefined reference to std::__1::*` linker errors from
  `libcadical.a` and friends; do not fall back to gcc + libstdc++.

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/cvc5_cpp.md`. Summary:
`cvc5::Solver` (as **term factory only**), `cvc5::SymbolManager`,
`cvc5::parser::InputParser`, `cvc5::parser::Command::invoke`,
`Term::getKind()` / `getNumChildren()` / `operator[](size_t)`,
`Term::getRealValue()` / `getIntegerValue()` (both `std::string`),
sort queries. **No** `cvc5::Solver::checkSat`, `getValue`,
`getModel`, `simplify`, optimisation, or anything inside
`cvc5::theory::arith::idl`.

## cvc5-specific subtleties

* The vendored cvc5 package exposes the modern `cvc5::parser::InputParser`
  + `Command::invoke` model. Drive it with `setFileInput` →
  `while (!ip.done()) ip.nextCommand().invoke(&solver, &sm);`. There
  is **no** `parseAndExecute` / `appendIncrementalStringInput` short
  cut on this build — the loop is the only supported entry point. See
  `api_excerpts/cvc5_cpp.md` §2 for the literal snippet.
* `Term::getKind()` returns a `cvc5::Kind` enum (`AND`, `LEQ`, `LT`,
  `GEQ`, `GT`, `EQUAL`, `SUB`, `ADD`, `NEG`, `MULT`, `CONST_RATIONAL`,
  …). Treat both `SUB` and `ADD-with-NEG` shapes as a difference.
* `Term::getRealValue()` returns **`std::string`**, not a numerator /
  denominator pair (older docs got that wrong). The lexical text
  may be either `"p/q"` or a plain integer / decimal — pass it
  unchanged to the JSON `bound` field. The pair-typed accessors are
  `getReal32Value()` and `getReal64Value()` and both throw if the
  rational does not fit in those bit widths, so they are unsafe for
  the big-number anchors in `dev_examples.md`.
* Reject anything not declared as `Real` in QF_RDL — query
  `term.getSort().isReal()`.

## Done criteria

1. `cvc5-rdl-adapter input.smt2 output.json` produces an
   `rdl_atoms.json` whose `frontend` field equals `"cvc5_cpp"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.
