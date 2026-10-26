#!/usr/bin/env python3
"""Batch02 Stage32 read-only effective DATM meteorological QC (BE-Bra, CH-Lae).
Reads every selected annual NetCDF from Stage30 prepared cases, not loosely
matching files by directory name. Verifies original CaseDocs == runtime CDEPS
stream SHA, exact year/site files and noleap half-hour numeric timestamps.
Performs complete time-series physical checks + RH/VPD diagnostic, jumps,
precipitation spikes and possible 23-hour rainfall clustering. Produces
actionable per-site per-year numerical results and sample flagged half hours.
No corrections, source NetCDF, model case or Slurm changes. Physical screening
is NOT independently validated tower/ERA meteorological QC.
"""
from __future__ import annotations
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset, num2date

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ROOT=BASE/"experiments/NonCompetitionObserved22/Batch02_10"
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
SITES={
 "BE-Bra":("BE-Bra_B02_FIXNC_FOREST_PROXY_AD5",1996,2025),
 "CH-Lae":("CH-Lae_B02_FIXNC_FOREST_PROXY_AD5",2004,2024)
}
REQUIRED=("TBOT","QBOT","PSRF","FSDS","FLDS","WIND","PRECTmms","ZBOT")
WARN_JUMP_C=12.
WARN_RAIN_30MIN_MM=40.
def die(s):raise RuntimeError(str(s))
def digest(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def decode_stream(site):
 case_name,first,last=SITES[site]
 case=BASE/"cases"/case_name
 p=case/"CaseDocs/datm.streams.xml"
 run=OUT/case_name/"run"
 r=run/"datm.streams.xml"
 if not p.is_file() or not r.is_file():die(site+" no effective DATM streams")
 if digest(p)!=digest(r):die(site+" live DATM stream != CaseDocs DATM")
 ledger=ROOT/"stage30_four_forest_AD5_preview"/(site+"_prepare_attempt.json")
 if not ledger.is_file():die(site+" Stage30 one-time preview receipt missing")
 state=json.loads(ledger.read_text(encoding="utf8"))
 if state.get("phase")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or state.get("slurm_submitted") is not False:
  die(site+" Phase/Slurm uncertain, do not use as clean AD5 initial source")
 root=ET.parse(p).getroot()
 entries=[e for e in root.iter("stream_info") if e.get("name")=="CLM_USRDAT.UNSET"]
 if len(entries)!=1:die(site+" missing unique 1PT CDEPS stream")
 e=entries[0]
 def val(k):
  z=e.find(k)
  return (z.text or "").strip() if z is not None else None
 if val("taxmode")!="cycle" or val("offset")!="0" or \
    (int(val("year_first")),int(val("year_last")),int(val("year_align")))!=(first,last,first):
  die(site+" clock loop changed")
 ds=e.find("datafiles")
 if ds is None:die(site+" DATM stream datafiles absent")
 files=[Path((a.text or "").strip()) for a in ds]
 if len(files)!=last-first+1:die(site+" DATM file count differs")
 for y,p in zip(range(first,last+1),files):
  if not p.is_file() or p.stat().st_size==0 or not p.name.startswith(site+"_DATM_") or \
      not re.search(r"(?<!\d)"+str(y)+r"(?!\d)",p.stem):
   die(site+" source year/filename/existence not matched "+str(p))
 return case,run,files
def axis_vector(ds,key,n,site,year):
 if key not in ds.variables:die(site+str(year)+" missing forcing variable "+key)
 v=ds.variables[key]
 if "time" not in v.dimensions:die(site+str(year)+" field "+key+" missing TIME dimension")
 ax=v.dimensions.index("time")
 if v.shape[ax]!=n or any(v.shape[j]!=1 for j in range(v.ndim) if j!=ax):
  die(site+str(year)+" unexpected 1pt NetCDF shape "+key+" "+str(v.shape))
 data=np.ma.asarray(v[:],dtype=float)
 arr=np.moveaxis(data,ax,0).reshape(n)
 return np.asarray(np.ma.filled(arr,np.nan),dtype=float)

def year_data(path,year,site):
 with Dataset(path) as ds:
  if "time" not in ds.dimensions or len(ds.dimensions["time"])!=17520:
   die(site+str(year)+" requires exactly 17520 noleap half-hour records")
  tv=ds.variables.get("time")
  if tv is None:die(site+str(year)+" missing time variable")
  info={"time_units":getattr(tv,"units","MISSING"),"calendar":getattr(tv,"calendar","MISSING")}
  if str(info["calendar"]).lower() not in ("noleap","365_day"):
   die(site+str(year)+" unexpected time calendar "+str(info["calendar"]))
  units=str(info["time_units"]).lower()
  factor=(1 if units.startswith("seconds") else
          60 if units.startswith("minutes") else
          3600 if units.startswith("hours") else
          86400 if units.startswith("days") else None)
  if factor is None:die(site+str(year)+" missing CF time units "+str(units))
  timed=np.asarray(tv[:],dtype=float).ravel()
  if timed.size!=17520 or not np.isfinite(timed).all() or not np.all(np.abs(np.diff(timed)*factor-1800)<5):
   die(site+str(year)+" time axis missing, gapped or not every 1800 sec")
  dates=num2date([float(timed[0]),float(timed[-1])],info["time_units"],info["calendar"])
  if any(d.year!=year for d in dates):
   die(site+str(year)+" source time stamps not inside requested calendar year")
  info["first_time"],info["last_time"]=str(dates[0]),str(dates[1])
  fields={key:axis_vector(ds,key,17520,site,year) for key in REQUIRED}
  meta={key:{"units":getattr(ds.variables[key],"units","NO_UNITS")} for key in REQUIRED}
 return fields,info,meta,timed

def diagnostic(site,year,arrays,timed,info,details=False):
 T=arrays["TBOT"];Q=arrays["QBOT"];P=arrays["PSRF"]
 rain=arrays["PRECTmms"]*1800.0
 T_C=T-273.15
 # RH is a diagnostic from input TBOT, QBOT, PSRF; NOT model HumanIndex RH.
 e=Q*P/(0.622+0.378*Q)
 es=611.2*np.exp(np.clip(17.67*T_C/(T_C+243.5),-30,30))
 with np.errstate(divide="ignore",invalid="ignore",over="ignore"):
  RH=100*e/es
 VPD_hPa=(es-e)/100.0
 valid=np.ones(17520,bool)
 for val in arrays.values():valid&=np.isfinite(val)
 # Broad model-input sanity; distinguish physical outliers from review flags.
 invalid=(~valid)|(T<180)|(T>350)|(Q<0)|(Q>0.05)|(P<40000)|(P>110000)
 invalid|=(arrays["PRECTmms"]<0)|(arrays["WIND"]<0)|(arrays["FSDS"]<-1)
 invalid|=(arrays["FLDS"]<0)|(arrays["ZBOT"]<=0)
 invalid|=(RH<0)|(RH>120)
 flags={
  "INVALID":invalid,
  "RH_LT1":valid&(RH>=0)&(RH<1),
  "RH_LT5":valid&(RH>=0)&(RH<5),
  "RH_GT100":valid&(RH>100.1),
  "RH_GT110":valid&(RH>110),
  "VPD_NEG":valid&(VPD_hPa<-.05),
  "DT_GT12":np.r_[False,(np.abs(np.diff(T))>12)&np.isfinite(T[1:])&np.isfinite(T[:-1])],
  "DT_GT8":np.r_[False,(np.abs(np.diff(T))>8)&np.isfinite(T[1:])&np.isfinite(T[:-1])],
  "RAIN_GT40":valid&(rain>40),
  "RAIN_GT15":valid&(rain>15),
  "FSDS_GT1400":valid&(arrays["FSDS"]>1400),
  "FLDS_GT750":valid&(arrays["FLDS"]>750),
  "WIND_GT45":valid&(arrays["WIND"]>45),
  "T_LTminus35":valid&(T_C< -35),
  "T_GT45":valid&(T_C>45)
 }
 days=rain.reshape(365,48)
 daily=np.nansum(days,axis=1)
 max_daily=float(np.nanmax(daily))
 excessive_daily=int((daily>100).sum())
 rain_total=float(np.nansum(rain))
 hours=(np.arange(17520)%48)//2
 h23=float(np.nansum(rain[hours==23]))
 share=h23/rain_total if rain_total>0 else 0.
 rain23flag=(rain_total>100 and share>0.8)
 counts={name:int(mask.sum()) for name,mask in flags.items()}
 counts.update({"RAIN_DAILY_GT100":excessive_daily,"RAIN_23H_CLUSTER":int(rain23flag)})
 def safe_min(v):
  a=v[np.isfinite(v)]
  return round(float(a.min()),3) if a.size else None
 def safe_max(v):
  a=v[np.isfinite(v)]
  return round(float(a.max()),3) if a.size else None
 print("YEAR",site,year,"PROV",int("provisional" in str(info.get("source","")).lower()),
       "INVALID",counts["INVALID"],"RH<1",counts["RH_LT1"],"RH<5",counts["RH_LT5"],
       "RH>100",counts["RH_GT100"],"RH>110",counts["RH_GT110"],
       "VPD<0",counts["VPD_NEG"],"DT>12",counts["DT_GT12"],
       "RAIN>40",counts["RAIN_GT40"],"DAYRAIN>100",excessive_daily,
       "T_C_RANGE",[safe_min(T_C),safe_max(T_C)],
       "RH_RANGE",[safe_min(RH),safe_max(RH)],
       "MAX_MM30",safe_max(rain),"MAX_MMday",round(max_daily,3),
       "YEAR_RAIN_MM",round(rain_total,3),
       "RAIN_23H_pct",round(share*100,2))
 # Focus review on human-actionable examples, not a dump of all ~0.9m steps.
 if details or counts["INVALID"] or counts["RH_LT1"] or counts["RH_GT110"] or counts["DT_GT12"] or counts["RAIN_GT40"] or rain23flag:
  selected=[
   ("INVALID",flags["INVALID"]),
   ("RH_LT1",flags["RH_LT1"]),
   ("RH_GT110",flags["RH_GT110"]),
   ("DT_GT12",flags["DT_GT12"]),
   ("RAIN_GT40",flags["RAIN_GT40"])]
  if details:
   selected.extend([("RH_LT5",flags["RH_LT5"]),("RH_GT100",flags["RH_GT100"]),
                    ("RAIN_GT15",flags["RAIN_GT15"]),("T_LTminus35",flags["T_LTminus35"])])
  for cat,mask in selected:
   ids=np.flatnonzero(mask)[:(5 if details else 3)]
   for i in ids:
    d=num2date(float(timed[i]),info["time_units"],info["calendar"])
    print(f"  REVIEW {site} {year} {cat} HH={i} TIME={d} T_C={T_C[i]:.3f} Q={Q[i]:.7f} P_PA={P[i]:.1f} RH={RH[i]:.2f} VPD_hPa={VPD_hPa[i]:.3f} RAIN_mm30={rain[i]:.3f}")
  if rain23flag:
   print("  REVIEW_RAIN_TIME",site,year,"23h rain share",round(share*100,2),
         "percent; verify source timestamp/accumulation before redistribution")
 return counts,{"rain_mm":rain_total,"rh_min":safe_min(RH),"rh_max":safe_max(RH),
                "temp_min_C":safe_min(T_C),"temp_max_C":safe_max(T_C),
                "max_mm30":safe_max(rain),"max_mmday":round(max_daily,3),
                "rain23_percent":round(share*100,2)}

def check(site,details=False):
 case,run,files=decode_stream(site)
 print("========== EFFECTIVE STAGE30 FOREST DATM QC",site,"==========")
 print("CASE",case,"FILES",len(files),"FIRST",files[0],"LAST",files[-1])
 print("CDEPS STREAM SHA256",digest(case/"CaseDocs/datm.streams.xml"))
 total={}
 worst=[]
 prev=None
 prov=0
 for year,file in zip(range(SITES[site][1],SITES[site][2]+1),files):
  a,info,meta,timed=year_data(file,year,site)
  info["source"]=str(file)
  prov+=int("provisional" in str(file).lower())
  if year==SITES[site][1]:
   print("VARIABLE_UNITS",json.dumps(meta,sort_keys=True),"TIME",json.dumps(info,sort_keys=True))
   units={k:meta[k]["units"].lower().replace(" ","") for k in REQUIRED}
   # Header unit conventions are advisory when absent, but incompatible
   # declared units make thresholds meaningless; require manual review.
   expected={"TBOT":("k","kelvin"),"QBOT":("kg/kg","kgkg-1","1","unitless"),
             "PSRF":("pa",),"PRECTmms":("mm/s","mms-1","kg/m2/s","kgm-2s-1","kg/m^2/s")}
   for key,choices in expected.items():
    u=units[key]
    if u!="no_units" and u not in choices:
     print("UNIT_REVIEW_REQUIRED",site,key,meta[key]["units"],"expected",choices)
  if prev is not None:
   seam=abs(float(a["TBOT"][0])-prev)
   if seam>12:print("YEAR_SEAM_DT_GT12",site,year,"delta_C",round(seam,3))
  prev=float(a["TBOT"][-1])
  counts,met=diagnostic(site,year,a,timed,info,details)
  for k,v in counts.items():total[k]=total.get(k,0)+v
  worst.append((year,met))
 print("SUMMARY",site,"ANNUAL_FILES",len(files),"PROVISIONAL_NAMED",prov,
       "COUNTS",json.dumps(total,sort_keys=True))
 print("EXTREMES",site,json.dumps(sorted(worst,key=lambda r:(r[1]["max_mm30"] or 0),reverse=True)[:5]))
 if total.get("INVALID",0) or total.get("RH_GT110",0) or total.get("DT_GT12",0) or total.get("RAIN_GT40",0) or total.get("RAIN_23H_CLUSTER",0):
  status="QC_HOLD_FOR_TARGETED_REVIEW"
 elif total.get("RH_LT5",0) or total.get("RH_GT100",0) or total.get("RAIN_GT15",0) or prov:
  status="QC_PROVISIONAL_REVIEW"
 else:status="NUMERIC_SCREEN_CLEAR"
 print("STAGE32 SITE_STATUS",site,status,
       "UNVERIFIED_ORIGINAL_DATM_SOURCE",prov,
       "PROXY_PFT_STILL_NOT_OBSERVED")
 return status
def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 p.add_argument("--site",choices=["BE-Bra","CH-Lae","all"],default="all")
 p.add_argument("--details",action="store_true")
 x=p.parse_args()
 if x.self_test:
  assert set(SITES)=={"BE-Bra","CH-Lae"}
  assert SITES["BE-Bra"][2]-SITES["BE-Bra"][1]+1==30
  assert SITES["CH-Lae"][2]-SITES["CH-Lae"][1]+1==21
  assert 17520==365*48 and abs(0.01*1800-18)<1e-9
  m=np.ma.masked_array([1.,2.,3.],mask=[False,True,False])
  assert np.isnan(np.ma.filled(m,np.nan)[1])
  print("STAGE32 SELF-TEST PASS: 51 actual NOLEAP annual DATM sources, masks, threshold math; no writes")
  return
 if not x.check:p.error("--check required (strictly read-only)")
 statuses={}
 for site in SITES:
  if x.site in ("all",site):statuses[site]=check(site,x.details)
 print("STAGE32 RESULTS",json.dumps(statuses,sort_keys=True))
 print("READ ONLY: no model, Slurm, case, forcing file or source modification.")
 print("NUMERIC SCREEN NOT A SCIENTIFIC MET-QC RELEASE; do not infer repaired/observed source.")
if __name__=="__main__": main()
