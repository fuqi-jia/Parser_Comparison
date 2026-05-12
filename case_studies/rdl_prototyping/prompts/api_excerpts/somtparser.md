# SOMTParser API excerpt — RDL adapter cheat sheet

SOMTParser is shipped as a git submodule under `SOMTParser/`. This sheet
is paraphrased directly from `SOMTParser/README.md` and the headers
under `SOMTParser/include/somtparser/`. Every symbol below is a real
public symbol of the library; treat anything **not** in this sheet as
nonexistent and re-check before you use it.

## 1. Headers and namespace — only one include is needed

```cpp
#include "somtparser/parser.h"      // umbrella header, includes everything below
using namespace SOMTParser;         // note the leading "O"
```

The single umbrella header re-exports `core/`, `ir/`, `passes/`, and
`frontend/` headers. Do **not** include sub-headers under
`somtparser/core/`, `somtparser/ir/`, etc. directly — they are
implementation paths and there is **no** `somtparser/core/term.h`,
no `somtparser/api/parser.h`, no `somtparser/core/sort.h`. Including
them will fail with "No such file or directory".

The namespace is `SOMTParser`, **not** `SMTParser`. Every symbol below
lives under it.

## 2. Constructing the parser and getting assertions

```cpp
SOMTParser::ParserPtr parser = SOMTParser::newParser();
if (!parser->parse("input.smt2")) {
    std::cerr << "parse error" << std::endl;
    return 1;
}
std::vector<std::shared_ptr<DAGNode>> asserts = parser->getAssertions();
```

* `ParserPtr` is `std::shared_ptr<Parser>` (declared in
  `somtparser/frontend/parser.h`).
* `Parser::parse(const std::string&)` returns `bool` (true == success).
* `Parser::getAssertions()` returns
  `std::vector<std::shared_ptr<DAGNode>>` — the top-level assertion
  list parsed from the file.

## 3. The IR node type — `DAGNode`

The library does **not** expose a type called `TermPtr`. The IR node
type is `DAGNode` and you pass it around as
`std::shared_ptr<DAGNode>`. Two convenience aliases exist:

```cpp
using NodePtr = std::shared_ptr<DAGNode>;   // typedef in ir/dag.h
using Node    = NodePtr;                    // alias in ir/node.h
```

Either spelling is fine.

### 3.1 Member methods you may call

| call                                | returns                              | meaning                                  |
|---|---|---|
| `node->getKind()`                   | `NODE_KIND`                          | top operator / leaf category             |
| `node->getName()`                   | `std::string`                        | variable name **or** numeral literal text|
| `node->getSort()`                   | `std::shared_ptr<Sort>`              | sort of this term                        |
| `node->getChildrenSize()`           | `size_t`                             | number of children                       |
| `node->getChild(int i)`             | `std::shared_ptr<DAGNode>`           | i-th child (0-based)                     |
| `node->getChildren()`               | `std::vector<std::shared_ptr<DAGNode>>` | full child list                       |
| `node->toString()`                  | `std::string`                        | printable form (for error messages)      |

There are no `getNumChildren()` or `getNumeralString()` calls. Numeral
literals are constant `DAGNode`s; their lexical text is just
`getName()`.

### 3.2 Predicate helpers (already defined on `DAGNode`)

These avoid having to spell out `NODE_KIND::NT_*` every time:

```cpp
node->isAnd()           // NT_AND
node->isLe(), isLt(), isGe(), isGt()        // arithmetic comparisons
node->isAdd(), isSub(), isMul(), isNeg()    // arithmetic operators
node->isEq()                                // NT_EQ (including bool/other variants)
node->isVar()                               // any variable kind
node->isConst()                             // any constant kind
node->isNumeral()  // isCInt() || isCReal() — integer or real numeral
node->isCInt(), isCReal()                   // sort-tagged numeral predicates
```

### 3.3 Free functions (alternative spelling, `somtparser/ir/node.h`)

```cpp
SOMTParser::Node n = ...;
NODE_KIND k        = SOMTParser::kind(n);
auto       s       = SOMTParser::sort(n);
size_t     m       = SOMTParser::numChildren(n);
SOMTParser::Node c = SOMTParser::child(n, i);
for (SOMTParser::Node c : SOMTParser::children(n)) { ... }
```

## 4. The kind enum — `NODE_KIND`, enumerators are `NT_*`

