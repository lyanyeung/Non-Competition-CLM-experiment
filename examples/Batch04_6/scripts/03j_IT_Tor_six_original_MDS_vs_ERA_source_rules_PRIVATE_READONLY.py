#!/usr/bin/env python3
"""Stage03J: validate IT-Tor six QC1/MDS ↔ QC2/ERA source-product handoffs.

Grounded in FLUXNET official FULLSET/SUBSET variable definitions:
  TA_F_QC/VPD_F_QC 0 measured, 1 good MDS gapfill, 2 downscaled ERA.
  Consolidated TA_F/VPD_F selects MDS where MDS_QC is 0 or 1;
  otherwise it selects the packaged downscaled ERA source.
Official source: https://fluxnet.org/data/fluxnet2015-dataset/fullset-data-product/

Prerequisites: passed Stage03H private JSON + 54-row context CSV + passed
Stage03I JSON. Read ONLY original IT-Tor FLUXMET source CSV and select the
EXACT 54 original context rows (unique timestamps may be fewer). The
officially-described MDS fields are optional: if absent, report a provenance
gap rather than inventing their values. Never replace data, rerun 1458 HH,
or approve a scientific model forcing source. PRIVATE outputs only.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path

H_STAGE="STAGE03H_IT_TOR_SIX_QC12_INTERNAL_TEMPERATURE_JUMPS_SOURCE_FORENSICS"
I_STAGE="STAGE03I_IT_TOR_6_QC12_HANDOFF_ERA_RELATIVE_EVIDENCE"
SITES=("TJ1128","TJ1131","TJ1134","TJ1162","TJ1229","TJ1373")
SOURCE_TIME="TIMESTAMP_START"
FIELDS=("TA_F","TA_F_QC","TA_F_MDS","TA_F_MDS_QC","TA_ERA",
        "VPD_F","VPD_F_QC","VPD_F_MDS","VPD_F_MDS_QC","VPD_ERA")
MUST_HAVE={"TA_F","TA_F_QC","TA_ERA","VPD_F","VPD_F_QC","VPD_ERA"}
OPTIONAL_MDS={"TA_F_MDS","TA_F_MDS_QC","VPD_F_MDS","VPD_F_MDS_QC"}
EPS=0.005

def require(c,why):
    if not c:raise ValueError(why)

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def num(v):
    try:
        n=float(v)
        return n if math.isfinite(n) and n>-9990 else None
    except (TypeError,ValueError):return None

def equivalent(a,b):
    return a is not None and b is not None and abs(a-b)<=EPS

def source_timestamp(s):
    try:return datetime.strptime(str(s).strip(),"%Y%m%d%H%M")
    except ValueError:return None

def validate_paths(hfile,cfile,ifile):
    paths=[hfile,cfile,ifile]
    require(all(x.is_file() and not x.is_symlink() and x.stat().st_size<5_000_000
                for x in paths),"Require exact small private Stage03H/I reports, no symlinks")
    h=json.loads(hfile.read_text(encoding="utf-8"))
    i=json.loads(ifile.read_text(encoding="utf-8"))
    require(h.get("stage")==H_STAGE and h.get("read_only") is True and
            h.get("science_release") is False and
            h.get("model_or_source_modified") is False,
            "Stage03H HOLD science source changed")
    require(i.get("stage")==I_STAGE and i.get("read_only") is True and
            i.get("science_release") is False and
            i.get("original_source_or_model_modified") is False and
            i.get("jump_count")==6,
            "Stage03I six-jump source analysis missing")
    require(digest(hfile)==i.get("original_stage03h_SHA256") and
            digest(cfile)==i.get("original_context_SHA256"),
            "Stage03H private report content changed since Stage03I")
    require({r.get("jump_id") for r in i.get("events",[])}==set(SITES),
            "Stage03I original event identity changed")
    events=h.get("jump_provenance",[])
    require(len(events)==6 and {e.get("jump_id") for e in events}==set(SITES),
            "Stage03H original event IDs changed")
    with cfile.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        fields=set(r.fieldnames or [])
        require({"jump_id","relative_HH","time","source_TA_F_C",
                 "source_TA_F_QC","source_VPD_F_hPa","source_VPD_F_QC",
                 "source_TA_ERA_C","source_VPD_ERA_hPa"}<=fields,
                 "Stage03H context required source columns absent")
        context=list(r)
    require(len(context)==54 and
            Counter(x.get("jump_id") for x in context)==Counter({k:9 for k in SITES}),
            "Stage03H must have 54 context rows, nine per event")
    original=Path(h.get("source_original",""))
    require(original.is_absolute() and original.is_file() and
            not original.is_symlink(),"Original pinned IT-Tor FLUXMET source absent")
    return h,i,context,original

def original_columns(path,needed):
    """One forward CSV pass to pull EXACT source-label timestamps only."""
    out={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        hd=set(r.fieldnames or [])
        require(SOURCE_TIME in hd and MUST_HAVE<=hd,
                "Original FLUXMET source lacks mandatory consolidated/ERA columns")
        cols=[c for c in FIELDS if c in hd]
        for row in r:
            t=source_timestamp(row[SOURCE_TIME])
            if t not in needed:continue
            require(t not in out,"Duplicate source-label timestamp "+str(t))
            out[t]={c:num(row.get(c)) for c in cols}
    require(set(out)==needed,"Missing original source-label context rows")
    return out,cols,sorted(OPTIONAL_MDS-hd)

def source_family(q):
    if q==0:return "MEASURED"
    if q==1:return "MDS"
    if q==2:return "PACKAGED_ERA"
    return "UNKNOWN_QC"

def examine(context,original):
    checked=[];per=defaultdict(list)
    for item in context:
        stamp=datetime.fromisoformat(item["time"])
        row=original[stamp]
        for typ in ("TA","VPD"):
            key="source_TA_F_C" if typ=="TA" else "source_VPD_F_hPa"
            qkey="source_TA_F_QC" if typ=="TA" else "source_VPD_F_QC"
            era_key="source_TA_ERA_C" if typ=="TA" else "source_VPD_ERA_hPa"
            require(equivalent(row[typ+"_F"],num(item[key])) and
                    row[typ+"_F_QC"]==num(item[qkey]) and
                    equivalent(row[typ+"_ERA"],num(item[era_key])),
                    "Original source values changed since saved Stage03H context: "+
                    str(stamp)+" "+typ)
        stampstr=item["time"]
        qc=int(row["TA_F_QC"]) if row["TA_F_QC"] in (0,1,2) else None
        vqc=int(row["VPD_F_QC"]) if row["VPD_F_QC"] in (0,1,2) else None
        result={"jump_id":item["jump_id"],"relative_HH":int(item["relative_HH"]),
                "time":stampstr,"TA_F_QC":qc,"VPD_F_QC":vqc,
                "TA_source_family":source_family(qc),
                "VPD_source_family":source_family(vqc)}
        for typ in ("TA","VPD"):
            q=result[typ+"_F_QC"]
            selected=row[typ+"_F"]
            mds=row.get(typ+"_F_MDS")
            mdsqc=row.get(typ+"_F_MDS_QC")
            era=row[typ+"_ERA"]
            expected=mds if q in (0,1) else era if q==2 else None
            match=None if expected is None else equivalent(selected,expected)
            result.update({
                typ+"_F":selected,typ+"_F_MDS":mds,
                typ+"_F_MDS_QC":mdsqc,typ+"_ERA":era,
                typ+"_official_consolidation_match":match,
                typ+"_F_minus_ERA":None if selected is None or era is None
                                          else selected-era,
                typ+"_MDS_QC_matches_consolidated_if_0or1":(
                    None if q not in (0,1) or mdsqc is None else q==mdsqc),
            })
        checked.append(result)
        per[item["jump_id"]].append(result)
    summaries=[]
    for key in SITES:
        rows=per[key]
        require(len(rows)==9 and
                {x["relative_HH"] for x in rows}==set(range(-4,5)),
                "Invalid nine-neighborhood provenance "+key)
        edge={r["relative_HH"]:r for r in rows}
        before,after=edge[-1],edge[0]
        require((before["TA_F_QC"],after["TA_F_QC"]) in ((1,2),(2,1))
                and before["TA_F_QC"]==before["VPD_F_QC"]
                and after["TA_F_QC"]==after["VPD_F_QC"],
                "Historical paired source QC handoff no longer valid "+key)
        q1=before if before["TA_F_QC"]==1 else after
        q2=before if before["TA_F_QC"]==2 else after
        offset=lambda r,typ:r[typ+"_F_minus_ERA"]
        summaries.append({
            "jump_id":key,"time":after["time"],
            "QC_transition":f'{before["TA_F_QC"]}->{after["TA_F_QC"]}',
            "QC1_T_MDS_minus_ERA_C":offset(q1,"TA"),
            "QC2_T_ERA_minus_ERA_C":offset(q2,"TA"),
            "QC1_T_F_equals_MDS":q1["TA_official_consolidation_match"],
            "QC2_T_F_equals_ERA":q2["TA_official_consolidation_match"],
            "QC1_VPD_F_equals_MDS":q1["VPD_official_consolidation_match"],
            "QC2_VPD_F_equals_ERA":q2["VPD_official_consolidation_match"],
            "QC1_T_MDS_QC_is_1":q1["TA_F_MDS_QC"]==1 if
                                     q1["TA_F_MDS_QC"] is not None else None,
            "QC1_VPD_MDS_QC_is_1":q1["VPD_F_MDS_QC"]==1 if
                                     q1["VPD_F_MDS_QC"] is not None else None,
            "source_scientific_status":"HOLD",
        })
    return checked,summaries

def self_test():
    # Six exact transitions, nine half-hours each: QC1 must select MDS,
    # QC2 must select ERA, with no invented local observation QC0.
    source={}
    context=[]
    for j,key in enumerate(SITES):
        t0=datetime(2025,11,13,0)+__import__("datetime").timedelta(days=j)
        for k in range(-4,5):
            t=t0+__import__("datetime").timedelta(minutes=30*k)
            qc=2 if k<0 else 1
            source[t]={"TA_F":0.0 if qc==2 else -10.0,
                       "TA_F_QC":qc,"TA_F_MDS":-10.0,
                       "TA_F_MDS_QC":1,"TA_ERA":0.0,
                       "VPD_F":3.0 if qc==2 else 1.0,
                       "VPD_F_QC":qc,"VPD_F_MDS":1.0,
                       "VPD_F_MDS_QC":1,"VPD_ERA":3.0}
            context.append({"jump_id":key,"relative_HH":str(k),
                            "time":str(t),"source_TA_F_C":
                                 str(source[t]["TA_F"]),
                            "source_TA_F_QC":str(qc),
                            "source_TA_ERA_C":"0",
                            "source_VPD_F_hPa":str(source[t]["VPD_F"]),
                            "source_VPD_F_QC":str(qc),
                            "source_VPD_ERA_hPa":"3"})
    rows,summary=examine(context,source)
    assert len(rows)==54 and len(summary)==6
    assert all(x["QC1_T_F_equals_MDS"] and
               x["QC2_T_F_equals_ERA"] and
               x["QC1_VPD_F_equals_MDS"] and
               x["QC2_VPD_F_equals_ERA"] for x in summary)
    assert all(x["source_scientific_status"]=="HOLD" for x in summary)
    print("STAGE03J SELF-TEST PASS: six QC1/MDS-to-QC2/ERA source transitions, 54 context rows, missing-source guard; no repairs or writes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03h",type=Path)
    p.add_argument("--context",type=Path)
    p.add_argument("--stage03i",type=Path)
    p.add_argument("--out-dir",type=Path)
    a=p.parse_args()
    if a.self_test:self_test();return
    require(a.stage03h is not None and a.context is not None and
            a.stage03i is not None,"Require passed original Stage03H/I private files")
    require(a.out_dir is not None and a.out_dir.is_dir() and
            not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
            "Use a new empty private HOME output directory")
    h,i,contexts,orig=validate_paths(a.stage03h,a.context,a.stage03i)
    needed={datetime.fromisoformat(r["time"]) for r in contexts}
    require(len(needed)<=54,"Source context selection greater than intended")
    original,fields,absent=original_columns(orig,needed)
    reviewed,summaries=examine(contexts,original)
    report={
        "stage":"STAGE03J_IT_TOR_OFFICIAL_QC1_MDS_QC2_ERA_CONSOLIDATION_SOURCE_PROVENANCE",
        "read_only":True,"science_release":False,
        "source_or_model_modified":False,"slurm_submitted":False,
        "prior_Stage03H_source":str(a.stage03h),
        "prior_Stage03I_source":str(a.stage03i),
        "prior_context_SHA256":i["original_context_SHA256"],
        "original_network_product_path":str(orig),
        "source_fields_found":fields,
        "official_MDS_product_fields_missing":absent,
        "context_records_reviewed":len(reviewed),
        "unique_source_times":len(original),
        "six_handoff_summaries":summaries,
        "official_variable_reference":"https://fluxnet.org/data/fluxnet2015-dataset/fullset-data-product/",
        "conclusion":"QC1=good quality MDS gapfill, QC2=downscaled ERA under official FLUXNET consolidated meteorology definitions. Source matching validates that the product follows its defined construction; does not establish that cold-biased MDS values are sensor-realistic or that packaged ERA is independent truth. NO REPAIRS OR SCIENCE RELEASE."
    }
    j=a.out_dir/"stage03j_IT_Tor_6_handoffs_MDS_ERA_consolidation_PRIVATE.json"
    c=a.out_dir/"stage03j_IT_Tor_54_context_MDS_ERA_fields_PRIVATE.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    if reviewed:
        with c.open("x",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(reviewed[0]))
            w.writeheader();w.writerows(reviewed)
    for x in summaries:
        print("SOURCE_HANDOFF",x["jump_id"],x["time"],
              "QC",x["QC_transition"],
              "QC1_MDS_OFFSET_C",x["QC1_T_MDS_minus_ERA_C"],
              "QC1_FROM_MDS",x["QC1_T_F_equals_MDS"],
              "QC2_FROM_ERA",x["QC2_T_F_equals_ERA"],
              "QC1_MDS_QC1",x["QC1_T_MDS_QC_is_1"],
              "VPD_SOURCE_MDS_ERA",x["QC1_VPD_F_equals_MDS"],
              x["QC2_VPD_F_equals_ERA"])
    print("MDS_SOURCE_FIELDS_MISSING",absent)
    print("STAGE03J COMPLETE: official QC family/source selection checked; original science HOLD retained; no source/NetCDF/CIME/Slurm writes")
    print("PRIVATE_JSON",j)
    print("PRIVATE_54HH",c)

if __name__=="__main__":
    main()
