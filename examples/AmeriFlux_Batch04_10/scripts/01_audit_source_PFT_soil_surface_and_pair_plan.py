#!/usr/bin/env python3
"""AmeriFlux Batch04 new paired FULL-FATES vs FIXNC experiment -- source-locked.

--self-test: synthetic registry/protocol checks; NO HPC/source writes.
--audit: original ten SYVH9 met source SHAs, Gate0 receipt, 10 original
         SYVH12 gridded surface NetCDF SHAs and coordinates, ten immutable
         PFT and soil recommendation snapshots; NO writes.
--plan: same checks and write NEW research-only paired 20-arm JSON+TSV
        under experiment NonCompetitionObserved22/AmeriFlux_Batch04_10.
        Does NOT create CIME cases/CLM namelists/forcing/netcdf/surface or jobs.
AD400 (5+395 years) then Normal400 (5+395), per-arm. Existing user
approved 10-site Gate0 is a numeric screen, not verified ZBOT/time center,
scientific PFT/organic soil, FATES HLM parameter map or model permission.
"""
import argparse,csv,hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=ROOT/"experiments/AmeriFlux_MultiSite_10_Batch04"
SOURCE=EXP/("manual_Batch04_SYVH9_12_low_LW_5sites_independent_ERA5Land_"
             "research_not_approved/candidate_20261026T121123Z_a8b8146f")
SURF=EXP/("stage12_provisional_ctsm_point_surfaces_RESEARCH_ONLY/"
          "candidate_20261026T163236Z_5737e505")
OUT=ROOT/"experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10"
BASE=Path(__file__).resolve().parent.parent
REGISTER=BASE/"data/AMF_BATCH04_10_SOURCE_SURFACE_REGISTER_20261026.tsv"
PFT=BASE/"data/AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv"
SOIL=BASE/"data/AMF_BATCH04_10_SOIL_SOURCE_SNAPSHOT_20261026.csv"
SITES=("US-Rpf","US-SP1","US-SRG","US-SRM","US-Seg",
       "US-Ses","US-Slt","US-Syv","US-Ton","US-Uaf")
ARCTIC={"US-Uaf"}
ARMS={"FULL_FATES_COMPETITION":{"use_fates":True,
                                "use_fates_sp":False,
                                "use_fates_fixed_biogeog":False,
                                "use_fates_nocomp":False},
      "FIXED_BIOGEOG_NO_COMPETITION":{"use_fates":True,
                                    "use_fates_sp":False,
                                    "use_fates_fixed_biogeog":True,
                                    "use_fates_nocomp":True}}
SURFACE_MODEL={
    "landunit":"IDEALIZED_NATVEG100_CROP0_AS_MODEL_SCENARIO",
    "initial_pft":"USE_PINNED_50_SITE_RECOMMENDATION_NOT_DEFAULT_2000_GRID",
    "soil":"ORIGINAL_DEPTH_LAYERS_PRESERVED_UNTIL_INDEPENDENT_TEN_LAYER_VERIFICATION",
    "organic":"PERMAFROST_ORGANIC_STATUS_NEEDS_REVIEW",
    "ZBOT":"NOT_SOURCE_VERIFIED_DO_NOT_ASSUME_2M_OR_CANOPY",
    "DATM":"NOT_PRODUCED_FROM_SYVH9_HH_SOURCE_YET",
    "CO2":"NOT_SELECTED_FROM_CASE_OR_FORCING"}

def require(v,msg):
    if not v:raise RuntimeError(msg)
def goodfile(p):
    require(p.is_file() and not p.is_symlink(),"File missing/symlink: "+str(p))
    return p
def sh(p):
    h=hashlib.sha256()
    with goodfile(p).open("rb") as f:
        for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
    return h.hexdigest()
def js(p):return json.loads(goodfile(p).read_text())
def tab(p,fields,sep=","):
    with goodfile(p).open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f,delimiter=sep)
        require(r.fieldnames is not None and set(fields).issubset(r.fieldnames),
                "Wrong column structure "+str(p))
        return list(r)
def unique(rows,flag):
    ids=[r["site"] for r in rows]
    require(len(rows)==10 and set(ids)==set(SITES) and len(set(ids))==10,
            "Wrong exact AmeriFlux Batch04 10 sites "+flag)
    return {x["site"]:x for x in rows}
