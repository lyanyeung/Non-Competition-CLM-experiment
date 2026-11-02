#!/usr/bin/env python3
"""ICOS Batch04 Stage03I: reuse 6 Stage03H events; examine QC1/QC2 source handoffs.

READ ONLY. Read only the saved PRIVATE Stage03H event JSON and 54-row
+/-2h boundary CSV. Do not scan FLUXMET/Stage28 again, rebuild any NC,
fetch ERA5, change a single value or submit jobs. A numerical discontinuity
relative to packaged ERA is a REVIEW CANDIDATE, not science approval.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from pathlib import Path

STAGE="STAGE03H_IT_TOR_SIX_QC12_INTERNAL_TEMPERATURE_JUMPS_SOURCE_FORENSICS"
EXPECTED={
    "TJ1128":"2025-11-13 14:30:00",
    "TJ1131":"2025-11-13 16:00:00",
    "TJ1134":"2025-11-13 17:30:00",
    "TJ1162":"2025-11-14 07:30:00",
    "TJ1229":"2025-11-15 17:00:00",
    "TJ1373":"2025-11-18 17:00:00",
}
COLUMNS=("jump_id","current","previous","QC_transition","delta_T_C",
         "delta_VPD_hPa","packaged_ERA_delta_T_C",
         "previous_T_minus_ERA_C","current_T_minus_ERA_C",
         "QC1_T_minus_ERA_C","QC2_T_minus_ERA_C",
         "QC1_QC2_offset_gap_C","ERA_near_flat_abs_lt2C",
         "original_source_equals_selected_at_jump",
         "evidence_class","scientific_action")

def require(condition,message):
    if not condition:raise ValueError(message)

def val(x):
    if x is None or str(x).strip()=="":
        return None
    try:
        v=float(x)
        return v if math.isfinite(v) and v>-9990 else None
    except (ValueError,TypeError):
        return None

def near(x,y,eps=1e-6):
    return x is not None and y is not None and abs(x-y)<=eps

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def load_inputs(report,context):
    require(report.is_file() and context.is_file() and
            not report.is_symlink() and not context.is_symlink(),
            "Use the existing Stage03H PRIVATE JSON and CSV (no symlinks)")
    require(report.stat().st_size<5_000_000 and
            context.stat().st_size<5_000_000,
            "Unexpectedly large Stage03H event reports")
    data=json.loads(report.read_text(encoding="utf-8"))
    require(data.get("stage")==STAGE and data.get("read_only") is True and
            data.get("science_release") is False and
            data.get("slurm_submitted") is False and
            data.get("model_or_source_modified") is False,
            "Original Stage03H source-provenance HOLD report is required")
    events=data.get("jump_provenance",[])
    require(isinstance(events,list) and len(events)==6 and
            {r.get("jump_id") for r in events}==set(EXPECTED),
            "Expected six exact original Stage03H temperature jumps")
    with context.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        needed={"jump_id","relative_HH","time","source_TA_F_C",
                "source_TA_F_QC","source_TA_ERA_C","selected_TA_USE_C",
                "source_VPD_F_QC","source_VPD_F_hPa","selected_VPD_USE_hPa"}
        require(needed<=set(reader.fieldnames or []),
                "Original Stage03H context schema differs")
        rows=list(reader)
    require(len(rows)==54,"Expected exactly 6 x 9 original +/-2h records")
    return data,events,rows

def analyze(events,rows):
    by=defaultdict(dict)
    for row in rows:
        key=row["jump_id"]
        require(key in EXPECTED,"Unknown event "+key)
        i=int(row["relative_HH"])
        require(-4<=i<=4 and i not in by[key],
                "Duplicate/invalid relative half-hour "+key)
        by[key][i]=row
    output=[]
    for e in sorted(events,key=lambda a:a["current"]):
        key=e["jump_id"]
        require(e["current"]==EXPECTED[key],"Historic jump time unexpectedly changed")
        require(set(by[key])==set(range(-4,5)),"Nine complete context records required: "+key)
        present=datetime.fromisoformat(e["current"])
        previous=present-timedelta(minutes=30)
        require(e["previous"]==str(previous),"Unexpected prior HH "+key)
        for i,r in by[key].items():
            require(datetime.fromisoformat(r["time"])==
                    present+timedelta(minutes=30*i),
                    "Original source-label time mismatch "+key)
        left,right=by[key][-1],by[key][0]
        t0=val(left["selected_TA_USE_C"]);t1=val(right["selected_TA_USE_C"])
        r0=val(left["source_TA_F_C"]);r1=val(right["source_TA_F_C"])
        era0=val(left["source_TA_ERA_C"]);era1=val(right["source_TA_ERA_C"])
        require(None not in (t0,t1,r0,r1,era0,era1),
                "Original/selected/ERA temperature missing at "+key)
        require(near(t1-t0,val(e["selected_delta_T_C"])) and
                near(r1-r0,val(e["original_source_delta_T_C"])) and
                near(era1-era0,val(e["source_ERA_delta_T_C"])),
                "Stage03H source jump values changed at "+key)
        require(abs(t1-t0)>5 and
                near(r0,t0) and near(r1,t1) and
                e.get("source_original_T_equals_Stage28_both_HH") is True,
                "Stage03H selected source equality or >5C criterion changed")
        qc0=val(left["source_TA_F_QC"]);qc1=val(right["source_TA_F_QC"])
        require((qc0,qc1) in ((1.0,2.0),(2.0,1.0)) and
                near(qc0,val(e["source_previous_TA_QC"])) and
                near(qc1,val(e["source_current_TA_QC"])),
                "QC1/QC2 source handoff no longer verified: "+key)
        require(near(qc0,val(left["source_VPD_F_QC"])) and
                near(qc1,val(right["source_VPD_F_QC"])),
                "Paired T/VPD source QC class unexpectedly diverged: "+key)
        offset0=t0-era0;offset1=t1-era1
        off1=offset0 if qc0==1 else offset1
        off2=offset0 if qc0==2 else offset1
        # This compares *relative* agreement to packaged ERA. ERA may be
        # used in QC2 generation, so it is NOT independent truth evidence.
        nearest=("QC1_NEARER_PACKAGED_ERA" if abs(off1)+1<abs(off2) else
                 "QC2_NEARER_PACKAGED_ERA" if abs(off2)+1<abs(off1) else
                 "SIMILAR_PACKAGED_ERA_DISTANCE")
        suspect=abs(t1-t0)>5 and abs(era1-era0)<2 and qc0!=qc1
        r={"jump_id":key,"current":e["current"],"previous":e["previous"],
           "QC_transition":f"{int(qc0)}->{int(qc1)}",
           "delta_T_C":t1-t0,
           "delta_VPD_hPa":val(e.get("selected_delta_VPD_hPa")),
           "packaged_ERA_delta_T_C":era1-era0,
           "previous_T_minus_ERA_C":offset0,
           "current_T_minus_ERA_C":offset1,
           "QC1_T_minus_ERA_C":off1,"QC2_T_minus_ERA_C":off2,
           "QC1_QC2_offset_gap_C":off1-off2,
           "ERA_near_flat_abs_lt2C":abs(era1-era0)<2,
           "original_source_equals_selected_at_jump":True,
           "evidence_class":(
               "QC1_QC2_HANDOFF_STEP_REVIEW_"+nearest
               if suspect else "NON_HANDOFF_STEP_REVIEW"),
           "scientific_action":"HOLD_NO_AUTOMATIC_REPAIR"}
        output.append(r)
    return output

def self_test():
    # Six source/selected jumps and one missing-value rejection, all local.
    jumps=[];samples=[]
    for key,stamp in EXPECTED.items():
        t=datetime.fromisoformat(stamp)
        qc0,qc1=(2,1) if key!="TJ1131" and key!="TJ1162" else (1,2)
        lt,rt=(10.0,-2.0) if qc0==2 else (-2.0,10.0)
        event={"jump_id":key,"previous":str(t-timedelta(minutes=30)),
               "current":str(t),"selected_delta_T_C":rt-lt,
               "original_source_delta_T_C":rt-lt,
               "source_ERA_delta_T_C":0.1,
               "source_previous_TA_QC":qc0,"source_current_TA_QC":qc1,
               "source_original_T_equals_Stage28_both_HH":True}
        jumps.append(event)
        for i in range(-4,5):
            qc=qc0 if i<0 else qc1
            temp=lt if i<0 else rt
            era=8.0 if i<0 else 8.1
            samples.append({"jump_id":key,"relative_HH":str(i),
                            "time":str(t+timedelta(minutes=30*i)),
                            "selected_TA_USE_C":str(temp),
                            "source_TA_F_C":str(temp),
                            "source_TA_ERA_C":str(era),
                            "source_TA_F_QC":str(qc),
                            "source_VPD_F_QC":str(qc)})
    analyzed=analyze(jumps,samples)
    assert len(analyzed)==6
    assert all(x["ERA_near_flat_abs_lt2C"] and
               x["scientific_action"]=="HOLD_NO_AUTOMATIC_REPAIR" for x in analyzed)
    assert Counter(x["QC_transition"] for x in analyzed)=={"2->1":4,"1->2":2}
    print("STAGE03I SELF-TEST PASS: six event source and 54 boundary records, QC1/2 handoff, ERA-relative offsets, HOLD; NO SOURCE WRITES")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03h",type=Path)
    p.add_argument("--context",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    require(a.stage03h is not None and a.context is not None,
            "Original saved Stage03H private JSON and 54-row context CSV required")
    require(a.out_dir is not None and a.out_dir.is_dir() and
            not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
            "Output must be NEW EMPTY private directory")
    prior,events,raw=load_inputs(a.stage03h,a.context)
    analyzed=analyze(events,raw)
    report={
      "stage":"STAGE03I_IT_TOR_6_QC12_HANDOFF_ERA_RELATIVE_EVIDENCE",
      "read_only":True,"science_release":False,
      "original_source_or_model_modified":False,"slurm_submitted":False,
      "source_stage03h":str(a.stage03h),
      "source_context_csv":str(a.context),
      "original_stage03h_SHA256":digest(a.stage03h),
      "original_context_SHA256":digest(a.context),
      "jump_count":len(analyzed),
      "source_QC_transitions":dict(Counter(x["QC_transition"] for x in analyzed)),
      "ERA_near_flat_jump_count":sum(x["ERA_near_flat_abs_lt2C"] for x in analyzed),
      "events":analyzed,
      "interpretation":"Strong QC1/QC2 product-handoff discontinuity evidence is NOT independent tower instrument error proof. The source-packaged ERA may be a gap-filling input, so agreement with it is not independent ERA5-Land verification. Hold all six events and avoid modifying a 1458-HH fill run until source QC semantics/independent evidence support a scoped decision.",
    }
    j=a.out_dir/"stage03i_IT_Tor_six_switches_ERA_relative_PRIVATE.json"
    c=a.out_dir/"stage03i_IT_Tor_six_switches_review_PRIVATE.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS)
        w.writeheader();w.writerows(analyzed)
    for r in analyzed:
        print("HANDOFF",r["jump_id"],r["current"],
              "QC",r["QC_transition"],
              "DT_C",round(r["delta_T_C"],3),
              "ERA_DT_C",round(r["packaged_ERA_delta_T_C"],3),
              "QC1_MINUS_ERA",round(r["QC1_T_minus_ERA_C"],3),
              "QC2_MINUS_ERA",round(r["QC2_T_minus_ERA_C"],3),
              "CLASS",r["evidence_class"])
    print("STAGE03I_SUMMARY",len(analyzed),"HANDOFFS",
          report["source_QC_transitions"],"ERA_NEAR_FLAT",
          report["ERA_near_flat_jump_count"],
          "SCIENCE_HOLD True; NO AUTOMATIC REPAIRS")
    print("PRIVATE_JSON",j)
    print("PRIVATE_CSV",c)
    print("STAGE03I COMPLETE: PRIOR REPORTS ONLY, NO SOURCE/NETCDF/CIME/SLURM")

if __name__=="__main__":
    main()
