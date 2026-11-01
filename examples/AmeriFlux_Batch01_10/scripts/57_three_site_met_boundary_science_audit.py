#!/usr/bin/env python3
"""Stage57: READ-ONLY physical and boundary-continuity diagnostics for Batch01.

After Stage56 verified seven canonical candidate years (64 edits), compare
original and candidate temperature, VPD and specific humidity around EACH
contiguous edited period. Preserve original QC flags, never infer that an
ERA/NOAA proxy is the true tower meteorology. No write, no case, no Slurm.

These are diagnostic thresholds, not automated acceptance criteria.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

HOME = Path("/iridisfs/home/ly3n24/CLM_FATES_PLOTS")
ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5")
YEARS = {
    ("CA-Cbo", 2018): 5,
    ("CA-Man", 1994): 1, ("CA-Man", 2005): 45, ("CA-Man", 2007): 3,
    ("US-Aud", 2012): 1, ("US-Aud", 2019): 3, ("US-Aud", 2023): 6,
}
T_LIMIT = 4.0
V_LIMIT = 4.0
REPLACEMENT_LIMIT = 5.0


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def doc(path):
    return json.loads(Path(path).resolve(strict=True).read_text())


def candidates(args):
    old, joint, merged = doc(args.approved), doc(args.joint), doc(args.merged)
    for label, o in (("Stage43",old),("Stage51",joint),("Stage54",merged)):
        require(o.get("status") == "DETACHED_NOT_USED_BY_CASES", label+" is not detached")
    require(digest(args.approved)==merged["prior_report_sha256"], "Stage54 prior SHA mismatch")
    require(digest(args.joint)==merged["CA_Cbo_joint_report_sha256"], "Stage54 joint SHA mismatch")
    man2007=Path(joint["linked_CA_Man_2007_13_14_manifest"]).resolve(strict=True)
    require(digest(man2007)==joint["linked_CA_Man_2007_13_14_manifest_sha256"], "CA-Man 2007 linked SHA mismatch")
    linked=doc(man2007)
    byfirst={(s["site"],int(f["year"])):f for s in old["sites"] for f in s["files"]}
    byjoint={(f["site"],int(f["year"])):f for f in joint["files"]}
    bymerged={(f["site"],int(f["year"])):f for f in merged["files"]}
    require(set(byfirst)|set(byjoint)|set(bymerged)|{("CA-Man",2007)}==set(YEARS),
            "Unexpected site/year candidate coverage")
    return {
        ("CA-Cbo",2018):bymerged[("CA-Cbo",2018)],
        ("CA-Man",1994):byfirst[("CA-Man",1994)],
        ("CA-Man",2005):byjoint[("CA-Man",2005)],
        ("CA-Man",2007):linked,
        ("US-Aud",2012):byfirst[("US-Aud",2012)],
        ("US-Aud",2019):bymerged[("US-Aud",2019)],
        ("US-Aud",2023):bymerged[("US-Aud",2023)],
    }


def groups(indices):
    runs=[]
    for i in sorted(indices):
        if not runs or i > runs[-1][-1]+1:
            runs.append([i])
        else:
            runs[-1].append(i)
    return runs


def met(ds, i):
    t=float(ds.variables["TBOT"][i,0,0])-273.15
    q=float(ds.variables["QBOT"][i,0,0])
    p=float(ds.variables["PSRF"][i,0,0])/100.
    require(math.isfinite(t) and math.isfinite(q) and math.isfinite(p)
            and 490<p<1110 and -90<t<65 and 0<q<.08,
            f"Nonphysical forcing at index {i}")
    es=6.112*math.exp(17.67*t/(t+243.5))
    e=q*p/(.622+.378*q)
    vpd=es-e
    rh=100*e/es
    return t,vpd,q,rh


def sci(site,year,f,expected_file):
    source=Path(f.get("original",f.get("source"))).resolve(strict=True)
    target=Path(f["candidate"]).resolve(strict=True)
    source_sha=f.get("original_sha256",f.get("source_sha256"))
    require(source==Path(expected_file["path"]).resolve(strict=True),site+" original does not match Stage23")
    require(source_sha==expected_file["sha256"] and digest(source)==source_sha,site+" original SHA changed")
    require(digest(target)==f["candidate_sha256"],site+" candidate SHA changed")
    changes=f["changes"]
    idxs={int(c["UTC_index"]):c for c in changes}
    require(len(changes)==len(idxs)==YEARS[(site,year)],site+" duplicated/missing edits")
    risk=0
    with Dataset(str(source)) as original,Dataset(str(target)) as candidate:
        for c in changes:
            i=int(c["UTC_index"])
            a,b=met(original,i),met(candidate,i)
            if abs(b[0]-float(c["candidate_TA_C"]))>.001 or abs(b[1]-float(c["candidate_VPD_hPa"]))>.01:
                raise ValueError(f"{site} {year} {i}: candidate T or VPD inconsistent with manifest")
            delta_t=b[0]-a[0]; delta_v=b[1]-a[1]
            qc=c.get("original_TA_QC","?")
            flags=[]
            if abs(delta_t)>REPLACEMENT_LIMIT: flags.append("T_REPLACEMENT_GT5")
            if qc!="?" and float(qc)==0: flags.append("ORIGINAL_TA_QC0")
            if b[1]<-0.02 or b[3]>100.1 or b[3]<0: flags.append("NONPHYSICAL_HUMIDITY")
            if flags: risk+=1
            print("STAGE57 EDIT",site,year,"idx",i,"local",c.get("time_local","?"),
                  "TA_QC",qc,"T_orig",round(a[0],3),"T_new",round(b[0],3),
                  "dT",round(delta_t,3),"VPD_orig",round(a[1],3),
                  "VPD_new",round(b[1],3),"dVPD",round(delta_v,3),
                  "RH_new",round(b[3],3),"flags",",".join(flags) or "-",flush=True)
        for block in groups(idxs):
            left,right=block[0],block[-1]
            pair_ranges=((left-1,left),(right,right+1))
            pairs=[(i,j) for i,j in pair_ranges if 0<=i<17520 and 0<=j<17520]
            def jumps(ds):
                values=[]
                for i,j in pairs:
                    a,b=met(ds,i),met(ds,j)
                    values.append((round(b[0]-a[0],3),round(b[1]-a[1],3)))
                return values
            oldj,newj=jumps(original),jumps(candidate)
            flags=[]
            for (dt,dv) in newj:
                if abs(dt)>T_LIMIT: flags.append("BOUNDARY_T_GT4")
                if abs(dv)>V_LIMIT: flags.append("BOUNDARY_VPD_GT4")
            if left==0 or right==17519: flags.append("ANNUAL_EDGE_UNCHECKED")
            print("STAGE57 BOUNDARY",site,year,"UTC_indices",left,right,
                  "HH",len(block),"orig_dT_dVPD",oldj,
                  "candidate_dT_dVPD",newj,"flags",",".join(sorted(set(flags))) or "-",flush=True)
            risk+=len(set(flags))
    return risk


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run",type=Path,default=ROOT)
    ap.add_argument("--approved",type=Path,default=HOME/"approved_met_candidates.TVqWqlLi/result/manifest.json")
    ap.add_argument("--joint",type=Path,default=HOME/"approved_cbo_caman.b5Ve5c8S/result/manifest.json")
    ap.add_argument("--merged",type=Path,default=HOME/"approved_q1_cbo.QeDyqeSz/result/manifest.json")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        require(groups([0,1,3,4,7])==[[0,1],[3,4],[7]],"Contiguous-run segmentation failed")
        print("STAGE57 SELF-TEST PASS | no filesystem/model/slurm edits")
        return
    root=a.run.resolve(strict=True)
    receipt=doc(root/"COMPLETE.json")
    records={r["site"]:r for r in receipt["sites"]}
    source={}
    for site in ("CA-Cbo","CA-Man","US-Aud"):
        man=Path(records[site]["manifest"]).resolve(strict=True)
        require(root in man.parents and digest(man)==records[site]["sha256"],site+" Stage23 source SHA")
        source[site]={int(x["year"]):x for x in doc(man)["annual_files"]}
    bykey=candidates(a)
    risk=0
    for (site,year),candidate in sorted(bykey.items()):
        print("STAGE57 YEAR",site,year,"approved_half_hours",len(candidate["changes"]),flush=True)
        risk+=sci(site,year,candidate,source[site][year])
    print("STAGE57 DIAGNOSTIC COMPLETE | 7 yearly candidates, 64 edits | flagged counts are NOT unique HH:",risk,flush=True)
    print("SCIENCE HOLD | CA-Man 2005: 45 original temperature QC0, ERA replacement has not been cleared for production",flush=True)
    print("SCIENCE HOLD | NOAA external representativeness, all remaining Met events and year-edge continuity need separate review",flush=True)
    print("READ ONLY | no original/candidate/model case modified; no Slurm job submitted",flush=True)


if __name__=="__main__":
    main()
