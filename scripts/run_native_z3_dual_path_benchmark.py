#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SOMTParser dumpSMT2 + dual Z3 paths: original vs dump; compare sat/unsat/unknown."""
from __future__ import print_function

import argparse
import csv
import json
import os
import experiment_presets as ep
import resource
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "results" / "native_z3_dual_path"
CHECKPOINT = OUT_DIR / "native_z3_dual_path_checkpoint.csv"
TABLE = OUT_DIR / "native_z3_dual_path_table.csv"
SUMMARY = OUT_DIR / "native_z3_dual_path_summary.md"


def dual_binary():
    for p in (
        REPO_ROOT / "build" / "native_z3_dual_path",
        REPO_ROOT / "native_z3_dual_path",
    ):
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
    import shutil

    return shutil.which("native_z3_dual_path")


def load_file_list(path):
    root = REPO_ROOT.resolve()
    files = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                p = Path(line)
                files.append(str(p if p.is_absolute() else (root / p)))
    return files


def extract_json(text):
    if not text:
        return None
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(text[i : j + 1])
    except Exception:
        return None


def run_one(binary, file_path, solve_timeout_ms, memory_mb, outer_sec):
    cmd = [binary, file_path, str(solve_timeout_ms)]
    to = outer_sec + 15

    def set_limits():
        try:
            b = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except (ValueError, resource.error):
            pass

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=set_limits if memory_mb > 0 else None,
        )
        out, err = proc.communicate(timeout=to)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait()
        except Exception:
            pass
        return {
            "status": "timeout",
            "dump_ok": "0",
            "path_a_verdict": "",
            "path_b_verdict": "",
            "verdict_disagree": "",
            "path_a_parse_ms": "",
            "path_a_solve_ms": "",
            "native_dump_ms": "",
            "path_b_parse_ms": "",
            "path_b_solve_ms": "",
            "info": "",
            "error": "wrapper_timeout",
        }

    js = extract_json(out or "")
    if not js:
        return {
            "status": "fail",
            "dump_ok": "0",
            "path_a_verdict": "",
            "path_b_verdict": "",
            "verdict_disagree": "",
            "path_a_parse_ms": "",
            "path_a_solve_ms": "",
            "native_dump_ms": "",
            "path_b_parse_ms": "",
            "path_b_solve_ms": "",
            "info": "",
            "error": (err or out or "no_json")[:500],
        }

    def g(k, default=""):
        v = js.get(k)
        if v is None:
            return default
        if isinstance(v, bool):
            return "1" if v else "0"
        return str(v)

    disagree = js.get("verdict_disagree")
    if isinstance(disagree, bool):
        vd = "1" if disagree else "0"
    elif isinstance(disagree, str):
        vd = "1" if disagree.lower() in ("true", "1", "yes") else "0"
    else:
        vd = "0"

    return {
        "status": g("status", "unknown"),
        "dump_ok": g("dump_ok", "0"),
        "path_a_verdict": g("path_a_verdict"),
        "path_b_verdict": g("path_b_verdict"),
        "verdict_disagree": vd,
        "path_a_parse_ms": g("path_a_parse_ms"),
        "path_a_solve_ms": g("path_a_solve_ms"),
        "native_dump_ms": g("native_dump_ms"),
        "path_b_parse_ms": g("path_b_parse_ms"),
        "path_b_solve_ms": g("path_b_solve_ms"),
        "info": g("info"),
        "error": g("error"),
    }


def load_done(path):
    done, rows = set(), []
    if not path.is_file():
        return done, rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            fp = row.get("file")
            if fp:
                done.add(fp)
                rows.append(row)
    return done, rows


def append_row(path, row, header):
    newf = not path.is_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if newf:
            w.writeheader()
        w.writerow(row)


def rebuild_table(rows, out):
    header = [
        "file",
        "status",
        "dump_ok",
        "path_a_verdict",
        "path_b_verdict",
        "verdict_disagree",
        "path_a_parse_ms",
        "path_a_solve_ms",
        "native_dump_ms",
        "path_b_parse_ms",
        "path_b_solve_ms",
        "info",
        "error",
    ]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for row in sorted(rows, key=lambda r: r.get("file", "")):
            w.writerow({k: row.get(k, "") for k in header})


