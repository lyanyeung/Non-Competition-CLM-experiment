#!/usr/bin/env python3
"""Batch02 Stage11: six still-unbuilt ICOS FIXNC sites, READ ONLY.

These six are DK-Sor, FR-FBn, BE-Bra, IT-Noe, CH-Lae and ES-LJu.
NOT the unrelated six unassigned stand-alone ICOS stations. The 4 active
Batch02 AD395 jobs are intentionally NEVER inspected/mutated/submitted.

Use the definitive 38-site PFT register, immutable Git blob. Print strict
observational known/unresolved PFT values, original existing source CIME
cases, surface lon/lat and background landunits, PTS values, source date
and CO2, FATES namelists, original forcing stream provenance and the
original compiled exe. Only inspect small NetCDF variables; no changes.
--self-test: no HPC filesystem required.
--audit --pft-csv ...: pure read-only, reports 6/6, potential scientific
HOLD statuses; never declares all six approved for model submission.
"""
from __future__ import annotations
import argparse,csv,hashlib,re,xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SOURCE_BLOB="63739e00408443bcbb4b286bb3324c76e9fd9100"
PARAM_SHA="0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
PARAM=BASE/"CTSM/src/fates/parameter_files/fates_params_default.json"
SITES={
"DK-Sor":{"case":"DK-Sor_FATES_SPINUP500",
          "source_pft":"DBF 80 / ENF+DNF 20 (split open)","gate":"OPEN_PICEA_ENF_LARIX_DNF_20_PERCENT"},
"FR-FBn":{"case":"FR-FBn_FATES_SPINUP500",
          "source_pft":"ENF 75 / EBF ≤25 (open)","gate":"OPEN_NONPINE_25_NOT_ALL_OAK"},
"BE-Bra":{"case":"BE-Bra_FATES_SPINUP500_11P",
          "source_pft":"ENF 55 / DBF 23 / unresolved 22","gate":"OPEN_FOREST_UNKNOWN_22_NO_GRASS_FILL"},
"IT-Noe":{"case":"IT-Noe_ERA5_ABW_BRANCH2009",
          "source_pft":"bare 34 / evergreen shrub 66",
          "gate":"PROPOSED_ONLY_BARE_MIDPOINT_42_TO_91_COVER",
          "host":{0:34,9:66}},
"CH-Lae":{"case":"CH-Lae_FATES_SPINUP500_11P",
          "source_pft":"DBF 80 / ENF 12 / unresolved 8","gate":"OPEN_FOREST_UNKNOWN_8_NO_GRASS_FILL"},
"ES-LJu":{"case":"ES-LJu_FATES_SPINUP1000_S30SHARED",
          "source_pft":"bare 49 / C3 grass 31 / evergreen shrub 20",
          "gate":"PROPOSED_ONLY_UNNAMED_VEG_19_8_ALLOCATED_PROXY",
          "host":{0:49,13:31,9:20}}}
ACTIVE={"FI-Hyy","FR-Hes","CH-Fru","IT-MBo"}
HEADINGS=("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND","PCT_GLACIER")
CONFIG_KEYS=("PTS_LAT","PTS_LON","PTS_DOMAINFILE","RUN_STARTDATE",
             "DATM_MODE","CLM_CO2_TYPE","CCSM_CO2_PPMV",
             "RUN_TYPE","CONTINUE_RUN","BUILD_COMPLETE",
             "CLM_ACCELERATED_SPINUP","EXEROOT","RUNDIR")
LAND_KEYS=("fsurdat","fates_paramfile","finidat","use_fates",
           "use_fates_sp","use_fates_nocomp",
           "use_fates_fixed_biogeog","spinup_state")
def stop(s):raise RuntimeError(str(s))
def blob(data):return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def official(path):
 if not path.is_file():stop("Official PFT CSV missing: "+str(path))
 if blob(path.read_bytes())!=SOURCE_BLOB:
  stop("STOP: authoritative 38-site PFT CSV SHA changed")
 with path.open(encoding="utf-8-sig",newline="") as f:
  rows=list(csv.DictReader(f))
 if len(rows)!=38 or len({r["site"] for r in rows})!=38:
  stop("Expected exact 38-site PFT registry")
 out={r["site"]:r for r in rows}
 for s,d in SITES.items():
  row=out.get(s)
  if not row or row["fixnc_cohort"]!="Batch02":
   stop("Wrong cohort for "+s)
  if row["final_PCT_NAT_PFT"]!=d["source_pft"]:
   stop("Authority changed exact PFT numbers for "+s+": "+str(row.get("final_PCT_NAT_PFT")))
  expected="PROPOSED" if "host" in d else "OPEN"
  if not row["status"].startswith(expected):
   stop("Authority changed PFT evidence status for "+s+": "+row["status"])
 return out
