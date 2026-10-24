#!/usr/bin/env python3
"""DE-Tha direct AD400: 2001->2396 guarded continuation AFTER one verified smoke.

Before first use:
  Stage10 has submitted ONLY 1996->2001 first five-year cold-start AD job.
  Stage11 audit insists both Slurm run/archive jobs COMPLETED/0:0, CIME
  success, archived cpl/datm/clm2 restarts at 2001-01-01, and
  land restart spinup_state=2. It also checks the pinned v2 surface and
  the persistent .submit_options skip_pnl=True.

If everything passes, 'continue-395' stages ONLY the 2001 AD restart in its
own RUNDIR, backs up old pointers, sets CONTINUE_RUN=TRUE, RESUBMIT=78
(2001->2006 + 78 subsequent 5y jobs) and submits ONCE.
The 1996->2001 segment plus 395 more model years = 400 yrs (1996->2396).

No external watchdog, no PRE50, no POST stage, no unrelated jobs/cases touched.
Do not retry after an uncertain submission or partial pointer handoff.
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
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("DETha_AD400_stage10",HERE/"10_DE_Tha_direct_AD400.py")
if not spec or not spec.loader:
    raise RuntimeError("Missing stage10 script")
C=importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

CONFIRM="CONTINUE_VERIFIED_DE_THA_AD400_FROM_2001_TO_2396"
REST=C.ARCH/"rest/2001-01-01-00000"
HANDOFF=C.WORK/"2001_restart_handoff"
POINTERS=(("rpointer.lnd","clm2"),("rpointer.atm","datm"),("rpointer.cpl","cpl"))

def fail(s):raise RuntimeError(str(s))

def accounting(runid,archid):
    text=C.run(["sacct","-X","-j",f"{runid},{archid}","-n","-P",
                "--format=JobIDRaw,JobName%128,State,ExitCode,Elapsed"],
               timeout=60)
    rows={}
    for line in text.splitlines():
        c=line.split("|")
        if len(c)>3 and c[0].strip() in (runid,archid):
            rows[c[0].strip()]=tuple(x.strip() for x in c[1:4])
    for job,jobname in ((runid,"run."+C.NAME),(archid,"st_archive."+C.NAME)):
        if rows.get(job)!=(jobname,"COMPLETED","0:0"):
            fail(f"Slurm {job} {jobname} not completed successfully: {rows.get(job)}")
    print("PASS Slurm model/archive jobs:",runid,archid)

def archive_restart(component):
    filename=f"{C.NAME}.{component}.r.2001-01-01-00000.nc"
    file=REST/filename
    if not file.is_file() or file.is_symlink() or file.stat().st_size<1024:
        fail("Missing or too small independent AD restart: "+str(file))
    return file

def spinup_state():
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(archive_restart("clm2"),"r") as ds:
        if "spinup_state" in ds.variables:
            values=np.asarray(ds.variables["spinup_state"][:]).ravel()
            if values.size!=1:fail("Unexpected CLM spinup_state shape")
            return int(values[0])
        if "spinup_state" in ds.ncattrs():
            return int(ds.getncattr("spinup_state"))
    fail("Restart has no spinup_state; cannot continue")

def check_pointer(ptr,comp):
    p=C.RUN/ptr
    if p.exists() and (not p.is_file() or p.is_symlink()):
        fail("Unsafe active pointer (not regular file): "+str(p))
    expected=archive_restart(comp).name
    if p.is_file():
        lines=[line.strip().strip("'\"") for line in p.read_text().splitlines() if line.strip()]
        if len(lines)!=1:fail("Unexpected rpointer content: "+str(p))
        raw=lines[0]
        loc=Path(raw)
        if loc.is_absolute() or ".." in loc.parts or len(loc.parts)!=1 or raw not in (loc.name,"./"+loc.name):
            fail("Unsafe relative restart pointer: "+str(p)+" => "+raw)
        if loc.name!=expected:
            fail("Active pointer not 2001 restart: "+ptr+"="+raw)
    local=C.RUN/expected
    if local.exists():
        if not local.is_file() or local.is_symlink() or C.sha(local)!=C.sha(REST/expected):
            fail("Run restart differs from verified archive: "+str(local))
    print(f"RESTART {ptr} expected {expected} pointer_present={p.is_file()} local_present={local.exists()}")
    return p.is_file() and local.is_file()

def audit():
    C.verify_surface()
    if not C.STATE.is_file() or not C.CASE.is_dir():
        fail("Original Stage10 case/controller not found")
    d=json.loads(C.STATE.read_text())
    if d.get("stage")!="FIRST_5Y_SUBMITTED" or d.get("experiment")!="DIRECT_AD400_COLDSTART":
        fail("First 5-year state not recorded as submitted; no continuation")
    if C.queue_matches():
        fail("Stage10 case still has queued model/archive jobs")
    runid=str(d.get("first_run_job",""))
    archid=str(d.get("first_archive_job",""))
    if not re.fullmatch(r"\d+",runid) or not re.fullmatch(r"\d+",archid):
        fail("Stage10 job IDs missing/invalid")
    accounting(runid,archid)
    log=(C.CASE/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",log) or not re.search(r"(?:case\.)?st_archive success",log):
        fail("CIME CaseStatus does not show successful run and archive")
    if not REST.is_dir():fail("First archived AD checkpoint missing: "+str(REST))
    for _,component in POINTERS:archive_restart(component)
    actual=spinup_state()
    if actual!=2:fail("First AD restart spinup_state is not 2: "+str(actual))
    if C.xml(C.CASE,"CONTINUE_RUN").lower()!="false" or C.xml(C.CASE,"RESUBMIT")!="0":
        fail("Case already resumed or modified, do not duplicate")
    if C.xml(C.CASE,"CLM_ACCELERATED_SPINUP").lower()!="on":
        fail("AD mode CIME flag not on")
    if C.xml(C.CASE,"STOP_N")!="5" or C.xml(C.CASE,"REST_N")!="5":
        fail("Expected 5-year run/rest parameters")
    if C.xml(C.CASE,"RESUBMIT_SETS_CONTINUE_RUN").lower()!="true":
        fail("CIME does not guarantee CONTINUE_RUN after resubmissions")
    original_lnd=C.CASE/"CaseDocs/lnd_in"
    running_lnd=C.RUN/"lnd_in"
    if not original_lnd.is_file() or not running_lnd.is_file():
        fail("CaseDocs/RUNDIR generated namelist missing")
    if C.sha(original_lnd)!=C.sha(running_lnd):
        fail("CaseDocs vs RUNDIR land namelists disagree")
    for f in (original_lnd,running_lnd):
        s=f.read_text()
        for k,v in (("spinup_state","2"),("use_fates_nocomp",".true."),
                    ("use_fates_fixed_biogeog",".true."),("fsurdat",str(C.SURFACE))):
            if C.nml_value(s,k)!=v:
                fail(f"Unexpected generated {k} in {f}")
    opts=C.CASE/".submit_options"
    if not opts.is_file():fail("No persisted CIME --skip-preview-namelist option")
    cfg=configparser.RawConfigParser()
    cfg.read(opts)
    if not cfg.has_section("SubmitOptions") or not cfg.getboolean(
            "SubmitOptions","skip_pnl",fallback=False):
        fail("CIME skip_pnl is not persisted; resubmits could alter AD namelist")
    if HANDOFF.exists():
        fail("Handoff already attempted; DO NOT re-run")
    for ptr,comp in POINTERS:check_pointer(ptr,comp)
    print("PASS: 2001 AD restart has spinup_state=2 and all three components")
    print("PASS: no queued jobs, accurate generated namelists and submit_options")
    print("AUDIT PASSED: 395 remaining model years 2001->2396 can be resumed")
    return d

def stage_restart():
    if HANDOFF.exists():fail("Handoff already exists, do not duplicate")
    HANDOFF.mkdir(parents=True,exist_ok=False)
    ledger={"archived_ref":str(REST),"files":{}}
    for ptr,comp in POINTERS:
        source=archive_restart(comp)
        pointer=C.RUN/ptr
        ledger["files"][ptr]={"expected":source.name,"source_sha256":C.sha(source)}
        if pointer.exists():
            shutil.copy2(pointer,HANDOFF/(ptr+".before"))
            ledger["files"][ptr]["previous_pointer"]=pointer.read_text()
        else:
            ledger["files"][ptr]["previous_pointer"]=None
    (HANDOFF/"manifest.json").write_text(json.dumps(ledger,indent=2)+"\n")
    # All source checksums pinned in manifest before new pointer generation.
    for ptr,comp in POINTERS:
        source=archive_restart(comp)
        target=C.RUN/source.name
        if target.exists():
            if C.sha(target)!=C.sha(source):
                fail("Existing local restart differs: "+str(target))
        else:
            shutil.copy2(source,target)
        if C.sha(target)!=C.sha(source):
            fail("Copied AD restart SHA256 mismatch: "+str(target))
    for ptr,comp in POINTERS:
        pointer=C.RUN/ptr
        expected=archive_restart(comp).name
        tmp=C.RUN/(ptr+".stage2001tmp")
        if tmp.exists():
            fail("Temporary rpointer already exists: "+str(tmp))
        tmp.write_text(expected+"\n")
        os.replace(tmp,pointer)
    if not all(check_pointer(ptr,comp) for ptr,comp in POINTERS):
        fail("Not all AD 2001 pointers/files staged")
    print("PASS: 2001 pointers and checkpoint files staged in isolated RUN only")

def continue_395():
    d=audit()
    d["stage"]="CONTINUATION_ATTEMPTED_UNCERTAIN"
    d["continuation_target_end"]=2396
    d["remaining_model_years"]=395
    d["remaining_segments"]=79
    C.STATE.write_text(json.dumps(d,indent=2)+"\n")
    stage_restart()
    C.change("CONTINUE_RUN","TRUE")
    C.change("RESUBMIT","78")
    if C.xml(C.CASE,"CONTINUE_RUN").lower()!="true" or C.xml(C.CASE,"RESUBMIT")!="78":
        fail("CIME continuation XML values not applied")
    print("SUBMIT: 2001-2006 plus 78 auto resubmits, ending 2396",flush=True)
    output=C.run(["./case.submit","--skip-preview-namelist"],cwd=C.CASE,timeout=300,verbose=True)
    runid=re.search(r"Submitted job case\.run with id (\d+)",output)
    archid=re.search(r"Submitted job case\.st_archive with id (\d+)",output)
    if not runid or not archid:
        fail("Submitted but job IDs unparseable. DO NOT retry this command")
    d=json.loads(C.STATE.read_text())
    d["stage"]="CONTINUATION_SUBMITTED"
    d["continuation_run_job"]=runid.group(1)
    d["continuation_archive_job"]=archid.group(1)
    C.STATE.write_text(json.dumps(d,indent=2)+"\n")
    print("CONTINUATION SUBMITTED: 395 years, run",runid.group(1),
          "archive",archid.group(1),flush=True)
    print("Do not re-run continue-395. Model completion/convergence not established.")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("audit","continue-395"))
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="audit":audit()
    else:
        if a.confirm!=CONFIRM:
            fail("Continuation requires --confirm "+CONFIRM)
        continue_395()

if __name__=="__main__":main()
