#!/usr/bin/env python3
"""Isolated DE-Tha FATES AD -> NORMAL five-year conversion experiment.

Two choices of verified AD restart (not interchangeable):
  --source-year 2001 : after initial AD5 smoke, TECHNICAL AD-to-normal test
  --source-year 2396 : after full AD400, SCIENTIFIC post-AD5-year pilot

Creates a new hybrid restart case from the original DE-Tha CIME template,
keeping v2 observed-forest/observed-soil surface, unchanged DATM forcing,
fixed biogeography and no competition, but CLM_ACCELERATED_SPINUP=off.
Normal spinup_state must be 0 or ABSENT in generated lnd_in; the pinned
CTSM's FATES namelist builder rejects any explicitly set spinup_state
when use_cn=false. Do NOT force spinup_state=0 into user_nl_clm.

NEVER edit/restart/submit the AD400 source case; copy the verified 3-component
AD restart into a NEW run directory and save separate restart pointers.
Do not submit more than one 5-year Normal test at a time.

audit is STRICTLY read only; stage creates an isolated case, no Slurm;
validate is READ ONLY; submit-smoke submits one 5y run, no resubmits.
verify-run audits Slurm/archived restart, including spinup_state==0.

IMPORTANT: a successful 2001->2006 Normal technical branch does NOT prove
AD400 soil carbon equilibration, and a five-year normal run alone does not
prove convergence.
"""
from __future__ import annotations
import argparse
import configparser
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from datetime import datetime,timezone
from pathlib import Path

from netCDF4 import Dataset
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("DEThaAD400Stage10",HERE/"10_DE_Tha_direct_AD400.py")
if spec is None or spec.loader is None:raise RuntimeError("Missing Stage10")
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

CONFIRM_STAGE="CREATE_ISOLATED_DE_THA_AD_TO_NORMAL_5Y_TEST"
CONFIRM_SUBMIT="SUBMIT_ISOLATED_DE_THA_NORMAL_5Y_ONLY"
RESTART_COMPONENTS=("clm2","datm","cpl")

def fail(m):raise RuntimeError(str(m))
def call(args,cwd=None,timeout=180):
    p=subprocess.run([str(x) for x in args],cwd=cwd,text=True,
                     capture_output=True,check=False,timeout=timeout)
    if p.returncode:raise RuntimeError(
        f"{' '.join(map(str,args))}: rc={p.returncode}\n"
        f"STDOUT:{p.stdout[-1700:]}\nSTDERR:{p.stderr[-2500:]}")
    return p.stdout.strip()
def utc():return datetime.now(timezone.utc).isoformat()
def choice(year):
    if year not in (2001,2396):fail("Only source-year 2001 or 2396 supported")
    label="AD5" if year==2001 else "AD400"
    name=f"DE-Tha_OBSPFT_NC_{label}_TO_NORMAL5_TEST"
    case=C.R/"cases"/name
    run=C.OUT/name/"run"
    archive=C.OUT/"archive"/name
    ledger=Path.home()/f"DE_Tha_{label}_Normal5_controller.json"
    checkpoint=C.ARCH/"rest"/f"{year:04d}-01-01-00000"
    return dict(year=year,label=label,name=name,case=case,run=run,
                archive=archive,ledger=ledger,checkpoint=checkpoint)

def xq(case,key):return call(["./xmlquery",key,"--value"],cwd=case,timeout=65)
def xmlchange(case,key,value):
    call(["./xmlchange",f"{key}={value}"],cwd=case,timeout=65)

def jobs_for(name):
    s=call(["squeue","-u",C.USER,"-h","-o","%i|%j|%T"],timeout=45)
    return [line for line in s.splitlines() if len(line.split("|"))>=3
            and line.split("|")[1] in ("run."+name,"st_archive."+name)]

def pft_input():
    C.verify_surface()
    if xq(C.EXISTING,"BUILD_COMPLETE").lower()!="true":
        fail("Original template not marked built")
    exe=Path(xq(C.EXISTING,"EXEROOT"))/"cesm.exe"
    if not exe.is_file():fail("Original FATES executable missing")
    return exe

