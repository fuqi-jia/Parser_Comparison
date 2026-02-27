# smt-switch 解析器支持

[smt-switch](https://github.com/stanford-centaur/smt-switch) 是斯坦福 Centaur 的**通用 C++ SMT API**。本仓库提供 **smt_switch_parser**，使用 smt-switch 自带的 **SmtLibReader**（flex/bison）解析 SMT-LIB，并输出本对比工具所需的 JSON（含 **ast_node_count**）。

## 使用方式

- **parserName**：`smt-switch`
- 本工具在 `external/smt-switch` 下查找可执行文件，顺序：
  1. `external/smt-switch/build/smt_switch_parser`
  2. `external/smt-switch/build/smt-switch-1.0.6/smt_switch_parser`（从 add_subdirectory 构建时）
  3. `external/smt-switch/smt-switch-1.0.6/build/smt_switch_parser`

## 编译 smt_switch_parser（需 SmtLibReader + CVC5 后端）

本实现依赖 **smt-switch-1.0.6** 源码、**bison ≥ 3.7**、**flex ≥ 2.6**，以及 **cvc5 源码**（供 smt-switch 的 CVC5 后端链接）。

### 在 smt-switch-1.0.6 目录内构建

```bash
cd external/smt-switch/smt-switch-1.0.6
mkdir build && cd build
cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5/source
make
# 得到 build/smt_switch_parser（且存在 ../src/smt_switch_parser.cpp 时）
```

`CVC5_HOME` 需指向 **cvc5 源码根目录**（含 `src/`、`build/` 等），smt-switch 会链接其 `build/src/libcvc5.a` 等。

### 从 external/smt-switch 根目录构建

```bash
cd external/smt-switch
mkdir build && cd build
cmake .. -DSMTLIB_READER=ON -DBUILD_CVC5=ON -DCVC5_HOME=/path/to/cvc5/source
make
# 得到 build/smt-switch-1.0.6/smt_switch_parser
```

## 输出格式

可执行文件向 **stdout** 输出一行 JSON，例如：

```json
{"success": true, "parse_time": 12.5, "memory_usage": 1024, "ast_node_count": 42, "errors": []}
```

解析失败时 `success: false`，并在 `errors` 中填入简要信息。

## 参考

- 仓库：<https://github.com/stanford-centaur/smt-switch>
- 支持的求解器：Bitwuzla, Boolector, cvc5, Z3, MathSAT, Yices2 等
