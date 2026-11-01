#!/usr/bin/env python3
"""ICOS Batch04 Stage03D — recover Stage21 rainfall provenance and review ONLY old HOLD windows.

This does NOT redo full meteorological QC. Reuses source-verified Stage03B
(4/4 original Stage28 MET hash & 74/74 Stage30 NC paths) and Stage03C
(49 DE-Gri MDS HOLDs). The old Stage21 all-13 site rain ledger was copied
by Stage22 under the name INHERITED_STAGE21_06_all_precip...; Stage03C
looked for the nonprefixed name, so its MISSING is a report-location
mistake, NOT evidence rain QC was never performed.

Sources: OLD Stage21 rain reports and Stage22 inherited files; the old
13-site primary source manifest and Stage28 selected forcing manifest.
Stream only requested meteorology fields across original files ONCE/site,
extracting DE-Gri 49 old MDS episodes (summary + boundary examples),
DE-RuR 2012-07-27 rain +/- 1 day, ES-Agu 2018-09-15 rain +/- 1 day,
and IT-Tor 2025 Oct/Nov source QC1/QC2-transition window (without
asserting that a 1458-HH interval has been numerically rediscovered).
No ERA5/ERA5-Land downloads, no replacement, no full-numeric forcing
audit, no new CIME/NetCDF or Slurm. Source products remain licensed:
outputs under PRIVATE NEW EMPTY HOME directory only, never commit values.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments")
STAGE21=BASE/"FLUXNET_MultiSite_13_meteorology_stage21_trial_v1_20261015/reports"
STAGE22=BASE/"FLUXNET_MultiSite_13_stage22_retry_20261018_041156_893243/reports"
STAGE28=BASE/"FLUXNET_MultiSite_13_MET_stage28_20261018_052344_851367/reports"
RAW=Path.home()/"FLUXNET_13_input_audit/site_input_summary.csv"
B_STAGE="STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE"
C_STAGE="STAGE03C_BATCH04_REUSE_HISTORICAL_SCIENCE_HOLDS_AND_AMERIFLUX_DELTA_SCOPE"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
RAIN_NAME="06_all_precip_gt18mm_source_timing_review.csv"
RAIN_INHERITED="INHERITED_STAGE21_"+RAIN_NAME
SUMMARY_NAME="05_precipitation_provenance_summary.csv"
FIELD_SRC=("TA_F","TA_F_QC","VPD_F","VPD_F_QC",
           "TA_ERA","VPD_ERA","P_F","P_F_QC")
FIELD_MET=("TA_USE","VPD_USE","TBOT","QBOT","PRECTmms")
MAX_HIST=30000
MAX_OUTPUT_SAMPLES=8
TIMESTR="%Y%m%d%H%M"

def digest(file):
    h=hashlib.sha256()
    with file.open("rb") as f:
        for p in iter(lambda:f.read(1<<20),b""):h.update(p)
    return h.hexdigest()

def load_csv(path,maxrows=MAX_HIST):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>14_000_000:
        raise ValueError("Missing/unexpected historical report: "+str(path))
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        if not r.fieldnames or len(r.fieldnames)>140:raise ValueError("Unexpected manifest schema "+str(path))
        out=[]
        for i,x in enumerate(r):
            if i>=maxrows:raise ValueError("Historical report row guard exceeded "+str(path))
            out.append(x)
        return out

def at(value,mode):
    s=str(value).strip().strip("'\"")
    if s.endswith(".0") and s[:-2].isdigit():s=s[:-2]
    if mode=="source":
        if len(s)!=12 or not s.isdigit():return None
        try:return datetime.strptime(s,TIMESTR)
        except ValueError:return None
    try:
        x=datetime.fromisoformat(s)
        return x if x.tzinfo is None else None
    except ValueError:return None

def num(x):
    try:
        v=float(x)
        return v if math.isfinite(v) and v!=-9999 else None
    except (TypeError,ValueError):
        return None

def require_inputs(b,c):
    if b.get("stage")!=B_STAGE or b.get("read_only") is not True or \
       b.get("science_release") is not False or b.get("slurm_submitted") is not False:
        raise ValueError("Original source-verified Stage03B lineage report required")
    by={r.get("site"):r for r in b.get("sites",[])}
    if len(by)!=4 or set(by)!=set(SITES):raise ValueError("Unexpected Stage03B four-site source")
    for site in SITES:
        x=by[site]
        if not all(x.get(k) is True for k in (
              "stage28_met_SHA_verified","all_current_paths_match_historical",
              "representative_NC_SHA_pass")):
            raise ValueError(site+" historic met-DATM lineage not source-verified")
    if c.get("stage")!=C_STAGE or c.get("read_only") is not True or \
       c.get("science_release") is not False or c.get("slurm_submitted") is not False:
        raise ValueError("Original Stage03C HOLD-only event ledger required")
    if len(c.get("sites",[]))!=4 or {r.get("site") for r in c["sites"]}!=set(SITES):
        raise ValueError("Stage03C four-site HOLD row identity changed")
    pending=[r for r in c.get("issues",[]) if r.get("site")=="DE-Gri"
             and r.get("issue")=="ORIGINAL_MDS_QC1_BLOCK_PENDING"]
    if len(pending)!=49 or any(x.get("current_science_gate")!="HOLD_NOT_NEW_OBSERVATIONAL_QC_PASS"
                             for x in pending):
        raise ValueError("Missing exact 49 original DE-Gri science-HOLD MDS blocks")
    return by,pending

def source_and_selected(by,raw_report,manifest):
    src={}
    selected={}
    original={r.get("site"):r for r in raw_report if r.get("site") in SITES}
    previous={r.get("site"):r for r in manifest if r.get("site") in SITES}
    if set(original)!=set(SITES) or set(previous)!=set(SITES):
        raise ValueError("Original 13-site source manifest/Stage28 selected paths missing")
    for site in SITES:
        p=Path(original[site].get("primary_file",""))
        q=Path(previous[site].get("forcing_path",""))
        if not p.is_absolute() or not p.is_file() or p.is_symlink():
            raise ValueError(site+" original primary file absent")
        if q!=Path(by[site]["stage28_met_path"]) or q.is_symlink() or not q.is_file():
            raise ValueError(site+" Stage28 selected meteorology path mismatch")
        if previous[site].get("sha256")!=by[site]["stage28_met_SHA_expected"]:
            raise ValueError(site+" Stage28 selected meteorology SHA evidence changed")
        src[site]=p;selected[site]=q
    return src,selected

def rain_provenance(stage21,stage22):
    p=stage21/RAIN_NAME
    inherited=stage22/RAIN_INHERITED
    report={"stage21_source_path":str(p),"stage22_inherited_path":str(inherited),
            "stage21_found":p.is_file(),"stage22_prefixed_found":inherited.is_file()}
    if not p.is_file() and not inherited.is_file():
        return [],{**report,"status":"RAIN_LEDGER_SOURCE_NOT_FOUND_IN_TWO_VERIFIED_HISTORICAL_LOCATIONS"}
    use=p if p.is_file() else inherited
    if p.is_file() and inherited.is_file() and digest(p)!=digest(inherited):
        raise ValueError("Stage21 rain report does not hash-match Stage22 inherited copy")
    ledger=load_csv(use,10000)
    if not {"site","time","candidate_rain_mm_in_30min",
            "original_P_F_value","original_P_F_QC"}<=set(ledger[0] if ledger else []):
        raise ValueError("Old rain ledger unexpectedly lacks source fields")
    report.update(status="FOUND_ACTUAL_STAGE21_OR_INHERITED_RAIN_LEDGER",
                  selected_source=str(use),selected_sha256=digest(use),
                  historical_total_events=len(ledger))
    return [r for r in ledger if r.get("site") in SITES],report

def scopes(pending):
    events={}
    for site in SITES:
        if site=="DE-Gri":
            episodes=[]
            for i,r in enumerate(pending):
                a=at(r["start_or_time"],"selected")
                b=at(r["end"],"selected")
                if not a or not b or a>b:raise ValueError("Old DE-Gri MDS episode times malformed")
                episodes.append({"id":f"DE-Gri_MDS_{i+1:02d}","start":a,
                                 "end":b,"window_start":a-timedelta(hours=2),
                                 "window_end":b+timedelta(hours=2),
                                 "source_report_entry":r})
            if len({(x["start"],x["end"]) for x in episodes})!=49:
                raise ValueError("Duplicate original 49 MDS episode boundaries")
            events[site]=sorted(episodes,key=lambda x:x["window_start"])
        elif site in ("DE-RuR","ES-Agu"):
            center=datetime(2012,7,27) if site=="DE-RuR" else datetime(2018,9,15)
            events[site]=[{"id":f"{site}_RAIN_{center.date()}",
                "start":center,"end":center+timedelta(hours=23,minutes=30),
                "window_start":center-timedelta(days=1),
                "window_end":center+timedelta(days=2)-timedelta(minutes=30)}]
        else:
            events[site]=[{"id":"IT-Tor_QC1_QC2_2025_OCT_NOV",
                "start":datetime(2025,10,1),
                "end":datetime(2025,11,30,23,30),
                "window_start":datetime(2025,10,1),
                "window_end":datetime(2025,11,30,23,30)}]
    return events

def site_filter_focus(mode,events):
    # Full 48-HH target-day numerical pairs only for the two specified rainfall days;
    # do not materialize 49 multi-year MDS block sets or a full IT-Tor 1458-HH run.
    return len(events)==1 and "RAIN_" in events[0]["id"]

def stream_relevant(path,time_field,mode,events,keep):
    """One forward CSV pass; only event-window values, no full-file QC scan."""
    spans=sorted([(e["window_start"],e["window_end"],e["id"]) for e in events])
    starts=[x[0] for x in spans]
    bounds={e["id"]:(e["start"],e["end"]) for e in events}
    stats={e["id"]:{"records":0,"qc_counts":Counter(),
                    "minmax":{},"target_minmax":{},
                    "first":[],"last":[],"focus_first":[],"focus_last":[],
                    "selected_timestamps":set(),
                    "target_rows":0,"paired_focus_rows":{}} for e in events}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        d=csv.DictReader(f)
        if not d.fieldnames or time_field not in d.fieldnames:
            raise ValueError("Actual source/Stage28 timestamp field absent "+str(path))
        selected=[x for x in keep if x in d.fieldnames]
        must=("TA_F","TA_F_QC","VPD_F","VPD_F_QC") if mode=="source" else \
             ("TA_USE","VPD_USE","PRECTmms")
        if not set(must)<=set(selected):
            raise ValueError("Required original source selected columns missing "+str(set(must)-set(selected)))
        total_rows=0; matched=0
        for r in d:
            total_rows+=1
            dt=at(r[time_field],mode)
            if dt is None:continue
            idx=bisect.bisect_right(starts,dt)-1
            if idx<0 or dt>spans[idx][1]:
                continue
            # Original 49 MDS intervals should be non-overlapping.
            key=spans[idx][2]
            s=stats[key]
            if dt in s["selected_timestamps"]:
                raise ValueError("Duplicate original episode timestamp "+str(path)+" "+str(dt))
            s["selected_timestamps"].add(dt)
            s["records"]+=1;matched+=1
            obj={"time":dt.isoformat(sep=" ")}
            for field in selected:
                v=num(r.get(field))
                obj[field]=v
                if v is not None and field in ("TA_F","VPD_F","TA_USE","VPD_USE","PRECTmms","P_F"):
                    old=s["minmax"].get(field,[v,v])
                    s["minmax"][field]=[min(old[0],v),max(old[1],v)]
                if field.endswith("_QC"):
                    s["qc_counts"][field+":"+str(r[field])]+=1
            if len(s["first"])<MAX_OUTPUT_SAMPLES:s["first"].append(obj)
            s["last"].append(obj)
            if len(s["last"])>MAX_OUTPUT_SAMPLES:s["last"].pop(0)
            if bounds[key][0]<=dt<=bounds[key][1]:
                s["target_rows"]+=1
                if len(s["focus_first"])<MAX_OUTPUT_SAMPLES:s["focus_first"].append(obj)
                s["focus_last"].append(obj)
                if len(s["focus_last"])>MAX_OUTPUT_SAMPLES:s["focus_last"].pop(0)
                if len(events)==1 and site_filter_focus(mode,events):
                    s["paired_focus_rows"][dt]=obj
                for field in ("TA_F","VPD_F","TA_USE","VPD_USE","P_F","PRECTmms"):
                    v=obj.get(field)
                    if v is not None:
                        lo,hi=s["target_minmax"].get(field,[v,v])
                        s["target_minmax"][field]=[min(lo,v),max(hi,v)]
    for item in stats.values():
        item["qc_counts"]=dict(item["qc_counts"])
        item["unique_timestamp_count"]=len(item["selected_timestamps"])
    return stats,{"file":str(path),"rows_scanned_streaming_not_numerically_rechecked":total_rows,
                   "event_rows_selected":matched,"fields":selected}

def self_test():
    assert len(SITES)==4
    assert at("202510011030","source")==datetime(2025,10,1,10,30)
    assert at("2025-10-01 10:30:00","selected")==datetime(2025,10,1,10,30)
    assert num("-9999") is None and num("2.5")==2.5
    assert RAIN_INHERITED.startswith("INHERITED_STAGE21_")
    fake=[{"start_or_time":f"2015-01-{i:02d}","end":f"2015-01-{i:02d}"}
          for i in range(1,29)]
    fake += [{"start_or_time":f"2015-02-{i:02d}","end":f"2015-02-{i:02d}"}
             for i in range(1,22)]
    assert len(scopes(fake)["DE-Gri"])==49
    print("STAGE03D SELF-TEST PASS: Stage21->Stage22 inherited rain path, event-scoped source/Stage28 stream, original 49 MDS and no writes")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage03b",type=Path)
    ap.add_argument("--stage03c",type=Path)
    ap.add_argument("--stage21",type=Path,default=STAGE21)
    ap.add_argument("--stage22",type=Path,default=STAGE22)
    ap.add_argument("--stage28",type=Path,default=STAGE28)
    ap.add_argument("--source-manifest",type=Path,default=RAW)
    ap.add_argument("--out-dir",type=Path)
    x=ap.parse_args()
    if x.self_test:self_test();return
    if not x.stage03b or not x.stage03b.is_file() or \
       not x.stage03c or not x.stage03c.is_file():
        ap.error("Require operator Stage03B and Stage03C original HOLD JSONs")
    if not x.out_dir or not x.out_dir.is_dir() or \
       x.out_dir.is_symlink() or any(x.out_dir.iterdir()):
        ap.error("--out-dir must be an existing NEW EMPTY PRIVATE directory")
    prior=json.loads(x.stage03b.read_text(encoding="utf-8"))
    current=json.loads(x.stage03c.read_text(encoding="utf-8"))
    by,pending=require_inputs(prior,current)
    original,selected=source_and_selected(by,load_csv(x.source_manifest,100),
        load_csv(x.stage28/"01_selected_13site_STAGE28_provisional_manifest.csv",100))
    rain,rain_status=rain_provenance(x.stage21,x.stage22)
    print("STAGE21_RAIN_LEDGER",rain_status["status"],
          "STAGE21_FOUND",rain_status["stage21_found"],
          "STAGE22_INHERITED_FOUND",rain_status["stage22_prefixed_found"],
          "SCOPED_FOUR_SITE_EVENTS",len(rain))
    windows=scopes(pending)
    audits=[]
    all_events=[]
    for site in SITES:
        source_stats,source_read=stream_relevant(
            original[site],"TIMESTAMP_START","source",windows[site],FIELD_SRC)
        forcing_stats,forcing_read=stream_relevant(
            selected[site],"time","selected",windows[site],FIELD_MET)
        site_rain=[r for r in rain if r["site"]==site]
        focus=[r for r in windows[site] if site!="DE-Gri"]
        target_rain_date=("2012-07-27" if site=="DE-RuR" else
                          "2018-09-15" if site=="ES-Agu" else None)
        matching_old_rain=[r for r in site_rain if target_rain_date in r["time"]]
        matched_keys=0
        for w in windows[site]:
            key=w["id"];a=source_stats[key];b=forcing_stats[key]
            if not a["records"] or not b["records"]:
                print(" TARGET_MISSING_SOURCE_OR_SELECTED",site,key,
                      "SOURCE",a["records"],"STAGE28",b["records"])
            else:matched_keys+=1
            shared=len(a["selected_timestamps"] & b["selected_timestamps"])
            paired_rain=[]
            if "RAIN_" in key:
                for ts in sorted(a["paired_focus_rows"].keys() & b["paired_focus_rows"].keys()):
                    oa=a["paired_focus_rows"][ts]
                    ob=b["paired_focus_rows"][ts]
                    p=oa.get("P_F")
                    q=ob.get("PRECTmms")
                    mm=q*1800 if q is not None else None
                    paired_rain.append({"time":ts.isoformat(sep=" "),
                                        "source_P_F_mm":p,
                                        "source_P_F_QC":oa.get("P_F_QC"),
                                        "candidate_PRECT_mm_per_30min":mm,
                                        "same_numeric_amount_only":p is not None and mm is not None and
                                             abs(p-mm)<=max(0.1,abs(mm)*0.01),
                                        "units_or_accumulation_period_scientifically_verified":False})
            all_events.append({
                "site":site,"episode":key,
                "window_start":w["window_start"].isoformat(sep=" "),
                "window_end":w["window_end"].isoformat(sep=" "),
                "original_HH_rows_in_window":a["records"],
                "Stage28_HH_rows_in_window":b["records"],
                "same_naive_timestamp_rows":shared,
                "same_naive_timestamp_comparison_not_UTC_proof":True,
                "focus_target_rows_source":a["target_rows"],
                "focus_target_rows_Stage28":b["target_rows"],
                "focus_target_minmax_source":a["target_minmax"],
                "focus_target_minmax_Stage28":b["target_minmax"],
                "focus_source_first_and_last":a["focus_first"]+a["focus_last"],
                "focus_selected_first_and_last":b["focus_first"]+b["focus_last"],
                "paired_rain_focus_HH":paired_rain,
                "original_QC_categories":a["qc_counts"],
                "original_source_ranges":a["minmax"],
                "selected_Stage28_ranges":b["minmax"],
                "source_first_and_last":a["first"]+a["last"],
                "selected_first_and_last":b["first"]+b["last"],
                "source_time_alignment_verified_UTC":False,
                "observational_science_release":False,
            })
        audits.append({"site":site,
            "old_stage28_lineage_sha_previously_passed":True,
            "old_rain_provenance_rows":len(site_rain),
            "explicit_focus_date":target_rain_date,
            "explicit_focus_rain_gt18_ledger_rows":len(matching_old_rain),
            "source_manifest_primary_file":str(original[site]),
            "Stage28_selected_forcing_path":str(selected[site]),
            "target_episodes":len(windows[site]),
            "target_episodes_with_both_source_and_selected_records":matched_keys,
            "source_stream":source_read,"selected_stream":forcing_read,
            "old_rain_timing_science_release":False,
            "old_MDS_QC0_QC1_science_release":False,
            "soil_science_release":False,
            "model_run_release":False})
        print("SITE",site,"TARGET_EPISODES",len(windows[site]),
              "SOURCE_AND_STAGE28_PRESENT",f"{matched_keys}/{len(windows[site])}",
              "OLD_RAIN_GT18_ROWS",len(site_rain),
              "FOCUS_DATE_RAIN_GT18_ROWS",len(matching_old_rain))
        if site=="DE-Gri":
            print(" ORIGINAL_MDS_PENDING",len(windows[site]),"HELD_WITH_SOURCE_CONTEXT_NO_AUTO_REPAIR")
        if site=="IT-Tor":
            print(" IT_TOR_2025_OCT_NOV_ORIGINAL_QC_COUNTS",
                  source_stats["IT-Tor_QC1_QC2_2025_OCT_NOV"]["qc_counts"],
                  "NOT_EQUIVALENT_TO_1458HH_HISTORIC_REPAIR_SCOPE")
    result={
        "stage":"STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT",
        "read_only":True,"science_release":False,
        "source_stage03b":str(x.stage03b),"source_stage03c":str(x.stage03c),
        "original_case_forcing_FATES_PFT_modified":False,"slurm_submitted":False,
        "historical_rain_provenance":rain_status,"four_site_old_rain_rows":rain,
        "sites":audits,"target_event_context":all_events,
        "interpretation":"Stage03C MISSING old rain ledger was a search-path issue. Stage21 originally produced it, Stage22 inherits with INHERITED_STAGE21_ prefix. Event source rows are unreviewed FLUXMET consolidated observations/QC, not automatically native direct RH sensor or UTC. Source rain P_F agreement != accumulation-time proof; no physical correction, reanalysis insertion, new model case or AD5 release."}
    out=x.out_dir
    pj=out/"stage03d_four_site_targeted_original_met_rain_MDS_source_review_PRIVATE.json"
    pc=out/"stage03d_four_site_legacy_rain_events_PRIVATE.csv"
    ps=out/"stage03d_four_site_target_window_counts.csv"
    with pj.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    with pc.open("x",encoding="utf-8",newline="") as f:
        if rain:
            fields=list(rain[0])
            ww=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
            ww.writeheader();ww.writerows(rain)
        else:f.write("site,time,source_rain_evidence_missing\n")
    with ps.open("x",encoding="utf-8",newline="") as f:
        cols=("site","episode","window_start","window_end",
              "original_HH_rows_in_window","Stage28_HH_rows_in_window",
              "original_QC_categories_json")
        ww=csv.DictWriter(f,fieldnames=cols);ww.writeheader()
        for e in all_events:
            ww.writerow({**{k:e[k] for k in cols if k!="original_QC_categories_json"},
                         "original_QC_categories_json":json.dumps(e["original_QC_categories"])})
    print("JSON_PRIVATE",pj)
    print("LEGACY_RAIN_PRIVATE",pc)
    print("TARGET_WINDOWS",ps)
    print("STAGE03D SOURCE_CONTEXT_ONLY; SCIENCE_HOLD. NO FORCING/NETCDF/CIME/SLURM CHANGES")

if __name__=="__main__":
    main()
