#!/usr/bin/env python3
"""READ ONLY: inspect DE-Tha questionable LW_IN_F and VPD_F event neighbourhoods.

Checks exact pinned processed forcing and QC files, prints event-local +/-1h
forcing conditions, and compares derived vapor-pressure deficit from
QBOT/PSRF/TBOT with VPD_USE (assuming conventional units).
Does not infer meteorological correctness from gross bounds or QC0 alone.
NO NetCDF modifications, NO CIME/Slurm activity, NO QC acceptance/rejection.

Review triggers are heuristic only, NOT validated quality thresholds.
"""
from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/DE-Tha/forcing")
DATA = ROOT / "processed_v5/DE-Tha_CLM_forcing_1996_2025.csv"
QC = ROOT / "qc_v5"
SHA = {
    DATA: "ed347a37dbd64c19420bb96a0738bc3d579c4717f6149591fc8ee2218f69cf43",
    QC/"DE-Tha_manual_review.csv": "d12acedd004b306f5d2fefe9f56d3842e5bf3a28bb8914df3433888593fe4306",
    QC/"DE-Tha_replacement_events.csv": "374034c66d7f551f99ae7e54d266dd5fed45bd206d72cf21a391a4fcf8676720",
}
V2 = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/DE-Tha/surface/surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_SoilField17_71_12_v2.nc")
V2_SHA = "0d3d827cc4bbfab277d629fafc33ee26933404a84b56ba1bfcac8b3e6cd5e60a"

def fatal(message):
    raise RuntimeError(str(message))

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def pinned_file(p, expected):
    if not p.is_file() or p.is_symlink():
        fatal("Pinned input missing or symlink: "+str(p))
    found=sha256(p)
    if found!=expected:
        fatal("Unexpected input checksum: "+str(p)+" expected="+expected+" found="+found)
    print("PASS pinned file:",p.name,found,flush=True)

