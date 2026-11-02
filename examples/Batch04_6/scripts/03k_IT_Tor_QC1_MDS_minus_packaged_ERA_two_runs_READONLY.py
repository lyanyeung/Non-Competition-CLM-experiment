#!/usr/bin/env python3
"""Stage03K: IT-Tor source MDS-vs-packaged-ERA bias only within TWO known runs.

Use completed Stage03F and Stage03J private provenance registers; scan
IT-Tor original network product only ONCE, retaining only 1458+29
identified non-QC0 half-hours and their immediate QC0 anchors. No new
Stage28, DATM, other station, entire-series numerical QC, or model run.

Report if QC1-MDS cold offset seen at six handoffs is widespread or
localized. ERA values packaged in the SAME product are correlated gapfill
references, not independent temperature validation. No replacements.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path

F_STAGE="STAGE03F_IT_TOR_2025_OCT_NOV_HISTORICAL_1458HH_QC1_QC2_EPISODE_FORENSICS"
J_STAGE="STAGE03J_IT_TOR_OFFICIAL_QC1_MDS_QC2_ERA_CONSOLIDATION_SOURCE_PROVENANCE"
RUNS=(("LONG_1458","2025-10-21 02:30:00","2025-11-20 11:00:00",1458,558,900),
      ("SHORT_29","2025-11-21 17:30:00","2025-11-22 07:30:00",29,29,0))
FIELDS={"TIMESTAMP_START","TA_F","TA_F_QC","TA_F_MDS","TA_F_MDS_QC","TA_ERA",
        "VPD_F","VPD_F_QC","VPD_F_MDS","VPD_F_MDS_QC","VPD_ERA"}
EPS=0.005

def ck(cond,msg):
    if not cond:raise ValueError(msg)

def number(s):
    try:
        v=float(s)
        return v if math.isfinite(v) and v>-9990 else None
    except (TypeError,ValueError):return None

def time(s):
    v=str(s).strip()
    if v.endswith(".0") and v[:-2].isdigit():v=v[:-2]
    try:return datetime.strptime(v,"%Y%m%d%H%M")
    except ValueError:return None

def percentile(vals,p):
    if not vals:return None
    a=sorted(vals);z=(len(a)-1)*p
    lo=int(math.floor(z));hi=int(math.ceil(z))
    return a[lo]*(hi-z)+a[hi]*(z-lo) if lo!=hi else a[lo]

def stats(values):
    a=[x for x in values if x is not None]
    return {"N":len(a),"min":min(a) if a else None,
            "p05":percentile(a,.05),"median":percentile(a,.5),
            "p95":percentile(a,.95),"max":max(a) if a else None,
            "mean":sum(a)/len(a) if a else None,
            "below_minus5C":sum(x<-5 for x in a),
            "below_minus10C":sum(x<-10 for x in a)}

def validated_inputs(f,j):
    ck(f.get("stage")==F_STAGE and f.get("read_only") is True and
       f.get("science_release") is False and f.get("slurm_submitted") is False,
       "Original Stage03F science-HOLD evidence missing")
    ck(j.get("stage")==J_STAGE and j.get("read_only") is True and
       j.get("science_release") is False and j.get("slurm_submitted") is False and
       j.get("source_or_model_modified") is False and
       j.get("context_records_reviewed")==54,
       "Original completed Stage03J six-event source consolidation evidence missing")
    ck(j.get("official_MDS_product_fields_missing")==[] and
       len(j.get("six_handoff_summaries",[]))==6,
       "Original Stage03J six MDS fields/decisions not pinned")
    ck(all(x.get("QC1_T_F_equals_MDS") is True and
           x.get("QC2_T_F_equals_ERA") is True and
           x.get("QC1_VPD_F_equals_MDS") is True and
           x.get("QC2_VPD_F_equals_ERA") is True
           for x in j["six_handoff_summaries"]),
       "Stage03J source handoff family tests not all verified")
    known=f.get("run_types",{}).get("PAIR_QC1_OR_QC2",[])
    ck(len(known)==2,"Expected only two original QC1/2 intervals")
    for _,start,end,n,_,_ in RUNS:
        ck(sum(x.get("start")==start and x.get("end")==end and
               x.get("half_hours")==n and x.get("both_sides_QC0") is True
               for x in known)==1,
           "Stage03F old run boundaries or QC0 source anchors changed: "+start)
    path=Path(j.get("original_network_product_path",""))
    prior=Path(f.get("source_paths",{}).get("original_network_product",""))
    ck(path.is_absolute() and path==prior and path.is_file() and
       not path.is_symlink(),"Original IT-Tor network source path mismatch")
    return path

def times_for_runs():
    runs={}
    for name,start,end,n,q1,q2 in RUNS:
        a=datetime.fromisoformat(start)
        b=datetime.fromisoformat(end)
        t=[a+timedelta(minutes=30*i) for i in range(n)]
        ck(t[-1]==b,"Specified run length/date conflict "+name)
        runs[name]=t
    checkset={t for group in runs.values() for t in group}
    for group in runs.values():
        checkset.add(group[0]-timedelta(minutes=30))
        checkset.add(group[-1]+timedelta(minutes=30))
    return runs,checkset

def scan_original(path,required):
    observed={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        hd=set(r.fieldnames or [])
        ck(FIELDS<=hd,"Original product lacks Stage03J-confirmed MDS/ERA fields "+
           str(FIELDS-hd))
        for row in r:
            stamp=time(row["TIMESTAMP_START"])
            if stamp not in required:continue
            ck(stamp not in observed,"Duplicate original source HH "+str(stamp))
            observed[stamp]={k:number(row[k]) for k in FIELDS if k!="TIMESTAMP_START"}
    ck(set(observed)==required,"Missing saved IT-Tor source label timestamps "+
       str(len(required-set(observed))))
    return observed

def partition_qc1(sub,source):
    out=[];begin=None
    for i,t in enumerate(sub):
        is_qc1=source[t]["TA_F_QC"]==source[t]["VPD_F_QC"]==1
        if is_qc1 and begin is None:begin=i
        if begin is not None and (not is_qc1 or i==len(sub)-1):
            last=i if is_qc1 and i==len(sub)-1 else i-1
            pts=sub[begin:last+1]
            diffs=[source[z]["TA_F"]-source[z]["TA_ERA"]
                   for z in pts if None not in (source[z]["TA_F"],source[z]["TA_ERA"])]
            out.append({"start":str(pts[0]),"end":str(pts[-1]),
                        "QC1_halfhours":len(pts),**stats(diffs)})
            begin=None
    return out

def audit(data):
    runs,needed=times_for_runs()
    ck(set(data)==needed,"Original source context mismatch")
    results=[];episodes=[]
    for name,_,_,length,expected_q1,expected_q2 in RUNS:
        ts=runs[name]
        qc1=[];qc2=[];tdiff=[];vdiff=[]
        provenance=Counter()
        for t in ts:
            r=data[t];qa=r["TA_F_QC"];qv=r["VPD_F_QC"]
            ck(qa==qv and qa in (1,2),"Mixed/unknown QC1/2 within "+name)
            key=int(qa)
            provenance[key]+=1
            k="MDS" if key==1 else "ERA"
            src_t=r["TA_F_MDS"] if key==1 else r["TA_ERA"]
            src_v=r["VPD_F_MDS"] if key==1 else r["VPD_ERA"]
            # These are the officially described product branches.
            if None in (r["TA_F"],r["VPD_F"],src_t,src_v):
                provenance["nonfinite_branch_source"]+=1
            elif abs(r["TA_F"]-src_t)>EPS or abs(r["VPD_F"]-src_v)>EPS:
                provenance["branch_selection_disagrees"]+=1
            if key==1:
                qc1.append(r)
                if r["TA_F_MDS_QC"]!=1:provenance["TA_MDS_QC_not_1"]+=1
                if r["VPD_F_MDS_QC"]!=1:provenance["VPD_MDS_QC_not_1"]+=1
                if None not in (r["TA_F"],r["TA_ERA"]):
                    tdiff.append(r["TA_F"]-r["TA_ERA"])
                if None not in (r["VPD_F"],r["VPD_ERA"]):
                    vdiff.append(r["VPD_F"]-r["VPD_ERA"])
            else:qc2.append(r)
        ck(provenance[1]==expected_q1 and provenance[2]==expected_q2,
           "Stage03F verified QC1 and QC2 counts drifted for "+name)
        ck(data[ts[0]-timedelta(minutes=30)]["TA_F_QC"]==
           data[ts[0]-timedelta(minutes=30)]["VPD_F_QC"]==0 and
           data[ts[-1]+timedelta(minutes=30)]["TA_F_QC"]==
           data[ts[-1]+timedelta(minutes=30)]["VPD_F_QC"]==0,
           "Both original immediate QC0 anchors changed: "+name)
        eps=partition_qc1(ts,data)
        episodes.extend([{"run":name,**x} for x in eps])
        results.append({"run":name,"total_HH":length,
          "QC1_MDS_HH":expected_q1,"QC2_ERA_HH":expected_q2,
          "MDS_minus_packaged_ERA_T_C":stats(tdiff),
          "MDS_minus_packaged_ERA_VPD_hPa":stats(vdiff),
          "QC1_subrun_count":len(eps),
          "QC1_max_contiguous_HH":max((x["QC1_halfhours"] for x in eps),default=0),
          "source_rules_issues":dict(provenance),
          "science_release":False})
    return results,episodes

def self_test():
    t=[datetime(2025,10,21,2,30)+timedelta(minutes=30*i)
       for i in range(1458)]
    s=[datetime(2025,11,21,17,30)+timedelta(minutes=30*i)
       for i in range(29)]
    assert t[-1]==datetime(2025,11,20,11)
    assert s[-1]==datetime(2025,11,22,7,30)
    _,need=times_for_runs()
    rows={}
    for i,p in enumerate(t+s):
        q=1 if i<558 or i>=1458 else 2
        temp=-10 if q==1 else 0
        rows[p]={"TA_F":temp,"VPD_F":1 if q==1 else 2,
                 "TA_F_QC":q,"VPD_F_QC":q,
                 "TA_F_MDS":-10,"TA_F_MDS_QC":1,
                 "VPD_F_MDS":1,"VPD_F_MDS_QC":1,
                 "TA_ERA":0,"VPD_ERA":2}
    for p in need-set(rows):
        rows[p]={"TA_F":0,"VPD_F":2,"TA_F_QC":0,"VPD_F_QC":0,
                 "TA_F_MDS":0,"TA_F_MDS_QC":0,
                 "VPD_F_MDS":2,"VPD_F_MDS_QC":0,
                 "TA_ERA":0,"VPD_ERA":2}
    out,eps=audit(rows)
    assert len(out)==2 and out[0]["QC1_MDS_HH"]==558
    assert out[0]["MDS_minus_packaged_ERA_T_C"]["below_minus10C"]==0
    assert out[1]["QC1_MDS_HH"]==29 and len(eps)==2
    assert all(r["science_release"] is False for r in out)
    print("STAGE03K SELF-TEST PASS: 558+29 QC1, 900 QC2, original MDS/ERA selection, QC0 boundaries, bias distributions; NO WRITES")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03f",type=Path)
    p.add_argument("--stage03j",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    ck(a.stage03f is not None and a.stage03f.is_file() and
       a.stage03j is not None and a.stage03j.is_file(),
       "Stage03F and Stage03J existing private JSON reports are required")
    ck(a.out_dir is not None and a.out_dir.is_dir() and
       not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
       "Use a NEW EMPTY private HOME output directory")
    f=json.loads(a.stage03f.read_text(encoding="utf-8"))
    j=json.loads(a.stage03j.read_text(encoding="utf-8"))
    source=validated_inputs(f,j)
    _,needed=times_for_runs()
    extracted=scan_original(source,needed)
    runs,eps=audit(extracted)
    report={"stage":"STAGE03K_IT_TOR_QC1_MDS_RELATIVE_ERA_BIAS_2_RUNS_ONLY",
        "read_only":True,"science_release":False,"model_or_source_modified":False,
        "slurm_submitted":False,"source_original":str(source),
        "stage03f_report":str(a.stage03f),"stage03j_report":str(a.stage03j),
        "time_labels_selected":len(extracted),
        "two_runs":runs,
        "scientific_limitations":"MDS versus packaged ERA difference is not independent sensor validation. QC1 and QC2 gapfill families may share input data; no wholesale ERA replacement, no 1458-HH or 587-HH scientific approval. Stage28 already inherits source values. Independent original tower/neighbor source evidence or sensitivity testing requires separate approval."}
    output=a.out_dir/"stage03k_IT_Tor_QC1_MDS_vs_ERA_bias_2_runs_PRIVATE.json"
    details=a.out_dir/"stage03k_IT_Tor_QC1_contiguous_segments_PRIVATE.csv"
    with output.open("x",encoding="utf-8") as handle:
        json.dump(report,handle,indent=2,ensure_ascii=False);handle.write("\n")
    with details.open("x",encoding="utf-8",newline="") as handle:
        cols=("run","start","end","QC1_halfhours","N","min","p05","median",
              "p95","max","mean","below_minus5C","below_minus10C")
        w=csv.DictWriter(handle,fieldnames=cols);w.writeheader();w.writerows(eps)
    for row in runs:
        x=row["MDS_minus_packaged_ERA_T_C"]
        print("RUN",row["run"],"QC1",row["QC1_MDS_HH"],"QC2",row["QC2_ERA_HH"],
            "QC1_SEGMENTS",row["QC1_subrun_count"],
            "MAX_QC1_HH",row["QC1_max_contiguous_HH"],
            "MDS_MINUS_PACKAGED_ERA_T_C",x,
            "QC1_VPD_MINUS_ERA",row["MDS_minus_packaged_ERA_VPD_hPa"],
            "BRANCH_RULE_FLAGS",row["source_rules_issues"])
    print("PRIVATE_JSON",output)
    print("PRIVATE_QC1_EPISODES",details)
    print("STAGE03K COMPLETE: 2 HISTORIC RUNS ONLY, SCIENCE HOLD, NO SOURCE/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
