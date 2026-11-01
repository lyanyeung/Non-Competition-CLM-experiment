#!/usr/bin/env python3
"""ICOS Batch04 Stage03C: REUSE old FLUXNET13 unresolved scientific event ledgers.

Requires Stage03B exact 4-site Stage28 MET + Stage30 DATM lineage PASS.
Extract ONLY selected inherited Stage22/28 MDS, precipitation, T/RH and
BIF/TA-height source-science risks to a new research HOLD action register.
This is NOT fresh full FLUXMET QC, not an independent source measurement
check and NOT a repair or model-ready forcing release.

Inputs are existing historical REPORTS, not native raw sensor arrays.
Never alter original source CSV, 74 DATM NC, Stage28, stage30, CIME, PFT,
shared FATES or Slurm. Writes only 3 reports in an EMPTY HOME directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments")
STAGE28=BASE/"FLUXNET_MultiSite_13_MET_stage28_20261018_052344_851367/reports"
STAGE22=BASE/"FLUXNET_MultiSite_13_stage22_retry_20261018_041156_893243/reports"
STAGE29=BASE/"FLUXNET_13_ZBOT_DATM_20261018_054150_1008203/reports"
STAGE_B="STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
YEARS={"DE-Gri":22,"DE-RuR":15,"IT-Tor":18,"ES-Agu":19}
PENDING={"NO_STAGE22_EDIT_STILL_PENDING",
         "STAGE22_PARTIAL_FLAGGED_BLOCK_STILL_PENDING"}
KEYS=("site","issue","source_stage","start_or_time","end","source_qc",
      "source_numeric_or_meta","legacy_decision","current_science_gate",
      "target_next_step")
FILE_LIMIT=12_000_000
ROW_LIMIT=50000
ISSUE_NOTES={
    "DE-Gri":"49 original Stage22 MDS flagged blocks; retain QC0 donors and full contiguous QC1 envelope",
    "DE-RuR":"2012-07-27 native rainfall/source QC and original dated TA-height/ZBOT epochs",
    "IT-Tor":"2025-10/11 historical 1458-HH QC1/QC2 fill/source transition; heavy rain; separate soil ORGANIC zero",
    "ES-Agu":"2018-09-15 rainfall source accumulation/time and inherited earlier Stage12/15 revisions",
}
EXPECTED_REPORTS={
    "stage28_science":("28","03_13site_science_risk_and_decisions.csv"),
    "stage28_mds":("28","08_DEGri_FILet_82_MDS_original_blocks_science_pending.csv"),
    "stage28_flags":("28","10_all13_remaining_temperature_pressure_rain_RH_flags.csv"),
    "stage28_rain7":("28","07_7site_heavy_rain_PROVENANCE_NO_EDITS.csv"),
    "stage28_edits":("28","04_exact_STAGE28_new_edits.csv"),
    "stage22_envelopes":("28","09_DEGri_FILet_stage22_whole_envelope_decisions.csv"),
    "stage22_block_native":("22","07_82_MDS_blocks_after_stage22.csv"),
    "stage22_rain_all13":("22","06_all_precip_gt18mm_source_timing_review.csv"),
    "stage29_zbot_yearly":("29","04_annual_ZBOT_height_and_backfill_QC.csv"),
    "stage29_bif_offgrid":("29","09_non_halfhour_BIF_events_audit.csv"),
}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def csv_records(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>FILE_LIMIT:
        return None
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        if not rd.fieldnames or len(rd.fieldnames)>180:
            raise ValueError("Unexpected historic report CSV schema "+str(path))
        vals=[]
        for i,r in enumerate(rd):
            if i>=ROW_LIMIT:raise ValueError("Historical ledger >50k rows "+str(path))
            vals.append(r)
    return vals

def verify_stage3b(data):
    if data.get("stage")!=STAGE_B or data.get("read_only") is not True or \
       data.get("science_release") is not False or \
       data.get("slurm_submitted") is not False:
        raise ValueError("Stage03B-REUSE original source HOLD report missing")
    reports=data.get("sites",[])
    if len(reports)!=4 or {r.get("site") for r in reports}!=set(SITES):
        raise ValueError("Need exact four sites from Stage03B-REUSE")
    by={r["site"]:r for r in reports}
    for s in SITES:
        r=by[s]
        if r.get("stage28_met_SHA_verified") is not True or \
           r.get("all_current_paths_match_historical") is not True or \
           r.get("representative_NC_SHA_pass") is not True or \
           r.get("expected_year_files")!=YEARS[s] or \
           r.get("historical_year_rows")!=YEARS[s] or \
           r.get("science_release") is not False:
            raise ValueError(s+" Stage28/30 provenance NOT completely matched")
    return by

def chosen(d,s):
    return [x for x in (d or []) if x.get("site")==s]

def source_detail(row):
    want=("start","end","time","original_flagged_halfhours",
          "rain_mm_per_HH","rain_mm","P_F","P_F_QC","source_P_F_mm",
          "source_P_F_QC","stage22_action","stage20_action",
          "stage21_action","TA_F_QC","VPD_F_QC","QC","height_m",
          "height_min_m","height_max_m","backfilled_halfhours",
          "rain_above18_mm_HH")
    return {k:row[k] for k in want if k in row and str(row[k]).strip()}

def make_issue(site,issue,origin,row,action,decision=None):
    t=row.get("start") or row.get("time") or row.get("TIMESTAMP_START") or ""
    e=row.get("end") or ""
    return {
        "site":site,"issue":issue,"source_stage":origin,
        "start_or_time":str(t),"end":str(e),
        "source_qc":str(row.get("source_P_F_QC") or row.get("P_F_QC") or
                        row.get("TA_F_QC") or row.get("VPD_F_QC") or ""),
        "source_numeric_or_meta":json.dumps(source_detail(row),ensure_ascii=False,sort_keys=True),
        "legacy_decision":str(decision or row.get("stage22_action") or
                              row.get("decision") or row.get("action") or "UNDECIDED"),
        "current_science_gate":"HOLD_NOT_NEW_OBSERVATIONAL_QC_PASS",
        "target_next_step":action,
    }

def main_audit(prior,roots):
    verify_stage3b(prior)
    paths={k:roots[origin]/name for k,(origin,name) in EXPECTED_REPORTS.items()}
    reports={k:csv_records(path) for k,path in paths.items()}
    if reports["stage28_science"] is None or reports["stage28_mds"] is None or \
       reports["stage22_block_native"] is None:
        raise ValueError("Required exact old Stage28 science/MDS and Stage22 original block reports missing")
    if len(reports["stage28_mds"])!=82 or len(reports["stage22_block_native"])!=82:
        raise ValueError("Old exact 82-block Stage22/28 ledger drifted")
    if {x["site"] for x in reports["stage28_science"]}!=set(
       ("DE-Lnf","DE-Obe","ES-Agu","ES-LJu","IT-Col","DE-Gri","DE-RuR",
        "FI-Hyy","FI-Let","FR-Pue","GF-Guy","IT-MBo","IT-Tor")):
        raise ValueError("Stage28 original 13-site scientific register changed")
    old_id={(r["site"],r["start"],r["end"]) for r in reports["stage22_block_native"]}
    newer_id={(r["site"],r["start"],r["end"]) for r in reports["stage28_mds"]}
    if old_id!=newer_id:raise ValueError("Stage22/28 MDS original block identities drift")
    pending=[x for x in reports["stage28_mds"]
             if x.get("stage22_action") in PENDING]
    if len(pending)!=69 or sum(x.get("site")=="DE-Gri" for x in pending)!=49:
        raise ValueError("Historical 69/49 original pending MDS science ledgers changed")
    selected=[]
    summary=[]
    for site in SITES:
        risk=chosen(reports["stage28_science"],site)
        if len(risk)!=1:raise ValueError(site+" original Stage28 science row ambiguous")
        mds=chosen(pending,site)
        for row in mds:
            selected.append(make_issue(
                site,"ORIGINAL_MDS_QC1_BLOCK_PENDING","Stage28/22",
                row,"Check whole QC1 interval, QC0 anchors, T/VPD/RH physics and approved ERA evidence"))
        rain_all=chosen(reports["stage22_rain_all13"],site)
        rain7=chosen(reports["stage28_rain7"],site)
        # Stage28 rain7 is seven-site only; do NOT infer zero events for other sites.
        for row in rain_all:
            selected.append(make_issue(
                site,"HISTORICAL_RAIN_GT18_SOURCE_REVIEW","Stage21→22",
                row,"Review original rain gauge P/P_F_QC, accumulation and local clock; DO NOT clip"))
        # Only append Stage28 rain7 if original all-13 rain ledger is unavailable.
        if reports["stage22_rain_all13"] is None:
            for row in rain7:
                selected.append(make_issue(
                    site,"PARTIAL_STAGE28_SEVEN_SITE_RAIN_SOURCE_REVIEW","Stage28-only-7-sites",
                    row,"Full 13-site rain ledger absent; find original 2012/2018 event provenance"))
        flags=chosen(reports["stage28_flags"],site)
        for row in flags:
            selected.append(make_issue(
                site,"STAGE28_REMAINING_MET_FLAG","Stage28",
                row,"Keep original source QC and episode context; independent evidence required"))
        height=chosen(reports["stage29_zbot_yearly"],site)
        nonhalf=chosen(reports["stage29_bif_offgrid"],site)
        if site=="DE-RuR":
            for row in nonhalf:
                selected.append(make_issue(
                    site,"BIF_TA_HEIGHT_OFFGRID_EPOCH","Stage29b",
                    row,"Check effective TA-height time against original BIF and DATM ZBOT"))
        must_dates={"DE-RuR":"2012-07-27","ES-Agu":"2018-09-15"}
        focus=must_dates.get(site)
        def contained(rows):
            return any(focus in str(row.get(k,"")) for row in (rows or [])
                       for k in ("time","start","TIMESTAMP_START","date")) if focus else None
        present=contained(rain_all) if rain_all else False
        if focus and not present:
            selected.append(make_issue(
                site,"LEGACY_RAIN_EVENT_NOT_RESOLVED_BY_ABOVE18_LEDGER",
                "Stage27 historical risk note",
                {"time":focus},
                "Review original site rain records and aggregation time; NOT a claim event absent",
                "SOURCE_PROVENANCE_PENDING"))
        if site=="IT-Tor":
            selected.append(make_issue(
                site,"ORIGINAL_QC1_QC2_1458HH_LONG_FILL","Stage27 historical science note",
                {"start":"2025-10","end":"2025-11","original_flagged_halfhours":"1458"},
                "Review entire original 1458-HH interval, both edges, source QC0 donors and era-family differences",
                "HISTORICAL_QC1_QC2_SOURCE_DISCONTINUITY_UNRESOLVED"))
        if site=="DE-RuR":
            selected.append(make_issue(
                site,"DYNAMIC_ZBOT_SOURCE_EPOCHS","Stage29b BIF",
                {"start":"2011","height_m":"initial 2.58"},
                "Protect dated original TA heights and early-backfill assumption; DO NOT flatten ZBOT",
                "DYNAMIC_EPOCH_REVIEW"))
        if site=="IT-Tor":
            selected.append(make_issue(
                site,"SOIL_ALL_TEN_ORGANIC_ZERO","Stage02U/V/02Y",
                {"time":"all 10 soil layers"},
                "Independent soil provenance; separate from meteorology; DO NOT change",
                "SOIL_SOURCE_HOLD"))
        if site=="ES-Agu":
            selected.append(make_issue(
                site,"HISTORICAL_STAGE12_STAGE15_MET_REPAIR_LINEAGE","FLUXNET13 historical",
                {"time":"legacy earlier-version repairs"},
                "Use Stage28 selected manifest; preserve earlier repairs; do NOT reset to original FLUXMET",
                "REPAIRS_INHERITED_NEEDS_EVENT_SOURCE_REVIEW"))
        if site=="DE-Gri":
            selected.append(make_issue(
                site,"HISTORICAL_STAGE20_11_HALF_HOUR_MODIFICATIONS","FLUXNET13 Stage20→28",
                {"time":"11 inherited variable/HH edits"},
                "Retain historical selected source SHA and operator decisions; no repeat generic v5",
                "KEEP_EXISTING_SELECTED_PARENT"))
        summary.append({
            "site":site,"Stage03B_source_SHA_PASS":True,
            "old_MDS_pending_original_blocks":len(mds),
            "old_Stage28_science_status":risk[0].get("scientific_status",""),
            "old_Stage28_action_class":risk[0].get("action_class",""),
            "old_Stage28_T_gt12":risk[0].get("T_step_gt12C",""),
            "old_Stage28_RH_lt1":risk[0].get("RH_lt1pct",""),
            "historical_all13_rain_ledger_found":reports["stage22_rain_all13"] is not None,
            "historical_rain_review_rows":len(rain_all),
            "rain_focus_date":focus or "",
            "rain_focus_found_in_gt18_ledger":present,
            "historical_stage28_remaining_flags":len(flags),
            "stage29b_ZBOT_annual_rows":len(height),
            "BIF_offgrid_events":len(nonhalf),
            "priority":ISSUE_NOTES[site],
            "source_observation_science_release":"HOLD",
        })
        print("SITE",site,"REUSED_STAGE28_SHA_PASS",
              "ORIGINAL_MDS_PENDING",len(mds),
              "OLD_RAIN_LEDGER",("PRESENT" if reports["stage22_rain_all13"] is not None else "MISSING"),
              "RAIN_REVIEW_ROWS",len(rain_all),
              "LEGACY_OTHER_FLAGS",len(flags),
              "BIF_YEAR_ROWS",len(height))
        print(" PRIORITY",ISSUE_NOTES[site])
    provenance={
        k:{"path":str(p),"present":reports[k] is not None,
           "sha256":sha(p) if reports[k] is not None else None,
           "rows":len(reports[k]) if reports[k] is not None else None}
        for k,p in paths.items()
    }
    return {
        "stage":"STAGE03C_BATCH04_REUSE_HISTORICAL_SCIENCE_HOLDS_AND_AMERIFLUX_DELTA_SCOPE",
        "read_only":True,"science_release":False,"source_CIME_NC_modified":False,
        "slurm_submitted":False,"old_13site_source_stage":"Stage28 selected; Stage22/26 inherited",
        "previous_reports":provenance,"sites":summary,
        "issues":selected,
        "interpretation":"Inherited science HOLD triage from historical reports; no new source-native half-hour QC evidence was generated, no previous human decision reversed. The separate 7-site Stage28 rain list cannot stand in for 13-site rain provenance. Scientific decisions and source/ERA validation remain to be done on these event scopes."
    }

def self_test():
    assert len(SITES)==4 and sum(YEARS.values())==74
    assert len(PENDING)==2 and "DE-Gri" in ISSUE_NOTES
    example=make_issue("DE-Gri","MDS","old",{"start":"2010-01-01","end":"2010-01-02",
                "stage22_action":"NO_STAGE22_EDIT_STILL_PENDING"},
                "review")
    assert example["start_or_time"]=="2010-01-01"
    assert example["current_science_gate"].startswith("HOLD")
    print("STAGE03C-REUSE SELF-TEST PASS: old 69/49 MDS protected HOLD, rain-source and BIF episode staging; NO WRITES")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03b",type=Path)
    p.add_argument("--stage28",type=Path,default=STAGE28)
    p.add_argument("--stage22",type=Path,default=STAGE22)
    p.add_argument("--stage29b",type=Path,default=STAGE29)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    if not a.stage03b or not a.stage03b.is_file():
        p.error("Original successful Stage03B-REUSE JSON required")
    if not a.out_dir or not a.out_dir.is_dir() or \
       a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        p.error("Use a NEW existing EMPTY directory")
    prior=json.loads(a.stage03b.read_text(encoding="utf-8"))
    result=main_audit(prior,{"28":a.stage28,"22":a.stage22,"29":a.stage29b})
    result["source_stage03b"]=str(a.stage03b)
    out=a.out_dir
    jsonpath=out/"stage03c_four_site_inherited_science_HOLD_episode_index.json"
    summary=out/"stage03c_four_site_QC_incremental_scope.csv"
    issues=out/"stage03c_four_site_original_source_event_HOLD.csv"
    with jsonpath.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    with summary.open("x",encoding="utf-8",newline="") as f:
        fieldnames=list(result["sites"][0])
        w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader()
        w.writerows(result["sites"])
    with issues.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=KEYS);w.writeheader()
        w.writerows(result["issues"])
    print("REUSED_OLD_13SITE_SCIENCE_LEDGER",len(result["issues"]),"HOLD_ACTION_ROWS")
    print("JSON",jsonpath)
    print("SUMMARY_CSV",summary)
    print("EVENT_CSV",issues)
    print("FINAL STAGE03C HISTORICAL SCIENCE HOLD; NO NUMERIC REPAIR/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
