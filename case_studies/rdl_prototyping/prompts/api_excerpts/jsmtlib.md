# jSMTLIB API excerpt — RDL adapter cheat sheet

jSMTLIB (David Cok's reference SMT-LIB v2 parser, packaged under
`external/jsmtlib/`) provides a Java AST hierarchy modelled directly
on the SMT-LIB grammar. The harness exposes `JSMTLIB_ROOT =
external/jsmtlib/` and `JSMTLIB_DIST_ROOT` (the unpacked
distribution; see `fairness_rules.md` §I).

You use jSMTLIB purely as a parser + `IExpr` walker. The auditor
blocks every solver entry point. Maven Central is reachable but the
fairness comparison is against the vendored jars; do not pull a
different version.

## 1. Imports

```java
import org.smtlib.SMT;
import org.smtlib.IParser;
import org.smtlib.ICommand;
import org.smtlib.IResponse;
import org.smtlib.ISource;
import org.smtlib.IExpr;
import org.smtlib.IExpr.IFcnExpr;
import org.smtlib.IExpr.INumeral;
import org.smtlib.IExpr.IDecimal;
import org.smtlib.IExpr.IRational;
import org.smtlib.IExpr.ISymbol;
import org.smtlib.IExpr.ILet;
import org.smtlib.IExpr.IForall;
import org.smtlib.IExpr.IExists;
import org.smtlib.IExpr.IAttributedExpr;
import org.smtlib.command.C_assert;
import org.smtlib.command.C_declare_fun;
import org.smtlib.ISort;
```

The library is split into the `org.smtlib` API surface and
`org.smtlib.command.*` typed command classes. There is **no** kind
enum on `IExpr`; you dispatch with Java's `instanceof`.

## 2. Construct & parse — driven command-by-command

```java
SMT smt = new SMT();
Reader reader = new BufferedReader(new FileReader("input.smt2"));
ISource source = smt.smtConfig.smtFactory.createSource(
    new CharSequenceReader(reader, 100000, 0, 2),
    "input.smt2");
IParser parser = smt.smtConfig.smtFactory.createParser(smt.smtConfig, source);

List<ICommand> commands = new ArrayList<>();
while (!parser.isEOD()) {
    ICommand cmd = parser.parseCommand();
    if (cmd == null) {
        IResponse err = parser.lastError();
        // err may be non-null with details
        continue;
    }
    commands.add(cmd);
}
```

You then walk `commands`, picking out the ones you need:

```java
for (ICommand cmd : commands) {
    if      (cmd instanceof C_declare_fun cf) { /* cf.symbol(), cf.resultSort() */ }
    else if (cmd instanceof C_assert ca)      { walk(ca.expr());                }
}
```

## 3. AST type & traversal — typed via `instanceof`

`IExpr` is the union AST type. jSMTLIB encodes shape information in
**subinterfaces** rather than a kind enum:

| subinterface     | what it represents             | key accessors                                          |
|------------------|--------------------------------|--------------------------------------------------------|
| `IFcnExpr`       | function application `(op args…)` | `head()` → `ISymbol`; `args()` → `List<IExpr>`         |
| `ISymbol`        | a name (variable or operator)  | `value()` → `String`                                   |
| `INumeral`       | integer literal `42`           | `value()` → `BigInteger`                               |
| `IDecimal`       | decimal literal `1.5`          | `value()` → `BigDecimal`                               |
| `IRational`      | rational literal `(/ p q)`     | `numerator()` / `denominator()` → `BigInteger`         |
| `ILet`           | `(let (...) body)`              | `bindings()`, `expr()`                                 |
| `IForall` / `IExists` | quantifier                  | `parameters()`, `expr()`                               |
| `IAttributedExpr`| `(! expr :attr …)`             | `expr()`                                               |

Walking pattern:

```java
void walk(IExpr e) {
    if (e instanceof IFcnExpr fe) {
        String op = fe.head().toString();        // "and", "<=", "<", "-", "+", "=", "*"
        for (IExpr arg : fe.args()) walk(arg);
        // dispatch on `op` string ...
    } else if (e instanceof INumeral n) {
        BigInteger v = n.value();                // exact integer
    } else if (e instanceof IDecimal d) {
        BigDecimal v = d.value();                // exact decimal
    } else if (e instanceof IRational r) {
        BigInteger num = r.numerator();
        BigInteger den = r.denominator();
    } else if (e instanceof ISymbol s) {
        String var = s.value();
    }
    // else: skip / report unsupported
}
```

## 4. "Kind" — operator is a **string**, not an enum

Where Z3 / cvc5 / smt-switch / pySMT all give you a typed enum,
jSMTLIB exposes the operator as the symbol token's text:

