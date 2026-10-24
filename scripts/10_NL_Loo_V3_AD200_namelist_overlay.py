#!/usr/bin/env python3
"""Safely stage a PRIVATE CTSM namelist-only overlay for NL-Loo V3 AD200.

The pinned CTSM build-namelist incorrectly guards spinup_state defaults under
use_cn only; -bgc fates sets use_cn=false and silently leaves state 0.
This tool patches ONLY a private copy of CLMBuildNamelist.pm, never CTSM itself.
'aduit'/'stage' never submits Slurm jobs. After stage, verify the output before
using 09_NL_Loo_V3_auto550.py submit-staged-ad200.
"""
from __future__ import annotations

import argparse
import fcntl
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
RUN = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS/NL-Loo_OBSPFT_NC_V3_AD200/run")
ARCH = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS/archive/NL-Loo_OBSPFT_NC_V3_AD200")
PRE = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS/archive/NL-Loo_OBSPFT_NC_V3_PRE50/rest/2047-01-01-00000")
OVERLAY = WORK / "ctsm_ad200_namelist_only_overlay"
SRC_BLOB = "698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
CTSM_REV = "d5ea9d0136530370a62ef267ccfaff6f001ef914"
SRC = CTSM / "bld/CLMBuildNamelist.pm"
TARGET = OVERLAY / "bld/CLMBuildNamelist.pm"
OLD = "if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
NEW = "if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
NAME = "NL-Loo_OBSPFT_NC_V3_PRE50"


def fail(message):
    raise RuntimeError(message)


