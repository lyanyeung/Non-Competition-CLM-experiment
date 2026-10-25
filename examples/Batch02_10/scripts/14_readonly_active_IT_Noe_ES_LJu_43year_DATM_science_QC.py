#!/usr/bin/env python3
"""Stage14: actual 43-year CDEPS DATM numeric/source review for prepared AD5.
READ ONLY. IT-Noe 2004-2025 (22 annual NCs), ES-LJu 2004-2024
(21 PROVISIONAL annual NCs). Read EXACT user-nl-selected datafiles from
the NEW Stage13 CIME CaseDocs (never guesses latest candidate files).
QC/model physics screening is NOT scientific approval; no auto replacement.

Check Stage13 two exact receipts in PREVIEW_VERIFIED_NOT_SUBMITTED, the
matching new (not legacy source) CaseDocs and RUNDIR DATM stream, no jobs,
exact site/year and noleap 17520x30min, required 8 meteorological
variables, numeric physical bounds, diagnostics for 2010 IT-Noe and
2023 ES-LJu, continuity, approximate RH from TBOT/QBOT/PSRF, per-30min
precipitation and ES-LJu 23:00 concentration. Actual source caveats
remain open independent of checks. Does NOT touch NetCDF / CIME / Slurm.
"""
from __future__ import annotations
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ROOT=BASE/"experiments/NonCompetitionObserved22/Batch02_10"
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
SITES={
 "IT-Noe":("IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5",2004,2025),
 "ES-LJu":("ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5",2004,2024)
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
 ledger=ROOT/"stage13_two_bare_shrub_AD5_preview"/(site+"_prepare_attempt.json")
 if not ledger.is_file():die(site+" Stage13 one-time proof missing")
 state=json.loads(ledger.read_text(encoding="utf8"))
 if state.get("phase")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or state.get("slurm_submitted") is not False:
  die(site+" Phase/Slurm uncertain, do not use as clean AD5 initial source")
 for sp in (case/"CaseStatus",):
  if sp.is_file():
   content=sp.read_text(errors="replace")
   if any(word in content for word in ("case.run starting","case.submit starting","model execution starting")):
    die(site+" CIME case has already been submitted; STOP review-only startup assumptions")
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
 if "time" not in v.dimensions:
  die(site+str(year)+" field "+key+" missing TIME dimension")
 ax=v.dimensions.index("time")
 if v.shape[ax]!=n:die(site+str(year)+" field "+key+" time dimension mismatch")
 if any(v.shape[j]!=1 for j in range(v.ndim) if j!=ax):
  die(site+str(year)+" field "+key+" not 1pt; shape="+str(v.shape))
 # Only ~17520 time records for a single site; no full-domain allocations.
 a=np.ma.asarray(v[:],dtype=float)
 if np.ma.getmaskarray(a).any():
  return np.full(n,np.nan)
 return np.moveaxis(a,ax,0).reshape(n)
def year_data(path,year,site):
 with Dataset(path) as ds:
  if "time" not in ds.dimensions or len(ds.dimensions["time"])!=17520:
   die(site+str(year)+" expected exactly 17520 noleap half-hour rows")
  tv=ds.variables.get("time")
  info={"time_units":getattr(tv,"units","MISSING"),"calendar":getattr(tv,"calendar","MISSING")}
  if tv is None:die(site+str(year)+" missing time variable")
  if info["calendar"].lower() not in ("noleap","365_day"):
   die(site+str(year)+" time calendar is not NOLEAP "+str(info["calendar"]))
  units=info["time_units"].lower()
  if units.startswith("seconds"):factor=1
  elif units.startswith("minutes"):factor=60
  elif units.startswith("hours"):factor=3600
  elif units.startswith("days"):factor=86400
  else:die(site+str(year)+" time units not CF-normalized "+str(info["time_units"]))
  timed=np.asarray(tv[:],dtype=float).ravel()
  if len(timed)!=17520 or not np.isfinite(timed).all() or \
     np.max(abs(np.diff(timed)*factor-1800))>5:
   die(site+str(year)+" time axis missing/gapped/not half-hourly")
  fields={key:axis_vector(ds,key,17520,site,year) for key in REQUIRED}
  meta={key:{"units":getattr(ds.variables[key],"units","NO_UNITS")} for key in REQUIRED}
 return fields,info,meta
def diagnostic(site,year,arrays):
 T=arrays["TBOT"];Q=arrays["QBOT"];P=arrays["PSRF"]
 pre=arrays["PRECTmms"]; t_C=T-273.15
 # Approximate vapour-pressure RH above water as a screening diagnostic only.
 e=Q*P/(0.622+0.378*Q)
 es=611.2*np.exp(np.clip(17.67*t_C/(t_C+243.5),-20,20))
 RH=100*e/es
 rain=pre*1800
 jumps=np.abs(np.diff(T))
 invalid=np.zeros(17520,bool)
 for k,v in arrays.items():invalid|=~np.isfinite(v)
 invalid|=(T<180)|(T>350)|(Q<0)|(Q>0.05)|(P<40000)|(P>110000)
 invalid|=(pre<-1e-12)|(arrays["WIND"]<0)|(arrays["FSDS"]<-1)|(arrays["FLDS"]<-1)
 any_invalid=int(invalid.sum())
 rh_bad=int(np.sum((RH<0)|(RH>120)))
 rh_lt5=int(np.sum(RH<5))
 rh_gt100=int(np.sum(RH>100.1))
 large_temp_jump=int(np.sum(jumps>WARN_JUMP_C))
 strong_rain=int(np.sum(rain>WARN_RAIN_30MIN_MM))
 print(f"YEAR {year} {site} INVALID_PHYSICAL={any_invalid} RH_LT5={rh_lt5} RH_GT100p1={rh_gt100} RH_NEG_OR_GT120={rh_bad} DT_GT12={large_temp_jump} RAIN_GT40MM_30MIN={strong_rain} T_C_MIN={np.nanmin(t_C):.3f} T_C_MAX={np.nanmax(t_C):.3f} APPROX_RH_MIN={np.nanmin(RH):.3f} APPROX_RH_MAX={np.nanmax(RH):.3f} MAX_RAIN_MM30={np.nanmax(rain):.3f}")
 if site=="IT-Noe" and year==2010 or site=="ES-LJu" and year==2023:
  flagged=np.where((~np.isfinite(T))|(t_C<-35)|(jumps.mean() if False else False))[0]
  combos=(RH<0)|(RH<1)|(RH>100.1)|(rain>40)|(t_C<-35)|(t_C>50)
  jumps_idx=np.where(jumps>12)[0]
  combos[jumps_idx]=True;combos[np.minimum(jumps_idx+1,17519)]=True
  flagged=np.where(combos)[0]
  print("REVIEW YEAR",site,year,"FLAGGED_RH/T/RAIN/DT",len(flagged))
  # Only brief fixed first-15 context; raw met values are retained on IRIDIS.
  for i in flagged[:15]:
   print(f"   HH={i:05d} NOLEAP_DOY={i//48+1:03d} TIME_SLOT={i%48//2:02d}:{30*(i%2):02d} T_C={t_C[i]:.3f} Q={Q[i]:.6f} P_PA={P[i]:.1f} RH_DIAGNOSTIC={RH[i]:.3f} PRECIP_MM30={rain[i]:.3f}")
 if site=="ES-LJu":
  wet=rain>0.01
  wet23=wet[np.arange(17520)%48//2==23]
  all23=rain[np.arange(17520)%48//2==23]
  print("ES-LJu 23H RAIN bins count",int(wet23.sum()),"mm total",round(float(np.nansum(all23)),3),
        "total year mm",round(float(np.nansum(rain)),3),
        "diagnostic-only; no time redistribution without source provenance")
 return {"invalid":any_invalid,"rh_lt5":rh_lt5,"rh_gt100":rh_gt100,
         "jumps":large_temp_jump,"rain_gt40":strong_rain}
def check(site):
 case,run,files=decode_stream(site)
 print("========== SELECTED ACTUAL STAGE13 CDEPS INPUT",site,"==========")
 print("CASE",case,"FILES",len(files),"FIRST",files[0],"LAST",files[-1])
 print("CDEPS SHA",digest(case/"CaseDocs/datm.streams.xml"))
 total={"invalid":0,"rh_lt5":0,"rh_gt100":0,"jumps":0,"rain_gt40":0}
 prevT=None
 for year,file in zip(range(SITES[site][1],SITES[site][2]+1),files):
  a,info,meta=year_data(file,year,site)
  if year==SITES[site][1]:print("VAR UNITS FIRST YEAR",json.dumps(meta,sort_keys=True),"TIME",info)
  if prevT is not None:
   seam=abs(float(a["TBOT"][0])-prevT)
   if seam>12:print("YEAR SEAM WARNING",site,year,"delta_C",round(seam,4))
  prevT=float(a["TBOT"][-1])
  result=diagnostic(site,year,a)
  for k,v in result.items():total[k]+=v
 print("AGGREGATE",site,json.dumps(total,sort_keys=True))
 if total["invalid"]:print("NUMERIC FAIL: unacceptable physical input; inspect original source NetCDF")
 elif total["rh_gt100"] or total["rh_lt5"] or total["jumps"] or total["rain_gt40"]:
  print("NUMERIC FLAGS require source-QC/timing review; flags alone do not prove invalid measurements")
 else:print("NUMERIC SCREEN clear at chosen coarse thresholds")
 if site=="IT-Noe":
  print("SCIENCE_HOLD=IT-Noe historical negative model 2m RH; selected ERA5_ABW branch, pending attribution to verified v3 full cycle; Juniperus cannot be assumed equivalent to evergreen BROADLEAF shrub")
 else:
  print("SCIENCE_HOLD=ES-LJu all 21 DATM names PROVISIONAL; 2023 temperature/ERA patch and rain 23:00 source QC/time accumulation not approved; evergreen shrub trait assumed")
 print("STAGE14 MODEL_SUBMISSION_APPROVAL=NO (review-only, no case/forcing changes)")
def main():
 p=argparse.ArgumentParser(description=__doc__)
 a=p.add_mutually_exclusive_group(required=True)
 a.add_argument("--self-test",action="store_true")
 a.add_argument("--check",action="store_true")
 p.add_argument("--site",choices=["IT-Noe","ES-LJu","all"],default="all")
 x=p.parse_args()
 if x.self_test:
  assert len(SITES)==2
  assert all(SITES[z][2]-SITES[z][1]+1 in (21,22) for z in SITES)
  assert abs(100*(0.01*100000/(0.622+0.378*0.01))/611.2-100*1606.82/611.2)<1
  print("STAGE14 SELF-TEST PASS: 43 annual files 2 sites, noleap 30-minute science screens; NO WRITES")
  return
 if not x.check:p.error("--check required (read-only)")
 for s in SITES:
  if x.site in ("all",s):check(s)
 print("STAGE14 READONLY MET REVIEW DONE; NO MODEL/SURFACE/NETCDF/SLURM WRITES")
if __name__=="__main__":main()
