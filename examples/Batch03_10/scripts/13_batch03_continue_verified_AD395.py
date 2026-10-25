#!/usr/bin/env python3
"""Batch03 10-site AD5->AD395 continuation, adapted from Batch01 Stage13 (DE-Tha method).

AUDIT: READ ONLY. Verifies exact initial run/archive sacct COMPLETED/0:0,
three archived CLM/DATM/CPL restarts, land spinup_state=2, original AD
namelist, CIME continue/resubmit settings, and preserved --skip-preview-namelist.

CONTINUE-395: ONLY after 10/10 pass audit; for each isolated new case, set
CONTINUE_RUN=TRUE and RESUBMIT=78 (79 x 5yr segments including first continuation
segment), stage restart + rpointer, submit ONCE with skip-preview-namelist.
Each site's ledger is marked ATTEMPTED before any handoff/write to fail closed
on an uncertain case. Do not run this twice.

No original forcing, old case, source surfdata, compiled exe, or shared CTSM
is modified. No re-check of forcing years or scientific input literature.
"""
from __future__ import annotations
import argparse
import configparser
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("batch03_stage11",P/"11_batch03_AD400_oneclick.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Missing Batch03 Stage11 helper")
B=importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

ACK="CONTINUE_BATCH03_TEN_VERIFIED_AD5_BY_395_YEARS"
# Unlike Batch01, job IDs are NOT hard-coded: Batch03 Stage11 submit-smoke stores
# the parsed run/st_archive IDs in each site ledger (AD5_run_job/AD5_archive_job).
def job_ids(site):
    obj=json.loads(B.ledger_path(site).read_text())
    runid,archid=obj.get("AD5_run_job"),obj.get("AD5_archive_job")
    if not (runid and archid and str(runid).isdigit() and str(archid).isdigit()):
        stop(site+": AD5 run/archive job IDs missing from Stage11 ledger; record them first")
    return str(runid),str(archid)

POINTERS=(("rpointer.lnd","clm2"),("rpointer.atm","datm"),("rpointer.cpl","cpl"))
ATTEMPT="AD395_CONTINUATION_ATTEMPTED_UNCERTAIN"
READY="AD395_CONTINUATION_SUBMITTED"

def stop(s):
    raise RuntimeError(str(s))

def shell(argv,cwd=None,timeout=90):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,text=True,
                     capture_output=True,timeout=timeout)
    if p.returncode:
        stop("Command failed "+repr(argv)+" "+(p.stdout+p.stderr)[-1200:])
    return p.stdout.strip()

def load_state(site):
    path=B.ledger_path(site)
    if not path.is_file() or path.is_symlink():
        stop(site+": expected existing Stage11 submission state")
    obj=json.loads(path.read_text())
    if obj.get("phase")!="FIRST_5Y_SUBMITTED":
        stop(site+": do not repeat continuation; ledger phase="+str(obj.get("phase")))
    if obj.get("case")!=str(B.case_path(site)) or obj.get("surface")!=str(B.surface(site)):
        stop(site+": Stage11 state case/surface mismatch")
    if not obj.get("CIME_env_case_lock_restored") or not obj.get("private_overlay"):
        stop(site+": private Stage12 recovery receipt missing")
    if B.digest(B.surface(site))!=obj.get("surface_sha256"):
        stop(site+": model surface has changed")
    return obj

def accounting():
    ids=[x for site in B.SITE_ORDER for x in job_ids(site)]
    rows=shell(["sacct","-X","-j",",".join(ids),"-n","-P",
                "--format=JobIDRaw,JobName%128,State,ExitCode"],timeout=60)
    got={}
    for line in rows.splitlines():
        parts=[p.strip() for p in line.split("|")]
        if len(parts)>=4 and parts[0] in ids:
            got[parts[0]]=tuple(parts[1:4])
    for site in B.SITE_ORDER:
        runid,archid=job_ids(site)
        for number,jobname in ((runid,"run."+B.case_name(site)),
                               (archid,"st_archive."+B.case_name(site))):
            expected=(jobname,"COMPLETED","0:0")
            if got.get(number)!=expected:
                stop(site+": Slurm "+number+" is "+repr(got.get(number))+
                     " expected "+repr(expected))
    return got

def active_jobs():
    out=shell(["squeue","-u",B.SLURM_USER,"-h","-o","%j"],timeout=45)
    targets={"run."+B.case_name(s) for s in B.SITE_ORDER}
    targets.update({"st_archive."+B.case_name(s) for s in B.SITE_ORDER})
    active=set(out.splitlines()) & targets
    if active:
        stop("Some Batch03 model/archive jobs remain in queue: "+repr(sorted(active)))

def checkpoint(site):
    case=B.case_path(site)
    d=B.xmlquery(case,"RUN_STARTDATE")
    if not re.fullmatch(r"\d{4}-01-01",d):
        stop(site+": unsupported non-Jan01 RUN_STARTDATE "+d)
    yr=int(d[:4])+5
    return f"{yr:04d}-01-01-00000",yr

