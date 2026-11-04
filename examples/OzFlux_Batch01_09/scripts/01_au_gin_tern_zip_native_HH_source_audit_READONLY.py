#!/usr/bin/env python3
"""OzFlux AU-Gin 2011-2025 TERN FLUXNET ZIP Stage01 (READ ONLY).

Read exact remote original ZIP, verify source SHA256 from WSL transfer receipt
supplied as --expected-sha, validate ZIP member names & metadata, inspect CSV
headers, read FLUXMET_HH (or a unique HH candidate) for first/last original
timestamps, row count, observed calendar years and missingness. Never extract
ZIP, overwrite original Gingin_L6.nc, or manufacture annual DATM.

2011..2025 are 15 CALENDAR-YEAR LABELS, not proof of a continuous >=15 elapsed
years or complete hourly/half-hourly met. Gingin site established June 2011.
Years/coverage, QC sources, clock, land cover, height still need science audit.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,re,sys,zipfile
from collections import Counter
from pathlib import Path

HOME=Path.home()
NAME="TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip"
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025")/NAME
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw")
FIELDS=("TA_F","VPD_F","P_F","PA_F","SW_IN_F","LW_IN_F","WS_F","RH_F")
def need(cond,msg):
    if not cond:raise RuntimeError(str(msg))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def date(s):
    v=str(s or "").strip()
    if re.fullmatch(r"\d{12}",v):
        return dt.datetime.strptime(v,"%Y%m%d%H%M")
    if re.fullmatch(r"\d{14}",v):
        return dt.datetime.strptime(v,"%Y%m%d%H%M%S")
    return None
def preflight_member(member):
    p=member.filename
    need("\\" not in p and not p.startswith("/") and
         not any(x in (".","..") for x in p.split("/")),
         "Unexpected ZIP member path: "+p)
    need(not member.flag_bits & 0x1,"Encrypted member: "+p)
def test():
    need(date("201101010000")==dt.datetime(2011,1,1),"timestamp decode")
    need(date("201112312330")==dt.datetime(2011,12,31,23,30),"end")
    need(date("notatime") is None,"not timestamp")
    need(len(FIELDS)==8,"met field list")
    print("OZFLUX AU-GIN TERN STAGE01 SELF-TEST PASS | ZIP header and native HH; READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return test()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-sha",required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--full-crc",action="store_true",
                   help="Read every compressed member and verify CRC (slower)")
    a=p.parse_args()
    o=a.out
    need(o.parent.resolve()==HOME.resolve() and not o.exists() and not o.is_symlink(),
         "Use unused HOME direct child for new reports")
    need(re.fullmatch("[0-9a-f]{64}",a.expected_sha or "") is not None,
         "Expected SHA256 must be exactly 64 lowercase hex digits")
    need(ZIP.is_file() and not ZIP.is_symlink() and ZIP.stat().st_size>1000,
         "Original safely isolated TERN ZIP missing on IRIDIS")
    zipsha=sha(ZIP)
    need(zipsha==a.expected_sha,"Source ZIP differs from WSL transfer receipt!")
    old=ROOT/"Gingin_L6.nc"
    need(old.is_file() and not old.is_symlink(),
         "Old Gingin_L6.nc must remain present and unchanged")
    inventory=[];headers=[];time_summary=None;warnings=[]
    with zipfile.ZipFile(ZIP,"r") as z:
        members=z.infolist()
        need(1<len(members)<=300,"Unusual archive member count")
        need(len(set(x.filename for x in members))==len(members),
             "Duplicate member names")
        need(sum(x.file_size for x in members)<12_000_000_000,
             "Unexpected decompressed payload >12GB; audit before opening")
        for x in members:
            preflight_member(x)
            inventory.append({"filename":x.filename,"file_size":x.file_size,
                             "compressed_size":x.compress_size,
                             "crc32":f"{x.CRC:08x}","is_dir":x.is_dir()})
        csvmembers=[x for x in members
                    if not x.is_dir() and x.filename.lower().endswith(".csv")]
        for m in csvmembers:
            with z.open(m,"r") as f:
                header=io.TextIOWrapper(f,encoding="utf-8-sig",
                         errors="replace",newline="").readline()
            fields=next(csv.reader([header]))
            headers.append({"member":m.filename,"columns":len(fields),
                 "first_100_columns":fields[:100],
                 "FLUXMET_available_fields":[n for n in FIELDS if n in fields],
                 "has_TIMESTAMP_START":"TIMESTAMP_START" in fields,
                 "has_TIMESTAMP_END":"TIMESTAMP_END" in fields})
        specific=[x for x in csvmembers
            if "FLUXMET_HH" in x.filename.upper()]
        if len(specific)!=1:
            warnings.append(f"FLUXMET_HH_exact_candidate_count={len(specific)}")
            # Don't silently substitute FULL_HH or FLUXMET_HR; operator review.
        else:
            m=specific[0]
            counts=Counter();gapcounts=Counter();missing=Counter()
            fst=last=prev=None
            n=0;duplicates=0;clock_step=Counter()
            with z.open(m,"r") as stream:
                txt=io.TextIOWrapper(stream,encoding="utf-8-sig",newline="")
                reader=csv.DictReader(txt)
                need(reader.fieldnames is not None and
                     "TIMESTAMP_START" in reader.fieldnames,
                     "Candidate FLUXMET_HH lacks TIMESTAMP_START")
                for row in reader:
                    stamp=date(row.get("TIMESTAMP_START"))
                    need(stamp is not None,"Unexpected raw timestamp at row "+str(n+1))
                    if fst is None:fst=stamp
                    if prev is not None:
                        mins=int((stamp-prev).total_seconds()/60)
                        clock_step[str(mins)]+=1
                        if mins<=0:duplicates+=1
                        if mins!=30:gapcounts[str(mins)]+=1
                    prev=stamp;last=stamp;n+=1;counts[stamp.year]+=1
                    for var in FIELDS:
                        if var in row and (not row[var].strip() or
                             row[var].strip() in ("-9999","-9999.0","NaN","nan")):
                            missing[var]+=1
            need(n>0 and duplicates==0,"No rows or time non-increasing")
            need(last is not None,"No usable HH timeline")
            time_summary={
                "member":m.filename,
                "first_raw_timestamp_start":fst.isoformat(sep=" "),
                "last_raw_timestamp_start":last.isoformat(sep=" "),
                "elapsed_years_between_raw_start_labels":
                       (last-fst).total_seconds()/86400/365.2425,
                "total_rows":n,"yearly_row_count":dict(sorted(counts.items())),
                "native_label_interval_minute_counts":dict(clock_step),
                "non30minute_step_histogram":dict(gapcounts),
                "missing_field_raw_strings":dict(missing),
                "actual_native_time_zone_verified":False,
                "source_timestamp_START_semantics_verified":False,
                "complete_15_years_and_meteorological_science_QC_verified":False}
            print("FLUXMET_HH_SOURCE",m.filename)
            print("NATIVE_START",time_summary["first_raw_timestamp_start"],
                  "NATIVE_END",time_summary["last_raw_timestamp_start"])
            print("ELAPSED_YEARS",round(time_summary["elapsed_years_between_raw_start_labels"],3))
            print("HH_ROWS",n,"YEAR_COUNTS",json.dumps(time_summary["yearly_row_count"]))
            print("NON30_STEP_HISTOGRAM",json.dumps(gapcounts))
            print("MISSING_MET_FIELD_STRINGS",json.dumps(missing))
        if a.full_crc:
            first_bad=z.testzip()
            need(first_bad is None,"ZIP CRC failure in member "+str(first_bad))
    out={"site":"AU-Gin","source_zip":str(ZIP),
         "source_sha256_verified":zipsha,
         "source_size_bytes":ZIP.stat().st_size,
         "Gingin_old_L6_preserved":True,"old_L6_sha256_readonly":sha(old),
         "all_zip_members":inventory,"csv_headers":headers,
         "native_FLUXMET_HH_timeline":time_summary,
         "warnings":warnings,
         "full_archive_crc_tested":bool(a.full_crc),
         "new_FLUXNET_prioritised_for_further_science_QC":True,
         "15_calendar_years_DOES_NOT_imply_15_elapsed_years":True,
         "isolated_source_not_selected_DATM":True,
         "source_science_approved":False,"AD400_authorised":False,
         "no_originals_surface_CIME_Slurm_modified":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    report=o/"stage01_AU_Gin_TERN_2011_2025_original_ZIP_source_AUDIT_HOLD.json"
    report.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
    print("ZIP_SOURCE_SHA256",zipsha)
    print("CSV_HEADER_SUMMARY",json.dumps(headers,ensure_ascii=False))
    print("STAGE01 AU-GIN ORIGINAL FLUXNET SOURCE READONLY AUDIT PASS; SCIENCE HOLD")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
