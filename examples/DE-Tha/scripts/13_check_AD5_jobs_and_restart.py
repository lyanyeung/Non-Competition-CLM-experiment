#!/usr/bin/env python3
"""DE-Tha direct AD400 1996->2001: independent READ-ONLY Slurm/restart audit.

Always distinguishes DE-Tha case/job from NL-Loo, even if squeue abbreviates.
User-facing statuses are NOT_SUBMITTED, QUEUED_OR_RUNNING, INCOMPLETE_HOLD,
FAILED_HOLD or VERIFIED_AD5_ARCHIVED.

Never modifies any CIME case, restart, file, Slurm job or Git repository.
"""
from __future__ import annotations
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("DETha_AD400_source",HERE/"10_DE_Tha_direct_AD400.py")
if spec is None or spec.loader is None:raise RuntimeError("Stage10 import failed")
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

def call(args):
    p=subprocess.run(args, text=True, capture_output=True, timeout=75, check=False)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)} failed: {p.stderr[-700:]}")
    return p.stdout.strip()

def main():
    print("=== DE-Tha AD400 FIRST 5 MODEL YEARS — READ ONLY ===",flush=True)
    print("EXPECTED EXACT CASE:",C.NAME,flush=True)
    print("INITIAL AD PERIOD: 1996-01-01 to 2001-01-01")
    print("CIME CASE:",C.CASE,"exists",C.CASE.is_dir())
    print("SOURCE AD RUNDIR:",C.RUN,"exists",C.RUN.is_dir())
    print("ARCHIVE:",C.ARCH,"exists",C.ARCH.is_dir())
    print("\n=== EXACT SLURM NAME MATCH (DO NOT TRUST squeue TRUNCATION) ===")
    active=call(["squeue","-u",C.USER,"-h","-o","%i|%j|%T|%R"])
    target={"run."+C.NAME,"st_archive."+C.NAME}
    actual=[x for x in active.splitlines()
            if len(x.split("|"))>=3 and x.split("|")[1] in target]
    print("DE-Tha active jobs:",actual if actual else "NONE")
    other=[x for x in active.splitlines() if len(x.split("|"))>=3 and (
           x.split("|")[1].startswith("run.NL-Loo_") or
           x.split("|")[1].startswith("st_archive.NL-Loo_"))]
    print("Separate NL-Loo jobs:",other if other else "NONE")
    if not C.STATE.is_file():
        print("STATE: NOT_SUBMITTED_OR_LEDGER_MISSING")
        print("NOTE: if a manual submission occurred, investigate CaseStatus/sacct")
        return
    state=json.loads(C.STATE.read_text(encoding="utf-8"))
    print("\nLEDGER stage:",state.get("stage","MISSING"))
    runid=str(state.get("first_run_job") or "")
    arcid=str(state.get("first_archive_job") or "")
    print("LEDGER first_run_job:",runid or "NONE")
    print("LEDGER first_archive_job:",arcid or "NONE")
    if C.CASE.is_dir():
        cs=C.CASE/"CaseStatus"
        if cs.is_file():
            print("\n=== LAST CASESTATUS ENTRIES ===")
            for line in cs.read_text(errors="replace").splitlines()[-24:]:
                print(line)
    if not runid or not arcid:
        print("\nSTATUS: NO_VERIFIED_FIRST5_SUBMISSION (ledger lacks both Slurm IDs)")
        print("Do NOT infer completion. If an attempted submission was made,")
        print("do not retry until historical Slurm/CaseStatus investigated.")
        return
    if not re.fullmatch(r"\d+",runid) or not re.fullmatch(r"\d+",arcid):
        raise RuntimeError("Ledger Slurm job IDs are not numeric")
    out=call(["sacct","-X","-j",f"{runid},{arcid}","-n","-P",
              "--format=JobIDRaw,JobName%128,State,ExitCode"])
    jobs={}
    for line in out.splitlines():
        x=line.split("|")
        if len(x)>=4 and x[0].strip() in (runid,arcid):
            jobs[x[0].strip()]=tuple(t.strip() for t in x[1:4])
    print("\n=== EXACT SLURM ACCOUNTING ===")
    for job,name in ((runid,"run."+C.NAME),(arcid,"st_archive."+C.NAME)):
        row=jobs.get(job)
        print(job,row or "MISSING_ACCOUNTING")
        if row and row[0]!=name:
            raise RuntimeError(f"Job ID {job} belongs to {row[0]}, not expected {name}")
    if actual:
        print("\nSTATUS: QUEUED_OR_RUNNING — do not launch 395yr or Normal branch")
        return
    if any((jobs.get(j) or ("","MISSING",""))[1].split()[0] in (
          "FAILED","TIMEOUT","CANCELLED","NODE_FAIL","OUT_OF_MEMORY")
           for j in (runid,arcid)):
        print("\nSTATUS: FAILED_HOLD — investigate logs; never retry blindly")
        return
    if not all(jobs.get(job)==(name,"COMPLETED","0:0")
               for job,name in ((runid,"run."+C.NAME),(arcid,"st_archive."+C.NAME))):
        print("\nSTATUS: INCOMPLETE_HOLD — run or archive not COMPLETED/0:0")
        return
    rest=C.ARCH/"rest/2001-01-01-00000"
    from netCDF4 import Dataset
    import numpy as np
    for component in ("clm2","datm","cpl"):
        p=rest/f"{C.NAME}.{component}.r.2001-01-01-00000.nc"
        if not p.is_file() or p.is_symlink() or p.stat().st_size<1024:
            raise RuntimeError("Failed restart check: "+str(p))
        print("PASS archived",component,p.name,p.stat().st_size,"bytes")
        if component=="clm2":
            with Dataset(p,"r") as d:
                if "spinup_state" in d.variables:
                    a=np.asarray(d.variables["spinup_state"][:]).reshape(-1)
                    if a.size!=1:raise RuntimeError("Unexpected spinup_state shape")
                    state_value=int(a[0])
                elif "spinup_state" in d.ncattrs():
                    state_value=int(d.getncattr("spinup_state"))
                else:
                    raise RuntimeError("Missing spinup_state from archived land restart")
            if state_value!=2:
                raise RuntimeError("Archived land spinup_state not 2: "+str(state_value))
            print("PASS: archived CLM restart spinup_state=2")
    status=(C.CASE/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",status) or not re.search(
            r"(?:case\.)?st_archive success",status):
        raise RuntimeError("CIME CaseStatus lacks both model and archive success")
    C.verify_surface()
    print("\nSTATUS: VERIFIED_AD5_ARCHIVED — first 5 AD years 1996->2001")
    print("TECHNICAL NEXT: independently audit Stage11 for 395yr AD continuation")
    print("OPTIONAL SCIENCE TEST: branch independent normal 5yr from 2001 AD restart")
    print("READ ONLY COMPLETE; no modifications or jobs submitted")

if __name__=="__main__":
    main()
