# v1 demo archive — DO NOT REGISTER WITH THE TRIAL HARNESS

This directory holds the hand-written v1 demo:

* `adapters/somtparser/` — the original hand-coded SOMTParser adapter
  (`main.cpp` + `CMakeLists.txt` + the v1 README).
* `tests/` — 6 hand-written `.smt2` sanity files plus `expected.csv`.
* `scripts/` — the v1 `reproduce.sh` harness and its companion Python
  scripts (`run_one_adapter.py`, `run_all_adapters.py`, `score_runs.py`,
  `gen_table1.py`).

## Why is it here

In v2 we run a fair LLM trial: every front-end adapter is generated from
scratch by the LLM. To preserve fairness, *no LLM and no v2 harness script*
must ever read this directory:

1. It contains a working SOMTParser adapter — copying it would obviously
   bias the SOMTParser front-end relative to others.
2. It contains the small hand-crafted test suite. The v2 dev/test split is
   drawn from the QF_RDL benchmark; mixing in these toy files would distort
   pass-rate metrics.

The v2 isolation policy is enforced in three layers:

* `.llmtrialignore` (repo root) lists this directory so prompt-bundling
  cannot pick it up.
* The top-level `CMakeLists.txt` no longer adds the v1 SOMTParser
  subdirectory; only `BUILD_RDL_LLM_ADAPTERS=ON` will pick up
  `results/runs/*/run_*/src/CMakeLists.txt`.
* `parser_comparison.sh rdl-case-study` is now a deprecation notice that
  exits non-zero.

If you want to inspect the v1 demo by hand, do so out-of-tree (e.g. copy to
`/tmp`); never run it from inside the live workspace while a trial is in
flight.
