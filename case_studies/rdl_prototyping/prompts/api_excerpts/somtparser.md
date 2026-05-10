# SOMTParser API excerpt — RDL adapter cheat sheet

SOMTParser is shipped as a git submodule under `SOMTParser/` and is what
the rest of `Parser_Comparison` uses as its native parser. For this trial
you may use **only** the parsing / AST surface; the auditor enforces this.

## Headers and namespaces

```cpp
#include "somtparser/parser.h"
#include "somtparser/api/parser.h"
#include "somtparser/core/term.h"
#include "somtparser/core/sort.h"
#include "somtparser/core/kind.h"
using namespace SMTParser;        // typical
```

## Allowed APIs

* `Parser` / `ParserBuilder` from `somtparser/api/parser.h` — construct a
  parser, drive it from a file path or a string.
* `Parser::getAssertions()` (or equivalent) returning a vector of
  `TermPtr` — the top-level assertion list.
* `TermPtr::getKind()` returning a `Kind` enum (e.g. `Kind::AND`,
  `Kind::LE`, `Kind::LT`, `Kind::GE`, `Kind::GT`, `Kind::EQ`,
  `Kind::SUB`, `Kind::ADD`, `Kind::MUL`, `Kind::CONST`, `Kind::VAR`,
  `Kind::NUMERAL` — names may differ slightly; consult the public header).
* `TermPtr::getChildren()` / `getNumChildren()` / `getChild(i)`.
* `TermPtr::getName()` for variable / constant names.
* `TermPtr::getNumeralString()` (or the equivalent rational accessor)
  returning the *exact* numeric literal as text.
* `TermPtr::getSort()`, `Sort::isReal()`, `Sort::isInt()`, `Sort::isBool()`
  for sort queries.
* `Parser::evaluate(term, model)` — pure rational substitution into an
  AST. This is allowed because it does not consult any solver; it is the
  same kind of evaluation the shared backend would do.

## Forbidden APIs (auditor will flag these)

* `Solver`, `SolverBuilder`, `Solver::checkSat`, `Solver::solve`.
* `Optimizer`, any optimisation tactic.
* Calls into a built-in DL/IDL/RDL theory solver shipped under
  `SOMTParser/src/theory/...`.
* Any model API that is populated by a solver.

## Tips

* SOMTParser keeps numerals as exact rationals; round-tripping
  `getNumeralString()` to `Fraction(...)` in Python is lossless.
* Equality `(= a b c)` may arrive either as a single `Kind::EQ` with
  `n` children or as a chain — handle both with a small helper.
* The parser may normalise `(- x y)` and `(+ x (- y))` differently; the
  adapter should canonicalise both into `lhs - rhs`.

## Where to look in the repo

You may read public headers under `SOMTParser/include/somtparser/`. Do
not read or copy from the v1 demo source under
`case_studies/rdl_prototyping/_archive/v1_demo/` — the auditor checks for
copy-pasted blocks.
