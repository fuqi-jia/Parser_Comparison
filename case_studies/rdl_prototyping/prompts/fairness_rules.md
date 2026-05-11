# Fairness rules for the RDL LLM trial

This document is the **single source of truth** for what an LLM-generated
adapter is and is not allowed to do. Every per-front-end prompt
(`<frontend>_adapter_prompt.md`) refers back here. Every audit run in
`scripts/audit_adapter.py` checks against this list.

The trial compares **seven SMT-LIB front ends** as parsing/AST libraries for
prototyping a tiny RDL theory solver. The fairness story only holds if all
seven adapters use comparable surfaces of their respective libraries.

## A. The shared backend is the only verdict-producing component

```
adapter   :  *.smt2  ->  rdl_atoms.json
backend   :  rdl_atoms.json -> sat | unsat | unknown
```

* The **adapter** must only emit `rdl_atoms.json` matching
  `case_studies/rdl_prototyping/schema/rdl_atoms.schema.json`.
* The **shared backend** at
  `case_studies/rdl_prototyping/shared_backend/rdl_backend.py` is the only
  thing allowed to print `sat / unsat / unknown`. Adapters never read,
  link to, embed, or shell out to it; the harness pipes between them.
* If the adapter cannot extract a clean RDL formula, it must emit
  `status: "unsupported"` (or `"error"`) and exit 0. Never invent a verdict.

## B. Capability rules — what every adapter MAY use

The adapter is allowed to use its front-end as a **parser, typed-AST library,
and sort/numeral query API**. Specifically, you may call:

1. SMT-LIB2 file/string parsers
   (e.g. `Z3_parse_smtlib2_file`, `cvc5::parser::Parser`, `pysmt.SmtLibParser`,
    `org.smtlib.SMT.smtlib2`, `smt-switch::SmtLibReader`).
2. AST traversal: top operator/kind queries, child accessors, name accessors,
   constant/literal predicates.
3. Sort queries: kind of a sort (`Real`, `Bool`, `Int`, `BV`, …).
4. Numeral introspection: rational/integer string accessors that return the
   exact lexical form (decimals, fractions, signed numerals).
5. **External evaluation only.** The shared backend may at the harness's own
   discretion ask an adapter to evaluate a closed term against a model that
   the adapter constructs *outside* the SMT solver (e.g. plug rationals into
   an arithmetic AST and reduce to a numeral). This is the only "evaluate"
   that is allowed, and it must not consult any solver state.

This list is intentionally generous — the case study is precisely about
which front-end gives the LLM the easiest path through (1)–(4).

## C. Capability rules — what every adapter MUST NOT use

Forbidden, regardless of front-end:

1. Any `check-sat` / `checkSat` / `solve()` / `Solver::check` /
   `Z3_solver_check*`.
2. Any optimisation API (`Z3_optimize_*`, `cvc5::Optimizer`, …).
3. Any model API exposed by the front-end's solver
   (`Z3_solver_get_model`, `cvc5::Solver::getValue`, `Solver::get_model`,
   `pysmt.Solver.get_model`, …) — this includes querying values of variables
   from the solver, blocking models, or `model.eval`.
4. Any tactic/preprocessing/simplification that is allowed to discharge the
   formula or rewrite using theory reasoning that yields `true`/`false`
   verdicts (`Z3_tactic_apply`, `Z3_simplify`, `cvc5::Solver::simplify`,
   `pysmt.Solver.simplify`, …). Pure structural simplification done *by the
   adapter itself* (e.g. flattening `and`) is fine.
5. Any access to a built-in or shipped DL/IDL/RDL theory solver inside the
   front-end's library (e.g. cvc5's `theory::arith::idl`, Z3's
   `theory_diff_logic`).
6. Any underlying SAT solver (CaDiCaL, kissat, MiniSat, glucose, …) — this
   case study is conjunction-only.
7. Any UNSAT-core, proof, or interpolation API.
8. Network calls (no remote LLM, no remote solver).
9. Reading any file under the explicit ignore list in
   `.llmtrialignore` at runtime — including the shared backend source, the
   final test set, the v1 demo archive, or other adapters' source. The
   harness whitelists only `data/dev/`, the schema, and the public README.

The static auditor in `scripts/audit_adapter.py` greps for the concrete
symbols of (1)–(7) inside the adapter source.

