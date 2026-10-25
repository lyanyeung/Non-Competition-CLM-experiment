#!/usr/bin/env python3
"""AmeriFlux CA-TP4 Stage08: isolated AD5 CIME case + generated namelist PREVIEW.
NO SLURM SUBMISSION, no AD395, and no Normal400.

--self-test  : parser tests, no filesystem needed
--check      : READ ONLY Stage04+Stage06+Stage07 provenance, source CH-Dav CIME
               reference, FATES AD overlay and cloned-case destination safety
--stage --confirm CREATE_ISOLATED_CA_TP4_AD5_CASE_PREVIEW_NO_SLURM
             : write a BRAND-NEW CA-TP4 case/run config and PREVIEW ONLY.

Case name: CA-TP4_AMF_FIXNC_AD400_PILOT
Source meteorology: Stage04 CA-TP4 2002-2023 half-hour MIDPOINT, 22 NC,
ZBOT=28m as a PROVISIONAL TEST PROXY, TA_F sensor crosswalk NOT VERIFIED.
Source surface: Stage06 separate NATVEG100/CROP0/ENF93/DBF7 stand proxy,
soil 10-layer original grid inherited (NOT STATION OBSERVED).
Reference CH-Dav case is ONLY the FATES/CIME machine/program template.
Never copy CH-Dav DATM annual met, CA-TP4 site-specific expected landuse,
soil observation claims, forcing years, or surface into another site's case.

Stage08 uses the successful EXISTING private FATES AD build-namelist overlay
READ-ONLY (two pinned local changes) and restores the CIME env_case.xml
lock after preview even if preview fails. The new case is stamped
ATTEMPTED_UNCERTAIN before mutating it. If stage fails, DO NOT repeat:
inspect original new case and attempt ledger. No code paths call case.submit,
srun, sbatch, and none modify original cases / shared CTSM / inputs.
"""
from __future__ import annotations

import argparse,hashlib,json,re,subprocess,sys,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from netCDF4 import Dataset
import numpy as np

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=B/"CTSM"
SOURCE=B/"cases/CH-Dav_B01_FIXNC_AD400"
NAME="CA-TP4_AMF_FIXNC_AD400_PILOT"
CASE=B/"cases"/NAME
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUNDIR=OUT/NAME/"run"
ARCH=OUT/"archive"/NAME
EXP=B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
S4=B/"experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
S6=EXP/"surface_stage06_20261025T064625818881201Z"
S7=EXP/"stage07_case_plan_20261025T065233585375346Z"
SURFACE=S6/"surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc"
OVERLAY=B/"experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay"
SHARED=CTSM/"bld/CLMBuildNamelist.pm"
PATCHED=OVERLAY/"bld/CLMBuildNamelist.pm"
SHARED_GIT_BLOB="698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
HISTORY=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")
BGC="--bgc fates --no-megan --no-drydep --no-fire_emis"
CONFIRM="CREATE_ISOLATED_CA_TP4_AD5_CASE_PREVIEW_NO_SLURM"
METFIELDS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
           "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
           "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
OLD_GUARD="if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
NEW_GUARD="if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
OLD_RESEED='if ( $nl_flags->{$var} ne "off" ) {'
NEW_RESEED='if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'
STATE=EXP/"stage08_CA_TP4_AD5_CASE_PREVIEW_ATTEMPT.json"

def stop(why):
 raise RuntimeError(str(why))

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()

def git_blob(raw):
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path):
 if not path.is_file():stop("Missing pinned prior stage artifact "+str(path))
 return json.loads(path.read_text(encoding="utf-8"))

def cli(cmd,cwd=None,timeout=240):
 p=subprocess.run([str(x) for x in cmd],cwd=cwd,capture_output=True,text=True,
                  timeout=timeout,check=False)
 if p.returncode!=0:
  stop("CLI FAILED rc=%s cmd=%s \nSTDOUT=%s\nSTDERR=%s"%
      (p.returncode," ".join(map(str,cmd)),p.stdout[-2500:],p.stderr[-2500:]))
 return p.stdout.strip()

