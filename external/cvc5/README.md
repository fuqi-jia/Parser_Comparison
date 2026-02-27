# cvc5 解析器支持

[cvc5](https://github.com/cvc5/cvc5) 是开源的 SMT 求解器（Cooperating Validity Checker 系列），支持 SMT-LIB 2.x 输入。本工具支持两种方式：

1. **cvc5_parser（推荐）**：链接 cvc5 C API（`cvc5_parser.h`），在进程内解析并输出 JSON（含 **ast_node_count**、parse_time、memory_usage）。需编译本目录下的 `cvc5_parser.cpp`，见下方「编译 cvc5_parser」。
2. **cvc5 二进制**：若未找到 `cvc5_parser` 可执行文件，则回退到直接调用 `cvc5` 命令，仅能采集时间与 peak RSS，无节点数。

## 使用方式

- **parserName**：`cvc5`
- 本工具会按以下顺序查找：
  1. **cvc5_parser**：`external/cvc5/build/cvc5_parser` 或 `external/cvc5/cvc5_parser`（输出 JSON，含 ast_node_count）
  2. **cvc5 二进制**：`external/cvc5/build/bin/cvc5`、`external/cvc5/bin/cvc5`、`external/cvc5/cvc5-Linux-*/bin/cvc5`，或 PATH 中的 `cvc5`

## 编译 cvc5_parser（C API，可输出节点数）

本目录提供 `cvc5_parser.cpp`，使用 cvc5 的 C 解析 API 读入 SMT-LIB 并统计断言/声明项的 AST 节点数，向 stdout 输出一行 JSON。

- **使用预编译包**（如 `cvc5-Linux-x86_64-libcxx-static`）：预编译包多为 **libc++** 构建，需用 **clang** 并指定 `-stdlib=libc++` 链接，例如：
  ```bash
  cd external/cvc5 && mkdir -p build && cd build
  cmake .. -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_FLAGS="-stdlib=libc++" -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++"
  make
  ```
  若系统无 clang/libc++，可改用「从源码构建」cvc5 后，用其 `include`/`lib` 编译本目录的 `cvc5_parser`（此时可用 g++）。
- **使用 cvc5 源码**：从 cvc5 源码构建后，将其 `include`、`lib` 指到本 CMake，或安装到系统后再链接。

## 安装 cvc5（二进制，用于回退或单独使用）

### 方式一：从源码构建（推荐，便于控制版本与选项）

```bash
git clone https://github.com/cvc5/cvc5.git
cd cvc5
./configure.sh
cd build
make -j$(nproc)
# 可执行文件在 build/bin/cvc5
```

将构建目录放到本仓库下即可，例如：

```bash
# 在 Parser_Comparison 根目录
ln -s /path/to/cvc5/build external/cvc5/build
# 或直接克隆到 external
git clone https://github.com/cvc5/cvc5.git external/cvc5
cd external/cvc5 && ./configure.sh && cd build && make -j$(nproc)
```

### 方式二：使用预编译包（推荐，免编译）

从 [cvc5 Releases](https://github.com/cvc5/cvc5/releases) 下载对应平台的包（如 `cvc5-Linux-x86_64-libcxx-static.tar.xz`），解压到 `external/cvc5/` 下，例如：

```text
external/cvc5/cvc5-Linux-x86_64-libcxx-static/
  bin/cvc5
  include/ ...
```

本工具会自动识别 `cvc5-Linux-*` 或 `cvc5-*-*` 形式目录并使用其中的 `bin/cvc5`。

### 方式三：使用系统或 conda 安装

若系统或 conda 环境中已安装 cvc5 并加入 PATH，无需在 `external/cvc5` 下放置任何文件，本工具会直接使用 `cvc5` 命令。

## 行为说明

- 命令形式：`cvc5 "<smt2 文件路径>"`
- cvc5 会解析并执行脚本（含 check-sat 等）；解析失败时以非零退出码并往 stderr 输出错误。
- 本工具不解析 cvc5 的 stdout（如 `sat`/`unsat`），仅根据 **退出码** 与 **stderr** 判断成功/失败，并统一采集 **wall time** 与 **peak RSS**（Linux 下由 ProcessRunner 从 `/proc` 读取）。

## 参考

- 仓库：<https://github.com/cvc5/cvc5>
- 文档：<https://cvc5.github.io/docs/>
