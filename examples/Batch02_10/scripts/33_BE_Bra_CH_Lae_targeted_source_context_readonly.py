#!/usr/bin/env python3
"""Batch02 Stage33 targeted read-only provenance/context around Stage32 anomalies.

Inspect EXACT selected CDEPS annual forcing for BE-Bra 1996,1999,2002,2005,2021
and CH-Lae 2004-2024. Show ±2h T,Q,RH,VPD,precip around all RH<5
BE-Bra 1996/1999, all >12C jumps in 2005/2021, T>45C 2021,
BE-Bra 2002 days >100mm, and all CH-Lae >8C half-hour jumps.
Source time is read from annual NetCDF CF units, not guessed UTC/tower time.
This is diagnostic only; no ERA inference, replacement, file writes or Slurm.
"""
from __future__ import annotations
import argparse,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,num2date

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
CASE={"BE-Bra":"BE-Bra_B02_FIXNC_FOREST_PROXY_AD5",
      "CH-Lae":"CH-Lae_B02_FIXNC_FOREST_PROXY_AD5"}
KEYS=("TBOT","QBOT","PSRF","PRECTmms")
def stop(msg):raise RuntimeError(str(msg))
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def paths(site):
 name=CASE[site];case=BASE/"cases"/name
 a=case/"CaseDocs/datm.streams.xml";b=RUN/name/"run/datm.streams.xml"
 if not a.is_file() or not b.is_file() or sha(a)!=sha(b):
  stop(site+" effective DATM stream differs/missing")
 root=ET.parse(a).getroot()
 st=[x for x in root.iter("stream_info") if x.get("name")=="CLM_USRDAT.UNSET"]
 if len(st)!=1:stop(site+" not exactly one selected 1PT DATM stream")
 start=int(st[0].find("year_first").text)
 end=int(st[0].find("year_last").text)
 nodes=st[0].find("datafiles")
 if nodes is None:stop(site+" no datafiles")
 yearmap={}
 for yr,node in zip(range(start,end+1),list(nodes)):
  p=Path((node.text or "").strip())
  if not p.is_file() or not p.name.startswith(site+"_DATM_") or str(yr) not in p.stem:
   stop(site+" missing/unexpected exact selected year "+str(yr)+": "+str(p))
  yearmap[yr]=p
 if len(yearmap)!=end-start+1 or len(list(nodes))!=len(yearmap):
  stop(site+" full CDEPS annual file list inconsistent")
 return yearmap
def load(p,year):
 with Dataset(p) as ds:
  tv=ds.variables["time"]
  t=np.asarray(tv[:],dtype=float).reshape(-1)
  if len(t)!=17520 or getattr(tv,"calendar",None) not in ("noleap","365_day"):
   stop(str(p)+" invalid NOLEAP 30-minute year")
  dates=num2date(t,getattr(tv,"units"),getattr(tv,"calendar"))
  if dates[0].year!=year or dates[-1].year!=year:stop(str(p)+" wrong source year")
  data={}
  for key in KEYS:
   v=ds.variables[key]
   if "time" not in v.dimensions:stop(key+" missing time axis")
   a=np.ma.asarray(v[:],dtype=float)
   x=np.moveaxis(a,v.dimensions.index("time"),0)
   if x.shape[0]!=17520 or x.size!=17520:stop(key+" not 1PT 17520 records")
   data[key]=np.asarray(np.ma.filled(x.reshape(17520),np.nan))
  return dates,data
def meteorology(d):
 T=d["TBOT"]-273.15; q=d["QBOT"];p=d["PSRF"]
 e=q*p/(.622+.378*q)
 es=611.2*np.exp(np.clip(17.67*T/(T+243.5),-30,30))
 return T,100*e/es,(es-e)/100,d["PRECTmms"]*1800
def episodes(idx):
 if not len(idx):return []
 groups=[]
 start=old=int(idx[0])
 for x in idx[1:]:
  x=int(x)
  if x>old+1:groups.append((start,old));start=x
  old=x
 groups.append((start,old))
 return groups
def show(site,year,dates,d,indices,category,limit=50):
 t,rh,vpd,rain=meteorology(d)
 ids=sorted(set(int(x) for x in indices))
 if not ids:return
 print(f"\nEVENT_GROUP {site} {year} {category} flagged_HH={len(ids)} contiguous_runs={len(episodes(ids))}")
 for first,last in episodes(ids)[:limit]:
  print(f"EVENT {category} {site} {year} first={dates[first]} last={dates[last]} HH={first}:{last} length={last-first+1}")
  # +/- 4 HH, cap very long contiguous episodes at the two edges.
  context=sorted(set(list(range(max(0,first-4),min(len(t),first+5)))+
                     list(range(max(0,last-4),min(len(t),last+5)))))
  for i in context:
   print("  HH",i,"TIME",dates[i],
         "T_C",round(float(t[i]),3),"QBOT",round(float(d["QBOT"][i]),8),
         "RH_pct",round(float(rh[i]),3),"VPD_hPa",round(float(vpd[i]),3),
         "Rain_mm30",round(float(rain[i]),3),
         "FLAG",int(i in ids))
def scan(site,year,p):
 print("\nYEAR_SOURCE",site,year,p,"SHA256",sha(p))
 dates,d=load(p,year)
 t,rh,vpd,rain=meteorology(d)
 if site=="BE-Bra":
  if year in (1996,1999):
   show(site,year,dates,d,np.flatnonzero((rh<5)&np.isfinite(rh)),"LOW_RH_LT5")
  if year in (2005,2021):
   jump=np.flatnonzero(np.abs(np.diff(t))>12)+1
   ids=set(jump.tolist())|set((jump-1).tolist())
   if year==2021:ids|=set(np.flatnonzero(t>45).tolist())
   show(site,year,dates,d,ids,"TEMP_JUMP_GT12_OR_T_GT45")
  if year==2002:
   daily=np.nansum(rain.reshape(365,48),axis=1)
   for day in np.flatnonzero(daily>100):
    i=int(day*48);top=np.argsort(rain[i:i+48])[-6:][::-1]+i
    print("\nRAIN_DAY_GT100",site,year,str(dates[i])[:10],"mm",round(float(daily[day]),3),
          "MAX_6_HH",
          [(str(dates[int(k)]),round(float(rain[k]),3)) for k in top])
    for k in top[:2]:show(site,year,dates,d,[k],"TOP_DAY_RAIN_MM30")
 elif site=="CH-Lae":
  jump=np.flatnonzero(np.abs(np.diff(t))>8)+1
  ids=set(jump.tolist())|set((jump-1).tolist())
  show(site,year,dates,d,ids,"TEMP_JUMP_GT8")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument("--self-test",action="store_true")
 ap.add_argument("--check",action="store_true")
 ap.add_argument("--site",choices=("BE-Bra","CH-Lae","all"),default="all")
 a=ap.parse_args()
 if a.self_test:
  assert episodes([1,2,5,6,9])==[(1,2),(5,6),(9,9)]
  assert len(CASE)==2
  print("STAGE33 SELF-TEST PASS: contiguous event runs, independent source keys; no writes")
  return
 if not a.check:ap.error("Use --check or --self-test")
 for site in CASE:
  if a.site not in ("all",site):continue
  m=paths(site)
  years=[1996,1999,2002,2005,2021] if site=="BE-Bra" else list(range(2004,2025))
  for year in years:
   if year not in m:stop(site+" absent required year "+str(year))
   scan(site,year,m[year])
 print("\nSTAGE33 ALL TARGETED SOURCE CONTEXT READ ONLY: no writes, no model/Slurm changes.")
if __name__=="__main__":main()