def xmlq(case,key):
 return cli([case/"xmlquery",key,"--value"],cwd=case,timeout=90).strip()

def xmlchange(case,key,value):
 return cli([case/"xmlchange",key+"="+str(value)],cwd=case,timeout=90)

def nml(text,key):
 hits=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
 if len(hits)>1:stop("Duplicate generated/attempted namelist key "+key)
 return hits[0].strip().strip("'\"").strip() if hits else None

def replace_nml(txt,key,val):
 pat=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*$"
 hits=list(re.finditer(pat,txt))
 if len(hits)>1:stop("Duplicate cloned user_nl_clm "+key)
 line=key+" = "+val
 if hits:
  m=hits[0]
  return txt[:m.start()]+line+txt[m.end():]
 return txt.rstrip()+"\n"+line+"\n"

def pin_sources():
 a=load(S4/"manifest.json")
 b=load(S6/"manifest.json")
 c=load(S7/"manifest.json")
 if (a.get("site")!="CA-TP4" or a.get("annual_netcdf_files")!=22 or
    a.get("height_m")!=28 or a.get("TA_F_source_sensor_verified") is not False or
    a.get("production_release") is not False or
    a.get("Slurm_submitted") is not False):
  stop("Stage04 pilot invalid or its science status changed")
 if (b.get("site")!="CA-TP4" or b.get("surface")!=str(SURFACE) or
     b.get("Slurm_submitted") is not False or
     b.get("site_specific_soil_observation_used") is not False or
     b.get("model_release") is not False):
  stop("Stage06 forest soil/landunit PROXY status changed")
 if (c.get("stage")!=7 or c.get("site")!="CA-TP4" or
     c.get("CIME_model_case_created") is not False or
     c.get("Slurm_job_submitted") is not False or
     c.get("model_plan_case")!=str(CASE) or
     c.get("model_plan_rundir")!=str(RUNDIR) or
     c.get("model_plan_archive")!=str(ARCH)):
  stop("Stage07 planned case mismatches actual paths / statuses")
 for key,path in (("source_stage04_manifest_sha256",S4/"manifest.json"),
                  ("source_stage06_manifest_sha256",S6/"manifest.json")):
  if c.get(key)!=sha(path):stop("Stage07 original receipt drift "+key)
 if sha(SURFACE)!=b.get("surface_sha256") or sha(SURFACE)!=c.get("surface_sha256"):
  stop("CA-TP4 forest-proxy surface SHA mismatch")
 st=S4/"CA-TP4/datm.streams.CA-TP4.CANDIDATE_NOT_ACTIVATED.xml"
 if sha(st)!=c.get("detached_met_stream_xml_sha256"):
  stop("Reference Stage04 CDEPS stream drift")
 files=[]
 for yr,item in zip(range(2002,2024),a["files"]):
  path=Path(item["path"])
  if (yr!=item["year"] or path!=S4/"CA-TP4/yearly"/f"{yr}.nc" or
      sha(path)!=item["sha256"]):
   stop("CA-TP4 annual 22-year SHA/year mismatch "+str(yr))
  files.append(path)
 if len(files)!=22:stop("Wrong number of year-file inputs")
 stream_candidate=Path(c.get("CIME_user_nl_datm_streams_candidate",""))
 if (stream_candidate!=S7/"CA-TP4_user_nl_datm_streams.CANDIDATE_NOT_INSTALLED" or
     sha(stream_candidate)!=c.get("CIME_user_nl_datm_streams_sha256")):
  stop("Stage07 user stream plan SHA mismatch")
 with Dataset(SURFACE) as ds:
  loc=(float(np.ma.asarray(ds.variables["LATIXY"][:]).ravel()[0]),
       float(np.ma.asarray(ds.variables["LONGXY"][:]).ravel()[0])%360)
  pft=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
  target=np.zeros(15);target[[1,7]]=[93,7]
  if pft.size!=15 or not np.allclose(pft,target,atol=1e-4,rtol=0):
   stop("Target forest surface altered ENF93/DBF7")
 with Dataset(files[0]) as nc:
  met=(float(np.ma.asarray(nc.variables["LATIXY"][:]).ravel()[0]),
       float(np.ma.asarray(nc.variables["LONGXY"][:]).ravel()[0])%360)
  if "ZBOT" not in nc.variables or "QBOT" not in nc.variables:
   stop("No candidate ZBOT/QBOT")
 if not np.allclose(loc,met,atol=1e-5,rtol=0):
  stop("Site surface vs forcing lat/lon mismatch "+str((loc,met)))
 return c,files,loc

