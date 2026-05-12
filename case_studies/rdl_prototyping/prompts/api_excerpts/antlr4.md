# ANTLR4 API excerpt — RDL adapter cheat sheet

The ANTLR4 front-end is the most "raw" of the seven: there is **no
SMT-LIB parser library**, only a generated ANTLR4 grammar that
produces an untyped parse tree. The harness exposes `ANTLR4_ROOT =
external/antlr4_parser/` (see `fairness_rules.md` §I). That directory
ships:

```
external/antlr4_parser/
├── SMTLIBv2.g4                # official SMT-LIB v2.6 grammar
├── SMTLIBv2Lexer.java         # generated lexer (with .class)
├── SMTLIBv2Parser.java        # generated parser (with .class)
├── SMTLIBv2BaseVisitor.java   # base visitor for typed walks
├── SMTLIBv2BaseListener.java  # base listener for typed walks
├── lib/antlr-4.*-complete.jar # ANTLR runtime + tool
└── Makefile, setup.sh, run.sh
```

Network access is **not available** at trial time, so do not attempt
to download the grammar or jars; everything you need is already
under `${ANTLR4_ROOT}`.

This is intentionally a stress test for "the LLM has to invent the
symbol / sort / numeral layer itself." The fairness rules still apply
(no `check-sat`, no model API, etc.), and with ANTLR alone you have
no solver to call anyway, so this front-end is naturally compliant.

## 1. Imports and entry point

```java
import org.antlr.v4.runtime.CharStream;
import org.antlr.v4.runtime.CharStreams;
import org.antlr.v4.runtime.CommonTokenStream;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.ParseTreeWalker;
// generated:
//   SMTLIBv2Lexer, SMTLIBv2Parser, SMTLIBv2BaseVisitor, SMTLIBv2BaseListener
```

The generated classes live in the **default package** (no `package`
declaration), so import them by simple name. Their `.class` files are
already compiled and shipped — you only need to compile your own
adapter and put both directories on the classpath.

## 2. Construct & parse

```java
CharStream         input  = CharStreams.fromFileName(filename);
SMTLIBv2Lexer      lexer  = new SMTLIBv2Lexer(input);
CommonTokenStream  tokens = new CommonTokenStream(lexer);
SMTLIBv2Parser     parser = new SMTLIBv2Parser(tokens);
ParseTree          tree   = parser.script();    // root rule of SMTLIBv2.g4
```

`parser.script()` returns the root of the parse tree, covering the
entire `(set-logic …)` / `(declare-fun …)` / `(assert …)` /
`(check-sat)` sequence.

## 3. Parse tree type & traversal

Unlike the other six front-ends, ANTLR4 hands you a **generic
`ParseTree`**, not a typed AST. The available API is small but
syntactic:

```java
ParseTree pt = ...;
int       n    = pt.getChildCount();
ParseTree c    = pt.getChild(i);
String    text = pt.getText();                  // concatenated token text
int       rule = ((ParserRuleContext) pt).getRuleIndex();
```

For typed walks, ANTLR generates one visitor method per grammar
rule. Extend `SMTLIBv2BaseVisitor<T>` and override only the rules you
care about:

```java
class MyVisitor extends SMTLIBv2BaseVisitor<Void> {
    @Override
    public Void visitCmd_assert(SMTLIBv2Parser.Cmd_assertContext ctx) {
        // ctx.term() is the asserted formula's parse-tree node
        walkTerm(ctx.term());
        return null;
    }
    // similarly: visitCmd_declareFun, visitCmd_setLogic, ...
}
new MyVisitor().visit(tree);
```

The rule-context class names follow the grammar; commonly useful ones
for QF_RDL adapter:

```
ScriptContext, CommandContext, Cmd_assertContext, Cmd_declareFunContext,
TermContext, Spec_constantContext, NumeralContext, DecimalContext,
QualIdentifierContext, IdentifierContext, SymbolContext
```

## 4. "Kind" enum — there isn't one; you read the operator's text

For SMT-LIB the operator name is just a symbol token inside a
`(qualIdentifier term*)` form. Pull it as text:

```java
String op = ctx.qualIdentifier().getText();     // "and", "<=", "<", "-", "+", "=", ...
```

You must dispatch on these strings yourself. This is the chief
cost-of-entry of ANTLR vs. the other six front-ends and is one of the
adapter-SLOC findings the case study reports.

## 5. Sort queries — read `(declare-fun x () Real)` headers yourself

