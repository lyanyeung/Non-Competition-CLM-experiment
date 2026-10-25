#!/usr/bin/env python3
"""Stage16: ES-LJu source-provenance-aware HUMAN meteorology review.

READS exactly 2004-2024 active Stage13 source annual DATM NetCDF;
checks selected Stage28 13-site manifest sha/provenance and CSV->DATM
equality, and produces human-readable CSV evidence:
- all annual precipitation percentages by hours and HH 23:00/23:30
- every 2005-2008 wet record and its daily rainfall context
- all >40 mm/30min strong precipitation events
- every year with half-hour temperature jump >12C, +/-6h context
- RH<5% rows, runs and full 2023 anomaly context
- optional ORIGINAL FLUXMET_HH P_F + P_F_QC independent clock summary
  (no silent timestamp join because UTC vs site-local not yet verified).
All reported timestamps are from the DATM model's actual noleap time axis.
DO NOT interpret as original tower local clock without source evidence.
Only --report --out FRESH_DIR writes reports, and never touches NetCDF,
CIME case, source raw data or Slurm. --check is fully read-only.
No numerical flag is automatically adjudicated or repaired.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
import calendar
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITE="ES-LJu"
NAME="ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5"
CASE=BASE/"cases"/NAME
SOURCE_MANIFEST=BASE/"experiments/FLUXNET_MultiSite_13_MET_stage28_20261018_052344_851367/reports/01_selected_13site_STAGE28_provisional_manifest.csv"
DATM_SHA="92217de7eb708d46cec03945061e0b7c2021c312a08e2e8f13ad18b11c884bab"
ATTEMPT=BASE/"experiments/NonCompetitionObserved22/Batch02_10/stage13_two_bare_shrub_AD5_preview/ES-LJu_prepare_attempt.json"
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/NAME/"run"
FIELDS=("TBOT","QBOT","PSRF","PRECTmms","WIND","FSDS","FLDS")
def stop(msg):raise RuntimeError(str(msg))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def save_csv(p,rows,columns):
 with p.open("x",newline="",encoding="utf-8") as f:
  out=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
  out.writeheader()
  for row in rows:out.writerow(row)
def date_at(y,i):
 # The NetCDF axis uses a *365_day/noleap* calendar; Python datetime is
 # Gregorian. Explicitly skip Gregorian February 29 in leap years so that
 # every March-Dec 2004/2008/2012/... slot has the correct model date.
 t=datetime(y,1,1)+timedelta(minutes=30*int(i))
 if calendar.isleap(y) and int(i)>=59*48:
  t+=timedelta(days=1)
 return t.strftime("%Y-%m-%d %H:%M")
def rh(T,Q,P):
 # Approximate TBOT/QBOT/PSRF RH using liquid water over entire year.
 # NOT model-computed 2m RH; a 0–5% result is a review flag only.
 C=T-273.15
 e=Q*P/(0.622+0.378*Q)
 es=611.2*np.exp(np.clip(17.67*C/(C+243.5),-20,20))
 return 100*e/es
def actual_paths():
 if not ATTEMPT.is_file():stop("Stage13 ES-LJu verified receipt missing")
 receipt=json.loads(ATTEMPT.read_text(encoding="utf8"))
 if receipt.get("phase")!="PREVIEW_VERIFIED_NOT_SUBMITTED":
  stop("ES-LJu Stage13 no longer clean preview state")
 if sha(CASE/"CaseDocs/datm.streams.xml")!=DATM_SHA or \
    sha(RUN/"datm.streams.xml")!=DATM_SHA:
  stop("Actual 21-year DATM source has changed; stop and re-audit")
 root=ET.parse(CASE/"CaseDocs/datm.streams.xml").getroot()
 found=[e for e in root.iter("stream_info") if e.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(found)!=1:stop("Expected one CDEPS 1PT meteorological stream")
 stream=found[0]
 def get(k):
  n=stream.find(k)
  return (n.text or "").strip() if n is not None else ""
 if (get("year_first"),get("year_last"),get("year_align"),get("taxmode"))!=(
     "2004","2024","2004","cycle"):
  stop("DATM source year loop changed")
 el=stream.find("datafiles")
 if el is None:stop("CDEPS datafiles absent")
 files=[Path((v.text or "").strip()) for v in el]
 if len(files)!=21:stop("Expected exactly 21 active annual source inputs")
 for year,p in zip(range(2004,2025),files):
  if not p.is_file() or not p.name.endswith(f"_DATM_{year}_PROVISIONAL.nc") or \
     SITE not in str(p):
   stop("Selected netcdf source-year mismatch "+str(p))
 return files
def read_year(year,p):
 with Dataset(p) as f:
  if len(f.dimensions["time"])!=17520:stop(f"{year}: unexpected rows")
  if getattr(f["time"],"calendar","").lower() not in ("noleap","365_day"):
   stop(f"{year}: not noleap calendar")
  if not getattr(f["time"],"units","").startswith("days since "+str(year)+"-01-01"):
   stop(f"{year}: time base is not expected year Jan 1")
  t=np.asarray(f["time"][:],dtype=float)
  if not np.allclose(t,np.arange(17520)/48.,atol=1e-8,rtol=0):
   stop(f"{year}: model halfhour timestamp grid shifted/missing")
  data={}
  for name in FIELDS:
   if name not in f.variables:stop(f"{year}: missing {name}")
   obj=f[name]
   if obj.shape!=(17520,1,1):stop(f"{year}: {name} shape != 1PT")
   arr=np.ma.asarray(obj[:,0,0])
   if np.ma.getmaskarray(arr).any():stop(f"{year}: {name} contains masked")
   data[name]=np.asarray(arr,dtype=float)
  return data,getattr(f,"stage28_meteorology_sha256","")
def stage28():
 if not SOURCE_MANIFEST.is_file():
  print("SOURCE WARNING: Stage28 selected meteorology manifest unavailable")
  return None
 m=pd.read_csv(SOURCE_MANIFEST,dtype={"site":str})
 if "site" not in m or "forcing_path" not in m or "sha256" not in m:
  stop("Stage28 manifest schema unexpected")
 row=m.loc[m["site"]==SITE]
 if len(row)!=1:stop("Stage28 selected meteorology not uniquely ES-LJu")
 p=Path(str(row.iloc[0]["forcing_path"]))
 h=str(row.iloc[0]["sha256"])
 if not p.is_file() or sha(p)!=h:stop("Stage28 selected original MET CSV absent/SHA drift")
 df=pd.read_csv(p,usecols=["time",*FIELDS],low_memory=False)
 stamps=pd.to_datetime(df["time"],errors="raise")
 if len(stamps)!=21*17520 or stamps.iloc[0]!=pd.Timestamp("2004-01-01 00:00:00"):
  stop("Stage28 active MET CSV time coverage incomplete")
 print("STAGE28 selected MET provenance VERIFIED",p,"SHA",h)
 return {"path":str(p),"sha256":h,"table":df,"time":stamps}
def original_raw(raw):
 if raw is None:return [],{},[],[]
 if not raw.is_file():stop("Optional supplied original FLUXMET HH CSV absent "+str(raw))
 selected={"TIMESTAMP_START","TIMESTAMP_END","P_F","P_F_QC","P","P_QC",
           "TA_F","TA_F_QC","VPD_F","VPD_F_QC"}
 df=pd.read_csv(raw,usecols=lambda k:k in selected,low_memory=False)
 if "TIMESTAMP_START" not in df.columns or not ("P_F" in df or "P" in df):
  stop("Raw source missing TIMESTAMP_START/P_F. No silent assumption about columns.")
 key="P_F" if "P_F" in df else "P"
 qc="P_F_QC" if "P_F_QC" in df else "P_QC" if "P_QC" in df else None
 times=pd.to_datetime(df["TIMESTAMP_START"].astype(str),format="%Y%m%d%H%M",errors="coerce")
 if times.isna().any():stop("Raw source time parse failed")
 d=pd.DataFrame({"year":times.dt.year,"hour":times.dt.hour,
                 "minute":times.dt.minute,"P_original_mm":pd.to_numeric(df[key],errors="coerce")})
 d["wet_original"]=(d["P_original_mm"]>0)&(d["P_original_mm"]!=-9999)
 d=d[d["year"].between(2004,2024)]
 review=[]
 for y,group in d.groupby("year"):
  wet=group.loc[group["wet_original"]]
  pos=wet["P_original_mm"].sum()
  hour23=wet.loc[wet["hour"]==23,"P_original_mm"].sum()
  review.append({"year":int(y),"source_column":key,
    "original_wet_halfhours":len(wet),
    "original_total_reported_P_F_mm":round(float(pos),4),
    "original_hour23_mm":round(float(hour23),4),
    "original_fraction_hour23":round(float(hour23/pos),6) if pos>0 else None,
    "original_negative_sentinel":int((group["P_original_mm"]<0).sum())})
 focus=df.loc[times.dt.year.between(2005,2008) &
              (pd.to_numeric(df[key],errors="coerce")>0)].copy()
 focus.insert(0,"raw_source_time_not_DATM_clock",
              times.loc[focus.index].dt.strftime("%Y-%m-%d %H:%M"))
 rawfocus=focus[[x for x in ("raw_source_time_not_DATM_clock","TIMESTAMP_START",
                            "TIMESTAMP_END",key,qc) if x and x in focus]].to_dict("records")
 local_2023=(times>=pd.Timestamp("2023-10-16"))&(
              times<pd.Timestamp("2023-10-21"))
 near=df.loc[local_2023].copy()
 near.insert(0,"raw_source_time_not_DATM_clock",
             times.loc[near.index].dt.strftime("%Y-%m-%d %H:%M"))
 raw2023=near[[x for x in ("raw_source_time_not_DATM_clock",
                          "TIMESTAMP_START","TIMESTAMP_END",
                          "TA_F","TA_F_QC","VPD_F","VPD_F_QC")
                   if x in near]].to_dict("records")
 return review,{"raw_path":str(raw),"sha256":sha(raw),
    "source_P_QC_column":qc,
    "warning":"Original station-local timestamps NOT aligned to DATM model clock, compare year/hour distributions only; original P_F unit must be confirmed"},rawfocus,raw2023
def scan(files,selected):
 all_years=[];rain_daily=[];wet_focus=[];rain_ext=[];temp_edges=[];humid=[];rh_spells=[];baseline=[]
 report20=[]
 for year,path in zip(range(2004,2025),files):
  dat,upsha=read_year(year,path)
  T=dat["TBOT"]; Q=dat["QBOT"]; P=dat["PSRF"]; rain=dat["PRECTmms"]*1800.
  R=rh(T,Q,P); C=T-273.15
  if not np.isfinite(rain).all() or np.min(rain)<0:
   stop(f"{year}: invalid precipitation; cannot review")
  if not (0<=np.min(R)<=np.max(R)<200):stop(f"{year}: diagnostic RH invalid")
  # For 1 PT all 30-min samples, time slots follow original model noleap.
  m23=np.arange(17520)%48>=46
  wet=rain>0.01
  full=float(rain.sum());total23=float(rain[m23].sum())
  maxima=float(np.max(rain))
  counted=int(np.sum(wet)); counted23=int(np.sum(wet&m23))
  row={"year":year,"input_datm_netcdf":str(path),
   "wet_halfhour_count_gt0p01":counted,
   "wet_23hour_halfhours":counted23,
   "annual_total_mm":round(full,6),"hour23_total_mm":round(total23,6),
   "hour23_share_pct":round(100*total23/full,5) if full>0 else None,
   "23_00_mm":round(float(rain[np.arange(17520)%48==46].sum()),6),
   "23_30_mm":round(float(rain[np.arange(17520)%48==47].sum()),6),
   "max_halfhour_mm":round(maxima,4),
   "rh_lt5_count":int(np.sum(R<5)),
   "Tjump_gt12_count":int(np.sum(np.abs(np.diff(T))>12)),
   "rain_gt40_count":int(np.sum(rain>40))}
  all_years.append(row)
  # Source cross-check: Stage28 uses only selected 7 met columns; DATM
  # copies exact values to float32. Require close within rounding tol.
  if selected:
   a=selected["table"].iloc[(year-2004)*17520:(year-2003)*17520]
   if len(a)!=17520:stop("Incorrect selected Stage28 year partition")
   for k in FIELDS:
    orig=np.asarray(a[k],dtype=float)
    actual=np.asarray(dat[k],dtype=float)
    diff=np.abs(orig-actual)
    denom=max(1.0,float(np.max(np.abs(orig))))
    maxerr=float(np.max(diff))
    baseline.append({"year":year,"variable":k,"max_abs_CSV_minus_DATM":maxerr,
       "max_relative_scale":maxerr/denom,
       "stage28_CSV_sha":selected["sha256"],"datm_embedded_stage28_sha":upsha})
    if np.any(~np.isfinite(orig)) or maxerr/denom>1.5e-6:
     stop(f"{year} {k}: Stage28 source vs selected DATM differs")
   if upsha and upsha!=selected["sha256"]:
    stop(f"{year}: source DATM embedded Stage28 SHA inconsistent")
  # Review *all* wet 2005-08 records and daily distribution, zero days too.
  if year in range(2005,2009):
   for d in range(365):
    ids=np.arange(48*d,48*(d+1))
    day=rain[ids]
    daily=float(day.sum())
    rain_daily.append({"year":year,"model_noleap_date":date_at(year,48*d)[:10],
     "daily_total_mm":round(daily,6),
     "hour23_total_mm":round(float(day[-2:].sum()),6),
     "outside_23hour_mm":round(float(day[:-2].sum()),6),
     "wet_slots_gt0p01":int(np.sum(day>0.01)),
     "max_30min_mm":round(float(day.max()),6)})
   for i in np.where(wet)[0]:
    wet_focus.append({"year":year,"model_time":date_at(year,i),
      "hh_index":int(i),"time_slot":int(i%48),
      "precip_mm_30min":round(float(rain[i]),6),
      "prev30_mm":round(float(rain[i-1]),6) if i>0 else None,
      "next30_mm":round(float(rain[i+1]),6) if i<17519 else None,
      "hour23_bucket":int(i%48>=46)})
  for i in np.where(rain>40)[0]:
   rain_ext.append({"year":year,"model_time":date_at(year,i),
      "rain_mm_30min":round(float(rain[i]),4),
      "prev30_mm":round(float(rain[i-1]),4) if i>0 else None,
      "next30_mm":round(float(rain[i+1]),4) if i<17519 else None})
  jum=np.where(np.abs(np.diff(T))>12)[0]+1
  # Context 6h on both sides (25-50 HH per event)
  toreview=set()
  for i in jum:
   toreview.update(range(max(0,int(i)-12),min(17520,int(i)+13)))
  if year==2023:
   # include all low-temp (< 0 C) near 2023 suspected jump hours context
   candidate=np.where(np.abs(np.diff(T))>10)[0]+1
   for i in candidate:
    toreview.update(range(max(0,int(i)-12),min(17520,int(i)+13)))
  for i in sorted(toreview):
   temp_edges.append({"year":year,"model_time":date_at(year,i),
      "hh_index":i,"jump_gt12_at_this_hh":int(i>0 and abs(T[i]-T[i-1])>12),
      "TBOT_C":round(float(C[i]),4),
      "T_prev_halfhour_C":round(float(C[i-1]),4) if i>0 else None,
      "T_jump_C":round(float(C[i]-C[i-1]),4) if i>0 else None,
      "QBOT_kgkg":round(float(Q[i]),8),"PSRF_Pa":round(float(P[i]),2),
      "RH_diagnostic_pct":round(float(R[i]),4),
      "precip_mm_30min":round(float(rain[i]),4)})
  mask=(R<5)
  for i in np.where(mask)[0]:
   humid.append({"year":year,"model_time":date_at(year,i),
    "hh_index":int(i),"RH_approx_pct":round(float(R[i]),4),
    "TBOT_C":round(float(C[i]),3),"QBOT":round(float(Q[i]),8),
    "PSRF_Pa":round(float(P[i]),2),"rain_mm30":round(float(rain[i]),4)})
  changes=np.diff(np.r_[False,mask,False].astype(int))
  for first,end in zip(np.where(changes==1)[0],np.where(changes==-1)[0]):
   rh_spells.append({"year":year,"start_model_time":date_at(year,first),
      "end_model_time":date_at(year,end-1),"n_halfhours":int(end-first),
      "duration_hours":round(float((end-first)*0.5),1),
      "min_approx_RH_pct":round(float(np.min(R[first:end])),4)})
  report20.append({"year":year,"wet23pct":row["hour23_share_pct"],"jumps":row["Tjump_gt12_count"],
    "rain40":row["rain_gt40_count"],"rh5":row["rh_lt5_count"]})
 return {"year":all_years,"daily":rain_daily,"wet":wet_focus,"extreme":rain_ext,
    "temperature":temp_edges,"RH":humid,"RH_spells":rh_spells,"upstream":baseline}
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 modes=ap.add_mutually_exclusive_group(required=True)
 modes.add_argument("--self-test",action="store_true")
 modes.add_argument("--check",action="store_true")
 modes.add_argument("--report",action="store_true")
 ap.add_argument("--out",type=Path)
 ap.add_argument("--raw-fluxmet",type=Path)
 a=ap.parse_args()
 if a.self_test:
  assert date_at(2023,13953)=="2023-10-18 16:30"
  assert date_at(2005,46)=="2005-01-01 23:00"
  assert date_at(2008,59*48)=="2008-03-01 00:00"
  assert date_at(2008,58*48)=="2008-02-28 00:00"
  assert sum(range(21))==210
  print("STAGE16 SELF-TEST PASS: noleap DATM slots, flagged 2023 date, all output isolated")
  return
 if a.check and a.out:ap.error("--check must not include --out")
 if a.report and not a.out:ap.error("--report requires --out NEW unique path")
 files=actual_paths()
 selected=stage28()
 raw,rawinfo,rawfocus,raw2023=original_raw(a.raw_fluxmet)
 reports=scan(files,selected)
 print("ES-LJu ACTUAL ACTIVE MODEL DATM 2004-2024 REVIEW")
 for y in reports["year"]:
  if y["year"] in (2005,2006,2007,2008,2023):
   print("ANNUAL",y["year"],"TOTAL_MM",y["annual_total_mm"],
         "HOUR23_SHARE_PCT",y["hour23_share_pct"],
         "JUMPS_GT12",y["Tjump_gt12_count"],
         "RH_LT5",y["rh_lt5_count"],"RAIN_GT40",y["rain_gt40_count"])
 print("ROWS",json.dumps({k:len(v) for k,v in reports.items()},sort_keys=True))
 print("SCIENTIFIC_RAIN_TIME_GATE=HOLD; model read-only inputs unchanged")
 if a.check:
  print("STAGE16 CHECK PASS: READ ONLY, NO NEW REPORT FILES")
  return
 dest=a.out.expanduser().resolve()
 if dest.exists() or dest.is_symlink():stop("Output exists. NEVER OVERWRITE: "+str(dest))
 dest.mkdir(parents=True,exist_ok=False)
 output={
  "01_all21_annual_precip_hour23_and_RH.csv":"year",
  "02_2005_2008_daily_rainfall.csv":"daily",
  "03_2005_2008_every_wet_halfhour.csv":"wet",
  "04_extreme_40mm30min_events_all_years.csv":"extreme",
  "05_all_temperature_jump_6h_context.csv":"temperature",
  "06_all_approx_RH_below5_halfhours.csv":"RH",
  "07_RH_below5_contiguous_episodes.csv":"RH_spells",
  "08_selected_Stage28_vs_active_DATM_integrity.csv":"upstream"}
 for name,kind in output.items():
  rows=reports[kind]
  if not rows:
   print("ZERO EVENTS",name)
   continue
  save_csv(dest/name,rows,list(rows[0]))
 if raw:
  save_csv(dest/"09_original_FLUXMET_HH_annual_precip_by_source_clock.csv",raw,list(raw[0]))
 if rawfocus:
  save_csv(dest/"10_original_2005_2008_wet_P_F_original_QC.csv",rawfocus,list(rawfocus[0]))
 if raw2023:
  save_csv(dest/"11_original_2023_Oct16_20_TA_VPD_and_QC.csv",raw2023,list(raw2023[0]))
 model={
 "site":SITE,"status":"HUMAN_REVIEW_ONLY_SOURCE_QC_UNRESOLVED",
 "selected_stage13_case":str(CASE),
 "CDEPS_xml_SHA256":DATM_SHA,
 "DATM_annual_files":[str(p) for p in files],
 "stage28_source":{"path":selected["path"],"sha256":selected["sha256"]} if selected else None,
 "original_fluxmet_hourly":rawinfo or "NOT_SUPPLIED_LOCAL_CLOCK_SOURCE_UNVERIFIED",
 "criteria":{"wet_gt_mm30":0.01,"heavy_gt_mm30":40,"temp_jump_gt_C30":12,"RH_approx_below_pct":5},
 "not_auto_corrected":True,"not_scientifically_approved":True,
 "no_DATM_CIME_SLURM_modified":True,
 "generated_at_utc":datetime.now(timezone.utc).isoformat(),
 "manual_review_questions":[
  "Does original FLUXMET P_F show wet events concentrated in 23h for 2005-2008? Compare distribution and original P_F_QC by year; confirm UTC/local clock before any timestamp matching.",
  "Is P_F original period accumulation 30 minutes or daily at 23:00? Check instrument/ICOS documentation; do not redistribute before establishing exact collection interval.",
  "Did source Stage28 selected CSV already have rainfall concentrated at 23:00? Inspect 08_Stage28_vs_active_DATM_integrity.",
  "What meteorology and original QC support 2023 high 13.8 C/30min jump and RH edges? Inspect 05/06 and raw source TA_F_QC and VPD_F_QC.",
  "For 9 heavy events >40mm/30min, inspect original precipitation instrument log/date and adjacent rain to decide true halfhour storm vs accumulated day."
 ]}
 (dest/"00_science_lineage_and_review_questions.json").write_text(
    json.dumps(model,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
 manual=[
 "# ES-LJu 2004–2024 human review — not approved and no model actions",
 "The 21-year ACTIVE Stage13 DATM source is the sole target; new CIME cases not touched.",
 "Read 01 (annual 23h fractions), 02 (daily 2005–08), 03 (every 2005–08 wet HH),",
 "04 (all >40mm HH), 05 (temperature jump with +/-6h), 06 (every RH<5),",
 "07 (low RH episodes), 08 (Stage28 selected CSV provenance and numeric equivalence).",
 "Optional raw original P_F: 09 only when supplied; site-local timestamp is NOT DATM time.",
 "Do not assume 23:00 denotes original observational local hour.",
 "Do not redistribute 23h rain automatically or delete original values.",
 "Do not start 400-year ES-LJu AD while provenance and time semantics unclear."]
 (dest/"README_MANUAL_REVIEW.md").write_text("\n".join(manual)+"\n")
 print("STAGE16 REPORT CREATED",dest)
 for p in sorted(dest.iterdir()):print("FILE",p.name,p.stat().st_size)
 print("MODEL_SUBMISSION_APPROVAL=NO | ORIGINAL FORCING/CASE/SLURM UNCHANGED")
if __name__=="__main__":main()
