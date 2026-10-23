#!/usr/bin/env python3
"""NL-Loo FIXNC guarded 45y + AD200 + postAD300 scheduler.

Single maintained script, THREE intentional submissions; each stage uses 5y
CIME segments and internal resubmission. All source cases/surfaces are intact.
Use status to inspect; continue45, ad200, post300 require explicit approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

USER = "ly3n24"
ROOT = Path(f"/iridisfs/scratch/{USER}/CLM_FATES")
CASES = ROOT / "cases"
CIME = ROOT / "CTSM/cime/scripts"
OUT = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS")
NAME = {
    "PRE50": "NL-Loo_OBSPFT_NC_PRE50",
    "AD200": "NL-Loo_OBSPFT_NC_AD200",
    "POST300": "NL-Loo_OBSPFT_NC_POST300",
}
CASE = {k: CASES / v for k,v in NAME.items()}
ARCH = {k: OUT / "archive" / v for k,v in NAME.items()}
RUN = {k: OUT / v / "run" for k,v in NAME.items()}
SOURCE = {
    "AD200": "PRE50",
    "POST300": "AD200",
}
YEAR_START = {"PRE50":1997, "AD200":2047, "POST300":2247}
YEAR_END = {"PRE50":2047, "AD200":2247, "POST300":2547}
MODE = {"PRE50":"off", "AD200":"on", "POST300":"off"}
SEGMENTS = {"AD200":40, "POST300":60}
SURF = ROOT / "experiments/NonCompetitionObserved22/NL-Loo/surface/surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc"
SURF_SHA = "81ca2872a9758325c0a18121ad060496ce47745a590264353b3cbcfcdcc95920"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
CONFIRM = {
    "continue45": "CONTINUE_NL_LOO_PRE50_45Y",
    "ad200": "START_NL_LOO_AD200_200Y",
    "post300": "START_NL_LOO_POSTAD300_300Y",
}
REQUIRED_NML = {
    "use_fates": ".true.",
    "use_fates_sp": ".false.",
    "use_fates_fixed_biogeog": ".true.",
    "use_fates_nocomp": ".true.",
    "fsurdat": str(SURF),
}

def fail(msg):
    raise SystemExit("STOP (no new Slurm submission): " + msg)

def command(args, cwd=None, capture=False):
    print("+", " ".join(map(str,args)),flush=True)
    r=subprocess.run([str(i) for i in args],cwd=cwd,text=True,
        capture_output=capture,check=False,timeout=120)
    if r.returncode:
        fail(f"{args[0]} failed (rc={r.returncode}): {r.stderr[-600:] if capture else 'inspect log'}")
    if capture:
        return r.stdout.strip()
    return ""

def xml(stage, key):
    return command(["./xmlquery",key,"--value"],CASE[stage],capture=True)

def checksum(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def queues(stage):
    r=subprocess.run(["squeue","-u",USER,"-h","-o","%j|%i|%T"],
        text=True,capture_output=True,check=False,timeout=30)
    if r.returncode:
        fail("Cannot read Slurm queue; refusing potential duplicate submission")
    return [line for line in r.stdout.splitlines() if NAME[stage] in line.split("|")[0]]

def check_paths():
    if not SURF.is_file() or checksum(SURF)!=SURF_SHA:
        fail("New observed PFT surface missing or changed")
    if not PARAM.is_file() or checksum(PARAM)!=PARAM_SHA:
        fail("FATES parameter file missing/changed (mapping not pinned)")
    if not (CIME/"create_clone").is_file():
        fail("CIME create_clone not found")
    if not CASE["PRE50"].is_dir():
        fail("PRE50 case absent")
    if xml("PRE50","COMPSET")!="2000_DATM%1PT_CLM60%FATES_SICE_SOCN_SROF_SGLC_SWAV_SESP":
        fail("Unexpected compset")
    if abs(float(xml("PRE50","CCSM_CO2_PPMV"))-363.04)>1e-4:
        fail("Unexpected fixed CO2")
    if xml("PRE50","CLM_CO2_TYPE").lower()!="constant":
        fail("CO2 type changed")

def nml_values(path):
    d={}
    for line in path.read_text(errors="replace").splitlines():
        m=re.match(r"^\s*([a-z]\w*)\s*=\s*(.*)",line,re.I)
        if m:
            d[m.group(1).lower()]=m.group(2).split("!")[0].strip().strip(",").strip().strip("'\"")
    return d

def check_case(stage, stage_ready=True):
    c=CASE[stage]
    if not c.is_dir() or not (c/"CaseDocs/lnd_in").is_file():
        fail(f"Missing generated namelist for {stage}")
    v=nml_values(c/"CaseDocs/lnd_in")
    for key, expected in REQUIRED_NML.items():
        if v.get(key,"").lower()!=expected.lower():
            fail(f"{stage}: generated {key} is {v.get(key)!r}, expected {expected!r}")
    if xml(stage,"CLM_ACCELERATED_SPINUP").lower()!=MODE[stage]:
        fail(f"{stage}: decomposition mode mismatch")
    state=v.get("spinup_state","not_explicit")
    if stage=="AD200" and state!="2":
        fail(f"AD stage did not generate spinup_state=2 (got {state}); verify local CTSM support")
    if stage!="AD200" and state not in ("0","not_explicit"):
        fail(f"{stage}: normal stage unexpectedly spinup_state={state}")
    if int(xml(stage,"STOP_N"))!=5:
        fail(f"{stage}: STOP_N must be 5")
    if xml(stage,"STOP_OPTION")!="nyears":
        fail(f"{stage}: STOP_OPTION must be nyears")
    if xml(stage,"DOUT_S").lower()!="true":
        fail(f"{stage}: DOUT_S required")
    if Path(xml(stage,"RUNDIR")) != RUN[stage] or Path(xml(stage,"DOUT_S_ROOT"))!=ARCH[stage]:
        fail(f"{stage}: RUNDIR / DOUT_S_ROOT collision")
    if xml(stage,"BUILD_COMPLETE").lower()!="true":
        fail(f"{stage}: cloned executable not marked built")
    prexe=Path(xml("PRE50","EXEROOT"))/"cesm.exe"
    if Path(xml(stage,"EXEROOT"))/"cesm.exe" != prexe or not prexe.is_file():
        fail(f"{stage}: compiled executable differs or absent")
    if not (c/".case.run").is_file() or not (c/"case.st_archive").is_file():
        fail(f"{stage}: CIME setup incomplete")
    batch=(c/".case.run").read_text(errors="replace")
    if re.search(r"(?im)^#SBATCH\s+.*--exclusive",batch):
        fail(f"{stage}: exclusive Slurm allocation forbidden")
    if not stage_ready:
        return
    # The actual interval and CO2 must remain identical in all stages.
    if xml(stage,"CALENDAR")!="NO_LEAP" or xml(stage,"ATM_NCPL")!="48":
        fail(f"{stage}: forcing coupling/calendar changed")
    if xml(stage,"CLM_CO2_TYPE").lower()!="constant" or abs(float(xml(stage,"CCSM_CO2_PPMV"))-363.04)>1e-4:
        fail(f"{stage}: CO2 changed")
    if not (c/"user_nl_datm_streams").is_file() or "NL-Loo_DATM_1997.nc" not in (c/"user_nl_datm_streams").read_text():
        fail(f"{stage}: site DATM stream absent")

def rest_directory(stage, year):
    date=f"{year:04d}-01-01-00000"
    p=ARCH[stage]/"rest"/date
    if not p.is_dir():
        fail(f"{stage} final checkpoint absent: {p}")
    files=list(p.iterdir())
    if not files:
        fail(f"{stage} empty checkpoint: {p}")
    needed={"cpl":f"{NAME[stage]}.cpl.r.{date}.nc",
            "atm":f"{NAME[stage]}.datm.r.{date}.nc",
            "lnd":f"{NAME[stage]}.clm2.r.{date}.nc"}
    for comp,n in needed.items():
        f=p/n
        if not f.is_file() or f.stat().st_size<512:
            fail(f"{stage} {comp} restart missing/small: {f}")
    ptrs=list(p.glob("rpointer.*"))
    if not ptrs:
        fail(f"{stage}: rpointer files not archived with restart")
    return p, date, needed

def status_lines(stage):
    p=CASE[stage]/"CaseStatus"
    return p.read_text(errors="replace") if p.exists() else ""

def stage_success(stage, end_year, require_archive=True):
    """Stop on pending stage jobs, incomplete archive, failed run, bad restart."""
    if queues(stage):
        fail(f"{stage} still has active or pending Slurm jobs: {queues(stage)}")
    data=status_lines(stage)
    if not re.search(r"case\.run success",data,re.I):
        fail(f"{stage}: CaseStatus lacks successful case.run")
    if require_archive and not re.search(r"case\.st_archive success|st_archive success",data,re.I):
        fail(f"{stage}: CaseStatus lacks successful archiver; inspect before continuing")
    p,date,_=rest_directory(stage,end_year)
    print(f"CHECKPOINT_PASS {stage} -> {date} at {p}")
    return p

def validate_first5():
    check_paths()
    check_case("PRE50")
    if xml("PRE50","CLM_ACCELERATED_SPINUP")!="off":
        fail("PRE50 not normal")
    if xml("PRE50","RUN_TYPE")!="startup":
        fail("PRE50 not startup")
    if xml("PRE50","RUN_STARTDATE")!="1997-01-01":
        fail("PRE50 initial date changed")
    if xml("PRE50","RESUBMIT")!="0" or xml("PRE50","CONTINUE_RUN").lower()!="false":
        fail("First5 state changed; use status and inspect before resubmission")
    stage_success("PRE50",2002)
    # Strict accounting verification for the exact first two jobs.
    result=subprocess.run(["sacct","-n","-X","-P","-j","4671182,4671183",
         "--format=JobIDRaw,State"],text=True,capture_output=True,timeout=30)
    if result.returncode:
        fail("sacct failed; first5 jobs must be independently verified")
    states={}
    for line in result.stdout.splitlines():
        col=line.split("|")
        if len(col)>=2:states[col[0]]=col[1].split()[0]
    for jid in ("4671182","4671183"):
        if states.get(jid)!="COMPLETED":
            fail(f"First5 job {jid} not confirmed COMPLETED by sacct (state={states.get(jid)})")
    print("FIRST_5_YEARS_PASS. PRE50 checkpoint at 2002; science: PFT area still merits plot validation.")

def preflight_quota():
    r=subprocess.run(["myfiles"],capture_output=True,text=True,timeout=30)
    if r.returncode:
        print("WARNING: myfiles command failed; verify Scratch inode quota manually")
        return
    m=re.search(r"Scratch number of files used:\s*([\d,]+)/([\d,]+)",r.stdout)
    if m:
        used,limit=(int(x.replace(",","")) for x in m.groups())
        print(f"Scratch inode use {used}/{limit} ({used/limit:.1%})")
        if used/limit>=0.85:
            fail("Scratch inodes >=85%; clean/archive first")
    else:
        print("WARNING: could not parse Scratch inodes from myfiles")

def assert_unsubmitted(stage):
    if queues(stage):
        fail(f"{stage} already has queue entries")
    if re.search(r"case\.submit starting|case\.submit success|case\.run starting",status_lines(stage),re.I):
        fail(f"{stage} has previous submission history, refusing double-submit")

def do_submit(stage, ledger, confirm):
    preflight_quota()
    if ledger.exists():
        fail(f"Prior submission ledger exists; inspect before retry: {ledger}")
    assert_unsubmitted(stage)
    ledger.write_text(json.dumps({"stage":stage,"state":"SUBMISSION_ATTEMPTED",
                   "case":str(CASE[stage]),"mode":MODE[stage]},indent=2)+"\n")
    try:
        command(["./case.submit"], CASE[stage])
    except Exception:
        raise
    ledger.write_text(json.dumps({"stage":stage,"state":"SUBMITTED",
                   "case":str(CASE[stage]),"mode":MODE[stage]},indent=2)+"\n")
    print(f"{stage}: Slurm submit accepted. Check CaseStatus / squeue / sacct.")
    print("No cross-stage Slurm auto-handoff; later stage requires completed restart gate.")

def continue45():
    validate_first5()
    c=CASE["PRE50"]
    ledger=c/"observed_PFT_PRE50_continue45.json"
    if ledger.exists():
        fail("45-year submission receipt already exists")
    # Existing CIME archive must leave its most recent rpointer and restart in RUNDIR,
    # or the user must explicitly recover them. Do not silently replace files.
    rdir=RUN["PRE50"]
    if not rdir.is_dir() or not any(rdir.glob("rpointer.*")):
        fail("PRE50 RUNDIR has no restart pointer; CIME restart staging needs review")
    command(["./xmlchange","CONTINUE_RUN=TRUE","RESUBMIT=8"],c)
    if xml("PRE50","CONTINUE_RUN").lower()!="true" or xml("PRE50","RESUBMIT")!="8":
        fail("CONTINUE_RUN/RESUBMIT were not changed correctly")
    # check_case for unchanged forcing, surface, flags and normal decomposition
    check_case("PRE50")
    do_submit("PRE50",ledger,CONFIRM["continue45"])
    print("PLAN: first5 COMPLETE + 9 automatic 5y segments = 50y, target 2047-01-01")

def stage_case(stage):
    check_paths()
    src=SOURCE[stage]
    check_case(src)
    stage_success(src,YEAR_END[src])
    target=CASE[stage]
    if target.exists() or RUN[stage].exists() or ARCH[stage].exists():
        fail(f"New {stage} case/RUNDIR/archive already exists; never overwrite")
    print("CREATING NEW STAGE",stage,"from validated",src)
    command([CIME/"create_clone","--case",target,"--clone",CASE[src],"--keepexe"],CIME)
    # Stage-specific runtime XML, no change to compiled physics.
    config={
        "RUN_TYPE":"branch",
        "CONTINUE_RUN":"FALSE",
        "RUN_REFCASE":NAME[src],
        "RUN_REFDATE":f"{YEAR_END[src]:04d}-01-01",
        "GET_REFCASE":"FALSE",
        "CLM_ACCELERATED_SPINUP":MODE[stage],
        "STOP_OPTION":"nyears","STOP_N":"5",
        "REST_OPTION":"nyears","REST_N":"5",
        "RESUBMIT":str(SEGMENTS[stage]-1),
        "DOUT_S":"TRUE",
        "RUNDIR":str(RUN[stage]),
        "DOUT_S_ROOT":str(ARCH[stage]),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores",
    }
    for k,v in config.items():
        command(["./xmlchange",f"{k}={v}"],target)
    if not (target/".case.run").is_file() or not (target/"case.st_archive").is_file():
        command(["./case.setup"],target)
    command(["./preview_namelists"],target)
    check_case(stage)
    command(["./check_input_data"],target)
    # Branch runs require ALL same-date component restart and rpointer files.
    # Copy to newly created stage RUNDIR only; never mutate source archive.
    original,date,required=rest_directory(src,YEAR_END[src])
    RUN[stage].mkdir(parents=True,exist_ok=False)
    source_files=list(original.iterdir())
    for p in source_files:
        if not p.is_file():continue
        if not (p.name.startswith("rpointer.") or ".r." in p.name):
            continue
        dest=RUN[stage]/p.name
        if dest.exists():fail(f"Stage input exists unexpectedly: {dest}")
        shutil.copy2(p,dest)
    # Archived dated pointer names may be rpointer.atm.2047-01-01-00000.
    # In this case reconstruct the matching undated pointer for branch startup.
    for p in list(RUN[stage].glob("rpointer.*")):
        suffix="."+date
        if p.name.endswith(suffix):
            base=RUN[stage]/p.name[:-len(suffix)]
            if not base.exists():
                shutil.copy2(p,base)
    # Verify existence of all three restart files, pointer referents,
    # and preserve original REFCASE-named NetCDF filenames.
    for name in required.values():
        if not (RUN[stage]/name).is_file():
            fail("Staged reference restart missing: "+name)
    pointers=list(RUN[stage].glob("rpointer.*"))
    if not pointers:fail("No staged rpointer files")
    for p in pointers:
        if p.name.endswith("."+date):continue
        for line in p.read_text(errors="replace").splitlines():
            value=line.strip().strip("'\"")
            if not value or value.startswith("#"):continue
            ref=Path(value).name
            if ref.endswith(".nc") and not (RUN[stage]/ref).is_file():
                fail(f"Pointer {p.name} refers to missing restart {ref}")
    if xml(stage,"RUN_TYPE")!="branch" or xml(stage,"RUN_REFCASE")!=NAME[src]:
        fail("Reference mode settings mismatch")
    if xml(stage,"RUN_REFDATE")!=f"{YEAR_END[src]:04d}-01-01":
        fail("Reference date mismatch")
    if xml(stage,"GET_REFCASE").lower()!="false":
        fail("GET_REFCASE must be FALSE for pre-staged restarts")
    print("STAGE_READY",stage,"source",src,"checkpoint",date)
    return target

def launch_next(stage):
    if stage not in SOURCE:fail("Invalid stage")
    check_paths()
    src=SOURCE[stage]
    if stage=="AD200":
        if CASE["PRE50"].exists():
            check_case("PRE50")
    if stage=="POST300":
        check_case("AD200")
    stage_success(src,YEAR_END[src])
    target=stage_case(stage)
    ledger=target/f"observed_PFT_{stage}_submission.json"
    do_submit(stage,ledger,CONFIRM["ad200" if stage=="AD200" else "post300"])
    print(f"PLAN: {SEGMENTS[stage]} x 5y -> end {YEAR_END[stage]}-01-01")

def status():
    check_paths()
    for stage in ("PRE50","AD200","POST300"):
        print(f"\n===== {stage} =====")
        if not CASE[stage].is_dir():
            print("NOT_CREATED");continue
        print("Case",CASE[stage])
        print("Active jobs",queues(stage))
        print("CLM_ACCELERATED_SPINUP",xml(stage,"CLM_ACCELERATED_SPINUP"))
        print("CONTINUE_RUN",xml(stage,"CONTINUE_RUN"),
              "RESUBMIT",xml(stage,"RESUBMIT"))
        for y in ([2002,2047] if stage=="PRE50" else [YEAR_END[stage]]):
            p=ARCH[stage]/"rest"/f"{y:04d}-01-01-00000"
            print("Restart",y,p.is_dir(),str(p))
        for line in status_lines(stage).splitlines()[-10:]:
            if "case." in line or "error" in line.lower():print(line)

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("action",choices=["status","audit5","continue45","ad200","post300"])
    a.add_argument("--confirm",default="",help="Exact confirmation string for a new Slurm submission")
    x=a.parse_args()
    if x.action=="status":
        status();return
    if x.action=="audit5":
        validate_first5();return
    if x.confirm!=CONFIRM[x.action]:
        fail(f"Wrong confirmation token. Required: --confirm {CONFIRM[x.action]}")
    if x.action=="continue45":
        continue45()
    elif x.action=="ad200":
        launch_next("AD200")
    elif x.action=="post300":
        launch_next("POST300")

if __name__=="__main__":
    main()
