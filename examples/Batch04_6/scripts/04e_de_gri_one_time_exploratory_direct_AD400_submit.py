#!/usr/bin/env python3
"""Batch04 DE-Gri: technical audit and ONE-TIME exploratory DIRECT AD400 submission.

Science remains HOLD (49 MDS, 12 source QC0 rain-time semantics, inherited soil).
This NEVER claims observational scientific release. Operator explicit confirmation
is required to submit 80 x 5-year AD400 segments without a separate AD5.
Use exact Stage04C source SHA and read-only verification. No re-cloning.
"""
import argparse
import configparser
import hashlib
import importlib.util
import json
import os
import re
import resource
import socket
import subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=ROOT/"cases/DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT"
TEMPLATE=ROOT/"cases/DE-Gri_FATES_SPINUP1000_S30SHARED"
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT/run")
STATE=ROOT/"experiments/Batch04_DE_Gri_AD400_DIRECT_preparation/stage04c_prepare_state.json"
SUBMISSION=ROOT/"experiments/Batch04_DE_Gri_AD400_DIRECT_preparation/stage04e_submission_attempt_PRIVATE.json"
SRC_SHA="0e6e5ab0d8469f4d2261555a0773b87bc178e5ba"
ACK="SUBMIT_DE_GRI_EXPLORATORY_DIRECT_AD400_80X5_SCIENCE_HOLD_ONCE"
NAME=CASE.name
CIME_EXPECT={"CASE":NAME,"RUN_TYPE":"startup","CONTINUE_RUN":"FALSE",
    "RUN_STARTDATE":"2004-01-01","STOP_OPTION":"nyears","STOP_N":"5",
    "REST_OPTION":"nyears","REST_N":"5","RESUBMIT":"0",
    "RESUBMIT_SETS_CONTINUE_RUN":"TRUE","DOUT_S":"TRUE",
    "CLM_FORCE_COLDSTART":"on","CLM_ACCELERATED_SPINUP":"on",
    "DATM_YR_START":"2004","DATM_YR_END":"2025","DATM_YR_ALIGN":"2004",
    "BUILD_COMPLETE":"TRUE","DATM_MODE":"1PT","CALENDAR":"NO_LEAP","ATM_NCPL":"48"}
def need(c,msg):
    if not c:raise RuntimeError(msg)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):h.update(block)
    return h.hexdigest()
