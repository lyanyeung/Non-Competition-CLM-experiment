#!/usr/bin/env python3
"""Batch01: reuse the proven DE-Tha Stage12 PRIVATE namelist overlay for ten AD5 cases.

Root cause is PINNED CTSM (d5ea9d0) CLMBuildNamelist.pm setup_cmdl_spinup:
it accepts explicit spinup_state=2 only with use_cn, but FATES has use_cn=false.
Exact error is hardcoded "BGC mode is Satellite Phenology", EVEN WITH --bgc fates.

The two transformations are precisely those in DE-Tha Stage12:
  1. allow (use_cn OR use_fates) at the spinup setup guard;
  2. restrict reseed_dead_plants to use_cn only.

Unlike prior broken Stage11 'stage', this script does not run preview_namelists
through unpatched shared CTSM. It creates a SINGLE private CTSM overlay via
symlinks (not 10 copies), temporarily sets the NEW case's COMP_ROOT_DIR_LND
to the overlay, generates and verifies FATES AD namelists, restores the
literal original CIME case XML lock, then writes the usual Stage11 state.

Existing 10 site surfaces / source CIME cases / shared CTSM / executables /
existing forcing are NEVER modified. No Slurm jobs are submitted here.

Commands:
  python3 -B .../12_batch10_recover_FATES_AD_private_overlay.py self-test
  python3 -B .../12_batch10_recover_FATES_AD_private_overlay.py recover \
    --confirm RECOVER_BATCH01_TEN_FATES_AD_CASES_NO_SLURM
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
SCRIPT11=HERE/"11_batch10_AD400_oneclick.py"
spec=importlib.util.spec_from_file_location("batch11",SCRIPT11)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load existing Batch01 Stage11")
B=importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

SHARED_SOURCE=B.CTSM/"bld/CLMBuildNamelist.pm"
EXPECTED_GIT_BLOB="698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
OVERLAY=B.OUT_BASE/"_private_ctsm_FATES_AD400_namelist_overlay"
PATCHED=OVERLAY/"bld/CLMBuildNamelist.pm"
PROVEN=B.REPO/"examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py"
ACK="RECOVER_BATCH01_TEN_FATES_AD_CASES_NO_SLURM"

OLD="if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
NEW="if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
OLD_RESEED='if ( $nl_flags->{$var} ne "off" ) {'
NEW_RESEED='if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'

def fail(s):
    raise RuntimeError(str(s))

def git_blob_bytes(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def create_patch():
    if not SHARED_SOURCE.is_file():
        fail("Shared source not found: "+str(SHARED_SOURCE))
    raw=SHARED_SOURCE.read_bytes()
    source_blob=git_blob_bytes(raw)
    if source_blob!=EXPECTED_GIT_BLOB:
        fail("CTSM source Git blob differs from DE-Tha pinned patch: "+
             source_blob+" != "+EXPECTED_GIT_BLOB+"; leave source untouched")
    txt=raw.decode("utf-8")
    lo=txt.index("sub setup_cmdl_spinup {")
    hi=txt.index("sub setup_cmdl_simulation_year {",lo)
    target=txt[lo:hi]
    if target.count(OLD)!=1 or target.count(OLD_RESEED)!=1:
        fail("Old FATES AD guard / reseed source signature changed; STOP")
    fixed=target.replace(OLD,NEW,1).replace(OLD_RESEED,NEW_RESEED,1)
    return txt[:lo]+fixed+txt[hi:]

def proven_reference_check():
    # Exact strings used by the successful DE-Tha Stage12 recovery.
    src=PROVEN.read_text(encoding="utf8")
    if not all(item in src for item in (
            EXPECTED_GIT_BLOB, OLD, NEW, OLD_RESEED,
            "COMP_ROOT_DIR_LND=$SRCROOT", "preview_namelists")):
        fail("Proven DE-Tha Stage12 reference changed: STOP")

def create_overlay(patch):
    if OVERLAY.exists() or OVERLAY.is_symlink():
        fail("Private overlay already exists; do not overwrite: "+str(OVERLAY))
    OVERLAY.mkdir(parents=True,exist_ok=False)
    for p in B.CTSM.iterdir():
        if p.name in (".git","bld"):
            continue
        (OVERLAY/p.name).symlink_to(p)
    dest=OVERLAY/"bld"
    dest.mkdir()
    for p in (B.CTSM/"bld").iterdir():
        if p.name in ("build-namelist","CLMBuildNamelist.pm"):
            continue
        (dest/p.name).symlink_to(p)
    shutil.copy2(B.CTSM/"bld/build-namelist",dest/"build-namelist")
    PATCHED.write_text(patch,encoding="utf8")
    if PATCHED.read_text(encoding="utf8")!=patch:
        fail("Private patched code mismatch")
    if git_blob_bytes(SHARED_SOURCE.read_bytes())!=EXPECTED_GIT_BLOB:
        fail("Shared CTSM changed during overlay construction")
    print("PRIVATE OVERLAY CREATED:",OVERLAY)
    print("Shared CTSM unchanged. Proven DE-Tha FATES AD fixes applied.")

def xml_entries(path):
    if not path.is_file():
        fail("Missing CIME case XML: "+str(path))
    return {x.attrib.get("id"):x.attrib.get("value")
            for x in ET.parse(path).getroot().iter("entry")
            if x.attrib.get("id")}

def require_unsubmitted(case,site):
    if case.is_symlink() or not case.is_dir():
        fail("Missing/unsafe new case dir "+str(case))
    if B.xmlquery(case,"CASE")!=B.case_name(site):
        fail("Wrong Batch01 isolated CIME case identity "+site)
    status=case/"CaseStatus"
    if status.is_file():
        cs=status.read_text(errors="replace")
        if re.search(r"case\.submit starting|case\.submit success|case\.run starting|case\.run success",cs):
            fail("Case has already been submitted or run: "+site)
    ledger=B.ledger_path(site)
    if ledger.exists() or ledger.is_symlink():
        fail("Case already has Stage11 state or partial recovery: "+site)
    if B.archive_path(site).exists():
        fail("Archive path already exists; do not touch: "+site)
    if B.run_path(site).is_dir():
        if any(B.run_path(site).glob("*.r.*.nc")):
            fail("Existing restart in target run: "+site)
    # There can be run directories from earlier FAILED preview_namelists; retain them.

def check_case_lock(case):
    current=case/"env_case.xml"
    locked=case/"LockedFiles/env_case.xml"
    if not current.is_file() or not locked.is_file() or current.read_bytes()!=locked.read_bytes():
        fail("CIME env_case.xml differs from LockedFiles original; inspect case: "+str(case))
    records=xml_entries(locked)
    if records.get("COMP_ROOT_DIR_LND")!="$SRCROOT":
        fail("COMP_ROOT_DIR_LND is not original literal $SRCROOT: "+str(case))
    if Path(B.xmlquery(case,"COMP_ROOT_DIR_LND")).resolve()!=B.CTSM.resolve():
        fail("Original component path does not resolve to shared CTSM "+str(case))
    return locked.read_bytes()

def get_cime_settings(site):
    settings=B.case_settings(site)
    if settings.get("CLM_BLDNML_OPTS")!=B.BGC_OPTS:
        fail("Stage11 BGC options differ from proven DE-Tha flags")
    return settings

def normalize_namelist(case,site):
    nl=case/"user_nl_clm"
    if not nl.is_file():
        fail("Missing cloned user_nl_clm "+site)
    s=nl.read_text(encoding="utf8")
    if B.nml_get(s,"finidat") not in (None,""):
        fail("Existing finidat; not a cold-start case "+site)
    if B.nml_get(s,"reseed_dead_plants") is not None:
        fail("CN-only reseed_dead_plants in user_nl_clm "+site)
    for key,value in B.desired_namelist(site).items():
        s=B.nml_set(s,key,value)
    nl.write_text(s,encoding="utf8")

def check_generated(case,site):
    doc=case/"CaseDocs/lnd_in"
    run=B.run_path(site)/"lnd_in"
    if not doc.is_file() or not run.is_file():
        fail("Missing generated CaseDocs or RUNDIR lnd_in "+site)
    if B.digest(doc)!=B.digest(run):
        fail("CaseDocs lnd_in and RUNDIR lnd_in differ "+site)
    txt=doc.read_text()
    for key,val in B.desired_namelist(site).items():
        if key=="hist_fincl1":
            fragment=re.findall(r"'([^']+)'",txt.split("hist_fincl1",1)[-1].split("\n",1)[0])
            if tuple(fragment)!=B.HISTORY:
                fail("FATES history list wrong "+site+" "+repr(fragment))
            continue
        if B.nml_get(txt,key)!=val.strip("'\""):
            fail("Generated FATES/AD namelist wrong "+site+" "+key)
    if B.nml_get(txt,"use_cn") not in (".false.","false"):
        fail("Generated lnd_in has CN mode "+site)
    if B.nml_get(txt,"finidat") not in (None,""):
        fail("Unexpected restart finidat "+site)
    if B.nml_get(txt,"reseed_dead_plants") is not None:
        fail("CN-only reseed_dead_plants was generated "+site)

def repair_one(site):
    surface=B.surface(site)
    rece=B.receipt(site)
    if not surface.is_file() or not rece.is_file():
        fail("Missing previously created surface/receipt "+site)
    meta=json.loads(rece.read_text())
    if meta.get("surface_sha256")!=B.digest(surface):
        fail("Surface receipt changed "+site)
    B.validate_surface(site,surface)
    old,exe=B.old_executable(site)
    case=B.case_path(site)
    attempt=B.OUT_BASE/site/"private_overlay_AD_recovery_attempt.json"
    if attempt.exists() or attempt.is_symlink():
        fail("Previous recovery attempt exists. Do NOT retry blindly: "+str(attempt))
    if case.exists() or case.is_symlink():
        require_unsubmitted(case,site)
        print(site,"RESUME EXISTING PARTIAL INDEPENDENT CASE",flush=True)
    else:
        if B.run_path(site).exists() or B.archive_path(site).exists():
            fail("Target run/archive exists without CIME case "+site)
        print(site,"CLONE NEW INDEPENDENT CASE",flush=True)
        B.cmd([B.CIMESCRIPTS/"create_clone","--case",case,"--clone",old,"--keepexe"],
              cwd=B.CIMESCRIPTS,timeout=420)
        require_unsubmitted(case,site)
    if B.xmlquery(case,"EXEROOT")!=str(exe.parent):
        fail("Case EXEROOT differs from the existing built FATES case "+site)
    for key,val in get_cime_settings(site).items():
        B.cmd([case/"xmlchange",key+"="+val],cwd=case,timeout=90)
    normalize_namelist(case,site)
    if not (case/".case.run").is_file():
        B.cmd([case/"case.setup"],cwd=case,timeout=300)
    lock_before=check_case_lock(case)
    B.ledger_path(site).parent.mkdir(parents=True,exist_ok=True)
    attempt.write_text(json.dumps({
        "site":site,"phase":"ATTEMPTED_UNCERTAIN",
        "overlay":str(OVERLAY),"at":datetime.now(timezone.utc).isoformat()
    },indent=2)+"\n")
    # Preserve the exact CIME lock even if preview_namelists raises.
    try:
        B.cmd([case/"xmlchange","COMP_ROOT_DIR_LND="+str(OVERLAY)],
              cwd=case,timeout=90)
        if Path(B.xmlquery(case,"COMP_ROOT_DIR_LND")).resolve()!=OVERLAY.resolve():
            fail("Private overlay did not become effective "+site)
        B.cmd([case/"preview_namelists"],cwd=case,timeout=600)
        check_generated(case,site)
    finally:
        # Restores the literal XML expression and the originally locked content.
        B.cmd([case/"xmlchange","COMP_ROOT_DIR_LND=$SRCROOT"],cwd=case,timeout=90)
        if (case/"env_case.xml").read_bytes()!=lock_before:
            fail("CIME env_case.xml differs from its prior LockedFiles copy: "+site)
    if Path(B.xmlquery(case,"COMP_ROOT_DIR_LND")).resolve()!=B.CTSM.resolve():
        fail("Case not restored to normal CTSM root "+site)
    if B.xmlquery(case,"CLM_BLDNML_OPTS").split()!=B.BGC_OPTS.split():
        fail("Wrong BGC option after overlay recovery "+site)
    if B.xmlquery(case,"CLM_ACCELERATED_SPINUP").lower()!="on":
        fail("AD accelerated mode was not enabled "+site)
    if B.xmlquery(case,"RESUBMIT")!="0" or B.xmlquery(case,"STOP_N")!="5":
        fail("Case segment length/resubmit policy changed "+site)
    B.ledger_path(site).write_text(json.dumps({
        "site":site,"case":str(case),
        "surface":str(surface),"surface_sha256":B.digest(surface),
        "template_case":str(old),"reused_executable":str(exe),
        "DATM":"INHERITED_EXISTING_TEMPLATE_STREAMS_UNMODIFIED",
        "CO2":"INHERITED_EXISTING_TEMPLATE_SETTINGS",
        "phase":"PREPARED_NOT_SUBMITTED",
        "first_five_years_only":True,
        "CLM_ACCELERATED_SPINUP":"on",
        "CLM_BLDNML_OPTS":B.BGC_OPTS,
        "spinup_state":2,"RESUBMIT":0,
        "private_overlay":str(OVERLAY),
        "CIME_env_case_lock_restored":True,
        "generated_lnd_in_sha256":B.digest(case/"CaseDocs/lnd_in"),
        "created_utc":datetime.now(timezone.utc).isoformat(),
    },indent=2)+"\n")
    attempt.write_text(json.dumps({
        "site":site,"phase":"DONE_NO_JOBS",
        "at":datetime.now(timezone.utc).isoformat(),
    },indent=2)+"\n")
    print(site,"PRIVATE FATES AD RECOVERY PASS | ready 5-year AD smoke, NO JOBS",flush=True)

def self_test():
    proven_reference_check()
    assert OLD!=NEW and OLD_RESEED!=NEW_RESEED
    assert "use_fates" in NEW and "use_cn" in NEW_RESEED
    assert B.BGC_OPTS=="--bgc fates --no-megan --no-drydep --no-fire_emis"
    assert len(B.SITE_ORDER)==10
    print("BATCH01 PRIVATE FATES AD OVERLAY SELF-TEST PASS (no HPC filesystem writes)")
    print("Exact proven DE-Tha Stage12 guard and reseed changes reused.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","recover"))
    p.add_argument("--confirm",default="")
    args=p.parse_args()
    if args.action=="self-test":
        self_test()
        return
    if args.confirm!=ACK:
        fail("Recovery requires --confirm "+ACK)
    proven_reference_check()
    patch=create_patch()  # pin original CTSM BEFORE writing anything
    create_overlay(patch)   # one private overlay for all ten sites
    problems=[]
    for site in B.SITE_ORDER:
        try:
            repair_one(site)
        except Exception as exc:
            print(site,"RECOVERY HOLD:",str(exc)[-1500:],flush=True)
            problems.append(site)
    print("BATCH01 PRIVATE FATES AD RECOVERY",len(B.SITE_ORDER)-len(problems),
          "/",len(B.SITE_ORDER),"successful; NO Slurm jobs submitted",flush=True)
    if problems:
        print("HOLD:",",".join(problems),"Do NOT run submit-smoke")
        raise SystemExit(2)
    print("READY: run Stage11 submit-smoke to launch ONLY the first AD5.")

if __name__=="__main__":
    main()
