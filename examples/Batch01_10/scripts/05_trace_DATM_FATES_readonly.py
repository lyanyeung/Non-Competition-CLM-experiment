#!/usr/bin/env python3
"""Batch01 Stage05 — station-first effective CIME / DATM / FATES audit.

NO source surface percentages, PCT_SAND, PCT_CLAY, or CROP comparisons.
Input: Stage02 case_trace.json (already produced 2026-10-24).
Reads bounded original CIME text config and stream files only.
Writes a new timestamped HOME report. Never edits original cases/forcing,
old fsurdat or restarts, and never submits/cancels Slurm jobs.

python3 -B examples/Batch01_10/scripts/05_trace_DATM_FATES_readonly.py --self-test
python3 -B examples/Batch01_10/scripts/05_trace_DATM_FATES_readonly.py \
  --stage02 "$HOME/Batch01_10_stage02_case_trace_20261024T094433Z/case_trace.json"
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

SITES=("CZ-BK1","IT-Ren","RU-Fyo","CH-Dav","IT-Col",
       "FR-Fon","FI-Sod","FR-Pue","DE-Hai","BE-Vie")
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
DOCS=("CaseDocs/lnd_in","CaseDocs/datm_in",
      "CaseDocs/datm.streams.xml","user_nl_clm","user_nl_datm",
      "user_nl_datm_streams","Buildconf/datm.input_data_list")
CIME_KEYS=("DATM_MODE","DATM_YR_START","DATM_YR_END","DATM_YR_ALIGN",
           "RUN_STARTDATE","RUN_TYPE","CALENDAR","COMPSET",
           "CLM_ACCELERATED_SPINUP","CLM_CO2_TYPE","CCSM_CO2_PPMV",
           "DATM_CO2_TSERIES","STOP_N","STOP_OPTION","RESUBMIT",
           "RUNDIR","DOUT_S_ROOT","EXEROOT")
LND_KEYS=("use_fates","use_fates_sp","use_fates_nocomp",
          "use_fates_fixed_biogeog","fates_hlm_pft_map",
          "fates_paramfile","spinup_state","fsurdat","finidat")
MAX_TEXT=2_000_000

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def safe_read(path):
    if path.is_symlink():
        return None,"SYMLINK_NOT_FOLLOWED"
    if not path.is_file():
        return None,"MISSING"
    if path.stat().st_size>MAX_TEXT:
        return None,"TOO_LARGE"
    try:
        return path.read_text(encoding="utf8",errors="replace"),"OK"
    except OSError as exc:
        return None,"READ_ERROR:"+repr(exc)

def namelist_values(text):
    out={}
    for key in (*LND_KEYS,"year_first","year_last","year_align","streams"):
        hits=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*(.*?)\s*(?:!.*)?$",text)
        if hits:out[key]=hits[-1].strip()
    return out

def years_from_text(text):
    matches={}
    for key in ("year_first","year_last","year_align"):
        all_vals=re.findall(r"(?im)(?:^|[\s<])"+key+
                            r"\s*(?:=|:|>)\s*['\"]?(\d{4})\b",text)
        if all_vals:matches[key]=sorted(set(all_vals))
    return matches

def doc_info(path):
    raw,status=safe_read(path)
    result={"path":str(path),"status":status}
    if raw is None:return result
    result["sha256"]=sha(path)
    result["fields"]=namelist_values(raw)
    result["year_candidates_UNVERIFIED"]=years_from_text(raw)
    excerpts=[]
    for line in raw.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        if any(x in line.lower() for x in ("password","private_key","api_key","token=")):
            continue
        if any(x in line.lower() for x in
               ("datm","streams","year","datafiles","datadir","filepaths",
                "domain","tintalgo","fates","fsurdat",".nc")):
            excerpts.append(line[:230])
            if len(excerpts)>=16:break
    result["text_excerpts"]=excerpts
    return result

def xml_info(case):
    out={}
    for file in ("env_run.xml","env_case.xml","env_build.xml"):
        raw,status=safe_read(case/file)
        if raw is None:continue
        try:
            root=ET.fromstring(raw)
            for item in root.iter("entry"):
                key=item.get("id")
                if key in CIME_KEYS:out[key]=item.get("value")
        except ET.ParseError as err:
            out["XML_ERROR_"+file]=str(err)
    return out

def docs_for_case(case,xml):
    out=[]
    seen=set()
    def add(p):
        if str(p) not in seen:
            seen.add(str(p))
            out.append(p)
    for rel in DOCS:add(case/rel)
    case_docs=case/"CaseDocs"
    if case_docs.is_dir():
        for p in sorted(case_docs.glob("datm.streams.*"))[:20]:add(p)
    rundir=xml.get("RUNDIR")
    if isinstance(rundir,str) and rundir.startswith("/"):
        rp=Path(rundir)
        if rp.is_dir():
            for n in ("datm_in","lnd_in","datm.streams.xml"):add(rp/n)
            for p in sorted(rp.glob("datm.streams.*"))[:20]:add(p)
    return out[:65]

def inspect(site,row):
    name=row.get("case")
    path=Path(row.get("path",""))
    result={"case":name,"path":str(path),"read_status":"UNINSPECTED"}
    if path.parent!=ROOT or not isinstance(name,str) or not name.startswith(site+"_"):
        result["read_status"]="INVALID_CASE_PATH"
        return result
    if not path.is_dir():
        result["read_status"]="CASE_MISSING"
        return result
    x=xml_info(path)
    result["xml"]=x
    docs=[doc_info(p) for p in docs_for_case(path,x)]
    result["documents"]=docs
    result["read_status"]="CONFIG_SCANNED"
    lnd=[d for d in docs if d["status"]=="OK" and
         (d["path"].endswith("/lnd_in") or d["path"].endswith("/user_nl_clm"))]
    result["fates_original_case_flags"]=[
        {"file":d["path"],"flags":{k:v for k,v in d["fields"].items()
          if k in LND_KEYS}} for d in lnd]
    candidates={}
    for k,cime_key in (("year_first","DATM_YR_START"),
                       ("year_last","DATM_YR_END"),
                       ("year_align","DATM_YR_ALIGN")):
        vals=[]
        if x.get(cime_key):vals.append(str(x[cime_key]))
        for d in docs:
            vals+=d.get("year_candidates_UNVERIFIED",{}).get(k,[])
            if d.get("fields",{}).get(k):
                vals.append(d["fields"][k])
        candidates[k]=sorted(set(vals))
    result["datm_year_candidates_UNVERIFIED"]=candidates
    result["datm_files_read"]=[
        d["path"] for d in docs if d["status"]=="OK" and
        ("datm" in d["path"].lower() or "input_data_list" in d["path"].lower())]
    result["forcing_validation"]="NOT_YET_CHECKED_FILE_LIST_CALENDAR_QC"
    result["target_new_case_flags_NOT_APPLIED"]={
        "use_fates":".true.",
        "use_fates_sp":".false.",
        "use_fates_nocomp":".true.",
        "use_fates_fixed_biogeog":".true."}
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage02",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        assert len(SITES)==10 and len(set(SITES))==10
        assert namelist_values("use_fates_nocomp = .true.\n")["use_fates_nocomp"]==".true."
        assert years_from_text("<year_align>1997</year_align>")=={"year_align":["1997"]}
        print("STAGE05 SELF-TEST PASS — DATM/FATES only; no source surface comparison")
        return
    if args.stage02 is None:ap.error("--stage02 is required")
    p=args.stage02.expanduser().resolve()
    if p.name!="case_trace.json" or not p.parent.name.startswith(
        "Batch01_10_stage02_case_trace_") or not p.is_file():
        raise SystemExit("Expected original timestamped Stage02 case_trace.json")
    data=json.loads(p.read_text(encoding="utf8"))
    if data.get("files_changed_outside_new_report") is not False or (
            data.get("slurm_submitted") is not False):
        raise SystemExit("Stage02 safety flags invalid")
    sites=data.get("sites",[])
    if tuple(row.get("site") for row in sites)!=SITES:
        raise SystemExit("Unexpected ten-site Stage02 membership")
    items=[]
    print("=== BATCH01 STAGE05: ACTUAL DATM / FATES CONFIG ONLY ===")
    print("STATION FIRST: NATVEG=100/CROP=0 target assumption; no old-grid soil or landcover used.")
    for row in sites:
        name=row["site"]
        cases=[inspect(name,c) for c in row.get("cases",[])]
        items.append({"site":name,"existing_cases":cases,
                      "landunit_model_assumption":{"PCT_NATVEG":100,"PCT_CROP":0},
                      "soil_policy":"STATION_FIELD_MEASURED_ONLY; NO_GRID_VALUE_TRANSFER",
                      "release":"HOLD_NEW_CASE_UNTIL_FORCING_MAPPING_SOIL_READY"})
        print(f"\n{name} CASES={len(cases)}  TARGET=FOREST_NATVEG100 CROP0")
        if len(cases)!=1:
            print("  REVIEW: MULTIPLE_OR_MISSING_ORIGINAL_CASES")
        for case in cases:
            print("  CASE",case["case"],case["read_status"])
            print("  XML DATM",[(k,case.get("xml",{}).get(k)) for k in
                  ("DATM_MODE","DATM_YR_START","DATM_YR_END","DATM_YR_ALIGN")])
            print("  DATM year candidates [first,last,align]:",
                  case.get("datm_year_candidates_UNVERIFIED",{}))
            print("  READABLE DATM CONFIG DOCS:",len(case.get("datm_files_read",[])))
            for item in case.get("fates_original_case_flags",[])[:2]:
                print("  SOURCE FATES FLAGS",item["file"],item["flags"])
    now=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=Path.home().resolve()/("Batch01_10_stage05_station_inputs_"+now)
    out.mkdir(mode=0o700,exist_ok=False)
    payload={"source_stage02":str(p),"stage02_sha256":sha(p),
             "input_sources_modified":False,"slurm_submitted":False,
             "source_surface_science_comparison_used":False,
             "run_time_utc":datetime.now(timezone.utc).isoformat(),"sites":items}
    output=out/"all_sites.json"
    output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",
                      encoding="utf8")
    print("\nJSON:",output)
    print("NO OLD SURFACE COMPARISON, NO CIME/SLURM MODIFICATIONS")

if __name__=="__main__":
    main()
