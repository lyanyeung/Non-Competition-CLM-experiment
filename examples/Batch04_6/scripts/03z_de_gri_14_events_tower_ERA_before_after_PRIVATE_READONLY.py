#!/usr/bin/env python3
"""DE-Gri human meteorology QC: tower/FLUXNET vs packaged ERA, before/during/after.

Uses existing Stage03X/D/V/Y private evidence. For each of 14 original flags,
read 9 half-hours (center +-2h) from FLUXNET FLUXMET and Stage28 selected CSV.
At the 2011 and 2024 focus events, also read corrected annual DATM NetCDF.
Print 9 rows per focus event and three rows for each remaining 12 events;
write all 126 flag-context rows to a PRIVATE CSV + decision-key JSON.
No source, forcing, NetCDF, CIME, Slurm or Git files modified.
Timestamp comparison by *same printed label*, not independently verified UTC.
TA_F/VPD_F QC0 denotes original-observation class in FLUXNET product;
QC1 gapfilled, QC2 ERA class. P_F is not automatically native tipping bucket.
"""
import argparse,csv,hashlib,json,math,sys
from datetime import datetime,timedelta
from pathlib import Path

FOCUS={"2011-06-13 07:00:00","2024-07-04 07:30:00"}
S_COLS=("TA_F","TA_F_QC","TA_ERA","VPD_F","VPD_F_QC","VPD_ERA",
        "P_F","P_F_QC","PA_F")
M_COLS=("TA_USE","VPD_USE","TBOT","QBOT","PSRF","PRECTmms")
CSV_FIELDS=("flag_time","time","offset_minutes","flag_type","source_T_QC",
 "tower_product_T_C","product_ERA_T_C","source_VPD_QC","tower_product_VPD_hPa",
 "product_ERA_VPD_hPa","source_P_QC","source_P_F_mm_per_HH",
 "old_T_C","old_VPD_hPa","old_RH_pct","old_rain_mm_per_HH",
 "candidate_T_C","candidate_VPD_hPa","candidate_RH_pct",
 "tower_minus_ERA_T_C","tower_minus_ERA_VPD_hPa",
 "source_product_T_matches_old","source_product_VPD_matches_old")
def need(cond,msg):
    if not cond:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for v in iter(lambda:f.read(1048576),b""):h.update(v)
    return h.hexdigest()
def number(x):
    try:
        v=float(x)
        return v if math.isfinite(v) and v!=-9999.0 else None
    except (TypeError,ValueError):return None
def stamp(t,source):
    s=str(t).strip().strip("'\"")
    if source and s.endswith(".0") and s[:-2].isdigit():s=s[:-2]
    return datetime.strptime(s,"%Y%m%d%H%M") if source else datetime.fromisoformat(s)
