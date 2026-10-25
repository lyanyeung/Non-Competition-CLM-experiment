#!/usr/bin/env python3
"""Guarded FI-Hyy-only first AD5 retry, testing a 256 MiB primary stack.

Changes only the failed independent FI-Hyy case's MPI_RUN_COMMAND to execute a
small task-side wrapper. Cancels only its verified blocked old archive 4728103,
then submits one fresh cold-start AD5 with RESUBMIT=0 and skip-preview. Preserves
original IDs, logs and state. Never edits science inputs, meshes, code or binary.
Stack overflow is a hypothesis until task-limit output and model outcome agree.
"""
import argparse
import configparser
import gzip
import hashlib
import json
import os
import re
import resource
import shlex
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITE = "FI-Hyy"
NAME = "FI-Hyy_B02_FIXNC_AD400"
CASE = BASE / "cases" / NAME
RUN = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS") / NAME / "run"
ARCHIVE = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/archive") / NAME
SITE_ROOT = BASE / "experiments/NonCompetitionObserved22/Batch02_10/FI-Hyy"
STATE = SITE_ROOT / "AD5_case_state.json"
PILOT = SITE_ROOT / "AD5_stack256_pilot_v1"
RECEIPT = PILOT / "retry_state.json"
WRAPPER = PILOT / "task_stack256.sh"
EVIDENCE = Path.home() / "Batch02_10_ESMF_mesh_stack_amha70m2/mesh_stack_inspection.json"
ESMF = BASE / "ESMF_8_8_1_OMPI/src/Infrastructure/Mesh/src/ESMCI_ESMFMesh_Util.C"
ESMF_SHA = "3ddcafe537a9b006718b6db54a26a0debbed7c9736201832b0c581486fa0538c"
OLD_RUN, OLD_ARCHIVE = "4728102", "4728103"
MPI = "srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"
STACK_KIB = 262144
VERSION = "batch02-FI-Hyy-AD5-stack256-pilot-v1-20261025"


def fail(message):
    raise RuntimeError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, obj, exclusive=False):
    # Exclusive pilot directory/receipt is the retry guard; no automatic retries.
    with path.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def call(args, cwd=None, timeout=60):
    p = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        fail("Command failed: " + str(list(map(str, args))) + "\n" + (p.stdout + p.stderr)[-2200:])
    return p.stdout.strip()


def query(key):
    return call([CASE / "xmlquery", key, "--value"], cwd=CASE)


