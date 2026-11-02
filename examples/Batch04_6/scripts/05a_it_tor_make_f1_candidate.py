#!/usr/bin/env python3
"""Create one detached IT-Tor 2025 forcing sensitivity; never submit a model."""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
from datetime import datetime
from pathlib import Path
import tempfile

import numpy as np
from netCDF4 import Dataset, date2num

TARGET = (
    "2025-11-13 14:30:00",
    "2025-11-13 15:00:00",
    "2025-11-13 15:30:00",
)
FILES = {"STAGE30_CONSOLIDATED": "04_consolidated_13site_271_DATM_SHA256_manifest.csv",
         "STAGE29B": "10_annual_full_DATM_SHA256_manifest.csv"}

def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def humidity(t, vpd, pressure):
    sat = 6.112 * math.exp(17.67 * t / (t + 243.5))
    vapour = (sat - vpd) * 100.
    need(0 <= vpd <= sat and 50000 <= pressure <= 115000 and 0 <= vapour < pressure,
         "Nonphysical T, VPD or pressure")
    return 0.622 * vapour / (pressure - 0.378 * vapour)

def source_rows(path):
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            stamp = row.get("time")
            if stamp not in TARGET:
                continue
            vals = tuple(float(row[k]) for k in ("TA_F", "VPD_F", "TA_ERA", "VPD_ERA"))
            need(float(row["TA_F_QC"]) == 1 and float(row["VPD_F_QC"]) == 1,
                 "Unexpected source QC at " + stamp)
            need(all(math.isfinite(a) and a > -9990 for a in vals),
                 "Missing or nonfinite source context: " + stamp)
            need(stamp not in rows or rows[stamp] == vals, "Conflicting duplicate: " + stamp)
            rows[stamp] = vals
    need(set(rows) == set(TARGET), "Three source records missing")
    return rows

def input_from_report(path):
    d = json.loads(path.read_text())
    need(d.get("read_only") is True and d.get("science_release") is False,
         "Unexpected source lineage report")
    sites = [x for x in d.get("sites", []) if x.get("site") == "IT-Tor"]
    need(len(sites) == 1 and sites[0].get("all_current_paths_match_historical") is True,
         "IT-Tor lineage missing")
    s = sites[0]
    manifest = Path(s["historical_DATM_manifest"])
    if manifest.is_dir():
        need(s.get("historical_manifest_selected") in FILES, "Unknown annual manifest")
        manifest /= FILES[s["historical_manifest_selected"]]
    with manifest.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r.get("site") == "IT-Tor" and r.get("year") == "2025"]
    need(len(rows) == 1, "Missing or duplicate 2025 annual manifest")
    path = Path(rows[0]["datm_nc"])
    comparison = [x for x in s["yearly_path_comparisons"] if int(x["year"]) == 2025]
    need(len(comparison) == 1 and comparison[0].get("current") == str(path)
         and comparison[0].get("literal_path_equal") is True, "Annual path mismatch")
    need(path.is_file() and sha(path) == rows[0]["sha256"], "Annual input SHA mismatch")
    return path, rows[0]["sha256"]

def make(original, partial, rows):
    before_sha = sha(original)
    need(not partial.exists(), "Candidate file already exists")
    with original.open("rb") as src, partial.open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024*1024)
    edits = {}
    with Dataset(original, "r") as old, Dataset(partial, "r+") as new:
        need(set(old.variables) == set(new.variables), "Variable set changed during copy")
        time = old.variables["time"]
        calendar = getattr(time, "calendar", "")
        need(calendar in ("noleap", "365_day") and len(time) == 17520,
             "Unexpected 2025 no-leap time axis")
        for name, unit in (("TBOT", "K"), ("QBOT", "kg/kg"), ("PSRF", "Pa")):
            need(name in old.variables and getattr(old.variables[name], "units", "") == unit,
                 "Missing variable or unexpected unit: " + name)
            need(old.variables[name].shape == (17520,1,1), "Unexpected dimensions: " + name)
        axis = np.asarray(time[:], dtype=float)
        for stamp, (ta, vpd, era_t, era_vpd) in sorted(rows.items()):
            target = float(date2num(datetime.fromisoformat(stamp), units=time.units, calendar=calendar))
            hits = np.flatnonzero(np.isclose(axis, target, rtol=0, atol=1e-9))
            need(len(hits) == 1, "DATM time not unique: " + stamp)
            i = int(hits[0])
            t = float(old.variables["TBOT"][i,0,0])
            q = float(old.variables["QBOT"][i,0,0])
            p = float(old.variables["PSRF"][i,0,0])
            need(abs(t-(ta+273.15)) < 5e-5, "Original TA differs from source label: " + stamp)
            need(abs(q-humidity(ta,vpd,p)) < 1e-8, "Original QBOT differs from source: " + stamp)
            t_new = era_t + 273.15
            q_new = humidity(era_t,era_vpd,p)
            new.variables["TBOT"][i,0,0] = t_new
            new.variables["QBOT"][i,0,0] = q_new
            edits[i] = {"time": stamp, "pressure_pa": p, "before_tbot_k": t,
                        "before_qbot": q, "after_tbot_k": t_new, "after_qbot": q_new}
        need(len(edits) == 3, "Expected exactly three distinct records")
        new.sensitivity_provenance_status = "EXPLORATORY_NOT_SCIENCE_RELEASED"
        new.sensitivity_description = "Three source labels: packaged ERA TA and VPD; pressure unchanged"
        new.sensitivity_original_sha256 = before_sha
    with Dataset(original) as old, Dataset(partial) as new:
        for name in old.variables:
            a, b = np.ma.asarray(old.variables[name][:]), np.ma.asarray(new.variables[name][:])
            expected = a.copy()
            if name in ("TBOT", "QBOT"):
                for i, e in edits.items():
                    expected[i,0,0] = e["after_tbot_k"] if name == "TBOT" else e["after_qbot"]
            need(np.ma.allequal(expected,b), "Outside-target or incorrect variable change: " + name)
    need(sha(original) == before_sha, "Original changed during candidate creation")
    return list(edits.values())

