# Z3 C++ API excerpt — RDL adapter cheat sheet

You are using Z3 (`#include <z3++.h>`) purely as a parser and AST walker.
The auditor blocks every solver entry point.

## Allowed APIs

* `z3::context ctx;`
* `z3::expr_vector ctx.parse_file("input.smt2");` and
  `ctx.parse_string("...");` — yield the assertion vector directly.
* AST traversal:
  * `z3::expr::is_app()`, `is_const()`, `is_numeral()`, `is_quantifier()`.
  * `z3::expr::decl()` returns `z3::func_decl`; `decl().decl_kind()`
    returns a `Z3_decl_kind` (`Z3_OP_AND`, `Z3_OP_LE`, `Z3_OP_LT`,
    `Z3_OP_GE`, `Z3_OP_GT`, `Z3_OP_EQ`, `Z3_OP_SUB`, `Z3_OP_ADD`,
    `Z3_OP_UMINUS`, `Z3_OP_MUL`, …).
  * `z3::expr::num_args()` and `arg(i)` to walk children.
  * `z3::expr::to_string()` for debugging.
* Sort queries:
  * `z3::expr::get_sort()` → `z3::sort`.
  * `Z3_get_sort_kind(ctx, sort)` returning `Z3_REAL_SORT`, `Z3_INT_SORT`,
    `Z3_BOOL_SORT`, `Z3_BV_SORT`, …
* Numeral introspection:
  * `Z3_get_numeral_string(ctx, e)` returns the exact lexical numeral as a
    C string. This is the canonical way to pass `bound` through to the
    JSON layer.
  * `Z3_get_numerator` / `Z3_get_denominator` if you prefer to assemble
    `"p/q"` yourself.

## Forbidden APIs (auditor will flag)

* `z3::solver`, `z3::solver::check`, `Z3_solver_check`,
  `Z3_solver_check_assumptions`.
* `z3::optimize`, `Z3_mk_optimize`.
* `z3::tactic`, `Z3_tactic_apply`, `Z3_simplify` *if used to flatten a
  formula past the structural level you wrote yourself*.
* `Z3_solver_get_model`, `Z3_model_eval`, `z3::model`.
* `Z3_eval_smtlib2_string` (this drives the full solver loop).

## Numeral subtleties

* Z3 internally rewrites `(- x y)` to one of: `Z3_OP_SUB(x, y)`,
  `Z3_OP_ADD(x, (* -1 y))`, or wraps a constant as `(* -1 c)`. Treat all
  three as the same shape after a small canonicaliser.
* Negative literals come in as `Z3_OP_UMINUS` over a numeral or as a
  numeral whose string is already negative — handle both.

## Build

There is **no** system `libz3` and **no** `Z3Config.cmake` on the trial
machine. Use the harness-provided `Z3_INCLUDE_DIR` / `Z3_LIBRARY_DIR`
CMake variables — see `fairness_rules.md` §I and the example
`CMakeLists.txt` in `z3_adapter_prompt.md`. The harness adds
`${Z3_LIBRARY_DIR}` to `LD_LIBRARY_PATH` so `libz3.so` resolves at
adapter run time without rpaths.
