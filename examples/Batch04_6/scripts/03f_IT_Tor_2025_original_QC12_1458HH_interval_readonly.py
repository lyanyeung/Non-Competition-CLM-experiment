#!/usr/bin/env python3
"""ICOS Batch04 Stage03F: locate the historical IT-Tor 1,458-HH QC1/QC2 block.

Narrow incremental audit only: reuse Stage03D/03E passed research HOLDs.
Streaming one historical native-network FLUXMET CSV and one already-selected
Stage28 CSV, collecting ONLY 2025 Oct-Nov (2,928 HH); no full-series QC,
no downloads, source changes, repairs or jobs.

Classify maximal contiguous original TA_F/VPD_F QC1/2 intervals and their
QC0 anchors, compare source and selected T/VPD at the same *source-label*
timestamp, and capture only non-sensitive aggregate diagnostics plus a
PRIVATE source/selected interval ledger. A length=1458 match alone cannot
prove it is the historical Stage27 1458-HH episode without its timestamps.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

D_STAGE="STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT"
E_STAGE="STAGE03E_PRIVATE_SUMMARIZE_STAGE03D_SELECTED_EVIDENCE"
SITE="IT-Tor"
START=datetime(2025,10,1)
END=datetime(2025,11,30,23,30)
EXPECTED=2928
EXPECT_Q={"TA_F_QC":{0:1441,1:587,2:900},
          "VPD_F_QC":{0:1441,1:587,2:900},
          "P_F_QC":{0:1440,2:1488}}
TOL=1e-8

def req(ok,msg):
    if not ok:raise ValueError(msg)

def time_val(val,source):
    s=str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():s=s[:-2]
    try:
        t=datetime.strptime(s,"%Y%m%d%H%M") if source else datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo is None else None

def number(val):
    try:
        x=float(val)
        return x if math.isfinite(x) and x>-9990 else None
    except (ValueError,TypeError):
        return None

def category(val):
    x=number(val)
    return int(x) if x is not None and x in (0,1,2) else None

def record_source(p):
    req(p.is_file() and not p.is_symlink(),"Pinned IT-Tor original CSV unavailable")
    fields={"TIMESTAMP_START","TA_F","TA_F_QC","VPD_F","VPD_F_QC","P_F_QC"}
    selected={}
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        d=csv.DictReader(f)
        req(fields<=set(d.fieldnames or []),"IT-Tor original source column schema differs")
        for row in d:
            t=time_val(row["TIMESTAMP_START"],True)
            if t is None or t<START or t>END:continue
            req(t not in selected,"Duplicate native-network timestamp in Oct-Nov "+str(t))
            selected[t]={"TA_F":number(row["TA_F"]),
                         "VPD_F":number(row["VPD_F"]),
                         "TA_F_QC":category(row["TA_F_QC"]),
                         "VPD_F_QC":category(row["VPD_F_QC"]),
                         "P_F_QC":category(row["P_F_QC"])}
    return selected

def record_selected(p):
    req(p.is_file() and not p.is_symlink(),"Pinned Stage28 source CSV unavailable")
    fields={"time","TA_USE","VPD_USE","PRECTmms"}
    out={}
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        d=csv.DictReader(f)
        req(fields<=set(d.fieldnames or []),"IT-Tor Stage28 source column schema differs")
        for row in d:
            t=time_val(row["time"],False)
            if t is None or t<START or t>END:continue
            req(t not in out,"Duplicate Stage28 timestamp in Oct-Nov "+str(t))
            out[t]={"TA_USE":number(row["TA_USE"]),
                    "VPD_USE":number(row["VPD_USE"])}
    return out

def expected_times():
    return [START+timedelta(minutes=30*i) for i in range(EXPECTED)]

def qualified(row,kind):
    a=row["TA_F_QC"];b=row["VPD_F_QC"]
    if kind=="PAIR_QC1_OR_QC2":return a in (1,2) and b in (1,2)
    if kind=="PAIR_QC1_ONLY":return a==1 and b==1
    if kind=="PAIR_QC2_ONLY":return a==2 and b==2
    if kind=="VPD_QC1_OR_QC2":return b in (1,2)
    if kind=="P_QC2":return row["P_F_QC"]==2
    raise ValueError("Unexpected QC episode kind "+kind)

def segment(times,original,kind):
    runs=[];start=None
    for i,t in enumerate(times):
        ok=qualified(original[t],kind)
        if ok and start is None:start=i
        if start is not None and ((not ok) or i==len(times)-1):
            last=i if ok and i==len(times)-1 else i-1
            left=original[times[start-1]] if start>0 else None
            right=original[times[last+1]] if last+1<len(times) else None
            runs.append({"kind":kind,"start":times[start].isoformat(sep=" "),
                         "end":times[last].isoformat(sep=" "),
                         "half_hours":last-start+1,
                         "source_left_anchor_QC":(
                           {"TA_F_QC":left["TA_F_QC"],"VPD_F_QC":left["VPD_F_QC"]}
                           if left is not None else None),
                         "source_right_anchor_QC":(
                           {"TA_F_QC":right["TA_F_QC"],"VPD_F_QC":right["VPD_F_QC"]}
                           if right is not None else None),
                         "both_sides_QC0":bool(left is not None and right is not None
                           and left["TA_F_QC"]==left["VPD_F_QC"]==
                               right["TA_F_QC"]==right["VPD_F_QC"]==0),
                         "matches_legacy_length_1458":last-start+1==1458})
            start=None
    return runs

def verify_inputs(d,e):
    req(d.get("stage")==D_STAGE and d.get("read_only") is True and
        d.get("science_release") is False and d.get("slurm_submitted") is False,
        "Original Stage03D private science-HOLD report required")
    req(e.get("stage")==E_STAGE and e.get("read_only") is True and
        e.get("science_release") is False and e.get("model_submitted") is False,
        "Original Stage03E private science-HOLD summary required")
    a={r.get("site"):r for r in d.get("sites",[])}
    b={r.get("site"):r for r in e.get("sites",[])}
    req(len(a)==4 and len(b)==4 and SITE in a and SITE in b,
        "Unexpected Stage03D/E station inventory")
    r=a[SITE];p=b[SITE]
    req(r.get("target_episodes")==1 and
        r.get("target_episodes_with_both_source_and_selected_records")==1 and
        p.get("2025_Oct_Nov_HH_count")==EXPECTED and
        p.get("old_1458_HH_exact_interval_located") is False,
        "Stage03D/E original IT-Tor 2,928-HH evidence not pinned")
    matching=[x for x in d.get("target_event_context",[])
              if x.get("site")==SITE]
    req(len(matching)==1 and
        matching[0].get("original_HH_rows_in_window")==EXPECTED and
        matching[0].get("Stage28_HH_rows_in_window")==EXPECTED,
        "Stage03D original 2025 Oct-Nov source/selected evidence missing")
    qc=matching[0].get("original_QC_categories",{})
    for col,codes in EXPECT_Q.items():
        for val,expected in codes.items():
            req(qc.get(f"{col}:{val}")==expected,
                f"Stage03D original count differs: {col} QC{val}")
    return Path(r["source_manifest_primary_file"]),Path(r["Stage28_selected_forcing_path"])

def audit(source,selected):
    times=expected_times()
    req(set(source)==set(times) and set(selected)==set(times),
        "Missing/extra/duplicate 2025 Oct-Nov source vs Stage28 half-hourly labels")
    qcounts={}
    for col,exp in EXPECT_Q.items():
        observed=Counter(source[t][col] for t in times)
        req(observed==Counter(exp),
            col+" original Stage03D provenance count mismatch "+str(observed))
        qcounts[col]={str(k):v for k,v in sorted(observed.items())}
    kinds=("PAIR_QC1_OR_QC2","PAIR_QC1_ONLY",
           "PAIR_QC2_ONLY","VPD_QC1_OR_QC2","P_QC2")
    runs={kind:segment(times,source,kind) for kind in kinds}
    pair=runs["PAIR_QC1_OR_QC2"]
    exact=[r for r in pair if r["matches_legacy_length_1458"]]
    # Numeric difference is a contextual source relationship, never proof of
    # in-situ sensor truth, ERA independence, correct UTC clock or valid forcing.
    qc_diff={str(k):{"N":0,"TA_equals":0,"VPD_equals":0,
                     "TA_different":0,"VPD_different":0,
                     "TA_comparable":0,"VPD_comparable":0} for k in (0,1,2)}
    for t in times:
        r=source[t];v=selected[t]
        for qname,sname,dname in (("TA_F_QC","TA_F","TA_USE"),
                                   ("VPD_F_QC","VPD_F","VPD_USE")):
            k=r[qname]
            if k not in (0,1,2):continue
            count=qc_diff[str(k)]
            if qname=="TA_F_QC":count["N"]+=1
            a=r[sname];b=v[dname]
            if a is None or b is None:continue
            name="TA" if qname=="TA_F_QC" else "VPD"
            count[name+"_comparable"]+=1
            count[name+("_equals" if abs(a-b)<=TOL else "_different")]+=1
    ranked=sorted(pair,key=lambda r:-r["half_hours"])
    return {"stage":"STAGE03F_IT_TOR_2025_OCT_NOV_HISTORICAL_1458HH_QC1_QC2_EPISODE_FORENSICS",
            "read_only":True,"science_release":False,
            "no_source_or_case_writes":True,"slurm_submitted":False,
            "site":SITE,"source_label_clock_assumed_not_UTC_proved":True,
            "source_and_Stage28_HH":len(times),
            "original_QC_counts":qcounts,
            "run_types":runs,
            "pair_filled_QC1_or_QC2_longest_10":ranked[:10],
            "pair_filled_exact_1458_length_candidates":exact,
            "historical_Stage27_1458HH_identity_proven":False,
            "source_vs_selected_numeric_equality_by_original_QC":qc_diff,
            "science_caution":"Historical Stage27 recorded a 1458-HH fill interval but no exact source timestamps in GitHub. A matching duration alone is NOT independent proof of the original event. Leave all source-QC, physical RH/VPD, station time, rain accumulation and 10-layer soil-organic science HOLD. Do not auto change model inputs."}

def self_test():
    times=[datetime(2025,10,1)+timedelta(minutes=30*i) for i in range(8)]
    x={t:{"TA_F_QC":1 if 1<=i<=5 else 0,
          "VPD_F_QC":2 if 1<=i<=5 else 0,
          "P_F_QC":0} for i,t in enumerate(times)}
    runs=segment(times,x,"PAIR_QC1_OR_QC2")
    assert len(runs)==1 and runs[0]["half_hours"]==5
    assert (runs[0]["both_sides_QC0"] and
            runs[0]["start"]=="2025-10-01 00:30:00")
    assert not segment(times,x,"PAIR_QC1_ONLY")
    assert time_val("202510010000",True)==times[0]
    assert time_val("2025-10-01 00:00:00",False)==times[0]
    assert sum(EXPECT_Q["TA_F_QC"].values())==EXPECTED
    assert sum(EXPECT_Q["P_F_QC"].values())==EXPECTED
    print("STAGE03F SELF-TEST PASS: paired QC1/QC2 run segmentation, two QC0 anchors, pinned 2928-HH provenance, no writes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03d",type=Path)
    p.add_argument("--stage03e",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    req(a.stage03d is not None and a.stage03d.is_file() and
        a.stage03e is not None and a.stage03e.is_file(),
        "Both operator-confirmed Stage03D and Stage03E private JSON inputs required")
    req(a.out_dir is not None and a.out_dir.is_dir() and
        not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
        "Output must be a NEW EMPTY private directory")
    d=json.loads(a.stage03d.read_text(encoding="utf-8"))
    e=json.loads(a.stage03e.read_text(encoding="utf-8"))
    source_file,selected_file=verify_inputs(d,e)
    raw=record_source(source_file)
    selected=record_selected(selected_file)
    report=audit(raw,selected)
    report["source_paths"]={"original_network_product":str(source_file),
                            "selected_Stage28":str(selected_file),
                            "original_Stage03D":str(a.stage03d),
                            "source_Stage03E":str(a.stage03e)}
    jsonfile=a.out_dir/"stage03f_IT_Tor_exact_QC1_QC2_run_lengths_PRIVATE.json"
    table=a.out_dir/"stage03f_IT_Tor_original_QC1_QC2_episodes_PRIVATE.csv"
    with jsonfile.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    fields=("kind","start","end","half_hours","both_sides_QC0",
            "matches_legacy_length_1458","source_left_anchor_QC",
            "source_right_anchor_QC")
    with table.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for group in report["run_types"].values():
            for row in group:
                w.writerow({**row,
                    "source_left_anchor_QC":json.dumps(row["source_left_anchor_QC"]),
                    "source_right_anchor_QC":json.dumps(row["source_right_anchor_QC"])})
    print("IT-Tor 2025_OCT_NOV",report["source_and_Stage28_HH"],"HALF_HOURS")
    print("ORIGINAL_TA_VPD_QC",report["original_QC_counts"]["TA_F_QC"])
    print("PAIRED_QC1_QC2_RUNS",len(report["run_types"]["PAIR_QC1_OR_QC2"]))
    for row in report["pair_filled_QC1_or_QC2_longest_10"][:5]:
        print(" TOP_RUN",row["start"],row["end"],
              "HH",row["half_hours"],
              "BOTH_SIDE_QC0",row["both_sides_QC0"])
    print("PAIR_RUNS_LENGTH_1458",len(report["pair_filled_exact_1458_length_candidates"]))
    print("STAGE27_EXACT_INTERVAL_PROVEN False")
    print("QC_SOURCE_VS_STAGE28_COUNTS",report["source_vs_selected_numeric_equality_by_original_QC"])
    print("PRIVATE_JSON",jsonfile)
    print("PRIVATE_EPISODE_CSV",table)
    print("STAGE03F READONLY PASS; ALL SOURCE SCIENCE HOLDS RETAINED; NO NEW MODEL RUN")

if __name__=="__main__":
    main()
