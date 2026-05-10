## Round-trip correctness (SOMTParser)

Two experimental settings are common in front-end work: **(A) same-engine parse → print → reparse** and **(B) cross-parser** runs on one file. This table is **(A) only**: SOMTParser parses the original script, **writes intermediate SMT2 with `dumpSMT2`**, then parses that text again (two parser objects, **one** implementation). Status **`mismatch`** means both parses succeeded but **AST node counts disagree**—that is expected to come from **`dumpSMT2` changing structure** (layout, grouping, or equivalent rewrites), not from “wrong logic” in the sense of bad `sat`/`unsat`; first-pass vs post-dump **node counts are not tautologically equal**. **(B)** is the multi-parser `benchmark`, which records `ast_nodes` per tool on the same path.

### Overall

| Status | Count | Share |
| --- | ---: | ---: |
| `ok` | 149758 | 92.4518% |
| `timeout` | 10885 | 6.7198% |
| `mismatch` | 1338 | 0.8260% |
| `fail` | 4 | 0.0025% |

### By theory family

| Theory | ok | mismatch | fail | timeout | other | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 454 | 97 | 0 | 0 | 0 | 551 |
| QF_BV | 36888 | 1216 | 4 | 8083 | 0 | 46191 |
| QF_FP | 40381 | 25 | 0 | 0 | 0 | 40406 |
| QF_LIA | 10511 | 0 | 0 | 2795 | 0 | 13306 |
| QF_LRA | 1749 | 0 | 0 | 4 | 0 | 1753 |
| QF_NIA | 25452 | 0 | 0 | 0 | 0 | 25452 |
| QF_NRA | 12151 | 0 | 0 | 3 | 0 | 12154 |
| QF_S | 22172 | 0 | 0 | 0 | 0 | 22172 |
