# Parser comparison — feature matrix

**Upstream trees:** large third-party drops under `external/*/` are fetched by **`./parser_comparison.sh prepare`** (or `scripts/download.sh` alone). The Git repository is expected to keep only wrappers and small patches, not full cvc5/Z3/smt-switch SDK trees.

| Parser | Language | Main dependencies | Parsing approach | Build | Notes |
|--------|----------|-------------------|------------------|-------|-------|
| **cvc5** | C++17 | cvc5 (C API + parser libs), libcvc5, libcvc5parser, libpicpoly/libpicpolyxx, libcadical, GMP/gmpxx; **clang++** + **libc++** for libcxx prebuilts | In-process cvc5 C API on SMT-LIB | CMake + make; prebuilt `cvc5-Linux-*` or source build | JSON with `ast_node_count`; libcxx prebuilts need `USE_CLANG_LIBCXX=1` or clang+libc++ |
| **z3** | C++17 | libz3; prebuilt `z3-*-x64-*` or source `z3-z3-*` | In-process Z3 C++ API | Makefile; auto-detect prebuilt vs source | JSON; prebuilt or source Z3 |
| **antlr4_parser** | Java | ANTLR 4.13.2 JAR, `SMTLIBv2.g4` | Grammar-driven lexer/parser + visitor | `make` / `make generate` from `.g4` | JSON; **`ast_node_count` counts parse-tree nodes** (much larger than semantic AST counts elsewhere); supply ANTLR JAR + grammar |
| **jsmtlib** | Java | jSMTLIB (sources or jar) | jSMTLIB SMT-LIB front end | `build.sh` or IDE jar | JSON; needs jSMTLIB sources/jar |
| **smt-switch** | C++17 | smt-switch, SmtLibReader (flex/bison), **cvc5 source** (`CVC5_HOME`), bison, flex | SmtLibReader + Cvc5 backend | CMake (`SMTLIB_READER=ON`, `BUILD_CVC5=ON`, `CVC5_HOME`) | JSON; **requires cvc5 source tree**, not prebuilt-only |
| **haskell-0.0.2** | Haskell | GHC, Cabal, **alex**; ghcup recommended | Library (`smt-lib`), no standalone parser binary | `cabal` workflow | Optional; needs **ghc**, **cabal-install**, **alex** |
| **pysmt** | Python 3 | `pip install pysmt` | `pysmt.smtlib.parser.SmtLibParser` | No compile; `python3 pysmt_parser.py <file>` | JSON; needs Python + pysmt |
| **prolog-smtlib** | Prolog (SWI) | `swipl` | Example `run.sh` around prolog libraries | No compile | Example only; extend `run.sh` for JSON |

---

## Quick dependency checklist

| Parser | Install / setup |
|--------|-----------------|
| cvc5 | Extract prebuilt under `cvc5/`; libcxx builds need `clang`, `libc++-dev` (or distro equivalent) |
| z3 | Prebuilt `z3-*-x64-*` under `z3/`, or Z3 source build include/lib |
| antlr4_parser | `antlr-4.13.2-complete.jar`, `SMTLIBv2.g4` (or smtlibv2-grammar) |
| jsmtlib | jSMTLIB sources (e.g. `jSMTLIB-0.9.10.1`) or jar |
| smt-switch | **bison**, **flex**; **`CVC5_HOME`** → cvc5 **source** root |
| haskell-0.0.2 | **GHC** + **Cabal** + **alex** |
| pysmt | **Python 3**, `pip install pysmt` |
| prolog-smtlib | **SWI-Prolog** (`swipl`) |

---

## Parsing styles

- **In-process C/C++ APIs:** cvc5, z3 — link solver libraries, parse in-process.
- **Grammar-driven:** antlr4_parser — ANTLR-generated parser independent of a solver.
- **Third-party libraries:** jsmtlib, pysmt, smt-switch reader, prolog-smtlib — each ecosystem’s SMT-LIB reader.
