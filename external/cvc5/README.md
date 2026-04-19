# cvc5 parser integration

[cvc5](https://github.com/cvc5/cvc5) is an open-source SMT solver (Cooperating Validity Checker family) with SMT-LIB 2.x input. This benchmark harness supports two modes:

1. **`cvc5_parser` (recommended):** links the cvc5 C API (`cvc5_parser.h`), parses in process, prints one JSON line to stdout (**`ast_node_count`**, parse time, memory). Build `cvc5_parser.cpp` in this directory (see **Building cvc5_parser**).
2. **`cvc5` binary fallback:** if `cvc5_parser` is not found, the harness may invoke the `cvc5` executable and only collect wall time and peak RSS (no AST node count).

## Discovery order

- **parser name:** `cvc5`
- Search order:
  1. `external/cvc5/build/cvc5_parser` or `external/cvc5/cvc5_parser` (JSON with `ast_node_count`)
  2. `cvc5` binary: `external/cvc5/build/bin/cvc5`, `external/cvc5/bin/cvc5`, `external/cvc5/cvc5-Linux-*/bin/cvc5`, or `cvc5` on `PATH`

## Building `cvc5_parser` (C API, emits node count)

`cvc5_parser.cpp` uses the cvc5 C parser API, counts assertion/declaration AST nodes, and prints JSON.

- **Prebuilt package** (e.g. `cvc5-Linux-x86_64-libcxx-static`): many builds use **libc++**; compile and link with **clang** and `-stdlib=libc++`, for example:
  ```bash
  cd external/cvc5 && mkdir -p build && cd build
  cmake .. -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_FLAGS="-stdlib=libc++" -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++"
  make
  ```
  Without clang/libc++, build cvc5 from source first, then point this CMake at that install’s `include`/`lib` (g++ is fine against a GNU-libstdc++ cvc5 build).
- **cvc5 from source:** configure and build cvc5, then set include/lib paths for this wrapper’s CMake.

## Installing the `cvc5` binary (fallback or standalone)

### Option A — build from source

```bash
git clone https://github.com/cvc5/cvc5.git
cd cvc5
./configure.sh
cd build
make -j"$(nproc)"
# binary: build/bin/cvc5
```

Place the tree under this repo, e.g.:

```bash
git clone https://github.com/cvc5/cvc5.git external/cvc5
cd external/cvc5 && ./configure.sh && cd build && make -j"$(nproc)"
```

### Option B — prebuilt release

Download a release from [cvc5 Releases](https://github.com/cvc5/cvc5/releases) (e.g. `cvc5-Linux-x86_64-libcxx-static.tar.xz`), extract under `external/cvc5/`:

```text
external/cvc5/cvc5-Linux-x86_64-libcxx-static/
  bin/cvc5
  include/ ...
```

The harness picks up directories matching `cvc5-Linux-*` or `cvc5-*-*` and uses `bin/cvc5`.

### Option C — system or Conda

If `cvc5` is already on `PATH`, no files are required under `external/cvc5`.

## Behaviour notes

- Invocation shape: `cvc5 "<path-to.smt2>"`
- cvc5 parses and may execute the script (including `check-sat`); parse errors yield non-zero exit and stderr.
- The comparison harness does not interpret solver output (`sat`/`unsat`); it uses **exit code** and **stderr** for success/failure and records **wall time** and **peak RSS** (Linux: via `/proc` in ProcessRunner).

## References

- Repository: <https://github.com/cvc5/cvc5>  
- Docs: <https://cvc5.github.io/docs/>
