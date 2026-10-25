#!/usr/bin/env python3
"""Check/submit exactly four prepared Batch02 first-five-year AD pilots.

No case creation, namelist preview, XML changes, AD395 or Normal submission.
Checks existing Stage04 receipts and current inputs. Exclusive batch/site attempt
records prevent duplicate submission after partial/ambiguous results. Real CIME
run/archive IDs are retained for subsequent accounting and continuation.
"""
from __future__ import annotations

import argparse
import configparser
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b02_prepare", HERE / "04_prepare_four_AD5_cases.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
VERSION = "batch02-four-initial-AD5-submit-v1-20261025"
PREPARED = "PREPARED_NOT_SUBMITTED"
ATTEMPTED = "AD5_SUBMISSION_ATTEMPTED_UNCERTAIN"
SUBMITTED = "FIRST_5Y_SUBMITTED"
REVIEW = "FIRST_5Y_SUBMITTED_REVIEW"


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, obj):
    fd, temp = tempfile.mkstemp(prefix=".AD5-state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def batch_attempt():
    return B.OUT / "_four_initial_AD5_submission_attempt.json"


def site_attempt(site):
    return B.OUT / site / "AD5_submit_attempt.json"


def load_state(site):
    path = B.paths(site)[3]
    if path.is_symlink() or not path.is_file():
        B.fail(site + ": Stage04 state missing/unsafe")
    return json.loads(path.read_text())


def identity(site, obj, row, data, source):
    case, run, archive, _ = B.paths(site)
    expected = {"phase": PREPARED, "version": B.VERSION, "site": site,
                "case": str(case), "run": str(run), "archive": str(archive),
                "surface": str(B.S.destination(row, B.OUT)), "start_date": source["start_date"],
                "spinup_state": 2, "RESUBMIT": 0, "years": 5, "Slurm_jobs_submitted": False,
                "CIME_env_case_lock_restored": True, "private_overlay": str(B.OVERLAY),
                "parameter_sha256": data["active_parameter_sha256"]}
    for key, value in expected.items():
        if obj.get(key) != value:
            B.fail(site + ": Stage04 state differs: " + key + "=" + repr(obj.get(key)))
    if obj.get("AD5_end_year") != int(source["start_date"][:4]) + 5:
        B.fail(site + ": AD5 end year differs")


def no_case_submission(case):
    status = case / "CaseStatus"
    if not status.is_file():
        B.fail("CaseStatus missing: " + str(case))
    if re.search(r"(?:case\.)?(?:submit|run|st_archive)\s+(?:starting|success)", status.read_text(errors="replace")):
        B.fail("Case has submission/run/archive history; do not duplicate: " + str(case))


def input_check(site, obj, row, data, source):
    identity(site, obj, row, data, source)
    case, run, archive, _ = B.paths(site)
    if case.is_symlink() or not case.is_dir():
        B.fail(site + ": independent case missing/unsafe")
    attempt = site_attempt(site)
    if attempt.exists() or attempt.is_symlink():
        B.fail(site + ": prior submission attempt exists; do not retry")
    prior_output = B.OUT / site / "AD5_case_submit_output.txt"
    if prior_output.exists() or prior_output.is_symlink():
        B.fail(site + ": submission output already exists; inspect before submitting")
    prep = B.OUT / site / "AD5_prepare_attempt.json"
    if prep.is_symlink() or not prep.is_file() or json.loads(prep.read_text()).get("phase") != "DONE_NO_JOBS":
        B.fail(site + ": preparation did not finish cleanly")
    no_case_submission(case)
    for key, expected in B.settings(source, site).items():
        if B.query(case, key).lower() != expected.lower():
            B.fail(site + ": current CIME setting differs: " + key)
    for key, expected in (("CASE", B.name(site)), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48"),
                          ("TOTALPES", "1"), ("NTHRDS_LND", "1"), ("BUILD_COMPLETE", "TRUE"),
                          ("CLM_CO2_TYPE", source["co2_type"])):
        if B.query(case, key).lower() != expected.lower():
            B.fail(site + ": current case identity/resource/CO2 differs: " + key)
    if not abs(float(B.query(case, "CCSM_CO2_PPMV")) - source["co2_ppm"]) <= 1e-8:
        B.fail(site + ": fixed CO2 changed")
    exe = Path(obj["executable"])
    if Path(B.query(case, "EXEROOT")).resolve() != exe.parent.resolve() or B.S.sha256(exe) != obj["executable_sha256"]:
        B.fail(site + ": executable root/bytes changed")
    B.lock_bytes(case)
    if archive.exists() or any(run.glob("*.r.*.nc")):
        B.fail(site + ": target has archive/restarts; not an initial cold start")
    surface = B.S.destination(row, B.OUT)
    receipt = surface.with_suffix(".json")
    if surface.is_symlink() or receipt.is_symlink() or B.S.sha256(surface) != obj["surface_sha256"]:
        B.fail(site + ": surface changed")
    rec = json.loads(receipt.read_text())
    if (rec.get("candidate_sha256") != obj["surface_sha256"]
            or rec.get("configuration_sha256") != B.S.sha256(B.S.CONFIG)
            or rec.get("site_inputs_and_assumptions") != row):
        B.fail(site + ": Stage03 receipt/config changed")
    for rel, sha in (("lnd_in", obj["generated_lnd_in_sha256"]),
                     ("datm.streams.xml", obj["generated_stream_sha256"])):
        for p in (case / "CaseDocs" / rel, run / rel):
            if not p.is_file() or B.S.sha256(p) != sha:
                B.fail(site + ": prepared generated input changed: " + str(p))
    for filename, sha in obj["user_DATM_files"].items():
        if B.S.sha256(case / filename) != sha:
            B.fail(site + ": user DATM input changed: " + filename)
    text = (case / "CaseDocs/lnd_in").read_text()
    user = (case / "user_nl_clm").read_text()
    for key, value in B.desired(row, data).items():
        if key != "hist_fincl1":
            if B.nml_get(text, key) != value.strip("'\"") or B.nml_get(user, key) != value.strip("'\""):
                B.fail(site + ": effective/user AD5 value differs: " + key)
    # No annual NetCDF meteorology reread. These are the verified Stage04 files.
    print(site, "AD5_SUBMIT_PREFLIGHT_PASS", "STOP_N=REST_N=5 RESUBMIT=0 spinup_state=2", flush=True)


def queue_rows():
    text = B.call(["squeue", "-u", "ly3n24", "-h", "-o", "%i|%j|%T"], timeout=45)
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            B.fail("Unparseable squeue output")
        rows.append(parts)
    return rows


def no_active_jobs(rows):
    names = {prefix + B.name(s) for s in B.S.SELECTED for prefix in ("run.", "st_archive.")}
    matches = [r for r in rows if r[1] in names]
    if matches:
        B.fail("Batch02 AD5 job already queued/running; do not duplicate: " + repr(matches))


def preflight():
    marker = batch_attempt()
    if marker.exists() or marker.is_symlink():
        B.fail("Initial submission already attempted; use status instead: " + str(marker))
    data, src = B.S.configuration(), B.sources()
    B.S.parameter_map(data)
    B.overlay_check()
    no_active_jobs(queue_rows())
    records = {}
    for row in data["sites"]:
        site = row["site"]
        obj = load_state(site)
        input_check(site, obj, row, data, src[site])
        records[site] = obj
    print("AD5_SUBMIT_PREFLIGHT_PASS 4/4 | existing cases only; no forcing-value rescan", flush=True)
    return records


def job_ids(output):
    run = re.findall(r"Submitted job case\.run with id (\d+)", output)
    archive = re.findall(r"Submitted job case\.st_archive with id (\d+)", output)
    if len(run) != 1 or len(archive) != 1 or run[0] == archive[0] or int(run[0]) <= 0 or int(archive[0]) <= 0:
        B.fail("CIME run/archive job IDs not unique/parseable; retain attempt and do not retry")
    return run[0], archive[0]


def skip_preview_persisted(case):
    cp = configparser.RawConfigParser()
    cp.read(case / ".submit_options")
    return cp.has_section("SubmitOptions") and cp.getboolean("SubmitOptions", "skip_pnl", fallback=False)


def submit_one(site, approved):
    case, _, _, ledger = B.paths(site)
    if load_state(site) != approved:
        B.fail(site + ": ledger changed after batch preflight")
    no_case_submission(case)
    B.write_json(site_attempt(site), {"site": site, "phase": ATTEMPTED, "utc": now()}, exclusive=True)
    obj = dict(approved, phase=ATTEMPTED, submission_attempt_utc=now(), submit_version=VERSION)
    atomic_json(ledger, obj)
    outpath = B.OUT / site / "AD5_case_submit_output.txt"
    with outpath.open("x", encoding="utf-8") as f:
        try:
            result = subprocess.run([str(case / "case.submit"), "--skip-preview-namelist"], cwd=case,
                                    capture_output=True, text=True, timeout=360)
            output = result.stdout + "\n" + result.stderr
            f.write(output)
        except Exception as exc:
            for chunk in (getattr(exc, "stdout", None), getattr(exc, "stderr", None)):
                if chunk:
                    f.write(chunk.decode(errors="replace") if isinstance(chunk, bytes) else str(chunk))
            f.write("\nSUBMISSION_EXCEPTION: " + str(exc))
            obj.update(submission_output_file=str(outpath), submission_error=str(exc))
            atomic_json(ledger, obj)
            raise
        finally:
            f.flush()
            os.fsync(f.fileno())
    obj["submission_output_file"] = str(outpath)
    obj["submission_exit_code"] = result.returncode
    try:
        runid, archiveid = job_ids(output)
        obj.update(first_run_job=runid, first_archive_job=archiveid)
        atomic_json(ledger, obj)
    except RuntimeError:
        atomic_json(ledger, obj)
        raise
    # Preserve IDs even if CIME reports a later error or submit-options check fails.
    try:
        persisted = skip_preview_persisted(case)
    except Exception as exc:
        persisted = False
        obj["submit_options_error"] = str(exc)
    obj.update(Slurm_jobs_submitted=True, submitted_utc=now(), skip_preview_persisted=persisted,
               phase=SUBMITTED if result.returncode == 0 and persisted else REVIEW)
    atomic_json(ledger, obj)
    B.write_json(site_attempt(site), {"site": site, "phase": obj["phase"], "first_run_job": runid,
                                    "first_archive_job": archiveid, "utc": now()})
    if obj["phase"] != SUBMITTED:
        B.fail(site + ": jobs have IDs but CIME return/options need review; no retry: " + str(outpath))
    print(site, "AD5_SUBMITTED", "RUN=" + runid, "ARCHIVE=" + archiveid,
          "YEARS=5 RESUBMIT=0 SKIP_PREVIEW_PERSISTED=TRUE", flush=True)


def submit():
    records = preflight()
    no_active_jobs(queue_rows())
    B.write_json(batch_attempt(), {"version": VERSION, "phase": ATTEMPTED, "utc": now(),
                                  "sites": list(B.S.SELECTED)}, exclusive=True)
    done = []
    try:
        for site in B.S.SELECTED:
            submit_one(site, records[site])
            done.append(site)
    except Exception as exc:
        atomic_json(batch_attempt(), {"version": VERSION, "phase": "STOPPED_REVIEW_REQUIRED", "utc": now(),
                                      "submitted_before_error": done, "error": str(exc)[-2500:]})
        print("AD5_SUBMIT_STOPPED", str(exc), flush=True)
        print("Do not rerun submit. Use status and retain per-site attempt/state/output records.", flush=True)
        return 2
    atomic_json(batch_attempt(), {"version": VERSION, "phase": "FOUR_FIRST_AD5_SUBMITTED", "utc": now(),
                                  "sites": done})
    print("AD5_SUBMIT_SUMMARY submitted= 4 failed= []")
    print("FIRST FIVE AD YEARS ONLY. AD395 and Normal400 NOT submitted.")
    return 0


def status():
    rows = queue_rows()
    records = {s: load_state(s) for s in B.S.SELECTED}
    ids = [str(obj[k]) for obj in records.values() for k in ("first_run_job", "first_archive_job") if obj.get(k)]
    acct = {}
    if ids:
        out = B.call(["sacct", "-X", "-j", ",".join(ids), "-n", "-P",
                      "--format=JobIDRaw,JobName%128,State,ExitCode"], timeout=60)
        for line in out.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[0] in ids:
                acct[parts[0]] = "/".join(parts[2:4])
    for site, obj in records.items():
        jobs = ["/".join(r) for r in rows if r[1] in ("run." + B.name(site), "st_archive." + B.name(site))]
        print(site, "PHASE=" + str(obj.get("phase")), "RUN=" + str(obj.get("first_run_job", "-")),
              acct.get(str(obj.get("first_run_job")), "-"), "ARCHIVE=" + str(obj.get("first_archive_job", "-")),
              acct.get(str(obj.get("first_archive_job")), "-"), "QUEUE=" + (";".join(jobs) or "-"))
    print("Read-only scheduler status; archived AD5 restarts must still be verified before AD395.")


def self_test():
    assert job_ids("Submitted job case.run with id 123\nSubmitted job case.st_archive with id 124") == ("123", "124")
    for text in ("Submitted batch job 123", "Submitted job case.run with id 123", "Submitted job case.run with id 123\nSubmitted job case.st_archive with id 123"):
        try:
            job_ids(text)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Ambiguous job IDs accepted")
    assert set(B.S.SELECTED) == {"FI-Hyy", "FR-Hes", "CH-Fru", "IT-MBo"}
    print("STAGE05 SELF-TEST PASS: four exact sites; distinct CIME run/archive job IDs; no model writes/submission")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "check", "submit", "status"))
    a = p.parse_args()
    if a.action == "self-test":
        self_test()
    elif a.action == "check":
        preflight()
        print("NO JOBS SUBMITTED BY CHECK")
    elif a.action == "status":
        status()
    else:
        return submit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
