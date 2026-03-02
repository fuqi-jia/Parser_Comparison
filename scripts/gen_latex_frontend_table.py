#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 results/summary/parser_summary_sampled_<Theory>.md 读取数据，生成 LaTeX 表。
表中每行每指标：时间/内存/超时/失败取最小为最佳（加粗），节点数取最大为最佳（加粗）。
不含支持率。内存输出为 MB（由 kB 除以 1024）。
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY_DIR = REPO_ROOT / "results" / "summary"

# 表列顺序：Z3, cvc5, smt-sw, pysmt, ANT4, jSMT, SMTParser
PARSER_ORDER = ["z3", "cvc5", "smt-switch", "pysmt", "antlr4", "jsmtlib", "native"]
PARSER_DISPLAY = {
    "z3": "Z3",
    "cvc5": "cvc5",
    "smt-switch": "smt-sw",
    "pysmt": "pysmt",
    "antlr4": "ANT4",
    "jsmtlib": "jSMT",
    "native": r"\textsc{SMTParser}",
}

THEORIES = ["QF_AX", "QF_BV", "QF_FP", "QF_LIA", "QF_LRA", "QF_NIA", "QF_NRA", "QF_S"]


def parse_float(s):
    s = (s or "").strip()
    if s == "" or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_summary_md(path):
    """返回 dict: parser -> { time_ms, memory_kb, nodes, timeout_pct, fail_pct }，无支持率。"""
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("|") or "---" in line or line.startswith("| Parser |"):
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < 6:
                continue
            parser = parts[0].strip()
            time_s, memory_s, nodes_s = parts[1], parts[2], parts[3]
            timeout_s, fail_s = parts[4], parts[5]
            data[parser] = {
                "time_ms": parse_float(time_s),
                "memory_kb": parse_float(memory_s),
                "nodes": parse_float(nodes_s),
                "timeout_pct": parse_float(timeout_s),
                "fail_pct": parse_float(fail_s),
            }
    return data


def load_all_theories(summary_dir):
    """返回 theory -> parser -> metrics dict。"""
    result = {}
    for th in THEORIES:
        p = summary_dir / f"parser_summary_sampled_{th}.md"
        if not p.exists():
            continue
        result[th] = read_summary_md(p)
    return result


def format_cell(value, is_best, is_second=False):
    if value is None or (isinstance(value, float) and value != value):
        return "-"
    if isinstance(value, float):
        if value == int(value):
            s = str(int(value))
        else:
            s = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        s = str(value)
    if is_best:
        return f"\\textbf{{{s}}}"
    if is_second:
        return f"\\underline{{{s}}}"
    return s


def best_indices(values, lower_better=True):
    """values: list of (float|None). 返回最佳下标集合（可并列）。"""
    if lower_better:
        valid = [(i, v) for i, v in enumerate(values) if v is not None]
        if not valid:
            return set()
        best_val = min(v for _, v in valid)
        return {i for i, v in valid if v == best_val}
    else:
        valid = [(i, v) for i, v in enumerate(values) if v is not None]
        if not valid:
            return set()
        best_val = max(v for _, v in valid)
        return {i for i, v in valid if v == best_val}


def second_best_indices(values, lower_better=True):
    """返回第二名下标集合（可并列）。若无第二名则返回空集。"""
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return set()
    best = best_indices(values, lower_better=lower_better)
    best_vals = {values[i] for i in best}
    second_vals = [v for _, v in valid if v not in best_vals]
    if not second_vals:
        return set()
    second_val = min(second_vals) if lower_better else max(second_vals)
    return {i for i, v in valid if v == second_val}


