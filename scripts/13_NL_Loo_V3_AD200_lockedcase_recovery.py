#!/usr/bin/env python3
"""Recover ONE AD200 smoke submit blocked by CIME's immutable env_case.xml lock.

We previously pointed COMP_ROOT_DIR_LND at a private namelist-only overlay,
generated and checked spinup_state=2, then case.submit failed before Slurm with
'env_case.xml' locked-file mismatch. CIME cannot submit until we restore the
original $SRCROOT reference in env_case.xml. We preserve the generated land
namelist using CIME's supported --skip-preview-namelist option, which carries
through to case.run. RESUBMIT=0; controller and watchdog remain disarmed.

audit          Read-only verification (no writes/jobs).
recover-submit Restore only COMP_ROOT_DIR_LND then submit the ONE 2047-2052
               smoke segment. No case clone, build, new science input, or
               195-year continuation. Existing submission ledgers are not
               deleted/rewound; a new one-time recovery action is recorded.
status         Read-only report about the attempted smoke run.

If any preflight fails, inspect output. Do not rerun submit blindly.
"""
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    if not spec or not spec.loader:
        raise RuntimeError("Cannot import " + filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


C = load("09_NL_Loo_V3_auto550.py", "nl_loo_v3")
O = load("11_NL_Loo_V3_AD200_fix_private_overlay.py", "nl_loo_private")
STAGE = "AD200"
CASE = C.CASE[STAGE]
RUN = C.RUN[STAGE]
LEDGER_ACTION = "AD200_env_case_lock_recovery_smoke"
PREVIOUS_ACTION = "AD200_smoke_2047_2052"
CONFIRM = "RECOVER_NL_LOO_AD200_LOCKED_CASE_AND_SUBMIT_5Y"
CURRENT = CASE / "env_case.xml"
LOCKED = CASE / "LockedFiles/env_case.xml"
MARKER = CASE / "V3_first_submission_attempt.json"
SUBMIT_OPTIONS = CASE / ".submit_options"


def fail(s):
    raise RuntimeError(s)


def run(args, cwd=None):
    r = subprocess.run([str(i) for i in args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if r.returncode:
        fail(f"{' '.join(map(str,args))}: rc={r.returncode}\n"
             f"stdout={r.stdout[-2400:]}\nstderr={r.stderr[-2400:]}")
    return r.stdout.strip()


def records(path):
    """Raw XML entry values; keep $SRCROOT literal for lock-safe restoration."""
    root = ET.parse(path).getroot()
    entries = {}
    for entry in root.iter("entry"):
        ident = entry.attrib.get("id")
        if ident:
            entries[ident] = entry.attrib.get("value")
    if "COMP_ROOT_DIR_LND" not in entries:
        fail("COMP_ROOT_DIR_LND not found in " + str(path))
    return entries


def xml_lock_state():
    if not CURRENT.is_file() or not LOCKED.is_file():
        fail("Missing original locked env_case.xml or current env_case.xml")
    actual, expected = records(CURRENT), records(LOCKED)
    keys = set(actual) | set(expected)
    changed = {k: (expected.get(k), actual.get(k))
               for k in keys if expected.get(k) != actual.get(k)}
    allowed = {"COMP_ROOT_DIR_LND"}
    if set(changed) - allowed:
        fail("Unexpected additional env_case.xml changes: " + repr(changed))
    original = expected["COMP_ROOT_DIR_LND"]
    if original != "$SRCROOT":
        fail("Locked COMP_ROOT_DIR_LND is not literal $SRCROOT: " + repr(original))
    if changed and Path(C.xq(STAGE, "COMP_ROOT_DIR_LND")).resolve() != O.OVERLAY.resolve():
        fail("Current COMP_ROOT_DIR_LND differs from expected isolated overlay")
    return original, changed


def historical_jobs():
    """Fail closed unless Slurm accounting can exclude an earlier AD200 run."""
    # The failed submission happened on 2026-10-24; include prior day.
    args = ["sacct", "-u", C.U, "-X", "-n", "-P",
            "--starttime", "2026-10-23T00:00:00",
            "--format", "JobIDRaw,JobName%128,State"]
    try:
        output = run(args)
    except Exception as e:
        fail("Cannot verify Slurm accounting; manual job-history audit required: " + str(e))
    hits = []
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name = parts[1].strip()
        if name in ("run." + C.NAME[STAGE], "st_archive." + C.NAME[STAGE]):
            hits.append(line)
    if hits:
        fail("Slurm already has AD200 job history; do not automatically retry:\n"
             + "\n".join(hits[:20]))
    return True


def smoke_settings():
    if not C.STATE.is_file() or C.STOP.exists():
        fail("Controller missing or STOP operator marker exists")
    state = C.load()
    if state.get("armed") is not False:
        fail("Controller is armed: watcher may submit a duplicate job")
    if state.get("actions", {}).get("PRE50_first") != "DONE":
        fail("PRE50 not recorded done")
    if state.get("actions", {}).get("AD200_first") != "ATTEMPTED":
        fail("AD200 first action is not the expected failed ATTEMPTED state")
    if state.get("actions", {}).get(PREVIOUS_ACTION) != "ATTEMPTED":
        fail("Earlier smoke attempt has unexpected ledger state")
    if LEDGER_ACTION in state.get("actions", {}):
        fail("Recovery already attempted; never retry without audit")
    if state.get("actions", {}).get("AD200_remaining") is not None:
        fail("Remaining AD200 has already been attempted")
    if not state.get("hold_after_first_ad_segment") or not state.get("ad_only"):
        fail("No evidence controller is configured to hold after the five-year test")

    if MARKER.is_file():
        data = json.loads(MARKER.read_text())
        if data.get("phase") != "first":
            fail("Unexpected prior submission marker content")
    else:
        fail("Expected prior AD200 first submission marker absent")

    if C.ARCH[STAGE].exists() or C.slurm(STAGE):
        fail("AD200 archive or Slurm job exists: cannot retry")
    queue = C.cmd(["squeue", "-u", C.U, "-h", "-o", "%i|%j|%T"])
    if any("NL-Loo-V3-watch" in l for l in queue.splitlines()):
        fail("A V3 watchdog is currently queued/running")
    if C.slurm("PRE50"):
        fail("PRE50 Slurm jobs still active")
    historical_jobs()
    logfile = (CASE / "CaseStatus").read_text(errors="replace")
    if "case.submit success" in logfile:
        fail("CaseStatus shows a successful case.submit already")
    if re.search(r"(?im)case\.run (?:starting|success|error)", logfile):
        fail("AD200 model already started: inspect instead")
    if not re.search(r"(?im)case\.submit (?:error|failed)", logfile):
        fail("CaseStatus does not document the blocked case.submit; inspect first")
    if C.xq(STAGE, "COMP_ROOT_DIR_LND") != str(O.OVERLAY):
        # xq returns an expanded path; trailing separator variants are fine.
        if Path(C.xq(STAGE, "COMP_ROOT_DIR_LND")).resolve() != O.OVERLAY.resolve():
            # If already restored after a partial recovery, other checks still
            # reject duplicate ledger actions, but permit verification.
            if Path(C.xq(STAGE, "COMP_ROOT_DIR_LND")).resolve() != C.CTSM.resolve():
                fail("Unexpected current component root")
    existing, bad, fixed = O.inspect()
    if existing != fixed:
        fail("Corrected private namelist builder no longer present")
    # O.verify_generated checks the overlay root; it MUST precede restoration.
    if Path(C.xq(STAGE, "COMP_ROOT_DIR_LND")).resolve() == O.OVERLAY.resolve():
        O.verify_generated()
    C.check(STAGE)
    if not C.complete("PRE50", 2047):
        fail("PRE50 2047 restart archive not verified")

    expected = {
        "RUN_TYPE": "hybrid",
        "RUN_REFCASE": C.NAME["PRE50"],
        "RUN_REFDATE": "2047-01-01",
        "RUN_STARTDATE": "2047-01-01",
        "CLM_ACCELERATED_SPINUP": "on",
        "CONTINUE_RUN": "FALSE",
        "STOP_OPTION": "nyears",
        "STOP_N": "5",
        "REST_OPTION": "nyears",
        "REST_N": "5",
        "RESUBMIT": "0",
        "GET_REFCASE": "FALSE",
        "DOUT_S": "TRUE",
    }
    for key, val in expected.items():
        if C.xq(STAGE, key).lower() != val.lower():
            fail(f"{key} differs: {C.xq(STAGE,key)}")

    # Check the namelist that skip-preview-namelist will actually preserve.
    for path in (CASE / "CaseDocs/lnd_in", RUN / "lnd_in"):
        if not path.is_file():
            fail("Missing previously generated land namelist: " + str(path))
        nml = path.read_text()
        for key, val in (("spinup_state", "2"), ("use_fates", ".true."),
                         ("use_cn", ".false."), ("use_fates_nocomp", ".true."),
                         ("use_fates_fixed_biogeog", ".true.")):
            if C.nml_get(nml, key) != val:
                fail(f"{path}: {key} differs or missing")
    if C.hashfile(CASE / "CaseDocs/lnd_in") != C.hashfile(RUN / "lnd_in"):
        fail("CaseDocs and RUNDIR lnd_in content differs")
    src_dir = C.ARCH["PRE50"] / "rest" / "2047-01-01-00000"
    for comp in ("clm2", "datm", "cpl"):
        name = f"{C.NAME['PRE50']}.{comp}.r.2047-01-01-00000.nc"
        a, b = src_dir / name, RUN / name
        if not a.is_file() or not b.is_file() or C.hashfile(a) != C.hashfile(b):
            fail("Staged restart mismatch: " + name)
    if SUBMIT_OPTIONS.exists():
        fail("Existing .submit_options: inspect before attempting recovery")

    print("PASS: previous submit was recorded as FAILED, no model job or Slurm history")
    print("PASS: PRE50 2047 restart, AD200 FATES spinup_state=2, namelists preserved")
    print("PASS: RESUBMIT=0 and controller disarmed; no 195-year continuation")
    return state


def audit():
    original, changed = xml_lock_state()
    print("Locked env_case.xml original:", original)
    print("Allowed env_case.xml diff:", changed or "none")
    smoke_settings()
    print("AUDIT ONLY: NO FILES CHANGED, NO SLURM JOBS SUBMITTED")


def recover_submit():
    original, changed = xml_lock_state()
    smoke_settings()
    C.validate_base()
    C.quota()
    # Check no change introduced by the last validation.
    xml_lock_state()
    historical_jobs()

    # Mark non-repeatable action BEFORE changing anything or submitting.
    state = C.load()
    state["actions"][LEDGER_ACTION] = "ATTEMPTED"
    state["armed"] = False
    state["ad_only"] = True
    state["hold_after_first_ad_segment"] = True
    C.save(state)

    if changed:
        # Pass literal string. Do not expand $SRCROOT through the shell.
        run(["./xmlchange", "COMP_ROOT_DIR_LND=" + original], cwd=CASE)
    _, after = xml_lock_state()
    if after:
        fail("Locked env_case.xml mismatch remains after restoration: " + repr(after))
    if Path(C.xq(STAGE, "COMP_ROOT_DIR_LND")).resolve() != C.CTSM.resolve():
        fail("Restored COMP_ROOT_DIR_LND does not resolve to shared CTSM")

    # Explicitly do NOT call plain case.submit: it would regenerate lnd_in
    # with unpatched shared source, silently losing spinup_state=2.
    # CIME case_submit.check_case + case_run._pre_run_check respect skip_pnl.
    print("PASS: env_case.xml lock restored; submitting with --skip-preview-namelist",
          flush=True)
    try:
        output = run(["./case.submit", "--skip-preview-namelist"], cwd=CASE)
        print(output[-4000:], flush=True)
    except Exception as exc:
        state = C.load()
        state["armed"] = False
        state["error"] = {"at": C.utc(), "message": str(exc)}
        C.save(state)
        raise

    state = C.load()
    state["actions"][LEDGER_ACTION] = "DONE"
    state["actions"][PREVIOUS_ACTION] = "DONE"
    state["actions"]["AD200_first"] = "DONE"
    state["armed"] = False
    state["ad_only"] = True
    state["hold_after_first_ad_segment"] = True
    state.pop("error", None)
    state["ad_smoke_recovery_submitted_at"] = C.utc()
    C.save(state)
    print("AD200 SMOKE SUBMITTED: 2047-2052 (one five-year segment ONLY)", flush=True)
    print("Watchdog DISARMED. DO NOT run plain case.submit or start 195-year continuation.")


def status():
    state = C.load()
    print("Controller armed:", state.get("armed"))
    print("Recovery action:", state.get("actions", {}).get(LEDGER_ACTION))
    print("5-year smoke action:", state.get("actions", {}).get(PREVIOUS_ACTION))
    print("AD200 jobs:", C.slurm(STAGE))
    print("Archive checkpoint 2052 exists:",
          (C.ARCH[STAGE] / "rest/2052-01-01-00000").is_dir())
    try:
        print("env_case.xml differences:", xml_lock_state()[1])
    except Exception as exc:
        print("env_case.xml audit error:", exc)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("audit", "recover-submit", "status"))
    p.add_argument("--confirm", default="")
    args = p.parse_args()
    if args.action == "status":
        status()
        return
    if args.action == "recover-submit" and args.confirm != CONFIRM:
        fail("Requires --confirm " + CONFIRM)
    with C.LOCK.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "audit":
            audit()
        else:
            recover_submit()


if __name__ == "__main__":
    main()