## D. Information rules — what the LLM MAY see

When the harness assembles a prompt for the LLM it concatenates *only*:

1. `prompts/base_task.md`
2. `prompts/fairness_rules.md`              (this file)
3. `prompts/api_excerpts/<frontend>.md`     (front-end API cheat sheet)
4. `prompts/<frontend>_adapter_prompt.md`   (front-end-specific extras)
5. `prompts/dev_examples.md`                (dev-set summary; see §F)
6. The **dev set** files under `data/dev/`  (full text, plus per-file
   expected status from `data/dev_index.csv`).

A fixed total token budget is enforced (`config/llm.yaml`'s
`prompt_token_budget`, default 24 000). Front ends that need more
documentation either link to upstream docs (the LLM cannot fetch URLs) or
trim. Every prompt bundle is hashed and saved under
`results/runs/<frontend>/run_NN/prompt/` for reproducibility.

## E. Information rules — what the LLM MUST NOT see

The harness withholds, and the auditor can statically check that the
generated source did not embed:

1. The **final test set** under `data/test/` and `data/test_index.csv`.
   These never enter any prompt; the adapter is only ever evaluated on the
   final test set after the K-th fix iteration.
2. The shared backend source under `shared_backend/` and the schema under
   `schema/` (only the schema's *contract*, not the file, is paraphrased
   inside `base_task.md`).
3. The v1 demo under `_archive/v1_demo/`.
4. Any other front-end's adapter source (including ones from previous
   trials in `results/runs/`).
5. Vendored upstream theory-solver implementations under `external/`
   (e.g. cvc5 IDL solver source, Z3 difference-logic theory).

The harness builds the prompt by reading whitelisted paths only and
re-checks each path against `.llmtrialignore` before injecting the file
into the conversation.

## F. Dev / test split

`scripts/split_dev_test.py` produces a fixed, seed=42 stratified split over
(family, status). The dev set (30 files) is the **only** set the LLM sees;
the test set (123 files) is held out and only used for the final
post-trial evaluation in `run_llm_trial.py`'s `final_test/` step. Status
labels (`sat`/`unsat`) are taken from the SMT-COMP `(set-info :status …)`
header.

## G. Iteration protocol

Each trial allows up to **K=3 fix iterations** (configurable in
`config/llm.yaml`). Per iteration the harness shows the LLM:

* the build log of its previous attempt,
* up to *N* failing dev-set test names with the per-file JSON the adapter
  produced and the verdict the shared backend then derived,
* the audit report (forbidden-symbol hits, if any).

It does **not** show the test set, the shared backend source, or any other
adapter's code.

## H. Honesty addendum

Reporting `status: "unsupported"` with a truthful `reason` is always
preferred over a guess. The shared backend turns `"unsupported"` into the
verdict `unknown`, which counts neither as a pass nor a wrong answer in the
fairness-aware metrics described in `case_study_notes.md`.

## I. Vendored dependencies the harness provides

All seven front-end libraries ship as submodules / pre-built packages
**inside this repository**, not as system-wide installs. The trial harness
discovers them at `run_llm_trial.py` startup and exposes their absolute
paths to your adapter via **both** of:

1. `-D<KEY>=<PATH>` flags appended to every `cmake configure` invocation
   (so `${KEY}` is available in your `CMakeLists.txt`).
2. Identically-named environment variables exported to every
   `bash build.sh` / `bash run.sh` / Python / Java adapter invocation
   (so `${KEY}` is available in shell scripts and `os.environ[KEY]` in
   Python). The harness additionally prepends every vendored shared-
   library directory to `LD_LIBRARY_PATH` for the produced binary.

The complete list of variables that **may** be set (any one of them is
*absent* if the underlying path is missing — your build must therefore
guard the path it actually needs):

