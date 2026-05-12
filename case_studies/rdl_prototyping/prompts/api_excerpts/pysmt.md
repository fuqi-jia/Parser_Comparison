# pySMT API excerpt — RDL adapter cheat sheet

pySMT is a Python library installed from PyPI (network access is
permitted at trial time for that purpose, per `fairness_rules.md` §I —
treat PyPI as a fallback, not a primary). The harness invokes the
adapter as a plain `python3 extract_rdl.py input.smt2 output.json`;
no CMake target is needed. **Your adapter must ship a
`requirements.txt` next to `extract_rdl.py` so the harness can
`pip install -r` before invocation.** A typical line is `pysmt>=0.9.5`.

You use pySMT purely as a parser + `FNode` walker + closed-term
substituter. The auditor blocks every solver entry point.

## 1. Imports

```python
from pysmt.smtlib.parser   import SmtLibParser
from pysmt.smtlib.script   import SmtLibScript
from pysmt.environment     import get_env
from pysmt.fnode           import FNode
import pysmt.operators     as op          # AND, LE, LT, EQUALS, MINUS, PLUS, TIMES, SYMBOL, REAL_CONSTANT, INT_CONSTANT, ...
import pysmt.typing        as types       # REAL, INT, BOOL
```

The `pysmt.operators` module holds **integer constants** (not enum
members) for each `FNode` kind — compare with `==`, not `is`.

## 2. Construct & parse — script with typed commands

```python
parser  = SmtLibParser()
script  = parser.get_script_fname("input.smt2")   # parses the entire file
asserts = [c.args[0] for c in script.filter_by_command_name(["assert"])]
# alternative for files with a single (assert ...) at the end:
#   formula = script.get_last_formula()
```

`script` is a `SmtLibScript` with a `.commands` list; every command
has a `.name` (e.g. `"assert"`, `"declare-fun"`) and a `.args` tuple.
`filter_by_command_name(...)` accepts either a single string or a
list.

## 3. AST type & traversal — `FNode`

```python
node = asserts[0]
n    = len(node.args())               # number of children
for c in node.args():
    walk(c)

text = node.serialize()               # SMT-LIB lexical form
nid  = node.node_id()                 # unique id for memoisation / cycle guard
```

Useful shape predicates already on `FNode`:

```python
node.is_symbol()           # free variable
node.is_constant()         # any literal
node.is_real_constant()
node.is_int_constant()
node.is_bool_constant()
node.is_and()
node.is_le() / .is_lt() / .is_ge() / .is_gt()
node.is_equals()
node.is_minus() / .is_plus() / .is_times()
```

These avoid having to spell out `op.LE` etc., and they're much faster
than a single big `if node.node_type() == op.LE` ladder.

## 4. Kind enum — `pysmt.operators` integer constants

For the rare cases where you do want the raw kind:

```python
import pysmt.operators as op
if   node.node_type() == op.AND:     ...
elif node.node_type() == op.LE:      ...
elif node.node_type() == op.LT:      ...
elif node.node_type() == op.MINUS:   ...
elif node.node_type() == op.REAL_CONSTANT: ...
elif node.node_type() == op.INT_CONSTANT:  ...
elif node.node_type() == op.SYMBOL:        ...
```

The full set of constants is the module's source code; it is the
canonical mapping.

## 5. Sort queries

```python
import pysmt.typing as types
t = node.get_type()
is_real = t == types.REAL
is_int  = t == types.INT
is_bool = t == types.BOOL
```

`types.REAL` / `types.INT` / `types.BOOL` are singletons — compare
with `==`, not `is`, just to be safe across reload boundaries.

For the variable name: `node.symbol_name()` (only when
`node.is_symbol()` is true).

## 6. Numeral access — pySMT keeps rationals as **native Python**

`pySMT`'s biggest single advantage for an adapter author is that
numeric literals are already exact and Python-native:

```python
if node.is_real_constant():
    val = node.constant_value()       # fractions.Fraction
    bound_text = str(val)             # e.g. "3/2", "-7", "0"
elif node.is_int_constant():
    val = node.constant_value()       # int
    bound_text = str(val)
```

