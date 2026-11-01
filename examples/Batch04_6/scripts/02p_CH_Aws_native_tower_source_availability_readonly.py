#!/usr/bin/env python3
"""Batch04 Stage02P: find CH-Aws original-tower observation provenance, READ ONLY.

Stage02O confirmed 20/20 selected processed-VPD-derived RH values <10%, whereas
ERA5/ERA5-Land RH differs by >=50 percentage points. This script inventories
the *site-scoped* source products, archive member names, raw CSV headers and
small JSON provenance references to find possible ORIGINAL unfilled tower
humidity/temperature/QC evidence. It does NOT infer native measurements from
a product called "raw": EUF FLUXMET_HH is processed/gapfilled.

No archive extraction, whole 372MB FLUXMET read, source/NC/CIME/Slurm changes
or Git worktree mutations. Only --out-dir writes new JSON and CSV in an
already-existing EMPTY directory. Direct original tower QC remains HOLD.
"""
from __future__ import annotations
import argparse
import collections
import csv
import gzip
import hashlib
import json
import os
import re
import tarfile
import zipfile
from pathlib import Path

STAGE = "STAGE02O_CH_AWS_REPAIR_EVENT_SCIENCE_TRIAGE_READONLY"
DEFAULT_ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws")
EXTENSIONS = (".csv", ".csv.gz", ".json", ".zip", ".tar", ".tar.gz",
              ".tgz", ".nc", ".nc4", ".txt", ".md", ".xlsx", ".dat", ".gz")
SKIP_DIRS = {".git", "__pycache__", ".cache", "logs", "archive", "run",
             "bld", "Buildconf", "CaseDocs", ".conda", "node_modules"}
MAX_FILES = 20000
MAX_DEPTH = 7
MAX_CANDIDATES = 300
MAX_MEMBERS = 80
MAX_SMALL_JSON = 5_000_000
MAX_HEADER_BYTES = 24000
OUTPUT_COLUMNS = ("classification", "path", "bytes", "content_examined",
                  "header_excerpt", "RH_TA_VPD_QC_column_names",
                  "archive_member_examples", "metadata_references",
                  "science_status")


def classify(path):
    p=str(path).lower()
    name=path.name.lower()
    if re.match(r".*_datm_(?:19|20)\d{2}.*\.nc4?$",name):
        return "MODEL_DATM_ANNUAL_NOT_RAW"
    if "merged_multisource" in p:
        return "MERGED_PROCESSED_CANDIDATE_NOT_NATIVE"
    if "fluxmet_hh" in name or "fluxmet_ww" in name:
        return "DISTRIBUTED_PROCESSED_FLUXMET_NOT_NATIVE"
    if "stage" in p and ("ledger" in name or "manifest" in name):
        return "EXPLORATORY_REVISION_EVIDENCE_NOT_TOWER"
    if "bif" in name or "!toc" in name:
        return "DISTRIBUTED_PRODUCT_METADATA"
    if any(k in p for k in ("tower", "logger", "instrument", "original", "unfilled",
                            "native", "obs", "sensor", "raw", "icos", "euf_", "rh")):
        return "POSSIBLE_TOWER_OR_SOURCE_PRODUCT_UNVERIFIED"
    return "UNCLASSIFIED_SOURCE_OR_METADATA"


def suffix(path):
    n=path.name.lower()
    return next((x for x in sorted(EXTENSIONS,key=len,reverse=True)
                 if n.endswith(x)),None)


