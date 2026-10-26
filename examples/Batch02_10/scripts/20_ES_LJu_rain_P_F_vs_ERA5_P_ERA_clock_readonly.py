#!/usr/bin/env python3
"""ES-LJu precipitation timing: original tower P_F vs companion site-downscaled ERA5 P_ERA.
Strictly READ ONLY, no changes to forcing/CIME/Slurm or previous reports.
FLUXNET HH precipitation units: mm per half-hour. Uses same labeled TIMESTAMP_START,
not an independently validated time-zone or instrument accumulation interval.
"""
from pathlib import Path
import pandas as pd
import numpy as np

RAW=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/ES-LJu/forcing/raw/EUF_ES-LJu_FLUXNET_2004-2024_v1.3_r1")
def one(pattern):
 files=sorted(RAW.glob(pattern))
 if len(files)!=1: raise RuntimeError(f"Expected one {pattern}, got {files}")
 return files[0]
def load(path, columns):
 hdr=set(pd.read_csv(path,nrows=0).columns)
 if "TIMESTAMP_START" not in hdr: raise RuntimeError("Missing TIMESTAMP_START in "+str(path))
 keep=["TIMESTAMP_START"]+[x for x in columns if x in hdr]
 d=pd.read_csv(path,usecols=keep,dtype={"TIMESTAMP_START":str},low_memory=False)
 d["time"]=pd.to_datetime(d.TIMESTAMP_START.astype(str).str.replace(r"\.0$","",regex=True),
                          format="%Y%m%d%H%M", errors="raise")
 d=d[d.time.dt.year.between(2005,2009)].copy()
 for c in keep[1:]:
  d[c]=pd.to_numeric(d[c],errors="coerce")
  d.loc[d[c]<=-9990,c]=np.nan
 if d.time.duplicated().any(): raise RuntimeError("Duplicate timestamp in "+str(path))
 return d.set_index("time")
def print_table(title,d,cols=None,limit=0):
 print("\n"+"="*100+"\n"+title+"\n"+"="*100)
 if cols: d=d[cols]
 print(d.head(limit).to_string(index=False,na_rep="NA") if limit else d.to_string(index=False,na_rep="NA"))
def main():
 mainp=one("*FLUXMET_HH*.csv")
 erap=one("*ERA5_HH*.csv")
 print("SOURCE P_F:",mainp)
 print("ERA5 COMPANION:",erap)
 print("Units: both P_F and P_ERA = mm per HALF-HOUR of 30-minute original dataset")
 print("Time labels NOT independently checked against UTC, station timezone or rain gauge daily accumulation convention")
 x=load(mainp,["P_F","P_F_QC","P","P_ERA"])
 if "P_F" not in x or "P_F_QC" not in x: raise RuntimeError("Missing tower P_F/QC")
 y=load(erap,["P_ERA"])
 if "P_ERA" not in x and "P_ERA" not in y:
  raise RuntimeError("Neither FLUXMET nor ERA5_HH contains P_ERA: independent ERA rainfall unavailable")
 if not x.index.equals(y.index):
  if not x.index.isin(y.index).all(): raise RuntimeError("ERA5_HH lacks original timestamps")
  y=y.reindex(x.index)
 if "P_ERA" in y:
  x["P_ERA_companion"]=y["P_ERA"]
  if "P_ERA" in x:
   mask=x.P_ERA.notna() & x.P_ERA_companion.notna()
   if mask.any():
    print("FLUXMET vs companion P_ERA max discrepancy (mm/HH):",
          float((x.loc[mask,"P_ERA"]-x.loc[mask,"P_ERA_companion"]).abs().max()))
  x["P_ERA_final"]=x.P_ERA_companion
 else:
  x["P_ERA_final"]=x["P_ERA"]
  print("ERA5 companion lacks P_ERA; using P_ERA embedded in FLUXMET_HH")
 if "P" in x:
  qc0=(x.P_F_QC==0)&x.P_F.notna()&x.P.notna()
  print("QC0 P_F vs raw P differing HH:",int(((x.loc[qc0,"P_F"]-x.loc[qc0,"P"]).abs()>1e-6).sum()))
 def stat(y):
  zz=x[x.index.year==y]
  rec={"year":y}
  for c in ["P_F","P_ERA_final"]:
   v=zz[c].where(zz[c]>0,0)
   total=v.sum()
   h23=v[(v.index.hour==23)].sum()
   rec[c+"_annual_mm"]=round(float(total),3)
   rec[c+"_n_wet_HH"]=int((v>0).sum())
   rec[c+"_pct_rain_at_23h"]=round(100*float(h23)/float(total),3) if total>0 else np.nan
   rec[c+"_max_HH_mm"]=round(float(v.max()),3)
   rec[c+"_pct_zero"]=round(100*float((v==0).mean()),3)
  return rec
 print_table("A. EACH YEAR: 23:00-23:30 RAIN CONCENTRATION P_F VS P_ERA",pd.DataFrame([stat(y) for y in range(2005,2010)]))
 clock=x.copy()
 clock["clock"]=clock.index.strftime("%H:%M")
 clock["year"]=clock.index.year
 for y in range(2005,2010):
  z=clock.loc[clock.year==y]
  g=z.groupby("clock")[["P_F","P_ERA_final"]].agg(lambda s:sum(float(v) for v in s if np.isfinite(v) and v>0))
  # Show 23:00/23:30 and ten ERA peak wettest half-hour clock slots
  g=g.rename(columns={"P_F":"tower_P_F_mm","P_ERA_final":"ERA5_P_ERA_mm"})
  ix=set(g.nlargest(10,"ERA5_P_ERA_mm").index) | {"23:00","23:30"}
  print_table(f"B. {y} rainfall by 30-minute CLOCK: 10 ERA peaks plus source 23:00/23:30",
              g.loc[sorted(ix)].reset_index())
  candidates=z.loc[z.P_F>0,"P_F"].nlargest(3)
  for t,p in candidates.items():
   lo=t-pd.Timedelta(hours=4);hi=t+pd.Timedelta(hours=4)
   part=x.loc[lo:hi].copy()
   part.insert(0,"time",part.index.strftime("%Y-%m-%d %H:%M"))
   print_table(f"C. {y} tower rain peak at {t} = {p:.3f} mm | +/-4 hours",
     part,["time","P_F","P_F_QC","P_ERA_final"],limit=17)
  # List 5 days with >0 tower precipitation and whether ERA rains over more HH
  daily=x.loc[x.index.year==y,["P_F","P_ERA_final"]].copy()
  daily["date"]=daily.index.date
  groups=daily.groupby("date")
  daily_sum=groups.agg(tower_total=("P_F","sum"),ERA_total=("P_ERA_final","sum"),
                       tower_wet_HH=("P_F",lambda s:int((s>0).sum())),
                       ERA_wet_HH=("P_ERA_final",lambda s:int((s>0).sum())))
  daily_sum=daily_sum[daily_sum.tower_total>0].nlargest(8,"tower_total")
  print_table(f"D. {y} 8 largest wet days: number of wet half hours by product",daily_sum.reset_index())
 print("\nREAD ONLY COMPLETE; no precipitation redistributed, no ERA forcing selected.")
if __name__=="__main__":main()
