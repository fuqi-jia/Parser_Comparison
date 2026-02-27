# cvc5 解析器支持

[cvc5](https://github.com/cvc5/cvc5) 是开源的 SMT 求解器（Cooperating Validity Checker 系列），支持 SMT-LIB 2.x 输入。本工具将 **cvc5 二进制** 作为“解析器”调用：对给定 `.smt2` 文件执行 cvc5，根据退出码与 stderr 判断解析是否成功，并采集 wall time 与子进程 peak RSS。

## 使用方式

- **parserName**：`cvc5`
- 本工具会按以下顺序查找 cvc5 可执行文件：
  1. `external/cvc5/build/bin/cvc5`（从源码构建的默认路径）
  2. `external/cvc5/bin/cvc5`
  3. `external/cvc5/cvc5-Linux-x86_64-libcxx-static/bin/cvc5`（或其它 `cvc5-*` / `cvc5-Linux-*` 预编译目录下的 `bin/cvc5`）
  4. 若传入路径为文件则直接使用
  5. 否则使用 PATH 中的 `cvc5`

## 安装 cvc5

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
