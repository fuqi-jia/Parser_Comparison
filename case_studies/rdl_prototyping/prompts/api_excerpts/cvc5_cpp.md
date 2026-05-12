# cvc5 C++ API excerpt — RDL adapter cheat sheet

cvc5 is vendored as a pre-built static package under
`external/cvc5/cvc5-Linux-x86_64-libcxx-static/` (built against LLVM
`libc++`, **not** GNU `libstdc++`). The harness exposes
`CVC5_INCLUDE_DIR` (with `cvc5/cvc5.h`, `cvc5/cvc5_parser.h`) and
`CVC5_LIBRARY_DIR` (with `libcvc5.a`, `libcvc5parser.a`). See
`fairness_rules.md` §I.3 — your build must use `clang++ -stdlib=libc++`.

You use cvc5 purely as a parser + Term/Sort walker + closed-term
substituter. The auditor blocks every solver entry point.

## 1. Headers and namespace

```cpp
#include <cvc5/cvc5.h>          // Solver, Term, Sort, Kind
#include <cvc5/cvc5_parser.h>   // InputParser, Command, SymbolManager
using namespace cvc5;
```

## 2. Construct & parse — driven command-by-command

cvc5 follows a `setLogic → loop over commands` pattern. You must own
a `Solver` (used as a term factory only — never as a checker) and a
`SymbolManager`:

```cpp
cvc5::Solver         solver;
solver.setLogic("QF_RDL");                  // informational; do NOT enable produce-models
cvc5::SymbolManager  sm(&solver);
cvc5::parser::InputParser ip(&solver, &sm);
ip.setFileInput(cvc5::modes::InputLanguage::SMT_LIB_2_6, "input.smt2");

while (!ip.done()) {
    cvc5::parser::Command cmd = ip.nextCommand();
    if (cmd.isNull()) break;
    cmd.invoke(&solver, &sm);   // executes assert/declare-fun/... into solver+sm
}

const std::vector<cvc5::Term>& asserts = solver.getAssertions();
```

(Older cvc5 releases use `cvc5::parser::Parser` instead of
`InputParser`. This package ships `InputParser`; use it.)

## 3. AST type & traversal — `cvc5::Term`

```cpp
size_t        n  = t.getNumChildren();
for (size_t i = 0; i < n; ++i) {
    cvc5::Term c = t[i];   // operator[](size_t) — *not* getChild
}
cvc5::Kind    k  = t.getKind();
cvc5::Sort    s  = t.getSort();
std::string  text = t.toString();
uint64_t      id = t.getId();
bool          hasSym = t.hasSymbol();
std::string   sym    = t.getSymbol();   // requires hasSymbol()
```

cvc5 exposes both `Term::operator[](size_t)` and `Term::begin()/end()`
iterators; either works for walking.

## 4. Kind enum — `cvc5::Kind` (enumerators without prefix)

```cpp
switch (t.getKind()) {
    case Kind::AND:        ...
    case Kind::LEQ:        ...     // note: LEQ, not LE
    case Kind::LT:         ...
    case Kind::GEQ:        ...     // note: GEQ, not GE
    case Kind::GT:         ...
    case Kind::EQUAL:      ...     // note: EQUAL, not EQ
    case Kind::SUB:        ...
    case Kind::ADD:        ...
    case Kind::NEG:        ...
    case Kind::MULT:       ...
    case Kind::CONST_RATIONAL:
    case Kind::CONST_INTEGER:
    case Kind::VARIABLE:
    case Kind::CONSTANT:
}
```

The exact spelling matters: cvc5 uses `LEQ`/`GEQ`/`EQUAL`, not
`LE`/`GE`/`EQ`. The full list lives in `cvc5/cvc5_kind.h`.

## 5. Sort queries

```cpp
cvc5::Sort s = t.getSort();
bool isReal  = s.isReal();
bool isInt   = s.isInteger();
bool isBool  = s.isBoolean();
```

## 6. Numeral access — exact rationals as strings

cvc5 provides several typed numeric accessors **plus** an arbitrary-
precision string fallback. For the RDL adapter, prefer the string
form so big rationals never overflow:

```cpp
if (t.isRealValue()) {
    std::string lit = t.getRealValue();      // returns "p/q" or decimal
    // pass `lit` straight through to JSON "bound"
}
if (t.isIntegerValue()) {
    std::string lit = t.getIntegerValue();   // decimal text
}
```

