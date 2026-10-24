#!/usr/bin/env python3
"""NL-Loo V3 AD200: verify 2052 restart, then run 195 remaining model years.

SAFETY
- 'audit': READ ONLY. Checks exact 5-year Slurm jobs, CIME CaseStatus,
  full archived 2052 checkpoint, FATES AD spinup_state=2 and 3 restart pointers.
- 'continue-195': single guarded submission for 2052->2057 + 38 subsequent
  5-year CIME resubmissions; DOUT_S short-term archiver orchestrates them.
- Shared CTSM code/binaries, PRE50/POST300 and unrelated Slurm jobs untouched.
- CIME --skip-preview-namelist preserves the verified private FATES AD namelist;
  *never* submit this case without this option.
- No watcher rearming. Does not claim scientifically converged carbon stocks.

Usage on IRIDIS LOGIN node:
  python3 scripts/15_NL_Loo_V3_AD200_complete_remaining.py audit
  python3 scripts/15_NL_Loo_V3_AD200_complete_remaining.py continue-195 \
      --confirm CONTINUE_VERIFIED_NL_LOO_AD200_FROM_2052_TO_2247
"""
from __future__ import annotations

import argparse
import configparser
import fcntl
import importlib.util
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

def script(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

C = script("09_NL_Loo_V3_auto550.py", "nl_loo_spinup")
STAGE = "AD200"
CASE = C.CASE[STAGE]
RUN = C.RUN[STAGE]
REF = C.ARCH[STAGE] / "rest/2052-01-01-00000"
FIRST_JOB = "4710752"
FIRST_ARCH = "4710753"
ACTION = "AD200_remaining_2052_to_2247_verified"
CONFIRM = "CONTINUE_VERIFIED_NL_LOO_AD200_FROM_2052_TO_2247"
HISTORY = ("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")

def fail(s):
    raise RuntimeError(str(s))

def run(args, cwd=None):
    p = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       check=False, timeout=180)
    if p.returncode:
        fail(f"{' '.join(map(str,args))} rc={p.returncode}:\n"
             f"{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p.stdout.strip()

def accounting():
    out = run(["sacct","-X","-j",f"{FIRST_JOB},{FIRST_ARCH}",
               "-n","-P","--format=JobIDRaw,JobName%128,State,ExitCode,Elapsed"])
    d = {}
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts)>=4 and parts[0].strip() in (FIRST_JOB, FIRST_ARCH):
            d[parts[0].strip()] = tuple(x.strip() for x in parts[1:4])
    expected = ((FIRST_JOB,"run."+C.NAME[STAGE]),(FIRST_ARCH,"st_archive."+C.NAME[STAGE]))
    for number,name in expected:
        if number not in d or d[number][0]!=name:
            fail(f"Slurm accounting lacks expected job {number} {name}: {d}")
        if d[number][1]!="COMPLETED" or d[number][2]!="0:0":
            fail(f"Slurm {number} is not successful: {d[number]}")
    # Reject unexpected additional AD200 runs since the 2026-10-24 incident.
    out=run(["sacct","-u",C.U,"-X","-n","-P",
             "--starttime","2026-10-23T00:00:00",
             "--format","JobIDRaw,JobName%128,State"])
    allowed={"4710529","4710530", FIRST_JOB, FIRST_ARCH}
    for line in out.splitlines():
        cols=line.split("|")
        if len(cols)<2: continue
        name=cols[1].strip()
        if name in ("run."+C.NAME[STAGE],"st_archive."+C.NAME[STAGE]) and cols[0] not in allowed:
            fail(f"Unexpected additional AD200 Slurm job: {line}")
    print(f"PASS: Slurm run {FIRST_JOB} and archive {FIRST_ARCH}: COMPLETED/0:0",flush=True)

def check_pointer(pointer,component):
    p = RUN / pointer
    if not p.is_file():
        fail(f"Active {pointer} missing; do NOT manually overwrite restart pointers")
    lines=[x.strip().strip("'\"") for x in p.read_text(errors="replace").splitlines() if x.strip()]
    if len(lines)!=1:
        fail(f"Unexpected multi-line {pointer}: {lines}")
    loc=Path(lines[0])
    if loc.is_absolute() or ".." in loc.parts:
        fail(f"Unsafe restart pointer {pointer}: {loc}")
    expected = f"{C.NAME[STAGE]}.{component}.r.2052-01-01-00000.nc"
    if loc.name != expected:
        fail(f"{pointer} does not reference the 2052 checkpoint: {loc} != {expected}")
    local=RUN/loc
    saved=REF/expected
    if not (local.is_file() and saved.is_file()):
        fail(f"Missing latest restart: {local} / {saved}")
    if C.hashfile(local)!=C.hashfile(saved):
        fail(f"Latest run restart differs from archived checkpoint: {local}")

