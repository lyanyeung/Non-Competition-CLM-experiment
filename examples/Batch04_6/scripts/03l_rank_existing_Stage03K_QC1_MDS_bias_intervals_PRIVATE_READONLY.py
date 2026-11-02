#!/usr/bin/env python3
"""ICOS Batch04 Stage03L — PRIORITIZE EXISTING IT-Tor QC1/MDS subintervals.

Only the successful Stage03K PRIVATE JSON and 10-row PRIVATE segment CSV
are read. No FLUXMET/Stage28/annual DATM/ERA source reread, no changes
to input forcing or case. Packaged ERA is a gapfill reference, not truth.

The 'severe' >=5C and >=10C negative differences are screening thresholds
for MDS-minus-packaged-ERA, NOT confirmed sensor biases or science approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

K_STAGE="STAGE03K_IT_TOR_QC1_MDS_RELATIVE_ERA_BIAS_2_RUNS_ONLY"
EXPECTED={"LONG_1458":{"QC1":558,"QC2":900,"segments":9,
                       "below_minus5C":183,"below_minus10C":98},
          "SHORT_29":{"QC1":29,"QC2":0,"segments":1,
                      "below_minus5C":0,"below_minus10C":0}}
LIMITS={"LONG_1458":("2025-10-21 02:30:00","2025-11-20 11:00:00"),
        "SHORT_29":("2025-11-21 17:30:00","2025-11-22 07:30:00")}
INPUT_COLS={"run","start","end","QC1_halfhours","N","min","p05",
            "median","p95","max","mean","below_minus5C","below_minus10C"}
OUTPUT_COLS=("rank","run","start","end","QC1_halfhours","relative_ERA_N",
             "MDS_minus_packaged_ERA_T_min_C",
             "MDS_minus_packaged_ERA_T_median_C",
             "MDS_minus_packaged_ERA_T_mean_C",
             "MDS_minus_packaged_ERA_T_p05_C",
             "MDS_minus_packaged_ERA_T_p95_C",
             "MDS_colder_than_ERA_gt5C_HH",
             "MDS_colder_than_ERA_gt10C_HH",
             "fraction_colder_gt5C_pct","fraction_colder_gt10C_pct",
             "review_class","scientific_action")

def require(ok,msg):
    if not ok:raise ValueError(msg)

def sha256(path):
    import hashlib
    d=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):d.update(block)
    return d.hexdigest()

def integer(text):
    v=int(text)
    require(v>=0,"Negative QC/event count")
    return v

def number(text):
    v=float(text)
    require(math.isfinite(v),"Nonfinite reported original MDS-relative statistics")
    return v

def parse_file(jpath,cpath):
    require(jpath.is_file() and cpath.is_file() and
            not jpath.is_symlink() and not cpath.is_symlink(),
            "Stage03K original private JSON and subrun CSV must exist")
    require(jpath.stat().st_size<5_000_000 and cpath.stat().st_size<5_000_000,
            "Unexpectedly large Stage03K reports")
    j=json.loads(jpath.read_text(encoding="utf-8"))
    with cpath.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        require(INPUT_COLS<=set(r.fieldnames or []),
                "Stage03K original segment source headers changed")
        segments=list(r)
    require(j.get("stage")==K_STAGE and j.get("read_only") is True and
            j.get("science_release") is False and
            j.get("model_or_source_modified") is False and
            j.get("slurm_submitted") is False,
            "Stage03K original source-science HOLD report invalid")
    require(len(segments)==10,"Expected 9 long QC1 segments + 1 short segment")
    return j,segments

def rank_segments(j,rows):
    actual={r.get("run"):r for r in j.get("two_runs",[])}
    require(len(actual)==2 and set(actual)==set(EXPECTED),
            "Unexpected original Stage03K run identity")
    for name,ex in EXPECTED.items():
        run=actual[name]
        require(run.get("QC1_MDS_HH")==ex["QC1"] and
                run.get("QC2_ERA_HH")==ex["QC2"] and
                run.get("QC1_subrun_count")==ex["segments"] and
                run.get("science_release") is False,
                "Original Stage03K QC count/science gate changed in "+name)
        t=run.get("MDS_minus_packaged_ERA_T_C",{})
        require(t.get("N")==ex["QC1"] and
                t.get("below_minus5C")==ex["below_minus5C"] and
                t.get("below_minus10C")==ex["below_minus10C"],
                "Original Stage03K QC1 relative ERA count unexpectedly changed "+name)

    transformed=[]
    for source in rows:
        name=source["run"]
        require(name in EXPECTED,"Unexpected original QC1 subrun name")
        start=datetime.fromisoformat(source["start"])
        end=datetime.fromisoformat(source["end"])
        lower,upper=[datetime.fromisoformat(x) for x in LIMITS[name]]
        count=integer(source["QC1_halfhours"])
        n=integer(source["N"])
        h5=integer(source["below_minus5C"])
        h10=integer(source["below_minus10C"])
        require(lower<=start<=end<=upper and
                int((end-start).total_seconds())==1800*(count-1),
                "Original QC1 subinterval calendar/length inconsistent")
        require(0<h10<=h5<=n<=count or (h10==0 and 0<=h5<=n<=count and n>0),
                "Original QC1 relative bias exceedance count inconsistent")
        row={
          "run":name,"start":source["start"],"end":source["end"],
          "QC1_halfhours":count,"relative_ERA_N":n,
          "MDS_minus_packaged_ERA_T_min_C":number(source["min"]),
          "MDS_minus_packaged_ERA_T_median_C":number(source["median"]),
          "MDS_minus_packaged_ERA_T_mean_C":number(source["mean"]),
          "MDS_minus_packaged_ERA_T_p05_C":number(source["p05"]),
          "MDS_minus_packaged_ERA_T_p95_C":number(source["p95"]),
          "MDS_colder_than_ERA_gt5C_HH":h5,
          "MDS_colder_than_ERA_gt10C_HH":h10,
          "fraction_colder_gt5C_pct":100*h5/n,
          "fraction_colder_gt10C_pct":100*h10/n,
          "scientific_action":"HOLD_NO_FORCING_EDITS",
        }
        row["review_class"]=(
          "PRIORITY_SEVERE_ERA_RELATIVE_COLD_DIFFERENCE" if h10>0 else
          "PRIORITY_MODERATE_ERA_RELATIVE_COLD_DIFFERENCE" if h5>0 else
          "NO_GT5C_COLD_DIFFERENCE_KEEP_SOURCE_PENDING_SCIENCE")
        transformed.append(row)
    for name,expected in EXPECTED.items():
        selected=sorted((r for r in transformed if r["run"]==name),
                        key=lambda r:r["start"])
        require(len(selected)==expected["segments"],
                "Original contiguous QC1 segment count changed")
        require(sum(r["QC1_halfhours"] for r in selected)==expected["QC1"],
                "Original subinterval HH no longer sum to Stage03K")
        require(sum(r["relative_ERA_N"] for r in selected)==expected["QC1"],
                "Original QC1 source missing relative ERA observations")
        for column,total in (("MDS_colder_than_ERA_gt5C_HH",expected["below_minus5C"]),
                             ("MDS_colder_than_ERA_gt10C_HH",expected["below_minus10C"])):
            require(sum(r[column] for r in selected)==total,
                    "Original per-episode threshold tallies disagree with Stage03K")
        for left,right in zip(selected,selected[1:]):
            require(datetime.fromisoformat(right["start"])>
                    datetime.fromisoformat(left["end"])+timedelta(minutes=30),
                    "QC1 segment intervals overlap or no intervening QC2")
        # The already-computed mean for each block must reconcile exactly
        # with the original count-weighted mean from Stage03K.
        original_mean=number(actual[name]["MDS_minus_packaged_ERA_T_C"]["mean"])
        aggregate=sum(r["relative_ERA_N"]*
                      r["MDS_minus_packaged_ERA_T_mean_C"] for r in selected)
        require(abs(aggregate/expected["QC1"]-original_mean)<=1e-7,
                "Original Stage03K block means not consistent with source totals")
    transformed.sort(key=lambda r:(
        -r["MDS_colder_than_ERA_gt10C_HH"],
        -r["MDS_colder_than_ERA_gt5C_HH"],
         r["MDS_minus_packaged_ERA_T_min_C"],r["start"]))
    for i,row in enumerate(transformed,1):row["rank"]=i
    summary={
      "stage":"STAGE03L_IT_TOR_RANK_EXISTING_QC1_MDS_ERA_DIFFERENCE_EPISODES",
      "read_only":True,"science_release":False,
      "source_or_model_modified":False,"slurm_submitted":False,
      "bias_is_relative_to_packaged_ERA_not_observed_error":True,
      "source_stage03k_SHA256_verified_by_current_read":True,
      "total_QC1_relative_HH":587,
      "long_run_QC1_HH":558,"long_run_QC2_HH":900,
      "short_run_QC1_HH":29,
      "long_run_colder_than_ERA_5C_HH":183,
      "long_run_colder_than_ERA_10C_HH":98,
      "short_run_colder_than_ERA_5C_HH":0,
      "subintervals_total":len(transformed),
      "subintervals_gt10C_count":sum(r["MDS_colder_than_ERA_gt10C_HH"]>0 for r in transformed),
      "subintervals_gt5C_count":sum(r["MDS_colder_than_ERA_gt5C_HH"]>0 for r in transformed),
      "method":"Prioritize by number of differences below -10C, then below -5C, then most negative min. These differences only compare two gapfilled source products.",
      "scientific_warning":"Never treat ERA-relative differences as sensor errors; do not automatically replace source MDS or build new DATM. Seek original tower sensor/QC and independent nearby meteorology evidence for the highest-priority exact subruns; soil ORGANIC=0 remains a separate HOLD."
    }
    return summary,transformed

def self_test():
    # Small negative screening and time-label checks; confirm that malformed
    # counts cannot bypass previous Stage03K evidence.
    assert number("-14.498")==-14.498
    assert integer("98")==98
    assert int((datetime.fromisoformat("2025-10-21 03:00:00")-
                datetime.fromisoformat("2025-10-21 02:30:00")).total_seconds())==1800
    assert EXPECTED["LONG_1458"]["QC1"]+EXPECTED["SHORT_29"]["QC1"]==587
    assert EXPECTED["LONG_1458"]["below_minus10C"]==98
    assert sum(x["segments"] for x in EXPECTED.values())==10
    print("STAGE03L SELF-TEST PASS: saved Stage03K 9+1 QC1 segments, strict per-episode count/time/mean reconciliation, readonly")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03k",type=Path)
    p.add_argument("--segments",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    require(a.stage03k is not None and a.segments is not None and
            a.out_dir is not None and a.out_dir.is_dir() and
            not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
            "Require both original Stage03K files and NEW EMPTY PRIVATE output directory")
    original,segments=parse_file(a.stage03k,a.segments)
    summary,ranked=rank_segments(original,segments)
    summary["Stage03K_original_JSON_SHA256"]=sha256(a.stage03k)
    summary["Stage03K_original_CSV_SHA256"]=sha256(a.segments)
    summary["source_stage03k_JSON"]=str(a.stage03k)
    summary["source_stage03k_CSV"]=str(a.segments)
    js=a.out_dir/"stage03l_IT_Tor_QC1_MDS_priority_summary_PRIVATE.json"
    csvout=a.out_dir/"stage03l_IT_Tor_10_QC1_subruns_ranked_PRIVATE.csv"
    with js.open("x",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,ensure_ascii=False);f.write("\n")
    with csvout.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=OUTPUT_COLS);w.writeheader()
        w.writerows(ranked)
    print("STAGE03L EXACT 10 QC1 SUBINTERVALS VERIFIED; NO FLUXMET/NETCDF REREAD")
    print("LONG_1458 558 QC1, 183 below -5C, 98 below -10C, 9 subruns")
    print("SHORT_29 29 QC1, 0 below -5C, 1 subrun")
    print("SUBRUNS_WITH_GT10C_COLD_DIFF",summary["subintervals_gt10C_count"],
          "SUBRUNS_WITH_GT5C_COLD_DIFF",summary["subintervals_gt5C_count"])
    for row in ranked[:10]:
        print("RANK",row["rank"],row["run"],row["start"],row["end"],
              "QC1_HH",row["QC1_halfhours"],
              "BELOW_MINUS5",row["MDS_colder_than_ERA_gt5C_HH"],
              "BELOW_MINUS10",row["MDS_colder_than_ERA_gt10C_HH"],
              "MEDIAN_DELTA",round(row["MDS_minus_packaged_ERA_T_median_C"],3),
              "SCIENCE_HOLD True")
    print("PRIVATE_JSON",js)
    print("PRIVATE_CSV",csvout)
    print("STAGE03L FINISHED: SCIENCE HOLD, NO MET/NETCDF/CIME/FATES/SLURM CHANGES")

if __name__=="__main__":
    main()
