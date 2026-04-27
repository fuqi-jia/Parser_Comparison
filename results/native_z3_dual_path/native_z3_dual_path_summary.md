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

