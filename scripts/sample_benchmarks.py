#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMT benchmark 抽样脚本：无人工挑选、可复现、按文件大小分层 + hash 排序。

从每个 theory 的已解压目录中抽取代表性子集，用于 parser cost evaluation。
不依赖 solver，不解压（使用已有解压目录），只用文件大小分层和 SHA256(relpath) 排序。

用法示例:
  python3 scripts/sample_benchmarks.py
  python3 scripts/sample_benchmarks.py --per_theory 200 --copy_files
  python3 scripts/sample_benchmarks.py --theories QF_LIA,QF_BV --no_copy_files
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

# 默认 8 个 theory
DEFAULT_THEORIES = [
    "QF_LIA",
    "QF_LRA",
    "QF_NIA",
    "QF_NRA",
    "QF_BV",
    "QF_FP",
    "QF_S",
    "QF_AX",
]

DEFAULT_SEED_STRING = "SMTParser-benchmark-v1"
DEFAULT_PER_THEORY = 200
NUM_QUARTILES = 4  # Q1..Q4
SAMPLED_DIR_NAME = "sampled"
MANIFEST_CSV = "manifest.csv"
MANIFEST_JSON = "manifest.json"
FILES_SUBDIR = "files"
README_NAME = "README.md"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def theory_root(bench_dir: Path, unpacked_subdir: str, theory: str) -> Path:
    """返回某 theory 的已解压根目录（不解压，仅路径）。"""
    return bench_dir / unpacked_subdir / theory


def collect_smt2_files(theory_root_path: Path) -> list[tuple[Path, int, str]]:
    """
    递归收集 theory 根目录下所有 .smt2 文件。
    返回: [(abs_path, size_bytes, relpath), ...]
    relpath 使用 POSIX 风格（便于跨平台一致）。
    """
    root = theory_root_path.resolve()
    if not root.is_dir():
        return []

    out: list[tuple[Path, int, str]] = []
    for p in root.rglob("*.smt2"):
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        try:
            rel = p.relative_to(root)
            relpath = rel.as_posix()
        except ValueError:
            continue
        out.append((p, size, relpath))
    return out


def hash_for_sort(seed_string: str, relpath: str) -> str:
    """确定性：hash_input = seed_string + ':' + relpath，返回 hex 字符串用于排序。"""
    h = hashlib.sha256((seed_string + ":" + relpath).encode("utf-8"))
    return h.hexdigest()


