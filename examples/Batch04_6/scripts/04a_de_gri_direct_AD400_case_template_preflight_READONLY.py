#!/usr/bin/env python3
"""DE-Gri Batch04 direct AD400 preflight of archived evidence and CIME templates.

Reads prior SHA-verified science reports and two existing ORIGINAL template cases.
Never modifies any CIME case, annual forcing, surface, FATES file, or Slurm.
This is NOT science release and NOT authority to submit AD400.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
SITE="DE-Gri"
NEEDED={"BUILD_COMPLETE","EXEROOT","DATM_MODE","CALENDAR","ATM_NCPL","RUN_STARTDATE","CLM_ACCELERATED_SPINUP"}
KEYS=("BUILD_COMPLETE","EXEROOT","DATM_MODE","CALENDAR","ATM_NCPL","RUN_STARTDATE","CLM_ACCELERATED_SPINUP","COMPSET","STOP_OPTION","STOP_N","REST_OPTION","REST_N","RESUBMIT","RESUBMIT_SETS_CONTINUE_RUN")
def need(ok,reason):
    if not ok:raise ValueError(reason)
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def query(case,key):
    try:
        p=subprocess.run([str(case/"xmlquery"),key,"--value"],cwd=case,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:return "ERROR:"+str(e)[:160]
    return p.stdout.strip() if p.returncode==0 else "ERROR:"+p.stderr.strip()[-180:]
def config_lnd(case):
    path=case/"CaseDocs/lnd_in"
    if not path.is_file() or path.is_symlink() or path.stat().st_size>2000000:return {}
    result={}
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        t=line.strip()
        for k in ("fsurdat","fates_paramfile","spinup_state","use_fates","use_fates_sp","fates_hlm_pft_map"):
            if t.lower().startswith(k+" ") or t.lower().startswith(k+"="):
                result[k]=t[:400]
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    for k in ("stage02y","stage02z","stage03v","stage03y"):p.add_argument("--"+k,type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:
        assert SITE=="DE-Gri" and len(KEYS)==14 and "EXEROOT" in KEYS
        assert "fates_paramfile" in ("fsurdat","fates_paramfile")
        print("STAGE04A SELF-TEST PASS | no case, model or Slurm writes")
        return
    paths=[a.stage02y,a.stage02z,a.stage03v,a.stage03y]
    need(all(q is not None and q.is_file() for q in paths),"Original four verified reports missing")
    need(a.out is not None and a.out.parent.is_dir() and not a.out.exists() and not a.out.is_symlink(),
         "Output must be new in an existing directory")
    y,z,v,r=[json.loads(q.read_text(encoding="utf-8")) for q in paths]
    need(y.get("stage")=="STAGE02Y_BATCH04_FOUR_SITE_CANDIDATE_SURFACE_STATIC_CIME_BINDING_AUDIT"
       and y.get("science_release") is False and y.get("read_only") is True,
       "Stage02Y expected source HOLD")
    need(z.get("stage")=="STAGE02Z_BATCH04_DATM_STREAM_DOCUMENT_FORENSICS_READONLY"
       and z.get("science_release") is False and z.get("original_case_count")==8,
       "Stage02Z static streams incomplete")
    need(v.get("site")==SITE and v.get("status")=="INPUT_PLAN_ONLY_NOT_MODEL_RELEASE"
       and v.get("source_science_or_soil_release") is False,"Stage03V not an unreleased verified plan")
    need(r.get("site")==SITE and r.get("stage")=="STAGE03Y_DE_GRI_VERIFIED_CANDIDATE_FLAG_PHYSICS"
       and r.get("AD400_submission_authorized") is False and len(r.get("years",[]))==2,
       "Stage03Y candidate test missing")
    sy=[s for s in y.get("sites",[]) if s.get("site")==SITE]
    need(len(sy)==1 and sy[0].get("PFT_selection_approved") is True,"DE-Gri approved PFT proxy missing")
    s=sy[0]; surf=s["surface"]
    sc=Path(surf["candidate_path"])
    need(surf.get("source_soil_unchanged") is True and sc.is_file()
         and sha(sc)==surf["candidate_sha"],"Candidate PFT surface SHA/soil source failed")
    need(0<=surf["soil_organic_min"]<=surf["soil_organic_max"]<=100,
         "Candidate inherited soil organic percentage invalid")
    annual=v.get("annual_inputs",[])
    need(len(annual)==22 and {int(t["year"]) for t in annual}==set(range(2004,2026)),
         "2004-2025 DATM plan incomplete")
    need({int(t["year"]) for t in annual if t["kind"]=="approved_sensitivity"}=={2011,2024},
         "Two sensitivity years missing")
    for t in annual:
        need(Path(t["path"]).is_file(),"Annual DATM missing "+str(t["year"]))
    oldcases=s["cases"]
    need(len(oldcases)==2 and {c["case"] for c in oldcases}==
         {c["case"] for c in z["cases"] if c["site"]==SITE},"Original template identity changed")
    templates=[]
    for rec in oldcases:
        name=rec["case"]
        case=BASE/name
        need(case.is_dir() and not case.is_symlink() and case.name==name,"Missing old case "+name)
        setting={key:query(case,key) for key in KEYS}
        docs=config_lnd(case)
        exe=Path(setting["EXEROOT"])/"cesm.exe" if setting["EXEROOT"] and not setting["EXEROOT"].startswith("ERROR:") else None
        flags={
          "CIME_query_no_errors":not any(x.startswith("ERROR:") for x in setting.values()),
          "build_complete":setting["BUILD_COMPLETE"].lower()=="true",
          "model_executable_exists":bool(exe and exe.is_file()),
          "datm_1pt":setting["DATM_MODE"]=="1PT",
          "noleap":setting["CALENDAR"].upper() in ("NO_LEAP","365_DAY"),
          "atm_half_hour":setting["ATM_NCPL"]=="48",
          "original_surface_not_candidate":rec["original_case_fsourced"]!=str(sc),
          "FATES_param_line_present":"fates_paramfile" in docs,
        }
        templates.append({"name":name,"case_dir":str(case),
          "xmlquery":setting,"lnd_in_selected_lines":docs,"checks":flags,
          "template_technically_candidate":all(flags.values()),
          "needs_new_cloned_case":True})
    obj={"stage":"STAGE04A_BATCH04_DE_GRI_DIRECT_AD400_TECHNICAL_PREFLIGHT",
         "site":SITE,"read_only":True,"science_release":False,
         "AD400_submission_authorized":False,"AD5_separate_trial_requested":False,
         "AD400_plan":"DIRECT_80x5_year_segments_REQUIRES_79_AUTO_RESUBMITS",
         "candidate_surface":str(sc),"candidate_surface_sha256":surf["candidate_sha"],
         "soil_source_unchanged":True,
         "soil_organic_min":surf["soil_organic_min"],
         "soil_organic_max":surf["soil_organic_max"],
         "original_soil_independent_science_release":False,
         "annual_DATM_22_path_list":annual,
         "2011_2024_corrected_candidate_physics":"PASS",
         "templates":templates,
         "technical_template_count":sum(t["template_technically_candidate"] for t in templates),
         "remaining_gates":["science uncertainty: 49 original MDS flagged blocks",
           "12 source-QC0 rainfall events: independent accumulation clock unverified",
           "site soil observed provenance/PFT footprint model proxy not measured",
           "new versioned CIME case and ACTUAL DATM stream must bind 20 baseline + 2 candidate files",
           "new case fsurdat and FATES param + run-directory namelist must match",
           "direct AD400 controller restart/archive/cycle and 79 resubmits before first submit"],
         "case_or_slurm_modified":False}
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False);f.write("\n")
    print("STAGE04A DE-GRI DIRECT AD400 CASE PREPREFLIGHT | SCIENCE HOLD")
    print("SURFACE_SHA PASS; SOIL ORGANIC",surf["soil_organic_min"],surf["soil_organic_max"],
          "| 22 ANNUAL DATM PATHS EXISTS; 2 SENSITIVITY YEARS")
    for t in templates:
        print("TEMPLATE",t["name"],"SUITABLE",t["template_technically_candidate"],
              "CHECKS",json.dumps(t["checks"],sort_keys=True))
        for key in ("EXEROOT","RUN_STARTDATE","CLM_ACCELERATED_SPINUP","COMPSET","STOP_OPTION","STOP_N","RESUBMIT"):
            print(" ",key,t["xmlquery"][key])
        for key,val in t["lnd_in_selected_lines"].items():print("  LND",key,val)
    print("NEXT: clone isolated new case, wire 22-year candidate DATM and surface; preflight direct AD400 80x5")
    print("NO CASE OR SLURM CREATED | PRIVATE_REPORT",a.out)

if __name__=="__main__":main()