def job_accounting():
    # This is a historical consistency gate for source AD400; do not rely on
    # the job being absent from the current queue to claim success.
    if not C.STATE.is_file():fail("AD400 source submission ledger absent")
    d=json.loads(C.STATE.read_text())
    if d.get("experiment")!="DIRECT_AD400_COLDSTART":
        fail("Unexpected AD400 controller")
    return d

def archived_ad_checkpoint(opts):
    year=opts["year"]
    source=opts["checkpoint"]
    ledger=job_accounting()
    if year==2001:
        if ledger.get("stage") not in ("FIRST_5Y_SUBMITTED","CONTINUATION_SUBMITTED",
                                       "CONTINUATION_ATTEMPTED_UNCERTAIN"):
            fail("AD400 first five-year submission not documented")
        ids=(str(ledger.get("first_run_job") or ""),
             str(ledger.get("first_archive_job") or ""))
        if not all(re.fullmatch(r"\d+",x) for x in ids):
            fail("Source AD5 Slurm job IDs unavailable")
        report=call(["sacct","-X","-j",",".join(ids),"-n","-P",
                     "--format=JobIDRaw,JobName%128,State,ExitCode"],timeout=60)
        found={}
        for line in report.splitlines():
            r=line.split("|")
            if len(r)>=4 and r[0] in ids:
                found[r[0]]=tuple(x.strip() for x in r[1:4])
        for ident,name in zip(ids,("run."+C.NAME,"st_archive."+C.NAME)):
            if found.get(ident)!=(name,"COMPLETED","0:0"):
                fail(f"Source AD5 Slurm not COMPLETED/0:0 {ident}: {found.get(ident)}")
    else:
        # At 2396 the AD400 controller must have submitted continuation, and
        # FULL terminal date must be verified against archived restart + job
        # accounting before interpreting this as science. CaseStatus and
        # last checkpoint require manual continuity review of 79 segments.
        if ledger.get("stage")!="CONTINUATION_SUBMITTED":
            fail("AD400 continuation has not been documented as submitted")
        if jobs_for(C.NAME):
            fail("AD400 model/archive still queued; no final conversion yet")
        status=(C.CASE/"CaseStatus").read_text(errors="replace")
        if not re.search(r"case\.run success",status) or not re.search(
                r"(?:case\.)?st_archive success",status):
            fail("Source AD400 CaseStatus lacks run/archive success")
    if not source.is_dir():fail("Archived AD checkpoint missing: "+str(source))
    files={}
    for comp in RESTART_COMPONENTS:
        p=source/f"{C.NAME}.{comp}.r.{year:04d}-01-01-00000.nc"
        if not p.is_file() or p.is_symlink() or p.stat().st_size<1024:
            fail("Source AD component missing/too small: "+str(p))
        files[comp]=p
    with Dataset(files["clm2"],"r") as nc:
        if "spinup_state" in nc.variables:
            arr=np.asarray(nc.variables["spinup_state"][:]).ravel()
            if arr.size!=1:fail("Invalid source CLM spinup_state shape")
            s=int(arr[0])
        elif "spinup_state" in nc.ncattrs():
            s=int(nc.getncattr("spinup_state"))
        else:
            fail("AD land restart does not record spinup_state")
        if s!=2:fail("Source AD restart spinup_state must be 2, saw "+str(s))
    status=(C.CASE/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",status) or not re.search(
           r"(?:case\.)?st_archive success",status):
        fail("Source AD CaseStatus run/archive incomplete")
    print("PASS: source",year,"AD checkpoint has 3 components; spinup_state=2")
    return files

def preflight(opts, needs_fresh=True):
    pft_input()
    files=archived_ad_checkpoint(opts)
    if needs_fresh:
        if any(p.exists() or p.is_symlink() for p in
               (opts["case"],opts["run"],opts["archive"],opts["ledger"])):
            fail("Independent Normal case/run/archive/ledger already exists; no overwrite")
        if jobs_for(opts["name"]):
            fail("New Normal test already has a job")
    print("PASS: NORMAL branch source and isolation gates; source year",opts["year"])
    print("NEW CASE:",opts["case"])
    print("NEW RUN:",opts["run"])
    print("KEEP AD400 SOURCE COMPLETELY UNCHANGED")
    return files

