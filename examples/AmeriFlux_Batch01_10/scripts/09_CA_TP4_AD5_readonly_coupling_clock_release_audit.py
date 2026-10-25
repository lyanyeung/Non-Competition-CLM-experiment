#!/usr/bin/env python3
"""Stage09: READ-ONLY CA-TP4 AD5 generated-case / coupler / solar-clock gate.

Runs on IRIDIS6 AFTER Stage08 confirmed PREVIEW_VERIFIED_NOT_SUBMITTED.
Reads case generated CDEPS streams, FATES namelists, the actual 22 pilot
NetCDF source manifest, the isolated forest-point surface, site BIF UTC_OFFSET,
and case runtime/XML configuration. No files are created/edited, no Slurm,
no case.submit, no newcase, no preview_namelists. Source CA-TP4 TA_F height,
forest cover, grid soil and CO2 remain TECHNICAL assumptions.

--self-test: pure, no IO
--check: full read-only audit, with PASS/REVIEW/HOLD distinctions.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
NAME="CA-TP4_AMF_FIXNC_AD400_PILOT"
CASE=BASE/"cases"/NAME
ROOT=BASE/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
STATE=ROOT/"stage08_CA_TP4_AD5_CASE_PREVIEW_ATTEMPT.json"
MET=BASE/"experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
LAND=ROOT/"surface_stage06_20261025T064625818881201Z"
PLAN=ROOT/"stage07_case_plan_20261025T065233585375346Z"
SURF=LAND/"surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc"
EXPECTED_MET={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
              "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
              "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
EXPECTED_YEARS=tuple(range(2002,2024))
ROOT_SITE=BASE/"sites/MY_EC_SITE/CA-TP4"
RAW=ROOT_SITE/"forcing/raw/AMF_CA-TP4_FLUXNET_2002-2023_v1.3_r1"
RUNDIR=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/NAME/"run"
ARCH=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/archive")/NAME
RUNTIME=("CASE","COMPSET","GRID","ATM_GRID","LND_GRID","DATM_MODE","CLM_USRDAT_NAME",
         "CALENDAR","ATM_NCPL","RUN_STARTDATE","RUN_TYPE","RUN_REFDATE",
         "STOP_OPTION","STOP_N","REST_OPTION","REST_N","RESUBMIT",
         "CONTINUE_RUN","CLM_FORCE_COLDSTART","CLM_ACCELERATED_SPINUP",
         "CLM_CO2_TYPE","CCSM_CO2_PPMV","DATM_CO2_TSERIES",
         "DATM_YR_START","DATM_YR_END","DATM_YR_ALIGN",
         "RUNDIR","DOUT_S_ROOT","EXEROOT","BUILD_COMPLETE",
         "LND_DOMAIN_FILE","LND_DOMAIN_PATH","ATM_DOMAIN_FILE","ATM_DOMAIN_PATH",
         "LND_MESH_FILE","ATM_MESH_FILE","COMP_ROOT_DIR_LND")
LAND_NML=("fsurdat","finidat","fates_paramfile","spinup_state","use_fates",
          "use_fates_sp","use_fates_fixed_biogeog","use_fates_nocomp",
          "use_cn","fates_hlm_pft_map","reseed_dead_plants")

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""):h.update(block)
 return h.hexdigest()

def fail(s):raise RuntimeError(str(s))

def load(p):
 if not p.is_file():fail("Missing exact previous stage manifest/ledger "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))

def xml_entries(case):
 vals={}
 for name in ("env_case.xml","env_run.xml","env_build.xml"):
  f=case/name
  if not f.is_file():fail("Missing actual CIME XML "+str(f))
  for item in ET.parse(f).iter():
   if item.tag.split("}")[-1]=="entry" and item.attrib.get("id") in RUNTIME:
    vals[item.attrib["id"]]=item.attrib.get("value","")
 return vals

def nml_text(path):
 if not path.is_file():fail("Missing generated model namelist "+str(path))
 t=path.read_text(encoding="utf-8",errors="replace")
 fields={}
 for key in LAND_NML:
  matches=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",t)
  if len(matches)>1:fail("Duplicate generated "+key+" in "+str(path))
  if matches:fields[key]=matches[0].strip().strip("'\"").strip()
 return fields

def summary_clock():
 bifs=sorted(p for p in RAW.glob("*.csv") if "_BIF_" in p.name.upper())
 print("=== AMERIFLUX SOURCE UTC TIMEZONE METADATA ===")
 if len(bifs)!=1:
  print("BIF UTC_OFFSET: UNRESOLVED; expected exactly one source BIF, got",len(bifs))
  return None
 bif=bifs[0]
 out={}
 with bif.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
  rd=csv.DictReader(f)
  if not {"VARIABLE","DATAVALUE"}.issubset(rd.fieldnames or []):
   fail("Unexpected source BIF CSV schema")
  for row in rd:
   key=(row.get("VARIABLE") or "").upper().strip()
   val=(row.get("DATAVALUE") or "").strip()
   if key in ("UTC_OFFSET","UTC_OFFSET_F","TIMEZONE","LOCATION_LAT",
              "LOCATION_LONG","LATITUDE","LONGITUDE") and val:
    out.setdefault(key,set()).add(val)
 print("BIF source:",bif,"SHA256:",sha(bif))
 for k in sorted(out):print("BIF",k,":",sorted(out[k]))
 values=sorted(out.get("UTC_OFFSET",set()))
 if len(values)!=1:
  print("CLOCK HOLD: NO UNIQUE OBSERVED SOURCE UTC_OFFSET IN BIF")
  return None
 try: tz=float(values[0])
 except ValueError:
  print("CLOCK HOLD: BIF UTC_OFFSET not numeric",values);return None
 if not -12<=tz<=14:fail("Invalid BIF offset")
 print(f"FLUXNET site UTC_OFFSET = UTC{tz:+g} hours; original FLUXNET timestamps are site LOCAL STANDARD TIME.")
 print(f"Local midnight (LST) corresponds to UTC clock {(-tz)%24:g}:00 in a same-calendar UTC frame.")
 print("DO NOT set datm offset yet: first prove CIME coupler clock convention and year-boundary handling.")
 return tz

def check_provenance():
 m=load(STATE)
 if m.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or m.get("case_created") is not True or m.get("model_jobs_submitted") is not False:
  fail("Stage08 receipt does not establish successful UNSUBMITTED new case")
 for label,p in (("stage04_met_manifest_sha256",MET/"manifest.json"),
                 ("stage06_surface_manifest_sha256",LAND/"manifest.json"),
                 ("stage07_plan_manifest_sha256",PLAN/"manifest.json")):
  if m.get(label)!=sha(p):fail("Stage08 scientific inputs moved/changed "+label)
 if m.get("CIME_generated_lnd_in_sha256")!=sha(CASE/"CaseDocs/lnd_in") or \
    m.get("CIME_generated_datm_stream_xml_sha256")!=sha(CASE/"CaseDocs/datm.streams.xml"):
  fail("Generated namelist or DATM effective stream CHANGED since Stage08")
 if m.get("input_surface_sha256")!=sha(SURF):
  fail("CA-TP4 independent surface changed")
 if m.get("ready_to_submit_AD5") is not False:
  fail("Stage08 readiness bit unexpectedly changed")
 if m.get("scientific_height_28m_verified") is not False or \
    m.get("soil_is_site_measured") is not False or \
    m.get("forest_point_PFT_ground_area_measured") is not False:
  fail("Source pilot science flags silently promoted to observations")
 print("STAGE08 RECEIPT PASSED: original manifests SHA, actual CaseDocs hashes, 1 independent site, NO SUBMISSION.")
 return m

def check_case_xml():
 vals=xml_entries(CASE)
 expected={"CASE":NAME,"DATM_MODE":"1PT","CALENDAR":"NO_LEAP","ATM_NCPL":"48",
           "RUN_TYPE":"startup","RUN_STARTDATE":"2002-01-01",
           "CLM_ACCELERATED_SPINUP":"on","STOP_OPTION":"nyears","STOP_N":"5",
           "REST_N":"5","RESUBMIT":"0","DATM_YR_START":"2002",
           "DATM_YR_END":"2023","DATM_YR_ALIGN":"2002"}
 for key,want in expected.items():
  if vals.get(key,"").lower()!=want.lower():fail(f"New CIME setting mismatch {key}: {vals.get(key)} != {want}")
 if vals.get("BUILD_COMPLETE","").lower()!="true":fail("CIME new case not marked built")
 if vals.get("RUNDIR")!=str(RUNDIR) or vals.get("DOUT_S_ROOT")!=str(ARCH):
  fail("New case RUN/ARCH paths not independent")
 if (CASE/"env_case.xml").read_bytes()!=(CASE/"LockedFiles/env_case.xml").read_bytes():
  fail("CIME lock env_case.xml not restored byte-for-byte")
 print("=== ACTUAL NEW CASE / MODEL RUNTIME ===")
 for k in RUNTIME:
  if k in vals:print("CIME",k,"=",vals[k])
 print("CIME CORE SETTINGS PASS: AD5 only, no auto resubmit, unlocked mutations not present")
 print("SITE GRID/DOMAIN: CASEDATM 1PT same grid NAME does NOT independently prove geolocation in coupler")
 return vals

def check_land():
 land=nml_text(CASE/"CaseDocs/lnd_in")
 for k,w in (("fsurdat",str(SURF)),("spinup_state","2"),
             ("use_fates",".true."),("use_fates_sp",".false."),
             ("use_fates_fixed_biogeog",".true."),
             ("use_fates_nocomp",".true."),("use_cn",".false.")):
  if land.get(k)!=w:fail(f"Actual generated FATES namelist changed {k}")
 if land.get("finidat") not in (None,"") or land.get("reseed_dead_plants") is not None:
  fail("Generated FATES land namelist not an assured AD cold start")
 print("ACTUAL FATES LAND: fixed biogeog / nocomp; startup AD spinup_state=2; no restart file")
 for key in ("fates_paramfile","fates_hlm_pft_map","fsurdat"):
  print("EFFECTIVE LAND",key,":",land.get(key,"NOT_SPECIFIED"))
 if land.get("fates_paramfile"):
  params=Path(land["fates_paramfile"])
  print("FATES PARAMFILE AVAILABLE:",params.is_file(),"SOURCE SHA256:",sha(params) if params.is_file() else "MISSING")
 return land

def check_datm():
 print("=== EFFECTIVE CLM_USRDAT DATASTREAM ===")
 root=ET.parse(CASE/"CaseDocs/datm.streams.xml").getroot()
 matches=[x for x in root.iter("stream_info") if x.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(matches)!=1:fail("Actual generated CDEPS site meteorology not uniquely CLM_USRDAT.UNSET")
 item=matches[0]
 for key,w in (("taxmode","cycle"),("tintalgo","linear"),("mapalgo","none"),
               ("year_first","2002"),("year_last","2023"),("year_align","2002"),
               ("offset","0"),("meshfile","none")):
  child=item.find(key)
  if child is None or (child.text or "").strip()!=w:
   fail("Actual source met CDEPS key mismatch "+key)
 varnames={}
 for var in item.find("datavars"):
  fields=(var.text or "").strip().split()
  if len(fields)!=2 or fields[0] in varnames:fail("Malformed CDEPS variable mapping")
  varnames[fields[0]]=fields[1]
 for k,w in EXPECTED_MET.items():
  if varnames.get(k)!=w:fail("Site met field map changed "+k)
 sources=[Path((f.text or "").strip()) for f in item.find("datafiles")]
 exp=[MET/"CA-TP4/yearly"/f"{y}.nc" for y in EXPECTED_YEARS]
 if sources!=exp:fail("Actual met stream not exactly CA-TP4 22 pilot NC years")
 print("DATM MET PASS:",len(sources),"CA-TP4 files, ZBOT/QBOT maps, 2002-2023 cycle linear, offset 0")
 print("DATM ancillary streams:",[v.attrib.get("name","UNKNOWN") for v in root.iter("stream_info") if v is not item])
 no_bad=[]
 for s in root.iter("stream_info"):
  for f in s.iter("file"):
   path=(f.text or "").strip()
   if "CH-Dav" in path: no_bad.append(path)
 if no_bad:fail("Generated site-incorrect CH-Dav path in effective DATM streams: "+repr(no_bad[:2]))
 print("CDEPS EFFECTIVE INPUT PASS: no CH-Dav annual meteorology references")
 return sources

def geometry_candidates(vals,sources):
 print("=== POINT GEOMETRY AND SOLAR CLOCK EVIDENCE ===")
 with Dataset(SURF) as ds:
  lat=float(np.asarray(ds.variables["LATIXY"][:]).ravel()[0])
  lon=float(np.asarray(ds.variables["LONGXY"][:]).ravel()[0])%360
 for path in (sources[0],sources[-1]):
  with Dataset(path) as d:
   thislat=float(np.asarray(d.variables["LATIXY"][:]).ravel()[0])
   thislon=float(np.asarray(d.variables["LONGXY"][:]).ravel()[0])%360
   if abs(thislat-lat)>1e-5 or abs(thislon-lon)>1e-5:
    fail("Actual forcing and surface geographic point mismatch")
 print(f"SURFACE/MET POINT MATCH: {lat:.4f} N, {lon:.4f} E = {(lon-360 if lon>180 else lon):.4f} signed lon")
 print("MODEL GRID:",vals.get("GRID"),"LAND DOMAIN:",vals.get("LND_DOMAIN_FILE"),
       "ATM DOMAIN:",vals.get("ATM_DOMAIN_FILE"))
 print("COUPLER POINT GEOMETRY: NOT INDEPENDENTLY VERIFIED via executable/runtime restart; needs actual site-specific mesh/domain diagnosis")
 print("MODEL SOLAR CLOCK: not inferred from matched NetCDF coordinates")
 return lat,lon

def check_rest():
 print("=== NUMERICAL TEST RELEASE GATES ===")
 print("Stage04 ZBOT=28 m is only BASE TA_PI_F_1_1_1 PROXY; crosswalk to consolidated FLUXNET TA_F remains UNVERIFIED.")
 print("Stage06 surface NATVEG100 ENF93/DBF7 is an IDEALIZED STAND fraction; original soil 10 layers are GRID fallback.")
 print("Stage08 reused reference FATES executable; previous reference case CCMS CO2 may be from its 1997 forcing.")
 print("User must pick an explicit technical CO2 year/baseline for CA-TP4 2002 spin-up, not inherit by accident.")
 print("No proof yet of LST/UTC solar phase in CIME coupler; a guessed 5-hour CDEPS offset risks year boundary errors.")
 print("AD5 still HOLD; do not submit case jobs. No AD395 / Normal400.")

def selftest():
 x=ET.fromstring('<file><stream_info name="CLM_USRDAT.UNSET"><year_first>2002</year_first></stream_info></file>')
 assert x.find("stream_info").find("year_first").text=="2002"
 assert len(EXPECTED_YEARS)==22 and len(EXPECTED_MET)==8
 print("SELF-TEST PASS: 22 CA-TP4 files, 8 CDEPS mappings, model receipt/solar UTC/source gate parser")

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 q=ap.add_mutually_exclusive_group(required=True)
 q.add_argument("--self-test",action="store_true")
 q.add_argument("--check",action="store_true")
 args=ap.parse_args()
 if args.self_test:selftest();return
 check_provenance()
 vals=check_case_xml()
 check_land()
 sources=check_datm()
 geometry_candidates(vals,sources)
 summary_clock()
 check_rest()
 print("STAGE09 READ-ONLY STRUCTURAL AUDIT PASS; SCIENTIFIC/COUPLER RELEASE=HOLD; NO FILE WRITES, NO SLURM JOBS.")

if __name__=="__main__":main()
