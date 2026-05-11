# Base task: build an RDL front-end adapter for a fair LLM trial

This document is concatenated verbatim before every per-front-end prompt
(`<frontend>_adapter_prompt.md`). The trial harness assembles the final
prompt as:

```
base_task.md
  + fairness_rules.md
  + api_excerpts/<frontend>.md
  + <frontend>_adapter_prompt.md
  + dev_examples.md
  + (full text of every *.smt2 in data/dev/, plus data/dev_index.csv)
```

A fixed total token budget is enforced (see `config/llm.yaml`).

## Repository

You are working inside
[`fuqi-jia/Parser_Comparison`](https://github.com/fuqi-jia/Parser_Comparison),
specifically inside `case_studies/rdl_prototyping/`. Do **not** modify
any submodule under `external/` or under `SOMTParser/`.

You may write only to:

* a fresh adapter source directory specified in
  `<frontend>_adapter_prompt.md`, normally
  `case_studies/rdl_prototyping/results/runs/<frontend>/run_NN/src/`.

You **must not**:

* read or copy from any other adapter directory under
  `case_studies/rdl_prototyping/adapters/<other-frontend>/`,
* read the shared backend at
  `case_studies/rdl_prototyping/shared_backend/`,
* read the v1 demo archive under
  `case_studies/rdl_prototyping/_archive/v1_demo/`,
* read or peek at the final test set under
  `case_studies/rdl_prototyping/data/test/` or the
  `data/test_index.csv`,
* read any other file listed in the repository's `.llmtrialignore`.

The trial harness has already withheld these paths from this prompt; the
auditor will reject your submission if the produced source contains
copy-pasted blocks that match any of them.

## Goal

Implement a single front-end adapter for a paper case study about how
useful different SMT-LIB front ends are for prototyping a small theory
solver. The fragment is **QF_RDL — Real Difference Logic, conjunction
only**. You are responsible for the *parsing + RDL atom extraction*
layer; a fixed shared backend then computes `sat / unsat / unknown`.

## Adapter contract (single, fixed)

```
<adapter> input.smt2 output.json
exit 0  ⇒  output.json was written
```

`output.json` must conform to
`case_studies/rdl_prototyping/schema/rdl_atoms.schema.json` (you have
that schema in your prompt as plain English below; you do **not** read
the schema file directly). The required `frontend` identifier is given
in the per-front-end prompt.

The shared backend at `case_studies/rdl_prototyping/shared_backend/` is
the **only** component permitted to print `sat / unsat / unknown`.
Adapters never spawn or link to it. The trial harness pipes between the
two.

## Hard rules

1. **No solver invocation.** See `fairness_rules.md` §B–§C for the
   exact whitelist / blacklist of front-end APIs. Pure parsing, AST
   walking, sort queries, numeral introspection, and *external*
   evaluation (closed-term substitution into your own AST) are allowed;
   `check-sat`, optimisation, theory simplification, model APIs, UNSAT
   cores, and SAT-solver invocations are forbidden.
2. **Honesty.** If your front-end's API does not give you something you
   need (sorts, exact rationals, …), emit `status: "unsupported"` (or
   `"error"`) with a truthful `reason` and exit 0. The shared backend
   turns those into `unknown`. **Never invent a verdict.**
3. **No code reuse from other adapters.** Adapter SLOC is one of the
   metrics. Copying logic between adapters would contaminate it.
4. **Never read the test set.** Only the dev set under `data/dev/` is
   available to you. The harness stages it for you and lists every dev
   file in the prompt.

## P0 fragment (mandatory for this trial)

A QF_RDL formula (after flattening top-level `assert` blocks and outer
`and` connectives) is a conjunction of atoms of the form

```
lhs - rhs  (op)  bound
```

where `op ∈ {≤, <, ≥, >, =}`, `lhs` and `rhs` are **distinct** real
variables (or the special `ZERO` node for unary bounds), and `bound`
is a rational numeral.

Concretely, accept these surface forms:

* `(<= (- x y) c)`, `(< (- x y) c)`, `(>= (- x y) c)`, `(> (- x y) c)`,
  `(= (- x y) c)`
* `(<= x c)`, `(>= x c)`, `(= x c)` (unary, mapped via the special
  `ZERO` node — synthesise a single `ZERO` variable that the shared
  backend interprets as the constant 0)
* Nested `(<= (+ x (* (- 1) y)) c)` shapes that normalise to the same
  `lhs - rhs ≤ c`.

Top-level structure:

* `set-logic QF_RDL` / `QF_LRA` / no `set-logic` (treat any of these as
  acceptable; reject other logics with `status: "unsupported"`).
* `declare-const x Real`, `declare-fun x () Real`. Reject Int / BV / FP
  / String / Array / function declarations as `"unsupported"`.
* Multiple `assert` commands, each one optionally wrapped in a top-level
  `and` of atoms.
* `(check-sat)`, `(exit)`, `set-info`, `set-option`, `push`/`pop` may
  appear and must be ignored.

Reject everything else with `status: "unsupported"` and a truthful
`reason`:

* `or / not / implies / xor / ite` (any non-conjunctive Boolean
  structure inside an assertion).
* quantifiers (`forall`, `exists`).
* arrays / BV / FP / strings / sequences / sets.
* uninterpreted functions.
* non-linear arithmetic (multiplication of two variables, division by a
  non-constant).

## Strict inequalities (no epsilon)

Track strictness **symbolically**, not via epsilon perturbation. Each
constraint is `lhs - rhs (≤ | <) bound` and is serialised as
`{lhs, rhs, bound, strict}`. The shared backend uses a lattice of pairs
`(value, strict)` so equality and strict bounds compose correctly.

Convert `>=` and `>` to `≤` / `<` form by swapping `lhs` and `rhs` and
negating `bound`:

```
(>= (- x y) c)   ≡   (<= (- y x) (- c))
(>  (- x y) c)   ≡   (<  (- y x) (- c))
```

## Equality

Split `(= a b)` into the pair `(<= (- a b) 0)` and `(<= (- b a) 0)`.
For an n-ary `(= a b c)` chain it accordingly.

Equality of two non-arithmetic terms (e.g. Boolean iff) is unsupported.

## Numerals

Pass numerals to the backend as `Fraction`-parsable strings:

* `"3"`, `"-2"`, `"3.5"`, `"-0.25"`, `"7/2"`, `"-7/2"`,
  `"1/1000000000000000000000000000000000"`, `"-1/2000…012"`.

Use exact rationals throughout. **Never** route a literal through a
double / float. Big rationals (33+ digits) appear in the dev set; see
`dev_examples.md` anchor 1.

## Output JSON

### Successful extraction (mode = "conjunction")

```json
{
  "status": "ok",
  "frontend": "<frontend-id>",
  "mode": "conjunction",
  "variables": ["x", "y", "ZERO"],
  "constraints": [
    {"lhs": "x", "rhs": "y", "bound": "3",  "strict": false,
     "source": "(<= (- x y) 3)"},
    {"lhs": "y", "rhs": "x", "bound": "-1", "strict": true,
     "source": "(<  (- y x) -1)"}
  ]
}
```

* `variables` is a deduplicated, sorted list of all variable names that
  appear in any constraint, plus `ZERO` if you used it.
* `constraints` is order-preserving (the order in which atoms were
  encountered while walking the assertion list).
* `source` is the front-end's `to_string()` of the original atom (or a
  best-effort reconstruction). It is logged for human debugging only;
  the backend ignores it.