def pct(p,site):
    require(isinstance(p,dict),"Non-dict host PFT "+site)
    dic={int(k):float(v) for k,v in p.items()}
    require(all(0<=i<=14 and math.isfinite(v) and 0<=v<=100 for i,v in dic.items())
       and abs(sum(dic.values())-100)<1e-5,
       "Invalid 15-HLM PFT share "+site+" "+str(dic))
    return dic
def config():
    r=unique(tab(REGISTER,("site","first_year","last_year",
       "SYVH12_surface_SHA256","SYVH12_surface_root",
       "forcing_source_status","experiment_case_status"),"\t"),"register")
    p=unique(tab(PFT,("site","batch","clm_pct_nat_pft_json",
       "mapping_profile","recommended_percent","bare_percent","uncertainty")),
       "PFT source")
    s=unique(tab(SOIL,("site","batch","tier","PCT_SAND_0_30cm",
       "PCT_CLAY_0_30cm")),"soil source")
    for site in SITES:
        require(p[site]["batch"]==s[site]["batch"]=="Batch04",
                "Cross-batch PFT/soil source row "+site)
        require(p[site]["mapping_profile"]==
          ("ARCTIC_PURE" if site in ARCTIC else "DEFAULT14"),
          "Unexpected FATES parameter mapping regime "+site)
        host=pct(json.loads(p[site]["clm_pct_nat_pft_json"]),site)
        require(abs(float(p[site]["bare_percent"])-host.get(0,0))<.00001,
                "Host BARE inconsistent "+site)
        sand=float(s[site]["PCT_SAND_0_30cm"])
        clay=float(s[site]["PCT_CLAY_0_30cm"])
        require(0<=sand<=100 and 0<=clay<=100 and sand+clay<=100,
                "Wrong 0-30cm recommendation "+site)
        require(r[site]["forcing_source_status"]==
                "SYVH9_SEVEN_MET_NOLEAP_NUMERIC_GATE0_PASS" and
                r[site]["experiment_case_status"]=="NOT_CREATED",
                "Source/existing-case record requires re-audit "+site)
        require(int(r[site]["last_year"])>=int(r[site]["first_year"]),
                "Year coverage invalid "+site)
    return r,p,s
