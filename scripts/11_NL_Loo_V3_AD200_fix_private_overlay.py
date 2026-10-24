#!/usr/bin/env python3
"""Repair ONLY the previously created NL-Loo AD200 private namelist overlay.

The earlier overlay caused CTSM's CN-only reseed_dead_plants default to be set
for FATES; CTSM then correctly rejected the namelist. This script adds an
explicit use_cn gate around that ONE default in the existing private module.
The shared CTSM source and executable are not changed. No Slurm submission.

Usage:
  python3 scripts/11_NL_Loo_V3_AD200_fix_private_overlay.py audit
  python3 scripts/11_NL_Loo_V3_AD200_fix_private_overlay.py repair \
    --confirm REPAIR_EXISTING_NL_LOO_AD200_PRIVATE_OVERLAY
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

USER = "ly3n24"
ROOT = Path(f"/iridisfs/scratch/{USER}/CLM_FATES")
CTSM = ROOT / "CTSM"
CASE = ROOT / "cases/NL-Loo_OBSPFT_NC_V3_AD200"
WORK = Path.home() / "NL_Loo_V3_auto550"
OUT = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS")
ARCH = OUT / "archive/NL-Loo_OBSPFT_NC_V3_AD200"
OVERLAY = WORK / "ctsm_ad200_namelist_only_overlay"
ORIG = CTSM / "bld/CLMBuildNamelist.pm"
TARGET = OVERLAY / "bld/CLMBuildNamelist.pm"
BACKUP = OVERLAY / "bld/CLMBuildNamelist.pm.bad_v1_backup"
PINNED_REV = "d5ea9d0136530370a62ef267ccfaff6f001ef914"
PINNED_BLOB = "698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
OLD = "if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
WIDE = "if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
RESEED = 'if ( $nl_flags->{$var} ne "off" ) {'
RESEED_FIXED = 'if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'
PRE = OUT / "archive/NL-Loo_OBSPFT_NC_V3_PRE50/rest/2047-01-01-00000"
PRE_NAME = "NL-Loo_OBSPFT_NC_V3_PRE50"


def fail(message):
    raise RuntimeError(str(message))


def run(*args, cwd=None):
    p = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        fail(f"{' '.join(map(str,args))} returned {p.returncode}\n"
             f"STDOUT:\n{p.stdout[-4000:]}\nSTDERR:\n{p.stderr[-4000:]}")
    return p.stdout.strip()


def xml(key):
    return run("./xmlquery", key, "--value", cwd=CASE)


def nml(text, key):
    m = re.search(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*(.*?)\s*$", text)
    return m.group(1).strip().strip("'\"") if m else None


def inspect():
    if not CASE.is_dir() or not TARGET.is_file():
        fail("AD200 case / existing private overlay missing")
    if ARCH.exists():
        fail("AD200 archive already exists, refuse to modify")
    if (CASE / "V3_first_submission_attempt.json").exists():
        fail("AD200 first-submission marker exists")
    if re.search(r"case\.submit starting|case\.run starting",
                 (CASE / "CaseStatus").read_text(errors="replace")):
        fail("AD200 was previously submitted")
    jobs = run("squeue", "-u", USER, "-h", "-o", "%i|%j|%T")
    if any("NL-Loo_OBSPFT_NC_V3_AD200" in line and
           ("run." in line or "st_archive." in line)
           for line in jobs.splitlines()):
        fail("AD200 currently has Slurm jobs")
    state = json.loads((WORK / "controller.json").read_text())
    if (state.get("armed") is not False or
        state.get("actions", {}).get("AD200_first") != "ATTEMPTED" or
        state.get("actions", {}).get("PRE50_first") != "DONE"):
        fail("Controller state no longer indicates halted partially prepared AD200")
    if (WORK / "STOP").exists():
        fail("STOP marker exists")
    if run("git", "rev-parse", "HEAD", cwd=CTSM) != PINNED_REV:
        fail("Shared CTSM revision differs")
    if run("git", "hash-object", ORIG, cwd=CTSM) != PINNED_BLOB:
        fail("Shared CTSM namelist module differs")
    if Path(xml("COMP_ROOT_DIR_LND")).resolve() != OVERLAY.resolve():
        fail("AD200 does not point to the expected isolated overlay")
    if (xml("CLM_ACCELERATED_SPINUP").lower() != "on"
            or xml("RUN_TYPE") != "hybrid"
            or xml("RUN_REFCASE") != PRE_NAME
            or xml("RUN_REFDATE") != "2047-01-01"
            or xml("STOP_N") != "5"
            or xml("RESUBMIT") != "0"):
        fail("AD200 mode/refcase/first-segment XML differs")
    from netCDF4 import Dataset
    with Dataset(PRE / f"{PRE_NAME}.clm2.r.2047-01-01-00000.nc") as ds:
        if "spinup_state" not in ds.variables:
            fail("PRE50 restart lacks spinup_state")
        value = int(ds.variables["spinup_state"][:].reshape(-1)[0])
        if value != 0:
            fail(f"Expected PRE50 normal spinup_state=0, got {value}")
    src = ORIG.read_text()
    start, end = src.index("sub setup_cmdl_spinup {"), src.index("sub setup_cmdl_simulation_year {")
    seg = src[start:end]
    if seg.count(OLD) != 1 or seg.count(RESEED) != 1:
        fail("Original spinup module does not have unique expected guards")
    wide = seg.replace(OLD, WIDE, 1)
    bad = src[:start] + wide + src[end:]
    fixed = src[:start] + wide.replace(RESEED, RESEED_FIXED, 1) + src[end:]
    existing = TARGET.read_text()
    if existing not in (bad, fixed):
        fail("Private overlay does not match exact earlier patch or this narrow fix")
    print("PASS: AD200 not submitted, PRE50 state=0, shared CTSM source unchanged")
    print("Overlay:", TARGET)
    print("Overlay status:", "BAD_V1" if existing == bad else "FIXED")
    print("Change to apply: keep FATES spinup_state default; gate reseed_dead_plants to CN")
    return existing, bad, fixed


def verify_generated():
    txt = (CASE / "CaseDocs/lnd_in").read_text()
    expected = {
        "spinup_state": "2",
        "use_cn": ".false.",
        "use_fates": ".true.",
        "use_fates_sp": ".false.",
        "use_fates_fixed_biogeog": ".true.",
        "use_fates_nocomp": ".true.",
        "soil_decomp_method": "CENTURYKoven2013",
    }
    for key, target in expected.items():
        value = nml(txt, key)
        if value != target:
            fail(f"AD200 generated {key}: expected {target!r}, found {value!r}")
    if nml(txt, "reseed_dead_plants") is not None:
        fail("reseed_dead_plants (CN-only) still present")
    fin = nml(txt, "finidat")
    expected_fin = str(OUT / "NL-Loo_OBSPFT_NC_V3_AD200/run"
                       / f"{PRE_NAME}.clm2.r.2047-01-01-00000.nc")
    if fin != expected_fin:
        fail(f"finidat unexpectedly changed: {fin}")
    if xml("BUILD_COMPLETE").lower() != "true":
        fail("BUILD_COMPLETE false; do not submit")
    if not (Path(xml("EXEROOT")) / "cesm.exe").is_file():
        fail("Existing executable not found")
    print("PASS: generated spinup_state=2 with FATES BGC, no CN-only reseed")
    print("PASS: 2047 PRE50 finidat and existing executable")
    print("NO SLURM JOB SUBMITTED; CHECK PHASE TRANSITION SCIENTIFICALLY")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("audit", "repair"))
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.action == "repair" and args.confirm != "REPAIR_EXISTING_NL_LOO_AD200_PRIVATE_OVERLAY":
        fail("Explicit --confirm REPAIR_EXISTING_NL_LOO_AD200_PRIVATE_OVERLAY required")
    with (WORK / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing, bad, fixed = inspect()
        if args.action == "audit":
            print("READ ONLY: no model tasks started")
            return
        if existing == bad:
            if BACKUP.exists():
                fail(f"Backup already exists: {BACKUP}; no overwrite")
            shutil.copy2(TARGET, BACKUP)
            tmp = TARGET.with_name(TARGET.name + ".new")
            if tmp.exists():
                fail(f"Temporary file already exists: {tmp}")
            tmp.write_text(fixed)
            os.replace(tmp, TARGET)
            print("PRIVATE MODULE FIXED; ORIGINAL CTSM UNCHANGED")
        else:
            print("FIX ALREADY PRESENT; regenerate and validate only")
        output = run("./preview_namelists", cwd=CASE)
        print("PREVIEW SUCCESS\n" + output[-2000:])
        result = run("./check_input_data", cwd=CASE)
        print("INPUT CHECK SUCCESS\n" + result[-1000:])
        verify_generated()


if __name__ == "__main__":
    main()