def read_qc(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames:
            fatal("QC empty header: "+str(path))
        return list(reader)

def number(row,key):
    try:
        x=float(row.get(key,""))
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None

def time_of(raw):
    return datetime.fromisoformat(raw.replace("T"," "))

def vapor_check(row):
    # CLM forcing conventions: TBOT Kelvin, QBOT kg/kg, PSRF Pa;
    # VPD_USE from pipeline hPa. Water saturation formula is a
    # diagnostic approximation; below 0C an ice convention differs.
    t=number(row,"TBOT")
    q=number(row,"QBOT")
    p=number(row,"PSRF")
    use=number(row,"VPD_USE")
    if t is None or q is None or p is None or use is None or not (
            150<t<350 and 0<=q<0.1 and 25000<p<115000):
        return None
    tc=t-273.15
    es=6.112*math.exp(17.67*tc/(tc+243.5))
    vapor_pa=q*p/(0.622+0.378*q)
    e=vapor_pa/100.
    rh=100*e/es
    diag=es-e
    return dict(saturation_hpa=es,relative_humidity_pct=rh,
                vpd_from_q_hpa=diag,vpd_use_hpa=use,
                discrepancy_hpa=use-diag)

def find_selected_rows(targets):
    wanted={t+timedelta(minutes=30*k) for t in targets for k in range(-2,3)}
    found={}
    with DATA.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        required={"time","TBOT","QBOT","PSRF","FLDS","TA_USE","VPD_USE"}
        if not required.issubset(set(reader.fieldnames or ())):
            fatal("Missing required processed forcing fields")
        for row in reader:
            t=time_of(row["time"])
            if t in wanted:
                if t in found:
                    fatal("Duplicate forcing timestamp: "+str(t))
                found[t]=row
    missing=set(targets)-set(found)
    if missing:
        fatal("Missing QC event timestamps in processed forcing: "+str(sorted(missing)))
    return found

def short(x,n=2):
    return "-" if x is None else f"{x:.{n}f}"

def main():
    print("=== DE-Tha CRITICAL QC EPISODES / STRICT READ ONLY ===",flush=True)
    for p,d in SHA.items():
        pinned_file(p,d)
    pinned_file(V2,V2_SHA)
    manual=read_qc(QC/"DE-Tha_manual_review.csv")
    replaced=read_qc(QC/"DE-Tha_replacement_events.csv")
    if len(manual)!=14 or len(replaced)!=32:
        fatal("Unexpected QC event counts")
    events=defaultdict(list)
    for kind,rows in (("MANUAL",manual),("REPLACED",replaced)):
        for row in rows:
            if row.get("variable") not in ("VPD_F","LW_IN_F"):
                fatal("Unexpected QC variable: "+str(row.get("variable")))
            t=time_of(row["time"])
            events[t].append((kind,row))
    print("QC source entries: 14 manual, 32 replacements, unique timestamps:",len(events))
    found=find_selected_rows(set(events))
    flags=Counter()
    print("NOTE units: TBOT K; QBOT kg/kg; PSRF Pa; VPD_USE hPa; FLDS W/m2.")
    print("Approximate water-saturation VPD diagnostic is NOT independent field QC.")
    for t in sorted(events):
        this=found[t]
        print("\n=== EVENT",t.isoformat(sep=" "),"===")
        for kind,row in events[t]:
            print(kind,"variable=",row["variable"],"source_QC=",row.get("official_qc",""),
                  "original=",row.get("original_value",""),
                  "final=",row.get("final_value",""),
                  "ERA=",row.get("era_reference",row.get("era_value","")),
                  "reason=",row.get("reason",""))
            if kind=="REPLACED":
                key="VPD_USE" if row["variable"]=="VPD_F" else "FLDS"
                actual=number(this,key)
                ledger=number(row,"final_value")
                if actual is None or ledger is None or abs(actual-ledger)>0.051:
                    flags["LEDGER_FORCING_MISMATCH"]+=1
                    print("  ATTENTION: replacement ledger != processed CSV:",key,actual,ledger)
        print("NEIGHBOURHOOD (-60 through +60 minutes)")
        print("   clock    TBOT_C  TA_USE_C    FLDS    VPD_USE   VPD(QBOT)  RH(QBOT)    deltaVPD")
        for k in range(-2,3):
            tk=t+timedelta(minutes=30*k)
            if tk not in found:
                print(tk.strftime("%H:%M"),"NOT_FOUND")
                continue
            row=found[tk]
            tb=number(row,"TBOT")
            tc=tb-273.15 if tb is not None else None
            lw=number(row,"FLDS")
            use=number(row,"VPD_USE")
            d=vapor_check(row)
            print("   ",tk.strftime("%H:%M"),short(tc),short(number(row,"TA_USE")),
                  short(lw),short(use),short(d["vpd_from_q_hpa"] if d else None),
                  short(d["relative_humidity_pct"] if d else None),
                  short(d["discrepancy_hpa"] if d else None))
        lw=number(this,"FLDS")
        diag=vapor_check(this)
        if lw is not None and lw<120:
            flags["LW_BELOW_120_WM2_SITE_REVIEW"]+=1
            print("  REVIEW: unusually low LW for site context; not automatically invalid")
        if diag:
            # T-dependent saturation diagnostic: flags are heuristic, no auto-repair.
            if diag["vpd_use_hpa"]>diag["saturation_hpa"]+0.5:
                flags["VPD_EXCEEDS_SATURATION_AT_TBOT"]+=1
            if diag["relative_humidity_pct"] < -0.5 or diag["relative_humidity_pct"]>105:
                flags["QBOT_IMPLIED_RH_OUTSIDE_LOOSE_RANGE"]+=1
            if abs(diag["discrepancy_hpa"])>max(1.,0.2*diag["saturation_hpa"]):
                flags["VPD_USE_VS_QBOT_DIFFERENCE"]+=1
            if abs(number(this,"TA_USE")-(number(this,"TBOT")-273.15))>1.5:
                flags["TA_USE_VS_TBOT_DIFFERENCE"]+=1
    print("\n=== SCIENTIFIC TRIAGE SUMMARY ===")
    print("UNIQUE QC EVENT TIMES:",len(events))
    print("FLAG COUNTS (event-based, heuristic):",dict(sorted(flags.items())))
    print("Do not infer valid/invalid from ERA discrepancy alone.")
    print("Required manual review: 2005 low LW/QC0 measured source, 2017")
    print("VPD interpolation and 2022 VPD reconstructed from ERA RH at site T.")
    print("Keep forcing status REVIEW and do not auto-repair these records.")
    print("READ ONLY COMPLETE: v2 surface, forcing, NetCDF, cases and Slurm unchanged")

if __name__=="__main__":
    main()
