## Round-trip correctness (SOMTParser)

Two experimental settings are common in front-end work: **(A) same-engine parse → print → reparse** and **(B) cross-parser** runs on one file. This table is **(A) only**: SOMTParser reads the original script, emits SMT2 via `dumpSMT2`, then SOMTParser parses that dump again (two parser objects, **one** implementation). The intermediate file can change structure, so first-pass and second-pass **node counts are not tautologically equal**—`mismatch` is informative. **(B)** is the multi-parser `benchmark`, which records `ast_nodes` per tool on the same path.

### Overall

| Status | Count | Share |
| --- | ---: | ---: |
| `ok` | 149895 | 92.5363% |
| `timeout` | 10724 | 6.6204% |
| `mismatch` | 1361 | 0.8402% |
| `fail` | 5 | 0.0031% |

### By theory family

| Theory | ok | mismatch | fail | timeout | other | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 454 | 97 | 0 | 0 | 0 | 551 |
| QF_BV | 37020 | 1246 | 5 | 7920 | 0 | 46191 |
| QF_FP | 40388 | 18 | 0 | 0 | 0 | 40406 |
| QF_LIA | 10507 | 0 | 0 | 2799 | 0 | 13306 |
| QF_LRA | 1750 | 0 | 0 | 3 | 0 | 1753 |
| QF_NIA | 25452 | 0 | 0 | 0 | 0 | 25452 |
| QF_NRA | 12152 | 0 | 0 | 2 | 0 | 12154 |
| QF_S | 22172 | 0 | 0 | 0 | 0 | 22172 |

