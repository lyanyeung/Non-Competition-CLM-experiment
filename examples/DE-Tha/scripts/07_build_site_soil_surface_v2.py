#!/usr/bin/env python3
"""DE-Tha ONLY: build immutable observed-forest+site-soil surface v2.

Site forest model PFTs stay ENF 87%, DNF 10%, DBF 3%, NATVEG=100%, CROP=0%.
Replace ONLY PCT_SAND and PCT_CLAY across all ten soil-texture input layers
using published DE-Tha forest site reference:
  sand=17%, silt=71% (100 - sand - clay), clay=12%
  Prescher, Gruenwald & Bernhofer (2010), Agric. For. Meteorol. 150, 1016-1025,
  https://doi.org/10.1016/j.agrformet.2010.03.008
  https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany

The reference is FIRST MINERAL HORIZON, described as relatively stable to
~1.2 m. All 10 input layers receive one uniform SITE-SOIL PROXY, which may
EXTRAPOLATE beyond the measured depth. These 10 are the surface-input texture
layers, not proven to coincide exactly with site-sampled soil horizons.
Stone fraction, soil organic matter, color, terrain, hydrology and all other
surface variables are inherited unchanged. Changing texture may still affect
computed soil hydraulic properties within CTSM: requires a model preflight.

No existing v1 surface, source file, model case or Slurm job may be modified.
Default audit is READ ONLY; write requires exact explicit acknowledgement.
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

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SURF_DIR = BASE / "experiments/NonCompetitionObserved22/DE-Tha/surface"
V1 = SURF_DIR / "surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.nc"
V2 = SURF_DIR / "surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_SoilField17_71_12_v2.nc"
SOURCE = BASE / "sites/MY_EC_SITE/DE-Tha/subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc"
PARAM = BASE / "CTSM/src/fates/parameter_files/fates_params_default.json"
EXPECTED = {
    V1:"6d415b420ece0f18dca051c91849dcd5a3a5748779f9ee349c98e84e52e80600",
    SOURCE:"7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d",
    PARAM:"0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04",
}
PFT = {1:87.,3:10.,7:3.}
TARGET = {"PCT_SAND":17.,"PCT_CLAY":12.}
ACK = "ACCEPT_DE_THA_PUBLISHED_SOIL_TEXTURE_17SAND_71SILT_12CLAY_ALL10_AS_PROXY"

def fatal(s):
    raise RuntimeError(s)

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def check_pinned():
    for p,expected in EXPECTED.items():
        if not p.is_file() or p.is_symlink():
            fatal("Pinned file missing or symlink: "+str(p))
        actual=sha256(p)
        if actual!=expected:
            fatal(f"PINNED HASH MISMATCH: {p}\nexpected={expected}\nactual={actual}")
        print("PASS PINNED:",p.name,actual,flush=True)

def singleton(ds,key):
    if key not in ds.variables:
        fatal("Missing "+key)
    a=np.ma.filled(ds.variables[key][:],np.nan).ravel()
    if a.size!=1 or not np.isfinite(a).all():
        fatal("Expected finite single-point variable: "+key)
    return float(a[0])

def soil_var(ds,key):
    if key not in ds.variables:
        fatal("Soil variable missing: "+key)
    v=ds.variables[key]
    indices=[i for i,n in enumerate(v.dimensions) if (
        "levsoi" in n.lower() or n.lower() in ("nlevgrnd","nlevsoil")
    )]
    if len(indices)!=1 or v.shape[indices[0]]!=10:
        fatal(f"Unexpected soil dimension for {key}: {v.dimensions} {v.shape}")
    if any(x!=1 for i,x in enumerate(v.shape) if i!=indices[0]):
        fatal("Not a single point "+key)
    a=np.ma.filled(v[:],np.nan)
    if not np.isfinite(a).all() or not (0 <= a).all() or not (a <= 100).all():
        fatal("Invalid percent values: "+key)
    if not np.issubdtype(v.dtype,np.floating):
        fatal("Cannot assign measured fractions to non-floating soil var "+key)
    return v,np.asarray(a,dtype=float)

def check_v1():
    with Dataset(V1,"r") as ds:
        if abs(singleton(ds,"PCT_NATVEG")-100)>1e-4 or abs(singleton(ds,"PCT_CROP"))>1e-4:
            fatal("v1 landunits different from approved forest")
        v=ds.variables["PCT_NAT_PFT"]
        arr=np.ma.filled(v[:],np.nan).ravel()
        if len(arr)!=15 or not np.isfinite(arr).all():
            fatal("v1 natural PFT fractions invalid")
        expected=np.zeros(15)
        for i,pct in PFT.items():
            expected[i]=pct
        if not np.allclose(arr,expected,atol=0.001,rtol=0):
            fatal("v1 forest PFT proportions invalid")
        _,sand=soil_var(ds,"PCT_SAND")
        _,clay=soil_var(ds,"PCT_CLAY")
        if sand.shape!=clay.shape:
            fatal("Mismatched soil shapes")
        if not np.allclose(sand.reshape(10)[:4],24.,atol=0.001) or not np.allclose(
            clay.reshape(10)[:4],25.,atol=0.001):
            fatal("Unexpected baseline topsoil; do not assume unreviewed inputs")
        print("PASS v1 forest PFTs and original topsoil 24/51/25",flush=True)

def same_array(a,b):
    x=np.ma.asarray(a)
    y=np.ma.asarray(b)
    if x.shape!=y.shape or x.dtype!=y.dtype:
        return False
    if not np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(y)):
        return False
    u=np.ma.getdata(x)
    v=np.ma.getdata(y)
    if np.issubdtype(u.dtype,np.inexact):
        return np.array_equal(u,v,equal_nan=True)
    return np.array_equal(u,v)

def validate_v2(path):
    with Dataset(V1,"r") as base, Dataset(path,"r") as revised:
        if set(base.variables)!=set(revised.variables) or set(base.dimensions)!=set(revised.dimensions):
            fatal("New surface variable/dimension inventory changed")
        for dim in base.dimensions:
            if len(base.dimensions[dim])!=len(revised.dimensions[dim]):
                fatal("Surface dimension length changed: "+dim)
        for name in sorted(base.variables):
            x=base.variables[name]
            y=revised.variables[name]
            if x.dimensions!=y.dimensions or x.dtype!=y.dtype:
                fatal("Unexpected variable structure changed: "+name)
            if set(x.ncattrs())!=set(y.ncattrs()):
                fatal("Variable metadata changed: "+name)
            if any(not same_array(x.getncattr(key),y.getncattr(key)) for key in x.ncattrs()):
                fatal("Variable attribute changed: "+name)
            if name in TARGET:
                var,data=soil_var(revised,name)
                if not np.allclose(data,TARGET[name],atol=1e-4,rtol=0):
                    fatal("Wrong measured soil texture in "+name)
            elif not same_array(x[:],y[:]):
                fatal("Non-texture variable changed: "+name)
        if abs(singleton(revised,"PCT_NATVEG")-100)>1e-5:
            fatal("Unexpected NATVEG in v2")
        if abs(singleton(revised,"PCT_CROP"))>1e-5:
            fatal("Unexpected CROP in v2")
    print("PASS: only PCT_SAND and PCT_CLAY changed among all NetCDF variables",flush=True)
    print("PASS: forest PFTs and non-soil inputs inherited exactly from v1",flush=True)
    print("PASS: 10 layers each sand=17%, clay=12%, derived silt=71%",flush=True)

def dest_guard():
    if V2==V1 or V2==SOURCE or V2.parent.resolve()!=V1.parent.resolve():
        fatal("Unexpected output location")
    if V2.exists() or V2.is_symlink() or V2.with_suffix(".json").exists():
        fatal("V2 surface/receipt already exists; will not overwrite")

def create_v2():
    dest_guard()
    fd,name=tempfile.mkstemp(dir=SURF_DIR,prefix=".DE-Tha-soil-tmp-",suffix=".nc")
    os.close(fd)
    tmp=Path(name)
    try:
        shutil.copyfile(V1,tmp)
        with Dataset(tmp,"r+") as ds:
            for key,value in TARGET.items():
                var,baseline=soil_var(ds,key)
                var[:]=np.full(baseline.shape,value,dtype=float)
        validate_v2(tmp)
        if sha256(V1)!=EXPECTED[V1] or sha256(SOURCE)!=EXPECTED[SOURCE]:
            fatal("An input surface changed during v2 construction")
        generated_sha=sha256(tmp)
        dest_guard()
        os.link(tmp,V2)  # fails atomically rather than overwriting an existing output
        receipt={
          "site":"DE-Tha",
          "status":"FOREST_PFT_PLUS_SITE_SOIL_TEXTURE_PROXY_GENERATED_PENDING_CIME_VALIDATION",
          "source_v1":str(V1),"source_v1_sha256":EXPECTED[V1],
          "original_surface":str(SOURCE),"original_surface_sha256":EXPECTED[SOURCE],
          "generated_v2":str(V2),"generated_v2_sha256":generated_sha,
          "landunit_percent":{"PCT_NATVEG":100.,"PCT_CROP":0.},
          "natpft_percent":{"ENF":87.,"DNF":10.,"DBF":3.},
          "measured_first_mineral_layer_pct":{"sand":17.,"silt":71.,"clay":12.},
          "applied_to_input_layer_count":10,
          "soil_texture_input_variables_changed":["PCT_SAND","PCT_CLAY"],
          "depth_policy":"UNIFORM 10-layer site-soil proxy. Literature reports first mineral horizon, relatively stable to ~1.2 m; extension beyond observed depth is extrapolation pending pinned CIME soil_layerstruct verification.",
          "texture_source_title":"Land use regulates carbon budgets in eastern Germany: From NEE to NBP",
          "texture_source_doi":"10.1016/j.agrformet.2010.03.008",
          "texture_source_url":"https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany",
          "other_soil_properties":"Inherited unchanged from verified v1; do not label as measured",
          "cases_created":False,"jobs_submitted":False,
          "created_at_utc":datetime.now(timezone.utc).isoformat()
        }
        with V2.with_suffix(".json").open("x",encoding="utf-8") as f:
            json.dump(receipt,f,indent=2)
            f.write("\n")
        print("CREATED ISOLATED v2:",V2,flush=True)
        print("GENERATED SHA256:",generated_sha)
        print("RECEIPT:",V2.with_suffix(".json"))
        print("PASS: pinned original and v1 SHA256s unchanged")
    finally:
        if tmp.exists():tmp.unlink()

def verify():
    receipt_path=V2.with_suffix(".json")
    if not V2.is_file() or V2.is_symlink() or not receipt_path.is_file():
        fatal("v2 NetCDF or receipt not found")
    receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("generated_v2")!=str(V2) or (
        receipt.get("source_v1_sha256")!=EXPECTED[V1] or
        receipt.get("original_surface_sha256")!=EXPECTED[SOURCE]
    ):
        fatal("Receipt provenance mismatches pinned source")
    if receipt.get("measured_first_mineral_layer_pct")!={"sand":17.,"silt":71.,"clay":12.}:
        fatal("Receipt site-soil values mismatched")
    got=sha256(V2)
    if got!=receipt.get("generated_v2_sha256"):
        fatal("v2 NetCDF SHA256 not equal to receipt")
    validate_v2(V2)
    print("VERIFY PASS v2 SHA256:",got)
    print("READ ONLY VERIFY COMPLETE. CIME mode, forcing QC and soil depths remain to review.")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("audit","write","verify"))
    ap.add_argument("--ack-uniform-10-layer-soil-proxy",default="")
    args=ap.parse_args()
    check_pinned()
    check_v1()
    print("SELECTED single DE-Tha forest+site-soil scenario: 87/10/3 PFT,")
    print("100% NATVEG, sand=17%, silt=71%, clay=12% in ten input layers.")
    print("CAUTION: all-layer assignment beyond the literature's ~1.2m support")
    print("is an explicit extrapolation, NOT 10 separate depth observations.")
    if args.action=="audit":
        print("READ ONLY AUDIT PASSED; no NetCDF written, no jobs.")
    elif args.action=="write":
        if args.ack_uniform_10_layer_soil_proxy!=ACK:
            fatal("Writing v2 requires explicit --ack-uniform-10-layer-soil-proxy "+ACK)
        create_v2()
    else:
        verify()

if __name__=="__main__":
    main()