ANTLR has no theory layer. To know whether `x` is `Real`, scan the
parse tree's `Cmd_declareFunContext` nodes:

```java
@Override
public Void visitCmd_declareFun(SMTLIBv2Parser.Cmd_declareFunContext ctx) {
    String name = ctx.symbol().getText();
    String sort = ctx.sort().getText();         // "Real", "Int", "Bool", ...
    sorts.put(name, sort);
    return null;
}
```

For QF_RDL it is fair to reject anything where the sort is not `Real`
or `Int` (emit `status: "unsupported"`).

## 6. Numeral access — parse the lexical text yourself

ANTLR returns numerals as the original text of `Numeral` / `Decimal`
tokens. Concrete forms you will see in the SMT-LIB corpus:

| token         | example       | what to do                              |
|---------------|---------------|-----------------------------------------|
| `Numeral`     | `3`, `0`      | text is already a decimal integer       |
| `Decimal`     | `1.5`, `0.25` | split on `.` or use BigDecimal          |
| `(/ p q)`     | `(/ 1 2)`     | sub-tree; concatenate `"p/q"`           |
| `(- 5)`       | `(- 5)`       | one-arg `-`; emit `"-5"`                |

Keep the numeric value as a *string* and pass it verbatim to the JSON
`bound` field. **Do not** convert to `double` — that loses exactness.

A safe Java pipeline:

```java
String num = ctx.numeral().getText();           // "3"
String dec = ctx.decimal().getText();           // "0.25"
// rationals are ASTs, handle in the term visitor
```

## 7. Closed-term evaluation — not available; n/a

ANTLR has no notion of substitution, no notion of model, no notion of
"a closed term reduces to a numeral". If your adapter needs that, you
write it yourself on the small typed AST you fold the parse tree
into (see §10). This is one of the case study's expected findings:
the ANTLR adapter ends up implementing a tiny QF_RDL semantics layer
the other adapters get for free.

## 8. Allowed API surface for this trial

* ANTLR runtime: `CharStream`, `CharStreams`, `CommonTokenStream`,
  `Token`, `ParseTree`, `ParseTreeWalker`, `RuleContext`,
  `TerminalNode`.
* Generated `SMTLIBv2Lexer`, `SMTLIBv2Parser`,
  `SMTLIBv2BaseListener`, `SMTLIBv2BaseVisitor` and all rule-context
  classes.
* Standard Java numerics: `java.math.BigInteger`,
  `java.math.BigDecimal` if you need exact arithmetic.

## 9. Forbidden APIs

* Embedding any external SMT solver (Z3 / cvc5 / smt-switch /
  jSMTLIB / pySMT) in the adapter — that would defeat the
  "antlr4-only" comparison point.
* Network calls (Maven Central, GitHub).
* Shelling out to a solver via `Runtime.exec`.

The fairness rules `§B`/`§C` still apply structurally, but with ANTLR
alone you have nothing to call anyway.

## 10. Required deliverables (Java + shell scripts)

Because ANTLR has no built-in numeric reasoning, your adapter must
implement:

1. A small typed AST (4–6 node kinds enough for QF_RDL: `And`,
   `Cmp(op, lhs, rhs, bound)`, `Sub`, `Var(name)`, `Numeral(text)`).
2. Sort tracking from `(declare-fun x () Real)` headers — reject if
   the sort is not `Real`/`Int`.
3. Numeral parsing of decimals, fractions, and signed forms — kept as
   strings, passed verbatim to the JSON `bound` field.

### Build / run

The harness invokes `bash build.sh && bash run.sh input.smt2
output.json`. A typical `build.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ANTLR_JAR="${ANTLR4_ROOT}/lib/antlr-4.13.2-complete.jar"
javac -cp "$ANTLR_JAR:${ANTLR4_ROOT}" \
      -d build \
      Adapter.java \
      "${ANTLR4_ROOT}"/SMTLIBv2{Lexer,Parser,BaseVisitor,BaseListener,Visitor,Listener}.java
```

The pre-compiled `.class` files under `${ANTLR4_ROOT}` are usable
directly; you only need `javac` if you change the grammar (you
should not).

A typical `run.sh`:

```bash
#!/usr/bin/env bash
ANTLR_JAR="${ANTLR4_ROOT}/lib/antlr-4.13.2-complete.jar"
java -cp "build:${ANTLR4_ROOT}:$ANTLR_JAR" Adapter "$@"
```
