# Round-trip (SMTParser)

Parse → linear SMT2 (`dumpSMT2`) → second parse on the same engine; success requires both parses without error and matching AST node counts (`match_nodes=1`).

Primary CSV: `results/roundtrip/roundtrip_table.csv`.

_No table yet._ Run:

```bash
./parser_comparison.sh roundtrip --file-list results/file_list.txt --timeout 30 --memory-mb 4096 -j 32
```

This file is regenerated when the round-trip benchmark finishes.
