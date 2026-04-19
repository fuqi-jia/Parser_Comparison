# Z3 parse vs solve (standalone)

Two timed passes per instance in one process: empty-assertions `check-sat` (parse path) vs full `check-sat` (includes solving). Columns `parse_ms` / `solve_ms` are wall-clock milliseconds from the instrumented binary.

Primary CSV: `results/parse_vs_solve/z3_parse_solve_table.csv`.

_No table yet._ Build `external/z3/z3_parse_vs_solve`, then run:

```bash
./parser_comparison.sh parse-vs-solve --file-list results/file_list.txt --timeout 30 --memory-mb 4096 -j 32
```

(build `z3_parse_vs_solve` under `external/z3/` first.)

This file is regenerated when the parse-vs-solve benchmark finishes.
