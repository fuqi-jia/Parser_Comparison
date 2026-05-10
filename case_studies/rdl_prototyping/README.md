# RDL Prototyping Case Study (v2: fair LLM trial on QF_RDL)

This case study evaluates **how useful different SMT-LIB front ends are
for prompting an LLM to write a small theory-solver adapter**, given a
fixed shared back-end. It does **not** compare the solving performance of
Z3, cvc5, or any other engine. Each front end is treated as a parser /
typed-AST source; the verdict (`sat / unsat / unknown`) is produced by a
single shared backend that implements Real Difference Logic (QF_RDL) via
Floyd–Warshall negative-cycle detection with symbolic strict bounds.

```
input.smt2
   |
   v
[LLM-generated front-end adapter]   --writes-->   rdl_atoms.json
                                                   |
                                                   v
                              shared_backend/rdl_backend.py
                                                   |
                                                   v
                                         sat / unsat / unknown
```

## v1 → v2 in one paragraph

v1 shipped a hand-written SOMTParser adapter and 6 sanity tests as a
proof-of-concept. v2 is the actual experiment for the paper: every
front-end adapter is generated from scratch by an LLM under a fixed
fairness regime, evaluated on a real SMT-COMP QF_RDL benchmark with a
deterministic dev/test split. The v1 demo is archived under
[`_archive/v1_demo/`](_archive/v1_demo/) and is intentionally invisible
to the LLM trial harness — see [`.llmtrialignore`](../../.llmtrialignore)
at the repo root.

## Contents

* [`shared_backend/`](shared_backend/) — the Python RDL backend used by
  every adapter; the only place that produces verdicts.
* [`schema/rdl_atoms.schema.json`](schema/rdl_atoms.schema.json) — the
  exact JSON shape every adapter must output.
* [`adapters/<frontend>/README.md`](adapters/) — seven slot directories
  (one per front end) used as the start state for each LLM trial.
* [`prompts/`](prompts/) — `base_task.md`, `fairness_rules.md`,
  `dev_examples.md`, `api_excerpts/<frontend>.md`, and one
  `<frontend>_adapter_prompt.md` per slot. These are the *only* files
  the trial harness ever feeds to the LLM.
* [`scripts/`](scripts/) — data-prep, audit, LLM client, single-trial
  driver, multi-trial campaign, aggregator. See the table below.
* [`config/llm.yaml.example`](config/llm.yaml.example) — copy to
  `config/llm.yaml` and edit; controls provider (`mock` /
  `openai` / `anthropic`), the API-key env var, and the iteration /
  budget knobs.
* [`data/`](data/) — populated by `rdl-prepare-data` from
  `benchmark/QF_RDL.tar.zst`. Holds `qf_rdl_raw/`, `qf_rdl_index.csv`,
  `dev/`, `test/`, and the four index CSVs.
* [`results/runs/`](results/) — one immutable subdirectory per trial:
  `<frontend>/run_NN/{prompt,conversation,src,build,audit,dev,final_test,meta.json}`.
* [`results/aggregate/`](results/) — read-only aggregator output:
  `summary.csv`, `per_frontend.csv`, `table_paper.{md,tex}`.

## Fairness rule (paper-critical)

> The same RDL backend is used across front-end variants; solver-native
> engines in Z3 and cvc5 are not invoked. Each front end is used only as
> a parser/AST library that exports normalised RDL atoms.

The authoritative API allow/deny matrix lives in
[`prompts/fairness_rules.md`](prompts/fairness_rules.md). Both the LLM
prompts and the static auditor (`scripts/audit_adapter.py`) refer back
to it. In short:

* Allowed: SMT-LIB parsing, AST traversal (kind / children / sort), exact
  numeral introspection, and external evaluation (closed-term
  substitution into the adapter's own AST).
* Forbidden: any `check-sat`, optimisation, model API, theory tactic,
  built-in DL/IDL/RDL solver, UNSAT core / proof, and any SAT-solver
  invocation.

If a front end cannot expose enough structure to extract RDL atoms, the
adapter must report this honestly via `status: "unsupported"` (or
`"error"`) and let the shared backend turn that into `unknown`.

## Front-end slots

| Slot         | Frontend ID   | Adapter language         |
|--------------|---------------|--------------------------|
| SOMTParser   | `somtparser`  | C++                      |
| Z3 (C++ AST) | `z3_cpp`      | C++                      |
| cvc5         | `cvc5_cpp`    | C++                      |
| smt-switch   | `smt_switch`  | C++                      |
| pySMT        | `pysmt`       | Python                   |
| ANTLR4       | `antlr4`      | Java or Python (your call) |
| jSMTLIB      | `jsmtlib`     | JVM                      |

Every slot has a per-front-end prompt + an API cheat sheet under
`prompts/api_excerpts/<frontend>.md` and a stub README under
`adapters/<frontend>/README.md`.

## How to reproduce

The harness is wired through the top-level CLI. All four entry points
are no-ops or self-contained scripts; they never reach the network
unless you switch the LLM provider away from `mock`.

```bash
./parser_comparison.sh rdl-prepare-data        # one-time: extract + index + split
./parser_comparison.sh rdl-llm-campaign \      # run N trials per front-end
        --frontends pysmt --trials 10
./parser_comparison.sh rdl-aggregate           # paper tables under results/aggregate/
./parser_comparison.sh rdl-audit \             # ad-hoc fairness audit
        --src case_studies/rdl_prototyping/results/runs/pysmt/run_00/src/turn_00 \
        --frontend pysmt
```

`rdl-llm-campaign` reads `case_studies/rdl_prototyping/config/llm.yaml`.
**Until you copy `llm.yaml.example` to `llm.yaml` and switch
`provider` to `openai` or `anthropic` (and supply the corresponding
API-key env var), the harness uses pre-recorded responses under
`scripts/mock_llm/<frontend>/` and never makes a network call.** This is
deliberate: the framework is fully exercisable on a fresh checkout.

## Data preparation invariants

`rdl-prepare-data` is fully deterministic:

* Source: `benchmark/QF_RDL.tar.zst` (255 SMT-COMP files, 6 families).
* `extract_qf_rdl.sh` — idempotent, strips the
  `non-incremental/QF_RDL/` prefix, writes a sentinel after success.
* `build_qf_rdl_index.py` — for every file, records `family`,
  `relpath`, `bytes`, `n_asserts`, `status` (from
  `(set-info :status …)`), and `oversize` (≥ 256 KiB).
* `split_dev_test.py` — `seed=42`, `n_dev=30`. Excludes oversize
  (skdmxa* and a few large scheduling files) and unlabeled
  (`status=unknown`) entries; performs stratified sampling over
  `(family, status)` cells; physically copies dev / test to
  `data/dev/` and `data/test/`.

The resulting split for `seed=42` is:

| family                              | status | dev | test |
|-------------------------------------|--------|-----|------|
| SMT-Temporal-Planning-Benchmarks    | sat    | 6   | 24   |
| check                               | sat    | 1   | 0    |
| check                               | unsat  | 1   | 0    |
| sal                                 | unsat  | 10  | 47   |
| scheduling                          | sat    | 7   | 31   |
| scheduling                          | unsat  | 5   | 21   |

`skdmxa` and `skdmxa2` are entirely above the oversize threshold and are
excluded from this trial.

## Trial layout (immutable per run)

```
results/runs/<frontend>/run_NN/
    meta.json                                # config + summary
    prompt/{bundle.md,bundle.sha256,sources.txt}
    conversation/turn_NN.{user,assistant}.md
    src/turn_NN/<files-as-emitted-by-LLM>
    audit/turn_NN/audit_report.json
    build/turn_NN/{build.log,cmake_build/,.venv/}
    dev/turn_NN/{per_file.csv,summary.json,adapter_out/<rel>.json}
    final_test/{per_file.csv,summary.json,adapter_out/<rel>.json}
```

Nothing under a run dir is ever rewritten — every iteration appends to a
fresh `turn_NN/` subdirectory. The harness refuses to start when the
target run dir already exists.

## Limitations of this trial

* **P0 only.** Conjunction-only QF_RDL. P1 (Boolean RDL via a CaDiCaL
  user propagator / IPASIR-UP) is out of scope; the schema reserves
  `mode: "boolean"`, `cnf`, and `atoms` fields for a future iteration.
* **Mock provider by default.** `provider=mock` ships pre-recorded
  responses for the `pysmt` slot only. Real LLM coverage requires
  setting `provider=openai|anthropic` and editing `llm.yaml`.
* **No automatic re-tuning of the dev split.** seed=42 is wired in.
  Sensitivity analysis lives in `case_study_notes.md`.

## See also

* [`case_study_notes.md`](case_study_notes.md) — author-facing notes
  for the paper (what to claim, what not to claim, and how to wording
  Section 4).
* [`prompts/fairness_rules.md`](prompts/fairness_rules.md) — the
  authoritative fairness contract.