```java
String op = ((IFcnExpr) e).head().toString();
switch (op) {
    case "and":  ...
    case "<=":   ...
    case "<":    ...
    case ">=":   ...
    case ">":    ...
    case "=":    ...
    case "-":    ...    // unary or binary, branch on args().size()
    case "+":    ...
    case "*":    ...
    default:     /* unsupported for QF_RDL */
}
```

This is by design — jSMTLIB stays close to the SMT-LIB surface
syntax — and it is one of the case study's expected findings (string
dispatch costs LLM tokens vs. typed enums).

## 5. Sort queries — only on declarations, not on `IExpr`

`IExpr` does not carry a sort. To know whether `x` is `Real`, scan
the parse-time `C_declare_fun` commands and store
`cf.resultSort().toString()` in a map:

```java
Map<String, String> sortOf = new HashMap<>();
for (ICommand cmd : commands) {
    if (cmd instanceof C_declare_fun cf) {
        sortOf.put(cf.symbol().value(), cf.resultSort().toString());  // "Real", "Int", "Bool"
    }
}
```

Then look up `sortOf.get(s.value())` whenever you visit an `ISymbol`.

## 6. Numeral access — `BigInteger` / `BigDecimal` for exactness

```java
String boundText;
if (e instanceof INumeral n) {
    boundText = n.value().toString();             // exact integer text
} else if (e instanceof IDecimal d) {
    boundText = d.value().toPlainString();        // exact decimal text
} else if (e instanceof IRational r) {
    boundText = r.numerator() + "/" + r.denominator();
} else if (e instanceof IFcnExpr neg
           && neg.head().toString().equals("-")
           && neg.args().size() == 1) {
    String inner = renderBound(neg.args().get(0));
    boundText = "-" + inner;
}
```

Always carry this text through to the JSON `bound` field unchanged;
do not convert to `double`.

## 7. Closed-term evaluation — not a first-class API

jSMTLIB exposes printers, command response objects, and parser
hooks, but no AST-level `substitute` / `evaluate`. If you need
substitution for closed-term reduction, you walk and rebuild the
`IExpr` tree yourself by hand, using
`smt.smtConfig.smtFactory.mk*` (`mkNumeral`, `mkSymbol`,
`mkFcnExpr`, …). For a QF_RDL adapter this is almost never needed —
emitting the structural JSON is enough — but it is one of the case
study's expected adapter-SLOC findings.

## 8. Allowed API surface for this trial

* `org.smtlib.SMT`, `smt.smtConfig`, `smt.smtConfig.smtFactory` (used
  only to construct `ISource` and `IParser`, **not** to invoke any
  solver back-end shipped with jSMTLIB).
* `org.smtlib.IParser.parseCommand`, `parser.isEOD`, `parser.lastError`.
* `org.smtlib.IExpr` and all subinterfaces above.
* `org.smtlib.command.C_assert`, `C_declare_fun`, `C_set_logic`,
  `C_define_fun`.
* Standard `java.math.{BigInteger, BigDecimal}`.

## 9. Forbidden APIs (auditor flags these)

* `org.smtlib.solvers.*` — jSMTLIB ships shim solvers for Z3 / cvc4 /
  Yices; all are blocked. Do **not** instantiate
  `org.smtlib.solvers.Solver_test`, `Solver_z3`, etc.
* Any `Runtime.exec` / `ProcessBuilder` that launches an external
  solver.
* `IParser.checkBackground` plus any `IResponse` whose source is an
  invoked solver.
* `smt.executeCommand` if it dispatches `(check-sat)` to a back-end.

## 10. Gotchas & minimal skeleton

* `parser.parseCommand()` returns `null` *and* sets `lastError()` for
  malformed commands; loop on `parser.isEOD()`, not on the return
  value being non-null, and collect errors as you go.
* The operator string is **case-sensitive**: SMT-LIB writes `and` /
  `<=` / `=` in lower-case (with the exception of the symbol `=`
  itself); dispatch on those exact tokens.
* Negative literals come either as a bare `INumeral` whose
  `BigInteger` is already negative (unusual), or as a one-arg
  `IFcnExpr` with `head() == "-"` — handle the second form too.
* For Java >=14 you can use record-style `instanceof IFcnExpr fe`
  patterns; older Java requires the cast on a separate line.

### Build / run

The harness invokes `bash build.sh && bash run.sh input.smt2
output.json`. A typical `build.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
JSMT_LIB="${JSMTLIB_DIST_ROOT}/lib"
mkdir -p build
javac -cp "$JSMT_LIB/*" -d build Adapter.java
```

A typical `run.sh`:

```bash
#!/usr/bin/env bash
JSMT_LIB="${JSMTLIB_DIST_ROOT}/lib"
java -cp "build:$JSMT_LIB/*" Adapter "$@"
```
