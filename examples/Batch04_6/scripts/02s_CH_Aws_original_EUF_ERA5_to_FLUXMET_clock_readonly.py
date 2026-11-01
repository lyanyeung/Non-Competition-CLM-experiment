#!/usr/bin/env python3
"""ICOS Batch04 Stage02S: verify original-distribution ERA source/clock candidates.

READ ONLY. Original EUF/ONEFlux BIF metadata: station UTC_OFFSET=1;
Stage09 historical temperature-offset diagnostic favored its 0-hour trial,
but their two reference clocks need not share an offset convention.
Stage02S looks for the EXACT EUF_ERA5_HH source identified by Stage03,
streams it once (no full-table materialization), and cross-checks 20
Stage02L original FLUXMET START/END VPD_ERA/TA_ERA values under separate
literal clock-label offsets -120..+120 minutes. It does not infer the true
UTC transform, original native tower RH, or a scientifically best forcing.

The distributed EUF_ERA5_HH is ERA-derived, NOT independent tower evidence.
If missing, report its absence without inventing/creating/downloading it.
Only a NEW EMPTY --out-dir receives JSON and CSV. No source, NetCDF, case,
Slurm, Git worktree, reanalysis download or model run.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import json
import math
from pathlib import Path

STAGE_R="STAGE02R_CH_AWS_LEGACY_SOURCE_GROUP_AND_CLOCK_AUDIT"
STAGE_L="STAGE02L_CH_AWS_DATM_FLUXMET_TWO_CLOCK_SOURCE_EVIDENCE"
OFFSETS=(-120,-90,-60,-30,0,30,60,90,120)
MAX_SOURCE_BYTES=2_000_000_000
MAX_SOURCE_ROWS=1_000_000
MAX_RECORDS=20*2*len(OFFSETS)
CSV_FIELDS=(
    "event_id","DATM_label_unverified","source_ERA_clock",
    "source_ERA_timestamp_raw","source_label_offset_minutes",
    "FLUXMET_clock_candidate","FLUXMET_VPD_ERA_raw",
    "ERA_source_VPD_ERA_raw","absolute_VPD_difference_hPa",
    "FLUXMET_TA_ERA_raw","ERA_source_TA_ERA_raw",
    "absolute_TA_difference_C",
    "native_tower_RH_QC_verified","actual_UTC_clock_verified",
    "independent_ERA5_provenance_verified","scientific_release",
)


def parse(s):
    raw=str(s).strip()
    for fmt in ("%Y%m%d%H%M","%Y%m%d%H%M%S",
                "%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M"):
        try:return dt.datetime.strptime(raw,fmt)
        except ValueError:pass
    return None


def num(s):
    try:
        v=float(str(s).strip())
        return v if math.isfinite(v) and v>-9990 else None
    except (TypeError,ValueError):return None


def validate(r,l):
    if r.get("stage")!=STAGE_R or r.get("read_only") is not True or \
       r.get("science_release") is not False or \
       r.get("source_native_tower_RH_QC_verified") is not False or \
       r.get("clock_conversion_approved") is not False:
        raise ValueError("Require original Stage02R source/time HOLD report")
    if l.get("stage")!=STAGE_L or l.get("read_only") is not True or \
       l.get("scientific_release") is not False or \
       l.get("FLUXMET_original_product_is_processed",True) is not True:
        # Stage02L schema has source data and flags, not original-product flag;
        # reject only if explicitly false.
        raise ValueError("Require source-pinned Stage02L all-version HOLD report")
    events=l.get("events")
    if not isinstance(events,list) or len(events)!=20:
        raise ValueError("Stage02L needs exactly 20 source-clock event rows")
    found=set()
    for item in events:
        eid=item.get("event_id")
        if eid in found or not isinstance(eid,str) or parse(item.get("event_time_DATM")) is None:
            raise ValueError("Duplicate or invalid Stage02L event ID/time")
        found.add(eid)
        if item.get("science_release")!="HOLD_NATIVE_SOURCE_QC_AND_ACTUAL_ERA_PROVENANCE":
            raise ValueError("Stage02L event incorrectly released")
        if not isinstance(item.get("source_START_raw"),dict) or not isinstance(item.get("source_END_raw"),dict):
            raise ValueError("Stage02L original FLUXMET two-clock values missing")
    status=r.get("historical_source_file_evidence",{}).get("STAGE09_STATUS",{}).get("status_content",{})
    bif=r.get("BIF_grouped_metadata",{}).get("selected_groups",[])
    if not isinstance(status,dict) or not isinstance(bif,list):
        raise ValueError("Stage02R source status/BIF metadata not available")
    utc=[x.get("raw_variables",{}).get("UTC_OFFSET") for x in bif
         if x.get("variable_group")=="GRP_UTC_OFFSET"]
    if utc!=["1"]:
        raise ValueError("Unexpected EUF BIF UTC offset; cannot apply source expectations")
    if status.get("reference_provider")!="Open-Meteo historical archive; explicitly models era5 and era5_land; NOT independent observations":
        raise ValueError("Stage09 reference origin changed: review manually")
    return events,status


def era_path(r):
    stage3=r.get("historical_source_file_evidence",{}).get("STAGE03_INPUTS",{})
    source_rows=stage3.get("first_rows_uninterpreted",[])
    if not isinstance(source_rows,list):
        raise ValueError("Stage03 original input source register missing")
    labels=[x.get("raw_values",{}) for x in source_rows
            if x.get("raw_values",{}).get("label")=="EUF_ERA5"]
    if len(labels)!=1:
        raise ValueError("Need exactly one Stage03 source-pinned EUF_ERA5 input")
    path=Path(labels[0].get("path",""))
    if not path.is_absolute() or path.name!="EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv":
        raise ValueError("Unexpected EUF original ERA5 source path")
    # The source must be an original-distribution file in the CH-Aws raw tree.
    if (path.parent.name!="EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2" or
            path.parent.parent.name!="raw" or
            path.parent.parent.parent.name!="forcing" or
            path.parent.parent.parent.parent.name!="CH-Aws"):
        raise ValueError("Source points outside original CH-Aws forcing/raw")
    if not path.exists():
        return path,"MISSING_ORIGINAL_DISTRIBUTED_ERA5_HH_INPUT"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Original ERA5 file is symlink/non-file")
    if path.stat().st_size>MAX_SOURCE_BYTES:
        return path,"EXCEEDS_2GB_READ_ONLY_LIMIT"
    if not path.resolve(strict=True).is_relative_to(path.parent.parent.resolve(strict=True)):
        raise ValueError("Original ERA file escapes raw source directory")
    return path,"AVAILABLE"


def targeted_scan(path,events):
    targets=collections.defaultdict(list)
    for event in events:
        t=parse(event["event_time_DATM"])
        for offset in OFFSETS:
            stamp=t+dt.timedelta(minutes=offset)
            for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
                targets[(clock,stamp)].append((event["event_id"],offset))
    matched=collections.defaultdict(list)
    rows_scanned=0
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as fh:
        rd=csv.DictReader(fh)
        columns=rd.fieldnames or []
        if not set(("TIMESTAMP_START","TIMESTAMP_END","VPD_ERA","TA_ERA")).issubset(columns):
            raise ValueError("Original EUF ERA5 source lacks required time and met fields: "+",".join(columns[:20]))
        for line,row in enumerate(rd,2):
            rows_scanned+=1
            if rows_scanned>MAX_SOURCE_ROWS:
                raise ValueError("EUF ERA5 source >1m rows; stop rather than partial scan")
            if None in row:
                raise ValueError("Malformed EUF ERA5 source CSV record")
            for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
                stamp=parse(row.get(clock))
                if stamp is None:continue
                for eid,offset in targets.get((clock,stamp),[]):
                    key=(eid,clock,offset)
                    if key in matched:
                        raise ValueError("Duplicate EUF ERA time key "+str(key))
                    matched[key]=[{
                        "source_row":line,
                        "source_timestamp":row.get(clock),
                        "VPD_ERA":row.get("VPD_ERA"),
                        "TA_ERA":row.get("TA_ERA"),
                        "PA_ERA":row.get("PA_ERA"),
                    }]
    return rows_scanned,columns,matched


def comparison(events,match):
    rows=[]
    stats=collections.defaultdict(list)
    for e in events:
        t=e["event_time_DATM"]
        for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
            source=e["source_START_raw" if clock=="TIMESTAMP_START" else "source_END_raw"]
            for offset in OFFSETS:
                record=match.get((e["event_id"],clock,offset),[])
                if len(record)>1:
                    raise ValueError("Duplicate source match")
                hit=record[0] if record else {}
                vpd=num(source.get("VPD_ERA"))
                ta=num(source.get("TA_ERA"))
                vnew=num(hit.get("VPD_ERA"))
                tnew=num(hit.get("TA_ERA"))
                d=abs(vnew-vpd) if vnew is not None and vpd is not None else None
                td=abs(tnew-ta) if tnew is not None and ta is not None else None
                if d is not None:stats[(clock,offset,"VPD")].append(d)
                if td is not None:stats[(clock,offset,"TA")].append(td)
                rows.append({
                    "event_id":e["event_id"],"DATM_label_unverified":t,
                    "source_ERA_clock":clock,
                    "source_ERA_timestamp_raw":hit.get("source_timestamp"),
                    "source_label_offset_minutes":offset,
                    "FLUXMET_clock_candidate":clock,
                    "FLUXMET_VPD_ERA_raw":source.get("VPD_ERA"),
                    "ERA_source_VPD_ERA_raw":hit.get("VPD_ERA"),
                    "absolute_VPD_difference_hPa":d,
                    "FLUXMET_TA_ERA_raw":source.get("TA_ERA"),
                    "ERA_source_TA_ERA_raw":hit.get("TA_ERA"),
                    "absolute_TA_difference_C":td,
                    "native_tower_RH_QC_verified":False,
                    "actual_UTC_clock_verified":False,
                    "independent_ERA5_provenance_verified":False,
                    "scientific_release":"HOLD",
                })
    metrics={}
    for (clock,off,var),vals in sorted(stats.items()):
        metrics.setdefault(clock,{}).setdefault(str(off),{})[var]={
            "n":len(vals),"MAE":sum(vals)/len(vals),
            "max_abs_difference":max(vals),
            "units":"hPa" if var=="VPD" else "deg C",
        }
    return rows,metrics


def self_test():
    assert parse("202007171000")==dt.datetime(2020,7,17,10,0)
    assert parse("2020-07-17 10:00:00")==dt.datetime(2020,7,17,10,0)
    assert num("-9999") is None and num("4.5")==4.5
    events=[]
    matches={}
    for k in range(20):
        eid=f"E{k+1:03d}"
        time=f"2020-07-17 {k:02d}:00:00"
        events.append({"event_id":eid,"event_time_DATM":time,
                       "source_START_raw":{"VPD_ERA":"2.1","TA_ERA":"8.0"},
                       "source_END_raw":{"VPD_ERA":"2.2","TA_ERA":"8.5"},
                       "science_release":"HOLD_NATIVE_SOURCE_QC_AND_ACTUAL_ERA_PROVENANCE"})
        for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
            matches[(eid,clock,0)]=[{"source_timestamp":"202007171000",
                "VPD_ERA":"2.1" if clock=="TIMESTAMP_START" else "2.2",
                "TA_ERA":"8.0" if clock=="TIMESTAMP_START" else "8.5"}]
    rows,metrics=comparison(events,matches)
    assert len(rows)==MAX_RECORDS
    assert metrics["TIMESTAMP_START"]["0"]["VPD"]["n"]==20
    assert metrics["TIMESTAMP_START"]["0"]["VPD"]["MAE"]==0
    assert metrics["TIMESTAMP_END"]["0"]["TA"]["MAE"]==0
    print("STAGE02S SELF-TEST PASS: 20x2x9 original ERA clock comparisons, bounded source scan contract, source QC HOLD; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02r",type=Path)
    ap.add_argument("--stage02l",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        self_test();return
    if any(x is None or not x.is_file() for x in (args.stage02r,args.stage02l)):
        ap.error("Saved Stage02R and Stage02L JSONs required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY")
    r=json.loads(args.stage02r.read_text(encoding="utf-8"))
    l=json.loads(args.stage02l.read_text(encoding="utf-8"))
    events,status=validate(r,l)
    source_path,state=era_path(r)
    print("DISTRIBUTED_ERA5_INPUT",state,str(source_path))
    print("STAGE09_UTC_OFFSET",status.get("reference_time_UTC_offset_hours"),
          "TIME_RULE",status.get("reference_time_rule"))
    data_rows=[]
    metrics={}
    rows_scanned=0
    columns=[]
    if state=="AVAILABLE":
        rows_scanned,columns,found=targeted_scan(source_path,events)
        data_rows,metrics=comparison(events,found)
        for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
            for off in OFFSETS:
                scores=metrics.get(clock,{}).get(str(off),{})
                print("CLOCK_CANDIDATE",clock,"OFFSET_MIN",off,
                      "VPD_N",scores.get("VPD",{}).get("n",0),
                      "VPD_MAE_HPA",scores.get("VPD",{}).get("MAE"),
                      "TA_N",scores.get("TA",{}).get("n",0),
                      "TA_MAE_C",scores.get("TA",{}).get("MAE"))
    else:
        # A missing source file is a provenance blocker, not a reason to
        # synthesize/pick another input or download an undocumented product.
        print("SOURCE_HOLD",state)
    report={
        "stage":"STAGE02S_CH_AWS_ORIGINAL_EUF_ERA_CLOCK_EVIDENCE_READONLY",
        "read_only":True,"scientific_release":False,
        "input_stage02r":str(args.stage02r),"input_stage02l":str(args.stage02l),
        "ERA5_original_source":str(source_path),
        "source_status":state,"source_rows_scanned":rows_scanned,
        "source_column_names":columns,
        "stage09_time_reference_note":status.get("reference_time_rule"),
        "BIF_UTC_OFFSET_label":"1",
        "hypothesis_only_VPD_and_TA_comparison":metrics,
        "matches":data_rows,"native_tower_RH_QC_verified":False,
        "DATM_UTC_local_conversion_approved":False,
        "independent_ERA5_station_grid_accuracy_verified":False,
        "source_modified":False,"slurm_submitted":False,
        "limitations":"Both EUF FLUXMET and EUF ERA5 are processed/related distributed products; numeric agreement is not independent tower truth. Clock offsets are literal label hypotheses only.",
    }
    jp=args.out_dir/"stage02s_CH_Aws_original_EUF_ERA_time_comparison.json"
    cp=args.out_dir/"stage02s_CH_Aws_ERA5_FLUXMET_two_clock_offsets.csv"
    with jp.open("x",encoding="utf-8") as fh:
        json.dump(report,fh,indent=2,ensure_ascii=False);fh.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=CSV_FIELDS)
        writer.writeheader();writer.writerows(data_rows)
    print("ROWS_SCANNED",rows_scanned,"COMPARISONS",len(data_rows))
    print("JSON",jp)
    print("CSV",cp)
    print("SCIENCE_HOLD: NATIVE SENSOR RH/QC, UTC CLOCK AND INDEPENDENT ERA REPRESENTATIVENESS UNVERIFIED")


if __name__=="__main__":
    main()
