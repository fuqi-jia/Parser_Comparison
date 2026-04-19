#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z3 parse vs check_sat wall-clock in one process; separate CSV output."""
from __future__ import print_function

import argparse
import csv
import json
import os
import resource
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "results" / "parse_vs_solve"
CHECKPOINT = OUT_DIR / "z3_parse_solve_checkpoint.csv"
TABLE = OUT_DIR / "z3_parse_solve_table.csv"


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


def main():
    ap = argparse.ArgumentParser(description="Z3 parse vs solve wall-clock benchmark")
    ap.add_argument("--file-list", type=Path, required=True)
    ap.add_argument(
        "--solve-timeout-ms",
        type=int,
        default=600000,
        help="Z3 solver timeout parameter (milliseconds)",
    )
    ap.add_argument(
        "--wall-timeout",
        type=int,
        default=120,
        help="Outer subprocess wall-clock timeout (seconds)",
    )
    ap.add_argument("--memory-mb", type=int, default=4096)
    ap.add_argument("--jobs", "-j", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    ap.add_argument("--table", type=Path, default=TABLE)
    args = ap.parse_args()

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
    print("table:", args.table, datetime.now().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
