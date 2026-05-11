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