def emit_table(all_data, out_path):
    lines = [
        r"\begin{table*}[hp]",
        r"\centering",
        r"\caption{Front-end performance comparison (solving disabled).",
        r"Time in ms, RSS in MB, timeout/failure in \%, and structural size in median node count.}",
        r"\label{tab:frontend-all}",
        r"\small",
        r"\begin{tabular}{lccccccc}",
        r"\toprule",
        r"\textbf{Theory} & "
        + " & ".join(r"\textbf{" + PARSER_DISPLAY.get(p, p) + "}" for p in PARSER_ORDER)
        + r" \\",
        r"\midrule",
        "",
    ]

    def row_cells(metric_key, lower_better, theory):
        row_data = all_data.get(theory, {})
        values = []
        for p in PARSER_ORDER:
            m = row_data.get(p, {})
            v = m.get(metric_key)
            values.append(v)
        best = best_indices(values, lower_better=lower_better)
        second = second_best_indices(values, lower_better=lower_better)
        cells = []
        for i, p in enumerate(PARSER_ORDER):
            v = values[i]
            if metric_key == "memory_kb" and v is not None:
                display_val = round(v / 1024.0, 2)
            elif v is not None and isinstance(v, float) and v == int(v):
                display_val = int(v)
            else:
                display_val = v
            cells.append(format_cell(display_val, i in best, i in second))
        return " & ".join(cells)

    time_block = []
    time_block.append(r"\multicolumn{8}{c}{\textbf{Parsing Time (ms)}} \\")
    time_block.append(r"\midrule")
    for th in THEORIES:
        if th not in all_data:
            continue
        cells = row_cells("time_ms", True, th)
        th_disp = th.replace("_", "\\_")
        time_block.append(f"{th_disp}  & {cells} \\\\")
    time_block.append(r"\midrule")
    time_block.append("")

    rss_block = []
    rss_block.append(r"\multicolumn{8}{c}{\textbf{Peak RSS (MB)}} \\")
    rss_block.append(r"\midrule")
    for th in THEORIES:
        if th not in all_data:
            continue
        cells = row_cells("memory_kb", True, th)
        th_disp = th.replace("_", "\\_")
        rss_block.append(f"{th_disp}  & {cells} \\\\")
    rss_block.append(r"\midrule")
    rss_block.append("")

    timeout_block = []
    timeout_block.append(r"\multicolumn{8}{c}{\textbf{Timeout Rate (\%)}} \\")
    timeout_block.append(r"\midrule")
    for th in THEORIES:
        if th not in all_data:
            continue
        cells = row_cells("timeout_pct", True, th)
        th_disp = th.replace("_", "\\_")
        timeout_block.append(f"{th_disp}  & {cells} \\\\")
    timeout_block.append(r"\midrule")
    timeout_block.append("")

    fail_block = []
    fail_block.append(r"\multicolumn{8}{c}{\textbf{Parsing Failure Rate (\%)}} \\")
    fail_block.append(r"\midrule")
    for th in THEORIES:
        if th not in all_data:
            continue
        cells = row_cells("fail_pct", True, th)
        th_disp = th.replace("_", "\\_")
        fail_block.append(f"{th_disp}  & {cells} \\\\")
    fail_block.append(r"\midrule")
    fail_block.append("")

    nodes_block = []
    nodes_block.append(r"\multicolumn{8}{c}{\textbf{Structural Size (nodes)}} \\")
    nodes_block.append(r"\midrule")
    for th in THEORIES:
        if th not in all_data:
            continue
        cells = row_cells("nodes", True, th)  # lower better (越小越好)
        th_disp = th.replace("_", "\\_")
        nodes_block.append(f"{th_disp}  & {cells} \\\\")
    nodes_block.append(r"\bottomrule")

    # Rebuild lines: header + time + rss + timeout + fail + nodes + end
    lines = [
        r"\begin{table*}[hp]",
        r"\centering",
        r"\caption{Front-end performance comparison (solving disabled).",
        r"Time in ms, RSS in MB, timeout/failure in \%, and structural size in median node count.}",
        r"\label{tab:frontend-all}",
        r"\small",
        r"\begin{tabular}{lccccccc}",
        r"\toprule",
        r"\textbf{Theory} & "
        + " & ".join(r"\textbf{" + PARSER_DISPLAY.get(p, p) + "}" for p in PARSER_ORDER)
        + r" \\",
        r"\midrule",
        "",
    ]
    lines.extend(time_block)
    lines.extend(rss_block)
    lines.extend(timeout_block)
    lines.extend(fail_block)
    lines.extend(nodes_block)
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("已写入:", out_path)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="从 summary 的 md 生成 LaTeX 前端对比表")
    ap.add_argument("--summary-dir", type=Path, default=DEFAULT_SUMMARY_DIR, help="summary 目录")
    ap.add_argument("-o", "--output", type=Path, default=None, help="输出 .tex 路径，默认 summary 目录下 frontend_table.tex")
    args = ap.parse_args()
    out = args.output or args.summary_dir / "frontend_table.tex"
    all_data = load_all_theories(args.summary_dir)
    if not all_data:
        print("未找到任何 parser_summary_sampled_*.md", file=__import__("sys").stderr)
        raise SystemExit(1)
    emit_table(all_data, out)


if __name__ == "__main__":
    main()
