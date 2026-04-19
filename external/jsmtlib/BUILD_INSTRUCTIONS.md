# jSMTLIB — build and run (Parser_Comparison)

[jSMTLIB](https://github.com/SMTLIBv2/jSMTLIB) is a Java library for SMT-LIB v2.x: parsing, printing, typing, solver bridges, etc. This document covers how to build it for use with **Parser_Comparison**’s harness.

## Requirements

- **JDK** 8 or newer (`javac`, `java`)
- **Eclipse** (optional; the upstream project is Eclipse-oriented)
- Optional: **Maven** / **Ant** if you prefer those over raw `javac`

## Project layout (excerpt)

```
external/jsmtlib/jSMTLIB-0.9.10.1/
├── SMT/
│   ├── src/org/smtlib/   # core packages (SMT.java, parsers, solvers, …)
│   └── test/
├── SMTPlugin/
└── SMTUpdateSite/
```

## Build methods

### 1. Eclipse (simplest if you already use it)

1. **File → Import → Existing Projects into Workspace**  
2. Select `external/jsmtlib/jSMTLIB-0.9.10.1/SMT`  
3. **Project → Build Project** (or enable *Build Automatically*)  
4. Ensure the JRE is JDK 8+ (**Project → Properties → Java Build Path**)

### 2. Command line (jar for the harness)

```bash
cd external/jsmtlib/jSMTLIB-0.9.10.1/SMT
mkdir -p out
find src -name "*.java" > sources.txt
javac -d out @sources.txt
jar cf jsmtlib.jar -C out .
```

Adjust `src` paths if your tree differs; include all packages under `org/smtlib`.

### 3. Maven (if you add a `pom.xml`)

Create a minimal `pom.xml` with `groupId`/`artifactId`, source directory `src`, Java 1.8+, then:

```bash
mvn -q package
```

Use the produced jar on the classpath for `java -cp …`.

## Run the bundled API example

```bash
cd external/jsmtlib/jSMTLIB-0.9.10.1/SMT
java -cp out org.smtlib.APIExample
# or: java -cp jsmtlib.jar org.smtlib.APIExample
```

In Eclipse: open `APIExample.java` → **Run As → Java Application**.

## Hooking into Parser_Comparison

The comparison driver expects a **wrapper** that prints JSON (success, timings, optional node counts). Typical pattern:

1. Build `jsmtlib.jar` (or use Eclipse output directory on the classpath).
2. Point the C++ harness `JSMTLIBParser` at your `java -jar …` command (see `external/jsmtlib/run.sh` / project-specific wrapper).
3. Ensure `JAVA_TOOL_OPTIONS` / heap flags match your machine (large benchmarks may need `-Xmx`).

If stdout is not yet JSON, extend the Java entry class to emit the same schema as other parsers (`success`, `parse_time`, `memory_usage`, `ast_node_count`, `errors`).

## JVM tips for benchmarks

```bash
export JAVA_TOOL_OPTIONS="-Xmx2g -XX:+UseG1GC"
```

Increase `-Xmx` when parsing very large `.smt2` files.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `java.lang.OutOfMemoryError` | Raise `-Xmx`; run fewer parallel jobs. |
| `cannot find symbol` during `javac` | JDK version; missing generated sources; wrong source root. |
| `NoClassDefFoundError` at runtime | Classpath must include **all** compiled packages and dependencies. |

## References

- jSMTLIB: <https://github.com/SMTLIBv2/jSMTLIB>  
- SMT-LIB: <http://smtlib.cs.uiowa.edu/>
