# Sampled benchmark: one-shot workflow

## One command (recommended)

From the repository root, run the full pipeline **sampling (optional) → benchmark → recheck → summary → LaTeX**:

```bash
./parser_comparison.sh sampled
# equivalent: ./scripts/run_sampled_full.sh
```

- **Default:** resume from checkpoints. Existing checkpoint/recheck work is skipped; only unfinished jobs run.
- **Fresh run:** `--fresh` clears checkpoint, long table, and recheck, then reruns everything.
- **Sampling already present:** if `benchmark/sampled/manifest.csv` and `benchmark/sampled/files/` exist, sampling is skipped automatically; use `--skip-sample` to force-skip the sampling step.
- **Clean known-unsupported failures:** `--clean-unsupported` removes failure trees for pysmt/QF_FP, smt-switch/QF_AX, smt-switch/QF_FP before running.

Examples:

```bash
# First run or resume
./parser_comparison.sh sampled

# Wipe artifacts and rerun from scratch
./parser_comparison.sh sampled --fresh

# Sampling exists; only benchmark + downstream
./parser_comparison.sh sampled --skip-sample
```

## Pipeline steps

1. **Sampling:** if `manifest.csv` / `sampled/files` are missing, run `scripts/sample.sh` (200 instances per theory, reproducible).
2. **Benchmark:** every `.smt2` in the file list × every parser, 10 s timeout by default; results go to checkpoint and long CSV.
3. **Recheck:** rerun `(file, parser)` pairs that were `fail` or `timeout` in the checkpoint to fix false negatives (e.g. non-JSON first line); append to recheck CSV.
4. **Summary:** merge recheck corrections into the long table, then emit per-theory CSV/Markdown summaries.
5. **LaTeX:** generate `results/summary/frontend_table.tex` from summaries.

Output paths (under repo root):

- `results/parser_benchmark_checkpoint_sampled.csv`
- `results/parser_benchmark_table_sampled.csv`
- `results/parser_benchmark_recheck_sampled.csv`
- `results/summary/` (includes `frontend_table.tex`)

## Linux server / non-WSL

Dependencies:

- Bash, Python 3
- Built `smt_parser_comparison` (or `build/smt_parser_comparison`) and configured external parsers (`scripts/build_all_parsers.sh`, `scripts/download.sh`)

On a **plain Linux server**:

1. **No root:** install user-space deps (Python/Java/C++/Haskell mix). See [server_setup_no_root.md](server_setup_no_root.md). Typical flow: `./scripts/setup_server_env.sh`, then `export PYTHON=/path/to/conda/env/bin/python`, then `./scripts/run_sampled_full.sh`.
2. **Copy tree:** copy the whole project (including `benchmark/sampled/files` or at least manifest + source benchmarks), install deps, build, run `./scripts/run_sampled_full.sh`.
3. **Docker (optional):** bake `download.sh`, `build_all_parsers.sh`, and `run_sampled_full.sh` into an image; mount or copy `results/` out.