def xml(case):
 out={}
 for name in ("env_case.xml","env_run.xml","env_build.xml"):
  p=case/name
  if not p.is_file():continue
  for element in ET.parse(p).iter():
   if element.tag.split("}")[-1]=="entry":
    out[element.attrib.get("id","")]=element.attrib.get("value","")
 return out
def land(case):
 p=case/"CaseDocs/lnd_in"
 if not p.is_file():
  return {"_status":"MISSING_CaseDocs_lnd_in"}
 text=p.read_text(encoding="utf8",errors="replace")
 out={}
 for key in LAND_KEYS:
  found=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
  if len(found)>1:out[key]="DUPLICATE_KEY"
  elif found:out[key]=found[0].strip().rstrip(",").strip("'\"")
 return out
def surface(file):
 from netCDF4 import Dataset
 import numpy as np
 ans={}
 with Dataset(file) as ds:
  for key in ("LATIXY","LONGXY",*HEADINGS,"PCT_NAT_PFT"):
   if key not in ds.variables:
    ans[key]="MISSING"
    continue
   v=ds.variables[key]
   if v.size>1000:
    ans[key]={"shape":list(v.shape),"read":"SKIPPED_GT_1000_VALUES"}
    continue
   flat=np.ma.asarray(v[:],dtype=float).ravel()
   if np.ma.getmaskarray(flat).any():
    ans[key]="HAS_MASKED_VALUES"
   else:
    ans[key]=[round(float(x),8) for x in flat]
  if "LATIXY" in ds.variables and "LONGXY" in ds.variables:
   lat=ds.variables["LATIXY"];lon=ds.variables["LONGXY"]
   if lat.size==lon.size==1:
    a=float(np.ma.asarray(lat[:]).ravel()[0])
    b=float(np.ma.asarray(lon[:]).ravel()[0])%360
    ans["POINT_LAT_LON"]=[a,b]
 return ans
def dpoint(p,q):
 if not p or not q:return None
 return [round(abs(float(p[0])-float(q[0])),6),
         round(abs((float(p[1])-float(q[1])+180)%360-180),6)]
def streams(case):
 p=case/"CaseDocs/datm.streams.xml"
 if not p.is_file():return ["MISSING_DATM_STREAMS_XML"]
 res=[]
 try:
  root=ET.parse(p).getroot()
  for elm in root.iter("stream_info"):
   files=[]
   x=elm.find("datafiles")
   if x is not None:
    files=[(node.text or "").strip() for node in x if (node.text or "").strip()]
   vals={}
   for key in ("taxmode","year_first","year_last","year_align","offset"):
    v=elm.find(key)
    if v is not None:vals[key]=(v.text or "").strip()
   res.append({"name":elm.get("name"),"fields":vals,
               "count":len(files),"first":files[:2],"last":files[-1:]})
 except Exception as e:res.append({"parse_error":str(e)[:300]})
 return res
