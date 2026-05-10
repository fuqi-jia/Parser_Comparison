# Dev-set examples (few-shot anchors)

The harness paths in this section are repository-relative. The dev/test
split is fixed (`scripts/split_dev_test.py`, seed=42, n_dev=30). Only the
**dev** files in this list will be bundled into the LLM prompt; the test
set is held out.

## Few-shot anchor 1 — `check/bignum_rdl1.smt2`  (status: sat, 602 B)

This is the smallest dev file and is the cleanest example of the QF_RDL
fragment your adapter must handle. Verbatim contents:

```smt2
(set-info :smt-lib-version 2.6)
(set-logic QF_RDL)
(set-info :source | SMT-COMP'06 Organizers |)
(set-info :category "check")
(set-info :status sat)
(set-info :notes |This benchmark is designed to check if the DP supports bignumbers.|)
(declare-fun x1 () Real)
(declare-fun x2 () Real)
(declare-fun x3 () Real)
(declare-fun x4 () Real)
(assert (and (<= (- x1 x2) (/ 1 1000000000000000000000000000000000)) (<= (- x2 x3) (/ 1 2000000000000000000000000000000011)) (<= (- x3 x4) (/ (- 1) 1000000000000000000000000000000000)) (<= (- x4 x1) (/ (- 1) 2000000000000000000000000000000012))))
(check-sat)
(exit)
```

Things to notice:

* Top-level `and` of four atoms; each atom is `(<= (- xi xj) c)`.
* Numerals appear as `(/ p q)` and `(/ (- p) q)` where `p`, `q` are very
  large integers (33+ digits). Use exact rationals throughout. The output
  JSON's `bound` field must be a string that Python's
  `Fraction("p/q")` can parse — e.g. `"1/1000000000000000000000000000000000"`
  or `"-1/2000000000000000000000000000000012"`.
* `(check-sat)` and `(exit)` appear at the end of the file. Your adapter
  must **ignore** them; only `(assert …)` blocks and `(declare-fun …)`
  blocks contribute to the JSON output.
* Expected verdict from the shared backend: `sat`.

## Few-shot anchor 2 — `check/bignum_rdl2.smt2`  (status: unsat, 600 B)

Same structure as anchor 1 but the inequalities form a negative cycle.
Expected verdict: `unsat`. This is the canonical "negative cycle" case for
the Floyd–Warshall pass in the shared backend.

## Few-shot anchor 3 — `SMT-Temporal-Planning-Benchmarks/tempo-width-1.smt2`  (status: sat)

Larger temporal-planning encoding. Multiple `assert` commands at the top
level (no outer `and` for some assertions). Some atoms use `>=`, `>`, `=`
and unary bounds like `(<= x 0)` (mapped via the special `ZERO` node, see
`base_task.md`). All variables are `Real`.

## Few-shot anchor 4 — `sal/fischer3-mutex-4.smt2`  (status: unsat)

Mutex encoding from the Fischer protocol. Many small atoms; the assertion
structure mixes ground equalities `(= a b)` with inequalities. The
adapter must split each `(= a b)` into a `<=` pair as `base_task.md`
specifies, and treat strict `<` symbolically (no epsilon arithmetic).

## Few-shot anchor 5 — `scheduling/orb08_700.smt2`  (status: unsat)

Job-shop scheduling encoding with hundreds of difference constraints. A
correct adapter reaches `status: "ok"` on this file with a few hundred
entries in the `constraints` array. This file stresses parsing
performance: streaming token-by-token will be much faster than re-walking
the whole AST per assertion.

## Full dev set

The complete 30-file dev set is enumerated in
`data/dev_index.csv` (one row per file, with columns
`family, relpath, bytes, n_asserts, status, oversize`). The harness will
pass that CSV in the prompt as well, and place the actual `*.smt2`
contents under `data/dev/<family>/...`.

The breakdown by `(family, status)` is fixed by seed:

| family                              | status | count |
|-------------------------------------|--------|-------|
| SMT-Temporal-Planning-Benchmarks    | sat    |   6   |
| check                               | sat    |   1   |
| check                               | unsat  |   1   |
| sal                                 | unsat  |   10  |
| scheduling                          | sat    |   7   |
| scheduling                          | unsat  |   5   |

`skdmxa` and `skdmxa2` are entirely above the oversize threshold and live
in `oversize_index.csv`; they are not used for development or evaluation
in this trial.
