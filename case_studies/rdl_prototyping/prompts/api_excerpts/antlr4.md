# ANTLR4 API excerpt — RDL adapter cheat sheet

The ANTLR4 front-end is the most "raw" of the seven: there is no SMT-LIB
parser library at all, just a generated grammar that produces a parse
tree. The trial assumes you start from the SMT-LIB v2.6 grammar already
checked into `external/antlr4/grammar/SMTLIBv2.g4` (or download the
official grammar from the SMT-LIB site if absent).

This adapter is intentionally a stress test for "the LLM has to invent
the symbol/sort layer itself".

## Allowed APIs (Java + ANTLR runtime)

* `org.antlr.v4.runtime.CharStreams.fromFileName(...)`.
* `SMTLIBv2Lexer` and `SMTLIBv2Parser` (generated from the grammar) plus
  the parse-tree walkers: `ParseTreeWalker`, listener / visitor classes.
* `ParseTree::getChild(i)`, `getText()`, `getRuleIndex()`.
* `Token::getText()`, `getType()`.
* The generated `BaseVisitor<T>` to fold the parse tree into an internal
  AST that you implement (small, ~5 node kinds enough for QF_RDL).

## Forbidden APIs (auditor will flag)

* Embedding any external SMT solver (Z3 / cvc5 / smt-switch) in the
  adapter — that would defeat the "antlr4-only" comparison point.
* Network calls.

The fairness rules in `fairness_rules.md` still apply: no `check-sat`,
no model API, no theory simplification. With ANTLR alone you have no
solver to call anyway, so this front-end is naturally compliant.

## Required deliverables

Because ANTLR has no built-in numeric reasoning, your adapter must
implement:

1. A small typed AST (4–6 node kinds: `And`, `Cmp(op, lhs, rhs, bound)`,
   `Sub`, `Var(name)`, `Numeral(string)`).
2. Sort tracking from `(declare-fun x () Real)` headers — reject if the
   sort is not `Real`/`Int`.
3. Numeral parsing of decimals, fractions, and signed forms — keep them
   as strings to be passed verbatim to the JSON `bound` field; do **not**
   convert to `double`.

## Build

The adapter lives at `adapters/antlr4/` and ships a small `build.sh`
that runs `antlr4 -Dlanguage=Java SMTLIBv2.g4` and `javac`. The wrapper
script `adapters/antlr4/run.sh` is what the harness invokes:

```
./adapters/antlr4/run.sh input.smt2 output.json
```

A Python ANTLR runtime variant is also acceptable; produce a
`adapters/antlr4/extract_rdl.py` wrapper instead. Whichever you pick,
keep the binary contract identical.
