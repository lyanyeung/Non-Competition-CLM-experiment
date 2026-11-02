#!/usr/bin/env python3
"""Batch04 Stage03H — six internal >5C jumps in IT-Tor's 1458-HH QC1/2 run.

Uses Stage03G exact completed HOLD result and Stage03B provenance. Streams
ONLY the original IT-Tor source plus already-selected Stage28 meteorology
to isolate the SIX Stage03G temperature-jump boundaries and +/- 2h context.
No new generic QC, ERA5 downloads, physics-based replacements or spin-up.

Source ERA columns are potentially not independent of ONEFlux fills. This
code prepares a decision-grade PRIVATE event ledger, not science approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

G_STAGE="STAGE03G_IT_TOR_TWO_ORIGINAL_QC12_RUNS_SOURCE_PHYSICS_AND_QC0_BOUNDARIES"
B_STAGE="STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE"
START=datetime(2025,10,21,2,30)
END=datetime(2025,11,20,11)
N_LONG=1458
JUMP_THRESHOLD_C=5.0
EXPECTED_JUMPS=6
PADDING=timedelta(hours=2)
SOURCE_REQUIRED={"TIMESTAMP_START","TA_F","VPD_F","TA_F_QC","VPD_F_QC"}
SOURCE_EXTRA={"TA_ERA","VPD_ERA","P_F","P_F_QC"}
SELECTED_REQUIRED={"time","TA_USE","VPD_USE","PSRF","QBOT"}
DETAIL_COLS=("jump_id","relative_HH","time","source_TA_F_C",
             "source_VPD_F_hPa","source_TA_F_QC","source_VPD_F_QC",
             "source_TA_ERA_C","source_VPD_ERA_hPa",
             "selected_TA_USE_C","selected_VPD_USE_hPa",
             "selected_PSRF_Pa","selected_QBOT_kgkg",
             "computed_RH_percent","source_P_F","source_P_F_QC")
 
def check(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def numeric(v):
    try:
        x=float(v)
        return x if math.isfinite(x) and x>-9990 else None
    except (ValueError,TypeError):return None

def timestamp(v,source):
    s=str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():s=s[:-2]
    try:
        p=datetime.strptime(s,"%Y%m%d%H%M") if source else datetime.fromisoformat(s)
        return p if p.tzinfo is None else None
    except ValueError:return None

def read_range(path,raw,required,extra,lo,hi):
    check(path.is_file() and not path.is_symlink(),"Original source/selected path absent")
    tkey="TIMESTAMP_START" if raw else "time"
    rows={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        d=csv.DictReader(f)
        fields=set(d.fieldnames or [])
        check(required<=fields,"Required original/selected columns missing: "+str(required-fields))
        keys=(required|extra)&fields-{tkey}
        for row in d:
            t=timestamp(row[tkey],raw)
            if t is None or t<lo or t>hi:continue
            check(t not in rows,"Duplicate source-label time within target "+str(t))
            rows[t]={k:numeric(row[k]) for k in keys}
    return rows,sorted(keys)

def discover_jumps(selected):
    times=[START+timedelta(minutes=30*i) for i in range(N_LONG)]
    check(times[-1]==END,"Run timing is not 1458 HH")
    check(set(times)==set(selected),"Selected run has gaps/extra time labels")
    jumps=[]
    for i in range(1,len(times)):
        l,r=times[i-1],times[i]
        lt,rt=selected[l]["TA_USE"],selected[r]["TA_USE"]
        check(lt is not None and rt is not None,"Missing Stage28 TA within pinned run")
        dv=rt-lt
        if abs(dv)>JUMP_THRESHOLD_C:
            jumps.append({"jump_id":f"TJ{i:04d}","previous":l,
                          "current":r,"delta_T_C":dv})
    return jumps

def verify_reports(g,b):
    check(g.get("stage")==G_STAGE and g.get("read_only") is True and
          g.get("science_release") is False and g.get("slurm_submitted") is False,
          "Original Stage03G science-HOLD report required")
    check(b.get("stage")==B_STAGE and b.get("read_only") is True and
          b.get("science_release") is False,"Original Stage03B source lineage required")
    run={x.get("id"):x for x in g.get("runs",[])}
    check(set(run)=={"LONG_1458","SHORT_29"},"Unexpected Stage03G two-run audit")
    check(run["LONG_1458"].get("start")==str(START) and
          run["LONG_1458"].get("end")==str(END) and
          run["LONG_1458"].get("half_hours")==N_LONG and
          run["LONG_1458"].get("physical_screen_counts",{}).get("inside_T_step_gt5C")==EXPECTED_JUMPS,
          "Stage03G expected six jumps are not present")
    check(not run["SHORT_29"].get("physical_screen_counts",{}).get("inside_T_step_gt5C",0),
          "Unexpected small-run >5C jump")
    row={r.get("site"):r for r in b.get("sites",[])}.get("IT-Tor")
    check(row is not None and row.get("stage28_met_SHA_verified") is True and
          row.get("all_current_paths_match_historical") is True,
          "Stage03B source lineage not confirmed")
    source=Path(g.get("source_csv_path",""))
    selected=Path(g.get("selected_stage28_path",""))
    check(source.is_absolute() and source.is_file() and not source.is_symlink(),
          "Original IT-Tor network product unavailable")
    check(selected.is_absolute() and selected.is_file() and not selected.is_symlink(),
          "Stage28 selected forcing unavailable")
    check(str(selected)==row.get("stage28_met_path") and
          sha(selected)==row.get("stage28_met_SHA_expected"),
          "Stage28 selected meteorology SHA mismatch")
    return source,selected

def rh_water(t,v):
    if t is None or v is None or not -90<t<80:return None
    es=6.112*math.exp(17.67*t/(t+243.5))
    return 100*(es-v)/es

def assess(selected,original,jumps):
    ledger=[];detail=[]
    for event in jumps:
        left,right=event["previous"],event["current"]
        check(left in original and right in original,"Missing original source at jump")
        lt,rt=selected[left],selected[right]
        ls,rs=original[left],original[right]
        left_v=lt.get("VPD_USE");right_v=rt.get("VPD_USE")
        dv=(right_v-left_v if left_v is not None and right_v is not None else None)
        source_t=[ls.get("TA_F"),rs.get("TA_F")]
        same_t=all(x is not None for x in source_t) and all(
            abs(x-t)<=1e-8 for x,t in zip(source_t,(lt["TA_USE"],rt["TA_USE"])))
        srcERA=[ls.get("TA_ERA"),rs.get("TA_ERA")]
        delta_ERA=(srcERA[1]-srcERA[0] if all(x is not None for x in srcERA) else None)
        delta_source=(source_t[1]-source_t[0] if all(x is not None for x in source_t) else None)
        note=("SOURCE_ERA_PRESENT_NOT_INDEPENDENT" if all(x is not None for x in srcERA)
              else "SOURCE_ERA_MISSING")
        item={"jump_id":event["jump_id"],"previous":left.isoformat(sep=" "),
              "current":right.isoformat(sep=" "),
              "selected_delta_T_C":event["delta_T_C"],
              "selected_delta_VPD_hPa":dv,
              "original_source_delta_T_C":delta_source,
              "source_ERA_delta_T_C":delta_ERA,
              "source_previous_TA_QC":ls.get("TA_F_QC"),
              "source_current_TA_QC":rs.get("TA_F_QC"),
              "source_previous_VPD_QC":ls.get("VPD_F_QC"),
              "source_current_VPD_QC":rs.get("VPD_F_QC"),
              "TA_QC_changed_at_jump":ls.get("TA_F_QC")!=rs.get("TA_F_QC"),
              "source_original_T_equals_Stage28_both_HH":same_t,
              "source_ERA_provenance":note,
              "previous_RH_water_pct":rh_water(lt["TA_USE"],left_v),
              "current_RH_water_pct":rh_water(rt["TA_USE"],right_v),
              "instrument_truth_verified":False,
              "numerical_or_physical_repair_approved":False,
              "science_gate":"HOLD"}
        ledger.append(item)
        center=right
        for j in range(-4,5):
            t=center+timedelta(minutes=30*j)
            check(t in selected and t in original,
                  "Missing +/-2-hour source context at "+str(t))
            a,b=original[t],selected[t]
            detail.append({
                "jump_id":event["jump_id"],"relative_HH":j,
                "time":t.isoformat(sep=" "),
                "source_TA_F_C":a.get("TA_F"),
                "source_VPD_F_hPa":a.get("VPD_F"),
                "source_TA_F_QC":a.get("TA_F_QC"),
                "source_VPD_F_QC":a.get("VPD_F_QC"),
                "source_TA_ERA_C":a.get("TA_ERA"),
                "source_VPD_ERA_hPa":a.get("VPD_ERA"),
                "selected_TA_USE_C":b.get("TA_USE"),
                "selected_VPD_USE_hPa":b.get("VPD_USE"),
                "selected_PSRF_Pa":b.get("PSRF"),
                "selected_QBOT_kgkg":b.get("QBOT"),
                "computed_RH_percent":rh_water(b.get("TA_USE"),b.get("VPD_USE")),
                "source_P_F":a.get("P_F"),
                "source_P_F_QC":a.get("P_F_QC"),
            })
    return ledger,detail

def self_test():
    # Test strict >5C, event is the second HH, QC transition and correct
    # 2-hour context; never rewrite or submit model data.
    saved_start=START
    times=[START+timedelta(minutes=30*i) for i in range(N_LONG)]
    synthetic={t:{"TA_USE":10.0,"VPD_USE":3.0,"PSRF":101325.0,"QBOT":0.005}
               for t in times}
    synthetic[times[3]]["TA_USE"]=16.1
    synthetic[times[4]]["TA_USE"]=10.0
    jumps=discover_jumps(synthetic)
    assert len(jumps)==2 and jumps[0]["current"]==times[3]
    ctx_times=[START+timedelta(minutes=30*i) for i in range(-5,N_LONG+5)]
    source={t:{"TA_F":synthetic[t]["TA_USE"] if t in synthetic else 10.0,
               "VPD_F":3.0,"TA_F_QC":1,"VPD_F_QC":1,"TA_ERA":10.0,
               "VPD_ERA":3.0} for t in ctx_times}
    for t in ctx_times:
        if t not in synthetic:
            synthetic[t]={"TA_USE":10.0,"VPD_USE":3.0,"PSRF":101325.0,"QBOT":0.005}
    records,contexts=assess(synthetic,source,jumps)
    assert len(records)==2 and len(contexts)==18
    assert all(x["science_gate"]=="HOLD" for x in records)
    assert records[0]["selected_delta_T_C"]>5
    assert rh_water(10.0,0)==100.0
    print("STAGE03H SELF-TEST PASS: 1458-HH run strict six-jump selection, 2h source-ERA context, QC transition, no replacement or writes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03g",type=Path)
    p.add_argument("--stage03b",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    check(a.stage03g is not None and a.stage03g.is_file() and
          a.stage03b is not None and a.stage03b.is_file(),
          "Original operator Stage03G and Stage03B private JSON required")
    check(a.out_dir is not None and a.out_dir.is_dir() and
          not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
          "Use NEW EMPTY private output directory")
    g=json.loads(a.stage03g.read_text(encoding="utf-8"))
    b=json.loads(a.stage03b.read_text(encoding="utf-8"))
    original_file,selected_file=verify_reports(g,b)
    # One selected-source streaming pass: exact 1458 HH plus +/-2h context.
    lo=START-PADDING
    hi=END+PADDING
    selected,keys=read_range(selected_file,False,SELECTED_REQUIRED,set(),lo,hi)
    inrun={t:r for t,r in selected.items() if START<=t<=END}
    jumps=discover_jumps(inrun)
    check(len(jumps)==EXPECTED_JUMPS,
          "Stage03G reported six >5C jumps, but Stage03H located "+str(len(jumps)))
    original,source_keys=read_range(
        original_file,True,SOURCE_REQUIRED,SOURCE_EXTRA,lo,hi)
    records,context=assess(selected,original,jumps)
    report={"stage":"STAGE03H_IT_TOR_SIX_QC12_INTERNAL_TEMPERATURE_JUMPS_SOURCE_FORENSICS",
            "read_only":True,"science_release":False,
            "slurm_submitted":False,"model_or_source_modified":False,
            "stage03g_source":str(a.stage03g),
            "stage03b_source":str(a.stage03b),
            "source_original":str(original_file),
            "source_selected":str(selected_file),
            "source_optional_present":source_keys,
            "source_selected_fields":keys,
            "run_start":str(START),"run_end":str(END),
            "temperature_jump_threshold_exclusive_C":JUMP_THRESHOLD_C,
            "jump_count":len(records),
            "jump_provenance":records,
            "scientific_notes":"Jump timestamps label the SECOND half-hour after each >5 C step. Original FLUXMET QC1/QC2 and source-packaged ERA are not independently verified sensor truth. RH from water saturation is derived, not observed or ice-corrected. No automatic edits, no jump artefact classification and no AD5 release."}
    j=a.out_dir/"stage03h_IT_Tor_6_internal_T_jumps_PRIVATE.json"
    c=a.out_dir/"stage03h_IT_Tor_6_jumps_2h_neighborhood_PRIVATE.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=DETAIL_COLS)
        w.writeheader();w.writerows(context)
    for x in records:
        print("JUMP",x["jump_id"],x["previous"],x["current"],
              "DT_C",x["selected_delta_T_C"],
              "DVPD_hPa",x["selected_delta_VPD_hPa"],
              "QC",x["source_previous_TA_QC"],"->",x["source_current_TA_QC"],
              "ERA_DT_C",x["source_ERA_delta_T_C"],
              "NATIVE_EQUALS_SELECTED",x["source_original_T_equals_Stage28_both_HH"])
    print("JUMPS",len(records), "CONTEXT_HALF_HOUR_ROWS",len(context),
          "ORIGINAL_QC_SCIENCE_HOLD True")
    print("PRIVATE_JSON",j)
    print("PRIVATE_CONTEXT",c)
    print("STAGE03H COMPLETE; NO MET REPAIR, NC/CIME/FATES/SLURM OR SCIENCE RELEASE")

if __name__=="__main__":
    main()
