# SMT-LIB 解析器对比工具 (Parser_Comparison)

本仓库提供用于**对比多种 SMT-LIB 解析器**的性能与行为的框架，面向论文实验与可复现评估。支持原生 C++ 解析器（SMTParser）、pySMT、jSMTLIB、Z3 前端、ANTLR4 等；可选扩展 SWI-Prolog / Haskell。

## 支持的解析器（parserName 与工具对应关系）

| parserName | 对应工具 / 实现 | 语言/运行时 | external 目录 | 检测方式 |
|------------|-----------------|-------------|----------------|----------|
| **native** | 本仓库内嵌 SMTParser（通过 smt_parser_wrapper 子进程调用） | C++ | —（构建产物） | wrapper 可执行文件存在 |
| **pysmt** | [pySMT](https://github.com/pysmt/pysmt) | Python 3 | `external/pysmt/` | `python3 -c "import pysmt"` |
| **jsmtlib** | jSMTLIB（SMT-LIB 2 解析与类型检查） | Java | `external/jsmtlib/` | 存在 `jsmtlib_parser.class` 或可运行脚本 |
| **z3** | Z3 求解器前端解析（仅解析，不求解） | C++ | `external/z3/` | 可执行文件 `z3_parser` 或等价脚本存在 |
| **antlr4** | ANTLR4 SMT-LIB 2.6 语法解析器 | Java | `external/antlr4_parser/` | jar 或 class 可运行 |
| **cvc5** | [cvc5](https://github.com/cvc5/cvc5) 求解器前端（解析 + 执行脚本） | C++ | `external/cvc5/` 或 PATH | `external/cvc5/build/bin/cvc5` 或系统 `cvc5` |
| **smt-switch** | [smt-switch](https://github.com/stanford-centaur/smt-switch) 通用 SMT API 包装 | C++ | `external/smt-switch/` | 需自行编译 `build/smt_switch_parser`，见 README |

**可选解析器（需自行配置，未配置则 `list` 不显示）**：

| parserName | 对应工具 | external 目录 | 说明 |
|------------|----------|----------------|------|
| **swipl** | SWI-Prolog SMT-LIB 2.6 | `external/prolog-smtlib/` | 需安装 `swipl`，并配置包装脚本 |
| **haskell** | Haskell smt-lib 库 | `external/haskell-0.0.2/` | 需 GHC + cabal 编译 |

**未集成**：OCaml SMT-LIB 2.0 解析器（已不再维护），仅作参考。

## 对比指标与口径

- **解析时间 (time_ms)**：wall time，单位毫秒。默认包含进程启动时间（`--include-startup true`）；部分解析器支持仅“纯解析”时间（如 native wrapper 内计时）。
- **内存 (peak_rss_kb)**：子进程峰值 RSS（Linux/WSL 下从 `/proc/<pid>/status` 的 VmHWM 或 wait4/getrusage 获取）。为公平比较，建议使用 `--isolate process`（默认），使所有解析器均在独立子进程中运行。
- **AST 节点数**：若解析器报告则写入结果；不同实现可能为 **raw 节点数** 或 **hash-consed 唯一节点数**，两者不可直接比较，报告中会区分 `raw_ast_nodes` / `unique_ast_nodes`，不可比时标为 N/A。
- **Feature coverage**：统计脚本中出现的 SMT-LIB **commands**（如 set-logic, declare-fun, assert, check-sat, get-model）与 **theory/features**（BV, FP, Arrays, Strings, Quantifiers, Let, Datatypes 等），用于描述“脚本使用了哪些特性”，而非虚构的“语法覆盖率”。

## 外部依赖与 external 目录规范

- **Python 3 + pySMT**：`pip install pysmt`
- **Java JRE**：供 jSMTLIB、ANTLR4 使用
- **SWI-Prolog**（可选）：供 swipl 解析器使用

**external 目录布局（与 parserName 对应）**：

```
external/
  antlr4_parser/    # ANTLR4 语法与 Java 解析器
  jsmtlib/          # jSMTLIB 源码/jar 与包装脚本
  pysmt/            # pysmt_parser.py 等
  z3/               # Z3 解析用可执行或脚本
  cvc5/             # cvc5 源码构建目录或 README（可选，也可用 PATH 中的 cvc5）
  smt-switch/       # smt-switch 解析器源码与构建（需自行编译 smt_switch_parser）
  prolog-smtlib/    # SWI-Prolog SMT-LIB 包（可选）
  haskell-0.0.2/    # Haskell 库（可选）
```

各外部解析器在**初始化时**检查对应路径或可执行是否存在；若不存在则该解析器不会被加入 `list`，并给出警告。

## 构建

```bash
mkdir build && cd build
cmake ..
make
```

要求：CMake 3.10+，C++17，以及 SMTParser 子模块/路径已配置。

## 使用方法

### 列出可用解析器

```bash
./smt_parser_comparison list
```

### 测试单个文件

```bash
./smt_parser_comparison test --file path/to/file.smt2
./smt_parser_comparison test --file path/to/file.smt2 --parser native --timeout 120
```

### 基准测试（多文件）

```bash
./smt_parser_comparison benchmark --file a.smt2 b.smt2 c.smt2
./smt_parser_comparison benchmark --parser pysmt --file a.smt2 --output my.csv --timeout 60
```

### 批量测试目录

```bash
./smt_parser_comparison batch --dir path/to/benchmark/directory
./smt_parser_comparison batch --dir path/to/benchmarks --output results.csv --timeout 180
```

### 推荐复现实验命令（论文级）

- 每个 (解析器, 文件) **重复 5 次**，取 **median** 作为报告值；**单线程**；统一**超时**。
- 示例（在实现 `--repeat` / `--raw-out` / `--manifest` 后）：

```bash
./smt_parser_comparison batch --dir /path/to/benchmarks \
  --repeat 5 --warmup 1 --timeout 60 \
  --output parser_comparison_report.csv \
  --raw-out raw_results.jsonl \
  --manifest manifest.json
```

- 当前版本若尚未支持 `--repeat`，请对同一批文件多次运行 batch 并自行取中位数；超时与单线程已支持。

### 常用选项

| 选项 | 说明 | 默认 |
|------|------|------|
| `-f, --file` | 测试的 SMT 文件（可多个） | — |
| `-d, --dir` | 批量测试的目录 | — |
| `-p, --parser` | 指定解析器名称 | 全部已加载 |
| `-o, --output` | 聚合 CSV 输出路径 | 见各命令说明 |
| `-t, --timeout` | 解析超时（秒） | 60 |

**计划中**（见 [docs/REFACTOR_PLAN.md](docs/REFACTOR_PLAN.md)）：`--repeat N`、`--warmup W`、`--raw-out`、`--manifest`、`--include-startup`、`--isolate`、`--shuffle`、`--seed`。

## 结果报告

- 控制台：每文件/每解析器的简要结果与摘要。
- 默认或指定 CSV：聚合表（文件名 × 解析器 → 时间、内存、节点数、成功与否）；后续将支持 schema 版本行与统计量（min/median/mean/std/p95）。
- 计划支持：`--raw-out results.jsonl` 记录每次运行的原始样本；`--manifest out.json` 记录机器信息、commit、编译选项、命令行与 seed，便于写入论文实验章节。

## 实验环境描述（可写入论文/ manifest）

> All experiments were conducted on a Linux machine running a 6.6-series kernel. The system is equipped with an AMD Ryzen 9 7940HS processor (8 cores, 16 threads) and 16 GB RAM. SMTParser and all compared solvers were compiled using g++ -O3 under identical settings. Unless otherwise stated, experiments were single-threaded, and runtimes are median of five runs.

（实验在 WSL 上跑时，上述描述仍适用；并行度默认不高，默认不并行。）

## 指标口径与局限性

- **时间**：wall time；默认含启动成本。不同运行时（JVM/Python/C++）启动差异较大，对比时建议固定 `--include-startup` 并说明。
- **内存**：子进程 peak RSS 为公平口径；若某解析器暂未接入子进程 RSS，则该项可能为 0 或 N/A，报告中应注明。
- **AST 节点**：各解析器定义可能不同（raw vs hash-consed），仅在同一解析器内或明确同一语义时可比；跨解析器比较时需说明局限性。
- **成功率/结果码**：将统一为结构化结果码（OK / PARSE_ERROR / TYPE_ERROR / UNSUPPORTED / TIMEOUT / OOM / CRASH / UNKNOWN），便于统计与表格。

## 扩展新解析器

1. 在 `src` 中实现继承 `ParserInterface` 的类（或 ExternalParser 子类），实现 `parse()` 并返回 `ParseResult`。
2. 在 `ParserManager::initializeParsers()`（或等价初始化逻辑）中注册；若为外部解析器，在构造时检查 external 路径/可执行是否存在，失败则跳过并警告。
3. 在 `printUsage()` 与本文 README 的“支持的解析器”表中加入 parserName 与说明。

## 许可

本项目采用 MIT 许可证开源。
