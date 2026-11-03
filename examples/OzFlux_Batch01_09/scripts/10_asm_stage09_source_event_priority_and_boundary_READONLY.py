#!/usr/bin/env python3
"""AU-ASM Stage10: rank actual Stage09 original OzFlux source-QC science evidence.

READ ONLY Stage09's 4 reports, no model inputs changed, no CIME or Slurm.
Outputs a concise review ledger and important original native before/after
windows. A successful audit is NOT scientific approval of any fill or AD400.
"""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter,defaultdict
from pathlib import Path

HOME=Path.home()
DEFAULT=HOME/"ozflux_nc_stage09_20261103T070958Z"
NAMES={
"year":"stage09_year_variable_original_QC.tsv",
"episodes":"stage09_ALL_native_QC_spells.tsv",
"context":"stage09_before_during_after_met_and_sensor_candidates.tsv",
"summary":"stage09_FORCING_SCIENCE_HOLD.json"}
VARIABLES=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
REQUIRED_QC=("QC0","QC10","QC50","QC400","QC410","QC420","QC430","QC440","other","missing_QC")
EVENT_COLUMNS=("variable","QC_class","first_native","last_native","hours",
    "count","before","first","last","after","jump_into","jump_out",
    "review_priority","reason","decision","independent_donor_verified")
BOUNDARY_COLUMNS=("focus","native_time","primary_variable","Ta","Ta_QCFlag",
    "SH","SH_QCFlag","ps","ps_QCFlag","Fsd","Fsd_QCFlag",
    "Fld","Fld_QCFlag","Ws","Ws_QCFlag","Precip","Precip_QCFlag",
    "alternate_sensor_json")

def ensure(c,why):
    if not c:raise ValueError(str(why))

def read_tsv(p):
    ensure(p.is_file() and not p.is_symlink(),"Missing Stage09 artifact: "+str(p))
    with p.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))