def audit():
    register,pfts,soils=config()
    meta=js(SOURCE/"SYVH9_SCIENCE_RECEIPT.json")
    require(meta.get("stage")=="SYVH9_INDEPENDENT_ERA5LAND_DEACCUMULATED_STRD"
       and meta.get("independently_retrieved_source_hh")==12
       and meta.get("research_only") is True and meta.get("model_ready") is False,
       "SYVH9 immutable original met receipt changed")
    manifest=SOURCE/"RESEARCH_TEN_SITE_MANIFEST.tsv"
    require(sh(manifest)==meta["new_manifest_sha256"],
       "Original final source manifest SHA mismatch")
    met=unique(tab(manifest,
       ("site","source_path","source_SHA256","latest_stage"),"\t"),"meteorology")
    gate=js(SOURCE/"SYVH9_TEN_SITE_GATE0_READONLY_RESULTS.json")
    require(gate.get("numeric_gate0_pass") is True
        and not gate["blocked"] and gate["native_VPD_source_rounding_HH"]==3,
        "Seven-met NOLEAP Gate0 source not fully verified")
    surfmeta=js(SURF/"SYVH12_RESEARCH_SURFACES_RECEIPT.json")
    require(surfmeta.get("n_site_surfaces_sha_verified")==10
            and surfmeta.get("surface_reference_year")==2000
            and surfmeta.get("source_gridded_PFT_validated_at_EC_tower") is False
            and surfmeta.get("postv5_approved") is False,
            "Provisional gridded year-2000 surface receipt changed")
    info=unique(surfmeta["selected_sites"],"surface receipt")
    results=[]
    import numpy as np
    from netCDF4 import Dataset
    for site in SITES:
        a=register[site]; m=met[site]; surf=info[site]
        require(sh(Path(m["source_path"]))==m["source_SHA256"],
                "Full SYVH9 met source SHA mismatch "+site)
        surffile=Path(surf["surfdata_path"])
        require(surffile.is_relative_to(SURF/site) and
                Path(a["SYVH12_surface_root"])==SURF/site/"subset_data" and
                sh(surffile)==surf["SHA256"]==a["SYVH12_surface_SHA256"],
                "Original independently created surface SHA drift "+site)
        with Dataset(str(surffile)) as d:
            for k in ("LATIXY","LONGXY","PCT_NATVEG","PCT_CROP",
                       "PCT_NAT_PFT","PCT_SAND","PCT_CLAY"):
                require(k in d.variables,"Source surface lacks "+k+" "+site)
            lat=float(np.ma.filled(d["LATIXY"][:],np.nan).ravel()[0])
            lon=float(np.ma.filled(d["LONGXY"][:],np.nan).ravel()[0])
            hostshape=d["PCT_NAT_PFT"].shape
            require(d["PCT_NAT_PFT"].size==15
                    and "natpft" in d["PCT_NAT_PFT"].dimensions,
                    "Host 15-PFT layout unknown "+site)
            require(d["PCT_SAND"].size>=10 and d["PCT_CLAY"].size>=10,
                    "Surface model layer soil layout unexpected "+site)
        require(abs(lat-surf["lat"])<.0001 and
                abs((lon-surf["lon"]+180)%360-180)<.0001,
                "User original tower coordinates don't match source surface "+site)
        hosts=pct(json.loads(pfts[site]["clm_pct_nat_pft_json"]),site)
        results.append({"site":site,"first_year":int(a["first_year"]),
          "last_year":int(a["last_year"]),"meteorology_SHA256":m["source_SHA256"],
          "meteorology_path":m["source_path"],
          "source_surface_SHA256":surf["SHA256"],
          "source_surface_path":str(surffile),
          "model_tower_coordinates":[lat,lon],
          "science_host_PFT_slots":hosts,
          "recommended_PFT":pfts[site]["recommended_percent"],
          "uncertainty":pfts[site]["uncertainty"],
          "FATES_mapping_profile":pfts[site]["mapping_profile"],
          "soil_recommended_0_30cm":{
            "sand":float(soils[site]["PCT_SAND_0_30cm"]),
            "clay":float(soils[site]["PCT_CLAY_0_30cm"]),
            "evidence_tier":soils[site]["tier"]},
          "soil_10_layer_observed_adopted":False,
          "site_ZBOT_verified":False,
          "source_time_centering_verified_in_active_CIME":False,
          "FATES_param_map_site_verified":False,
          "model_scenario_approved":False})
        print("AMF_B04 SOURCE PASS",site,"MET_SHA",m["source_SHA256"],
              "SURFACE_SHA",surf["SHA256"],
              "PFT_PROFILE",pfts[site]["mapping_profile"],
              "PFT_HLM",hosts,"SOIL",soils[site]["tier"],flush=True)
    require(len(results)==10,"Not ten source-audited sites")
    print("AMF_B04 TEN SITE SYVH9 MET + SYVH12 SURFACE SOURCE AUDIT PASS 10/10")
    return results,meta,sha_values()
def sha_values():
    return {"PFT_snapshot":sh(PFT),"SOIL_snapshot":sh(SOIL),
            "source_surface_register":sh(REGISTER),
            "SYVH9_manifest":sh(SOURCE/"RESEARCH_TEN_SITE_MANIFEST.tsv"),
            "SYVH12_surface_receipt":sh(SURF/"SYVH12_RESEARCH_SURFACES_RECEIPT.json")}
