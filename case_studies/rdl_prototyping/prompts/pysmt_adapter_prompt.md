# pySMT adapter prompt

> The trial harness has already prepended `base_task.md`,
> `fairness_rules.md`, `api_excerpts/pysmt.md`, and will append
> `dev_examples.md` plus the dev-set bundle. Read those first.

* **Adapter directory:** harness-supplied path of the form
  `case_studies/rdl_prototyping/results/runs/pysmt/run_NN/src/`. Write
  `extract_rdl.py` and a one-line `requirements.txt` (`pysmt==0.9.6`
  or whatever pinned version you need) there.
* **Frontend identifier:** `"pysmt"`.
* **Invocation contract:** the harness will run
  `python3 extract_rdl.py input.smt2 output.json` from your run's
  `src/` directory, after creating a fresh virtualenv and
  `pip install -r requirements.txt`. No CMake target is needed.

## Allowed / forbidden APIs

See `fairness_rules.md` §B–§C and `api_excerpts/pysmt.md`. Summary:
`pysmt.smtlib.parser.SmtLibParser`, `FNode` traversal
(`node_type()`, `args()`, `is_symbol()`, `constant_value()`),
type queries via `node.get_type()`. **No**
`pysmt.shortcuts.Solver`, `is_sat`, `is_unsat`, `get_model`,
`get_value`, or `pysmt.shortcuts.simplify`.

## pySMT-specific subtleties

* `SmtLibParser().get_script_fname(path)` (or `get_script(file_obj)`)
  yields a `SmtLibScript`. The shortest way to harvest assertions is
  `[c.args[0] for c in script.filter_by_command_name(["assert"])]`;
  iterating `script.commands` and filtering on `c.name == "assert"`
  works too.
* `node.constant_value()` already returns a `fractions.Fraction` for
  `is_real_constant()` nodes (and a `int` for `is_int_constant()`);
  `str(...)` it for the JSON `bound` field, no manual reconstruction
  needed.
* Inspect the AST with `node.is_and()` / `is_le()` / `is_lt()` /
  `is_ge()` / `is_gt()` / `is_equals()` / `is_minus()` / `is_plus()`
  / `is_times()` / `is_symbol()` / `is_real_constant()` /
  `is_int_constant()`. These are faster and clearer than a single
  `node.node_type() == op.LE` ladder, but both work.
* For `(>= a b)` and `(> a b)` rewrites, swap and negate as
  `base_task.md` describes; pySMT does **not** automatically
  canonicalise these into `<= / <`.

## Done criteria

1. `python3 extract_rdl.py input.smt2 output.json` writes an
   `rdl_atoms.json` whose `frontend` field equals `"pysmt"`.
2. The static auditor reports 0 violations.
3. The shared backend's verdicts on the dev set match
   `data/dev_index.csv` as closely as possible.
