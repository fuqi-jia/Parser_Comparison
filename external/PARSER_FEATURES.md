# Parser 对比 — 各 Parser 特征一览

| Parser | 实现语言 | 主要依赖 | 解析方式 | 构建方式 | 备注 |
|--------|----------|----------|----------|----------|------|
| **cvc5** | C++17 | cvc5（C API + parser 库）、libcvc5、libcvc5parser、libpicpoly/libpicpolyxx、libcadical、GMP/gmpxx；预编译包为 libcxx 时需 **clang++** 与 **libc++** | 进程内调用 cvc5 C API 解析 SMT-LIB，不调二进制 | CMake + make；支持预编译包（cvc5-Linux-*）或自编 cvc5 | 输出 JSON（含 ast_node_count）；预编译包名含 `libcxx` 时需 `USE_CLANG_LIBCXX=1` 或安装 clang+libc++ |
| **z3** | C++17 | Z3 库（libz3）；预编译包 z3-*-x64-* 或源码 z3-z3-* | 进程内调用 Z3 C++ API 解析 SMT-LIB | Makefile；自动检测预编译/源码目录，lib 或 bin 下找 libz3 | 输出 JSON；支持预编译或从源码构建 Z3 |
| **antlr4_parser** | Java | ANTLR 4.13.2（antlr-*-complete.jar）、SMTLIBv2.g4 语法（smtlibv2-grammar 或本地） | 语法驱动：ANTLR4 生成 Lexer/Parser，Visitor/Listener 遍历 AST | make（需 `make generate` 从 .g4 生成 Java 再编译） | 输出 JSON；**ast_node_count 为整棵 parse tree 节点数**，会明显多于其他 parser 的“语义 AST”节点数；需自行准备 ANTLR JAR 与 SMTLIBv2.g4 |
| **jsmtlib** | Java | jSMTLIB 库（jSMTLIB-0.9.10.1 源码或 jar） | 调用 jSMTLIB 解析 SMT-LIB | build.sh 编译或 IDE 导出 jar | 输出 JSON；本目录脚本为占位，完整解析需 jSMTLIB 源码/ jar |
| **smt-switch** | C++17 | smt-switch 库、SmtLibReader（flex/bison）、**cvc5 源码**（CVC5_HOME）、bison、flex | 使用 smt-switch 的 SmtLibReader + Cvc5 后端解析 SMT-LIB | CMake（需 `SMTLIB_READER=ON`、`BUILD_CVC5=ON`、`CVC5_HOME`） | 输出 JSON；**必须提供 cvc5 源码目录**，不能只用预编译包 |
| **haskell-0.0.2** | Haskell | GHC、Cabal（cabal-install）、**alex**（词法生成器）；推荐 ghcup 安装 | 库项目（smt-lib），无独立 parser 可执行文件；run.sh 可用 ghci 或脚本调用 | cabal update && cabal configure && cabal build | 无独立可执行文件；需 **ghc**、**cabal-install** 与 **alex**（`cabal install alex` 或 `apt install alex`） |
| **pysmt** | Python 3 | pysmt 库（`pip install pysmt`） | 使用 pysmt 的 `pysmt.smtlib.parser.SmtLibParser` 解析 | 无需编译；直接 `python3 pysmt_parser.py <file.smt2>` | 脚本+库；输出 JSON；依赖 Python 环境与 pysmt |
| **prolog-smtlib** | Prolog（SWI-Prolog） | SWI-Prolog（`swipl`） | 加载 prolog/smtlib.pl，smtlib_read_script/2 等；当前 run.sh 为示例，非标准 JSON 输出 | 无需编译；`run.sh <file.smt2>` | 库用法；需 **swipl**；若需统一 JSON 需在 run.sh 中扩展 |

---

## 依赖安装速查

| Parser | 需安装/设置 |
|--------|-------------|
| cvc5 | 预编译包解压到 cvc5/ 下；若为 libcxx 包：`clang`、`libc++-dev`（或 `libc++-18-dev`） |
| z3 | 预编译包 z3-*-x64-* 解压到 z3/，或 Z3 源码构建后指向 include/lib |
| antlr4_parser | `antlr-4.13.2-complete.jar`、`SMTLIBv2.g4`（或 smtlibv2-grammar-master） |
| jsmtlib | jSMTLIB 源码（如 jSMTLIB-0.9.10.1）或导出 jar |
| smt-switch | **bison**、**flex**；**CVC5_HOME** 指向 cvc5 **源码**根目录 |
| haskell-0.0.2 | **GHC** + **Cabal** + **alex**（如 `apt install ghc cabal-install alex` 或 ghcup + `cabal install alex`） |
| pysmt | **Python 3**、`pip install pysmt` |
| prolog-smtlib | **SWI-Prolog**（`apt install swi-prolog`） |

---

## 解析方式简要说明

- **C/ C++ API 进程内**：cvc5、z3 — 直接链接求解器库，在进程内解析，无子进程。
- **语法驱动**：antlr4_parser — 由 SMT-LIB 语法生成解析器，与求解器无关。
- **第三方解析库**：jsmtlib（Java）、pysmt（Python）、smt-switch（C++ Reader）、prolog-smtlib（Prolog）— 各用各自生态的 SMT-LIB 解析实现。
