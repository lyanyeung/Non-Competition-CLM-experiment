#!/usr/bin/env python3
"""CA-TP4 Stage07: read-only real CIME/DATM/FATES *compatibility gate* and
an isolated candidate configuration plan for one five-year AD smoke.

Stage04: detached 22-yr CA-TP4 candidate CDEPS DATM (midpoint +15 min;
         experimental ZBOT 28 m, TA_F sensor crosswalk UNVERIFIED).
Stage06: independent fixed-biogeography forest-point surface, ENF93 DBF7,
         NATVEG100 CROP0, original gridded soil texture fallback.

--self-test: pure Python tests
--check: read original CIME case, candidate files and maps; NO WRITES
--plan --outdir NONEXISTENT: same validation, write a NEW detached
         user_nl_datm_streams candidate, JSON report and user_nl_clm
         EXAMPLE only. NO actual case, Slurm, CIME, NetCDF or surface edit.

NEVER run Stage07 plan's files as a site case without final mesh/domain,
CIME clocks and an isolated preview_namelists validation. Do not copy
CH-Dav surface/forcing/time metadata, patch CaseDocs XML, or patch shared CTSM.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
PILOT=BASE/"experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
SURFACE_DIR=BASE/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4/surface_stage06_20261025T064625818881201Z"
REFERENCE=BASE/"cases/CH-Dav_B01_FIXNC_AD400"
SITE="CA-TP4"
CASE_NAME="CA-TP4_AMF_FIXNC_AD400_PILOT"
CASE=BASE/"cases"/CASE_NAME
OUTPUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUN=OUTPUT/CASE_NAME/"run"
ARCH=OUTPUT/"archive"/CASE_NAME
SURF=SURFACE_DIR/"surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc"
STREAM=PILOT/SITE/"datm.streams.CA-TP4.CANDIDATE_NOT_ACTIVATED.xml"
CIME_SETTINGS=("COMPSET","GRID","ATM_GRID","LND_GRID","OCN_GRID",
               "MASK_GRID","CLM_USRDAT_NAME","DATM_MODE","DATM_YR_START",
               "DATM_YR_END","DATM_YR_ALIGN","CALENDAR","ATM_NCPL",
               "RUN_TYPE","RUN_STARTDATE","RUN_REFDATE","STOP_OPTION",
               "STOP_N","REST_N","REST_OPTION","RESUBMIT",
               "BUILD_COMPLETE","EXEROOT","COMP_ROOT_DIR_LND",
               "RUNDIR","DOUT_S_ROOT","LND_DOMAIN_FILE","LND_DOMAIN_PATH",
               "ATM_DOMAIN_FILE","ATM_DOMAIN_PATH","LND_MESH_FILE",
               "ATM_MESH_FILE","CLM_ACCELERATED_SPINUP","CLM_BLDNML_OPTS",
               "CLM_CO2_TYPE","CCSM_CO2_PPMV","DATM_CO2_TSERIES")
LND_FIELDS=("fsurdat","finidat","spinup_state","use_fates","use_fates_sp",
            "use_fates_nocomp","use_fates_fixed_biogeog","use_cn",
            "fates_paramfile","fates_hlm_pft_map")
MET_MAP={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
         "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
         "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
N=17520
YEARS=tuple(range(2002,2024))
HISTORY=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")
BGC="--bgc fates --no-megan --no-drydep --no-fire_emis"

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for part in iter(lambda:f.read(1024*1024),b""):h.update(part)
 return h.hexdigest()

def fail(msg):raise RuntimeError(str(msg))

def json_load(path):
 if not path.is_file():fail("Missing required previous output "+str(path))
 return json.loads(path.read_text(encoding="utf-8"))

def text_safe(path):
 if not path.is_file():return "ABSENT"
 if path.stat().st_size>1000000:return "TOO_LARGE"
 if path.is_symlink():return "SYMLINK_NOT_FOLLOWED"
 return path.read_text(encoding="utf-8",errors="replace")

def values_from_xml(case):
 values={}
 for name in ("env_run.xml","env_case.xml","env_build.xml","env_mach_pes.xml"):
  p=case/name
  if not p.is_file():continue
  try:root=ET.parse(p).getroot()
  except ET.ParseError:fail("Bad reference case XML "+str(p))
  for e in root.iter():
   if e.tag.split("}")[-1]=="entry" and e.attrib.get("id") in CIME_SETTINGS:
    values[e.attrib["id"]]=e.attrib.get("value","")
 return values

def nml(text):
 ans={}
 if text in ("ABSENT","TOO_LARGE","SYMLINK_NOT_FOLLOWED"):return ans
 for key in LND_FIELDS:
  vals=re.findall(r"(?m)^\s*"+re.escape(key)+r"\s*=\s*([^\n!]*)",text)
  if vals:ans[key]=vals[-1].strip()
 return ans

def pft_coord(ds):
 for lon,lat in (("LONGXY","LATIXY"),("lon","lat")):
  if lon in ds.variables and lat in ds.variables:
   a=np.asarray(ds.variables[lon][:]).ravel()
   b=np.asarray(ds.variables[lat][:]).ravel()
   if len(a)==1 and len(b)==1:return float(b[0]),float(a[0])%360
 fail("No single-point LONGXY/LATIXY or lon/lat metadata")

def validate_met():
 m=json_load(PILOT/"manifest.json")
 if (m.get("site")!=SITE or m.get("annual_netcdf_files")!=22 or
     m.get("height_m")!=28. or m.get("production_release") is not False or
     m.get("TA_F_source_sensor_verified") is not False or
     m.get("Slurm_submitted") is not False):
  fail("Invalid scientific-scope Stage04 manifest")
 if m.get("stream_candidate",{}).get("path")!=str(STREAM) or sha(STREAM)!=m["stream_candidate"]["sha256"]:
  fail("Candidate detached DATM stream integrity mismatch")
 if len(m.get("files",[]))!=len(YEARS):fail("Invalid annual met census")
 infos=[]
 for yr,item in zip(YEARS,m["files"]):
  p=Path(item["path"])
  if p!=PILOT/SITE/"yearly"/f"{yr}.nc" or item["year"]!=yr or sha(p)!=item["sha256"]:
   fail("Stage04 yearly NetCDF path/year/hash mismatch "+str(yr))
  infos.append((yr,p))
 # First and last NC sample: Stage04 already verified all 22 by SHA.
 met_xy=None
 for yr,p in (infos[0],infos[-1]):
  with Dataset(p) as ds:
   var=ds.variables["time"]
   if getattr(var,"calendar",None)!="noleap" or len(var)!=N:
    fail("Stage04 calendar mismatch "+str(p))
   if not np.allclose(var[[0,1,17519]],
           [1/96,1/48+1/96,17519/48+1/96],rtol=0,atol=1e-11):
    fail("Stage04 midpoint mismatch "+str(p))
   for key in MET_MAP:
    if key not in ds.variables:fail("Stage04 lacks DATM mapped input "+key)
   if ds.variables["ZBOT"].dimensions!=ds.variables["QBOT"].dimensions:
    fail("Incompatible ZBOT/QBOT dimensions")
   val=pft_coord(ds)
   if met_xy is not None and not np.allclose(val,met_xy,rtol=0,atol=1e-5):
    fail("Met grid different between first/last years")
   met_xy=val
 return m,infos,met_xy

def validate_surface():
 m=json_load(SURFACE_DIR/"manifest.json")
 if (m.get("site")!=SITE or m.get("surface")!=str(SURF) or
     m.get("Slurm_submitted") is not False or
     m.get("model_release") is not False or
     m.get("site_specific_soil_observation_used") is not False or
     m.get("soil_policy")!="GRID_SOIL_TEXTURE_FALLBACK_ONLY_NOT_OBSERVED"):
  fail("Unexpected Stage06 manifest/science policy")
 if sha(SURF)!=m["surface_sha256"]:
  fail("Stage06 surface SHA256 mismatch")
 with Dataset(SURF) as ds:
  coord=pft_coord(ds)
  for field,target in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
   val=float(np.ma.filled(ds.variables[field][:],np.nan).ravel()[0])
   if not np.isclose(val,target,atol=1e-4):fail("Surface landunit drift "+field)
  vals=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
  expect=np.zeros(15);expect[[1,7]]=[93,7]
  if len(vals)!=15 or not np.allclose(vals,expect,rtol=0,atol=1e-4):
   fail("Surface idealized ENF93 DBF7 changed")
 return m,coord

def validate_stream(files):
 tree=ET.parse(STREAM)
 root=tree.getroot()
 if root.tag!="file":fail("CDEPS stream candidate root changed")
 streams=[a for a in root.iter("stream_info") if a.attrib.get("name","").startswith("CLM_USRDAT.")]
 if len(streams)!=1:fail("Cannot uniquely select point met stream")
 met=streams[0]
 streamname=met.attrib["name"]
 if streamname!="CLM_USRDAT.UNSET":fail("Unknown pinned 1PT stream name "+streamname)
 fields={}
 for v in met.find("datavars"):
  raw=(v.text or "").split()
  if len(raw)!=2 or raw[0] in fields:fail("Malformed/duplicate met stream datavars")
  fields[raw[0]]=raw[1]
 for key,val in MET_MAP.items():
  if fields.get(key)!=val:fail("Wrong CDEPS met mapping "+key)
 for field,value in (("taxmode","cycle"),("tintalgo","linear"),("mapalgo","none"),
                     ("year_first","2002"),("year_last","2023"),("year_align","2002"),
                     ("offset","0")):
  node=met.find(field)
  if node is None or node.text.strip()!=value:fail("CDEPS met stream drift "+field)
 expected=[str(p) for _,p in files]
 found=[(v.text or "").strip() for v in met.find("datafiles")]
 if found!=expected:fail("Datafiles are not exact CA-TP4 22 year pilot")
 print("STREAM PASS:",streamname,"mapped",len(MET_MAP),"variables, 2002-2023 cycle linear, files",len(found))
 return streamname

def check_template():
 if not REFERENCE.is_dir():fail("No known CH-Dav FATES AD reference case")
 x=values_from_xml(REFERENCE)
 text=text_safe(REFERENCE/"CaseDocs/lnd_in")
 if text in ("ABSENT","TOO_LARGE","SYMLINK_NOT_FOLLOWED"):
  fail("No readable generated reference FATES namelist")
 nl=nml(text)
 for k,v in (("use_fates",".true."),("use_fates_sp",".false."),
             ("use_fates_fixed_biogeog",".true."),("use_fates_nocomp",".true."),
             ("spinup_state","2")):
  if nl.get(k)!=v:fail("Reference FATES AD mode changed "+k)
 for k,v in (("DATM_MODE","1PT"),("CALENDAR","NO_LEAP"),("ATM_NCPL","48"),
             ("CLM_ACCELERATED_SPINUP","on")):
  if x.get(k)!=v:fail("Reference CIME mode differs "+k)
 if (REFERENCE/"user_nl_datm_streams").is_file():
  raw=text_safe(REFERENCE/"user_nl_datm_streams")
 else:raw="ABSENT"
 print("=== REFERENCE CIME BUILD/GRID / STREAM USER CONFIG ===")
 for k in CIME_SETTINGS:
  if k in x:print(k,"=",x[k])
 for k in LND_FIELDS:
  if k in nl:print("REFERENCE LND",k,"=",nl[k])
 if raw in ("ABSENT","TOO_LARGE","SYMLINK_NOT_FOLLOWED"):
  print("REFERENCE user_nl_datm_streams:",raw)
 else:
  print("REFERENCE user_nl_datm_streams SHA256:",sha(REFERENCE/"user_nl_datm_streams"))
  for line in raw.splitlines():
   z=line.strip()
   if z and not z.startswith(("#","!")) and "CLM_USRDAT." in z:
    if "datafiles" in z:
     print("REFERENCE_STREAM_USER:",z.split("=",1)[0].strip(),"= [site-specific paths OMITTED]")
    else:
     print("REFERENCE_STREAM_USER:",z[:180])
 if x.get("BUILD_COMPLETE","").lower()!="true":
  fail("Reference CIME case not marked BUILD_COMPLETE; reuse exe not proved")
 root=Path(x.get("EXEROOT",""))
 if not root.is_absolute() or not (root/"cesm.exe").is_file():
  fail("Reference executable unavailable; need standalone CIME build instead")
 print("REFERENCE CESM EXECUTABLE FOUND:",root/"cesm.exe")
 print("DO NOT inherit CH-Dav climate years, DATM datafiles, fsurdat, surface coords, case-grid/coupler geo.")
 return x,nl

def custom_stream_user(streamname,files):
 # Preserve CDEPS namelist syntax. Use only differences from the old stream.
 # Unchanged map is checked from actual effective XML in validate_stream.
 base=streamname+":"
 lines=[
 "! CA-TP4 technical AD5 pilot: generated from pinned Stage04 detached stream",
 "! 28m ZBOT is a PROVISIONAL TA sensor proxy, not approved tower TA_F crosswalk",
 "! Native FLUXNET HH timestamps transformed to midpoint; site clock relative to coupler must be inspected",
 base+"taxmode = cycle",
 base+"tintalgo = linear",
 base+"mapalgo = none",
 base+"year_first = 2002",
 base+"year_last = 2023",
 base+"year_align = 2002",
 base+"offset = 0",
 base+"datafiles = "+",".join(str(p) for _,p in files)]
 return "\n".join(lines)+"\n"

def example_land_user():
 return "\n".join([
 "! CA-TP4 AD5 preview example; NOT ready for case installation or science production",
 "! Original Stage06 forest stand proxy 93/7 and grid soil fallback",
 "fsurdat = '"+str(SURF)+"'",
 "use_fates = .true.",
 "use_fates_sp = .false.",
 "use_fates_fixed_biogeog = .true.",
 "use_fates_nocomp = .true.",
 "spinup_state = 2",
 "hist_fincl1 = "+",".join("'"+v+"'" for v in HISTORY),
 ""]) 

def output_paths_safe():
 for p in (CASE,RUN,ARCH):
  print("PLANNED (NOT CREATED):",p,"EXISTS:",p.exists() or p.is_symlink())
 if any(p.exists() or p.is_symlink() for p in (CASE,RUN,ARCH)):
  print("CAUTION: previous CA-TP4 experimental case/run/archive detected; inspect before any future stage")
 else:
  print("NO EXISTING CASE/RUN/ARCHIVE COLLISION FOR PLANNED NAME")
 print("MUST VERIFY CASE GRID/DOMAIN IS REALLY CA-TP4, NOT CH-Dav")
 print("ONLY PRODUCTION-SAFE PATH: new isolated case preview -> generated datm.streams.xml/lnd_in -> AD5 smoke")
 return not any(p.exists() or p.is_symlink() for p in (CASE,RUN,ARCH))

def selftest():
 assert len(YEARS)==22 and YEARS[0]==2002 and YEARS[-1]==2023
 assert len(MET_MAP)==8
 assert "CLM_USRDAT.UNSET:datafiles" in custom_stream_user("CLM_USRDAT.UNSET",[(2002,Path("/tmp/CA-TP4/2002.nc"))])
 assert len(HISTORY)==7
 print("SELF-TEST PASS: CA-TP4 isolated AD5 configuration plan, 22-year forcing, 8 DATM fields")

def main():
 a=argparse.ArgumentParser(description=__doc__)
 g=a.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--plan",action="store_true")
 a.add_argument("--outdir",type=Path)
 args=a.parse_args()
 if args.self_test:selftest();return
 if args.check and args.outdir is not None:a.error("--check must not specify --outdir")
 if args.plan and args.outdir is None:a.error("--plan requires a NEW --outdir")
 m,files,metcoord=validate_met()
 surface,surfcoord=validate_surface()
 if not np.allclose(metcoord,surfcoord,rtol=0,atol=1e-5):
  fail("CA-TP4 model surface and forcing LAT/LON mismatch: "+repr((metcoord,surfcoord)))
 print("CA-TP4 FORCING LAT/LON",metcoord,"SURFACE LAT/LON",surfcoord,"MATCH")
 stream=validate_stream(files)
 ref,nl=check_template()
 free=output_paths_safe()
 print("SOURCE PASS: Stage04 22 NC and Stage06 forest surface + SHA/coordinates")
 print("SCIENTIFIC GATES STILL: source TA_F->28m sensor crosswalk and station vs model solar-clock alignment")
 print("SCIENTIFIC GATES STILL: idealized stand 93/7 is NOT observed ground fraction; soil is grid fallback")
 print("CIME GRID/DOMAIN GATE: inherits reference machine/binary ONLY IF new case grid/point lat/lon correctly reconfigured")
 print("CASE AUTHORING GATE: user_nl_datm_streams override must be tested by actual preview_namelists; do not copy CaseDocs output")
 if args.check:
  print("STAGE07 READ-ONLY PASS. NO WRITES. Case preparation remains pending.",flush=True)
  return
 out=args.outdir.expanduser().resolve()
 if out.exists() or out.is_symlink():fail("Refuse existing Stage07 output directory "+str(out))
 out.mkdir(parents=True,exist_ok=False)
 u=out/"CA-TP4_user_nl_datm_streams.CANDIDATE_NOT_INSTALLED"
 u.write_text(custom_stream_user(stream,files),encoding="utf-8")
 l=out/"CA-TP4_user_nl_clm_AD5.CANDIDATE_NOT_INSTALLED"
 l.write_text(example_land_user(),encoding="utf-8")
 report={
  "stage":7,"site":SITE,"source_stage04_manifest_sha256":sha(PILOT/"manifest.json"),
  "source_stage06_manifest_sha256":sha(SURFACE_DIR/"manifest.json"),
  "detached_met_stream_xml_sha256":sha(STREAM),
  "surface_sha256":sha(SURF),"model_plan_case":str(CASE),
  "model_plan_rundir":str(RUN),"model_plan_archive":str(ARCH),
  "met_lat_lon":metcoord,"surface_lat_lon":surfcoord,
  "reference_case":str(REFERENCE),
  "reference_xml_settings":ref,
  "actual_stream_source":"CLM_USRDAT.UNSET",
  "CIME_user_nl_datm_streams_candidate":str(u),"CIME_user_nl_datm_streams_sha256":sha(u),
  "CIME_user_nl_clm_candidate":str(l),"CIME_user_nl_clm_sha256":sha(l),
  "run_type":"startup","run_startdate":"2002-01-01",
  "AD_target_year":2402,"NORMAL_target_year":2802,
  "first_test":"ONLY FIVE AD YEARS 2002–2007, STOP_N=5, REST_N=5, RESUBMIT=0",
  "CLM_BLDNML_OPTS":BGC,
  "scientific_scope":"PROVISIONAL_MODEL_TECHNICAL_SMOKE_NOT_TOWER_FOOTPRINT_AREA_OR_SOIL",
  "ZBOT_m":28,"TA_F_height_crosswalk_proven":False,
  "timestep_interval_midpoint_minutes":15,
  "selected_soil":"UNMODIFIED_GRID_TEXTURE_FALLBACK",
  "grid_domain_site_geometry_approved":False,
  "CIME_model_case_created":False,"Slurm_job_submitted":False,
  "build_compatible_case_name_currently_unused":free,
  "remaining_pre_submit":["Case grid/domain location and CIME res definition",
     "Complete case from appropriate POINT case template, not copying CH-Dav station inputs",
     "Actual CIME preview_namelists through private FATES AD overlay, with XML lock restored",
     "Generated DATM stream matches exactly 22 CA-TP4 NC and mapping and cycle",
     "Actual lnd_in fsurdat and all FATES flags/spinup_state and no CN-only reseed",
     "Local standard time convention matches actual coupler timestep/solar geometry",
     "Only 1 x 5yr AD smoke, independently archived triplet restart validated before AD395"]}
 p=out/"manifest.json";p.write_text(json.dumps(report,indent=2,default=str)+"\n",encoding="utf-8")
 print("STAGE07 DETACHED CIME INPUT PLAN CREATED:",out)
 print("NOT A CIME CASE; NOT ACTIVATED DATM; NO MODEL OR SLURM ACTIONS")

if __name__=="__main__":main()
