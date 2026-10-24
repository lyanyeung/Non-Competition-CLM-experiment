#!/usr/bin/env python3
"""Recover exact DE-Tha direct-AD400 first-stage preview-namelist failure.

Pinned CTSM CLMBuildNamelist.pm incorrectly gates accelerated spinup_state
under use_cn alone. FATES uses use_cn=.false., use_fates=.true. We use the
NL-Loo-verified private overlay with TWO narrowly pinned changes:
  1. allow (use_cn OR use_fates) in setup_cmdl_spinup
  2. gate CN-only reseed_dead_plants under use_cn.
Shared CTSM, already-built cesm.exe and all old sites remain untouched.

AUDIT: strictly read-only. RECOVER: isolated overlay, temporary
COMP_ROOT_DIR_LND path, preview_namelists, check_input_data, restored
locked env_case.xml, guarded first-5y submission ledger initialization.
No Slurm jobs submitted. A failed RECOVER leaves an attempted ledger and
must NOT be retried without inspecting the partial case/overlay.

The original failed stage stopped at ./preview_namelists on 2026-10-24:
DO NOT run Stage10 'stage' again (case already exists).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("detha_stage10",HERE/"10_DE_Tha_direct_AD400.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Missing Stage10 script")
C=importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

SRC=C.CTSM/"bld/CLMBuildNamelist.pm"
SRC_BLOB="698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
OVERLAY=C.WORK/"ctsm_ad400_namelist_private_overlay"
TARGET=OVERLAY/"bld/CLMBuildNamelist.pm"
CURRENT=C.CASE/"env_case.xml"
LOCKED=C.CASE/"LockedFiles/env_case.xml"
ATTEMPT=C.WORK/"recovery_attempt.json"
OLD="if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
WIDE="if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
RESEED='if ( $nl_flags->{$var} ne "off" ) {'
RESEED_FIXED="if ( $nl_flags->{$var} ne \"off\" && &value_is_true($nl_flags->{'use_cn'}) ) {"
CONFIRM="RECOVER_DE_THA_AD400_FATES_PRIVATE_NAMELIST_NO_SLURM"

def fail(s):
    raise RuntimeError(str(s))

def call(args,cwd=None,timeout=240):
    r=subprocess.run([str(x) for x in args],cwd=cwd,
                     capture_output=True,text=True,timeout=timeout,check=False)
    print("COMMAND"," ".join(map(str,args)),"RC",r.returncode,flush=True)
    if r.stdout: print(r.stdout[-4000:],flush=True)
    if r.stderr: print("STDERR",r.stderr[-4000:],flush=True)
    if r.returncode:
        fail("Command failed. STOP; do not rerun recovery blindly.")
    return r.stdout.strip()

def filehash(p):
    return C.sha(p)

def xml_records(path):
    if not path.is_file():
        fail("Expected locked XML missing: "+str(path))
    out={}
    root=ET.parse(path).getroot()
    for entry in root.iter("entry"):
        ident=entry.attrib.get("id")
        if ident:out[ident]=entry.attrib.get("value")
    return out

def cime_lock_preflight():
    original=xml_records(LOCKED)
    current=xml_records(CURRENT)
    if original!=current or LOCKED.read_bytes()!=CURRENT.read_bytes():
        fail("env_case.xml differs from LockedFiles/env_case.xml BEFORE recovery")
    if original.get("COMP_ROOT_DIR_LND")!="$SRCROOT":
        fail("Locked COMP_ROOT_DIR_LND is not literal $SRCROOT; inspect manually")
    if Path(C.xml(C.CASE,"COMP_ROOT_DIR_LND")).resolve()!=C.CTSM.resolve():
        fail("Live COMP_ROOT_DIR_LND does not resolve to shared CTSM")
    print("PASS: env_case.xml matches CIME lock, original COMP_ROOT_DIR_LND=$SRCROOT")

def diff_after_restore():
    if not CURRENT.is_file() or not LOCKED.is_file():
        fail("CIME env_case.xml lock lost")
    if CURRENT.read_bytes()!=LOCKED.read_bytes():
        fail("CIME env_case.xml lock mismatch after restoration. DO NOT SUBMIT.")

def pinned_patch():
    if call(["git","-C",str(C.CTSM),"hash-object",str(SRC)])!=SRC_BLOB:
        fail("Shared original CLMBuildNamelist.pm blob changed")
    source=SRC.read_text(encoding="utf-8")
    start=source.index("sub setup_cmdl_spinup {")
    end=source.index("sub setup_cmdl_simulation_year {",start)
    section=source[start:end]
    if section.count(OLD)!=1 or section.count(RESEED)!=1:
        fail("Pinned upstream spinup guards changed; no broad/unsafe string replace")
    amended=section.replace(OLD,WIDE,1).replace(RESEED,RESEED_FIXED,1)
    return source[:start]+amended+source[end:]

def no_prior_submission():
    if not C.CASE.is_dir():
        fail("Failed-stage CIME case does not exist; Stage10 inspect/stage path applies")
    if C.STATE.exists() or C.WORK.exists():
        fail("Controller/work folder already exists: another recovery/stage may have been attempted")
    if C.RUN.is_dir() and any(C.RUN.glob("*.r.*.nc")):
        fail("Restart files exist in target run folder; cannot assert no prior run")
    if C.ARCH.exists():
        fail("Target archive path already exists; cannot assert this is only a failed preview")
    if C.queue_matches():
        fail("Target case already has queued jobs")
    history=(C.CASE/"CaseStatus")
    if not history.is_file():
        fail("CIME CaseStatus missing")
    content=history.read_text(errors="replace")
    if not re.search(r"case\.setup success",content):
        fail("CaseStatus lacks successful case.setup")
    if re.search(r"case\.submit starting|case\.submit success|case\.run starting|case\.run success",content):
        fail("CIME case was submitted or run: abort recovery")
    if (C.CASE/".submit_options").exists():
        fail("Unexpected existing .submit_options (may indicate submission)")
    # Active Slurm queue may be empty for a previous completed job: also
    # check accounting for target job names since creation.
    sacct=call(["sacct","-u",C.USER,"-X","-n","-P",
                "--starttime","2026-10-23T00:00:00",
                "--format=JobIDRaw,JobName%128,State"],timeout=60)
    for row in sacct.splitlines():
        values=row.split("|")
        if len(values)>1 and values[1].strip() in (
                "run."+C.NAME,"st_archive."+C.NAME):
            fail("Historical job record exists; never auto-resubmit: "+row)
    print("PASS: no archived run, case.submit history, current/historical Slurm job or controller")

def audit():
    C.verify_surface()
    no_prior_submission()
    cime_lock_preflight()
    if C.xml(C.CASE,"BUILD_COMPLETE").lower()!="true":
        fail("Cloned case not marked built")
    if C.xml(C.CASE,"EXEROOT")!=C.xml(C.EXISTING,"EXEROOT"):
        fail("Cloned exe path differs from existing DE-Tha FATES")
    bldopts=C.xml(C.CASE,"CLM_BLDNML_OPTS")
    print("CLM_BLDNML_OPTS:",repr(bldopts))
    # FATES BGC mode must be selected at build-namelist invocation level;
    # user_nl_clm: use_fates=true by itself is not sufficient evidence.
    if not re.search(r"(?:^|\s)-bgc\s+fates(?:\s|$)",bldopts):
        fail("Case CLM_BLDNML_OPTS does NOT contain '-bgc fates'. "
             "Do not apply overlay to SP-mode configuration. "
             "Inspect case CLM_BLDNML_OPTS and CLM_CONFIG_OPTS first.")
    if C.xml(C.CASE,"CLM_ACCELERATED_SPINUP").lower()!="on":
        fail("AD accelerator not enabled")
    if C.xml(C.CASE,"RUN_TYPE").lower()!="startup":
        fail("Not a cold-start startup case")
    if C.xml(C.CASE,"RESUBMIT")!="0" or C.xml(C.CASE,"STOP_N")!="5":
        fail("Not isolated initial five-year smoke with RESUBMIT=0")
    if not (C.CASE/".case.run").is_file() or not (C.CASE/"case.st_archive").is_file():
        fail("Missing setup-generated run/archive scripts")
    for key,val in C.NAMELIST.items():
        txt=(C.CASE/"user_nl_clm").read_text()
        if key=="hist_fincl1":
            got=re.findall(r"'([^']+)'",C.nml_value_raw(txt,key))
            if got!=C.HISTORY:
                fail("FATES history list incorrect: "+str(got))
        elif C.nml_value(txt,key)!=val.strip("'\""):
            fail("User namelist does not match configured FATES/AD state: "+key)
    patch=pinned_patch()
    print("PASS pinned CTSM source revision:",C.CTSM_REV)
    print("PASS private patch validated: FATES or CN spinup, reseed_dead_plants CN-only")
    print("PASS original case, shared CTSM and executable untouched")
    print("AUDIT PASSED: no changes or jobs. Eligible for guarded repair.")
    return patch

def build_overlay(patch):
    if OVERLAY.exists():
        fail("Private overlay already exists")
    OVERLAY.mkdir(parents=True,exist_ok=False)
    for p in C.CTSM.iterdir():
        if p.name in (".git","bld"):
            continue
        (OVERLAY/p.name).symlink_to(p)
    dest=OVERLAY/"bld"
    dest.mkdir()
    for p in (C.CTSM/"bld").iterdir():
        if p.name in ("CLMBuildNamelist.pm","build-namelist"):
            continue
        (dest/p.name).symlink_to(p)
    shutil.copy2(C.CTSM/"bld/build-namelist",dest/"build-namelist")
    TARGET.write_text(patch,encoding="utf-8")
    if TARGET.read_text(encoding="utf-8")!=patch:
        fail("Private patch content not verified")
    print("PASS: private overlay created; shared CTSM unchanged")

def restore_lock():
    # Force the original literal XML variable reference with no shell expansion.
    call(["./xmlchange","COMP_ROOT_DIR_LND=$SRCROOT"],cwd=C.CASE,timeout=60)
    diff_after_restore()
    if Path(C.xml(C.CASE,"COMP_ROOT_DIR_LND")).resolve()!=C.CTSM.resolve():
        fail("Restored component path does not resolve to shared CTSM")
    print("PASS: env_case.xml matches locked copy again")

def repair():
    patch=audit()
    C.WORK.mkdir(parents=True,exist_ok=False)
    ATTEMPT.write_text(json.dumps({
        "status":"ATTEMPTED_UNCERTAIN",
        "origin_error":"CLMBuildNamelist.pm FATES accelerated spinup rejected as SP",
        "action":"private source overlay + restore XML lock; no submission",
        "started":datetime.now(timezone.utc).isoformat()
    },indent=2)+"\n")
    build_overlay(patch)
    call(["./xmlchange",f"COMP_ROOT_DIR_LND={OVERLAY}"],cwd=C.CASE,timeout=60)
    if Path(C.xml(C.CASE,"COMP_ROOT_DIR_LND")).resolve()!=OVERLAY.resolve():
        fail("Private overlay not selected correctly")
    call(["./preview_namelists"],cwd=C.CASE,timeout=240)
    call(["./check_input_data"],cwd=C.CASE,timeout=300)
    # Verify the ACTUAL generated FATES namelist before restoring the locked
    # XML root; never rely only on the user_nl setting.
    C.validation_namelists()
    restore_lock()
    C.validate()
    if C.STATE.exists():
        fail("Unexpected existing controller state; STOP")
    executable=Path(C.xml(C.CASE,"EXEROOT"))/"cesm.exe"
    C.STATE.write_text(json.dumps({
        "site":"DE-Tha",
        "experiment":"DIRECT_AD400_COLDSTART",
        "case":str(C.CASE),
        "v2_surface":str(C.SURFACE),
        "surface_sha256":C.SURF_SHA,
        "base_exe_sha256":filehash(executable),
        "stage":"PREPARED_NOT_SUBMITTED",
        "action_history":["STAGE10_FAILED_PREVIEW","STAGE12_PRIVATE_OVERLAY_REPAIRED"],
        "first_5y":{"start_year":1996,"end_year":2001},
        "target_end":2396,
        "intended_segments":80,
        "resubmit":0,
        "watchdog_armed":False,
        "postAD_scheduled":False,
        "user_accepts_existing_forcing_QC_REVIEW":True,
        "isolated_overlay":str(OVERLAY),
        "case_xml_lock_restored":True,
        "repaired_utc":datetime.now(timezone.utc).isoformat()
    },indent=2)+"\n")
    ATTEMPT.write_text(json.dumps({"status":"DONE_NO_JOBS",
                      "completed":datetime.now(timezone.utc).isoformat()},indent=2)+"\n")
    print("REPAIR PASS: Stage10 validate passed, cold-start AD spinup_state=2")
    print("PREPARED_NOT_SUBMITTED; no Slurm job, first 5 years only when explicitly requested")
    print("Use Stage10 validate again; then Stage10 submit-smoke, never Stage10 stage")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("audit","repair"))
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="audit":
        audit()
    else:
        if a.confirm!=CONFIRM:fail("repair requires --confirm "+CONFIRM)
        repair()

if __name__=="__main__":
    main()
