# pySMT API excerpt — RDL adapter cheat sheet

pySMT exposes a clean Python AST and an SMT-LIB parser. You use **only**
the parser + `FNode` walker. The auditor blocks every solver entry point.

## Imports

```python
from pysmt.smtlib.parser import SmtLibParser
from pysmt.shortcuts import (
    get_env,                     # type info
)
from pysmt.fnode import FNode    # the AST node type
import pysmt.operators as op     # node kinds: AND, LE, LT, EQUALS, MINUS, ...
```

## Allowed APIs

* Parse:
  ```python
  parser = SmtLibParser()
  with open(path, "rt") as f:
      script = parser.get_script(f)
  asserts = [c.args[0] for c in script.commands if c.name == "assert"]
  ```
* AST walking on `FNode`:
  * `node.node_type()` returning constants from `pysmt.operators`
    (`AND`, `LE`, `LT`, `EQUALS`, `MINUS`, `PLUS`, `TIMES`, `SYMBOL`,
    `REAL_CONSTANT`, `INT_CONSTANT`, …).
  * `node.args()` returns a tuple of children.
  * `node.is_symbol()`, `is_constant()`, `is_real_constant()`,
    `is_int_constant()`.
  * `node.symbol_name()` for variables.
  * `node.constant_value()` returns a `Fraction` (rational) or `int`
    directly — perfect, just `str(...)` it for the JSON `bound` field.
* Sort queries: `node.get_type()` → `pysmt.typing.REAL`,
  `pysmt.typing.INT`, `BOOL`. Compare with the symbols
  in `pysmt.typing` rather than string-compare.

## Forbidden APIs (auditor will flag)

* `pysmt.shortcuts.Solver`, `Solver(...).solve()`, `is_sat`, `is_unsat`,
  `get_model`, `get_value`.
* `pysmt.solvers.*` direct imports.
* `pysmt.shortcuts.simplify` (theory rewriting through the back-end).
* `pysmt.cmd.shell` (drives a real solver).

## Tips

* pySMT's parser already collapses `(- x y)` into `MINUS(x, y)` and
  preserves rationals as `Fraction`. So your adapter is mostly a
  recursive walker that emits `{lhs, rhs, bound, strict, source}`.
* For `(= a b c)` (n-ary), `node.node_type() == EQUALS` and
  `node.args()` has length n; split into `n-1` consecutive pairs and
  emit two `<=` constraints per pair as described in `base_task.md`.
* Numerals can already be negative `Fraction`s; do not strip the sign.

## Adapter location

The Python adapter lives at
`adapters/pysmt/extract_rdl.py` and is invoked directly:
`python3 extract_rdl.py input.smt2 output.json`. No CMake target needed.
