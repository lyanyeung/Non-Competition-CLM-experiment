#!/usr/bin/env python3
"""Batch04 Stage03G — read-only science screens for the TWO known IT-Tor QC1/2 runs.

Source-pinned by the completed Stage03F and Stage03B reports. Stream only
two previously determined QC1/QC2 intervals plus 2-hour boundaries from
the original FLUXMET source and Stage28 selected CSV. Evaluate actual
source T/VPD/QC; physical RH/e_sat/QBOT consistency, jumps and endpoint
QC0 brackets. Source-packaged ERA is context only, NOT independent truth.

Never correct a value or infer the 1458-HH episode is human-approved.
Only two PRIVATE reports in a NEW EMPTY HOME dir. No CIME, NetCDF, Slurm,
ERA download, other site scans, or new spin-up.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path

F_STAGE="STAGE03F_IT_TOR_2025_OCT_NOV_HISTORICAL_1458HH_QC1_QC2_EPISODE_FORENSICS"
B_STAGE="STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE"
RUN_SPECS=(("LONG_1458","2025-10-21 02:30:00","2025-11-20 11:00:00",1458),
           ("SHORT_29","2025-11-21 17:30:00","2025-11-22 07:30:00",29))
PADDING=timedelta(hours=2)
SRC_REQ={"TIMESTAMP_START","TA_F","TA_F_QC","VPD_F","VPD_F_QC"}
SEL_REQ={"time","TA_USE","VPD_USE","PSRF","QBOT"}
SRC_OPTIONAL={"TA_ERA","VPD_ERA","PA_F"}
ENDPOINT_FIELDS=("run","position","time","source_TA_C","source_VPD_hPa",
                 "source_TA_QC","source_VPD_QC","selected_TA_C",
                 "selected_VPD_hPa","selected_PSRF_Pa","selected_QBOT",
                 "reconstructed_RH_pct","source_TA_ERA_C",
                 "source_VPD_ERA_hPa")

def require(ok,msg):
    if not ok:raise ValueError(msg)

def dt(s,raw=False):
    t=str(s).strip()
    if t.endswith(".0") and t[:-2].isdigit():t=t[:-2]
    try:
        val=datetime.strptime(t,"%Y%m%d%H%M") if raw else datetime.fromisoformat(t)
        return val if val.tzinfo is None else None
    except ValueError:return None

def num(s):
    try:
        x=float(s)
        return x if math.isfinite(x) and x>-9990 else None
    except (TypeError,ValueError):return None

def qc(s):
    v=num(s)
    return int(v) if v in (0,1,2) else None

def esat(t):
    if t is None or not -90<t<80:return None
    return 6.112*math.exp(17.67*t/(t+243.5))

def physics(t,v,pa,q):
    sat=esat(t)
    if sat is None or v is None:
        return {"RH":None,"Q_pred":None,"invalid_humidity":True,
                "near_zero_RH":False,"qbot_diff_gt_1e_5":None}
    ea=sat-v
    rh=100*ea/sat
    invalid=(v<0 or ea<0 or rh>100 or rh<0)
    pred=None
    if pa is not None and pa>0 and ea>=0 and (pa-0.378*ea*100)>0:
        pred=0.622*ea*100/(pa-0.378*ea*100)
    diff=None if pred is None or q is None else abs(pred-q)>1e-5
    return {"RH":rh,"Q_pred":pred,"invalid_humidity":invalid,
            "near_zero_RH":0<=rh<1,"qbot_diff_gt_1e_5":diff}

def source_sha(file):
    h=hashlib.sha256()
    with file.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def validate_old(f,b):
    require(f.get("stage")==F_STAGE and f.get("read_only") is True and
            f.get("science_release") is False and f.get("slurm_submitted") is False,
            "Original Stage03F passed HOLD report required")
    require(b.get("stage")==B_STAGE and b.get("read_only") is True and
            b.get("science_release") is False,"Original Stage03B source register required")
    r={x["site"]:x for x in b.get("sites",[])}.get("IT-Tor")
    require(r is not None and r.get("stage28_met_SHA_verified") is True and
            r.get("all_current_paths_match_historical") is True and
            r.get("representative_NC_SHA_pass") is True,
            "Stage03B IT-Tor source/datm provenance changed")
    old=f.get("run_types",{}).get("PAIR_QC1_OR_QC2",[])
    require(len(old)==2,"Only exact two actual IT-Tor paired non-QC0 runs are accepted")
    for _,start,end,n in RUN_SPECS:
        found=[x for x in old if x.get("start")==start and x.get("end")==end
               and x.get("half_hours")==n and x.get("both_sides_QC0") is True]
        require(len(found)==1,"Original Stage03F interval/anchors changed: "+start)
    require(f.get("source_and_Stage28_HH")==2928 and
            f.get("historical_Stage27_1458HH_identity_proven") is False,
            "Original Stage03F HOLD provenance changed")
    paths=f.get("source_paths",{})
    source=Path(paths.get("original_network_product",""))
    selected=Path(paths.get("selected_Stage28",""))
    require(source.is_absolute() and source.is_file() and not source.is_symlink(),
            "Original network product unavailable")
    require(selected.is_absolute() and selected.is_file() and not selected.is_symlink(),
            "Selected Stage28 data unavailable")
    require(str(selected)==r["stage28_met_path"] and
            source_sha(selected)==r["stage28_met_SHA_expected"],
            "Selected historical Stage28 SHA changed")
    return source,selected

def capture(file,timecol,raw,required,fields,bounds):
    # The CSV rows are streamed once. Only two exact event windows are retained.
    result={}
    with file.open("r",encoding="utf-8-sig",newline="") as fd:
        reader=csv.DictReader(fd)
        header=set(reader.fieldnames or [])
        require(required<=header,"Source selected CSV missing expected fields "+str(required-header))
        columns=fields & header
        for row in reader:
            t=dt(row[timecol],raw)
            if t is None or not any(a<=t<=z for a,z in bounds):continue
            require(t not in result,"Duplicate timestamp in protected event scope")
            result[t]={k:(qc(row[k]) if k.endswith("_QC") else num(row[k]))
                       for k in columns}
    return result,sorted(columns)

def evaluate(s,o,run_specs):
    per_run=[];endpoints=[]
    for rid,left,right,n in run_specs:
        t0=dt(left);t1=dt(right)
        times=[t0+timedelta(minutes=30*i) for i in range(n)]
        require(times[-1]==t1,"Original 30-minute length/time count disagrees")
        alltimes=[t0-timedelta(minutes=30*i) for i in range(4,0,-1)]
        alltimes+=times+[t1+timedelta(minutes=30*i) for i in range(1,5)]
        require(all(t in s and t in o for t in alltimes),
                rid+" missing source/selected +/-2-hour boundary or in-run HH")
        qdist=Counter((s[t]["TA_F_QC"],s[t]["VPD_F_QC"]) for t in times)
        require(sum(qdist.values())==n and all(a in (1,2) and b in (1,2)
               for a,b in qdist),rid+" native QC1/2 pair interval no longer matches")
        for t in (t0-timedelta(minutes=30),t1+timedelta(minutes=30)):
            require(s[t]["TA_F_QC"]==s[t]["VPD_F_QC"]==0,
                    rid+" immediate original QC0 anchor changed")
        flags=Counter();mm={"RH_min":None,"RH_max":None}
        first_prev=t0-timedelta(minutes=30)
        last_next=t1+timedelta(minutes=30)
        comparisons={"TA_both_present":0,"TA_equals":0,"VPD_both_present":0,
                     "VPD_equals":0,"source_ERA_T_available":0,
                     "source_ERA_VPD_available":0}
        prior=None
        for t in times:
            a=s[t];v=o[t];p=physics(v["TA_USE"],v["VPD_USE"],v["PSRF"],v["QBOT"])
            flags["screened"]+=1
            if p["invalid_humidity"]:flags["invalid_RH_or_negative_VPD"]+=1
            if p["near_zero_RH"]:flags["RH_below_1pct"]+=1
            if p["qbot_diff_gt_1e_5"] is True:flags["selected_QBOT_physics_diff_gt_1e_5"]+=1
            if p["RH"] is None:flags["RH_not_computable"]+=1
            else:
                mm["RH_min"]=p["RH"] if mm["RH_min"] is None else min(mm["RH_min"],p["RH"])
                mm["RH_max"]=p["RH"] if mm["RH_max"] is None else max(mm["RH_max"],p["RH"])
            if a.get("TA_ERA") is not None:comparisons["source_ERA_T_available"]+=1
            if a.get("VPD_ERA") is not None:comparisons["source_ERA_VPD_available"]+=1
            for source_key,dest,key in (("TA_F","TA_USE","TA"),
                                        ("VPD_F","VPD_USE","VPD")):
                if a[source_key] is not None and v[dest] is not None:
                    comparisons[key+"_both_present"]+=1
                    if abs(a[source_key]-v[dest])<=1e-8:
                        comparisons[key+"_equals"]+=1
            if prior is not None:
                prev=o[prior]
                if all(v[x] is not None and prev[x] is not None for x in ("TA_USE","VPD_USE")):
                    if abs(v["TA_USE"]-prev["TA_USE"])>5:flags["inside_T_step_gt5C"]+=1
                    if abs(v["VPD_USE"]-prev["VPD_USE"])>8:flags["inside_VPD_step_gt8hPa"]+=1
            prior=t
        edges=[]
        for a,b,label in ((first_prev,t0,"LEFT"),(t1,last_next,"RIGHT")):
            u=o[a];v=o[b]
            deltaT=(v["TA_USE"]-u["TA_USE"] if None not in (v["TA_USE"],u["TA_USE"]) else None)
            deltaV=(v["VPD_USE"]-u["VPD_USE"] if None not in (v["VPD_USE"],u["VPD_USE"]) else None)
            edges.append({"side":label,"source_label_left":a.isoformat(sep=" "),
                          "source_label_right":b.isoformat(sep=" "),
                          "deltaT_C":deltaT,"deltaVPD_hPa":deltaV,
                          "deltaT_abs_gt4C":deltaT is not None and abs(deltaT)>4,
                          "deltaVPD_abs_gt5hPa":deltaV is not None and abs(deltaV)>5})
        for pos,t in ([(f"LEFT_{i}",t0-timedelta(minutes=30*i)) for i in range(4,0,-1)]
                      +[("RUN_START",t0),("RUN_START_PLUS1",t0+timedelta(minutes=30)),
                         ("RUN_END_MINUS1",t1-timedelta(minutes=30)),("RUN_END",t1)]
                      +[(f"RIGHT_{i}",t1+timedelta(minutes=30*i)) for i in range(1,5)]):
            a=s[t];v=o[t]
            p=physics(v["TA_USE"],v["VPD_USE"],v["PSRF"],v["QBOT"])
            endpoints.append({
              "run":rid,"position":pos,"time":t.isoformat(sep=" "),
              "source_TA_C":a.get("TA_F"),"source_VPD_hPa":a.get("VPD_F"),
              "source_TA_QC":a.get("TA_F_QC"),"source_VPD_QC":a.get("VPD_F_QC"),
              "selected_TA_C":v.get("TA_USE"),"selected_VPD_hPa":v.get("VPD_USE"),
              "selected_PSRF_Pa":v.get("PSRF"),"selected_QBOT":v.get("QBOT"),
              "reconstructed_RH_pct":p["RH"],
              "source_TA_ERA_C":a.get("TA_ERA"),
              "source_VPD_ERA_hPa":a.get("VPD_ERA")})
        per_run.append({"id":rid,"start":left,"end":right,"half_hours":n,
                        "original_QC_pairs":{str(k):count for k,count in qdist.items()},
                        "original_QC0_at_both_immediate_anchors":True,
                        "selected_reconstructed_RH_range":mm,
                        "physical_screen_counts":dict(flags),
                        "source_selected_numeric_comparison":comparisons,
                        "source_network_ERA_not_independent_truth":True,
                        "selected_source_label_boundary_steps":edges,
                        "scientific_release":False})
    return per_run,endpoints

def selftest():
    assert round(esat(0),3)==6.112
    good=physics(10.0,0.0,101325,0.007)
    assert good["RH"]==100.0 and good["invalid_humidity"] is False
    assert physics(10.0,-0.1,101325,None)["invalid_humidity"] is True
    assert physics(10.0,30.0,101325,None)["invalid_humidity"] is True
    t0=datetime(2025,10,21,2,30)
    assert t0+timedelta(minutes=30*(1458-1))==datetime(2025,11,20,11)
    t1=datetime(2025,11,21,17,30)
    assert t1+timedelta(minutes=30*(29-1))==datetime(2025,11,22,7,30)
    # Small synthetic target with two immediate QC0 anchor records and
    # a clean unmodified source/Stage28 match exercises all report writers.
    t=datetime(2025,10,1,3)
    seq=[t+timedelta(minutes=30*i) for i in range(-4,7)]
    s={a:{"TA_F":10.0,"VPD_F":3.0,
          "TA_F_QC":1 if t<=a<=t+timedelta(minutes=30) else 0,
          "VPD_F_QC":2 if t<=a<=t+timedelta(minutes=30) else 0} for a in seq}
    v={a:{"TA_USE":10.0,"VPD_USE":3.0,"PSRF":101325.0,"QBOT":0.005} for a in seq}
    rows,samples=evaluate(s,v,(("TEST",t.isoformat(sep=" "),
                                 (t+timedelta(minutes=30)).isoformat(sep=" "),2),))
    assert len(rows)==1 and len(samples)==12
    assert rows[0]["source_selected_numeric_comparison"]["TA_equals"]==2
    assert rows[0]["original_QC0_at_both_immediate_anchors"]
    print("STAGE03G SELF-TEST PASS: both historical run dates, QC0 anchors, T/VPD physical screens, tiny full audit and private-only output; NO SOURCE WRITES")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03f",type=Path)
    p.add_argument("--stage03b",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:selftest();return
    require(a.stage03f is not None and a.stage03f.is_file() and
            a.stage03b is not None and a.stage03b.is_file(),
            "Need original Stage03F and Stage03B reports")
    require(a.out_dir is not None and a.out_dir.is_dir() and
            not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
            "Use a NEW EMPTY private HOME output dir")
    old=json.loads(a.stage03f.read_text(encoding="utf-8"))
    parent=json.loads(a.stage03b.read_text(encoding="utf-8"))
    src,met=validate_old(old,parent)
    bounds=[(datetime.fromisoformat(start)-PADDING,
             datetime.fromisoformat(end)+PADDING) for _,start,end,n in RUN_SPECS]
    native,native_columns=capture(src,"TIMESTAMP_START",True,SRC_REQ,
                                   SRC_REQ|SRC_OPTIONAL,bounds)
    selected,selected_columns=capture(met,"time",False,SEL_REQ,SEL_REQ,bounds)
    reports,samples=evaluate(native,selected,RUN_SPECS)
    outcome={"stage":"STAGE03G_IT_TOR_TWO_ORIGINAL_QC12_RUNS_SOURCE_PHYSICS_AND_QC0_BOUNDARIES",
             "read_only":True,"science_release":False,"slurm_submitted":False,
             "original_source_or_CIME_written":False,
             "stage03f_source":str(a.stage03f),"stage03b_source":str(a.stage03b),
             "source_csv_path":str(src),"selected_stage28_path":str(met),
             "source_fields_present":native_columns,
             "selected_fields_present":selected_columns,
             "source_timestamps_in_two_padded_windows":len(native),
             "Stage28_timestamps_in_two_padded_windows":len(selected),
             "runs":reports,
             "science_warning":"This screens network-product TA/VPD/QC at original source-label timestamps. RH is derived from water saturation formula, not an independent RH measurement or ice-corrected proof. Network ERA fields are not independent evidence. Old Stage27 precise event identity, original instrument QC, dated rain accumulation, time-zone truth and IT-Tor soil ORGANIC=0 remain HOLD. No automatic ERA substitution or production approval."}
    output=a.out_dir/"stage03g_IT_Tor_two_runs_physics_anchors_PRIVATE.json"
    csvfile=a.out_dir/"stage03g_IT_Tor_two_runs_boundary_values_PRIVATE.csv"
    with output.open("x",encoding="utf-8") as f:
        json.dump(outcome,f,indent=2,ensure_ascii=False);f.write("\n")
    with csvfile.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=ENDPOINT_FIELDS)
        writer.writeheader();writer.writerows(samples)
    for x in reports:
        print("RUN",x["id"],"HH",x["half_hours"],
              "QC_PAIRS",x["original_QC_pairs"],
              "RH_RANGE",x["selected_reconstructed_RH_range"],
              "SCREENS",x["physical_screen_counts"],
              "COMPARE",x["source_selected_numeric_comparison"])
        for side in x["selected_source_label_boundary_steps"]:
            print(" BOUNDARY",side["side"],"DT_C",side["deltaT_C"],
                  "DVPD_hPa",side["deltaVPD_hPa"],
                  "T_GT4",side["deltaT_abs_gt4C"],
                  "VPD_GT5",side["deltaVPD_abs_gt5hPa"])
    print("PRIVATE_JSON",output)
    print("PRIVATE_ENDPOINTS",csvfile)
    print("STAGE03G READONLY COMPLETE; SOURCE SCIENCE AND SOIL HOLD; NO CIME/NETCDF/SLURM")

if __name__=="__main__":
    main()
