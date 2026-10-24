#!/usr/bin/env python3
"""STRICT READ ONLY: DE-Tha v5 forcing 14 manual-review + 32 replacements triage.

No file writes, no netCDF modifications, no CIME setup, no Slurm submission.
Print every review/replacement row with source/QC context; check metadata,
time continuity (NO_LEAP calendar), basic physical sanity and missing values.

An existing status='REVIEW' is *not* treated as a PASS or implicitly cleared.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/DE-Tha/forcing")
QC=ROOT/"qc_v5"
FORCING=ROOT/"processed_v5/DE-Tha_CLM_forcing_1996_2025.csv"
SOURCE={
 "DE-Tha_status.json":"431d87d68494c2fdfe741d8f620e3b8cfd9d196c17089037367579bdf83bb184",
 "DE-Tha_manual_review.csv":"d12acedd004b306f5d2fefe9f56d3842e5bf3a28bb8914df3433888593fe4306",
 "DE-Tha_replacement_events.csv":"374034c66d7f551f99ae7e54d266dd5fed45bd206d72cf21a391a4fcf8676720",
 "DE-Tha_qc_summary.csv":"edf20c0cfc20e816320311738d7781e1ffb2ecace5224b398394130c32768478",
}
REQUIRED=["time","TBOT","QBOT","PSRF","FSDS","FLDS","WIND","PRECTmms","TA_USE","VPD_USE"]
N=30*365*48

def fail(m):
    raise RuntimeError(m)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda:fp.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def csv_load(path):
    with path.open(newline="",encoding="utf-8-sig") as fp:
        reader=csv.DictReader(fp)
        if not reader.fieldnames:
            fail("Empty/broken header: "+str(path))
        return list(reader)

def qc_check():
    print("\n========== VERIFIED EXISTING QC RECEIPTS ==========")
    for filename,expected in SOURCE.items():
        f=QC/filename
        if not f.is_file() or f.is_symlink() or sha(f)!=expected:
            fail("QC receipt changed or absent; manual re-audit needed: "+str(f))
        print("PASS",filename,"SHA256",expected)
    j=json.loads((QC/"DE-Tha_status.json").read_text(encoding="utf-8-sig"))
    manual=csv_load(QC/"DE-Tha_manual_review.csv")
    events=csv_load(QC/"DE-Tha_replacement_events.csv")
    summary=csv_load(QC/"DE-Tha_qc_summary.csv")
    if j.get("status")!="REVIEW" or len(manual)!=14 or len(events)!=32 or len(summary)!=7:
        fail("Recorded status/row counts changed; inspect raw QC before proceeding")
    if j.get("manual_review_records")!=14 or j.get("changes")!=32:
        fail("QC status summary and event counts disagree")
    print("QC JSON status: REVIEW, manual reviews:",len(manual),
          "replacement events:",len(events))
    print("\n========== 7 VARIABLES: EXISTING QC SUMMARY ==========")
    for row in summary:
        print(" ".join(f"{k}={str(v)!r}" for k,v in row.items()))
    print("\n========== ALL 14 MANUAL REVIEW EVENTS ==========")
    for i,rec in enumerate(manual,1):
        print(f"{i:02d} "+ " | ".join(f"{k}={v}" for k,v in rec.items()))
    print("\n========== ALL 32 REPLACEMENT EVENTS ==========")
    for i,rec in enumerate(events,1):
        print(f"{i:02d} "+ " | ".join(f"{k}={v}" for k,v in rec.items()))
    for name,rows in (("MANUAL",manual),("REPLACEMENT",events)):
        print("\n"+name+" BY VARIABLE:",dict(sorted(Counter(r.get("variable","") for r in rows).items())))
        print(name+" BY REASON:",dict(sorted(Counter(r.get("reason","") for r in rows).items())))
    return j,manual,events

def noleap_gaps():
    if not FORCING.is_file():
        fail("Processed forcing CSV missing "+str(FORCING))
    print("\n========== PHYSICAL/TIMESTAMP QC OF PROCESSED FILE ==========")
    print("FORCING",FORCING,"bytes",FORCING.stat().st_size,"SHA256",sha(FORCING))
    issues=Counter()
    examples={}
    bounds={
     # Wide gross plausibility limits only. NOT proof of meteorological quality.
     "TBOT":(150.,370.),    # Kelvin
     "QBOT":(0.,0.1),       # kg/kg
     "PSRF":(25000.,115000.), # Pa
     "FSDS":(-1.,1800.),    # W/m2 (small negative possible after processing)
     "FLDS":(0.,1000.),     # W/m2
     "WIND":(0.,100.),      # m/s
     "PRECTmms":(0.,0.1),  # mm/s; very loose
     "TA_USE":(-120.,100.), # typically C; here wide flag only
     "VPD_USE":(-0.01,150.), # hPa; allow very small rounding negative
    }
    rows=0
    prev=None
    first=last=None
    seen_years=Counter()
    with FORCING.open(newline="",encoding="utf-8-sig") as fp:
        reader=csv.DictReader(fp)
        fields=reader.fieldnames or []
        if not set(REQUIRED).issubset(fields):
            fail("Required forcing variables absent: "+str(set(REQUIRED)-set(fields)))
        for r in reader:
            rows+=1
            stamp=r["time"].strip()
            try:
                t=datetime.fromisoformat(stamp)
            except ValueError:
                fail(f"Invalid time row {rows}: {stamp}")
            if first is None:first=t
            last=t
            if t.month==2 and t.day==29:
                fail("Unexpected Feb-29 in NO_LEAP series")
            if prev:
                allowed=timedelta(minutes=30)
                if prev.month==2 and prev.day==28 and prev.hour==23 and prev.minute==30 and (
                    prev.year%4==0 and (prev.year%100!=0 or prev.year%400==0)):
                    allowed=timedelta(days=1,minutes=30)
                if t-prev!=allowed:
                    fail(f"Gap/duplicate/out-of-order time: {prev} -> {t}")
            prev=t
            seen_years[t.year]+=1
            for k,(low,high) in bounds.items():
                value=r.get(k,"").strip()
                try:
                    x=float(value)
                except (ValueError,TypeError):
                    x=float("nan")
                if not math.isfinite(x):
                    issue=f"{k}:NONFINITE"
                elif x<low:
                    issue=f"{k}:LOW_GROSS_BOUND"
                elif x>high:
                    issue=f"{k}:HIGH_GROSS_BOUND"
                else:
                    continue
                issues[issue]+=1
                if len(examples.setdefault(issue,[]))<5:
                    examples[issue].append((stamp,value))
    if rows!=N or first!=datetime(1996,1,1,0,0) or last!=datetime(2025,12,31,23,30):
        fail(f"Incorrect 30yr forcing continuity: rows={rows},first={first},last={last}")
    if len(seen_years)!=30 or any(n!=17520 for n in seen_years.values()):
        fail("Not 17520 half-hours in each of 30 noleap years")
    print("PASS: 525600 continuous 30-minute records, no leap days, 1996–2025")
    print("GROSS PHYSICAL FLAGS:",dict(sorted(issues.items())))
    for name,items in sorted(examples.items()):
        print("EXAMPLE",name,items)
    print("NOTE: broad gross physical bounds do not establish scientific accuracy.")
    return issues

def main():
    j,manual,events=qc_check()
    issues=noleap_gaps()
    print("\n========== REVIEW DECISION ==========")
    print("SOURCE QC STATUS:",j["status"],"(preserved, NOT AUTOMATICALLY APPROVED)")
    print("Manual-review timestamps:",len({r.get("time","") for r in manual}))
    print("Replacement timestamps:",len({r.get("time","") for r in events}))
    if issues:
        print("HOLD: gross forcing bounds flagged; inspect examples and provenance")
    else:
        print("PASS: no gross-value outliers under deliberately WIDE sanity bounds")
    print("HOLD: interpret the 14 manual and 32 replacement events before PRE50.")
    print("READ ONLY COMPLETE: no forcing, surface, case or Slurm job modified")

if __name__=="__main__":
    main()