def check_stage(data):
    if not isinstance(data,dict) or data.get("stage")!=STAGE or \
       data.get("read_only") is not True or data.get("science_release") is not False:
        raise ValueError("Require original unreleased Stage02O result")
    summary=data.get("summary",{})
    if summary.get("event_count")!=20 or summary.get("low_implied_RH_under10_events")!=20 \
       or summary.get("native_tower_RH_verified_events")!=0:
        raise ValueError("Stage02O source/event counts do not match operator record")
    if summary.get("ERA5_conflict_50pp_events")!=20 or \
       summary.get("ERA5Land_conflict_50pp_events")!=20:
        raise ValueError("Expected 20/20 ERA-vs-implied-RH source conflicts")
    events=data.get("events_ranked")
    if not isinstance(events,list) or len(events)!=20:
        raise ValueError("Stage02O event record missing")
    ids=[e.get("event_id") for e in events]
    if len(set(ids))!=20:
        raise ValueError("Duplicate high-risk event ID")
    if any(e.get("scientific_release")!="HOLD" or
           e.get("native_tower_RH_QC_verified") is not False for e in events):
        raise ValueError("Unexpected original tower QC approval")
    return events


def within(root,path):
    if path.is_symlink():
        return False
    try:
        return path.resolve(strict=True).is_relative_to(root)
    except (OSError,RuntimeError):
        return False


def header_of(path, ext):
    try:
        if ext==".csv.gz":
            with gzip.open(path,"rt",encoding="utf-8-sig",errors="replace") as f:
                raw=f.readline(MAX_HEADER_BYTES)
        else:
            with path.open("r",encoding="utf-8-sig",errors="replace") as f:
                raw=f.readline(MAX_HEADER_BYTES)
        header=next(csv.reader([raw]))
        headers=[h.strip().strip('"') for h in header]
        candidates=[
            k for k in headers if re.search(
                r"(^|[_\W])(RH|TA|VPD|HUMID|DEW|QC|QUALITY|FLAG|ERA|TIMESTAMP|TIME|PRESS|PA)([_\W]|$)",
                k,re.I)]
        return raw.strip()[:1000],candidates[:55],"CSV_HEADER_ONLY"
    except Exception as exc:
        return "HEADER_ERROR_"+type(exc).__name__,[],"HEADER_READ_ERROR"


def json_references(path):
    if path.stat().st_size>MAX_SMALL_JSON:
        return {"status":"SKIPPED_LARGE_JSON"}
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj,dict):
            return {"status":"NOT_OBJECT"}
        refs={}
        for k,v in obj.items():
            if re.search(r"source|raw|input|rh|sensor|native|era|qc|original|reference|sha|status|version",k,re.I):
                if isinstance(v,(str,int,float,bool,type(None))):
                    refs[k]=str(v)[:220]
                elif isinstance(v,list):
                    refs[k]=str(v[:5])[:400]
                elif isinstance(v,dict):
                    refs[k]=str(list(v.items())[:5])[:400]
            if len(refs)>=28:break
        return {"status":"PARSED_JSON_METADATA","keys":list(obj)[:45],"references":refs}
    except Exception as exc:
        return {"status":"JSON_ERROR_"+type(exc).__name__,"reason":str(exc)[:180]}


def archive_names(path,ext):
    if path.stat().st_size>2_000_000_000:
        return {"status":"SKIPPED_ARCHIVE_OVER_2GB"}
    try:
        if ext==".zip":
            with zipfile.ZipFile(path) as f:
                names=f.namelist()
        else:
            # Listing TAR.GZ may stream all compressed contents; only small archives.
            if path.stat().st_size>25_000_000:
                return {"status":"SKIPPED_COMPRESSED_TAR_OVER_25MB"}
            with tarfile.open(path,"r:*") as f:
                names=[m.name for m in f if m.isfile()]
        interesting=[n for n in names if re.search(
            r"(^|/|[_\W])(RH|TA|HUMID|TOWER|MET|OBS|SENSOR|LOGGER|QC|FLUX)([_\W]|$)",
            n,re.I)]
        return {"status":"ARCHIVE_NAME_ONLY_NO_EXTRACTION",
                "member_count":len(names),
                "interesting_members":interesting[:MAX_MEMBERS],
                "first_members":names[:15]}
    except Exception as exc:
        return {"status":"ARCHIVE_ERROR_"+type(exc).__name__,
                "reason":str(exc)[:180]}