def check_history():
    for path in (CASE/"CaseDocs/lnd_in",RUN/"lnd_in"):
        if not path.is_file():
            fail(f"Missing AD200 namelist: {path}")
        text=path.read_text()
        for key,value in (("spinup_state","2"),("use_fates",".true."),
                          ("use_cn",".false."),("use_fates_nocomp",".true."),
                          ("use_fates_fixed_biogeog",".true.")):
            if C.nml_get(text,key)!=value:
                fail(f"Incorrect {key} in {path}")
        inc=C.nml_get(text,"hist_fincl1")
        fields=re.findall(r"'([^']+)'",inc or "")
        if tuple(fields)!=HISTORY:
            fail(f"Unexpected AD history list {fields} in {path}")
    if C.hashfile(CASE/"CaseDocs/lnd_in")!=C.hashfile(RUN/"lnd_in"):
        fail("Land namelist in CASE and RUNDIR differs")
    config=CASE/".submit_options"
    if not config.is_file():
        fail("Missing CIME .submit_options; future resubmissions might regenerate AD namelist")
    cfg=configparser.RawConfigParser()
    cfg.read(config)
    if not cfg.has_section("SubmitOptions") or not cfg.getboolean(
            "SubmitOptions","skip_pnl",fallback=False):
        fail("CIME resubmission is not configured with skip_pnl=True")
    print("PASS: FATES fixed-biogeography/no-comp, spinup_state=2 and history outputs",flush=True)
    print("PASS: --skip-preview-namelist persists in CIME .submit_options",flush=True)

def audited_state():
    if not C.STATE.is_file() or C.STOP.exists():
        fail("Controller state missing or explicit operator STOP exists")
    d=C.load()
    if d.get("armed") is not False or not d.get("ad_only"):
        fail("V3 watchdog is armed or AD-only guard absent")
    if not d.get("hold_after_first_ad_segment"):
        fail("Five-year smoke hold marker missing")
    if d.get("actions",{}).get("AD200_history_4710529_five_year_retry")!="DONE":
        fail("Fixed GPP/NPP 5-year retry not recorded successfully")
    if d.get("history_retry_model_job")!=FIRST_JOB or d.get("history_retry_archive_job")!=FIRST_ARCH:
        fail("Controller smoke job IDs do not match known validated Slurm jobs")
    if "AD200_remaining" in d.get("actions",{}) or ACTION in d.get("actions",{}):
        fail("AD200 continuation has already been attempted")
    if any(p.exists() for p in (C.CASE["POST300"],C.ARCH["POST300"],C.RUN["POST300"])):
        fail("POST300 already staged: this continuation must not interfere")
    return d

def audit():
    d=audited_state()
    accounting()
    queued=C.cmd(["squeue","-u",C.U,"-h","-o","%i|%j|%T"])
    for l in queued.splitlines():
        seg=l.split("|")
        if len(seg)>=2 and (seg[1] in ("run."+C.NAME[STAGE],
            "st_archive."+C.NAME[STAGE]) or seg[1]=="NL-Loo-V3-watch"):
            fail(f"AD200/watcher job already queued: {l}")
    if C.slurm("PRE50"):
        fail("PRE50 currently has a job")
    if C.xq(STAGE,"CONTINUE_RUN").lower()!="false" or C.xq(STAGE,"RESUBMIT")!="0":
        fail("CIME flags no longer match completed single-segment test")
    for k,v in (("RUN_TYPE","hybrid"),("CLM_ACCELERATED_SPINUP","on"),
                ("STOP_N","5"),("STOP_OPTION","nyears"),("REST_N","5"),
                ("REST_OPTION","nyears"),("RUN_REFDATE","2047-01-01"),
                ("RUN_REFCASE",C.NAME["PRE50"]),("DOUT_S","TRUE"),
                ("EXTERNAL_WORKFLOW","FALSE")):
        if C.xq(STAGE,k).lower()!=v.lower():
            fail(f"Unexpected CIME {k}: {C.xq(STAGE,k)!r}")
    if C.xq(STAGE,"BUILD_COMPLETE").lower()!="true":
        fail("Case executable is not marked complete")
    if C.xq(STAGE,"EXEROOT") != C.xq("PRE50","EXEROOT"):
        fail("Executable differs from successful PRE50")
    if (CASE/"LockedFiles/env_case.xml").read_bytes()!=(CASE/"env_case.xml").read_bytes():
        fail("CIME env_case.xml lock is not restored")
    # Enforce both CIME records and all three component files.
    if not C.complete(STAGE,2052):
        fail("2052 archived checkpoint / CIME success not verified")
    if C.spinup_value(STAGE,2052)!=2:
        fail("2052 restart must be FATES AD spinup_state=2")
    for comp,pointer in (("clm2","rpointer.lnd"),("datm","rpointer.atm"),
                         ("cpl","rpointer.cpl")):
        check_pointer(pointer,comp)
    check_history()
    # Also validate all PRE50 science/surface/executable preconditions.
    C.validate_base()
    print("PASS: 2052 archived AD restart spinup_state=2, three checksummed live pointers",flush=True)
    print("PASS: controller disarmed; no queued AD jobs; 39 x 5-year segments remain",flush=True)
    print("AUDIT PASSED: 2052->2247 continuation eligible",flush=True)
    return d

