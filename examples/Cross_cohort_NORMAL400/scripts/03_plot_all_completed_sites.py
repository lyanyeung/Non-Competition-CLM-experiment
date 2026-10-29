#!/usr/bin/env python3
"""Plot every completed FIXNC AD400 -> Normal400 reference pair, read-only inputs.

Place this file beside scan.py (Stage02) and plot.py (Stage15). Each case pair
gets its own directory; incomplete, ambiguous and failed cases remain visible
in the run manifest. A quick completion scan is not the formal cohort audit.
"""
import argparse
import csv
import importlib.util
import os
import subprocess
import traceback
from pathlib import Path
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verified_queue(user):
    p = subprocess.run(["squeue", "-u", user, "-h", "-o", "%i|%j|%T"],
                       text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError("squeue failed; cannot establish that cases are idle: " + p.stderr.strip())
    import re
    q = {}
    for line in p.stdout.splitlines():
        cols = line.split("|")
        if len(cols) != 3 or not cols[1] or not cols[2]:
            raise ValueError("Unexpected squeue line: " + repr(line))
        if not cols[1].startswith(("run.", "st_archive.")):
            continue
        name = re.sub(r"^(run|st_archive)\.", "", cols[1])
        q.setdefault(name, []).append(cols[2])
    return q


def restart_check(scan, row):
    folder = scan.OUT / "archive" / row["name"] / "rest" / row["latest"]
    for comp in ("clm2", "datm", "cpl"):
        p = folder / f"{row['name']}.{comp}.r.{row['latest']}.nc"
        if not p.is_file() or p.stat().st_size < 1024:
            raise ValueError("Missing or invalid final " + comp + " restart: " + str(p))


def stream_status(scan, ad, normal):
    pa, fa, ya = scan.stream_info(ad)
    pn, fn, yn = scan.stream_info(normal)
    if not fa or not fn:
        return "UNVERIFIED", str(pa or ""), str(pn or "")
    return ("MATCH" if fa == fn and ya == yn else "DIFFERENT"), str(pa), str(pn)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-root", required=True, type=Path,
                    help="New absolute output directory on Home or Research Filestore")
    args = ap.parse_args()
    root = args.output_root.expanduser()
    if not root.is_absolute():
        ap.error("--output-root must be absolute")
    root = root.resolve()
    if any(root == p or p in root.parents for p in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("Output under Scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("Output directory must be new or empty: " + str(root))
    here = Path(__file__).resolve().parent
    scan = load("progress_scan", here / "scan.py")
    plot = load("plot_stage15", here / "plot.py")
    q = verified_queue(scan.USER)
    scan.queue = lambda: q
    rows = scan.scan(None, True, False)
    by_name = {r["name"]: r for r in rows}
    normal = sorted((r for r in rows if r["mode"] == "NORMAL"),
                    key=lambda r: (r["site"], r["name"]))
    root.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(
        archive_root=scan.OUT / "archive", cases_root=scan.BASE / "cases",
        sites_root=scan.BASE / "sites/MY_EC_SITE", output_root=root,
        allow_incomplete=False, carbon_only=False, case_subdirectories=True,
        min_halfhour=40, min_days=20, obs_csv={})
    results = []
    for r in normal:
        ad_name = r.get("refcase") or ""
        record = {"Site": r["site"], "AD_case": ad_name, "Normal_case": r["name"],
                  "Normal_scan": r["verdict"], "AD_scan": "NOT_FOUND", "Status": "SKIPPED"}
        print(f"\n== {r['site']} | {r['name']} ==", flush=True)
        try:
            if r["verdict"] != "DONE":
                raise ValueError("Normal phase not DONE in current scan")
            ad = by_name.get(ad_name)
            if not ad or ad["site"] != r["site"] or ad["mode"] != "AD":
                raise ValueError("RUN_REFCASE does not identify a scanned AD case for this site")
            record["AD_scan"] = ad["verdict"]
            if ad["verdict"] != "DONE":
                raise ValueError("referenced AD phase not DONE in current scan")
            restart_check(scan, ad)
            restart_check(scan, r)
            ss, pa, pn = stream_status(scan, ad_name, r["name"])
            record.update(Stream_comparison=ss, AD_stream=pa, Normal_stream=pn)
            if ss != "MATCH":
                print("  WARNING: AD and Normal effective streams " + ss +
                      "; inspect stream provenance before interpreting the comparison", flush=True)
            pair = {"site": r["site"], "ad": ad_name, "normal": r["name"],
                    "ad_case_dir": settings.cases_root / ad_name, "cohort": "cross-cohort"}
            row = plot.process(pair, settings)
            record.update(row)
            record["Output_directory"] = str(root / r["site"] / r["name"])
        except Exception as exc:
            record["Error"] = f"{type(exc).__name__}: {exc}"
            print("  SKIP:", record["Error"], flush=True)
            if os.environ.get("DEBUG"):
                traceback.print_exc()
        results.append(record)
        save_manifest(root, results)
    if not normal:
        print("No Normal cases found in the current scan.", flush=True)
        save_manifest(root, results)
    ok = sum(r["Status"] == "OK" for r in results)
    failures = [r for r in results if r["Normal_scan"] == "DONE" and r["Status"] != "OK"]
    print(f"\nCOMPLETE: {ok} fully plotted; {len(failures)} DONE Normal cases need review.")
    print("Manifest:", root / "all_sites_summary.csv", flush=True)
    return int(bool(failures) or not ok)


def save_manifest(root, rows):
    fields = sorted({k for r in rows for k in r} | {"Site", "AD_case", "Normal_case", "Status", "Error"})
    tmp = root / ".all_sites_summary.tmp"
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(root / "all_sites_summary.csv")


if __name__ == "__main__":
    raise SystemExit(main())

