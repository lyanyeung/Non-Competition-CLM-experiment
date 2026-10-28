#!/usr/bin/env python3
"""READ ONLY quick scan: which cases have finished AD400 and NORMAL400, across all cohorts.

For every archive folder under OUT/archive that has restarts (plus any case that is only
queued), it reads the case's env_run.xml directly (no xmlquery, no Slurm writes):

  mode      NORMAL if CLM_ACCELERATED_SPINUP=off (or the name contains NORMAL), else AD
  start     RUN_STARTDATE year
  latest    newest archived restart folder; years = latest - start
  state     spinup_state in the latest land restart (AD expects 2, Normal 0)
  queue     run/st_archive jobs in squeue for this exact case name
  last      last CaseStatus event

Verdicts (quick view; the per-cohort audit actions remain the formal completion check):
  DONE      years >= 400, nothing queued, spinup_state as expected, last event success
  RUNNING   jobs queued (R/PD)
  STOPPED   not queued and < 400 years, or last event an error (shows the event)

Then one line per site: best AD and best Normal case.

Usage:  python3 -B 02_scan_all_spinup_progress_readonly.py [--match TEXT ...] [--all]
        --all also lists cases with < 5 archived years (smokes, failed first segments).
"""
from __future__ import annotations
import argparse, re, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
USER = "ly3n24"
TARGET = 400
STAMP = re.compile(r"^(\d{4})-01-01-00000$")


def env(case, key):
    for f in ("env_run.xml", "env_case.xml", "env_build.xml"):
        p = case / f
        if not p.is_file(): continue
        try:
            for e in ET.parse(p).getroot().iter("entry"):
                if e.get("id") == key: return e.get("value")
        except ET.ParseError:
            pass
    return None


def queue():
    try:
        out = subprocess.run(["squeue", "-u", USER, "-h", "-o", "%i|%j|%T"], text=True, capture_output=True,
                             timeout=60).stdout
    except Exception:
        return None
    q = {}
    for ln in out.splitlines():
        p = ln.split("|")
        if len(p) >= 3:
            n = re.sub(r"^(run|st_archive)\.", "", p[1])
            q.setdefault(n, []).append(("run" if p[1].startswith("run.") else "arc") + ":" + p[2][:2])
    return q


def spinup(path):
    try:
        from netCDF4 import Dataset
        with Dataset(str(path)) as ds:
            if "spinup_state" in ds.variables: return int(ds.variables["spinup_state"][:].ravel()[0])
            if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
    except Exception as e:
        return "err:" + type(e).__name__
    return None


def last_event(case):
    p = case / "CaseStatus"
    if not p.is_file(): return "-"
    ev = re.findall(r"(case\.run|st_archive|case\.submit|model execution) (success|error|starting)", p.read_text(errors="replace"))
    return " ".join(ev[-1]) if ev else "-"


def scan(match, show_all):
    q = queue()
    names = set()
    arch = OUT / "archive"
    if arch.is_dir():
        names |= {d.name for d in arch.iterdir() if (d / "rest").is_dir()}
    if q: names |= {n for n in q if (BASE / "cases" / n).is_dir()}
    if match: names = {n for n in names if any(m in n for m in match)}
    rows = []
    for n in sorted(names):
        case = BASE / "cases" / n
        acc = (env(case, "CLM_ACCELERATED_SPINUP") or "").lower()
        mode = "NORMAL" if (acc == "off" or "NORMAL" in n.upper()) else ("AD" if acc == "on" else "?")
        sd = env(case, "RUN_STARTDATE") or ""
        start = int(sd[:4]) if re.match(r"\d{4}-", sd) else None
        rest = arch / n / "rest"
        stamps = sorted(d.name for d in rest.iterdir() if d.is_dir() and STAMP.match(d.name)) if rest.is_dir() else []
        latest = stamps[-1] if stamps else None
        years = (int(latest[:4]) - start) if latest and start is not None else None
        st = spinup(rest / latest / f"{n}.clm2.r.{latest}.nc") if latest else None
        qq = ",".join(q.get(n, [])) if q is not None else "squeue?"
        ev = last_event(case) if case.is_dir() else "no case dir"
        want = 0 if mode == "NORMAL" else 2
        if qq and qq != "squeue?": verdict = "RUNNING"
        elif years is not None and years >= TARGET and st == want and "error" not in ev: verdict = "DONE"
        else: verdict = "STOPPED"
        if not show_all and verdict != "RUNNING" and (years is None or years < 5): continue
        rows.append(dict(name=n, site=n.split("_")[0], mode=mode, start=start, latest=latest, years=years,
                         st=st, q=qq or "-", ev=ev, verdict=verdict, refcase=env(case, "RUN_REFCASE")))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--match", nargs="+"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    rows = scan(a.match, a.all)
    print(f"{'VERDICT':8} {'MODE':6} {'YEARS':>5} {'SPIN':>4} {'LATEST':16} {'QUEUE':12} {'LAST EVENT':24} CASE")
    for r in sorted(rows, key=lambda r: (r["site"], r["mode"], r["name"])):
        print(f"{r['verdict']:8} {r['mode']:6} {str(r['years']):>5} {str(r['st']):>4} {str(r['latest']):16} "
              f"{r['q'][:12]:12} {r['ev'][:24]:24} {r['name']}")
    print("\nPER SITE (best case per mode; DONE > RUNNING > STOPPED, then most years)")
    rank = {"DONE": 2, "RUNNING": 1, "STOPPED": 0}
    sites = {}
    for r in rows: sites.setdefault(r["site"], {}).setdefault(r["mode"], []).append(r)
    cnt = {"AD400 DONE": 0, "NORMAL400 DONE": 0}
    for s in sorted(sites):
        best = {}
        for m, rs in sites[s].items():
            best[m] = max(rs, key=lambda r: (rank[r["verdict"]], r["years"] or -1))
        ad, nm = best.get("AD"), best.get("NORMAL")
        if ad and ad["verdict"] == "DONE": cnt["AD400 DONE"] += 1
        if nm and nm["verdict"] == "DONE": cnt["NORMAL400 DONE"] += 1
        f = lambda r: f"{r['verdict']} {r['years']}y" if r else "-"
        print(f"  {s:8} AD400: {f(ad):14} NORMAL400: {f(nm):14}")
    print(f"\nSITES {len(sites)} | AD400 DONE {cnt['AD400 DONE']} | NORMAL400 DONE {cnt['NORMAL400 DONE']}"
          " | quick scan only; use the cohort audit actions before plotting or the next stage")


if __name__ == "__main__":
    main()
