#!/usr/bin/env python3
"""ICOS Batch04 Stage02U — four-site effective-input *static* source/soil audit.

Read-only follow-up to completed Stage02C and Stage02D. For exactly
DE-Gri, DE-RuR, IT-Tor, ES-Agu, compare original S30SHARED/EXCL cases'
recorded CaseDocs/datm_in, lnd_in, stream document excerpts, source DATM
input list, candidate annual file paths, point surface and FATES parameter
path. Inspect point soil/PFT landunit fields from *referenced original*
surface NC without changing source. A generated CaseDocs file is still only
STATIC case evidence, NOT proof of currently effective runtime DATM binding.

No CIME xmlchange, model, Slurm, original NetCDF, Git worktree or global
file tree modification. Only a NEW EMPTY --out-dir receives JSON/CSV.
Model PFT proxies are not independently measured tower-footprint fractions.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

STAGE_C="STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
STAGE_D="STAGE02D_FULL_ANNUAL_INTERNAL_DATM_QC"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
EXPECTED_YEARS={"DE-Gri":(2004,2025,22),
                "DE-RuR":(2011,2025,15),
                "IT-Tor":(2008,2025,18),
                "ES-Agu":(2006,2024,19)}
EXPECTED_PROXY={
    "DE-Gri":{13:100.0},
    "DE-RuR":{13:100.0},
    "IT-Tor":{13:100.0},
    "ES-Agu":{0:49.0,9:22.0,13:29.0},
}
XML_KEYS=("CASE","RUNDIR","CASEROOT","DIN_LOC_ROOT","RUN_TYPE",
          "DATM_MODE","DATM_CLMNCEP_YR_START","DATM_CLMNCEP_YR_END",
          "DATM_CLMNCEP_YR_ALIGN","PTS_LAT","PTS_LON","CALENDAR",
          "CLM_ACCELERATED_SPINUP")
LAND_KEYS=("fsurdat","fates_paramfile","finidat","use_fates",
           "use_fates_fixed_biogeog","use_fates_nocomp",
           "hist_fincl1","spinup_state")
DATM_KEYS=("year_first","year_last","year_align","streams","taxmode")
SURFACE_FIELDS=("LATIXY","LONGXY","PCT_NATVEG","PCT_CROP",
                "PCT_NAT_PFT","PCT_SAND","PCT_CLAY","ORGANIC",
                "PCT_LAKE","PCT_GLACIER","PCT_WETLAND","PCT_URBAN",
                "SOIL_COLOR")
CSV_FIELDS=("site","case","candidate_DATM_years",
            "original_DATM_input_list_matching","datm_in_exists",
            "land_in_exists","stream_document_count",
            "fsurdat_original","fates_paramfile_original",
            "site_point_lat_lon_static_match",
            "surface_pft_vector_available","surface_soil_fields_available",
            "static_case_diff_vs_other","science_release")


def validate_inputs(c,d):
    if c.get("stage")!=STAGE_C or c.get("read_only") is not True or \
       c.get("science_release") is not False:
        raise ValueError("Expected original unreleased Stage02C result")
    if d.get("stage")!=STAGE_D or d.get("read_only") is not True or \
       d.get("science_release") is not False:
        raise ValueError("Expected original unreleased four-site Stage02D result")
    sources={x.get("site"):x for x in c.get("sites",[])}
    if len(sources)!=6:
        raise ValueError("Original Stage02C must contain all six sites")
    audited={x.get("site"):x for x in d.get("sites",[])}
    if set(audited)!=set(SITES) or len(d.get("sites",[]))!=4:
        raise ValueError("Stage02D must be the original four-site full-year audit")
    for site in SITES:
        first,last,n=EXPECTED_YEARS[site]
        row=sources[site]
        cases=row.get("cases",[])
        if len(cases)!=2 or row.get("distinct_site_datm_files")!=n or \
           row.get("release")!="HOLD_SOURCE_QC_STREAM_BINDING_PFT_SOIL":
            raise ValueError(site+" Stage02C cases/years/source HOLD mismatch")
        if row.get("distinct_case_datm_path_sets")!=1:
            raise ValueError(site+" input path-set count changed")
        expect=set(range(first,last+1))
        pathset=set()
        for cc in cases:
            dates={int(x.get("year")) for x in cc.get("site_datm",[])}
            if dates!=expect:
                raise ValueError(site+" case annual year coverage changed")
            for item in cc["site_datm"]:
                path=Path(item.get("path",""))
                if not path.is_absolute() or not path.name.startswith(site+"_DATM_"):
                    raise ValueError(site+" unpinned site DATM reference")
                pathset.add(str(path))
        if len(pathset)!=n:
            raise ValueError(site+" case annual path sets unexpectedly differ")
        prev=audited[site]
        if prev.get("annual_file_count")!=n or prev.get("flagged_file_counts")!={} or \
           prev.get("status")!="HOLD_DATM_INTERNAL_QC_ONLY_NO_SOURCE_TOWER_QC_OR_ACTIVE_STREAM_RELEASE":
            raise ValueError(site+" previous Stage02D internal screen unverified")
        if set(prev.get("all_years",[]))!=expect:
            raise ValueError(site+" previous Stage02D years changed")
    return sources,audited


def read_assignments(path,keys):
    if not path.is_file():
        return {}, "MISSING"
    text=path.read_text(encoding="utf-8",errors="replace")
    result={}
    for key in keys:
        expressions=re.findall(r"(?im)^[ \t]*"+re.escape(key)+
                               r"[ \t]*=[ \t]*([^\r\n]*)",text)
        if len(expressions)>1:
            result[key]="MULTIPLE_ASSIGNMENTS_REVIEW"
        elif expressions:
            value=expressions[0].split("!")[0].strip().rstrip(",").strip().strip("'\"")
            result[key]=value
    return result,"PRESENT"


def xml_values(case):
    out={}
    for filename in ("env_case.xml","env_run.xml","env_build.xml"):
        f=case/filename
        if not f.is_file():continue
        try:
            for node in ET.parse(f).getroot().iter("entry"):
                k=node.attrib.get("id")
                if k in XML_KEYS:
                    out[k]=node.attrib.get("value")
        except (OSError,ET.ParseError) as exc:
            return out,"XML_PARSE_HOLD:"+type(exc).__name__
    return out,"OK"


def file_digest(path,limit=8_000_000):
    if path is None or not path.is_file() or path.is_symlink():
        return {"exists":False}
    size=path.stat().st_size
    digest=None
    if size<=limit:
        h=hashlib.sha256()
        with path.open("rb") as fd:
            for buf in iter(lambda:fd.read(256*1024),b""):
                h.update(buf)
        digest=h.hexdigest()
    return {"exists":True,"bytes":size,
            "sha256_if_small":digest,"hash_policy":"SMALL_ONLY"}


def static_path(text):
    if not text or "$" in text or "MULTIPLE_" in text:
        return None
    p=Path(text)
    return p if p.is_absolute() else None


def source_paths_from_list(text,site):
    # Only exact site-DATM path names; aerosol/deposition NC excluded.
    pat=re.compile(r"/[^\s,'\"=;]+?"+re.escape(site)+
                   r"_DATM_(?:19|20)\d{2}\.nc",re.I)
    return sorted(set(m.group(0) for m in pat.finditer(text)))


def surface_read(path):
    info={"path":str(path) if path else None,"status":"UNVERIFIED"}
    if path is None or not path.is_file():
        info["status"]="MISSING_OR_UNRESOLVED_ORIGINAL_SURFACE"
        return info
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        info["status"]="MISSING_NUMPY_NETCDF4:"+str(exc)
        return info
    try:
        with Dataset(path,"r") as nc:
            out={}
            for name in SURFACE_FIELDS:
                v=nc.variables.get(name)
                if v is None:
                    out[name]={"status":"ABSENT"}
                    continue
                if not 0<v.size<=20000:
                    out[name]={"status":"TOO_LARGE_NOT_READ","shape":list(v.shape)}
                    continue
                a=np.ma.filled(np.ma.asarray(v[:]).astype("float64"),np.nan).reshape(-1)
                good=a[np.isfinite(a)]
                rec={"shape":list(v.shape),"n_total":int(v.size),
                     "n_valid":int(good.size)}
                if good.size:
                    rec["min"]=float(good.min());rec["max"]=float(good.max())
                    if a.size<=30:
                        rec["values"]=[float(x) if math.isfinite(float(x)) else None for x in a]
                    if name=="PCT_NAT_PFT" and a.size==15:
                        rec["HOST_PFT_vector"]=[float(x) if math.isfinite(float(x)) else None for x in a]
                        rec["HOST_PFT_sum"]=float(np.nansum(a))
                out[name]=rec
            info["status"]="POINT_SURFACE_HEADER_AND_BOUNDED_NUMERIC_READ"
            info["fields"]=out
    except Exception as exc:
        info["status"]="SURFACE_NC_READ_HOLD:"+type(exc).__name__
    return info


def point_check(surface,xml):
    try:
        lat=float(xml["PTS_LAT"]);lon=float(xml["PTS_LON"])%360
        fields=surface["fields"]
        a=float(fields["LATIXY"]["values"][0])
        b=float(fields["LONGXY"]["values"][0])%360
        gap=abs((lon-b+180)%360-180)
        if abs(lat-a)<=0.001 and gap<=0.001:
            return "MATCH_STATIC_XML_NOT_RUNTIME"
        return "POINT_MISMATCH_REVIEW"
    except (ValueError,TypeError,KeyError,IndexError):
        return "MISSING_POINT_EVIDENCE_REVIEW"


def inspect_case(base,site,entry):
    name=entry["case"]
    case=base/"cases"/name
    if case.name!=name or not name.startswith(site+"_") or \
       not case.is_dir() or case.is_symlink():
        return {"case":name,"site":site,"status":"CASE_FOLDER_MISSING_OR_UNEXPECTED","HOLD":True}
    docs=case/"CaseDocs"
    land,landstate=read_assignments(docs/"lnd_in",LAND_KEYS)
    datm,datmstate=read_assignments(docs/"datm_in",DATM_KEYS)
    xml,xmlstatus=xml_values(case)
    target={str(x["path"]) for x in entry["site_datm"]}
    data_list=case/"Buildconf/datm.input_data_list"
    list_text=data_list.read_text(encoding="utf-8",errors="replace") if data_list.is_file() else ""
    recorded=set(source_paths_from_list(list_text,site))
    stream_paths=sorted(x for x in docs.glob("*stream*") if x.is_file() and not x.is_symlink())[:30] if docs.is_dir() else []
    streams=[]
    for p in stream_paths:
        content=p.read_text(encoding="utf-8",errors="replace")[:16000]
        streams.append({"path":str(p),"sha256":file_digest(p)["sha256_if_small"],
                        "mentions_site_DATM":site+"_DATM_" in content,
                        "mentions_any_site_nc":any(Path(x).name in content for x in target),
                        "site_token_excerpt":[x.strip()[:300] for x in content.splitlines()
                                              if (site in x or "dataSource" in x or "taxmode" in x)][:15]})
    surf=static_path(land.get("fsurdat"))
    param=static_path(land.get("fates_paramfile"))
    surface=surface_read(surf)
    return {
        "case":name,"site":site,
        "xml":xml,"xml_parse":xmlstatus,
        "land_in_status":landstate,"datm_in_status":datmstate,
        "land_config":land,"datm_config":datm,
        "land_sha":file_digest(docs/"lnd_in"),
        "datm_sha":file_digest(docs/"datm_in"),
        "datm_input_list":file_digest(data_list),
        "datm_expected_year_paths":len(target),
        "datm_recorded_year_paths":len(recorded),
        "datm_list_exact_site_path_match":bool(target) and recorded==target,
        "datm_list_missing_expected":sorted(target-recorded)[:12],
        "datm_list_other_case_site_paths":sorted(recorded-target)[:12],
        "stream_documents":streams,
        "stream_documents_found":len(streams),
        "stream_site_nc_mention_any":any(x["mentions_any_site_nc"] for x in streams),
        "surface_original":surface,
        "surface_path":str(surf) if surf else None,
        "surface_sha":file_digest(surf),
        "fates_param_path":str(param) if param else None,
        "fates_param":file_digest(param),
        "point_check":point_check(surface,xml),
        "original_case_science_status":"HOLD_STATIC_CIME_AND_OBS_QC_UNVERIFIED",
    }


def compare_pair(cases):
    if len(cases)!=2:
        return {"status":"UNRESOLVED_NOT_EXACTLY_TWO"}
    a,b=cases
    keys=("surface_path","fates_param_path")
    return {
        "status":"CANDIDATE_CASE_STATIC_DIFFERENCES_NOT_SCIENCE_APPROVAL",
        "case_A":a["case"],"case_B":b["case"],
        "same_site_DATM_input_list_paths":a.get("datm_list_exact_site_path_match") is True and
            b.get("datm_list_exact_site_path_match") is True and
            a.get("datm_recorded_year_paths")==b.get("datm_recorded_year_paths"),
        "same_original_surface_path":a.get("surface_path") is not None and
            a.get("surface_path")==b.get("surface_path"),
        "same_FATES_param_path":a.get("fates_param_path") is not None and
            a.get("fates_param_path")==b.get("fates_param_path"),
        "different_xml_values":{k:[a.get("xml",{}).get(k),b.get("xml",{}).get(k)]
                                for k in XML_KEYS
                                if a.get("xml",{}).get(k)!=b.get("xml",{}).get(k)},
        "different_xml_science_values":{k:[a.get("xml",{}).get(k),b.get("xml",{}).get(k)]
                                for k in XML_KEYS if k not in ("CASE","CASEROOT","RUNDIR")
                                and a.get("xml",{}).get(k)!=b.get("xml",{}).get(k)},
        "different_land_values":{k:[a.get("land_config",{}).get(k),b.get("land_config",{}).get(k)]
                                 for k in LAND_KEYS
                                 if a.get("land_config",{}).get(k)!=b.get("land_config",{}).get(k)},
        "different_datm_values":{k:[a.get("datm_config",{}).get(k),b.get("datm_config",{}).get(k)]
                                 for k in DATM_KEYS
                                 if a.get("datm_config",{}).get(k)!=b.get("datm_config",{}).get(k)},
    }


def self_test():
    assert len(SITES)==4 and sum(x[2] for x in EXPECTED_YEARS.values())==74
    t="/scratch/x/DE-Gri_DATM_2004.nc\n/scratch/y/DE-Gri_DATM_2005.nc"
    assert len(source_paths_from_list(t,"DE-Gri"))==2
    assert not source_paths_from_list(t,"IT-Tor")
    assert point_check({"fields":{"LATIXY":{"values":[50]},
                                  "LONGXY":{"values":[358]}}},
                       {"PTS_LAT":"50","PTS_LON":"-2"})=="MATCH_STATIC_XML_NOT_RUNTIME"
    assert sum(EXPECTED_PROXY["ES-Agu"].values())==100
    print("STAGE02U SELF-TEST PASS: exact four sites/74 annual NC evidence, case stream list and PFT point guards; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02c",type=Path)
    ap.add_argument("--stage02d",type=Path)
    ap.add_argument("--base",type=Path,default=Path("/iridisfs/scratch/ly3n24/CLM_FATES"))
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:self_test();return
    if any(x is None or not x.is_file() for x in (args.stage02c,args.stage02d)):
        ap.error("Original Stage02C and four-site Stage02D JSONs required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY")
    if args.base.name!="CLM_FATES" or not args.base.is_dir():
        ap.error("Expected original CLM_FATES case input root")
    src,check=validate_inputs(json.loads(args.stage02c.read_text(encoding="utf-8")),
                              json.loads(args.stage02d.read_text(encoding="utf-8")))
    rows=[]
    simple=[]
    for site in SITES:
        cases=[inspect_case(args.base,site,x) for x in src[site]["cases"]]
        pair=compare_pair(cases)
        item={
            "site":site,"expected_model_PFT_conditional_NATVEG_pct":EXPECTED_PROXY[site],
            "expected_original_case_count":2,
            "Stage02D_internal_annual_files":check[site]["annual_file_count"],
            "Stage02D_flags":check[site]["flagged_file_counts"],
            "source_case_inspections":cases,"S30_case_static_pair":pair,
            "native_tower_QC_verified":False,
            "active_runtime_DATM_stream_verified":False,
            "site_soil_original_QC_verified":False,
            "PFT_footprint_observed_verified":False,
            "science_release":"HOLD",
        }
        rows.append(item)
        print("SITE",site,"ANNUAL_CANDIDATE_NC",item["Stage02D_internal_annual_files"],
              "STAGE02D_FLAGS",item["Stage02D_flags"],"CASE_COUNT",len(cases))
        for case in cases:
            print(" CASE",case["case"],"DATM_STATIC_LIST_MATCH",
                  case.get("datm_list_exact_site_path_match"),
                  "STREAM_DOCS",case.get("stream_documents_found"),
                  "SURFACE",case.get("surface_path"),
                  "SURFACE_STATUS",case.get("surface_original",{}).get("status"),
                  "POINT",case.get("point_check"),
                  "PARAM_EXISTS",case.get("fates_param",{}).get("exists"))
            fields=case.get("surface_original",{}).get("fields",{})
            print("  LANDUNITS",site,case["case"],
                  "PCT_NATVEG",fields.get("PCT_NATVEG",{}).get("values"),
                  "PCT_CROP",fields.get("PCT_CROP",{}).get("values"),
                  "PFT_NONZERO",[(i,round(x,3))
                    for i,x in enumerate(fields.get("PCT_NAT_PFT",{}).get("HOST_PFT_vector") or [])
                    if x is not None and x>0])
            print("  SOIL",site,case["case"],
                  "SAND_SHAPE",fields.get("PCT_SAND",{}).get("shape"),
                  "SAND_MINMAX",[fields.get("PCT_SAND",{}).get("min"),fields.get("PCT_SAND",{}).get("max")],
                  "CLAY_SHAPE",fields.get("PCT_CLAY",{}).get("shape"),
                  "CLAY_MINMAX",[fields.get("PCT_CLAY",{}).get("min"),fields.get("PCT_CLAY",{}).get("max")],
                  "ORGANIC_SHAPE",fields.get("ORGANIC",{}).get("shape"),
                  "ORGANIC_MINMAX",[fields.get("ORGANIC",{}).get("min"),fields.get("ORGANIC",{}).get("max")])
            simple.append({
                "site":site,"case":case["case"],
                "candidate_DATM_years":case.get("datm_expected_year_paths"),
                "original_DATM_input_list_matching":case.get("datm_list_exact_site_path_match"),
                "datm_in_exists":case.get("datm_in_status")=="PRESENT",
                "land_in_exists":case.get("land_in_status")=="PRESENT",
                "stream_document_count":case.get("stream_documents_found",0),
                "fsurdat_original":case.get("surface_path"),
                "fates_paramfile_original":case.get("fates_param_path"),
                "site_point_lat_lon_static_match":case.get("point_check"),
                "surface_pft_vector_available":(
                    "HOST_PFT_vector" in case.get("surface_original",{}).get("fields",{}).get("PCT_NAT_PFT",{})),
                "surface_soil_fields_available":(
                    all(case.get("surface_original",{}).get("fields",{}).get(x,{}).get("n_valid",0)>0
                        for x in ("PCT_SAND","PCT_CLAY","ORGANIC"))),
                "static_case_diff_vs_other":json.dumps(pair,sort_keys=True),
                "science_release":"HOLD",
            })
        print(" PAIR",site,"SAME_SURFACE",pair.get("same_original_surface_path"),
              "SAME_FATES_PARAM",pair.get("same_FATES_param_path"),
              "XML_SCIENCE_DIFF_KEYS",",".join(pair.get("different_xml_science_values",{})),
              "LAND_DIFF_KEYS",",".join(pair.get("different_land_values",{})))
        print(" SOURCE_TOWER_QC/PFT/SOIL/ACTUAL_RUNTIME_BINDING HOLD")
    report={
        "stage":"STAGE02U_BATCH04_FOUR_SITE_STATIC_CASE_SURFACE_SOIL_PFT_GATE",
        "read_only":True,"science_release":False,
        "input_stage02c":str(args.stage02c),"input_stage02d":str(args.stage02d),
        "source_changed":False,"CIME_modified":False,"slurm_submitted":False,
        "sites":rows,
        "limitations":"Only static case effective generated docs and original surface fields. No runtime stream-open verification, no site-observed PFT, tower native QC, ERA provenance or FATES actual run state.",
    }
    j=args.out_dir/"stage02u_four_site_case_surface_soil_PFT_static_audit.json"
    c=args.out_dir/"stage02u_four_site_eight_case_static_matrix.csv"
    with j.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=CSV_FIELDS);wr.writeheader();wr.writerows(simple)
    print("JSON",j)
    print("CSV",c)
    print("ALL_FOUR_SCIENCE_HOLD; NO SOURCE/CIME/SLURM WRITES")


if __name__=="__main__":
    main()
