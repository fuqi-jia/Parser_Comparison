# Reruns: writing the main table and resuming

## Current behaviour

- **Main table:** `results/parser_benchmark_table_sampled.csv`. When `--table` points at the main table, **each rerun row overwrites that row immediately** (success or failure), **flushed to disk per row** so partial progress survives crashes.
- **Recheck log:** `results/parser_benchmark_recheck_sampled.csv`. **Every** rerun row is appended (including successful fixes). Used for **resume:** the next identical command skips `(file, parser)` pairs already present in recheck and only runs what is left.
- **Summary:** regenerate from the main table directly (`gen_summary_table.py --input <main> --output-dir results/summary`); you **do not** need `--update-from-recheck` if the main table is kept up to date.

## Resume after a crash

Default is **resume** (`--resume`): run the **same command again**; do **not** pass `--fresh`.

```bash
./scripts/run_re_run_benchmark.sh --only-parser cvc5 \
  benchmark/sampled/file_list.txt \
  results/parser_benchmark_checkpoint_sampled.csv \
  results/parser_benchmark_recheck_sampled.csv \
  results/parser_benchmark_table_sampled.csv \
  results/summary
```

- Pairs already in recheck are merged into the main table first, then only pending pairs run.
- After each pair: main table updated on disk + row appended to recheck. Repeat the same command if another crash happens.

## Rerun `native` only

```bash
./scripts/run_re_run_benchmark.sh \
  --only-parser native \
  benchmark/sampled/file_list.txt \
  results/parser_benchmark_checkpoint_sampled.csv \
  results/parser_benchmark_recheck_sampled.csv \
  results/parser_benchmark_table_sampled.csv \
  results/summary
```

The wrapper passes `--table`; successes are written back; at the end `gen_summary_table.py --input <main>` runs automatically.

## Legacy path without `--table`

If the main table is **not** passed, everything still lands in recheck only. Then merge manually:

```bash
python3 scripts/gen_summary_table.py --input results/parser_benchmark_table_sampled.csv \
  --update-from-recheck results/parser_benchmark_recheck_sampled.csv \
  --output-dir results/summary
```
