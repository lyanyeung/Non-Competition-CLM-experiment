#!/usr/bin/env python3
"""ICOS Batch04 Stage02R: CH-Aws historical timezone/source-provenance audit.

READ ONLY. Use the actual saved Stage02Q JSON to inspect small source-pinned
FLUXNET_MultiSite_11 Stage03/06/09 files, original EUF BIF/BIFVARINFO groups,
and the time ranges of Stage21/25 legacy ledger files. Extract raw metadata,
not a scientific decision. No timezone conversion, no full FLUXMET read,
no network, no ZIP extraction, no forcing/NC/CIME/Slurm/Git modifications.
Only --out-dir receives two new report files in an EMPTY directory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import json
import re
from pathlib import Path

STAGE_Q="STAGE02Q_CH_AWS_TIME_AND_NATIVE_SOURCE_PROVENANCE_READONLY"
MAX_SOURCE_BYTES=2_000_000
MAX_ROWS=100_000
MAX_REPORTED_MATCHES=200
HISTORICAL={
    "STAGE03_INPUTS": "stage03_merge_qc/CH-Aws_inputs.csv",
    "STAGE03_STATUS": "stage03_merge_qc/CH-Aws_status.json",
    "STAGE03_HUMIDITY_REVIEW": "stage03_merge_qc/CH-Aws_humidity_review.csv",
    "STAGE06_RH_EPISODES": "stage06_science_diagnostics/CH-Aws_RH_episodes.csv",
    "STAGE09_TIMEZONE_ALIGNMENT": "stage09_CH_Aws/01_timezone_alignment.csv",
    "STAGE09_559_REFERENCE": "stage09_CH_Aws/02_CH_Aws_559_event_reference_comparison.csv",
    "STAGE09_STATUS": "stage09_CH_Aws/04_stage09_status.json",
}
KEY_COLUMNS=re.compile(r"(TIME|DATE|TIMESTAMP|RH|VPD|TA|QC|ERA|SOURCE|UTC|OFFSET|SENSOR|INSTRUMENT|FLAG|HOLD|STATUS)",re.I)
TARGET_NAMES={"RH","VPD_F","VPD_F_QC","VPD_F_MDS","VPD_ERA","TA_F","TA_F_QC",
              "TA_ERA","PA_F","PA_F_QC"}
CSV_COLUMNS=("source_label","source_path","source_record_number",
             "source_column","source_raw_timestamp","DATM_event_id",
             "DATM_event_time","literal_source_minus_DATM_minutes",
             "raw_original_record_json","source_time_verified",
             "native_tower_QC_verified","scientific_release")


def parse_time(x):
    s=str(x).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M",
                "%Y%m%d%H%M","%Y%m%d%H%M%S"):
        try:return dt.datetime.strptime(s,fmt)
        except ValueError:pass
    return None


def require_stage(data):
    if not isinstance(data,dict) or data.get("stage")!=STAGE_Q or \
       data.get("read_only") is not True or data.get("science_release") is not False:
        raise ValueError("Saved Stage02Q scientific HOLD report required")
    if data.get("native_unfilled_tower_RH_QC_verified") is not False or \
       data.get("DATM_FLUXMET_UTC_basis_verified") is not False:
        raise ValueError("Prior Stage02Q erroneously approved source/time")
    ext=data.get("external_filename_candidates",{})
    if ext.get("search_truncated") is not False:
        raise ValueError("Stage02Q external candidate scan truncated")
    entries=ext.get("candidate_paths",[])
    if not isinstance(entries,list):
        raise ValueError("No Stage02Q external filename evidence list")
    events=data.get("source_stage02o")
    if not events or not Path(events).is_file():
        raise ValueError("Stage02Q source Stage02O report missing")
    # Stage02Q provides its actual source high-difference anchor times.
    o=json.loads(Path(events).read_text(encoding="utf-8"))
    if o.get("stage")!="STAGE02O_CH_AWS_REPAIR_EVENT_SCIENCE_TRIAGE_READONLY" or \
       o.get("read_only") is not True or o.get("science_release") is not False:
        raise ValueError("Original Stage02O source not read-only/HOLD")
    anchors=o.get("events_ranked",[])
    if len(anchors)!=20:
        raise ValueError("Expected 20 original Stage02O events")
    ids=set()
    output=[]
    for x in anchors:
        eid=x.get("event_id")
        when=parse_time(x.get("DATM_time"))
        if not eid or eid in ids or when is None or x.get("scientific_release")!="HOLD":
            raise ValueError("Invalid Stage02O event identity/time/approval")
        ids.add(eid)
        output.append({"event_id":eid,"DATM_time":str(when),"time":when})
    return entries,output


def pin_files(data,entries):
    root=Path(data.get("site_root","")).resolve(strict=True)
    if root.name!="CH-Aws" or root.parent.name!="MY_EC_SITE":
        raise ValueError("Original Stage02Q CH-Aws root invalid")
    home=Path.home().resolve(strict=True)
    files={}
    candidates=[str(x.get("path","")) for x in entries]
    for label,rel in HISTORICAL.items():
        suffix="/FLUXNET_MultiSite_11/"+rel
        found=[Path(x) for x in candidates if x.endswith(suffix)]
        if len(found)!=1:
            raise ValueError("Stage02Q did not uniquely pin historical source "+label)
        path=found[0]
        if not path.is_absolute() or path.is_symlink() or not path.is_file() or \
           path.stat().st_size>MAX_SOURCE_BYTES:
            raise ValueError("Unsafe/oversize external historical source "+str(path))
        base=next((p for p in path.parents if p.name=="FLUXNET_MultiSite_11"),None)
        if base is None or not base.parent.samefile(home) or \
           not path.resolve(strict=True).is_relative_to(base.resolve(strict=True)):
            raise ValueError("Historical source unexpectedly outside operator HOME "+str(path))
        files[label]=path
    for label,key in (("BIF","BIF"),("BIFVARINFO_HH","BIFVARINFO_HH")):
        metadata=data.get("original_distributed_metadata",{}).get(key,{})
        path=Path(metadata.get("path",""))
        if not path.is_file() or path.is_symlink() or \
           not path.resolve(strict=True).is_relative_to(root) or \
           path.stat().st_size>MAX_SOURCE_BYTES:
            raise ValueError("Missing/unsafe original EUF metadata "+label)
        files[label]=path
    for name in ("STAGE21","STAGE25"):
        path=Path(data.get("stage21_25_original_local_standard_time_ledgers",{})
                  .get(name,{}).get("path",""))
        if not path.is_file() or path.is_symlink() or \
           not path.resolve(strict=True).is_relative_to(root) or \
           path.stat().st_size>MAX_SOURCE_BYTES:
            raise ValueError("Missing/unsafe Stage21/25 time ledger "+name)
        files[name]=path
    return files


def read_rows(path):
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
        reader=csv.DictReader(f)
        cols=reader.fieldnames
        if not cols:raise ValueError("Missing CSV headers "+str(path))
        result=[]
        for index,row in enumerate(reader,2):
            if len(result)>=MAX_ROWS:
                raise ValueError("Unexpected >100k source rows "+str(path))
            if None in row:
                raise ValueError("Malformed source CSV "+str(path))
            result.append((index,{str(k):str(v) if v is not None else ""
                                  for k,v in row.items()}))
    return list(cols),result


def aggregate_grouped_metadata(path):
    headers,rows=read_rows(path)
    groups=collections.defaultdict(list)
    for lineno,r in rows:
        key=(r.get("GROUP_ID",""),r.get("VARIABLE_GROUP",""))
        groups[key].append({"line":lineno,"variable":r.get("VARIABLE",""),
                            "raw_value":r.get("DATAVALUE","")})
    output=[]
    for (gid,group),raw in groups.items():
        kv={entry["variable"]:entry["raw_value"] for entry in raw}
        if group=="GRP_VAR_INFO":
            varname=kv.get("VAR_INFO_VARNAME","").strip().upper()
            if varname not in TARGET_NAMES and not varname.startswith(("RH_","VPD_")):
                continue
            kind="TARGET_VARIABLE_METADATA"
        elif group in ("GRP_UTC_OFFSET","GRP_ONEFLUX","GRP_ERA_DOWN"):
            kind="TIME_NETWORK_OR_ERA_METADATA"
        else:continue
        output.append({"group_id":gid,"variable_group":group,"kind":kind,
                       "target_varname":kv.get("VAR_INFO_VARNAME"),
                       "raw_variables":kv,"source_lines":raw})
    return {"source_path":str(path),"rows":len(rows),"headers":headers,
            "groups_examined":len(groups),
            "selected_group_count":len(output),"selected_groups":output,
            "native_QC_verified":False,"UTC_offset_conversion_verified":False}


def file_evidence(label,path,anchors):
    if path.suffix.lower()==".json":
        obj=json.loads(path.read_text(encoding="utf-8"))
        return {
            "source":str(path),"source_type":"JSON_STATUS_OR_PROVENANCE",
            "status_content":obj,"scientific_release":False,
        },[]
    headers,rows=read_rows(path)
    keynames=[h for h in headers if KEY_COLUMNS.search(h)]
    times=[h for h in headers if re.search("TIME|TIMESTAMP|DATE",h,re.I)]
    exact=[]
    per_time=collections.Counter()
    matching=[]
    for rowno,row in rows:
        for col in times:
            t=parse_time(row.get(col))
            if t is None:continue
            per_time[col]+=1
            for e in anchors:
                offset=int((t-e["time"]).total_seconds()/60)
                if offset not in (-60,-30,0,30,60):continue
                if len(matching)>=MAX_REPORTED_MATCHES:
                    raise ValueError("Exceeded max 200 timeline hypothesis matches")
                matching.append({
                    "source_label":label,"source_path":str(path),
                    "source_record_number":rowno,
                    "source_column":col,"source_raw_timestamp":row[col],
                    "DATM_event_id":e["event_id"],"DATM_event_time":e["DATM_time"],
                    "literal_source_minus_DATM_minutes":offset,
                    "raw_original_record_json":json.dumps(row,ensure_ascii=False),
                    "source_time_verified":False,"native_tower_QC_verified":False,
                    "scientific_release":"HOLD"})
            if label in ("STAGE21","STAGE25"):
                exact.append(t)
    info={
        "path":str(path),"rows":len(rows),"headers":headers,
        "interesting_columns":keynames[:100],"time_columns":times,
        "valid_parsed_timestamp_count_by_column":dict(per_time),
        "time_range_min":str(min(exact)) if exact else None,
        "time_range_max":str(max(exact)) if exact else None,
        "time_candidate_matches":len(matching),
        "first_rows_uninterpreted":[dict(row=i,raw_values=r)
                                    for i,r in rows[:5]],
        "original_observation_QC_verified":False,
        "source_timezone_verified":False,
    }
    return info,matching


def self_test():
    fake={"stage":STAGE_Q,"read_only":True,"science_release":False,
          "native_unfilled_tower_RH_QC_verified":False,
          "DATM_FLUXMET_UTC_basis_verified":False,
          "external_filename_candidates":{"search_truncated":False,"candidate_paths":[]}}
    assert parse_time("2007-07-22 07:30:00")==dt.datetime(2007,7,22,7,30)
    assert parse_time("200707220730")==dt.datetime(2007,7,22,7,30)
    assert parse_time("2007-07-22T07:30:00") is None  # No guessing unsupported clocks
    group_rows=[
        (2,{"GROUP_ID":"18","VARIABLE_GROUP":"GRP_VAR_INFO",
            "VARIABLE":"VAR_INFO_VARNAME","DATAVALUE":"RH"}),
        (3,{"GROUP_ID":"18","VARIABLE_GROUP":"GRP_VAR_INFO",
            "VARIABLE":"VAR_INFO_MODEL","DATAVALUE":"RH-Other"}),
    ]
    d=collections.defaultdict(list)
    for i,r in group_rows:d[(r["GROUP_ID"],r["VARIABLE_GROUP"])].append(r)
    assert len(d)==1 and d[("18","GRP_VAR_INFO")][0]["DATAVALUE"]=="RH"
    assert "STAGE09_TIMEZONE_ALIGNMENT" in HISTORICAL
    print("STAGE02R SELF-TEST PASS: evidence-pinned sources, grouped RH metadata and no time conversion; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02q",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:self_test();return
    if args.stage02q is None or not args.stage02q.is_file():
        ap.error("Saved Stage02Q JSON required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("Output directory must already exist and be EMPTY")
    q=json.loads(args.stage02q.read_text(encoding="utf-8"))
    entries,anchors=require_stage(q)
    pins=pin_files(q,entries)
    bif=aggregate_grouped_metadata(pins["BIF"])
    varinfo=aggregate_grouped_metadata(pins["BIFVARINFO_HH"])
    comparisons={}
    matches=[]
    for label in list(HISTORICAL)+["STAGE21","STAGE25"]:
        detail,rows=file_evidence(label,pins[label],anchors)
        comparisons[label]=detail
        matches.extend(rows)
        print("SOURCE",label,"PATH",pins[label],
              "ROWS",detail.get("rows","JSON"),
              "TIME_COLS",",".join(detail.get("time_columns",[])) or "NONE",
              "MATCHES",detail.get("time_candidate_matches",0))
        if label in ("STAGE21","STAGE25"):
            print(" LEDGER_TIME_RANGE",label,detail["time_range_min"],detail["time_range_max"])
        if label=="STAGE09_TIMEZONE_ALIGNMENT":
            for r in detail.get("first_rows_uninterpreted",[])[:12]:
                print(" TIMEZONE_SOURCE_ROW",json.dumps(r,ensure_ascii=False)[:1100])
        if label.endswith("STATUS"):
            print(" STATUS_METADATA",label,json.dumps(detail["status_content"],ensure_ascii=False)[:1400])
        if label=="STAGE03_INPUTS":
            for r in detail.get("first_rows_uninterpreted",[])[:5]:
                print(" STAGE03_INPUT_ROW",json.dumps(r,ensure_ascii=False)[:1100])
    for name,info in (("BIF",bif),("BIFVARINFO_HH",varinfo)):
        print("SOURCE_METADATA",name,"ROWS",info["rows"],
              "GROUPS",info["groups_examined"],"SELECTED_GROUPS",info["selected_group_count"])
        for group in info["selected_groups"][:20]:
            print(" META_GROUP",name,group["variable_group"],
                  group["target_varname"] or "",group["group_id"],
                  json.dumps(group["raw_variables"],ensure_ascii=False)[:900])
    for row in matches[:25]:
        print("EVENT_CONTEXT",row["source_label"],row["DATM_event_id"],
              row["source_column"],row["source_raw_timestamp"],
              "RAW_OFFSET_MIN",row["literal_source_minus_DATM_minutes"])
    report={
        "stage":"STAGE02R_CH_AWS_LEGACY_SOURCE_GROUP_AND_CLOCK_AUDIT",
        "read_only":True,"science_release":False,
        "source_stage02q":str(args.stage02q),
        "data_unchanged":True,"slurm_submitted":False,
        "BIF_grouped_metadata":bif,"BIFVARINFO_HH_grouped_metadata":varinfo,
        "historical_source_file_evidence":comparisons,
        "event_context_matches_UNVERIFIED_CLOCK":matches,
        "source_native_tower_RH_QC_verified":False,
        "ERA5_independent_provenance_verified":False,
        "clock_conversion_approved":False,
        "scientific_conclusion":"HOLD. Historical source metadata and clock hypotheses are evidence; do not select RH34/38/42 based on ERA proximity.",
    }
    j=args.out_dir/"stage02r_CH_Aws_original_metadata_legacy_clock_review.json"
    c=args.out_dir/"stage02r_CH_Aws_legacy_time_context_candidates.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=CSV_COLUMNS);w.writeheader();w.writerows(matches)
    print("EVENT_CONTEXT_CANDIDATE_MATCHES",len(matches))
    print("JSON",j)
    print("CSV",c)
    print("SCIENCE_HOLD: NATIVE SENSOR RH/QC, ACTUAL LOCAL/UTC CLOCK AND ERA REPRESENTATIVENESS UNVERIFIED")


if __name__=="__main__":
    main()