### Out of fragment

```json
{
  "status": "unsupported",
  "frontend": "<frontend-id>",
  "reason": "non-conjunctive Boolean structure",
  "detail": "encountered Z3_OP_OR at top level"
}
```

### Adapter / parser error

```json
{
  "status": "error",
  "frontend": "<frontend-id>",
  "reason": "parse failed",
  "detail": "syntax error at line 42: unexpected token ..."
}
```

## Tests you must aim to pass

The dev set lives in `case_studies/rdl_prototyping/data/dev/` and is
indexed by `data/dev_index.csv` (also embedded in this prompt). Five
hand-picked anchor files are detailed in `dev_examples.md`. The trial
harness will:

1. build your adapter,
2. run it on every dev file,
3. compare the shared backend's verdict to the `status` column of
   `dev_index.csv` (`sat`/`unsat`),
4. show you, on each fix iteration, the build log, up to N failing
   files (with the JSON your adapter produced and the verdict the
   backend then derived), and the static auditor's report.

Up to **K=3** fix iterations are allowed (see `config/llm.yaml`). After
the K-th iteration the harness flips to the held-out **test set** and
records the final metrics; you do not see the test set during the
trial.

## Where the adapter lives

* C++: write `main.cpp` and a `CMakeLists.txt` in your run's `src/`
  directory. The harness runs `cmake -S . -B build -D<KEY>=<PATH>...`
  *inside that directory* (no top-level CMake involvement); see
  `fairness_rules.md` §I for the vendored-dependency variables it
  passes in.
* Python: write `extract_rdl.py` plus a `requirements.txt` listing only
  the front-end you need (e.g. `pysmt==0.9.6`). The harness creates a
  per-run venv and runs `pip install -r requirements.txt` against
  public PyPI before exec'ing `python3 extract_rdl.py input.smt2
  output.json`, so adding `pysmt` (or any pip-installable dep your
  adapter needs) is fine.
* JVM: write a `build.sh` that compiles your sources using the
  vendored jars under `${ANTLR4_ROOT}/lib/` or
  `${JSMTLIB_DIST_ROOT}/lib/`, plus a `run.sh input.smt2 output.json`
  wrapper. The harness invokes `run.sh`. Maven Central is not part
  of the trial contract — rely on vendored jars only.

## Delivery format (read carefully)

Each iteration you reply with **file blocks**, plus a short prose
preamble if you like (≤ a few sentences). The harness extracts files
and ignores the rest. Two equivalent forms are accepted — pick whichever
you find most natural, the parser tolerates both. Paths are interpreted
**relative to your run's `src/` directory**; do not prepend
`case_studies/...` or `results/runs/...`.

### Form A — XML-style (preferred for unambiguous parsing)

```
<file path="extract_rdl.py">
#!/usr/bin/env python3
import sys, json
...
</file>

<file path="requirements.txt">
pysmt==0.9.6
</file>
```

### Form B — Markdown-fenced (also accepted)

The **first** line inside the fence MUST be a comment of the form
`# file: <path>` (or `// file: <path>` for C/C++/Java); without it the
block is treated as ordinary documentation and discarded.

````
```python
# file: extract_rdl.py
#!/usr/bin/env python3
import sys, json
...
```

```text
# file: requirements.txt
pysmt==0.9.6
```
````

Rules common to both forms:

* One block per file. Multiple blocks for the same path overwrite in
  source order (last one wins); avoid that if you can.
* Do not emit absolute paths or `..` segments — they are rejected as
  unsafe.
* If you change nothing in a fix iteration, you may re-emit the whole
  file unchanged so the harness records a no-op turn; sending an empty
  response ends the trial.

## Out of scope for this trial

A future iteration will extend the case study to Boolean RDL via a
CaDiCaL user propagator (IPASIR-UP). The schema already reserves
`mode: "boolean"`, `cnf`, and `atoms` fields, but you should **not**
implement that layer in this trial.