def quartile_index(i: int, n: int, num_quartiles: int) -> int:
    """
    将排序后的下标 i (0..n-1) 映射到层 0..num_quartiles-1。
    尽量等量；n 不足时层数可能少于 num_quartiles。
    """
    if n <= 0 or num_quartiles <= 0:
        return 0
    if n <= num_quartiles:
        return min(i, num_quartiles - 1)
    # 等分
    q = (n * (num_quartiles - 1)) // num_quartiles
    if q <= 0:
        return 0
    return min(i // max(1, (n + num_quartiles - 1) // num_quartiles), num_quartiles - 1)


def sample_one_theory(
    theory_root_path: Path,
    theory: str,
    per_theory: int,
    seed_string: str,
    num_quartiles: int,
) -> list[dict[str, Any]]:
    """
    对单个 theory 做分层抽样，返回 manifest 行列表。
    每行: theory, relpath, abs_path, size_bytes, quartile, hash
    """
    rows = collect_smt2_files(theory_root_path)
    total = len(rows)
    if total == 0:
        return []

    # 按 size_bytes 排序
    rows.sort(key=lambda x: (x[1], x[2]))

    # 分配 quartile
    quartile_assignments: list[int] = []
    for i in range(total):
        q = quartile_index(i, total, num_quartiles)
        quartile_assignments.append(q)

    # 每层内按 SHA256(seed:relpath) 排序，取前 k；k 按层均分，余数给前几层
    k_per_layer = per_theory // num_quartiles
    remainder = per_theory % num_quartiles
    layer_limits = [k_per_layer + (1 if j < remainder else 0) for j in range(num_quartiles)]

    # 按 (quartile, hash_hex, relpath) 排序，然后每层取前 k
    with_hash = []
    for idx, (abs_path, size_bytes, relpath) in enumerate(rows):
        q = quartile_assignments[idx]
        h = hash_for_sort(seed_string, relpath)
        with_hash.append((q, h, relpath, abs_path, size_bytes))

    with_hash.sort(key=lambda x: (x[0], x[1], x[2]))

    # 每层计数取前 k
    layer_count = [0] * num_quartiles
    selected: list[dict[str, Any]] = []
    for q, h, relpath, abs_path, size_bytes in with_hash:
        if layer_count[q] >= layer_limits[q]:
            continue
        layer_count[q] += 1
        selected.append({
            "theory": theory,
            "relpath": relpath,
            "abs_path": str(abs_path),
            "size_bytes": size_bytes,
            "quartile": q + 1,  # 1-based Q1..Q4
            "hash": h,
        })

    return selected


def run_sampling(
    bench_dir: Path,
    unpacked_subdir: str,
    theories: list[str],
    per_theory: int,
    seed_string: str,
    out_dir: Path,
    copy_files: bool,
    skip_missing: bool,
    num_quartiles: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    对每个 theory 抽样，汇总 manifest 行。
    返回 (all_manifest_rows, list of theories that were skipped due to missing dir)。
    """
    all_rows: list[dict[str, Any]] = []
    skipped: list[str] = []

    for theory in theories:
        troot = theory_root(bench_dir, unpacked_subdir, theory)
        logging.info("正在处理 theory: %s ...", theory)
        if not troot.is_dir():
            msg = f"Theory '{theory}': 未找到已解压目录 {troot}"
            if skip_missing:
                logging.warning("跳过: %s", msg)
                skipped.append(theory)
                continue
            logging.error("%s", msg)
            sys.exit(2)

        # 统计该 theory 总文件数
        files_info = collect_smt2_files(troot)
        total_files = len(files_info)
        if total_files == 0:
            logging.warning("Theory '%s': 未找到 .smt2 文件，跳过", theory)
            skipped.append(theory)
            continue

        selected = sample_one_theory(troot, theory, per_theory, seed_string, num_quartiles)
        n_selected = len(selected)

        # 每层数量（用于日志）
        by_q: dict[int, int] = {}
        for r in selected:
            q = r["quartile"]
            by_q[q] = by_q.get(q, 0) + 1
        q_counts = [by_q.get(i, 0) for i in range(1, num_quartiles + 1)]

        logging.info(
            "Theory %s: 总文件数=%d, 每层抽样数=%s, 最终选中=%d",
            theory,
            total_files,
            q_counts,
            n_selected,
        )
        all_rows.extend(selected)

    return all_rows, skipped


def write_manifest_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["theory", "relpath", "abs_path", "size_bytes", "quartile", "hash"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_manifest_json(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def copy_sampled_files(rows: list[dict[str, Any]], out_dir: Path) -> None:
    """将选中文件按 theory/relpath 复制到 out_dir/files/<theory>/..."""
    files_dir = out_dir / FILES_SUBDIR
    for r in rows:
        theory = r["theory"]
        relpath = r["relpath"]
        src = Path(r["abs_path"])
        dst = files_dir / theory / relpath
        if not src.is_file():
            logging.warning("源文件不存在，跳过: %s", src)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_readme(out_dir: Path, per_theory: int, seed_string: str) -> None:
    """生成 benchmark/sampled/README.md，说明抽样规则与可复现性。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    readme = out_dir / README_NAME
    content = f"""# SMT Benchmark 抽样子集

本目录由 `scripts/sample_benchmarks.py` 生成，用于 parser cost evaluation 的代表性子集。

## 抽样规则

1. **覆盖每个 theory**：对每个 theory 单独抽样，保证各 theory 均有代表。
2. **规模分层**：按文件大小（字节数）排序，分为四分位数层 Q1～Q4（尽量等量）。
3. **层内确定性选取**：每层内按 `SHA256(seed_string + ":" + relpath)` 的十六进制字符串排序，取前 k 个。
4. **无人工挑选**：完全由脚本根据文件大小与路径 hash 决定，无人为干预。
5. **不依赖 solver**：不读取 SMT 内容、不跑求解，仅用文件大小与路径。

## 参数（本次生成默认）

- **per_theory**: 每个 theory 抽样数 = {per_theory}（即每层 k ≈ {per_theory // 4}，余数分配至前几层）
- **seed_string**: `{seed_string}`（用于 hash 盐，保证可复现）
- **theories**: QF_LIA, QF_LRA, QF_NIA, QF_NRA, QF_BV, QF_FP, QF_S, QF_AX（可配置）

## 可复现性

- 同一输入集（同一批已解压的 benchmark 目录）、同一参数、同一 `seed_string` 下，输出完全一致。
- 不使用随机数；仅使用文件路径与大小的确定性计算。

## 如何复现抽样

在项目根目录执行（复制文件到 `sampled/files/`）：

```bash
python3 scripts/sample_benchmarks.py --bench_dir benchmark --per_theory 200 --seed_string "{seed_string}" --copy_files
```

仅生成 manifest 不复制文件：

```bash
python3 scripts/sample_benchmarks.py --bench_dir benchmark --per_theory 200 --no_copy_files
```

指定部分 theory：

```bash
python3 scripts/sample_benchmarks.py --theories QF_LIA,QF_BV --per_theory 100 --copy_files
```

## 输出文件

- **manifest.csv** / **manifest.json**：抽样列表，字段含 theory, relpath, abs_path, size_bytes, quartile, hash。
- **files/<theory>/...**：复制出的 .smt2 文件（保持相对目录结构），仅在使用 `--copy_files` 时生成。
"""
    readme.write_text(content, encoding="utf-8")
    logging.info("已写入 %s", readme)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SMT benchmark 抽样：按文件大小分层 + hash 排序，可复现、无人工挑选。",
    )
    parser.add_argument(
        "--bench_dir",
        type=Path,
        default=None,
        help="Benchmark 根目录（默认: 项目根目录/benchmark）",
    )
    parser.add_argument(
        "--unpacked_subdir",
        type=str,
        default="non-incremental",
        help="已解压目录相对 bench_dir 的子目录名，各 theory 在其下（默认: non-incremental）",
    )
    parser.add_argument(
        "--theories",
        type=str,
        default=",".join(DEFAULT_THEORIES),
        help="Theory 列表，逗号分隔（默认: 8 个 QF_*）",
    )
    parser.add_argument(
        "--per_theory",
        type=int,
        default=DEFAULT_PER_THEORY,
        help="每个 theory 抽样数量（默认: 200）",
    )
    parser.add_argument(
        "--seed_string",
        type=str,
        default=DEFAULT_SEED_STRING,
        help="Hash 盐前缀，用于可复现性（默认: SMTParser-benchmark-v1）",
    )
    parser.add_argument(
        "--copy_files",
        action="store_true",
        help="将选中文件复制到 sampled/files/<theory>/...",
    )
    parser.add_argument(
        "--no_copy_files",
        action="store_true",
        help="不复制文件，只生成 manifest（与 --copy_files 二选一）",
    )
    parser.add_argument(
        "--force_unpack",
        action="store_true",
        help="（当前未实现解压）保留选项，忽略。使用已有解压目录。",
    )
    parser.add_argument(
        "--skip_missing",
        action="store_true",
        help="若某 theory 无已解压目录则跳过而非退出",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=None,
        help="输出目录（默认: bench_dir/sampled）",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="详细日志",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    repo = get_repo_root()
    bench_dir = args.bench_dir if args.bench_dir is not None else repo / "benchmark"
    bench_dir = bench_dir.resolve()
    out_dir = args.out_dir if args.out_dir is not None else bench_dir / SAMPLED_DIR_NAME
    out_dir = out_dir.resolve()

    theories = [t.strip() for t in args.theories.split(",") if t.strip()]
    copy_files = args.copy_files and not args.no_copy_files

    if args.force_unpack:
        logging.info("--force_unpack 已忽略：当前使用已有解压目录，不解压。")

    logging.info("bench_dir=%s, unpacked_subdir=%s, theories=%s, per_theory=%d", bench_dir, args.unpacked_subdir, theories, args.per_theory)
    logging.info("seed_string=%s, copy_files=%s, out_dir=%s", args.seed_string, copy_files, out_dir)

    rows, skipped = run_sampling(
        bench_dir=bench_dir,
        unpacked_subdir=args.unpacked_subdir,
        theories=theories,
        per_theory=args.per_theory,
        seed_string=args.seed_string,
        out_dir=out_dir,
        copy_files=copy_files,
        skip_missing=args.skip_missing,
        num_quartiles=NUM_QUARTILES,
    )

    if not rows:
        logging.error("没有抽中任何文件。")
        return 1

    write_manifest_csv(rows, out_dir / MANIFEST_CSV)
    write_manifest_json(rows, out_dir / MANIFEST_JSON)
    write_readme(out_dir, args.per_theory, args.seed_string)
    logging.info("已写入 %s 与 %s", out_dir / MANIFEST_CSV, out_dir / MANIFEST_JSON)

    if copy_files:
        copy_sampled_files(rows, out_dir)
        logging.info("已复制文件到 %s", out_dir / FILES_SUBDIR)

    # 总体统计
    by_theory: dict[str, int] = {}
    for r in rows:
        by_theory[r["theory"]] = by_theory.get(r["theory"], 0) + 1
    logging.info("--- 总体统计 ---")
    logging.info("总抽样数: %d", len(rows))
    logging.info("各 theory 数量: %s", by_theory)
    if skipped:
        logging.info("跳过的 theory: %s", skipped)
    logging.info("输出目录: %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
