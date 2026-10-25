#!/usr/bin/env python3
"""CA-TP4 Stage10. Strictly READ ONLY: compare 2002/2010/2019 observed
FSDS to astronomical day/night under LST(UTC-5) vs UTC model clock.
Also flag inherited 1997 CO2 in new CA-TP4 AD5 case. No writes/submits.

Positive CDEPS offset shifts the source time forward (seconds). A +18000s
offset is a HYPOTHESIS only if the actual coupler uses UTC time; this
offline sunlight comparison cannot by itself certify model time semantics.
"""
from __future__ import annotations
import argparse,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ROOT=B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
PILOT=B/"experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
CASE=B/"cases/CA-TP4_AMF_FIXNC_AD400_PILOT"
STATE=ROOT/"stage08_CA_TP4_AD5_CASE_PREVIEW_ATTEMPT.json"
LAT,LON,UTC_OFFSET=42.7102,-80.3574,-5.
YEARS={2002,2010,2019}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()

def solar_cosz(days,minutes,tz):
 g=2*np.pi/365*(days-1+(minutes/60-12)/24)
 eq=229.18*(0.000075+0.001868*np.cos(g)-0.032077*np.sin(g)
       -0.014615*np.cos(2*g)-0.040849*np.sin(2*g))
 dec=(0.006918-0.399912*np.cos(g)+0.070257*np.sin(g)
       -0.006758*np.cos(2*g)+0.000907*np.sin(2*g)
       -0.002697*np.cos(3*g)+0.00148*np.sin(3*g))
 hour=np.deg2rad(((minutes+eq+4*LON-60*tz)%1440)/4-180)
 phi=math.radians(LAT)
 return np.sin(phi)*np.sin(dec)+np.cos(phi)*np.cos(dec)*np.cos(hour)

def verify_case():
 s=json.loads(STATE.read_text())
 if s.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or s.get("model_jobs_submitted") is not False:
  raise RuntimeError("Stage08 case not successful/unsent")
 for key,fn in (("CIME_generated_lnd_in_sha256","lnd_in"),
                ("CIME_generated_datm_stream_xml_sha256","datm.streams.xml")):
  if sha(CASE/"CaseDocs"/fn)!=s[key]:
   raise RuntimeError("Generated CaseDocs changed since Stage08")
 if (CASE/"env_case.xml").read_bytes()!=(CASE/"LockedFiles/env_case.xml").read_bytes():
  raise RuntimeError("CIME env_case.xml lock changed")
 vals={}
 for p in ("env_run.xml","env_case.xml","env_build.xml"):
  for e in ET.parse(CASE/p).iter("entry"):
   vals[e.attrib.get("id")]=e.attrib.get("value")
 for k,v in (("CALENDAR","NO_LEAP"),("ATM_NCPL","48"),("STOP_N","5"),
             ("RESUBMIT","0"),("DATM_YR_START","2002"),
             ("DATM_YR_END","2023"),("CLM_ACCELERATED_SPINUP","on")):
  if vals.get(k,"").lower()!=v.lower():
   raise RuntimeError("Changed CIME setup: "+k)
 doc=ET.parse(CASE/"CaseDocs/datm.streams.xml")
 streams=[x for x in doc.iter("stream_info") if x.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(streams)!=1 or streams[0].findtext("offset").strip()!="0":
  raise RuntimeError("Effective CDEPS stream no longer 1PT offset=0")
 print("CIME CASE RECEIPT PASS; 5yr AD5 only, effective CDEPS offset=0")
 print("CIME GRID:",vals.get("GRID"),"LAND DOMAIN:",vals.get("LND_DOMAIN_FILE","UNSET"))
 print("CIME CO2:",vals.get("CLM_CO2_TYPE"),"ppm",vals.get("CCSM_CO2_PPMV"))
 print("CO2 1997 GLOBAL NOAA:",363.04,"ppm; 2002 GLOBAL NOAA:",372.58,"ppm")
 print("CO2 ACTION: 372.58ppm recommended as 2002 technical spinup baseline; NOT CHANGED.")
 return vals

def inspect_shortwave():
 manifest=json.loads((PILOT/"manifest.json").read_text())
 assert manifest["annual_netcdf_files"]==22 and manifest["site"]=="CA-TP4"
 results={}
 for item in manifest["files"]:
  yr=item["year"]
  if yr not in YEARS:continue
  p=Path(item["path"])
  if sha(p)!=item["sha256"]:raise RuntimeError("Source pilot NetCDF SHA changed")
  with Dataset(p) as nc:
   ts=np.asarray(nc.variables["time"][:],dtype=float)
   sw=np.asarray(nc.variables["FSDS"][:,0,0],dtype=float)
   lat=float(np.asarray(nc.variables["LATIXY"][:]).reshape(-1)[0])
   lon=float(np.asarray(nc.variables["LONGXY"][:]).reshape(-1)[0])
   if len(ts)!=17520 or not np.isfinite(sw).all() or np.min(sw)<-1e-5:
    raise RuntimeError("Invalid 30min solar series: "+str(yr))
   if abs(lat-LAT)>1e-4 or abs((lon%360)-(LON%360))>1e-4:
    raise RuntimeError("Pilot geometry does not match CA-TP4")
   if not np.allclose(ts[[0,1,-1]],
          [1/96,1/48+1/96,17519/48+1/96],atol=1e-9,rtol=0):
    raise RuntimeError("Half-hour midpoint not preserved")
   mins=(ts%1)*1440
   doy=np.floor(ts).astype(int)+1
   print("=== SOLAR FSDS SOURCE YEAR",yr,"===")
   vals=[]
   for tag,tz in (("LST_UTC_MINUS5",-5.),("UTC_ZERO",0.)):
    cosz=solar_cosz(doy,mins,tz)
    nighttime=cosz<math.sin(math.radians(-3))
    frac=100*float(np.sum(sw[nighttime])/np.sum(sw))
    vals.append(frac)
    print(tag,"FSDS energy at astronomical night:",round(frac,3),"%")
   results[yr]=vals
 if set(results)!=YEARS:raise RuntimeError("Missing requested three source years")
 lst=np.mean([v[0] for v in results.values()])
 utc=np.mean([v[1] for v in results.values()])
 print("THREE-YEAR MEAN NIGHT-RADIATION LST:",round(lst,3),"% UTC:",round(utc,3),"%")
 if lst<utc/4 and lst<3:
  print("OBSERVED SOLAR PHASE: strongly consistent with FLUXNET LOCAL STANDARD TIME.")
  print("IF CIME MODEL SOLAR CLOCK IS UTC, CDEPS offset +18000 seconds is the hypothesis, NOT APPLIED.")
 else:
  print("OBSERVED SOLAR PHASE: not decisive; inspect source temporal convention.")
 print("STILL UNPROVEN: ACTUAL CIME coupled solar-clock and year-boundary interpolation.")

def main():
 a=argparse.ArgumentParser(description=__doc__)
 g=a.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 z=a.parse_args()
 if z.self_test:
  v=solar_cosz(np.array([172]),np.array([720.]),-5.)[0]
  assert v>0.7 and solar_cosz(np.array([172]),np.array([720.]),0.)[0]<v
  assert YEARS=={2002,2010,2019}
  print("SELF-TEST PASS: CA-TP4 solar geometry LST/UTC diagnostic")
  return
 verify_case()
 inspect_shortwave()
 print("STAGE10 READ-ONLY PASS: no changes, no Slurm; AD5 remains unsubmitted.")

if __name__=="__main__":main()