def archives(site):
    time,yr=checkpoint(site)
    folder=B.archive_path(site)/"rest"/time
    if not folder.is_dir():
        stop(site+": expected archived rest folder "+str(folder))
    files={}
    for _,component in POINTERS:
        p=folder/(B.case_name(site)+"."+component+".r."+time+".nc")
        if not p.is_file() or p.is_symlink() or p.stat().st_size<1024:
            stop(site+": missing archived "+component+" restart: "+str(p))
        files[component]=p
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(files["clm2"]),"r") as ds:
        if "spinup_state" in ds.variables:
            a=np.asarray(ds.variables["spinup_state"][:]).ravel()
            if a.size!=1:
                stop(site+": invalid CLM spinup_state array shape")
            state=int(a[0])
        elif "spinup_state" in ds.ncattrs():
            state=int(ds.getncattr("spinup_state"))
        else:
            stop(site+": land restart has no spinup_state")
    if state!=2:
        stop(site+": land restart spinup_state is "+str(state)+" rather than 2")
    return files,yr

def one_pointer(site,pointer,source):
    rundir=B.run_path(site)
    p=rundir/pointer
    if p.exists() or p.is_symlink():
        if not p.is_file() or p.is_symlink():
            stop(site+": unsafe restart pointer "+str(p))
        lines=[x.strip().strip("'\"") for x in p.read_text().splitlines() if x.strip()]
        if len(lines)!=1 or lines[0] not in (source.name,"./"+source.name):
            stop(site+": restart pointer not at AD5 checkpoint "+pointer+" "+repr(lines))
    local=rundir/source.name
    if local.exists() or local.is_symlink():
        if not local.is_file() or local.is_symlink() or B.digest(local)!=B.digest(source):
            stop(site+": RUNDIR restart conflicts with archived restart "+str(local))

def audit_one(site):
    obj=load_state(site)
    case=B.case_path(site)
    if not case.is_dir() or case.is_symlink():
        stop(site+": independent CIME case directory absent")
    if B.xmlquery(case,"CASE")!=B.case_name(site):
        stop(site+": wrong case identity")
    for key,desired in (("CONTINUE_RUN","false"),("RESUBMIT","0"),
                        ("CLM_ACCELERATED_SPINUP","on"),
                        ("STOP_N","5"),("REST_N","5"),
                        ("RESUBMIT_SETS_CONTINUE_RUN","true")):
        got=B.xmlquery(case,key).lower()
        if got!=desired:
            stop(site+": CIME "+key+"="+got+" expected "+desired)
    if B.xmlquery(case,"CLM_BLDNML_OPTS").split()!=B.BGC_OPTS.split():
        stop(site+": BGC mode changed from FATES")
    cs=case/"CaseStatus"
    if not cs.is_file():
        stop(site+": no CIME CaseStatus")
    text=cs.read_text(errors="replace")
    if not re.search(r"case\.run success",text):
        stop(site+": CIME model success missing")
    if not re.search(r"(?:case\.)?st_archive success",text):
        stop(site+": CIME archive success missing")
    doc=case/"CaseDocs/lnd_in"
    run=B.run_path(site)/"lnd_in"
    if not doc.is_file() or not run.is_file() or B.digest(doc)!=B.digest(run):
        stop(site+": generated CIME land namelists differ/missing")
    for key,val in (("spinup_state","2"),
                    ("use_fates",".true."),
                    ("use_fates_sp",".false."),
                    ("use_fates_nocomp",".true."),
                    ("use_fates_fixed_biogeog",".true."),
                    ("fsurdat",str(B.surface(site)))):
        if B.nml_get(doc.read_text(),key)!=val:
            stop(site+": generated namelist mismatch "+key)
    cfg=case/".submit_options"
    if not cfg.is_file():
        stop(site+": CIME .submit_options absent; resubmitted preview might corrupt AD namelist")
    cp=configparser.RawConfigParser()
    cp.read(cfg)
    if not cp.has_section("SubmitOptions") or not cp.getboolean(
            "SubmitOptions","skip_pnl",fallback=False):
        stop(site+": --skip-preview-namelist not persisted in CIME submit options")
    if (B.OUT_BASE/site/"AD395_restart_handoff").exists():
        stop(site+": AD395 handoff already exists; duplicate/recovery not automatic")
    files,yr=archives(site)
    for ptr,comp in POINTERS:
        one_pointer(site,ptr,files[comp])
    print(site,"AD5 RESTART PASS",str(yr)+"-01-01",
          "clm2+datm+cpl spinup_state=2",flush=True)
    return obj,files,yr

