#!/usr/bin/env python3
"""ES-LJu Stage23: scoped operator-approved ERA5 boundary extensions, isolated candidate.
NO modification to Stage21, Stage28, raw flux or ERA5 files, DATM, cases or Slurm.
Adaptive endpoints require 3 consecutive half-hours where tower and ERA5 TA
differ by <=3 C within a maximum 48-hour lookback/lookahead. If not found,
HOLD this window; do not apply speculative partial patches.
2006: ERA5 TA + verified neighboring QC1 median offset 0.852 C; keep VPD.
2019/2023: pair ERA5 TA+VPD, recompute RH/QBOT consistently.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

D=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10")
STAGE21=D/"stage21_20261026T011416Z"
SOURCE16=D/"stage16_ES_LJu_manual_review_v1_20261025"/"00_science_lineage_and_review_questions.json"
LOOK=96
DELTA_MAX=3.0
STABLE=3
SPEC=[
 ("2006-05-31_to_Jun01","forward","2006-06-01 00:00","ERA_TA_PLUS_2006_QC1_BIAS_KEEP_VPD"),
 ("2019-06-30_late","forward","2019-06-30 07:00","ERA_TA_VPD_PAIR"),
 ("2023-01-15_early","backward","2023-01-15 01:00","ERA_TA_VPD_PAIR"),
]
def die(msg):raise RuntimeError(str(msg))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def sat(t):return 6.112*np.exp(np.clip(17.67*t/(t+243.5),-20,20))
def thermo(t,v,p):
 e=(sat(t)-v)*100
 q=.622*e/(p-.378*e)
 rh=100*e/(sat(t)*100)
 if not (np.isfinite(q) and np.isfinite(rh) and 1<=rh<=100 and 0<q<.05):
  die(f"Invalid patched T/VPD pair: T={t} VPD={v}, RH={rh} QBOT={q}")
 return float(q),float(rh)
def load(path,cols):
 available=pd.read_csv(path,nrows=0).columns
 need=["TIMESTAMP_START"]+[x for x in cols if x in available]
 x=pd.read_csv(path,usecols=need,dtype={"TIMESTAMP_START":str},low_memory=False)
 x["time"]=pd.to_datetime(x.TIMESTAMP_START.astype(str).str.replace(r"\.0$","",regex=True),
                           format="%Y%m%d%H%M",errors="raise")
 x=x[x.time.dt.year.between(2004,2024)&
     ~((x.time.dt.month==2)&(x.time.dt.day==29))].copy()
 for c in need[1:]:
  x[c]=pd.to_numeric(x[c],errors="coerce")
  x.loc[x[c]<=-9990,c]=np.nan
 if x.time.duplicated().any():die(f"Duplicate source times {path}")
 return x.sort_values("time").set_index("time")
def self_test():
 assert abs(np.median([1.15,.265,1.443,.7,.781,.852,1.087])-.852)<1e-9
 q,r=thermo(21.5765,20.225,100000)
 assert q>0 and 1<r<100
 print("STAGE23 SELF-TEST PASS: 2006 offset + paired humidity physics")
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--self-test",action="store_true")
 a.add_argument("--out",type=Path)
 opt=a.parse_args()
 self_test()
 if opt.self_test:return
 if opt.out is None:die("--out needed")
 dest=opt.out.expanduser().resolve()
 if dest.exists() or dest.is_symlink():die("Refuse existing --out")
 stage_manifest=json.loads((STAGE21/"06_manifest.json").read_text())
 s16=json.loads(SOURCE16.read_text())
 selected=Path(s16["stage28_source"]["path"])
 original=Path(s16["original_fluxmet_hourly"]["raw_path"])
 era=Path(stage_manifest["ERA5_companion"])
 prior=STAGE21/"ES-LJu_stage21_full21yr_provisional_forcing.csv"
 for p in [selected,original,era,prior]:
  if not p.is_file():die(f"Missing source {p}")
 if (sha(selected)!=s16["stage28_source"]["sha256"] or
     sha(selected)!=stage_manifest["original_sha256"]):die("Stage28 provenance SHA mismatch")
 if (sha(original)!=s16["original_fluxmet_hourly"]["sha256"] or
     sha(original)!=stage_manifest["tower_original_sha256"]):die("Original source SHA mismatch")
 if sha(era)!=stage_manifest["ERA5_sha256"]:die("ERA5 provenance SHA mismatch")
 src=load(original,["TA_F","TA_F_QC","VPD_F","VPD_F_QC","P_F","P_F_QC"])
 comp=load(era,["TA_ERA","VPD_ERA","P_ERA"])
 candidate=pd.read_csv(prior,low_memory=False)
 candidate["time"]=pd.to_datetime(candidate.time,errors="raise")
 if (len(candidate)!=367920 or not candidate.time.is_unique or
     not candidate.time.is_monotonic_increasing):
  die("Stage21 candidate timeline mismatch")
 idx=pd.DatetimeIndex(candidate.time)
 if not (idx.equals(src.index) and idx.equals(comp.index)):
  die("Original/ERA5/candidate timestamp labels misaligned")
 if not all(k in candidate for k in ["TA_USE","VPD_USE","TBOT","QBOT","PSRF","PRECTmms"]):
  die("Missing Stage21 columns")
 if not all(k in src for k in ["TA_F","TA_F_QC","VPD_F","VPD_F_QC","P_F","P_F_QC"]):
  die("Missing tower source cols")
 if not all(k in comp for k in ["TA_ERA","VPD_ERA","P_ERA"]):
  die("Missing ERA5 cols")
 lut={t:i for i,t in enumerate(idx)}
 bias=float(stage_manifest["2006_QC1_median_T_minus_ERA_C"])
 if abs(bias-.852)>1e-6:die("2006 offset unexpectedly changed")
 scopes=[]
 rows=[]
 holds=[]
 for key,direction,boundary,method in SPEC:
  anchor=lut.get(pd.Timestamp(boundary))
  if anchor is None:die("Unknown anchor "+boundary)
  # Require three consecutive *tower* records of stable temperature agreement.
  # QC flags are recorded for review; QC0 alone is not guaranteed physically valid.
  def stable_at(j):
   js=range(j,j+STABLE)
   return all(0<=q<len(idx) and
              np.isfinite(src.iloc[q].TA_F) and
              np.isfinite(comp.iloc[q].TA_ERA) and
              abs(float(src.iloc[q].TA_F)-float(comp.iloc[q].TA_ERA))<=DELTA_MAX
              for q in js)
  if direction=="forward":
   recovery=next((j for j in range(anchor, min(len(idx)-STABLE+1,anchor+LOOK))
                  if stable_at(j)),None)
   lo=anchor
   hi=(recovery-1) if recovery is not None else None
  else:
   recovery=next((j for j in range(anchor-STABLE, max(-1,anchor-LOOK-STABLE),-1)
                  if stable_at(j)),None)
   lo=(recovery+STABLE) if recovery is not None else None
   hi=anchor
  if recovery is None or hi is None or lo is None or hi<lo:
   holds.append({"event":key,"anchor":boundary,
                 "reason":"NO_3_CONSECUTIVE_TOWER_ERA_WITHIN_3C_IN_48H"})
   # Save a full +/- 12h original context for actual operator decision.
   start=max(0,anchor-24);end=min(len(idx),anchor+25)
   for j in range(start,end):
    rows.append({"event":key,"status":"UNRESOLVED_CONTEXT",
      "time":str(idx[j]),"tower_T_C":float(src.iloc[j].TA_F),
      "tower_T_QC":float(src.iloc[j].TA_F_QC),
      "era_T_C":float(comp.iloc[j].TA_ERA),
      "era_VPD_hPa":float(comp.iloc[j].VPD_ERA),
      "tower_VPD_hPa":float(src.iloc[j].VPD_F),
      "tower_VPD_QC":float(src.iloc[j].VPD_F_QC),
      "Stage21_T_C":float(candidate.iloc[j].TA_USE),
      "Stage23_T_C":float(candidate.iloc[j].TA_USE),
      "T_minus_ERA_C":float(src.iloc[j].TA_F-comp.iloc[j].TA_ERA)})
   continue
  # Scope is now bounded by 3 consecutive original-T/ERA matches.
  lo=max(0,lo);hi=min(len(idx)-1,hi)
  edits=[]
  for j in range(lo,hi+1):
   record=comp.iloc[j]
   newt=float(record.TA_ERA)+bias if method.startswith("ERA_TA_PLUS") else float(record.TA_ERA)
   newv=float(candidate.iloc[j].VPD_USE) if method.startswith("ERA_TA_PLUS") else float(record.VPD_ERA)
   q,r=thermo(newt,newv,float(candidate.iloc[j].PSRF))
   edits.append((j,newt,newv,q,r))
  # Boundary checks after editing against untouched neighboring times
  replacement={j:t for j,t,*_ in edits}
  values=candidate.TA_USE.to_numpy(dtype=float)
  def val(k):return replacement.get(k,float(values[k]))
  edge_before=abs(val(lo)-val(lo-1)) if lo>0 else 0
  edge_after=abs(val(hi+1)-val(hi)) if hi+1<len(idx) else 0
  status=("BOUNDED" if max(edge_before,edge_after)<=5 else "BOUNDARY_GT5C_REVIEW")
  if status!="BOUNDED":
   holds.append({"event":key,"anchor":boundary,
                 "reason":f"Remaining join jump {edge_before:.3f}/{edge_after:.3f} C; edits provisional only"})
  for j,t,v,q,r in edits:
   before=float(candidate.at[j,"TA_USE"])
   oldv=float(candidate.at[j,"VPD_USE"])
   candidate.at[j,"TA_USE"]=t
   candidate.at[j,"VPD_USE"]=v
   candidate.at[j,"TBOT"]=t+273.15
   candidate.at[j,"QBOT"]=q
   rows.append({"event":key,"status":status,"time":str(idx[j]),
     "tower_T_C":float(src.iloc[j].TA_F),
     "tower_T_QC":float(src.iloc[j].TA_F_QC),
     "era_T_C":float(comp.iloc[j].TA_ERA),
     "era_VPD_hPa":float(comp.iloc[j].VPD_ERA),
     "tower_VPD_hPa":float(src.iloc[j].VPD_F),
     "tower_VPD_QC":float(src.iloc[j].VPD_F_QC),
     "Stage21_T_C":before,"Stage23_T_C":t,
     "Stage21_VPD_hPa":oldv,"Stage23_VPD_hPa":v,
     "Stage23_RH_pct":r,"Stage23_QBOT":q,
     "T_minus_ERA_C":float(src.iloc[j].TA_F-comp.iloc[j].TA_ERA)})
  scopes.append({"event":key,"start":str(idx[lo]),"end":str(idx[hi]),
                 "n_HH":len(edits),"normal_recovery_start":str(idx[recovery]),
                 "join_T_jump_before_C":round(float(edge_before),4),
                 "join_T_jump_after_C":round(float(edge_after),4),
                 "status":status})
 print("STAGE23 SOURCE SHA and TIMELINE VERIFIED")
 print("BOUNDED RECOVERY SCOPES:")
 print(pd.DataFrame(scopes).to_string(index=False))
 print("HOLD/UNRESOLVED:")
 print(pd.DataFrame(holds).to_string(index=False))
 editlog=pd.DataFrame(rows)
 if not editlog.empty:print("EXACT EVENT HEAD/TAlL\n",editlog.head(12).round(3).to_string(index=False))
 # Run science consistency checks, never force remaining RH<5% to ERA5.
 active=~((candidate.time.dt.month==2)&(candidate.time.dt.day==29))
 if not active.all():die("NOLEAP guard failed")
 if not (np.isfinite(candidate[["TBOT","QBOT","PRECTmms"]].to_numpy(dtype=float)).all() and
         (candidate.QBOT>=0).all() and (candidate.PRECTmms>=0).all()):
  die("Stage23 candidate physical numeric failed")
 # Focused very-heavy-rain read-only evidence, original source vs companion ERA5
 print("\nEXTREME RAIN EVENTS: raw tower and paired ERA5 P_ERA (mm/HH)")
 for target in ["2013-12-25 02:00","2016-12-06 10:00"]:
  date=pd.Timestamp(target)
  i=lut[date]
  rr=[]
  for j in range(max(0,i-8),min(len(idx),i+9)):
   rr.append(dict(time=str(idx[j]),original_P_mm=float(src.iloc[j].P_F),
                  P_QC=float(src.iloc[j].P_F_QC),
                  ERA5_P_mm=float(comp.iloc[j].P_ERA),
                  Stage23_P_mm=float(candidate.iloc[j].PRECTmms)*1800,
                  tower_T_C=float(src.iloc[j].TA_F),
                  ERA5_T_C=float(comp.iloc[j].TA_ERA)))
  print(target,"\n",pd.DataFrame(rr).round(4).to_string(index=False))
 # Non-decisional low-RH residual QC inventory (no extra replacements)
 low_index=pd.read_csv(STAGE21/"07_remaining_RH_below5_ERA_comparison.csv",parse_dates=["time"])
 flag=pd.DataFrame({"time":low_index.time})
 flag["tower_T_QC"]=src.loc[flag.time,"TA_F_QC"].to_numpy()
 flag["tower_VPD_QC"]=src.loc[flag.time,"VPD_F_QC"].to_numpy()
 flag["stage21_RH_pct"]=low_index.candidate_RH_pct.to_numpy()
 flag["ERA_RH_pct"]=low_index.ERA_RH_pct.to_numpy()
 flag["original_both_QC0"]=(flag.tower_T_QC==0)&(flag.tower_VPD_QC==0)
 print("\nREMAINING LOW-RH QC EVIDENCE: both QC0",
       int(flag.original_both_QC0.sum()),"/",len(flag),
       "; not automatically changed")
 dest.mkdir(parents=True,exist_ok=False)
 editlog.to_csv(dest/"01_three_temperature_boundary_adaptive_scopes.csv",index=False)
 pd.DataFrame(scopes).to_csv(dest/"02_recovered_scope_summary.csv",index=False)
 pd.DataFrame(holds).to_csv(dest/"03_unresolved_scope_HOLD.csv",index=False)
 flag.to_csv(dest/"04_all_low_RH_source_QC_preserve_decisions.csv",index=False)
 # Copy Stage21 rainfall mass distribution unchanged for Stage23.
 if not holds:
  candidate["time"]=candidate.time.dt.strftime("%Y-%m-%d %H:%M:%S")
  candidate.to_csv(dest/"ES-LJu_stage23_boundary_repaired_full21yr_candidate.csv",index=False)
 else:
  print("NO WHOLE-YEAR STAGE23 FORCING WRITTEN; boundary HOLD requires operator review")
 (dest/"05_metadata.json").write_text(json.dumps({
     "source_Stage21_candidate_path":str(prior),
     "source_Stage21_sha256":sha(prior),
     "remaining_low_RH_are_NOT_changed":True,
     "rainfall_28_HOLD_are_NOT_changed":True,
     "temperature_scopes":scopes,"HOLD":holds,
     "whole_year_candidate_created":not holds,
     "active_DATM_changed":False,"jobs_submitted":False
 },indent=2)+"\n")
 print("OUTPUT:",dest)
 print("PREVIEW ONLY: ORIGINALS/STAGE21/DATM/CIME/SLURM UNCHANGED")

if __name__=="__main__": main()
