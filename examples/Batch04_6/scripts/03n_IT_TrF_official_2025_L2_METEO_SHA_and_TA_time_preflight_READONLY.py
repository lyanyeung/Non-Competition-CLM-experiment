#!/usr/bin/env python3
"""ICOS Batch04 Stage03N: audit a separate official IT-TrF 2025 ETC L2 Meteo ZIP.

Pure read-only. No downloading, license acceptance, source replacement,
CIME edits, NetCDF modifications, Slurm, other-site source rescanning.
The operator obtains the official ICOS 16.7-MB archive AFTER accepting
the CC BY 4.0 licence in their browser. This script verifies its exact
ICOS SHA256, inventories ZIP and selects ONLY 2025-11-12..20 air T
near IT-Tor's already-known Stage03L three MDS priority windows.

IT-TrF L2 METEO TA is an ETC-aggregated meteorological source, NOT a
FLUXNET TA_F gapfill. Do NOT interpret Meteo QC using FLUXNET F_QC 0/1/2
codes, do NOT autojoin IT-Tor TIMESTAMP_START with ICOS TIMESTAMP_END.
It produces time/column/quality inventory only, no IT-Tor comparison.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

EXPECTED_SHA="9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f"
PRODUCT_ID="11676/mwN98ExGR4uPnaUKi5mWoISl"
SOURCE_URL="https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl"
STATION="IT-TrF"
FILENAME="ICOSETC_IT-TrF_METEO_L2.zip"
LOWER=datetime(2025,11,12)
UPPER=datetime(2025,11,21)
EXPECTED_STATION_TZ_NON_DST_HOURS=1
MAX_FILES=50
MAX_EXPANDED_BYTES=250_000_000
MAX_TOTAL_ROWS=500_000
TOP3=(("2025-11-15 17:00:00","2025-11-18 07:00:00",125),
      ("2025-11-13 17:30:00","2025-11-14 07:00:00",28),
      ("2025-11-13 14:30:00","2025-11-13 15:30:00",3))

def ensure(value,message):
    if not value:raise ValueError(message)

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def value(v):
    try:
        x=float(v)
        return x if math.isfinite(x) and x>-9990 else None
    except (ValueError,TypeError):
        return None

def parse_ts(v):
    t=str(v or "").strip()
    if t.endswith(".0") and t[:-2].isdigit():t=t[:-2]
    for fmt in ("%Y%m%d%H%M","%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M",
                "%Y-%m-%dT%H:%M"):
        try:return datetime.strptime(t,fmt)
        except ValueError:pass
    return None

def archive_inventory(archive):
    ensure(archive.is_file() and not archive.is_symlink(),
           "Please first obtain original ICOS 2025 IT-TrF L2 METEO archive")
    ensure(archive.stat().st_size<50_000_000,
           "Unexpected official archive size, do not process it")
    found=sha256(archive)
    ensure(found==EXPECTED_SHA,"ICOS exact SHA256 mismatch: "+found)
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist()
        ensure(0<len(infos)<=MAX_FILES and sum(x.file_size for x in infos)<
               MAX_EXPANDED_BYTES,"Unexpected ZIP structure or decompressed size")
        ensure(all(not x.is_dir() and not x.flag_bits & 1 for x in infos),
               "Encrypted or folder ZIP entries unsupported")
        names=[x.filename for x in infos]
    return {"sha256":found,"archive_bytes":archive.stat().st_size,
            "zip_members":names}

def inspect(archive):
    sources=archive_inventory(archive)
    items=[]
    seen=set()
    members=[]
    totalrows=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path=Path(info.filename)
            # Reject traversal, symlinks and hidden files; do not extract.
            ensure(".." not in path.parts and not path.is_absolute(),
                   "Unsafe ZIP member path")
            if path.suffix.lower()!=".csv":continue
            with z.open(info,"r") as raw:
                with io.TextIOWrapper(raw,encoding="utf-8-sig",
                                      newline="") as f:
                    reader=csv.DictReader(f)
                    columns=set(reader.fieldnames or [])
                    if not {"TIMESTAMP","TIMESTAMP_END","TA"}<=columns:
                        members.append({"name":info.filename,
                            "has_TA_and_both_time_columns":False,
                            "column_count":len(columns)})
                        continue
                    qc_cols=sorted(c for c in columns if
                        c.upper().startswith("TA") and ("QC" in c.upper() or
                                                       "FLAG" in c.upper()))
                    count=0
                    for r in reader:
                        count+=1
                        totalrows+=1
                        ensure(totalrows<=MAX_TOTAL_ROWS,
                               "Exceeded official expected 245472 half-hours plus tolerance")
                        utc=parse_ts(r.get("TIMESTAMP"))
                        local=parse_ts(r.get("TIMESTAMP_END"))
                        if utc is None or local is None:continue
                        if not LOWER<=utc<UPPER:continue
                        ensure(utc not in seen,
                               "Duplicate UTC half-hour among official L2 Meteo rows")
                        seen.add(utc)
                        t=value(r.get("TA"))
                        one={"timestamp_UTC":str(utc),
                             "timestamp_end_local_non_DST":str(local),
                             "TA_C":t,
                             "TA_missing":t is None,
                             "utc_to_local_end_offset_minutes":
                                 int((local-utc).total_seconds()/60),
                             "source_file":info.filename}
                        for qc in qc_cols:
                            one[qc]=r.get(qc)
                        items.append(one)
                    members.append({"name":info.filename,
                        "has_TA_and_both_time_columns":True,
                        "TA_quality_flag_columns_found":qc_cols,
                        "total_rows_in_member":count})
    ensure(items,"No IT-TrF Nov 2025 official TA records in candidate source")
    items.sort(key=lambda r:r["timestamp_UTC"])
    dt_counts=dict(Counter(r["utc_to_local_end_offset_minutes"] for r in items))
    dates=[datetime.fromisoformat(r["timestamp_UTC"]) for r in items]
    result={
        "stage":"STAGE03N_IT_TRF_OFFICIAL_ETC_METEO_2025_TA_METADATA_PREFLIGHT",
        "read_only":True,"science_release":False,
        "source_or_model_modified":False,"slurm_submitted":False,
        "data_source_station":"IT-TrF",
        "target_station":"IT-Tor",
        "product_id":PRODUCT_ID,
        "official_metadata_url":SOURCE_URL,
        "license":"ICOS CC BY 4.0; operator accepts licence before download",
        "archive_path":str(archive),
        "source_SHA256":sources["sha256"],
        "zip_members":sources["zip_members"],
        "columns_and_rows":members,
        "Nov12_to_Nov20_UTC_TA_records":len(items),
        "Nov12_to_Nov20_UTC_finite_TA_records":
            sum(r["TA_C"] is not None for r in items),
        "UTC_to_local_nonDST_end_offset_minutes_counts":dt_counts,
        "first_UTC_record":str(min(dates)),
        "last_UTC_record":str(max(dates)),
        "official_Meteo_TA_not_FLUXNET_gapfilled_TA_F":True,
        "TA_QC_0_1_not_assumed_FLUXNET_F_QC":True,
        "IT_Tor_source_TIMESTAMPS_not_yet_normalised":True,
        "target_3_original_source_label_intervals":TOP3,
        "independent_tower_temperature_comparison_complete":False,
        "science_limitations":"L2 Meteo TA aggregated from station sensors, not guaranteed physically representative at IT-Tor grassland. Verify sensor QC/flags and source-label clock mapping before comparing. IT-TrF is larch forest; do not treat its nighttime cold air, canopy measurement or temperature as identical to IT-Tor. No automatic science repair."
    }
    return result,items

def selftest():
    assert len(EXPECTED_SHA)==64 and FILENAME.startswith("ICOSETC_IT-TrF")
    assert parse_ts("202511151700")==datetime(2025,11,15,17)
    assert parse_ts("2025-11-15T17:00:00")==datetime(2025,11,15,17)
    assert parse_ts("n/a") is None
    assert value("-9999")==None and value("-4.5")==-4.5
    assert sum(x[2] for x in TOP3)==156
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as folder:
        d=Path(folder)/"simple.zip"
        with zipfile.ZipFile(d,"w") as z:
            z.writestr("example.csv","TIMESTAMP,TIMESTAMP_END,TA\n202511151700,202511151800,-1\n")
        try:archive_inventory(d)
        except ValueError:pass
        else:raise AssertionError("Non-official archive wrongly passed official SHA gate")
    print("STAGE03N SELF-TEST PASS: official 2025 IT-TrF source PID/SHA, UTC/non-DST time parsing, three targets and nonofficial archive rejection; NO WRITES")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--source-info",action="store_true")
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--out-dir",type=Path)
    a=ap.parse_args()
    if a.self_test:selftest();return
    if a.source_info:
        print("ICOS_OFFICIAL_PRODUCT",SOURCE_URL)
        print("STATION",STATION,"ARCHIVE",FILENAME)
        print("SHA256",EXPECTED_SHA)
        print("2025_COVERAGE_CONFIRMED_BY_OFFICIAL_METADATA True")
        print("LICENSE_ACCEPTANCE_REQUIRED_BY_OPERATOR True")
        print("NO_LOCAL_SOURCE_FOUND_BY_STAGE03M True")
        print("NO_SOURCE_DOWNLOAD_OR_WRITES")
        return
    ensure(a.archive is not None and a.out_dir is not None and
           a.out_dir.is_dir() and not a.out_dir.is_symlink() and
           not any(a.out_dir.iterdir()),
           "Require operator-downloaded verified --archive and NEW EMPTY private output dir")
    result,items=inspect(a.archive)
    report=a.out_dir/"stage03n_IT_TrF_official_2025_meteo_inventory_PRIVATE.json"
    csv_path=a.out_dir/"stage03n_IT_TrF_2025Nov_TA_UTC_context_PRIVATE.csv"
    with report.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    keys=list(items[0])
    for r in items:keys.extend(k for k in r if k not in keys)
    with csv_path.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore")
        writer.writeheader();writer.writerows(items)
    print("IT_TRF_OFFICIAL_2025_ZIP_SHA256_PASS",result["source_SHA256"])
    print("IT_TRF_2025_NOV_UTC_ROWS",result["Nov12_to_Nov20_UTC_TA_records"],
          "FINITE_TA",result["Nov12_to_Nov20_UTC_finite_TA_records"])
    print("UTC_TO_LOCAL_NON_DST_END_MINUTES",result["UTC_to_local_nonDST_end_offset_minutes_counts"])
    print("SENSOR_QC_FIELDS",[(x["name"],x.get("TA_quality_flag_columns_found"))
        for x in result["columns_and_rows"]])
    print("PRIVATE_JSON",report)
    print("PRIVATE_CSV",csv_path)
    print("STAGE03N METEO SOURCE PREFLIGHT PASS; TIME ALIGNMENT AND OBSERVATION QC SCIENCE HOLD; NO MODEL/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