def scan_one(site,spec,official_row):
 case=BASE/"cases"/spec["case"]
 print("\n"+"="*68)
 print("SITE",site,"MODEL PFT",spec["source_pft"],"SCIENTIFIC STATUS",official_row["status"])
 print("GATE",spec["gate"])
 print("SOURCE",official_row["sources"][:600])
 if "host" in spec:
  v=[0.]*15
  for index,pct in spec["host"].items():v[index]=float(pct)
  assert sum(v)==100
  print("CANDIDATE HOST NATPFT 0-14",v)
  print("CAUTION: MODEL PROXY ONLY - NOT OBSERVED FOOTPRINT FRACTION")
 else:
  print("NO CLOSED 15-ELEMENT PFT VECTOR; HOLD SOURCE RESIDUAL, DO NOT ASSIGN GRASS OR BARE")
 print("SOURCE CIME CASE",case)
 if not case.is_dir():
  print("TECHNICAL HOLD: EXACT ORIGINAL CASE DIRECTORY IS MISSING")
  return
 x=xml(case)
 for k in CONFIG_KEYS:
  if k in x:print("CIME",k,x[k])
 l=land(case)
 for k in LAND_KEYS:
  if k in l:print("ORIGINAL LAND",k,l[k])
 surf=Path(l["fsurdat"]) if l.get("fsurdat","").startswith("/") else None
 print("SOURCE fsurdat",surf or "UNRESOLVED")
 if surf and surf.is_file():
  print("SOURCE SURFACE SHA256",file_sha(surf))
  try:
   d=surface(surf)
   for key in ("POINT_LAT_LON",*HEADINGS,"PCT_NAT_PFT"):
    if key in d:print("SOURCE SURFACE",key,d[key])
   if d.get("POINT_LAT_LON"):
    try:
     pts=(float(x["PTS_LAT"]),float(x["PTS_LON"]))
     gap=dpoint(pts,d["POINT_LAT_LON"])
     print("SOURCE PTS-vs-SURFACE ERROR degrees [lat,lon]",gap)
     if max(gap)>0.001:
      print("WARNING: inherited CIME PTS_LON/LAT != original surface; new case MUST set site PTS from new surface")
    except (KeyError,ValueError,TypeError):
     print("SOURCE PTS ERROR: PTS_LAT/LON unknown")
  except Exception as e:print("TECHNICAL HOLD SURFACE READ",type(e).__name__,str(e)[:300])
 else:print("TECHNICAL HOLD: original surface unresolved/missing")
 print("EXISTING MET STREAM SUMMARY",streams(case))
 exe=Path(x.get("EXEROOT",""))/"cesm.exe" if x.get("EXEROOT","").startswith("/") else None
 print("EXISTING EXE",str(exe or "UNRESOLVED"),"EXISTS",bool(exe and exe.is_file()))
 # Note: source branch IT-Noe ERA5 repaired after failed original met; do not
 # assume source time series is valid solely because CaseDocs files exist.
 if site=="IT-Noe":
  print("IT-Noe ABW-ERA5 source branch REQUIRES forcing source provenance; no silent original forcing reuse")
 print("NO SOURCE/CIME/NETCDF/SLURM MODIFICATIONS")
def run(file):
 rows=official(file)
 if not PARAM.is_file() or file_sha(PARAM)!=PARAM_SHA:
  stop("Shared FATES parameter SHA mismatch or file missing")
 print("BATCH02 STAGE11 SIX SOURCE INVENTORY | READ ONLY")
 print("AUTHORITY CSV SOURCE GIT BLOB",SOURCE_BLOB)
 print("ACTIVE FATES PARAM SHA256",PARAM_SHA)
 print("SIX",",".join(SITES))
 print("EXCLUDES ACTIVE AD395",",".join(sorted(ACTIVE)))
 for site,spec in SITES.items():scan_one(site,spec,rows[site])
 print("\nSTAGE11 AUDIT COMPLETE 6/6; NO FILE WRITES OR SLURM")
 print("PROPOSED MODEL PFT CANDIDATES 2/6 IT-Noe ES-LJu")
 print("FOREST PFT SCIENCE HOLDS 4/6 DK-Sor FR-FBn BE-Bra CH-Lae")
 print("NEXT: approve explicit residual scenarios before writing the other 4 forest surfaces")
def selftest():
 assert set(SITES).isdisjoint(ACTIVE) and len(SITES)==6
 assert set(s for s,d in SITES.items() if "host" in d)=={"IT-Noe","ES-LJu"}
 assert dpoint([42.7102,-80.3574],[42.7102,279.6426])==[0.,0.]
 for d in SITES.values():
  if "host" in d:assert sum(d["host"].values())==100
 print("SELF-TEST PASS six exact remaining Batch02 sites; 2 explicit proxies + 4 science HOLDS; no writes")
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 modes=parser.add_mutually_exclusive_group(required=True)
 modes.add_argument("--self-test",action="store_true")
 modes.add_argument("--audit",action="store_true")
 parser.add_argument("--pft-csv",type=Path)
 opt=parser.parse_args()
 if opt.self_test:selftest()
 else:
  if opt.pft_csv is None:parser.error("--pft-csv is required for --audit")
  run(opt.pft_csv)
if __name__=="__main__":main()
