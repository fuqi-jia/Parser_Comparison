# smt-switch API excerpt — RDL adapter cheat sheet

`smt-switch` is a thin abstraction over Z3 / cvc5 / Boolector / MathSAT.
For this trial you use it as a **parser + abstract Term/Op/Sort walker**.
You must not invoke `Solver::check_sat`; the auditor blocks that call.

## Headers

```cpp
#include "smt-switch/smt.h"
#include "smt-switch/smtlib_reader.h"
// pick one back-end strictly for parsing/AST construction:
#include "smt-switch/cvc5_factory.h"   // or z3_factory.h, ...
```

## Allowed APIs

* Construct a backend purely as a Term factory:
  * `smt::SmtSolver s = smt::Cvc5SolverFactory::create(false);`
    (the `false` typically disables logging / proof; the trial does not
    care about that).
  * `s->set_logic("QF_RDL");` — informational only.
* Parsing: the `smt::SmtLibReader` subclass pattern.
  ```cpp
  class RDLReader : public smt::SmtLibReader {
   public:
    using smt::SmtLibReader::SmtLibReader;
    void term_attribute(const smt::Term & t, ...) override { /* … */ }
    smt::Term assert(const smt::Term & t) override {
      asserts_.push_back(t);
      return t;
    }
    std::vector<smt::Term> asserts_;
  };
  RDLReader r(s);
  r.parse("input.smt2");
  ```
* AST traversal on `smt::Term`:
  * `t->get_op()` returning a `smt::Op` (with `.prim_op` of type
    `smt::PrimOp`: `And`, `Le`, `Lt`, `Ge`, `Gt`, `Equal`, `Minus`,
    `Plus`, `Negate`, `Mult`, `Apply`, `Numeral`, `Symbol`, …).
  * `t->begin()`, `t->end()`, `t->get_id()`, `t->get_sort()`.
  * `t->is_value()`, `t->is_symbol()`.
* Sort queries: `Sort::get_sort_kind()` returning
  `smt::SortKind::REAL`, `INT`, `BOOL`, `BV`, …
* Numeral access: `t->to_string()` for the lexical form, or
  `t->to_int()` for small integers; for rationals retrieve the literal
  string and parse with `Fraction(...)` on the Python side.

## Forbidden APIs (auditor will flag)

* `Solver::check_sat`, `check_sat_assuming`.
* `Solver::get_value`, `get_model`.
* Any `Solver::push`/`pop` is allowed at parse time but blocked from
  being followed by a `check_sat`; in practice the auditor flags
  `check_sat` directly.
* The `smt::TermTranslator` pipeline if it triggers solver-side
  simplification.

## Tips

* The cleanest path is: pick **one** back-end (cvc5 or Z3), use
  `SmtLibReader` to populate a vector of asserted terms, then walk those
  terms with `get_op()` and `begin()/end()`. This keeps the adapter
  back-end-agnostic in spirit.
* Numerals reach you as `t->is_value()` with op-kind `Numeral`. Use
  `t->to_string()` and pass through unchanged — `Fraction` accepts
  `"3"`, `"-2"`, `"7/2"`.
