#!/usr/bin/env python3
"""ICOS Batch04 Stage03A — read-only native met source and QC-column discovery.

Purpose: distinguish the four sites' native half-hourly tower source products,
ONEFlux gapfilled meteorology, ERA downscaled columns and QC flags BEFORE
attempting time-aligned DATM/source comparison. The existing 74 annual DATM NC
already passed numerical QC; do NOT reread/regenerate them.

Reads the verified Stage02C, Stage02D (four sites), Stage02Z (8 source cases)
operator reports. Searches bounded files ONLY under four original station
site/forcing roots, reads tiny CSV/ZIP/GZIP headers plus <=2 sample records,
and opens optional non-model source NC *headers* without loading arrays.
ZERO source/case/NetCDF/Slurm changes; new JSON and CSV in an EMPTY output dir.

A filename/QC column is only a candidate provenance; measured RH/VPD, actual
time basis, original QC0 observations and ERA replacement may remain UNKNOWN.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import io
import json
import os
import re
import zipfile
from collections import Counter
from pathlib import Path

SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
YEARS={"DE-Gri":(2004,2025,22),"DE-RuR":(2011,2025,15),
       "IT-Tor":(2008,2025,18),"ES-Agu":(2006,2024,19)}
C_STAGE="STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
D_STAGE="STAGE02D_FULL_ANNUAL_INTERNAL_DATM_QC"
Z_STAGE="STAGE02Z_BATCH04_DATM_STREAM_DOCUMENT_FORENSICS_READONLY"
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
MAX_DEPTH=8
MAX_VISITED=16000
MAX_CANDIDATES=320
MAX_ARCHIVES=40
MAX_ZIP_MEMBERS=20000
MAX_META_HEAD=65536
MAX_BYTES_FOR_ZIP=2_000_000_000
MAX_RECORD_FIELDS=140
SKIP={".git",".cache","__pycache__","node_modules","case","cases",
      "archive","logs","run","build","bld","subset_data"}
MET=re.compile(r"(?:^|[_./-])(FLUXMET|FLUXNET|ONEFLUX|ICOS|EUF|ERA5|ERA|BASE|BADM|BIF|HH|HALFHOURLY|MET|METEO|FORCING|QC)(?:[_./-]|$)",re.I)
FIELD=re.compile(r"(?i)(?:^|_)(?:RH|VPD|TA|T_AIR|PA|PRECIP|P|P_F|P_RAIN|SW_IN|LW_IN|WS|USTAR|TIMESTAMP|TIME|DATE|QC)(?:_|$)|_QC$|_ERA$")
TIME=re.compile(r"(?i)TIMESTAMP|^TIME$|^DATE$|DATE_TIME|DATETIME")
QC=re.compile(r"(?i)_QC(?:_|$)|^QC(?:_|$)|FLAG|QUALITY")
ERA=re.compile(r"(?i)_ERA(?:_|$)|ERA5|ERAI")
NATIVE=re.compile(r"(?i)^(?:RH|VPD|TA|PA|P|SW_IN|LW_IN|WS|USTAR)(?:_F)?(?:_QC)?$")
OUT_COLS=("site","candidate_kind","source_file","archive_member",
          "source_bytes","original_artifact_present","source_header_read",
          "time_fields","native_or_fluxmet_columns","qc_fields",
          "era_fields","numeric_native_sensor_RH_verified",
          "time_clock_verified","meterological_science_release")


def validate(c,d,z):
    if c.get("stage")!=C_STAGE or c.get("read_only") is not True or \
       c.get("science_release") is not False:
        raise ValueError("Original Stage02C source inventory HOLD required")
    if d.get("stage")!=D_STAGE or d.get("read_only") is not True or \
       d.get("science_release") is not False:
        raise ValueError("Original four-site Stage02D internal QC HOLD required")
    if z.get("stage")!=Z_STAGE or z.get("read_only") is not True or \
       z.get("science_release") is not False or z.get("slurm_submitted") is not False:
        raise ValueError("Original Stage02Z stream source forensic HOLD required")
    crows={x.get("site"):x for x in c.get("sites",[])}
    drows={x.get("site"):x for x in d.get("sites",[])}
    if len(crows)!=6 or set(drows)!=set(SITES) or len(d.get("sites",[]))!=4:
        raise ValueError("Expected six-site Stage02C and exact four-site Stage02D")
    zrows=z.get("cases",[])
    if len(zrows)!=8:
        raise ValueError("Expected eight source CIME case stream forensic rows")
    for site in SITES:
        start,end,n=YEARS[site]
        row=drows[site]
        if row.get("annual_file_count")!=n or \
           row.get("all_years")!=list(range(start,end+1)) or \
           row.get("flagged_file_counts")!={}:
            raise ValueError(site+" previous Stage02D annual internal scan changed")
        if row.get("status")!="HOLD_DATM_INTERNAL_QC_ONLY_NO_SOURCE_TOWER_QC_OR_ACTIVE_STREAM_RELEASE":
            raise ValueError(site+" previous source QC status unexpectedly released")
        cr=crows[site]
        if cr.get("distinct_site_datm_files")!=n or \
           cr.get("distinct_case_datm_path_sets")!=1:
            raise ValueError(site+" Stage02C source path register changed")
        ss=[x for x in zrows if x.get("site")==site]
        if len(ss)!=2 or {x.get("case") for x in ss}!={
                f"{site}_FATES_SPINUP1000_S30EXCL",
                f"{site}_FATES_SPINUP1000_S30SHARED"}:
            raise ValueError(site+" original stream source-case identities changed")
        if any(x.get("science_release")!="HOLD" for x in ss):
            raise ValueError(site+" unexpected CIME source science release")
    return True


def relevant(path):
    name=path.name
    suffix=name.lower()
    if suffix.endswith((".csv",".csv.gz",".zip",".json",".txt",".nc",".nc4")):
        return bool(MET.search(name) or "flux" in name.lower()
                    or "badm" in name.lower() or "bif" in name.lower())
    return False


def classify(name):
    u=name.upper()
    if "BIFVARINFO" in u:return "ORIGINAL_PRODUCT_VARIABLE_DEFINITIONS"
    if "BIF" in u or "BADM" in u:return "ORIGINAL_PRODUCT_SITE_METADATA"
    if "FLUXMET_HH" in u:return "ONEFLUX_GAPFILLED_MET_HH_CANDIDATE"
    if "ERA5_HH" in u or "ERA_HH" in u:return "DISTRIBUTED_ERA_MET_HH_CANDIDATE"
    if "BASE" in u and "HH" in u:return "BASE_HH_CANDIDATE_VERIFY_NATIVE"
    if "HH" in u or "HALFHOURLY" in u:return "HH_PRODUCT_UNKNOWN_SENSOR_OR_PROCESSING"
    if "ERA" in u:return "ERA_MET_PRODUCT_OR_METADATA"
    return "OTHER_SOURCE_OR_METADATA_CANDIDATE"


def source_files(site):
    root=ROOT/site
    if not root.is_dir() or root.is_symlink():
        return [],{"site":site,"status":"SITE_SOURCE_ROOT_MISSING",
                   "root":str(root),"visited":0,"truncated":False}
    files=[]
    visited=0
    truncated=False
    for here,dirs,names in os.walk(root,topdown=True,followlinks=False):
        herepath=Path(here)
        level=len(herepath.parts)-len(root.parts)
        dirs[:]=[k for k in sorted(dirs) if k not in SKIP and \
                  not (herepath/k).is_symlink()] if level<MAX_DEPTH else []
        for name in sorted(names):
            visited+=1
            if visited>MAX_VISITED:
                truncated=True;break
            path=herepath/name
            if not relevant(path) or path.is_symlink() or not path.is_file():
                continue
            if len(files)>=MAX_CANDIDATES:
                truncated=True;break
            if not path.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
                continue
            files.append(path)
        if truncated:break
    return files,{"site":site,"status":"SCANNED","root":str(root),
                  "visited":visited,"candidates":len(files),"truncated":truncated}


def first_rows(buffer):
    """Parse only an actual product header and 2 rows, not source QC truth."""
    try:
        sample=buffer.decode("utf-8-sig","replace")
    except Exception:
        sample=buffer.decode("latin-1","replace")
    try:
        records=csv.reader(io.StringIO(sample))
        fields=next(records,[])
        fields=[x.strip() for x in fields]
        if len(fields)>MAX_RECORD_FIELDS or not fields:
            return {"status":"MISSING_OR_TOO_MANY_FIELDS","fields":fields[:30]}
        rows=[]
        for i in range(2):
            try:r=next(records)
            except StopIteration:break
            if len(r)==len(fields):
                rows.append(dict(zip(fields,r)))
        tags={
            "time_fields":[x for x in fields if TIME.search(x)],
            "qc_fields":[x for x in fields if QC.search(x)],
            "era_fields":[x for x in fields if ERA.search(x)],
            "met_fields":[x for x in fields if FIELD.search(x)],
        }
        rows=[{k:v for k,v in row.items() if
               k in tags["time_fields"] or k in ("RH","VPD_F","VPD_F_QC","TA_F","TA_F_QC","VPD_ERA","TA_ERA")}
              for row in rows]
        return {"status":"CSV_HEADER_AND_2_ROWS_ONLY","column_count":len(fields),
                "fields":fields,"sample_rows_unvalidated":rows,**tags}
    except (csv.Error,UnicodeError) as exc:
        return {"status":"SOURCE_CSV_HEADER_PARSE_HOLD","error":type(exc).__name__}


def csv_head(path):
    try:
        if path.stat().st_size>MAX_BYTES_FOR_ZIP:return {"status":"SOURCE_OVER_2GB_LIMIT"}
        if path.name.lower().endswith(".gz"):
            with gzip.open(path,"rb") as fd:buf=fd.read(MAX_META_HEAD)
        else:
            with path.open("rb") as fd:buf=fd.read(MAX_META_HEAD)
        return first_rows(buf)
    except (OSError,EOFError) as exc:
        return {"status":"HEADER_READ_HOLD","error":type(exc).__name__}


def nc_header(path):
    try:
        from netCDF4 import Dataset
        with Dataset(str(path),"r") as d:
            names=list(d.variables)
            return {"status":"NETCDF_VARIABLE_HEADERS_ONLY",
                    "met_fields":[x for x in names if FIELD.search(x)],
                    "time_fields":[x for x in names if TIME.search(x)],
                    "qc_fields":[x for x in names if QC.search(x)],
                    "era_fields":[x for x in names if ERA.search(x)],
                    "variable_count":len(names),
                    "time_var_metadata":{key:{
                        "units":str(getattr(d.variables[key],"units","")),
                        "calendar":str(getattr(d.variables[key],"calendar",""))}
                        for key in names if TIME.search(key) and len(names)<500},
                    "NC_arrays_read":False}
    except Exception as e:
        return {"status":"NC_HEADER_ERROR","error":type(e).__name__}


def inspect_zip(path):
    if path.stat().st_size>MAX_BYTES_FOR_ZIP:
        return [],{"status":"ZIP_OVER_2GB","member_count":None}
    try:
        with zipfile.ZipFile(path,"r") as z:
            names=z.infolist()
            if len(names)>MAX_ZIP_MEMBERS:
                return [],{"status":"TOO_MANY_MEMBERS","member_count":len(names)}
            selected=[n for n in names if not n.is_dir() and relevant(Path(n.filename))]
            ranked=sorted(selected,key=lambda x:
                          (classify(x.filename) not in (
                           "BASE_HH_CANDIDATE_VERIFY_NATIVE",
                           "ONEFLUX_GAPFILLED_MET_HH_CANDIDATE",
                           "DISTRIBUTED_ERA_MET_HH_CANDIDATE"),
                           Path(x.filename).name))[:80]
            entries=[]
            for n in ranked:
                detail={"archive_member":n.filename,"uncompressed_bytes":n.file_size,
                        "CRC32_not_independent_SHA":f"{n.CRC:08x}",
                        "candidate_kind":classify(n.filename)}
                if n.filename.lower().endswith((".csv",".csv.gz")) and n.file_size<=MAX_BYTES_FOR_ZIP:
                    try:
                        with z.open(n,"r") as h:
                            raw=h.read(MAX_META_HEAD)
                        if n.filename.lower().endswith(".gz"):
                            detail["header"]={"status":"NESTED_GZIP_HEADER_NOT_READ"}
                        else:detail["header"]=first_rows(raw)
                    except (OSError,RuntimeError,EOFError,zipfile.BadZipFile):
                        detail["header"]={"status":"ZIP_MEMBER_HEADER_READ_HOLD"}
                entries.append(detail)
            return entries,{"status":"ZIP_DIRECTORY_ONLY_AND_BOUNDED_MEMBER_HEADERS",
                            "member_count":len(names),
                            "selected_candidate_members":len(selected),
                            "reported_members":len(entries),
                            "member_report_truncated":len(selected)>len(entries)}
    except (OSError,zipfile.BadZipFile,zipfile.LargeZipFile) as exc:
        return [],{"status":"ZIP_READ_HOLD_"+type(exc).__name__}


def inspect_source(site,path):
    detail={"site":site,"source_file":str(path),"source_bytes":path.stat().st_size,
            "candidate_kind":classify(path.name),"archive_member":"",
            "original_artifact_present":True,
            "numeric_native_sensor_RH_verified":False,
            "time_clock_verified":False,
            "meteorological_science_release":"HOLD"}
    suf=path.name.lower()
    if suf.endswith(".zip"):
        detail["candidate_kind"]="SOURCE_ARCHIVE_ZIP"
        detail["members"],detail["zip_scan"]=inspect_zip(path)
    elif suf.endswith((".csv",".csv.gz")):
        detail["header"]=csv_head(path)
    elif suf.endswith((".nc",".nc4")):
        detail["header"]=nc_header(path)
    elif suf.endswith((".json",".txt")):
        detail["header"]={"status":"TEXT_METADATA_FILENAME_ONLY_NOT_SOURCE_TRUTH"}
    return detail


def rows_for_csv(item):
    entries=item.get("members",[None])
    for m in entries:
        doc=(m or {}).get("header",item.get("header",{}))
        yield {
            "site":item["site"],
            "candidate_kind":(m or {}).get("candidate_kind",item["candidate_kind"]),
            "source_file":item["source_file"],
            "archive_member":(m or {}).get("archive_member",""),
            "source_bytes":item["source_bytes"],
            "original_artifact_present":True,
            "source_header_read":doc.get("status","NOT_READ"),
            "time_fields":"|".join(doc.get("time_fields",[]))[:1200],
            "native_or_fluxmet_columns":"|".join(doc.get("met_fields",[]))[:2000],
            "qc_fields":"|".join(doc.get("qc_fields",[]))[:2000],
            "era_fields":"|".join(doc.get("era_fields",[]))[:2000],
            "numeric_native_sensor_RH_verified":False,
            "time_clock_verified":False,
            "meterological_science_release":"HOLD",
        }


def self_test():
    assert len(SITES)==4 and sum(v[2] for v in YEARS.values())==74
    header=b"TIMESTAMP_START,TIMESTAMP_END,TA_F,TA_F_QC,VPD_F,VPD_F_QC,VPD_ERA,RH\n202001010000,202001010030,0,1,2,1,3,50\n"
    x=first_rows(header)
    assert x["time_fields"]==["TIMESTAMP_START","TIMESTAMP_END"]
    assert set(("TA_F_QC","VPD_F_QC")).issubset(x["qc_fields"])
    assert x["era_fields"]==["VPD_ERA"]
    assert x["sample_rows_unvalidated"][0]["VPD_F_QC"]=="1"
    assert classify("EUF_DE-Gri_FLUXNET_FLUXMET_HH_2004-2025.csv")=="ONEFLUX_GAPFILLED_MET_HH_CANDIDATE"
    assert classify("EUF_DE-Gri_FLUXNET_ERA5_HH_1981-2025.csv")=="DISTRIBUTED_ERA_MET_HH_CANDIDATE"
    print("STAGE03A SELF-TEST PASS: source filename classes, HH time/QC/ERA header extraction and provenance HOLD; NO SOURCE WRITES")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage02c",type=Path)
    p.add_argument("--stage02d",type=Path)
    p.add_argument("--stage02z",type=Path)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:
        self_test();return
    if any(x is None or not x.is_file() for x in
           (args.stage02c,args.stage02d,args.stage02z)):
        p.error("Need saved original Stage02C, four-site Stage02D and Stage02Z JSON")
    if args.out_dir is None or not args.out_dir.is_dir() or \
       args.out_dir.is_symlink() or any(args.out_dir.iterdir()):
        p.error("--out-dir must be an existing EMPTY directory")
    c=json.loads(args.stage02c.read_text(encoding="utf-8"))
    d=json.loads(args.stage02d.read_text(encoding="utf-8"))
    z=json.loads(args.stage02z.read_text(encoding="utf-8"))
    validate(c,d,z)
    site_summaries=[]
    all_items=[]
    for site in SITES:
        files,summary=source_files(site)
        print("SITE",site,"SCAN_FILES",summary["visited"],
              "SOURCE_CANDIDATE_FILES",len(files),
              "SCAN_TRUNCATED",summary["truncated"])
        archives=0
        type_counts=Counter()
        for path in files:
            if path.name.lower().endswith(".zip"):
                if archives>=MAX_ARCHIVES:
                    summary["archives_skipped_due_limit"]=summary.get("archives_skipped_due_limit",0)+1
                    continue
                archives+=1
            rec=inspect_source(site,path)
            all_items.append(rec)
            type_counts[rec["candidate_kind"]]+=1
            if rec.get("members"):
                for m in rec["members"]:
                    type_counts[m["candidate_kind"]]+=1
            print(" SOURCE",rec["candidate_kind"],path.name,
                  "HEADER",rec.get("header",{}).get("status","ZIP_OR_METADATA"),
                  "ZIP_MATCHES",len(rec.get("members",[])))
            for member in rec.get("members",[])[:6]:
                h=member.get("header",{})
                print("  ZIP_MEMBER",member["candidate_kind"],member["archive_member"],
                      "TIME",",".join(h.get("time_fields",[])),
                      "QC_COUNT",len(h.get("qc_fields",[])),
                      "ERA_COUNT",len(h.get("era_fields",[])))
        summary["archive_scanned"]=archives
        summary["source_candidate_type_counts"]=dict(type_counts)
        summary["native_tower_RH_independently_QC_verified"]=False
        summary["DATM_source_timestamps_verified"]=False
        summary["scientific_release"]="HOLD"
        site_summaries.append(summary)
        print("SITE_SOURCE_QC_HOLD",site,"ORIGINAL_HH_PRODUCTS_FOUND",
              type_counts.get("BASE_HH_CANDIDATE_VERIFY_NATIVE",0),
              "FLUXMET_HH_CANDIDATES",
              type_counts.get("ONEFLUX_GAPFILLED_MET_HH_CANDIDATE",0),
              "ERA_HH_CANDIDATES",
              type_counts.get("DISTRIBUTED_ERA_MET_HH_CANDIDATE",0))
    result={
        "stage":"STAGE03A_BATCH04_FOUR_SITE_SOURCE_HH_QC_PROVENANCE_INVENTORY",
        "read_only":True,"science_release":False,
        "input_stage02c":str(args.stage02c),"input_stage02d":str(args.stage02d),
        "input_stage02z":str(args.stage02z),
        "source_modified":False,"CIME_modified":False,"Slurm_submitted":False,
        "sites":site_summaries,"source_artifact_candidates":all_items,
        "caution":"Names, headers and ZIP members are only candidate source evidence. No source-QC0 rate, selected ERA replacement, tower measurement validity, UTC mapping, or DATM raw/value equality established. Stage02D only established numerical/internal NC consistency. Native-source science HOLD for all four.",
    }
    jp=args.out_dir/"stage03a_four_site_original_met_source_QC_inventory.json"
    cp=args.out_dir/"stage03a_four_site_source_HH_QC_columns.csv"
    with jp.open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=OUT_COLS);w.writeheader()
        for obj in all_items:w.writerows(rows_for_csv(obj))
    print("JSON",jp)
    print("CSV",cp)
    print("STAGE03A COMPLETED: IDENTIFIED SOURCE CANDIDATES ONLY; ALL FOUR NATIVE_MET_QC SCIENCE HOLD")


if __name__=="__main__":
    main()