def audit_batch():
    accounting()
    active_jobs()
    approved={}
    for site in B.SITE_ORDER:
        approved[site]=audit_one(site)
    print("BATCH03 AUDIT PASS: 10/10 AD5 run+archive Slurm success,"
          " 10/10 complete AD-state three-component restarts."
          " All eligible for 395-year continuation.",flush=True)
    return approved

def handoff(site,files,yr):
    rundir=B.run_path(site)
    if not rundir.is_dir():
        stop(site+": RUN folder absent")
    hand=B.OUT_BASE/site/"AD395_restart_handoff"
    hand.mkdir(parents=True,exist_ok=False)
    data={"site":site,"checkpoint_year":yr,"files":{}}
    # Backup all existing pointer values BEFORE writing new pointers.
    for ptr,comp in POINTERS:
        source=files[comp]
        p=rundir/ptr
        data["files"][ptr]={"source":str(source),
                            "sha256":B.digest(source),
                            "prior_pointer":p.read_text() if p.is_file() else None}
        if p.is_file():
            shutil.copy2(p,hand/(ptr+".before"))
    (hand/"manifest.json").write_text(json.dumps(data,indent=2)+"\n")
    for ptr,comp in POINTERS:
        source=files[comp]
        target=rundir/source.name
        if not target.exists():
            shutil.copy2(source,target)
        if B.digest(target)!=data["files"][ptr]["sha256"]:
            stop(site+": restart source and staged copy differ")
    for ptr,comp in POINTERS:
        p=rundir/ptr
        tmp=rundir/(ptr+".AD395_tmp")
        if tmp.exists() or tmp.is_symlink():
            stop(site+": temporary pointer already present "+str(tmp))
        tmp.write_text(files[comp].name+"\n")
        os.replace(tmp,p)
        one_pointer(site,ptr,files[comp])

def continue_one(site,data):
    obj,files,yr=data
    # No retry after uncertain handoff or submission. Write ledger before any writes.
    ledger=B.ledger_path(site)
    obj["phase"]=ATTEMPT
    obj["continuation_started_utc"]=datetime.now(timezone.utc).isoformat()
    obj["AD5_verified_checkpoint_year"]=yr
    obj["remaining_years"]=395
    obj["remaining_five_year_segments"]=79
    obj["intended_final_year"]=yr+395
    ledger.write_text(json.dumps(obj,indent=2)+"\n")
    handoff(site,files,yr)
    case=B.case_path(site)
    shell([case/"xmlchange","CONTINUE_RUN=TRUE"],cwd=case)
    shell([case/"xmlchange","RESUBMIT=78"],cwd=case)
    if B.xmlquery(case,"CONTINUE_RUN").lower()!="true" or B.xmlquery(case,"RESUBMIT")!="78":
        stop(site+": CIME continuation setting not applied")
    print(site,"SUBMIT 395-year AD continuation",yr,"->",yr+395,flush=True)
    out=shell([case/"case.submit","--skip-preview-namelist"],cwd=case,timeout=360)
    matchrun=re.search(r"Submitted job case\.run with id (\d+)",out)
    matcharch=re.search(r"Submitted job case\.st_archive with id (\d+)",out)
    if not matchrun or not matcharch:
        stop(site+": case.submit response unparseable. DO NOT RETRY. "+out[-700:])
    obj["phase"]=READY
    obj["continuation_run_job"]=matchrun.group(1)
    obj["continuation_archive_job"]=matcharch.group(1)
    ledger.write_text(json.dumps(obj,indent=2)+"\n")
    print(site,"AD395 SUBMITTED run=",matchrun.group(1),
          "archive=",matcharch.group(1),"NO DUPLICATE SUBMIT",flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","audit","continue-395"))
    p.add_argument("--confirm",default="")
    args=p.parse_args()
    if args.action=="self-test":
        assert len(B.SITE_ORDER)==10 and B.SITE_TAG=="B03"
        assert ACK.startswith("CONTINUE_BATCH03")
        assert [c for _,c in POINTERS]==["clm2","datm","cpl"]
        print("BATCH03 STAGE13 SELF-TEST PASS (no HPC access, no writes)")
        return
    if args.action=="audit":
        audit_batch()
        return
    if args.confirm!=ACK:
        stop("Explicit confirmation required: --confirm "+ACK)
    approved=audit_batch()  # Strict all-ten preflight before any write.
    problems=[]
    for site in B.SITE_ORDER:
        try:
            continue_one(site,approved[site])
        except Exception as exc:
            problems.append(site)
            print("HOLD",site,str(exc)[-950:],"DO NOT RETRY THIS SITE",flush=True)
    print("BATCH03 AD395 submit summary:",len(B.SITE_ORDER)-len(problems),"/10",flush=True)
    if problems:
        stop("Some AD395 submissions are uncertain: "+",".join(problems)+
             "; inspect each site's ledger/Slurm; never rerun bulk continuation")
    print("TEN AD395 continuations submitted. This is NOT confirmation they finished.")

if __name__=="__main__":
    main()
