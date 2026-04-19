#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z3 parse vs check_sat wall-clock in one process; separate CSV output."""
from __future__ import print_function

import argparse
import csv
import json
import os
import experiment_presets as ep
import resource
import statistics
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "results" / "parse_vs_solve"
CHECKPOINT = OUT_DIR / "z3_parse_solve_checkpoint.csv"
TABLE = OUT_DIR / "z3_parse_solve_table.csv"
SUMMARY = OUT_DIR / "parse_vs_solve_summary.md"


def z3_binary():
    for p in (
        REPO_ROOT / "external" / "z3" / "z3_parse_vs_solve",
        REPO_ROOT / "external" / "z3" / "z3_parse_vs_solve.exe",
    ):
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
    import shutil
    return shutil.which("z3_parse_vs_solve")


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


def run_one(binary, file_path, solve_timeout_ms, memory_mb, wall_timeout_sec):
    cmd = [binary, file_path, str(solve_timeout_ms)]
    to = wall_timeout_sec + 10

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
            "parse_ok": "0",
            "solve_ok": "0",
            "parse_ms": "",
            "solve_ms": "",
            "check_result": "",
            "parse_over_solve": "",
            "parse_over_total": "",
            "error": "wrapper_timeout",
        }

    js = extract_json(out or "")
    if not js:
        return {
            "status": "fail",
            "parse_ok": "0",
            "solve_ok": "0",
            "parse_ms": "",
            "solve_ms": "",
            "check_result": "",
            "parse_over_solve": "",
            "parse_over_total": "",
            "error": (err or out or "no_json")[:400],
        }

    parse_ok = bool(js.get("parse_ok"))
    solve_ok = bool(js.get("solve_ok"))
    try:
        pm = float(js.get("parse_ms") or 0)
        sm = float(js.get("solve_ms") or 0)
    except (TypeError, ValueError):
        pm = sm = 0.0
    tot = pm + sm
    pos = sm > 0
    ps_ratio = (pm / sm) if pos else ("inf" if pm > 0 else "")
    pt_ratio = (pm / tot) if tot > 0 else ""

    errs = js.get("errors")
    err_s = ""
    if isinstance(errs, list) and errs:
        err_s = "; ".join(str(x) for x in errs)[:400]
    elif js.get("errors"):
        err_s = str(js.get("errors"))[:400]

    if not parse_ok:
        st = "parse_fail"
    elif not solve_ok:
        st = "solve_fail"
    else:
        st = "ok"

    return {
        "status": st,
        "parse_ok": "1" if parse_ok else "0",
        "solve_ok": "1" if solve_ok else "0",
        "parse_ms": str(pm),
        "solve_ms": str(sm),
        "check_result": str(js.get("check_result", "")),
        "parse_over_solve": "" if ps_ratio == "" else str(ps_ratio),
        "parse_over_total": "" if pt_ratio == "" else str(pt_ratio),
        "error": err_s,
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
        "parse_ok",
        "solve_ok",
        "parse_ms",
        "solve_ms",
        "check_result",
        "parse_over_solve",
        "parse_over_total",
        "error",
    ]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for row in sorted(rows, key=lambda r: r.get("file", "")):
            w.writerow({k: row.get(k, "") for k in header})


