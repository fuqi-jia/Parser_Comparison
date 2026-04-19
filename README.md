# Parser_Comparison

Parse-only comparison of SMT-LIB front ends on SMT-COMP 2025 non-incremental benchmarks. **SMTParser** is recorded as parser name **`native`**.

---

## 1. Using `./parser_comparison.sh`

`./parser_comparison.sh` is the **only command surface** you need for workflows in this repo. It resolves the repository root from the script path, `cd`s there, and forwards all remaining arguments to the wrapped tool.

```bash
chmod +x ./parser_comparison.sh    # once, if your clone is not executable
./parser_comparison.sh help          # list commands and examples
```

### Command reference

| Command | Calls | Purpose |
|--------|--------|---------|
| `benchmark` / `bench` | `scripts/run_parser_benchmark.py` | Multi-parser parse-only run over a file list |
| `plots` | `scripts/gen_all_tables_and_plots.sh` | Per-theory summaries, `results/summary/frontend_table.tex`, scatter PNGs under `results/frontend_scatter/` |
| `readme` | `scripts/gen_readme_tables.py` | Markdown tables from `frontend_table.tex`; add `--readme README.md` to splice **section 2** of this file |
| `roundtrip` | `scripts/run_roundtrip_benchmark.py` | Native parse → `dumpSMT2` → reparse; outputs under `results/roundtrip/` |
| `robustness` | `scripts/summarize_robustness.py` | Native `ok`/`timeout`/`fail` by theory; merges `roundtrip_table.csv` if present |
| `parse-vs-solve` | `scripts/run_parse_vs_solve_benchmark.py` | Z3 parse vs `check_sat` wall clock; outputs under `results/parse_vs_solve/` |
| `sampled` | `scripts/run_sampled_full.sh` | Sampled pipeline (`--fresh`, `--skip-sample`, …) |
| `build-parsers` | `scripts/build_all_parsers.sh` | Build drivers under `external/*` (Z3, cvc5, …) |
| `download` | `scripts/download.sh` | Benchmarks / parser binaries |
| `summary` | `scripts/gen_summary_table.py` | Per-theory CSV/Markdown from a long benchmark CSV |
| `sample` | `scripts/sample.sh` | Sampled manifest / file copy via `sample_benchmarks.py` |
| `help` | — | Print built-in help |

Everything after the command name is passed through unchanged (`argparse` flags, extra paths, etc.).

### Typical workflow

1. **Dependencies / binaries:** `./parser_comparison.sh download` (e.g. `--parsers-only`) as needed.  
2. **External parsers:** `./parser_comparison.sh build-parsers`  
3. **Main driver + round-trip tool:** from repo root, `mkdir -p build && cd build && cmake .. && cmake --build .` → `smt_parser_comparison`, `roundtrip_tool`.  
4. **Benchmark:** prepare `results/file_list.txt` (one `.smt2` per line), then e.g.  
   `./parser_comparison.sh benchmark --file-list results/file_list.txt --timeout 30 --memory-mb 4096 -j 64`  
5. **Tables and figures:** `./parser_comparison.sh plots`  
6. **Refresh the results section of this README:** `./parser_comparison.sh readme --readme README.md`

**Paper-aligned defaults (tunable in scripts):** Ubuntu-class OS, `-O3`, single-threaded parser runs, ~30 s timeout, ~4 GiB per-process limit unless you override flags.

### More documentation

- Sampled pipeline details: [docs/run_sampled_full.md](docs/run_sampled_full.md)  
- Recheck / merge behaviour: [docs/recheck_and_native.md](docs/recheck_and_native.md)  
- Parser layout and dependencies: [external/PARSER_FEATURES.md](external/PARSER_FEATURES.md)  
- Per-parser build notes: `external/cvc5/README.md`, `external/smt-switch/README.md`, `external/antlr4_parser/README.md`, `external/jsmtlib/BUILD_INSTRUCTIONS.md`  
- SMTParser library (submodule): [SOMTParser/README.md](SOMTParser/README.md)

---

## 2. Experimental results

Tables below are generated from [`results/summary/frontend_table.tex`](results/summary/frontend_table.tex) (coverage + appendix scatter numbers). **Regenerate or update after changing the LaTeX source:**

```bash
./parser_comparison.sh readme
./parser_comparison.sh readme --readme README.md
```

Long-form commentary and extra statistics: [results/summary/experimental_evaluation_data_summary.md](results/summary/experimental_evaluation_data_summary.md). Standalone copy of the tables: [results/summary/readme_paper_tables.md](results/summary/readme_paper_tables.md). Native robustness rollup: [results/summary/robustness_summary.md](results/summary/robustness_summary.md).

Scatter PNGs (not embedded here): run `./parser_comparison.sh plots` → `results/frontend_scatter/{time,rss,nodes}/`.

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
