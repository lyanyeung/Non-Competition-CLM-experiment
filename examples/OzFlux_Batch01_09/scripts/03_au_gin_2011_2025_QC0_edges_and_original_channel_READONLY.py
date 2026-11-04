#!/usr/bin/env python3
"""AU-Gin Stage03: first/last tower-QC0 source transitions and original channels.

Strictly read-only and SHA-verified. Stage02v2 demonstrated 15 calendar-year
filled FLUXMET_HH but original measured-class starts Oct 2011, ends Jun
2025. Inspect original date/quality/source at transitions, late 2025,
original PA/P/WS versus F, and conservative physical alarms by QC class.
A value marked QC0 does not itself prove independent instrument quality.
All original ZIP / old L6 / model inputs remain unchanged. No AD400.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,re,zipfile
from collections import Counter,defaultdict
from pathlib import Path

HOME=Path.home()
SRC=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
PREV=HOME/"ozflux_AU_Gin_stage02v2_20261104T162322Z/stage02_AU_Gin_15yr_source_2011_early_QC_science_HOLD.json"
MEMBER="TERN_AU-Gin_FLUXNET_FLUXMET_HH_2011-2025_v1.3_r1.csv"
MET=("TA","VPD","SW_IN","LW_IN","PA","P","WS")
RAW=("PA","P","WS","RH","WD")
BOUNDS={"TA":(-35,56),"VPD":(-.1,85),"SW_IN":(-5,1600),
        "LW_IN":(120,650),"PA":(72,115),"P":(-.05,65),"WS":(-.1,35)}
JUMP={"TA":9,"VPD":20,"PA":1.5,"WS":15}
BASE_COLS=["TIMESTAMP_START","TIMESTAMP_END"]
CSV_COLS=BASE_COLS+["windows"]+sum(([v+"_F",v+"_F_QC",v+"_ERA"] for v in MET),[])+list(RAW)
ALARM_COLS=("native_time","variable","value_F","QC_F","ERA_value","alarm","score")
MONTH_COLS=("year","month","var","records","QC0_finite","QC1_finite","QC2_finite",
            "QC_other_finite","F_missing","QC2_total")
def need(ok,why):
    if not ok:raise RuntimeError(str(why))
def sha(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),"Original source missing/symlink")
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def dtime(s):
    s=str(s or "").strip()
    need(re.fullmatch(r"\d{12}",s) is not None,"Bad raw time "+str(s))
    return dt.datetime.strptime(s,"%Y%m%d%H%M")
def val(s):
    try:
        v=float(str(s).strip())
        return v if math.isfinite(v) and v>-9990 else None
    except (ValueError,TypeError):return None
def qc(s):
    n=val(s)
    return str(int(n)) if n in (0,1,2) else "other"
def threshold(var,v,ta):
    if v is None:return []
    a,b=BOUNDS[var]; flags=[]
    if v<a:flags.append(("BELOW_SCREEN",a-v))
    if v>b:flags.append(("ABOVE_SCREEN",v-b))
    if var=="VPD" and ta is not None and -100<ta<80:
        es=6.112*math.exp(max(-50,min(30,17.67*ta/(ta+243.5))))
        if v>1.05*es:flags.append(("VPD_GT_SATURATION_ES",v/es))
    return flags
def writer(path,cols,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(rows)
def test():
    need(dtime("201110131330")==dt.datetime(2011,10,13,13,30),"time")
    need(qc("2.0")=="2" and qc("9")=="other","flag")
    need(val("-9999") is None and val("0.0")==0.0,"missing")
    need(threshold("VPD",30,0)[0][0]=="VPD_GT_SATURATION_ES","thermodynamic")
    print("OZFLUX AU-GIN STAGE03 SELFTEST PASS | transition + original source QC physical; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return test()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),"Use new direct HOME output folder")
    need(sha(SRC)==SHA,"Immutable TERN FLUXNET source ZIP SHA changed")
    stage=json.loads(PREV.read_text(encoding="utf-8"))
    need(stage.get("original_ZIP_SHA256")==SHA and
         stage.get("native_total_HH")==262992 and
         stage.get("AD400_authorised") is False and
         stage.get("2011_JAN_to_MAY_QC0_by_variable")=={v:0 for v in MET},
         "Operator Stage02v2 science receipt changed")
    pairs=stage["first_last_QC0_records"]
    need(pairs["TA"]=={"first":"2011-10-13 13:30:00",
                        "last":"2025-06-27 23:00:00"},
         "Actual tower QC0 start/end changed")
    windows=[]
    for v in MET:
        for typ in ("first","last"):
            d=dt.datetime.fromisoformat(pairs[v][typ])
            windows.append((v+"_"+typ,d-dt.timedelta(hours=24),
                            d+dt.timedelta(hours=24)))
    windows.extend([
        ("JAN2011",dt.datetime(2011,1,1),dt.datetime(2011,1,2)),
        ("OCT2011",dt.datetime(2011,10,12),dt.datetime(2011,10,15)),
        ("JUL2025",dt.datetime(2025,6,27),dt.datetime(2025,7,2)),
        ("DEC2025",dt.datetime(2025,12,30),dt.datetime(2026,1,1))])
    context=[];alarms=defaultdict(list);alarm_counts=Counter()
    months=defaultdict(lambda:{"n":0,"q":Counter(),"finite_by_q":Counter(),"missing":0})
    raw_pairs=defaultdict(lambda:{"n":0,"exact":0,"max_abs":0.,"diffs":[]})
    first=None;last=None;prior_end=None;prior_values={};prior_q={}
    n=0;qc0_missing=Counter()
    with zipfile.ZipFile(SRC,"r") as z:
        need(z.namelist().count(MEMBER)==1,"Unique source member missing")
        with z.open(MEMBER,"r") as f:
            r=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
            want=set(BASE_COLS)
            for v in MET:want.update([v+"_F",v+"_F_QC",v+"_ERA"])
            need(want.issubset(set(r.fieldnames or [])),
                 "Missing source columns "+str(sorted(want-set(r.fieldnames or []))))
            raw_present=[v for v in RAW if v in r.fieldnames]
            for item in r:
                t=dtime(item["TIMESTAMP_START"])
                end=dtime(item["TIMESTAMP_END"])
                need(end-t==dt.timedelta(minutes=30) and
                     (prior_end is None or prior_end==t),
                     "Original non-contiguous interval")
                if first is None:first=t
                last=end;prior_end=end;n+=1
                vv={v:val(item[v+"_F"]) for v in MET}
                qq={v:qc(item[v+"_F_QC"]) for v in MET}
                for v in MET:
                    key=(t.year,t.month,v)
                    mm=months[key];mm["n"]+=1
                    mm["q"][qq[v]]+=1
                    if vv[v] is None:
                        mm["missing"]+=1
                        if qq[v]=="0":qc0_missing[v]+=1
                    else:
                        mm["finite_by_q"][qq[v]]+=1
                    for flag,mag in threshold(v,vv[v],vv["TA"]):
                        label=(v,flag,qq[v])
                        alarm_counts[label]+=1
                        if len(alarms[label])<30:
                            alarms[label].append([t,vv[v],qq[v],val(item[v+"_ERA"]),mag])
                    if v in JUMP and vv[v] is not None and prior_values.get(v) is not None:
                        if qq[v]=="0" and prior_q.get(v)=="0":
                            delta=abs(vv[v]-prior_values[v])
                            if delta>JUMP[v]:
                                label=(v,"QC0_TO_QC0_30MIN_JUMP","0")
                                alarm_counts[label]+=1
                                if len(alarms[label])<30:
                                    alarms[label].append([t,vv[v],qq[v],val(item[v+"_ERA"]),delta])
                    if v in raw_present and vv[v] is not None:
                        raw=val(item[v])
                        if raw is not None:
                            k=(v,qq[v]);info=raw_pairs[k]
                            d=vv[v]-raw;info["n"]+=1
                            if abs(d)<=1e-6:info["exact"]+=1
                            info["max_abs"]=max(info["max_abs"],abs(d))
                            if abs(d)>1e-6 and len(info["diffs"])<4:
                                info["diffs"].append({"time":str(t),
                                                     "F":vv[v],"raw":raw})
                prior_values=vv;prior_q=qq
                tags=[name for name,lo,hi in windows if lo<=t<=hi]
                if tags:
                    x={"TIMESTAMP_START":item["TIMESTAMP_START"],
                       "TIMESTAMP_END":item["TIMESTAMP_END"],
                       "windows":";".join(tags)}
                    for v in MET:
                        x[v+"_F"]=item[v+"_F"]
                        x[v+"_F_QC"]=item[v+"_F_QC"]
                        x[v+"_ERA"]=item[v+"_ERA"]
                    for v in RAW:x[v]=item.get(v)
                    context.append(x)
    need(n==262992 and first==dt.datetime(2011,1,1)
         and last==dt.datetime(2026,1,1),"Original 15 calendar-year count/clock drift")
    monthrows=[]
    for year in range(2011,2026):
        for month in range(1,13):
            for v in MET:
                m=months[(year,month,v)]
                monthrows.append({"year":year,"month":month,"var":v,
                  "records":m["n"],"QC0_finite":m["finite_by_q"]["0"],
                  "QC1_finite":m["finite_by_q"]["1"],
                  "QC2_finite":m["finite_by_q"]["2"],
                  "QC_other_finite":m["finite_by_q"]["other"],
                  "F_missing":m["missing"],
                  "QC2_total":m["q"]["2"]})
    # Count flag origin rather than interpreting all flags as observation validity.
    alarmrows=[]
    for (v,label,q),events in sorted(alarms.items()):
        for when_,obs,flag,era,mag in events:
            alarmrows.append({"native_time":str(when_),"variable":v,
                              "value_F":obs,"QC_F":flag,
                              "ERA_value":era,"alarm":label,"score":mag})
    pairsout={v:{q:x for (name,q),x in raw_pairs.items() if name==v}
              for v in RAW if any(k[0]==v for k in raw_pairs)}
    report={"site":"AU-Gin","stage":"Stage03 original new TERN FLUXNET QC0 transition and raw channel screen",
       "source_zip_sha256":SHA,"prior_stage02v2_SHA256":sha(PREV),
       "total_source_HH":n,"first_native":str(first),"last_end_native":str(last),
       "original_first_last_QC0":pairs,
       "original_QC0_2011_JAN_MAY_verified_zero":True,
       "raw_PA_P_WS_vs_same_product_F":pairsout,
       "QC0_with_invalid_F_values":dict(qc0_missing),
       "physical_alarm_counts":{"/".join(k):v for k,v in alarm_counts.items()},
       "BIF_instrument_start_and_time_semantics_still_unverified":True,
       "same_product_ERA_not_independent_observation":True,
       "15_calendar_year_product_available":True,
       "15_continuous_measured_years_proven":False,
       "no_originals_DATM_Soil_Surface_CIME_Slurm_writes":True,
       "science_release":False,"AD400_authorised":False}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    writer(o/"stage03_AU_Gin_QC0_ERA_transition_original_HH.tsv",CSV_COLS,context)
    writer(o/"stage03_AU_Gin_2011_2025_monthly_QC_provenance.tsv",MONTH_COLS,monthrows)
    writer(o/"stage03_AU_Gin_original_source_physics_alarm_examples.tsv",ALARM_COLS,alarmrows)
    (o/"stage03_AU_Gin_QC0_transition_and_raw_channels_SCIENCE_HOLD.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE03 SOURCE SHA256 VERIFIED",SHA,"NATIVE_HH",n)
    print("ORIGINAL_QC0_FIRST_LAST",json.dumps(pairs))
    for y,ms in ((2011,(1,5,9,10,11,12)),(2025,(5,6,7,8,9,10,11,12))):
        for month in ms:
            print("MONTH",y,month," ".join(
               f"{v}:QC0={months[(y,month,v)]['q']['0']}/QC2={months[(y,month,v)]['q']['2']}"
               for v in MET))
    print("RAW_VERSUS_FLUXNET_F",json.dumps(pairsout))
    print("PHYSICAL_ALARM_COUNTS",json.dumps(report["physical_alarm_counts"]))
    print("ORIGINAL_QC0_NONFINITE_COUNTS",json.dumps(report["QC0_with_invalid_F_values"]))
    print("STAGE03 SOURCE TRIAGE PASS; NO REPAIR, NO DATM/AD400")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
