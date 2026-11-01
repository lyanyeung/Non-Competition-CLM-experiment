#!/usr/bin/env python3
"""Guarded Batch01 Stage45 Normal400 direct submit, for prepared CA-TP1/CA-TP3/US-Bar.

The original Lane A staging validator expects RESUBMIT=0; Stage45 has already
configured 79 for the 80x5 direct Normal400 run. Use a SHA-pinned, in-memory
copy of Lane A with ONLY that validator expectation changed. This is the same
one-line compatibility fix validated on IRIDIS6 for CA-TP1 (job 4799483).

The AD case, Stage23 forcing and original Lane A source are never edited.
'check' and 'self-test' submit nothing. 'submit' is a ONE-TIME action, requiring
an exact confirmation string and an extra acknowledgement for provisional
US-Bar meteorology. Never retry blindly after interrupted submission.
"""
from __future__ import annotations
import argparse
import hashlib
import types
from pathlib import Path

SITES = ("CA-TP1", "CA-TP3", "US-Bar")
CONFIRM = "SUBMIT_AMF_B01_STAGE45_NORMAL400_ONCE"
LANE_BLOB = "c461a85feef163830316c71410c1c3fd2c4d859e"
EXPECTED_BEFORE = b'"CLM_FORCE_COLDSTART":"off","RESUBMIT":"0","STOP_N":"5","REST_N":"5","DOUT_S":"TRUE"'
EXPECTED_AFTER = EXPECTED_BEFORE.replace(b'"RESUBMIT":"0"', b'"RESUBMIT":"79"')


def gitblob(src: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(src)).encode() + b"\0" + src).hexdigest()


def patched_lane_bytes(path: Path) -> bytes:
    src = path.read_bytes()
    if gitblob(src) != LANE_BLOB:
        raise ValueError("Lane A source is not the pinned, audited version")
    if src.count(EXPECTED_BEFORE) != 1:
        raise ValueError("Expected exactly one direct79 validator change")
    result = src.replace(EXPECTED_BEFORE, EXPECTED_AFTER)
    compile(result, str(path), "exec")
    return result


def load_patched_lane(path: Path):
    mod = types.ModuleType("lane55_direct79")
    mod.__file__ = str(path)
    exec(compile(patched_lane_bytes(path), str(path), "exec"), mod.__dict__)
    return mod


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "check", "submit"))
    p.add_argument("--tool-dir", type=Path)
    p.add_argument("--run", type=Path,
                   default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5"))
    p.add_argument("--sites", nargs="+", choices=SITES)
    p.add_argument("--confirm", default="")
    p.add_argument("--ack-provisional-usbar", action="store_true")
    args = p.parse_args()
    if not args.tool_dir:
        p.error("--tool-dir is required")
    tool = args.tool_dir.resolve(strict=True)
    lane_path = tool / "lane.py"
    patched_lane_bytes(lane_path)
    if args.action == "self-test":
        assert EXPECTED_AFTER != EXPECTED_BEFORE
        print("STAGE55 SELF-TEST PASS | pinned Lane A; only direct79 validator changed; NO MODEL/SLURM")
        return
    if not args.sites:
        p.error("--sites is required for check or submit")
    if len(set(args.sites)) != len(args.sites):
        raise ValueError("Duplicate site IDs")
    if args.action == "submit" and args.confirm != CONFIRM:
        p.error("Submit requires --confirm " + CONFIRM)
    if args.action == "submit" and "US-Bar" in args.sites and not args.ack_provisional_usbar:
        p.error("US-Bar has unresolved Met caveats; --ack-provisional-usbar required")

    stage45 = __import__("importlib.util", fromlist=["spec_from_file_location"])
    stage_path = tool / "normal.py"
    spec = stage45.spec_from_file_location("stage45_55", stage_path)
    stage = stage45.module_from_spec(spec)
    spec.loader.exec_module(stage)
    stage26 = stage.load(tool / "stage26.py", "stage26_55")
    direct = stage.load(tool / "direct.py", "direct36_55")
    helper = stage26.load_helper(tool / "helper.py")
    lane = load_patched_lane(lane_path)
    root, data = stage26.inputs(args.run)
    stage.configure(stage26, direct, helper, lane, root, data)

    verified = []
    for site in args.sites:
        ad = stage.audit(site, helper, lane, lane.pft_gate)
        expected_year = 2404 if site == "US-Bar" else 2402
        if ad["final"] != f"{expected_year:04d}-01-01-00000" or ad["spinup_state"] != 2:
            raise ValueError(site + ": AD400 terminal checkpoint differs from reviewed result")
        name = lane.n_name(site)
        if name != site + "_AMF_B01SIX_FIXNC_NORMAL400_DIRECT":
            raise ValueError(site + ": unexpected case identity")
        record = lane.load(lane.n_ledger(site))
        if record.get("phase") != "PREPARED_NOT_SUBMITTED":
            raise ValueError(site + ": not in unsubmitted prepared phase: " + str(record.get("phase")))
        if record.get("protocol") != "DIRECT_NORMAL400_80x5_RESUBMIT79_NOT_SUBMITTED":
            raise ValueError(site + ": Stage45 protocol does not match direct 80x5")
        if record.get("normal_start_year") != expected_year or record.get("normal400_target_year") != expected_year + 400:
            raise ValueError(site + ": Normal400 start/target differs")
        case = lane.n_case(site)
        if lane.queued(name) or lane.sacct_name(name):
            raise ValueError(site + ": Normal Slurm job already queued or accounted")
        if lane.latest(lane.n_arch(site))[1] != 0:
            raise ValueError(site + ": Normal archive already exists")
        lane.validate_normal(site)
        lane.pft_gate(site, case)
        if lane.xq(case, "RESUBMIT") != "79" or lane.xq(case, "CONTINUE_RUN").lower() != "false":
            raise ValueError(site + ": expected staged direct80x5 XML")
        print("STAGE55 PREFLIGHT PASS", site, "Normal400",
              expected_year, "to", expected_year + 400,
              "NO PREVIOUS JOBS", flush=True)
        verified.append(site)

    if args.action == "check":
        print("STAGE55 CHECK PASS", ",".join(verified), "NO MODEL OR SLURM CHANGES")
        return
    stack = lane.stack_guard()
    for site in verified:
        print("STAGE55 SUBMIT ONCE", site, flush=True)
        lane.submit_normal400_direct(site, stack)
    print("STAGE55 SUBMIT RETURNED", ",".join(verified),
          "| verify job IDs using squeue/sacct; NEVER blindly resubmit", flush=True)


if __name__ == "__main__":
    main()
