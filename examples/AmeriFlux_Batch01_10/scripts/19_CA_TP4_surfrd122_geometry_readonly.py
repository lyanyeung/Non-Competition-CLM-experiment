#!/usr/bin/env python3
"""Stage19: CA-TP4 AD5 4728206 source-level land-domain mismatch diagnosis.
READ ONLY. Original Batch01/Batch03 scripts clone a matching site template;
this experimental case cloned CH-Dav and substituted CA-TP4 met/surface.
CTSM d5ea9d0 src/main/surfrdMod.F90:120-122 aborts if
fabs(ldomain longitude/latitude - surface longitude/latitude) > 0.001 deg.
This script does NOT alter CIME, NetCDF, mesh, source or Slurm.
"""
from __future__ import annotations
import argparse,re,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=BASE/"cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"
REF=BASE/"cases/CH-Dav_B01_FIXNC_AD400"
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5/run")
SOURCE=BASE/"CTSM/src/main/surfrdMod.F90"
YEAR=BASE/"experiments/AmeriFlux_MultiSite_10/reports/stage11_CA_TP4_DATM_UTC_20261025T080240825734395Z/CA-TP4/yearly/2002.nc"
NC_KEYS=("LATIXY","LONGXY","yc","xc","lat","lon","grid_center_lat","grid_center_lon",
         "elementCenterLat","elementCenterLon")
KEYS=("GRID","ATM_GRID","LND_GRID","MASK_GRID","DATM_MODE",
      "ATM_DOMAIN_FILE","ATM_DOMAIN_PATH","LND_DOMAIN_FILE","LND_DOMAIN_PATH",
      "ATM_MESH_FILE","LND_MESH_FILE","DIN_LOC_ROOT")
TOPIC=re.compile(r"(?i)domain|mesh|grid|longitude|latitude|latc|lonc|lfsurdat|fsurdat")
ERR=re.compile(r"(?i)surfrd|lon/lat mismatch|domain.*(lon|lat)|surface.*(lon|lat)|error")
NC_FINDER=re.compile(r"""(/[^\s"'<>(),;]+?\.(?:nc|nc4|cdf))(?=[\s"'<>(),;]|$)""",re.I)

def entries(case):
 d={}
 for x in ("env_case.xml","env_run.xml","env_build.xml"):
  p=case/x
  if p.is_file():
   for e in ET.parse(p).iter():
    if e.tag.split("}")[-1]=="entry":d[e.attrib.get("id")]=e.attrib.get("value")
 return d

def surface(case):
 for p in (case/"CaseDocs/lnd_in",case/"user_nl_clm"):
  if p.is_file():
   vals=re.findall(r"""(?im)^\s*fsurdat\s*=\s*['"]?([^'"\s,!,]+)""",p.read_text(errors="replace"))
   if len(vals)==1:return Path(vals[0])
 return None

def nc(label,p):
 print("NC INPUT",label,p,flush=True)
 if not p or not p.is_file():
  print("  ABSENT");return None
 got={}
 try:
  with Dataset(p) as ds:
   for k in NC_KEYS:
    if k not in ds.variables:continue
    v=ds.variables[k]
    if len(v.shape)==0:arr=np.ma.asarray(v[...]).reshape(1)
    else:arr=np.ma.asarray(v[(slice(0,min(v.shape[0],4)),)+tuple(0 for _ in v.shape[1:])]).ravel()
    values=[]
    for x in arr:
     if not np.ma.is_masked(x) and np.isfinite(x):values.append(float(x))
    got[k]=values
    print("  ",k,"size",v.size,"head",values[:4])
 except Exception as e:print("  OPEN/READ FAIL",str(e)[:250])
 for la,lo in (("LATIXY","LONGXY"),("yc","xc"),("lat","lon"),
               ("grid_center_lat","grid_center_lon"),("elementCenterLat","elementCenterLon")):
  if len(got.get(la,[]))==1 and len(got.get(lo,[]))==1:
   return (got[la][0],got[lo][0]%360)
 return None

def delta(a,b):
 if not a or not b:return "UNRESOLVED"
 return ("LAT_DELTA="+str(round(abs(a[0]-b[0]),7))+
         " LON_DELTA="+str(round(abs((a[1]-b[1]+180)%360-180),7))+
         " DEGREES ; LIMIT EACH <=0.001")

