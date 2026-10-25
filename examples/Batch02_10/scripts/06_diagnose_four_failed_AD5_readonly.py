#!/usr/bin/env python3
"""Read-only diagnosis of four failed Batch02 first AD5 jobs, 25 Oct 2026.

Reads exact submitted job IDs, Slurm stdout/stderr, CaseStatus and recent model
logs. Writes only a new HOME report. No CIME commands, model/forcing changes,
case.submit, scancel, restart manipulation, AD395 or Normal submission.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
OUT = BASE / "experiments/NonCompetitionObserved22/Batch02_10"
OUTPUTS = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
JOBS = {"FI-Hyy": ("4728102", "4728103"), "FR-Hes": ("4728104", "4728105"),
        "CH-Fru": ("4728106", "4728107"), "IT-MBo": ("4728108", "4728109")}
ERROR = re.compile(r"error|fatal|abort|traceback|forrtl|not found|no such file|permission denied|"
                   r"killed|segmentation|cannot open|could not|failed|mismatch|exception|"
                   r"undefined symbol|bad termination|out.of.memory", re.I)
LIMIT = 768 * 1024


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=40)
        return {"command": args, "returncode": result.returncode,
                "text": (result.stdout + "\n" + result.stderr).strip()}
    except Exception as exc:
        return {"command": args, "returncode": None, "text": type(exc).__name__ + ": " + str(exc)}


def fields(text):
    # Slurm -o output uses key=value fields. Do not execute returned paths.
    return dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)=(\S+)", text))


def tail_text(path):
    if path.suffix == ".gz":
        # Retain a bounded tail while streaming; do not expand runaway logs.
        tail, total = b"", 0
        with gzip.open(path, "rb") as f:
            while total < 16 * 1024 * 1024:
                chunk = f.read(65536)
                if not chunk:
                    return tail.decode("utf-8", errors="replace"), "COMPLETE_OR_BOUNDED_TAIL"
                total += len(chunk)
                tail = (tail + chunk)[-LIMIT:]
        return tail.decode("utf-8", errors="replace"), "EXPANSION_LIMIT_FIRST_16MIB_ONLY"
    with path.open("rb") as f:
        size = path.stat().st_size
        f.seek(max(0, size - LIMIT))
        return f.read(LIMIT).decode("utf-8", errors="replace"), "COMPLETE" if size <= LIMIT else "LAST_768KIB"


def error_excerpt(text, limit=80):
    lines = text.splitlines()
    indices = set()
    hits = [i for i, line in enumerate(lines) if ERROR.search(line)]
    for i in hits[:16]:
        indices.update(range(max(0, i - 3), min(len(lines), i + 5)))
    return [lines[i][:1200] for i in sorted(indices)[:limit]]


def file_record(path):
    try:
        text, scope = tail_text(path)
        return {"path": str(path), "bytes": path.stat().st_size, "scope": scope,
                "error_context": error_excerpt(text), "tail": text.splitlines()[-140:]}
    except Exception as exc:
        return {"path": str(path), "read_error": type(exc).__name__ + ": " + str(exc)}


def recent(folder, pattern, count=2):
    try:
        files = [p for p in folder.glob(pattern) if p.is_file()]
        return sorted(files, key=lambda p: p.stat().st_mtime_ns, reverse=True)[:count]
    except OSError:
        return []


def case_metadata(case, run):
    obj = {"case_exists": case.is_dir(), "run_exists": run.is_dir(), "xml": {}, "land_namelists": {}}
    keys = {"CASE", "RUNDIR", "EXEROOT", "RUN_TYPE", "RUN_STARTDATE", "CONTINUE_RUN", "STOP_N", "REST_N",
            "RESUBMIT", "CLM_ACCELERATED_SPINUP", "CLM_FORCE_COLDSTART", "CLM_BLDNML_OPTS", "MPI_RUN_COMMAND"}
    for file in ("env_case.xml", "env_run.xml", "env_build.xml"):
        p = case / file
        if p.is_file():
            try:
                obj["xml"][file] = {e.get("id"): e.get("value") for e in ET.parse(p).getroot().iter("entry") if e.get("id") in keys}
            except Exception as exc:
                obj["xml"][file] = {"error": str(exc)}
    for p in (case / "CaseDocs/lnd_in", run / "lnd_in"):
        if p.is_file():
            text, _ = tail_text(p)
            vals = {}
            for key in ("use_fates", "use_fates_sp", "use_fates_fixed_biogeog", "use_fates_nocomp", "spinup_state", "finidat", "fsurdat"):
                vals[key] = re.findall(r"(?im)^\s*" + key + r"\s*=([^\r\n]*)", text)
            obj["land_namelists"][str(p)] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "values": vals}
    obj["run_restart_names"] = [p.name for p in sorted(run.glob("*.r.*.nc"))[:12]]
    return obj


def site_report(site):
    name = site + "_B02_FIXNC_AD400"
    case, run = BASE / "cases" / name, OUTPUTS / name / "run"
    ids = JOBS[site]
    result = {"site": site, "case": str(case), "run": str(run), "run_job": ids[0], "archive_job": ids[1]}
    ledger = OUT / site / "AD5_case_state.json"
    try:
        obj = json.loads(ledger.read_text())
        result["submission_state"] = {k: obj.get(k) for k in ("phase", "first_run_job", "first_archive_job", "submission_output_file", "skip_preview_persisted")}
        if (str(obj.get("first_run_job")), str(obj.get("first_archive_job"))) != ids:
            result["ledger_issue"] = "Ledger differs from operator's exact submitted job IDs; no automatic recovery"
    except Exception as exc:
        result["ledger_issue"] = str(exc)
    result["metadata"] = case_metadata(case, run)
    result["scontrol"] = [command(["scontrol", "show", "job", "-o", j]) for j in ids]
    candidates = [case / "CaseStatus", case / ".submit_options", case / ".case.run",
                  OUT / site / "AD5_case_submit_output.txt"]
    for jobid, response in zip(ids, result["scontrol"]):
        parsed = fields(response["text"])
        for key in ("StdOut", "StdErr"):
            value = parsed.get(key, "")
            if value.startswith("/"):
                p = Path(value.replace("%j", jobid).replace("%x", parsed.get("JobName", name)))
                if p.is_file():
                    candidates.append(p)
    # These are direct, bounded globs in the exact case/run, never recursive scans.
    for folder in (case, run):
        for job in ids:
            candidates += recent(folder, "*" + job + "*", 4)
        for pattern in ("*.out", "*.err", "slurm-*.out"):
            candidates += recent(folder, pattern, 2)
    for family in ("cesm", "cpl", "lnd", "atm", "med", "datm"):
        candidates += recent(run, family + ".log.*", 2)
    paths = []
    seen = set()
    for p in candidates:
        if p.is_file() and str(p.resolve()) not in seen:
            paths.append(p)
            seen.add(str(p.resolve()))
    result["files"] = [file_record(p) for p in paths[:28]]
    return result


def diagnose():
    ids = [j for pair in JOBS.values() for j in pair]
    report = {"version": "batch02-four-AD5-failure-diagnosis-v1-20261025", "created_utc": datetime.now(timezone.utc).isoformat(),
              "model_files_modified": False, "jobs_submitted_or_cancelled": False,
              "sacct": command(["sacct", "-j", ",".join(ids), "-n", "-P",
                                  "--format=JobIDRaw,JobName%96,State,ExitCode,Elapsed,NodeList%40,Reason%80,MaxRSS"]),
              "squeue": command(["squeue", "-j", ",".join(ids), "-h", "-o", "%i|%j|%T|%R"]), "sites": []}
    work = Path(tempfile.mkdtemp(prefix="Batch02_10_AD5_failure_diagnosis_", dir=Path.home()))
    print("=== EXACT AD5 RUN/ARCHIVE ACCOUNTING ===")
    print(report["sacct"]["text"])
    print("=== REMAINING QUEUE / REASONS ===")
    print(report["squeue"]["text"] or "NO MATCHING JOBS IN QUEUE")
    console = []
    for site in JOBS:
        try:
            obj = site_report(site)
        except Exception as exc:
            obj = {"site": site, "run_job": JOBS[site][0], "archive_job": JOBS[site][1],
                   "ledger_issue": "SITE_DIAGNOSIS_ERROR: " + str(exc), "scontrol": [], "files": [], "metadata": {}}
        report["sites"].append(obj)
        lines = ["\n=== " + site + " | run=" + obj["run_job"] + " archive=" + obj["archive_job"] + " ==="]
        if obj.get("ledger_issue"):
            lines.append("LEDGER_REVIEW " + obj["ledger_issue"])
        for job in obj["scontrol"]:
            meta = fields(job["text"])
            lines.append("JOB " + " ".join(k + "=" + meta[k] for k in ("JobId", "JobState", "Reason", "ExitCode", "StdOut", "StdErr") if k in meta))
        errors = [f for f in obj["files"] if f.get("error_context") and Path(f["path"]).name not in (".case.run", ".submit_options")]
        for f in errors[:6]:
            lines.append("FILE " + f["path"])
            lines.extend(f["error_context"][:36])
        if not errors:
            lines.append("NO_ERROR_CONTEXT_FOUND; review available log tails in report")
        print("\n".join(lines), flush=True)
        console.extend(lines)
    json_path = work / "failure_diagnosis.json"
    text_path = work / "failure_diagnosis.txt"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with text_path.open("w", encoding="utf-8") as f:
        f.write(report["sacct"]["text"] + "\n" + report["squeue"]["text"] + "\n")
        for site in report["sites"]:
            f.write("\n===== " + site["site"] + " =====\n" + json.dumps(site["metadata"], indent=2) + "\n")
            for item in site["files"]:
                f.write("\nFILE " + item["path"] + "\n" + "\n".join(item.get("tail", [])) + "\n")
    print("REPORT_JSON=" + str(json_path))
    print("REPORT_TEXT=" + str(text_path))
    print("READ-ONLY DIAGNOSIS COMPLETE: no model/forcing edits, job cancellation or submission; no AD395/Normal")


def self_test():
    assert fields("JobId=12 StdOut=/tmp/a JobState=FAILED")["StdOut"] == "/tmp/a"
    assert "fatal" in " ".join(error_excerpt("start\ncontext\nfatal input mismatch\nend")).lower()
    assert len({j for pair in JOBS.values() for j in pair}) == 8
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cesm.log.gz"
        with gzip.open(path, "wt") as f:
            f.write("initialization\nERROR: fixture only\n")
        assert "fixture only" in tail_text(path)[0]
        assert file_record(path)["error_context"]
    print("STAGE06 SELF-TEST PASS: exact eight IDs, Slurm path extraction, gzip/error-context reading; no model writes")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "diagnose"))
    a = p.parse_args()
    self_test() if a.action == "self-test" else diagnose()
