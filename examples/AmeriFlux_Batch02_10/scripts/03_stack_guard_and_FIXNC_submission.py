#!/usr/bin/env python3
"""AmeriFlux Batch02 STACK and once-only CIME submit gate.

Port of Batch01 Stage21 RLIMIT_STACK ≥65536 KiB. Raises LOW soft limit
to 300000 KiB when hard limit allows; never lowers high/unlimited soft
or modifies hard. Subprocess inherits soft RLIMIT_STACK. Verify Slurm
PropagateResourceLimits includes STACK before model submission.

--self-test  : code invariants, no files or jobs
--audit      : live CPU shell/Slurm config evidence, no files or jobs
--submit     : only a fully science-approved, independently built new
               Batch02 FIXNC CIME case with matching SHA receipt; writes
               attempt ledger BEFORE submitting; never duplicate submissions.
Supports AD5, AD395, NORMAL5, NORMAL395. Does not create model cases.
"""
import argparse,configparser,hashlib,json,os,re,resource,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=BASE/"experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10"
CASES=BASE/"cases"
SITES=("US-BZS","US-CMW","US-EML","US-GLE","US-Ha1","US-Ho1","US-Ho2","US-Ho3","US-ICh","US-ICt")
MIN_KB=65536
TARGET_KB=300000
PHASES=("AD5","AD395","NORMAL5","NORMAL395")
CONFIRM="SUBMIT_AMF_BATCH02_ONE_SCIENCE_APPROVED_FIXNC_CASE_WITH_STACK_GUARD"
REQUIRED=("site_PFT_surface_sha_verified",
          "all_ten_soil_layers_and_organic_policy_approved",
          "FATES_site_HLM_mapping_parameters_verified",
          "DATM_source_clock_ZBOT_UTC_and_CO2_approved",
          "point_PTS_lat_lon_effective_domain_verified",
          "CIME_case_setup_and_preview_pass",
          "ready_to_submit")

def fail(msg):raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def show(v):
    return "unlimited" if v==resource.RLIM_INFINITY else f"{v//1024} KiB"

def stack_guard(raise_low=True):
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    previous=(soft,hard)
    if soft!=resource.RLIM_INFINITY and soft<MIN_KB*1024:
        if not raise_low:
            fail("STACK SOFT "+show(soft)+" BELOW 65536 KiB; no model submission")
        target=TARGET_KB*1024 if hard==resource.RLIM_INFINITY or hard>=TARGET_KB*1024 else MIN_KB*1024
        if hard!=resource.RLIM_INFINITY and hard<target:
            fail("STACK HARD "+show(hard)+" BELOW 65536 KiB; switch to high-hard-limit login shell")
        try:
            resource.setrlimit(resource.RLIMIT_STACK,(target,hard))
        except (ValueError,OSError) as e:
            fail("STACK RAISE FAILED "+str(e)+"; set a high limit in the same shell before launching Python")
        soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    if soft!=resource.RLIM_INFINITY and soft<MIN_KB*1024:
        fail("STACK GUARD BLOCK: SOFT "+show(soft)+" < 65536 KiB")
    if hard!=previous[1]:
        fail("Stack hard limit changed unexpectedly")
    child=subprocess.run([sys.executable,"-c","import resource;print(resource.getrlimit(resource.RLIMIT_STACK)[0])"],
        capture_output=True,text=True,timeout=30,check=True)
    if int(child.stdout.strip())!=soft:
        fail("CIME child process stack limit is not inherited")
    proof={"before_soft":show(previous[0]),"after_soft":show(soft),
           "hard":show(hard),"raised_low_soft_only":previous[0]!=soft,
           "python_child_inherits":True}
    print("AMF_B02_STACK_GUARD_PASS",json.dumps(proof,sort_keys=True),flush=True)
    return proof

def slurm_config(required):
    try:
        p=subprocess.run(["scontrol","show","config"],capture_output=True,text=True,timeout=45,check=True)
    except (OSError,subprocess.SubprocessError) as e:
        if required:fail("Slurm stack propagation not verifiable: "+str(e))
        print("AMF_B02_SLURM_STACK_UNVERIFIED",str(e),flush=True)
        return None
    m=re.search(r"(?im)^\s*PropagateResourceLimits\s*=\s*(\S+)",p.stdout)
    cfg=m.group(1) if m else ""
    print("AMF_B02_SLURM_PROPAGATE",cfg or "MISSING",flush=True)
    if required and cfg.upper()!="ALL" and "STACK" not in cfg.upper().split(","):
        fail("Slurm PropagateResourceLimits does not prove STACK inherited: "+repr(cfg))
    return cfg

