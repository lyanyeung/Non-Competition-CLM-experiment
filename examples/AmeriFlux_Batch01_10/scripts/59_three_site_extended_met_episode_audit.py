#!/usr/bin/env python3
"""Stage59: read-only expanded-window original tower/ERA context and suspect runs.

Coverage: CA-Cbo 2018, CA-Man 1994 and the 2004/05 QC0 block, US-Aud
2012/2019/2023. Link SHA-pinned Stage43/51/54 candidates, then find clusters
of original tower-minus-ERA differences beyond illustrative thresholds.
No automatic repairs, no forcing/case edits, no Slurm jobs.

CAUTION: ERA5_HH may share gap-fill data provenance with FLUXMET and is not an
independent observation. Difference thresholds are *review markers only*.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5")
HOME=Path("/iridisfs/home/ly3n24/CLM_FATES_PLOTS")
PIN_STAGE58="82b63dbf16665df05060c7ed70ea77023ba2cea5"
WINDOWS={
"CA-Cbo":[("2018-07-18 12:00:00","2018-07-19 00:00:00")],
"CA-Man":[("1994-04-10 09:00:00","1994-04-10 20:00:00"),
          ("2004-12-30 12:00:00","2005-01-02 12:00:00")],
"US-Aud":[("2012-08-28 00:00:00","2012-08-29 12:00:00"),
          ("2019-04-04 08:00:00","2019-04-05 02:00:00"),
          ("2023-04-30 09:00:00","2023-05-01 12:00:00"),
          ("2023-12-18 12:00:00","2023-12-19 18:00:00")]
}
TOWER_COLS=("TA_F","TA_F_QC","VPD_F","VPD_F_QC")
ERA_COLS=("TA_ERA","VPD_ERA")
SELECTED_COLS=("TA_USE","VPD_USE","PSRF")
THRESHOLD_T_C=8.0
THRESHOLD_VPD_HPA=10.0

def check(condition,reason):
    if not condition:raise ValueError(reason)

def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for buf in iter(lambda:f.read(1024*1024),b""):h.update(buf)
    return h.hexdigest()

def load(path,name,blob=None):
    path=Path(path).resolve(strict=True)
    raw=path.read_bytes()
    if blob:check(gitblob(raw)==blob,"Pinned "+name+" module changed")
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def ticks(start,end):
    a,b=datetime.fromisoformat(start),datetime.fromisoformat(end)
    check(b>=a and a.minute in (0,30) and b.minute in (0,30),"Invalid interval")
    count=int((b-a).total_seconds()//1800)+1
    check(count<=200,"Abnormally long window")
    return [(a+timedelta(minutes=30*i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(count)]

def number(row,column):
    try:
        x=float(row[column])
        return x if math.isfinite(x) and x>-9990 else None
    except (TypeError,ValueError,KeyError):return None

def groups_of_flags(times,flags):
    runs=[]
    for time in times:
        if time not in flags:continue
        d=datetime.fromisoformat(time)
        if not runs or d-datetime.fromisoformat(runs[-1][-1])!=timedelta(minutes=30):
            runs.append([time])
        else:runs[-1].append(time)
    return runs

def fmt(value):
    if value is None:return "NA"
    return f"{value:.3f}"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage58",type=Path,required=True)
    p.add_argument("--context-helper",type=Path,required=True)
    p.add_argument("--approved",type=Path,default=HOME/"approved_met_candidates.TVqWqlLi/result/manifest.json")
    p.add_argument("--joint",type=Path,default=HOME/"approved_cbo_caman.b5Ve5c8S/result/manifest.json")
    p.add_argument("--merged",type=Path,default=HOME/"approved_q1_cbo.QeDyqeSz/result/manifest.json")
    a=p.parse_args()
    if a.self_test:
        check(len(ticks("2023-04-30 23:00:00","2023-05-01 01:00:00"))==5,"Clock test")
        check(groups_of_flags(["2023-01-01 00:00:00","2023-01-01 00:30:00","2023-01-01 01:00:00"],
                              {"2023-01-01 00:00:00","2023-01-01 01:00:00"})==
              [["2023-01-01 00:00:00"],["2023-01-01 01:00:00"]],"Segmentation")
        check(gitblob(Path(a.stage58).read_bytes())==PIN_STAGE58,"Stage58 helper integrity")
        print("STAGE59 SELF-TEST PASS | pinned Stage58 and time/group tests; NO WRITES",flush=True)
        return
    s58=load(a.stage58,"s58_59",PIN_STAGE58)
    h=load(a.context_helper,"context29_59")
    # Requires exact validated provenance for all seven canonical candidate years.
    selected_candidates=s58.candidates(a)
    check(len(selected_candidates)==7,"Unexpected Stage58 selected candidate inventory")
    for (site,year),f in selected_candidates.items():
        check(sha256(f["candidate"])==f["candidate_sha256"],
              f"Candidate checksum changed: {site} {year}")
    edits={}
    for (site,year),f in selected_candidates.items():
        edits.setdefault(site,set()).update(c["time_local"] for c in f["changes"])
    with h.STAGE80.open(encoding="utf-8-sig",newline="") as f:
        selected={r["site"]:r for r in csv.DictReader(f,delimiter="\t")}
    episodes=0
    for site,windows in WINDOWS.items():
        rec=selected[site]
        source=Path(rec["selected_source"]).resolve(strict=True)
        check(sha256(source)==rec["selected_sha256"],site+": Stage80 source SHA changed")
        tower,ti=h.sources(site,"FLUXMET_HH")
        era,ei=h.sources(site,"ERA5_HH")
        check(tower is not None and era is not None,
              site+": ambiguous original tower/ERA source "+str((ti,ei)))
        times=sorted({time for start,end in windows for time in ticks(start,end)})
        sr=h.read_subset(source,"time",set(times),SELECTED_COLS)
        tw=h.read_subset(tower,"TIMESTAMP_START",set(times),TOWER_COLS,True)
        er=h.read_subset(era,"TIMESTAMP_START",set(times),ERA_COLS,True)
        print("STAGE59 SOURCE",site,"tower",ti,"ERA",ei,flush=True)
        for start,end in windows:
            episodes+=1
            stamps=ticks(start,end)
            flags=set(); reason={}; counts=Counter()
            for time in stamps:
                t=tw.get(time,{}); e=er.get(time,{})
                ta,vpd=number(t,"TA_F"),number(t,"VPD_F")
                et,ev=number(e,"TA_ERA"),number(e,"VPD_ERA")
                qc=number(t,"TA_F_QC")
                dta=ta-et if ta is not None and et is not None else None
                dv=vpd-ev if vpd is not None and ev is not None else None
                marked=set()
                if dta is not None and abs(dta)>=THRESHOLD_T_C:marked.add("TOWER_ERA_DT_GE8")
                if dv is not None and abs(dv)>=THRESHOLD_VPD_HPA:marked.add("TOWER_ERA_DVPD_GE10")
                if ta==0 and vpd==0:marked.add("T_AND_VPD_ZERO")
                if marked:
                    flags.add(time);reason[time]=marked;counts.update(marked)
                if time in edits[site]:counts["APPROVED_EDIT_IN_WINDOW"]+=1
                if qc==0:counts["ORIGINAL_TA_QC0"]+=1
                if t=={}:counts["TOWER_ROWS_MISSING"]+=1
            print("STAGE59 WINDOW",site,start,"TO",end,"HH",len(stamps),
                  "approved_edit",counts["APPROVED_EDIT_IN_WINDOW"],
                  "threshold_flagged",len(flags),"flags",dict(counts),flush=True)
            clusters=groups_of_flags(stamps,flags)
            for run in clusters:
                n_edits=sum(t in edits[site] for t in run)
                kinds=sorted(set.union(*(reason[t] for t in run)))
                print("STAGE59 SUSPECT_RUN",site,run[0],"TO",run[-1],
                      "HH",len(run),"approved_edits",n_edits,"UNREVIEWED_FLAGGED_HH",len(run)-n_edits,
                      "flags",",".join(kinds),flush=True)
            # Keep output compact: show exact values at each run endpoint,
            # at the three highest temperature outliers, and around edited edges.
            wanted=set()
            for run in clusters:
                aidx=stamps.index(run[0]);bidx=stamps.index(run[-1])
                wanted.update(stamps[max(0,aidx-1):min(len(stamps),aidx+2)])
                wanted.update(stamps[max(0,bidx-1):min(len(stamps),bidx+2)])
            wanted.update(t for t in stamps if t in edits[site] and (t in flags or
                             any(abs((datetime.fromisoformat(t)-datetime.fromisoformat(x)).total_seconds())<=1800
                                 for x in flags)))
            for time in sorted(wanted):
                t,e,sel=tw.get(time,{}),er.get(time,{}),sr.get(time,{})
                ta,vpd=number(t,"TA_F"),number(t,"VPD_F")
                et,ev=number(e,"TA_ERA"),number(e,"VPD_ERA")
                print("STAGE59 SAMPLE",site,time,
                      "edit",int(time in edits[site]),"flag",",".join(sorted(reason.get(time,()))) or "-",
                      "towerT",fmt(ta),"TQC",fmt(number(t,"TA_F_QC")),
                      "towerV",fmt(vpd),"VQC",fmt(number(t,"VPD_F_QC")),
                      "ERA_T",fmt(et),"ERA_V",fmt(ev),
                      "selectedT",fmt(number(sel,"TA_USE")),
                      "selectedV",fmt(number(sel,"VPD_USE")),flush=True)
            print("STAGE59 WINDOW END",site,start,end,"suspect_runs",len(clusters),flush=True)
    print("STAGE59 COMPLETE",episodes,"review windows; all 7 canonical candidate SHAs verified",flush=True)
    print("SCIENCE HOLD | thresholds are exploratory; ERA5_HH is a companion product, not independent tower truth",flush=True)
    print("SCIENCE HOLD | CA-Man QC0 edits and US-Aud adjacent events remain unapproved for production",flush=True)
    print("READ ONLY | no forcing/case/Slurm writes",flush=True)

if __name__=="__main__":
    main()
