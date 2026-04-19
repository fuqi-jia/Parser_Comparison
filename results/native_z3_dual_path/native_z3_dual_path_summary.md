## SOMTParser `dumpSMT2` vs Z3 verdict agreement (standalone)

**Path A:** Z3 `parse` + `check` on the **original** SMT2 file. **Path B:** SOMTParser parses the same file, `dumpSMT2` to a temp file, then Z3 `parse` + `check` on the dump. **Disagreement** is only `(sat,unsat)` or `(unsat,sat)`; if either side is `unknown` or a path did not complete, we do not count that as a sat/unsat mismatch. The `info` column repeats `path_a=…;path_b=…` for quick grepping; full timings are in the CSV.

_No aggregate results yet — run `./parser_comparison.sh dual-path --file-list results/file_list.txt --preset sat2026` after `build-internal`._