def nc_inventory(path):
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        return {"status":"NETCDF4_NOT_INSTALLED","reason":str(exc)}
    try:
        with Dataset(path,"r") as ds:
            vars=list(ds.variables)
            wanted=[k for k in vars if re.search(
                r"(^|[_\W])(RH|TA|HUMID|VPD|QC|TEMP|TIME|ERA|PRESS)([_\W]|$)",
                k,re.I)]
            return {"status":"NC_HEADER_VARIABLE_NAMES_ONLY",
                    "variables":vars[:80],"humidity_qc_candidates":wanted[:65]}
    except Exception as exc:
        return {"status":"NETCDF_HEADER_ERROR_"+type(exc).__name__,
                "reason":str(exc)[:180]}


def inventory(root):
    root=root.resolve(strict=True)
    if root.name!="CH-Aws" or root.parent.name!="MY_EC_SITE":
        raise ValueError("Refuse unscoped tree; require the original MY_EC_SITE/CH-Aws root")
    files_seen=0
    counts=collections.Counter()
    candidates=[]
    truncated=False
    base_depth=len(root.parts)
    for parent,dirs,files in os.walk(root,topdown=True,followlinks=False):
        depth=len(Path(parent).parts)-base_depth
        dirs[:]=[d for d in sorted(dirs) if d not in SKIP_DIRS and
                 not (Path(parent)/d).is_symlink()] if depth<MAX_DEPTH else []
        for name in sorted(files):
            files_seen+=1
            if files_seen>MAX_FILES:
                truncated=True
                break
            file=Path(parent)/name
            ext=suffix(file)
            if ext is None or not within(root,file) or not file.is_file():
                continue
            kind=classify(file)
            counts[kind]+=1
            if kind=="MODEL_DATM_ANNUAL_NOT_RAW":
                continue
            if len(candidates)>=MAX_CANDIDATES:
                truncated=True
                continue
            rec={"classification":kind,"path":str(file),
                 "bytes":file.stat().st_size,
                 "content_examined":"NAME_AND_SIZE_ONLY",
                 "header_excerpt":"",
                 "RH_TA_VPD_QC_column_names":[],
                 "archive_member_examples":[],
                 "metadata_references":{},
                 "science_status":"HOLD_NATIVE_SOURCE_QC_AND_TIME"}
            if ext in (".csv",".csv.gz"):
                header,fields,status=header_of(file,ext)
                rec.update(header_excerpt=header,
                           RH_TA_VPD_QC_column_names=fields,
                           content_examined=status)
            elif ext==".json":
                info=json_references(file)
                rec.update(metadata_references=info,
                           content_examined=info.get("status","UNKNOWN"))
            elif ext in (".zip",".tar",".tar.gz",".tgz"):
                info=archive_names(file,ext)
                rec.update(archive_member_examples=info.get("interesting_members",[]),
                           metadata_references=info,
                           content_examined=info.get("status","UNKNOWN"))
            elif ext in (".nc",".nc4"):
                info=nc_inventory(file)
                rec.update(RH_TA_VPD_QC_column_names=info.get("humidity_qc_candidates",[]),
                           metadata_references=info,
                           content_examined=info.get("status","UNKNOWN"))
            candidates.append(rec)
        if files_seen>MAX_FILES:
            break
    return {"site_root":str(root),"files_seen":files_seen,
            "truncated":truncated,"classes":dict(counts),
            "candidate_artifacts":candidates,
            "interpretation":"Only filenames/headers/metadata, not actual sensor QC observations"}


