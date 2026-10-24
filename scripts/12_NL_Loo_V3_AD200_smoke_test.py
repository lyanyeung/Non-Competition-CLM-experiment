#!/usr/bin/env python3
"""Guarded NL-Loo AD200 smoke-test submission (2047 -> 2052 only).

Runs against an EXISTING partially staged CIME AD200 case. It never creates,
deletes, rebuilds or rewrites CTSM model cases / restarts. Before one permitted
case.submit it validates the isolated FATES-AD namelist patch, hybrid restart
files, case settings and controller ledger. Watchdog remains DISARMED, and
RESUBMIT=0 means exactly one five-model-year run + its archive.
"""
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


controller = load_script("09_NL_Loo_V3_auto550.py", "nl_loo_v3_controller")
overlay = load_script("11_NL_Loo_V3_AD200_fix_private_overlay.py", "nl_loo_v3_ad_overlay")

ACTION = "AD200_smoke_2047_2052"
CONFIRM = "SUBMIT_NL_LOO_AD200_ONLY_2047_TO_2052"
STAGE = "AD200"


def fail(msg):
    raise RuntimeError(msg)


def ready():
    """Only reads from case/config/slurm/checkpoints, except no file writes."""
    if not controller.STATE.is_file():
        fail("Controller ledger missing")
    d = controller.load()
    if d.get("armed") is not False or controller.STOP.exists():
        fail("Existing controller is armed or operator STOP exists")
    if d.get("actions", {}).get("PRE50_first") != "DONE":
        fail("PRE50 prior launch is not DONE")
    if d.get("actions", {}).get("AD200_first") != "ATTEMPTED":
        fail("Expected recoverable AD200_first=ATTEMPTED; do not duplicate")
    if ACTION in d.get("actions", {}):
        fail("AD200 smoke submit has already been ATTEMPTED/DONE; no retries")
    if d.get("actions", {}).get("AD200_remaining") is not None:
        fail("Continuation actions already exist")
    if controller.ARCH[STAGE].exists():
        fail("AD200 archive already exists; cannot submit smoke again")
    if controller.slurm(STAGE):
        fail("AD200 already has running/queued Slurm jobs")
    if controller.slurm("PRE50"):
        fail("PRE50 still has Slurm jobs")
    queue = controller.cmd(["squeue", "-u", controller.U, "-h", "-o", "%i|%j|%T"])
    if any("NL-Loo-V3-watch" in line for line in queue.splitlines()):
        fail("Watchdog still queued/running; inspect before smoke submission")

    existing, previous_patch, fixed_patch = overlay.inspect()
    if existing != fixed_patch:
        fail("Only corrected isolated FATES AD namelist patch is acceptable")
    overlay.verify_generated()
    controller.check(STAGE)

    # This check reads the archived PRE50 restart and checks normal spinup=0.
    if not controller.complete("PRE50", 2047):
        fail("PRE50 final 2047 archive checkpoint not fully verified")

    expected_settings = {
        "RUN_TYPE": "hybrid",
        "RUN_REFCASE": controller.NAME["PRE50"],
        "RUN_REFDATE": "2047-01-01",
        "RUN_STARTDATE": "2047-01-01",
        "GET_REFCASE": "FALSE",
        "CONTINUE_RUN": "FALSE",
        "RESUBMIT": "0",
        "CLM_ACCELERATED_SPINUP": "on",
        "STOP_OPTION": "nyears",
        "STOP_N": "5",
        "REST_OPTION": "nyears",
        "REST_N": "5",
        "DOUT_S": "TRUE",
    }
    for name, desired in expected_settings.items():
        actual = controller.xq(STAGE, name)
        if actual.lower() != desired.lower():
            fail(f"Unexpected {name}: {actual!r} != {desired!r}")

    log = (controller.CASE[STAGE] / "CaseStatus").read_text(errors="replace")
    if re.search(r"case\.submit starting|case\.run starting", log):
        fail("AD200 has previously been submitted; no duplicate")
    if (controller.CASE[STAGE] / "V3_first_submission_attempt.json").exists():
        fail("AD200 submit marker already exists")

    # Compare full archived restart bytes, not file sizes alone.
    source = controller.ARCH["PRE50"] / "rest" / "2047-01-01-00000"
    dest = controller.RUN[STAGE]
    if not dest.is_dir():
        fail("AD200 run directory missing")
    for component in ("clm2", "cpl", "datm"):
        name = f"{controller.NAME['PRE50']}.{component}.r.2047-01-01-00000.nc"
        a, b = source / name, dest / name
        if not (a.is_file() and b.is_file()):
            fail(f"2047 staged file missing: {name}")
        if a.stat().st_size != b.stat().st_size or controller.hashfile(a) != controller.hashfile(b):
            fail(f"2047 staged restart checksum mismatch: {name}")
    for ptr in ("rpointer.lnd", "rpointer.cpl", "rpointer.atm"):
        p = dest / ptr
        if not p.is_file():
            fail(f"Missing active pointer: {ptr}")
        pointed = p.read_text(errors="replace").strip().strip("'\"")
        if pointed.startswith("/") or ".." in Path(pointed).parts:
            fail(f"Unsafe pointer {ptr}: {pointed}")
        pointed_file = dest / pointed
        if not pointed_file.is_file():
            fail(f"Dangling pointer {ptr}: {pointed}")

    print("PASS: PRE50 normal restart 2047 and staged files SHA256-identical", flush=True)
    print("PASS: FATES AD spinup_state=2 in corrected private namelist", flush=True)
    print("PASS: hybrid AD200, STOP_N=5, RESUBMIT=0, no live jobs", flush=True)
    print("PASS: controller disarmed; this step will NOT start remaining 195 years", flush=True)
    return d


