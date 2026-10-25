#!/usr/bin/env python3
"""Stage20: fix CIME single-point PTS_LAT/LON for all four AmeriFlux AD5 cases.

PROVEN root cause: failed CA-TP4 run 4728206 kept CH-Dav
PTS_LAT=46.81533, PTS_LON=9.85591, but its site fsurdat LATIXY=42.7102
LONGXY=279.6426; CTSM surfrdMod.F90 line122 checks <0.001 degrees.

NO met QC/reindex, NO modified source netcdf, NO model recompilation.
Create NEW versioned case for each site from its verified former CIME case
using create_clone --keepexe, set PTS_LAT/LON from EXACT source fsurdat
LATIXY/LONGXY, PTS_DOMAINFILE=UNSET, retain source user_nl/datm stream,
independent run/archive, preview with proven private FATES AD namelist
overlay and RESTORE original CTSM lock. Check actual generated AND
RUNDIR nuopc.runconfig scol_{lat,lon} agree with actual fsurdat + met.

--self-test             pure checks; no I/O
--check                 READ ONLY source & destination-absence for all 4
--stage --site all       CREATE 4 fixed cases + preview; NO Slurm
        --confirm FIX_FOUR_AMERIFLUX_PTS_FROM_SURFACE_PREVIEW_NO_SLURM
--stage --site SITE      CREATE one case, if others already created
        --confirm FIX_FOUR_AMERIFLUX_PTS_FROM_SURFACE_PREVIEW_NO_SLURM
--verify                READ ONLY four new case manifests/runtime
--submit-ca-tp4          ONE-TIME REAL Slurm AD5 smoke only for fixed CA-TP4
        --confirm SUBMIT_FIXED_CA_TP4_ONE_AD5_SKIP_PREVIEW
WARNING: NEVER rerun a failed --stage on an existing partial clone or retry
failed/uncertain --submit. Prior CA-TP4 failure and Stage18 receipt unchanged.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from netCDF4 import Dataset
import numpy as np

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=B/"CTSM"
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
ROOT=B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10"
D=ROOT/"LaneA_Stage20_correct_PTS_from_surface"
ACK_STAGE="FIX_FOUR_AMERIFLUX_PTS_FROM_SURFACE_PREVIEW_NO_SLURM"
ACK_SUBMIT="SUBMIT_FIXED_CA_TP4_ONE_AD5_SKIP_PREVIEW"
HELP=Path(__file__).resolve().with_name("08_CA_TP4_create_AD5_CIME_case_preview_no_slurm.py")
HELP_BLOB="38cb1acbfd6502b3a9d49b5249bf7e9c006d1528"
SITES={
"CA-TP4":("CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5", "CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5",ROOT/"CA-TP4/stage12_CA_TP4_UTC_V2_AD5_PREVIEW_ATTEMPT.json",2002,2023,372.58),
"BR-Ma2":("BR-Ma2_AMF_FIXNC_AD400_UTC_AD5", "BR-Ma2_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",ROOT/"LaneA_Stage16_CIME_preview/BR-Ma2_attempt.json",1999,2016,367.79),
"CA-Ca3":("CA-Ca3_AMF_FIXNC_AD400_UTC_AD5", "CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",ROOT/"LaneA_Stage16_CIME_preview/CA-Ca3_attempt.json",2001,2024,370.57),
"CA-LP1":("CA-LP1_AMF_FIXNC_AD400_UTC_AD5", "CA-LP1_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",ROOT/"LaneA_Stage16_CIME_preview/CA-LP1_attempt.json",2007,2024,382.90),
}
FATES={"use_fates":".true.","use_fates_sp":".false.",
       "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
       "use_cn":".false.","spinup_state":"2"}
VARS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
      "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
      "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}

def abort(s):raise RuntimeError(str(s))
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as fd:
  for part in iter(lambda:fd.read(1048576),b""):h.update(part)
 return h.hexdigest()
def load(p):
 if not p.is_file():abort("Expected completed receipt missing "+str(p))
 return json.loads(p.read_text(encoding="utf8"))
def run_cmd(argv,cwd=None,timeout=180):
 p=subprocess.run([str(x) for x in argv],cwd=cwd,text=True,
                  capture_output=True,check=False,timeout=timeout)
 if p.returncode:
  abort("COMMAND FAILED "+repr(argv)+" RETURN "+str(p.returncode)+
        "\nOUT "+p.stdout[-2300:]+"\nERR "+p.stderr[-2300:])
 return p.stdout.strip()
def q(case,key):return run_cmd([case/"xmlquery",key,"--value"],cwd=case,timeout=90)
def ch(case,key,value):return run_cmd([case/"xmlchange",key+"="+str(value)],cwd=case,timeout=90)
def field(data,key):
 v=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",data)
 if len(v)>1:abort("Duplicate namelist key "+key)
 return v[0].strip().strip("'\"").strip() if v else None
def coords(surf):
 with Dataset(surf) as ds:
  lat=ds.variables["LATIXY"]
  lon=ds.variables["LONGXY"]
  if lat.size!=1 or lon.size!=1:abort("Not exactly 1PT surface "+str(surf))
  a=float(np.ma.asarray(lat[:]).ravel()[0])
  b=float(np.ma.asarray(lon[:]).ravel()[0])%360
  if not (-90<=a<=90) or not (0<=b<360):abort("Invalid surface lat/lon")
 return a,b
def err(a,b):
 return max(abs(a[0]-b[0]),abs(((a[1]-b[1]+180)%360)-180))
def coupled(cfg):
 result={}
 for key in ("scol_lat","scol_lon","single_column_lnd_domainfile"):
  found=re.findall(r"(?im)^\s*"+key+r"\s*=\s*(.*?)\s*$",cfg)
  if len(found)!=1:abort("NUOPC missing/duplicated "+key)
  result[key]=found[0].strip().strip("'\"")
 return result
def stream(case,site,first,last):
 root=ET.parse(case/"CaseDocs/datm.streams.xml").getroot()
 found=[e for e in root.iter("stream_info") if e.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(found)!=1:abort(site+": no unique user meteorological CDEPS stream")
 v=found[0]
 for k,w in (("taxmode","cycle"),("tintalgo","linear"),("offset","0"),
             ("year_first",str(first)),("year_last",str(last)),("year_align",str(first))):
  el=v.find(k)
  if el is None or (el.text or "").strip()!=w:abort(site+" CDEPS wrong "+k)
 mapped={}
 for el in v.find("datavars"):
  tok=(el.text or "").split()
  if len(tok)!=2 or tok[0] in mapped:abort("CDEPS variable mapping malformed")
  mapped[tok[0]]=tok[1]
 if any(mapped.get(k)!=u for k,u in VARS.items()):
  abort(site+": mapped meteorological variable mismatch")
 files=[Path((e.text or "").strip()) for e in v.find("datafiles")]
 if len(files)!=last-first+1:abort(site+": expected original UTC year count")
 for yr,p in zip(range(first,last+1),files):
  if p.stem!=str(yr) or site not in str(p) or not p.is_file():
   abort(site+": missing/wrong-year UTC forcing "+str(p))
 return files

def model_data(site,case,old_receipt):
 old,new,receipt,first,last,co2=SITES[site]
 if not case.is_dir():abort(site+": source case absent "+str(case))
 if load(receipt).get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED":
  abort(site+": original Stage12/16 preview not verified")
 source_doc=load(receipt)
 if site=="CA-TP4":
  lhash=source_doc["generated_lnd_in_sha256"]
  dhash=source_doc["generated_datm_stream_sha256"]
 else:
  lhash=source_doc["result"]["lnd_in_sha256"]
  dhash=source_doc["result"]["datm_stream_sha256"]
 a=case/"CaseDocs/lnd_in"
 b=case/"CaseDocs/datm.streams.xml"
 if digest(a)!=lhash or digest(b)!=dhash:
  abort(site+": original CaseDocs SHA differed from audited receipt")
 if (case/"env_case.xml").read_bytes()!=(case/"LockedFiles/env_case.xml").read_bytes():
  abort(site+": original CIME CTSM lock not restored")
 t=a.read_text(encoding="utf8")
 for k,v in FATES.items():
  if field(t,k)!=v:abort(site+": source FATES flag drift "+k)
 sf=field(t,"fsurdat")
 surf=Path(sf) if sf else None
 if not surf or site not in str(surf) or not surf.is_file():
  abort(site+": original site surface missing")
 p=coords(surf)
 files=stream(case,site,first,last)
 with Dataset(files[0]) as nc:
  point=(float(np.asarray(nc.variables["LATIXY"][:]).ravel()[0]),
         float(np.asarray(nc.variables["LONGXY"][:]).ravel()[0])%360)
  if err(p,point)>0.00001:abort(site+": UTC forcing and site surface differ")
 for key,value in (("RUN_TYPE","startup"),("STOP_N","5"),("REST_N","5"),
                   ("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","on")):
  if q(case,key).lower()!=value.lower():abort(site+": original CIME AD5 "+key+" wrong")
 if abs(float(q(case,"CCSM_CO2_PPMV"))-co2)>0.03:
  abort(site+": original fixed CO2 changed")
 if q(case,"BUILD_COMPLETE").lower()!="true":
  abort(site+": proven compiled case BUILD_COMPLETE false")
 exe=Path(q(case,"EXEROOT"))/"cesm.exe"
 if not exe.is_file():abort("Shared FATES executable missing")
 oldp=(float(q(case,"PTS_LAT")),float(q(case,"PTS_LON"))%360)
 print("PRECHECK",site,"surface",p,"old PTS",oldp,"mismatch degrees",err(p,oldp),
       "source UTC years",len(files),"fixed CO2",co2,"EXE",exe,flush=True)
 return {"surface":surf,"point":p,"files":files,"exe":exe,
         "original_lnd_sha256":lhash,"original_datm_sha256":dhash,
         "original_case":case,"old_point":oldp}
def helper():
 if not HELP.is_file():abort("Pinned FATES private buildnml helper missing")
 data=HELP.read_bytes()
 blob=b"blob "+str(len(data)).encode()+b"\0"+data
 if hashlib.sha1(blob).hexdigest()!=HELP_BLOB:
  abort("Existing original Stage08 helper version changed")
 spec=importlib.util.spec_from_file_location("stage20_CIME_proven_helper",HELP)
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 mod.overlay_test()
 return mod

def paths(site):
 src,target,record,first,last,co2=SITES[site]
 return (B/"cases"/target,OUT/target/"run",OUT/"archive"/target,
         D/(site+"_new_PTS_case_attempt.json"))
def ensure_new(site):
 for p in paths(site):
  if p.exists() or p.is_symlink():
   abort(site+": existing/partial corrected case/output. NEVER OVERWRITE: "+str(p))
def validate(site,data,receipt=None):
 old,target,source,first,last,co2=SITES[site]
 case,rundir,archive,attempt=paths(site)
 point=data["point"]
 if not case.is_dir() or q(case,"CASE")!=target:abort(site+": independent cloned case identity wrong")
 for key,val in (("RUNDIR",str(rundir)),("DOUT_S_ROOT",str(archive)),
                 ("PTS_DOMAINFILE","UNSET"),
                 ("STOP_N","5"),("REST_N","5"),("RESUBMIT","0"),
                 ("CLM_ACCELERATED_SPINUP","on")):
  if q(case,key).lower()!=val.lower():abort(site+": new CIME "+key+" wrong")
 p=(float(q(case,"PTS_LAT")),float(q(case,"PTS_LON"))%360)
 if err(p,point)>1e-5:abort(site+": new CIME PTS_LAT/LON not site surface")
 if (case/"env_case.xml").read_bytes()!=(case/"LockedFiles/env_case.xml").read_bytes():
  abort(site+": new clone original CTSM env_case lock mismatch")
 land=case/"CaseDocs/lnd_in"
 met=case/"CaseDocs/datm.streams.xml"
 if not land.is_file() or not met.is_file():abort(site+": generated CaseDocs missing")
 text=land.read_text(encoding="utf8")
 if field(text,"fsurdat")!=str(data["surface"]):
  abort(site+": generated land surface changed")
 for k,v in FATES.items():
  if field(text,k)!=v:abort(site+": generated land FATES flag "+k+" changed")
 if field(text,"finidat") not in (None,""):
  abort(site+": new AD5 should be cold start")
 # The new CASE identity can legitimately alter cosmetic lnd_in fields.
 # Preserve substantive land science, forcing and ancillary streams instead
 # of requiring exact byte equality to the old case's entire generated file.
 oldland=(data["original_case"]/"CaseDocs/lnd_in").read_text(encoding="utf8")
 for k in ("fates_paramfile","hist_fincl1","use_crop","co2_ppmv",
           "fates_spitfire_mode","use_fates","use_fates_sp",
           "use_fates_fixed_biogeog","use_fates_nocomp","spinup_state","fsurdat"):
  if field(text,k)!=field(oldland,k):
   abort(site+": cloned generated land science changed "+k)
 def semantic(e):
  return (e.tag,tuple(sorted(e.attrib.items())),(e.text or "").strip(),
          tuple(semantic(k) for k in e))
 if semantic(ET.parse(met).getroot())!=semantic(
         ET.parse(data["original_case"]/"CaseDocs/datm.streams.xml").getroot()):
  abort(site+": generated DATM stream semantics differ from proven source case")
 files=stream(case,site,first,last)
 if files!=data["files"]:abort(site+": new CDEPS points at different forcing data")
 checks={}
 for name,file in (("CaseDocs",case/"CaseDocs/nuopc.runconfig"),
                  ("RUNDIR",rundir/"nuopc.runconfig")):
  if not file.is_file():abort(site+": missing effective "+name+" nuopc.runconfig")
  vals=coupled(file.read_text(encoding="utf8"))
  p=(float(vals["scol_lat"]),float(vals["scol_lon"])%360)
  if err(p,point)>0.0001:abort(site+": "+name+" coupler scol coords mismatch with surface")
  if vals["single_column_lnd_domainfile"]!="UNSET":
   abort(site+": unexpected nearest-neighbor point domainfile path")
  print("EFFECTIVE COUPLER PASS",site,name,"scol_lat/lon",p,"MATCH SITE SURFACE",flush=True)
  checks[name+"_nuopc_sha256"]=digest(file)
 if not (rundir/"lnd_in").is_file() or digest(rundir/"lnd_in")!=digest(land):
  abort(site+": live runtime FATES AD namelist changed")
 if not (rundir/"datm.streams.xml").is_file() or digest(rundir/"datm.streams.xml")!=digest(met):
  abort(site+": live runtime UTC forcing stream changed")
 if (Path(q(case,"EXEROOT"))/"cesm.exe")!=data["exe"]:
  abort(site+": new case not reusing original FATES binary")
 if abs(float(q(case,"CCSM_CO2_PPMV"))-co2)>0.03:
  abort(site+": fixed source-year CO2 changed")
 if q(case,"BUILD_COMPLETE").lower()!="true":abort(site+": new CIME case not built")
 return {"case":str(case),"surface":str(data["surface"]),"PTS_LAT":point[0],
    "PTS_LON":point[1],"fixed_global_co2_ppm":co2,
    "source_lnd_sha256":data["original_lnd_sha256"],
    "source_datm_sha256":data["original_datm_sha256"],
    "nuopc":checks,"no_model_submitted":True}

def create(site,data,m):
 old,target,receipt,first,last,co2=SITES[site]
 case,rundir,archive,attempt=paths(site)
 ensure_new(site)
 D.mkdir(parents=True,exist_ok=True)
 with attempt.open("x",encoding="utf8") as fd:
  json.dump({"site":site,"stage":20,"status":"ATTEMPTED_UNCERTAIN",
             "old_case":str(B/"cases"/old),"new_case":str(case),
             "PTS_LAT":data["point"][0],"PTS_LON":data["point"][1],
             "original_FATES_case_preserved":True,"slurm_submitted":False,
             "created_utc":datetime.now(timezone.utc).isoformat()},fd,indent=2)
  fd.write("\n")
 print("ONE-TIME FIX ATTEMPT",site,attempt,flush=True)
 run_cmd([CTSM/"cime/scripts/create_clone","--case",case,
          "--clone",B/"cases"/old,"--keepexe"],
         cwd=CTSM/"cime/scripts",timeout=480)
 if not case.is_dir() or q(case,"CASE")!=target:
  abort(site+": clone did not produce requested independent case")
 updates={"RUNDIR":str(rundir),"DOUT_S_ROOT":str(archive),
          "PTS_LAT":str(data["point"][0]),"PTS_LON":str(data["point"][1]),
          "PTS_DOMAINFILE":"UNSET","RUN_TYPE":"startup","CONTINUE_RUN":"FALSE",
          "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears",
          "REST_N":"5","RESUBMIT":"0","DOUT_S":"TRUE"}
 for key,val in updates.items():ch(case,key,val)
 if not (case/".case.run").is_file():
  run_cmd([case/"case.setup"],cwd=case,timeout=300)
 env=case/"env_case.xml";lock=case/"LockedFiles/env_case.xml"
 if not lock.is_file() or env.read_bytes()!=lock.read_bytes():
  abort(site+": CIME lock already differs before private preview")
 snapshot=env.read_bytes()
 attrs={x.attrib.get("id"):x.attrib.get("value") for x in ET.parse(lock).iter("entry")}
 if attrs.get("COMP_ROOT_DIR_LND")!="$SRCROOT" or \
    Path(q(case,"COMP_ROOT_DIR_LND")).resolve()!=CTSM.resolve():
  abort(site+": original CTSM source lock invalid")
 try:
  ch(case,"COMP_ROOT_DIR_LND",str(m.OVERLAY))
  run_cmd([case/"preview_namelists"],cwd=case,timeout=650)
 finally:
  ch(case,"COMP_ROOT_DIR_LND","$SRCROOT")
  if env.read_bytes()!=snapshot or lock.read_bytes()!=snapshot:
   abort(site+": critical CIME private AD lock not restored")
 verified=validate(site,data)
 state=load(attempt)
 state.update({"status":"PREVIEW_VERIFIED_NOT_SUBMITTED",
     "validated_runtime_geometry":True,
     "old_source_case_is_preserved":True,
     "case_runtime":verified,
     "no_model_submitted":True,
     "validated_utc":datetime.now(timezone.utc).isoformat()})
 attempt.write_text(json.dumps(state,indent=2)+"\n",encoding="utf8")
 print("STAGE20 SUCCESS",site,"NEW CORRECTED POINT CIME CASE PREVIEW, NO SLURM",case,flush=True)

def check(sites,m):
 all_data={}
 for site in sites:
  old,_,rec,first,last,co2=SITES[site]
  src=B/"cases"/old
  d=model_data(site,src,rec)
  all_data[site]=d
  ensure_new(site)
 print("STAGE20 READ-ONLY PREFLIGHT PASS",len(sites),"case(s), no files created")
 return all_data

def verify():
 for site in SITES:
  old,_,rec,first,last,co2=SITES[site]
  data=model_data(site,B/"cases"/old,rec)
  newcase,rundir,archive,attempt=paths(site)
  state=load(attempt)
  if state.get("status")!="PREVIEW_VERIFIED_NOT_SUBMITTED":
   abort(site+": fixed case not yet successfully verified")
  match=validate(site,data)
  if state["case_runtime"]["nuopc"]!=match["nuopc"]:
   abort(site+": new runtime NUOPC config changed after preview")
  print("READ-ONLY VERIFIED",site,"NO SUBMISSION IMPLIED",flush=True)
 print("STAGE20 FOUR-SITE CORRECTED PTS CASES 4/4 VERIFIED")

def one_submit():
 site="CA-TP4"
 old,_,rec,first,last,co2=SITES[site]
 oldcase=B/"cases"/old
 data=model_data(site,oldcase,rec)
 case,rundir,archive,attempt=paths(site)
 state=load(attempt)
 if state.get("status")!="PREVIEW_VERIFIED_NOT_SUBMITTED":
  abort("New CA-TP4 was not successfully previewed")
 validate(site,data)
 stamp=D/"CA-TP4_PTS_V3_AD5_SUBMISSION_ATTEMPT.json"
 if stamp.exists():abort("CA-TP4 Stage20 submit already attempted, DO NOT RETRY")
 # Do not start the new STARTUP if someone manually submitted or wrote restart.
 if any(rundir.glob("rpointer*")) or any(rundir.glob("*.r.*.nc")):
  abort("New CA-TP4 run directory contains restart artifacts; refuse duplicate startup")
 cs=case/"CaseStatus"
 if cs.is_file():
  case_status=cs.read_text(encoding="utf8",errors="replace")
  if any(item in case_status for item in (
          "case.submit starting", "model execution starting", "case.run starting")):
   abort("Corrected case has prior CIME submission/start record; do not duplicate")
 from subprocess import run
 cli=run([str(case/"case.submit"),"--help"],cwd=case,capture_output=True,
         text=True,check=False,timeout=75)
 if cli.returncode not in (0,1) or "--skip-preview-namelist" not in (cli.stdout+cli.stderr):
  abort("Actual CIME case.submit does not prove --skip-preview-namelist support")
 slurm=run(["squeue","-h","-u","ly3n24","-o","%j|%i|%T"],
           capture_output=True,text=True,timeout=30,check=False)
 if slurm.returncode:abort("Slurm queue status unavailable")
 target=case.name
 if any(target in line for line in slurm.stdout.splitlines()):
  abort("The corrected model already appears in Slurm, stop")
 # A ledger is created *before* submitting so a disconnect cannot cause a
 # second blind submission. Check sacct before manual recovery.
 with stamp.open("x",encoding="utf8") as f:
  json.dump({"site":site,"case":str(case),"state":"SUBMISSION_ATTEMPTED_UNCERTAIN",
     "model_success_confirmed":False,"previous_failed_case_preserved":True,
     "command":"./case.submit --skip-preview-namelist",
     "utc":datetime.now(timezone.utc).isoformat()},f,indent=2)
  f.write("\n")
 print("ONCE-ONLY REAL MODEL JOB SUBMIT:",case,flush=True)
 p=run([str(case/"case.submit"),"--skip-preview-namelist"],cwd=case,
       capture_output=True,text=True,check=False,timeout=650)
 print("=== CIME OUTPUT ===\n",p.stdout[-7000:],"\n",p.stderr[-4000:],flush=True)
 if p.returncode:
  abort("CIME submit returned "+str(p.returncode)+"; inspect Slurm/CaseStatus; DO NOT retry")
 obj=load(stamp)
 obj["state"]="CIME_SUBMIT_RETURNED_SUCCESS_MODEL_UNVERIFIED"
 obj["output_tail"]=(p.stdout+"\n"+p.stderr)[-4000:]
 obj["utc_returned"]=datetime.now(timezone.utc).isoformat()
 stamp.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf8")
 print("CA-TP4 PTS FIXED AD5 SUBMITTED, MODEL SUCCESS NOT YET VERIFIED; MONITOR CASESTATUS/SLURM")

def selftest():
 assert len(SITES)==4
 assert err((42.7102,279.6426),(42.7102,-80.3574))<1e-9
 assert err((42.7102,279.6426),(46.81533,9.85591))>4
 assert "use_fates_nocomp" in FATES
 print("SELF-TEST PASS 4 new case IDs, strict surface PTS coordinates, no existing cases overwritten")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--stage",action="store_true")
 g.add_argument("--verify",action="store_true")
 g.add_argument("--submit-ca-tp4",action="store_true")
 p.add_argument("--site",choices=["all",*SITES],default="all")
 p.add_argument("--confirm")
 args=p.parse_args()
 if args.self_test:selftest();return
 if args.stage and args.confirm!=ACK_STAGE:
  p.error("--stage requires --confirm "+ACK_STAGE)
 if args.submit_ca_tp4 and args.confirm!=ACK_SUBMIT:
  p.error("--submit-ca-tp4 requires --confirm "+ACK_SUBMIT)
 if (args.check or args.verify) and args.confirm:
  p.error("--check and --verify are strictly read-only")
 if not args.stage and args.site!="all":p.error("--site only for --stage")
 if args.check:
  check(list(SITES),helper());return
 if args.stage:
  m=helper()
  sites=list(SITES) if args.site=="all" else [args.site]
  inputs=check(sites,m)
  for site in sites:create(site,inputs[site],m)
  print("STAGE20 COMPLETE",len(sites),"NEW point-corrected case(s), NO Slurm")
 elif args.verify:verify()
 else:one_submit()
if __name__=="__main__":main()