Older docs claim `getRealValue()` returns a `std::pair<int64_t,int64_t>`
— that is **wrong** for this header. It returns `std::string`. The
pair-typed accessors are `getReal32Value()` and `getReal64Value()` and
both throw if the rational does not fit in 32/64 bits. Use the string
form unless you have a very strong reason.

`int32_t Term::getRealOrIntegerValueSign() const` returns -1/0/1
without requiring you to commit to a representation; useful for
quick sign checks.

## 7. Closed-term evaluation — `Term::substitute` (§B.5 allowed)

cvc5 supports pre-order substitution at the Term layer:

```cpp
// single-pair form
cvc5::Term plugged = atom.substitute(x, solver.mkReal("3/2"));

// vector form for simultaneous substitution
std::vector<cvc5::Term> vars = {x, y};
std::vector<cvc5::Term> vals = {solver.mkReal("3/2"), solver.mkInteger(0)};
cvc5::Term plugged2 = atom.substitute(vars, vals);
```

This is *one-shot* (no fixpoint) and does **not** consult the SAT/SMT
core — it is pure syntactic rewriting, which is exactly what the
fairness rule §B.5 permits.

## 8. Allowed API surface for this trial

* `cvc5::Solver` (as **term factory** only: `mkReal`, `mkInteger`,
  `mkTerm`, etc.; `setLogic` for informational purposes;
  `getAssertions` to harvest parsed asserts).
* `cvc5::SymbolManager`, `cvc5::parser::InputParser`,
  `cvc5::parser::Command::invoke`.
* `cvc5::Term`: `getKind`, `getSort`, `getNumChildren`,
  `operator[](size_t)`, `begin`/`end`, `getId`, `hasSymbol`,
  `getSymbol`, `toString`.
* Value predicates / accessors: `isRealValue`, `getRealValue`,
  `isIntegerValue`, `getIntegerValue`,
  `getRealOrIntegerValueSign`, `isInt32Value`, `isInt64Value`,
  `isReal32Value`, `isReal64Value` (only the last four return ints
  / pairs; the rest are bool/string).
* `cvc5::Sort::isReal`, `isInteger`, `isBoolean`.
* `Term::substitute` (single-pair and vector forms).

## 9. Forbidden APIs (auditor flags these)

* `Solver::checkSat`, `Solver::checkSatAssuming`.
* `Solver::getValue`, `Solver::getModel`, `Solver::getModelDomainElements`.
* `Solver::simplify` (cross-theory rewriting).
* `cvc5::Optimizer` and `cvc5::Solver::*` optimisation calls.
* Anything from `cvc5::theory::*` — including the built-in DL/IDL
  solver under `theory::arith::idl` that would defeat this case study.

## 10. Gotchas & minimal skeleton

* The parse loop **must** call `cmd.invoke(&solver, &sm)` for each
  command; otherwise `assert`s never reach `solver.getAssertions()`.
* Some logics need `setLogic` *before* parsing — call it explicitly
  with `"QF_RDL"`. Do **not** enable `produce-models` (forbidden).
* `Term::operator[](size_t)` is preferred over `getChild`-style — the
  latter does not exist on `cvc5::Term`.
* Numeral kinds split: `CONST_RATIONAL` for `1.5` / `1/2`,
  `CONST_INTEGER` for `3`. Use `isRealValue` / `isIntegerValue` to
  branch; both return *exact* text.

```cpp
#include <cvc5/cvc5.h>
#include <cvc5/cvc5_parser.h>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 3) { std::cerr << "usage: <in.smt2> <out.json>\n"; return 2; }
    cvc5::Solver        solver;
    solver.setLogic("QF_RDL");
    cvc5::SymbolManager sm(&solver);
    cvc5::parser::InputParser ip(&solver, &sm);
    ip.setFileInput(cvc5::modes::InputLanguage::SMT_LIB_2_6, argv[1]);
    while (!ip.done()) {
        auto cmd = ip.nextCommand();
        if (cmd.isNull()) break;
        cmd.invoke(&solver, &sm);
    }
    for (const cvc5::Term& a : solver.getAssertions()) {
        // walk a with a.getKind(), a[i], etc.
    }
    // write rdl_atoms.json with frontend="cvc5_cpp"
    return 0;
}
```