def write_parse_vs_solve_summary(table_path, summary_path):
    """Markdown rollup for Z3 parse-vs-solve (same folder as CSV)."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "## Z3 parse vs solver wall time (standalone)",
        "",
        "Per instance: empty-assertions `check-sat` (parse path) vs full `check-sat` (includes solving); `parse_ms` / `solve_ms` are wall-clock milliseconds in one Z3 process.",
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
    st_counts = Counter((r.get("status") or "").strip().lower() or "unknown" for r in rows)
    lines.append("### Overall (by outcome)")
    lines.append("")
    lines.append("| Status | Count | Share |")
    lines.append("| --- | ---: | ---: |")
    for st in sorted(st_counts.keys(), key=lambda k: (-st_counts[k], k)):
        c = st_counts[st]
        lines.append("| `{}` | {} | {:.4f}% |".format(st, c, 100.0 * c / n if n else 0.0))
    lines.append("")

    ok_rows = [r for r in rows if (r.get("status") or "").strip().lower() == "ok"]
    parse_ms = []
    solve_ms = []
    pot = []  # parse_over_total as float
    pos = []  # parse_over_solve when finite
    for r in ok_rows:
        try:
            parse_ms.append(float(r.get("parse_ms") or 0))
            solve_ms.append(float(r.get("solve_ms") or 0))
        except (TypeError, ValueError):
            continue
        pt = (r.get("parse_over_total") or "").strip()
        if pt:
            try:
                pot.append(float(pt))
            except ValueError:
                pass
        ps = (r.get("parse_over_solve") or "").strip().lower()
        if ps and ps != "inf":
            try:
                pos.append(float(ps))
            except ValueError:
                pass

    lines.append("### Timing (`status=ok` only)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    lines.append("| Count | {} |".format(len(ok_rows)))
    if parse_ms:
        lines.append("| Median `parse_ms` | {:.6g} |".format(statistics.median(parse_ms)))
        lines.append("| Median `solve_ms` | {:.6g} |".format(statistics.median(solve_ms)))
    else:
        lines.append("| Median `parse_ms` | — |")
        lines.append("| Median `solve_ms` | — |")
    if pot:
        lines.append(
            "| Median `parse_over_total` (parse / (parse+solve)) | {:.6g} |".format(
                statistics.median(pot)
            )
        )
    else:
        lines.append("| Median `parse_over_total` | — |")
    if pos:
        lines.append(
            "| Median `parse_over_solve` (finite only) | {:.6g} |".format(statistics.median(pos))
        )
    else:
        lines.append("| Median `parse_over_solve` (finite) | — |")
    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Z3 parse vs solve wall-clock benchmark")
    ap.add_argument("--file-list", type=Path, required=True)
    ap.add_argument(
        "--solve-timeout-ms",
        type=int,
        default=None,
        help="Z3 solver timeout parameter (milliseconds); default 600000, or from --preset",
    )
    ap.add_argument(
        "--wall-timeout",
        type=int,
        default=None,
        help="Outer subprocess wall-clock timeout (seconds); default 120, or from --preset",
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
    args.wall_timeout = ep.pick(args.preset, "wall_timeout", args.wall_timeout, 120)
    args.memory_mb = ep.pick(args.preset, "memory_mb", args.memory_mb, 4096)
    args.jobs = ep.pick(args.preset, "jobs", args.jobs, 8)
    if args.preset:
        print(
            "preset {}: solve_timeout_ms={} wall_timeout={}s memory_mb={} jobs={}".format(
                args.preset,
                args.solve_timeout_ms,
                args.wall_timeout,
                args.memory_mb,
                args.jobs,
            )
        )

    fl = (REPO_ROOT / args.file_list).resolve() if not args.file_list.is_absolute() else args.file_list.resolve()
    files = load_file_list(fl)
    if not files:
        print("error: empty file-list", file=sys.stderr)
        return 1

    b = z3_binary()
    if not b:
        print("error: z3_parse_vs_solve not found (run make in external/z3)", file=sys.stderr)
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
        "parse_ok",
        "solve_ok",
        "parse_ms",
        "solve_ms",
        "check_result",
        "parse_over_solve",
        "parse_over_total",
        "error",
    ]
    jobs = max(1, min(args.jobs, len(todo) or 1))
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {
            ex.submit(
                run_one,
                b,
                fp,
                args.solve_timeout_ms,
                args.memory_mb,
                args.wall_timeout,
            ): fp
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
                    "parse_ok": "0",
                    "solve_ok": "0",
                    "parse_ms": "",
                    "solve_ms": "",
                    "check_result": "",
                    "parse_over_solve": "",
                    "parse_over_total": "",
                    "error": str(e)[:300],
                }
            row = {"file": fp, **r}
            crows.append(row)
            append_row(args.checkpoint, row, header)
            print("[{}/{}] {}".format(n, len(todo), Path(fp).name[:48]), r["status"], flush=True)

    _, allrows = load_done(args.checkpoint)
    rebuild_table(allrows, args.table)
    write_parse_vs_solve_summary(args.table, SUMMARY)
    print("table:", args.table, datetime.now().isoformat())
    print("summary:", SUMMARY.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
