#!/usr/bin/env python3
"""Batch04 Stage02T: locate the original CH-Aws EUF ERA5_HH source, READ-ONLY.

Stage02S's exact Stage03-registered EUF_ERA5_HH file was missing from the
expected on-disk location. Stage02T checks names and ZIP member inventories
under explicitly scoped site and historical-workflow roots. ZIP inspection
reads central directories ONLY: NO extraction, download, original forcing/
CIME/Slurm/Git changes, or full processed FLUXMET data reading.

An archive name/member match is ONLY a *source candidate*, not source SHA,
original tower RH QC, timezone correctness, or permission to run AD5/AD400.
Only a NEW EMPTY --out-dir gets JSON and CSV.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import zipfile
from pathlib import Path

STAGE_S="STAGE02S_CH_AWS_ORIGINAL_EUF_ERA_CLOCK_EVIDENCE_READONLY"
STAGE_R="STAGE02R_CH_AWS_LEGACY_SOURCE_GROUP_AND_CLOCK_AUDIT"
ERA_FILE="EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv"
ZIP_LIMIT_BYTES=2_000_000_000
MAX_ROOT_FILES=25000
MAX_DEPTH=6
MAX_REPORT_CANDIDATES=350
MAX_ARCHIVE_ITEMS=25000
MAX_ZIPS=50
CSV_FIELDS=("candidate_kind","path","size_bytes",
            "archive_member","archive_member_uncompressed_bytes",
            "source_sha_verified","original_tower_QC_verified",
            "scientific_release")
SKIP_DIRS={".git",".cache","__pycache__",".conda","node_modules","build",
           "run","bld","CaseDocs","logs","old_outputs","archive"}


def validate(s,r):
    if not isinstance(s,dict) or s.get("stage")!=STAGE_S or \
       s.get("read_only") is not True or s.get("scientific_release") is not False:
        raise ValueError("Require saved Stage02S read-only HOLD JSON")
    if s.get("source_status")!="MISSING_ORIGINAL_DISTRIBUTED_ERA5_HH_INPUT" or \
       s.get("source_rows_scanned")!=0:
        raise ValueError("Stage02S source status changed; do not invoke missing-source workflow")
    if s.get("native_tower_RH_QC_verified") is not False or \
       s.get("DATM_UTC_local_conversion_approved") is not False:
        raise ValueError("Stage02S native QC/time unexpectedly released")
    if not isinstance(r,dict) or r.get("stage")!=STAGE_R or \
       r.get("read_only") is not True or r.get("science_release") is not False:
        raise ValueError("Require original Stage02R read-only HOLD report")
    if r.get("source_native_tower_RH_QC_verified") is not False:
        raise ValueError("Stage02R original sensor QC unexpectedly approved")
    file=Path(s.get("ERA5_original_source",""))
    if not file.is_absolute() or file.name!=ERA_FILE or \
       file.parent.name!="EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2" or \
       file.parent.parent.name!="raw" or \
       file.parent.parent.parent.name!="forcing" or \
       file.parent.parent.parent.parent.name!="CH-Aws":
        raise ValueError("Stage02S original source path unexpected")
    input_rows=r.get("historical_source_file_evidence",{}).get("STAGE03_INPUTS",{}).get("first_rows_uninterpreted",[])
    paths=[rec.get("raw_values",{}).get("path") for rec in input_rows
           if rec.get("raw_values",{}).get("label")=="EUF_ERA5"]
    if paths!=[str(file)]:
        raise ValueError("Stage02R original registered EUF_ERA5 path does not match Stage02S")
    return file


def relevant(name,root_kind):
    n=name.lower()
    # User's historical-root folders contain many site names, avoid
    # unrelated ERA5 products. Site root is already specifically CH-Aws.
    if root_kind=="SITE":
        return ("era5" in n and ("hh" in n or "euf" in n)) or n.endswith(".zip")
    return ("ch-aws" in n or "ch_aws" in n or "chaws" in n or
            "weissenstein" in n) and (
            "era" in n or n.endswith(".zip") or "fluxnet" in n)


def safe_file(path,root):
    if path.is_symlink() or not path.is_file():return False
    try:return path.resolve(strict=True).is_relative_to(root)
    except (OSError,RuntimeError):return False


def inspect_zip(path):
    if path.stat().st_size>ZIP_LIMIT_BYTES:
        return {"status":"ZIP_OVER_2GB_SKIP","matched":[],
                "members_checked":0,"total_members":None}
    try:
        with zipfile.ZipFile(path,"r") as z:
            info=z.infolist()
            if len(info)>MAX_ARCHIVE_ITEMS:
                return {"status":"ZIP_MEMBER_COUNT_LIMIT_SKIP","matched":[],
                        "members_checked":0,"total_members":len(info)}
            members=[]
            for item in info:
                if item.is_dir():continue
                n=Path(item.filename).name
                if n==ERA_FILE or re.search(r"(?i)(?:CH[-_]Aws|CHAws).*ERA5.*HH",item.filename):
                    members.append({
                        "archive_member":item.filename,
                        "uncompressed_bytes":item.file_size,
                        "crc32_unverified":f"{item.CRC:08x}",
                        "exact_expected_basename":n==ERA_FILE,
                    })
            return {"status":"ZIP_DIRECTORY_READ_ONLY",
                    "members_checked":len(info),"total_members":len(info),
                    "matched":members}
    except (OSError,zipfile.BadZipFile,zipfile.LargeZipFile) as exc:
        return {"status":"ZIP_ERROR_"+type(exc).__name__,
                "members_checked":0,"total_members":None,"matched":[]}


def bounded_scan(root,kind):
    real=root.resolve(strict=True)
    seen=0
    truncated=False
    matches=[]
    zipped=[]
    for here,dirs,files in os.walk(real,topdown=True,followlinks=False):
        depth=len(Path(here).parts)-len(real.parts)
        dirs[:]=[d for d in sorted(dirs)
                 if d not in SKIP_DIRS and not (Path(here)/d).is_symlink()] \
                if depth<MAX_DEPTH else []
        for name in sorted(files):
            seen+=1
            if seen>MAX_ROOT_FILES:
                truncated=True;break
            if not relevant(name,kind):continue
            path=Path(here)/name
            if not safe_file(path,real):continue
            if len(matches)>=MAX_REPORT_CANDIDATES:
                truncated=True;break
            typ=("EXACT_EXPECTED_CSV" if name==ERA_FILE else
                 "POSSIBLE_ERA_HH_CSV" if name.lower().endswith((".csv",".csv.gz")) else
                 "POSSIBLE_ARCHIVE_ZIP" if name.lower().endswith(".zip") else
                 "OTHER_MATCHING_FILENAME")
            record={"candidate_kind":typ,"path":str(path),
                    "size_bytes":path.stat().st_size,
                    "source_sha_verified":False,
                    "original_tower_QC_verified":False,
                    "scientific_release":"HOLD"}
            matches.append(record)
            if name.lower().endswith(".zip") and len(zipped)<MAX_ZIPS:
                zipped.append(path)
        if truncated:break
    return {"root":str(real),"kind":kind,
            "files_visited":seen,"truncated":truncated,
            "candidate_files":matches,
            "candidate_zip_paths":[str(z) for z in zipped],
            "all_zips_inspected":len(zipped)<MAX_ZIPS}


def run(s,r,roots):
    expected=validate(s,r)
    scans=[]
    zip_files={}
    out=[]
    for root,kind in roots:
        if not root.is_dir():
            scans.append({"root":str(root),"kind":kind,"status":"ROOT_MISSING"})
            continue
        res=bounded_scan(root,kind)
        for x in res["candidate_files"]:
            out.append({**x,"archive_member":"","archive_member_uncompressed_bytes":""})
        for filename in res["candidate_zip_paths"]:
            if filename not in zip_files:
                zip_files[filename]=inspect_zip(Path(filename))
        scans.append({k:v for k,v in res.items() if k!="candidate_files"})
        scans[-1]["reported_candidate_files"]=len(res["candidate_files"])
    for filename,details in zip_files.items():
        for item in details["matched"]:
            out.append({"candidate_kind":"ZIP_MEMBER_SOURCE_CANDIDATE",
                        "path":filename,"size_bytes":Path(filename).stat().st_size,
                        "archive_member":item["archive_member"],
                        "archive_member_uncompressed_bytes":item["uncompressed_bytes"],
                        "source_sha_verified":False,
                        "original_tower_QC_verified":False,
                        "scientific_release":"HOLD"})
    return {
        "stage":"STAGE02T_CH_AWS_MISSING_EUF_ERA_SOURCE_ARCHIVE_DISCOVERY",
        "read_only":True,"science_release":False,
        "source_expected_path":str(expected),
        "source_still_missing":not expected.is_file(),
        "scans":scans,"zip_metadata":zip_files,"source_candidates":out,
        "any_exact_named_file":any(x["candidate_kind"]=="EXACT_EXPECTED_CSV" for x in out),
        "any_exact_zip_member":any(x.get("archive_member","").split("/")[-1]==ERA_FILE for x in out),
        "source_integrity_proven":False,"source_QC_verified":False,
        "era_time_verified":False,"slurm_submitted":False,"source_modified":False,
        "limitations":"Bounded roots, depth/file-count limits. ZIP central directory only; no extract/hash or native tower observations. Missing exact path does not prove source unavailable elsewhere.",
    }


def self_test():
    s={"stage":STAGE_S,"read_only":True,"scientific_release":False,
       "source_status":"MISSING_ORIGINAL_DISTRIBUTED_ERA5_HH_INPUT",
       "source_rows_scanned":0,
       "native_tower_RH_QC_verified":False,
       "DATM_UTC_local_conversion_approved":False,
       "ERA5_original_source":("/iridisfs/scratch/ly3n24/CLM_FATES/sites/"
                              "MY_EC_SITE/CH-Aws/forcing/raw/"
                              "EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/"+ERA_FILE)}
    r={"stage":STAGE_R,"read_only":True,"science_release":False,
       "source_native_tower_RH_QC_verified":False,
       "historical_source_file_evidence":{"STAGE03_INPUTS":{
           "first_rows_uninterpreted":[{"raw_values":{
               "label":"EUF_ERA5","path":s["ERA5_original_source"]}}]}}}
    assert validate(s,r).name==ERA_FILE
    assert relevant("EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv","SITE")
    assert relevant("EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2.zip","HIST")
    assert not relevant("EUF_DE-Gri_FLUXNET_ERA5_HH.csv","HIST")
    print("STAGE02T SELF-TEST PASS: exact missing-source pin, guarded candidate ZIP-name discovery; NO WRITES")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage02s",type=Path)
    p.add_argument("--stage02r",type=Path)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:self_test();return
    if any(f is None or not f.is_file() for f in (args.stage02s,args.stage02r)):
        p.error("Original Stage02S and Stage02R JSON inputs required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        p.error("--out-dir must be existing and EMPTY")
    s=json.loads(args.stage02s.read_text(encoding="utf-8"))
    r=json.loads(args.stage02r.read_text(encoding="utf-8"))
    expected=validate(s,r)
    site_root=expected.parent.parent.parent.parent
    hist_root=Path.home()/"FLUXNET_MultiSite_11"
    output=run(s,r,[(site_root,"SITE"),(hist_root,"HIST")])
    output["stage02s_input"]=str(args.stage02s)
    output["stage02r_input"]=str(args.stage02r)
    for scan in output["scans"]:
        print("SEARCH",scan["kind"],scan["root"],
              "FILENAMES",scan.get("files_visited",0),
              "CANDIDATES",scan.get("reported_candidate_files",0),
              "TRUNCATED",scan.get("truncated","ROOT_MISSING"))
    for x in output["source_candidates"][:70]:
        print("CANDIDATE",x["candidate_kind"],x["path"],
              "ARCHIVE_MEMBER",x.get("archive_member","") or "NONE",
              "BYTES",x["size_bytes"])
    for path,info in output["zip_metadata"].items():
        print("ZIP",path,"STATUS",info["status"],
              "MEMBERS",info["total_members"],
              "MATCHES",len(info["matched"]))
    print("EXACT_CSV_FOUND",output["any_exact_named_file"],
          "EXACT_ZIP_MEMBER_FOUND",output["any_exact_zip_member"])
    print("STILL_NO_SCIENCE_RELEASE: source existence != integrity, tower QC or actual ERA clock")
    jp=args.out_dir/"stage02t_CH_Aws_ERA5_original_source_location.json"
    cp=args.out_dir/"stage02t_CH_Aws_archive_source_candidates.csv"
    with jp.open("x",encoding="utf-8") as f:
        json.dump(output,f,indent=2,ensure_ascii=False);f.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=CSV_FIELDS)
        w.writeheader();w.writerows(output["source_candidates"])
    print("JSON",jp)
    print("CSV",cp)
    print("SCIENCE_HOLD; NO SOURCE/NETCDF/CASE/SLURM WRITES")


if __name__=="__main__":
    main()
