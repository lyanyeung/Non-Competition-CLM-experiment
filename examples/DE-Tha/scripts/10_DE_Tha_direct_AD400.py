#!/usr/bin/env python3
"""DE-Tha direct 400-year FATES accelerated-decomposition cold-start (no PRE50).

STAGE10: gated PREPARE and 5-year SMOKE only. 1996 -> 2001 (5 model years).
A separate, not-yet-authorized 395-year continuation follows verification of
three archived component restarts AND spinup_state=2. NEVER auto-resubmit
before the smoke archive has been independently verified.

Pinned NL-Loo lessons: enforce generated FATES spinup_state=2, use FATES_GPP
and FATES_NPP in hist_fincl1, never use a stale rpointer, do not patch shared
CTSM source, do not blindly submit on a failed preview_namelists.

CLI:
  inspect                 strictly READ ONLY; inspect template and sources
  stage --confirm ...     create ONLY independent case, generate namelists
  validate                strictly READ ONLY; inspect isolated case
  submit-smoke --confirm ...  submit ONLY ONE 5-year run+archive
  status                  strictly READ ONLY

Known DE-Tha forcing has QC REVIEW: user explicitly accepts using existing
v5 forcing AS IS for this experimental spinup. No QC records are modified.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

USER = "ly3n24"
R = Path(f"/iridisfs/scratch/{USER}/CLM_FATES")
CTSM = R/"CTSM"
SCRIPTS = CTSM/"cime/scripts"
EXISTING = R/"cases/DE-Tha_FATES_SPINUP500"
NAME = "DE-Tha_OBSPFT_NC_V1_AD400"
CASE = R/"cases"/NAME
OUT = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS")
RUN = OUT/NAME/"run"
ARCH = OUT/"archive"/NAME
SURFACE = R/"experiments/NonCompetitionObserved22/DE-Tha/surface/surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_SoilField17_71_12_v2.nc"
PARAM = CTSM/"src/fates/parameter_files/fates_params_default.json"
FORCING = R/"sites/MY_EC_SITE/DE-Tha/forcing/processed_v5/DE-Tha_CLM_forcing_1996_2025.csv"
STREAM_SOURCE = EXISTING/"user_nl_datm_streams"
WORK = Path.home()/"DE_Tha_AD400_controller"
STATE = WORK/"submission_state.json"
RUN_FIRST = 1996
SMOKE_LAST = 2001
FINISH = 2396
AD_YEARS = 400
SURF_SHA = "0d3d827cc4bbfab277d629fafc33ee26933404a84b56ba1bfcac8b3e6cd5e60a"
PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
FORCING_SHA = "ed347a37dbd64c19420bb96a0738bc3d579c4717f6149591fc8ee2218f69cf43"
CTSM_REV = "d5ea9d0136530370a62ef267ccfaff6f001ef914"
STAGE_ACK = "STAGE_DE_THA_DIRECT_AD400_COLDSTART_REVIEWED_FORCING"
SUBMIT_ACK = "SUBMIT_DE_THA_AD400_FIRST_FIVE_YEARS_ONLY"
HISTORY = ["TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO"]
NAMELIST = {
    "fsurdat":f"'{SURFACE}'",
    "use_fates":".true.",
    "use_fates_sp":".false.",
    "use_fates_fixed_biogeog":".true.",
    "use_fates_nocomp":".true.",
    "spinup_state":"2",
    "hist_fincl1":",".join("'"+x+"'" for x in HISTORY),
}

def fail(msg):
    raise RuntimeError(str(msg))

def run(cmd, cwd=None, timeout=240, verbose=False):
    p=subprocess.run([str(x) for x in cmd],cwd=cwd,text=True,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=timeout,check=False)
    if verbose or p.returncode:
        print("COMMAND:", " ".join(map(str,cmd)), "returncode",p.returncode,flush=True)
        if p.stdout: print(p.stdout[-5500:],flush=True)
        if p.stderr: print("STDERR:",p.stderr[-5500:],flush=True)
    if p.returncode:
        fail("Command returned nonzero; do not retry blindly: "+" ".join(map(str,cmd)))
    return p.stdout.strip()

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def pinned(path, expected):
    if not path.is_file():
        fail("Required pinned file missing: "+str(path))
    got=sha(path)
    if got!=expected:
        fail(f"PINNED HASH FAIL for {path}: {got} != {expected}")
    print("PASS pinned:",path.name,got,flush=True)

def xml(case,key):
    return run(["./xmlquery",key,"--value"],cwd=case,timeout=60)

def change(key,value):
    run(["./xmlchange",f"{key}={value}"],cwd=CASE,timeout=60)

def nml_value(text,key):
    hits=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n]*)",text)
    if len(hits)>1:
        fail("Duplicate namelist setting: "+key)
    return hits[0].strip().strip("'\"") if hits else None

def replace_nl(text,key,value):
    # Accept at most one existing assignment, do not alter unknown text.
    regex=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*$"
    match=list(re.finditer(regex,text))
    if len(match)>1:
        fail("Ambiguous inherited user_nl_clm: "+key)
    if match:
        text=text[:match[0].start()]+key+" = "+value+text[match[0].end():]
    else:
        text=text.rstrip()+"\n"+key+" = "+value+"\n"
    return text

def queue_matches():
    output=run(["squeue","-u",USER,"-h","-o","%i|%j|%T"],timeout=30)
    return [line for line in output.splitlines()
            if ("run."+NAME in line or "st_archive."+NAME in line)]

def verify_surface():
    pinned(SURFACE,SURF_SHA)
    pinned(PARAM,PARAM_SHA)
    pinned(FORCING,FORCING_SHA)
    if run(["git","rev-parse","HEAD"],cwd=CTSM)!=CTSM_REV:
        fail("CTSM checkout is not pinned revision")
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(SURFACE,"r") as ds:
        def val(field):
            a=np.ma.filled(ds.variables[field][:],np.nan).ravel()
            if a.size!=1 or not np.isfinite(a).all():
                fail("Invalid "+field)
            return float(a[0])
        if abs(val("PCT_NATVEG")-100)>1e-4 or abs(val("PCT_CROP"))>1e-4:
            fail("Selected new surface is not NATVEG100/CROP0")
        pft=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
        exp=np.zeros(15)
        exp[[1,3,7]]=[87,10,3]
        if not np.allclose(pft,exp,atol=.001,rtol=0):
            fail("Observed-forest PFT shares do not match 87/10/3")
        for key,value in (("PCT_SAND",17.),("PCT_CLAY",12.)):
            a=np.ma.filled(ds.variables[key][:],np.nan)
            if a.size!=10 or not np.isfinite(a).all() or not np.allclose(a,value,atol=.001):
                fail(f"Site soil {key} does not equal {value}% in ten layers")
    print("PASS: verified v2 forest and measured-site soil proxy",flush=True)

def inspect():
    verify_surface()
    if not EXISTING.is_dir() or not (EXISTING/"CaseDocs/lnd_in").is_file():
        fail("Original DE-Tha CIME case missing; cannot inherit site setup")
    if xml(EXISTING,"BUILD_COMPLETE").lower()!="true":
        fail("Existing DE-Tha case not BUILD_COMPLETE; --keepexe unsafe")
    exe=Path(xml(EXISTING,"EXEROOT"))/"cesm.exe"
    if not exe.is_file():
        fail("Existing DE-Tha executable missing: "+str(exe))
    if not STREAM_SOURCE.is_file():
        fail("Original DE-Tha DATM streams missing")
    stream=STREAM_SOURCE.read_text(errors="replace")
    required=["year_first = 1996","year_last = 2025","year_align = 1996",
              "DE-Tha_DATM_1996.nc","DE-Tha_DATM_2025.nc"]
    for token in required:
        if token not in stream:
            fail("Original DATM stream does not contain "+token)
    original=(EXISTING/"user_nl_clm").read_text(errors="replace")
    if nml_value(original,"finidat") not in (None,""):
        fail("Original DE-Tha case has an explicit finidat; inspect before cold-start clone")
    print("PASS: existing site case provides pinned DATM streams and executable")
    print("BASE EXEROOT:",exe.parent)
    print("BASE EXE SHA256:",sha(exe))
    print("ORIGINAL user_nl_clm no explicit nonempty finidat")
    for key in ("RUN_TYPE","RUN_STARTDATE","CLM_CO2_TYPE","CCSM_CO2_PPMV",
                "RUN_REFCASE","RUN_REFDATE","STOP_N","REST_N"):
        try: print("REFERENCE",key,xml(EXISTING,key))
        except RuntimeError: print("REFERENCE",key,"unavailable")
    print("FORCING POLICY: use currently pinned processed_v5/DATM unchanged")
    print("USER-ACCEPTED QC REVIEW: 14 manual, 32 replacements; no corrections")
    print("NO RUN OR CASE WRITES (INSPECT ONLY)")
    return exe

def stage():
    exe=inspect()
    if any(p.exists() for p in (CASE,RUN,ARCH,WORK)):
        fail("Case/run/archive/ledger path already exists; do not overwrite or rerun STAGE")
    if queue_matches():fail("Matching AD400 jobs exist in Slurm")
    # Clone the site's original case for streams/machine settings. The clone
    # does NOT alter the existing case or build a different executable.
    run([SCRIPTS/"create_clone","--case",CASE,"--clone",EXISTING,"--keepexe"],
        cwd=SCRIPTS,timeout=300,verbose=True)
    if not CASE.is_dir():
        fail("Clone reported success but new case absent")
    settings={
        "RUN_TYPE":"startup",
        "RUN_STARTDATE":"1996-01-01",
        "CONTINUE_RUN":"FALSE",
        "CLM_FORCE_COLDSTART":"on",
        "CLM_ACCELERATED_SPINUP":"on",
        "STOP_OPTION":"nyears","STOP_N":"5",
        "REST_OPTION":"nyears","REST_N":"5",
        "RESUBMIT":"0",
        "DOUT_S":"TRUE",
        "RUNDIR":str(RUN),
        "DOUT_S_ROOT":str(ARCH),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores",
    }
    for k,v in settings.items():
        change(k,v)
    if xml(CASE,"EXEROOT")!=str(exe.parent):
        fail("Cloned case changed shared executable path; stop")
    if xml(CASE,"BUILD_COMPLETE").lower()!="true":
        fail("Cloned case not built (--keepexe failed)")
    original=(CASE/"user_nl_clm")
    if not original.is_file():
        fail("Cloned user_nl_clm absent")
    text=original.read_text()
    if nml_value(text,"finidat") not in (None,""):
        fail("Cloned user_nl_clm has finidat; cannot perform cold start")
    if nml_value(text,"reseed_dead_plants") is not None:
        fail("CN-only reseed_dead_plants in inherited user_nl_clm")
    for key,value in NAMELIST.items():
        text=replace_nl(text,key,value)
    original.write_text(text,encoding="utf-8")
    print("PASS: copied and constrained user_nl_clm with explicit spinup_state=2")
    if not (CASE/".case.run").is_file():
        run(["./case.setup"],cwd=CASE,timeout=240,verbose=True)
    # A failure here is a SAFE STOP, not a reason to patch the shared CTSM
    # or force spinup_state into run/lnd_in manually without provenance.
    run(["./preview_namelists"],cwd=CASE,timeout=240,verbose=True)
    run(["./check_input_data"],cwd=CASE,timeout=300,verbose=True)
    validate()
    WORK.mkdir(parents=True,exist_ok=False)
    STATE.write_text(json.dumps({
       "site":"DE-Tha","experiment":"DIRECT_AD400_COLDSTART",
       "case":str(CASE),"v2_surface":str(SURFACE),
       "surface_sha256":SURF_SHA,"base_exe_sha256":sha(exe),
       "stage":"PREPARED_NOT_SUBMITTED","action_history":["STAGE"],
       "first_5y":{"start_year":RUN_FIRST,"end_year":SMOKE_LAST},
       "target_end":FINISH,"intended_segments":80,"resubmit":0,
       "watchdog_armed":False,"postAD_scheduled":False,
       "user_accepts_existing_forcing_QC_REVIEW":True,
       "created_utc":datetime.now(timezone.utc).isoformat()
    },indent=2)+"\n")
    print("STAGED ONLY: direct AD400 1996->2396, first 5y case is READY")
    print("DO NOT submit until VALIDATE printed PASS above; NO JOBS SUBMITTED")

def validation_settings():
    for key,value in {
        "RUN_TYPE":"startup","RUN_STARTDATE":"1996-01-01",
        "CONTINUE_RUN":"FALSE","CLM_FORCE_COLDSTART":"on",
        "CLM_ACCELERATED_SPINUP":"on",
        "STOP_N":"5","STOP_OPTION":"nyears",
        "REST_N":"5","REST_OPTION":"nyears",
        "RESUBMIT":"0","DOUT_S":"TRUE",
        "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH),
    }.items():
        actual=xml(CASE,key)
        if actual.lower()!=value.lower():
            fail(f"AD400 XML mismatch {key}: {actual} != {value}")
    if xml(CASE,"BUILD_COMPLETE").lower()!="true":
        fail("Cloned case not marked built")
    if xml(CASE,"EXEROOT")!=xml(EXISTING,"EXEROOT"):
        fail("New case EXEROOT differs from DE-Tha original")
    if not (Path(xml(CASE,"EXEROOT"))/"cesm.exe").is_file():
        fail("Referenced cesm.exe missing")
    if not (CASE/".case.run").is_file() or not (CASE/"case.st_archive").is_file():
        fail("New .case.run or case.st_archive missing")
    if re.search(r"(?im)^#SBATCH .*--exclusive",(CASE/".case.run").read_text()):
        fail("Exclusive node reservation not accepted for this experiment")

def validation_namelists():
    user=(CASE/"user_nl_clm").read_text()
    for key,value in NAMELIST.items():
        present=nml_value(user,key)
        wanted=value.strip("'\"") if key!="hist_fincl1" else value
        if (present or "").strip()!=wanted:
            fail(f"USER_NL expected {key}={value} but got {present}")
    for file in (CASE/"CaseDocs/lnd_in",RUN/"lnd_in"):
        if not file.is_file():
            fail("Generated namelist missing: "+str(file))
        txt=file.read_text()
        for k in NAMELIST:
            if k=="hist_fincl1":
                registered=re.findall(r"'([^']+)'",nml_value_raw(txt,k))
                if registered!=HISTORY:
                    fail("Wrong FATES history fields in "+str(file)+": "+str(registered))
                continue
            val=nml_value(txt,k)
            expect=NAMELIST[k].strip("'\"")
            if val!=expect:
                fail(f"Generated {file} expected {k}={expect}, observed {val}")
        if nml_value(txt,"use_cn") not in (".false.","false"):
            fail("Generated lnd_in not use_cn=.false.")
        if nml_value(txt,"reseed_dead_plants") is not None:
            fail("Generated lnd_in contains CN-only reseed_dead_plants")
        if nml_value(txt,"finidat") not in (None,""):
            fail("Generated lnd_in has finidat: cold startup not assured")
    if sha(CASE/"CaseDocs/lnd_in")!=sha(RUN/"lnd_in"):
        fail("CaseDocs and RUNDIR lnd_in differ")
    if (CASE/"user_nl_datm_streams").read_text()!=STREAM_SOURCE.read_text():
        fail("Cloned site DATM streams differ from pinned legacy streams")
    print("PASS: generated FATES cold-start AD spinup_state=2; no CN-only reseed")
    print("PASS: ENF/DNF/DBF FIXNC, FATES GPP/NPP, no finidat, DATM streams unchanged")

def nml_value_raw(text,key):
    hits=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n]*)",text)
    if len(hits)!=1:
        fail(f"Expected one {key}, got {len(hits)}")
    return hits[0].strip()

def validate():
    verify_surface()
    if not CASE.is_dir():
        fail("Independent case not staged yet")
    validation_settings()
    validation_namelists()
    if queue_matches():
        fail("DE-Tha direct AD400 case already has queued job")
    print("VALIDATE PASS: AD400 1996-startup 5-year smoke eligible (RESUBMIT=0)")

def submit_smoke():
    validate()
    if not STATE.is_file():
        fail("Submission state not found; staged case metadata missing")
    ledger=json.loads(STATE.read_text())
    if ledger.get("stage")!="PREPARED_NOT_SUBMITTED":
        fail("Stage has already been submitted or submission uncertainty exists")
    if ledger.get("base_exe_sha256")!=sha(Path(xml(CASE,"EXEROOT"))/"cesm.exe"):
        fail("Original executable SHA256 changed after stage")
    cs=(CASE/"CaseStatus").read_text(errors="replace")
    if re.search(r"case\.submit starting|case\.run starting|case\.submit success",cs):
        fail("CaseStatus indicates an earlier submission; do not duplicate")
    if queue_matches():
        fail("Matched job already exists")
    # A crash or timeout after this marker requires investigation, not retry.
    ledger["stage"]="SUBMISSION_ATTEMPTED_UNCERTAIN"
    ledger["submitted_attempt_utc"]=datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(ledger,indent=2)+"\n")
    # user_nl_clm has EXPLICIT spinup_state=2, so avoid private module
    # patch and CIME immutable-env lock used in the NL-Loo hybrid handoff.
    print("Submitting ONE 5y cold-start AD smoke job + conditional archive; RESUBMIT=0",flush=True)
    output=run(["./case.submit"],cwd=CASE,timeout=300,verbose=True)
    match=re.search(r"Submitted job case\.run with id (\d+)",output)
    archive=re.search(r"Submitted job case\.st_archive with id (\d+)",output)
    if not match or not archive:
        fail("Submission returned no parseable job IDs. Do not rerun; inspect squeue.")
    ledger["stage"]="FIRST_5Y_SUBMITTED"
    ledger["first_run_job"]=match.group(1)
    ledger["first_archive_job"]=archive.group(1)
    STATE.write_text(json.dumps(ledger,indent=2)+"\n")
    print("SUBMITTED: first 5y AD 1996-2001 only, run=",match.group(1),
          "archive=",archive.group(1),flush=True)
    print("HOLD: remaining 395 years NOT submitted, no watchdog, no POST stage.")

def status():
    print("CASE:",CASE,"exists=",CASE.is_dir())
    print("RUN:",RUN,"exists=",RUN.is_dir())
    print("ARCHIVE:",ARCH,"exists=",ARCH.is_dir())
    print("STATE:",STATE,"exists=",STATE.is_file())
    if STATE.is_file():
        print(STATE.read_text())
    print("QUEUE:",queue_matches())
    final=ARCH/"rest"/f"{SMOKE_LAST:04d}-01-01-00000"
    print("FIRST-5Y ARCHIVE:",final,final.is_dir())
    print("HOLD: never infer a successful AD run from job submission alone")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("inspect","stage","validate","submit-smoke","status"))
    parser.add_argument("--confirm",default="")
    args=parser.parse_args()
    if args.action=="inspect":inspect()
    elif args.action=="stage":
        if args.confirm!=STAGE_ACK:fail("Stage requires --confirm "+STAGE_ACK)
        stage()
    elif args.action=="validate":validate()
    elif args.action=="submit-smoke":
        if args.confirm!=SUBMIT_ACK:fail("Smoke submit requires --confirm "+SUBMIT_ACK)
        submit_smoke()
    else:status()

if __name__=="__main__":
    main()
