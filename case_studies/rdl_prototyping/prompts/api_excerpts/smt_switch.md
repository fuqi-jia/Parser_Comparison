# smt-switch API excerpt — RDL adapter cheat sheet

`smt-switch` is a thin solver-agnostic abstraction over cvc5 / Z3 /
Boolector / MathSAT, vendored under `external/smt-switch/`. The
harness exposes `SMT_SWITCH_INCLUDE_DIR`,
`SMT_SWITCH_LIBRARY_DIR` (with `libsmt-switch.so`) and
`SMT_SWITCH_CVC5_LIBRARY_DIR` (with `libsmt-switch-cvc5.so`) — see
`fairness_rules.md` §I.5. The vendored build links cvc5 statically;
pick the cvc5 backend in your adapter unless you have a strong
reason.

You use smt-switch purely as a parser + abstract `Term`/`Op`/`Sort`
walker. The auditor blocks every solver entry point.

## 1. Headers and namespace

```cpp
#include "smt-switch/smt.h"             // umbrella: Term, Sort, Op, SmtSolver
#include "smt-switch/smtlib_reader.h"   // SmtLibReader base class
#include "smt-switch/cvc5_factory.h"    // Cvc5SolverFactory (one backend)
using namespace smt;
```

`smt.h` is the umbrella; it re-exports the relevant pieces under
`smt::`. The factory header you include picks the term-construction
backend; for this trial use cvc5.

## 2. Construct & parse — subclass `SmtLibReader`

smt-switch's parser is a flex/bison driver that walks the file once
and calls **virtual callbacks** on a `SmtLibReader` subclass for each
top-level command. The cleanest pattern is:

```cpp
class RDLReader : public smt::SmtLibReader {
 public:
    using smt::SmtLibReader::SmtLibReader;       // inherit constructors
    void assert_formula(const smt::Term& t) override {
        asserts_.push_back(t);
        smt::SmtLibReader::assert_formula(t);    // optional: forward to backend
    }
    std::vector<smt::Term> asserts_;
};

smt::SmtSolver solver = smt::Cvc5SolverFactory::create(false /*logging*/);
RDLReader r(solver);
r.parse("input.smt2");                           // returns int (0 == ok)
for (const auto& a : r.asserts_) { walk(a); }
```

Other virtuals you can override if needed: `set_logic`,
`term_attribute`, `push`, `pop`, `check_sat`, `check_sat_assuming`.
Do **not** override `check_sat` to actually run the solver — the
auditor flags `check_sat` symbols.

## 3. AST type & traversal — `smt::Term` (shared_ptr to `AbsTerm`)

`Term` is `std::shared_ptr<smt::AbsTerm>`. Children are reached via
STL-style iterators:

```cpp
for (auto it = t->begin(); it != t->end(); ++it) {
    smt::Term c = *it;
    // ...
}
std::size_t id = t->get_id();
smt::Sort  s   = t->get_sort();
smt::Op    op  = t->get_op();
std::string text = t->to_string();
bool is_sym = t->is_symbol();        // free variable
bool is_val = t->is_value();         // literal
```

There is **no** `get_num_children()` or `t[i]` indexing; use the
iterator pair.

## 4. Op enum — `smt::PrimOp` (no class prefix)

`Op::prim_op` is the canonical handle on a term's top operator:

```cpp
smt::PrimOp p = t->get_op().prim_op;
switch (p) {
    case smt::And:       ...
    case smt::Or:        ...
    case smt::Not:       ...
    case smt::Equal:     ...
    case smt::Distinct:  ...
    case smt::Plus:      ...
    case smt::Minus:     ...
    case smt::Negate:    ...
    case smt::Mult:      ...
    case smt::Lt:        ...
    case smt::Le:        ...
    case smt::Gt:        ...
    case smt::Ge:        ...
    case smt::Apply:     ...    // (f x y) — usually only for symbols
    // ...
}
```

`smt::PrimOp` is a plain `enum` (no class), and the enumerators are
plain identifiers like `And`, `Le`, `Plus`. The full list is in
`ops.h`. For non-symbol leaves (numerals, free constants) the
operator's `prim_op` may be `NUM_OPS_AND_NULL`; treat those as values
and check `t->is_value()` / `t->is_symbol()`.