def stage(opts):
    files=preflight(opts)
    exe=Path(xq(C.EXISTING,"EXEROOT"))/"cesm.exe"
    old_exe_sha=C.sha(exe)
    call([C.SCRIPTS/"create_clone","--case",opts["case"],
          "--clone",C.EXISTING,"--keepexe"],cwd=C.SCRIPTS,timeout=300)
    cs=opts["case"]
    for key,value in {
        "RUN_TYPE":"hybrid","RUN_STARTDATE":f"{opts['year']:04d}-01-01",
        "RUN_REFCASE":C.NAME,"RUN_REFDATE":f"{opts['year']:04d}-01-01",
        "GET_REFCASE":"FALSE",
        "CONTINUE_RUN":"FALSE","CLM_FORCE_COLDSTART":"off",
        "CLM_ACCELERATED_SPINUP":"off",
        "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears","REST_N":"5",
        "RESUBMIT":"0","DOUT_S":"TRUE",
        "RUNDIR":str(opts["run"]),"DOUT_S_ROOT":str(opts["archive"]),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"
    }.items():
        xmlchange(cs,key,value)
    if xq(cs,"EXEROOT")!=str(exe.parent) or C.sha(exe)!=old_exe_sha:
        fail("Normal test executable not identical to validated FATES binary")
    # Restarts are COPIED into isolated RUNDIR. AD source untouched.
    opts["run"].mkdir(parents=True,exist_ok=False)
    for comp in RESTART_COMPONENTS:
        src=files[comp];dst=opts["run"]/src.name
        shutil.copy2(src,dst)
        if C.sha(dst)!=C.sha(src):
            fail("Copied AD source restart differs: "+str(dst))
    for ptr,comp in (("rpointer.lnd","clm2"),("rpointer.atm","datm"),
                     ("rpointer.cpl","cpl")):
        (opts["run"]/ptr).write_text(files[comp].name+"\n",encoding="utf-8")
    user_file=cs/"user_nl_clm"
    if not user_file.is_file():fail("New case user_nl_clm absent")
    user=user_file.read_text(encoding="utf-8")
    if C.nml_value(user,"spinup_state") is not None:
        fail("Normal case unexpectedly inherited explicit spinup_state")
    if C.nml_value(user,"reseed_dead_plants") is not None:
        fail("Normal case contains CN-only reseed_dead_plants")
    if C.nml_value(user,"finidat") not in (None,""):
        fail("Normal case inherited preexisting finidat")
    expected={
        "fsurdat":f"'{C.SURFACE}'",
        "use_fates":".true.",
        "use_fates_sp":".false.",
        "use_fates_fixed_biogeog":".true.",
        "use_fates_nocomp":".true.",
        "hist_fincl1":",".join("'"+x+"'" for x in C.HISTORY),
        "finidat":f"'{opts['run']/files['clm2'].name}'",
    }
    for key,val in expected.items():
        user=C.replace_nl(user,key,val)
    user_file.write_text(user,encoding="utf-8")
    if not (cs/".case.run").is_file():
        call(["./case.setup"],cwd=cs,timeout=240)
    # Unlike AD, normal FATES must not contain an explicit spinup_state=0.
    # The original pinned unpatched CLMBuildNamelist.pm will otherwise fail.
    call(["./preview_namelists"],cwd=cs,timeout=300)
    call(["./check_input_data"],cwd=cs,timeout=300)
    validate(opts)
    opts["ledger"].write_text(json.dumps({
      "status":"PREPARED_NOT_SUBMITTED",
      "case":str(cs),
      "name":opts["name"],
      "source_case":C.NAME,
      "source_ad_restart_year":opts["year"],
      "target_normal_year":opts["year"]+5,
      "source_restart_sha256":{k:C.sha(v) for k,v in files.items()},
      "surface_sha256":C.SURF_SHA,
      "executable_sha256":old_exe_sha,
      "resubmit":0,"model_runs_planned":1,
      "scientific_role":"technical" if opts["year"]==2001 else "post_AD400_pilot",
      "created_utc":utc()
    },indent=2)+"\n",encoding="utf-8")
    print("STAGE PASS: isolated Normal5 hybrid case, first 5y ready, NO SLURM submitted")

