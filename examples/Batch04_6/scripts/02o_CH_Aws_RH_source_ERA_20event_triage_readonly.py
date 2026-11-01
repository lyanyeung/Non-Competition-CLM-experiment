#!/usr/bin/env python3
"""Batch04 Stage02O — CH-Aws 20-event humidity source conflicts, READ ONLY.

Combines *already verified* Stage02N original CSV ledger rows (sha256 pinned,
real event times) with the saved Stage02M source-vs-forcing diagnostics.
Reports missing native RH, MDS-filled VPD, ERA5/ERA5-Land humidity contrast,
adjacent RH jump where supplied, and source-seam evidence. A ranked triage
flag is NOT approval to choose ERA or amend any forcing; individual original
instrument QC, source time, altimetry and ERA representativeness are missing.

Only creates JSON and CSV in an existing EMPTY --out-dir. Reads only the
two input JSONs; no source NC, model case, Git worktree or Slurm writes.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
from pathlib import Path

STAGE_N = "STAGE02N_CH_AWS_ORIGINAL_REVISION_LEDGER_QC_PROVENANCE"
STAGE_M = "STAGE02M_CH_AWS_SEVEN_SOURCE_VPD_ERA_LEDGER_TRIAGE"
EXPECTED_STAGES = {"stage34": 7, "stage38": 5, "stage42": 8}
COLUMNS = (
    "event_id","DATM_time","revision_stage","source_ledger_sha_verified",
    "original_ledger_science_status","FLUXMET_VPD_F_hPa_raw",
    "FLUXMET_VPD_F_QC_raw","FLUXMET_VPD_ERA_hPa_raw",
    "RH_from_processed_input_pct","ERA5_RH_pct_ledger",
    "ERA5_Land_RH_pct_ledger","ERA5_minus_input_RH_pp",
    "ERA5Land_minus_input_RH_pp","ERA5Land_minus_ERA5_RH_pp",
    "RH_previous_pct","RH_next_pct","neighbor_max_abs_jump_pp",
    "source_seam_in_ledger","flags","priority",
    "native_tower_RH_QC_verified","ERA_representativeness_verified",
    "timestamp_convention_verified","scientific_release"
)


def value(row, name):
    raw=row.get(name)
    if raw is None or str(raw).strip().lower() in ("", "none", "nan", "-9999", "-9999.0"):
        return None
    try:
        f=float(str(raw).strip())
        if not math.isfinite(f) or f<=-9990:
            return None
        return f
    except (TypeError, ValueError):
        return None


def check_inputs(n,m):
    if not isinstance(n,dict) or n.get("stage")!=STAGE_N or n.get("read_only") is not True or n.get("science_release") is not False:
        raise ValueError("Not an unreleased/read-only Stage02N evidence file")
    if not isinstance(m,dict) or m.get("stage")!=STAGE_M or m.get("read_only") is not True or m.get("science_release") is not False:
        raise ValueError("Not an unreleased/read-only Stage02M source comparison")
    if n.get("reported_science_holds") != []:
        raise ValueError("Previous ledger row/time holds remain unresolved")
    if n.get("ledger_sha_unverified_stages") != []:
        raise ValueError("One or more source ledger SHA hashes were not verified")
    records=n.get("matched_exact_event_records")
    events=m.get("event_science_and_revision_ledgers")
    if not isinstance(records,list) or len(records)!=20 or not isinstance(events,list) or len(events)!=20:
        raise ValueError("Expected exactly 20 Stage02N original ledger rows and 20 Stage02M event entries")
    meta=n.get("original_ledger_provenance")
    if not isinstance(meta,list) or len(meta)!=3:
        raise ValueError("Expected three original revision ledger provenance objects")
    for item in meta:
        if item.get("sha256_verified") is not True:
            raise ValueError("Original ledger SHA provenance not verified")
    by_id={}
    for item in events:
        eid=item.get("event_id")
        if not isinstance(eid,str) or eid in by_id or item.get("decision")!="HOLD_NATIVE_TOWER_RH_ERA_AND_REPAIR_JUSTIFICATION":
            raise ValueError("Invalid or duplicate Stage02M event / scientific status")
        by_id[eid]=item
    counts=collections.Counter()
    for row in records:
        eid=row.get("event_id")
        if eid not in by_id or row.get("event_time_DATM") != by_id[eid].get("time_DATM"):
            raise ValueError("Exact ledger event identity/time mismatch")
        if row.get("ledger_time_matches_prior_scan") is not True or row.get("ledger_sha256_matches_manifest") is not True:
            raise ValueError("Source ledger did not pass provenance checks")
        if row.get("scientific_release")!="HOLD":
            raise ValueError("Prior ledger has unexpected scientific approval")
        counts[row.get("ledger_stage")]+=1
    if dict(counts)!=EXPECTED_STAGES:
        raise ValueError("Unexpected Stage34/38/42 event distribution: "+str(dict(counts)))
    return records,by_id


def triage(record, old):
    ledger=record.get("ledger_full_record")
    if not isinstance(ledger,dict):
        raise ValueError("Stage02N original full ledger row not available")
    rh=value(ledger,"RH_IMPLIED_PCT")
    if rh is None:
        rh=value(ledger,"RH_input_pct")
    era=value(ledger,"era5_RH_pct")
    land=value(ledger,"era5_land_RH_pct")
    before=value(ledger,"RH_previous")
    after=value(ledger,"RH_next")
    qc=ledger.get("VPD_F_QC")
    if qc is None: qc=old.get("source_FLUXMET_START_VPD_F_QC_raw")
    vpd=old.get("source_FLUXMET_START_VPD_F_raw")
    vpd_era=old.get("source_FLUXMET_START_VPD_ERA_raw")
    source_rh_present=old.get("source_RH_numeric_present")
    if source_rh_present is not False:
        raise ValueError("Native/distributed RH availability different from previously verified missing-RH sample")
    gaps=[abs(x-rh) for x in (before,after) if x is not None and rh is not None]
    jump=max(gaps) if gaps else None
    seam=str(ledger.get("is_source_seam","")).strip().lower()=="true"
    flags=[]
    if rh is None: flags.append("NO_LEDGER_IMPLIED_RH")
    elif rh<10: flags.append("IMPLIED_RH_BELOW_10PCT")
    if qc is not None and str(qc).strip()=="1": flags.append("VPD_F_QC1_GAPFILLED_SOURCE")
    if era is None or land is None: flags.append("MISSING_ERA5_OR_ERA5LAND_LEDGER_RH")
    if rh is not None and era is not None and abs(era-rh)>=50: flags.append("ERA5_IMPLIED_RH_GAP_GE50PP")
    if rh is not None and land is not None and abs(land-rh)>=50: flags.append("ERA5LAND_IMPLIED_RH_GAP_GE50PP")
    if era is not None and land is not None and abs(land-era)>=10: flags.append("ERA5_VS_LAND_GAP_GE10PP")
    if jump is not None and jump>=40: flags.append("NEIGHBOR_RH_JUMP_GE40PP")
    if seam: flags.append("SOURCE_SEAM_RECORDED")
    status=str(record.get("ledger_manifest_status",""))
    if not status.startswith("EXPLORATORY_"):
        flags.append("UNEXPECTED_OR_UNSPECIFIED_LEDGER_SCIENCE_STATUS")
    flags.append("NATIVE_TOWER_RH_UNVERIFIED")
    severity=sum(x in flags for x in (
        "IMPLIED_RH_BELOW_10PCT","ERA5_IMPLIED_RH_GAP_GE50PP",
        "ERA5LAND_IMPLIED_RH_GAP_GE50PP","NEIGHBOR_RH_JUMP_GE40PP",
        "SOURCE_SEAM_RECORDED"))
    return {
        "event_id":record["event_id"],"DATM_time":record["event_time_DATM"],
        "revision_stage":record["ledger_stage"],
        "source_ledger_sha_verified":True,
        "original_ledger_science_status":status,
        "FLUXMET_VPD_F_hPa_raw":vpd,
        "FLUXMET_VPD_F_QC_raw":qc,
        "FLUXMET_VPD_ERA_hPa_raw":vpd_era,
        "RH_from_processed_input_pct":rh,
        "ERA5_RH_pct_ledger":era,"ERA5_Land_RH_pct_ledger":land,
        "ERA5_minus_input_RH_pp":era-rh if rh is not None and era is not None else None,
        "ERA5Land_minus_input_RH_pp":land-rh if rh is not None and land is not None else None,
        "ERA5Land_minus_ERA5_RH_pp":land-era if era is not None and land is not None else None,
        "RH_previous_pct":before,"RH_next_pct":after,"neighbor_max_abs_jump_pp":jump,
        "source_seam_in_ledger":seam,
        "flags":"|".join(flags),"priority":"REVIEW_FIRST" if severity>=3 else "REVIEW",
        "native_tower_RH_QC_verified":False,
        "ERA_representativeness_verified":False,
        "timestamp_convention_verified":False,
        "scientific_release":"HOLD",
    }


def summarize(rows):
    count=collections.Counter()
    for r in rows:
        count.update([r["revision_stage"]])
        count.update("FLAG:"+flag for flag in r["flags"].split("|") if flag)
    return {"event_count":len(rows),
            "revision_stage_events":{s:count[s] for s in sorted(EXPECTED_STAGES)},
            "low_implied_RH_under10_events":count["FLAG:IMPLIED_RH_BELOW_10PCT"],
            "ERA5_conflict_50pp_events":count["FLAG:ERA5_IMPLIED_RH_GAP_GE50PP"],
            "ERA5Land_conflict_50pp_events":count["FLAG:ERA5LAND_IMPLIED_RH_GAP_GE50PP"],
            "neighbor_jump_40pp_events":count["FLAG:NEIGHBOR_RH_JUMP_GE40PP"],
            "source_seam_events":count["FLAG:SOURCE_SEAM_RECORDED"],
            "review_first_count":sum(r["priority"]=="REVIEW_FIRST" for r in rows),
            "native_tower_RH_verified_events":0,
            "case_selection_approved":False}


def self_test():
    n={"stage":STAGE_N,"read_only":True,"science_release":False,
       "reported_science_holds":[],"ledger_sha_unverified_stages":[],
       "original_ledger_provenance":[{"sha256_verified":True}]*3,
       "matched_exact_event_records":[]}
    m={"stage":STAGE_M,"read_only":True,"science_release":False,
       "event_science_and_revision_ledgers":[]}
    for idx in range(20):
        eid=f"E{idx+1:03d}"
        stage=("stage34" if idx<7 else "stage38" if idx<12 else "stage42")
        time=f"2007-07-22 {idx:02d}:00:00"
        row={"time":time,"RH_IMPLIED_PCT":"0.3","era5_RH_pct":"99",
             "era5_land_RH_pct":"98","VPD_F_QC":"1"}
        if stage=="stage34":row.update(RH_previous="70",RH_next="90",is_source_seam="True")
        n["matched_exact_event_records"].append({
            "event_id":eid,"event_time_DATM":time,"ledger_stage":stage,
            "ledger_time_matches_prior_scan":True,"ledger_sha256_matches_manifest":True,
            "ledger_manifest_status":"EXPLORATORY_NOT_TOWER_VALIDATED",
            "ledger_full_record":row,"scientific_release":"HOLD"})
        m["event_science_and_revision_ledgers"].append({
            "event_id":eid,"time_DATM":time,"decision":"HOLD_NATIVE_TOWER_RH_ERA_AND_REPAIR_JUSTIFICATION",
            "source_FLUXMET_START_VPD_F_QC_raw":"1",
            "source_FLUXMET_START_VPD_F_raw":"11.2",
            "source_FLUXMET_START_VPD_ERA_raw":"1.5",
            "source_RH_numeric_present":False})
    records,by_id=check_inputs(n,m)
    rows=[triage(r,by_id[r["event_id"]]) for r in records]
    s=summarize(rows)
    assert s["event_count"]==20 and s["low_implied_RH_under10_events"]==20
    assert s["source_seam_events"]==7
    assert all(r["scientific_release"]=="HOLD" for r in rows)
    print("STAGE02O SELF-TEST PASS: 20 verified event ledgers, native RH/QC HOLD, ERA-vs-gapfill screening; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02n",type=Path)
    ap.add_argument("--stage02m",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        self_test();return
    if any(p is None or not p.is_file() for p in (args.stage02n,args.stage02m)):
        ap.error("Saved Stage02N and Stage02M JSONs are required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("Output directory must already exist and be EMPTY")
    n=json.loads(args.stage02n.read_text(encoding="utf-8"))
    m=json.loads(args.stage02m.read_text(encoding="utf-8"))
    records,by_id=check_inputs(n,m)
    rows=[triage(r,by_id[r["event_id"]]) for r in records]
    rows.sort(key=lambda x:(x["priority"]!="REVIEW_FIRST",
                             -abs(x["ERA5Land_minus_input_RH_pp"] or 0),
                             x["DATM_time"]))
    stats=summarize(rows)
    for row in rows:
        print("EVENT",row["event_id"],row["DATM_time"],"STAGE",row["revision_stage"],
              "RH_SOURCE",row["RH_from_processed_input_pct"],
              "RH_ERA5",row["ERA5_RH_pct_ledger"],
              "RH_ERA5LAND",row["ERA5_Land_RH_pct_ledger"],
              "NEIGHBOR_MAX_JUMP_PP",row["neighbor_max_abs_jump_pp"],
              "SEAM",row["source_seam_in_ledger"],
              "PRIORITY",row["priority"],
              "FLAGS",row["flags"])
    print("SUMMARY",json.dumps(stats,sort_keys=True))
    output={
        "stage":"STAGE02O_CH_AWS_REPAIR_EVENT_SCIENCE_TRIAGE_READONLY",
        "read_only":True,"science_release":False,
        "model_input_modified":False,"slurm_submitted":False,
        "input_stage02n":str(args.stage02n),"input_stage02m":str(args.stage02m),
        "summary":stats,"events_ranked":rows,
        "critical_limitations":(
            "These are only 20 high-difference, nonrandom event candidates. "
            "RH_from_processed_input is NOT measured native tower RH. "
            "ERA5 and ERA5-Land may share systematic biases and are not independent "
            "tower evidence. START and native clock, pressure, source altitude, "
            "instrument QC and PFT remain unverified. No repair is approved."),
    }
    j=args.out_dir/"stage02o_CH_Aws_20_event_risk_triage.json"
    c=args.out_dir/"stage02o_CH_Aws_20_event_risk_triage.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(output,f,indent=2,ensure_ascii=False);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(rows)
    print("REPORT",j)
    print("CSV",c)
    print("SCIENCE_HOLD: NATIVE_TOWER_RH_QC, SOURCE_CLOCK, ERA5_SITE_REPRESENTATIVENESS; NO AD5/AD400")


if __name__=="__main__":
    main()
