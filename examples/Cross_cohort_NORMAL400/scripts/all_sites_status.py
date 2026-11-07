#!/usr/bin/env python3
"""READ ONLY. Every AmeriFlux / ICOS site of the cross-cohort experiment: which AD400 + Normal400 pair is the
production run now, and whether it is finished.

Production pair per site (script 22 classification, plus the cases made outside it):
  RESTART_NLF   <AD>_NLFP  -> <Normal>_NLFP      (needleleaf F + phenology patch, script 22)
  RERUN_PHEN    <AD>_PHEN  -> <Normal>_PHEN      (phenology patch, script 22)
  RESTART_AD    GL-ZaH _PHEN AD -> its Normal    (script 22)
  KEEP_NLF      <AD>_NLF   -> <Normal>_NLF       (needleleaf F, script 20 / 20b)
  UNCHANGED     original AD -> original Normal   (no fix applies; the first runs stand)
  HINONE        US-Aud _HINONE pair              (script 21)
  BATCH04       DE-Gri, DE-RuR, IT-Tor, ES-Agu, CH-Aws (_HINONE): AD -> _NORMAL400 (script 23)
  EXCLUDED      US-CMW (groundwater site; listed, not counted as missing)
Finished = the latest archived restart is at RUN_STARTDATE + 400 years and nothing of the case is queued.

  cd $HOME/CLM_FATES_PLOTS/diag_rerun_tool     (needs 22 -> 20/21/17/18/13/09 in the same folder)
  python -B all_sites_status.py               one line per site + summary by network and status
  python -B all_sites_status.py --csv FILE    also write the table
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
YEARS = 400
BATCH04 = ["DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT", "DE-RuR_ICOS_B04_FIXNC_AD400_DIRECT",
           "IT-Tor_ICOS_B04_FIXNC_AD400_DIRECT", "ES-Agu_ICOS_B04_FIXNC_AD400_DIRECT",
           "CH-Aws_ICOS_B04_FIXNC_AD400_DIRECT_HINONE"]
HINONE = {"US-Aud": ("US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT_HINONE", "US-Aud_AMF_B01SIX_FIXNC_NORMAL400_DIRECT_HINONE")}
M22 = R = None
QUEUE = {}


def load():
    global M22, R
    spec = importlib.util.spec_from_file_location("roll22", HERE / "22_phenology_patch_rollout.py")
    M22 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M22)
    M22.load()
    R = M22.R


def read_queue():
    out = subprocess.run(["squeue", "-u", R.USER, "-h", "-o", "%j|%T|%r"], capture_output=True, text=True,
                         timeout=60).stdout
    q = {}
    for ln in out.splitlines():
        if ln.count("|") == 2:
            job, st, reason = ln.split("|")
            q.setdefault(job.split(".", 1)[-1], []).append(
                (job.split(".", 1)[0], "DEAD" if reason == "DependencyNeverSatisfied" else st))
    return q


def progress(case):
    """(years done, target end year, latest restart year) from the archived restart folders."""
    d = R.CASES / case
    if not d.is_dir():
        return None, None, None
    try:
        start = int(R.xq(d, "RUN_STARTDATE")[:4])
        arch = Path(R.xq(d, "DOUT_S_ROOT"))
    except Exception:
        return None, None, None
    years = [int(m.group(1)) for p in (arch / "rest").glob("*") if (m := re.match(r"(\d{4})-01-01", p.name))]
    last = max(years) if years else None
    return (last - start if last else 0), start + YEARS, last


def state(case, years):
    q = QUEUE.get(case, [])
    if any(s == "DEAD" for _, s in q):
        return "DEAD"
    if any(j == "run" and s == "RUNNING" for j, s in q):
        return "RUNNING"
    if any(j == "run" for j, _ in q):
        return "PENDING"
    if q:
        return "ARCHIVING"
    if years is None:
        return "NO_CASE"
    return "DONE" if years >= YEARS else "STALLED"


def network(*names):
    return "AmeriFlux" if any("_AMF_" in (n or "") for n in names) else "ICOS"


def production(site):
    if site in HINONE:
        return "HINONE", *HINONE[site]
    i, act, *_ = M22.classify(site)
    if act == "RESTART_NLF" or act in ("RERUN_PHEN", "RESTART_AD"):
        return act, i["ad"], i["n"]
    if act == "KEEP_NLF":
        return act, i["nlf"], i["n0"] + M22.M20.SUFFIX
    return act, i["ad0"], i["n0"]


def main(argv=None):
    global QUEUE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path)
    a = ap.parse_args(argv)
    load()
    QUEUE = read_queue()
    rows = []
    todo = [(s, None) for s in sorted(M22.SITES) if s not in HINONE] + [(s, None) for s in HINONE] + \
           [(c.split("_")[0], c) for c in BATCH04]
    for site, b04 in todo:
        try:
            if b04:
                act, ad, n = "BATCH04", b04, b04.replace("_AD400", "_NORMAL400", 1)
            else:
                act, ad, n = production(site)
            ya, _, la = progress(ad)
            yn, endn, ln = progress(n)
            sa, sn = state(ad, ya), state(n, yn)
            overall = "EXCLUDED" if act == "EXCLUDED" else (sn if sa == "DONE" else f"AD_{sa}")
            rows.append(dict(Site=site, Network=network(ad, n), Category=act, AD_case=ad, AD_years=ya,
                             AD_status=sa, Normal_case=n, Normal_years=yn, Normal_last_restart=ln,
                             Normal_status=sn, Overall=overall))
        except Exception as exc:
            rows.append(dict(Site=site, Network="?", Category="?", Overall="ERROR",
                             Normal_case=f"{type(exc).__name__}: {str(exc)[:150]}"))
    order = {"DEAD": 0, "STALLED": 1, "AD_DEAD": 0, "AD_STALLED": 1, "ERROR": 0, "NO_CASE": 1, "AD_NO_CASE": 1}
    rows.sort(key=lambda r: (order.get(r["Overall"], 5), r["Network"], r["Site"]))
    print(f"{'SITE':7} {'NET':9} {'CATEGORY':11} {'AD':>7} {'NORMAL':>8} {'STATUS':10} NORMAL CASE")
    for r in rows:
        f = lambda v: "-" if v is None else v
        print(f"{r['Site']:7} {r['Network']:9} {r['Category']:11} {f(r.get('AD_years')):>4}/400 "
              f"{f(r.get('Normal_years')):>4}/400  {r['Overall']:10} {r.get('Normal_case', '')}")
    print("\n== summary (Overall status per network)")
    nets = sorted({r["Network"] for r in rows})
    stats = sorted({r["Overall"] for r in rows})
    print(f"   {'':12}" + "".join(f"{n:>11}" for n in nets) + f"{'total':>8}")
    for s in stats:
        c = [sum(1 for r in rows if r["Network"] == n and r["Overall"] == s) for n in nets]
        print(f"   {s:12}" + "".join(f"{x:>11}" for x in c) + f"{sum(c):>8}")
    print(f"   {'sites':12}" + "".join(f"{sum(1 for r in rows if r['Network'] == n):>11}" for n in nets)
          + f"{len(rows):>8}")
    cats = sorted({r["Category"] for r in rows})
    print("\n== by category: " + ", ".join(
        f"{c} {sum(1 for r in rows if r['Category'] == c and r['Overall'] == 'DONE')}/"
        f"{sum(1 for r in rows if r['Category'] == c)} done" for c in cats))
    bad = [r for r in rows if r["Overall"] not in ("DONE", "EXCLUDED", "RUNNING", "PENDING", "ARCHIVING")]
    if bad:
        print("\n== need attention:")
        for r in bad:
            print(f"   {r['Site']}: {r['Overall']}  AD {r.get('AD_case')} ({r.get('AD_status')}), "
                  f"Normal {r.get('Normal_case')} ({r.get('Normal_status')})")
    if a.csv:
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with a.csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader(); w.writerows(rows)
        print(f"\ntable: {a.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