def submit_smoke():
    with controller.LOCK.open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ready()
        # Recheck user's scratch quota and pinned surface/CTSM/parameters
        # immediately before any irreversible submission.
        controller.validate_base()
        ready()

        d = controller.load()
        d.setdefault("actions", {})[ACTION] = "ATTEMPTED"
        d["armed"] = False
        d["ad_only"] = True
        d["hold_after_first_ad_segment"] = True
        controller.save(d)
        try:
            # This existing submit() writes its own marker BEFORE calling
            # case.submit. On uncertain failure both markers stay ATTEMPTED.
            controller.submit(STAGE, "first")
        except Exception as exc:
            d = controller.load()
            d["error"] = {"at": controller.utc(), "message": str(exc)}
            d["armed"] = False
            controller.save(d)
            raise

        d = controller.load()
        d["actions"][ACTION] = "DONE"
        d["actions"]["AD200_first"] = "DONE"
        d["armed"] = False
        d["ad_only"] = True
        d["hold_after_first_ad_segment"] = True
        d["smoke_submitted_at"] = controller.utc()
        d.pop("error", None)
        controller.save(d)
        print("\nAD200 SMOKE SUBMITTED: 2047 -> 2052 (five years ONLY)", flush=True)
        print("Controller remains DISARMED; no watcher/195-year continuation submitted", flush=True)
        print("After completion run: python3 scripts/12_NL_Loo_V3_AD200_smoke_test.py monitor", flush=True)


def monitor():
    d = controller.load()
    print("AD200 5Y SMOKE | READ ONLY", flush=True)
    print("controller armed:", d.get("armed"), flush=True)
    print("smoke ledger:", d.get("actions", {}).get(ACTION), flush=True)
    print("remaining-195-year ledger:", d.get("actions", {}).get("AD200_remaining"), flush=True)
    print("Slurm:", controller.slurm(STAGE), flush=True)
    f = controller.CASE[STAGE] / "CaseStatus"
    if f.is_file():
        print("CaseStatus (last 24 lines):\n" + "\n".join(f.read_text(errors="replace").splitlines()[-24:]), flush=True)
    folder = controller.ARCH[STAGE] / "rest" / "2052-01-01-00000"
    print("2052 archived restart directory exists:", folder.is_dir(), flush=True)
    if controller.slurm(STAGE):
        print("Model/archive still queued or running; final check deferred")
        return
    if not folder.is_dir():
        print("2052 final checkpoint not archived yet; inspect case/run logs")
        return
    try:
        verified = controller.complete(STAGE, 2052)
        if verified:
            print("PASS: AD200 first 5 years archived at 2052, spinup_state in (1,2)")
            print("HOLD: remaining 195 years NOT scheduled; scientific diagnostics required")
        else:
            print("2052 checkpoint not verified yet")
    except Exception as ex:
        print("2052 restart validation FAILED:", ex)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit", "submit-smoke", "monitor"))
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.action == "monitor":
        monitor()
    elif args.action == "audit":
        with controller.LOCK.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            ready()
        print("AUDIT ONLY; Slurm jobs NOT submitted")
    else:
        if args.confirm != CONFIRM:
            fail("Submit requires --confirm " + CONFIRM)
        submit_smoke()


if __name__ == "__main__":
    main()
