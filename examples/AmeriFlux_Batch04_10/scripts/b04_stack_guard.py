#!/usr/bin/env python3
"""Batch04 RLIMIT_STACK/Slurm propagation gate, sourced from AmeriFlux Batch01 Stage21.

MANDATORY: future submitters must IMPORT and call require_for_submission()
immediately before every CIME case.submit, in the SAME Python process,
for AD5, AD395, NORMAL5, NORMAL395, including retries/recovery.
Standalone --ensure changes only this Python process, never its parent
shell, so it cannot protect a later separate case.submit shell command.

Minimum soft stack 65536 KiB; prefer 300000 KiB when raising is permitted.
NEVER decrease a higher or unlimited soft stack. Verify scontrol Slurm
PropagateResourceLimits=STACK or ALL; otherwise fail closed.
No CIME submission implemented here.
"""
from __future__ import annotations
import argparse
import json
import re
import resource
import subprocess

MIN_KIB=65536
PREFERRED_KIB=300000
KIB=1024

def fmt(limit):
    return "unlimited" if limit==resource.RLIM_INFINITY else limit//KIB

def adequate(soft):
    return soft==resource.RLIM_INFINITY or soft>=MIN_KIB*KIB

def suggested_target(soft,hard):
    """Pure policy; returns None when hard limit blocks 64 MiB."""
    if adequate(soft):return soft
    if hard!=resource.RLIM_INFINITY and hard<MIN_KIB*KIB:
        return None
    goal=PREFERRED_KIB*KIB if hard==resource.RLIM_INFINITY else min(hard,PREFERRED_KIB*KIB)
    return goal if goal>soft else None

def inspect_or_raise(*,may_raise=False):
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    before_soft,before_hard=soft,hard
    if not adequate(soft) and may_raise:
        target=suggested_target(soft,hard)
        if target is None:
            raise RuntimeError("B04 STACK HARD LIMIT HOLD: soft="+str(fmt(soft))+
              "KiB hard="+str(fmt(hard))+"KiB; need at least 65536KiB")
        try:
            # Raise ONLY current Python process soft limit, no hard changes.
            resource.setrlimit(resource.RLIMIT_STACK,(target,hard))
        except (ValueError,OSError) as e:
            raise RuntimeError("B04 STACK RAISE FAILED "+str(e)) from e
        soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    if not adequate(soft):
        raise RuntimeError("B04 STACK GUARD HOLD soft="+str(fmt(soft))+
          "KiB < 65536KiB. In the SAME submitting shell try "+
          "ulimit -s unlimited or ulimit -s 300000 if permitted; "+
          "or use require_for_submission inside actual Python submitter.")
    if before_soft==resource.RLIM_INFINITY:
        assert soft==before_soft,"Never lower unlimited"
    elif soft!=resource.RLIM_INFINITY:
        assert soft>=before_soft,"Never lower a higher limit"
    assert hard==before_hard,"Never change hard limit"
    record={"soft_before_KiB":fmt(before_soft),
            "soft_at_submit_KiB":fmt(soft),"hard_KiB":fmt(hard),
            "minimum_KiB":MIN_KIB,"adequate":True,
            "changed_this_python_process_only":soft!=before_soft,
            "parent_shell_unchanged":True}
    print("B04 STACK GUARD PASS",json.dumps(record,sort_keys=True),flush=True)
    return record

def verify_slurm_propagation():
    try:
        p=subprocess.run(["scontrol","show","config"],text=True,
            capture_output=True,timeout=15,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise RuntimeError("B04 SLURM STACK PROPAGATION UNKNOWN; do NOT submit") from e
    if p.returncode:
        raise RuntimeError("B04 SLURM CONFIG HOLD "+p.stderr[-500:])
    m=re.search(r"(?mi)^\s*PropagateResourceLimits\s*=\s*(\S.*)$",p.stdout)
    if m is None:
        raise RuntimeError("B04 SLURM PropagateResourceLimits unavailable; do NOT submit")
    value=m.group(1).strip().split()[0]
    propagated={t.upper() for t in value.split(",")}
    if "ALL" not in propagated and "STACK" not in propagated:
        raise RuntimeError("B04 SLURM PROPAGATION HOLD "+value+
                           " must include STACK or ALL")
    result={"PropagateResourceLimits":value,"stack_propagated":True}
    print("B04 SLURM STACK PROPAGATION PASS",json.dumps(result),flush=True)
    return result

def require_for_submission(*,site,phase,may_raise=True):
    """Call in future actual submitter immediately before case.submit.

    Returned proof MUST be written to the attempt-before-submit ledger.
    This resource check never substitutes for scientific/case readiness.
    """
    if phase not in ("AD5","AD395","NORMAL5","NORMAL395"):
        raise RuntimeError("B04 invalid stage "+str(phase))
    if not re.fullmatch(r"US-[A-Za-z0-9]{3}",site):
        raise RuntimeError("B04 wrong site "+str(site))
    a=inspect_or_raise(may_raise=may_raise)
    a.update(site=site,phase=phase,slurm=verify_slurm_propagation())
    print("B04 FUTURE CASE.SUBMIT RESOURCE GATE PASS",site,phase)
    return a

def self_test():
    K=KIB;inf=resource.RLIM_INFINITY
    assert adequate(65536*K) and adequate(inf) and not adequate(8192*K)
    assert suggested_target(8192*K,inf)==300000*K
    assert suggested_target(8192*K,400000*K)==300000*K
    assert suggested_target(8192*K,180000*K)==180000*K
    assert suggested_target(8192*K,32768*K) is None
    assert suggested_target(450000*K,inf)==450000*K
    assert suggested_target(inf,inf)==inf
    assert suggested_target(65536*K,inf)==65536*K
    print("B04 STACK SYNTHETIC SELFTEST PASS low8192->300000; "+
          "hard-limit failclosed; high/unlimited retained; no model writes")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test",action="store_true")
    g.add_argument("--check",action="store_true")
    g.add_argument("--ensure",action="store_true")
    opt=ap.parse_args()
    if opt.self_test:
        self_test()
        return
    inspect_or_raise(may_raise=opt.ensure)
    verify_slurm_propagation()
    if opt.ensure:
        print("B04 NOTE: --ensure only changed CURRENT Python process; "+
              "must import guard inside subsequent actual submitter.")
    print("B04 NO CIME/SLURM SUBMISSION")

if __name__=="__main__":main()
