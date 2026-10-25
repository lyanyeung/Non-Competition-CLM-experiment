#!/usr/bin/env python3
"""Stage12: one independent CA-TP4 UTC-V2 FATES AD5 CASE PREVIEW, no Slurm.

Stage11 UTC 22-year 5h shifted NetCDF; preserve old Stage08 LOCAL-LABEL
case unchanged. Use the already-proven shared FATES AD *PRIVATE* build-
namelist overlay without editing CTSM. Apply fixed 2002 GLOBAL NOAA
background CO2 372.58 ppm (technical experiment decision, not tower data).
No 400y submission, no initial 5yr Slurm; verified generated input only.

Usage:
  --self-test         offline parser tests
  --check             only reads Stage08, Stage11, pinned files/CIME source
  --stage --confirm CREATE_NEW_CA_TP4_UTC_V2_AD5_PREVIEW_NO_SLURM
                      explicit ONE-TIME CIME clone and preview, never overwrite
After any --stage error, preserve its one-time attempt ledger and partial
case. DO NOT rerun stage without manual diagnosis.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
S8=Path(__file__).with_name("08_CA_TP4_create_AD5_CIME_case_preview_no_slurm.py")
S11=B/"experiments/AmeriFlux_MultiSite_10/reports/stage11_CA_TP4_DATM_UTC_20261025T080240825734395Z"
PREV=B/"cases/CA-TP4_AMF_FIXNC_AD400_PILOT"
NAME="CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"
CASE=B/"cases"/NAME
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUNDIR=OUT/NAME/"run"
ARCH=OUT/"archive"/NAME
EXE_EXPECTED=OUT/"GF-Guy_FATES_SURF2000_CO2405_1PT/bld/cesm.exe"
STATE=EXP/"stage12_CA_TP4_UTC_V2_AD5_PREVIEW_ATTEMPT.json"
ACK="CREATE_NEW_CA_TP4_UTC_V2_AD5_PREVIEW_NO_SLURM"
CO2="372.58"
MET_FIELDS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
            "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
            "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
YEARS=list(range(2002,2024))
THIS_SCRIPT=Path(__file__).resolve()

def fail(s):raise RuntimeError(str(s))

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1<<20),b""):h.update(x)
 return h.hexdigest()

def jsonload(p):
 if not p.is_file():fail("Missing manifest or one-time ledger "+str(p))
 return json.loads(p.read_text(encoding="utf8"))

def stage8():
 if not S8.is_file():fail("Stage08 script absent next to Stage12; fetch pinned file first")
 spec=importlib.util.spec_from_file_location("ca_tp4_verified_stage08",S8)
 if spec is None or spec.loader is None:fail("Cannot import Stage08 script")
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 if (mod.CASE!=PREV or mod.SURFACE!=
       B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4/surface_stage06_20261025T064625818881201Z/surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc"):
  fail("Stage08 installed source case/science assumptions differ")
 return mod

def cli(cmd,cwd=None,seconds=180):
 result=subprocess.run([str(x) for x in cmd],cwd=cwd,text=True,
                       capture_output=True,timeout=seconds,check=False)
 if result.returncode:
  fail("COMMAND FAILED: %s\nEXIT=%d\nOUT=%s\nERR=%s"%
       (" ".join(map(str,cmd)),result.returncode,
        result.stdout[-2300:],result.stderr[-2300:]))
 return result.stdout.strip()

def q(case,key):
 return cli([case/"xmlquery",key,"--value"],cwd=case,seconds=90).strip()

def ch(case,key,val):
 return cli([case/"xmlchange",key+"="+str(val)],cwd=case,seconds=90)

def reference(m):
 old=jsonload(m.STATE)
 if (old.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or
     old.get("model_jobs_submitted") is not False or
     old.get("case_created") is not True or
     old.get("ready_to_submit_AD5") is not False):
  fail("Stage08 independent FATES case not verified and unsent")
 for k,p in (("CIME_generated_lnd_in_sha256",PREV/"CaseDocs/lnd_in"),
             ("CIME_generated_datm_stream_xml_sha256",PREV/"CaseDocs/datm.streams.xml"),
             ("input_surface_sha256",m.SURFACE)):
  if old.get(k)!=sha(p):fail("Stage08 original model files were modified "+k)
 if (PREV/"env_case.xml").read_bytes()!=(PREV/"LockedFiles/env_case.xml").read_bytes():
  fail("Old Stage08 case CIME env_case lock mismatch")
 if q(PREV,"CASE")!=PREV.name or q(PREV,"BUILD_COMPLETE").lower()!="true":
  fail("Original FATES case no longer built")
 exe=Path(q(PREV,"EXEROOT"))/"cesm.exe"
 if exe!=EXE_EXPECTED or not exe.is_file():fail("Original built cesm executable changed")
 if q(PREV,"CLM_CO2_TYPE")!="constant":fail("Unexpected source model CO2 policy")
 if q(PREV,"CCSM_CO2_PPMV")!="363.04":fail("Original 1997 CO2 inheritance changed; review manually")
 m.overlay_test()
 return old,exe

def utc_inputs(m,old):
 n=jsonload(S11/"manifest.json")
 if (n.get("stage")!=11 or n.get("site")!="CA-TP4" or
     n.get("n_years")!=22 or n.get("annual_samples")!=17520 or
     n.get("total_samples")!=385440 or n.get("shift_seconds")!=18000 or
     n.get("stream_offset_seconds")!=0 or
     n.get("model_case_modified") is not False or
     n.get("slurm_submitted") is not False or
     n.get("production_release") is not False or
     n.get("model_solar_clock_runtime_verified") is not False):
  fail("Stage11 UTC forcing source or scientific status changed")
 if n.get("source_stage04_manifest_sha256")!=sha(m.S4/"manifest.json"):
  fail("Stage11 was not built from pinned Stage04 original")
 if sha(Path(n["detached_CDEPS_stream_path"]))!=n.get("detached_CDEPS_stream_sha256"):
  fail("Stage11 UTC detached CDEPS stream changed")
 items=n.get("pilot_nc",[])
 if len(items)!=22:fail("Stage11 needs exactly 22 yearly pilot source receipts")
 files=[]
 for y,item in zip(YEARS,items):
  f=S11/"CA-TP4/yearly"/f"{y}.nc"
  if item["year"]!=y or Path(item["path"])!=f or sha(f)!=item["sha256"]:
   fail("Stage11 UTC annual NC SHA or filename drift "+str(y))
  files.append(f)
 with Dataset(files[0]) as first:
  t=first.variables["time"]
  if len(t)!=17520 or t.calendar!="noleap" or not np.allclose(
      t[[0,1,-1]],[1/96,1/48+1/96,17519/48+1/96],atol=1e-10,rtol=0):
   fail("UTC meteorological midpoint time does not match model forcing")
  lon=float(np.asarray(first.variables["LONGXY"][:]).ravel()[0])
  lat=float(np.asarray(first.variables["LATIXY"][:]).ravel()[0])
  if abs(lon-279.6426)>1e-4 or abs(lat-42.7102)>1e-4:
   fail("UTC pilot point geometry changed")
 old_surface=Path(old["input_surface"])
 if not old_surface.is_file() or sha(old_surface)!=old["input_surface_sha256"]:
  fail("Stage06 site forest surface changed")
 print("STAGE11 UTC INPUT PASS: 22/22 SHA, +5h UTC cyclic records, midpoint/point geometry, original Stage08 preserved")
 return n,files

def check_src_cime_files(m,files):
 if not (PREV/"user_nl_datm_streams").is_file() or not (PREV/"user_nl_clm").is_file():
  fail("Missing actual Stage08 user DATM or CLM source")
 orig_datm=(PREV/"user_nl_datm_streams").read_text(encoding="utf8")
 orig_land=(PREV/"user_nl_clm").read_text(encoding="utf8")
 # Proven Stage08 CDEPS key parser + FATES namelist transformer; no writes.
 modified_datm=m.build_stream_user(orig_datm,files)
 modified_land=m.clm_user(orig_land)
 if "CH-Dav_DATM_" in modified_datm:fail("Original European site DATM leaked")
 if len(m.stream_assignments(modified_datm).get("CLM_USRDAT.UNSET:datafiles",[]))!=1:
  fail("UTC user stream path override ambiguous")
 if modified_datm==orig_datm:fail("UTC stream update did not change source dataset")
 return modified_datm,modified_land

def xmlsettings(m):
 settings=m.xml_settings()
 settings.update({"RUNDIR":str(RUNDIR),
                  "DOUT_S_ROOT":str(ARCH),
                  "CLM_CO2_TYPE":"constant",
                  "CCSM_CO2_PPMV":CO2,
                  "DATM_CO2_TSERIES":"none",
                  "DATM_YR_START":"2002","DATM_YR_END":"2023",
                  "DATM_YR_ALIGN":"2002",
                  "RUN_STARTDATE":"2002-01-01",
                  "STOP_N":"5","REST_N":"5","RESUBMIT":"0"})
 if settings.get("CLM_ACCELERATED_SPINUP")!="on" or settings.get("DATM_MODE")!="1PT":
  fail("Stage08 model settings no longer accelerate FATES AD 1PT")
 return settings

def check_new_absence():
 for p in (CASE,RUNDIR,ARCH,STATE):
  if p.exists() or p.is_symlink():
   fail("Stage12 might have been attempted already. Never rerun on partial case: "+str(p))

def stream_actual(files):
 ref=ET.parse(PREV/"CaseDocs/datm.streams.xml").getroot()
 current=ET.parse(CASE/"CaseDocs/datm.streams.xml").getroot()
 originals={x.attrib.get("name"):x for x in ref.iter("stream_info")}
 actual={x.attrib.get("name"):x for x in current.iter("stream_info")}
 if set(actual)!=set(originals):fail("CDEPS ancillary stream set changed in clone")
 met=actual.get("CLM_USRDAT.UNSET")
 if met is None:fail("New case missing CA-TP4 USRDAT main meteorology stream")
 for k,v in (("taxmode","cycle"),("tintalgo","linear"),("mapalgo","none"),
             ("meshfile","none"),("offset","0"),("year_first","2002"),
             ("year_last","2023"),("year_align","2002")):
  x=met.find(k)
  if x is None or (x.text or "").strip()!=v:
   fail("Generated UTC CDEPS met setting incorrect "+k)
 mapped={}
 for e in met.find("datavars"):
  parts=(e.text or "").strip().split()
  if len(parts)!=2 or parts[0] in mapped:fail("Duplicated/invalid actual datavars entry")
  mapped[parts[0]]=parts[1]
 for k,v in MET_FIELDS.items():
  if mapped.get(k)!=v:fail("Incorrect CDEPS source-to-model map "+k)
 input_paths=[Path((f.text or "").strip()) for f in met.find("datafiles")]
 if input_paths!=files:fail("Generated new case does not use exact 22 Stage11 UTC NetCDF")
 for key in (set(actual)-{"CLM_USRDAT.UNSET"}):
  a=originals[key];b=actual[key]
  if ET.tostring(a)!=ET.tostring(b):
   fail("Reference auxiliary forcing stream modified unexpectedly: "+key)
 print("UTC GENERATED DATM PASS: 22 Stage11 files, 8 maps, cycle/linear, offset 0, ancillary preserved")
 return len(input_paths)

def land_actual(m):
 f=CASE/"CaseDocs/lnd_in"
 if not f.is_file():fail("New case generated lnd_in absent")
 raw=f.read_text(encoding="utf8")
 for k,v in (("fsurdat",str(m.SURFACE)),("spinup_state","2"),
             ("use_fates",".true."),("use_fates_sp",".false."),
             ("use_fates_fixed_biogeog",".true."),
             ("use_fates_nocomp",".true."),("use_cn",".false.")):
  if m.nml(raw,k)!=v:fail("Generated land mode mismatch: "+k)
 if m.nml(raw,"finidat") not in (None,"") or m.nml(raw,"reseed_dead_plants") is not None:
  fail("Generated FATES AD5 not cold start")
 # Some CTSM versions specify co2_ppmv in generated lnd_in; when present
 # it must track requested CIME xml CCSM_CO2_PPMV baseline.
 p=m.nml(raw,"co2_ppmv")
 if p is not None and abs(float(p)-float(CO2))>0.03:
  fail("Generated lnd_in CO2 ppmv differs from requested 2002 global baseline")
 print("UTC GENERATED LAND PASS: site-only surface, FATES fixed PFT nocomp, spinup_state2, cold start")
 print("LAND CO2_PPMV:",p if p else "CONTROLLED VIA CIME CONSTANT-CO2 COUPLING")
 return True

def try_stage(m,exe,files,moddatm,modland):
 check_new_absence()
 settings=xmlsettings(m)
 # Immutable attempt receipt is deliberately saved BEFORE any CIME change.
 STATE.parent.mkdir(parents=True,exist_ok=True)
 with STATE.open("x",encoding="utf8") as f:
  json.dump({"stage":12,"case":str(CASE),
       "source_case":str(PREV),"state":"ATTEMPTED_UNCERTAIN",
       "UTC_stage11_manifest_sha256":sha(S11/"manifest.json"),
       "Stage08_existing_case_unchanged":True,
       "model_jobs_submitted":False,
       "created_utc":datetime.now(timezone.utc).isoformat()},f,indent=2)
  f.write("\n")
 print("ONE-TIME STAGE12 ATTEMPT RECORDED:",STATE,flush=True)
 cli([m.CTSM/"cime/scripts/create_clone","--case",CASE,
      "--clone",PREV,"--keepexe"],cwd=m.CTSM/"cime/scripts",seconds=420)
 if not CASE.is_dir() or q(CASE,"CASE")!=NAME:
  fail("CIME new UTC clone identity not correct")
 if Path(q(CASE,"EXEROOT"))/"cesm.exe"!=exe or q(CASE,"BUILD_COMPLETE").lower()!="true":
  fail("UTC case didn't preserve compiled 1PT FATES executable")
 for k,v in settings.items():ch(CASE,k,v)
 (CASE/"user_nl_datm_streams").write_text(moddatm,encoding="utf8")
 (CASE/"user_nl_clm").write_text(modland,encoding="utf8")
 if not (CASE/".case.run").is_file():
  cli([CASE/"case.setup"],cwd=CASE,seconds=300)
 current=CASE/"env_case.xml"
 locked=CASE/"LockedFiles/env_case.xml"
 if not locked.is_file() or current.read_bytes()!=locked.read_bytes():
  fail("New CIME env_case.xml lock already inconsistent")
 lock_bytes=current.read_bytes()
 entries={x.attrib.get("id"):x.attrib.get("value") for x in ET.parse(locked).iter("entry")}
 if entries.get("COMP_ROOT_DIR_LND")!="$SRCROOT":fail("New CIME shared CTSM root lock differs")
 if Path(q(CASE,"COMP_ROOT_DIR_LND")).resolve()!=m.CTSM.resolve():
  fail("CIME new clone does not point to original unpatched shared CTSM")
 try:
  ch(CASE,"COMP_ROOT_DIR_LND",str(m.OVERLAY))
  cli([CASE/"preview_namelists"],cwd=CASE,seconds=600)
 finally:
  ch(CASE,"COMP_ROOT_DIR_LND","$SRCROOT")
  if current.read_bytes()!=lock_bytes or locked.read_bytes()!=lock_bytes:
   fail("CIME env_case.xml not restored exactly after private overlay. STOP.")
 print("PRIVATE CTSM FATES AD NAMELIST PREVIEW PASS AND LOCK RESTORED")
 stream_actual(files)
 land_actual(m)
 for k,v in settings.items():
  if q(CASE,k).strip().lower()!=str(v).lower():
   fail("Actual case settings do not match expected "+k)
 if q(CASE,"CLM_CO2_TYPE")!="constant" or abs(float(q(CASE,"CCSM_CO2_PPMV"))-372.58)>0.02:
  fail("Generated CIME 2002 CO2 baseline is not 372.58")
 state=jsonload(STATE)
 state.update({
  "state":"PREVIEW_VERIFIED_NOT_SUBMITTED",
  "model_case_created":True,"model_jobs_submitted":False,
  "ready_to_submit_AD5":False,
  "needs_coupler_geometry_and_clock_validation":True,
  "source_evidence":"FLUXNET LST UTC-5 -> Stage11 UTC 22yr forcing",
  "verified_new_CO2_ppm":372.58,
  "new_met_file_count":22,
  "source_stage11_manifest_sha256":sha(S11/"manifest.json"),
  "source_stage06_surface_sha256":sha(m.SURFACE),
  "generated_lnd_in_sha256":sha(CASE/"CaseDocs/lnd_in"),
  "generated_datm_stream_sha256":sha(CASE/"CaseDocs/datm.streams.xml"),
  "case_new_RUNDIR":str(RUNDIR),"case_new_archive":str(ARCH),
  "provisional_height_m":28,"height_measurement_crosswalk_verified":False,
  "forest_PFT93_7_are_measured_cover":False,
  "grid_soil_is_site_measured":False,
  "UTC_cycle_2002_preceded_by_2023_assumption":True,
  "no_AD395_or_Normal400_started":True,
  "verified_utc":datetime.now(timezone.utc).isoformat()})
 STATE.write_text(json.dumps(state,indent=2)+"\n",encoding="utf8")
 print("STAGE12 SUCCESS: NEW UTC-V2 CA-TP4 AD5 FATES CIME CASE PREVIEW VERIFIED")
 print("CASE:",CASE)
 print("SOURCE: Stage11 UTC 22y, FLUXNET first 2002 00:15 UTC uses last 2023 forcing cycle")
 print("CO2: 372.58 ppm constant, 2002 NOAA global background")
 print("AD5 CONFIG: STOP_N=5, REST_N=5, RESUBMIT=0, spinup_state=2")
 print("NO SLURM SUBMITTED / NO ORIGINAL STAGE08 CASE CHANGED")
 print("NEXT GATE: pilot validation of actual coupler geometry/clock, then single AD5 job.")

def selftest():
 assert len(YEARS)==22 and YEARS[0]==2002 and YEARS[-1]==2023
 assert len(MET_FIELDS)==8 and CO2=="372.58"
 assert "UTC_V2_AD5" in NAME and NAME!=PREV.name
 assert "stage12" in STATE.name
 print("SELF-TEST PASS: new CA-TP4 UTC-V2 AD5 case paths, 22 NC, CO2 2002 policy, no Slurm")

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--stage",action="store_true")
 ap.add_argument("--confirm")
 args=ap.parse_args()
 if args.self_test:selftest();return
 if args.stage and args.confirm!=ACK:ap.error("--stage requires --confirm "+ACK)
 if args.check and args.confirm:ap.error("--check does not accept confirmation")
 m=stage8()
 old,exe=reference(m)
 note,files=utc_inputs(m,old)
 candidate,land_candidate=check_src_cime_files(m,files)
 check_new_absence()
 print("CHECK: existing Stage08 case unchanged; 22 new Stage11 UTC inputs integrity PASS")
 print("CHECK: shared private FATES AD overlay, reference executable and site surface PASS")
 print("CHECK: expected new CO2 372.58 ppm (2002 annual global mean); new case not yet created")
 print("CHECK: proposed new case",CASE)
 if args.check:
  print("STAGE12 READ-ONLY CHECK PASS, no files created or jobs submitted")
  return
 try_stage(m,exe,files,candidate,land_candidate)

if __name__=="__main__":main()
