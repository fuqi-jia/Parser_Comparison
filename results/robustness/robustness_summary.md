# Native (SMTParser) robustness summary

Source: rows with `parser=native` in `parser_benchmark_table.csv`; grouped by theory directory name (e.g. `QF_BV`) in the benchmark path.

## Overall totals

| Metric | Count | Share |
| --- | ---: | ---: |
| ok | 161852 | 99.9179% |
| timeout | 133 | 0.0821% |
| fail | 0 | 0.0000% |
| other | 0 | 0.0000% |

## By theory family

| Theory | ok | timeout | fail | other | total | fail%+timeout% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QF_AX | 551 | 0 | 0 | 0 | 551 | 0.0000% |
| QF_BV | 46088 | 103 | 0 | 0 | 46191 | 0.2230% |
| QF_FP | 40406 | 0 | 0 | 0 | 40406 | 0.0000% |
| QF_LIA | 13285 | 21 | 0 | 0 | 13306 | 0.1578% |
| QF_LRA | 1747 | 6 | 0 | 0 | 1753 | 0.3423% |
| QF_NIA | 25452 | 0 | 0 | 0 | 25452 | 0.0000% |
| QF_NRA | 12151 | 3 | 0 | 0 | 12154 | 0.0247% |
| QF_S | 22172 | 0 | 0 | 0 | 22172 | 0.0000% |