def call(*args, cwd=None):
    p = subprocess.run([str(x) for x in args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode:
        fail(f"Command failed ({p.returncode}): {' '.join(map(str,args))}\n"
             f"{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout.strip()


def xq(key):
    return call("./xmlquery", key, "--value", cwd=CASE)


def setting(txt, key):
    m = re.search(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*(.*?)\s*$", txt)
    return m.group(1).strip().strip("'\"") if m else None


def jobs():
    out = call("squeue", "-u", USER, "-h", "-o", "%i|%j|%T")
    return [x for x in out.splitlines() if "NL-Loo_OBSPFT_NC_V3_AD200" in x
            and ("run." in x or "st_archive." in x)]


def verify():
    if not CASE.is_dir() or not RUN.is_dir():
        fail("Existing AD200 case or staged run directory missing")
    if ARCH.exists():
        fail("AD200 archive exists: do not modify or duplicate this stage")
    if jobs():
        fail("AD200 Slurm job exists: refuse to modify running case")
    if (CASE / "V3_first_submission_attempt.json").exists():
        fail("AD200 submission marker exists")
    status = (CASE / "CaseStatus").read_text(errors="replace")
    if re.search(r"case\.submit starting|case\.run starting", status):
        fail("AD200 case appears already submitted")
    state = json.loads((WORK / "controller.json").read_text())
    if (state.get("armed") is not False or
            state.get("actions", {}).get("AD200_first") != "ATTEMPTED" or
            state.get("actions", {}).get("PRE50_first") != "DONE"):
        fail("Controller not in expected stopped/partially prepared state")
    if (WORK / "STOP").exists():
        fail("STOP marker exists; inspect operator intervention")
    if call("git", "rev-parse", "HEAD", cwd=CTSM) != CTSM_REV:
        fail("CTSM revision changed")
    if call("git", "hash-object", SRC, cwd=CTSM) != SRC_BLOB:
        fail("Original CLMBuildNamelist.pm content changed")
    if xq("CLM_ACCELERATED_SPINUP").lower() != "on":
        fail("AD200 mode is not on")
    if xq("RUN_TYPE").lower() != "hybrid" or xq("RUN_REFDATE") != "2047-01-01":
        fail("AD200 hybrid restart setup differs")
    if xq("STOP_N") != "5" or xq("RESUBMIT") != "0":
        fail("AD200 not configured for a single five-year test")
    if xq("RUN_REFCASE") != NAME:
        fail("AD200 source case mismatch")
    if (CASE / "CaseDocs/lnd_in").is_file():
        nml = (CASE / "CaseDocs/lnd_in").read_text()
        if setting(nml, "use_fates") != ".true." or setting(nml, "use_cn") != ".false.":
            fail("Expected FATES mode with use_cn=false")
        if setting(nml, "use_fates_nocomp") != ".true." or setting(nml, "use_fates_fixed_biogeog") != ".true.":
            fail("Observed fixed-biogeography/no-comp mode missing")
    from netCDF4 import Dataset
    pre_n = PRE / f"{NAME}.clm2.r.2047-01-01-00000.nc"
    if not pre_n.is_file():
        fail("PRE50 final land restart absent")
    with Dataset(pre_n) as ds:
        if "spinup_state" not in ds.variables:
            fail("PRE50 spinup_state missing")
        val = int(ds.variables["spinup_state"][:].reshape(-1)[0])
        if val != 0:
            fail(f"PRE50 restart should be normal mode state 0, saw {val}")
    for component in ("clm2", "datm", "cpl"):
        name = f"{NAME}.{component}.r.2047-01-01-00000.nc"
        p = PRE / name
        q = RUN / name
        if not p.is_file() or not q.is_file() or p.stat().st_size != q.stat().st_size:
            fail(f"Staged reference restart missing/different size: {name}")
    if not (RUN / "rpointer.lnd").is_file():
        fail("Land restart pointer missing")
    print("PASS: stopped AD200, PRE50 restart spinup_state=0, staged files present")
    print("AD200 jobs: none | submission marker: absent")


def make_overlay():
    if OVERLAY.exists():
        fail("Private overlay already exists; inspect it; no overwrites")
    original_root = Path(xq("COMP_ROOT_DIR_LND")).resolve()
    if original_root != CTSM.resolve():
        fail(f"Unexpected case component root {original_root}; no change")
    src_text = SRC.read_text()
    begin = src_text.index("sub setup_cmdl_spinup {")
    end = src_text.index("sub setup_cmdl_simulation_year {", begin)
    segment = src_text[begin:end]
    if segment.count(OLD) != 1:
        fail("Pinned FATES spinup guard not uniquely found")
    patch = src_text[:begin] + segment.replace(OLD, NEW, 1) + src_text[end:]
    OVERLAY.mkdir(parents=True, exist_ok=False)
    for item in CTSM.iterdir():
        if item.name in (".git", "bld"):
            continue
        (OVERLAY / item.name).symlink_to(item)
    bld = OVERLAY / "bld"
    bld.mkdir()
    for item in (CTSM / "bld").iterdir():
        if item.name in ("CLMBuildNamelist.pm", "build-namelist"):
            continue
        (bld / item.name).symlink_to(item)
    shutil.copy2(CTSM / "bld/build-namelist", bld / "build-namelist")
    TARGET.write_text(patch)
    print("PRIVATE PATCH: only one guard in setup_cmdl_spinup changed")
    print("ORIGINAL CTSM SOURCE UNCHANGED")
    print("Overlay:", OVERLAY)


def validate_generated():
    f = CASE / "CaseDocs/lnd_in"
    if not f.is_file():
        fail("CaseDocs/lnd_in missing")
    txt = f.read_text()
    for key, expected in (("spinup_state", "2"),
                          ("use_fates", ".true."),
                          ("use_cn", ".false."),
                          ("use_fates_fixed_biogeog", ".true."),
                          ("use_fates_nocomp", ".true.")):
        actual = setting(txt, key)
        if actual != expected:
            fail(f"Generated lnd_in {key} expected {expected}, got {actual!r}")
    fin = setting(txt, "finidat")
    expected = str(RUN / f"{NAME}.clm2.r.2047-01-01-00000.nc")
    if fin != expected:
        fail(f"finidat unexpected: {fin!r}")
    if Path(xq("COMP_ROOT_DIR_LND")).resolve() != OVERLAY.resolve():
        fail("Private overlay root not selected")
    if xq("BUILD_COMPLETE").lower() != "true":
        fail("Existing executable no longer marked built; no submission")
    print("PASS: generated FATES AD namelist spinup_state=2, correct finidat")
    print("PASS: existing executable remains built")
    print("NO MODEL OR SLURM JOB SUBMITTED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("audit", "stage"))
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    WORK.mkdir(exist_ok=True)
    with (WORK / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify()
        print("COMP_ROOT_DIR_LND:", xq("COMP_ROOT_DIR_LND"))
        if args.action == "audit":
            print("READ ONLY: stage would create isolated namelist overlay, NOT submit")
            return
        if args.confirm != "STAGE_PRIVATE_NL_LOO_AD200_NAMELIST_ONLY":
            fail("Missing --confirm STAGE_PRIVATE_NL_LOO_AD200_NAMELIST_ONLY")
        make_overlay()
        call("./xmlchange", f"COMP_ROOT_DIR_LND={OVERLAY}", cwd=CASE)
        print("Case-only XML land component root changed; regenerating namelists")
        print(call("./preview_namelists", cwd=CASE)[-1200:])
        print(call("./check_input_data", cwd=CASE)[-1200:])
        validate_generated()


if __name__ == "__main__":
    main()
