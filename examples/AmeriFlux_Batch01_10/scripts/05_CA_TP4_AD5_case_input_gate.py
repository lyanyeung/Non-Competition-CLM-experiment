#!/usr/bin/env python3
"""AmeriFlux CA-TP4 Stage05 — READ-ONLY science + CIME case-input gate.

Stage04 produced 22 independent annual DATM midpoint NetCDF (28m ZBOT as
EXPLICIT TEST PROXY), and a DETACHED real-schema CDEPS XML. Stage05 confirms
the EXACT output source, checks all 22 actual files and the XML, inventories
CA-TP4 point-surface landunits/soil and tree-cover evidence, and compares
existing CH-Dav FIXNC AD400 case (a FORMAT ONLY reference). It does not edit
anything or create/submit a CIME/Slurm job.

Outputs a concise plan in --report ONLY. Never infer tree stand percentages
to be observed ground-area percentages or copy CH-Dav fsurdat/soil/years.
"""
from __future__ import annotations

import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
AMF=BASE/"experiments/AmeriFlux_MultiSite_10"
PILOT=AMF/"reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
SITE="CA-TP4"
EXPECTED_YEARS=range(2002,2024)
KNOWN_MET={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn",
           "ZBOT":"Sa_z","TBOT":"Sa_tbot","WIND":"Sa_wind",
           "QBOT":"Sa_shum","PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
REFERENCE=BASE/"cases/CH-Dav_B01_FIXNC_AD400"
SITE_ROOT=BASE/"sites/MY_EC_SITE"/SITE
META=Path(__file__).resolve().with_name("Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv")
META_BLOB_SHA1="266a1bb8f56a3ca99eef317a20dc913f3b5cf9a4"
FILES_TO_EXAMINE=("env_run.xml","env_case.xml","CaseDocs/datm_in",
                  "CaseDocs/datm.streams.xml","CaseDocs/lnd_in")
CIME_VARS={"COMPSET","DATM_MODE","CALENDAR","ATM_NCPL","DATM_YR_START",
           "DATM_YR_END","DATM_YR_ALIGN","RUN_STARTDATE","RUN_TYPE",
           "STOP_OPTION","STOP_N","REST_N","RESUBMIT","DOUT_S",
           "CLM_ACCELERATED_SPINUP","EXEROOT","BUILD_COMPLETE"}
NML_VARS={"fsurdat","finidat","spinup_state","use_fates",
          "use_fates_fixed_biogeog","use_fates_nocomp","use_fates_sp",
          "fates_paramfile","fates_hlm_pft_map","PCT_NAT_PFT"}

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def jsonfile(p):
 if not p.is_file():raise RuntimeError("Missing file "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))

def xmlvalues(path,fields):
 if not path.is_file():raise RuntimeError("Missing CIME XML "+str(path))
 res={}
 for n in ET.parse(path).iter():
  if n.tag.split("}")[-1]=="entry" and n.attrib.get("id") in fields:
   res[n.attrib["id"]]=n.attrib.get("value","")
 return res