def validate(opts):
    C.verify_surface()
    cs=opts["case"]
    if not cs.is_dir():fail("New Normal test case not staged")
    if xq(cs,"BUILD_COMPLETE").lower()!="true":fail("Normal cloned case unbuilt")
    for key,value in {
        "RUN_TYPE":"hybrid","RUN_STARTDATE":f"{opts['year']:04d}-01-01",
        "RUN_REFCASE":C.NAME,"RUN_REFDATE":f"{opts['year']:04d}-01-01",
        "CLM_ACCELERATED_SPINUP":"off",
        "CONTINUE_RUN":"FALSE","RESUBMIT":"0","STOP_N":"5",
        "REST_N":"5","DOUT_S":"TRUE",
        "RUNDIR":str(opts["run"]),"DOUT_S_ROOT":str(opts["archive"])
    }.items():
        got=xq(cs,key)
        if got.lower()!=value.lower():fail(f"Wrong normal XML {key}: {got}")
    for path in (cs/"CaseDocs/lnd_in",opts["run"]/"lnd_in"):
        if not path.is_file():fail("Generated Normal lnd_in missing: "+str(path))
        txt=path.read_text()
        for key,val in (("use_fates",".true."),("use_fates_sp",".false."),
                        ("use_fates_nocomp",".true."),
                        ("use_fates_fixed_biogeog",".true."),
                        ("fsurdat",str(C.SURFACE)),
                        ("finidat",str(opts["run"]/
                                     f"{C.NAME}.clm2.r.{opts['year']:04d}-01-01-00000.nc"))):
            if C.nml_value(txt,key)!=val:
                fail(f"Generated Normal {key} mismatches in {path}: {C.nml_value(txt,key)!r}")
        if C.nml_value(txt,"spinup_state") not in (None,"0"):
            fail("Normal lnd_in must have spinup_state 0 or absent")
        if C.nml_value(txt,"reseed_dead_plants") is not None:
            fail("Normal lnd_in must omit CN-only reseed_dead_plants")
        fields=re.findall(r"'([^']+)'",C.nml_value_raw(txt,"hist_fincl1"))
        if fields!=C.HISTORY:fail("Wrong FATES GPP/NPP history fields")
    if C.sha(cs/"CaseDocs/lnd_in")!=C.sha(opts["run"]/"lnd_in"):
        fail("CaseDocs vs RUNDIR generated namelist differs")
    for ptr,comp in (("rpointer.lnd","clm2"),("rpointer.atm","datm"),
                     ("rpointer.cpl","cpl")):
        src=opts["checkpoint"]/f"{C.NAME}.{comp}.r.{opts['year']:04d}-01-01-00000.nc"
        dest=opts["run"]/src.name
        if not src.is_file() or not dest.is_file() or C.sha(src)!=C.sha(dest):
            fail("Normal branch staged restart SHA does not match archived AD: "+comp)
        p=opts["run"]/ptr
        if not p.is_file() or p.read_text().strip()!=src.name:
            fail("Normal branch restart pointer invalid: "+ptr)
    if jobs_for(opts["name"]):
        fail("Normal test already has Slurm job queued")
    print("VALIDATE PASS: independent 5yr Normal hybrid-from-AD restart; no AD source edits")

