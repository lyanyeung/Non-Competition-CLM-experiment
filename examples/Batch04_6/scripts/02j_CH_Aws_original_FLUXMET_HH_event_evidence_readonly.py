#!/usr/bin/env python3
"""ICOS Batch04 Stage02J: read large CH-Aws FLUXMET_HH source at event times.

READ ONLY. Stage02I omitted the >90MB EUF FLUXMET_HH CSV; stream that exact
existing product without changing its contents. Match both TIMESTAMP_START
and TIMESTAMP_END independently within +/-60 minutes of the top ranked
DATM QBOT-change timestamps. Report raw product TA/RH/VPD/pressure/QC columns
actually present, alongside the unverified Stage02I processed candidate rows.

FLUXMET_HH is a processed FLUXNET/ICOS product; do NOT claim its _F fields
are original unfilled tower observations or QC0. No UTC/local, start/end,
instrument, or ERA5 provenance is inferred. Only --out-dir writes JSON/CSV
into a NEW existing EMPTY directory. No source/CIME/Slurm changes.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import io
import json
import re
from pathlib import Path

STAGE_I="STAGE02I_CH_AWS_SOURCE_CSV_EVENT_SCHEMA_READONLY"
SOURCE_NAME="EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv"
EXPECTED_PRODUCT_PART="EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2"
OFFSETS=(-60,-30,0,30,60)
MAX_SCAN_ROWS=750000
MAX_RAW_MATCHES=1800
MAX_EVENT_COUNT=20
CSV_FIELDS=(
    "event_id","DATM_event_time","source_product","source_row_number",
    "source_time_column","original_source_timestamp","offset_minutes",
    "field_values_json","time_basis_verified","raw_tower_observed_status",
    "source_QC_verified","ERA5_evidence_verified",
)


def parse_time(value):
    if value is None:
        return None
    s=str(value).strip().strip('"').strip("'")
    if re.fullmatch(r"\d{12}",s):
        try:return dt.datetime.strptime(s,"%Y%m%d%H%M")
        except ValueError:return None
    if re.fullmatch(r"\d{14}",s):
        try:return dt.datetime.strptime(s,"%Y%m%d%H%M%S")
        except ValueError:return None
    try:
        d=dt.datetime.fromisoformat(s)
        if d.tzinfo is None and 1990<=d.year<=2035:
            return d
    except ValueError:
        return None
    return None


def verify_stage02i(data):
    if not isinstance(data,dict) or data.get("stage")!=STAGE_I:
        raise ValueError("Require the actual Stage02I JSON result")
    if data.get("read_only") is not True or data.get("scientific_release") is not False:
        raise ValueError("Stage02I was not held as read-only")
    events=data.get("selected_ranked_events")
    if not isinstance(events,list) or not events:
        raise ValueError("Stage02I selected event IDs missing")
    original_entries=[
        x for x in data.get("candidate_csv_inspections",[])
        if Path(str(x.get("path",""))).name==SOURCE_NAME
    ]
    if len(original_entries)!=1:
        raise ValueError("Exactly one source-pinned original EUF FLUXMET HH CSV required")
    entry=original_entries[0]
    if entry.get("status")!="SKIP_OVER_MAX_MB":
        raise ValueError("Stage02J expected the previously size-skipped FLUXMET_HH file")
    return events,entry


def verify_source_path(raw_entry,forcing_root):
    root=forcing_root.resolve(strict=True)
    if root.name!="forcing" or root.parent.name!="CH-Aws":
        raise ValueError("Source directory must be CH-Aws/forcing")
    p=Path(raw_entry["path"])
    if not p.is_absolute() or p.name!=SOURCE_NAME or EXPECTED_PRODUCT_PART not in p.parts:
        raise ValueError("Original product path is not the pinned EUF FLUXMET_HH")
    resolved=p.resolve(strict=True)
    if not resolved.is_relative_to(root) or p.is_symlink() or not p.is_file():
        raise ValueError("Path escapes original forcing root or is not a regular CSV")
    if p.stat().st_size<90_000_000:
        # Historical Stage02I skipped due to 90MB, but file size can differ;
        # report rather than reject a source that has since changed.
        pass
    if p.stat().st_size>1_500_000_000:
        raise ValueError("Source product unexpectedly over 1.5GB; manual review required")
    return p


def make_targets(events,limit):
    selected=[]
    lookup=collections.defaultdict(list)
    seen=set()
    for event in events:
        eid=event.get("event_id")
        when=parse_time(event.get("event_time_DATM"))
        if not isinstance(eid,str) or when is None:
            raise ValueError("Unparseable Stage02I event identity/time")
        if eid in seen:
            raise ValueError("Duplicate event identity")
        seen.add(eid)
        selected.append({
            "event_id":eid,"time":str(when),
            "qbot_abs_delta_gkg":event.get("max_abs_delta_QBOT_gkg"),
            "vapor_abs_delta_hPa":event.get("max_abs_delta_vapor_hPa"),
            "candidate_cases":event.get("candidate_cases"),
            "actual_native_tower_verified":False
        })
        for offset in OFFSETS:
            lookup[when+dt.timedelta(minutes=offset)].append((eid,offset))
        if len(selected)>=limit:break
    if not selected:
        raise ValueError("No valid Stage02I event")
    return selected,lookup


def is_relevant_field(k):
    s=str(k).upper()
    if s in {"TIMESTAMP_START","TIMESTAMP_END"}:
        return True
    return bool(re.match(r"^(TA|RH|VPD|PA|PSRF|QBOT|T_SONIC|DEWPOINT|P|SW_IN|LW_IN)(?:_|$)",s)
                or "_QC" in s or s.startswith(("ERA_","QC_")))


def capture_row_values(row,fieldnames):
    # Retain the raw strings to avoid interpreting missing-value codes
    # (e.g. -9999) or column-specific QC meanings without metadata.
    return {k:str(row.get(k,""))[:300] for k in fieldnames
            if is_relevant_field(k) and row.get(k) not in (None,"")}


def stream_original_rows(reader,targets,limit=MAX_RAW_MATCHES):
    headers=reader.fieldnames or []
    timekeys=[x for x in ("TIMESTAMP_START","TIMESTAMP_END") if x in headers]
    if not timekeys:
        raise ValueError("Original HH CSV lacks separately identifiable TIMESTAMP_START/END")
    results=[]
    rows=0
    truncated=False
    for row in reader:
        rows+=1
        if rows>MAX_SCAN_ROWS:
            truncated=True
            break
        for source_time_key in timekeys:
            original_ts=row.get(source_time_key)
            t=parse_time(original_ts)
            if t is None:
                continue
            for eid,offset in targets.get(t,()):
                if len(results)>=limit:
                    truncated=True
                    continue
                results.append({
                    "event_id":eid,
                    "source_row_number":rows+1,
                    "source_time_column":source_time_key,
                    "original_source_timestamp":str(original_ts),
                    "offset_minutes":offset,
                    "field_values":capture_row_values(row,headers),
                    "time_basis_verified":False,
                    "raw_tower_observed_status":"PROCESSED_FLUXMET_PRODUCT_UNVERIFIED",
                    "source_QC_verified":False,
                    "ERA5_evidence_verified":False,
                })
    return {
        "rows_scanned":rows,"scan_complete":not truncated,
        "headers":list(headers), "time_columns":timekeys,
        "relevant_source_fields":[h for h in headers if is_relevant_field(h)],
        "original_product_records":results,
        "original_product_matches":len(results),
        "matching_limit_hit":truncated
    }


def candidate_rows(data,selected):
    wanted={x["event_id"] for x in selected}
    result=collections.defaultdict(list)
    for row in data.get("candidate_matched_rows",[]):
        eid=row.get("event_id")
        if eid in wanted:
            result[eid].append({
                "source_csv":row.get("source_csv"),
                "row_number":row.get("row_number"),
                "matched_time_column":row.get("matched_time_column"),
                "raw_time_value":row.get("raw_time_value"),
                "matched_offset_minutes":row.get("matched_offset_minutes"),
                "candidate_record_fields":row.get("candidate_record_fields",{}),
                "time_basis_status":row.get("time_basis_status","UNVERIFIED"),
                "tower_QC_status":row.get("tower_QC_status","NOT_VERIFIED"),
                "ERA5_status":row.get("ERA5_status","NOT_VERIFIED")
            })
    return result


def selftest():
    fake={
        "stage":STAGE_I,"read_only":True,"scientific_release":False,
        "candidate_csv_inspections":[{"path":
            "/x/CH-Aws/forcing/raw/"+EXPECTED_PRODUCT_PART+"/"+SOURCE_NAME,
            "status":"SKIP_OVER_MAX_MB"}],
        "selected_ranked_events":[{"event_id":"E001",
            "event_time_DATM":"2007-07-22 07:30:00"}]
    }
    events,raw=verify_stage02i(fake)
    assert raw["status"]=="SKIP_OVER_MAX_MB"
    selected,lookup=make_targets(events,1)
    text=("TIMESTAMP_START,TIMESTAMP_END,TA_F,TA_F_QC,VPD_F,VPD_F_QC\n"
          "200707220700,200707220730,12,0,7,0\n"
          "200707220730,200707220800,13,1,8,1\n"
          "200707220800,200707220830,14,0,9,0\n")
    result=stream_original_rows(csv.DictReader(io.StringIO(text)),lookup)
    assert result["rows_scanned"]==3
    assert len(result["original_product_records"])==6
    assert {r["source_time_column"] for r in result["original_product_records"]}=={
        "TIMESTAMP_START","TIMESTAMP_END"}
    assert any(r["offset_minutes"]==0 for r in result["original_product_records"])
    assert all(not r["source_QC_verified"] for r in result["original_product_records"])
    assert parse_time("200707220730")==dt.datetime(2007,7,22,7,30)
    print("STAGE02J SELF-TEST PASS: decoded Stage02I, HH START/END source matching, original QC unverified; no writes")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02i",type=Path)
    ap.add_argument("--forcing-root",type=Path,default=Path(
        "/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing"))
    ap.add_argument("--event-limit",type=int,default=20)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest();return
    if not args.stage02i or not args.stage02i.is_file():
        ap.error("Existing Stage02I source-matches JSON required")
    if not 1<=args.event_limit<=MAX_EVENT_COUNT:
        ap.error("event-limit must be from 1 to 20")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("Output directory must exist and be EMPTY")
    data=json.loads(args.stage02i.read_text(encoding="utf-8"))
    all_events,original_entry=verify_stage02i(data)
    p=verify_source_path(original_entry,args.forcing_root)
    events,lookup=make_targets(all_events,args.event_limit)
    print("ORIGINAL_SOURCE_PRODUCT",p.name,"SIZE_BYTES",p.stat().st_size)
    # Only a single streaming pass; no 90MB skip and no memory-sized data frame.
    with p.open("r",encoding="utf-8-sig",errors="replace",newline="") as handle:
        reader=csv.DictReader(handle)
        raw=stream_original_rows(reader,lookup)
    raw["source_path"]=str(p)
    candidates=candidate_rows(data,events)
    matched_by_id=collections.defaultdict(list)
    for row in raw["original_product_records"]:
        matched_by_id[row["event_id"]].append(row)
    report=[]
    for event in events:
        eid=event["event_id"]
        source_rows=matched_by_id.get(eid,[])
        processed=candidates.get(eid,[])
        item={
            **event,
            "original_FLUXMET_source_rows":source_rows,
            "candidate_processing_or_ledger_rows":processed,
            "original_source_row_matches":len(source_rows),
            "other_source_candidate_row_matches":len(processed),
            "time_convention":"UNVERIFIED: keep TIMESTAMP_START/END separate; no UTC conversion",
            "QC_ERA_validation":"HOLD",
        }
        report.append(item)
        print("EVENT",eid,event["time"],
              "ORIGINAL_SOURCE_MATCHES",len(source_rows),
              "PROCESSED_AND_LEDGER_MATCHES",len(processed),
              "START_MATCHES",sum(r["source_time_column"]=="TIMESTAMP_START" for r in source_rows),
              "END_MATCHES",sum(r["source_time_column"]=="TIMESTAMP_END" for r in source_rows))
        if source_rows:
            keyset=["TA_F","TA_F_QC","RH_F","RH_F_QC","VPD_F","VPD_F_QC","PA_F"]
            sample=next((r for r in source_rows if r["offset_minutes"]==0),source_rows[0])
            print(" SOURCE_EXAMPLE",sample["source_time_column"],
                  json.dumps({k:sample["field_values"][k] for k in keyset if k in sample["field_values"]},
                             ensure_ascii=False))
    print("RAW_FLUXMET_ROWS_SCANNED",raw["rows_scanned"],"FULL_SCAN",raw["scan_complete"])
    print("RAW_FLUXMET_COLUMN_COUNT",len(raw["headers"]),"TIME_COLUMNS",",".join(raw["time_columns"]))
    print("RAW_SOURCE_RELEVANT_FIELDS",",".join(raw["relevant_source_fields"][:90]))
    print("TOTAL_RAW_SOURCE_MATCHES",raw["original_product_matches"])
    report_json={
        "stage":"STAGE02J_CH_AWS_ORIGINAL_FLUXMET_HH_EVENT_REVIEW",
        "read_only":True,"science_release":False,
        "original_forcing_modified":False,"Slurm_submitted":False,
        "stage02i_input":str(args.stage02i),
        "raw_HH_product":raw,"event_comparisons":report,
        "limitations":(
            "FLUXMET_HH is a processed product. Matching HH START and END "
            "as alternative timestamps does not verify UTC/local offsets, "
            "tower-native raw QC0, or ERA5 substitution. Nothing approved."),
    }
    jout=args.out_dir/"stage02j_original_FLUXMET_HH_event_review.json"
    cout=args.out_dir/"stage02j_original_FLUXMET_HH_source_matches.csv"
    with jout.open("x",encoding="utf-8") as handle:
        json.dump(report_json,handle,indent=2)
        handle.write("\n")
    with cout.open("x",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=CSV_FIELDS)
        writer.writeheader()
        for event in report:
            for row in event["original_FLUXMET_source_rows"]:
                writer.writerow({
                    "event_id":event["event_id"],"DATM_event_time":event["time"],
                    "source_product":str(p),
                    "source_row_number":row["source_row_number"],
                    "source_time_column":row["source_time_column"],
                    "original_source_timestamp":row["original_source_timestamp"],
                    "offset_minutes":row["offset_minutes"],
                    "field_values_json":json.dumps(row["field_values"],ensure_ascii=False),
                    "time_basis_verified":False,
                    "raw_tower_observed_status":row["raw_tower_observed_status"],
                    "source_QC_verified":False,"ERA5_evidence_verified":False
                })
    print("NEW_JSON",jout)
    print("NEW_CSV",cout)
    print("NO SCIENCE RELEASE; RAW TOWER/ERA TIME AND QC UNVERIFIED; NO SOURCE MODIFICATIONS")


if __name__=="__main__":
    main()
