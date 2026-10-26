#!/usr/bin/env python3
"""Stage22 ES-LJu exhaustive operator review, read-only against ORIGINAL + ERA + Stage28 + Stage21.
Produces detailed half-hour CSVs for: three remaining temperature discontinuities,
2023-10-18 hand-off, ALL remaining low-RH halfhours grouped into contiguous spells with
2h before+after, ALL 28 precipitation HOLD days with +/-1day ERA5 precipitation,
2013/2016 extreme precipitation, and ALL 73 previous edits with original vs ERA.
No forcing, raw observation, case, DATM or Slurm file is altered.
Same TIMESTAMP_START label equality used; instrument accumulation-day convention
and site/source timezone not independently established.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10")
STAGE16=EXPECTED_ROOT/"stage16_ES_LJu_manual_review_v1_20261025"
DEFAULT_STAGE21=EXPECTED_ROOT/"stage21_20261026T011416Z"

EVENTS=[
 ("2006_05_31_to_06_01_jump","2006-05-31 18:00","2006-06-01 09:00"),
 ("2019_06_30_ERA_to_tower_jump","2019-06-29 22:00","2019-06-30 14:00"),
 ("2023_01_15_tower_to_ERA_jump","2023-01-14 20:00","2023-01-15 12:00"),
 ("2023_10_18_ERA_bridge","2023-10-18 13:30","2023-10-18 22:00"),
 ("2009_09_27_approved","2009-09-27 12:00","2009-09-28 01:00"),
 ("2017_08_08_approved","2017-08-08 17:00","2017-08-09 04:00"),
]
EXTREME_TIMES=["2013-12-25 02:00","2016-12-06 10:00"]

def ensure(cond,msg):
 if not bool(cond):
  raise RuntimeError(str(msg))

def digest(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def es(temp):
 v=np.asarray(temp,dtype=float)
 return 6.112*np.exp(np.clip(17.67*v/(v+243.5),-20,20))

def rh(ta,vpd):
 e=es(ta)
 with np.errstate(divide="ignore",invalid="ignore"):
  return 100*(e-np.asarray(vpd,dtype=float))/e

def load_source(path,requested):
 names=set(pd.read_csv(path,nrows=0).columns)
 ensure("TIMESTAMP_START" in names,f"No timestamp column: {path}")
 columns=["TIMESTAMP_START"]+[s for s in requested if s in names]
 d=pd.read_csv(path,usecols=columns,dtype={"TIMESTAMP_START":str},low_memory=False)
 d["time"]=pd.to_datetime(d.TIMESTAMP_START.astype(str).str.replace(r"\.0$","",regex=True),
                          format="%Y%m%d%H%M",errors="raise")
 d=d.loc[d.time.dt.year.between(2004,2024)]
 d=d.loc[~((d.time.dt.month==2)&(d.time.dt.day==29))].copy()
 for col in columns[1:]:
  d[col]=pd.to_numeric(d[col],errors="coerce")
  d.loc[d[col]<=-9990,col]=np.nan
 ensure(not d.time.duplicated().any(),f"Duplicated input timestamps {path}")
 return d.set_index("time").sort_index()

def load_model(path):
 required=["time","TA_USE","VPD_USE","QBOT","PSRF","PRECTmms"]
 d=pd.read_csv(path,usecols=required,low_memory=False)
 d["time"]=pd.to_datetime(d["time"],errors="raise")
 ensure(d.time.is_unique and d.time.is_monotonic_increasing,"Model timestamp uniqueness/order failed")
 ensure(len(d)==21*365*48 and not ((d.time.dt.month==2)&(d.time.dt.day==29)).any(),
        "Model 21-year NOLEAP failed")
 return d.set_index("time")

def daysum(df,col,day):
 return float(df.loc[day:day+pd.Timedelta(days=1)-pd.Timedelta(minutes=30),col].sum(min_count=1))

def self_test():
 ensure(abs(float(rh([20],[es([20])[0]*.7])[0])-30)<1e-9,"RH formula self-test")
 keys=pd.DatetimeIndex(pd.to_datetime(["2023-01-15 00:00","2023-01-15 00:30","2023-01-15 02:00"]))
 ensure(((keys.to_series().diff()!=pd.Timedelta(minutes=30)).cumsum().to_list())==[1,1,2],
        "Consecutive spell separation test")
 ensure(abs(1800*.001-1.8)<1e-10,"half-hour PRECTmms units test")
 print("STAGE22 SELF-TEST PASS: vapor pressure RH, contiguous episodes, 30-min precipitation")

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--self-test",action="store_true")
 ap.add_argument("--stage21",type=Path,default=DEFAULT_STAGE21)
 ap.add_argument("--out",type=Path)
 ap.add_argument("--print-all",action="store_true",help="Print all 412 low-RH rows and all rain-hold contexts to terminal")
 arg=ap.parse_args()
 self_test()
 if arg.self_test:return
 ensure(arg.out is not None,"--out is required")
 out=arg.out.expanduser().resolve()
 ensure(not out.exists() and not out.is_symlink(),"Refusing existing output folder "+str(out))
 source_receipt=json.loads((STAGE16/"00_science_lineage_and_review_questions.json").read_text())
 final_dir=arg.stage21.expanduser().resolve()
 receipt=json.loads((final_dir/"06_manifest.json").read_text())
 selected=Path(source_receipt["stage28_source"]["path"])
 candidate=final_dir/"ES-LJu_stage21_full21yr_provisional_forcing.csv"
 raw=Path(source_receipt["original_fluxmet_hourly"]["raw_path"])
 era=Path(receipt["ERA5_companion"])
 ensure(all(x.is_file() for x in (selected,candidate,raw,era)),"Input source files missing")
 ensure(digest(selected)==source_receipt["stage28_source"]["sha256"]==receipt["original_sha256"],
        "Stage28 -> Stage16 -> Stage21 provenance divergence")
 ensure(digest(raw)==source_receipt["original_fluxmet_hourly"]["sha256"]==receipt["tower_original_sha256"],
        "Original FLUXMET bytes changed")
 ensure(digest(era)==receipt["ERA5_sha256"],"ERA5 companion bytes changed")
 base=load_model(selected)
 final=load_model(candidate)
 tower=load_source(raw,["TA_F","TA_F_QC","VPD_F","VPD_F_QC","P_F","P_F_QC"])
 comp=load_source(era,["TA_ERA","VPD_ERA","P_ERA"])
 ensure(all(x.index.equals(base.index) for x in (final,tower,comp)),"Date labels not exactly aligned")
 ensure({"TA_F","TA_F_QC","VPD_F","VPD_F_QC","P_F","P_F_QC"}.issubset(tower),
        "Missing original FLUXMET columns")
 ensure({"TA_ERA","VPD_ERA","P_ERA"}.issubset(comp),"Missing ERA5 companion data columns")
 audit=pd.DataFrame(index=base.index)
 for c,old,new in [
   ("TA_F","tower_TA_C",tower),("TA_F_QC","tower_TA_QC",tower),
   ("VPD_F","tower_VPD_hPa",tower),("VPD_F_QC","tower_VPD_QC",tower),
   ("P_F","tower_P_mmHH",tower),("P_F_QC","tower_P_QC",tower),
   ("TA_ERA","ERA5_TA_C",comp),("VPD_ERA","ERA5_VPD_hPa",comp),
   ("P_ERA","ERA5_P_mmHH",comp),
   ("TA_USE","stage28_TA_C",base),("VPD_USE","stage28_VPD_hPa",base),
   ("TA_USE","stage21_TA_C",final),("VPD_USE","stage21_VPD_hPa",final),
   ("QBOT","stage28_QBOT",base),("QBOT","stage21_QBOT",final)
 ]:
  audit[old]=new[c].to_numpy(float)
 audit["stage28_RH_pct"]=rh(audit.stage28_TA_C,audit.stage28_VPD_hPa)
 audit["stage21_RH_pct"]=rh(audit.stage21_TA_C,audit.stage21_VPD_hPa)
 audit["tower_RH_pct"]=rh(audit.tower_TA_C,audit.tower_VPD_hPa)
 audit["ERA5_RH_pct"]=rh(audit.ERA5_TA_C,audit.ERA5_VPD_hPa)
 audit["stage28_P_mmHH"]=base.PRECTmms.to_numpy(float)*1800.
 audit["stage21_P_mmHH"]=final.PRECTmms.to_numpy(float)*1800.
 audit["stage21_minus_ERA_TA_C"]=audit.stage21_TA_C-audit.ERA5_TA_C
 audit["tower_minus_ERA_TA_C"]=audit.tower_TA_C-audit.ERA5_TA_C
 ensure(len(audit)==367920 and audit.index.is_unique,"Exhaustive audit timeline invariant")
 display=[
  "time","tower_TA_C","tower_TA_QC","ERA5_TA_C","stage28_TA_C",
  "stage21_TA_C","tower_VPD_hPa","tower_VPD_QC","ERA5_VPD_hPa",
  "tower_RH_pct","ERA5_RH_pct","stage28_RH_pct","stage21_RH_pct"
 ]
 rain_display=[
  "time","tower_P_mmHH","tower_P_QC","ERA5_P_mmHH",
  "stage28_P_mmHH","stage21_P_mmHH","tower_TA_C","ERA5_TA_C"
 ]
 def frame(x):
  return x.reset_index().round(4)
 def window(st,en,cols=display):
  return frame(audit.loc[st:en])[cols]
 sections={}
 for name,lo,hi in EVENTS:
  sections[name]=window(lo,hi)
 edges=pd.read_csv(final_dir/"05_modified_temperature_boundary_warnings.csv")
 ensure(len(edges)==3,"Stage21 boundary-count drift: expected 3")
 low=pd.read_csv(final_dir/"07_remaining_RH_below5_ERA_comparison.csv",parse_dates=["time"])
 low=low.sort_values("time").reset_index(drop=True)
 ensure(len(low)==412,"Stage21 low-RH count changed: expected 412")
 ensure(set(low.time).issubset(set(audit.index)),"Missing low RH timestamps in timeline")
 low["episode_id"]=(low.time.diff()!=pd.Timedelta(minutes=30)).cumsum()
 ep_summary=[]
 ep_context=[]
 for epi,g in low.groupby("episode_id",sort=True):
  a=g.time.iloc[0];b=g.time.iloc[-1]
  body=audit.loc[a:b]
  core=frame(body)
  keep_t=float(body.stage21_minus_ERA_TA_C.abs().median())
  era_rh_med=float(body.ERA5_RH_pct.median())
  q0=int((body.tower_VPD_QC==0).sum())
  q1=int((body.tower_VPD_QC==1).sum())
  q2=int((body.tower_VPD_QC==2).sum())
  cls=("ERA5_ALSO_LT10_REVIEW_DO_NOT_FORCE" if era_rh_med<10
       else "HUMIDITY_ONLY_CANDIDATE_KEEP_TA" if keep_t<=3
       else "COUPLED_TA_AND_VPD_REVIEW")
  ep_summary.append(dict(
    episode_id=int(epi),start=str(a),end=str(b),half_hours=len(body),
    duration_hours=len(body)*.5,
    min_stage21_RH_pct=round(float(body.stage21_RH_pct.min()),3),
    median_stage21_RH_pct=round(float(body.stage21_RH_pct.median()),3),
    median_ERA5_RH_pct=round(era_rh_med,3),
    median_abs_stage21_minus_ERA_TA_C=round(keep_t,3),
    tower_VPD_QC0_HH=q0,tower_VPD_QC1_HH=q1,tower_VPD_QC2_HH=q2,
    suggested_review_class=cls
  ))
  lo=max(a-pd.Timedelta(hours=2),audit.index[0])
  hi=min(b+pd.Timedelta(hours=2),audit.index[-1])
  sub=frame(audit.loc[lo:hi])
  sub["episode_id"]=int(epi)
  sub["relation"]=np.where(sub.time<a,"BEFORE",np.where(sub.time>b,"AFTER","LOW_RH"))
  ep_context.append(sub[["episode_id","relation"]+display])
 eps=pd.DataFrame(ep_summary).sort_values(["half_hours","min_stage21_RH_pct"],ascending=[False,True])
 ctx=pd.concat(ep_context,ignore_index=True) if ep_context else pd.DataFrame()

 holds=pd.read_csv(final_dir/"04_ERA_dry_or_missing_rain_HOLD.csv")
 ensure(len(holds)==28,"Stage21 held rain-day count changed: expected 28")
 hold_sum=[];hold_ctx=[]
 for _,rec in holds.iterrows():
  day=pd.Timestamp(rec["day"]).normalize()
  start=day-pd.Timedelta(days=1)
  end=day+pd.Timedelta(days=2)-pd.Timedelta(minutes=30)
  today=audit.loc[day:day+pd.Timedelta(days=1)-pd.Timedelta(minutes=30)]
  nearby=audit.loc[start:end]
  prev=day-pd.Timedelta(days=1)
  nxt=day+pd.Timedelta(days=1)
  prev_era=daysum(audit,"ERA5_P_mmHH",prev)
  same_era=daysum(audit,"ERA5_P_mmHH",day)
  next_era=daysum(audit,"ERA5_P_mmHH",nxt)
  after6=audit.loc[nxt:nxt+pd.Timedelta(hours=6)-pd.Timedelta(minutes=30),"ERA5_P_mmHH"].sum(min_count=1)
  before6=audit.loc[day-pd.Timedelta(hours=6):day-pd.Timedelta(minutes=30),"ERA5_P_mmHH"].sum(min_count=1)
  hold_sum.append(dict(
   day=str(day.date()),tower_total_mm=round(float(today.tower_P_mmHH.sum()),5),
   candidate_today_mm=round(float(today.stage21_P_mmHH.sum()),5),
   ERA5_prev_day_mm=round(float(prev_era),5),
   ERA5_same_day_mm=round(float(same_era),5),
   ERA5_next_day_mm=round(float(next_era),5),
   ERA5_prev_day_last6h_mm=round(float(before6),5),
   ERA5_next_day_first6h_mm=round(float(after6),5),
   tower_wet_halfhours=int((today.tower_P_mmHH>0).sum()),
   status="HOLD_ZERO_ERA_SAME_DAY_NEED_OPERATOR"
  ))
  x=frame(nearby)[rain_display]
  x.insert(0,"hold_day",str(day.date()))
  x.insert(1,"relative_day",(pd.to_datetime(x["time"]).dt.normalize()-day).dt.days)
  hold_ctx.append(x)
 hold_sum=pd.DataFrame(hold_sum)
 hold_context=pd.concat(hold_ctx,ignore_index=True)
 extremes=[];extreme_summ=[]
 for t in EXTREME_TIMES:
  at=pd.Timestamp(t)
  part=window(at-pd.Timedelta(hours=12),at+pd.Timedelta(hours=12),rain_display)
  part.insert(0,"extreme_timestamp",t)
  extremes.append(part)
  d=at.normalize()
  p=audit.loc[d:d+pd.Timedelta(days=1)-pd.Timedelta(minutes=30)]
  extreme_summ.append(dict(
    extreme_time=t,tower_P_mmHH=float(audit.loc[at,"tower_P_mmHH"]),
    tower_P_QC=float(audit.loc[at,"tower_P_QC"]),
    ERA5_P_mmHH=float(audit.loc[at,"ERA5_P_mmHH"]),
    stage28_P_mmHH=float(audit.loc[at,"stage28_P_mmHH"]),
    stage21_P_mmHH=float(audit.loc[at,"stage21_P_mmHH"]),
    tower_day_P_mm=float(p.tower_P_mmHH.sum()),
    ERA5_day_P_mm=float(p.ERA5_P_mmHH.sum()),
    stage21_day_P_mm=float(p.stage21_P_mmHH.sum()),
    tower_wet_HH_today=int((p.tower_P_mmHH>0).sum()),
    ERA5_wet_HH_today=int((p.ERA5_P_mmHH>0).sum())
  ))
 ext_summary=pd.DataFrame(extreme_summ)
 ext_windows=pd.concat(extremes,ignore_index=True)
 ledger=pd.read_csv(final_dir/"01_exact_TA_VPD_RH_QBOT_edit_ledger.csv",parse_dates=["time"])
 ensure(len(ledger)==73,"Stage21 targeted meteorology edit count drift: expected 73")
 full_ledger=ledger.merge(frame(audit)[display],how="left",on="time",validate="one_to_one")
 ensure(full_ledger.tower_TA_C.notna().all(),"Missing tower joined edit records")

 print("STAGE22 PROVENANCE PASS: original tower SHA, ERA5 companion SHA, Stage28/21 lineage")
 print("Stage21 full candidate SHA256:",digest(candidate))
 print("BOUNDARY JUMPS:",len(edges),"LOW_RH_HH:",len(low),"LOW_RH_EPISODES:",len(eps),
       "RAIN_ZERO_ERA_HOLD_DAYS:",len(holds),"EXTREMES:",len(ext_summary))
 print("\n=== REMAINING TEMPERATURE/2023 BRIDGE/APPROVED EVENT WINDOWS ===")
 for name,x in sections.items():
  print("\n---",name,"---")
  print(x.round(3).to_string(index=False,na_rep="NA"))
 print("\n=== ALL LOW RH EPISODES: first 35 highest-duration ===")
 print(eps.head(35).to_string(index=False))
 print("\n=== LOW RH RECOMMENDATION CLASS COUNTS ===")
 print(eps.groupby("suggested_review_class").agg(
   episodes=("episode_id","size"),half_hours=("half_hours","sum")).to_string())
 print("\n=== ALL 28 RAIN ZERO-ERA HOLD DAYS WITH NEIGHBORING ERA5 ===")
 print(hold_sum.round(4).to_string(index=False))
 print("\n=== TWO EXTREME RAIN EVENTS, TOWER QC/ERA5/BEFORE/AFTER ===")
 print(ext_summary.round(4).to_string(index=False))
 for t,x in zip(EXTREME_TIMES,extremes):
  print("\n--- Extreme precipitation +/-12h around",t,"---")
  print(x.round(4).to_string(index=False,na_rep="NA"))
 if arg.print_all:
  print("\n=== ALL 412 remaining RH<5 original+ERA5+stage28+stage21 ===")
  print(frame(audit.loc[low.time])[display].round(4).to_string(index=False,na_rep="NA"))
  print("\n=== ALL low RH episodes WITH 2h BEFORE AND AFTER ===")
  print(ctx.round(4).to_string(index=False,na_rep="NA"))
  print("\n=== ALL rain HOLD days with previous-day and next-day hourly P_ERA ===")
  print(hold_context.round(4).to_string(index=False,na_rep="NA"))
 # Compute and write all data in a fresh isolated report directory only
 ensure(not out.exists() and not out.is_symlink(),"New output suddenly appeared")
 out.mkdir(parents=True,exist_ok=False)
 for name,x in sections.items():
  x.to_csv(out/("01_window_"+name+".csv"),index=False)
 eps.to_csv(out/"02_all_remaining_low_RH_EPISODES_priority.csv",index=False)
 frame(audit.loc[low.time])[display].to_csv(out/"03_all_412_low_RH_halfhours_tower_ERA_stage28_stage21.csv",index=False)
 ctx.to_csv(out/"04_all_low_RH_event_before_after_2h.csv",index=False)
 hold_sum.to_csv(out/"05_all_28_rain_HOLD_daily_neighbor_ERA5.csv",index=False)
 hold_context.to_csv(out/"06_all_rain_HOLD_prev_today_next_3days_HH.csv",index=False)
 ext_summary.to_csv(out/"07_two_extreme_rain_event_summary.csv",index=False)
 ext_windows.to_csv(out/"08_two_extreme_rain_before_after_12h.csv",index=False)
 full_ledger.to_csv(out/"09_all_73_operator_edits_before_after_tower_ERA.csv",index=False)
 edges.to_csv(out/"10_three_remaining_jump_warnings.csv",index=False)
 metadata={
  "operator_review_only":True,"no_original_writes":True,"no_slurm":True,
  "stage21_directory":str(final_dir),"stage21_candidate_sha256":digest(candidate),
  "selected_stage28_sha256":digest(selected),"tower_raw_sha256":digest(raw),
  "ERA5_companion_sha256":digest(era),
  "low_RH_records":len(low),"low_RH_episodes":len(eps),"rain_HOLD_days":len(holds),
  "extreme_events":len(ext_summary),
  "methodology":"exact matching source timestamp labels; not independently validated actual sensor accumulation-day semantics",
  "science_note":"not an instruction to automatically overwrite low-RH QC0 or extreme rain; requires operator approval"
 }
 (out/"00_science_review_manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
 print("\nREAD-ONLY SCIENCE REVIEW COMPLETE")
 print("OUTPUT_DIR=",out)
 print("FILES: 01 windows x6; 02-04 ALL 412 RH; 05-06 ALL 28 rain holds; 07-08 two extremes; 09 all 73 previous edits; 10 boundaries")
 print("ACTIVE DATM/CIME/SLURM/ORIGINAL DATA: UNCHANGED")

if __name__=="__main__":
 main()
