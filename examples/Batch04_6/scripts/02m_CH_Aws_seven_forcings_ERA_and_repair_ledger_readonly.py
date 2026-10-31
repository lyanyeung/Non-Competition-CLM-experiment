#!/usr/bin/env python3
"""Batch04 Stage02M: CH-Aws VPD_F vs VPD_ERA and historical repair ledgers.

Read-only evidence triage using actual saved Stage02L/02I JSON reports.
At 20 selected large-QBOT-change event anchors, compare seven candidate
DATM model VPD values against both original-distribution FLUXMET START-time
VPD_F (gap-filled QC1 in observed 20 events) and VPD_ERA. Join exact and
nearby Stage34/38/42 repair-ledger candidate matches by event ID.

Numerical similarity to ERA, or to MDS-filled VPD_F, DOES NOT establish
scientific correctness or approve any candidate. Native unfilled tower RH,
QC semantics, ERA5 provenance and UTC/start clock remain unverified.

No source/NC/CIME/FATES/Slurm/Git modification; only --out-dir writes two
new files in a pre-existing EMPTY directory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import math
from pathlib import Path

STAGE_L="STAGE02L_CH_AWS_DATM_FLUXMET_TWO_CLOCK_SOURCE_EVIDENCE"
STAGE_I="STAGE02I_CH_AWS_SOURCE_CSV_EVENT_SCHEMA_READONLY"
REFERENCE="CH-Aws_FATES_SPINUP500_11P"
LEDGERS=("stage34", "stage38", "stage42")
COLS=(
    "event_id","DATM_time","candidate_case_group",
    "is_unapproved_reference","DATM_VPD_water_hPa","DATM_QBOT_gkg",
    "DATM_RH_water_pct","FLUXMET_START_VPD_F_hPa_IF_UNITS",
    "FLUXMET_START_VPD_F_QC_raw","FLUXMET_START_TA_F_QC_raw",
    "FLUXMET_START_VPD_ERA_hPa_IF_UNITS","FLUXMET_START_RH_raw",
    "abs_DATM_minus_START_VPD_F_hPa_HYPOTHESIS",
    "abs_DATM_minus_START_VPD_ERA_hPa_HYPOTHESIS",
    "exact_time_revision_ledger_row_count","near_time_revision_ledger_row_count",
    "tower_native_RH_verified","ERA5_provenance_verified",
    "START_time_basis_verified","scientific_release",
)


def as_number(value):
    try:
        x=float(str(value).strip())
        if math.isfinite(x) and x > -9990:
            return x
    except (TypeError, ValueError):
        pass
    return None


def read_inputs(l, i):
    if not isinstance(l,dict) or l.get("stage")!=STAGE_L or \
       l.get("read_only") is not True or l.get("scientific_release") is not False:
        raise ValueError("Require unreleased Stage02L JSON")
    if not isinstance(i,dict) or i.get("stage")!=STAGE_I or \
       i.get("read_only") is not True or i.get("scientific_release") is not False:
        raise ValueError("Require unreleased Stage02I source-matches JSON")
    events=l.get("events")
    targets=i.get("selected_ranked_events")
    if not isinstance(events,list) or len(events)!=20 or \
       not isinstance(targets,list) or len(targets)!=20:
        raise ValueError("Require same 20 selected CH-Aws events")
    time_by_id={str(x.get("event_id")):str(x.get("event_time_DATM")) for x in targets}
    if len(time_by_id)!=20:
        raise ValueError("Stage02I event identity duplication")
    eids=set()
    for e in events:
        eid=e.get("event_id")
        if eid in eids or time_by_id.get(eid)!=e.get("event_time_DATM"):
            raise ValueError("Stage02L and Stage02I exact event time/id mismatch")
        eids.add(eid)
        if len(e.get("model_versions",[]))!=7:
            raise ValueError("Require 7 distinct DATM case-group values per event")
        if e.get("science_release")!="HOLD_NATIVE_SOURCE_QC_AND_ACTUAL_ERA_PROVENANCE":
            raise ValueError("Stage02L event source approval state changed")
    return events, i.get("candidate_matched_rows",[])


def collect_ledgers(matches, event_ids):
    result=collections.defaultdict(list)
    for m in matches:
        eid=m.get("event_id")
        if eid not in event_ids:
            continue
        path=str(m.get("source_csv",""))
        stage=next((s for s in LEDGERS if s in path.lower()),None)
        if stage is None:
            continue
        offset=m.get("matched_offset_minutes")
        if not isinstance(offset,int) or offset not in (-60,-30,0,30,60):
            raise ValueError("Unexpected matched half-hour offset from Stage02I ledger")
        fields=m.get("candidate_record_fields",{})
        if not isinstance(fields,dict):
            raise ValueError("Stage02I candidate ledger fields not a mapping")
        result[eid].append({
            "ledger_stage":stage,"source_csv":path,
            "row_number":m.get("row_number"),
            "source_timestamp_column":m.get("matched_time_column"),
            "original_time":m.get("raw_time_value"),
            "offset_minutes":offset,
            "source_time_basis_verified":False,
            "native_QC_verified":False,
            "fields":{str(k):str(v)[:400] for k,v in list(fields.items())[:70]},
        })
    return result


def analyse(events, matches, verbose=True):
    grouped=collect_ledgers(matches,{e["event_id"] for e in events})
    result=[]
    rows=[]
    by_case=collections.defaultdict(lambda:{
        "events":0,"MAE_F_abs_sum":0.0,"MAE_ERA_abs_sum":0.0,
        "F_valid":0,"ERA_valid":0,"max_delta_F":0.0,"max_delta_ERA":0.0,
    })
    per_event=[]
    for event in events:
        eid=event["event_id"]
        start=event.get("source_START_raw",{})
        if not isinstance(start,dict):
            raise ValueError("Expected original Stage02L FLUXMET START source record")
        vpd_f=as_number(start.get("VPD_F"))
        era=as_number(start.get("VPD_ERA"))
        raw_rh=as_number(start.get("RH"))
        raw_qc=start.get("VPD_F_QC")
        ta_qc=start.get("TA_F_QC")
        if vpd_f is not None and not 0<=vpd_f<120:
            raise ValueError("Outside expected FLUXMET VPD_F domain")
        if era is not None and not 0<=era<120:
            raise ValueError("Outside expected FLUXMET VPD_ERA domain")
        ledgers=grouped.get(eid,[])
        exact=[x for x in ledgers if x["offset_minutes"]==0]
        near=[x for x in ledgers if x["offset_minutes"]!=0]
        cases=[]
        for m in event["model_versions"]:
            names=m.get("cases")
            if not isinstance(names,list) or not names:
                raise ValueError("Missing original case label")
            key=",".join(names)
            model_vpd=as_number(m.get("VPD_water_hPa"))
            qb=as_number(m.get("QBOT_gkg"))
            rh=as_number(m.get("RH_water_pct"))
            if None in (model_vpd,qb,rh):
                raise ValueError("Invalid Stage02L numeric DATM field")
            d_f=abs(model_vpd-vpd_f) if vpd_f is not None else None
            d_era=abs(model_vpd-era) if era is not None else None
            rec={
                "event_id":eid,"DATM_time":event["event_time_DATM"],
                "candidate_case_group":key,
                "is_unapproved_reference":REFERENCE in names,
                "DATM_VPD_water_hPa":model_vpd,"DATM_QBOT_gkg":qb,
                "DATM_RH_water_pct":rh,
                "FLUXMET_START_VPD_F_hPa_IF_UNITS":vpd_f,
                "FLUXMET_START_VPD_F_QC_raw":raw_qc,
                "FLUXMET_START_TA_F_QC_raw":ta_qc,
                "FLUXMET_START_VPD_ERA_hPa_IF_UNITS":era,
                "FLUXMET_START_RH_raw":start.get("RH"),
                "abs_DATM_minus_START_VPD_F_hPa_HYPOTHESIS":d_f,
                "abs_DATM_minus_START_VPD_ERA_hPa_HYPOTHESIS":d_era,
                "exact_time_revision_ledger_row_count":len(exact),
                "near_time_revision_ledger_row_count":len(near),
                "tower_native_RH_verified":False,
                "ERA5_provenance_verified":False,
                "START_time_basis_verified":False,
                "scientific_release":"HOLD",
            }
            rows.append(rec)
            agg=by_case[key]
            agg["events"]+=1
            if d_f is not None:
                agg["F_valid"]+=1
                agg["MAE_F_abs_sum"]+=d_f
                agg["max_delta_F"]=max(agg["max_delta_F"],d_f)
            if d_era is not None:
                agg["ERA_valid"]+=1
                agg["MAE_ERA_abs_sum"]+=d_era
                agg["max_delta_ERA"]=max(agg["max_delta_ERA"],d_era)
            cases.append({"case_group":key,"DATM_VPD_water_hPa":model_vpd,
                          "abs_vs_gapfilled_START_F_hPa":d_f,
                          "abs_vs_ERA_product_hPa":d_era})
        closest_era=sorted([x for x in cases if x["abs_vs_ERA_product_hPa"] is not None],
                           key=lambda r:r["abs_vs_ERA_product_hPa"])
        summary={
            "event_id":eid,"time_DATM":event["event_time_DATM"],
            "source_FLUXMET_START_VPD_F_raw":start.get("VPD_F"),
            "source_FLUXMET_START_VPD_F_QC_raw":raw_qc,
            "source_FLUXMET_START_TA_F_QC_raw":ta_qc,
            "source_FLUXMET_START_VPD_ERA_raw":start.get("VPD_ERA"),
            "source_FLUXMET_START_RH_raw":start.get("RH"),
            "source_RH_numeric_present":raw_rh is not None,
            "source_ERA_VPD_numeric_present":era is not None,
            "source_START_clock_verified":False,
            "source_QC_ERA_provenance_verified":False,
            "most_numerically_similar_to_ERA_DIAGNOSTIC_ONLY":(
                closest_era[0] if closest_era else None),
            "matched_revision_ledger_exact_time":exact,
            "matched_revision_ledger_context_only":near,
            "seven_case_comparisons":cases,
            "decision":"HOLD_NATIVE_TOWER_RH_ERA_AND_REPAIR_JUSTIFICATION",
        }
        per_event.append(summary)
        if verbose: print("EVENT",eid,event["event_time_DATM"],
              "SRC_VPD_F",vpd_f,"SRC_VPD_ERA",era,"SRC_RH_PRESENT",raw_rh is not None,
              "SRC_VPD_F_QC_RAW",raw_qc,
              "LEDGER_EXACT",len(exact),"LEDGER_NEAR",len(near),
              "CLOSEST_ERA_NUMERIC_ONLY",closest_era[0]["case_group"] if closest_era else "NONE",
              "CLOSEST_ERA_ABS_HPA",
              round(closest_era[0]["abs_vs_ERA_product_hPa"],6) if closest_era else "NA")
    bycase={}
    for key,a in sorted(by_case.items()):
        bycase[key]={
            "events":a["events"],"source_F_n":a["F_valid"],"source_ERA_n":a["ERA_valid"],
            "MAE_vs_F_gapfilled_START_hPa_HYPOTHESIS":(
                a["MAE_F_abs_sum"]/a["F_valid"] if a["F_valid"] else None),
            "MAE_vs_VPD_ERA_product_hPa_HYPOTHESIS":(
                a["MAE_ERA_abs_sum"]/a["ERA_valid"] if a["ERA_valid"] else None),
            "max_abs_diff_F_hPa":a["max_delta_F"],
            "max_abs_diff_ERA_hPa":a["max_delta_ERA"],
            "scientific_approval":False,
        }
        if verbose: print("VERSION",key,
              "N",a["events"],"MAE_GAPFILLED_F",
              round(bycase[key]["MAE_vs_F_gapfilled_START_hPa_HYPOTHESIS"],6)
              if a["F_valid"] else "NA",
              "MAE_ERA",round(bycase[key]["MAE_vs_VPD_ERA_product_hPa_HYPOTHESIS"],6)
              if a["ERA_valid"] else "NA",
              "STATUS HOLD")
    return rows,per_event,bycase


def selftest():
    def event(k):
        m=[]
        for j in range(7):
            key=REFERENCE if j==0 else "CH-Aws_FATES_TEST_"+str(j)
            m.append({"cases":[key],"VPD_water_hPa":10+j,
                      "QBOT_gkg":3+j*.1,"RH_water_pct":50+j})
        return {"event_id":f"E{k:03d}","event_time_DATM":"2007-07-22 07:30:00",
                "science_release":"HOLD_NATIVE_SOURCE_QC_AND_ACTUAL_ERA_PROVENANCE",
                "source_START_raw":{"VPD_F":"10.002","VPD_ERA":"12","VPD_F_QC":"1",
                                    "TA_F_QC":"0","RH":"-9999"},
                "model_versions":m}
    events=[event(k) for k in range(1,21)]
    l={"stage":STAGE_L,"read_only":True,"scientific_release":False,"events":events}
    i={"stage":STAGE_I,"read_only":True,"scientific_release":False,
       "selected_ranked_events":[{"event_id":f"E{k:03d}",
          "event_time_DATM":"2007-07-22 07:30:00"} for k in range(1,21)],
       "candidate_matched_rows":[{"event_id":"E001",
          "source_csv":"/mock/stage34_27_QC1_sensitivity_ledger.csv",
          "matched_offset_minutes":0,"candidate_record_fields":{"QC":"UNVERIFIED"}}]}
    actual,matches=read_inputs(l,i)
    rows,report,by=analyse(actual,matches,verbose=False)
    assert len(rows)==140 and len(report)==20 and len(by)==7
    assert report[0]["source_RH_numeric_present"] is False
    assert len(report[0]["matched_revision_ledger_exact_time"])==1
    assert by[REFERENCE]["source_ERA_n"]==20
    assert all(x["scientific_release"]=="HOLD" for x in rows)
    print("STAGE02M SELF-TEST PASS: 20 events x 7 variants, raw gapfilled VPD vs ERA, exact ledger QC HOLD; no writes")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02l",type=Path)
    ap.add_argument("--stage02i",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest()
        return
    if args.stage02l is None or not args.stage02l.is_file() or \
       args.stage02i is None or not args.stage02i.is_file():
        ap.error("Saved Stage02L and Stage02I JSON inputs are both required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY; existing files are never overwritten")
    l=json.loads(args.stage02l.read_text(encoding="utf-8"))
    i=json.loads(args.stage02i.read_text(encoding="utf-8"))
    events,matches=read_inputs(l,i)
    rows,by_event,by_case=analyse(events,matches)
    summary={
        "stage":"STAGE02M_CH_AWS_SEVEN_SOURCE_VPD_ERA_LEDGER_TRIAGE",
        "read_only":True,"science_release":False,
        "source_modified":False,"model_case_modified":False,"slurm_submitted":False,
        "source_stage02l":str(args.stage02l),"source_stage02i":str(args.stage02i),
        "selected_events":20,"DATM_model_case_group_rows":len(rows),
        "start_clock_metadata_verified":False,"unfilled_tower_RH_QC_verified":False,
        "independent_ERA5_source_verified":False,
        "warning":"Numerical agreement with gap-filled VPD_F or VPD_ERA is NOT an approval/ranking",
        "model_case_diagnostic_only":by_case,
        "event_science_and_revision_ledgers":by_event,
    }
    jp=args.out_dir/"stage02m_ERA_gapfill_revision_evidence.json"
    cp=args.out_dir/"stage02m_seven_forcings_twenty_events.csv"
    with jp.open("x",encoding="utf-8") as h:
        json.dump(summary,h,indent=2)
        h.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)
    print("EVENTS",len(by_event),"MODEL_VERSION_ROWS",len(rows))
    print("REPORT",jp)
    print("MATRIX",cp)
    print("SCIENCE_HOLD: ORIGINAL_TOWER_RH_QC, ERA_PROVENANCE, START_TIME, REPAIR_JUSTIFICATION")


if __name__=="__main__":
    main()
