#!/usr/bin/env python3
"""Stage18 CA-TP4 UTC-V2 one-time AD5 FATES technical smoke submission.

Only the ALREADY PREVIEWED CA-TP4 case. The other 3 Stage16 LaneA cases
MUST remain unsubmitted. Reuses exact verified effective CaseDocs/RUNDIR
lnd_in and CDEPS stream; NEVER regenerates model inputs. The verified
private FATES AD buildnml overlay was restored to original CTSM, so submit
MUST use ./case.submit --skip-preview-namelist (CIME documented option).

--self-test pure static case guards; NO I/O mutations
--check     READ-ONLY inspect 5yr AD config/runtime input/queue, no writes
--submit --confirm SUBMIT_ONE_CA_TP4_AD5_TECHNICAL_SMOKE_SKIP_PREVIEW
            ONE-TIME create non-overwritable attempt ledger, then submit
            CIME only once; CIME may submit run + dependent st_archive.
            If ANY error occurs, DO NOT retry blindly. State may be
            ATTEMPTED_UNCERTAIN with model job already queued.

No AD395, Normal400, or other sites launched. This is a COMPUTATIONAL smoke
only, not scientific validation of the existing ZBOT=28m, forest PFT 93/7,
global gridded soil, coupler point grid/solar geometry, or flux benchmark.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
NAME="CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"
CASE=ROOT/"cases"/NAME
EXP=ROOT/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
SOURCE=EXP/"stage12_CA_TP4_UTC_V2_AD5_PREVIEW_ATTEMPT.json"
OUTPUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUN=OUTPUT/NAME/"run"
ARCH=OUTPUT/"archive"/NAME
ATTEMPT=EXP/"stage18_CA_TP4_ONE_AD5_SUBMISSION_ATTEMPT.json"
CONFIRM="SUBMIT_ONE_CA_TP4_AD5_TECHNICAL_SMOKE_SKIP_PREVIEW"
FS_FIELDS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
           "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
           "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}

def stop(msg):raise RuntimeError(str(msg))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()
def readjson(path):
 if not path.is_file():stop("Missing exact pinned case receipt "+str(path))
 return json.loads(path.read_text(encoding="utf-8"))
def utc():return datetime.now(timezone.utc).isoformat()
def xml_vals():
 out={}
 for nm in ("env_case.xml","env_run.xml","env_build.xml"):
  f=CASE/nm
  if not f.is_file():stop("Actual CIME XML missing "+str(f))
  for x in ET.parse(f).iter():
   if x.tag.split("}")[-1]=="entry":
    out[x.attrib.get("id")]=x.attrib.get("value","")
 return out
def nml(t,k):
 vals=re.findall(r"(?im)^\s*"+re.escape(k)+r"\s*=\s*([^\r\n!]*)",t)
 if len(vals)>1:stop("Duplicate FATES namelist "+k)
 return vals[0].strip().strip("'\"").strip() if vals else None
def effective_met():
 root=ET.parse(CASE/"CaseDocs/datm.streams.xml").getroot()
 a=[e for e in root.iter("stream_info") if e.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(a)!=1:stop("CA-TP4 CDEPS meteorology stream not unique")
 stream=a[0]
 for k,v in (("year_first","2002"),("year_last","2023"),
             ("year_align","2002"),("taxmode","cycle"),
             ("tintalgo","linear"),("offset","0")):
  e=stream.find(k)
  if e is None or (e.text or "").strip()!=v:
   stop("Generated CA-TP4 CDEPS met year/UTC setting wrong "+k)
 varmap={}
 for e in stream.find("datavars"):
  parts=(e.text or "").split()
  if len(parts)!=2 or parts[0] in varmap:stop("Duplicate generated met variable")
  varmap[parts[0]]=parts[1]
 if any(varmap.get(k)!=v for k,v in FS_FIELDS.items()):
  stop("Effective CDEPS source-to-model variable map changed")
 met=[Path((e.text or "").strip()) for e in stream.find("datafiles")]
 if len(met)!=22 or len(set(met))!=22:
  stop("Generated CA-TP4 UTC must have 22 annual paths")
 for yr,f in zip(range(2002,2024),met):
  if f.stem!=str(yr) or "stage11_CA_TP4_DATM_UTC_20261025T080240825734395Z" not in str(f) or not f.is_file():
   stop("CA-TP4 source site/year UTC file missing "+str(f))
 return met
def queue():
 try:
  p=subprocess.run(["squeue","-h","-u","ly3n24","-o","%j|%i|%T"],
                   capture_output=True,text=True,check=False,timeout=25)
 except (OSError,subprocess.TimeoutExpired) as e:
  stop("Cannot prove no existing CA-TP4 job via squeue: "+str(e))
 if p.returncode:stop("squeue unavailable to establish single job safety")
 hits=[]
 for line in p.stdout.splitlines():
  if NAME in line:hits.append(line)
 if hits:stop("CA-TP4 job already visible in Slurm; do not duplicate: "+repr(hits))
 print("SLURM QUEUE PASS: no active CA-TP4 UTC-V2 AD5 job")
def cli_help():
 p=CASE/"case.submit"
 if not p.is_file():stop("CIME case.submit tool missing")
 result=subprocess.run([str(p),"--help"],cwd=CASE,capture_output=True,
                       text=True,check=False,timeout=75)
 if result.returncode not in (0,1) or "--skip-preview-namelist" not in result.stdout+result.stderr:
  stop("Installed CIME submit does not prove skip-preview-namelist option")
 print("CIME LOCAL case.submit --skip-preview-namelist SUPPORT PASS")
def audit():
 if not CASE.is_dir():stop("CA-TP4 UTC-V2 AD5 case not created")
 receipt=readjson(SOURCE)
 if (receipt.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or
     receipt.get("model_jobs_submitted") is not False or
     receipt.get("ready_to_submit_AD5") is not False):
  stop("Stage12 case was not an approved no-submission preview")
 lnd=CASE/"CaseDocs/lnd_in"
 datm=CASE/"CaseDocs/datm.streams.xml"
 expectedlnd=receipt["generated_lnd_in_sha256"]
 expecteddatm=receipt["generated_datm_stream_sha256"]
 if sha(lnd)!=expectedlnd or sha(datm)!=expecteddatm:
  stop("Generated CIME CaseDocs SHA changed after Stage12")
 if (CASE/"env_case.xml").read_bytes()!=(CASE/"LockedFiles/env_case.xml").read_bytes():
  stop("CIME env_case.xml lock differs; private buildnml overlay not restored")
 cfg=xml_vals()
 desired={"CASE":NAME,"RUN_TYPE":"startup","RUN_STARTDATE":"2002-01-01",
  "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears",
  "REST_N":"5","RESUBMIT":"0","CONTINUE_RUN":"FALSE",
  "CLM_FORCE_COLDSTART":"on","CLM_ACCELERATED_SPINUP":"on",
  "CALENDAR":"NO_LEAP","ATM_NCPL":"48","DATM_MODE":"1PT",
  "DATM_YR_START":"2002","DATM_YR_END":"2023","DATM_YR_ALIGN":"2002",
  "CLM_CO2_TYPE":"constant","BUILD_COMPLETE":"TRUE",
  "COMP_ROOT_DIR_LND":"$SRCROOT","DOUT_S":"TRUE",
  "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH)}
 for k,v in desired.items():
  if cfg.get(k,"").lower()!=v.lower():
   stop("CIME before pilot run has unexpected XML "+k+"="+str(cfg.get(k)))
 if abs(float(cfg.get("CCSM_CO2_PPMV","nan"))-372.58)>0.02:
  stop("CA-TP4 fixed CO2 baseline is not 372.58 ppm")
 if not (Path(cfg["EXEROOT"])/"cesm.exe").is_file():
  stop("FATES compiled executable missing")
 raw=lnd.read_text(encoding="utf8")
 for k,v in (("spinup_state","2"),("use_fates",".true."),
             ("use_fates_sp",".false."),
             ("use_fates_fixed_biogeog",".true."),
             ("use_fates_nocomp",".true."),("use_cn",".false.")):
  if nml(raw,k)!=v:stop("CaseDocs land mode changed "+k)
 if nml(raw,"finidat") not in (None,"") or nml(raw,"reseed_dead_plants") is not None:
  stop("AD5 model must be FATES AD startup, no existing finidat")
 surface=nml(raw,"fsurdat")
 if not surface or not Path(surface).is_file() or "CA-TP4" not in surface:
  stop("Missing site-specific FATES land surface")
 met=effective_met()
 if not RUN.is_dir():stop("Actual site RUNDIR does not exist")
 if not (RUN/"lnd_in").is_file() or sha(RUN/"lnd_in")!=expectedlnd:
  stop("Runtime FATES lnd_in differs from validated Stage12 preview")
 if not (RUN/"datm_in").is_file() or not (RUN/"datm.streams.xml").is_file():
  stop("Runtime CDEPS DATM input files missing")
 if sha(RUN/"datm.streams.xml")!=expecteddatm:
  stop("Runtime CDEPS DATM XML differs from verified CaseDocs")
 for pattern in ("rpointer.*","*.r.*.nc"):
  if list(RUN.glob(pattern)):
   stop("Unexpected existing restart files; refuse STARTUP pilot")
 if not (CASE/".case.run").is_file():
  stop("CIME hidden batch payload missing")
 if ATTEMPT.exists() or ATTEMPT.is_symlink():
  stop("CA-TP4 Stage18 was already attempted; inspect ledger, queue and case statuses; DO NOT resubmit")
 cli_help()
 queue()
 print("STAGE18 READ-ONLY AUDIT PASS: one CA-TP4 5-year FATES AD startup; 22 UTC files, fixed CO2 372.58")
 print("RUNTIME lnd_in + datm.streams match pinned Stage12 SHA, no preview regeneration")
 print("OTHER THREE LANE-A SITES NOT SUBMITTED BY THIS SCRIPT")
 return {"case":str(CASE),"case_docs_lnd_sha256":expectedlnd,
         "case_docs_datm_sha256":expecteddatm,
         "stage12_receipt_sha256":sha(SOURCE),
         "slurm_hidden_run_script_sha256":sha(CASE/".case.run"),
         "met_years":len(met),"co2_ppm":372.58}
def submit(info):
 state={"stage":18,"site":"CA-TP4","state":"ATTEMPTED_UNCERTAIN",
        "submission_intent":"ONE_INITIAL_5YR_FATES_AD_SMOKE",
        "submission_mode":"CIME_CASE_SUBMIT_SKIP_PREVIEW_NAMELIST",
        "science_release":False,"model_success_confirmed":False,
        "job_ids_verified":False,"no_other_site_submissions":True,
        "created_utc":utc(),**info}
 with ATTEMPT.open("x",encoding="utf-8") as f:
  json.dump(state,f,indent=2);f.write("\n")
 print("STAGE18 NON-RETRY ATTEMPT RECEIPT CREATED:",ATTEMPT,flush=True)
 print("SUBMITTING ONLY CA-TP4: ./case.submit --skip-preview-namelist",flush=True)
 try:
  proc=subprocess.run([str(CASE/"case.submit"),"--skip-preview-namelist"],
                      cwd=CASE,check=False,capture_output=True,text=True,timeout=540)
  result=proc.stdout+"\n"+proc.stderr
  print("=== CIME SUBMIT STDOUT/STDERR ===")
  print(result[-18000:],flush=True)
  if proc.returncode:
   stop("CIME submit returned "+str(proc.returncode)+
        ". Attempt ledger remains UNCERTAIN. DO NOT re-run automatically.")
  # Numeric IDs reported by CIME are NOT blindly assumed to be actual RUN IDs:
  # subsequent sacct/squeue/CaseStatus checks are the source of truth.
  jobids=re.findall(r"(?i)(?:submitted job|job id|jobid)\s*[:=# ]+\s*(\d{6,})",result)
  state.update({"state":"SUBMISSION_COMMAND_RETURNED_SUCCESS_UNVERIFIED_MODEL",
                "CIME_submit_returncode":proc.returncode,
                "reported_job_ids":sorted(set(jobids)),
                "job_ids_verified":False,
                "model_success_confirmed":False,
                "CIME_submit_output_tail":result[-4000:],
                "submitted_utc":utc()})
  ATTEMPT.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
  print("STAGE18 CIME SUBMIT RETURNED SUCCESS; MODEL/SLURM STATUS NOT YET CONFIRMED")
  print("REPORTED JOB IDS (unverified):",sorted(set(jobids)))
  print("CASESTATUS:",CASE/"CaseStatus")
  print("FOLLOW-UP: squeue -u ly3n24 ; sacct -u ly3n24 -S today --format=JobID,JobName,State,Elapsed,ExitCode")
  print("DO NOT SUBMIT AGAIN; monitor run/archive and verify model restart.")
 except BaseException:
  print("STAGE18 UNCERTAIN — check Slurm/CaseStatus and attempt receipt; NEVER blind rerun",flush=True)
  raise

def selftest():
 assert NAME=="CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"
 assert len(FS_FIELDS)==8
 assert "SUBMIT_ONE_CA_TP4" in CONFIRM
 print("SELF-TEST PASS: one fixed CA-TP4 UTC-V2 AD5 only; no rerun; no other site")

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 grp=ap.add_mutually_exclusive_group(required=True)
 grp.add_argument("--self-test",action="store_true")
 grp.add_argument("--check",action="store_true")
 grp.add_argument("--submit",action="store_true")
 ap.add_argument("--confirm")
 a=ap.parse_args()
 if a.self_test:selftest();return
 if a.submit and a.confirm!=CONFIRM:
  ap.error("--submit requires --confirm "+CONFIRM)
 if a.check and a.confirm:ap.error("--check does not accept confirmation")
 verified=audit()
 if a.check:return
 submit(verified)
if __name__=="__main__":main()