def asint(v):return int(v)
def asfloat(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def _sort_rows(rows):
    return sorted(rows,key=lambda r:(-float(r["hours"]),r["variable"],r["first_native"]))

def priority(r):
    v=r["variable"];cls=r["QC_class"];n=int(r["count"]);h=float(r["hours"])
    joins=[asfloat(r["jump_into"]),asfloat(r["jump_out"])]
    reasons=[]
    if cls=="ACCESS_420":reasons.append("ACCESS_MODEL_REPLACEMENT")
    if cls=="ERA5_440":reasons.append("ERA5_MODEL_REPLACEMENT")
    if cls=="OTHER_ALT_400_410_430":reasons.append("ALTERNATE_SOURCE_OR_AWS")
    if cls=="INTERPOLATION_50":reasons.append("INTERPOLATION")
    if v in ("Fsd","Fld") and h>=24:
        reasons.append("RADIATION_FILL_GE24H")
    if any(abs(j)>({"Fld":75,"Fsd":250,"Ta":5,"SH":.003,"ps":2,
                    "Ws":8,"Precip":20}.get(v,10))
           for j in joins if j is not None):
        reasons.append("BOUNDARY_JUMP_REVIEW")
    if v=="Fld" and cls=="ACCESS_420" and r["first_native"]=="2017-08-17 22:00:00":
        reasons.append("EXACT_2017_395H_FLDS")
    if cls=="ANY_NON_QC0" and not reasons:reasons.append("SOURCE_NON_QC0_MIXED")
    if "EXACT_2017_395H_FLDS" in reasons or ("RADIATION_FILL_GE24H" in reasons):
        rank="HIGH"
    elif "BOUNDARY_JUMP_REVIEW" in reasons or (
        cls in ("ACCESS_420","ERA5_440","OTHER_ALT_400_410_430") and h>=6):
        rank="REVIEW"
    else:rank="INVENTORY"
    return rank,";".join(reasons)

def tsv(path,fields,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter="\t",extrasaction="raise")
        w.writeheader()
        w.writerows(rows)

def select_focus(contexts, focus, threshold, sides=9):
    target=[r for r in contexts if r["focus"]==focus]
    ensure(len(target)>=threshold,"Missing full original focus: "+focus)
    target.sort(key=lambda r:int(r["source_row"]))
    if len(target)<=sides*2:
        return target
    return target[:sides]+target[-sides:]

def selftest():
    t={"variable":"Fld","QC_class":"ACCESS_420",
       "first_native":"2017-08-17 22:00:00","hours":"395",
       "count":"790","jump_into":"0","jump_out":"0"}
    a,b=priority(t)
    ensure(a=="HIGH" and "EXACT_2017_395H_FLDS" in b,"priority test")
    ensure(asfloat("") is None and asfloat("1.25")==1.25,"float handling")
    print("OZFLUX STAGE10 SELF TEST PASS | event ranking and source-window excerpt; READ ONLY")

def main():
    import sys
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser()
    p.add_argument("--stage09",type=Path,default=DEFAULT)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    src=a.stage09
    ensure(src.is_dir() and not src.is_symlink(),"Stage09 source report dir absent")
    out=a.out
    ensure(not out.exists() and not out.is_symlink() and
           out.parent.resolve()==HOME.resolve(),"Output must be new direct HOME child")
    prior=json.loads((src/NAMES["summary"]).read_text(encoding="utf-8"))
    ensure(prior["site"]=="AU-ASM" and
           prior["status"]=="FORCING_SCIENCE_HOLD" and
           prior["science_release"] is False and
           prior["AD400_authorised"] is False and
           prior["2017_395h_Fld_ACCESS_source_reproduced"] is True and
           prior["year_variable_reconciled"]==42,
           "Stage09 evidence or science-HOLD changed")
    years=read_tsv(src/NAMES["year"])
    episodes=read_tsv(src/NAMES["episodes"])
    contexts=read_tsv(src/NAMES["context"])
    ensure(len(years)==42 and len(episodes)==1860 and len(contexts)==9291,
           "Stage09 operator receipt row counts changed: review version")
    ensure({(int(r["year"]),r["variable"]) for r in years}==
           {(y,v) for y in range(2013,2019) for v in VARIABLES},
           "Stage09 year-variable scope incomplete")
    ensure(set(REQUIRED_QC).issubset(years[0]),"Stage09 QC columns missing")
    annual=[]
    for r in years:
        total=int(r["native_rows"])
        countsum=sum(int(r[c]) for c in REQUIRED_QC)
        ensure(countsum==total,"QC histogram does not close "+str((r["year"],r["variable"])))
        qc0=int(r["QC0"])
        annual.append({"year":int(r["year"]),"variable":r["variable"],
            "n_halfhours":total,"original_QC0":qc0,
            "QC0_percent":round(100*qc0/total,4),
            "model_ACCESS_420":int(r["QC420"]),
            "model_ERA5_440":int(r["QC440"]),
            "other_alternate_400_410_430":sum(int(r[k]) for k in ("QC400","QC410","QC430")),
            "interpolated_50":int(r["QC50"]),
            "other_or_missing_QC":sum(int(r[k]) for k in ("QC10","other","missing_QC")),
            "physical_alarm_HH":int(r["broad_physical_alarms"]),
            "large_step_change_HH":int(r["step_jump_review"])})
    keyed={(r["year"],r["variable"]):r for r in annual}
    ensure(keyed[(2017,"Fld")]["model_ACCESS_420"]>=790,
           "2017 Fld long ACCESS replacement missing")
    ranked=[]
    for r in episodes:
        rank,reason=priority(r)
        if r["QC_class"]=="ANY_NON_QC0":continue
        ranked.append({k:r[k] for k in EVENT_COLUMNS[:12]}|{
            "review_priority":rank,"reason":reason,"decision":"HOLD_REVIEW",
            "independent_donor_verified":False})
    high=[r for r in ranked if r["review_priority"]=="HIGH"]
    longest=_sort_rows([r for r in ranked if r["QC_class"] in
                       ("ACCESS_420","ERA5_440","OTHER_ALT_400_410_430","INTERPOLATION_50")])
    full=[r for r in contexts if r["focus"]=="2017_Fld_395H_FULL_SOURCE_CONTEXT"]
    ensure(len(full)>=790,"2017 original 395-hour raw context missing")
    full.sort(key=lambda r:int(r["source_row"]))
    inrun=[r for r in full if r["Fld_QCFlag"] in ("420.0","420")]
    ensure(len(inrun)>=790,"2017 source ACCESS QC in full focus not recovered")
    fld=[asfloat(r["Fld"]) for r in inrun]
    fld=[v for v in fld if v is not None]
    ensure(len(fld)>=790,"2017 original Fld values missing")
    changes=[]
    vals=[asfloat(r["Fld"]) for r in full]
    for i in range(1,len(vals)):
        if vals[i] is not None and vals[i-1] is not None:
            changes.append(abs(vals[i]-vals[i-1]))
    donor_names=set()
    for r in full:
        obj=json.loads(r["alternate_sensor_json"])
        donor_names.update(obj)
    picked=[]
    for focus,minimum in (
       ("2017_Fld_395H_FULL_SOURCE_CONTEXT",790),
       ("PEAK_WIND_SOURCE",1)):
        picked+=select_focus(contexts,focus,minimum)
    # Add top original radiation event boundaries from Stage09 full context.
    for row in longest:
        if row["variable"] in ("Fsd","Fld") and row["QC_class"] in ("ACCESS_420","ERA5_440"):
            if row["first_native"][:4] not in ("2014","2016","2018"):continue
            name=f'{row["variable"]}_{row["QC_class"]}_{row["first_native"]}'
            if any(r["focus"]==name for r in contexts):
                picked+=select_focus(contexts,name,1,5)
            if len({r["focus"] for r in picked})>=14:break
    picked=[{k:r[k] for k in BOUNDARY_COLUMNS} for r in picked]
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    tsv(out/"stage10_ranked_original_nonzero_QC_spells.tsv",
        EVENT_COLUMNS,ranked)
    tsv(out/"stage10_annual_QC_source_composition.tsv",
        list(annual[0]),annual)
    tsv(out/"stage10_selected_original_source_windows.tsv",
        BOUNDARY_COLUMNS,picked)
    result={
     "scope":"AU-ASM 2013-2018 original L6, native source clock not independently certified",
     "stage09_original":str(src),"read_only":True,
     "source_events_inherited":len(episodes),
     "original_year_variable_groups":42,"priority_high":len(high),
     "priority_review":sum(r["review_priority"]=="REVIEW" for r in ranked),
     "critical_2017_Fld_ACCESS_395h":{
       "original_QC420_rows":len(inrun),
       "min_Fld_Wm2":min(fld),"max_Fld_Wm2":max(fld),
       "mean_Fld_Wm2":sum(fld)/len(fld),
       "max_neighbor_step_Wm2":max(changes) if changes else None,
       "source_alternate_sensor_names_only_NOT_VALIDATED":sorted(donor_names)},
     "annual_radiation_QC_by_year":[r for r in annual if r["variable"] in ("Fsd","Fld")],
     "annual_min_QC0":[{"year":r["year"],"variable":r["variable"],
                         "QC0_percent":r["QC0_percent"]}
       for r in sorted(annual,key=lambda r:r["QC0_percent"])[:12]],
     "top_20_source_replacement_spells":longest[:20],
     "selected_original_windows_rows":len(picked),
     "original_source_2018_wind_max_mps":16.29613,
     "human_decisions_ready":False,
     "external_independent_donor_validation_complete":False,
     "time_zone_interval_semantics_approved":False,
     "science_release":False,"AD400_authorised":False,
     "next":"Per-event source+donor evidence, model fill boundary checks and source-time validation; keep AD400 blocked."
    }
    (out/"stage10_AU_ASM_SCIENCE_REVIEW_HOLD.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    print("STAGE10 ORIGINAL QC GROUPS 42 | CONTIGUOUS EPISODES",len(episodes))
    print("PRIORITY HIGH",len(high),"REVIEW",result["priority_review"])
    for r in sorted(annual,key=lambda r:r["QC0_percent"])[:10]:
        print("LOW QC0",r["year"],r["variable"],r["QC0_percent"],
              "ACCESS",r["model_ACCESS_420"],"ERA5",r["model_ERA5_440"],
              "INTERP",r["interpolated_50"])
    for r in longest[:14]:
        print("LONGEST",r["variable"],r["QC_class"],r["first_native"],
              r["last_native"],r["hours"],"h",
              "JUMP_IN",r["jump_into"],"JUMP_OUT",r["jump_out"])
    print("2017 Fld ACCESS 395h",
          "MIN",round(min(fld),2),"MAX",round(max(fld),2),
          "MEAN",round(sum(fld)/len(fld),2),
          "MAX_STEP",round(max(changes),2) if changes else None,
          "DONOR_CANDIDATES",sorted(donor_names))
    print("STAGE10 SOURCE REVIEW EVIDENCE PASS; FORCING SCIENCE HOLD; NO SLURM")
    print("REPORT_DIR",out)

if __name__=="__main__":main()