```cpp
enum class NODE_KIND {
    NT_UNKNOWN, NT_ERROR, NT_NULL,
    NT_CONST, NT_VAR, NT_CONST_TRUE, NT_CONST_FALSE, ...
    NT_AND, NT_OR, NT_NOT, NT_IMPLIES, NT_XOR,
    NT_EQ, NT_DISTINCT, NT_ITE,
    NT_ADD, NT_NEG, NT_SUB, NT_MUL, ...
    NT_LE, NT_LT, NT_GE, NT_GT,
    ...
};
```

The enumerators you will need for QF_RDL: `NT_AND`, `NT_LE`, `NT_LT`,
`NT_GE`, `NT_GT`, `NT_EQ`, `NT_SUB`, `NT_ADD`, `NT_NEG`, `NT_CONST`,
`NT_VAR`. There is **no** `Kind::AND`, **no** `Kind::LE`, etc. — the
enum class is `NODE_KIND` and the enumerators are prefixed `NT_`.

## 5. Sort queries — `Sort`, `SORT_KIND`

```cpp
auto s = node->getSort();           // std::shared_ptr<Sort>
s->isBool();
s->isInt();
s->isReal();
s->isIntOrReal();   // numeric literal of mixed kind
```

`SORT_KIND` enumerators (`SK_BOOL`, `SK_INT`, `SK_REAL`, ...) exist if
you want a switch, but `isReal()` / `isInt()` / `isBool()` is what you
usually want for an RDL adapter.

## 6. Allowed API surface for this trial

You may use:

* `newParser()`, `Parser::parse(const std::string&)`,
  `Parser::getAssertions()`.
* `DAGNode` accessors `getKind`, `getName`, `getSort`,
  `getChildrenSize`, `getChild`, `getChildren`, `toString`, and the
  `isAnd / isLe / ... / isNumeral / isVar / isConst` predicate
  helpers.
* The free functions in `somtparser/ir/node.h` (`kind`, `sort`,
  `numChildren`, `child`, `children`).
* `Sort::isBool`, `isInt`, `isReal`, `isIntOrReal`.
* `Parser::evaluate(term, model)` — pure rational substitution into an
  AST. This is allowed because it does not consult any solver; it is
  the same kind of evaluation the shared backend would do.

## 7. Forbidden APIs (auditor will flag these)

* `Solver`, `SolverBuilder`, `Solver::checkSat`, `Solver::solve`.
* Anything from `SOMTParser`'s OMT layer that runs an `Optimizer` /
  `ObjectiveManager` solve loop.
* Any built-in DL/IDL/RDL theory entry point shipped under
  `SOMTParser/src/theory/...`.
* Any model API populated by a solver.

## 8. Tips that have actually bitten past attempts

* `(- x y)` may arrive as a binary `NT_SUB` *or* as `NT_ADD` whose
  second child is `(NT_NEG y)` — canonicalise both into `lhs - rhs`.
* Equality `(= a b c)` may arrive as a single `NT_EQ` with `n`
  children, or chained — handle both with a small helper.
* Numeral literals are *exact* rational text; pass `getName()` straight
  through to the JSON `bound` field (no `double`, no rounding).

## 9. Minimal, known-good adapter skeleton

This compiles against `somtparser_static`. Fill in the
`extract_constraint` body for the RDL atoms you actually emit.

```cpp
#include "somtparser/parser.h"
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace SOMTParser;

static void walk(const std::shared_ptr<DAGNode>& n /*, ...emit JSON... */) {
    if (!n) return;
    if (n->isAnd()) {
        for (size_t i = 0; i < n->getChildrenSize(); ++i) {
            walk(n->getChild(static_cast<int>(i)));
        }
        return;
    }
    if (n->isLe() || n->isLt() || n->isGe() || n->isGt() || n->isEq()) {
        // ... inspect n->getChild(0), n->getChild(1), their kinds and names ...
    }
    // ignore other operators / report "unsupported" for QF_RDL
}

int main(int argc, char** argv) {
    if (argc != 3) { std::cerr << "usage: <in.smt2> <out.json>\n"; return 2; }
    ParserPtr parser = newParser();
    if (!parser->parse(argv[1])) {
        std::cerr << "parse failed\n";
        return 1;
    }
    for (const auto& a : parser->getAssertions()) {
        walk(a);
    }
    // ... write rdl_atoms.json to argv[2] ...
    return 0;
}
```

## 10. Where to look in the repo

You may read the public headers under `SOMTParser/include/somtparser/`
**but only via the umbrella include `somtparser/parser.h`**. Do not
read or copy from the v1 demo source under
`case_studies/rdl_prototyping/_archive/v1_demo/` — the auditor checks
for copy-pasted blocks.
