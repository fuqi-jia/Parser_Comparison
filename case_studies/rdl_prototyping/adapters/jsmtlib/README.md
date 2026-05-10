# jSMTLIB (JVM) adapter (LLM-trial slot, not implemented)

Status: `not_implemented`. This directory is the start state for the v2
LLM trial. It is intentionally empty (apart from this README) so the LLM
cannot copy a hand-written reference and must build the adapter from the
prompt + the fairness rules.

The v2 harness places each LLM-generated adapter under
`case_studies/rdl_prototyping/results/runs/jsmtlib/run_NN/src/`,
not back into this directory. This README only exists so the directory
is tracked by git as one of the seven recognised front-end slots.

## Adapter contract

```
<adapter> input.smt2 output.json
```

The `output.json` payload must conform to
[`schema/rdl_atoms.schema.json`](../../schema/rdl_atoms.schema.json) and
have `"frontend": "jsmtlib"`.

## Fairness rule

See [`prompts/fairness_rules.md`](../../prompts/fairness_rules.md) for
the authoritative allowed / forbidden API matrix and the dev/test
isolation rules. The shared backend at
[`shared_backend/rdl_backend.py`](../../shared_backend/rdl_backend.py)
is the only component permitted to produce `sat / unsat / unknown`.