def scalar(text, key):
    matches = re.findall(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*([^\r\n!]*)", text)
    if len(matches) != 1:
        fail("Expected one namelist value: " + key)
    return matches[0].strip().rstrip(",").strip().strip("'\"")


def queue():
    rows = []
    for line in call(["squeue", "-u", "ly3n24", "-h", "-o", "%i|%j|%T|%R"]).splitlines():
        if line.strip():
            parts = [x.strip() for x in line.split("|")]
            if len(parts) != 4:
                fail("Cannot parse squeue")
            rows.append(parts)
    return rows


def old_jobs():
    text = call(["sacct", "-X", "-j", OLD_RUN + "," + OLD_ARCHIVE, "-n", "-P",
                 "--format=JobIDRaw,JobName%128,State,ExitCode"])
    rows = {}
    for line in text.splitlines():
        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 4:
            rows[parts[0]] = tuple(parts[1:4])
    if rows.get(OLD_RUN) != ("run." + NAME, "FAILED", "1:0"):
        fail("Original FI-Hyy run is not the known FAILED/1:0 job: " + repr(rows.get(OLD_RUN)))
    if rows.get(OLD_ARCHIVE) != ("st_archive." + NAME, "PENDING", "0:0"):
        fail("Original FI-Hyy archive is not the known blocked pending job: " + repr(rows.get(OLD_ARCHIVE)))
    matches = [r for r in queue() if r[1] in ("run." + NAME, "st_archive." + NAME)]
    if len(matches) != 1 or matches[0][:3] != [OLD_ARCHIVE, "st_archive." + NAME, "PENDING"] or "DependencyNeverSatisfied" not in matches[0][3]:
        fail("FI-Hyy queue differs from one blocked original archive: " + repr(matches))


def immutable_inputs(obj):
    files = {Path(obj["surface"]): obj["surface_sha256"], Path(obj["executable"]): obj["executable_sha256"]}
    for rel, key in (("lnd_in", "generated_lnd_in_sha256"), ("datm.streams.xml", "generated_stream_sha256")):
        files[CASE / "CaseDocs" / rel] = obj[key]
        files[RUN / rel] = obj[key]
    for name, sha in obj["user_DATM_files"].items():
        files[CASE / name] = sha
    # Record remaining user/generated inputs so the runtime-only retry cannot
    # accidentally change them. The binary/mesh files are never written.
    for folder in (CASE, CASE / "CaseDocs", RUN):
        for name in ("user_nl_clm", "datm_in", "nuopc.runconfig", ".env_mach_specific.sh", ".env_mach_specific.csh"):
            p = folder / name
            if p.is_file():
                files.setdefault(p, digest(p))
    for path, expected in files.items():
        if not path.is_file() or digest(path) != expected:
            fail("Prepared input changed: " + str(path))
    return {str(p): sha for p, sha in files.items()}


def verify_immutable(files):
    for p, sha in files.items():
        if digest(Path(p)) != sha:
            fail("Runtime-only pilot changed an input: " + p)


def audit():
    if PILOT.exists() or PILOT.is_symlink():
        fail("Stack pilot already attempted; use status, do not rerun retry: " + str(PILOT))
    if CASE.is_symlink() or not CASE.is_dir() or STATE.is_symlink():
        fail("Expected independent case/state absent or unsafe")
    obj = json.loads(STATE.read_text())
    expected = {"site": SITE, "case": str(CASE), "run": str(RUN), "archive": str(ARCHIVE),
                "phase": "FIRST_5Y_SUBMITTED", "first_run_job": OLD_RUN, "first_archive_job": OLD_ARCHIVE,
                "start_date": "1997-01-01", "spinup_state": 2, "RESUBMIT": 0,
                "skip_preview_persisted": True, "CIME_env_case_lock_restored": True}
    for key, value in expected.items():
        if obj.get(key) != value:
            fail("Original state differs: " + key)
    for key, value in {"CASE": NAME, "RUN_TYPE": "startup", "RUN_STARTDATE": "1997-01-01", "CONTINUE_RUN": "FALSE",
                       "CLM_FORCE_COLDSTART": "on", "CLM_ACCELERATED_SPINUP": "on", "STOP_OPTION": "nyears",
                       "STOP_N": "5", "REST_OPTION": "nyears", "REST_N": "5", "RESUBMIT": "0",
                       "RUNDIR": str(RUN), "DOUT_S_ROOT": str(ARCHIVE), "MPI_RUN_COMMAND": MPI,
                       "TOTALPES": "1", "NTHRDS_LND": "1", "BUILD_COMPLETE": "TRUE"}.items():
        if query(key).lower() != value.lower():
            fail("FI-Hyy cold-start setting changed: " + key)
    if Path(query("EXEROOT")).resolve() != Path(obj["executable"]).parent.resolve():
        fail("EXEROOT differs from pinned executable")
    if ARCHIVE.is_symlink():
        fail("Unexpected archive symlink")
    if next(ARCHIVE.rglob("*.nc"), None) is not None or any(RUN.glob("*.r.*.nc")) or any(RUN.glob(NAME + ".clm2.h*.nc")):
        fail("Archive/restart/history outputs exist; do not cold-start over progressed output")
    if (CASE / "env_case.xml").read_bytes() != (CASE / "LockedFiles/env_case.xml").read_bytes():
        fail("CIME env_case lock differs")
    land = (RUN / "lnd_in").read_text()
    for key, value in {"spinup_state": "2", "use_fates": ".true.", "use_fates_sp": ".false.",
                       "use_fates_fixed_biogeog": ".true.", "use_fates_nocomp": ".true.", "finidat": ""}.items():
        if scalar(land, key) != value:
            fail("Generated AD/FATES setting changed: " + key)
    cp = configparser.RawConfigParser()
    cp.read(CASE / ".submit_options")
    if not cp.getboolean("SubmitOptions", "skip_pnl", fallback=False):
        fail("Missing existing persistent skip-preview setting")
    if digest(ESMF) != ESMF_SHA:
        fail("Local ESMF source differs from Stage07 evidence")
    evidence = json.loads(EVIDENCE.read_text())
    if evidence.get("local_ESMF_source", {}).get("sha256") != ESMF_SHA:
        fail("Stage07 report local ESMF provenance differs")
    dust = [m for m in evidence["meshes"] if Path(m["path"]).name == "dust_0.25x0.25_ESMFmesh_cdf5_c240222.nc"]
    if len(dust) != 1 or dust[0].get("dimensions", {}).get("elementCount") != 1036800 or dust[0]["dimensions"].get("coordDim") != 2:
        fail("Expected Stage07 mesh-size evidence missing")
    if not Path(dust[0]["path"]).is_file():
        fail("Declared dust mesh is absent")
    original_log = sorted(RUN.glob("cesm.log." + OLD_RUN + ".*"))
    if not original_log:
        fail("Original failing model log missing")
    p = original_log[-1]
    with (gzip.open(p, "rt", errors="replace") if p.suffix == ".gz" else p.open(errors="replace")) as f:
        log = f.read(2 * 1024 * 1024)
    if "get_centerCoords_from_ESMFMesh_file" not in log or "Segmentation fault" not in log:
        fail("Original FI-Hyy log does not match the diagnosed ESMF mesh SIGSEGV")
    files = immutable_inputs(obj)
    old_jobs()
    print("STAGE08 AUDIT PASS: exact failed FI-Hyy run, blocked old archive, unchanged AD5 inputs; no restart/history outputs")
    print("PILOT: task-side stack -> 262144 KiB (256 MiB), same executable and cold-start years1997->2002, RESUBMIT=0")
    return obj, files


def wrapper_text(executable):
    return ("#!/usr/bin/env bash\nset -euo pipefail\n"
            "if [[ $# -lt 1 || \"$1\" != " + shlex.quote(executable) + " ]]; then\n"
            "  echo '[B02_STACK_PILOT] unexpected executable arguments' >&2\n  exit 64\nfi\n"
            "echo \"[B02_STACK_PILOT] host=$(hostname) before_kib=$(ulimit -S -s) hard_kib=$(ulimit -H -s)\"\n"
            "ulimit -S -s " + str(STACK_KIB) + "\n"
            "echo \"[B02_STACK_PILOT] after_kib=$(ulimit -S -s) OMP_STACKSIZE=${OMP_STACKSIZE:-unset} exec=$1\"\n"
            "[[ \"$(ulimit -S -s)\" == " + str(STACK_KIB) + " ]]\nexec \"$@\"\n")


def parse_ids(text):
    run = re.findall(r"Submitted job case\.run with id (\d+)", text)
    archive = re.findall(r"Submitted job case\.st_archive with id (\d+)", text)
    if len(run) != 1 or len(archive) != 1 or run[0] == archive[0] or run[0] in (OLD_RUN, OLD_ARCHIVE) or archive[0] in (OLD_RUN, OLD_ARCHIVE):
        fail("New run/archive IDs ambiguous; do not repeat retry")
    return run[0], archive[0]


def retry():
    obj, files = audit()
    PILOT.mkdir(exist_ok=False)
    backup = PILOT / "before"
    backup.mkdir()
    record = {"version": VERSION, "phase": "ATTEMPTED_UNCERTAIN", "created_utc": utc(),
              "original_run_job": OLD_RUN, "original_archive_job": OLD_ARCHIVE,
              "old_MPI_RUN_COMMAND": MPI, "target_stack_KiB": STACK_KIB, "immutable_input_sha256": files}
    save(RECEIPT, record, exclusive=True)
    # Preserve overwritten case output names and the original submission ledger.
    backups = [STATE, CASE / "env_run.xml", CASE / "CaseStatus", CASE / ".submit_options", CASE / ".case.run",
               CASE / ("run." + NAME + ".out"), CASE / ("run." + NAME + ".err")]
    for p in backups:
        if p.is_file():
            target = backup / p.name
            shutil.copy2(p, target)
            if digest(target) != digest(p):
                fail("Backup mismatch: " + str(p))
    WRAPPER.write_text(wrapper_text(obj["executable"]), encoding="utf-8")
    WRAPPER.chmod(0o700)
    call(["bash", "-n", WRAPPER])
    new_mpi = MPI + " " + shlex.quote(str(WRAPPER))
    call([CASE / "xmlchange", "MPI_RUN_COMMAND=" + new_mpi], cwd=CASE)
    if query("MPI_RUN_COMMAND") != new_mpi:
        fail("Task-side wrapper command did not become effective")
    verify_immutable(files)
    # Recheck exact old archive identity/status immediately before cancellation.
    old_jobs()
    call(["scancel", OLD_ARCHIVE])
    record.update(old_archive_cancel_requested=True, new_MPI_RUN_COMMAND=new_mpi)
    save(RECEIPT, record)
    # Allow a short scheduler cancellation delay, never another active pilot.
    matches = []
    for attempt in range(8):
        matches = [r for r in queue() if r[1] in ("run." + NAME, "st_archive." + NAME)]
        if not matches:
            break
        if any(r[0] != OLD_ARCHIVE for r in matches):
            fail("Unexpected active FI-Hyy job after cancellation: " + repr(matches))
        if attempt < 7:
            time.sleep(1)
    if matches:
        fail("FI-Hyy jobs remain after old-archive cancellation; inspect, do not retry: " + repr(matches))
    verify_immutable(files)
    print("CANCELLED VERIFIED BLOCKED OLD ARCHIVE", OLD_ARCHIVE, "| SUBMIT ONE FI-Hyy AD5 STACK PILOT", flush=True)
    try:
        result = subprocess.run([str(CASE / "case.submit"), "--skip-preview-namelist"], cwd=CASE,
                                capture_output=True, text=True, timeout=360)
    except Exception as exc:
        output = getattr(exc, "stdout", "") or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        (PILOT / "case_submit_output.txt").write_text(output + "\n" + str(exc))
        raise
    output = result.stdout + "\n" + result.stderr
    (PILOT / "case_submit_output.txt").write_text(output, encoding="utf-8")
    record["submission_exit_code"] = result.returncode
    try:
        runid, archiveid = parse_ids(output)
    except Exception:
        save(RECEIPT, record)
        raise
    record.update(run_job=runid, archive_job=archiveid, submitted_utc=utc())
    save(RECEIPT, record)
    cp = configparser.RawConfigParser()
    cp.read(CASE / ".submit_options")
    skip = cp.getboolean("SubmitOptions", "skip_pnl", fallback=False)
    record.update(phase="SUBMITTED" if result.returncode == 0 and skip else "SUBMITTED_REVIEW", skip_preview_persisted=skip)
    save(RECEIPT, record)
    # Original first-job IDs stay untouched. This nested receipt tracks the pilot.
    obj["stack256_pilot"] = {"receipt": str(RECEIPT), "run_job": runid, "archive_job": archiveid, "phase": record["phase"]}
    save(STATE, obj)
    if record["phase"] != "SUBMITTED":
        fail("New jobs have IDs but CIME return/options require review; do not repeat retry")
    print("FI-Hyy STACK256_AD5_SUBMITTED RUN=" + runid + " ARCHIVE=" + archiveid + " YEARS=5 RESUBMIT=0")
    print("STATUS: python3 -B", Path(__file__).resolve(), "status")
    print("Only FI-Hyy retried. Other three cases/archives unchanged; no AD395 or Normal submission.")


def status():
    obj = json.loads(RECEIPT.read_text())
    ids = [obj.get("run_job"), obj.get("archive_job")]
    print("PILOT_PHASE=" + obj["phase"])
    print("RECEIPT=" + str(RECEIPT))
    if all(ids):
        print(call(["sacct", "-X", "-j", ",".join(ids), "-n", "-P", "--format=JobIDRaw,JobName%128,State,ExitCode,Elapsed"]))
        print("ACTIVE", [r for r in queue() if r[0] in ids])
        for p in sorted(RUN.glob("cesm.log." + ids[0] + ".*")):
            with (gzip.open(p, "rt", errors="replace") if p.suffix == ".gz" else p.open(errors="replace")) as f:
                lines = f.readlines()
            print("LOG", p)
            print("\n".join(line.rstrip() for line in lines if "[B02_STACK_PILOT]" in line))
            print("\n".join(line.rstrip() for line in lines[-12:]))
        checkpoint = "2002-01-01-00000"
        folder = ARCHIVE / "rest" / checkpoint
        print("AD5_ARCHIVE_TRIPLET_PRESENT", all((folder / (NAME + "." + c + ".r." + checkpoint + ".nc")).is_file() for c in ("clm2", "datm", "cpl")))
    else:
        print("Submission incomplete/uncertain. Inspect saved output and queue; no automatic retry.")


def self_test():
    assert parse_ids("Submitted job case.run with id 999001\nSubmitted job case.st_archive with id 999002") == ("999001", "999002")
    assert STACK_KIB * 1024 == 256 * 1024 * 1024
    script = wrapper_text("/test/cesm.exe")
    assert "ulimit -S -s 262144" in script and 'exec "$@"' in script
    assert SITE == "FI-Hyy"
    print("STAGE08 SELF-TEST PASS: FI-Hyy-only retry, task-side 256MiB stack wrapper, distinct new job IDs; no model writes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("self-test", "audit", "retry", "status"))
    args = parser.parse_args()
    if args.action == "self-test":
        self_test()
    elif args.action == "audit":
        audit()
    elif args.action == "status":
        status()
    else:
        retry()
