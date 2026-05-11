# Case study notes (paper-facing, v2)

This document is for the paper authors. It captures, in plain language,
what v2 of the case study delivers, what it deliberately leaves out, and
which sentences in the manuscript may need to be weakened depending on
how many real LLM runs we end up reporting.

## What v2 delivers

* **A shared RDL backend, in two implementations that must agree.**
  The paper-grade implementation is C++ (GMP + Floyd–Warshall over
  symbolic strict bounds) at [`shared_backend/cpp/`](shared_backend/cpp/);
  the trial harness exclusively calls the compiled binary
  `shared_backend/cpp/build/rdl_backend`. The Python file
  [`shared_backend/rdl_backend.py`](shared_backend/rdl_backend.py) is
  kept as an executable *reference specification* (~240 LoC) and is the
  source of truth for the semantics. Strict inequalities are tracked
  symbolically as `(value, strict)` pairs; the verdict is decided by
  Floyd–Warshall negative-cycle detection over a graph of difference
  constraints. The two backends must produce identical verdicts on
  every payload — [`scripts/test_backend.py`](scripts/test_backend.py)
  enforces this on a built-in 100-instance self-test set (see next
  bullet) and the harness records both the binary path and its SHA-256
  in every trial's `meta.json`.
* **A 100-instance self-test set.**
  [`scripts/gen_synth_rdl.py`](scripts/gen_synth_rdl.py) generates 100
  conjunction-only QF_RDL instances under
  [`data/synth/`](data/synth/) (5 difficulty buckets:
  tiny / small / medium / large / edge; sat ≈ unsat) along with a
  hand-constructed ground-truth label per instance. The label is
  produced *by construction* (sat: realised by a concrete assignment;
  unsat: built around an injected negative cycle), so it never depends
  on any solver. The self-test script then requires three-way
  agreement (Python ref / C++ binary / `.expect`) on all 100; this is
  the gate that catches regressions in either backend.
* **A real benchmark.** The QF_RDL division of SMT-LIB (255 files, six
  families) is unpacked from `benchmark/QF_RDL.tar.zst` and split into a
  30-file dev set and a 123-file test set with `seed=42`, stratified by
  `(family, status)`. The remaining 102 files are excluded for being
  oversize (`>=256 KiB`) or having `status=unknown` upstream. See
  [`README.md`](README.md) for the breakdown.
* **A fair LLM trial protocol.** Each front-end adapter is generated
  from scratch by an LLM under a fixed prompt budget (24 000 tokens) and
  a fixed iteration budget (`K=3` fix iterations). The trial harness
  enforces the prompt allow-list, persists the entire conversation +
  every intermediate source tree + every per-file JSON, and never
  rewrites a directory once it has been written.
* **A static fairness auditor**
  ([`scripts/audit_adapter.py`](scripts/audit_adapter.py)) that scans
  the produced source for forbidden symbols (front-end-specific solver,
  optimisation, and model APIs; v1-demo byte-identical copies). It is
  run on every iteration and on every aggregated run.
* **Mock-LLM mode by default** so that the entire pipeline is
  exercisable on a fresh checkout without an API key. The real-LLM
  modes (`provider=openai`, `provider=anthropic`) require the
  corresponding API-key env var; the harness fails fast otherwise.
* **An aggregator** that reads all `meta.json` files under
  `results/runs/<frontend>/run_NN/` and emits
  `results/aggregate/{summary.csv, per_frontend.csv,
  table_paper.{md,tex}}` without touching any run dir.
* **A CLI front door**:
  `parser_comparison.sh rdl-{prepare-data,llm-campaign,aggregate,audit}`.

## v1 → v2 changeset (so the diff makes sense)

* The hand-written SOMTParser adapter, the 6-file sanity test suite, the
  `reproduce.sh` harness, and the v1 helper scripts (`run_one_adapter.py`,
  `run_all_adapters.py`, `score_runs.py`, `gen_table1.py`) have moved to
  [`_archive/v1_demo/`](_archive/v1_demo/). They are explicitly hidden
  from the v2 harness and the LLM via [`.llmtrialignore`](../../.llmtrialignore).
* `BUILD_RDL_CASE_STUDY` is now a deprecation no-op; LLM-generated
  adapters are picked up by `BUILD_RDL_LLM_ADAPTERS` (see
  [`/CMakeLists.txt`](../../CMakeLists.txt)).
* `parser_comparison.sh rdl-case-study` now exits non-zero with a pointer
  to the four v2 commands.

## Reproduction commands

