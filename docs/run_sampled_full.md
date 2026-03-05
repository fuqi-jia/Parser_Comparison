# Sampled 一键全流程与部署说明

## 一键执行（推荐）

在项目根目录执行，完成「抽样(可选) → benchmark → recheck → summary → LaTeX 表」全流程：

```bash
./scripts/run_sampled_full.sh
```

- **默认**：断点续跑。若已有 checkpoint/recheck，会跳过已完成任务，只跑未完成部分。
- **从头重跑**：加 `--fresh` 会清空 checkpoint、长表、recheck 后重新跑全量。
- **已有抽样**：若已存在 `benchmark/sampled/manifest.csv` 和 `benchmark/sampled/files/`，会自动跳过抽样；也可加 `--skip-sample` 显式跳过抽样检查。
- **清理已知不支持的 failure**：加 `--clean-unsupported` 会删除 pysmt/QF_FP、smt-switch/QF_AX、smt-switch/QF_FP 的 failure 目录后再跑。

示例：

```bash
# 首次或断点续跑
./scripts/run_sampled_full.sh

# 清空结果从头跑
./scripts/run_sampled_full.sh --fresh

# 已有抽样，只跑 benchmark + 后续
./scripts/run_sampled_full.sh --skip-sample
```

## 流程说明

1. **抽样**：若无 `manifest.csv` / `sampled/files`，会执行 `scripts/sample.sh`（每 theory 200 个、可复现）。
2. **Benchmark**：对 file_list 中每个 .smt2 × 每个 parser 跑一遍，10s 超时，结果写入 checkpoint 与长表。
3. **Recheck**：仅对 checkpoint 里 status 为 fail/timeout 的 (file, parser) 再跑一遍，纠正误判（如首行非 JSON），写入 recheck CSV。
4. **Summary**：用 recheck 覆盖长表中的误判，按理论生成汇总表与 markdown。
5. **LaTeX**：由 summary 生成 `results/summary/frontend_table.tex`。

输出路径（均在项目根下）：

- `results/parser_benchmark_checkpoint_sampled.csv`
- `results/parser_benchmark_table_sampled.csv`
- `results/parser_benchmark_recheck_sampled.csv`
- `results/summary/`（含 `frontend_table.tex`）

## 在服务器 / 非 WSL 环境运行

当前脚本仅依赖：

- Bash、Python 3
- 项目内已编译的 `smt_parser_comparison`（或 `build/smt_parser_comparison`）及各 parser 所需环境（见 `scripts/build_all_parsers.sh`、`scripts/download.sh`）

若要在**纯 Linux 服务器**上跑同样的 sampled 流程，可以：

1. **无 root 服务器**：各 external parser 依赖不一（Python/Java/C++/Haskell），可用**用户空间**统一解决，无需 sudo。详见 [server_setup_no_root.md](server_setup_no_root.md)。推荐：
   - 运行 `./scripts/setup_server_env.sh` 用 Conda 创建 Python+pysmt+Java 环境；
   - 设置 `export PYTHON=/path/to/conda/env/bin/python` 后执行 `./scripts/run_sampled_full.sh`。
2. **直接迁移**：将整个项目（含 `benchmark/sampled/files` 或至少 manifest + 源 benchmark）拷到服务器，安装依赖、编译后执行：
   ```bash
   ./scripts/run_sampled_full.sh
   ```
3. **Docker（后续）**：可做一份 Dockerfile，在镜像内执行 `download.sh`、`build_all_parsers.sh`、`run_sampled_full.sh`，将 `results/` 挂载或拷贝出来。
