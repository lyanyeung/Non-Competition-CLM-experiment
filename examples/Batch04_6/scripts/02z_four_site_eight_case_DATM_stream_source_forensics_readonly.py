#!/usr/bin/env python3
"""Batch04 Stage02Z: targeted CIME DATM stream forensic after Stage02Y.

READ ONLY. Stage02Y showed eight original CaseDocs/datm_in with no parsed
'streams' assignment, while original Buildconf/datm.input_data_list and
new candidate point surface hashes pass. The missing parsed field is NOT
evidence that DATM was missing at runtime. This tool inspects exactly the
eight source-pinned original case dirs and bounded generated CIME documents,
printing original source lines, env XML entries, and stream-document
evidence. It does not use 'case.setup', 'preview_namelists', 'xmlchange',
or any model/Slurm command. Only two reports in NEW EMPTY --out-dir.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_STAGE="STAGE02Y_BATCH04_FOUR_SITE_CANDIDATE_SURFACE_STATIC_CIME_BINDING_AUDIT"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
YEARS={"DE-Gri":22,"DE-RuR":15,"IT-Tor":18,"ES-Agu":19}
CASE_ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
XML_FIELDS=("DATM_MODE","DATM_CLMNCEP_YR_START","DATM_CLMNCEP_YR_END",
            "DATM_CLMNCEP_YR_ALIGN","RUNDIR","RUN_STARTDATE","RUN_TYPE",
            "CALENDAR","STOP_N","STOP_OPTION","REST_N","RESUBMIT",
            "CLM_ACCELERATED_SPINUP","DATM_PRESAERO")
SCOPED_DOCS=("CaseDocs/datm_in","CaseDocs/lnd_in",
             "Buildconf/datm.input_data_list","user_nl_datm",
             "env_run.xml","env_case.xml")
STREAM_EXCERPT=re.compile(
    r"streams|filenames|fileNames|filepath|dataSource|taxmode|year_"
    r"|datm_|domain|stream|(?:^|[^a-z])file(?:$|[^a-z])",re.I)
ASSIGN=re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:!.*)?$",re.I)
CSV_COLUMNS=("site","case","stage02y_DATM_annual_refs",
             "CaseDocs_datm_in_status","CaseDocs_datm_in_stream_assignment_count",
             "CaseDocs_datm_in_present",
             "CaseDocs_stream_docs_count","CaseDocs_stream_docs_with_site_token",
             "CaseDocs_stream_docs_with_site_DATM_annual",
             "CaseDocs_datm_in_original_lines_json",
             "stream_doc_excerpt_json","env_run_DATM_MODE",
             "env_run_RUN_TYPE","env_run_RUNDIR",
             "actual_runtime_DATM_binding_verified",
             "native_tower_source_QC_verified",
             "model_release")


def digest(file):
    h=hashlib.sha256()
    with file.open("rb") as f:
        for piece in iter(lambda:f.read(128*1024),b""):
            h.update(piece)
    return h.hexdigest()


def safe_read(file,maximum=500_000):
    if not file.is_file():
        return {"status":"MISSING","path":str(file)}
    if file.is_symlink():
        return {"status":"SYMLINK_NOT_READ","path":str(file)}
    if file.stat().st_size>maximum:
        return {"status":"OVER_BOUNDED_LIMIT","path":str(file),"bytes":file.stat().st_size}
    raw=file.read_text(encoding="utf-8",errors="replace")
    return {"status":"READ","path":str(file),"bytes":file.stat().st_size,
            "sha256":digest(file),"lines":raw.splitlines(),"text":raw}


def selection(text,limit=25):
    return [{"line":i,"raw":line.strip()[:650]}
            for i,line in enumerate(text.splitlines(),1)
            if STREAM_EXCERPT.search(line)][:limit]


def read_datm(file):
    info=safe_read(file)
    if info["status"]!="READ":
        return info
    matches={}
    for i,line in enumerate(info["lines"],1):
        match=ASSIGN.match(line)
        if match:
            key=match.group(1).lower()
            if key in ("streams","stream","taxmode","mapalgo","year_first",
                       "year_last","year_align","dtlimit","fillalgo","dtlimit",
                       "readmode","restfilm"):
                matches.setdefault(key,[]).append({"line":i,"raw":line.strip()[:1000]})
    return {"status":"READ","path":info["path"],"bytes":info["bytes"],
            "sha256":info["sha256"],"line_count":len(info["lines"]),
            "assignments":matches,"relevant_lines":selection(info["text"],50),
            "first_lines":[{"line":i,"raw":x[:480]}
                           for i,x in enumerate(info["lines"][:12],1)]}


def read_xml(path):
    info=safe_read(path,1_000_000)
    if info["status"]!="READ":
        return {"status":info["status"],"path":str(path)}
    try:
        tree=ET.fromstring(info["text"])
    except ET.ParseError as e:
        return {"status":"XML_PARSE_FAILED","reason":str(e),"path":str(path)}
    vals={}
    for el in tree.iter("entry"):
        key=el.attrib.get("id")
        if key in XML_FIELDS:
            vals[key]=el.attrib.get("value")
    return {"status":"READ","path":str(path),"sha256":info["sha256"],"entries":vals}


def validate_stage(report):
    if report.get("stage")!=EXPECTED_STAGE or \
       report.get("read_only") is not True or \
       report.get("science_release") is not False or \
       report.get("slurm_submitted") is not False:
        raise ValueError("Require source-verified Stage02Y read-only science HOLD JSON")
    sites=report.get("sites",[])
    if not isinstance(sites,list) or [x.get("site") for x in sites]!=list(SITES):
        raise ValueError("Stage02Y needs exactly four expected sites in order")
    out=[]
    for item in sites:
        cases=item.get("cases",[])
        if len(cases)!=2:
            raise ValueError("Expected exactly two original CIME source cases/site")
        for c in cases:
            site=item["site"]
            name=c.get("case","")
            if name not in (f"{site}_FATES_SPINUP1000_S30EXCL",
                            f"{site}_FATES_SPINUP1000_S30SHARED"):
                raise ValueError("Unexpected original case "+name)
            if c.get("Stage02V_exact_site_file_references")!=YEARS[site] or \
               c.get("Stage02V_static_path_match") is not True or \
               c.get("candidate_surface_not_yet_bound") is not True or \
               c.get("model_release")!="HOLD":
                raise ValueError("Original case source path or science HOLD changed")
            out.append((site,name))
    if len(out)!=8 or len(set(out))!=8:
        raise ValueError("Incomplete original case set")
    return out


def audit_case(root,site,name):
    case=root/name
    if not case.is_dir() or case.is_symlink() or case.name!=name:
        raise ValueError("Original case absent, unexpected or symlink "+name)
    datm=read_datm(case/"CaseDocs/datm_in")
    lnd=read_datm(case/"CaseDocs/lnd_in")
    envrun=read_xml(case/"env_run.xml")
    envcase=read_xml(case/"env_case.xml")
    datm_list=safe_read(case/"Buildconf/datm.input_data_list",4_000_000)
    docs=case/"CaseDocs"
    streamfiles=[]
    if docs.is_dir():
        streamfiles=sorted(x for x in docs.iterdir()
                           if x.is_file() and not x.is_symlink()
                           and "stream" in x.name.lower())[:30]
    stream=[]
    for path in streamfiles:
        d=safe_read(path,750_000)
        if d["status"]=="READ":
            text=d["text"]
            stream.append({"path":str(path),"sha256":d["sha256"],
                           "line_count":len(d["lines"]),
                           "site_token_present":site in text,
                           "site_DATM_annual_token_present":site+"_DATM_" in text,
                           "important_raw_lines":selection(text,35),
                           "first_lines":[{"line":i,"raw":s[:550]}
                                          for i,s in enumerate(d["lines"][:10],1)]})
        else:
            stream.append({"path":str(path),"status":d["status"]})
    source=[]
    if datm_list["status"]=="READ":
        source=[{"line":i,"raw":s.strip()[:500]}
                for i,s in enumerate(datm_list["lines"],1)
                if site+"_DATM_" in s][:5]
    return {"site":site,"case":name,
            "CaseDocs_datm_in":datm,"CaseDocs_lnd_in":lnd,
            "case_env_run_xml":envrun,"case_env_case_xml":envcase,
            "original_CIME_data_input_list_status":datm_list["status"],
            "data_input_list_site_line_examples":source,
            "stream_docs":stream,
            "CaseDocs_datm_stream_assignment_present":bool(datm.get("assignments",{}).get("streams")),
            "stream_doc_count":len(stream),
            "stream_docs_with_site_name":sum(bool(x.get("site_token_present")) for x in stream),
            "stream_docs_with_site_DATM_annual_token":sum(
                bool(x.get("site_DATM_annual_token_present")) for x in stream),
            "actual_runtime_DATM_stream_approved":False,
            "observed_tower_native_humidity_QC_approved":False,
            "site_soil_source_QC_approved":False,
            "science_release":"HOLD"}


def as_csv(x):
    xml=x["case_env_run_xml"].get("entries",{})
    doc=x["CaseDocs_datm_in"]
    return {
        "site":x["site"],"case":x["case"],
        "stage02y_DATM_annual_refs":YEARS[x["site"]],
        "CaseDocs_datm_in_status":doc["status"],
        "CaseDocs_datm_in_stream_assignment_count":len(doc.get("assignments",{}).get("streams",[])),
        "CaseDocs_datm_in_present":doc["status"]=="READ",
        "CaseDocs_stream_docs_count":x["stream_doc_count"],
        "CaseDocs_stream_docs_with_site_token":x["stream_docs_with_site_name"],
        "CaseDocs_stream_docs_with_site_DATM_annual":x["stream_docs_with_site_DATM_annual_token"],
        "CaseDocs_datm_in_original_lines_json":json.dumps(doc.get("relevant_lines",[]),ensure_ascii=False),
        "stream_doc_excerpt_json":json.dumps(
            [{"path":a["path"],"raw":a.get("important_raw_lines",[])}
             for a in x["stream_docs"]],ensure_ascii=False),
        "env_run_DATM_MODE":xml.get("DATM_MODE"),
        "env_run_RUN_TYPE":xml.get("RUN_TYPE"),
        "env_run_RUNDIR":xml.get("RUNDIR"),
        "actual_runtime_DATM_binding_verified":False,
        "native_tower_source_QC_verified":False,"model_release":"HOLD",
    }


def self_test():
    assert len(SITES)==4 and sum(YEARS.values())==74
    toy="""&shr_strdata_nml
  streams = 'datm.streams.txt.CLMCRUNCEP.Solar 2001 2001 2001',
  taxmode = 'cycle'