def case_gate(site,phase,case,receipt):
    if site not in SITES or phase not in PHASES:fail("Wrong cohort site or AD/Normal phase")
    if not case.is_dir() or case.resolve().parent!=CASES.resolve():
        fail("Expected new distinct CIME case in "+str(CASES))
    if not case.name.startswith(site+"_") or "FIXNC" not in case.name.upper() or "HISTMET" in case.name.upper():
        fail("Refuse unrelated/original/historical case "+str(case))
    if not receipt.is_file() or not receipt.resolve().is_relative_to(EXP.resolve()):
        fail("No science APPROVAL receipt from separate Batch02 FIXNC pipeline")
    proof=json.loads(receipt.read_text())
    if proof.get("site")!=site or proof.get("phase")!=phase or Path(proof.get("case","")).resolve()!=case.resolve():
        fail("Science receipt does not match case and phase")
    for k in REQUIRED:
        if proof.get(k) is not True:fail("SCIENCE HOLD "+site+" "+k)
    for item,key in (("CaseDocs/lnd_in","lnd_in_sha256"),
                     ("user_nl_datm_streams","user_nl_datm_streams_sha256"),
                     (".case.run","case_run_script_sha256")):
        p=case/item
        if not p.is_file() or sha(p)!=proof.get(key):
            fail("Case configuration changed after science approval: "+item)
    if not (case/"case.submit").is_file():fail("Missing CIME case.submit")
    # Batch01 Stage21 requires skip-preview-namelist to be persisted
    # in case submit options after the scientifically approved private
    # FATES AD buildnml configuration was previewed. Do NOT silently
    # regenerate different namelists during model submission.
    cp=configparser.RawConfigParser()
    if not cp.read(case/".submit_options"):
        fail("Missing CIME .submit_options, cannot prove prior approved buildnml")
    if not (cp.has_section("SubmitOptions") and
            cp.getboolean("SubmitOptions","skip_pnl",fallback=False)):
        fail("CIME skip_pnl was not persisted like Batch01 Stage21")
    cs=case/"CaseStatus"
    if cs.is_file() and re.search("case.submit starting|case.run starting|model execution starting",
                                  cs.read_text(errors="replace"),re.I):
        fail("Prior submission seen in CaseStatus; refuse duplicate")
    if phase in ("AD5","NORMAL5") and not (
        proof.get("STOP_OPTION")=="nyears" and proof.get("STOP_N")==5
        and proof.get("REST_N")==5 and proof.get("RESUBMIT")==0):
        fail("AD5/Normal5 smoke must be 5 years, RESUBMIT=0")
    if phase in ("AD395","NORMAL395") and not (
        proof.get("prior_5year_completed_and_restart_sha_verified") is True
        and proof.get("intended_years")==395 and proof.get("RESUBMIT")==78):
        fail("395y continuation requires real 5-year restart and 78 resubmits")
    return proof

def submit(site,phase,case,receipt):
    # Both stack and Slurm config guards happen before ANY case or ledger writes.
    st=stack_guard(True)
    propagated=slurm_config(True)
    case_gate(site,phase,case,receipt)
    ledger=EXP/"submission_ledger"/(site+"_"+phase+"_"+case.name+".json")
    ledger.parent.mkdir(parents=True,exist_ok=True)
    record={"site":site,"phase":phase,"case":str(case),
            "source_receipt":str(receipt),"source_receipt_sha256":sha(receipt),
            "stack":st,"PropagateResourceLimits":propagated,
            "status":"ATTEMPT_BEFORE_SUBMIT_DO_NOT_REPEAT",
            "attempt_at":datetime.now(timezone.utc).isoformat()}
    # Atomic exclusive creation: failed/uncertain jobs are never resubmitted blindly.
    with ledger.open("x") as out:json.dump(record,out,indent=2);out.write("\n")
    print("AMF_B02_SUBMIT_ATTEMPT_STAMP",ledger,flush=True)
    p=subprocess.run([str(case/"case.submit"),"--skip-preview-namelist"],cwd=case,
        capture_output=True,text=True,timeout=660)
    record.update(returncode=p.returncode,stdout=(p.stdout or "")[-7000:],
                  stderr=(p.stderr or "")[-2500:],
                  status="SUBMITTED_MODEL_UNVERIFIED" if p.returncode==0 else "FAILED_OR_UNCERTAIN_NO_BLIND_RETRY")
    ledger.write_text(json.dumps(record,indent=2)+"\n")
    if p.returncode:fail("CIME submission returned error, inspect ledger and Slurm before deciding any retry")
    print("AMF_B02_SUBMITTED",site,phase,"MODEL_NOT_YET_VERIFIED",flush=True)

def main():
    p=argparse.ArgumentParser()
    modes=p.add_mutually_exclusive_group(required=True)
    for x in ("self-test","audit","submit"):modes.add_argument("--"+x,action="store_true")
    p.add_argument("--site",choices=SITES)
    p.add_argument("--phase",choices=PHASES)
    p.add_argument("--case",type=Path)
    p.add_argument("--receipt",type=Path)
    p.add_argument("--confirm",default="")
    a=p.parse_args()
    if a.self_test:
        assert MIN_KB==65536 and TARGET_KB>=MIN_KB and len(SITES)==10
        assert len(PHASES)==4 and len(REQUIRED)==7
        print("AMF_B02_STACK_SELF_TEST_PASS | Stage21 64MiB minimum, four phases, no model jobs or file writes")
        return
    if a.audit:
        stack_guard(True)
        slurm_config(False)
        print("AMF_B02_STACK_AUDIT_PASS | stack raised only in current Python process; parent shell NOT changed; NO SLURM JOBS")
        return
    if not (a.site and a.phase and a.case and a.receipt and a.confirm==CONFIRM):
        fail("Real submission requires explicit --site --phase --case --receipt --confirm "+CONFIRM)
    submit(a.site,a.phase,a.case,a.receipt)

if __name__=="__main__":
    main()