def plan(results,shas):
    rows=[]
    for site in results:
        for arm,flags in ARMS.items():
            rows.append({
              "site":site["site"],"arm":arm,
              "case_name_proposed":site["site"]+"_AMF_B04_"+
                   ("FULL" if arm.startswith("FULL") else "FIXNC")+"_AD400",
              "AD400_years":400,"AD_first_smoke":5,"AD_continue_after_success":395,
              "Normal400_years":400,"Normal_first_smoke":5,
              "Normal_continue_after_success":395,
              "forcing_source_sha256":site["meteorology_SHA256"],
              "surface_source_sha256":site["source_surface_SHA256"],
              "PFT_model_hypothesis":site["recommended_PFT"],
              "fates_PFT_mapping_profile":site["FATES_mapping_profile"],
              "case_flags_desired_requires_CTSM_build_verification":flags,
              "common_input_PFT_policy":"SHARED_PER_SITE_IDENTICAL_PRESCRIBED_START",
              "active_DATM":None,"active_surface":None,"active_FATES_param":None,
              "actual_CIME_case_exists":False,"AD5_completed":False,
              "spinup_authorized":False,
              "submission_resource_guards":{
                 "min_soft_stack_KiB":65536,
                 "preferred_soft_stack_KiB":300000,
                 "accept_higher_or_unlimited_without_decrease":True,
                 "Slurm_PropagateResourceLimits_must_include":"ALL_OR_STACK",
                 "guard_import":"scripts/b04_stack_guard.py",
                 "guard_before_each_CIME_case_submit":True,
                 "check_every_phase":["AD5","AD395","NORMAL5","NORMAL395"],
                 "attempt_before_submit_ledger_mandatory":True,
                 "current_model_submission_allowed":False},
              "HOLD":["ZBOT","DATM_UTC_TIME_CENTER",
                      "MODEL_SURFACE_RECOMMENDED_PFT_SITE_SPECIFIC",
                      "SOIL_CLM10_AND_ORGANIC","FATES_MAPPING",
                      "REAL_CASE_CIME_CO2_PTS_GEOMETRY"]})
    return {"cohort":"AmeriFlux_Batch04_10",
            "status":"PAIRED_EXPERIMENT_REGISTER_RESEARCH_ONLY_NO_MODEL_CASES",
            "source_receipts":shas,"protocol":"AD400_THEN_NORMAL400_PER_ARM",
            "arms":{"FULL_FATES_COMPETITION":ARMS["FULL_FATES_COMPETITION"],
                    "FIXED_BIOGEOG_NO_COMPETITION":ARMS[
                       "FIXED_BIOGEOG_NO_COMPETITION"]},
            "model_surface_policy":SURFACE_MODEL,
            "sites":results,"experiments":rows,
            "fates_ad_spinup_state":2,
            "fates_normal_spinup_state":"REMOVE_AD_ACCELERATION_PARAMETER",
            "paired_model_runs_not_submitted":True,
            "stack_policy": {
              "Source":"AmeriFlux Batch01 Stage21 65536KiB gate",
              "minimum_soft_KiB":65536,
              "prefer_soft_KiB":300000,
              "never_reduce_high_or_unlimited":True,
              "verify_Slurm_PropagateResourceLimits":"STACK_OR_ALL",
              "enforce_for_AD5_AD395_Normal5_Normal395":True,
              "live_cases_exist":False,
              "model_jobs_submitted":False}}
def main():
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    for x in ("self-test","audit","plan"):group.add_argument("--"+x,action="store_true")
    a=ap.parse_args()
    _,pft,soil=config()
    if a.self_test:
        require(len(SITES)==10 and len(ARMS)==2 and
                len(ARCTIC)==1 and
                pct(json.loads(pft["US-Uaf"]["clm_pct_nat_pft_json"]),"US-Uaf")
                and len(soil)==10,"Synthetic register/source experiment test failed")
        print("AMF_B04 PAIR SELF-TEST PASS 10 sites, 2 independent FATES arms, 800y per arm; NO WRITES")
        return
    sites,_,shas=audit()
    if a.audit:
        print("AMF_B04 AUDIT READONLY; 20 PROPOSED ARMS MODEL_NOT_READY")
        return
    p=plan(sites,shas)
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/("paired_FATES_FIXNC_AD400_Normal400_plan_"+
       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid4().hex[:8]+".json")
    target.write_text(json.dumps(p,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("AMF_B04 PAIRED EXPERIMENT PLAN 20 ARM ENTRIES CREATED",target)
    print("AMF_B04 GATE HOLD ZBOT DATM UTC CLOCK FATES PARAM PFT SOIL ORGANIC PTS CO2")
    print("NO SOURCE/SURFACE/CASE/DATM/MODEL/SLURM WRITES")
if __name__=="__main__":main()
