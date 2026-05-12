# Z3 C++ API excerpt — RDL adapter cheat sheet

Z3 ships as a pre-built package under `external/z3/z3-4.16.0-x64-glibc-2.39/`.
The harness exposes `Z3_INCLUDE_DIR` (`include/`) and `Z3_LIBRARY_DIR`
(`bin/`, where `libz3.so` lives) — see `fairness_rules.md` §I and the
build snippet in `z3_adapter_prompt.md`. Every symbol below is in
`include/z3++.h` and `include/z3_api.h`. There is **no** system
`libz3-dev` and **no** `Z3Config.cmake`.

You use Z3 purely as a parser + AST walker + closed-term substituter.
The auditor blocks every solver entry point.

## 1. Headers and namespace

```cpp
#include <z3++.h>           // C++ wrapper (umbrella)
// optionally: #include <z3.h>  for raw C API (Z3_get_numeral_string, etc.)
using namespace z3;
```

`z3++.h` re-exports `z3.h`, so a single include is enough. All C++
types live in the `z3::` namespace; C API symbols (e.g.
`Z3_get_numeral_string`, `Z3_decl_kind`) are global.

## 2. Construct & parse — Z3 returns assertions in **one** call

```cpp
z3::context ctx;
z3::expr_vector asserts = ctx.parse_file("input.smt2");
// or: z3::expr_vector asserts = ctx.parse_string(text.c_str());
```

This is the cleanest parse-and-extract pattern of any front-end in the
trial: a single call returns the full conjunction of asserted formulae
as a vector. No solver is created, no `assert` callback is needed.

## 3. AST type & traversal

The AST node is `z3::expr` (a subclass of `z3::ast`). Children are
accessed by index:

```cpp
unsigned n = e.num_args();
for (unsigned i = 0; i < n; ++i) {
    z3::expr c = e.arg(i);
    // ...
}
std::string text = e.to_string();
```

Useful node-shape predicates already on `z3::expr`:

```cpp
e.is_app();         // true for f(args) including all builtins
e.is_const();       // 0-arity application: a variable or numeral
e.is_numeral();     // numeric literal
e.is_bool();        // boolean-sorted
e.is_real();        // real-sorted   (NOTE: a numeric value can be is_int())
e.is_int();
e.is_var();         // bound variable inside a quantifier
```

## 4. Kind enum — `Z3_decl_kind`, accessed via the function declaration

```cpp
z3::func_decl    f  = e.decl();
Z3_decl_kind     k  = f.decl_kind();   // top operator
std::string      nm = f.name().str();  // for free constants / variables
```

`Z3_decl_kind` values you will need for QF_RDL:

```
Z3_OP_AND, Z3_OP_NOT,
Z3_OP_LE, Z3_OP_LT, Z3_OP_GE, Z3_OP_GT, Z3_OP_EQ,
Z3_OP_ADD, Z3_OP_SUB, Z3_OP_UMINUS, Z3_OP_MUL,
Z3_OP_UNINTERPRETED   // free constants
```

These constants are integers; the auditor's grep only looks for the
forbidden families, so don't worry about matching strings.

## 5. Sort queries

```cpp
z3::sort      s  = e.get_sort();
Z3_sort_kind  sk = s.sort_kind();   // Z3_REAL_SORT, Z3_INT_SORT, Z3_BOOL_SORT, ...
bool          isReal = (sk == Z3_REAL_SORT);
bool          isInt  = (sk == Z3_INT_SORT);
```

`e.is_real()` and `e.is_int()` on the expression itself are convenient
shortcuts.

## 6. Numeral access — preserve exact rationals

```cpp
if (e.is_numeral()) {
    // canonical: returns the lexical numeral as a C string.
    // Handles arbitrary precision, decimals, fractions, and signs.
    std::string lit = Z3_get_numeral_string(ctx, e);
    // pass `lit` straight through to JSON "bound" — do NOT cast to double.
}
```

`Z3_get_numeral_decimal_string(ctx, e, prec)` exists but is lossy; do
not use it. If you prefer a `p/q` form, use `Z3_get_numerator(ctx, e)`
+ `Z3_get_denominator(ctx, e)`, each returning a fresh numeral expr
that you again pass through `Z3_get_numeral_string`.

## 7. Closed-term evaluation — `expr::substitute` (§B.5 allowed)

Z3 exposes a clean substitution API at the AST level — no solver, no
model, no theory tactic. This is the only "evaluate" operation the
fairness rules permit:

```cpp
z3::expr_vector vars(ctx), vals(ctx);
vars.push_back(x); vals.push_back(ctx.real_val("3/2"));
vars.push_back(y); vals.push_back(ctx.real_val("0"));
z3::expr plugged = atom.substitute(vars, vals);
// `plugged` is an AST in which all occurrences of x,y have been
// textually replaced; it is *not* simplified by any theory.
```

Use this to reduce a closed difference-logic atom to a numeral atom
when needed; do **not** call `.simplify()` on the result (that crosses
the theory boundary — see §C).

## 8. Allowed API surface for this trial

* `z3::context`, `z3::expr`, `z3::sort`, `z3::func_decl`,
  `z3::expr_vector`, `z3::ast_vector`.
* `context::parse_file`, `context::parse_string`.
* `expr` traversal: `num_args`, `arg(i)`, `decl()`, `is_app`,
  `is_const`, `is_numeral`, `is_var`, `is_real`, `is_int`, `is_bool`,
  `to_string`, `get_sort`.
* `func_decl::decl_kind()`, `func_decl::name().str()`.
* `Z3_get_sort_kind`, `Z3_get_numeral_string`, `Z3_get_numerator`,
  `Z3_get_denominator`.
* `expr::substitute(expr_vector const&, expr_vector const&)`.

## 9. Forbidden APIs (auditor flags these)

* `z3::solver`, `solver::check`, `solver::assertions`,
  `Z3_solver_check`, `Z3_solver_check_assumptions`.
* `z3::optimize`, `Z3_mk_optimize`.
* `z3::tactic`, `Z3_tactic_apply`.
* `expr::simplify()`, `Z3_simplify`, `Z3_simplify_ex` — these cross the
  theory boundary; structural canonicalisation must be written by hand.
* `Z3_solver_get_model`, `Z3_model_eval`, `z3::model`, `model::eval`.
* `Z3_eval_smtlib2_string` (this drives the full solver loop).

## 10. Gotchas & minimal skeleton

* `(- x y)` may arrive as `Z3_OP_SUB` *or* `Z3_OP_ADD` with one child
  wrapped in `Z3_OP_UMINUS` — canonicalise both.
* Negative literals come in two shapes: a `Z3_OP_UMINUS` over a
  positive numeral, or a numeral whose string already begins with `-`.
  Handle both.
* `Z3_get_numeral_string` returns text *without* a trailing slash for
  integers (`"3"`, not `"3/1"`). Your JSON layer should accept both.

```cpp
#include <z3++.h>
#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 3) { std::cerr << "usage: <in.smt2> <out.json>\n"; return 2; }
    z3::context ctx;
    z3::expr_vector asserts = ctx.parse_file(argv[1]);
    for (unsigned i = 0; i < asserts.size(); ++i) {
        z3::expr a = asserts[i];
        // walk a with a.decl().decl_kind() and a.arg(i); emit JSON
    }
    // write rdl_atoms.json with frontend="z3_cpp"
    return 0;
}
```
