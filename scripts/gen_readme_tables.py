#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse results/summary/frontend_table.tex and emit Markdown tables.
Writes results/summary/readme_paper_tables.md or splices README.md between
<!--PAPER_TABLES_BEGIN--> ... <!--PAPER_TABLES_END-->.
"""
from __future__ import print_function

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_TEX = REPO / "results" / "summary" / "frontend_table.tex"

EXTENDED_BEGIN = "<!--EXTENDED_RESULTS_BEGIN-->"
EXTENDED_END = "<!--EXTENDED_RESULTS_END-->"

STANDALONE_SUMMARY_FILES = (
    "results/roundtrip/roundtrip_summary.md",
    "results/robustness/robustness_summary.md",
    "results/parse_vs_solve/parse_vs_solve_summary.md",
    "results/native_z3_dual_path/native_z3_dual_path_summary.md",
)


def unescape_tex_cell(s):
    s = s.strip()
    s = s.replace(r"\_", "_")
    s = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", s)
    s = re.sub(r"\\underline\{([^}]*)\}", r"*\1*", s)
    s = s.replace(r"\%", "%")
    return s.strip()


def parse_theory_rows_between(tex_text, start_substr, end_substr):
    """Data rows after start_substr and before end_substr."""
    i0 = tex_text.find(start_substr)
    if i0 < 0:
        return []
    rest = tex_text[i0:]
    i1 = rest.find(end_substr) if end_substr else -1
    chunk = rest[:i1] if i1 > 0 else rest
    rows = []
    for line in chunk.splitlines():
        line = line.strip()
        if "\\multicolumn" in line and "textbf" in line:
            continue
        if not line.startswith("QF"):
            continue
        if "&" not in line:
            continue
        line = line.replace("\\\\", "").strip()
        parts = [unescape_tex_cell(p) for p in line.split("&")]
        if len(parts) < 8:
            continue
        theory = parts[0]
        if not theory.startswith("QF_"):
            continue
        rows.append((theory, parts[1:8]))
    return rows


def md_table(headers, rows):
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def scatter_appendix_md():
    """Appendix-style scatter statistics (numbers aligned with the paper)."""
    lines = [
        "### Scatter plots: common-success subset and timeouts",
        "",
        "**Note**: Ratios use instances where **both** SOMTParser (`native`) and the baseline are `ok`; timeouts are drawn at the plot boundary.",
        "jSMTLIB RSS reflects JVM process RSS and is not directly comparable to C++ front-end RSS.",
        "",
        "#### Timeouts and common-success counts (N)",
        "",
        "| Baseline | Only_SP_TO | Only_Base_TO | Both_TO | Base successful | Common successful (N) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        "| Z3 | 51 | 459 | 81 | 161,444 | 161,390 |",
        "| cvc5 | 36 | 34,135 | 97 | 127,746 | 127,707 |",
        "| smt-switch | 36 | 30,989 | 97 | 69,409 | 69,372 |",
        "| pySMT | 3 | 475 | 130 | 99,284 | 99,279 |",
        "| ANTLR4 | 6 | 108 | 10 | 158,506 | 158,497 |",
        "| jSMTLIB | 38 | 105 | 95 | 145,788 | 145,747 |",
        "",
        "#### Scatter summary: time / peak RSS / AST nodes (ratio = competitor / SOMTParser)",
        "",
        "| Baseline | N | Time mean | Time Better(%) | RSS mean | RSS Better(%) | Nodes mean | Nodes Better(%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        "| Z3 | 161,390 | 0.500 | 2.85 | 0.528 | 4.11 | 1.978 | 86.40 |",
        "| cvc5 | 127,707 | 9.42 | 30.38 | 1.566 | 99.95 | 0.989 | 37.37 |",
        "| smt-switch | 69,372 | 14.81 | 54.57 | 1.997 | 96.14 | 1.760 | 72.46 |",
        "| pySMT | 99,279 | 1.524 | 47.43 | 1.260 | 99.75 | 1.163 | 71.40 |",
        "| ANTLR4 | 158,497 | 8.329 | 99.98 | 0.534 | 9.27 | 34.37 | 100.00 |",
        "| jSMTLIB | 145,747 | 3.925 | 98.69 | 0.278 | 2.62 | 3.497 | 94.71 |",
        "",
    ]
    return "\n".join(lines)


def build_markdown(tex_path):
    text = tex_path.read_text(encoding="utf-8")
    succ = parse_theory_rows_between(
        text,
        r"\textbf{Success Rate",
        r"\textbf{Timeout Rate",
    )
    timeout = parse_theory_rows_between(
        text,
        r"\textbf{Timeout Rate",
        r"\textbf{Fail Rate",
    )
    fail = parse_theory_rows_between(
        text,
        r"\textbf{Fail Rate",
        r"\bottomrule",
    )
    headers = ["Theory", "Z3", "cvc5", "smt-sw", "pysmt", "ANTLR4", "jSMTLIB", "SOMTParser"]
    blocks = [
        "## Front-end coverage (same source as paper Table `tab:frontend-all`)",
        "",
        "Success rate $\\%= 100 - \\mathrm{timeout} - \\mathrm{failure}$; timeout rate follows from this identity.",
        "",
        "### Success rate (%)",
        "",
    ]
    if succ:
        blocks.append(md_table(headers, [[t] + v for t, v in succ]))
    else:
        blocks.append("_Could not parse Success block from `frontend_table.tex`._")
    blocks.append("")
    blocks.append("### Timeout rate (%)")
    blocks.append("")
    if timeout:
        blocks.append(md_table(headers, [[t] + v for t, v in timeout]))
    else:
        blocks.append("_Could not parse Timeout block._")
    blocks.append("")
    blocks.append("### Fail rate (%)")
    blocks.append("")
    if fail:
        blocks.append(md_table(headers, [[t] + v for t, v in fail]))
    else:
        blocks.append("_Could not parse Fail block._")
    blocks.append("")
    blocks.append(scatter_appendix_md())
    return "\n".join(blocks)


def splice_readme(readme_path, md_block):
    p = Path(readme_path)
    s = p.read_text(encoding="utf-8")
    begin = "<!--PAPER_TABLES_BEGIN-->"
    end = "<!--PAPER_TABLES_END-->"
    if begin not in s or end not in s:
        return False, "README missing markers {} / {}".format(begin, end)
    a = s.index(begin) + len(begin)
    b = s.index(end)
    new_s = s[:a] + "\n\n" + md_block.strip() + "\n\n" + s[b:]
    p.write_text(new_s, encoding="utf-8")
    return True, "Updated {}".format(p)


def build_standalone_experiments_md():
    """Concatenate per-experiment summaries from results/<experiment>/."""
    parts = []
    for i, rel in enumerate(STANDALONE_SUMMARY_FILES):
        path = (REPO / rel).resolve()
        if i:
            parts.append("---")
            parts.append("")
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8").rstrip())
        else:
            parts.append("_Summary not present for this slot._")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def splice_readme_extended(readme_path, md_block):
    p = Path(readme_path)
    s = p.read_text(encoding="utf-8")
    if EXTENDED_BEGIN not in s or EXTENDED_END not in s:
        return True, "README has no {} / {} (skipped)".format(EXTENDED_BEGIN, EXTENDED_END)
    a = s.index(EXTENDED_BEGIN) + len(EXTENDED_BEGIN)
    b = s.index(EXTENDED_END)
    new_s = s[:a] + "\n\n" + md_block.strip() + "\n\n" + s[b:]
    p.write_text(new_s, encoding="utf-8")
    return True, "Updated extended block in {}".format(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", type=Path, default=DEFAULT_TEX)
    ap.add_argument("--out-md", type=Path, default=REPO / "results" / "summary" / "readme_paper_tables.md")
    ap.add_argument(
        "--readme",
        type=Path,
        default=None,
        help="If set, replace content between PAPER_TABLES markers in this README",
    )
    args = ap.parse_args()

    tex = args.tex.resolve()
    if not tex.is_file():
        print("error: file not found:", tex, file=sys.stderr)
        return 1
    md = build_markdown(tex)
    out_md = args.out_md.resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    print("Wrote", out_md)
    ext_md = build_standalone_experiments_md()
    ext_path = REPO / "results" / "summary" / "readme_standalone_experiments.md"
    ext_path.parent.mkdir(parents=True, exist_ok=True)
    ext_path.write_text(ext_md, encoding="utf-8")
    print("Wrote", ext_path)
    if args.readme:
        ok, msg = splice_readme(args.readme.resolve(), md)
        print(msg)
        if not ok:
            return 1
        ok2, msg2 = splice_readme_extended(args.readme.resolve(), ext_md)
        print(msg2)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