def self_test(root):
    # Synthetic values do not reproduce the licensed station observations.
    fixtures = {
        TARGET[0]: (-3., 1., 6., 3.),
        TARGET[1]: (-2., 1.1, 6.2, 3.1),
        TARGET[2]: (-1., 1.2, 6.4, 3.2),
    }
    with tempfile.TemporaryDirectory(dir=root) as directory:
        root = Path(directory)
        original, candidate = root/"baseline.nc", root/"candidate.nc"
        with Dataset(original, "w", format="NETCDF4_CLASSIC") as ds:
            ds.createDimension("time",17520)
            ds.createDimension("lat",1)
            ds.createDimension("lon",1)
            t = ds.createVariable("time","f8",("time",))
            t.units = "days since 2025-01-01 00:00:00"
            t.calendar = "noleap"
            t[:] = np.arange(17520)/48
            for name,unit,val in (("TBOT","K",280.),("QBOT","kg/kg",0.003),
                                  ("PSRF","Pa",78957.),("ZBOT","m",2.)):
                v = ds.createVariable(name,"f4",("time","lat","lon"))
                v.units=unit
                v[:]=val
            for stamp,(ta,vpd,_,_) in fixtures.items():
                i=int(np.flatnonzero(np.isclose(t[:],date2num(datetime.fromisoformat(stamp),
                    units=t.units,calendar=t.calendar),rtol=0,atol=1e-9))[0])
                ds["TBOT"][i,0,0]=ta+273.15
                ds["QBOT"][i,0,0]=humidity(ta,vpd,78957.)
        result=make(original,candidate,fixtures)
        need(len(result)==3, "Self-test edits mismatch")
        wrong=dict(fixtures)
        stamp=next(iter(wrong))
        old=wrong[stamp]
        wrong[stamp]=(old[0]+5,old[1],old[2],old[3])
        try:
            make(original,root/"bad.nc",wrong)
        except ValueError:
            pass
        else:
            raise ValueError("Self-test failed to reject baseline mismatch")
    print("SELF-TEST PASS: target indices, whole-array diff and baseline mismatch guard")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--test-dir", type=Path)
    p.add_argument("--stage03b", type=Path)
    p.add_argument("--context", type=Path)
    p.add_argument("--out-dir", type=Path)
    a=p.parse_args()
    if a.self_test:
        need(a.test_dir is not None and a.test_dir.is_dir(), "Existing --test-dir required")
        self_test(a.test_dir)
        return
    need(all(x is not None for x in (a.stage03b,a.context,a.out_dir)), "Required arguments missing")
    need(a.out_dir.is_dir() and not a.out_dir.is_symlink() and not any(a.out_dir.iterdir()),
         "Output must be an existing empty directory")
    original, before_sha = input_from_report(a.stage03b)
    rows = source_rows(a.context)
    context_sha = sha(a.context)
    partial = a.out_dir/"IT-Tor_DATM_2025_F1.partial.nc"
    final = a.out_dir/"IT-Tor_DATM_2025_F1.nc"
    edits = make(original,partial,rows)
    need(sha(a.context) == context_sha and sha(original) == before_sha, "Input changed during processing")
    result={"status":"DETACHED_EXPLORATORY_NOT_RELEASED", "site":"IT-Tor",
        "baseline_path":str(original),"baseline_sha256":before_sha,
        "context_sha256":context_sha,"candidate_path":str(final),"candidate_sha256":sha(partial),
        "source_label_clock_alignment_independently_verified":False,
        "case_or_slurm_modified":False,"changes":edits}
    with (a.out_dir/"manifest_PRIVATE.json").open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2);f.write("\n")
    os.replace(partial,final)
    print("CANDIDATE:",final)
    print("SHA256:",result["candidate_sha256"])
    for edit in edits: print("EDIT",json.dumps(edit,sort_keys=True))
    print("VERIFIED: all variable arrays unchanged outside the six target values; no model submission")

if __name__=="__main__":
    main()
