#!/usr/bin/env python3
"""Batch02 4-site AD5->AD395 continuation, based on proven DE-Tha Stage11.

AUDIT: READ ONLY. Verifies exact initial run/archive sacct COMPLETED/0:0,
three archived CLM/DATM/CPL restarts, land spinup_state=2, original AD
namelist, CIME continue/resubmit settings, and preserved --skip-preview-namelist.

CONTINUE-395: ONLY after 4/4 pass audit; for each isolated new case, set
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
import json
import os
import re
import resource
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class B:
    BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
    OUT_BASE=BASE/"experiments/NonCompetitionObserved22/Batch02_10"
    OUTPUTS=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
    SITE_ORDER=("FI-Hyy","FR-Hes","CH-Fru","IT-MBo")
    BGC_OPTS="--bgc fates --no-megan --no-drydep --no-fire_emis"
    @staticmethod
    def case_name(s): return s+"_B02_FIXNC_AD400"
    @staticmethod
    def case_path(s): return B.BASE/"cases"/B.case_name(s)
    @staticmethod
    def run_path(s): return B.OUTPUTS/B.case_name(s)/"run"
    @staticmethod
    def archive_path(s): return B.OUTPUTS/"archive"/B.case_name(s)
    @staticmethod
    def ledger_path(s): return B.OUT_BASE/s/"AD5_case_state.json"
    @staticmethod
    def surface(s): return Path(json.loads(B.ledger_path(s).read_text())["surface"])
    @staticmethod
    def digest(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
        return h.hexdigest()
    @staticmethod
    def xmlquery(case,key):
        p=subprocess.run([str(case/"xmlquery"),key,"--value"],cwd=case,capture_output=True,text=True,timeout=60)
        if p.returncode: raise RuntimeError("xmlquery failed "+key+" "+p.stderr[-900:])
        return p.stdout.strip()
    @staticmethod
    def nml_get(text,key):
        m=re.findall(r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[ \t]*([^\r\n!]*)",text)
        if len(m)!=1: raise RuntimeError("Missing or duplicate namelist key "+key)
        return m[0].strip().rstrip(",").strip().strip("'\"")

ACK="CONTINUE_BATCH02_FOUR_VERIFIED_AD5_BY_395_YEARS"
# Exact initial AD5 Slurm job IDs from first CIME Batch01 submission, 2026-10-24.
IDS={
 "FI-Hyy":("4728292","4728293"),
 "FR-Hes":("4728294","4728295"),
 "CH-Fru":("4728296","4728297"),
 "IT-MBo":("4728298","4728299"),
}
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
        stop(site+": Stage09 ledger absent")
    obj=json.loads(path.read_text())
    if obj.get("phase")!="FIRST_5Y_RESUBMITTED_STACK_GUARD":
        stop(site+": AD5 ledger phase does not permit continuation: "+str(obj.get("phase")))
    if obj.get("site")!=site or obj.get("case")!=str(B.case_path(site)):
        stop(site+": Stage09 ledger case identity mismatch")
    if (obj.get("active_run_job"),obj.get("active_archive_job"))!=IDS[site]:
        stop(site+": Stage09 active jobs do not match audited IDs")
    recpath=B.OUT_BASE/site/"stage09_Batch03_method_retry"/"retry_state.json"
    if not recpath.is_file() or recpath.is_symlink():
        stop(site+": Stage09 receipt absent")
    rec=json.loads(recpath.read_text())
    if (rec.get("phase")!="SUBMITTED" or rec.get("submission_exit_code")!=0
        or (str(rec.get("run_job")),str(rec.get("archive_job")))!=IDS[site]
        or obj.get("stage09_retry_receipt")!=str(recpath)):
        stop(site+": Stage09 receipt not eligible")
    if not obj.get("CIME_env_case_lock_restored") or not obj.get("private_overlay") or not obj.get("skip_preview_persisted"):
        stop(site+": private build-namelist overlay or skip-preview state missing")
    if str(B.surface(site))!=obj.get("surface") or B.digest(B.surface(site))!=obj.get("surface_sha256"):
        stop(site+": surface differs since AD5")
    if B.digest(Path(obj["executable"]))!=obj.get("executable_sha256"):
        stop(site+": compiled executable differs since AD5")
    return obj


def accounting():
    ids=[str(x) for site in B.SITE_ORDER for x in IDS[site]]
    rows=shell(["sacct","-X","-j",",".join(ids),"-n","-P",
                "--format=JobIDRaw,JobName%128,State,ExitCode"],timeout=60)
    got={}
    for line in rows.splitlines():
        parts=[p.strip() for p in line.split("|")]
        if len(parts)>=4 and parts[0] in ids:
            got[parts[0]]=tuple(parts[1:4])
    for site in B.SITE_ORDER:
        runid,archid=IDS[site]
        for number,jobname in ((runid,"run."+B.case_name(site)),
                               (archid,"st_archive."+B.case_name(site))):
            expected=(jobname,"COMPLETED","0:0")
            if got.get(number)!=expected:
                stop(site+": Slurm "+number+" is "+repr(got.get(number))+
                     " expected "+repr(expected))
    return got

def active_jobs():
    out=shell(["squeue","-u","ly3n24","-h","-o","%j"],timeout=45)
    targets={"run."+B.case_name(s) for s in B.SITE_ORDER}
    targets.update({"st_archive."+B.case_name(s) for s in B.SITE_ORDER})
    active=set(out.splitlines()) & targets
    if active:
        stop("Some Batch01 model/archive jobs remain in queue: "+repr(sorted(active)))

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
    if (case/"env_case.xml").read_bytes()!=(case/"LockedFiles/env_case.xml").read_bytes():
        stop(site+": CIME case lock changed")
    if B.xmlquery(case,"CASE")!=B.case_name(site):
        stop(site+": wrong case identity")
    if B.xmlquery(case,"RUN_TYPE").lower()!="startup":
        stop(site+": unexpected RUN_TYPE")
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
    if B.digest(doc)!=obj.get("generated_lnd_in_sha256"):
        stop(site+": original AD5 land namelist changed")
    if B.digest(Path(B.nml_get(doc.read_text(),"fates_paramfile")))!=obj.get("parameter_sha256"):
        stop(site+": FATES parameter bytes changed")
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
    if (B.OUT_BASE/site/"AD395_continuation_attempt.json").exists():
        stop(site+": prior AD395 attempt exists; never re-submit")
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
    print("BATCH02 AUDIT PASS: 4/4 AD5 run+archive Slurm success,"
          " 4/4 complete AD-state three-component restarts."
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
    marker=B.OUT_BASE/site/"AD395_continuation_attempt.json"
    with marker.open("x") as f:
        json.dump({"site":site,"phase":ATTEMPT,"utc":datetime.now(timezone.utc).isoformat()},f)
        f.write("\n");f.flush();os.fsync(f.fileno())
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
    marker.write_text(json.dumps({"site":site,"phase":READY,
                 "run_job":matchrun.group(1),"archive_job":matcharch.group(1)},indent=2)+"\n")
    obj["continuation_run_job"]=matchrun.group(1)
    obj["continuation_archive_job"]=matcharch.group(1)
    ledger.write_text(json.dumps(obj,indent=2)+"\n")
    print(site,"AD395 SUBMITTED run=",matchrun.group(1),
          "archive=",matcharch.group(1),"NO DUPLICATE SUBMIT",flush=True)

def stack_guard():
    cfg=shell(["scontrol","show","config"])
    m=re.search(r"(?m)^\s*PropagateResourceLimits\s*=\s*(\S+)",cfg)
    if not m or m[1]!="ALL":stop("Stage09 stack policy requires PropagateResourceLimits=ALL")
    override=os.environ.get("SBATCH_PROPAGATE","")
    if override and not ({"ALL","STACK"} & set(override.split(","))):
        stop("SBATCH_PROPAGATE excludes STACK")
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    target=soft
    if soft!=resource.RLIM_INFINITY and soft<64*1024*1024:
        if hard!=resource.RLIM_INFINITY and hard<64*1024*1024:
            stop("Submit stack hard limit less than 64MiB")
        target=resource.RLIM_INFINITY if hard==resource.RLIM_INFINITY else min(hard,300000*1024)
        resource.setrlimit(resource.RLIMIT_STACK,(target,hard))
    print("STAGE10 STACK",soft,"->",target,"host",socket.gethostname(),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("audit","continue-395"))
    p.add_argument("--confirm",default="")
    args=p.parse_args()
    if args.action=="audit":
        audit_batch()
        return
    if args.confirm!=ACK:
        stop("Explicit confirmation required: --confirm "+ACK)
    stack_guard()
    approved=audit_batch()  # Strict all-four preflight before any write.
    batch=B.OUT_BASE/"_stage10_four_AD395_continuation_attempt.json"
    with batch.open("x") as f:
        json.dump({"version":"batch02-stage10-v1","phase":ATTEMPT,"sites":list(B.SITE_ORDER)},f)
        f.write("\n");f.flush();os.fsync(f.fileno())
    problems=[]
    for site in B.SITE_ORDER:
        try:
            continue_one(site,approved[site])
        except Exception as exc:
            problems.append(site)
            print("HOLD",site,str(exc)[-950:],"DO NOT RETRY THIS SITE",flush=True)
    print("BATCH02 AD395 submit summary:",4-len(problems),"/4",flush=True)
    if problems:
        batch.write_text(json.dumps({"version":"batch02-stage10-v1","phase":"STOPPED_REVIEW_REQUIRED",
                                      "failed_sites":problems},indent=2)+"\n")
        stop("Some AD395 submissions are uncertain: "+",".join(problems)+
             "; inspect each site's ledger/Slurm; never rerun bulk continuation")
    batch.write_text(json.dumps({"version":"batch02-stage10-v1","phase":"FOUR_AD395_SUBMITTED",
                                  "sites":list(B.SITE_ORDER)},indent=2)+"\n")
    print("FOUR AD395 continuations submitted. This is NOT confirmation they finished.")

if __name__=="__main__":
    main()