def effective_original():
 f=SOURCE/"CaseDocs/datm.streams.xml"
 if not f.is_file():stop("Original source CIME DATM stream XML missing")
 root=ET.parse(f).getroot()
 opts=[e for e in root.iter("stream_info") if e.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(opts)!=1:stop("Reference CLM_USRDAT.UNSET not uniquely identified")
 s=opts[0]
 mapping={}
 for var in s.find("datavars"):
  pair=(var.text or "").split()
  if len(pair)!=2:stop("Unexpected reference DATM datavars")
  mapping[pair[0]]=pair[1]
 for key,val in METFIELDS.items():
  if mapping.get(key)!=val:
   stop("Reference DATM 1PT source variable mismatch "+key)
 return mapping

def overlay_test():
 if not SHARED.is_file() or git_blob(SHARED.read_bytes())!=SHARED_GIT_BLOB:
  stop("Shared pinned CTSM namelist source changed; refuse overlay")
 if not PATCHED.is_file():stop("Existing proven private FATES overlay unavailable; no new overlay writes")
 original=SHARED.read_text(encoding="utf-8")
 start=original.index("sub setup_cmdl_spinup {")
 end=original.index("sub setup_cmdl_simulation_year {",start)
 section=original[start:end]
 if section.count(OLD_GUARD)!=1 or section.count(OLD_RESEED)!=1:
  stop("Original CTSM patch precondition changed")
 expected=original[:start]+section.replace(OLD_GUARD,NEW_GUARD,1).replace(OLD_RESEED,NEW_RESEED,1)+original[end:]
 if PATCHED.read_text(encoding="utf-8")!=expected:
  stop("Private AD overlay differs from demonstrated two-correction source")
 if not (OVERLAY/"bld/build-namelist").is_file():
  stop("Private FATES build-namelist executable unavailable")
 print("PINNED FATES PRIVATE AD OVERLAY PASS:",PATCHED)

def clone_template():
 if not SOURCE.is_dir():stop("Original CH-Dav case missing")
 for key,want in (("BUILD_COMPLETE","TRUE"),("DATM_MODE","1PT"),
                  ("CALENDAR","NO_LEAP"),("ATM_NCPL","48")):
  if xmlq(SOURCE,key).upper()!=want.upper():
   stop("Source FATES CIME reference does not match "+key)
 if xmlq(SOURCE,"GRID")!="a%CLM_USRDAT_l%CLM_USRDAT_oi%null_r%null_g%null_w%null_z%null_m%null":
  stop("Source not CLM_USRDAT 1pt grids")
 exe=Path(xmlq(SOURCE,"EXEROOT"))/"cesm.exe"
 if not exe.is_file():stop("Reference built cesm.exe not found")
 if not (SOURCE/"user_nl_clm").is_file():stop("Original CIME user_nl_clm missing")
 if not (SOURCE/"user_nl_datm_streams").is_file():stop("Original user_nl_datm_streams missing")
 if not (SOURCE/"LockedFiles/env_case.xml").is_file():stop("Original reference locked env_case.xml missing")
 effective_original()
 overlay_test()
 print("REFERENCE FATES CASE & SHARED EXE PASS:",exe)
 return exe

def stream_assignments(text):
 # CDEPS user_nl_datm_streams grammar consists of stream:key = VALUE
 # with optional multiline continuation values. Preserve every non-meteorology
 # stream unchanged and reject ambiguities; replace ONLY CLM_USRDAT.UNSET.
 rex=re.compile(r"(?m)^[ \t]*([A-Za-z][\w.-]*):([A-Za-z_]\w*)[ \t]*=")
 starts=list(rex.finditer(text))
 found={}
 for i,m in enumerate(starts):
  key=m.group(1)+":"+m.group(2)
  begin=m.start()
  end=starts[i+1].start() if i+1<len(starts) else len(text)
  found.setdefault(key,[]).append((begin,end,text[begin:end]))
 return found

def build_stream_user(text,files):
 got=stream_assignments(text)
 changes={
 "taxmode":"cycle","tintalgo":"linear","mapalgo":"none",
 "meshfile":"none","year_first":"2002","year_last":"2023",
 "year_align":"2002","offset":"0",
 "datafiles":",".join(str(p) for p in files)}
 prefix="CLM_USRDAT.UNSET:"
 # Leave original datavars unchanged; verified against effective reference.
 for name in (*[k for k in changes if k!="offset"],"datavars"):
  if len(got.get(prefix+name,[]))!=1:
   stop("Expected one known 1PT override in template user_nl_datm_streams: "+name)
 # Offset is sometimes omitted from user overrides but is present
 # as offset=0 in the effective CDEPS XML. Add an explicit override.
 if len(got.get(prefix+"offset",[]))>1:
  stop("Duplicate 1PT offset override")
 result=text
 substitutions=[]
 for key,value in changes.items():
  if key=="offset" and not got.get(prefix+key):continue
  lo,hi,_=got[prefix+key][0]
  substitutions.append((lo,hi,prefix+key+" = "+value+"\n"))
 for lo,hi,replacement in sorted(substitutions,reverse=True):
  result=result[:lo]+replacement+result[hi:]
 if not got.get(prefix+"offset"):
  result=result.rstrip()+"\n"+prefix+"offset = 0\n"
 if "CH-Dav_DATM_" in result:
  stop("Unremoved original station CH-Dav annual input in DATM user file")
 revised=stream_assignments(result)
 for key in changes:
  if len(revised.get(prefix+key,[]))!=1:
   stop("Replaced 1PT configuration is ambiguous "+key)
 payload=revised[prefix+"datafiles"][0][2]
 for p in files:
  if str(p) not in payload:
   stop("Lost CA-TP4 DATM annual file "+str(p))
 if result==text:stop("No actual CA-TP4 stream change")
 return result

def clm_user(text):
 for name in ("finidat","reseed_dead_plants"):
  if nml(text,name) is not None:
   if name=="reseed_dead_plants" or nml(text,name):
    stop("Refusing cloned non-coldstart / CN-only user setting: "+name)
 desired={
  "fsurdat":"'"+str(SURFACE)+"'",
  "use_fates":".true.","use_fates_sp":".false.",
  "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
  "spinup_state":"2",
  "hist_fincl1":",".join("'"+x+"'" for x in HISTORY)}
 for k,v in desired.items():
  text=replace_nml(text,k,v)
 return text

def xml_settings():
 return {
 "RUN_TYPE":"startup","RUN_STARTDATE":"2002-01-01",
 "CONTINUE_RUN":"FALSE","CLM_FORCE_COLDSTART":"on",
 "CLM_ACCELERATED_SPINUP":"on",
 "STOP_OPTION":"nyears","STOP_N":"5",
 "REST_OPTION":"nyears","REST_N":"5",
 "RESUBMIT":"0","DOUT_S":"TRUE",
 "DATM_MODE":"1PT","DATM_YR_START":"2002",
 "DATM_YR_END":"2023","DATM_YR_ALIGN":"2002",
 "ATM_NCPL":"48","CLM_USRDAT_NAME":"UNSET",
 "CLM_BLDNML_OPTS":BGC,
 "RUNDIR":str(RUNDIR),"DOUT_S_ROOT":str(ARCH),
 "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"}

def no_existing():
 for path in (CASE,RUNDIR,ARCH,STATE):
  if path.exists() or path.is_symlink():
   stop("Already exists / possible previous Stage08 attempt: "+str(path))
 if not EXP.is_dir():stop("Expected project experiment output not found")
 # No scheduler calls in Stage08; no case with this name can have been submitted
 # if the path is absent, but users must not create this case by another script.

def generated_met_check():
 root=ET.parse(CASE/"CaseDocs/datm.streams.xml").getroot()
 s=[v for v in root.iter("stream_info") if v.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(s)!=1:stop("Generated CDEPS stream missing/duplicate CLM_USRDAT.UNSET")
 s=s[0]
 expect=xml_settings()
 for field,value in (("taxmode","cycle"),("tintalgo","linear"),
                     ("mapalgo","none"),("year_first","2002"),
                     ("year_last","2023"),("year_align","2002"),
                     ("meshfile","none"),("offset","0")):
  node=s.find(field)
  if node is None or (node.text or "").strip()!=value:
   stop("Generated stream disagrees with CA-TP4 override "+field)
 mapping={}
 for n in s.find("datavars"):
  arr=(n.text or "").split()
  if len(arr)!=2:stop("Generated DATM field pair malformed")
  mapping[arr[0]]=arr[1]
 for k,v in METFIELDS.items():
  if mapping.get(k)!=v:stop("Generated CDEPS field mismatch "+k)
 files=[(f.text or "").strip() for f in s.find("datafiles")]
 exp=[str(S4/"CA-TP4/yearly"/f"{y}.nc") for y in range(2002,2024)]
 if files!=exp:stop("Generated DATM stream still references old site OR missing 22 annual files")
 print("GENERATED DATM STREAM PASS: CA-TP4 22/22 years, midpoint candidate, ZBOT, all 8 variables, cycle/linear")

def generated_land_check():
 doc=CASE/"CaseDocs/lnd_in"
 if not doc.is_file():stop("Generated effective land namelist absent")
 raw=doc.read_text(encoding="utf-8",errors="replace")
 for key,want in (("fsurdat",str(SURFACE)),
                  ("use_fates",".true."),("use_fates_sp",".false."),
                  ("use_fates_fixed_biogeog",".true."),
                  ("use_fates_nocomp",".true."),
                  ("spinup_state","2"),("use_cn",".false.")):
  value=nml(raw,key)
  if value!=want:stop("Generated FATES lnd_in mismatch "+key+"="+str(value))
 if nml(raw,"finidat") not in (None,"") or nml(raw,"reseed_dead_plants") is not None:
  stop("AD coldstart lnd_in contains nonempty finidat or CN-only reseed_dead_plants")
 print("GENERATED FATES LAND PASS: correct CA-TP4 surface, fixed PFT/nocomp, AD spinup_state=2")

def lock_bytes():
 a=CASE/"env_case.xml"
 b=CASE/"LockedFiles/env_case.xml"
 if not a.is_file() or not b.is_file() or a.read_bytes()!=b.read_bytes():
  stop("CIME env_case.xml differs from LockedFiles copy")
 root=ET.parse(b).getroot()
 flags={n.attrib["id"]:n.attrib.get("value") for n in root.iter("entry") if n.attrib.get("id")}
 if flags.get("COMP_ROOT_DIR_LND")!="$SRCROOT":
  stop("CIME lock COMP_ROOT_DIR_LND is not literal $SRCROOT")
 return a.read_bytes()

def stage(exe,files,source,loc):
 no_existing()
 # PRE-VALIDATE all clm/datm transformations before creating the case.
 src_user=(SOURCE/"user_nl_datm_streams").read_text(encoding="utf-8")
 new_stream=build_stream_user(src_user,files)
 src_land=(SOURCE/"user_nl_clm").read_text(encoding="utf-8")
 new_land=clm_user(src_land)
 # Create non-overwritable attempt stamp BEFORE CIME mutations, so never retry.
 with STATE.open("x",encoding="utf-8") as f:
  json.dump({"stage":8,"site":"CA-TP4","state":"ATTEMPTED_UNCERTAIN",
       "source_stage07_manifest_sha256":sha(S7/"manifest.json"),
       "source_stage06_surface_sha256":sha(SURFACE),
       "original_CIME_template":str(SOURCE),"target_CIME_case":str(CASE),
       "target_run":str(RUNDIR),"target_archive":str(ARCH),
       "created_utc":datetime.now(timezone.utc).isoformat(),
       "model_jobs_submitted":False},f,indent=2)
  f.write("\n")
 print("STAGE08 ATTEMPT STAMP:",STATE,flush=True)
 cli([CTSM/"cime/scripts/create_clone","--case",CASE,"--clone",SOURCE,"--keepexe"],cwd=CTSM/"cime/scripts",timeout=420)
 if not CASE.is_dir() or xmlq(CASE,"CASE")!=NAME:
  stop("CIME case clone did not create expected independent identity")
 if xmlq(CASE,"EXEROOT")!=str(exe.parent) or xmlq(CASE,"BUILD_COMPLETE").lower()!="true":
  stop("Clone failed to preserve proven built 1PT/FATES executable")
 for key,value in xml_settings().items():
  xmlchange(CASE,key,value)
 (CASE/"user_nl_datm_streams").write_text(new_stream,encoding="utf-8")
 (CASE/"user_nl_clm").write_text(new_land,encoding="utf-8")
 # CIME clone may have already generated setup; use setup only if needed.
 if not (CASE/".case.run").is_file():
  cli([CASE/"case.setup"],cwd=CASE,timeout=300)
 snapshot=lock_bytes()
 if Path(xmlq(CASE,"COMP_ROOT_DIR_LND")).resolve()!=CTSM.resolve():
  stop("New CIME case current COMP_ROOT_DIR_LND does not resolve to shared CTSM")
 try:
  xmlchange(CASE,"COMP_ROOT_DIR_LND",OVERLAY)
  cli([CASE/"preview_namelists"],cwd=CASE,timeout=600)
 finally:
  # Restore CIME locked env_case.xml EVEN IF preview failed. Stop if restore
  # fails, never retry the entire case creation over a partial case.
  xmlchange(CASE,"COMP_ROOT_DIR_LND","$SRCROOT")
  if (CASE/"env_case.xml").read_bytes()!=snapshot or (CASE/"LockedFiles/env_case.xml").read_bytes()!=snapshot:
   stop("CIME env_case lock not restored byte-for-byte; STOP.")
 print("CIME LOCK RESTORED after preview",flush=True)
 generated_met_check()
 generated_land_check()
 for k,value in xml_settings().items():
  if xmlq(CASE,k).strip().lower()!=value.lower():
   stop("Generated target case XML differs "+k)
 if xmlq(CASE,"EXEROOT")!=str(exe.parent):
  stop("Unexpected CA-TP4 case executable drift")
 receipt=load(STATE)
 receipt.update({
  "state":"PREVIEW_VERIFIED_NOT_SUBMITTED",
  "stage04_met_manifest_sha256":sha(S4/"manifest.json"),
  "stage06_surface_manifest_sha256":sha(S6/"manifest.json"),
  "stage07_plan_manifest_sha256":sha(S7/"manifest.json"),
  "reference_executable_sha256":sha(exe),
  "input_surface":str(SURFACE),"input_surface_sha256":sha(SURFACE),
  "met_22_files":[str(p) for p in files],
  "ca_tp4_lat_lon":loc,
  "CIME_generated_lnd_in_sha256":sha(CASE/"CaseDocs/lnd_in"),
  "CIME_generated_datm_stream_xml_sha256":sha(CASE/"CaseDocs/datm.streams.xml"),
  "CLM_ACCELERATED_SPINUP":"on","spinup_state":2,
  "year_start":2002,"AD5_checkpoint":2007,"AD400_target":2402,
  "normal400_target":2802,
  "scientific_height_28m_verified":False,
  "forest_point_PFT_ground_area_measured":False,
  "soil_is_site_measured":False,
  "co2_baseline_ppm_is_scientifically_reviewed":False,
  "model_solar_clock_vs_station_LST_approved":False,
  "CIME_site_domain_geometry_approved":False,
  "case_created":True,"model_jobs_submitted":False,
  "ready_to_submit_AD5":False,
  "requires_further_science_coupler_geometry_and_time_review":True,
  "validated_utc":datetime.now(timezone.utc).isoformat()
 })
 STATE.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
 print("STAGE08 CASE CREATED + GENERATED NAMELISTS VERIFIED:",CASE)
 print("NO SLURM JOB SUBMITTED. AD5 SUBMISSION STILL HELD: coupling geometry/time + scientific pilot approval.")
 print("CONTINUE ONLY AFTER REVIEWING CASEDOCS AND PILOT SOLAR/GEOMETRY ASSUMPTIONS.")

def selftest():
 a="CLM_USRDAT.UNSET:taxmode = cycle\nCLM_USRDAT.UNSET:year_first = 1997\nCLM_USRDAT.UNSET:year_last = 2025\nCLM_USRDAT.UNSET:year_align = 1997\nCLM_USRDAT.UNSET:tintalgo = linear\nCLM_USRDAT.UNSET:mapalgo = none\nCLM_USRDAT.UNSET:meshfile = none\nCLM_USRDAT.UNSET:offset = 0\nCLM_USRDAT.UNSET:datafiles = /tmp/old.nc\nCLM_USRDAT.UNSET:datavars = QBOT Sa_shum,ZBOT Sa_z\npreso3.clim_2000:taxmode = cycle\n"
 f=[Path("/tmp/CA-TP4/2002.nc"),Path("/tmp/CA-TP4/2003.nc")]
 v=build_stream_user(a,f)
 assert "CA-TP4/2002.nc" in v and "old.nc" not in v
 assert "preso3.clim_2000:taxmode = cycle" in v
 sample_without_offset=a.replace("CLM_USRDAT.UNSET:offset = 0\n","")
 without=build_stream_user(sample_without_offset,f)
 assert "CLM_USRDAT.UNSET:offset = 0" in without
 assert "preso3.clim_2000:taxmode = cycle" in without
 assert len(METFIELDS)==8 and len(HISTORY)==7
 assert nml("fsurdat = '/tmp/site.nc'\n","fsurdat")=="/tmp/site.nc"
 print("SELF-TEST PASS: new site-only CIME user_nl_DATM stream overrides with ancillary preservation, 22-year and FATES AD gates")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 grp=p.add_mutually_exclusive_group(required=True)
 grp.add_argument("--self-test",action="store_true")
 grp.add_argument("--check",action="store_true")
 grp.add_argument("--stage",action="store_true")
 p.add_argument("--confirm",type=str)
 opts=p.parse_args()
 if opts.self_test:selftest();return
 if opts.stage and opts.confirm!=CONFIRM:
  p.error("--stage requires --confirm "+CONFIRM)
 if opts.check and opts.confirm:
  p.error("--check does not accept --confirm")
 plan,files,loc=pin_sources()
 exe=clone_template()
 print("PROVENANCE PASS: Stage04 (22 met NetCDF), Stage06 (forest-proxy), Stage07 (detached CIME plan)")
 print("CA-TP4 LAT/LON",loc,"FORCING AND LAND SURFACE MATCH")
 print("REFERENCE 1PT FATES EXECUTABLE:",exe)
 print("STAGE08 CASE:",CASE)
 if opts.check:
  no_existing()
  src_user=(SOURCE/"user_nl_datm_streams").read_text(encoding="utf-8")
  prepared=build_stream_user(src_user,files)
  keys=stream_assignments(src_user)
  print("CDEPS ACTUAL SOURCE OVERRIDES:",
        sorted(k for k in keys if k.startswith("CLM_USRDAT.UNSET:")))
  print("CA-TP4 MET OVERRIDES PRECHECK PASS:",
        len(files),"annual files, zero CH-Dav met inputs, ancillary streams retained")
  print("CDEPS ORIGINAL OFFSET OVERRIDE PRESENT:",
        "CLM_USRDAT.UNSET:offset" in keys)
  print("CDEPS CA-TP4 OVERRIDE CHAR COUNT:",len(prepared))
  print("STAGE08 READ-ONLY CHECK PASS. No case or Slurm changes.")
  return
 stage(exe,files,plan,loc)

if __name__=="__main__":main()
