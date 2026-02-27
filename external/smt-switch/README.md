# smt-switch 解析器支持

[smt-switch](https://github.com/stanford-centaur/smt-switch) 是斯坦福 Centaur 的**通用 C++ SMT API**，对多种求解器（Bitwuzla、Boolector、cvc5、Z3、MathSAT、Yices2 等）提供统一接口。本工具通过调用 **smt-switch 包装的可执行**（需自行编译）来解析 SMT-LIB 文件。

## 使用方式

- **parserName**：`smt-switch`
- 本工具默认查找可执行文件：`external/smt-switch/build/smt_switch_parser`
- 该二进制需输出与 Z3/cvc5 等一致的 **JSON**（含 `success`, `parse_time`, `memory_usage`, `ast_node_count`, `errors`），以便对比框架解析结果。

## 编译 smt_switch_parser

smt-switch 是库而非独立可执行程序，需要您在本目录下：

1. 克隆并构建 smt-switch（及至少一个后端，如 cvc5 或 Z3）
2. 编写/编译一个小的“解析器”程序，链接 smt-switch + 后端，读入 SMT-LIB 文件并输出上述 JSON

### 1. 构建 smt-switch 与后端

```bash
# 克隆
git clone https://github.com/stanford-centaur/smt-switch.git
cd smt-switch

# 按官方文档安装后端，例如 cvc5
./contrib/setup-cvc5.sh
./configure.sh --cvc5
cd build
make -j$(nproc)
```

详见 [smt-switch README](https://github.com/stanford-centaur/smt-switch#quick-start) 与 [Solvers](https://github.com/stanford-centaur/smt-switch#solvers)。

### 2. 解析器二进制

在 `external/smt-switch/` 下提供源码 `smt_switch_parser.cpp`（或使用 `src/` 下的示例），编译为 `build/smt_switch_parser`，要求：

- 接受一个命令行参数：SMT-LIB 文件路径
- 解析该文件（通过 smt-switch API 或其所用后端的解析能力）
- 向 **stdout** 输出一行 JSON，格式示例：

```json
{"success": true, "parse_time": 12.5, "memory_usage": 2048, "ast_node_count": 0, "errors": []}
```

- 解析失败时 `success: false`，并在 `errors` 中填入简要信息

若 smt-switch 的 C++ API 支持“仅解析不求解”，可在解析后直接输出上述 JSON；否则可在解析+一次 check-sat 后根据是否异常来设置 `success`。

### 3. 与本仓库对接

将编译得到的可执行文件放到：

```text
external/smt-switch/build/smt_switch_parser
```

或在构建时让本工具通过 `SMT_SWITCH_PARSER` 等环境变量指向该路径（若后续支持）。完成后运行 `./smt_parser_comparison list` 应能看到 `smt-switch` 解析器。

## 可选：示例源码桩

`src/smt_switch_parser.cpp`（若存在）为示例桩，展示如何链接 smt-switch 与后端、读入文件并输出 JSON。需根据您安装的 smt-switch 版本与后端调整 include 路径与 CMake/Makefile。

## 参考

- 仓库：<https://github.com/stanford-centaur/smt-switch>
- 支持的求解器：Bitwuzla, Boolector, cvc5, Z3, MathSAT, Yices2 等
