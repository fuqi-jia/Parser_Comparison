## Round-trip correctness (SMTParser)

Two experimental settings are common in front-end work: **(A) same-engine parse → print → reparse** and **(B) cross-parser** runs on one file. This table is **(A) only**: SMTParser reads the original script, emits SMT2 via `dumpSMT2`, then SMTParser parses that dump again (two parser objects, **one** implementation). The intermediate file can change structure, so first-pass and second-pass **node counts are not tautologically equal**—`mismatch` is informative. **(B)** is the multi-parser `benchmark`, which records `ast_nodes` per tool on the same path.

_No aggregate results yet._
