#!/usr/bin/env python3
"""DE-Tha strictly READ-ONLY surface, forcing, DATM, FATES PFT-map preflight.

Known source paths come from the 2026-10-24 IRIDIS6 inventory. The source
forest-tree 87/10/1/2 proportions are NOT validated CLM natural PFT area shares.
No model case, netCDF, restart, Slurm or input file is ever changed.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITE = ROOT / "sites/MY_EC_SITE/DE-Tha"
SURF = SITE / "subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc"
CSV = SITE / "forcing/processed_v5/DE-Tha_CLM_forcing_1996_2025.csv"
DATM = SITE / "forcing/datm_v5_candidate_timevarying_zbot"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
CASE = ROOT / "cases/DE-Tha_FATES_SPINUP500"
REV = "d5ea9d0136530370a62ef267ccfaff6f001ef914"
PARAM_HASH = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
MAPPING = {
    1: ("ENF", "needleleaf_evergreen_extratrop_tree"),
    3: ("DNF", "needleleaf_colddecid_extratrop_tree"),
    7: ("DBF", "broadleaf_colddecid_extratrop_tree"),
}

def fail(msg):
    raise RuntimeError(str(msg))

def need(p):
    if not p.is_file():
        fail("Missing site input: " + str(p))
    return p

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def land_value(ds, key, np):
    if key not in ds.variables:
        return "NOT_PRESENT"
    a = np.ma.filled(ds.variables[key][:], np.nan).ravel()
    if not len(a) or not np.isfinite(a).all():
        fail("Invalid "+key)
    if len(a) == 1:
        return float(a[0])
    if key in ("PCT_NATVEG","PCT_CROP"):
        fail("Multiple spatial values: "+key)
    return {"components":[float(x) for x in a],"sum":float(a.sum())}

def surface(np, Dataset):
    print("\n=== 1. ORIGINAL SURFACE (NO WRITES) ===",flush=True)
    need(SURF)
    print("SURFACE:",SURF,"SHA256:",sha(SURF))
    with Dataset(SURF,"r") as ds:
        for key in ("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND",
                    "PCT_GLACIER","PCT_URBAN"):
            print(key,land_value(ds,key,np))
        if "PCT_NAT_PFT" not in ds.variables:
            fail("PCT_NAT_PFT missing")
        v=ds.variables["PCT_NAT_PFT"]
        axes=[i for i,d in enumerate(v.dimensions) if d.lower()=="natpft"]
        if len(axes)!=1 or v.shape[axes[0]]!=15 or any(
                sz!=1 for i,sz in enumerate(v.shape) if i!=axes[0]):
            fail("Unexpected single-point PFT dimensions: "+str(v.dimensions))
        fractions=np.moveaxis(np.ma.filled(v[:],np.nan),axes[0],0).reshape(15)
        if not np.isfinite(fractions).all() or abs(float(fractions.sum())-100)>0.02:
            fail("Original natural PFT fractions invalid")
        print("PCT_NAT_PFT sum:",float(fractions.sum()))
        for i,x in enumerate(fractions):
            if x>0.0001:
                print(f"  CLM natpft[{i:2d}]: {float(x):8.4f}%")
        print("CLM forest PFT positions (not observed shares):",
              {MAPPING[i][0]:round(float(fractions[i]),4) for i in MAPPING})
        print("HOLD: tower composition 87/10/1/2 is not automatically PCT_NAT_PFT")

def fates(np):
    print("\n=== 2. CTSM REVISION / FATES PFT MAP ===",flush=True)
    need(PARAM)
    result=subprocess.run(["git","-C",str(ROOT/"CTSM"),"rev-parse","HEAD"],
                          check=False,capture_output=True,text=True,timeout=20)
    if result.returncode or result.stdout.strip()!=REV:
        fail("CTSM pinned revision differs; inspect before modeling")
    print("PASS CTSM pinned revision:",REV)
    digest=sha(PARAM)
    print("FATES JSON SHA256:",digest)
    if digest!=PARAM_HASH:
        fail("FATES parameter hash differs from pinned reference")
    j=json.loads(PARAM.read_text())["parameters"]
    names=j["fates_pftname"]["data"]
    a=np.asarray(j["fates_hlm_pft_map"]["data"],dtype=float)
    if a.shape!=(14,len(names)):
        fail("Unexpected FATES HLM-to-PFT map dimensions: "+str(a.shape))
    for index,(group,expected) in MAPPING.items():
        row=a[index-1]
        hits=np.flatnonzero(row>0)
        mapping=[(names[int(x)],float(row[int(x)])) for x in hits]
        print("CLM",index,group,"->",mapping)
        if len(mapping)!=1 or mapping[0][0]!=expected or abs(mapping[0][1]-1)>1e-8:
            fail("HLM mapping mismatch for "+group)
    print("PASS: ENF/DNF/DBF mapped to distinct FATES tree PFTs")

def forcing():
    print("\n=== 3. PROCESSED v5 FORCING CSV ===",flush=True)
    need(CSV)
    print("FILE:",CSV,"bytes:",CSV.stat().st_size)
    rows=0
    years=Counter()
    first=last=None
    with CSV.open(newline="",encoding="utf-8-sig") as f:
        rd=csv.DictReader(f)
        if not rd.fieldnames:
            fail("Forcing CSV missing header")
        cols=rd.fieldnames
        print("COLUMNS:",",".join(cols[:45]))
        timecol=next((s for s in ("TIMESTAMP_START","timestamp_start",
                                  "TIMESTAMP","timestamp","datetime","time") if s in cols),None)
        print("TIME FIELD:",timecol or "NOT_RECOGNIZED")
        for row in rd:
            rows+=1
            if rows==1: first=row
            last=row
            if timecol:
                m=re.match(r"^(\d{4})",(row.get(timecol) or "").strip())
                if m: years[int(m.group(1))]+=1
    if not rows: fail("Forcing CSV empty")
    print("ROWS:",rows)
    if timecol:
        print("FIRST/LAST:",first[timecol],last[timecol])
        print("YEAR COUNTS:",dict(sorted(years.items())))
    if rows==30*365*48:
        print("PASS: 525600 rows consistent with 30 no-leap half-hour years")
    else:
        print("HOLD: row count differs from 525600; calendar and missing stamps need QC")
    print("NOTE: counts alone do not validate meteorological physical/QC quality")

def datm(Dataset):
    print("\n=== 4. YEARLY DATM NETCDF TIME AXIS ===",flush=True)
    if not DATM.is_dir():
        fail("DATM directory absent: "+str(DATM))
    byyear={}
    for p in DATM.glob("DE-Tha_DATM_*.nc"):
        m=re.fullmatch(r"DE-Tha_DATM_(\d{4})\.nc",p.name)
        if m:
            byyear[int(m.group(1))]=p
    print("DATM DIRECTORY:",DATM)
    print("DATM YEAR COUNT:",len(byyear),"RANGE:",sorted(byyear))
    if set(byyear)!=set(range(1996,2026)):
        fail("DATM years are not exactly 1996-2025")
    for year in (1996,1997,2000,2010,2025):
        with Dataset(byyear[year],"r") as ds:
            time=ds.variables.get("time")
            if time is None:
                time=ds.variables.get("TIME")
            if time is None:
                print("HOLD",year,"no standard time variable; inspect manually")
                continue
            metadata={x:getattr(time,x) for x in ("units","calendar") if x in time.ncattrs()}
            print("DATM",year,"steps:",time.size,"time:",metadata)
            if time.size!=365*48:
                print("HOLD",year,"not 17520 half-hours")
    print("PASS: 30 existing candidate DATM files. Physical QC remains separate.")

def original_case():
    print("\n=== 5. ORIGINAL CASE — REFERENCE ONLY ===",flush=True)
    p=need(CASE/"CaseDocs/lnd_in")
    s=p.read_text(errors="replace")
    print("REFERENCE CASE:",CASE)
    for field in ("fsurdat","use_fates","use_fates_nocomp",
                  "use_fates_fixed_biogeog","spinup_state"):
        m=re.search(r"(?im)^\s*"+field+r"\s*=\s*([^\r\n]*)",s)
        print(field,":",m.group(1).strip() if m else "NOT_SET")
    for field in ("RUN_STARTDATE","RUN_TYPE","STOP_N","REST_N",
                  "DATM_CLMNCEP_YR_START","DATM_CLMNCEP_YR_END",
                  "CLM_ACCELERATED_SPINUP"):
        if not (CASE/"xmlquery").is_file():
            break
        p=subprocess.run(["./xmlquery",field,"--value"],cwd=CASE,
                         capture_output=True,text=True,check=False,timeout=15)
        if p.returncode==0:
            print(field,":",p.stdout.strip())
    streams=CASE/"user_nl_datm_streams"
    if streams.is_file():
        print("USER DATM STREAMS (first 25 lines):")
        for line in streams.read_text(errors="replace").splitlines()[:25]:
            print(" ",line[:200])
    print("HOLD: original DE-Tha case is ordinary FATES, not FIXNC")

def main():
    import numpy as np
    from netCDF4 import Dataset
    surface(np,Dataset)
    fates(np)
    forcing()
    datm(Dataset)
    original_case()
    print("\nREAD ONLY COMPLETE: NO FILES MODIFIED, NO CASE/JOBS SUBMITTED")
    print("HOLD: original landunits, forcing QC, 2% tree group and PFT-area proxy")

if __name__=="__main__":
    main()
