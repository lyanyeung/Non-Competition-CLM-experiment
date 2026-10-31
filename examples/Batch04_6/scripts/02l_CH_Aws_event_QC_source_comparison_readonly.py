#!/usr/bin/env python3
"""ICOS Batch04 Stage02L — CH-Aws all-seven DATM vs FLUXMET source clock/QC matrix.

Read-only 20-event scientific triage from Stage02K JSON. Model DATM VPD values
are computed using Buck liquid-water saturation; FLUXMET source VPD_F, VPD_ERA
and RH fields are retained exactly. START-vs-END comparisons are numerically
diagnostic, NOT UTC/local/START-END source provenance approval. FLUXMET _F
and QC labels are not necessarily original native tower observations.
Only --out-dir creates NEW JSON and CSV in an existing empty HOME folder.
Never changes original source, NC, case, FATES, Git tree, or Slurm.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
from pathlib import Path

STAGE_K="STAGE02K_CH_AWS_FLUXMET_DATM_EVENT_PHYSICS_REVIEW"
REF_CASE="CH-Aws_FATES_SPINUP500_11P"
CLOCKS=("TIMESTAMP_START","TIMESTAMP_END")
NUMERIC_FIELDS=("TA_F","TA_F_QC","VPD_F","VPD_F_QC","VPD_ERA","TA_ERA",
                "RH","PA","PA_F","PA_F_QC")
CSV_FIELDS=(
    "event_id","DATM_time","DATM_index","model_cases","historical_reference",
    "candidate_DATM_QBOT_gkg","candidate_DATM_TBOT_C",
    "candidate_DATM_vapor_hPa","candidate_DATM_VPD_water_hPa",
    "candidate_DATM_RH_water_pct","source_START_VPD_F_raw","source_END_VPD_F_raw",
    "candidate_minus_START_VPD_F_hPa_HYPOTHESIS",
    "candidate_minus_END_VPD_F_hPa_HYPOTHESIS",
    "source_START_VPD_F_QC_raw","source_END_VPD_F_QC_raw",
    "source_START_RH_raw","source_END_RH_raw",
    "source_START_VPD_ERA_raw","source_END_VPD_ERA_raw",
    "source_START_TA_F_raw","source_END_TA_F_raw",
    "source_START_PA_F_raw","source_END_PA_F_raw",
    "source_CLOCK_basis_verified","native_tower_QC_verified","ERA5_provenance_verified",
)
MAX_EVENTS=20


def finite_raw(raw):
    if raw is None: return None
    try:
        v=float(str(raw).strip())
        if not math.isfinite(v) or v<=-9990:
            return None
        return v
    except (TypeError,ValueError):
        return None


def require_k(j):
    if not isinstance(j,dict) or j.get("stage")!=STAGE_K:
        raise ValueError("Need actual saved Stage02K JSON")
    if j.get("read_only") is not True or j.get("science_release") is not False:
        raise ValueError("Stage02K scientific release/immutability mismatch")
    if j.get("FLUXMET_original_product_is_processed") is not True:
        raise ValueError("FLUXMET product provenance incorrectly approved")
    if j.get("DATM_time_alignment_to_event_label_verified") is not True:
        raise ValueError("No verified DATM time provenance")
    if j.get("source_START_END_and_UTC_alignment_verified") is not False:
        raise ValueError("Must preserve START/END/UTC unresolved")
    events=j.get("events")
    if not isinstance(events,list) or len(events)!=MAX_EVENTS:
        raise ValueError("Expected exactly 20 Stage02K event summaries")
    ids=[x.get("event_id") for x in events]
    if len(ids)!=len(set(ids)):
        raise ValueError("Duplicate Stage02K event IDs")
    return events


def source_clock(event,clock):
    slot=("same_time_source_alternative_START" if clock=="TIMESTAMP_START"
          else "same_time_source_alternative_END")
    obj=event.get(slot)
    if not isinstance(obj,dict) or obj.get("status")!="SOURCE_CANDIDATE_UNVERIFIED_TIME_AND_QC":
        raise ValueError("Missing exact-zero "+clock+" FLUXMET source candidate")
    row=obj.get("raw_source_values")
    if not isinstance(row,dict):
        raise ValueError("Missing original raw FLUXMET source field values")
    return {k:row.get(k) for k in NUMERIC_FIELDS}


def water_es_hpa(celsius):
    return 6.1121*math.exp((18.678-celsius/234.5)*celsius/(257.14+celsius))


def reconstruct_from_source(row):
    """FLUXMET Celsius / hPa / kPa interpretations remain CONDITIONAL."""
    temp=finite_raw(row.get("TA_F"))
    vpd=finite_raw(row.get("VPD_F"))
    pa=finite_raw(row.get("PA_F"))
    rh=finite_raw(row.get("RH"))
    out={"units_verified":False,"source_raw_QC_verified":False}
    if temp is not None and -90<temp<65:
        sat=water_es_hpa(temp)
        out["es_water_hPa_IF_TA_C"]=sat
        if vpd is not None:
            e=sat-vpd
            out["vapor_hPa_IF_VPD_F_hPa"]=e
            out["RH_water_pct_IF_TA_C_VPD_hPa"]=100*e/sat
            if pa is not None and pa>0 and 0<=e<pa*10:
                ePa=e*100
                pressure=pa*1000
                out["QBOT_gkg_IF_PA_F_kPa_AND_VPD_F_hPa"]=1000*(.622*ePa/(pressure-.378*ePa))
        if rh is not None and 0<=rh<=150:
            out["VPD_water_hPa_IF_RH_percent"]=sat*(1-rh/100)
            out["VPD_from_RH_minus_VPD_F_hPa_IF_UNITS"]=(sat*(1-rh/100)-vpd
                                                       if vpd is not None else None)
    return out


def investigate_event(event):
    model=event.get("model_versions")
    if not isinstance(model,list) or len(model)!=7:
        raise ValueError("Expected seven model forcing-version groups")
    if event.get("scientific_release")!="HOLD":
        raise ValueError("No valid release gate")
    if event.get("source_QC_verified") is not False or event.get("time_start_end_verified") is not False:
        raise ValueError("Source QC/time falsely approved")
    reference=[r for r in model if REF_CASE in r.get("cases",[])]
    if len(reference)!=1:
        raise ValueError("Reference forcing group missing")
    if any(r.get("status")!="DATM_INTERNAL_EVENT_READ" for r in model):
        raise ValueError("Model event was not an internally valid read")
    ref=reference[0]
    for v in model:
        if (str(v["DATM_time"])!=str(event["DATM_event_time"])
                or v["index"]!=event["DATM_halfhour_index"]):
            raise ValueError("DATM index/date disagreement across model versions")
        if abs(float(v["TBOT_K"])-float(ref["TBOT_K"]))>1e-8:
            raise ValueError("TBOT differs among candidates")
        if abs(float(v["PSRF_Pa"])-float(ref["PSRF_Pa"]))>1e-5:
            raise ValueError("PSRF differs among candidates")
    source={clock:source_clock(event,clock) for clock in CLOCKS}
    ref_vpd=float(ref["VPD_water_hPa"])
    start_vpd=finite_raw(source["TIMESTAMP_START"].get("VPD_F"))
    end_vpd=finite_raw(source["TIMESTAMP_END"].get("VPD_F"))
    source_reconstruction={clock:reconstruct_from_source(source[clock]) for clock in CLOCKS}
    variants=[]
    for v in model:
        vpd=float(v["VPD_water_hPa"])
        row={
            "cases":v.get("cases",[]),"QBOT_gkg":1000*float(v["QBOT_kgkg"]),
            "VPD_water_hPa":vpd,"RH_water_pct":float(v["RH_water_pct"]),
            "TBOT_C":float(v["TBOT_K"])-273.15,
            "PSRF_Pa":float(v["PSRF_Pa"]),
            "vapor_hPa":float(v["vapor_pressure_hPa"]),
            "delta_VPD_vs_SOURCE_START_hPa_HYPOTHESIS":vpd-start_vpd if start_vpd is not None else None,
            "delta_VPD_vs_SOURCE_END_hPa_HYPOTHESIS":vpd-end_vpd if end_vpd is not None else None,
            "delta_VPD_vs_SOURCE_START_ERA_hPa_HYPOTHESIS":(
                vpd-finite_raw(source["TIMESTAMP_START"].get("VPD_ERA"))
                if finite_raw(source["TIMESTAMP_START"].get("VPD_ERA")) is not None else None
            ),
            "QC0_provenance_approved":False,
        }
        variants.append(row)
    start_error=abs(ref_vpd-start_vpd) if start_vpd is not None else None
    end_error=abs(ref_vpd-end_vpd) if end_vpd is not None else None
    return {
        "event_id":event["event_id"],"event_time_DATM":event["DATM_event_time"],
        "half_hour_index":event["DATM_halfhour_index"],
        "historical_reference_case_unapproved":REF_CASE,
        "reference_DATM_VPD_hPa":ref_vpd,
        "source_START_raw":source["TIMESTAMP_START"],
        "source_END_raw":source["TIMESTAMP_END"],
        "source_START_reconstruction_HYPOTHESIS":source_reconstruction["TIMESTAMP_START"],
        "source_END_reconstruction_HYPOTHESIS":source_reconstruction["TIMESTAMP_END"],
        "reference_abs_diff_START_VPD_F_hPa_IF_UNITS":start_error,
        "reference_abs_diff_END_VPD_F_hPa_IF_UNITS":end_error,
        "START_closer_than_END_IF_UNITS":(start_error<end_error
            if start_error is not None and end_error is not None else None),
        "source_START_VPD_F_QC_raw":source["TIMESTAMP_START"].get("VPD_F_QC"),
        "source_END_VPD_F_QC_raw":source["TIMESTAMP_END"].get("VPD_F_QC"),
        "source_START_TA_F_QC_raw":source["TIMESTAMP_START"].get("TA_F_QC"),
        "source_START_RH_present":finite_raw(source["TIMESTAMP_START"].get("RH")) is not None,
        "source_START_VPD_ERA_present":finite_raw(source["TIMESTAMP_START"].get("VPD_ERA")) is not None,
        "model_versions":variants,
        "science_release":"HOLD_NATIVE_SOURCE_QC_AND_ACTUAL_ERA_PROVENANCE",
    }


def build_matrix(result):
    rows=[]
    start=result["source_START_raw"]
    end=result["source_END_raw"]
    for v in result["model_versions"]:
        rows.append({
            "event_id":result["event_id"],
            "DATM_time":result["event_time_DATM"],
            "DATM_index":result["half_hour_index"],
            "model_cases":",".join(v["cases"]),
            "historical_reference":REF_CASE in v["cases"],
            "candidate_DATM_QBOT_gkg":v["QBOT_gkg"],
            "candidate_DATM_TBOT_C":v["TBOT_C"],
            "candidate_DATM_vapor_hPa":v["vapor_hPa"],
            "candidate_DATM_VPD_water_hPa":v["VPD_water_hPa"],
            "candidate_DATM_RH_water_pct":v["RH_water_pct"],
            "source_START_VPD_F_raw":start.get("VPD_F"),
            "source_END_VPD_F_raw":end.get("VPD_F"),
            "candidate_minus_START_VPD_F_hPa_HYPOTHESIS":v["delta_VPD_vs_SOURCE_START_hPa_HYPOTHESIS"],
            "candidate_minus_END_VPD_F_hPa_HYPOTHESIS":v["delta_VPD_vs_SOURCE_END_hPa_HYPOTHESIS"],
            "source_START_VPD_F_QC_raw":start.get("VPD_F_QC"),
            "source_END_VPD_F_QC_raw":end.get("VPD_F_QC"),
            "source_START_RH_raw":start.get("RH"),
            "source_END_RH_raw":end.get("RH"),
            "source_START_VPD_ERA_raw":start.get("VPD_ERA"),
            "source_END_VPD_ERA_raw":end.get("VPD_ERA"),
            "source_START_TA_F_raw":start.get("TA_F"),
            "source_END_TA_F_raw":end.get("TA_F"),
            "source_START_PA_F_raw":start.get("PA_F"),
            "source_END_PA_F_raw":end.get("PA_F"),
            "source_CLOCK_basis_verified":False,
            "native_tower_QC_verified":False,
            "ERA5_provenance_verified":False,
        })
    return rows


def summarize(results):
    starts=[x["reference_abs_diff_START_VPD_F_hPa_IF_UNITS"] for x in results]
    ends=[x["reference_abs_diff_END_VPD_F_hPa_IF_UNITS"] for x in results]
    if any(v is None for v in starts+ends):
        raise ValueError("At least one original FLUXMET source VPD_F is missing")
    qc_start=collections.Counter(str(x["source_START_VPD_F_QC_raw"]) for x in results)
    qc_temp=collections.Counter(str(x["source_START_TA_F_QC_raw"]) for x in results)
    return {
        "events":len(results),
        "reference_START_VPD_F_mae_hPa_IF_UNITS":sum(starts)/len(starts),
        "reference_END_VPD_F_mae_hPa_IF_UNITS":sum(ends)/len(ends),
        "reference_START_VPD_F_max_abs_hPa_IF_UNITS":max(starts),
        "reference_END_VPD_F_max_abs_hPa_IF_UNITS":max(ends),
        "reference_within_0p01_hPa_START_count":sum(x<0.01 for x in starts),
        "reference_within_0p01_hPa_END_count":sum(x<0.01 for x in ends),
        "START_closer_than_END_count":sum(x<y for x,y in zip(starts,ends)),
        "END_closer_than_START_count":sum(x>y for x,y in zip(starts,ends)),
        "TIE_exact_rounded_counts":sum(x==y for x,y in zip(starts,ends)),
        "source_START_VPD_F_QC_raw_counts":dict(qc_start),
        "source_START_TA_F_QC_raw_counts":dict(qc_temp),
        "source_START_RH_numeric_presence":sum(x["source_START_RH_present"] for x in results),
        "source_START_VPD_ERA_numeric_presence":sum(
            x["source_START_VPD_ERA_present"] for x in results),
        "any_natively_observed_tower_RH_verified":False,
        "actual_UTC_START_END_convention_verified":False,
        "any_science_release":False,
    }


def selftest():
    model=[]
    for i in range(7):
        case=REF_CASE if i==0 else "CH-Aws_FATES_TEST"+str(i)
        model.append({
            "cases":[case],"status":"DATM_INTERNAL_EVENT_READ",
            "index":9711,"DATM_time":"2007-07-22 07:30:00",
            "TBOT_K":282.399,"PSRF_Pa":79941.,
            "QBOT_kgkg":.003+i*.00001,
            "VPD_water_hPa":11.253246-i*.02,
            "RH_water_pct":40+i,
            "vapor_pressure_hPa":4+i*.02,
        })
    sample={
        "event_id":"E001","DATM_event_time":"2007-07-22 07:30:00",
        "DATM_halfhour_index":9711,"scientific_release":"HOLD",
        "source_QC_verified":False,"time_start_end_verified":False,
        "model_versions":model,
        "same_time_source_alternative_START":{
            "status":"SOURCE_CANDIDATE_UNVERIFIED_TIME_AND_QC",
            "raw_source_values":{"VPD_F":"11.247","VPD_F_QC":"1","TA_F":"9.249",
                                 "TA_F_QC":"0","PA_F":"79.941"}},
        "same_time_source_alternative_END":{
            "status":"SOURCE_CANDIDATE_UNVERIFIED_TIME_AND_QC",
            "raw_source_values":{"VPD_F":"10.344","VPD_F_QC":"1","TA_F":"7.52"}},
    }
    result=investigate_event(sample)
    assert abs(result["reference_abs_diff_START_VPD_F_hPa_IF_UNITS"]-.006246)<1e-8
    assert result["START_closer_than_END_IF_UNITS"]
    assert len(build_matrix(result))==7
    fake={"stage":STAGE_K,"read_only":True,"science_release":False,
          "FLUXMET_original_product_is_processed":True,
          "DATM_time_alignment_to_event_label_verified":True,
          "source_START_END_and_UTC_alignment_verified":False,
          "events":[dict(sample,event_id=f"E{i:03d}") for i in range(1,21)]}
    require_k(fake)
    summ=summarize([investigate_event(x) for x in require_k(fake)])
    assert summ["events"]==20 and summ["reference_within_0p01_hPa_START_count"]==20
    print("STAGE02L SELF-TEST PASS: decoded 20 Stage02K events, 7-model matrix, time alternatives and QC HOLD; no writes")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02k",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest()
        return
    if args.stage02k is None or not args.stage02k.is_file():
        ap.error("Need existing Stage02K event source JSON")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must be pre-existing and EMPTY")
    obj=json.loads(args.stage02k.read_text(encoding="utf-8"))
    original_events=require_k(obj)
    results=[investigate_event(e) for e in original_events]
    stats=summarize(results)
    rows=[row for event in results for row in build_matrix(event)]
    for e in results:
        print("EVENT",e["event_id"],e["event_time_DATM"],
              "REF_MINUS_START_ABS_HPA",
              round(e["reference_abs_diff_START_VPD_F_hPa_IF_UNITS"],6),
              "REF_MINUS_END_ABS_HPA",
              round(e["reference_abs_diff_END_VPD_F_hPa_IF_UNITS"],6),
              "START_VPD_QC",e["source_START_VPD_F_QC_raw"],
              "START_RH_PRESENT",e["source_START_RH_present"],
              "ERA_VPD_PRESENT",e["source_START_VPD_ERA_present"])
    print("SUMMARY",json.dumps(stats,sort_keys=True))
    output={
        "stage":"STAGE02L_CH_AWS_DATM_FLUXMET_TWO_CLOCK_SOURCE_EVIDENCE",
        "input_stage02k":str(args.stage02k),
        "read_only":True,"scientific_release":False,
        "original_forcing_modified":False,"slurm_submitted":False,
        "comparison_methods":"FLUXMET VPD_F hPa vs computed model VPD over water; conditional on metadata",
        "limitations":"Source product is processed; raw RH and ERA VPD are candidates, QC/time basis unverified; no forcing case selection",
        "BIFVARINFO_metadata_from_previous_stage":obj.get("BIFVARINFO_source_metadata"),
        "statistics":stats,"events":results,
    }
    jsonpath=args.out_dir/"stage02l_source_clock_QC_matrix.json"
    csvpath=args.out_dir/"stage02l_seven_models_twenty_events.csv"
    with jsonpath.open("x",encoding="utf-8") as h:
        json.dump(output,h,indent=2);h.write("\n")
    with csvpath.open("x",encoding="utf-8",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=CSV_FIELDS)
        writer.writeheader();writer.writerows(rows)
    print("REPORT",jsonpath)
    print("MATRIX",csvpath)
    print("SCIENCE_HOLD: ACTUAL TOWER OBSERVATION/QC, ERA SOURCE AND TIME CONVENTION UNVERIFIED")


if __name__=="__main__":
    main()
