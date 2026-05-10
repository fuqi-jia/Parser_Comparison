# jSMTLIB API excerpt — RDL adapter cheat sheet

jSMTLIB (David Cok's reference SMT-LIB v2 parser, packaged under
`external/jsmtlib/`) provides a Java AST hierarchy modelled directly on
the SMT-LIB grammar. The adapter for this trial is JVM-based and uses
**only** the parser + AST walker. The auditor blocks every solver call.

## Imports

```java
import org.smtlib.SMT;
import org.smtlib.IExpr;
import org.smtlib.IExpr.IFcnExpr;
import org.smtlib.IExpr.INumeral;
import org.smtlib.IExpr.IDecimal;
import org.smtlib.IExpr.IRational;
import org.smtlib.IExpr.ISymbol;
import org.smtlib.ICommand;
import org.smtlib.command.C_assert;
import org.smtlib.command.C_declare_fun;
```

## Allowed APIs

* Parsing:
  * `SMT smt = new SMT();`
  * `smt.smtConfig.smtlib = ".../bin/SMT-LIBv2.6"` (path to the grammar
    bundle shipped under `external/jsmtlib/`).
  * `smt.start();` then iterate the script via the `ICommand` stream.
* AST walking on `IExpr`:
  * `if (e instanceof IFcnExpr fe) { … fe.head().toString(); fe.args(); }`
    — `head()` is the operator symbol (`"and"`, `"<="`, `"<"`, `">="`,
    `">"`, `"="`, `"-"`, `"+"`, `"*"`).
  * `INumeral` (integer literals), `IDecimal` (e.g. `1.5`),
    `IRational` (`(/ a b)`), `ISymbol` (variable names).
* Numeral access: each numeric subclass exposes `value()` (`BigInteger`
  for `INumeral`, `BigDecimal` for `IDecimal`, separate
  numerator/denominator for `IRational`). Concatenate to a `Fraction`-
  parsable string (e.g. `bigInt.toString()`, or `p.toString()+"/"+q`).
* Sort queries: `C_declare_fun.resultSort()` returning an `ISort`; check
  `sort.toString().equals("Real")` for the QF_RDL fragment.

## Forbidden APIs (auditor will flag)

* `org.smtlib.solvers.*` (jSMTLIB ships back-end shims around Z3, cvc4,
  Yices — all blocked).
* Any direct call to an external solver via shell or
  `Runtime.exec` from inside the adapter.
* `SMT::checkSat`, `Solver_test_simplify` etc.

## Build

The adapter lives at `adapters/jsmtlib/` and ships a `build.sh` /
`run.sh` pair similar to ANTLR. The wrapper invocation is identical:

```
./adapters/jsmtlib/run.sh input.smt2 output.json
```

Use the vendored `external/jsmtlib/lib/` jars on the classpath; do not
re-download.
