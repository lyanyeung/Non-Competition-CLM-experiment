#!/usr/bin/env python3
"""Batch04 10-site paired model hypotheses: NEW PFT-only surface candidates.

Original CTSM gridded 2000 surfaces (SYVH12) untouched. Use exact 10-row
50-site recommended CLM host PCT_NAT_PFT (index 0 is source-model bare).
Construct a COMMON initial point surface for both Full Competition FATES and
Fixed Biogeography/No Competition FATES, idealized NATVEG 100 CROP 0.

Soil profile PCT_SAND/PCT_CLAY/ORGANIC intentionally remains byte-equivalent
in every layer. The 50-site 0–30cm soil recommendations are NOT 10-layer
data. A successful candidate is not a model-ready PFT+soil/ZBOT source.

--self-test synthetic host mapping/allocation; no files/no writes
--check reads all source SHA/manifest and validates actual schemas; NO writes
--build creates ten isolated complete SHA-verified NetCDF research copies
        and a 10-site/20-arm common-initial-surface registry. NO case/DATM,
        no private FATES parameter map, no Slurm, original files unchanged.

One-arm case input must never be substituted for the other if a subsequent
science decision changes the PFT field. Both arms share the SAME per-site
initial condition unless the science design is explicitly re-approved.
"""
import argparse,csv,hashlib,importlib.util,json,math,os,shutil,tempfile
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
import numpy as np
from netCDF4 import Dataset

HERE=Path(__file__).resolve().parent
PRE=HERE/"01_audit_source_PFT_soil_surface_and_pair_plan.py"
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10")
LANDUNITS=("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def loadpre():
    require(PRE.is_file(),"Missing colocated verified Batch04 source preflight")
    p=importlib.util.spec_from_file_location("amf_b04_source_gate",str(PRE))
    mod=importlib.util.module_from_spec(p);p.loader.exec_module(mod)
    return mod
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4<<20),b""):h.update(x)
    return h.hexdigest()
def scenario_check(data,site):
    host=data["science_host_PFT_slots"]
    require(abs(sum(host.values())-100)<1e-6 and
            all(int(k) in range(15) for k in host),
            site+" invalid pinned HLM indices or sum")
    if site=="US-Uaf":
        require(data["FATES_mapping_profile"]=="ARCTIC_PURE",
                site+" requires non-default private FATES arctic map")
    else:
        require(data["FATES_mapping_profile"]=="DEFAULT14",
                site+" model-specific shared FATES map unexpected")
def original_layout(site,source):
    with Dataset(str(source),"r") as d:
        required=("PCT_NATVEG","PCT_CROP","PCT_NAT_PFT",
                  "LATIXY","LONGXY","PCT_SAND","PCT_CLAY")
        require(all(k in d.variables for k in required),
                site+" original surface lacks landunit/site variables")
        v=d["PCT_NAT_PFT"]
        require(v.size==15 and "natpft" in v.dimensions,
                site+" original HLM 15-slot surface unsupported")
        require(d["PCT_NATVEG"].size==d["PCT_CROP"].size==1 and
                d["PCT_SAND"].size>=10 and d["PCT_CLAY"].size>=10,
                site+" single-site/source soil layer metadata unsupported")
        before={}
        for name in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            if name in d.variables:
                before[name]=np.ma.filled(d[name][:],np.nan).copy()
        return before
def verify(site,path,host,soil_original):
    with Dataset(str(path),"r") as d:
        for field,x in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
            value=np.ma.filled(d[field][:],np.nan).ravel()
            require(value.size==1 and abs(float(value[0])-x)<.0001,
                    site+" idealized landunit % check failed "+field)
        for field in LANDUNITS:
            if field in d.variables:
                a=np.ma.filled(d[field][:],np.nan)
                require(np.isfinite(a).all() and np.allclose(a,0,atol=1e-5),
                        site+" nonveg landunit not zero "+field)
        pft=np.ma.filled(d["PCT_NAT_PFT"][:],np.nan).ravel()
        expected=np.array([float(host.get(i,0)) for i in range(15)])
        require(pft.size==15 and np.isfinite(pft).all() and
                np.allclose(pft,expected,atol=1e-5),
                site+" selected source host PFT differs from recommended HLM")
        for field,a in soil_original.items():
            require(field in d.variables and
                    np.allclose(np.ma.filled(d[field][:],np.nan),a,
                                equal_nan=True,atol=0,rtol=0),
                    site+" original "+field+" full-layer field was modified")
