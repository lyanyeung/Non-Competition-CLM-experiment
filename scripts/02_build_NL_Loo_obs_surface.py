#!/usr/bin/env python3
"""Generate an isolated NL-Loo FIXNC *candidate* surface, with explicit proxy choice.

No original NetCDF is modified. Writing requires TWO explicit scientific
assumption acknowledgements. Does not create cases, submit jobs, or edit FATES JSON.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ORIGINAL = ROOT / "sites/MY_EC_SITE/NL-Loo/subset_data/surfdata_NL-Loo_hist_2000_16pfts_c261011.nc"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
ORIGINAL_SHA256 = "b2d717b88638f90bd536233564e03b90196813b0f4d0343686db2349b45e5e31"
PARAM_SHA256 = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
# CLM 'natpft': index 0 bare, index 1 needleleaf evergreen temperate,
# index 7 broadleaf deciduous temperate, index 9 broadleaf evergreen shrub,
# index 13 cool C3 grass. Mapping is verified below against actual FATES JSON.
SCENARIOS = {"grass_proxy": (13, "cool_c3_grass"),
             "heath_proxy": (9, "broadleaf_evergreen_extratrop_shrub")}
SITE = "NL-Loo"
RUN_ROOT = ROOT / "experiments/NonCompetitionObserved22/NL-Loo"
FATES_NAMES = {1: "needleleaf_evergreen_extratrop_tree",
               5: "broadleaf_colddecid_extratrop_tree"}
LAND = ("PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def singleton(ds, name):
    if name not in ds.variables: raise RuntimeError(f"Missing required {name}")
    a=np.ma.filled(ds.variables[name][:], np.nan)
    if a.size != 1 or not np.isfinite(a).all(): raise RuntimeError(f"Invalid {name} shape")
    return float(a.ravel()[0])

def surface_info(ds):
    for name in ("PCT_NATVEG","PCT_CROP"):
        singleton(ds,name)
    for name in LAND:
        if name in ds.variables:
            a=np.ma.filled(ds.variables[name][:],np.nan)
            if not np.isfinite(a).all() or abs(float(np.sum(a)))>1e-5:
                raise RuntimeError(f"{name} is nonzero/invalid: model-specific treatment needed")
    if "PCT_NAT_PFT" not in ds.variables: raise RuntimeError("PCT_NAT_PFT absent")
    v=ds.variables["PCT_NAT_PFT"]
    axes=[i for i,d in enumerate(v.dimensions) if d.lower()=="natpft"]
    if len(axes)!=1 or v.shape[axes[0]] != 15 or any(n != 1 for i,n in enumerate(v.shape) if i!=axes[0]):
        raise RuntimeError(f"Unexpected CLM PFT dimensions: {v.dimensions} {v.shape}")
    x=np.ma.filled(v[:],np.nan).ravel()
    if not np.isfinite(x).all() or abs(x.sum()-100)>0.01: raise RuntimeError("Original CLM PFT sum invalid")
    return v, axes[0], x

def fates_map():
    if not PARAM.is_file() or digest(PARAM)!=PARAM_SHA256:
        raise RuntimeError("FATES parameter JSON differs from audited original; STOP")
    doc=json.loads(PARAM.read_text(encoding="utf8"))
    names=doc["parameters"]["fates_pftname"]["data"]
    m=np.asarray(doc["parameters"]["fates_hlm_pft_map"]["data"],dtype=float)
    if m.shape != (14,14) or len(names)!=14:
        raise RuntimeError(f"FATES map shape changed: {m.shape} {len(names)}")
    checks={1:FATES_NAMES[1],7:FATES_NAMES[5],13:SCENARIOS["grass_proxy"][1],9:SCENARIOS["heath_proxy"][1]}
    results={}
    for clm_idx,expected in checks.items():
        row=m[clm_idx-1]  # 14 mapped HLM classes exclude bare-ground (CLM index 0)
        nz=np.flatnonzero(row>0)
        if len(nz)!=1 or not np.isclose(row[nz[0]],1) or names[int(nz[0])]!=expected:
            raise RuntimeError(f"CLM index {clm_idx} not mapped 1:1 to {expected}; got {row} {names}")
        results[str(clm_idx)]=names[int(nz[0])]
    return results

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario",choices=sorted(SCENARIOS),required=True)
    ap.add_argument("--accept-open-cover-proxy",action="store_true")
    ap.add_argument("--accept-500m-radius-as-proxy",action="store_true")
    ap.add_argument("--write",action="store_true",help="default prints audit; --write creates NEW surface+report")
    ap.add_argument("--out-dir",type=Path,default=RUN_ROOT/"surface")
    args=ap.parse_args()
    if not ORIGINAL.is_file() or digest(ORIGINAL)!=ORIGINAL_SHA256:
        raise SystemExit("STOP: original NL-Loo surface differs from previously audited SHA256")
    m=fates_map()
    idx, name=SCENARIOS[args.scenario]
    with Dataset(ORIGINAL) as ds:
        _,_,original=surface_info(ds)
        old_nat=singleton(ds,"PCT_NATVEG")
        old_crop=singleton(ds,"PCT_CROP")
    chosen={1:93.6,7:2.9,idx:3.5}
    print("Original grid fractions: NATVEG=",old_nat,"CROP=",old_crop)
    print("Candidate grid fractions: NATVEG=100%, CROP=0% (assumes tower 500-m area represents modeled point)")
    print("CLM natural-landunit PFT shares (%):",chosen)
    print("Verified FATES PFT mapping:",{str(k):m[str(k)] for k in chosen})
    print("WARNING: OPEN 3.5% is heather/grass mixture, not observed as solely "+name)
    print("Source inventory is a 500-m circle, not a true dynamic EC footprint.")
    if not args.write:
        print("AUDIT ONLY: no files written. Use --write and two assumption acknowledgements.")
        return
    if not(args.accept_open_cover_proxy and args.accept_500m_radius_as_proxy):
        raise SystemExit("STOP: BOTH scientific assumption flags are required to write a proxy scenario")
    dst=args.out_dir / f"surfdata_NL-Loo_obsPFT_{args.scenario}_v1.nc"
    receipt=dst.with_suffix(".json")
    if dst.exists() or receipt.exists():
        raise SystemExit("STOP: candidate or receipt already exists; never overwrite")
    dst.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".NL-Loo-new-",suffix=".nc",dir=dst.parent);os.close(fd)
    tmp=Path(temp)
    try:
        shutil.copyfile(ORIGINAL,tmp)
        with Dataset(tmp,"r+") as ds:
            v,axis,_=surface_info(ds)
            out=np.zeros(v.shape,dtype=float)
            for k,pct in chosen.items():
                address=[0]*out.ndim
                address[axis]=k
                out[tuple(address)]=pct
            v[:]=out
            ds.variables["PCT_NATVEG"][:]=100.0
            ds.variables["PCT_CROP"][:]=0.0
            ds.setncattr("observed_pft_scenario","NL-Loo 500m proxy "+args.scenario+
                         "; open 3.5% assigned to ONE proxy PFT; NOT full footprint observation")
        with Dataset(tmp) as ds:
            _,_,v=surface_info(ds)
            if not np.allclose(v[[1,7,idx]], [93.6,2.9,3.5],atol=0.002):
                raise RuntimeError("Candidate PFT percentages mismatch")
            if not np.isclose(singleton(ds,"PCT_NATVEG"),100) or not np.isclose(singleton(ds,"PCT_CROP"),0):
                raise RuntimeError("Candidate landunit mismatch")
        sha=digest(tmp)
        os.replace(tmp,dst)
    finally:
        if tmp.exists():tmp.unlink()
    report={
        "site":SITE,"scenario":args.scenario,"status":"CANDIDATE_NOT_VALIDATED_BY_FATES_RUN",
        "original_surface":str(ORIGINAL),"original_sha256":ORIGINAL_SHA256,
        "generated_surface":str(dst),"generated_sha256":sha,
        "param_file_sha256":PARAM_SHA256,
        "landunit_grid_pct":{"PCT_NATVEG":100.0,"PCT_CROP":0.0},
        "natpft_pct":{str(k):v for k,v in chosen.items()},
        "fates_pft_names":{str(k):m[str(k)] for k in chosen},
        "limits":["500-m area is not flux-footprint weighted",
                  "Open 3.5% heather+grass assigned to a single proxy",
                  "Crop 33.16% changed to 0%; surface point changed to NATVEG 100%",
                  "PFT shares are % of CLM natural landunit, NOT % of vegetation carbon",
                  "No other model inputs modified; check FATES output PFT area after first segment"]
    }
    receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("CREATED NEW CANDIDATE SURFACE",dst)
    print("SHA256",sha)
    print("RECEIPT",receipt)
    print("Original surface intact. No case setup or Slurm submission.")

if __name__=="__main__":main()