| variable | what it points to |
|---|---|
| `PARSER_COMPARISON_ROOT`     | repo root |
| `SOMTPARSER_ROOT`            | `SOMTParser/` (has its own CMakeLists; `add_subdirectory` is the recommended use) |
| `SOMTPARSER_INCLUDE_DIR`     | `SOMTParser/include` |
| `Z3_ROOT`                    | `external/z3/z3-<ver>-x64-glibc-2.39/` (pre-built Z3 package) |
| `Z3_INCLUDE_DIR`             | `${Z3_ROOT}/include` (contains `z3++.h`, `z3.h`) |
| `Z3_LIBRARY_DIR`             | `${Z3_ROOT}/bin` (contains `libz3.so`) |
| `CVC5_ROOT`                  | `external/cvc5/cvc5-Linux-x86_64-libcxx-static/` |
| `CVC5_INCLUDE_DIR`           | `${CVC5_ROOT}/include` (contains `cvc5/cvc5.h`, `cvc5/cvc5_parser.h`) |
| `CVC5_LIBRARY_DIR`           | `${CVC5_ROOT}/lib` (`libcvc5.a`, `libcvc5parser.a`, deps) |
| `SMT_SWITCH_ROOT`            | `external/smt-switch/` (whole vendor tree) |
| `SMT_SWITCH_INCLUDE_DIR`     | `external/smt-switch/smt-switch-1.0.6/include` |
| `SMT_SWITCH_LIBRARY_DIR`     | `external/smt-switch/build/smt-switch-1.0.6` (contains `libsmt-switch.so`) |
| `SMT_SWITCH_CVC5_LIBRARY_DIR`| `${SMT_SWITCH_LIBRARY_DIR}/cvc5` (`libsmt-switch-cvc5.so`) |
| `ANTLR4_ROOT`                | `external/antlr4_parser/` (grammar, prebuilt `.class` files, Makefile, jars under `lib/`) |
| `JSMTLIB_ROOT`               | `external/jsmtlib/` (build.sh, run.sh, jars) |
| `JSMTLIB_DIST_ROOT`          | `external/jsmtlib/jSMTLIB-<ver>/` (the upstream distribution dir) |

**Hard rules following from this list:**

1. **Do not assume any system install** of Z3 / cvc5 / smt-switch /
   ANTLR / jSMTLIB. There is no `find_package(Z3)`, no
   `apt-get install libz3-dev`. The vendored variables above are the
   only sanctioned source for parser binaries / static libs / jars.
   (PyPI and Maven Central are both reachable from the trial sandbox,
   but treat them as fallbacks, not as primary dependencies — the
   fairness comparison is against the vendored copies.)
2. **`Z3_ROOT` ships shared libs under `${Z3_ROOT}/bin`** (not
   `${Z3_ROOT}/lib`). The harness puts that directory on
   `LD_LIBRARY_PATH`; in your CMakeLists.txt you typically write
   `target_link_directories(<tgt> PRIVATE "${Z3_LIBRARY_DIR}")` then
   `target_link_libraries(<tgt> PRIVATE z3)`.
3. **`CVC5_ROOT` is the libcxx-static prebuilt package.** Its `.a`
   archives reference LLVM `libc++` symbols (`std::__1::...`),
   *not* GNU `libstdc++`. To link successfully you must set
   `CMAKE_CXX_COMPILER=clang++` and pass `-stdlib=libc++` to both
   compiler and linker. `clang++ 18` and `libc++-18-dev` are
   pre-installed on the trial machine. The harness does NOT inject
   these flags automatically — the adapter's CMakeLists.txt owns
   the toolchain choice.
4. **`SOMTPARSER_ROOT` is a source tree, not a prebuilt package.**
   The recommended use is
   `add_subdirectory("${SOMTPARSER_ROOT}" "${CMAKE_BINARY_DIR}/somtparser_build")`
   then `target_link_libraries(<tgt> PRIVATE somtparser_static)`;
   `target_include_directories` is unnecessary because the library
   target propagates `SOMTParser/include/` automatically.
5. **`SMT_SWITCH_*` libraries are pre-built `.so` files.** Your
   CMakeLists should `target_link_directories` to
   `${SMT_SWITCH_LIBRARY_DIR}` and link `smt-switch`, plus
   `${SMT_SWITCH_CVC5_LIBRARY_DIR}` and `smt-switch-cvc5` if you
   pick the cvc5 back-end.
6. **For Java / shell adapters**, the same names are available as
   shell variables; e.g. `build.sh` can do
   `javac -cp "$JSMTLIB_DIST_ROOT/lib/*:..." Adapter.java`.

If your build needs a path that is **not** in the table above, your
adapter is probably trying to depend on something outside the trial
contract — re-check §B / §C of these fairness rules first.
