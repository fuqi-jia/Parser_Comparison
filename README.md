# Parser_Comparison

Parse-only comparison of SMT-LIB front ends on SMT-COMP 2025 non-incremental benchmarks. **SOMTParser** is the front end under test; in benchmark CSVs it appears as parser name **`native`**.

---

## 1. Using `./parser_comparison.sh`

`./parser_comparison.sh` is the **only command surface** you need for workflows in this repo. It resolves the repository root from the script path, `cd`s there, and forwards all remaining arguments to the wrapped tool.

```bash
chmod +x ./parser_comparison.sh    # once, if your clone is not executable
./parser_comparison.sh help          # list commands and examples
```

**Fresh clone (GitHub-friendly):** this repository keeps **wrapper code** under `external/` (CMake/Make, small drivers). Large third-party trees (cvc5, Z3 drops, smt-switch upstream, jSMTLIB SDK, …) are **not** meant to be committed—run **`./parser_comparison.sh prepare`** to init submodules (e.g. `SOMTParser`) and fetch everything `download.sh` supports. **`./scripts/prune_external_vendored.sh`** deletes those trees **on disk** (dry-run first, then `--yes`).

**Already pushed vendor blobs to GitHub but want to keep local copies:** use **`./parser_comparison.sh git-untrack-vendored`** (dry-run) then **`./parser_comparison.sh git-untrack-vendored --yes`**. That runs `git rm --cached` only—**working tree files are not deleted**; after you `commit` and `push`, the default branch tree on GitHub no longer contains those paths. Old commits still store blobs until you rewrite history (e.g. [`git filter-repo`](https://github.com/newren/git-filter-repo)); optional **`--sweep-ignored`** also untracks anything under `external/` that is tracked but matches current `.gitignore`. See `external/PARSER_FEATURES.md`.

### Command reference

| Command | Calls | Purpose |
|--------|--------|---------|
| `benchmark` / `bench` | `scripts/run_parser_benchmark.py` | Multi-parser parse-only run over a file list; optional `--preset sat2026` (alias `--param`) |
| `plots` | `scripts/gen_all_tables_and_plots.sh` | Per-theory summaries, `results/summary/frontend_table.tex`, scatter PNGs under `results/frontend_scatter/` |
| `readme` | `scripts/gen_readme_tables.py` | Paper tables from `frontend_table.tex` + splice standalone summaries; add `--readme README.md` |
| `presets` / `preset-list` | `scripts/experiment_presets.py` | List named `--preset` bundles (`sat2026`, …) |
| `roundtrip` | `scripts/run_roundtrip_benchmark.py` | **Same-engine** round-trip: SOMTParser (`native`) parse → `dumpSMT2` → reparse (differs from cross-parser `benchmark`); `results/roundtrip/`; optional `--preset sat2026` |
| `robustness` | `scripts/summarize_robustness.py` | SOMTParser (`native`) `ok`/`timeout`/`fail` by theory; `results/robustness/robustness_summary.md`; merges `roundtrip_table.csv` if present |
| `parse-vs-solve` | `scripts/run_parse_vs_solve_benchmark.py` | Z3 parse vs `check_sat` wall clock; `results/parse_vs_solve/` (`*.csv`, `parse_vs_solve_summary.md`); optional `--preset sat2026` |
| `dual-path` | `scripts/run_native_z3_dual_path_benchmark.py` | **SOMTParser + Z3:** Z3 on original vs SOMTParser `dumpSMT2` then Z3 on dump; `verdict_disagree` only on sat↔unsat; `results/native_z3_dual_path/`; needs `build/native_z3_dual_path` + Z3 |
| `sampled` | `scripts/run_sampled_full.sh` | Sampled pipeline (`--fresh`, `--skip-sample`, …) |
| `build` | `scripts/build_all.sh` | **Full** build: `build-internal` then `build-external` (extra args → native `cmake --build` only) |
| `build-internal` | `scripts/build_native.sh` | CMake configure + build for `smt_parser_comparison`, `roundtrip_tool`, … (default `build/`; `BUILD_DIR`; extra args → `cmake --build`) |
| `build-external` | `scripts/build_all_parsers.sh` | Build all drivers under `external/*` (same as legacy `build-parsers`) |
| `prepare` | `scripts/prepare.sh` | **After clone:** `git submodule update --init --recursive`, then `download.sh` (same flags: `--parsers-only`, `--benchmark-only`, …) |
| `download` | `scripts/download.sh` | Benchmarks / parser deps only (no submodule init); use **`prepare`** on new clones |
| `git-untrack-vendored` | `scripts/git_untrack_external_vendored.sh` | `git rm --cached` for vendored paths under `external/`; **`--yes`** to apply; optional **`--sweep-ignored`**; local files stay |
| `summary` | `scripts/gen_summary_table.py` | Per-theory CSV/Markdown from a long benchmark CSV |
| `sample` | `scripts/sample.sh` | Sampled manifest / file copy via `sample_benchmarks.py` |
| `help` | — | Print built-in help |

Everything after the command name is passed through unchanged (`argparse` flags, extra paths, etc.).

### Common experiment settings (time, memory, parallelism)

The same **logical** limits apply across all heavy runs in this repo (multi-parser compare, round-trip, Z3 parse-vs-solve, `dual-path`, sampled pipelines, recheck scripts): how long each instance may run, how much address space a child may use, and how many workers run in parallel. Those are **not** tied to a single command — each driver just exposes them under its own CLI names (see `--help` per tool).

| Dimension | Meaning | Typical CLI flags |
| --- | --- | --- |
| **Instance / driver time budget** | Wall clock allowed for one benchmark file in the driver | `--timeout` (seconds) on `benchmark`, `roundtrip`, and `scripts/re_run_parser_benchmark.py`; on `parse-vs-solve` also `--wall-timeout` (outer wrapper) and `--solve-timeout-ms` (passed into Z3) |
| **Per-process memory cap** | `RLIMIT_AS`-style limit for child processes (MiB) | `--memory-mb` |
| **Host parallelism** | Concurrent benchmark workers (parsers stay single-threaded inside each run) | `-j` / `--jobs` |

**Built-in defaults when you omit flags and `--preset`:**

| Entry point | Relevant flags | Defaults |
| --- | --- | --- |
| `./parser_comparison.sh benchmark` | `--timeout`, `--memory-mb`, `-j` | **10** s, **4096** MiB, **24** |
| `./parser_comparison.sh roundtrip` | `--timeout`, `--memory-mb`, `-j` | **30** s, **4096** MiB, **24** |
| `./parser_comparison.sh parse-vs-solve` | `--solve-timeout-ms`, `--wall-timeout`, `--memory-mb`, `-j` | **600000**, **720** s (outer subprocess; must be ≥ solve budget), **4096** MiB, **8** |
| `python3 scripts/re_run_parser_benchmark.py` | `--timeout`, `--memory-mb` (see `--help`) | **10** s, **4096** MiB |
| `./parser_comparison.sh sampled` | Benchmark / recheck invoke Python drivers with flags in [`scripts/run_sampled_full.sh`](scripts/run_sampled_full.sh) (e.g. `--timeout 10 --memory-mb 4096`; no `-j` → benchmark default **24**) | align that script with the same budgets you use elsewhere |

**Named bundles:** `--preset` / `--param` (e.g. `sat2026`) on supported drivers loads a bundle from [`scripts/experiment_presets.py`](scripts/experiment_presets.py); run `./parser_comparison.sh presets` to list names. Explicit flags always **override** the preset. For **`sat2026`**: `timeout` / `memory_mb` / `jobs` apply to **`benchmark`** and **`roundtrip`**; **`parse-vs-solve`** uses the same `memory_mb` and `jobs` but **not** the 30 s parse-instance cap—its time limits are `solve_timeout_ms` (inside Z3) and `wall_timeout` (Python wrapper around the whole child). **`dual-path`** uses `memory_mb`, `jobs`, `solve_timeout_ms`, and `dual_path_outer_sec` (subprocess wall for two Z3 `check` calls plus native dump). **`robustness`** only aggregates CSVs and has no `--preset` (use a benchmark table produced with the preset you care about).

### Typical workflow

1. **Fetch deps:** `./parser_comparison.sh prepare` (or `prepare --parsers-only` / `prepare --benchmark-only` as needed).  
2. **Compile:** `./parser_comparison.sh build` (native + external), or split as `./parser_comparison.sh build-internal` then `./parser_comparison.sh build-external` (same as `build-parsers`). Use `BUILD_DIR=/path ./parser_comparison.sh build-internal` if you want a non-default CMake tree.  
3. **Benchmark:** prepare `results/file_list.txt` (one `.smt2` per line), then e.g.  
   `./parser_comparison.sh benchmark --file-list results/file_list.txt --preset sat2026`  
   (or set `--timeout` / `--memory-mb` / `-j` explicitly; see **Common experiment settings**.)  
4. **Tables and figures:** `./parser_comparison.sh plots`  
5. **Refresh the results section of this README:** `./parser_comparison.sh readme --readme README.md` (paper tables + standalone experiment blocks).

**Paper-style full-artifact run:** use `--preset sat2026` on `benchmark`, `roundtrip`, `parse-vs-solve`, and `dual-path`. Other environment notes: Ubuntu-class OS, `-O3`, single-threaded *per parser invocation* inside the driver unless you change build flags.

### More documentation

- Sampled pipeline details: [docs/run_sampled_full.md](docs/run_sampled_full.md)  
- Recheck / merge behaviour: [docs/recheck_and_native.md](docs/recheck_and_native.md)  
- Parser layout and dependencies: [external/PARSER_FEATURES.md](external/PARSER_FEATURES.md)  
- Per-parser build notes: `external/cvc5/README.md`, `external/smt-switch/README.md`, `external/antlr4_parser/README.md`, `external/jsmtlib/BUILD_INSTRUCTIONS.md`  
- SOMTParser library (submodule): [SOMTParser/README.md](SOMTParser/README.md)

---

## 2. Experimental results

Tables below are generated from [`results/summary/frontend_table.tex`](results/summary/frontend_table.tex) (coverage + appendix scatter numbers). The **standalone experiment** subsection further down is filled from `results/{roundtrip,robustness,parse_vs_solve,native_z3_dual_path}/*_summary.md`. **Regenerate after changing LaTeX or re-running those benchmarks:**

```bash
./parser_comparison.sh readme
./parser_comparison.sh readme --readme README.md
```

Long-form commentary and extra statistics: [results/summary/experimental_evaluation_data_summary.md](results/summary/experimental_evaluation_data_summary.md). Standalone copy of the paper tables: [results/summary/readme_paper_tables.md](results/summary/readme_paper_tables.md). Concatenated standalone experiment write-ups (same sources spliced into this README): [results/summary/readme_standalone_experiments.md](results/summary/readme_standalone_experiments.md). Per-experiment folders: [results/roundtrip/roundtrip_summary.md](results/roundtrip/roundtrip_summary.md), [results/robustness/robustness_summary.md](results/robustness/robustness_summary.md), [results/parse_vs_solve/parse_vs_solve_summary.md](results/parse_vs_solve/parse_vs_solve_summary.md), [results/native_z3_dual_path/native_z3_dual_path_summary.md](results/native_z3_dual_path/native_z3_dual_path_summary.md).

Scatter PNGs (not embedded here): run `./parser_comparison.sh plots` → `results/frontend_scatter/{time,rss,nodes}/`.

<!--PAPER_TABLES_BEGIN-->

## Front-end coverage (same source as paper Table `tab:frontend-all`)

Success rate $\%= 100 - \mathrm{timeout} - \mathrm{failure}$; timeout rate follows from this identity.

### Success rate (%)

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SOMTParser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QF_AX | **100** | *97.28* | - | **100** | **100** | **100** | **100** |
| QF_BV | 98.87 | 82.54 | 83.14 | 99.31 | 94.22 | **99.84** | *99.78* |
| QF_FP | **100** | *99.6* | - | - | **100** | **100** | **100** |
| QF_LIA | **99.91** | 65.25 | 65.87 | 98.41 | 97.47 | 99.19 | *99.84* |
| QF_LRA | **99.83** | 64.52 | 41.81 | 96.46 | 92.07 | 99.37 | *99.66* |
| QF_NIA | **100** | 36.42 | 36.08 | 99.29 | 99.41 | *99.98* | **100** |
| QF_NRA | **99.98** | 86.69 | 74.93 | 99.48 | 98.47 | *99.94* | **99.98** |
| QF_S | **100** | *86.69* | 14.5 | 3.21 | **100** | 27.87 | **100** |

### Timeout rate (%)

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SOMTParser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QF_AX | **0** | *2.72* | - | **0** | **0** | **0** | **0** |
| QF_BV | 1.13 | 17.46 | 16.81 | 0.58 | **0.15** | *0.16* | 0.22 |
| QF_FP | **0** | *0.4* | - | - | **0** | **0** | **0** |
| QF_LIA | *0.09* | 34.75 | 34.12 | 1.41 | **0.06** | 0.8 | 0.16 |
| QF_LRA | **0.17** | 35.48 | 18.2 | 3.14 | 0.68 | 0.63 | *0.34* |
| QF_NIA | **0** | 63.55 | 63.89 | 0.19 | 0.06 | *0.02* | **0** |
| QF_NRA | **0.02** | 13.31 | 9.35 | 0.39 | 0.11 | *0.03* | **0.02** |
| QF_S | **0** | 13.31 | *4.8* | **0** | **0** | **0** | **0** |

### Fail rate (%)

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SOMTParser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| QF_AX | **0** | **0** | - | **0** | **0** | **0** | **0** |
| QF_BV | **0** | **0** | *0.05* | 0.11 | 5.62 | **0** | **0** |
| QF_FP | **0** | **0** | - | - | **0** | **0** | **0** |
| QF_LIA | **0** | **0** | *0.01* | 0.18 | 2.47 | *0.01* | **0** |
| QF_LRA | **0** | **0** | 39.99 | *0.4* | 7.24 | **0** | **0** |
| QF_NIA | **0** | *0.02* | *0.02* | 0.52 | 0.53 | **0** | **0** |
| QF_NRA | **0** | **0** | 15.71 | 0.13 | 1.42 | *0.02* | **0** |
| QF_S | **0** | **0** | 80.7 | 96.79 | **0** | *72.13* | **0** |

### Scatter plots: common-success subset and timeouts

**Note**: Ratios use instances where **both** SOMTParser (`native`) and the baseline are `ok`; timeouts are drawn at the plot boundary.
jSMTLIB RSS reflects JVM process RSS and is not directly comparable to C++ front-end RSS.

#### Timeouts and common-success counts (N)

| Baseline | Only_SP_TO | Only_Base_TO | Both_TO | Base successful | Common successful (N) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Z3 | 51 | 459 | 81 | 161,444 | 161,390 |
| cvc5 | 36 | 34,135 | 97 | 127,746 | 127,707 |
| smt-switch | 36 | 30,989 | 97 | 69,409 | 69,372 |
| pySMT | 3 | 475 | 130 | 99,284 | 99,279 |
| ANTLR4 | 6 | 108 | 10 | 158,506 | 158,497 |
| jSMTLIB | 38 | 105 | 95 | 145,788 | 145,747 |

#### Scatter summary: time / peak RSS / AST nodes (ratio = competitor / SOMTParser)

| Baseline | N | Time mean | Time Better(%) | RSS mean | RSS Better(%) | Nodes mean | Nodes Better(%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Z3 | 161,390 | 0.500 | 2.85 | 0.528 | 4.11 | 1.978 | 86.40 |
| cvc5 | 127,707 | 9.42 | 30.38 | 1.566 | 99.95 | 0.989 | 37.37 |
| smt-switch | 69,372 | 14.81 | 54.57 | 1.997 | 96.14 | 1.760 | 72.46 |
| pySMT | 99,279 | 1.524 | 47.43 | 1.260 | 99.75 | 1.163 | 71.40 |
| ANTLR4 | 158,497 | 8.329 | 99.98 | 0.534 | 9.27 | 34.37 | 100.00 |
| jSMTLIB | 145,747 | 3.925 | 98.69 | 0.278 | 2.62 | 3.497 | 94.71 |

<!--PAPER_TABLES_END-->

### Standalone experiments (not multi-parser comparison)

Same presentation style as **Front-end coverage** above: section titles plus tables of measured outcomes only. Drivers and refresh workflow are in **§1**. **Round-trip** stress-tests **one** SOMTParser build through print–reparse; **`dual-path`** combines SOMTParser `dumpSMT2` with **two** Z3 `check` runs to compare verdicts; cross-front-end parse-only counts appear in the main benchmark tables.

<!--EXTENDED_RESULTS_BEGIN-->

## Round-trip correctness (SOMTParser)

Two experimental settings are common in front-end work: **(A) same-engine parse → print → reparse** and **(B) cross-parser** runs on one file. This table is **(A) only**: SOMTParser parses the original script, **writes intermediate SMT2 with `dumpSMT2`**, then parses that text again (two parser objects, **one** implementation). Status **`mismatch`** means both parses succeeded but **AST node counts disagree**—that is expected to come from **`dumpSMT2` changing structure** (layout, grouping, or equivalent rewrites), not from “wrong logic” in the sense of bad `sat`/`unsat`; first-pass vs post-dump **node counts are not tautologically equal**. **(B)** is the multi-parser `benchmark`, which records `ast_nodes` per tool on the same path.

### Overall

| Status | Count | Share |
| --- | ---: | ---: |
| `ok` | 149744 | 92.4431% |
| `timeout` | 10907 | 6.7333% |
| `mismatch` | 1330 | 0.8211% |
| `fail` | 4 | 0.0025% |

### By theory family

| Theory | ok | mismatch | fail | timeout | other | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 454 | 97 | 0 | 0 | 0 | 551 |
| QF_BV | 36879 | 1208 | 4 | 8100 | 0 | 46191 |
| QF_FP | 40381 | 25 | 0 | 0 | 0 | 40406 |
| QF_LIA | 10506 | 0 | 0 | 2800 | 0 | 13306 |
| QF_LRA | 1749 | 0 | 0 | 4 | 0 | 1753 |
| QF_NIA | 25452 | 0 | 0 | 0 | 0 | 25452 |
| QF_NRA | 12151 | 0 | 0 | 3 | 0 | 12154 |
| QF_S | 22172 | 0 | 0 | 0 | 0 | 22172 |

---

## Native parser robustness by theory (SOMTParser)

Per-theory counts of SOMTParser (`native`) front-end outcomes (`ok`, `timeout`, `fail`, `other`) on the evaluated instances.

### Overall totals

| Metric | Count | Share |
| --- | ---: | ---: |
| ok | 161931 | 99.9667% |
| timeout | 54 | 0.0333% |
| fail | 0 | 0.0000% |
| other | 0 | 0.0000% |

### By theory family

| Theory | ok | timeout | fail | other | total | fail%+timeout% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 551 | 0 | 0 | 0 | 551 | 0.0000% |
| QF_BV | 46139 | 52 | 0 | 0 | 46191 | 0.1126% |
| QF_FP | 40406 | 0 | 0 | 0 | 40406 | 0.0000% |
| QF_LIA | 13306 | 0 | 0 | 0 | 13306 | 0.0000% |
| QF_LRA | 1753 | 0 | 0 | 0 | 1753 | 0.0000% |
| QF_NIA | 25452 | 0 | 0 | 0 | 25452 | 0.0000% |
| QF_NRA | 12152 | 2 | 0 | 0 | 12154 | 0.0165% |
| QF_S | 22172 | 0 | 0 | 0 | 22172 | 0.0000% |

### Round-trip side summary (when round-trip run is available)

| Theory | roundtrip_ok | mismatch | fail | timeout |
| --- | ---: | ---: | ---: | ---: |
| QF_AX | 454 | 97 | 0 | 0 |
| QF_BV | 36879 | 1208 | 4 | 8100 |
| QF_FP | 40381 | 25 | 0 | 0 |
| QF_LIA | 10506 | 0 | 0 | 2800 |
| QF_LRA | 1749 | 0 | 0 | 4 |
| QF_NIA | 25452 | 0 | 0 | 0 |
| QF_NRA | 12151 | 0 | 0 | 3 |
| QF_S | 22172 | 0 | 0 | 0 |

Round-trip totals: ok=149744 mismatch=1330 fail=4 timeout=10907

---

## Z3 parse vs solver wall time (standalone)

Per instance, **one** Z3 process (`z3_parse_vs_solve`): load the script with `parse_file` / `parse_string`, add all assertions to a solver, then run **one** `check()` (full problem). `parse_ms` is wall time for parse+load; `solve_ms` is wall time for that single `check()`. This is **not** a two-verdict agreement experiment (no cross-check of sat vs unsat); for that you would need a gold label or a second pipeline and a separate results table.

### Overall (by outcome)

| Status | Count | Share |
| --- | ---: | ---: |
| `ok` | 158099 | 97.6010% |
| `timeout` | 3769 | 2.3268% |
| `fail` | 84 | 0.0519% |
| `solve_fail` | 32 | 0.0198% |
| `parse_fail` | 1 | 0.0006% |

### Timing (`status=ok` only)

| Metric | Value |
| --- | ---: |
| Count | 158099 |
| Median `parse_ms` | 10.5111 |
| Median `solve_ms` | 18.2055 |
| Median `parse_over_total` (parse / (parse+solve)) | 0.362239 |
| Median `parse_over_solve` (finite only) | 0.567986 |

---

## SOMTParser `dumpSMT2` vs Z3 verdict agreement (standalone)

**Path A:** Z3 `parse` + `check` on the **original** SMT2 file. **Path B:** SOMTParser parses the same file, `dumpSMT2` to a temp file, then Z3 `parse` + `check` on the dump. **Disagreement** is only `(sat,unsat)` or `(unsat,sat)`; if either side is `unknown` or a path did not complete, we do not count that as a sat/unsat mismatch. The `info` column repeats `path_a=…;path_b=…` for quick grepping; full timings are in the CSV.

### Overall (by `status`)

| Status | Count | Share |
| --- | ---: | ---: |
| `verdict_agree` | 152374 | 94.0667% |
| `timeout` | 8991 | 5.5505% |
| `dump_fail` | 439 | 0.2710% |
| `fail` | 92 | 0.0568% |
| `path_b_incomplete` | 68 | 0.0420% |
| `path_a_incomplete` | 19 | 0.0117% |
| `verdict_disagree` | 2 | 0.0012% |

### Verdict disagreement (sat vs unsat only)

| Metric | Count |
| --- | ---: |
| `verdict_disagree==1` | 2 |
| Share of all rows | 0.0012% |

### Verdict marginals

| path_a_verdict | Count |
| --- | ---: |
| `sat` | 76006 |
| `unsat` | 63642 |
| `unknown` | 13235 |
| `∅` | 9102 |

| path_b_verdict | Count |
| --- | ---: |
| `sat` | 75873 |
| `unsat` | 62950 |
| `unknown` | 13553 |
| `∅` | 9609 |

<!--EXTENDED_RESULTS_END-->
