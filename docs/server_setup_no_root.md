# 无 root 服务器部署实验环境

在**没有 root 权限**的服务器上，各 external parser 依赖不同（Python/Java/C++/Haskell 等），可通过「用户空间安装」统一解决：不装系统包，所有依赖装到 `$HOME` 或项目目录。

## 思路概览

| 依赖类型 | 方案 | 说明 |
|----------|------|------|
| Python + pysmt | Conda 或 venv | 用 `PYTHON` 指向 conda/venv 的 python，benchmark 会优先读该环境变量 |
| Java (antlr4, jsmtlib) | Conda 的 openjdk 或 用户目录 JDK | 保证 `java`/`javac` 在 PATH 前 |
| C++ (cvc5, z3, smt-switch) | 不装系统包 | 用已有 gcc/clang、cmake；产物在 `external/*/build/`，无需 make install |
| Haskell (可选) | ghcup | 安装到 `~/.ghcup`，无需 root |
| SWI-Prolog (可选) | Conda 或 源码安装到 `$HOME` | 若不做 prolog parser 对比可跳过 |

推荐：**用 Conda 建一个环境**，把 Python、pysmt、OpenJDK 都放进去；C++ 只在本机编译，不 install 到系统。

---

## 一、用 Conda 建统一环境（推荐）

### 1. 安装 Miniconda（用户目录）

若还没有 conda：

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p "$HOME/miniconda3"
"$HOME/miniconda3/bin/conda" init bash
# 重新开一个 shell 或 source ~/.bashrc
```

### 2. 创建环境并安装依赖

```bash
cd /path/to/Parser_Comparison
# 创建环境（Python 3.10+ 即可）
conda create -n smtbench python=3.11 -y
conda activate smtbench

# 实验必需：pysmt + Java（antlr4、jsmtlib 用）
conda install -c conda-forge pysmt openjdk=17 -y

