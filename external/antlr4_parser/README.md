# ANTLR4 SMT-LIB parser (benchmark driver)

SMT-LIB v2 parser used by **Parser_Comparison**, built from the official ANTLR4 grammar. It reports parse time, memory, and **parse-tree node count** (this count is larger than “semantic AST” counts from solver-integrated parsers).

## Layout

```
external/antlr4_parser/
├── antlr4_parser.java     # entrypoint + JSON reporting
├── Makefile
├── smtlibv2-grammar/      # or smtlibv2-grammar-master: contains SMTLIBv2.g4
└── antlr4-4.13.2/         # created by make setup-antlr4
```

## Quick start

```bash
make setup-antlr4    # download ANTLR 4.13.2 complete JAR
make check-deps
make generate        # .g4 -> Java
make                 # compile
make test            # quick run
```

One-shot: `make build-and-test` (if defined in the Makefile).

## Output (JSON)

```json
{
  "success": true,
  "parse_time": 15.234,
  "memory_usage": 1024,
  "ast_node_count": 42,
  "parsing_method": "antlr4_parse_tree",
  "errors": []
}
```

`ast_node_count` counts **parse tree** nodes (ANTLR visitor), not solver IR nodes.

## Makefile targets (common)

| Target | Action |
|--------|--------|
| `setup-antlr4` | Fetch ANTLR JAR into `antlr4-4.13.2/` |
| `check-deps` | Verify grammar + JAR |
| `generate` | Regenerate Java from `SMTLIBv2.g4` |
| `all` | Build the parser |
| `clean` / `clean-all` | Remove build artifacts |
| `test` / `test-detailed` / `test-complex` | Smoke tests |
| `run FILE=path.smt2` | Parse a single file |

## Requirements

- JDK 8+ (`javac`, `java`)
- `SMTLIBv2.g4` (from `smtlibv2-grammar` submodule or `smtlibv2-grammar-master`)
- ANTLR 4.13.2 complete JAR (handled by `make setup-antlr4`)

## References

- [ANTLR4](https://www.antlr.org/)  
- [SMT-LIB 2.6 reference (PDF)](http://smtlib.cs.uiowa.edu/papers/smt-lib-reference-v2.6-r2017-07-18.pdf)  
- Grammar project: <https://github.com/julianthome/smtlibv2-grammar>
