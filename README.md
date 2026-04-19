# Parser_Comparison

Artifact for comparing multiple **SMT-LIB front ends** under a **parse-only** configuration on the SMT-COMP 2025 non-incremental families (QF_AX, QF_BV, QF_FP, QF_LIA, QF_LRA, QF_NIA, QF_NRA, QF_S). Solving is disabled; we report coverage and front-end cost (time, peak RSS, AST node count). **SMTParser** appears as parser name **`native`** in benchmark tables.

For a longer numeric discussion, see [results/summary/experimental_evaluation_data_summary.md](results/summary/experimental_evaluation_data_summary.md).

## Experimental setup (paper-aligned, short)

- OS: Ubuntu 22.04-class environment; C/C++ **`-O3`**; single-threaded runs; **30 s** timeout; **4 GiB** address-space cap per process (tunable in scripts).
- Front ends: Z3, cvc5, smt-switch, pySMT, ANTLR4, jSMTLIB, SMTParser (native).
- Long result table: `results/parser_benchmark_table.csv`; per-theory summaries and LaTeX: `scripts/gen_all_tables_and_plots.sh`.

## Main results: coverage (paper Table `tab:frontend-all`)

The blocks below are generated from [`results/summary/frontend_table.tex`](results/summary/frontend_table.tex). A standalone copy lives in [results/summary/readme_paper_tables.md](results/summary/readme_paper_tables.md).

**Regenerate tables:** `python3 scripts/gen_readme_tables.py` writes `readme_paper_tables.md`. To splice them into this README:

`python3 scripts/gen_readme_tables.py --readme README.md`

<!--PAPER_TABLES_BEGIN-->

## Front-end coverage (same source as paper Table `tab:frontend-all`)

Success rate $\%= 100 - \mathrm{timeout} - \mathrm{failure}$; timeout rate follows from this identity.

### Success rate (%)

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SMTParser |
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

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SMTParser |
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

| Theory | Z3 | cvc5 | smt-sw | pysmt | ANTLR4 | jSMTLIB | SMTParser |
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

**Note**: Ratios use instances where **both** SMTParser and the baseline are `ok`; timeouts are drawn at the plot boundary.
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

#### Scatter summary: time / peak RSS / AST nodes (ratio = competitor / SMTParser)

| Baseline | N | Time mean | Time Better(%) | RSS mean | RSS Better(%) | Nodes mean | Nodes Better(%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Z3 | 161,390 | 0.500 | 2.85 | 0.528 | 4.11 | 1.978 | 86.40 |
| cvc5 | 127,707 | 9.42 | 30.38 | 1.566 | 99.95 | 0.989 | 37.37 |
| smt-switch | 69,372 | 14.81 | 54.57 | 1.997 | 96.14 | 1.760 | 72.46 |
| pySMT | 99,279 | 1.524 | 47.43 | 1.260 | 99.75 | 1.163 | 71.40 |
| ANTLR4 | 158,497 | 8.329 | 99.98 | 0.534 | 9.27 | 34.37 | 100.00 |
| jSMTLIB | 145,747 | 3.925 | 98.69 | 0.278 | 2.62 | 3.497 | 94.71 |

<!--PAPER_TABLES_END-->

## Scatter plots (time / RSS / nodes)

If plots are missing after clone, from the repo root run:

```bash
./scripts/gen_all_tables_and_plots.sh
```

Outputs: `results/frontend_scatter/time/`, `results/frontend_scatter/rss/`, `results/frontend_scatter/nodes/` (x-axis: SMTParser, y-axis: baseline; log–log; timeouts as crosses at the boundary).

## Reproducing the main benchmark

1. Build the driver and external parsers: `./scripts/build_all_parsers.sh` (under `external/z3` this produces both `z3_parser` and `z3_parse_vs_solve`). Main driver and round-trip tool: `mkdir -p build && cd build && cmake .. && cmake --build .` → `smt_parser_comparison` and `roundtrip_tool`.
2. Prepare `results/file_list.txt` (one `.smt2` path per line, absolute or repo-relative).
3. Run, e.g.  
   `python3 scripts/run_parser_benchmark.py --file-list results/file_list.txt --timeout 30 --memory-mb 4096 -j 64`  
   See [docs/run_sampled_full.md](docs/run_sampled_full.md).

## Extended experiments

### 1. Round-trip (parse → `dumpSMT2` → reparse)

- Binary: `roundtrip_tool` (CMake target; after build: `build/roundtrip_tool`).
- Batch:  
  `python3 scripts/run_roundtrip_benchmark.py --file-list results/file_list.txt --timeout 30 --memory-mb 4096 -j 32`
- Outputs: `results/roundtrip/roundtrip_checkpoint.csv`, `results/roundtrip/roundtrip_table.csv` with `ok1` / `ok2` / `nodes1` / `nodes2` / `match_nodes`.

### 2. Robustness summary (native by theory)

After `parser_benchmark_table.csv` exists:

`python3 scripts/summarize_robustness.py`

If `results/roundtrip/roundtrip_table.csv` exists, it is merged automatically. Output: [results/summary/robustness_summary.md](results/summary/robustness_summary.md).

### 3. Parse time vs Z3 solve time

- Binary: `external/z3/z3_parse_vs_solve` (`make -C external/z3`).
- Batch:  
  `python3 scripts/run_parse_vs_solve_benchmark.py --file-list results/file_list.txt --solve-timeout-ms 600000 --wall-timeout 120 --memory-mb 4096 -j 8`
- Outputs: `results/parse_vs_solve/z3_parse_solve_table.csv` (`parse_ms`, `solve_ms`, `parse_over_solve`, …). **Z3 only**, independent of the parse-only main table.

## Subproject

- SMTParser library documentation: [SOMTParser/README.md](SOMTParser/README.md).