def read_csv(path,source,wanted):
    key="TIMESTAMP_START" if source else "time"
    cols=S_COLS if source else M_COLS
    out={}
    with path.open(encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        need(set((key,)+cols).issubset(r.fieldnames or []),
             "CSV required columns missing: "+str(set((key,)+cols)-set(r.fieldnames or [])))
        for item in r:
            t=stamp(item[key],source)
            if t in wanted:
                need(t not in out,"Duplicate source timestamp "+str(t))
                out[t]={k:number(item[k]) for k in cols}
    return out
def sat(t):
    return 6.112*math.exp(17.67*t/(t+243.5))
def rh(t,vpd):
    if t is None or vpd is None or t<=-80 or t>=70:return None
    return round(100*(1-vpd/sat(t)),3)
def rounded(a,dec=3):
    return None if a is None or not math.isfinite(a) else round(float(a),dec)
def subtract(a,b):
    return rounded(a-b) if a is not None and b is not None else None
def model_from_nc(nc,t):
    from netCDF4 import date2num
    import numpy as np
    coord=nc.variables["time"]
    need(len(coord)==17520 and getattr(coord,"calendar",None) in ("noleap","365_day"),
         "Candidate NC time axis invalid")
    numerical=date2num(t,units=coord.units,calendar=coord.calendar)
    ix=np.flatnonzero(np.isclose(np.ma.filled(coord[:],np.nan),numerical,rtol=0,atol=1e-9))
    need(len(ix)==1,"Candidate NC timestamp missing or repeated "+str(t))
    i=int(ix[0]); T=float(nc.variables["TBOT"][i,0,0])-273.15
    q=float(nc.variables["QBOT"][i,0,0])
    p=float(nc.variables["PSRF"][i,0,0])
    need(0<=q<.1 and 50000<=p<=115000 and -80<=T<=65,
         "Invalid candidate NC physical values "+str(t))
    vapour_hpa=(q*p/(0.622+0.378*q))/100.
    vpd=sat(T)-vapour_hpa
    return {"T":rounded(T),"VPD":rounded(vpd),"RH":rh(T,vpd)}
def row(center,t,src,old,candidate):
    s=src.get(t,{})
    m=old.get(t,{})
    if s and m:
        match_t=abs(s["TA_F"]-m["TA_USE"])<1e-5 if s["TA_F"] is not None and m["TA_USE"] is not None else None
        match_v=abs(s["VPD_F"]-m["VPD_USE"])<1e-5 if s["VPD_F"] is not None and m["VPD_USE"] is not None else None
    else:match_t=match_v=None
    flagname=("T+VPD_QC1_EDIT_2011" if center.year==2011 and str(center)=="2011-06-13 07:00:00" else
              "VPD_QC1_EDIT_2024" if str(center)=="2024-07-04 07:30:00" else "QC0_PRECIP_REVIEW")
    return dict(flag_time=str(center),time=str(t),offset_minutes=int((t-center).total_seconds()/60),
        flag_type=flagname,source_T_QC=s.get("TA_F_QC"),tower_product_T_C=s.get("TA_F"),
        product_ERA_T_C=s.get("TA_ERA"),source_VPD_QC=s.get("VPD_F_QC"),
        tower_product_VPD_hPa=s.get("VPD_F"),product_ERA_VPD_hPa=s.get("VPD_ERA"),
        source_P_QC=s.get("P_F_QC"),source_P_F_mm_per_HH=s.get("P_F"),
        old_T_C=m.get("TA_USE"),old_VPD_hPa=m.get("VPD_USE"),
        old_RH_pct=rh(m.get("TA_USE"),m.get("VPD_USE")),
        old_rain_mm_per_HH=rounded(m["PRECTmms"]*1800) if m.get("PRECTmms") is not None else None,
        candidate_T_C=candidate.get("T") if candidate else None,
        candidate_VPD_hPa=candidate.get("VPD") if candidate else None,
        candidate_RH_pct=candidate.get("RH") if candidate else None,
        tower_minus_ERA_T_C=subtract(s.get("TA_F"),s.get("TA_ERA")),
        tower_minus_ERA_VPD_hPa=subtract(s.get("VPD_F"),s.get("VPD_ERA")),
        source_product_T_matches_old=match_t,source_product_VPD_matches_old=match_v)
def fmt(v,dec=2):
    return "NA" if v is None else (f"{v:.{dec}f}" if isinstance(v,float) else str(v))
def show(r):
    v=lambda k:fmt(r[k])
    print(" ".join((r["time"][11:16],f"{r['offset_minutes']:+4d}m",
       "T_F",v("tower_product_T_C"),"QT",v("source_T_QC"),
       "T_ERA",v("product_ERA_T_C"),"VPD_F",v("tower_product_VPD_hPa"),
       "QV",v("source_VPD_QC"),"VPD_ERA",v("product_ERA_VPD_hPa"),
       "OLD_T",v("old_T_C"),"OLD_VPD",v("old_VPD_hPa"),
       "NEW_T",v("candidate_T_C"),"NEW_VPD",v("candidate_VPD_hPa"),
       "P_F",v("source_P_F_mm_per_HH"),"PQ",v("source_P_QC"),
       "P_OLD",v("old_rain_mm_per_HH"))))
def run(args):
    x,d,v,y=[json.loads(Path(z).read_text(encoding="utf-8")) for z in
             (args.stage03x,args.stage03d,args.stage03v,args.stage03y)]
    need(x.get("site")=="DE-Gri" and x.get("science_release") is False
         and x.get("stage28_forcing_sha_verified") is True,"Stage03X science-HOLD source invalid")
    need(d.get("stage")=="STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT"
         and d.get("science_release") is False,"Stage03D source invalid")
    need(v.get("site")=="DE-Gri" and v.get("status")=="INPUT_PLAN_ONLY_NOT_MODEL_RELEASE",
         "Stage03V input plan invalid")
    need(y.get("stage")=="STAGE03Y_DE_GRI_VERIFIED_CANDIDATE_FLAG_PHYSICS"
         and y.get("science_release") is False,"Stage03Y corrected NC audit invalid")
    flags=x.get("14_flags",[])
    need(len(flags)==14 and len({q["time"] for q in flags})==14,"14 event timestamps required")
    centers=[datetime.fromisoformat(q["time"]) for q in flags]
    need({str(t) for t in centers if str(t) in FOCUS}==FOCUS,
         "2011/2024 QC focus timestamps absent")
    need(sum(q["source_T_QC"]==0 and q["source_VPD_QC"]==0 for q in flags)==12,
         "12 QC0 precipitation events changed")
    site=[z for z in d["sites"] if z["site"]=="DE-Gri"]
    need(len(site)==1,"Stage03D DE-Gri source not unique")
    src=Path(site[0]["source_manifest_primary_file"])
    met=Path(site[0]["Stage28_selected_forcing_path"])
    need(str(src)==x["source_path"] and src.is_file() and met.is_file(),
         "Original Stage03D/Stage03X source mismatch or missing")
    windows={c:[c+timedelta(minutes=30*i) for i in range(-4,5)] for c in centers}
    wanted=set(t for w in windows.values() for t in w)
    a=read_csv(src,True,wanted)
    b=read_csv(met,False,wanted)
    need(set(wanted).issubset(a) and set(wanted).issubset(b),
         "At least one source or selected record missing in context")
    plan={int(j["year"]):j for j in v["annual_inputs"]}
    receipt={int(j["year"]):j for j in y["years"]}
    from netCDF4 import Dataset
    matched={}
    for year in (2011,2024):
        need(year in plan and year in receipt,"Candidate annual NC not registered")
        path=Path(plan[year]["path"])
        need(path.is_file() and sha(path)==receipt[year]["candidate_sha256"],
             "Candidate annual NetCDF SHA changed "+str(year))
        with Dataset(path,"r") as nc:
            for t in wanted:
                if t.year==year and any(abs((t-c).total_seconds())<=7200 for c in centers if c.year==year and str(c) in FOCUS):
                    matched[t]=model_from_nc(nc,t)
    rows=[]
    for center in centers:
        for t in windows[center]:
            rows.append(row(center,t,a,b,matched.get(t)))
    need(len(rows)==14*9,"Unexpected output count")
    need(args.out_dir.is_dir() and not args.out_dir.is_symlink()
         and not any(args.out_dir.iterdir()),"Output must be existing EMPTY directory")
    fname=args.out_dir/"DE-Gri_14_anomalies_tower_ERA_before_after_PRIVATE.csv"
    with fname.open("x",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=CSV_FIELDS)
        writer.writeheader();writer.writerows(rows)
    summary={"site":"DE-Gri","read_only":True,"science_release":False,
        "source_is_FLUXNET_gapfilled_product_NOT_verified_native_sensor":True,
        "source_and_ERA_time_alignment":"SAME_LABEL_ONLY_NOT_INDEPENDENT_UTC",
        "source_path":str(src),"source_sha256_at_review":sha(src),
        "old_stage28_path":str(met),"old_stage28_sha256_at_review":sha(met),
        "centers":[{"time":str(c),"T_QC":next(z["source_T_QC"] for z in flags if z["time"]==str(c)),
                    "VPD_QC":next(z["source_VPD_QC"] for z in flags if z["time"]==str(c)),
                    "center_row":next(r for r in rows if r["flag_time"]==str(c) and r["offset_minutes"]==0)}
                    for c in centers],
        "detailed_csv":str(fname),
        "candidate_annual_sha_verified":{str(year):receipt[year]["candidate_sha256"] for year in (2011,2024)},
        "no_source_case_or_Slurm_changed":True}
    q=args.out_dir/"DE-Gri_14_anomalies_summary_PRIVATE.json"
    with q.open("x",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,ensure_ascii=False);f.write("\n")
    print("STAGE03Z | EXACT 14 DE-GRI EVENTS | ALL -120 TO +120min CSV; MET/ERA SAME LABEL")
    print("COLUMN KEY: T_F,VPD_F are FLUXNET product; QC0 measured-class/QC1 gapfill; ERA is distributed product column; NEW is corrected candidate NC")
    for c in centers:
        data=[r for r in rows if r["flag_time"]==str(c)]
        focus=str(c) in FOCUS
        print("\nEVENT",str(c),"MAIN_SENSITIVITY" if focus else "QC0_HEAVY_RAIN",
              "CENTER_RAIN_mm",next(q for q in data if q["offset_minutes"]==0)["old_rain_mm_per_HH"])
        for r in data:
            if focus or abs(r["offset_minutes"])<=30:show(r)
    print("\nCSV_ALL_126_ROWS",fname)
    print("PRIVATE_SUMMARY",q)
    print("NO MODEL OR SOURCE EDITS; NO Slurm; scientific decision pending")
def selftest():
    t=stamp("201106130700.0",True)
    assert t==datetime(2011,6,13,7)
    assert stamp("2024-07-04 07:30:00",False)==datetime(2024,7,4,7,30)
    assert number("-9999") is None and number("17.2")==17.2
    assert rh(20,0)==100.0 and subtract(20.0,18)==2.0
    assert len(CSV_FIELDS)==23
    print("STAGE03Z SELF-TEST PASS | context time, QC formatting, no source reads")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    for k in ("stage03x","stage03d","stage03v","stage03y"):p.add_argument("--"+k,type=Path)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:selftest();return
    need(all(getattr(args,k) is not None and getattr(args,k).is_file()
             for k in ("stage03x","stage03d","stage03v","stage03y")),
         "All four existing Stage03X/D/V/Y reports required")
    need(args.out_dir is not None,"New empty output directory required")
    run(args)
if __name__=="__main__":main()