```bash
# 1) one-time data prep (idempotent):
./parser_comparison.sh rdl-prepare-data

# 2) edit case_studies/rdl_prototyping/config/llm.yaml — set provider,
#    model, api_key_env. Default config/llm.yaml.example uses provider=mock,
#    which never makes a network call.

# 3) run trials (defaults: 10 trials per front-end):
./parser_comparison.sh rdl-llm-campaign --frontends pysmt --trials 10

# 4) build paper tables:
./parser_comparison.sh rdl-aggregate
#    -> results/aggregate/summary.csv
#       results/aggregate/per_frontend.csv
#       results/aggregate/table_paper.md
#       results/aggregate/table_paper.tex

# 5) ad-hoc audit on any single src dir:
./parser_comparison.sh rdl-audit \
    --src case_studies/rdl_prototyping/results/runs/pysmt/run_00/src/turn_00 \
    --frontend pysmt
```

## Honesty rules (please respect these in the manuscript)

* The fairness rule is a one-sentence-fix-or-quote-it-everywhere thing.
  Use:

  ```latex
  The solver-native engines of Z3 and cvc5 were not invoked; each system
  was used only as a front end that exports normalised RDL atoms to the
  same backend. The LLM was given the same prompt budget and the same
  dev set across all front ends; the held-out test set was never shown
  to the model.
  ```

* **Do not stand up a seven-row Table 1 with placeholder numbers.** The
  aggregator only emits a row for a front end if at least one trial
  exists under `results/runs/<frontend>/`. Show what was actually run
  and explicitly mark the rest as "trial not yet executed".
* If you publish a partial table, also publish the *iteration depth*
  (mean fix iterations to first success) and the *audit-violation rate*
  per front-end. Otherwise the reader cannot tell whether a missing
  entry is an LLM failure, a fairness violation, an API limitation, or
  simply unfinished work.
* Suggested phrasing for an early submission with limited coverage:

  ```latex
  We report \(M\) front-end slots out of seven for which we have run the
  full LLM trial protocol; the remaining slots have a documented prompt
  bundle but no trial data and are not summarised in the table.
  ```

## Mock-mode caveats

The mock client in `scripts/mock_llm/<frontend>/turn_NN.txt` is a
fixture, not an LLM. It only ships a `pysmt` slot; running the campaign
against `--frontends all` will fail mock-style for the other six slots
because there is no `turn_*.txt` under their directories. This is
intentional: production runs must point at a real provider.

The mock pysmt fixture writes a stdlib-only RDL extractor that recovers
the two `check/bignum_rdl*` dev files and emits
`status=unsupported` on everything else. It exists purely to exercise
the harness end-to-end (build, audit, dev pass, final test, aggregate);
it is **not** representative of pySMT's real expressive power.

## Sensitivity analysis (planned, not yet wired)

* Try `n_dev ∈ {15, 30, 60}` to check whether ranking between front ends
  is stable under different few-shot budgets.
* Try `seed ∈ {1, 42, 100}` for the dev/test split.
* Try `K ∈ {0, 1, 3, 5}` fix iterations.

The harness keeps the seed and K in `meta.json` for every trial, so all
three sweeps are read-only re-aggregations of an existing campaign once
the trial dirs exist.

## File / line index for paper writing

* Backend (paper-grade): [`shared_backend/cpp/src/`](shared_backend/cpp/src/)
  — entry point `rdl_backend.cpp`; decision in `rdl_solver.cpp`;
  symbolic bounds in `rdl_bound.{hpp,cpp}`; tiny JSON parser in
  `rdl_payload.cpp`. Build: [`shared_backend/cpp/build.sh`](shared_backend/cpp/build.sh).
  Unit tests: `tests/unit_bound.cpp` + `tests/unit_solver.cpp`,
  invoked by `ctest` inside `build.sh`.
* Backend (reference spec): [`shared_backend/rdl_backend.py`](shared_backend/rdl_backend.py).
* Backend self-test: [`scripts/test_backend.py`](scripts/test_backend.py)
  on [`data/synth/`](data/synth/) (gates: 100/100 three-way agreement).
* Schema: [`schema/rdl_atoms.schema.json`](schema/rdl_atoms.schema.json).
* Fairness contract:
  [`prompts/fairness_rules.md`](prompts/fairness_rules.md).
* Single-trial driver:
  [`scripts/run_llm_trial.py`](scripts/run_llm_trial.py).
* Static auditor:
  [`scripts/audit_adapter.py`](scripts/audit_adapter.py).
* Aggregator:
  [`scripts/aggregate_runs.py`](scripts/aggregate_runs.py).

## What is explicitly out of scope for v2

1. **Boolean RDL (P1).** No CaDiCaL user propagator, no Boolean
   abstraction harness, no `mode: "boolean"` payload generation. The
   JSON schema already reserves `cnf` and `atoms` so adding P1 is a
   backwards-compatible extension.
2. **Solver performance numbers.** This case study is about adapter
   *generatability*, not throughput. The existing
   `benchmark / parse-vs-solve / dual-path / roundtrip` experiments in
   this repo are the right home for performance.
3. **A grader for human-written adapters.** The v1 demo is preserved
   under `_archive/v1_demo/` precisely so it can serve as a sanity
   reference, but the v2 metrics intentionally only count
   LLM-generated adapters.
