#!/usr/bin/env python3
"""NL-Loo no-competition gated Slurm watch: PRE50 -> AD200 -> POST300.

Create/submit only after the prior complete archive and restart are checked.
Within AD and POST: 5-year smoke segment -> validate spinup_state and restart
-> submit remaining 195/295 years via normal CIME RESUBMIT.
One low-resource Slurm watcher polls at most hourly; it is NOT a login daemon.
All output lives in separate case/run/archive directories; nothing is deleted.
Run 'plan' before 'arm'. Use 'disarm' to stop future watchers (not running models).
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

USER = "ly3n24"
ROOT = Path(f"/iridisfs/scratch/{USER}/CLM_FATES")
CTSM = ROOT / "CTSM"
CASES = ROOT / "cases"
SCRIPTS = CTSM / "cime/scripts"
OUT = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS")
REPO = Path(__file__).resolve().parent.parent
STATE = Path.home() / "NL_Loo_NC_auto550"
LEDGER = STATE / "controller.json"
WATCH = STATE / "watch.sh"
STOPFILE = STATE / "STOP"
C = {"PRE50": "NL-Loo_OBSPFT_NC_PRE50",
     "AD200": "NL-Loo_OBSPFT_NC_AD200",
     "POST300": "NL-Loo_OBSPFT_NC_POST300"}
S = {k: CASES / v for k, v in C.items()}
R = {k: OUT / v / "run" for k, v in C.items()}
A = {k: OUT / "archive" / v for k, v in C.items()}
PREV = {"AD200": "PRE50", "POST300": "AD200"}
START = {"PRE50": 1997, "AD200": 2047, "POST300": 2247}
END = {"PRE50": 2047, "AD200": 2247, "POST300": 2547}
FIRST5 = {"AD200": 2052, "POST300": 2252}
STATE_MODE = {"PRE50": 0, "AD200": 2, "POST300": 0}
MODES = {"PRE50": "off", "AD200": "on", "POST300": "off"}
LEFT_RESUBMITS = {"AD200": 38, "POST300": 58}
SURF = ROOT / "experiments/NonCompetitionObserved22/NL-Loo/surface/surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc"
SURF_SHA = "81ca2872a9758325c0a18121ad060496ce47745a590264353b3cbcfcdcc95920"
PARAM = CTSM / "src/fates/parameter_files/fates_params_default.json"
PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
EXPECTED_COMPSET = "2000_DATM%1PT_CLM60%FATES_SICE_SOCN_SROF_SGLC_SWAV_SESP"
CONFIRM = "ARM_NL_LOO_GATED_550_YEAR_PIPELINE"
WATCH_INTERVAL = "now+1hour"
MAX_IDLE_CHECKS = 4


def die(msg):
    raise RuntimeError(msg)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run(args, cwd=None, capture=True, timeout=120):
    p = subprocess.run([str(v) for v in args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None,
                       timeout=timeout, check=False)
    if p.returncode:
        die(f"Command returned {p.returncode}: {' '.join(map(str,args))}\n"
            + (p.stderr[-1300:] if capture else "Inspect external log"))
    if capture:
        return p.stdout.strip()
    return ""


def xml(stage, field):
    return run(["./xmlquery", field, "--value"], S[stage])


def change(stage, field, value):
    # Some deployed CIME versions accept only one argument per xmlchange.
    run(["./xmlchange", f"{field}={value}"], S[stage])


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_common():
    if not SURF.is_file() or digest(SURF) != SURF_SHA:
        die("Changed or missing NL-Loo observed PFT surface")
    if not PARAM.is_file() or digest(PARAM) != PARAM_SHA:
        die("Changed or missing FATES PFT JSON; mapping must be reaudited")
    if not S["PRE50"].is_dir():
        die("Original PRE50 case missing")
    if xml("PRE50", "COMPSET") != EXPECTED_COMPSET:
        die("Original compset changed")
    if xml("PRE50", "CLM_CO2_TYPE").lower() != "constant":
        die("Original fixed-CO2 policy changed")
    if abs(float(xml("PRE50", "CCSM_CO2_PPMV")) - 363.04) > 1e-4:
        die("Original CO2 value changed")
    if run(["git", "rev-parse", "HEAD"], CTSM) != "d5ea9d0136530370a62ef267ccfaff6f001ef914":
        die("Pinned CTSM git revision differs; source-level AD audit required")
    return True


def active_jobs(stage):
    rows = run(["squeue", "-u", USER, "-h", "-o", "%j|%i|%T"])
    return [x for x in rows.splitlines() if C[stage] in x.split("|", 1)[0]]


def case_status(stage):
    p = S[stage] / "CaseStatus"
    return p.read_text(errors="replace") if p.exists() else ""


def validate_case(stage):
    if not (S[stage] / "CaseDocs/lnd_in").is_file():
        die(f"{stage}: CIME land namelist missing")
    nam = (S[stage] / "CaseDocs/lnd_in").read_text(errors="replace")
    def get(field):
        m = re.search(r"(?m)^\s*" + re.escape(field) + r"\s*=\s*(.*?)\s*$", nam, re.I)
        return m.group(1).strip().strip("'\"") if m else None
    for field, val in {"use_fates": ".true.", "use_fates_sp": ".false.",
                       "use_fates_nocomp": ".true.",
                       "use_fates_fixed_biogeog": ".true.",
                       "fsurdat": str(SURF)}.items():
        if (get(field) or "").lower() != val.lower():
            die(f"{stage}: {field} mismatch: {get(field)!r}")
    if xml(stage, "CLM_ACCELERATED_SPINUP").lower() != MODES[stage]:
        die(f"{stage}: decomposition mode mismatch")
    spin = get("spinup_state")
    # Current CTSM often omits spinup_state=0 from generated normal namelist.
    if stage == "AD200" and spin != "2":
        die(f"{stage}: AD namelist did not explicitly select spinup_state=2: {spin}")
    if stage != "AD200" and spin not in (None, "0"):
        die(f"{stage}: normal namelist spinup_state unexpected: {spin}")
    if xml(stage, "CALENDAR") != "NO_LEAP" or xml(stage, "ATM_NCPL") != "48":
        die(f"{stage}: calendar / time resolution mismatch")
    if xml(stage, "CLM_CO2_TYPE").lower() != "constant":
        die(f"{stage}: CO2 policy changed")
    if abs(float(xml(stage, "CCSM_CO2_PPMV")) - 363.04) > 1e-4:
        die(f"{stage}: fixed CO2 changed")
    if xml(stage, "STOP_OPTION") != "nyears" or xml(stage, "STOP_N") != "5":
        die(f"{stage}: STOP must be five model years")
    if Path(xml(stage, "RUNDIR")) != R[stage] or Path(xml(stage, "DOUT_S_ROOT")) != A[stage]:
        die(f"{stage}: run/archive dir wrong")
    if xml(stage, "BUILD_COMPLETE").lower() != "true":
        die(f"{stage}: executable not marked complete")
    if xml(stage, "EXEROOT") != xml("PRE50", "EXEROOT"):
        die(f"{stage}: executable root changed; FATES build incompatible")
    if not (Path(xml(stage, "EXEROOT")) / "cesm.exe").is_file():
        die(f"{stage}: model executable missing")
    for f in (".case.run", "case.st_archive", "user_nl_datm_streams"):
        if not (S[stage] / f).is_file():
            die(f"{stage}: missing {f}")
    if "NL-Loo_DATM_1997.nc" not in (S[stage] / "user_nl_datm_streams").read_text():
        die(f"{stage}: DATM forcing does not match NL-Loo")
    if re.search(r"(?im)^\s*#SBATCH.*--exclusive", (S[stage] / ".case.run").read_text()):
        die(f"{stage}: unexpected exclusive-node job")


def cp_record(stage, year, *, desired_state=None):
    """All 3 components and rpointer files must be present in exact archived checkpoint."""
    stamp = f"{year:04d}-01-01-00000"
    p = A[stage] / "rest" / stamp
    if not p.is_dir():
        return None
    for prefix in ("cpl", "datm", "clm2"):
        f = p / f"{C[stage]}.{prefix}.r.{stamp}.nc"
        if not f.is_file() or f.stat().st_size < 512:
            die(f"Incomplete archived {prefix} restart at {p}")
    if not list(p.glob("rpointer.*")):
        die(f"No archived rpointer files in {p}")
    if desired_state is not None:
        land = p / f"{C[stage]}.clm2.r.{stamp}.nc"
        try:
            from netCDF4 import Dataset
            with Dataset(land) as ds:
                if "spinup_state" not in ds.variables:
                    die(f"{stage} restart missing spinup_state; inspect version")
                actual = int(ds.variables["spinup_state"][:].item())
        except ImportError:
            die("netCDF4 required for spinup_state verification; use clm_fates_env")
        if actual != desired_state:
            die(f"{stage} restart spinup_state={actual}, expected {desired_state}")
    return p


def completed(stage, year):
    if active_jobs(stage):
        return False
    ck = cp_record(stage, year, desired_state=STATE_MODE[stage])
    if ck is None:
        return False
    hist = case_status(stage)
    # Crucial: a finished run has a successfully archived model segment.
    if not re.search(r"case\.run success", hist, re.I):
        die(f"{stage} checkpoint exists but case.run success not recorded")
    if not re.search(r"(?:case\.)?st_archive success", hist, re.I):
        die(f"{stage} checkpoint exists but st_archive success not recorded")
    return True


def assert_no_old_submission(stage):
    if active_jobs(stage):
        die(f"{stage} has live jobs already: {active_jobs(stage)}")
    if re.search(r"case\.submit starting|case\.run starting", case_status(stage), re.I):
        die(f"{stage} was previously submitted. No duplicate case.submit allowed")


def preflight_inodes():
    s = run(["myfiles"])
    m = re.search(r"Scratch number of files used:\s*([\d,]+)/([\d,]+)", s)
    if not m:
        die("Unable to parse Scratch inode quota; refusing auto-submit")
    used, limit = (int(v.replace(",", "")) for v in m.groups())
    print(f"Scratch inode use: {used}/{limit} ({used/limit:.1%})", flush=True)
    if used / limit >= .83:
        die("Scratch inodes >=83%: archive/cleanup before more runs")


def stage_restart(source, target, year):
    p = cp_record(source, year, desired_state=STATE_MODE[source])
    if p is None:
        die(f"Reference restart missing {source} -> {target} {year}")
    dst = R[target]
    if dst.exists() and any(dst.iterdir()):
        die(f"New target run dir has existing files; do not overwrite: {dst}")
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(p.iterdir()):
        if f.is_file() and (f.name.startswith("rpointer.") or ".r." in f.name):
            shutil.copy2(f, dst/f.name)
    # Use actual dated pointer files, not invented new restart pointer contents.
    # A previous CIME archive can have only dated pointers.
    stamp = f"{year:04d}-01-01-00000"
    for f in list(dst.glob("rpointer.*")):
        if f.name.endswith("."+stamp):
            un = dst/f.name[: -len("."+stamp)]
            if not un.exists():
                shutil.copy2(f, un)
    names = {f.name for f in dst.iterdir() if f.is_file()}
    if not any(n.startswith("rpointer.") for n in names):
        die(f"{target} missing staged rpointer")
    for f in dst.glob("rpointer.*"):
        if f.name.endswith("."+stamp):
            continue
        for line in f.read_text(errors="replace").splitlines():
            v = line.strip().strip("'\"")
            if v.endswith(".nc") and Path(v).name not in names:
                die(f"Pointer {f} references missing {v}")
    for prefix in ("cpl","datm","clm2"):
        if f"{C[source]}.{prefix}.r.{stamp}.nc" not in names:
            die(f"{target} stage missing source {prefix} restart")


def put_finidat(stage, source, year):
    path = R[stage] / f"{C[source]}.clm2.r.{year:04d}-01-01-00000.nc"
    nml = S[stage] / "user_nl_clm"
    text = nml.read_text(errors="replace")
    text = re.sub(r"(?m)^\s*finidat\s*=.*(?:\n|$)", "", text)
    nml.write_text(text.rstrip()+f"\nfinidat = '{path}'\n")


def new_stage(stage):
    """Make an independent CIME hybrid case ONLY after source final archive completes."""
    src = PREV[stage]
    if not completed(src, END[src]):
        die(f"{src} is not completed at model year {END[src]}")
    if S[stage].exists() or A[stage].exists() or R[stage].exists():
        die(f"{stage} already exists; cannot safely recreate automatically")
    preflight_inodes()
    print("CREATING",stage,"from",src,flush=True)
    run([SCRIPTS/"create_clone","--case",S[stage],
         "--clone",S["PRE50"],"--keepexe"], SCRIPTS, capture=False)
    cfg = {
        "RUN_TYPE": "hybrid",
        "CONTINUE_RUN": "FALSE",
        "RUN_REFCASE": C[src],
        "RUN_REFDATE": f"{END[src]:04d}-01-01",
        "RUN_STARTDATE": f"{START[stage]:04d}-01-01",
        "GET_REFCASE": "FALSE",
        "CLM_ACCELERATED_SPINUP": MODES[stage],
        "STOP_OPTION":"nyears", "STOP_N":"5",
        "REST_OPTION":"nyears", "REST_N":"5",
        "RESUBMIT":"0", "DOUT_S":"TRUE",
        "RUNDIR":str(R[stage]), "DOUT_S_ROOT":str(A[stage]),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"
    }
    for k,v in cfg.items():
        change(stage,k,v)
    stage_restart(src,stage,END[src])
    put_finidat(stage,src,END[src])
    if not (S[stage]/".case.run").is_file():
        run(["./case.setup"],S[stage],capture=False)
    run(["./preview_namelists"],S[stage],capture=False)
    validate_case(stage)
    if xml(stage,"RUN_TYPE") != "hybrid" or xml(stage,"CONTINUE_RUN").lower() != "false":
        die("Hybrid initialization not configured correctly")
    if xml(stage,"RUN_REFCASE") != C[src] or xml(stage,"RUN_REFDATE") != f"{END[src]:04d}-01-01":
        die("Hybrid refcase/refdate mismatch")
    run(["./check_input_data"],S[stage],capture=False)
    print("STAGE PREPARED",stage,"at",S[stage],flush=True)


def saved_state():
    return json.loads(LEDGER.read_text()) if LEDGER.is_file() else {
        "created_at":now(),"armed":False,"actions":{},"idle_checks":0}


def save_state(s):
    tmp=LEDGER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s,indent=2,sort_keys=True)+"\n")
    tmp.replace(LEDGER)


def action_once(s,key,operation):
    if key in s["actions"]:
        if s["actions"][key]["state"] == "DONE":
            return False
        die(f"Action {key} has an unfinished ATTEMPTED receipt: manual review needed")
    s["actions"][key]={"state":"ATTEMPTED","at":now()}
    save_state(s)
    operation()
    s["actions"][key]={"state":"DONE","at":now()}
    save_state(s)
    print("ACTION DONE",key,flush=True)
    return True


def submit_stage(stage):
    preflight_inodes()
    validate_case(stage)
    assert_no_old_submission(stage)
    run(["./case.submit"], S[stage], capture=False)
    print(stage,"first 5y submitted",flush=True)


def stage_continue(stage):
    preflight_inodes()
    if active_jobs(stage):
        die(f"{stage} still has active jobs")
    if not completed(stage,FIRST5[stage]):
        die(f"{stage} first five years not complete")
    if xml(stage,"RESUBMIT")!="0":
        die(f"{stage}: first5 was not a standalone smoke submission")
    # Explicit checkpoint verified. Same-case continuation must use latest rpointer.
    if not R[stage].is_dir() or not list(R[stage].glob("rpointer.*")):
        die(f"{stage} has no latest RUNDIR rpointer; stage manually with audit first")
    change(stage,"CONTINUE_RUN","TRUE")
    change(stage,"RESUBMIT",str(LEFT_RESUBMITS[stage]))
    validate_case(stage)
    run(["./case.submit"],S[stage],capture=False)
    print(stage,"remaining 5-year segments submitted",flush=True)


def next_watch(s):
    if STOPFILE.exists() or not s["armed"]:
        print("Watch stopped (disarmed).",flush=True)
        return
    # New Slurm job for NEXT check; job is not a daemon and consumes minutes
    # only when it runs. Keeps at most one successor job in the queue.
    cmd=["sbatch",f"--begin={WATCH_INTERVAL}","--parsable",str(WATCH)]
    job=run(cmd,STATE)
    s["next_watch_submitted_at"]=now()
    s["next_watch_job_id"]=job
    save_state(s)
    print("NEXT WATCH SCHEDULED",job,flush=True)


def tick(s):
    check_common()
    print("Controller tick",now(),flush=True)
    if not s["armed"] or STOPFILE.exists():
        print("Controller disarmed; no action",flush=True)
        return False
    # If a step is still running, wait; never bind to a preliminary Slurm Job ID.
    if not completed("PRE50",END["PRE50"]):
        print("PRE50 still running or not archived to 2047; no stage submission",flush=True)
        if not active_jobs("PRE50"):
            s["idle_checks"]+=1
            save_state(s)
            if s["idle_checks"]>=MAX_IDLE_CHECKS:
                die("PRE50 appears stalled without queued jobs and final checkpoint")
        else:
            s["idle_checks"]=0; save_state(s)
        return True
    s["idle_checks"]=0
    if not S["AD200"].is_dir():
        action_once(s,"ad200:first5",lambda: (new_stage("AD200"),submit_stage("AD200")))
        return True
    if active_jobs("AD200"):
        print("AD200 has active jobs",active_jobs("AD200"),flush=True)
        return True
    if completed("AD200",END["AD200"]):
        if not S["POST300"].is_dir():
            action_once(s,"post300:first5",lambda: (new_stage("POST300"),submit_stage("POST300")))
            return True
        if active_jobs("POST300"):
            print("POST300 has active jobs",active_jobs("POST300"),flush=True)
            return True
        if completed("POST300",END["POST300"]):
            print("PIPELINE FINISHED: model year 2547 final checkpoint verified",flush=True)
            s["finished_at"]=now();s["armed"]=False;save_state(s)
            return False
        if completed("POST300",FIRST5["POST300"]):
            action_once(s,"post300:remaining295",lambda: stage_continue("POST300"))
            return True
        die("POST300 has no running job and no verified first5 or terminal restart")
    if completed("AD200",FIRST5["AD200"]):
        action_once(s,"ad200:remaining195",lambda: stage_continue("AD200"))
        return True
    die("AD200 has no running job and no verified first5 or terminal restart")


def install_watch():
    STATE.mkdir(parents=True,exist_ok=True)
    # Use the Python interpreter from the author's tested clm_fates_env;
    # export environment through sbatch from this interactive login shell.
    python=sys.executable
    script = (f"#!/usr/bin/env bash\n"
              f"#SBATCH --job-name=NL-Loo-NC-watch\n"
              f"#SBATCH --partition=batch\n"
              f"#SBATCH --nodes=1\n"
              f"#SBATCH --ntasks=1\n"
              f"#SBATCH --cpus-per-task=1\n"
              f"#SBATCH --mem=1G\n"
              f"#SBATCH --time=00:05:00\n"
              f"#SBATCH --output={STATE}/watch-%j.log\n"
              f"#SBATCH --mail-type=FAIL\n"
              f"set -euo pipefail\n"
              f"cd '{REPO}'\n"
              f"exec '{python}' '{Path(__file__).resolve()}' tick\n")
    if WATCH.exists() and WATCH.read_text()!=script:
        die("Existing watchdog script differs; refusing to overwrite")
    WATCH.write_text(script)
    WATCH.chmod(0o750)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd",choices=["plan","arm","tick","status","disarm"])
    p.add_argument("--confirm",default="")
    a=p.parse_args()
    if a.cmd=="plan":
        check_common()
        print("PRE50 running jobs",active_jobs("PRE50"))
        print("PRE50 2047 final archive",bool(cp_record("PRE50",END["PRE50"])))
        for st in ("AD200","POST300"):
            print(st,"case exists",S[st].exists(),"run/archive",R[st],A[st])
        print("Requirements: verified original PFT, unchanged CTSM, CONDA netCDF4, "
              "Slurm permits hourly lightweight watch, full restart.")
        print("No files changed; no jobs submitted.")
        return
    if a.cmd=="arm" and a.confirm!=CONFIRM:
        die("Explicit --confirm "+CONFIRM+" required")
    if a.cmd=="disarm":
        STATE.mkdir(parents=True,exist_ok=True)
        STOPFILE.write_text("Disarmed at "+now()+"\n")
        print("DISARMED: existing model jobs unchanged; pending watch will exit.")
        return
    if a.cmd=="status":
        s=saved_state()
        print(json.dumps(s,indent=2))
        for stage in C:
            print(stage,"jobs",active_jobs(stage), "case",S[stage].exists())
        return
    if a.cmd=="arm":
        check_common()
        if S["AD200"].exists() or S["POST300"].exists():
            die("Stage cases already exist; require manual provenance audit before arming")
        if STOPFILE.exists():
            die("STOP marker exists from earlier disarm; don't auto-remove")
        install_watch()
        with (STATE/"lock").open("a") as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            s=saved_state()
            if s["armed"]:
                die("Already armed; do not duplicate watcher")
            s["armed"]=True
            save_state(s)
            print("GATED PIPELINE ARMED. PRE50 is unchanged.")
            # Immediately schedule first watchdog; never submit model now.
            next_watch(s)
        return
    if a.cmd=="tick":
        if not LEDGER.exists():
            die("Not armed; run arm from login shell")
        with (STATE/"lock").open("a") as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            s=saved_state()
            try:
                keep=tick(s)
                if keep:
                    next_watch(s)
            except Exception as exc:
                # A failed gate is a terminal stop. Operator inspects detailed log.
                s["armed"]=False
                s["error"]={"time":now(),"message":str(exc)}
                save_state(s)
                raise


if __name__=="__main__":
    main()
