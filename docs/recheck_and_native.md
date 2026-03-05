# 重跑结果：写回主表与断点续跑

## 当前逻辑

- **主表**：`results/parser_benchmark_table_sampled.csv`。重跑时若指定 `--table 主表路径`，**每条重跑结果都会直接更新主表对应行**（成功与失败都写回）；且**每完成一条就写回磁盘**，中途崩溃也不会丢已跑完的。
- **recheck**：`results/parser_benchmark_recheck_sampled.csv`。**每条重跑结果都会追加到 recheck**（含成功与 fail/timeout），用于**断点续跑**：再次执行同一命令时，会跳过 recheck 里已有的 (file, parser)，只跑未完成的。
- **Summary**：直接按主表生成（`gen_summary_table.py --input 主表 --output-dir results/summary`），**不再需要** `--update-from-recheck`。

## 中途崩溃怎么继续

默认就是**断点续跑**（`--resume`）：  
再次执行**同一条命令**即可，不要加 `--fresh`。

```bash
./scripts/run_re_run_benchmark.sh --only-parser cvc5 \
  benchmark/sampled/file_list.txt \
  results/parser_benchmark_checkpoint_sampled.csv \
  results/parser_benchmark_recheck_sampled.csv \
  results/parser_benchmark_table_sampled.csv \
  results/summary
```

- 已完成的 (file, parser) 会从 recheck 里读出，**先合并回主表**（把崩溃前跑完的那部分写进主表），再只跑「待跑」的那部分。
- 每跑完一条会：更新主表并写回磁盘、追加该条到 recheck。所以再崩一次，再执行同一命令即可继续。

## 单独重跑 native 并更新表

```bash
./scripts/run_re_run_benchmark.sh \
  --only-parser native \
  benchmark/sampled/file_list.txt \
  results/parser_benchmark_checkpoint_sampled.csv \
  results/parser_benchmark_recheck_sampled.csv \
  results/parser_benchmark_table_sampled.csv \
  results/summary
```

脚本会传 `--table` 给重跑程序，成功的结果会写回主表，并在结束时自动执行 `gen_summary_table.py --input 主表` 生成 summary；无需再手动带 `--update-from-recheck`。

## 未指定 --table 时（兼容旧用法）

若不传主表（或脚本未传 `--table`），重跑结果仍会**全部**写入 recheck，此时需用：

```bash
python3 scripts/gen_summary_table.py --input 主表 --update-from-recheck results/parser_benchmark_recheck_sampled.csv --output-dir results/summary
```

合并 recheck 后再生成 summary。
