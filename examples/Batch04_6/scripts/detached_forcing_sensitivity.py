#!/usr/bin/env python3
"""Create an auditable detached single-point forcing sensitivity.

Input paths, timestamps, values and output directories are supplied at runtime;
the script contains no station records. It never submits a model or overwrites
the baseline. It implements a water-reference saturation-vapour-pressure
formula; callers must verify that formula and the clock suit their source data.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, date2num


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def humidity(t, vpd, pressure):
    sat = 6.112 * math.exp(17.67 * t / (t + 243.5))
    vapour = (sat - vpd) * 100.0
    need(0 <= vpd <= sat and 50000 <= pressure <= 115000 and 0 <= vapour < pressure,
         "Temperature, VPD or pressure is outside the supported physical range")
    return 0.622 * vapour / (pressure - 0.378 * vapour)


def validate_edits(edits):
    need(isinstance(edits, list) and 1 <= len(edits) <= 1000, "Invalid number of edits")
    rows = {}
    fields = ("baseline_ta_c", "baseline_vpd_hpa", "candidate_ta_c", "candidate_vpd_hpa")
    for e in edits:
        stamp = e["time"]
        dt = datetime.fromisoformat(stamp)
        need(dt.tzinfo is None, "Expected timezone-naive source label")
        need(stamp not in rows, "Duplicate time: " + stamp)
        values = [float(e[k]) for k in fields]
        need(all(math.isfinite(x) and x > -9990 for x in values), "Missing source value")
        need(e.get("ta_source_qc") == 1 and e.get("vpd_source_qc") == 1,
             "Expected QC1 source values")
        rows[stamp] = values
    return rows


def make(baseline, partial, rows):
    original_sha = sha(baseline)
    need(not partial.exists(), "Output already exists")
    with baseline.open("rb") as src, partial.open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    edits = {}
    with Dataset(baseline, "r") as old, Dataset(partial, "r+") as new:
        need(set(old.variables) == set(new.variables), "Variable set differs")
        time = old.variables["time"]
        calendar = getattr(time, "calendar", "")
        need(calendar in ("noleap", "365_day") and len(time) == 17520,
             "Expected a 17520-point no-leap year")
        for name, unit in (("TBOT", "K"), ("QBOT", "kg/kg"), ("PSRF", "Pa")):
            need(name in old.variables and getattr(old.variables[name], "units", "") == unit,
                 "Missing variable or unexpected unit: " + name)
            need(old.variables[name].shape == (17520, 1, 1), "Unexpected dimensions: " + name)
        axis = np.asarray(time[:], dtype=float)
        for stamp, (ta, vpd, replacement_t, replacement_vpd) in sorted(rows.items()):
            when = float(date2num(datetime.fromisoformat(stamp), units=time.units, calendar=calendar))
            hits = np.flatnonzero(np.isclose(axis, when, rtol=0, atol=1e-9))
            need(len(hits) == 1, "Time not uniquely matched: " + stamp)
            i = int(hits[0])
            t = float(old.variables["TBOT"][i, 0, 0])
            q = float(old.variables["QBOT"][i, 0, 0])
            pressure = float(old.variables["PSRF"][i, 0, 0])
            need(abs(t - (ta + 273.15)) < 5e-5, "Baseline TBOT mismatch: " + stamp)
            need(abs(q - humidity(ta, vpd, pressure)) < 1e-8, "Baseline QBOT mismatch: " + stamp)
            replacement_k = replacement_t + 273.15
            replacement_q = humidity(replacement_t, replacement_vpd, pressure)
            new.variables["TBOT"][i, 0, 0] = replacement_k
            new.variables["QBOT"][i, 0, 0] = replacement_q
            edits[i] = {"time": stamp, "pressure_pa": pressure, "before_tbot_k": t,
                        "before_qbot": q, "after_tbot_k": replacement_k,
                        "after_qbot": replacement_q}
        need(len(edits) == len(rows), "Unexpected edit count")
        new.sensitivity_provenance_status = "EXPLORATORY_NOT_SCIENCE_RELEASED"
        new.sensitivity_original_sha256 = original_sha
        new.sensitivity_description = "Selected temperature and VPD alternatives; pressure unchanged"
    with Dataset(baseline) as old, Dataset(partial) as new:
        need(set(old.variables) == set(new.variables), "Variable set changed")
        for name in old.variables:
            before = np.ma.asarray(old.variables[name][:])
            actual = np.ma.asarray(new.variables[name][:])
            expected = before.copy()
            if name in ("TBOT", "QBOT"):
                for i, e in edits.items():
                    expected[i, 0, 0] = e["after_tbot_k"] if name == "TBOT" else e["after_qbot"]
            need(np.ma.allequal(expected, actual), "Outside-target or incorrect edit: " + name)
    need(sha(baseline) == original_sha, "Baseline changed during candidate generation")
    return list(edits.values())


def self_test(parent):
    with tempfile.TemporaryDirectory(dir=parent) as temp:
        root = Path(temp)
        baseline, candidate = root / "baseline.nc", root / "candidate.nc"
        fixtures = {"2023-03-02 12:00:00": (-3., 1., 6., 3.),
                    "2023-03-02 12:30:00": (-2., 1.1, 6.2, 3.1)}
        with Dataset(baseline, "w", format="NETCDF4_CLASSIC") as ds:
            ds.createDimension("time", 17520)
            ds.createDimension("lat", 1)
            ds.createDimension("lon", 1)
            t = ds.createVariable("time", "f8", ("time",))
            t.units = "days since 2023-01-01 00:00:00"
            t.calendar = "noleap"
            t[:] = np.arange(17520) / 48
            for name, unit, value in (("TBOT", "K", 280.), ("QBOT", "kg/kg", 0.003),
                                      ("PSRF", "Pa", 78957.), ("ZBOT", "m", 2.)):
                v = ds.createVariable(name, "f4", ("time", "lat", "lon"))
                v.units = unit
                v[:] = value
            for stamp, (ta, vpd, _, _) in fixtures.items():
                target = date2num(datetime.fromisoformat(stamp), units=t.units, calendar=t.calendar)
                i = int(np.flatnonzero(np.isclose(t[:], target, rtol=0, atol=1e-9))[0])
                ds["TBOT"][i, 0, 0] = ta + 273.15
                ds["QBOT"][i, 0, 0] = humidity(ta, vpd, 78957.)
        need(len(make(baseline, candidate, fixtures)) == 2, "Self-test edit count mismatch")
        wrong = dict(fixtures)
        first = next(iter(wrong))
        old = wrong[first]
        wrong[first] = (old[0] + 5, old[1], old[2], old[3])
        try:
            make(baseline, root / "bad.nc", wrong)
        except ValueError:
            pass
        else:
            raise ValueError("Self-test failed to reject baseline mismatch")
    print("SELF-TEST PASS: no-leap indices, full-array differences and mismatch guard")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--test-dir", type=Path)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--expected-baseline-sha256")
    p.add_argument("--edits-json", type=Path)
    p.add_argument("--out-dir", type=Path)
    a = p.parse_args()
    if a.self_test:
        need(a.test_dir is not None and a.test_dir.is_dir(), "Existing test directory required")
        self_test(a.test_dir)
        return
    need(all((a.baseline, a.expected_baseline_sha256, a.edits_json, a.out_dir)),
         "Baseline, baseline SHA, edits and output directory are required")
    need(a.out_dir.is_dir() and not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
         "Output must be an existing empty directory")
    need(a.baseline.is_file() and sha(a.baseline) == a.expected_baseline_sha256,
         "Baseline SHA mismatch")
    edit_sha = sha(a.edits_json)
    rows = validate_edits(json.loads(a.edits_json.read_text())["edits"])
    partial, final = a.out_dir / "candidate.partial.nc", a.out_dir / "candidate.nc"
    edits = make(a.baseline, partial, rows)
    need(sha(a.edits_json) == edit_sha and sha(a.baseline) == a.expected_baseline_sha256,
         "Input changed during processing")
    report = {"status": "DETACHED_EXPLORATORY_NOT_RELEASED",
              "baseline_path": str(a.baseline), "baseline_sha256": a.expected_baseline_sha256,
              "edits_sha256": edit_sha, "candidate_path": str(final),
              "candidate_sha256": sha(partial), "case_or_slurm_modified": False,
              "observational_clock_alignment_verified": False, "changes": edits}
    with (a.out_dir / "manifest.json").open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    os.replace(partial, final)
    print("CANDIDATE", final)
    print("SHA256", report["candidate_sha256"])
    print("EDITS", len(edits), "all variable arrays checked; no case or job submitted")


if __name__ == "__main__":
    main()