No string parsing, no overflow handling, no separate numerator /
denominator dance. Pass `bound_text` straight through to the JSON
`bound` field — `Fraction(...)` round-trips it on the backend side.

## 7. Closed-term evaluation — `FNode.substitute` (§B.5 allowed)

```python
from fractions import Fraction
from pysmt.shortcuts import Real, Int

# vars : dict[FNode, FNode]  (symbol -> value FNode)
substituted = atom.substitute({x: Real(Fraction("3/2")),
                               y: Int(0)})
# `substituted` is an FNode with no remaining free variables.
# It is NOT theory-simplified, only syntactically rewritten.
```

`FNode.substitute` walks once, in pre-order, and produces a new node
tree. It does not consult a solver and does not invoke
`pysmt.shortcuts.simplify`, which would be forbidden.

## 8. Allowed API surface for this trial

* `pysmt.smtlib.parser.SmtLibParser` — `get_script(file)`,
  `get_script_fname(path)`.
* `pysmt.smtlib.script.SmtLibScript` — `.commands`,
  `.filter_by_command_name(...)`, `.get_last_formula()`,
  `.get_declared_symbols()`.
* `pysmt.fnode.FNode` — `args`, `arg(i)`, `node_id`, `node_type`,
  `serialize`, `is_*` predicates, `symbol_name`, `constant_value`,
  `get_type`, `substitute`.
* `pysmt.operators` constants.
* `pysmt.typing.REAL`, `INT`, `BOOL`.
* `pysmt.shortcuts.Real`, `Int`, `Symbol`, `And`, `LE`, `LT`, `Minus`,
  `Plus`, `Times`, `Equals` — strictly as **constructors** to build
  substitution values; not as `solve()`-bearing helpers.

## 9. Forbidden APIs (auditor flags these)

* `pysmt.shortcuts.Solver`, `Solver(...).solve()`, `is_sat`,
  `is_unsat`, `is_valid`, `get_model`, `get_value`.
* `pysmt.shortcuts.simplify` and `FNode.simplify` (theory rewriting).
* `pysmt.solvers.*` direct imports — including
  `pysmt.solvers.z3.Z3Solver`, `pysmt.solvers.cvc5.CVC5Solver`, etc.
* `pysmt.cmd.shell` (drives a real solver).
* Anything that runs a theory simplifier or model construction.

## 10. Gotchas & minimal skeleton

* `(- x y)` arrives as `op.MINUS` (binary). `(+ x y z)` arrives as
  `op.PLUS` (n-ary). Both can appear in nested mixed shapes; flatten
  with a tiny helper before extracting `lhs - rhs`.
* `(= a b c)` arrives as `op.EQUALS` with `n` children; chain into
  `n-1` consecutive `<=` ∧ `>=` pairs as described in `base_task.md`.
* `Fraction(0)` stringifies as `"0"`, not `"0/1"`; the backend accepts
  both, but be consistent inside the adapter.
* Do **not** create a `pysmt.shortcuts.Solver` to "introspect" types —
  the auditor flags the import. Use `node.get_type()` and the
  `pysmt.typing` singletons instead.

```python
#!/usr/bin/env python3
# file: extract_rdl.py
import sys, json
from fractions import Fraction
from pysmt.smtlib.parser import SmtLibParser
from pysmt.fnode         import FNode

def walk(node, out):
    if node.is_and():
        for c in node.args(): walk(c, out)
        return
    if node.is_le() or node.is_lt() or node.is_ge() or node.is_gt() or node.is_equals():
        # inspect node.args()[0] / [1], their kinds & constant_value()
        pass
    # else: report "unsupported" for QF_RDL

def main(in_smt2: str, out_json: str) -> int:
    parser  = SmtLibParser()
    script  = parser.get_script_fname(in_smt2)
    asserts = [c.args[0] for c in script.filter_by_command_name(["assert"])]
    out = {"status": "ok", "frontend": "pysmt", "mode": "rdl",
           "variables": [], "constraints": []}
    for a in asserts:
        walk(a, out)
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
```

And the matching `requirements.txt`:

```
pysmt>=0.9.5
```