## 5. Sort queries

```cpp
smt::Sort       s  = t->get_sort();
smt::SortKind   sk = s->get_sort_kind();   // REAL, INT, BOOL, BV, ARRAY, ...
bool isReal = (sk == smt::REAL);
bool isInt  = (sk == smt::INT);
bool isBool = (sk == smt::BOOL);
```

(Enumerators live in `sort.h` as `smt::SortKind::REAL` etc.; the
plain `smt::REAL` short forms also work.)

## 6. Numeral access — lexical form via `to_string()`

smt-switch does not expose a typed `getRationalValue()` API; the
portable way is the lexical form:

```cpp
if (t->is_value()) {
    std::string lit = t->to_string();   // "3", "-2", "7/2", "0.25" — backend dependent
    // pass `lit` straight through to JSON "bound"; do NOT cast to double.
}
```

For small integers you may also use `t->to_int()` (returns
`uint64_t`; throws on rationals or out-of-range values).

## 7. Closed-term evaluation — not a first-class API

smt-switch deliberately keeps the abstract surface minimal; there is
no `Term::substitute(...)` exposed at the abstract layer. If you need
substitution you must do it yourself, mirroring the pattern of the
shared backend (`solver->make_term(op, {new_children...})` to rebuild
nodes). For the QF_RDL adapter this is almost never necessary —
emitting the structural JSON is enough.

This is intentionally a place where smt-switch costs more LLM tokens
than Z3 / cvc5 / SOMTParser / pySMT, and is part of the case study's
comparison.

## 8. Allowed API surface for this trial

* `smt::SmtSolver`, `smt::Cvc5SolverFactory::create(false)`,
  `Solver::set_logic("QF_RDL")` (informational only).
* `smt::SmtLibReader` subclassed for parse-only use; overrides
  `assert_formula`, `term_attribute`, `set_logic`. `int parse(const
  std::string&)`.
* `smt::Term`: `get_op`, `get_sort`, `get_id`, `begin`, `end`,
  `to_string`, `to_int`, `is_value`, `is_symbol`,
  `is_symbolic_const`, `is_param`.
* `smt::Op::prim_op`, `smt::PrimOp` enumerators.
* `smt::Sort::get_sort_kind`, `smt::SortKind` enumerators.

## 9. Forbidden APIs (auditor flags these)

* `SmtSolver::check_sat`, `check_sat_assuming`, `get_value`,
  `get_model` (and the `SmtLibReader` versions that drive them).
* `SmtSolver::push`/`pop` followed by `check_sat`.
* `TermTranslator` if it triggers solver-side simplification.
* Any backend's native solver entry point reached through the
  abstract wrapper.

## 10. Gotchas & minimal skeleton

* `set_logic_all()` is convenient but the harness expects you to
  honour `QF_RDL`; pick `set_logic("QF_RDL")` explicitly.
* The base `SmtLibReader::assert_formula` forwards the assertion
  *into the underlying solver*. Forwarding is harmless (the auditor
  only flags `check_sat`), but you may skip it for clarity.
* Numerals appearing in some backends (Z3) round-trip
  `"-2"` while cvc5 keeps `"(- 2)"` in `to_string`. Normalise both
  with a small canonicaliser.

```cpp
#include "smt-switch/smt.h"
#include "smt-switch/smtlib_reader.h"
#include "smt-switch/cvc5_factory.h"
#include <iostream>
#include <vector>

using namespace smt;

class RDLReader : public SmtLibReader {
 public:
    using SmtLibReader::SmtLibReader;
    void assert_formula(const Term& t) override { asserts_.push_back(t); }
    std::vector<Term> asserts_;
};

int main(int argc, char** argv) {
    if (argc != 3) { std::cerr << "usage: <in.smt2> <out.json>\n"; return 2; }
    SmtSolver  solver = Cvc5SolverFactory::create(false);
    RDLReader  r(solver);
    if (r.parse(argv[1]) != 0) { std::cerr << "parse failed\n"; return 1; }
    for (const Term& a : r.asserts_) {
        // walk a via a->get_op().prim_op and a->begin()/end()
    }
    // write rdl_atoms.json with frontend="smt_switch"
    return 0;
}
```