# 可选：若需要 prolog 对比
# conda install -c conda-forge swi-prolog -y
```

### 3. 让 benchmark 使用该环境

运行 benchmark 前激活环境，并设置 `PYTHON`（C++ 主程序会优先用该解释器调 pysmt）：

```bash
conda activate smtbench
export PYTHON="$(which python)"
# 然后照常运行
./scripts/run_sampled_full.sh
# 或
python3 scripts/run_parser_benchmark.py --file-list benchmark/sampled/file_list.txt ...
```

若用 `nohup` 或 cron，建议在脚本里写死：

```bash
export PYTHON="$HOME/miniconda3/envs/smtbench/bin/python"
```

---

## 二、各 Parser 在无 root 下的准备

### 已由 Conda 覆盖

- **pysmt**：`conda install pysmt`，用 `PYTHON` 指向该环境即可。
- **antlr4 / jsmtlib**：需要 Java；`conda install openjdk` 后，同一 shell 里 `java`/`javac` 即来自该环境。

### C++ 类（无需 install 到系统）

- **cvc5**、**z3**、**smt-switch**：用 `scripts/build_all_parsers.sh` 在项目内编译即可，可执行文件在 `external/*/build/` 下，主程序会到这些路径找，**不需要** `make install` 或 root。
- 若系统没有 cmake/g++：可用 `conda install -c conda-forge cmake compilers`，再在激活该环境的情况下执行 `build_all_parsers.sh`。
- cvc5 若用 libcxx 预编译包：需本机有 clang 和 libc++；无 root 时可用 conda：`conda install -c conda-forge clangxx`。

### Haskell（可选）

- 若需要 haskell-0.0.2 对比：用 [ghcup](https://www.haskell.org/ghcup/) 安装 GHC/Cabal，全部在 `~/.ghcup`，无需 root。再 `cabal install alex` 或 conda 装 alex，然后在 `external/haskell-0.0.2` 里构建。
- 若不做 haskell 对比，可直接跳过，benchmark 里也可 `--exclude-parser` 掉（若列表里有）。

### 下载与编译顺序建议

1. **只下载 parser 相关**（不拉 benchmark 时可省流量）  
   `./scripts/download.sh --parsers-only`

2. **编译 C++ parser**  
   `./scripts/build_all_parsers.sh`  
   若 cvc5 使用预编译 libcxx 包且缺 clang，先：  
   `conda install -c conda-forge clangxx` 再 build。

3. **编译主程序**（若尚未编译）  
   在项目根目录：  
   `mkdir -p build && cd build && cmake .. && make -j$(nproc)`  
   运行 benchmark 时从项目根目录执行，或保证 `smt_parser_comparison` 在 PATH 且当前目录/可执行文件所在目录能解析到 `external/`（见主程序说明）。

---

## 三、一键脚本（可选）

项目提供 `scripts/setup_server_env.sh`，可自动完成：

- 检测或创建 conda 环境
- 安装 pysmt、OpenJDK 等
- 提示设置 `PYTHON` 和后续 build/run 命令

用法示例：

```bash
./scripts/setup_server_env.sh
# 按脚本末尾提示 activate 环境并 export PYTHON，再执行 download/build/run
```

---

## 四、常见问题

- **找不到 pysmt**：确认 `PYTHON` 指向的 python 里 `import pysmt` 成功（`$PYTHON -c "import pysmt"`）。
- **Java 找不到或版本不对**：在运行 benchmark 的同一 shell 里先 `conda activate smtbench`，再执行；或把 `$CONDA_PREFIX/bin` 放在 PATH 最前。
- **cvc5/z3/smt-switch 未找到**：主程序会到 `external/cvc5/build/`、`external/z3/`、`external/smt-switch/build/` 等找可执行文件；确保在项目根执行 `build_all_parsers.sh` 且无报错。
- **无 root 且无 Docker**：若机器上有 Singularity/Apptainer，可后续做镜像把上述环境打进去，在无 root 的集群上同样用 `PYTHON` 和相对路径运行。

---

## 五、无 root 下“失败/跳过”的解决办法

若 `./scripts/build_all_parsers.sh` 报 **cvc5 失败**、**haskell-0.0.2 跳过**、**smt-switch 跳过**，且服务器没有 root，可按下面做（全部用 Conda 或 ghcup 装到用户目录）。

### 1. cvc5 失败

**若报错：** `The source directory .../external/cvc5 does not appear to contain CMakeLists.txt`

说明服务器上的 `external/cvc5` 缺少本仓库的包装器文件（此前 CMakeLists.txt 被 .gitignore 排除）。解决：从本机把 `external/cvc5/CMakeLists.txt`、`external/cvc5/cvc5_parser.cpp`、`external/cvc5/run.sh` 拷到服务器同一路径；或在本机提交并推送 CMakeLists.txt 后在服务器 `git pull`，再执行下面的编译。

**若为预编译包 libcxx 的链接/编译失败：** 预编译包 `cvc5-Linux-*-libcxx-static` 需要 **clang++** 和 **libc++**。用 Conda 装到当前环境时，需同时安装编译器与标准库（否则可能报 `cannot find -lc++`）：

```bash
conda activate smtbench   # 或你的环境名
conda install -c conda-forge clangxx libcxx-devel -y
```

然后**指定用 clang + libc++** 再编译：

```bash
cd /path/to/Parser_Comparison
USE_CLANG_LIBCXX=1 ./scripts/build_all_parsers.sh
```

若已装 clangxx 仍报 **`cannot find -lc++`** 或 **`x86_64-conda-linux-gnu-ld: cannot find -lc++`**，补装 libc++ 即可：`conda install -c conda-forge libcxx-devel -y`，再重新执行上面的编译命令。

### 2. haskell-0.0.2 跳过（未找到 cabal）

需要 GHC + Cabal，且**不需要 root**：用 [ghcup](https://www.haskell.org/ghcup/) 装到 `~/.ghcup`：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh
# 按提示选默认即可；安装完成后按提示 source 环境（如 source ~/.ghcup/env）
```

然后安装 alex（二选一）：

- **用 Cabal**：`cabal install alex`
- **用 Conda**（更省事）：`conda activate smtbench && conda install -c conda-forge alex -y`

最后重新编译：

```bash
source ~/.ghcup/env   # 若当前 shell 还没加载 ghcup
./scripts/build_all_parsers.sh
```

### 3. smt-switch 跳过（检测到 cvc5 源码但尚未构建）

脚本会优先用 `external/cvc5/` 下的**预编译包**（如 `cvc5-Linux-x86_64-libcxx-static`）。若服务器上这里没有预编译包，只有 `external/smt-switch/src/cvc5` 里的 cvc5 源码，就会提示“尚未构建”。

**推荐做法**：在能下载的机器上把 cvc5 预编译包解压到 `external/cvc5/`，再把整个 `external/cvc5/` 拷到服务器同一路径（例如 rsync/scp）。然后按上面「cvc5 失败」装好 clangxx 并执行：

```bash
USE_CLANG_LIBCXX=1 ./scripts/build_all_parsers.sh
```

smt-switch 会自动用 `external/cvc5/` 下的预编译包，无需先编 cvc5 源码。

**若必须从 cvc5 源码构建**（无预编译包可用）：

1. 安装 bison、flex（Conda，无需 root）：
   ```bash
   conda activate smtbench
   conda install -c conda-forge bison flex -y
   ```
2. 先单独编译 cvc5 源码（耗时会较长）：
   ```bash
   CVC5_SRC=/path/to/Parser_Comparison/external/smt-switch/src/cvc5
   cd "$CVC5_SRC" && mkdir -p build && cd build && cmake .. && make -j$(nproc)
   ```
3. 再执行一键编译（此时会检测到已构建的 cvc5）：
   ```bash
   cd /path/to/Parser_Comparison
   ./scripts/build_all_parsers.sh
   ```

---

按上述步骤，所有依赖均可落在用户目录或项目内，实验可在无 root 的服务器上完整跑通。
