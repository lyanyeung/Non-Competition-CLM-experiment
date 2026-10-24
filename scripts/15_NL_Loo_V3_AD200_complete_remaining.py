#!/usr/bin/env python3
"""NL-Loo V3 AD200: verify 2052 restart, then run 195 remaining model years.

SAFETY
- 'audit': READ ONLY. Checks exact 5-year Slurm jobs, CIME CaseStatus,
  full archived 2052 checkpoint and FATES AD spinup_state=2.
  Detects stale PRE50 2047 pointers left by a hybrid smoke run and validates
  that only a 2052 restart pointer handoff is needed.
- 'continue-195': backups original AD200 run pointers, checksums 2052 three
  component restart files, stages ONLY AD200 run pointers and then submits
  2052->2057 + 38 subsequent 5-year CIME resubmissions; DOUT_S archiver
  orchestrates them.
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
import shutil
import os
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
HANDOFF = C.WORK / "AD200_2052_verified_pointer_handoff"
POINTERS = (("rpointer.lnd","clm2"),("rpointer.atm","datm"),
            ("rpointer.cpl","cpl"))

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

def expected_restart(component, model_year):
    case = C.NAME["PRE50"] if model_year == 2047 else C.NAME[STAGE]
    return f"{case}.{component}.r.{model_year:04d}-01-01-00000.nc"


def pointer_state(pointer, component):
    """Read-only check: 2047 original or correct 2052 pointer, and archive content."""
    p = RUN / pointer
    if not p.is_file() or p.is_symlink():
        fail(f"Expected ordinary active pointer file: {p}")
    raw = p.read_text(errors="replace")
    lines = [x.strip().strip("'\"") for x in raw.splitlines() if x.strip()]
    if len(lines) != 1:
        fail(f"Unrecognized pointer content {pointer}: {lines}")
    loc = Path(lines[0])
    if loc.is_absolute() or ".." in loc.parts or loc.name != lines[0]:
        fail(f"Unsafe or nonlocal restart pointer {pointer}: {loc}")
    earlier = expected_restart(component, 2047)
    latest = expected_restart(component, 2052)
    if loc.name not in (earlier, latest):
        fail(f"Unexpected restart date in {pointer}: {loc}")
    archive_file = REF / latest
    if not archive_file.is_file() or archive_file.is_symlink():
        fail(f"Verified 2052 restart not found as regular archive file: {archive_file}")
    if archive_file.stat().st_size < 1024:
        fail(f"Archived 2052 restart too small: {archive_file}")
    local_latest = RUN / latest
    if local_latest.exists():
        if not local_latest.is_file() or C.hashfile(local_latest) != C.hashfile(archive_file):
            fail(f"Conflicting 2052 restart already in run directory: {local_latest}")
    if loc.name == earlier:
        previous = RUN / earlier
        if not previous.is_file():
            fail(f"Old pointer has no source file: {previous}")
    elif not local_latest.exists():
        # A correct active pointer with a missing file is recoverable using
        # the fully checked archival copy; require explicit staging before submit.
        pass
    print(f"POINTER {pointer}: {loc.name} -> {latest}" +
          (" (unchanged)" if loc.name == latest else " (handoff required)"),flush=True)
    return loc.name == latest and local_latest.is_file()


def audit_pointer_handoff():
    valid = [pointer_state(pointer,component) for pointer,component in POINTERS]
    if HANDOFF.exists():
        fail("Previous 2052 handoff directory exists; inspect before any further submit")
    if all(valid):
        print("PASS: all 2052 pointers and restart files already staged",flush=True)
    else:
        print("PASS: archive verified; 2052 pointer/file staging needed for continuation",flush=True)


def stage_2052_handoff():
    """Only change three active pointers and stage verified AD200 2052 restarts."""
    if HANDOFF.exists():
        fail("2052 handoff backup already exists; do not repeat")
    audit_pointer_handoff()
    HANDOFF.mkdir(parents=True,exist_ok=False)
    manifest = {"source":str(REF),"year":2052,"files":{}}
    for ptr,comp in POINTERS:
        p = RUN / ptr
        back = HANDOFF / (ptr + ".before")
        shutil.copy2(p,back)
        manifest["files"][ptr]={"original":p.read_text(),
                                "old_sha256":C.hashfile(p),
                                "backup":str(back)}
    (HANDOFF/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    for ptr,comp in POINTERS:
        filename = expected_restart(comp,2052)
        src = REF / filename
        dest = RUN / filename
        if not dest.exists():
            shutil.copy2(src,dest)
        if C.hashfile(dest) != C.hashfile(src):
            fail(f"Staged restart checksum mismatch: {dest}")
        p = RUN / ptr
        # Rewrite only after all archived restart files were verified. The
        # original pointers remain permanently backed up in HANDOFF.
        tmp = RUN / (ptr+".stage2052_tmp")
        if tmp.exists():
            fail(f"Unexpected temporary pointer exists: {tmp}")
        tmp.write_text(filename+"\n")
        os.chmod(tmp,p.stat().st_mode & 0o777)
        os.replace(tmp,p)
    if not all(pointer_state(ptr,comp) for ptr,comp in POINTERS):
        fail("2052 pointers not fully verified after staging")
    print("PASS: AD200 2052 checkpoint pointers staged; PRE50 and archive untouched",
          flush=True)


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
        # C.nml_get() strips the outer quotes of a scalar value;
        # for a comma-delimited Fortran string list that would drop the
        # first/last delimiters. Read the full line without stripping them.
        hist = re.findall(r"(?im)^\\s*hist_fincl1\\s*=\\s*([^\\r\\n]*)$", text)
        if len(hist)!=1:
            fail(f"Expected one hist_fincl1 in {path}, got {len(hist)}")
        fields=re.findall(r"'([^']+)'",hist[0])
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
    audit_pointer_handoff()
    check_history()
    # Also validate all PRE50 science/surface/executable preconditions.
    C.validate_base()
    print("PASS: 2052 archived AD restart spinup_state=2, safe pointer handoff eligible",flush=True)
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
        # CIME left PRE50's 2047 rpointer.lnd active after successful hybrid
        # smoke. Stage only the verified 2052 restart in this AD200 RUNDIR.
        stage_2052_handoff()
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