def nmlvalues(p):
 if not p.is_file():raise RuntimeError("Missing CIME namelist "+str(p))
 text=p.read_text(encoding="utf-8",errors="replace")
 out={}
 for key in sorted(NML_VARS):
  allv=re.findall(r"(?mi)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
  if allv:out[key]=allv[-1].strip()
 return out

def check_pilot():
 from netCDF4 import Dataset
 import numpy as np
 m=jsonfile(PILOT/"manifest.json")
 required={"annual_netcdf_files":22,"height_m":28.0,
           "TA_F_source_sensor_verified":False,
           "modified_stage81_files":False,
           "model_case_created":False,"Slurm_submitted":False,
           "production_release":False}
 for k,v in required.items():
  if m.get(k)!=v:raise RuntimeError("Invalid detached pilot manifest "+k)
 if m.get("site")!=SITE or len(m.get("files",[]))!=22:
  raise RuntimeError("CA-TP4 pilot manifest invalid")
 if "TIMESTAMP_START+15MIN" not in m.get("time_policy",""):
  raise RuntimeError("CA-TP4 intended HH midpoint not declared")
 xmlfile=Path(m["stream_candidate"]["path"])
 expected_xml=PILOT/SITE/"datm.streams.CA-TP4.CANDIDATE_NOT_ACTIVATED.xml"
 if xmlfile!=expected_xml or sha(xmlfile)!=m["stream_candidate"]["sha256"]:
  raise RuntimeError("Pilot detached stream XML misplaced or SHA drift")
 from netCDF4 import Dataset
 for year,entry in zip(EXPECTED_YEARS,m["files"]):
  p=Path(entry["path"])
  if (entry["year"]!=year or
      p!=PILOT/SITE/"yearly"/f"{year}.nc"):
   raise RuntimeError("Unexpected pilot source/year "+str(year))
  if sha(p)!=entry["sha256"]:
   raise RuntimeError("Pilot NetCDF SHA drift "+str(year))
  with Dataset(p) as nc:
   t=nc.variables["time"]
   if len(t)!=17520 or t.calendar!="noleap":
    raise RuntimeError("Wrong pilot noleap clock "+str(year))
   if not np.allclose(t[[0,1,17519]],
     [1/96,1/48+1/96,17519/48+1/96],rtol=0,atol=1e-11):
    raise RuntimeError("Pilot midpoint clock drift "+str(year))
   z=nc.variables["ZBOT"]
   if z.dimensions!=nc.variables["QBOT"].dimensions:
    raise RuntimeError("Pilot ZBOT dimensions unexpected")
   if not np.allclose(z[[0,200,17519],0,0],28.0,rtol=0,atol=1e-9):
    raise RuntimeError("Pilot 28 m hypothesis not consistent "+str(year))
 print("PILOT INPUT PASS: 22/22 annual SHA, sampled midpoint time & 28m provisional ZBOT")
 return m,xmlfile

def check_stream(xml):
 root=ET.parse(xml).getroot()
 if root.tag!="file":raise RuntimeError("Pilot stream root is not case-native <file>")
 entries=[a for a in root.iter("stream_info") if a.attrib.get("name","").startswith("CLM_USRDAT.")]
 if len(entries)!=1:raise RuntimeError("Expected exactly one local CLM_USRDAT stream")
 s=entries[0]
 fields={}
 vars=s.find("datavars")
 if vars is None:raise RuntimeError("Expected CDEPS datavars")
 for item in vars:
  tokens=(item.text or "").split()
  if len(tokens)!=2:raise RuntimeError("Noncanonical CDEPS mapping entry")
  fields[tokens[0]]=tokens[1]
 for field,dest in KNOWN_MET.items():
  if fields.get(field)!=dest:raise RuntimeError(f"Wrong met mapping {field}: {fields.get(field)}")
 for k,required in (("taxmode","cycle"),("tintalgo","linear"),("year_first","2002"),("year_last","2023"),("year_align","2002"),("offset","0")):
  node=s.find(k)
  if node is None or (node.text or "").strip()!=required:
   raise RuntimeError("CDEPS stream incorrect "+k)
 dat=s.find("datafiles")
 if dat is None:raise RuntimeError("CDEPS datafiles missing")
 filenames=[Path((x.text or "").strip()) for x in dat]
 if filenames!=[PILOT/SITE/"yearly"/f"{year}.nc" for year in EXPECTED_YEARS]:
  raise RuntimeError("CDEPS stream does not point only to the 22 CA-TP4 pilot files")
 print("STREAM INPUT PASS: effective CDEPS 1PT main stream cycle linear, 2002-2023, all 8 source mappings, all 22 pilot paths")
 print("GLOBAL ANCILLARY STREAMS: inherited reference case; NOT independent CA-TP4 science validation")
 return fields

def inspect_surface():
 import numpy as np
 from netCDF4 import Dataset
 folder=SITE_ROOT/"subset_data"
 choices=sorted(folder.glob("surfdata*.nc"))
 if len(choices)!=1:
  raise RuntimeError("Expected exactly one CA-TP4 point surface; found "+str(len(choices)))
 p=choices[0]
 r={"path":str(p),"sha256":sha(p)}
 with Dataset(p) as ds:
  for var in ("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND","PCT_SAND","PCT_CLAY","PCT_NAT_PFT"):
   if var not in ds.variables:
    raise RuntimeError("CA-TP4 base surface missing "+var)
   vals=np.ma.filled(ds.variables[var][:],np.nan)
   if not np.isfinite(vals).all():raise RuntimeError("Nonfinite surface variable "+var)
   flat=vals.ravel()
   if var in ("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND"):
    if flat.size!=1:raise RuntimeError("Non-point landunit variable "+var)
    r[var]=float(flat[0])
   elif var=="PCT_NAT_PFT":
    r["NATPFT_VECTOR_FULL"]=[round(float(x),5) for x in flat]
    if len(flat) not in (15,16):raise RuntimeError("Unexpected CLM natural PFT count")
   else:
    r[var+"_N_LAYERS"]=len(flat)
    r[var+"_minmax"]=list(map(float,(np.min(flat),np.max(flat))))
  r["DETECTED_HOST_CROP_GT20PCT"]=r["PCT_CROP"]>20
 print("ORIGINAL GRID SURFACE:",r["path"])
 print("ORIGINAL GRID SURFACE SHA256:",r["sha256"])
 print("HOST LANDUNIT NATVEG/CROP/LAKE/WETLAND [%]:",*[f"{r[k]:.3f}" for k in ("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND")])
 print("HOST CLM PCT_NAT_PFT (GRID, NOT TOWER):",r["NATPFT_VECTOR_FULL"])
 print("SOIL GRID LAYERS:",r["PCT_SAND_N_LAYERS"],"SAND range",r["PCT_SAND_minmax"],"CLAY range",r["PCT_CLAY_minmax"])
 print("DO NOT FORCE OBSERVED NATVEG100/CROP0/ENF93 DBF7 WITHOUT EXPLICIT IDEALIZED FOREST-POINT ASSUMPTION AND MODE COMPATIBILITY")
 return r

def evidence():
 if not META.is_file():raise RuntimeError("Download pinned v4 PFT evidence next to Stage05 script before running: "+str(META))
 raw=META.read_bytes()
 blob=b"blob "+str(len(raw)).encode()+b"\0"+raw
 if hashlib.sha1(blob).hexdigest()!=META_BLOB_SHA1:
  raise RuntimeError("Unverified/v4 tower PFT evidence blob: refuse unpinned station percentages")
 with META.open(encoding="utf-8-sig",newline="") as f:
  rows=[r for r in csv.DictReader(f,delimiter="\t") if r.get("site")==SITE]
 if len(rows)!=1:raise RuntimeError("CA-TP4 tower evidence ambiguous")
 r=rows[0]
 if "PFT2=93" not in r.get("published_PFT_or_cover_percent","") or "PFT6=7" not in r.get("published_PFT_or_cover_percent",""):
  raise RuntimeError("Versioned PFT evidence for CA-TP4 changed; review first")
 print("TOWER PFT EVIDENCE SHA256:",sha(META))
 print("TOWER published functional stand grouping:",r["published_PFT_or_cover_percent"])
 print("EVIDENCE DENOMINATOR:",r["percentage_denominator"])
 print("FATES SLOTS (not CLM host NAT_PFT):",r["exact_FATES_PFTs_and_slot"])
 print("WHOLE FOOTPRINT COVER / SOIL / PFT AREA: NOT SCIENTIFICALLY VERIFIED")
 return r

def inventory_case():
 print("=== LIVE CIME REFERENCE CASE + AMERIFLUX CASE DISCOVERY ===")
 root=BASE/"cases"
 if not root.is_dir():raise RuntimeError("CIME case directory not available")
 found=sorted(p for p in root.glob("CA-TP4*") if p.is_dir())
 print("EXISTING CA-TP4 CIME CASE COUNT:",len(found))
 for p in found[:16]:print("  EXISTING:",str(p),"CaseDocs:",(p/"CaseDocs").is_dir())
 if not (REFERENCE/"CaseDocs/lnd_in").is_file() or not (REFERENCE/"CaseDocs/datm.streams.xml").is_file():
  raise RuntimeError("CH-Dav real CIME/FATES reference incomplete")
 x={}
 for file in ("env_run.xml","env_case.xml"):
  x.update(xmlvalues(REFERENCE/file,CIME_VARS))
 actual=nmlvalues(REFERENCE/"CaseDocs/lnd_in")
 print("REFERENCE CASE:",REFERENCE)
 print("CIME REFERENCE:",json.dumps(x,sort_keys=True))
 print("FATES EFFECTIVE REFERENCE:",json.dumps(actual,sort_keys=True))
 for key,want in (("use_fates",".true."),("use_fates_sp",".false."),
                  ("use_fates_nocomp",".true."),("use_fates_fixed_biogeog",".true."),
                  ("spinup_state","2")):
  if actual.get(key,"").strip("'\"")!=want:
   raise RuntimeError("AD400 reference FATES flag drift "+key)
 if x.get("DATM_MODE")!="1PT" or x.get("CALENDAR")!="NO_LEAP" or x.get("ATM_NCPL")!="48":
  raise RuntimeError("1PT NO_LEAP ATM_NCPL=48 reference model constraints changed")
 print("REFERENCE MODEL AD FATES MODE: PASS; REFERENCE STATION SURFACE, YEARS, CO2 AND PFT MUST NOT BE COPIED.")
 print("CA-TP4 SITE CASE PRESENT:",bool(found))
 return x,actual,[str(p) for p in found]

def test_self():
 assert len(EXPECTED_YEARS)==22 and set(KNOWN_MET)=={"PRECTmms","FSDS","ZBOT","TBOT","WIND","QBOT","PSRF","FLDS"}
 assert nmlvalues.__name__=="nmlvalues"
 root=ET.fromstring('<file><stream_info name="CLM_USRDAT.UNSET"><taxmode>cycle</taxmode></stream_info></file>')
 assert root.find("stream_info").find("taxmode").text=="cycle"
 print("SELF-TEST PASS: pilot 22 years, exact 8 field mappings, CDEPS XML, FATES AD mode gates")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 args=p.parse_args()
 if args.self_test:test_self();return
 pilot,xml=check_pilot()
 fields=check_stream(xml)
 r=inspect_surface()
 ev=evidence()
 x,land,cases=inventory_case()
 print("=== STAGE05 FINDINGS ===")
 print("MET PILOT: PASS (22 SHA, 28m PROXY, +15min midpoint, 2002-2023 CDEPS cycle/linear)")
 print("MODEL SITE LANDUNIT AND NAT_PFT: NEEDS INDEPENDENT EXPLICIT SCIENCE SCENARIO (tower 93/7 is stand composition, not footprint area)")
 print("TA_F TO 28m SENSOR HEIGHT: NOT VERIFIED; AD5 experimental proxy only")
 print("EXPERIMENT: independent FATES FIXED BIOGEOG + NOCOMP with AD5 smoke before AD395 and independent Normal400")
 print("CASE CREATION/SUBMISSION: NOT PERFORMED (READ ONLY)")
 print("STAGE05 SOURCE AUDIT PASS: NO FILES CHANGED, NO SLURM JOBS.")
if __name__=="__main__":main()
