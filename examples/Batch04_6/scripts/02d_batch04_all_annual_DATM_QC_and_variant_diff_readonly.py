#!/usr/bin/env python3
"""ICOS Batch04 Stage02D: all annual candidate DATM NetCDF internal QC, read-only.

Input: actual Stage02C JSON. No PFT/case/active forcing selection is made.
Full year scans of candidate site-DATM NetCDF variables, calendar/time-axis,
annual joins and cross-variant exact numerical signatures. Does NOT validate
native tower QC, ERA5 substitutions, source provenance, soil or FATES.
Only --report creates one NEW JSON; no shell commands, Slurm, CIME or writes
to original model input files. Use a Python with numpy and netCDF4.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
NC_MAX_ELEMENTS = 300000
MAX_FILES_PER_SITE = 260
CHECK_FIELDS = ("TBOT", "QBOT", "FSDS", "FLDS", "WIND", "PSRF",
                "ZBOT", "PRECTMMS", "PRECT", "PRECIP", "RH", "VPD")
REQUIRED = ("TBOT", "QBOT", "FSDS", "FLDS", "WIND", "PSRF", "ZBOT")


def validate_input(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stage") != "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC":
        raise ValueError("Input is not Stage02C JSON")
    if data.get("read_only") is not True or data.get("science_release") is not False:
        raise ValueError("Stage02C was not an unreleased read-only inventory")
    rows = data.get("sites", [])
    if tuple(x.get("site") for x in rows) != SITES:
        raise ValueError("Requires all six Stage02C station rows")
    for row in rows:
        if not isinstance(row.get("cases"), list) or not row["cases"]:
            raise ValueError("Missing source cases for " + row["site"])
        if row.get("release") != "HOLD_SOURCE_QC_STREAM_BINDING_PFT_SOIL":
            raise ValueError("Unexpected source release marker " + row["site"])
    return data


def source_paths(row):
    site = row["site"]
    pattern = re.compile(r"^" + re.escape(site) +
                         r"_DATM_((?:19|20)\d{2})(?:[_.-]|$)", re.I)
    paths = {}
    for case in row["cases"]:
        for entry in case["site_datm"]:
            path = str(entry["path"])
            name = Path(path).name
            match = pattern.match(name)
            if not match or not Path(path).is_absolute():
                raise ValueError("Unexpected site DATM path: " + path)
            year = int(match.group(1))
            if year != int(entry["year"]):
                raise ValueError("DATM year provenance discrepancy: " + path)
            if path in paths and paths[path] != year:
                raise ValueError("Conflicting year for same DATM input")
            paths[path] = year
    if not paths or len(paths) > MAX_FILES_PER_SITE:
        raise ValueError(site + ": empty or excessive candidate file set")
    return paths


def normalize_array(var, np):
    if var.size == 0 or var.size > NC_MAX_ELEMENTS:
        raise ValueError("variable size outside bounded annual point limit")
    arr = np.ma.asarray(var[:]).astype("float64")
    return np.ma.filled(arr, np.nan).reshape(-1)


def variable_summary(var, name, np):
    info = {"source_name": var.name, "units": str(getattr(var, "units", "")),
            "shape": list(var.shape), "elements": int(var.size)}
    try:
        arr = normalize_array(var, np)
        finite_mask = np.isfinite(arr)
        good = arr[finite_mask]
        info["finite"] = int(good.size)
        info["missing_or_nonfinite"] = int(arr.size - good.size)
        info["missing_pct"] = round(100 * (arr.size - good.size) / arr.size, 6)
        normalized = np.where(finite_mask, arr, np.nan).astype("<f8", copy=False)
        info["numeric_sha256"] = hashlib.sha256(normalized.tobytes()).hexdigest()
        if good.size:
            info["min"], info["max"], info["mean"] = map(float, (
                good.min(), good.max(), good.mean()))
            units = info["units"].lower().strip()
            faults = {}
            if name in ("QBOT", "PRECTMMS", "PRECT", "PRECIP", "WIND", "FSDS", "FLDS"):
                faults["negative"] = int(np.count_nonzero(good < -1e-9))
            if name == "QBOT":
                faults["outside_0_0p08_kgkg"] = int(np.count_nonzero(
                    (good < 0) | (good > 0.08)))
            if name == "TBOT" and units in ("k", "kelvin"):
                faults["outside_180_340K"] = int(np.count_nonzero(
                    (good < 180) | (good > 340)))
            if name == "PSRF" and units in ("pa", "pascal", "pascals"):
                faults["outside_40000_110000Pa"] = int(np.count_nonzero(
                    (good < 40000) | (good > 110000)))
            if name == "RH" and ("%" in units or "percent" in units):
                faults["outside_0_100pct"] = int(np.count_nonzero(
                    (good < 0) | (good > 100)))
            if name == "ZBOT":
                faults["nonpositive_height"] = int(np.count_nonzero(good <= 0))
            info["screen_flags"] = {k: v for k, v in faults.items() if v > 0}
        else:
            info["error"] = "NO_FINITE_VALUES"
    except Exception as exc:
        info["read_error"] = type(exc).__name__ + ": " + str(exc)
    return info


def time_summary(ds, year, np, num2date, date2num):
    name = next((x for x in ("time", "DTIME", "dtime", "TIME") if x in ds.variables), None)
    if name is None:
        return {"error": "NO_TIME_VARIABLE"}
    var = ds.variables[name]
    info = {"source_name": name, "elements": int(var.size),
            "units": str(getattr(var, "units", "")),
            "calendar": str(getattr(var, "calendar", "UNSPECIFIED"))}
    if var.size != 17520:
        info["expected_17520_warning"] = True
    try:
        a = normalize_array(var, np)
        mask = np.isfinite(a)
        if not np.all(mask):
            info["nonfinite_count"] = int(np.count_nonzero(~mask))
        if not len(a) or not np.all(mask):
            info["error"] = "TIME_HAS_MISSING_VALUES"
            return info
        delta = np.diff(a)
        info["nonpositive_steps"] = int(np.count_nonzero(delta <= 0))
        if delta.size:
            median = float(np.median(delta))
            info["median_numeric_step"] = median
            info["irregular_step_count"] = int(np.count_nonzero(
                ~np.isclose(delta, median, atol=max(1e-12, abs(median)*1e-6), rtol=0)))
        info["numeric_first"] = float(a[0])
        info["numeric_last"] = float(a[-1])
        calendar = info["calendar"]
        if calendar == "UNSPECIFIED":
            # Report exactly the assumption, do not falsely infer NOLEAP.
            calendar = "standard"
            info["calendar_assumption"] = "standard_default_NOT_DECLARED"
        if not info["units"] or " since " not in info["units"].lower():
            info["decode_status"] = "NO_CF_UNITS"
            return info
        first = num2date(float(a[0]), units=info["units"], calendar=calendar,
                         only_use_cftime_datetimes=True)
        last = num2date(float(a[-1]), units=info["units"], calendar=calendar,
                        only_use_cftime_datetimes=True)
        info["first_iso"] = str(first)
        info["last_iso"] = str(last)
        info["first_year"] = int(first.year)
        info["last_year"] = int(last.year)
        info["date_year_matches_filename"] = (int(first.year) == year and
                                              int(last.year) == year)
        # Common monotonically comparable reference across annual source files.
        target = "hours since 0001-01-01 00:00:00"
        info["start_hour"] = float(date2num(first, target, calendar=calendar))
        info["end_hour"] = float(date2num(last, target, calendar=calendar))
        info["calendar_used_for_hours"] = calendar
        info["decoded_cadence_hours"] = float(
            date2num(num2date(float(a[1]), units=info["units"], calendar=calendar,
                             only_use_cftime_datetimes=True),
                     target, calendar=calendar) - info["start_hour"]) if len(a) > 1 else None
    except Exception as exc:
        info["decode_error"] = type(exc).__name__ + ": " + str(exc)
    return info


def inspect(path, year, np, Dataset, num2date, date2num):
    info = {"path": path, "year_token": year, "exists": Path(path).is_file()}
    if not info["exists"]:
        info["error"] = "MISSING_FILE"
        return info
    info["bytes"] = Path(path).stat().st_size
    try:
        with Dataset(path, "r") as ds:
            info["open"] = "PASS"
            info["data_model"] = str(ds.data_model)
            info["time"] = time_summary(ds, year, np, num2date, date2num)
            canonical = {}
            for key, var in ds.variables.items():
                ku = key.upper()
                if ku in CHECK_FIELDS:
                    if ku in canonical:
                        info.setdefault("warnings", []).append("DUPLICATE_CASE_INSENSITIVE_FIELD:" + ku)
                    canonical[ku] = var
            info["all_variable_names"] = list(ds.variables)
            info["meteorology"] = {key: variable_summary(var, key, np)
                                   for key, var in canonical.items()}
            info["absent_required"] = [x for x in REQUIRED if x not in canonical]
            info["precipitation_present"] = any(x in canonical for x in
                                                 ("PRECTMMS", "PRECT", "PRECIP"))
    except Exception as exc:
        info["error"] = type(exc).__name__ + ": " + str(exc)
    return info


def summarize_site(row, np, Dataset, num2date, date2num):
    site = row["site"]
    source = source_paths(row)
    reports = [inspect(p, y, np, Dataset, num2date, date2num)
               for p, y in sorted(source.items(), key=lambda x:(x[1],x[0]))]
    records = {x["path"]: x for x in reports}
    by_year = collections.defaultdict(list)
    for f in reports:
        by_year[f["year_token"]].append(f)
    variation = {}
    for year, candidates in sorted(by_year.items()):
        if len(candidates) < 2:
            continue
        names = sorted(set(name for item in candidates
                           for name in item.get("meteorology", {})))
        diff = {}
        for name in names:
            groups = collections.defaultdict(list)
            for item in candidates:
                met = item.get("meteorology", {}).get(name, {})
                key = met.get("numeric_sha256", "MISSING_OR_UNREADABLE")
                groups[key].append(item["path"])
            if len(groups) > 1:
                diff[name] = [{"numeric_sha256": k, "files": v}
                              for k, v in groups.items()]
        if diff:
            variation[str(year)] = {"differing_fields": sorted(diff),
                                    "signatures_by_field": diff}
    by_folder = collections.defaultdict(list)
    for r in reports:
        by_folder[str(Path(r["path"]).parent)].append(r)
    seam_checks = []
    for folder, items in sorted(by_folder.items()):
        a = sorted(items, key=lambda x:x["year_token"])
        for left, right in zip(a, a[1:]):
            l, r = left.get("time", {}), right.get("time", {})
            seam = {"folder": folder, "left_year": left["year_token"],
                    "right_year": right["year_token"]}
            if right["year_token"] != left["year_token"] + 1:
                seam["status"] = "YEAR_GAP"
            elif (l.get("calendar_used_for_hours") != r.get("calendar_used_for_hours")
                  or "end_hour" not in l or "start_hour" not in r):
                seam["status"] = "NOT_COMPARABLE_CALENDAR_OR_TIME_UNDECODED"
            else:
                gap = r["start_hour"] - l["end_hour"]
                seam["gap_hours"] = round(gap, 8)
                seam["status"] = ("CONSISTENT_30MIN" if abs(gap-0.5) < 0.0005
                                  else "JOIN_GAP_OR_OVERLAP_REVIEW")
            seam_checks.append(seam)
    problems = collections.Counter()
    for f in reports:
        if f.get("open") != "PASS":
            problems["NC_OPEN_ERROR"] += 1
        t = f.get("time", {})
        if t.get("error") or t.get("decode_error") or t.get("decode_status"):
            problems["TIME_DECODE_OR_MISSING"] += 1
        if t.get("nonpositive_steps", 0) or t.get("irregular_step_count", 0):
            problems["TIME_NONMONOTONIC_OR_IRREGULAR"] += 1
        if t.get("date_year_matches_filename") is False:
            problems["TIME_YEAR_MISMATCH"] += 1
        if t.get("expected_17520_warning"):
            problems["TIME_LENGTH_NOT_17520"] += 1
        if t.get("calendar_assumption"):
            problems["UNDECLARED_CALENDAR"] += 1
        if f.get("absent_required"):
            problems["REQUIRED_MET_FIELD_MISSING"] += 1
        if f.get("precipitation_present") is False:
            problems["PRECIP_VARIABLE_NOT_FOUND"] += 1
        for name, met in f.get("meteorology", {}).items():
            if met.get("read_error") or met.get("missing_or_nonfinite", 0):
                problems[name + "_INVALID_OR_MISSING"] += 1
            if met.get("screen_flags"):
                problems[name + "_PHYSICAL_FLAG"] += 1
    for e in seam_checks:
        if e["status"] not in ("CONSISTENT_30MIN",):
            problems["YEAR_JOIN_" + e["status"]] += 1
    return {
        "site": site, "annual_file_count": len(reports),
        "all_years": sorted(by_year), "full_year_file_reports": reports,
        "cross_variant_differing_year_count": len(variation),
        "cross_variant_year_field_differences": variation,
        "year_boundary_checks": seam_checks,
        "flagged_file_counts": dict(problems),
        "status": "HOLD_DATM_INTERNAL_QC_ONLY_NO_SOURCE_TOWER_QC_OR_ACTIVE_STREAM_RELEASE",
    }


def selftest():
    assert len(SITES) == 6 and len(CHECK_FIELDS) >= 10
    assert re.match(r"^CH\-Aws_DATM_((?:19|20)\d{2})(?:[_.-]|$)",
                    "CH-Aws_DATM_2024.nc").group(1) == "2024"
    assert set(REQUIRED).issubset(set(CHECK_FIELDS))
    print("STAGE02D SELF-TEST PASS: 6 sites, annual physics/time/variant guards; no writes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stage02c", type=Path)
    p.add_argument("--sites", nargs="+", choices=SITES, default=list(SITES))
    p.add_argument("--report", type=Path, help="Exclusive-create new JSON file in existing parent")
    args = p.parse_args()
    if args.self_test:
        if args.report:
            p.error("No reports during self-test")
        selftest()
        return
    if not args.stage02c or not args.stage02c.is_file():
        p.error("--stage02c must name an existing Stage02C JSON report")
    data = validate_input(args.stage02c)
    try:
        import numpy as np
        import netCDF4
        from netCDF4 import Dataset, num2date, date2num
    except ImportError as exc:
        p.error("activate clm_fates_env with numpy and netCDF4: " + str(exc))
    print("PYTHON", sys.executable, "NUMPY", np.__version__, "NETCDF4", netCDF4.__version__)
    rows = [summarize_site(r, np, Dataset, num2date, date2num)
            for r in data["sites"] if r["site"] in args.sites]
    for r in rows:
        print("SITE", r["site"], "ANNUAL_NC", r["annual_file_count"],
              "YEARS", f"{min(r['all_years'])}-{max(r['all_years'])}",
              "VARIANT_DIFF_YEARS", r["cross_variant_differing_year_count"])
        print(" FLAGS", json.dumps(r["flagged_file_counts"], sort_keys=True))
        if r["site"] == "CH-Aws":
            for year, diff in sorted(r["cross_variant_year_field_differences"].items()):
                print(" RH_VARIANTS_YEAR", year, "DIFF_FIELDS",
                      ",".join(diff["differing_fields"]))
        failures = [x for x in r["full_year_file_reports"] if x.get("open") != "PASS"]
        for f in failures[:10]:
            print(" OPEN_HOLD", f["path"], f.get("error", "unknown"))
        for e in r["year_boundary_checks"]:
            if e["status"] != "CONSISTENT_30MIN":
                print(" JOIN_REVIEW", e["left_year"], e["right_year"],
                      e["folder"], e["status"], e.get("gap_hours"))
        print(" SCIENCE_RELEASE HOLD; native-source/ERA and stream bindings NOT checked")
    report = {
        "stage": "STAGE02D_FULL_ANNUAL_INTERNAL_DATM_QC",
        "stage02c_source": str(args.stage02c),
        "read_only": True, "slurm_submitted": False,
        "original_forcing_modified": False, "case_selected": False,
        "science_release": False,
        "limits": "Full candidate DATM annual numeric QC only; not tower source QC or FATES surface science",
        "sites": rows
    }
    if args.report:
        target = args.report.expanduser().resolve()
        if not target.parent.is_dir():
            p.error("Output parent must exist, no directory creation: " + str(target.parent))
        with target.open("x", encoding="utf-8") as out:
            json.dump(report, out, indent=2)
            out.write("\n")
        print("NEW STAGE02D REPORT:", target)
    print("READ-ONLY COMPLETE; ALL SCIENCE AND SLURM GATES REMAIN HOLD")


if __name__ == "__main__":
    main()
