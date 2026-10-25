#!/usr/bin/env python3
"""Read-only Stage17: four existing AmeriFlux FATES FIXNC AD5 CIME runtime gates.

CIME case.submit regenerates component namelists by default. Prior FATES AD
namelist previews used a PRIVATE CTSM correction and then restored the
shared original CTSM lock. A normal case.submit could regenerate an
incompatible lnd_in. We verify that this local CIME version supports
--skip-preview-namelist before anyone submits the FIRST five-year smoke.

Checks live RUNDIR/lnd_in, generated CaseDocs hashes, 1PT 8-field CDEPS
stream, years, CO2, executable, FATES spinup_state 2, locked env_case and
case.submit / case.run help output. No meteorology QC, files written,
model code changes, Slurm or submission.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
PROJ=ROOT/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10"
RUNROOT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
SPECS={
"CA-TP4":("CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5",2002,2023,372.58,22,PROJ/"CA-TP4/stage12_CA_TP4_UTC_V2_AD5_PREVIEW_ATTEMPT.json"),
"BR-Ma2":("BR-Ma2_AMF_FIXNC_AD400_UTC_AD5",1999,2016,367.79,18,PROJ/"LaneA_Stage16_CIME_preview/BR-Ma2_attempt.json"),
"CA-Ca3":("CA-Ca3_AMF_FIXNC_AD400_UTC_AD5",2001,2024,370.57,24,PROJ/"LaneA_Stage16_CIME_preview/CA-Ca3_attempt.json"),
"CA-LP1":("CA-LP1_AMF_FIXNC_AD400_UTC_AD5",2007,2024,382.90,18,PROJ/"LaneA_Stage16_CIME_preview/CA-LP1_attempt.json")}
MAP={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
     "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
     "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}

def stop(msg):raise RuntimeError(str(msg))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def read(p):
 if not p.is_file():stop("Source receipt missing "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))
def xml(case):
 vals={}
 for f in ("env_case.xml","env_run.xml","env_build.xml"):
  p=case/f
  if not p.is_file():stop("Missing CIME case XML "+str(p))
  for e in ET.parse(p).iter():
   if e.tag.split("}")[-1]=="entry":vals[e.attrib.get("id")]=e.attrib.get("value","")
 return vals
def key(raw,k):
 vals=re.findall(r"(?im)^\s*"+re.escape(k)+r"\s*=\s*([^\r\n!]*)",raw)
 if len(vals)>1:stop("Duplicate effective land key "+k)
 return vals[0].strip().strip("'\"").strip() if vals else None
def helpcheck(case,p):
 x=case/p
 if not x.is_file():stop("Missing local CIME CLI "+str(x))
 y=subprocess.run([str(x),"--help"],cwd=case,capture_output=True,text=True,timeout=75,check=False)
 if y.returncode not in (0,1) or "--skip-preview-namelist" not in y.stdout+y.stderr:
  stop("Local "+p+" skip-preview option not verified. DO NOT SUBMIT.")
 print("SKIP-PREVIEW OPTION PASS",p)

def check(site,spec):
 name,first,last,co2,ny,receiptfile=spec
 case=ROOT/"cases"/name
 if not case.is_dir():stop(site+": expected existing CIME case missing")
 r=read(receiptfile)
 if (r.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or
     r.get("model_jobs_submitted") is not False or
     r.get("ready_to_submit_AD5") is not False):
  stop(site+": source AD5 preview not proven successful/unsubmitted")
 original=case/"CaseDocs/lnd_in"
 datm=case/"CaseDocs/datm.streams.xml"
 if site=="CA-TP4":
  h1=r["generated_lnd_in_sha256"]
  h2=r["generated_datm_stream_sha256"]
 else:
  h1=r["result"]["lnd_in_sha256"]
  h2=r["result"]["datm_stream_sha256"]
 if sha(original)!=h1 or sha(datm)!=h2:
  stop(site+": CIME generated CaseDocs changed after validated preview")
 if (case/"env_case.xml").read_bytes()!=(case/"LockedFiles/env_case.xml").read_bytes():
  stop(site+": CIME private AD overlay lock not restored")
 opts=xml(case)
 expected={"CASE":name,"RUN_TYPE":"startup","RUN_STARTDATE":str(first)+"-01-01",
   "CALENDAR":"NO_LEAP","ATM_NCPL":"48","STOP_OPTION":"nyears",
   "STOP_N":"5","REST_OPTION":"nyears","REST_N":"5","RESUBMIT":"0",
   "CONTINUE_RUN":"FALSE","DATM_MODE":"1PT",
   "DATM_YR_START":str(first),"DATM_YR_END":str(last),
   "DATM_YR_ALIGN":str(first),"CLM_FORCE_COLDSTART":"on",
   "CLM_ACCELERATED_SPINUP":"on","CLM_CO2_TYPE":"constant",
   "BUILD_COMPLETE":"TRUE","COMP_ROOT_DIR_LND":"$SRCROOT"}
 for k,val in expected.items():
  if opts.get(k,"").lower()!=val.lower():
   stop(site+": CIME effective "+k+" is not "+val)
 if abs(float(opts.get("CCSM_CO2_PPMV","nan"))-co2)>0.03:
  stop(site+": CO2 initial-year value changed")
 if not (Path(opts["EXEROOT"])/"cesm.exe").is_file():
  stop(site+": compiled 1PT FATES executable unavailable")
 if opts.get("RUNDIR")!=str(RUNROOT/name/"run"):
  stop(site+": independent RUNDIR changed")
 raw=original.read_text(encoding="utf-8")
 for k,val in (("use_fates",".true."),("use_fates_sp",".false."),
               ("use_fates_fixed_biogeog",".true."),
               ("use_fates_nocomp",".true."),("use_cn",".false."),
               ("spinup_state","2")):
  if key(raw,k)!=val:stop(site+": generated FATES AD mode wrong "+k)
 if key(raw,"finidat") not in (None,"") or key(raw,"reseed_dead_plants") is not None:
  stop(site+": source model not a cold start")
 surf=key(raw,"fsurdat")
 if surf is None or site not in surf or not Path(surf).is_file():
  stop(site+": effective land surface absent/wrong site")
 streams=ET.parse(datm).getroot()
 candidates=[x for x in streams.iter("stream_info") if x.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(candidates)!=1:stop(site+": no uniquely identified meteorological DATM stream")
 stream=candidates[0]
 for k,val in (("year_first",first),("year_last",last),("year_align",first),
               ("offset",0),("taxmode","cycle"),("tintalgo","linear")):
  n=stream.find(k)
  if n is None or (n.text or "").strip()!=str(val):
   stop(site+": generated DATM "+k+" mismatch")
 fields={}
 for item in stream.find("datavars"):
  parts=(item.text or "").split()
  if len(parts)!=2 or parts[0] in fields:stop(site+": invalid effective CDEPS datavars")
  fields[parts[0]]=parts[1]
 if any(fields.get(k)!=v for k,v in MAP.items()):
  stop(site+": effective 8-variable DATM met map wrong")
 files=[Path((x.text or "").strip()) for x in stream.find("datafiles")]
 if len(files)!=ny or len(set(files))!=ny:stop(site+": annual file count/duplicate mismatch")
 for yr,f in zip(range(first,last+1),files):
  if not f.is_file() or site not in str(f) or f.stem!=str(yr):
   stop(site+": annual UTC NetCDF absent/wrong year or site "+str(f))
 rundir=RUNROOT/name/"run"
 live=rundir/"lnd_in"
 if not live.is_file():
  stop(site+": RUNDIR/lnd_in missing, cannot safely skip runtime regeneration")
 if sha(live)!=h1:
  stop(site+": RUNDIR/lnd_in differs from pinned CaseDocs FATES AD namelist")
 print("RUNDIR DATM PRESENT:",(rundir/"datm_in").is_file(),
       "DATM STREAM XML PRESENT:",(rundir/"datm.streams.xml").is_file())
 helpcheck(case,"case.submit")
 helpcheck(case,"case.run")
 print("PASS",site,"UTC MET YEARS",ny,"FIXED CO2",co2,
       "FATES FIXNC spinup_state2; executable/inputs/CIME lock preserved",flush=True)
 print("RELEASE STATUS: technical AD5-only candidate; actual coupler geometry and solar phase still require runtime observation")

def selftest():
 assert set(SPECS)=={"CA-TP4","BR-Ma2","CA-Ca3","CA-LP1"}
 assert sum(s[4] for s in SPECS.values())==82
 assert all(s[2]-s[1]+1==s[4] for s in SPECS.values())
 print("SELF-TEST PASS: four CIME AD5 cases, 82 existing UTC annual forcing files, no Slurm")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 group=p.add_mutually_exclusive_group(required=True)
 group.add_argument("--self-test",action="store_true")
 group.add_argument("--check",action="store_true")
 a=p.parse_args()
 if a.self_test:selftest();return
 for site,spec in SPECS.items():check(site,spec)
 print("STAGE17 FOUR-SITE PRE-SUBMISSION CIME INPUT GATE PASS; NO FILE MODIFICATION OR SLURM")
 print("DO NOT USE UNQUALIFIED ./case.submit: source private FATES AD overlay was restored.")
 print("POTENTIAL AFTER SCIENCE/MACHINE RELEASE: ./case.submit --skip-preview-namelist")
if __name__=="__main__":main()
