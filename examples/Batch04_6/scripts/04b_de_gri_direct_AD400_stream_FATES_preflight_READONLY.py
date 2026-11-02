#!/usr/bin/env python3
"""ICOS Batch04 Stage04B: direct AD400 DE-Gri template stream and FATES audit.

Uses Stage04A verified static evidence. No original source/case writes,
no CIME case creation, no model execution, no Slurm submission.
"""
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path

SITE="DE-Gri"
CASEROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
CTSM=Path("/iridisfs/scratch/ly3n24/CLM_FATES/CTSM")
OUTPUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
NEW_NAME="DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT"
TARGET=CASEROOT/NEW_NAME
RUN=OUTPUT/NEW_NAME/"run"
ARCH=OUTPUT/"archive"/NEW_NAME
TEMPLATE=CASEROOT/"DE-Gri_FATES_SPINUP1000_S30SHARED"
STREAM="CLM_USRDAT.UNSET"
FIELDS=["datafiles","year_first","year_last","year_align","offset","taxmode","tintalgo","mapalgo","meshfile","datavars"]
def need(ok,msg):
    if not ok:raise ValueError(msg)
def hashfile(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for x in iter(lambda:f.read(1048576),b""):h.update(x)
    return h.hexdigest()
def small(path,limit=1000000):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>limit:return None
    return path.read_text(encoding="utf-8",errors="replace")
def nml_lines(t):
    found={}
    for line in t.splitlines():
        m=re.match(r"^\s*([A-Za-z_][\w]*)\s*=\s*(.*?)\s*(?:!.*)?$",line)
        if m:found.setdefault(m.group(1).lower(),[]).append(m.group(2))
    return found
def stream_entries(t):
    found={}
    regex=re.compile(r"(?m)^[ \t]*([A-Za-z][\w.\-]*):([A-Za-z_]\w*)[ \t]*=")
    markers=list(regex.finditer(t))
    for i,m in enumerate(markers):
        end=markers[i+1].start() if i+1<len(markers) else len(t)
        found.setdefault(m.group(1),{}).setdefault(m.group(2),[]).append(t[m.end():end].strip())
    return found
def xml_stream(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>1000000:return {"present":False}
    root=ET.parse(path).getroot()
    blocks=[e for e in root.iter("stream_info") if e.get("name")==STREAM]
    if len(blocks)!=1:return {"present":True,"USRDAT_count":len(blocks)}
    x=blocks[0]
    dat=x.find("datafiles")
    return {"present":True,"USRDAT_count":1,
            "datafiles":[(e.text or "").strip() for e in dat] if dat is not None else [],
            "settings":{k:(x.findtext(k) or "").strip() for k in FIELDS if k!="datafiles"},
            "other_streams":[e.get("name") for e in root.iter("stream_info") if e.get("name")!=STREAM],
            "sha256":hashfile(path)}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage04a",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:
        t="CLM_USRDAT.UNSET:datafiles = /a/DE-Gri_DATM_2004.nc,/b/DE-Gri_DATM_2005.nc\nCLM_USRDAT.UNSET:taxmode = cycle\n"
        z=stream_entries(t)
        assert z[STREAM]["taxmode"]==["cycle"] and len(z[STREAM]["datafiles"])==1
        assert len(nml_lines("spinup_state = 2\nfsurdat='/x.nc'")["spinup_state"])==1
        print("STAGE04B SELF-TEST PASS | private stream parser, NO CASE OR JOB");return
    need(a.stage04a is not None and a.stage04a.is_file(),"Stage04A report missing")
    need(a.out is not None and a.out.parent.is_dir() and not a.out.exists() and not a.out.is_symlink(),"Output must be a new file")
    r=json.loads(a.stage04a.read_text(encoding="utf-8"))
    need(r.get("stage")=="STAGE04A_BATCH04_DE_GRI_DIRECT_AD400_TECHNICAL_PREFLIGHT" and
         r.get("site")==SITE and r.get("science_release") is False and
         r.get("AD400_submission_authorized") is False and r.get("read_only") is True,
         "Stage04A must be the verified science-HOLD report")
    need(len(r.get("annual_DATM_22_path_list",[]))==22,"Annual data list mismatch")
    templates=[t for t in r.get("templates",[]) if t.get("name")==TEMPLATE.name]
    need(len(templates)==1 and templates[0]["template_technically_candidate"] is True,"S30SHARED failed Stage04A")
    need(TEMPLATE.is_dir() and not TEMPLATE.is_symlink(),"Original template missing/unsafe")
    nc=r["annual_DATM_22_path_list"]
    need([int(x["year"]) for x in nc]==list(range(2004,2026)),"22 annual years not ordered 2004–2025")
    need({int(x["year"]) for x in nc if x["kind"]=="approved_sensitivity"}=={2011,2024},"Override years wrong")
    expected=[x["path"] for x in nc]
    need(all(Path(q).is_file() for q in expected),"One or more planned DATM NC missing")
    sn=small(TEMPLATE/"user_nl_datm_streams")
    ln=small(TEMPLATE/"user_nl_clm")
    ex=xml_stream(TEMPLATE/"CaseDocs/datm.streams.xml")
    old=stream_entries(sn) if sn is not None else {}
    val=old.get(STREAM,{})
    usr={k:len(val.get(k,[])) for k in FIELDS}
    src_dat=val.get("datafiles",[""])[0].strip("'\"") if len(val.get("datafiles",[]))==1 else ""
    usrfiles=[v.strip().strip("'\"") for v in src_dat.split(",") if v.strip()]
    old_lnd=nml_lines(ln) if ln is not None else {}
    paramline=old_lnd.get("fates_paramfile",[])
    params=Path(paramline[0].strip("'\"")) if len(paramline)==1 else None
    flags={
      "original_case_script_present":(CTSM/"cime/scripts/create_clone").is_file(),
      "new_case_path_absent":not TARGET.exists() and not TARGET.is_symlink(),
      "new_run_path_absent":not RUN.exists() and not RUN.is_symlink(),
      "new_archive_path_absent":not ARCH.exists() and not ARCH.is_symlink(),
      "user_nl_clm_present":ln is not None,
      "user_nl_datm_streams_present":sn is not None,
      "user_stream_all_required_fields_unique":all(usr.get(k)==1 for k in FIELDS if k!="offset") and usr.get("offset") in (0,1),
      "CIME_generated_original_USRDAT_present":ex.get("USRDAT_count")==1,
      "user_stream_22_original_files":len(usrfiles)==22 and all("DE-Gri_DATM_" in v for v in usrfiles),
      "FATES_paramfile_declared_and_exists":bool(params and params.is_file()),
      "verified_AD_spinup_state_in_template":old_lnd.get("spinup_state")==["2"],
      "template_no_unexpected_finidat":not old_lnd.get("finidat") or all(not q.strip("'\" ") for q in old_lnd.get("finidat",[])),
      "surface_candidate_exists":Path(r["candidate_surface"]).is_file(),
      "surface_SHA_stable":hashfile(Path(r["candidate_surface"]))==r["candidate_surface_sha256"],
    }
    result={"site":SITE,"stage":"STAGE04B_DE_GRI_DIRECT_AD400_TEMPLATE_STREAM_AND_FATES_PREFLIGHT",
        "read_only":True,"science_release":False,"AD400_authorized":False,
        "target_new_case":str(TARGET),"target_run":str(RUN),"target_archive":str(ARCH),
        "template_case":str(TEMPLATE),"templates_new_case_required":True,
        "checks":flags,"technical_ready_for_isolated_case_prepare":all(flags.values()),
        "original_user_nl_stream_fields_counts":usr,"original_user_nl_stream_datafiles_count":len(usrfiles),
        "original_stream_first_two":usrfiles[:2],"original_stream_last_two":usrfiles[-2:],
        "old_stream_usrd_years":{k:val.get(k,[])[:1] for k in ("year_first","year_last","year_align","taxmode")},
        "generated_stream_USRDAT_count":ex.get("USRDAT_count"),"generated_stream_file_count":len(ex.get("datafiles",[])),
        "generated_stream_non_USRDAT":ex.get("other_streams",[]),
        "FATES_paramfile":str(params) if params else None,
        "FATES_namelist":{k:old_lnd.get(k) for k in ("use_fates","use_fates_sp",
          "use_fates_nocomp","use_fates_fixed_biogeog","spinup_state","finidat","fates_paramfile")},
        "planned_22_files":nc,
        "future_CIME_settings":{"RUN_TYPE":"startup","RUN_STARTDATE":"2004-01-01",
          "CONTINUE_RUN":"FALSE","CLM_ACCELERATED_SPINUP":"on",
          "CLM_FORCE_COLDSTART":"on","STOP_OPTION":"nyears","STOP_N":"5",
          "REST_OPTION":"nyears","REST_N":"5","RESUBMIT":"79",
          "RESUBMIT_SETS_CONTINUE_RUN":"TRUE","DATM_YR_START":"2004",
          "DATM_YR_END":"2025","DATM_YR_ALIGN":"2004"},
        "no_AD5_separate_trial":True,"no_CIME_or_Slurm_modified":True,
        "operator_decisions_pending":"PFT proxy/soil provenance; 49 MDS flags and rainfall clock still science HOLD"}
    with a.out.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print("STAGE04B DE-GRI DIRECT AD400 | SOURCE SCIENCE HOLD | READ ONLY")
    for k,v in flags.items():print("CHECK",k,"PASS" if v else "HOLD")
    print("TEMPLATE USRDAT datafiles",len(usrfiles),"GENERATED_STREAM_FILES",len(ex.get("datafiles",[])))
    print("FATES",str(params) if params else "MISSING",
          "SPINUP_STATE",old_lnd.get("spinup_state","MISSING"))
    print("TECHNICAL_READY_TO_PREPARE_ISOLATED_CASE",result["technical_ready_for_isolated_case_prepare"])
    print("NEW_CASE_NAME",NEW_NAME,"DIRECT_400=80x5, RESUBMIT79, NO AD5")
    print("NO CASE OR JOB CREATED | PRIVATE_REPORT",a.out)
if __name__=="__main__":main()