def self_test():
    fake={
        "stage":STAGE,"read_only":True,"science_release":False,
        "summary":{"event_count":20,"low_implied_RH_under10_events":20,
                   "native_tower_RH_verified_events":0,
                   "ERA5_conflict_50pp_events":20,
                   "ERA5Land_conflict_50pp_events":20},
        "events_ranked":[{"event_id":f"E{k:03d}","scientific_release":"HOLD",
                          "native_tower_RH_QC_verified":False}
                         for k in range(1,21)]
    }
    assert len(check_stage(fake))==20
    assert classify(Path("/x/CH-Aws_DATM_2007.nc"))=="MODEL_DATM_ANNUAL_NOT_RAW"
    assert classify(Path("/x/raw/EUF_CH-Aws_FLUXNET_FLUXMET_HH.csv"))=="DISTRIBUTED_PROCESSED_FLUXMET_NOT_NATIVE"
    assert classify(Path("/x/instrument/native_tower_RH.csv"))=="POSSIBLE_TOWER_OR_SOURCE_PRODUCT_UNVERIFIED"
    assert suffix(Path("original_met.csv.gz"))==".csv.gz"
    assert len(OUTPUT_COLUMNS)==len(set(OUTPUT_COLUMNS))
    print("STAGE02P SELF-TEST PASS: 20 Stage02O events, source path classes, source QC HOLD; NO WRITES")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage02o",type=Path)
    p.add_argument("--site-root",type=Path,default=DEFAULT_ROOT)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:
        self_test();return
    if args.stage02o is None or not args.stage02o.is_file():
        p.error("--stage02o must point to the saved successful Stage02O JSON")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        p.error("--out-dir must exist and be EMPTY")
    events=check_stage(json.loads(args.stage02o.read_text(encoding="utf-8")))
    data=inventory(args.site_root)
    priority={
        "POSSIBLE_TOWER_OR_SOURCE_PRODUCT_UNVERIFIED":0,
        "DISTRIBUTED_PRODUCT_METADATA":1,
        "UNCLASSIFIED_SOURCE_OR_METADATA":2,
        "EXPLORATORY_REVISION_EVIDENCE_NOT_TOWER":3,
        "DISTRIBUTED_PROCESSED_FLUXMET_NOT_NATIVE":4,
        "MERGED_PROCESSED_CANDIDATE_NOT_NATIVE":5
    }
    data["candidate_artifacts"].sort(key=lambda r:(
        priority.get(r["classification"],9),r["path"]))
    for record in data["candidate_artifacts"][:55]:
        print("SOURCE",record["classification"],record["path"],
              "BYTES",record["bytes"],
              "READ_MODE",record["content_examined"],
              "RH_QC_COLS",",".join(record["RH_TA_VPD_QC_column_names"][:18]) or "NONE",
              "ARCHIVE_MEMBERS",",".join(record["archive_member_examples"][:4]) or "NONE")
    print("SITE_FILES_SCANNED",data["files_seen"],
          "TRUNCATED",data["truncated"],
          "CATEGORIES",json.dumps(data["classes"],sort_keys=True))
    report={
        "stage":"STAGE02P_CH_AWS_NATIVE_TOWER_SOURCE_AVAILABILITY_DISCOVERY",
        "read_only":True,"science_release":False,
        "source_modified":False,"slurm_submitted":False,
        "input_stage02o":str(args.stage02o),
        "risk_event_times":[{"event_id":x["event_id"],"time_DATM":x.get("DATM_time"),
                             "flags":x.get("flags","")}
                            for x in events],
        "source_manifest":data,
        "conclusion":"DISCOVERY_ONLY; raw humidity observation & QC NOT ESTABLISHED",
        "limitations":"Only CH-Aws site tree depth<=7 and 20k files; no external/missing original package inferred. No full observations/zip members extracted or compared at event times. FLUXMET _F is processed.",
    }
    jp=args.out_dir/"stage02p_CH_Aws_native_source_availability.json"
    cp=args.out_dir/"stage02p_CH_Aws_source_file_headers.csv"
    with jp.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for rec in data["candidate_artifacts"]:
            row={k:rec.get(k) for k in OUTPUT_COLUMNS}
            for key in ("RH_TA_VPD_QC_column_names","archive_member_examples","metadata_references"):
                row[key]=json.dumps(row[key],ensure_ascii=False)
            writer.writerow(row)
    print("REPORT",jp)
    print("CSV",cp)
    print("SCIENTIFIC_HOLD: NO ORIGINAL TOWER RH/QC / INDEPENDENT ERA VALIDATED; NO SOURCE/SLURM WRITES")


if __name__=="__main__":
    main()