def build_one(site,info,output):
    parent=Path(info["source_surface_path"])
    original_sha=info["source_surface_SHA256"]
    require(sha(parent)==original_sha,
            site+" SYVH12 source before-copy SHA changed")
    dest=output/(site+"_AMF_B04_SHARED_PFT_START_RESEARCH.nc")
    require(not dest.exists(),site+" cannot overwrite selected research output")
    fd,name=tempfile.mkstemp(suffix=".nc",prefix="stage_B04_",dir=output)
    os.close(fd);temporary=Path(name)
    soil_original=original_layout(site,parent)
    host={int(k):float(v) for k,v in info["science_host_PFT_slots"].items()}
    try:
        shutil.copyfile(parent,temporary)
        with Dataset(str(temporary),"r+") as d:
            d["PCT_NATVEG"][:]=100.
            d["PCT_CROP"][:]=0.
            for field in LANDUNITS:
                if field in d.variables:d[field][:]=0.
            pft=d["PCT_NAT_PFT"]
            a=np.zeros(pft.shape,dtype=float)
            axis=pft.dimensions.index("natpft")
            for idx,value in host.items():
                key=[0]*a.ndim;key[axis]=idx
                a[tuple(key)]=value
            pft[:]=a
            d.AMF_B04_input_status="PFT_MODEL_HYPOTHESIS_NOT_SITE_OBSERVATION"
            d.AMF_B04_FATES_mapping_profile=info["FATES_mapping_profile"]
            d.AMF_B04_soil_policy="PCT_SAND_CLAY_ORGANIC_ORIGINAL_GRID_UNCHANGED"
            d.AMF_B04_no_ZBOT_or_CIME_release="TRUE"
        verify(site,temporary,host,soil_original)
        require(sha(parent)==original_sha,
                site+" source surface changed while building")
        os.link(temporary,dest)
    finally:
        temporary.unlink(missing_ok=True)
    return {"site":site,"source_surface_SHA256":original_sha,
            "new_model_hypothesis_surface":str(dest),
            "new_surface_SHA256":sha(dest),
            "idealized_NATVEG100_CROP0":True,
            "host_PFT_percentages":host,
            "FATES_mapping_profile":info["FATES_mapping_profile"],
            "FULL_FATES_start_surface":str(dest),
            "FIXED_NO_COMP_START_SURFACE":str(dest),
            "soil_texture_CLM10_layers_unchanged":True,
            "organic_unchanged_not_approved":True,
            "bare_fraction_pct":host.get(0,0),
            "FATES_PRIVATE_MAPPING_ACTIVATED":False,
            "case_submitted":False,
            "scientific_PFT_approved":False}
def main():
    a=argparse.ArgumentParser()
    modes=a.add_mutually_exclusive_group(required=True)
    for mode in ("self-test","check","build"):
        modes.add_argument("--"+mode,action="store_true")
    x=a.parse_args()
    pre=loadpre()
    cfg,pft,soil=pre.config()
    if x.self_test:
        require(len(cfg)==10 and len(pft)==10 and
           pre.pct(json.loads(pft["US-Seg"]["clm_pct_nat_pft_json"]),"US-Seg").get(0)==40 and
           pre.pct(json.loads(pft["US-Uaf"]["clm_pct_nat_pft_json"]),"US-Uaf").get(0,0)==0,
           "PFT scenario synthetic test failed")
        print("AMF_B04 PFT SURFACE SELF-TEST PASS 10 sites, bare40 at Seg, arctic Uaf private map, no writes")
        return
    rows,_,shas=pre.audit()
    for rec in rows:
        scenario_check(rec,rec["site"])
        original_layout(rec["site"],Path(rec["source_surface_path"]))
        print("AMF_B04 PFT SOURCE SCHEMA VERIFIED",rec["site"],
              rec["FATES_mapping_profile"],"PFT",rec["science_host_PFT_slots"])
    if x.check:
        print("AMF_B04 ALL TEN PFT/SOIL-UNCHANGED SURFACE PRECHECK PASS NO MODEL RELEASE")
        return
    BASE.mkdir(parents=True,exist_ok=True)
    folder=BASE/"PFT_surface_candidate_research_ONLY"/(
        "candidate_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+
        "_"+uuid4().hex[:8])
    folder.mkdir(parents=True,exist_ok=False)
    output=[]
    for rec in rows:
        sub=folder/rec["site"];sub.mkdir(exist_ok=False)
        output.append(build_one(rec["site"],rec,sub))
        print("AMF_B04 TWO ARM PFT SURFACE PREPARED",rec["site"],
              output[-1]["new_surface_SHA256"],flush=True)
    require(len(output)==10,"Ten research model surfaces not fully generated")
    receipt={
      "status":"TEN_IDENTICAL_PAIRED_INITIAL_PFT_SURFACES_CREATED_RESEARCH_ONLY",
      "site_surfaces":output,"n_sites":10,"n_planned_model_arms":20,
      "source_provenance":shas,
      "PFT_mapping_profile_ACTIVATED":False,
      "observed_PFT_proportions_accepted_as_actual":False,
      "soil_horizons_verified_as_site_observed":False,
      "ZBOT_resolved":False,
      "DATM_timecenter_UTC_ready":False,
      "active_CIME_case_created":False,
      "submitted_SLURM_jobs":False}
    target=folder/"AMF_B04_PFT_SURFACES_BOTH_ARMS_RESEARCH_ONLY.json"
    with target.open("x",encoding="utf-8") as f:
        json.dump(receipt,f,indent=2);f.write("\n")
    print("AMF_B04 TEN SHARED PFT SURFACE CANDIDATES FULL SHA AUDIT PASS",folder)
    print("MODEL_GATE HOLD SOURCE_HEIGHT ZBOT UTC_NC FATES_MAPPING PERLAYER_SOIL ORGANIC CIME")
    print("NO ORIGINAL SOURCE/SURFACE/DATM/CASE/SLURM WRITES")
if __name__=="__main__":main()
