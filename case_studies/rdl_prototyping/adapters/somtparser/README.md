# SOMTParser adapter (LLM-trial slot, not implemented)

Status: `not_implemented`. This directory is the start state for the v2 LLM
trial. The hand-written v1 implementation (`main.cpp`, `CMakeLists.txt`, the
v1 README, and the 6 hand-written sanity tests) has been moved to
[`../../_archive/v1_demo/`](../../_archive/v1_demo/) so that the LLM trial
cannot copy from it.

The v2 trial harness is responsible for placing the LLM-generated adapter
under `case_studies/rdl_prototyping/results/runs/somtparser/run_NN/src/`,
not back into this directory. This README is kept only so the directory is
tracked by git as one of the seven recognised front-end slots.

## Adapter contract (every front-end must satisfy)

```
<adapter> input.smt2 output.json
```

The `output.json` payload must conform to
[`schema/rdl_atoms.schema.json`](../../schema/rdl_atoms.schema.json) and have
`"frontend": "somtparser"`.

## Fairness rule

See [`prompts/fairness_rules.md`](../../prompts/fairness_rules.md) for the
authoritative allowed/forbidden API matrix and the dev/test isolation rules.
The shared backend at
[`shared_backend/rdl_backend.py`](../../shared_backend/rdl_backend.py) is the
only component allowed to produce `sat / unsat / unknown`.
