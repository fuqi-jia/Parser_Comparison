# 重跑结果：成功写回主表，recheck 只存仍 fail/timeout

## 当前逻辑

- **主表**：`results/parser_benchmark_table_sampled.csv`。重跑时若指定 `--table 主表路径`，**每条重跑结果都会直接更新主表对应行**（成功与失败都写回）。
- **recheck**：`results/parser_benchmark_recheck_sampled.csv`。**仅重跑后仍为 fail/timeout 的条目会追加到 recheck**，成功的不再保存到 recheck。
- **Summary**：直接按主表生成（`gen_summary_table.py --input 主表 --output-dir results/summary`），**不再需要** `--update-from-recheck`。

这样主表是唯一数据源，recheck 只作“仍有问题的个案”留底。

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