def write_summary(table_path, summary_path):
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "## SOMTParser `dumpSMT2` vs Z3 verdict agreement (standalone)",
        "",
        "**Path A:** Z3 `parse` + `check` on the **original** SMT2 file. **Path B:** SOMTParser parses the "
        "same file, `dumpSMT2` to a temp file, then Z3 `parse` + `check` on the dump. **Disagreement** is "
        "only `(sat,unsat)` or `(unsat,sat)`; if either side is `unknown` or a path did not complete, we do "
        "not count that as a sat/unsat mismatch. The `info` column repeats `path_a=…;path_b=…` for quick "
        "grepping; full timings are in the CSV.",
        "",
    ]
    if not table_path.is_file():
        lines.append("_No aggregate results yet._")
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    with open(table_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        lines.append("_No aggregate results yet._")
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    n = len(rows)
    st = Counter((r.get("status") or "").strip().lower() or "unknown" for r in rows)
    lines.append("### Overall (by `status`)")
    lines.append("")
    lines.append("| Status | Count | Share |")
    lines.append("| --- | ---: | ---: |")
    for k in sorted(st.keys(), key=lambda x: (-st[x], x)):
        c = st[k]
        lines.append("| `{}` | {} | {:.4f}% |".format(k, c, 100.0 * c / n if n else 0.0))
    lines.append("")

    dis = sum(1 for r in rows if (r.get("verdict_disagree") or "").strip() == "1")
    lines.append("### Verdict disagreement (sat vs unsat only)")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    lines.append("| `verdict_disagree==1` | {} |".format(dis))
    lines.append("| Share of all rows | {:.4f}% |".format(100.0 * dis / n if n else 0.0))
    lines.append("")

    va = Counter((r.get("path_a_verdict") or "").strip() or "∅" for r in rows)
    vb = Counter((r.get("path_b_verdict") or "").strip() or "∅" for r in rows)
    lines.append("### Verdict marginals")
    lines.append("")
    lines.append("| path_a_verdict | Count |")
    lines.append("| --- | ---: |")
    for k in sorted(va.keys(), key=lambda x: (-va[x], x)):
        lines.append("| `{}` | {} |".format(k, va[k]))
    lines.append("")
    lines.append("| path_b_verdict | Count |")
    lines.append("| --- | ---: |")
    for k in sorted(vb.keys(), key=lambda x: (-vb[x], x)):
        lines.append("| `{}` | {} |".format(k, vb[k]))
    lines.append("")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(
        description="SOMTParser dumpSMT2 + Z3 on original vs dump; compare sat/unsat/unknown."
    )
    ap.add_argument("--file-list", type=Path, required=True)
    ap.add_argument(
        "--solve-timeout-ms",
        type=int,
        default=None,
        help="Z3 solver timeout per check (ms); default 600000, or from --preset",
    )
    ap.add_argument(
        "--outer-sec",
        type=int,
        default=None,
        dest="outer_sec",
        help="Subprocess wall timeout (seconds) for whole native_z3_dual_path run; default 1500, or dual_path_outer_sec from --preset",
    )
    ap.add_argument(
        "--memory-mb",
        type=int,
        default=None,
        help="RLIMIT_AS cap per child (MiB); default 4096, or from --preset",
    )
    ap.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=None,
        help="Parallel workers; default 8, or from --preset",
    )
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    ap.add_argument("--table", type=Path, default=TABLE)
    ep.add_preset_arguments(ap)
    args = ap.parse_args()
    ep.require_known_preset(args.preset)
    args.solve_timeout_ms = ep.pick(args.preset, "solve_timeout_ms", args.solve_timeout_ms, 600000)
    args.outer_sec = ep.pick(args.preset, "dual_path_outer_sec", args.outer_sec, 1500)
    args.memory_mb = ep.pick(args.preset, "memory_mb", args.memory_mb, 4096)
    args.jobs = ep.pick(args.preset, "jobs", args.jobs, 8)
    if args.preset:
        print(
            "preset {}: solve_timeout_ms={} outer_sec={}s memory_mb={} jobs={}".format(
                args.preset,
                args.solve_timeout_ms,
                args.outer_sec,
                args.memory_mb,
                args.jobs,
            )
        )

    fl = (REPO_ROOT / args.file_list).resolve() if not args.file_list.is_absolute() else args.file_list.resolve()
    files = load_file_list(fl)
    if not files:
        print("error: empty file-list", file=sys.stderr)
        return 1

    b = dual_binary()
    if not b:
        print(
            "error: native_z3_dual_path not found (build-internal with Z3 available: external/z3 prebuilt, conda, or libz3-dev)",
            file=sys.stderr,
        )
        return 1
    print("binary:", b)

    args.checkpoint = args.checkpoint.resolve()
    args.table = args.table.resolve()
    done, crows = load_done(args.checkpoint)
    if not args.resume and args.checkpoint.is_file():
        args.checkpoint.unlink()
        done, crows = set(), []

    todo = [f for f in files if f not in done]
    print("files", len(files), "todo", len(todo))

    header = [
        "file",
        "status",
        "dump_ok",
        "path_a_verdict",
        "path_b_verdict",
        "verdict_disagree",
        "path_a_parse_ms",
        "path_a_solve_ms",
        "native_dump_ms",
        "path_b_parse_ms",
        "path_b_solve_ms",
        "info",
        "error",
    ]
    jobs = max(1, min(args.jobs, len(todo) or 1))
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {
            ex.submit(run_one, b, fp, args.solve_timeout_ms, args.memory_mb, args.outer_sec): fp
            for fp in todo
        }
        n = 0
        for fu in as_completed(futs):
            fp = futs[fu]
            n += 1
            try:
                r = fu.result()
            except Exception as e:
                r = {
                    "status": "error",
                    "dump_ok": "0",
                    "path_a_verdict": "",
                    "path_b_verdict": "",
                    "verdict_disagree": "",
                    "path_a_parse_ms": "",
                    "path_a_solve_ms": "",
                    "native_dump_ms": "",
                    "path_b_parse_ms": "",
                    "path_b_solve_ms": "",
                    "info": "",
                    "error": str(e)[:300],
                }
            row = {"file": fp, **r}
            crows.append(row)
            append_row(args.checkpoint, row, header)
            print("[{}/{}] {}".format(n, len(todo), Path(fp).name[:48]), r.get("status"), flush=True)

    _, allrows = load_done(args.checkpoint)
    rebuild_table(allrows, args.table)
    write_summary(args.table, SUMMARY)
    print("table:", args.table, datetime.now().isoformat())
    print("summary:", SUMMARY.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
