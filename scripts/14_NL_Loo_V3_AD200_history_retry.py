#!/usr/bin/env python3
"""Fix the two verified FATES history names and safely retry AD200 2047-2052.

Specific incident only: Slurm run 4710529 FAILED before time integration in
histFileMod (missing GPP/NPP); dependent archive 4710530 cannot run.
No cases/build/restarts or other Slurm jobs are touched. PRE50 is retained.
The new smoke test uses --skip-preview-namelist, STOP_N=5, RESUBMIT=0 and
keeps the controller/watcher DISARMED.

  audit          read-only preflight
  repair-submit  backup and change only hist_fincl1 in the 2 generated lnd_in
                 files (+ user_nl_clm provenance), cancel ONLY the verified
                 stale archive 4710530 if still blocked, submit one new 5y job
  status         read-only current state
"""
from __future__ import annotations

import argparse
import configparser
import fcntl
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
def module(file, name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS/file)
    if not spec or not spec.loader:
        raise RuntimeError("Cannot load " + file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

C = module("09_NL_Loo_V3_auto550.py", "nl_v3_history")
STAGE = "AD200"
CASE = C.CASE[STAGE]
RUN = C.RUN[STAGE]
WORK = C.WORK
SRC_JOB = "4710529"
OLD_ARCHIVE = "4710530"
RETRY_KEY = "AD200_history_4710529_five_year_retry"
CONFIRM = "FIX_AD200_HISTORY_CANCEL_4710530_AND_RETRY_5Y"
OLD_FIELDS = ["TOTSOMC", "TOTSOMN", "TLAI", "GPP", "NPP", "TWS", "H2OSNO"]
NEW_FIELDS = ["TOTSOMC", "TOTSOMN", "TLAI", "FATES_GPP", "FATES_NPP", "TWS", "H2OSNO"]
OLD_USER = CASE/"user_nl_clm"
GENERATED = (CASE/"CaseDocs/lnd_in", RUN/"lnd_in")
BACKUP_DIR = WORK/"AD200_history_fix_from_failed_4710529"
LOG = RUN/"lnd.log.4710529.261024-051629"

def stop(msg):
    raise RuntimeError(msg)

def call(args, cwd=None):
    p = subprocess.run([str(v) for v in args], cwd=cwd, capture_output=True,
                       text=True, check=False, timeout=180)
    if p.returncode:
        stop(f"Command failed rc={p.returncode}: {' '.join(map(str,args))}\n"
             f"{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p.stdout.strip()

def slurm():
    output = call(["squeue","-u",C.U,"-h","-o","%i|%j|%T|%r"])
    rows = {}
    for line in output.splitlines():
        v=line.split("|",3)
        if len(v)==4:
            rows[v[0].strip()] = tuple(p.strip() for p in v[1:])
    return rows

def job_history():
    output=call(["sacct","-X","-j",SRC_JOB+","+OLD_ARCHIVE,"-n","-P",
                 "--format=JobIDRaw,JobName%128,State,ExitCode"])
    rows={}
    for line in output.splitlines():
        v=line.split("|")
        if len(v)>=4 and v[0] in (SRC_JOB,OLD_ARCHIVE):
            rows[v[0]]=(v[1].strip(),v[2].strip(),v[3].strip())
    if SRC_JOB not in rows or OLD_ARCHIVE not in rows:
        stop("sacct does not show both incident jobs; inspect Slurm history")
    if rows[SRC_JOB][0] != "run."+C.NAME[STAGE]:
        stop("Original job ID belongs to another case")
    if rows[SRC_JOB][1].split()[0]!="FAILED" or rows[SRC_JOB][2]!="1:0":
        stop(f"Unexpected model job state: {rows[SRC_JOB]}")
    if rows[OLD_ARCHIVE][0] != "st_archive."+C.NAME[STAGE]:
        stop("Original archive job ID belongs to another case")
    if rows[OLD_ARCHIVE][1].split()[0] not in ("PENDING","CANCELLED"):
        stop("Original archive not pending/cancelled: "+repr(rows[OLD_ARCHIVE]))
    return rows

def original_history():
    if not LOG.is_file():
        stop("Original 4710529 lnd.log is missing")
    txt=LOG.read_text(errors="replace")
    if not ("htapes_fieldlist ERROR: GPP in fincl" in txt and
            "Successfully read restart data for restart run" in txt and
            "taking c12 SOM pools into AD spinup mode" in txt):
        stop("Failed model log differs from known history-field incident")
    registered=set(re.findall(r"(?m)^[ \t]*\d+[ \t]+([A-Z][A-Z0-9_]*)[ \t]{2,}",txt))
    if len(registered)<900:
        stop("Incomplete history registry in failed land log")
    for f in NEW_FIELDS:
        if f not in registered:
            stop("Proposed FATES history output unavailable: "+f)
    for f in ("GPP","NPP"):
        if f in registered:
            stop("Original history field unexpectedly registered: "+f)
    print(f"PASS: history registry {len(registered)} fields; FATES_GPP/FATES_NPP exist",flush=True)

def history_line(text):
    matches=list(re.finditer(r"(?im)^([ \t]*hist_fincl1[ \t]*=[ \t]*)([^\r\n]*)$",text))
    if len(matches)!=1:
        stop(f"Expected one hist_fincl1, found {len(matches)}")
    m=matches[0]
    fields=re.findall(r"'([^']+)'",m.group(2))
    if fields not in (OLD_FIELDS, NEW_FIELDS):
        stop(f"Unexpected history field list: {fields}")
    return fields, m

def update_history(text):
    fields,m=history_line(text)
    if fields!=OLD_FIELDS:
        stop("History fields already patched; retry prohibited")
    return text[:m.start(2)] + ",".join("'"+v+"'" for v in NEW_FIELDS) + text[m.end(2):]

def update_user(text):
    found=list(re.finditer(r"(?im)^([ \t]*hist_fincl1[ \t]*=[ \t]*)([^\r\n]*)$",text))
    if len(found)>1:
        stop("Duplicate hist_fincl1 in user_nl_clm")
    if found:
        return update_history(text)
    return text.rstrip("\n") + "\n! NL-Loo AD200: FATES-compatible history flux fields\n" + \
           "hist_fincl1 = " + ",".join("'"+v+"'" for v in NEW_FIELDS) + "\n"

def read_status():
    d=C.load()
    if d.get("armed") is not False or C.STOP.exists():
        stop("Controller armed or STOP marker exists")
    if d.get("actions",{}).get("PRE50_first")!="DONE":
        stop("PRE50 ledger is not complete")
    if d.get("actions",{}).get("AD200_first")!="DONE":
        stop("AD200 first-phase ledger unexpectedly not DONE")
    if d.get("actions",{}).get("AD200_env_case_lock_recovery_smoke")!="DONE":
        stop("Earlier lock recovery was not recorded as submitted")
    if d.get("actions",{}).get("AD200_remaining") is not None:
        stop("AD200 continuation has already been attempted")
    if d.get("actions",{}).get(RETRY_KEY) is not None:
        stop("History fix retry already attempted; do not repeat")
    if not d.get("ad_only") or not d.get("hold_after_first_ad_segment"):
        stop("5-year hold not active")
    if BACKUP_DIR.exists():
        stop("History repair backup folder already exists; inspect manual changes")
    if C.ARCH[STAGE].exists():
        stop("AD200 archive exists, cannot safely retry")
    if (CASE/"CaseStatus").is_file():
        status=(CASE/"CaseStatus").read_text(errors="replace")
        if not (f"case.run starting {SRC_JOB}" in status and
                "case.run error" in status and
                "case.submit success" in status):
            stop("CaseStatus does not match known failed smoke run")
        if re.search(r"(?im)case\.run success|st_archive success",status):
            stop("CaseStatus shows model/archive success; inspect")
    else:
        stop("CaseStatus missing")
    if not (CASE/"V3_first_submission_attempt.json").is_file():
        stop("Original case submission marker missing")
    if C.slurm("PRE50"):
        stop("PRE50 jobs still exist")
    alljobs=slurm()
    expected_archive="st_archive."+C.NAME[STAGE]
    for jid,(name,state,reason) in alljobs.items():
        if name in ("run."+C.NAME[STAGE],expected_archive) and jid!=OLD_ARCHIVE:
            stop(f"Another active AD200 job detected: {jid} {name} {state}")
        if "NL-Loo-V3-watch" in name:
            stop("Watchdog active or queued")
    if OLD_ARCHIVE in alljobs:
        name,state,reason=alljobs[OLD_ARCHIVE]
        if name!=expected_archive or state!="PENDING" or "DependencyNeverSatisfied" not in reason:
            stop(f"Old archive job not safely cancelable: {OLD_ARCHIVE} {name} {state} {reason}")
    job_history()
    if not C.complete("PRE50",2047):
        stop("2047 normal restart not verified")
    if (CASE/"LockedFiles/env_case.xml").read_bytes() != (CASE/"env_case.xml").read_bytes():
        # Locked file must not be edited again. Exact byte equality is stronger
        # than CIME's semantic XML check; if formatting differs, inspect first.
        stop("env_case.xml differs from CIME-locked original; inspect")
    if C.xq(STAGE,"COMP_ROOT_DIR_LND")!=str(C.CTSM) and \
       Path(C.xq(STAGE,"COMP_ROOT_DIR_LND")).resolve()!=C.CTSM.resolve():
        stop("Case no longer points to original shared CTSM root")
    for name,val in (("RUN_TYPE","hybrid"),("RUN_STARTDATE","2047-01-01"),
                     ("RUN_REFDATE","2047-01-01"),("RUN_REFCASE",C.NAME["PRE50"]),
                     ("CLM_ACCELERATED_SPINUP","on"),("STOP_N","5"),
                     ("STOP_OPTION","nyears"),("REST_N","5"),
                     ("REST_OPTION","nyears"),("RESUBMIT","0"),
                     ("CONTINUE_RUN","FALSE"),("DOUT_S","TRUE")):
        if C.xq(STAGE,name).lower()!=val.lower():
            stop(f"Case setting {name} changed unexpectedly")
    if not (CASE/".case.run").is_file():
        stop("Missing case.run script")
    if not OLD_USER.is_file():
        stop("Missing user_nl_clm")
    if not all(p.is_file() for p in GENERATED):
        stop("Missing generated history namelist")
    if C.hashfile(GENERATED[0])!=C.hashfile(GENERATED[1]):
        stop("Generated lnd_in copies differ")
    for p in GENERATED:
        text=p.read_text()
        fields,_=history_line(text)
        if fields!=OLD_FIELDS:
            stop(str(p)+": history fields no longer match original list")
        for key,value in (("spinup_state","2"),("use_fates",".true."),
                          ("use_cn",".false."),("use_fates_nocomp",".true."),
                          ("use_fates_fixed_biogeog",".true.")):
            if C.nml_get(text,key)!=value:
                stop(f"{p}: {key} changed")
    if re.search(r"(?im)^[ \t]*hist_fincl1[ \t]*=",OLD_USER.read_text()):
        f,_=history_line(OLD_USER.read_text())
        if f!=OLD_FIELDS:
            stop("user_nl_clm has a non-original output list")
    # Full restart checksums before allowing rerun from 2047.
    src=C.ARCH["PRE50"]/"rest"/"2047-01-01-00000"
    for comp in ("clm2","cpl","datm"):
        name=f"{C.NAME['PRE50']}.{comp}.r.2047-01-01-00000.nc"
        a,b=src/name,RUN/name
        if not (a.is_file() and b.is_file()) or C.hashfile(a)!=C.hashfile(b):
            stop("2047 restart file changed: "+name)
    for ptr in ("rpointer.lnd","rpointer.cpl","rpointer.atm"):
        if not (RUN/ptr).is_file():
            stop("Missing active 2047 restart pointer: "+ptr)
    # Prior job was submitted with this option; insist on same behavior again.
    options=CASE/".submit_options"
    cfg=configparser.RawConfigParser()
    if not options.is_file() or not cfg.read(options) or \
       not cfg.getboolean("SubmitOptions","skip_pnl",fallback=False):
        stop("Earlier --skip-preview-namelist submission config missing")
    original_history()
    print("PASS: failed job 4710529; old archive 4710530 only stale dependent job",flush=True)
    print("PASS: verified FATES AD state=2; PRE50 2047 restarts unchanged",flush=True)
    print("PASS: only GPP/NPP invalid; no newer AD200 job; watchdog disarmed",flush=True)
    print("PLAN: GPP -> FATES_GPP; NPP -> FATES_NPP; single 5-year retry",flush=True)
    return d,alljobs

def atomic_write(path, data):
    tmp=path.with_name(path.name+".history_fix_tmp")
    if tmp.exists():
        stop("Temporary file already exists: "+str(tmp))
    tmp.write_text(data)
    os.chmod(tmp,path.stat().st_mode & 0o777)
    os.replace(tmp,path)

def repair_and_submit():
    d,alljobs=read_status()
    C.validate_base()
    C.quota()
    d,alljobs=read_status() # fail if jobs appeared while validating
    d["actions"][RETRY_KEY]="ATTEMPTED"
    d["armed"]=False
    C.save(d)

    BACKUP_DIR.mkdir(parents=True,exist_ok=False)
    originals=[*GENERATED,OLD_USER]
    manifest={}
    for i,p in enumerate(originals):
        backup=BACKUP_DIR/("before_"+str(i)+"_"+p.name)
        shutil.copy2(p,backup)
        manifest[str(p)]={"before_sha256":C.hashfile(p),"backup":str(backup)}
    (BACKUP_DIR/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")

    for p in GENERATED:
        atomic_write(p,update_history(p.read_text()))
    atomic_write(OLD_USER,update_user(OLD_USER.read_text()))
    if C.hashfile(GENERATED[0])!=C.hashfile(GENERATED[1]):
        stop("Patched generated namelists differ; HOLD")
    for p in GENERATED:
        text=p.read_text()
        f,_=history_line(text)
        if f!=NEW_FIELDS or C.nml_get(text,"spinup_state")!="2":
            stop("Post-patch AD namelist verification failed")
    C.check(STAGE)
    print("PASS: patched AD200 history only; originals backed up:",BACKUP_DIR,flush=True)

    # Remove only the obsolete blocked dependent archive, never any model jobs.
    if OLD_ARCHIVE in alljobs:
        newer=slurm()
        if OLD_ARCHIVE not in newer or newer[OLD_ARCHIVE]!=alljobs[OLD_ARCHIVE]:
            stop("Old archive state changed before cancellation")
        call(["scancel",OLD_ARCHIVE])
        print("CANCELLED obsolete blocked archive 4710530 only",flush=True)
    for jid,(name,state,reason) in slurm().items():
        if name in ("run."+C.NAME[STAGE],"st_archive."+C.NAME[STAGE]):
            stop(f"An AD200 job is still active/queued: {jid} {name}")
    print("SUBMITTING --skip-preview-namelist RESUBMIT=0 STOP_N=5",flush=True)
    result=call(["./case.submit","--skip-preview-namelist"],cwd=CASE)
    print(result[-4000:],flush=True)
    match=re.search(r"Submitted job case\.run with id (\d+)",result)
    arch=re.search(r"Submitted job case\.st_archive with id (\d+)",result)
    if not match or not arch:
        stop("Case submit output did not expose both job IDs; inspect before retry")
    d=C.load()
    d["actions"][RETRY_KEY]="DONE"
    d["armed"]=False
    d["ad_only"]=True
    d["hold_after_first_ad_segment"]=True
    d["history_retry_model_job"]=match.group(1)
    d["history_retry_archive_job"]=arch.group(1)
    d["history_retry_recorded_at"]=C.utc()
    C.save(d)
    print(f"AD200 2047-2052 SMOKE RETRY SUBMITTED: run={match.group(1)} archive={arch.group(1)}",flush=True)
    print("NO AUTOMATIC CONTINUATION; DO NOT REPEAT THIS COMMAND",flush=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("audit","repair-submit","status"))
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="status":
        print("Controller action:", C.load().get("actions",{}).get(RETRY_KEY))
        print("Current AD200 job queue:",C.slurm(STAGE))
        print("2052 archived restart exists:",
              (C.ARCH[STAGE]/"rest/2052-01-01-00000").is_dir())
        return
    if a.action=="repair-submit" and a.confirm!=CONFIRM:
        stop("Explicit --confirm "+CONFIRM+" required")
    with C.LOCK.open("a") as fh:
        fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.action=="audit":
            read_status()
            print("AUDIT ONLY; NO FILES CHANGED OR JOBS SUBMITTED")
        else:
            repair_and_submit()

if __name__=="__main__":
    main()
