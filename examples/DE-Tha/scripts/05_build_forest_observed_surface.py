#!/usr/bin/env python3
"""DE-Tha ONLY: create isolated tower-forest FIXNC surface, 87 ENF / 10 DNF / 3 DBF.

The legacy DE-Tha grid fractions are *NOT* retained:
PCT_NATVEG=100, PCT_CROP=0, NAT_PFT[1]=87, [3]=10, [7]=3.
The 2% unspecified species in the official deciduous class are provisionally
grouped with DBF (1% identified birch + 2% unknown broadleaf/other).
This is a tower-forest PFT PROXY, not measured gridded PFT area.

Original NetCDF is copied as a structural/soil/terrain template ONLY; never
modified or overwritten. This script never creates cases, edits CTSM, or
submits/cancels Slurm jobs. Mode is read-only by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SRC = ROOT / "sites/MY_EC_SITE/DE-Tha/subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc"
SRC_SHA256 = "7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
PARAM_SHA256 = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
OUT_ROOT = ROOT / "experiments/NonCompetitionObserved22/DE-Tha/surface"
OUTPUT_NAME = "surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.nc"
PCT = {1: 87.0, 3: 10.0, 7: 3.0}
FATES_NAMES = {
    1: "needleleaf_evergreen_extratrop_tree",
    3: "needleleaf_colddecid_extratrop_tree",
    7: "broadleaf_colddecid_extratrop_tree",
}
ACK_2 = "ACCEPT_UNIDENTIFIED_DECIDUOUS_2PCT_AS_DBF_PROXY"
ACK_LAND = "ACCEPT_TOWER_FOREST_PROXY_NATVEG100_CROP0"

def stop(message: str) -> None:
    raise RuntimeError(str(message))

def hashfile(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def checked_file(path: Path, expected_hash: str, what: str) -> None:
    if not path.is_file() or path.is_symlink():
        stop(f"Missing original {what}: {path}")
    if hashfile(path) != expected_hash:
        stop(f"{what} SHA256 unexpectedly changed; do not reuse model assumptions: {path}")

def get_one(ds, key: str) -> float:
    if key not in ds.variables:
        stop("Required surface variable absent: " + key)
    a = np.ma.filled(ds.variables[key][:], np.nan).ravel()
    if a.size != 1 or not np.isfinite(a).all():
        stop("Expected one finite value for "+key)
    return float(a[0])

def natpft(ds):
    if "PCT_NAT_PFT" not in ds.variables:
        stop("PCT_NAT_PFT not present")
    v = ds.variables["PCT_NAT_PFT"]
    axes = [i for i,d in enumerate(v.dimensions) if d.lower() == "natpft"]
    if len(axes) != 1 or v.shape[axes[0]] != 15 or any(
            n != 1 for i,n in enumerate(v.shape) if i != axes[0]):
        stop(f"Unexpected single-cell CLM natural PFT dimensions: {v.dimensions} {v.shape}")
    original = np.ma.filled(v[:], np.nan)
    if not np.isfinite(original).all() or abs(float(original.sum())-100)>0.02:
        stop("Original PCT_NAT_PFT has invalid sum/NaN")
    return v, axes[0]

def check_landunits(ds):
    nat=get_one(ds, "PCT_NATVEG")
    crop=get_one(ds, "PCT_CROP")
    if abs(nat-62.674061760264706)>1e-4 or abs(crop-37.325938239735294)>1e-4:
        stop(f"Unrecognized original site landunit proportions: NATVEG={nat} CROP={crop}")
    for name in ("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN"):
        if name in ds.variables:
            a = np.ma.filled(ds.variables[name][:], np.nan)
            if not np.isfinite(a).all() or float(np.abs(a).sum())>1e-8:
                stop("Nonzero or invalid other landunit " + name)
    natpft(ds)

def fates_map():
    checked_file(PARAM,PARAM_SHA256,"FATES parameter JSON")
    doc=json.loads(PARAM.read_text(encoding="utf-8"))
    data=doc["parameters"]
    names=data["fates_pftname"]["data"]
    mapdata=np.asarray(data["fates_hlm_pft_map"]["data"], dtype=float)
    if mapdata.shape != (14, len(names)):
        stop(f"Unexpected FATES HLM map shape {mapdata.shape}")
    for idx,expect in FATES_NAMES.items():
        row=mapdata[idx-1]
        nz=np.flatnonzero(row>0)
        if len(nz)!=1 or not np.isclose(row[nz[0]],1) or names[int(nz[0])]!=expect:
            stop(f"CLM index {idx} does not uniquely map to {expect}")
    print("PASS: current FATES JSON maps natpft[1]/[3]/[7] to ENF/DNF/DBF")

def verify_output(path: Path):
    with Dataset(path,"r") as ds:
        a=get_one(ds,"PCT_NATVEG")
        b=get_one(ds,"PCT_CROP")
        if abs(a-100)>1e-4 or abs(b)>1e-4:
            stop("New surface landunit fractions failed verification")
        v,axis=natpft(ds)
        fractions=np.moveaxis(np.ma.filled(v[:],np.nan),axis,0).reshape(15)
        expected=np.zeros(15,dtype=float)
        for idx,pct in PCT.items():
            expected[idx]=pct
        if not np.allclose(fractions,expected,atol=0.001,rtol=0):
            stop(f"New surface has incorrect 15-class PFT shares: {fractions}")
        for name in ("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN"):
            if name in ds.variables:
                arr=np.ma.filled(ds.variables[name][:],np.nan)
                if not np.isfinite(arr).all() or float(np.abs(arr).sum())>1e-8:
                    stop("New surface has unexpected landunit "+name)

def write_new_surface(out: Path):
    receipt=out.with_suffix(".json")
    if out.exists() or receipt.exists():
        stop(f"Output or receipt already exists. Never overwrite: {out}")
    if out.parent.is_symlink():
        stop("Destination parent is a symlink; STOP")
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".DE-Tha-forest-",suffix=".nc",dir=out.parent)
    os.close(fd)
    tmp=Path(name)
    try:
        shutil.copyfile(SRC,tmp)
        with Dataset(tmp,"r+") as ds:
            check_landunits(ds)
            variable,axis=natpft(ds)
            new=np.zeros(variable.shape,dtype=float)
            for idx,pct in PCT.items():
                slc=[0]*new.ndim
                slc[axis]=idx
                new[tuple(slc)]=pct
            variable[:]=new
            ds.variables["PCT_NATVEG"][:]=100.
            ds.variables["PCT_CROP"][:]=0.
            ds.setncattr("observed_forest_scenario","DE-Tha FIXNC ENF87 DNF10 DBF3")
            ds.setncattr("observed_forest_provenance",
                "ICOS DE-Tha 72% Picea + 15% Pinus, 10% Larix, 1% Betula, 2% others")
            ds.setncattr("observed_forest_assumption",
                "Other 2% in deciduous category assigned to DBF proxy; "
                "forest flux-influence composition treated as 100% NATVEG single point; "
                "not independently verified mapped grid PFT area")
            ds.setncattr("observed_forest_source_url",
                           "https://meta.icos-cp.eu/resources/stations/ES_DE-Tha")
        verify_output(tmp)
        source_after=hashfile(SRC)
        if source_after!=SRC_SHA256:
            stop("Original surface was changed during generation; STOP")
        digest=hashfile(tmp)
        os.replace(tmp,out)
        report={
            "site":"DE-Tha",
            "status":"NEW_SURFACE_PROXY_WRITTEN_NOT_YET_MODEL_VALIDATED",
            "is_measured_grid_area":False,
            "source_surface":str(SRC),
            "source_surface_sha256":SRC_SHA256,
            "generated_surface":str(out),
            "generated_surface_sha256":digest,
            "pinned_fates_parameter_sha256":PARAM_SHA256,
            "landunits":{"PCT_NATVEG":100.0,"PCT_CROP":0.0},
            "clm_natpft_percent":{"1_ENF":87.0,"3_DNF":10.0,"7_DBF":3.0},
            "assumptions":[
                "Flux-influence forest species composition is a proxy for 100% natural forest grid landunit",
                "Unidentified 2% deciduous species allocated to DBF (cannot verify species identities)",
                "Original landunit and PFT fractions deliberately not carried into this tower-forest scenario",
                "Other physical properties remain from original gridded source and require separate site representativeness review",
            ],
            "created_at_utc":datetime.now(timezone.utc).isoformat(),
            "run_cases_created":False,"slurm_jobs_submitted":False
        }
        # Receipt is always a new file, never replaces an existing receipt.
        with receipt.open("x",encoding="utf-8") as f:
            json.dump(report,f,indent=2)
            f.write("\n")
        print("PASS: NEW ISOLATED FOREST-PROXY SURFACE CREATED")
        print("OUTPUT:",out)
        print("SHA256:",digest)
        print("RECEIPT:",receipt)
        print("PASS: original NetCDF SHA256 unchanged")
        print("NO MODEL CASES OR SLURM JOBS SUBMITTED")
    finally:
        if tmp.exists():
            tmp.unlink()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("audit","write"))
    parser.add_argument("--ack-2pct",default="",
                        help="Required exact statement for 2% unknown-species proxy")
    parser.add_argument("--ack-forest",default="",
                        help="Required exact statement for landunit NATVEG100/CROP0 proxy")
    parser.add_argument("--output-dir",type=Path,default=OUT_ROOT)
    args=parser.parse_args()
    checked_file(SRC,SRC_SHA256,"original DE-Tha source surface")
    with Dataset(SRC,"r") as ds:
        check_landunits(ds)
    fates_map()
    print("SURFACE STRUCTURAL TEMPLATE:",SRC)
    print("PROPOSED SINGLE FOREST SCENARIO: NATVEG=100% CROP=0%")
    print("PROPOSED PFTS: ENF=87% DNF=10% DBF=3% (2% unknown allocated to DBF)")
    print("WARNING: proxy for forest EC tower, NOT verified mapped grid-area observation")
    if args.action=="audit":
        print("READ ONLY AUDIT COMPLETE: no files written")
        return
    if args.ack_2pct!=ACK_2 or args.ack_forest!=ACK_LAND:
        stop("Write requires --ack-2pct "+ACK_2+" and --ack-forest "+ACK_LAND)
    if args.output_dir.resolve()==SRC.parent.resolve():
        stop("Output directory cannot be original source directory")
    write_new_surface(args.output_dir/OUTPUT_NAME)

if __name__=="__main__":
    main()
