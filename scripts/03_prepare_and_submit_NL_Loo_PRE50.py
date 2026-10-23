#!/usr/bin/env python3
"""Guarded NL-Loo FIXNC 50-year case creator and FIRST five-year Slurm submitter.

Use prepare for fresh clones, recover for the existing incomplete clone. Submit ONLY
after reviewing the results. Never changes the old NL-Loo case or old surface.
Does not schedule AD or post-AD and cannot complete 550 years automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

USER = "ly3n24"
ROOT = Path(f"/iridisfs/scratch/{USER}/CLM_FATES")
OLD_CASE = ROOT / "cases/NL-Loo_FATES_SPINUP500"
CASE_NAME = "NL-Loo_OBSPFT_NC_PRE50"
CASE = ROOT / "cases" / CASE_NAME
OUT_ROOT = Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS")
RUN = OUT_ROOT / CASE_NAME / "run"
ARCHIVE = OUT_ROOT / "archive" / CASE_NAME
CIME = ROOT / "CTSM/cime/scripts"
SURFACE = (ROOT / "experiments/NonCompetitionObserved22/NL-Loo/surface"
           / "surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc")
SURFACE_RECEIPT = SURFACE.with_suffix(".json")
SURFACE_HASH = "81ca2872a9758325c0a18121ad060496ce47745a590264353b3cbcfcdcc95920"
OLD_HASH = "b2d717b88638f90bd536233564e03b90196813b0f4d0343686db2349b45e5e31"
PARAM_HASH = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
EXPECTED_COMPSET = "2000_DATM%1PT_CLM60%FATES_SICE_SOCN_SROF_SGLC_SWAV_SESP"
ORIGINAL_SURFACE = (ROOT / "sites/MY_EC_SITE/NL-Loo/subset_data"
                    / "surfdata_NL-Loo_hist_2000_16pfts_c261011.nc")
MANIFEST = CASE / "observed_PFT_PRE50_manifest.json"
CONFIG = {
    "RUN_TYPE": "startup", "CONTINUE_RUN": "FALSE",
    "RUN_STARTDATE": "1997-01-01",
    "CALENDAR": "NO_LEAP", "ATM_NCPL": "48",
    "CLM_CO2_TYPE": "constant", "CCSM_CO2_PPMV": "363.04",
    "CLM_ACCELERATED_SPINUP": "off",
    "STOP_OPTION": "nyears", "STOP_N": "5",
    "REST_OPTION": "nyears", "REST_N": "5", "RESUBMIT": "0",
    "RUNDIR": str(RUN), "DOUT_S": "TRUE", "DOUT_S_ROOT": str(ARCHIVE)
}
NML = {
    "use_fates": ".true.",
    "use_fates_sp": ".false.",
    "use_fates_fixed_biogeog": ".true.",
    "use_fates_nocomp": ".true.",
    "fsurdat": "'" + str(SURFACE) + "'",
}
SUBMISSION_CONFIRM = "SUBMIT_NL_LOO_FIXNC_FIRST_5_YEARS"


def stop(msg):
    raise SystemExit("STOP: " + msg)


def run(args, cwd=None):
    print("+", " ".join(map(str, args)), flush=True)
    proc = subprocess.run(list(map(str, args)), cwd=cwd, check=False)
    if proc.returncode:
        stop(f"Command failed ({proc.returncode}); inspect case. "
             "Never auto-delete or overwrite a partial case.")


def capture(args, cwd=None):
    proc = subprocess.run(list(map(str, args)), cwd=cwd,
                          capture_output=True, text=True, check=False)
    if proc.returncode:
        stop(f"Failed {args}: {proc.stderr[-600:]}")
    return proc.stdout.strip()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for part in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def query(case, key):
    return capture(["./xmlquery", key, "--value"], case)


def check_source():
    if not OLD_CASE.is_dir() or not (OLD_CASE / "xmlquery").exists():
        stop("Original case missing; do not substitute a different source")
    if query(OLD_CASE, "COMPSET") != EXPECTED_COMPSET:
        stop("Baseline compset changed")
    if query(OLD_CASE, "CLM_CO2_TYPE").lower() != "constant":
        stop("Original CO2 policy changed")
    if abs(float(query(OLD_CASE, "CCSM_CO2_PPMV")) - 363.04) > 0.00001:
        stop("Original fixed CO2 changed")
    if query(OLD_CASE, "RUN_STARTDATE") != "1997-01-01":
        stop("Original start date changed")
    if query(OLD_CASE, "BUILD_COMPLETE").upper() != "TRUE":
        stop("Original compiled executable not marked BUILT")
    exe = Path(query(OLD_CASE, "EXEROOT")) / "cesm.exe"
    if not exe.is_file():
        stop(f"Original executable missing: {exe}")
    original_datm = OLD_CASE / "user_nl_datm_streams"
    if not original_datm.is_file():
        stop("Original DATM stream config missing")
    text = original_datm.read_text(errors="replace")
    for y in range(1997, 2026):
        # Match existing annual input by explicit filename, not a vague site substring
        matches = sorted({Path(x) for x in re.findall(
            rf"/[A-Za-z0-9_./-]*/NL-Loo_DATM_{y}\.nc", text)})
        if len(matches) != 1 or not matches[0].is_file():
            stop(f"Missing or ambiguous NL-Loo DATM {y}: {matches}")
    if not ORIGINAL_SURFACE.is_file() or sha(ORIGINAL_SURFACE) != OLD_HASH:
        stop("Original surface has changed")
    if not SURFACE.is_file() or sha(SURFACE) != SURFACE_HASH:
        stop("Approved candidate surface missing or SHA256 mismatch")
    if not SURFACE_RECEIPT.is_file():
        stop("Missing new surface science/assumption receipt")
    receipt = json.loads(SURFACE_RECEIPT.read_text())
    if (receipt.get("generated_sha256") != SURFACE_HASH
            or receipt.get("scenario") != "grass_proxy"
            or receipt.get("landunit_grid_pct") != {"PCT_NATVEG": 100.0, "PCT_CROP": 0.0}):
        stop("Surface receipt / scenario mismatch")
    if not PARAM.is_file() or sha(PARAM) != PARAM_HASH:
        stop("FATES parameter JSON has changed")
    # Assert exact underlying area allocation once more.
    try:
        from netCDF4 import Dataset
        import numpy as np
    except ImportError:
        stop("netCDF4 and numpy required in clm_fates_env")
    with Dataset(SURFACE) as ds:
        v = ds.variables["PCT_NAT_PFT"]
        if v.shape[0] != 15 or v.size != 15:
            stop("Unexpected surface natural PFT dimension")
        x = np.ma.filled(v[:], np.nan).reshape(-1)
        expect = np.zeros(15)
        expect[[1, 7, 13]] = [93.6, 2.9, 3.5]
        if not np.allclose(x, expect, atol=0.002) or not np.isclose(np.sum(x), 100):
            stop("Surface does not contain the pinned proxy mixture")
        if not np.isclose(float(ds.variables["PCT_NATVEG"][:].reshape(-1)[0]), 100):
            stop("Not 100% natural vegetation")
        if not np.isclose(float(ds.variables["PCT_CROP"][:].reshape(-1)[0]), 0):
            stop("Unexpected CROP")
    return str(exe)


def rewrite_user_nl(path):
    if not path.is_file():
        stop("Clone lacks user_nl_clm")
    current = path.read_text()
    remove = re.compile(
        r"^\s*(?:" + "|".join(map(re.escape, NML.keys()))
        + r")\s*=.*(?:\n|$)", re.IGNORECASE | re.MULTILINE)
    modified = remove.sub("", current)
    lines = [f"{k} = {v}" for k, v in NML.items()]
    modified = modified.rstrip() + "\n\n! Observed NL-Loo FIXNC pilot - 500m grass proxy\n"
    modified += "\n".join(lines) + "\n"
    path.write_text(modified)


def verify_clone(exe, require_batch=True):
    if not CASE.is_dir() or not (CASE / "xmlquery").is_file():
        stop("Clone missing")
    if query(CASE, "CASE") != CASE_NAME:
        stop("Clone name mismatch")
    for key, expected in CONFIG.items():
        got = query(CASE, key)
        if key == "CCSM_CO2_PPMV":
            if abs(float(got) - float(expected)) < 0.00001:
                continue
        elif got.strip().lower() == expected.strip().lower():
            continue
        stop(f"XML {key}: expected {expected!r}; got {got!r}")
    if query(CASE, "COMPSET") != EXPECTED_COMPSET:
        stop("Cloned compset differs")
    if str(Path(query(CASE, "EXEROOT")) / "cesm.exe") != exe:
        stop("Executable is not original compiled FATES version")
    text = (CASE / "CaseDocs/lnd_in").read_text(errors="replace")
    for key, value in NML.items():
        pattern = rf"(?mi)^\s*{re.escape(key)}\s*=\s*{re.escape(value)}\s*(?:[!,]|$)"
        if not re.search(pattern, text):
            stop(f"Generated lnd_in missing expected {key} = {value}")
    if re.search(r"(?mi)^\s*spinup_state\s*=\s*[12]\s*(?:[!,]|$)", text):
        stop("PRE50 is supposed to run normal decomposition")
    if "fates_params_default.json" not in text:
        stop("Actual FATES parameter file changed or hidden")
    if "NL-Loo_DATM_1997.nc" not in (CASE / "user_nl_datm_streams").read_text():
        stop("Cloned DATM stream incorrect")
    job = CASE / ".case.run"
    if not job.is_file():
        if require_batch:
            stop("Missing .case.run: CIME setup is incomplete. Use the guarded recover command.")
    else:
        batch = job.read_text(errors="replace")
        if re.search(r"(?mi)^\s*#SBATCH.*--exclusive", batch):
            stop("Exclusive Slurm allocation forbidden")
        if re.search(r"(?mi)^\s*#SBATCH.*--nodes(?:=|\s+)([2-9]|\d{2,})", batch):
            stop("Multi-node Slurm job forbidden")
        for field in (r"--ntasks(?:-per-node)?", r"--cpus-per-task"):
            m = re.search(r"(?mi)^\s*#SBATCH.*"+field+r"(?:=|\s+)(\d+)", batch)
            if m and int(m.group(1)) != 1:
                stop(f"Unexpected batch CPU layout: {m.group(0)}")
    print("VERIFIED: isolated FIXNC clone, generated namelist, preserved forcing and CO2")
    print("NOTE: CIME configuration does not prove model's actual PFT patch areas.")



def save_prepared_manifest(exe):
    if MANIFEST.exists():
        stop("Manifest exists; never overwrite an existing preparation record")
    manifest = {
        "case": str(CASE), "stage": "PRE50", "site": "NL-Loo",
        "first_submission_years": 5, "target_years": 50,
        "later_stage_targets": {"AD": 200, "POSTAD": 300},
        "surface": str(SURFACE), "surface_sha256": SURFACE_HASH,
        "fates_paramfile_sha256": PARAM_HASH,
        "source_case": str(OLD_CASE), "source_executable": exe,
        "comp_set": EXPECTED_COMPSET, "new_mode": NML,
        "runtime_xml": CONFIG, "no_competition": True,
        "assumption": "3.5% open/heath/grass assigned to cool C3 grass proxy",
        "submission_authorized": False,
        "status": "PREPARED_FOR_MANUAL_REVIEW_FIRST_FIVE_YEARS",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


def ensure_batch_scripts_for_new_case():
    """CIME setup may be incomplete after create_clone; do not touch old cases."""
    batch = CASE / ".case.run"
    archive_script = CASE / "case.st_archive"
    if batch.is_file() and archive_script.is_file():
        return
    history = (CASE / "CaseStatus").read_text(errors="replace") if (CASE / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit\s+(?:starting|success)|case\.run\s+starting|model execution starting", history, re.I):
        stop("Case was submitted; do not reset batch setup")
    if re.search(r"case\.setup success", history):
        print("Missing batch script after recorded setup; regenerating NEW case setup (--reset).")
        run(["./case.setup", "--reset"], CASE)
    else:
        print("Case setup not recorded; calling NEW case ./case.setup.")
        run(["./case.setup"], CASE)
    if not batch.is_file() or not archive_script.is_file():
        stop("CIME case.setup returned but .case.run / case.st_archive is still absent. "
             "Inspect CaseStatus and setup logs; do not submit.")


def recover_incomplete_setup():
    """Only recover the single known unsubmitted NL-Loo clone after prior setup stop."""
    exe = check_source()
    if not CASE.is_dir():
        stop("NEW case does not exist; recover is only for the already-cloned case")
    if MANIFEST.exists():
        stop("Manifest exists; recover is not an overwrite/resubmit operation")
    # No changes to the source case, old run, old archive, or to any NetCDF.
    verify_clone(exe, require_batch=False)
    status_path = CASE / "CaseStatus"
    if not status_path.is_file():
        stop("New case CaseStatus is missing; provenance ambiguous")
    status = status_path.read_text(errors="replace")
    if re.search(r"case\.submit\s+(?:starting|success)|case\.run\s+starting|model execution starting", status, re.I):
        stop("Prior run/submission history detected; refuse recovery")
    for p in (RUN, ARCHIVE):
        if p.exists() and not p.is_dir():
            stop(f"Output path is not directory: {p}")
        if p.exists():
            names = ("*.nc", "rpointer.*", "*.log.*", "cesm.log*", "*.r.*")
            if any(next(p.rglob(pattern), None) is not None for pattern in names):
                stop(f"Model files found in output path: {p}")
    try:
        queue = capture(["squeue", "-u", USER, "-h", "-o", "%j %i %T"])
    except SystemExit:
        stop("Unable to confirm Slurm queue; do not modify case setup")
    if CASE_NAME in queue:
        stop("Queue already has a matching job")
    ensure_batch_scripts_for_new_case()
    run(["./preview_namelists"], CASE)
    verify_clone(exe)
    save_prepared_manifest(exe)
    print("RECOVERED NEW CASE SAFELY:", CASE)
    print("No jobs have been submitted; inspect PRE50 namelist and .case.run.")
    print("Then explicitly invoke submit only after review.")

def prepare():
    exe = check_source()
    if CASE.exists() or RUN.exists() or ARCHIVE.exists():
        stop("Target case, RUNDIR, or DOUT_S_ROOT exists. "
             "Do not overwrite or blindly retry a partial case.")
    if not (CIME / "create_clone").is_file():
        stop("CIME create_clone not found")
    print("PREPARING NEW CASE: nothing in original case will be modified")
    run([CIME / "create_clone", "--case", CASE, "--clone", OLD_CASE, "--keepexe"], CIME)
    rewrite_user_nl(CASE / "user_nl_clm")
    # Change runtime XML only, not build-time configuration.
    for key, value in CONFIG.items():
        run(["./xmlchange", f"{key}={value}"], CASE)
    # Required for 1-rank original MPI build; retain existing 1-core batch layout.
    run(["./xmlchange",
         "MPI_RUN_COMMAND=srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"], CASE)
    ensure_batch_scripts_for_new_case()
    run(["./preview_namelists"], CASE)
    verify_clone(exe)
    save_prepared_manifest(exe)
    print("CASE PREPARED:", CASE)
    print("FIRST 5-YEAR SUBMISSION IS NOT AUTOMATIC.")
    print("Inspect .case.run, CaseDocs/lnd_in, quota and scientific mapping.")
    print("Then run: python scripts/03_prepare_and_submit_NL_Loo_PRE50.py submit"
          " --confirm " + SUBMISSION_CONFIRM)


def submit(confirm):
    if confirm != SUBMISSION_CONFIRM:
        stop("Explicit correct --confirm token required")
    exe = check_source()
    if not MANIFEST.is_file():
        stop("Prepared and reviewed manifest absent")
    info = json.loads(MANIFEST.read_text())
    if info.get("status") != "PREPARED_FOR_MANUAL_REVIEW_FIRST_FIVE_YEARS":
        stop("Case not in unsubmitted state")
    verify_clone(exe)
    status = (CASE / "CaseStatus").read_text(errors="replace")
    if re.search(r"case\.submit (?:starting|success)|case\.run starting|model execution starting", status):
        stop("Case has already been submitted; never double-submit")
    try:
        q = subprocess.run(["squeue", "-u", USER, "-h", "-o", "%j %i %T"],
                           capture_output=True, text=True, timeout=20, check=True).stdout
    except Exception as exc:
        stop("Cannot validate Slurm queue: " + str(exc))
    if CASE_NAME in q:
        stop("Matching jobs in queue; do not submit again")
    if shutil.which("myfiles") is not None:
        raw = capture(["myfiles"])
        match = re.search(r"Scratch number of files used:\s*([\d,]+)/([\d,]+)", raw)
        if match:
            used, limit = (int(v.replace(",", "")) for v in match.groups())
            if used >= 0.90 * limit:
                stop(f"Scratch inode usage too high ({used}/{limit})")
        else:
            print("WARNING: cannot parse myfiles inode display; check it manually")
    print("SUBMITTING EXACTLY ONE FIRST 5-YEAR JOB. No AD/POST jobs submitted.")
    run(["./case.submit"], CASE)
    # Persist a local receipt; if write fails CaseStatus remains authoritative.
    info["status"] = "FIRST_5_YEAR_SUBMISSION_REQUESTED"
    info["submission_authorized"] = True
    MANIFEST.write_text(json.dumps(info, indent=2) + "\n")
    print("SUBMIT REQUEST FINISHED. This is not evidence of a completed segment.")
    print("squeue -u", USER)
    print("tail -25", CASE / "CaseStatus")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("inspect")
    sub.add_parser("prepare")
    sub.add_parser("recover")
    s = sub.add_parser("submit")
    s.add_argument("--confirm", required=True)
    args = ap.parse_args()
    if args.action == "inspect":
        exe = check_source()
        print("PREPARE_INPUTS_PASS", exe)
        print("New case exists?", CASE.exists())
        print("New run dir exists?", RUN.exists())
        print("New archive exists?", ARCHIVE.exists())
        if MANIFEST.is_file(): print(MANIFEST.read_text())
    elif args.action == "prepare":
        prepare()
    elif args.action == "recover":
        recover_incomplete_setup()
    else:
        submit(args.confirm)


if __name__ == "__main__":
    main()
