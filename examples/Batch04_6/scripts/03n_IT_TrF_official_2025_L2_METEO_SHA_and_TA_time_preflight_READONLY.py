#!/usr/bin/env python3
"""ICOS Batch04 Stage03N: audit a separate official IT-TrF 2025 ETC L2 Meteo ZIP.

Pure read-only. No downloading, license acceptance, source replacement,
CIME edits, NetCDF modifications, Slurm, other-site source rescanning.
The operator obtains the official ICOS 16.7-MB INNER data ZIP after accepting
the CC BY 4.0 licence in their browser. This script verifies its exact
ICOS SHA256, inventories ZIP and selects ONLY 2025-11-12..20 air T
near IT-Tor's already-known Stage03L three MDS priority windows.

IT-TrF L2 METEO TA is an ETC-aggregated meteorological source, NOT a
FLUXNET TA_F gapfill. Do NOT interpret Meteo QC using FLUXNET F_QC 0/1/2
codes, do NOT autojoin IT-Tor TIMESTAMP_START with ICOS TIMESTAMP_END.
Actual source CSV contains TIMESTAMP_START and TIMESTAMP_END, not TIMESTAMP.
Their 30-minute difference is an interval length, NOT a proven timezone offset.
No per-row TA_QC flag is present in the supplied source CSV. This script
produces time/column/availability inventory only, no IT-Tor comparison.
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
    # ICOS UTC T may have a terminal Z; parse and preserve the UTC clock.
    if t.endswith("Z"):t=t[:-1]
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
        ensure(all(not x.flag_bits & 1 for x in infos),
               "Encrypted ZIP entries unsupported")
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
            ensure(".." not in path.parts and not path.is_absolute(),
                   "Unsafe ZIP member path")
            if info.is_dir() or path.suffix.lower()!=".csv":continue
            with z.open(info,"r") as raw:
                with io.TextIOWrapper(raw,encoding="utf-8-sig",
                                      newline="") as f:
                    reader=csv.DictReader(f)
                    columns=set(reader.fieldnames or [])
                    # Verified against original supplied 2026 ICOS IT-TrF
                    # source: real CSV uses interval start/end labels.
                    if not {"TIMESTAMP_START","TIMESTAMP_END","TA"}<=columns:
                        members.append({"name":info.filename,
                            "has_real_start_end_TA_columns":False,
                            "column_count":len(columns)})
                        continue
                    qc_cols=sorted(c for c in columns if
                        c.upper().startswith("TA") and
                        ("QC" in c.upper() or "FLAG" in c.upper()))
                    count=0
                    for r in reader:
                        count+=1
                        totalrows+=1
                        ensure(totalrows<=MAX_TOTAL_ROWS,
                               "Unexpected Meteo CSV row count")
                        t0=parse_ts(r.get("TIMESTAMP_START"))
                        t1=parse_ts(r.get("TIMESTAMP_END"))
                        if t0 is None or t1 is None:continue
                        if not LOWER<=t0<UPPER:continue
                        ensure(t0 not in seen,
                               "Duplicate source start timestamp")
                        seen.add(t0)
                        step=int((t1-t0).total_seconds()/60)
                        ensure(step==30,
                               "Source half-hour interval boundary not 30 min")
                        temp=value(r.get("TA"))
                        one={"timestamp_start_source_label":str(t0),
                             "timestamp_end_source_label":str(t1),
                             "interval_duration_minutes":step,
                             "TA_C":temp,
                             "TA_missing":temp is None,
                             "source_file":info.filename}
                        for qc in qc_cols:
                            one[qc]=r.get(qc)
                        items.append(one)
                    members.append({"name":info.filename,
                        "has_real_start_end_TA_columns":True,
                        "TA_quality_flag_columns_found":qc_cols,
                        "total_rows_in_member":count})
    ensure(items,"No IT-TrF Nov 2025 source-label TA records found")
    items.sort(key=lambda r:r["timestamp_start_source_label"])
    dates=[datetime.fromisoformat(r["timestamp_start_source_label"])
           for r in items]
    target=[]
    for first,last,count in TOP3:
        selected=[r for r in items if first<=r["timestamp_start_source_label"]<=last]
        target.append({
            "original_IT_Tor_source_label_start_unaligned":first,
            "original_IT_Tor_source_label_end_unaligned":last,
            "expected_IT_Tor_HH":count,
            "neighbor_IT_TrF_same_literal_source_label_HH":len(selected),
            "neighbor_IT_TrF_same_literal_source_label_finite_TA_HH":
                sum(x["TA_C"] is not None for x in selected),
            "timebases_independently_aligned":False,
        })
    result={
        "stage":"STAGE03N_IT_TRF_OFFICIAL_ETC_METEO_2025_TA_METADATA_PREFLIGHT_V2",
        "read_only":True,"science_release":False,
        "source_or_model_modified":False,"slurm_submitted":False,
        "data_source_station":"IT-TrF",
        "target_station":"IT-Tor",
        "product_id":PRODUCT_ID,
        "official_metadata_url":SOURCE_URL,
        "license":"ICOS CC BY 4.0; operator accepted before download",
        "archive_path":str(archive),
        "source_SHA256":sources["sha256"],
        "zip_members":sources["zip_members"],
        "columns_and_rows":members,
        "Nov12_to_Nov20_source_label_TA_records":len(items),
        "Nov12_to_Nov20_source_label_finite_TA_records":
            sum(r["TA_C"] is not None for r in items),
        "observed_start_end_interval_duration_minutes":
            dict(Counter(r["interval_duration_minutes"] for r in items)),
        "first_source_label":str(min(dates)),
        "last_source_label":str(max(dates)),
        "official_Meteo_TA_not_FLUXNET_gapfilled_TA_F":True,
        "per_row_TA_quality_flag_fields_available":
            any(bool(r["TA_quality_flag_columns_found"])
                for r in members if r.get("has_real_start_end_TA_columns")),
        "source_timestamp_start_end_are_UTC_or_local_independently_verified":False,
        "IT_Tor_source_TIMESTAMPS_not_yet_normalised":True,
        "priority_intervals_same_literal_label_availability":target,
        "neighbor_TA_direct_sensor_QC0_verified":False,
        "independent_tower_temperature_comparison_complete":False,
        "science_limitations":
            "Original source CSV columns are TIMESTAMP_START and TIMESTAMP_END, 30 min apart. This interval difference is not timezone offset; independent UTC/local mapping is unresolved. Original CSV has no per-row TA_QC column. Finite aggregate L2 TA is NOT automatically a verified source QC0 direct measurement. IT-TrF forest canopy/height differs from IT-Tor grassland. Do not alter source forcing."
    }
    return result,items

def selftest():
    assert len(EXPECTED_SHA)==64 and FILENAME.startswith("ICOSETC_IT-TrF")
    assert parse_ts("202511151700")==datetime(2025,11,15,17)
    assert parse_ts("2025-11-15T17:00:00")==datetime(2025,11,15,17)
    assert parse_ts("2025-11-15T17:00:00Z")==datetime(2025,11,15,17)
    assert parse_ts("n/a") is None
    assert value("-9999")==None and value("-4.5")==-4.5
    assert sum(x[2] for x in TOP3)==156
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as folder:
        d=Path(folder)/"simple.zip"
        with zipfile.ZipFile(d,"w") as z:
            z.writestr("example.csv","TIMESTAMP_START,TIMESTAMP_END,TA\n202511151700,202511151730,-1\n")
        try:archive_inventory(d)
        except ValueError:pass
        else:raise AssertionError("Non-official archive wrongly passed official SHA gate")
    print("STAGE03N SELF-TEST PASS: source 30-min START/END labels, official ZIP SHA rejection, 3 target intervals; NO FORCING OR SOURCE WRITES")

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
    csv_path=a.out_dir/"stage03n_IT_TrF_2025Nov_TA_SOURCE_LABEL_context_PRIVATE.csv"
    with report.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    keys=list(items[0])
    for r in items:keys.extend(k for k in r if k not in keys)
    with csv_path.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction="ignore")
        writer.writeheader();writer.writerows(items)
    print("IT_TRF_OFFICIAL_2025_ZIP_SHA256_PASS",result["source_SHA256"])
    print("IT_TRF_2025_NOV_SOURCE_LABEL_ROWS",result["Nov12_to_Nov20_source_label_TA_records"],
          "FINITE_TA",result["Nov12_to_Nov20_source_label_finite_TA_records"])
    print("START_TO_END_INTERVAL_MINUTES",result["observed_start_end_interval_duration_minutes"])
    for q in result["priority_intervals_same_literal_label_availability"]:
        print("PRIORITY_SAME_SOURCE_LABEL_UNALIGNED",q["original_IT_Tor_source_label_start_unaligned"],
              "TA_ROWS",q["neighbor_IT_TrF_same_literal_source_label_HH"],
              "FINITE_TA",q["neighbor_IT_TrF_same_literal_source_label_finite_TA_HH"])
    print("TIMEBASE_ALIGNED False; TA_DIRECT_QC0_VERIFIED False")
    print("SENSOR_QC_FIELDS",[(x["name"],x.get("TA_quality_flag_columns_found"))
        for x in result["columns_and_rows"]])
    print("PRIVATE_JSON",report)
    print("PRIVATE_CSV",csv_path)
    print("STAGE03N METEO SOURCE PREFLIGHT PASS; TIME ALIGNMENT AND OBSERVATION QC SCIENCE HOLD; NO MODEL/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
