# cvc5 C++ API excerpt — RDL adapter cheat sheet

cvc5 ships both a low-level `cvc5::Solver` API and a higher-level
`cvc5::parser` namespace. For this trial you must use **only** the parser
+ Term/Sort traversal layer; the auditor blocks all solver and model
entry points.

## Headers

```cpp
#include <cvc5/cvc5.h>
#include <cvc5/cvc5_parser.h>     // cvc5::parser::Parser, InputParser
```

## Allowed APIs

* Parser construction:
  * `cvc5::TermManager tm;`
  * `cvc5::parser::Parser parser{&tm, …};`
  * `parser.setLogic("QF_RDL")` — for context only; do not call
    `setOption("produce-models", true)`.
  * `parser.appendIncrementalStringInput(text)` /
    `parser.parseAndExecute()`.
  * In recent cvc5 versions, the `cvc5::parser::InputParser` wrapper is
    cleaner: `InputParser ip(&tm); ip.setStringInput(...); auto cmd =
    ip.nextCommand(); ...`.
* AST traversal on `cvc5::Term`:
  * `Term::getKind()` → `cvc5::Kind` enum
    (`AND`, `LEQ`, `LT`, `GEQ`, `GT`, `EQUAL`, `SUB`, `ADD`, `NEG`,
    `MULT`, `CONST_RATIONAL`, `CONST_INTEGER`, `VARIABLE`, …).
  * `Term::getNumChildren()`, `operator[](size_t)`, `getId()`,
    `toString()`.
  * `Term::isVariable()`, `isConst()`.
* Sort queries: `Term::getSort()`, `Sort::isReal()`, `isInteger()`,
  `isBoolean()`.
* Numeral access:
  * `Term::getRealValue()` returning a `std::pair<int64_t,int64_t>` for
    small rationals, or
  * `Term::getRealOrIntegerValueSign()` and the string accessor — use the
    string form for big numerals to avoid overflow.

## Forbidden APIs (auditor will flag)

* `cvc5::Solver`, `Solver::checkSat`, `Solver::checkSatAssuming`.
* `Solver::getValue`, `getModel`, `getModelDomainElements`.
* `cvc5::Optimizer`.
* `Solver::simplify` if it crosses theory-rewrite boundaries (the
  auditor flags any call regardless of arguments to be safe).
* Anything under `cvc5::theory::arith::idl` — that is cvc5's own DL
  solver, which would defeat the case study.

## Tips

* You can build cvc5 in parser-only mode by linking against the
  `cvc5parser` static library + `cvc5` for the term manager. See the
  vendored `external/cvc5/` README for `cmake` invocation flags. Do not
  modify `external/cvc5/`.
* `CONST_RATIONAL` terms contain numerator / denominator separately;
  using `Term::getRealValue()` returns `(p, q)`. Pass `f"{p}/{q}"`
  through to the JSON `bound` field.