def submit(opts):
    validate(opts)
    if not opts["ledger"].is_file():fail("Normal test controller ledger absent")
    ledger=json.loads(opts["ledger"].read_text())
    if ledger.get("status")!="PREPARED_NOT_SUBMITTED":
        fail("Normal test submission already attempted or status uncertain")
    original=(opts["case"]/"CaseStatus").read_text(errors="replace")
    if re.search(r"case\.submit starting|case\.run starting",original):
        fail("Normal test CaseStatus indicates earlier submission")
    ledger["status"]="SUBMISSION_ATTEMPTED_UNCERTAIN"
    ledger["attempted_utc"]=utc()
    opts["ledger"].write_text(json.dumps(ledger,indent=2)+"\n",encoding="utf-8")
    # Stop before any automatic resubmission; explicit skip_pnl preserves
    # independently checked normal namelist and finidat.
    output=call(["./case.submit","--skip-preview-namelist"],
                cwd=opts["case"],timeout=300)
    runid=re.search(r"Submitted job case\.run with id (\d+)",output)
    arcid=re.search(r"Submitted job case\.st_archive with id (\d+)",output)
    if not runid or not arcid:
        fail("Submission job IDs unparseable; do NOT resubmit blindly. "+output[-1200:])
    ledger["status"]="FIRST_NORMAL5_SUBMITTED"
    ledger["runid"]=runid.group(1);ledger["archiveid"]=arcid.group(1)
    opts["ledger"].write_text(json.dumps(ledger,indent=2)+"\n",encoding="utf-8")
    print("SUBMITTED NORMAL5 HYBRID TEST:",opts["year"],"->",opts["year"]+5,
          "run",runid.group(1),"archive",arcid.group(1))
    print("AD400 source case not modified, NORMAL RESUBMIT=0")

def verify_run(opts):
    if not opts["ledger"].is_file():fail("Normal test ledger absent")
    d=json.loads(opts["ledger"].read_text())
    runid=str(d.get("runid",""));archiveid=str(d.get("archiveid",""))
    if not re.fullmatch(r"\d+",runid) or not re.fullmatch(r"\d+",archiveid):
        fail("Normal5 was not recorded submitted")
    if jobs_for(opts["name"]):fail("Normal test still queued/running")
    raw=call(["sacct","-X","-j",f"{runid},{archiveid}","-n","-P",
              "--format=JobIDRaw,JobName%128,State,ExitCode"])
    got={}
    for line in raw.splitlines():
        seg=line.split("|")
        if len(seg)>=4 and seg[0] in (runid,archiveid):
            got[seg[0]]=tuple(x.strip() for x in seg[1:4])
    for ident,name in ((runid,"run."+opts["name"]),
                       (archiveid,"st_archive."+opts["name"])):
        if got.get(ident)!=(name,"COMPLETED","0:0"):
            fail("Normal test Slurm job not COMPLETE: "+repr((ident,got.get(ident))))
    status=(opts["case"]/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",status) or not re.search(
         r"(?:case\.)?st_archive success",status):
        fail("Normal test CIME run/archive success not recorded")
    rest=opts["archive"]/"rest"/f"{opts['year']+5:04d}-01-01-00000"
    for comp in RESTART_COMPONENTS:
        p=rest/f"{opts['name']}.{comp}.r.{opts['year']+5:04d}-01-01-00000.nc"
        if not p.is_file() or p.stat().st_size<1024:
            fail("Normal final restart missing "+str(p))
        if comp=="clm2":
            with Dataset(p,"r") as ds:
                if "spinup_state" in ds.variables:
                    a=np.asarray(ds.variables["spinup_state"][:]).reshape(-1)
                    if a.size!=1:fail("Normal output state shape not 1")
                    val=int(a[0])
                elif "spinup_state" in ds.ncattrs():
                    val=int(ds.getncattr("spinup_state"))
                else:fail("No spinup_state in Normal restart")
            if val!=0:fail("Normal restart did not switch to state 0: "+str(val))
            print("PASS: Normal final CLM restart spinup_state=0")
    print("VERIFIED NORMAL BRANCH: AD restart -> normal five-year hybrid technically succeeded")
    print("NOTE: NOT a demonstration of equilibrium or low post-AD carbon flux drift")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("audit","stage","validate","submit-smoke","verify-run"))
    ap.add_argument("--source-year",type=int,choices=(2001,2396),default=2001)
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    opts=choice(a.source_year)
    if a.action=="audit":preflight(opts)
    elif a.action=="stage":
        if a.confirm!=CONFIRM_STAGE:fail("Explicit --confirm "+CONFIRM_STAGE+" needed")
        stage(opts)
    elif a.action=="validate":validate(opts)
    elif a.action=="submit-smoke":
        if a.confirm!=CONFIRM_SUBMIT:fail("Explicit --confirm "+CONFIRM_SUBMIT+" needed")
        submit(opts)
    else:verify_run(opts)

if __name__=="__main__":main()
