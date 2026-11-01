#!/usr/bin/env python3
"""Stage58: READ-ONLY source-level forensic checks for Stage57 flagged boundaries.

At flagged intervals compare original Stage23 and detached candidate NetCDF
against the native FLUXMET tower TA/VPD/QC and ERA5 companion TA/VPD at exact
local half-hour timestamps. Include cross-year 2004->2005 boundary for CA-Man.
NEVER infer a tower repair from an independent station without checking
representativeness. This script writes NOTHING and submits no Slurm jobs.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path

from netCDF4 import Dataset

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5")
HOME=Path("/iridisfs/home/ly3n24/CLM_FATES_PLOTS")
# Stage57 flagged contiguous intervals, not a list of all outstanding events.
FOCUS={
    ("CA-Cbo",2018):[(9546,9547)],
    ("CA-Man",1994):[(4792,4792)],
    ("CA-Man",2005):[(0,44)],
    ("US-Aud",2012):[(11500,11500)],
    ("US-Aud",2019):[(4507,4509)],
    ("US-Aud",2023):[(5757,5759),(16898,16900)],
}
MET_COLS=("TA_USE","VPD_USE","PSRF")
TOWER_COLS=("TA_F","TA_F_QC","VPD_F","VPD_F_QC")
ERA_COLS=("TA_ERA","VPD_ERA")


def check(cond, why):
    if not cond: raise ValueError(why)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for buf in iter(lambda:stream.read(1024*1024),b""): h.update(buf)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).resolve(strict=True).read_text())


def load_helper(path):
    p=Path(path).resolve(strict=True)
    spec=importlib.util.spec_from_file_location("stage58_context29",p)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def select_candidates(args):
    first,joint,merged=[read_json(p) for p in (args.approved,args.joint,args.merged)]
    for label,obj in (("43",first),("51",joint),("54",merged)):
        check(obj.get("status")=="DETACHED_NOT_USED_BY_CASES","Stage"+label+" not detached")
    check(sha(args.approved)==merged["prior_report_sha256"],"Stage54 lineage to Stage43 changed")
    check(sha(args.joint)==merged["CA_Cbo_joint_report_sha256"],"Stage54 lineage to Stage51 changed")
    link=Path(joint["linked_CA_Man_2007_13_14_manifest"]).resolve(strict=True)
    check(sha(link)==joint["linked_CA_Man_2007_13_14_manifest_sha256"],"CA-Man linked 2007 manifest changed")
    old={(s["site"],int(f["year"])):f for s in first["sites"] for f in s["files"]}
    second={(f["site"],int(f["year"])):f for f in joint["files"]}
    third={(f["site"],int(f["year"])):f for f in merged["files"]}
    return {("CA-Cbo",2018):third[("CA-Cbo",2018)],
            ("CA-Man",1994):old[("CA-Man",1994)],
            ("CA-Man",2005):second[("CA-Man",2005)],
            ("US-Aud",2012):old[("US-Aud",2012)],
            ("US-Aud",2019):third[("US-Aud",2019)],
            ("US-Aud",2023):third[("US-Aud",2023)]}


def selected_indices(start,end):
    if end-start<8: return list(range(start-3,end+4))
    # Show both sides of the 45-HH CA-Man QC0 replacement plus a central sample.
    middle=(start+end)//2
    return sorted(set(range(start-3,start+4))|
                  set(range(middle-1,middle+2))|
                  set(range(end-3,end+4)))


def label_index(index,year):
    if index<0: return year-1,index+17520
    if index>=17520: return year+1,index-17520
    return year,index


def fmt(row,col):
    if row is None:return "MISSING"
    value=row.get(col,"")
    if value is None or value=="":return "NA"
    try:return f"{float(value):.3f}"
    except (ValueError,TypeError):return str(value)


def from_nc(ds,i):
    import math
    t=float(ds["TBOT"][i,0,0])-273.15
    q=float(ds["QBOT"][i,0,0])
    p=float(ds["PSRF"][i,0,0])/100.
    es=6.112*math.exp(17.67*t/(t+243.5))
    e=q*p/(.622+.378*q)
    return t,es-e


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--context-helper",required=True,type=Path)
    ap.add_argument("--run",type=Path,default=ROOT)
    ap.add_argument("--approved",type=Path,default=HOME/"approved_met_candidates.TVqWqlLi/result/manifest.json")
    ap.add_argument("--joint",type=Path,default=HOME/"approved_cbo_caman.b5Ve5c8S/result/manifest.json")
    ap.add_argument("--merged",type=Path,default=HOME/"approved_q1_cbo.QeDyqeSz/result/manifest.json")
    args=ap.parse_args()
    if args.self_test:
        check(selected_indices(4,4)==list(range(1,8)),"Short-window indexing")
        y,i=label_index(-1,2005); check((y,i)==(2004,17519),"Cross-year index")
        check(label_index(17520,2023)==(2024,0),"Forward cross-year index")
        print("STAGE58 SELF-TEST PASS | time/index mapping; NO WRITES")
        return
    h=load_helper(args.context_helper)
    root=args.run.resolve(strict=True)
    selected=select_candidates(args)
    receipts={r["site"]:r for r in read_json(root/"COMPLETE.json")["sites"]}
    manifests={}
    for site in ("CA-Cbo","CA-Man","US-Aud"):
        rec=receipts[site]
        mp=Path(rec["manifest"]).resolve(strict=True)
        check(root in mp.parents and sha(mp)==rec["sha256"],site+": Stage23 checksum failure")
        manifests[site]={int(v["year"]):v for v in read_json(mp)["annual_files"]}
    with h.STAGE80.open(encoding="utf-8-sig",newline="") as f:
        selected_tsv={r["site"]:r for r in csv.DictReader(f,delimiter="\t")}
    total_events=0
    for site in ("CA-Cbo","CA-Man","US-Aud"):
        item=selected_tsv[site]
        station_selected=Path(item["selected_source"]).resolve(strict=True)
        check(sha(station_selected)==item["selected_sha256"],site+": Stage80 selected SHA mismatch")
        tower,twsrc=h.sources(site,"FLUXMET_HH")
        era,ersrc=h.sources(site,"ERA5_HH")
        check(tower is not None and era is not None,site+": source ambiguous/missing "+str((twsrc,ersrc)))
        print("STAGE58 SOURCE",site,"TOWER",twsrc,"ERA",ersrc,flush=True)
        blocks=[]
        for (s,year),intervals in FOCUS.items():
            if s!=site:continue
            f=selected[(site,year)]
            original=Path(f.get("original",f.get("source"))).resolve(strict=True)
            candidate=Path(f["candidate"]).resolve(strict=True)
            rec=manifests[site][year]
            check(original==Path(rec["path"]).resolve(strict=True) and
                  rec["sha256"]==f.get("original_sha256",f.get("source_sha256")) and
                  sha(original)==rec["sha256"],site+" original annual SHA mismatch")
            check(sha(candidate)==f["candidate_sha256"],site+" candidate SHA mismatch")
            edits={int(x["UTC_index"]):x for x in f["changes"]}
            for start,end in intervals:
                check(all(i in edits for i in range(start,end+1)),
                      site+f" {year}: expected flagged edits absent")
                anchor=edits[start]
                start_local=datetime.fromisoformat(anchor["time_local"])
                display=[]
                for idx in selected_indices(start,end):
                    local=(start_local+timedelta(minutes=30*(idx-start))).strftime("%Y-%m-%d %H:%M:%S")
                    y,ii=label_index(idx,year)
                    display.append((idx,y,ii,local))
                blocks.append((year,start,end,original,candidate,edits,display))
        wanted=set(local for _,_,_,_,_,_,rows in blocks for _,_,_,local in rows)
        station=h.read_subset(station_selected,"time",wanted,MET_COLS)
        tower_rows=h.read_subset(tower,"TIMESTAMP_START",wanted,TOWER_COLS,True)
        era_rows=h.read_subset(era,"TIMESTAMP_START",wanted,ERA_COLS,True)
        for year,start,end,source,candidate,edits,display in blocks:
            total_events+=1
            qc_count=Counter(str(c.get("original_TA_QC","NA")) for i,c in edits.items() if start<=i<=end)
            print("STAGE58 EPISODE",site,year,"indices",start,end,
                  "half_hours",end-start+1,"QC_in_manifest",dict(qc_count),
                  "source_tower_and_ERA_are_comparisons_not_automatic_replacements",flush=True)
            with ExitStack() as stack:
                old=stack.enter_context(Dataset(str(source)))
                new=stack.enter_context(Dataset(str(candidate)))
                other={}
                for idx,y,i,local in display:
                    if y==year:
                        a=from_nc(old,i);b=from_nc(new,i)
                    else:
                        if y not in manifests[site]:
                            print("STAGE58 CROSS_YEAR_HOLD",site,year,local,y,"SOURCE_YEAR_ABSENT",flush=True)
                            continue
                        orig_other=Path(manifests[site][y]["path"]).resolve(strict=True)
                        check(sha(orig_other)==manifests[site][y]["sha256"],
                              site+": cross-year original SHA mismatch")
                        if y not in other:other[y]=stack.enter_context(Dataset(str(orig_other)))
                        a=from_nc(other[y],i);b=a
                    row=tower_rows.get(local);er=era_rows.get(local);chosen=station.get(local)
                    tag="EDIT" if idx in edits else "CONTEXT"
                    print("STAGE58 ROW",site,year,tag,local,
                          "UTC_file",y,"idx",i,
                          "towerT",fmt(row,"TA_F"),"towerTQC",fmt(row,"TA_F_QC"),
                          "towerV",fmt(row,"VPD_F"),"towerVQC",fmt(row,"VPD_F_QC"),
                          "ERA_T",fmt(er,"TA_ERA"),"ERA_V",fmt(er,"VPD_ERA"),
                          "selectedT",fmt(chosen,"TA_USE"),"selectedV",fmt(chosen,"VPD_USE"),
                          "NC_original_T",round(a[0],3),"NC_candidate_T",round(b[0],3),
                          "NC_original_VPD",round(a[1],3),"NC_candidate_VPD",round(b[1],3),
                          flush=True)
            print("STAGE58 EPISODE END",site,year,start,end,flush=True)
    print("STAGE58 COMPLETE | flagged episodes",total_events,
          "| no automated science clearance; no original/candidate/case writes; NO SLURM",flush=True)


if __name__=="__main__":
    main()
