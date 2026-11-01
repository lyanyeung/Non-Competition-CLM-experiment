#!/usr/bin/env python3
"""ICOS Batch04 Stage03E — summarize the already completed Stage03D private JSON.

No rereading FLUXMET_HH or historical Stage28 CSV, no new QC or model input
processing. Only aggregate event and source/Stage28 evidence already captured
by Stage03D, retaining all native meteorology and soil science HOLDs.

Private numeric per-HH source and processed rainfall comparisons are written
ONLY inside an explicitly empty private HOME directory, never public GitHub.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

EXPECTED="STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
EXPECTED_RAIN={"DE-Gri":12,"DE-RuR":1,"IT-Tor":2,"ES-Agu":5}
EXPECTED_WINDOWS={"DE-Gri":49,"DE-RuR":1,"IT-Tor":1,"ES-Agu":1}
RAIN_FIELDS=("site","focus_date","time","source_P_F_mm","source_P_F_QC",
             "candidate_PRECT_mm_per_30min","same_numeric_amount_only",
             "source_accumulation_time_science_verified")
MDS_FIELDS=("site","episode","window_start","window_end","context_source_HH",
            "target_source_HH","Stage28_target_HH","TA_QC0_context",
            "TA_QC1_context","TA_QC2_context","VPD_QC0_context",
            "VPD_QC1_context","VPD_QC2_context",
            "QC1_or_QC2_context_count_for_priority_only",
            "source_TA_F_range_C","selected_TA_USE_range_C",
            "source_VPD_F_range_hPa","selected_VPD_USE_range_hPa",
            "science_release")

def validate(d):
    if d.get("stage")!=EXPECTED or d.get("read_only") is not True or \
       d.get("science_release") is not False or \
       d.get("slurm_submitted") is not False:
        raise ValueError("Not original completed Stage03D science HOLD report")
    sites=d.get("sites")
    if not isinstance(sites,list) or [r.get("site") for r in sites]!=list(SITES):
        raise ValueError("Expected exact ordered 4 Stage03D site results")
    events=d.get("target_event_context")
    if not isinstance(events,list) or len(events)!=52:
        raise ValueError("Expected 49 MDS + 3 explicitly scoped target windows")
    counts=Counter(r.get("site") for r in events)
    if counts!=Counter(EXPECTED_WINDOWS):
        raise ValueError("Stage03D original event scope changed")
    old=d.get("four_site_old_rain_rows")
    if not isinstance(old,list) or len(old)!=20 or \
       Counter(r.get("site") for r in old)!=Counter(EXPECTED_RAIN):
        raise ValueError("Stage21 original 20 event source ledger unexpectedly changed")
    sites_by={r["site"]:r for r in sites}
    for site in SITES:
        row=sites_by[site]
        if row.get("target_episodes")!=EXPECTED_WINDOWS[site] or \
           row.get("target_episodes_with_both_source_and_selected_records")!=EXPECTED_WINDOWS[site] or \
           row.get("old_rain_provenance_rows")!=EXPECTED_RAIN[site] or \
           row.get("model_run_release") is not False:
            raise ValueError(site+" original Stage03D source/selected evidence not all present")
    for event in events:
        if event.get("observational_science_release") is not False or \
           event.get("original_HH_rows_in_window",0)<=0 or \
           event.get("Stage28_HH_rows_in_window",0)<=0:
            raise ValueError("Source event missing or illegally science-approved: "+str(event.get("episode")))
    return sites_by,events,old

def qc(row,field,code):
    return int(row.get("original_QC_categories",{}).get(f"{field}_QC:{code}",0))

def mds_summary(event):
    a=qc(event,"TA_F",0); b=qc(event,"TA_F",1); c=qc(event,"TA_F",2)
    v0=qc(event,"VPD_F",0);v1=qc(event,"VPD_F",1);v2=qc(event,"VPD_F",2)
    s=event.get("original_source_ranges") or {}
    n=event.get("selected_Stage28_ranges") or {}
    return {
      "site":"DE-Gri","episode":event["episode"],
      "window_start":event["window_start"],"window_end":event["window_end"],
      "context_source_HH":event["original_HH_rows_in_window"],
      "target_source_HH":event.get("focus_target_rows_source"),
      "Stage28_target_HH":event.get("focus_target_rows_Stage28"),
      "TA_QC0_context":a,"TA_QC1_context":b,"TA_QC2_context":c,
      "VPD_QC0_context":v0,"VPD_QC1_context":v1,"VPD_QC2_context":v2,
      "QC1_or_QC2_context_count_for_priority_only":b+c+v1+v2,
      "source_TA_F_range_C":json.dumps(s.get("TA_F")),
      "selected_TA_USE_range_C":json.dumps(n.get("TA_USE")),
      "source_VPD_F_range_hPa":json.dumps(s.get("VPD_F")),
      "selected_VPD_USE_range_hPa":json.dumps(n.get("VPD_USE")),
      "science_release":"HOLD"
    }

def summarize(d):
    sites,events,old=validate(d)
    byevent={s:[e for e in events if e["site"]==s] for s in SITES}
    rainout=[]
    per_site=[]
    for site in SITES:
        row=sites[site]
        target=byevent[site]
        focus_date=row["explicit_focus_date"]
        if site in ("DE-Gri","IT-Tor"):
            if focus_date is not None or any(x.get("paired_rain_focus_HH") for x in target):
                raise ValueError(site+" wrongly assigned a focus rainfall date")
        else:
            if focus_date not in ("2012-07-27","2018-09-15"):
                raise ValueError(site+" rain focus date unexpectedly changed")
            for pair in target[0].get("paired_rain_focus_HH",[]):
                if not str(pair.get("time","")).startswith(focus_date):
                    raise ValueError(site+" paired event outside designated rain day")
                rainout.append({
                  "site":site,"focus_date":focus_date,"time":pair.get("time"),
                  "source_P_F_mm":pair.get("source_P_F_mm"),
                  "source_P_F_QC":pair.get("source_P_F_QC"),
                  "candidate_PRECT_mm_per_30min":pair.get("candidate_PRECT_mm_per_30min"),
                  "same_numeric_amount_only":pair.get("same_numeric_amount_only"),
                  "source_accumulation_time_science_verified":False,
                })
        evidence=[x for x in old if x["site"]==site]
        day_old=[x for x in evidence if focus_date and focus_date in str(x.get("time") or "")]
        event_info={
          "site":site,"old_gt18mm_30min_rain_event_candidates":len(evidence),
          "focus_date":focus_date,
          "old_gt18mm_30min_candidates_on_focus_date":len(day_old),
          "target_episode_count":len(target),
          "event_scope_source_selected_present":True,
          "source_QC0_sensor_verified":False,
          "time_and_accumulation_verified":False,
          "new_numeric_data_changes":0,
          "science_gate":"HOLD"
        }
        if site=="IT-Tor":
            e=target[0]
            q=e.get("original_QC_categories",{})
            expected={
              "TA_F_QC:0":1441,"TA_F_QC:1":587,"TA_F_QC:2":900,
              "VPD_F_QC:0":1441,"VPD_F_QC:1":587,"VPD_F_QC:2":900,
              "P_F_QC:0":1440,"P_F_QC:2":1488
            }
            if any(int(q.get(k,-1))!=v for k,v in expected.items()):
                raise ValueError("IT-Tor reported Oct-Nov QC counts changed")
            event_info["2025_Oct_Nov_HH_count"]=e["original_HH_rows_in_window"]
            event_info["TA_VPD_QC0_HH"]=1441
            event_info["TA_VPD_QC1_HH"]=587
            event_info["TA_VPD_QC2_HH"]=900
            event_info["P_F_QC0_HH"]=1440
            event_info["P_F_QC2_HH"]=1488
            event_info["old_1458_HH_exact_interval_located"]=False
            event_info["soil_10layer_organic_zero_source_verified"]=False
        if site=="DE-Gri":
            event_info["original_MDS_science_HOLD_blocks"]=len(target)
        per_site.append(event_info)
    mds=sorted(
      [mds_summary(e) for e in byevent["DE-Gri"]],
      key=lambda x:(-x["QC1_or_QC2_context_count_for_priority_only"],x["window_start"])
    )
    for site in ("DE-RuR","ES-Agu"):
        vals=[r for r in rainout if r["site"]==site]
        valid=[r for r in vals if r["source_P_F_mm"] is not None and
                 r["candidate_PRECT_mm_per_30min"] is not None]
        matches=sum(r["same_numeric_amount_only"] is True for r in valid)
        print("RAIN_DATE",site,"PAIRED_HH",len(vals),
              "BOTH_NUMERIC",len(valid),"NUMERIC_EQUALS",matches,
              "DIFFER",len(valid)-matches,
              "ACCUMULATION_CLOCK_QC","HOLD")
    print("DE-Gri","49 original MDS science-HOLD episodes, source QC context ranked; NO repair")
    print("IT-Tor","2025 Oct-Nov: TA/VPD QC0=1441 QC1=587 QC2=900; P_F QC0=1440 QC2=1488; exact 1458-HH original interval NOT reconstructed")
    return {"stage":"STAGE03E_PRIVATE_SUMMARIZE_STAGE03D_SELECTED_EVIDENCE",
            "read_only":True,"science_release":False,
            "source_stage03d":"OPERATOR_PROVIDED_SAVED_STAGE03D_JSON",
            "source_or_CIME_written":False,"model_submitted":False,
            "sites":per_site,"rain_focus_halfhour_rows":rainout,
            "DE_Gri_49_MDS_episodes_ranked":mds,
            "interpretation":"Only prior Stage03D private source/Stage28 event context summarized. No new source QC pass, time zone, ERA independence, gauge accumulation validation, physical repair or AD5 approval. QC counts for DE-Gri include +/-2-hour window padding. Do not confuse IT-Tor 2928-HH Oct-Nov interval with historical exact 1458-HH source discontinuity."}

def self_test():
    # Minimal four-site synthetic Stage03D schema exercises no-focus dates,
    # rain comparisons and the exact 49-block branch.
    e=[]
    for i in range(49):
        e.append({"site":"DE-Gri","episode":f"mds{i}","window_start":f"2020-01-{i%28+1:02d}",
                  "window_end":"2020-02-01","original_HH_rows_in_window":2,
                  "Stage28_HH_rows_in_window":2,"observational_science_release":False,
                  "original_QC_categories":{"TA_F_QC:1":2,"VPD_F_QC:1":2}})
    for site in SITES[1:]:
        x={"site":site,"episode":site,"original_HH_rows_in_window":2928 if site=="IT-Tor" else 48,
           "Stage28_HH_rows_in_window":2928 if site=="IT-Tor" else 48,
           "observational_science_release":False}
        if site=="IT-Tor":
            x["original_QC_categories"]={
              "TA_F_QC:0":1441,"TA_F_QC:1":587,"TA_F_QC:2":900,
              "VPD_F_QC:0":1441,"VPD_F_QC:1":587,"VPD_F_QC:2":900,
              "P_F_QC:0":1440,"P_F_QC:2":1488}
        if site=="DE-RuR":x["paired_rain_focus_HH"]=[
            {"time":"2012-07-27 12:00:00","source_P_F_mm":19.5,
             "candidate_PRECT_mm_per_30min":19.5,"same_numeric_amount_only":True}]
        if site=="ES-Agu":x["paired_rain_focus_HH"]=[
            {"time":"2018-09-15 12:00:00","source_P_F_mm":20.0,
             "candidate_PRECT_mm_per_30min":21.0,"same_numeric_amount_only":False}]
        e.append(x)
    test={"stage":EXPECTED,"read_only":True,"science_release":False,"slurm_submitted":False,
          "sites":[{"site":site,"target_episodes":EXPECTED_WINDOWS[site],
                    "target_episodes_with_both_source_and_selected_records":EXPECTED_WINDOWS[site],
                    "old_rain_provenance_rows":EXPECTED_RAIN[site],
                    "model_run_release":False,
                    "explicit_focus_date":{"DE-RuR":"2012-07-27","ES-Agu":"2018-09-15"}.get(site)}
                  for site in SITES],
          "target_event_context":e,
          "four_site_old_rain_rows":[{"site":site,"time":"2012-07-27" if site=="DE-RuR" else "2018-09-15"}
                for site,count in EXPECTED_RAIN.items() for _ in range(count)]}
    result=summarize(test)
    assert len(result["DE_Gri_49_MDS_episodes_ranked"])==49
    assert len(result["rain_focus_halfhour_rows"])==2
    assert all(x["science_gate"]=="HOLD" for x in result["sites"])
    print("STAGE03E SELF-TEST PASS: 52 original windows, all four site branches, 20 historic rain events, private outputs; NO SOURCE WRITES")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage03d",type=Path)
    ap.add_argument("--out-dir",type=Path)
    x=ap.parse_args()
    if x.self_test:self_test();return
    if x.stage03d is None or not x.stage03d.is_file():
        ap.error("Original saved Stage03D private JSON required")
    if x.out_dir is None or not x.out_dir.is_dir() or \
       x.out_dir.is_symlink() or any(x.out_dir.iterdir()):
        ap.error("--out-dir must be EXISTING, EMPTY and private")
    d=json.loads(x.stage03d.read_text(encoding="utf-8"))
    report=summarize(d)
    report["source_stage03d"]=str(x.stage03d)
    j=x.out_dir/"stage03e_4site_private_event_science_HOLD_summary.json"
    rain=x.out_dir/"stage03e_DE-RuR_ES-Agu_focus_rain_HH_PRIVATE.csv"
    mds=x.out_dir/"stage03e_DE-Gri_49_source_MDS_prioritized_PRIVATE.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump({k:v for k,v in report.items()
                   if k not in ("rain_focus_halfhour_rows","DE_Gri_49_MDS_episodes_ranked")},
                  f,indent=2,ensure_ascii=False);f.write("\n")
    with rain.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=RAIN_FIELDS);writer.writeheader()
        writer.writerows(report["rain_focus_halfhour_rows"])
    with mds.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=MDS_FIELDS);writer.writeheader()
        writer.writerows(report["DE_Gri_49_MDS_episodes_ranked"])
    print("SUMMARY_PRIVATE",j)
    print("RAIN_48HH_PRIVATE",rain)
    print("DEGri_49_MDS_PRIVATE",mds)
    print("STAGE03E PASSED: 4 original station source windows summarized; ALL SCIENCE HOLDS RETAINED; NO FORCING/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
