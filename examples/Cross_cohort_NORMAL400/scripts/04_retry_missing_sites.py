#!/usr/bin/env python3
"""Retry incomplete/missing plots, reusing validated figures from a completed job.

Place this file beside scan.py (Stage02) and plot.py (Stage15). Each case pair
gets its own directory; incomplete, ambiguous and failed cases remain visible
in the run manifest. A quick completion scan is not the formal cohort audit.
"""
import argparse
import csv
import importlib.util
import json
import os
import subprocess
import traceback
import uuid
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


def previous_job_finished(job):
    if not str(job).isdigit():
        raise ValueError("previous job ID must contain digits only")
    p = subprocess.run(["sacct", "-n", "-P", "-j", str(job), "--format=JobIDRaw,State"],
                       text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError("sacct failed: " + p.stderr.strip())
    matches = [s.split("|")[1].strip().split()[0].rstrip("+") for s in p.stdout.splitlines()
               if "|" in s and s.split("|")[0].strip() == str(job)]
    terminal = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
                "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}
    if len(matches) != 1 or matches[0] not in terminal:
        raise RuntimeError(f"Previous job {job} is not confirmed finished by sacct: {matches}")
    return matches[0]


def find_previous(previous, job, base):
    if previous:
        root = Path(previous).expanduser().resolve()
    else:
        log = base / f"all_sites_{job}.log"
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.is_file() else []
        found = [Path(s[len("Manifest: "):]).parent for s in lines
                 if s.startswith("Manifest: ") and s.endswith("/all_sites_summary.csv")]
        if found:
            root = found[-1].resolve()
        else:
            candidates = [p for p in base.glob("All_completed_AD400_NORMAL400_*")
                          if (p / "all_sites_summary.csv").is_file()]
            if not candidates:
                return None
            if len(candidates) != 1:
                raise ValueError("Cannot uniquely identify previous output. Pass --previous-run; candidates: " +
                                 ", ".join(map(str, sorted(candidates))))
            root = candidates[0].resolve()
    if not (root / "all_sites_summary.csv").is_file():
        if previous:
            raise FileNotFoundError("Previous summary missing: " + str(root / "all_sites_summary.csv"))
        print("Previous summary is absent; proceeding with fresh live discovery", flush=True)
        return None
    return root


def load_previous(root):
    with (root / "all_sites_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {(r.get("Site"), r.get("Normal_case"), r.get("AD_case")): r for r in rows}


def find_retry_output(job, base, previous_root, previous_job):
    """Locate a finished supplementary run by recorded job ID, never by recency."""
    candidates = []
    for p in base.glob("Missing_completed_AD400_NORMAL400_*"):
        try:
            info = json.loads((p / "RUN_INFO.json").read_text(encoding="utf-8"))
            if (str(info.get("retry_job", "")) == str(job) and
                    str(info.get("previous_job", "")) == str(previous_job) and
                    (previous_root is None or Path(info["previous_root"]).resolve() == previous_root.resolve()) and
                    (p / "all_sites_summary.csv").is_file()):
                candidates.append(p.resolve())
        except (OSError, ValueError, KeyError):
            continue
    if len(candidates) > 1:
        raise ValueError(f"Multiple outputs claim retry job {job}: {candidates}")
    return candidates[0] if candidates else None


def reusable(previous, root, site, ad, normal):
    row = previous.get((site, normal, ad))
    if not row or row.get("Status") != "OK":
        return None
    folder = (root / site / normal).resolve()
    if root.resolve() not in folder.parents:
        raise ValueError("Previous output escapes its root")
    paths = [folder / f"{site}_01_carbon_pools_AD400_NORMAL400.png",
             folder / f"{site}_02_carbon_pools_NORMAL400_panels.png",
             folder / f"{site}_GPP_NEE_monthly_overview.png"]
    for p in paths:
        if not p.is_file() or p.stat().st_size <= 8:
            return None
        with p.open("rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
    try:
        meta = json.loads((folder / f"{site}_metadata.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if meta.get("status") != "OK" or meta.get("ad_case") != ad or meta.get("normal_case") != normal:
        return None
    return folder


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-root", required=True, type=Path,
                    help="New absolute output directory on Home or Research Filestore")
    ap.add_argument("--previous-job", required=True, help="The finished original plotting Slurm job ID")
    ap.add_argument("--previous-run", type=Path, help="Original output directory, if automatic identification is ambiguous")
    ap.add_argument("--extra-job", help="Also reuse completed plots from this finished supplementary Slurm job")
    ap.add_argument("--login", action="store_true", help="Run directly in the login shell, without Slurm")
    args = ap.parse_args()
    root = args.output_root.expanduser()
    if not root.is_absolute():
        ap.error("--output-root must be absolute")
    root = root.resolve()
    if any(root == p or p in root.parents for p in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("Output under Scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("Output directory must be new or empty: " + str(root))
    job_state = previous_job_finished(args.previous_job)
    previous_root = find_previous(args.previous_run, args.previous_job, Path.home() / "CLM_FATES_PLOTS")
    previous_roots = [previous_root] if previous_root is not None else []
    if args.extra_job:
        extra_state = previous_job_finished(args.extra_job)
        extra = find_retry_output(args.extra_job, Path.home() / "CLM_FATES_PLOTS", previous_root, args.previous_job)
        if extra:
            previous_roots.append(extra)
            print(f"SUPPLEMENTARY JOB {args.extra_job}: {extra_state}; OUTPUT: {extra}", flush=True)
        else:
            print(f"SUPPLEMENTARY JOB {args.extra_job}: {extra_state}; no matching saved summary, continuing", flush=True)
    previous = [(p, load_previous(p)) for p in previous_roots]
    print(f"PREVIOUS JOB {args.previous_job}: {job_state}; PREVIOUS OUTPUT: {previous_root}", flush=True)
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
    run_id = uuid.uuid4().hex
    (root / "RUN_INFO.json").write_text(json.dumps({"previous_job": str(args.previous_job),
        "retry_job": os.environ.get("SLURM_JOB_ID", ""),
        "run_mode": "login" if args.login else "slurm", "run_id": run_id,
        "previous_job_state": job_state, "previous_root": str(previous_root) if previous_root else "",
        "previous_roots": [str(p) for p in previous_roots]}, indent=2) + "\n", encoding="utf-8")
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
            reused = next((folder for p, old in reversed(previous)
                           if (folder := reusable(old, p, r["site"], ad_name, r["name"])) is not None), None)
            if reused:
                record.update(Status="REUSED", Output_directory=str(reused), Source="previous run")
                print("  REUSED:", reused, flush=True)
                results.append(record)
                save_manifest(root, results)
                continue
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
            record["Output_directory"] = str(root / r["site"] / r["name"])
            record["Error"] = f"{type(exc).__name__}: {exc}"
            print("  SKIP:", record["Error"], flush=True)
            if os.environ.get("DEBUG"):
                traceback.print_exc()
        results.append(record)
        save_manifest(root, results)
    if not normal:
        print("No Normal cases found in the current scan.", flush=True)
        save_manifest(root, results)
    ok = sum(r["Status"] in ("OK", "REUSED") for r in results)
    failures = [r for r in results if r["Normal_scan"] == "DONE" and r["Status"] not in ("OK", "REUSED")]
    print(f"\nCOMPLETE: {ok} fully plotted or reused; {len(failures)} DONE Normal cases need review.")
    print("Manifest:", root / "all_sites_summary.csv", flush=True)
    (root / "RUN_COMPLETE.json").write_text(json.dumps({"run_id": run_id, "ok_or_reused": ok,
        "completed_needing_review": len(failures)}, indent=2) + "\n", encoding="utf-8")
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