/
"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"datm_in"
        p.write_text(toy,encoding="utf-8")
        parsed=read_datm(p)
        assert len(parsed["assignments"]["streams"])==1
        assert parsed["assignments"]["streams"][0]["line"]==2
    assert selection("x\nfileNames = x.nc\n")[-1]["line"]==2
    print("STAGE02Z SELF-TEST PASS: 8 case name gates, real DATM streams assignment read, bounded source excerpts; NO SOURCE/CIME/SLURM WRITES")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage02y",type=Path)
    p.add_argument("--case-root",type=Path,default=CASE_ROOT)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:
        self_test();return
    if not args.stage02y or not args.stage02y.is_file():
        p.error("Original saved Stage02Y JSON required")
    if args.out_dir is None or not args.out_dir.is_dir() or \
       args.out_dir.is_symlink() or any(args.out_dir.iterdir()):
        p.error("--out-dir must be a NEW EXISTING EMPTY folder")
    if args.case_root.resolve(strict=True)!=CASE_ROOT.resolve(strict=True):
        p.error("Only original pinned Batch04 case root accepted")
    prior=json.loads(args.stage02y.read_text(encoding="utf-8"))
    pins=validate_stage(prior)
    rows=[]
    for site,name in pins:
        x=audit_case(args.case_root,site,name)
        rows.append(x)
        env=x["case_env_run_xml"].get("entries",{})
        print("CASE",site,name,
              "DATM_IN",x["CaseDocs_datm_in"]["status"],
              "STREAMS_ASSIGNMENT",x["CaseDocs_datm_stream_assignment_present"],
              "STREAM_DOCS",x["stream_doc_count"],
              "WITH_SITE",x["stream_docs_with_site_name"],
              "WITH_SITE_ANNUAL_NC",x["stream_docs_with_site_DATM_annual_token"],
              "DATM_MODE",env.get("DATM_MODE","NOT_IN_ENV_RUN_XML"))
        for line in x["CaseDocs_datm_in"].get("relevant_lines",[])[:10]:
            print(" DATM_SOURCE",line["line"],line["raw"])
        for stream in x["stream_docs"][:3]:
            print(" STREAM_DOC",stream["path"],
                  "SITE_ANNUAL_TOKEN",stream.get("site_DATM_annual_token_present"))
            for line in stream.get("important_raw_lines",[])[:6]:
                print("  STREAM_SOURCE",line["line"],line["raw"])
        print(" SCIENCE_QC_RUNTIME_HOLD; NO CASE EDITS")
    report={"stage":"STAGE02Z_BATCH04_DATM_STREAM_DOCUMENT_FORENSICS_READONLY",
            "source_stage02y":str(args.stage02y),
            "read_only":True,"science_release":False,
            "source_modified":False,"cime_modified":False,"slurm_submitted":False,
            "original_case_count":len(rows),"cases":rows,
            "interpretation":"Missing streams assignment in CaseDocs/datm_in may reflect different DATM CIME namelist/doc conventions. Original input lists alone do not prove runtime streams; no model reconfiguration, new case or AD5 approved.",
            "separate_soil_hold":"IT-Tor original ORGANIC=0 for all ten layers; do not auto-fill."}
    j=args.out_dir/"stage02z_eight_original_DATM_stream_document_audit.json"
    c=args.out_dir/"stage02z_eight_original_case_stream_matrix.csv"
    with j.open("x",encoding="utf-8") as fh:
        json.dump(report,fh,indent=2,ensure_ascii=False);fh.write("\n")
    with c.open("x",encoding="utf-8",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(as_csv(x) for x in rows)
    print("ORIGINAL_CASES_AUDITED",len(rows))
    print("JSON",j)
    print("CSV",c)
    print("SCIENCE_HOLD: ORIGINAL_TOWER_MET_QC, SOIL_AND_ACTUAL_RUNTIME_DATM; NO ORIGINAL WRITES")


if __name__=="__main__":
    main()
