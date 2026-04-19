# smt-switch parser integration

[smt-switch](https://github.com/stanford-centaur/smt-switch) is Stanford Centaur’s **generic C++ SMT API**. This repo ships **`smt_switch_parser`**, which uses smt-switch’s **SmtLibReader** (flex/bison) to parse SMT-LIB and prints the JSON format expected by the benchmark harness (**`ast_node_count`** included).

## Discovery order

- **parser name:** `smt-switch`
- Executable search order under `external/smt-switch`:
  1. `external/smt-switch/build/smt_switch_parser`
  2. `external/smt-switch/build/smt-switch-1.0.6/smt_switch_parser` (when built via nested CMake)
  3. `external/smt-switch/smt-switch-1.0.6/build/smt_switch_parser`

## Building `smt_switch_parser` (SmtLibReader + CVC5 backend)

Requires **smt-switch-1.0.6** sources, **bison ≥ 3.7**, **flex ≥ 2.6**, and a **cvc5 source tree** (`CVC5_HOME`) for smt-switch’s CVC5 backend.

### Build inside `smt-switch-1.0.6/`

```bash
cd external/smt-switch/smt-switch-1.0.6
mkdir build && cd build
cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5/source
make
# produces build/smt_switch_parser when src/smt_switch_parser.cpp is present
```

`CVC5_HOME` must be the **cvc5 source root** (with `src/`, `build/`, …). smt-switch links against artifacts such as `build/src/libcvc5.a`.

### Build from `external/smt-switch/` root

```bash
cd external/smt-switch
mkdir build && cd build
cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5/source
make
# produces build/smt-switch-1.0.6/smt_switch_parser
```

## Output format

One JSON line on stdout, for example:

```json
{"success": true, "parse_time": 12.5, "memory_usage": 1024, "ast_node_count": 42, "errors": []}
```

On parse failure, `success` is `false` and `errors` contains a short message.

## References

- Repository: <https://github.com/stanford-centaur/smt-switch>  
- Supported backends include Bitwuzla, Boolector, cvc5, Z3, MathSAT, Yices2, etc.
