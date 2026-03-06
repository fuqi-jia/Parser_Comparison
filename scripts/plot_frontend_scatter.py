#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
两两对比散点图：横轴 SMTParser (native)，纵轴另一 parser；每个实例一个点，y=x 参考线。
仅使用两方都 success (status==ok) 的实例。
生成 time / rss / nodes 三类，每类 6 张图（vs z3, cvc5, smt-switch, pysmt, antlr4, jsmtlib），共 18 张。
"""
from pathlib import Path
import csv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = REPO_ROOT / "results" / "parser_benchmark_table_sampled.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "results" / "frontend_scatter"

# 纵轴 parser（横轴固定为 native）
OTHER_PARSERS = ["z3", "cvc5", "smt-switch", "pysmt", "antlr4", "jsmtlib"]
OTHER_DISPLAY = {
    "z3": "Z3",
    "cvc5": "cvc5",
    "smt-switch": "smt-sw",
    "pysmt": "pysmt",
    "antlr4": "ANT4",
    "jsmtlib": "jSMT",
}

METRICS = [
    ("time_ms", "time", "Median parsing time (ms)", "SMTParser time (ms)", "{} time (ms)"),
    ("memory_kb", "rss", "Peak RSS (MB)", "SMTParser RSS (MB)", "{} RSS (MB)"),
    ("ast_nodes", "nodes", "Structural size (nodes)", "SMTParser nodes", "{} nodes"),
]


def load_table(path):
    """返回 list of dict: file, parser, status, time_ms, memory_kb, ast_nodes。"""
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def parse_float(s):
    if s is None or (isinstance(s, str) and s.strip() in ("", "-")):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_val(raw, metric_key):
    if metric_key == "ast_nodes":
        try:
            return int((raw or "").strip()) if raw is not None else None
        except (ValueError, TypeError):
            return None
    return parse_float(raw)


def get_pairs(rows, metric_key):
    """按 file 聚合：ok 点 (native_val, other_val)；超时点谁超时谁放边界 (SMTParser 超时->x=MAX, 对方超时->y=MAX)。"""
    by_file = {}
    for r in rows:
        f = (r.get("file") or "").strip()
        p = (r.get("parser") or "").strip()
        if not f or not p:
            continue
        status = (r.get("status") or "").strip().lower()
        raw = r.get(metric_key)
        v = _parse_val(raw, metric_key) if status == "ok" else None
        if f not in by_file:
            by_file[f] = {}
        by_file[f][p] = (status, v)

    result = {}
    for p in OTHER_PARSERS:
        result[p] = {"ok": [], "native_to": [], "other_to": [], "both_to": 0}
    for f, data in by_file.items():
        native = data.get("native")
        if native is None:
            continue
        ns, nv = native
        for p in OTHER_PARSERS:
            other = data.get(p)
            if other is None:
                continue
            os_, ov = other
            if ns == "ok" and os_ == "ok" and nv is not None and ov is not None:
                result[p]["ok"].append((nv, ov))
            elif ns == "timeout" and os_ == "ok" and ov is not None:
                result[p]["native_to"].append(ov)
            elif ns == "ok" and os_ == "timeout" and nv is not None:
                result[p]["other_to"].append(nv)
            elif ns == "timeout" and os_ == "timeout":
                result[p]["both_to"] += 1
    return result


def plot_one(ax, data, metric_key, other_parser, xlabel, ylabel, scale_rss=False):
    """data: dict with 'ok', 'native_to', 'other_to', 'both_to'. 超时点放在边界，另一色。"""
    try:
        from matplotlib.ticker import MaxNLocator
    except ImportError:
        MaxNLocator = None
    ok_pairs = data.get("ok") or []
    native_to = data.get("native_to") or []
    other_to = data.get("other_to") or []
    both_to = data.get("both_to") or 0
    if not ok_pairs and not native_to and not other_to and both_to == 0:
        return
    scale = (lambda x: x / 1024.0) if scale_rss else (lambda x: x)
    # 先只用 ok 点定范围
    if ok_pairs:
        xs, ys = zip(*ok_pairs)
        xs = [scale(x) for x in xs]
        ys = [scale(y) for y in ys]
        lim_min = min(min(xs), min(ys))
        lim_max = max(max(xs), max(ys))
    else:
        all_vals = [scale(v) for v in native_to] + [scale(v) for v in other_to]
        lim_min = 0
        lim_max = max(all_vals) if all_vals else 1
    # 边界要包住超时点中非边界一侧的值
    if native_to:
        lim_max = max(lim_max, max(scale(v) for v in native_to))
    if other_to:
        lim_max = max(lim_max, max(scale(v) for v in other_to))
    margin = (lim_max - lim_min) * 0.02 or 1
    lim_min = max(0, lim_min - margin)
    lim_max = lim_max + margin
    # log scale：下限必须为正；time/RSS 通常没有很小值，用 max 的 1% 做下限，不从 10^0 起留空
    if lim_min <= 0:
        lim_min = max(1e-9, lim_max * 0.01) if lim_max > 0 else 1e-9
    # 超时叉号画在数据最外侧（boundary = lim_max），保证叉号是最外层的点
    boundary = lim_max
    # 坐标轴再往外扩一截（log 下用比例），让叉号与边框之间留出缝隙，不贴边
    pad_factor = 1.12  # 约 12% 扩展，留出可见空隙
    lim_min_plot = lim_min / pad_factor
    lim_max_plot = lim_max * pad_factor
    # 成功点
    if ok_pairs:
        xs, ys = zip(*ok_pairs)
        xs = [scale(x) for x in xs]
        ys = [scale(y) for y in ys]
        ax.scatter(xs, ys, alpha=0.65, s=14, rasterized=True, edgecolors="none", c="C0")
    # 超时点：叉号，谁超时谁在 boundary（略小于 lim_max）
    tx, ty = [], []
    for ov in native_to:
        tx.append(boundary)
        ty.append(scale(ov))
    for nv in other_to:
        tx.append(scale(nv))
        ty.append(boundary)
    for _ in range(both_to):
        tx.append(boundary)
        ty.append(boundary)
    if tx:
        ax.scatter(tx, ty, marker="x", s=36, linewidths=1.2, c="k", zorder=5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.plot([lim_min_plot, lim_max_plot], [lim_min_plot, lim_max_plot], "k--", alpha=0.6, linewidth=1)
    ax.set_xlim(lim_min_plot, lim_max_plot)
    ax.set_ylim(lim_min_plot, lim_max_plot)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(axis="both", labelsize=8)
    ax.set_aspect("equal")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="SMTParser vs 各 parser 两两对比散点图（time / rss / nodes）")
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE, help="主表 CSV")
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUT_DIR, help="输出目录，下建 time/ rss/ nodes/")
    ap.add_argument("--no-rss", action="store_true", help="不生成 RSS 图（jSMT 无 RSS 时可跳过）")
    args = ap.parse_args()

    if not args.table.exists():
        print("错误: 表不存在", args.table, file=__import__("sys").stderr)
        return 1

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("错误: 需要 matplotlib，请安装 pip install matplotlib", file=__import__("sys").stderr)
        return 1

    rows = load_table(args.table)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for metric_key, subdir, title, xlabel_template, ylabel_template in METRICS:
        if metric_key == "memory_kb" and args.no_rss:
            continue
        sub = out / subdir
        sub.mkdir(parents=True, exist_ok=True)
        scale_rss = metric_key == "memory_kb"
        xlabel = xlabel_template
        pairs_all = get_pairs(rows, metric_key)

        for other in OTHER_PARSERS:
            data = pairs_all[other]
            if not (data.get("ok") or data.get("native_to") or data.get("other_to") or data.get("both_to")):
                print("跳过 {}/{}：无共同实例".format(subdir, other))
                continue
            fig, ax = plt.subplots(figsize=(4, 4))
            ylabel = ylabel_template.format(OTHER_DISPLAY.get(other, other))
            plot_one(ax, data, metric_key, other, xlabel, ylabel, scale_rss=scale_rss)
            png = sub / "{}_vs_{}.png".format("SMTParser", other.replace("-", "_"))
            fig.savefig(png, dpi=150, bbox_inches="tight", pad_inches=0.05)
            plt.close(fig)
            print("已写:", png)

    print("全部保存到:", out)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