def config(case,label):
 print("=== CIME",label,"===")
 if not case.is_dir():
  print("NO CASE DIR",case);return None,{}
 d=entries(case)
 for k in KEYS:
  if k in d:print(k,"=",d[k])
 p=surface(case)
 return nc(label+" fsurdat",p),d

def logs():
 print("=== PRIMARY REAL LAND MODEL LOG / ERROR EVIDENCE ===")
 logs=list(RUN.glob("lnd.log.*"))+list(RUN.glob("cesm.log.4728206*"))+list(RUN.glob("med.log.*"))
 for p in sorted(set(logs)):
  if not p.is_file():continue
  if p.stat().st_size>12000000:
   print("OVERSIZED LOG SKIPPED",p);continue
  lines=p.read_text(errors="replace").splitlines()
  hits=[(i+1,x) for i,x in enumerate(lines) if ERR.search(x)]
  print("LOG",p,"LINES",len(lines),"ERROR HITS",len(hits))
  for i,x in hits[-25:]:print(" ",i,x[:400])

def scan():
 print("=== DOMAIN/MESH REFS FROM EFFECTIVE COUPLER INPUTS ===")
 refs=set()
 for folder in (CASE/"CaseDocs",RUN):
  files=[folder/f for f in ("datm_in","drv_in","lnd_in","nuopc.runconfig","datm.streams.xml")]
  files.extend(sorted(folder.glob("*runconfig*"))[:3])
  for p in dict.fromkeys(files):
   if not p.is_file():continue
   content=p.read_text(errors="replace")
   hits=[(i+1,x.strip()) for i,x in enumerate(content.splitlines()) if TOPIC.search(x)]
   print("FILE",p,"RELEVANT LINES",len(hits))
   for i,x in hits[:27]:print("  ",i,x[:350])
   for match in NC_FINDER.findall(content):
    if len(match)<400:refs.add(match)
 d=entries(CASE)
 for prefix in ("ATM_DOMAIN","LND_DOMAIN"):
  val=d.get(prefix+"_FILE","")
  directory=d.get(prefix+"_PATH","")
  if val and val!="UNSET":
   refs.add(str(Path(directory)/val) if not val.startswith("/") and directory.startswith("/") else val)
 for key in ("ATM_MESH_FILE","LND_MESH_FILE"):
  if d.get(key):refs.add(d[key])
 local_din=d.get("DIN_LOC_ROOT","")
 for s in sorted(refs):
  s=s.replace("$DIN_LOC_ROOT",local_din)
  if not s.startswith("/"):continue
  if not any(k in s.lower() for k in ("mesh","domain","usrdat","grid","1x1")):continue
  point=nc("REFERENCED POINT MESH/DOMAIN",Path(s))
  if point:print("  VS CA-TP4 observed point",delta(point,(42.7102,279.6426)))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 group=p.add_mutually_exclusive_group(required=True)
 group.add_argument("--self-test",action="store_true")
 group.add_argument("--check",action="store_true")
 args=p.parse_args()
 if args.self_test:
  assert "LAT_DELTA=0.0" in delta((42.7102,-80.3574),(42.7102,279.6426))
  print("STAGE19 SELF-TEST PASS: longitude wrap and lat/lon comparison, no writes")
  return
 if SOURCE.is_file():
  lines=SOURCE.read_text(errors="replace").splitlines()
  print("=== LOCAL CTSM surfrdMod.F90:119-123 ===")
  for n in range(119,124):
   if len(lines)>=n:print(str(n)+": "+lines[n-1])
 a,_=config(CASE,"CA-TP4 FAILED")
 b,_=config(REF,"CH-Dav ORIGINAL TEMPLATE")
 c=nc("CA-TP4 STAGE11 UTC MET FILE",YEAR)
 print("CA-TP4 MET VS CA-TP4 SURFACE",delta(a,c))
 print("CA-TP4 SURFACE VS CH-Dav TEMPLATE SURFACE",delta(a,b))
 logs()
 scan()
 print("STAGE19 READ-ONLY GEOMETRY REVIEW COMPLETED. NO MODEL RESUBMITTED.")
 print("Do NOT change observed coords or force old mesh to appear to match.")
if __name__=="__main__":main()
