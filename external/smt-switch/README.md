# smt-switch 解析器支持

[smt-switch](https://github.com/stanford-centaur/smt-switch) 是斯坦福 Centaur 的**通用 C++ SMT API**。本仓库提供**独立可执行** `smt_switch_parser`（不链接 smt-switch 库），通过调用 **cvc5 二进制**解析 SMT-LIB 并输出本对比工具所需的 JSON，便于与 z3、cvc5 等解析器一起参与 benchmark。

## 使用方式

- **parserName**：`smt-switch`
- 本工具默认在 `external/smt-switch` 下查找可执行文件，顺序：
  1. `external/smt-switch/build/smt_switch_parser`（本仓库 CMake 或手动编译）
  2. `external/smt-switch/smt-switch-1.0.6/build/smt_switch_parser`（或其它 `smt-switch-*` 发布目录下的 `build/smt_switch_parser`）

## 编译 smt_switch_parser（推荐：本仓库独立编译）

本目录提供不依赖 smt-switch 库的实现，仅依赖 **cvc5 二进制**（用于实际解析）。编译后即可参与对比。

```bash
# 在 Parser_Comparison 根目录
mkdir -p external/smt-switch/build
cd external/smt-switch/build
cmake ..
make
# 得到 build/smt_switch_parser
```

或使用单文件编译（无需 CMake）：

```bash
cd external/smt-switch
mkdir -p build
c++ -std=c++17 -O2 -o build/smt_switch_parser src/smt_switch_parser.cpp
```

`smt_switch_parser` 会自行查找 cvc5：优先使用环境变量 `CVC5_BIN`，否则在相对路径下查找 `../cvc5/.../bin/cvc5` 或系统 `cvc5`。确保 cvc5 已就绪（如 `external/cvc5/cvc5-Linux-x86_64-libcxx-static/bin/cvc5` 或 PATH 中的 `cvc5`）。

## 可选：使用 smt-switch 发布包目录

若使用 smt-switch 官方发布包（如解压得到 `smt-switch-1.0.6`），可将本仓库的 `src/smt_switch_parser.cpp` 复制到该目录下，用其 CMake 或单独编译，生成 `smt-switch-1.0.6/build/smt_switch_parser`。本工具会自动识别 `external/smt-switch/smt-switch-*/build/smt_switch_parser`。

## 输出格式

可执行文件需向 **stdout** 输出一行 JSON，例如：

```json
{"success": true, "parse_time": 12.5, "memory_usage": 0, "ast_node_count": 0, "errors": []}
```

解析失败时 `success: false`，并在 `errors` 中填入简要信息。本仓库提供的 `smt_switch_parser.cpp` 已实现该格式。

## 参考

- 仓库：<https://github.com/stanford-centaur/smt-switch>
- 支持的求解器：Bitwuzla, Boolector, cvc5, Z3, MathSAT, Yices2 等