def blob(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def command(argv,at=None,timeout=120,allowed=(0,)):
    try:
        p=subprocess.run([str(x) for x in argv],cwd=at,text=True,
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise RuntimeError("Command failed "+str(argv)+": "+str(e)) from e
    need(p.returncode in allowed,"Command "+str(argv)+
         " rc "+str(p.returncode)+" "+(p.stdout+p.stderr)[-1200:])
    return p.stdout+p.stderr
def cime(case,key):
    return command([case/"xmlquery",key,"--value"],case,60).strip()
def check_case_status():
    file=CASE/"CaseStatus"
    need(file.is_file(),"CIME CaseStatus unavailable")
    stat=file.read_text(errors="replace")
    need(not re.search(r"case\.submit starting|case\.run starting",stat,re.I),
         "CIME CaseStatus has prior submit/run; no repeat")
    need(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")),
         "Startup run directory already has restart")
    return sha(file)
def load_pinned(code):
    p=Path(code)
    need(p.is_file() and blob(p)==SRC_SHA,"Stage04C source blob differs")
    spec=importlib.util.spec_from_file_location("stage04c_pinned",p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    need(mod.CASE==CASE and mod.LEDGER==STATE and mod.TEMPLATE==TEMPLATE,
         "Loaded Stage04C targets different case")
    return mod
def scheduler_clear():
    user=os.environ.get("USER","ly3n24")
    need(bool(re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*",user)),"Invalid scheduler user")
    q=command(["squeue","-h","-u",user,"-o","%i|%j|%T"],timeout=100)
    found=[s for s in q.splitlines() if NAME in s]
    need(not found,"Slurm queue already has this case: "+str(found[:5]))
    # Accounting might not be available on every IRIDIS login node.
    # Do not interpret a failing query as "no jobs": fail closed.
    hist=command(["sacct","-X","-u",user,"-S","2026-11-01",
                  "--format=JobIDRaw,JobName,State","--parsable2","--noheader"],
                  timeout=100)
    found=[s for s in hist.splitlines() if NAME in s]
    need(not found,"Slurm accounting already knows this case: "+str(found[:5]))
    return {"squeue_clear":True,"sacct_clear_since":"2026-11-01"}
def audit(code,check_queue=True):
    need(CASE.is_dir() and not CASE.is_symlink(),"Prepared new case absent/unsafe")
    need(STATE.is_file() and not STATE.is_symlink(),"Stage04C prepared receipt absent")
    need(not SUBMISSION.exists() and not SUBMISSION.is_symlink(),
         "Submission attempt receipt already exists; never submit twice")
    obj=json.loads(STATE.read_text(encoding="utf-8"))
    need(obj.get("phase")=="PREPARED_VERIFIED_NOT_SUBMITTED"
         and obj.get("source_science_HOLD") is True
         and obj.get("science_release") is False
         and obj.get("slurm_submitted") is False
         and obj.get("case")==str(CASE),
         "Wrong prepared technical state/science declaration")
    need(obj.get("future_resubmits")==79 and obj.get("verified_annual_file_count")==22,
         "Not configured for 80 x 5 year AD400")
    mod=load_pinned(code)
    original=Path(obj["source_stage04a"])
    need(original.is_file(),"Source verified Stage04A missing")
    parent=json.loads(original.read_text())
    need(parent.get("site")=="DE-Gri" and parent.get("science_release") is False,
         "Input provenance not science HOLD")
    fates=Path(obj["FATES_param"])
    surface=Path(obj["PFT_surface"])
    need(fates.is_file() and surface.is_file(),"FATES param or PFT surface missing")
    need(sha(fates)==obj["FATES_param_sha256"] and sha(surface)==obj["PFT_surface_sha256"],
         "FATES param / surface content differs from prepared state")
    detail={
        "expected_inputs":parent["annual_DATM_22_path_list"],
        "surface":str(surface),"surface_sha256":obj["PFT_surface_sha256"],
        "param":str(fates),"param_sha256":obj["FATES_param_sha256"],
        "executable":str(Path(mod.xq(TEMPLATE,"EXEROOT"))/"cesm.exe")}
    h=mod.verify(detail)
    need(h["lnd_in_sha256"]==obj["lnd_in_sha256"]
         and h["effective_stream_sha256"]==obj["effective_stream_sha256"],
         "CIME generated effective streams or land config changed")
    need((CASE/"env_case.xml").read_bytes()==(CASE/"LockedFiles/env_case.xml").read_bytes(),
         "CIME original env_case lock error recurred")
    for key,want in CIME_EXPECT.items():
        got=cime(CASE,key)
        need(got.lower()==want.lower(),"CIME "+key+"="+got+" expected "+want)
    need(Path(cime(CASE,"EXEROOT")).joinpath("cesm.exe").is_file(),
         "Compiled model executable unavailable")
    case_status_sha=check_case_status()
    need(not list(RUN.glob("*job*")) and not list(RUN.glob("*.log.*")),
         "Run directory appears previously started")
    # Check that the actual case-submit implementation supports preserving
    # the generated private DATM stream and land namelists.
    helptext=command([CASE/"case.submit","--help"],CASE,100,allowed=(0,1,2))
    need("--skip-preview-namelist" in helptext,"case.submit lacks skip-preview-namelist")
    queue=scheduler_clear() if check_queue else {"scheduler_status":"not checked"}
    result={"case":str(CASE),"phase":"AUDIT_PASS_NOT_SUBMITTED",
        "prepared_ledger_sha256":sha(STATE),
        "case_status_sha256":case_status_sha,
        "lnd_in_sha256":h["lnd_in_sha256"],
        "datm_stream_sha256":h["effective_stream_sha256"],
        "surface_sha256":obj["PFT_surface_sha256"],
        "FATES_param_sha256":obj["FATES_param_sha256"],
        "years":400,"segments":80,"segment_years":5,"resubmits_at_submission":79,
        "science":"EXPLORATORY_SCIENCE_HOLD_NO_PUBLICATION_QC_RELEASE",
        "manual_science_questions":["49 original MDS-HOLD events",
          "12 QC0 heavy-rain gauge accumulation timing",
          "inherited soil source representativeness and CO2 hypothesis"],
        "no_separate_AD5":True,"Slurm_submitted":False,**queue}
    print("STAGE04E DIRECT AD400 SUBMISSION PREFLIGHT PASS | ZERO JOBS SUBMITTED")
    print("CASE",CASE,"22 site annual DATM verified, 2011/2024 sensitivities pinned")
    print("Effective FATES AD + soil-proxy surface PASS; CIME lock PASS")
    print("STOP_N=5 / 80 SEGMENTS / RESUBMIT will change 0 -> 79 at submission")
    print("SCHEDULER",queue,"| SCIENCE: EXPLORATORY HOLD, NOT PUBLICATION QC PASS")
    return result
def stack():
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    threshold=64*1024*1024
    if soft!=resource.RLIM_INFINITY and soft<threshold:
        need(hard==resource.RLIM_INFINITY or hard>=threshold,
             "Stack hard limit under 64 MiB")
        resource.setrlimit(resource.RLIMIT_STACK,
            (resource.RLIM_INFINITY if hard==resource.RLIM_INFINITY else hard,hard))
    return resource.getrlimit(resource.RLIMIT_STACK)
def submit(code,token):
    need(token==ACK,"Must explicitly confirm EXPLORATORY direct AD400 with unresolved science holds")
    report=audit(code,True)
    print("STACK",stack(),"HOST",socket.gethostname(),flush=True)
    recorded={"phase":"SUBMISSION_ATTEMPT_UNCERTAIN",
        "source_audit":report,
        "submit_utc":datetime.now(timezone.utc).isoformat(),
        "case":str(CASE),"science_release":False,
        "no_separate_AD5":True}
    # Crash-safe sentinel *before* xmlchange/case.submit: repeat never safe.
    with SUBMISSION.open("x",encoding="utf-8") as f:
        json.dump(recorded,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
    command([CASE/"xmlchange","RESUBMIT=79"],CASE,90)
    need(cime(CASE,"RESUBMIT")=="79",
         "RESUBMIT=79 failed; submission attempt uncertain, do not retry")
    p=subprocess.run([str(CASE/"case.submit"),"--skip-preview-namelist"],
        cwd=CASE,capture_output=True,text=True,timeout=650,check=False)
    print("CIME SUBMIT STDOUT\n"+p.stdout[-5500:],"CIME SUBMIT STDERR\n"+p.stderr[-1500:],flush=True)
    need(p.returncode==0,"CIME case.submit returned nonzero; attempt uncertain, do not retry")
    run=re.findall(r"Submitted job case\.run with id (\d+)",p.stdout)
    arch=re.findall(r"Submitted job case\.st_archive with id (\d+)",p.stdout)
    need(len(run)==1 and len(arch)==1,"Could not uniquely parse job IDs; do NOT retry")
    cfg=configparser.RawConfigParser()
    opts=CASE/".submit_options"
    if opts.is_file():cfg.read(opts)
    persisted=cfg.has_section("SubmitOptions") and cfg.getboolean(
        "SubmitOptions","skip_pnl",fallback=False)
    recorded.update({"phase":"AD400_SUBMITTED_MODEL_NOT_COMPLETED" if persisted else
                    "SUBMITTED_SKIP_PREVIEW_PERSISTENCE_UNCERTAIN",
        "run_job_id":run[0],"archive_job_id":arch[0],
        "skip_preview_persisted":persisted,
        "submitted_utc":datetime.now(timezone.utc).isoformat()})
    # Only this private submission receipt is updated; no modifications
    # to forcing, parameter files, original case or science approval.
    with SUBMISSION.open("w",encoding="utf-8") as f:
        json.dump(recorded,f,indent=2);f.write("\n")
    print("DE-GRI EXPLORATORY DIRECT AD400 SUBMITTED | run",run[0],
          "| archive",arch[0],"| 80x5y / RESUBMIT79")
    print("NO YEARS COMPLETED YET | SCIENCE HOLD PERSISTS | RECEIPT",SUBMISSION)
    if not persisted:
        print("WARNING: skip-preview flag not verified as persistent; do not assume future automatic resubmits will preserve custom streams. Check CIME behavior; do not manually resubmit.")
def selftest():
    need(80*5==400 and 80-1==79,"Segment arithmetic")
    need(CASE.name=="DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT","Case identity")
    need(ACK.endswith("SCIENCE_HOLD_ONCE"),"Human acknowledgement")
    need(CIME_EXPECT["CLM_ACCELERATED_SPINUP"]=="on"
         and CIME_EXPECT["RESUBMIT"]=="0","CIME submit preflight")
    print("STAGE04E SELF-TEST PASS: direct 400-year CIME guard; NO SLURM")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("self-test","audit","submit"))
    ap.add_argument("--stage04c-code",type=Path)
    ap.add_argument("--confirm")
    a=ap.parse_args()
    if a.action=="self-test":selftest();return
    need(a.stage04c_code is not None,"Verified original Stage04C code path required")
    if a.action=="audit":audit(a.stage04c_code);return
    submit(a.stage04c_code,a.confirm)
if __name__=="__main__":main()
