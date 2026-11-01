#!/usr/bin/env python3
"""Stage02X: operator-approved Batch04 four-site PFT surface candidates.

self-test / plan are read-only. build creates only new isolated four-site
candidate surface NetCDFs and SHA receipts in an existing EMPTY directory.
No source NC, original cases, forcing, FATES shared map, or Slurm changes.
This does not release meteorology, soil source QC, or AD5/AD400.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

W_STAGE="STAGE02W_BATCH04_GITHUB_AUTHORITATIVE_PFT_VS_SOURCE_SURFACE_MANUAL_REVIEW"
U_STAGE="STAGE02U_BATCH04_FOUR_SITE_STATIC_CASE_SURFACE_SOIL_PFT_GATE"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
TARGET={"DE-Gri":{13:100.0},"DE-RuR":{13:100.0},
        "IT-Tor":{13:100.0},"ES-Agu":{0:49.0,9:22.0,13:29.0}}
REGISTER={"DE-Gri":"C3 grass 100 (candidate)",
          "DE-RuR":"C3 grass 100 (candidate)",
          "IT-Tor":"C3 grass 100 (candidate)",
          "ES-Agu":"bare 49 / C3 grass 29 / evergreen shrub 22"}
OTHERS=("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
CONFIRM="CREATE_FOUR_BATCH04_APPROVED_PFT_SURFACE_CANDIDATES_NO_CASES"


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):
            h.update(b)
    return h.hexdigest()


def validation(w,u):
    if w.get("stage")!=W_STAGE or w.get("read_only") is not True or \
       w.get("science_release") is not False:
        raise ValueError("Original Stage02W report not pinned or not science HOLD")
    if u.get("stage")!=U_STAGE or u.get("read_only") is not True or \
       u.get("science_release") is not False:
        raise ValueError("Original Stage02U report not pinned or not science HOLD")
    rec=w.get("records",[])
    ur=u.get("sites",[])
    if len(rec)!=8 or len(ur)!=4 or \
       {x.get("site") for x in ur}!=set(SITES):
        raise ValueError("Expected exact four-site eight-case evidence")
    sc={}
    for item in ur:
        site=item["site"]
        if item.get("Stage02D_flags")!={} or item.get("science_release")!="HOLD":
            raise ValueError(site+" previous annual DATM screen changed")
        cases=item.get("source_case_inspections",[])
        if len(cases)!=2 or len({c.get("case") for c in cases})!=2:
            raise ValueError(site+" source case count not two")
        sources={c.get("surface_path") for c in cases}
        params={c.get("fates_param_path") for c in cases}
        if len(sources)!=1 or len(params)!=1 or None in sources or None in params:
            raise ValueError(site+" case-pair source surface/FATES maps differ")
        if any(c.get("point_check")!="MATCH_STATIC_XML_NOT_RUNTIME" or
               c.get("surface_original",{}).get("status")!="POINT_SURFACE_HEADER_AND_BOUNDED_NUMERIC_READ"
               for c in cases):
            raise ValueError(site+" source point matching unresolved")
        source=Path(next(iter(sources)))
        param=Path(next(iter(params)))
        if not source.is_absolute() or source.is_symlink() or not source.is_file() or \
           not source.name.startswith("surfdata_"+site+"_") or \
           not source.name.endswith(".nc"):
            raise ValueError(site+" original source surface unavailable/unsafe")
        if not param.is_absolute() or param.is_symlink() or not param.is_file():
            raise ValueError(site+" original site FATES parameter unavailable")
        sc[site]={"source":source,"param":param,"cases":cases}
    for site in SITES:
        subset=[x for x in rec if x.get("site")==site]
        if len(subset)!=2 or {x.get("case") for x in subset}!={x["case"] for x in sc[site]["cases"]}:
            raise ValueError(site+" Stage02U/W case mismatch")
        for item in subset:
            if item.get("GitHub_registered_proxy")!=REGISTER[site] or \
               item.get("model_submission_release")!="HOLD" or \
               item.get("GitHub_target_active_case_verified") is not False:
                raise ValueError(site+" GitHub registry/science gate changed")
    return sc


def vec(site):
    return [TARGET[site].get(i,0.0) for i in range(15)]


def map_check(path,site):
    import numpy as np
    obj=json.loads(path.read_text(encoding="utf-8"))["parameters"]
    names=[str(x).strip() for x in obj["fates_pftname"]["data"]]
    mapping=np.asarray(obj["fates_hlm_pft_map"]["data"],dtype=float)
    expected={13:"cool_c3_grass"}
    if site=="ES-Agu":expected[9]="broadleaf_evergreen_extratrop_shrub"
    out={}
    for hlm,kind in expected.items():
        if mapping.ndim!=2 or mapping.shape[0]<hlm or mapping.shape[1]!=len(names):
            raise ValueError(site+" unexpected FATES HLM map dimensions")
        row=mapping[hlm-1]
        nonzero=[(names[i],float(x)) for i,x in enumerate(row) if x>1e-10]
        if len(nonzero)!=1 or nonzero[0][0]!=kind or abs(nonzero[0][1]-1)>1e-6:
            raise ValueError(site+" unexpected FATES HLM map "+str(nonzero))
        out[str(hlm)]=kind
    return out


def bare_support(root):
    fates=root/"CTSM/src/fates"
    iface=root/"CTSM/src/utils/clmfates_interfaceMod.F90"
    matches=[]
    if fates.is_dir():
        for f in fates.rglob("*.F90"):
            if f.is_file() and not f.is_symlink():
                if "nocomp_bareground" in f.read_text(encoding="utf-8",errors="replace").lower():
                    matches.append(str(f))
    text=iface.read_text(encoding="utf-8",errors="replace").lower() if iface.is_file() else ""
    return {"source_tag_found":len(matches)>0,
            "area_fraction_interface_found":"pft_areafrac" in text or "baregroundfrac" in text,
            "sources":matches[:5],
            "supported":len(matches)>0 and ("pft_areafrac" in text or "baregroundfrac" in text)}


def surface_check(path):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(str(path),"r") as ds:
        must=("PCT_NATVEG","PCT_CROP","PCT_NAT_PFT",
              "PCT_SAND","PCT_CLAY","ORGANIC","LATIXY","LONGXY")
        if any(x not in ds.variables for x in must):
            raise ValueError("Incomplete point surface: "+str(path))
        for x in ("PCT_NATVEG","PCT_CROP","LATIXY","LONGXY"):
            if ds.variables[x].size!=1:raise ValueError(x+" not point scalar")
        v=ds.variables["PCT_NAT_PFT"]
        if v.size!=15 or "natpft" not in v.dimensions:
            raise ValueError("Unexpected PCT_NAT_PFT schema")
        old=np.ma.filled(v[:],np.nan).reshape(-1)
        if not np.isfinite(old).all() or abs(old.sum()-100)>0.1:
            raise ValueError("Original PFT vector invalid")
        values={}
        for x in ("PCT_NATVEG","PCT_CROP"):
            values[x]=float(np.ma.filled(ds.variables[x][:],np.nan).reshape(-1)[0])
        for x in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            v=ds.variables[x]
            a=np.ma.filled(v[:],np.nan).reshape(-1)
            if len(a)!=10 or not np.isfinite(a).all():
                raise ValueError(x+" does not have 10 finite layers")
            values[x+"_range"]=[float(a.min()),float(a.max())]
        values["original_NAT_PFT"]=[float(x) for x in old]
        return values


def preflight(sources,root):
    out={}
    for site in SITES:
        path=sources[site]["source"]
        source_sha=sha(path)
        previous=sources[site]["cases"][0].get("surface_sha",{}).get("sha256_if_small")
        if previous and source_sha!=previous:
            raise ValueError(site+" original surface changed since Stage02U")
        info=surface_check(path)
        info.update(source_path=str(path),source_sha256=source_sha,
                    fates_parameter=str(sources[site]["param"]),
                    fates_parameter_sha256=sha(sources[site]["param"]),
                    hlm_fates_map=map_check(sources[site]["param"],site),
                    approved_GitHub_PFT=TARGET[site])
        out[site]=info
    out["ES-Agu"]["fates_bare_support"]=bare_support(root)
    return out


def build_one(site,profile,directory):
    from netCDF4 import Dataset
    import numpy as np
    src=Path(profile["source_path"])
    dst=directory/(site+"_B04_GITHUBPFT_POINT_CANDIDATE.nc")
    receipt=directory/(site+"_B04_surface_manifest.json")
    if dst.exists() or receipt.exists():
        raise FileExistsError("Never overwrite previous candidate surfaces")
    fd,tmpname=tempfile.mkstemp(prefix="."+site+"_",suffix=".nc",dir=directory)
    os.close(fd)
    tmp=Path(tmpname)
    try:
        shutil.copyfile(src,tmp)
        with Dataset(str(tmp),"r+") as ds:
            ds.variables["PCT_NATVEG"][:]=100.
            ds.variables["PCT_CROP"][:]=0.
            for k in OTHERS:
                if k in ds.variables:ds.variables[k][:]=0.
            v=ds.variables["PCT_NAT_PFT"]
            a=np.zeros(v.shape)
            ax=v.dimensions.index("natpft")
            for k,val in TARGET[site].items():
                key=[0]*a.ndim
                key[ax]=k
                a[tuple(key)]=val
            v[:]=a
        checked=surface_check(tmp)
        if abs(checked["PCT_NATVEG"]-100)>1e-4 or \
           abs(checked["PCT_CROP"])>1e-4 or \
           not np.allclose(checked["original_NAT_PFT"],vec(site),atol=1e-4):
            raise ValueError(site+" new surface PFT/landunit failed")
        with Dataset(str(src),"r") as old,Dataset(str(tmp),"r") as new:
            for key in ("PCT_SAND","PCT_CLAY","ORGANIC","LATIXY","LONGXY"):
                if not np.ma.allequal(old.variables[key][:],new.variables[key][:]):
                    raise ValueError(site+" protected soil/location modified: "+key)
        if sha(src)!=profile["source_sha256"]:
            raise ValueError(site+" original surface changed during copy")
        os.link(tmp,dst)
        report={
            "site":site,"source_surface":str(src),
            "source_sha256":profile["source_sha256"],
            "candidate_surface":str(dst),"candidate_sha256":sha(dst),
            "PCT_NATVEG":100,"PCT_CROP":0,
            "PCT_NAT_PFT_target":TARGET[site],
            "model_proxy_GitHub_approved":True,
            "old_soil_source_kept_UNVERIFIED":True,
            "IT_Tor_ten_organic_layers_zero_HOLD":site=="IT-Tor",
            "meteorology_QC_approved":False,"runtime_case_approved":False,
            "CIME_case_created":False,"slurm_submitted":False,
        }
        with receipt.open("x",encoding="utf-8") as f:
            json.dump(report,f,indent=2);f.write("\n")
        return report
    finally:
        tmp.unlink(missing_ok=True)


def self_test():
    assert list(TARGET)==list(SITES)
    assert sum(vec("ES-Agu"))==100 and vec("ES-Agu")[0]==49 and vec("ES-Agu")[9]==22
    assert len(vec("DE-Gri"))==15 and vec("DE-RuR")[13]==100
    print("STAGE02X SELF-TEST PASS: four GitHub PFT scenarios, new model NATVEG100 point and no original-file overwrite")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("self-test","plan","build"))
    ap.add_argument("--stage02w",type=Path)
    ap.add_argument("--stage02u",type=Path)
    ap.add_argument("--ctsm-base",type=Path,default=Path("/iridisfs/scratch/ly3n24/CLM_FATES"))
    ap.add_argument("--out-dir",type=Path)
    ap.add_argument("--confirm")
    x=ap.parse_args()
    if x.action=="self-test":
        self_test();return
    if not x.stage02w or not x.stage02w.is_file() or \
       not x.stage02u or not x.stage02u.is_file():
        ap.error("Original Stage02W and Stage02U saved JSON required")
    w=json.loads(x.stage02w.read_text(encoding="utf-8"))
    u=json.loads(x.stage02u.read_text(encoding="utf-8"))
    sources=validation(w,u)
    profiles=preflight(sources,x.ctsm_base)
    for site in SITES:
        p=profiles[site]
        print("SITE",site,"GH_PFT",p["approved_GitHub_PFT"],
              "SURFACE",p["source_path"],
              "ORIGINAL_NATVEG",p["PCT_NATVEG"],"ORIGINAL_CROP",p["PCT_CROP"],
              "CANDIDATE_NATVEG",100,"CANDIDATE_CROP",0,
              "HLM_FATES",p["hlm_fates_map"],
              "SOIL_SAND",p["PCT_SAND_range"],
              "SOIL_CLAY",p["PCT_CLAY_range"],
              "SOIL_ORGANIC",p["ORGANIC_range"])
    print("ES-AGU_NOCOMP_BARE",profiles["ES-Agu"]["fates_bare_support"])
    print("STAGE02X PFT PROXY OPERATOR APPROVED 4/4; "
          "TOWER_FORCING/ACTIVE_STREAM/SOIL SCIENCE HOLD; NO JOBS")
    if x.action=="plan":
        print("STAGE02X PLAN PASS; NO FILES OR CASES WRITTEN")
        return
    if x.confirm!=CONFIRM:
        ap.error("Requires --confirm "+CONFIRM)
    if not profiles["ES-Agu"]["fates_bare_support"]["supported"]:
        raise ValueError("ES-Agu FATES bare-ground feature unverified: NO BUILD")
    if x.out_dir is None or not x.out_dir.is_dir() or \
       x.out_dir.is_symlink() or any(x.out_dir.iterdir()):
        ap.error("Build requires a NEW, existing, EMPTY and non-symlink output directory")
    base=x.ctsm_base.resolve(strict=True)
    out=x.out_dir.resolve(strict=True)
    original_site_dir=base/"sites"
    if out==base or out.is_relative_to(original_site_dir):
        ap.error("Refuse output under original site source directory")
    for site in SITES:
        result=build_one(site,profiles[site],out)
        print("CANDIDATE_CREATED",site,result["candidate_surface"],
              "SHA256",result["candidate_sha256"])
    print("CREATED FOUR ISOLATED SURFACE CANDIDATES; NO CASE/SLURM; SOIL/QC HOLD")


if __name__=="__main__":
    main()
