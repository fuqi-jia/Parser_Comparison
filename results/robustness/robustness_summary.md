## Native parser robustness by theory (SOMTParser)

Per-theory counts of SOMTParser (`native`) front-end outcomes (`ok`, `timeout`, `fail`, `other`) on the evaluated instances.

### Overall totals

| Metric | Count | Share |
| --- | ---: | ---: |
| ok | 161931 | 99.9667% |
| timeout | 54 | 0.0333% |
| fail | 0 | 0.0000% |
| other | 0 | 0.0000% |

### By theory family

| Theory | ok | timeout | fail | other | total | fail%+timeout% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 551 | 0 | 0 | 0 | 551 | 0.0000% |
| QF_BV | 46142 | 49 | 0 | 0 | 46191 | 0.1061% |
| QF_FP | 40406 | 0 | 0 | 0 | 40406 | 0.0000% |
| QF_LIA | 13303 | 3 | 0 | 0 | 13306 | 0.0225% |
| QF_LRA | 1753 | 0 | 0 | 0 | 1753 | 0.0000% |
| QF_NIA | 25452 | 0 | 0 | 0 | 25452 | 0.0000% |
| QF_NRA | 12152 | 2 | 0 | 0 | 12154 | 0.0165% |
| QF_S | 22172 | 0 | 0 | 0 | 22172 | 0.0000% |

### Round-trip side summary (when round-trip run is available)

| Theory | roundtrip_ok | mismatch | fail | timeout |
| --- | ---: | ---: | ---: | ---: |
| QF_AX | 454 | 97 | 0 | 0 |
| QF_BV | 36888 | 1216 | 4 | 8083 |
| QF_FP | 40381 | 25 | 0 | 0 |
| QF_LIA | 10511 | 0 | 0 | 2795 |
| QF_LRA | 1749 | 0 | 0 | 4 |
| QF_NIA | 25452 | 0 | 0 | 0 |
| QF_NRA | 12151 | 0 | 0 | 3 |
| QF_S | 22172 | 0 | 0 | 0 |

Round-trip totals: ok=149758 mismatch=1338 fail=4 timeout=10885

