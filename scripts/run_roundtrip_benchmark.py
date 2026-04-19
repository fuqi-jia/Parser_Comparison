#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SMTParser parse -> dumpSMT2 -> reparse round-trip; parallel runs + checkpoint."""
from __future__ import print_function

import argparse
import csv
import json
import os
import resource
import signal
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "results" / "roundtrip"
CHECKPOINT = OUT_DIR / "roundtrip_checkpoint.csv"
TABLE = OUT_DIR / "roundtrip_table.csv"
BINARY_CANDIDATES = [
    REPO_ROOT / "build" / "roundtrip_tool",
    REPO_ROOT / "roundtrip_tool",
]


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


def find_binary():
    for p in BINARY_CANDIDATES:
        if p.is_file() and os.access(str(p), os.X_OK):
            return str(p)
    import shutil
    w = shutil.which("roundtrip_tool")
    return w


def extract_json_obj(text):
    if not text:
        return None
    i = text.find("{")
    j = text.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(text[i : j + 1])
    except Exception:
        return None


def run_one(binary, file_path, timeout_sec, memory_mb):
    proc_timeout = timeout_sec + 5
    cmd = [binary, file_path, str(timeout_sec), str(memory_mb)]

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
        out, err = proc.communicate(timeout=proc_timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait()
        except Exception:
            pass
        return {
            "status": "timeout",
            "ok1": "0",
            "ok2": "0",
            "nodes1": "",
            "nodes2": "",
            "match_nodes": "0",
            "wall_ms": str(timeout_sec * 1000),
            "error": "wrapper_timeout",
        }

    js = extract_json_obj(out or "")
    if not js:
        return {
            "status": "fail",
            "ok1": "0",
            "ok2": "0",
            "nodes1": "",
            "nodes2": "",
            "match_nodes": "0",
            "wall_ms": "",
            "error": (err or out or "no_json")[:500],
        }

    ok1 = bool(js.get("ok1"))
    ok2 = bool(js.get("ok2"))
    match = bool(js.get("match_nodes"))
    err = js.get("error") or ""
    if err == "timeout":
        st = "timeout"
    elif ok1 and ok2 and match:
        st = "ok"
    elif ok1 and ok2:
        st = "mismatch"
    else:
        st = "fail"

    return {
        "status": st,
        "ok1": "1" if ok1 else "0",
        "ok2": "1" if ok2 else "0",
        "nodes1": str(js.get("nodes1", "")),
        "nodes2": str(js.get("nodes2", "")),
        "match_nodes": "1" if match else "0",
        "wall_ms": str(js.get("wall_ms", "")),
        "error": err[:500],
    }


def load_done(path):
    done = set()
    rows = []
    if not path.is_file():
        return done, rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            fp = row.get("file")
            if fp:
                done.add(fp)
                rows.append(row)
    return done, rows


def append_row(path, row, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    newf = not path.is_file()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if newf:
            w.writeheader()
        w.writerow(row)
        f.flush()


def rebuild_table(checkpoint_rows, out_table):
    header = ["file", "status", "ok1", "ok2", "nodes1", "nodes2", "match_nodes", "wall_ms", "error"]
    out_table.parent.mkdir(parents=True, exist_ok=True)
    with open(out_table, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for row in sorted(checkpoint_rows, key=lambda r: r.get("file", "")):
            w.writerow({k: row.get(k, "") for k in header})


def main():
    ap = argparse.ArgumentParser(description="SOMTParser round-trip benchmark")
    ap.add_argument("--file-list", type=Path, required=True)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--memory-mb", type=int, default=4096)
    ap.add_argument("--jobs", "-j", type=int, default=24)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    ap.add_argument("--table", type=Path, default=TABLE)
    args = ap.parse_args()

    fl = (REPO_ROOT / args.file_list).resolve() if not args.file_list.is_absolute() else args.file_list.resolve()
    files = load_file_list(fl)
    if not files:
        print("error: empty file-list", file=sys.stderr)
        return 1

    binary = find_binary()
    if not binary:
        print("error: roundtrip_tool not found (build with cmake first)", file=sys.stderr)
        return 1
    print("binary:", binary)

    args.checkpoint = args.checkpoint.resolve()
    args.table = args.table.resolve()
    done, crows = load_done(args.checkpoint)
    if not args.resume:
        if args.checkpoint.is_file():
            args.checkpoint.unlink()
        done, crows = set(), []

    todo = [f for f in files if f not in done]
    print("files", len(files), "todo", len(todo), "jobs", args.jobs)

    header = ["file", "status", "ok1", "ok2", "nodes1", "nodes2", "match_nodes", "wall_ms", "error"]
    jobs = max(1, min(args.jobs, len(todo) or 1))

    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(run_one, binary, fp, args.timeout, args.memory_mb): fp for fp in todo}
        n = 0
        for fu in as_completed(futs):
            fp = futs[fu]
            n += 1
            try:
                r = fu.result()
            except Exception as e:
                r = {
                    "status": "error",
                    "ok1": "0",
                    "ok2": "0",
                    "nodes1": "",
                    "nodes2": "",
                    "match_nodes": "0",
                    "wall_ms": "",
                    "error": str(e)[:300],
                }
            row = {"file": fp, **r}
            crows.append(row)
            append_row(args.checkpoint, row, header)
            print("[{}/{}] {} {}".format(n, len(todo), Path(fp).name[:48], r["status"]), flush=True)

    _, allrows = load_done(args.checkpoint)
    rebuild_table(allrows, args.table)
    print("table:", args.table, datetime.now().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