def continue_remaining():
    audit()
    # Once audited again under the lock, mark before any CIME writes.
    d=C.load()
    d["actions"][ACTION]="ATTEMPTED"
    d["actions"]["AD200_remaining"]="ATTEMPTED"
    d["armed"]=False
    d["ad_only"]=True
    C.save(d)
    try:
        C.change(STAGE,"CONTINUE_RUN","TRUE")
        C.change(STAGE,"RESUBMIT","38")
        if C.xq(STAGE,"RESUBMIT")!="38" or C.xq(STAGE,"CONTINUE_RUN").lower()!="true":
            fail("CIME continuation flags failed to update")
        if C.xq(STAGE,"RESUBMIT_SETS_CONTINUE_RUN").lower()!="true":
            fail("CIME auto-resubmit might not set CONTINUE_RUN true")
        # Original V3 run ledger is retained; no re-use or deletion of the old markers.
        out=run(["./case.submit","--skip-preview-namelist"],cwd=CASE)
        print(out[-4000:],flush=True)
    except Exception as e:
        d=C.load()
        d["armed"]=False
        d["error"]={"at":C.utc(),"message":str(e)}
        C.save(d)
        raise
    match=re.search(r"Submitted job case\.run with id (\d+)",out)
    archive=re.search(r"Submitted job case\.st_archive with id (\d+)",out)
    if not match or not archive:
        fail("CIME returned no parseable run/archive job IDs: inspect before any retry")
    d=C.load()
    d["actions"][ACTION]="DONE"
    d["actions"]["AD200_remaining"]="DONE"
    d["armed"]=False
    d["ad_only"]=True
    d["hold_after_first_ad_segment"]=False
    d["remaining_run_job"]=match.group(1)
    d["remaining_archive_job"]=archive.group(1)
    d["remaining_submitted_at"]=C.utc()
    d.pop("error",None)
    C.save(d)
    print(f"AD200 CONTINUATION SUBMITTED 2052-2247: run={match.group(1)} archive={archive.group(1)}",flush=True)
    print("STOP_N=5; 38 CIME auto-resubmissions after the first new 5y job",flush=True)
    print("V3 WATCHDOG DISARMED; POST300 not scheduled; do NOT repeat this command",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("audit","continue-195","status"))
    parser.add_argument("--confirm",default="")
    args=parser.parse_args()
    if args.action=="status":
        d=C.load()
        print("AD200 remaining:",d.get("actions",{}).get(ACTION))
        print("CONTINUE_RUN:",C.xq(STAGE,"CONTINUE_RUN"))
        print("RESUBMIT:",C.xq(STAGE,"RESUBMIT"))
        print("Active AD jobs:",C.slurm(STAGE))
        print("2247 archive exists:",(C.ARCH[STAGE]/"rest/2247-01-01-00000").is_dir())
        return
    if args.action=="continue-195" and args.confirm!=CONFIRM:
        fail("Explicit confirmation required: --confirm "+CONFIRM)
    with C.LOCK.open("a") as fh:
        fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=="audit":
            audit()
        else:
            continue_remaining()

if __name__=="__main__":
    main()
