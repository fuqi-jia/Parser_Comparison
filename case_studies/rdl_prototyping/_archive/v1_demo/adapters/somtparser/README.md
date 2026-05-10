# SOMTParser RDL adapter

`somt-rdl-adapter` is the SOMTParser-backed front end for the RDL prototyping
case study. It is intentionally tiny and uses SOMTParser only as a parser /
typed DAG provider.

## Contract

```
somt-rdl-adapter input.smt2 output.json
```

* On success, writes an `rdl_atoms.json` payload conforming to
  `case_studies/rdl_prototyping/schema/rdl_atoms.schema.json`.
* If the input contains constructs outside the P0 fragment (non-conjunctive
  Boolean structure, quantifiers, arrays, BV/FP/strings, UF, non-linear
  arithmetic), the adapter writes a `status=unsupported` payload with a
  `reason` string and exits 0.
* If parsing fails or an exception is raised during traversal, the adapter
  writes a `status=error` payload and exits 0.

## What the adapter does (front-end work)

1. Parses the SMT-LIB2 file via `SOMTParser::Parser::parse`.
2. Reads the assertion list via `SOMTParser::Parser::getAssertions`.
3. Walks the typed DAG via `DAGNode::getKind` / `getChild` / `getChildrenSize`
   / `getName` / `isVar` / `isVInt` / `isVReal` / `isCInt` / `isCReal`.
4. Flattens top-level `(and ...)` and rejects `or / not / implies / ite /
   forall / exists` for P0.
5. Linearises each atom into an exact rational form using `mpq_class` from
   GMP/GMPXX (already a transitive dependency of SOMTParser).
6. Normalises every difference constraint into `lhs - rhs (<=|<) bound`,
   splitting equalities into two `<=` atoms and using a special `ZERO` node
   for unary bounds.

## What the adapter explicitly does NOT do

* It never invokes `SOMTParser::Parser::checkSat`, `getModel`, or any built-in
  solver. The whole point of the case study is to compare front ends, not
  solvers.
* It does not call `toCNF` / `getCNFAtoms` / `getCNFBoolVars`. Those APIs are
  available and would be the natural starting point for a future P1 Boolean
  RDL extension via CaDiCaL user propagators, but P1 is out of scope in v1.

## Building

The example only builds when the top-level CMake is configured with:

```
cmake -B build_rdl -S . -DBUILD_RDL_CASE_STUDY=ON
cmake --build build_rdl --target somt-rdl-adapter
```

`scripts/reproduce.sh` does this automatically.
