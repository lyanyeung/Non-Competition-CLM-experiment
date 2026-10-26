#!/usr/bin/env python3
"""ES-LJu Stage24: operator-approved 2016-12-06 precipitation time redistribution.
Read-only original tower and companion ERA; new ISOLATED Stage24 candidate only.
- Retain entire 2016-12-06 tower DAILY accumulation.
- Allocate that amount over 48 half-hours using same-date companion ERA5 P_ERA.
- Retain all 28 Stage21 zero-ERA rain-HOLD days, with no synthetic rain timing.
- Keep 2013-12-25 untouched and SCIENCE_HOLD: ERA5 does not independently
  corroborate tower extreme magnitude or temporal peak.
- Keep all Stage23 air-temperature/VPD/QBOT corrections unchanged, all low-RH
  source records unchanged, no blanket threshold-driven replacement.
DO NOT edit active DATM, cases, originals, Stage21/Stage23 outputs or Slurm.
Timestamp joins are same-labeled FLUXNET half-hours, not independently verified
rain-gauge daily accumulation-day clocks.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

STAGE21=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage21_20261026T011416Z")
DEFAULT23=Path("/iridisfs/home/ly3n24/ES_LJu_stage23_20261026T013605Z")
STAGE16=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage16_ES_LJu_manual_review_v1_20261025")
TARGET=pd.Timestamp("2016-12-06")
HOLD_DAY=pd.Timestamp("2013-12-25")

def stop(message): raise RuntimeError(str(message))
def ensure(condition,message):
 if not bool(condition):stop(message)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for x in iter(lambda:f.read(1<<20),b""):h.update(x)
 return h.hexdigest()

def model(path):
 d=pd.read_csv(path,low_memory=False)
 required={"time","TA_USE","VPD_USE","TBOT","QBOT","PSRF","PRECTmms"}
 ensure(required.issubset(d.columns),f"{path}: missing {required-set(d.columns)}")
 d["time"]=pd.to_datetime(d.time,errors="raise")
 ensure(len(d)==367920 and d.time.is_unique and d.time.is_monotonic_increasing,
        "Expected exactly 21x365x48 unique ordered model half-hours")
 ensure(not ((d.time.dt.month==2)&(d.time.dt.day==29)).any(),"Model NOLEAP mismatch")
 ensure(np.isfinite(d.PRECTmms.to_numpy(dtype=float)).all() and
        (d.PRECTmms.to_numpy(dtype=float)>=0).all(),
        "Original Stage23 precip invalid")
 return d

def source(path,cols):
 columns=set(pd.read_csv(path,nrows=0).columns)
 required={"TIMESTAMP_START",*cols}
 ensure(required.issubset(columns),f"Original {path}: missing {required-columns}")
 d=pd.read_csv(path,usecols=["TIMESTAMP_START",*cols],
               dtype={"TIMESTAMP_START":str},low_memory=False)
 d["time"]=pd.to_datetime(d.TIMESTAMP_START.astype(str).str.replace(r"\.0$","",regex=True),
                          format="%Y%m%d%H%M",errors="raise")
 d=d.loc[d.time.dt.year.between(2004,2024) &
         ~((d.time.dt.month==2)&(d.time.dt.day==29))].copy()
 for k in cols:
  d[k]=pd.to_numeric(d[k],errors="coerce")
  d.loc[d[k]<=-9990,k]=np.nan
 ensure(len(d)==367920 and d.time.is_unique,
        "Source timeline has missing/repeated half-hours")
 return d.sort_values("time").reset_index(drop=True)

def test():
 w=np.array([0.,1.,2.,3.])
 p=43.382
 q=p*w/w.sum()
 ensure(abs(float(q.sum())-p)<1e-9 and q[0]==0,"ERA shape conservation failure")
 print("STAGE24 SELF-TEST PASS | exact day conservation, no writes")

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--self-test",action="store_true")
 ap.add_argument("--stage23",type=Path,default=DEFAULT23)
 ap.add_argument("--out",type=Path)
 x=ap.parse_args()
 test()
 if x.self_test:return
 ensure(x.out is not None,"--out required")
 out=x.out.expanduser().resolve()
 ensure(not out.exists() and not out.is_symlink(),"Output exists; refuse overwrite")
 parent=x.stage23.expanduser().resolve()
 m23=json.loads((parent/"05_metadata.json").read_text())
 ensure(m23["whole_year_candidate_created"] and len(m23["HOLD"])==0,
        "Stage23 not fully bounded; cannot create Stage24")
 path23=parent/"ES-LJu_stage23_boundary_repaired_full21yr_candidate.csv"
 path21=STAGE21/"ES-LJu_stage21_full21yr_provisional_forcing.csv"
 meta21=json.loads((STAGE21/"06_manifest.json").read_text())
 meta16=json.loads((STAGE16/"00_science_lineage_and_review_questions.json").read_text())
 raw=Path(meta21["tower_raw_source"])
 era=Path(meta21["ERA5_companion"])
 old28=Path(meta16["stage28_source"]["path"])
 ensure(all(p.is_file() for p in (path23,path21,raw,era,old28)),
        "A previously approved input file missing")
 ensure(sha(path21)==m23["source_Stage21_sha256"],"Stage23 parent input SHA mismatch")
 ensure(sha(raw)==meta16["original_fluxmet_hourly"]["sha256"]==
        meta21["tower_original_sha256"],"Original tower SHA mismatch")
 ensure(sha(era)==meta21["ERA5_sha256"],"Original ERA5 SHA mismatch")
 ensure(sha(old28)==meta16["stage28_source"]["sha256"]==
        meta21["original_sha256"],"Stage28 provenance SHA mismatch")
 df=model(path23)
 rawd=source(raw,["P_F","P_F_QC","TA_F","TA_F_QC","VPD_F","VPD_F_QC"])
 erad=source(era,["P_ERA","TA_ERA","VPD_ERA"])
 ensure(df.time.equals(rawd.time) and df.time.equals(erad.time),
        "Tower/ERA/model half-hour timestamp labels differ: stop")
 baseline=df.copy(deep=True)
 day_mask=df.time.dt.normalize()==TARGET
 hold_mask=df.time.dt.normalize()==HOLD_DAY
 ensure(int(day_mask.sum())==48 and int(hold_mask.sum())==48,
        "Expected exactly 48 HH on each special day")
 positions=np.flatnonzero(day_mask.to_numpy())
 raw_p=rawd.loc[day_mask,"P_F"].to_numpy(dtype=float)
 raw_qc=rawd.loc[day_mask,"P_F_QC"].to_numpy(dtype=float)
 era_p=erad.loc[day_mask,"P_ERA"].to_numpy(dtype=float)
 old_p=df.loc[day_mask,"PRECTmms"].to_numpy(dtype=float)*1800.
 ensure(np.isfinite(raw_p).all() and (raw_p>=0).all(),
        "2016 rain source invalid")
 ensure(np.isfinite(era_p).all() and (era_p>=0).all() and era_p.sum()>0,
        "2016 ERA5 all zero/negative/missing: HOLD no redistribution")
 ensure(np.allclose(raw_p,old_p,atol=.0005,rtol=0),
        "2016 Stage23 already diverges from original tower daily precipitation")
 ensure(np.isclose(float(raw_p[20]),43.382,atol=.0005),
        "2016 10:00 QC0 43.382mm source anchor changed")
 ensure(float(raw_qc[20])==0,
        "2016 10:00 QC0 provenance changed")
 original_daily=float(raw_p.sum())
 fractions=era_p/float(era_p.sum())
 new_p=original_daily*fractions
 ensure(np.isclose(float(new_p.sum()),original_daily,atol=1e-8,rtol=1e-12),
        "2016 daily rainfall mass conservation failed")
 df.loc[day_mask,"PRECTmms"]=new_p/1800.
 actual_day=float(df.loc[day_mask,"PRECTmms"].sum()*1800.)
 ensure(np.isclose(actual_day,original_daily,atol=1e-8,rtol=1e-12),
        "2016 written candidate daily rain total not conserved")
 unchanged=(~day_mask).to_numpy()
 ensure(np.array_equal(df.loc[~day_mask,"PRECTmms"].to_numpy(),
                       baseline.loc[~day_mask,"PRECTmms"].to_numpy()),
        "Non-2016 rain changed: stop")
 ensure(np.array_equal(df.loc[hold_mask,"PRECTmms"].to_numpy(),
                       baseline.loc[hold_mask,"PRECTmms"].to_numpy()),
        "2013-12-25 rain changed: stop")
 for variable in ("TA_USE","VPD_USE","TBOT","QBOT","PSRF"):
  ensure(np.array_equal(df[variable].to_numpy(),baseline[variable].to_numpy()),
         f"Stage23 original meteorology changed in {variable}: stop")
 # Leave the original 28 HOLD days completely unchanged.
 hold=pd.read_csv(STAGE21/"04_ERA_dry_or_missing_rain_HOLD.csv")
 ensure(len(hold)==28 and hold.day.nunique()==28,
        "Operator's 28 rain-HOLD dates provenance changed")
 totals=[]
 for day in hold.day:
  d=pd.Timestamp(day)
  mask=df.time.dt.normalize()==d
  b=float(baseline.loc[mask,"PRECTmms"].sum()*1800)
  a=float(df.loc[mask,"PRECTmms"].sum()*1800)
  ensure(np.isclose(a,b,atol=1e-10,rtol=0),
         "Unapproved low-rain HOLD day modified: "+str(day))
  totals.append(b)
 ensure(max(totals)<=3.351 and np.isclose(sum(totals),25.140,atol=.005),
        "Operator 28-HOLD daily rainfall totals drift: inspect before approval")
 low_idx=pd.read_csv(STAGE21/"07_remaining_RH_below5_ERA_comparison.csv",parse_dates=["time"])
 retained_review=pd.DataFrame({
    "time":low_idx.time,
    "raw_TA_QC":low_idx.raw_TA_QC,
    "raw_VPD_QC":low_idx.raw_VPD_QC,
    "source_qc_pair_ok":(low_idx.raw_TA_QC==0)&(low_idx.raw_VPD_QC==0),
    "decision":"RETAIN_NO_AUTOMATIC_RH_REPLACEMENT",
    "scientific_note":"QC0 is only preliminary quality evidence; Stage23 changed some TA/VPD windows"
 })
 table=pd.DataFrame({
   "time":df.loc[day_mask,"time"].to_numpy(),
   "original_tower_P_mm_per_30min":raw_p,
   "source_P_QC":raw_qc,
   "ERA5_P_ERA_mm_per_30min":era_p,
   "ERA5_fraction_of_same_day":fractions,
   "Stage23_P_mm_per_30min":old_p,
   "Stage24_new_P_mm_per_30min":new_p
 })
 summary={
   "target_day":str(TARGET.date()),
   "original_tower_daily_total_mm":original_daily,
   "ERA5_same_day_total_mm":float(era_p.sum()),
   "Stage23_tower_daily_total_mm":float(old_p.sum()),
   "Stage24_reallocated_daily_total_mm":actual_day,
   "before_tower_max_halfhour_mm":float(old_p.max()),
   "after_max_halfhour_mm":float(new_p.max()),
   "after_wet_halfhours":int((new_p>0).sum()),
   "rain_hold_28_days_count":len(hold),
   "rain_hold_28_days_total_mm":round(sum(totals),4),
   "rain_hold_max_daily_mm":round(max(totals),4),
   "2013_12_25_status":"SCIENCE_HOLD_SOURCE_QC0_ERA5_MAGNITUDE_AND_PEAK_TIME_DISAGREE",
   "2013_12_25_original_precip_left_untouched":True,
   "remaining_low_RH_policy":"No threshold-based edits; retain source QC0/physically credible, other QC for review",
   "Stage23_parent_candidate_sha256":sha(path23),
   "no_active_DATM_or_CIME_or_Slurm_changes":True
 }
 print("STAGE24 SOURCE PROVENANCE SHA / SAME-LABEL TIMELINE PASS")
 print("\n2016-12-06 PRECIP RECONSTRUCTION: old tower DAILY",original_daily,
       "ERA5 daily",float(era_p.sum()),"new daily",actual_day)
 print(table.round(5).to_string(index=False))
 print("STAGE24 28 LOW-RAIN HOLD DAYS PRESERVED:",len(hold),
       "daily total sum",round(sum(totals),3),"max day",round(max(totals),3))
 print("STAGE24 2013-12-25 EXTREME SCIENCE HOLD: unchanged")
 print("STAGE24 RH SOURCE QC0 pairs / listed 412:",
       int(retained_review.source_qc_pair_ok.sum()),"/",len(retained_review),
       "all RH values from Stage23 unchanged")
 # Write only new output folder after all scientific invariants pass.
 ensure(not out.exists() and not out.is_symlink(),"Output directory appeared before write")
 out.mkdir(parents=True,exist_ok=False)
 table.to_csv(out/"01_2016-12-06_all48_tower_ERA5_before_after.csv",index=False)
 pd.DataFrame({"day":hold.day,"original_tower_daily_total_mm":totals,
               "decision":"RETAIN_ORIGINAL_DAILY_RECORD_UNDISTRIBUTED"}).to_csv(
   out/"02_28_LOW_RAIN_HOLD_originals_retained.csv",index=False)
 retained_review.to_csv(out/"03_remaining_RH_412_QC_evidence_preserved.csv",index=False)
 df["time"]=df.time.dt.strftime("%Y-%m-%d %H:%M:%S")
 df.to_csv(out/"ES-LJu_stage24_full21yr_provisional_candidate.csv",index=False)
 (out/"04_science_decision_manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
 print("\nSTAGE24 FINISHED, PROVISIONAL ONLY:",out)
 print("No modifications to active DATM, Stage23 source, originals, CIME or Slurm.")

if __name__=="__main__":main()
