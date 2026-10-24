#!/usr/bin/env python3
"""Batch01 Stage09: CZ-BK1 read-only AD5 inputs gate, NOT an AD case builder.

Takes the successful Stage08 JSON. Inspects the ORIGINAL CZ-BK1 case's generated
DATM configurations, selected XML state, FATES parameter/mapping references,
existing model executable, and soil-layer metadata. Prints evidence only and
writes a new report under HOME. Does NOT modify old source files or CIME/Slurm.

Usage:
  python3 -B examples/Batch01_10/scripts/09_CZ_BK1_AD5_input_gate_readonly.py --self-test
  python3 -B examples/Batch01_10/scripts/09_CZ_BK1_AD5_input_gate_readonly.py \
    --stage08 "$HOME/Batch01_10_stage08_soil_preflight_20261024T104122Z/all_sites.json"
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[3]
CASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases/CZ-BK1_FATES_SPINUP500")
SITE_ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CZ-BK1")
CTSM = Path("/iridisfs/scratch/ly3n24/CLM_FATES/CTSM")
DOCS = (
    "CaseDocs/lnd_in", "CaseDocs/datm_in", "CaseDocs/datm.streams.xml",
    "user_nl_clm", "user_nl_datm_streams", "user_nl_datm",
    "Buildconf/datm.input_data_list",
)
XML_KEYS = (
    "RUN_STARTDATE", "RUN_TYPE", "RUNDIR", "EXEROOT", "COMPSET",
    "DATM_MODE", "DATM_YR_START", "DATM_YR_END", "DATM_YR_ALIGN",
    "CALENDAR", "CLM_ACCELERATED_SPINUP", "CLM_CO2_TYPE",
    "CCSM_CO2_PPMV", "DATM_CO2_TSERIES",
)
TOPICS = (
    "datm", "streams", "datafiles", "domain", "datadir", "filepaths",
    "year_first", "year_last", "year_align", "tintalgo",
    "fates", "fsurdat", "soil_layerstruct", "co2", ".nc",
)
MAX_TEXT = 2_000_000

def stop(s):
    raise SystemExit(str(s))

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def safe_text(path):
    if path.is_symlink():
        return None,"SYMLINK_REFUSED"
    if not path.is_file():
        return None,"ABSENT"
    if path.stat().st_size > MAX_TEXT:
        return None,"TEXT_TOO_LARGE"
    try:
        return path.read_text(encoding="utf8",errors="replace"),"OK"
    except OSError as exc:
        return None,"READ_ERROR:"+repr(exc)

def xml_data():
    result={}
    for fn in ("env_run.xml","env_case.xml","env_build.xml"):
        raw,status=safe_text(CASE/fn)
        if status!="OK":
            result["_STATUS_"+fn]=status
            continue
        try:
            root=ET.fromstring(raw)
        except ET.ParseError as err:
            result["_ERROR_"+fn]=str(err)
            continue
        for ent in root.iter("entry"):
            if ent.get("id") in XML_KEYS:
                result[ent.get("id")]=ent.get("value")
    return result

def inspect_doc(file):
    raw,status=safe_text(file)
    item={"path":str(file),"status":status}
    if status!="OK":
        return item
    item["sha256"]=sha(file)
    item["matched_lines"]=[]
    for lineno,line in enumerate(raw.splitlines(),1):
        x=line.strip()
        if not x or x.startswith("#"):
            continue
        if any(secret in x.lower() for secret in
               ("password","private_key","api_key","token=")):
            continue
        if any(topic in x.lower() for topic in TOPICS):
            item["matched_lines"].append({"line":lineno,"text":x[:250]})
            if len(item["matched_lines"])>=65:
                break
    item["year_field_candidates"]={
        key:sorted(set(re.findall(
            r"(?im)(?:^|[\s<])"+key+r"\s*(?:=|:|>)\s*['\"]?(\d{4})\b",
            raw)))
        for key in ("year_first","year_last","year_align")
    }
    return item

def collect_docs(xml):
    paths=[CASE/rel for rel in DOCS]
    case_docs=CASE/"CaseDocs"
    if case_docs.is_dir():
        paths += sorted(case_docs.glob("datm.streams.*"))[:20]
    rundir=xml.get("RUNDIR","")
    if isinstance(rundir,str) and rundir.startswith("/"):
        p=Path(rundir)
        if p.is_dir():
            paths += [p/n for n in ("lnd_in","datm_in","datm.streams.xml")]
            paths += sorted(p.glob("datm.streams.*"))[:20]
    seen=set()
    result=[]
    for p in paths:
        if str(p) not in seen:
            seen.add(str(p))
            result.append(inspect_doc(p))
    return result

def checks(stage8):
    if stage8.name!="all_sites.json" or not stage8.parent.name.startswith(
            "Batch01_10_stage08_soil_preflight_") or not stage8.is_file():
        stop("Expected Stage08 saved JSON in timestamped report directory")
    doc=json.loads(stage8.read_text(encoding="utf8"))
    if any(doc.get(k) is not False for k in (
            "old_source_modified", "new_surface_modified",
            "new_case_created", "slurm_submitted")):
        stop("Stage08 safety flags invalid")
    cz=doc.get("site_science",{}).get("CZ-BK1",{})
    if cz.get("soil_selection",{}).get("reported_pct")!={
            "sand":22,"silt":58,"clay":21}:
        stop("Stage08 approved CZ-BK1 texture does not match")
    if not CASE.is_dir():
        stop("CZ original case missing: "+str(CASE))
    return cz

def run(path):
    cz=checks(path)
    xml=xml_data()
    documents=collect_docs(xml)
    input_dir=SITE_ROOT/"forcing"
    forcing_subdirs=[]
    if input_dir.is_dir():
        forcing_subdirs=[str(p) for p in sorted(input_dir.iterdir())
                         if p.is_dir()][:70]
    exe_base=xml.get("EXEROOT")
    exe=Path(exe_base)/"cesm.exe" if isinstance(exe_base,str) and exe_base.startswith("/") else None
    params=CTSM/"src/fates/parameter_files/fates_params_default.json"
    param_doc={"path":str(params),"present":params.is_file()}
    if params.is_file() and params.stat().st_size<10_000_000:
        param_doc["sha256"]=sha(params)
    report={
        "site":"CZ-BK1",
        "source_stage08":str(path),"stage08_sha256":sha(path),
        "published_CZ_soil":cz["soil_selection"],
        "original_reference_case":str(CASE),
        "reference_case_xml":xml,
        "reference_case_documents":documents,
        "existing_forcing_subdirectories":forcing_subdirs,
        "FATES_default_parameters":param_doc,
        "reference_executable":{
            "path":str(exe) if exe else None,
            "present":bool(exe and exe.is_file()),
            "bytes":exe.stat().st_size if exe and exe.is_file() else None
        },
        "technical_next_gates":{
            "DATM":"CONFIRM_EFFECTIVE_STREAM_YEARS_FILES_AND_NOLEAP",
            "FATES":"CONFIRM_HLM_PFT_MAP_FIXED_BIOGEOG_AND_NOCOMP_EXECUTABLE",
            "SOIL":"APPROVE_EXPLICIT_DEPTH_EXTRAPOLATION_POLICY_AND_SOIL_PHYSICS",
            "SURFACE":"BUILD_NEW_VERSIONED_CZ_SURFACE_NATVEG100_CROP0",
            "AD5":"NEW_INDEPENDENT_CIME_CASE; FIVE_YEAR_SMOKE_ONLY_AFTER_PREFLIGHT"
        },
        "production_case_created":False,
        "source_modified":False,
        "slurm_submitted":False,
    }
    print("STAGE09 CZ-BK1 | AD5 INPUT GATE | READ ONLY")
    print("REFERENCE_XML:",{k:xml.get(k) for k in
          ("RUN_STARTDATE","DATM_MODE","DATM_YR_START","DATM_YR_END",
           "DATM_YR_ALIGN","CALENDAR","EXEROOT")})
    print("REFERENCE_EXE_EXISTS:",report["reference_executable"]["present"])
    print("FATES_PARAM_EXISTS:",param_doc["present"])
    print("EXISTING_FORCING_DIRS:",len(forcing_subdirs))
    for d in documents:
        print("\nDOCUMENT:",d["path"],d["status"])
        for line in d.get("matched_lines",[])[:28]:
            print(f"  {line['line']}: {line['text']}")
    out=(Path.home().resolve()/
         ("Batch01_10_stage09_CZ_AD5_inputs_"+datetime.now(
             timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    out.mkdir(mode=0o700,exist_ok=False)
    report_path=out/"all_sites.json"
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("\nREPORT:",report_path)
    print("NO SOURCE MODIFICATIONS, NO SURFACE BUILDS, NO SLURM JOBS.")
    print("NOT YET APPROVED TO SUBMIT AD5.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage08",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        assert re.findall(r"(?im)(?:^|[\s<])year_first\s*(?:=|:|>)\s*['\"]?(\d{4})\b",
                          "year_first=2018") == ["2018"]
        assert len(DOCS)==7
        print("STAGE09 SELF-TEST PASS | read-only config scanner, no jobs")
        return
    if a.stage08 is None:
        p.error("--stage08 required")
    run(a.stage08.expanduser().resolve())

if __name__=="__main__":
    main()
