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

