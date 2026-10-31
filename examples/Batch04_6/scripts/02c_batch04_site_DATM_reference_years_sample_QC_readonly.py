#!/usr/bin/env python3
"""ICOS Batch04 Stage02C — original-case DATM annual references and bounded numerical QC.

READ ONLY. Source is the operator's actual Stage02B JSON; no source-case selection.
A CIME input_data_list entry is a candidate reference, NOT proof of the active
DATM stream. All annual paths are inventoried, and first/last NC per distinct
directory are sampled by default. Use --samples-per-directory 0 to assess all.
Only --report writes ONE NEW JSON, with exclusive creation.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
EXPECTED_CASES = (8, 2, 2, 2, 2, 1)
FIELDS = ("TBOT", "QBOT", "PRECTMMS", "FSDS", "FLDS", "WIND", "PSRF",
          "ZBOT", "RH", "VPD")
MAX_ELEMENTS_PER_VARIABLE = 250000


def read_stage02b(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stage") != "STAGE02B_EXPLAIN_ERRORS_AND_TRACE_CIME_NC_PATHS":
        raise ValueError("Input is not a Stage02B JSON")
    rows = data.get("sites", [])
    if tuple(x.get("site") for x in rows) != SITES:
        raise ValueError("Input must include all six Stage02B sites in order")
    if not data.get("read_only") or data.get("scientific_release") is not False:
        raise ValueError("Stage02B provenance did not pass")
    for row, count in zip(rows, EXPECTED_CASES):
        if len(row.get("original_CIME_candidate_refs", [])) != count:
            raise ValueError("Unexpected number of original CIME cases for " + row["site"])
    return data


def extract_site_datm(site, references):
    # Input list includes aerosol/deposition/surface data. Only files with
    # the exact <site>_DATM_<YYYY> prefix are considered meteorological here.
    pattern = re.compile(r"^" + re.escape(site) + r"_DATM_((?:19|20)\d{2})(?:[_.-]|$)", re.I)
    selected = []
    for obj in references:
        path = obj.get("path", "")
        if not isinstance(path, str) or not Path(path).is_absolute():
            continue
        match = pattern.match(Path(path).name)
        if match:
            selected.append({"year": int(match.group(1)), "path": path,
                             "exists_in_stage02b": obj.get("exists"),
                             "exists_now": Path(path).is_file()})
    return sorted(selected, key=lambda x: (x["year"], x["path"]))


def annual_case(case, site):
    entry = case.get("datm_references", {})
    all_refs = entry.get("absolute_NC_paths", [])
    selected = extract_site_datm(site, all_refs)
    years = sorted(set(x["year"] for x in selected))
    missing_years = list(range(years[0], years[-1]+1)) if years else []
    missing_years = sorted(set(missing_years) - set(years))
    duplicate_years = sorted(y for y, n in collections.Counter(x["year"] for x in selected).items() if n != 1)
    return {
        "case": case.get("case", ""), "listed_paths_total": entry.get("absolute_NC_path_count"),
        "path_list_truncated": entry.get("paths_truncated", False),
        "site_datm_count": len(selected), "year_first": min(years) if years else None,
        "year_last": max(years) if years else None, "years": years,
        "year_gaps": missing_years, "duplicate_years": duplicate_years,
        "missing_paths": [x["path"] for x in selected if not x["exists_now"]],
        "site_datm": selected, "stream_binding": "UNVERIFIED",
    }


def choose_paths(paths, per_directory):
    grouped = collections.defaultdict(list)
    for p in sorted(set(paths)):
        grouped[str(Path(p).parent)].append(p)
    picked = []
    for folder, items in sorted(grouped.items()):
        if per_directory == 0:
            chosen = items
        elif per_directory == 1:
            chosen = items[:1]
        elif per_directory == 2:
            chosen = [items[0], items[-1]]
        else:
            chosen = [items[0], items[len(items)//2], items[-1]]
        for p in dict.fromkeys(chosen):
            picked.append(p)
    return picked, {folder: len(items) for folder, items in grouped.items()}


def open_summary(path, np, Dataset):
    out = {"path": path, "exists": Path(path).is_file()}
    if not out["exists"]:
        return out
    out["bytes"] = Path(path).stat().st_size
    try:
        with Dataset(path, "r") as ds:
            out["open"] = "PASS"
            out["data_model"] = ds.data_model
            out["dimensions"] = {k: len(v) for k, v in ds.dimensions.items()}
            time_var = next((ds.variables[k] for k in ("time", "DTIME", "dtime", "TIME")
                             if k in ds.variables), None)
            if time_var is not None:
                time_info = {"n": int(time_var.size),
                             "units": str(getattr(time_var, "units", "")),
                             "calendar": str(getattr(time_var, "calendar", "UNSPECIFIED"))}
                if 0 < time_var.size <= MAX_ELEMENTS_PER_VARIABLE:
                    try:
                        arr = np.ma.filled(np.ma.asarray(time_var[:]).astype("float64"), np.nan).ravel()
                        finite = arr[np.isfinite(arr)]
                        if finite.size:
                            time_info["first"] = float(finite[0])
                            time_info["last"] = float(finite[-1])
                            if finite.size > 1:
                                deltas = np.diff(finite)
                                time_info["nonpositive_steps"] = int(np.sum(deltas <= 0))
                                time_info["min_step"] = float(np.min(deltas))
                                time_info["max_step"] = float(np.max(deltas))
                    except Exception as exc:
                        time_info["read_error"] = type(exc).__name__ + ": " + str(exc)
                out["time"] = time_info
            else:
                out["time"] = {"status": "NO_IDENTIFIED_TIME_VARIABLE"}
            out["meteorology"] = {}
            for key in FIELDS:
                if key not in ds.variables:
                    continue
                var = ds.variables[key]
                info = {"units": str(getattr(var, "units", "")),
                        "shape": list(var.shape), "elements": int(var.size)}
                if var.size > MAX_ELEMENTS_PER_VARIABLE or var.size == 0:
                    info["status"] = "NOT_READ_SIZE_LIMIT"
                    out["meteorology"][key] = info
                    continue
                try:
                    a = np.ma.filled(np.ma.asarray(var[:]).astype("float64"), np.nan).ravel()
                    finite = a[np.isfinite(a)]
                    info["n_finite"] = int(finite.size)
                    info["missing_nonfinite"] = int(a.size - finite.size)
                    if finite.size:
                        info["min"] = float(finite.min())
                        info["max"] = float(finite.max())
                        unit = info["units"].strip().lower()
                        if key in ("QBOT", "PRECTMMS") and (finite < -1e-12).any():
                            info["negative_values"] = int(np.sum(finite < -1e-12))
                        if key == "RH" and ("%" in unit or "percent" in unit):
                            info["outside_0_100_percent"] = int(np.sum((finite < 0) | (finite > 100)))
                        if key == "TBOT" and unit in ("k", "kelvin"):
                            info["outside_180_340_kelvin"] = int(np.sum((finite < 180) | (finite > 340)))
                        if key == "PSRF" and unit in ("pa", "pascal", "pascals"):
                            info["outside_40000_110000_pascal"] = int(np.sum(
                                (finite < 40000) | (finite > 110000)))
                    else:
                        info["status"] = "NO_FINITE_VALUES"
                except Exception as exc:
                    info["read_error"] = type(exc).__name__ + ": " + str(exc)
                out["meteorology"][key] = info
            if not out["meteorology"]:
                out["warning"] = "NONE_OF_THE_EXPECTED_MET_FIELDS_PRESENT"
    except Exception as exc:
        out["open_error"] = type(exc).__name__ + ": " + str(exc)
    return out


def site_audit(row, np, Dataset, per_directory):
    site = row["site"]
    cases = [annual_case(c, site) for c in row["original_CIME_candidate_refs"]]
    paths = [entry["path"] for case in cases for entry in case["site_datm"]]
    selected, folder_counts = choose_paths(paths, per_directory)
    signatures = collections.defaultdict(list)
    for c in cases:
        sig = tuple((x["year"], x["path"]) for x in c["site_datm"])
        signatures[str(sig)].append(c["case"])
    samples = [open_summary(p, np, Dataset) for p in selected]
    issues = []
    for c in cases:
        if not c["site_datm_count"]:
            issues.append(c["case"] + ":NO_SITE_DATM_IN_INPUT_LIST")
        if c["path_list_truncated"]:
            issues.append(c["case"] + ":SOURCE_LIST_TRUNCATED")
        if c["year_gaps"]:
            issues.append(c["case"] + ":YEAR_GAPS=" + str(c["year_gaps"]))
        if c["duplicate_years"]:
            issues.append(c["case"] + ":MULTIPLE_FILES_PER_YEAR")
        if c["missing_paths"]:
            issues.append(c["case"] + ":MISSING_REFERENCED_NETCDF")
    if len(signatures) > 1:
        issues.append("CASE_VARIANTS_REFERENCE_DIFFERENT_DATM_PATHS")
    for x in samples:
        if x.get("open") != "PASS":
            issues.append("NC_OPEN_HOLD:" + x["path"])
        if x.get("time", {}).get("nonpositive_steps", 0) > 0:
            issues.append("NONMONOTONIC_TIME:" + x["path"])
        if x.get("time", {}).get("read_error"):
            issues.append("TIME_READ_HOLD:" + x["path"])
        for name, f in x.get("meteorology", {}).items():
            if f.get("read_error") or f.get("status") == "NO_FINITE_VALUES":
                issues.append(name + "_READ_HOLD:" + x["path"])
            if f.get("negative_values") or f.get("outside_0_100_percent") or f.get("outside_180_340_kelvin") or f.get("outside_40000_110000_pascal"):
                issues.append(name + "_PHYSICAL_SCREEN:" + x["path"])
    return {
        "site": site, "cases": cases,
        "distinct_case_datm_path_sets": len(signatures),
        "case_groups_with_identical_input_lists": list(signatures.values()),
        "distinct_site_datm_files": len(set(paths)), "candidate_datm_roots": folder_counts,
        "sampled_file_count": len(samples), "sampled_file_reports": samples,
        "issues_to_review": issues,
        "release": "HOLD_SOURCE_QC_STREAM_BINDING_PFT_SOIL",
        "study_limitations": "CIME input lists are candidate paths, not proof of bound DATM stream; no native source/ERA comparisons",
    }


def selftest():
    assert tuple(EXPECTED_CASES) == (8, 2, 2, 2, 2, 1)
    ref = {"path": "/x/DE-Gri_DATM_2004_PROVISIONAL.nc", "exists": True}
    assert extract_site_datm("DE-Gri", [ref])[0]["year"] == 2004
    assert not extract_site_datm("DE-RuR", [ref])
    assert not extract_site_datm("DE-Gri", [{"path": "/x/aerosoldep_WACCM_2015.nc"}])
    sample, roots = choose_paths(["/a/2001.nc", "/a/2002.nc", "/b/2003.nc"], 2)
    assert len(sample) == 3 and roots["/a"] == 2
    print("STAGE02C SELF-TEST PASS: exact six sites; site DATM year paths; no writes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stage02b", type=Path)
    p.add_argument("--samples-per-directory", type=int, choices=(0, 1, 2, 3), default=2)
    p.add_argument("--report", type=Path, help="New JSON path, parent must exist")
    args = p.parse_args()
    if args.self_test:
        if args.report:
            p.error("self-test cannot write report")
        selftest()
        return
    if not args.stage02b or not args.stage02b.is_file():
        p.error("--stage02b must reference the verified Stage02B JSON")
    data = read_stage02b(args.stage02b)
    try:
        import numpy as np
        from netCDF4 import Dataset
        import netCDF4
    except ImportError as exc:
        p.error("Activate a Python environment with numpy+netCDF4: " + str(exc))
    print("PYTHON", sys.executable, "NUMPY", np.__version__, "NETCDF4", netCDF4.__version__)
    rows = [site_audit(row, np, Dataset, args.samples_per_directory) for row in data["sites"]]
    for row in rows:
        print("SITE", row["site"], "CASES", len(row["cases"]),
              "DATM_UNIQUE_FILES", row["distinct_site_datm_files"],
              "PATH_SET_VARIANTS", row["distinct_case_datm_path_sets"],
              "SAMPLED", row["sampled_file_count"])
        for case in row["cases"]:
            print(" CASE", case["case"], "DATM_NC", case["site_datm_count"],
                  "YEARS", f"{case['year_first']}-{case['year_last']}",
                  "GAPS", len(case["year_gaps"]), "MISSING", len(case["missing_paths"]))
        for sample in row["sampled_file_reports"]:
            t = sample.get("time", {})
            met = sample.get("meteorology", {})
            flags = []
            if sample.get("open") != "PASS": flags.append("OPEN_ERROR")
            if t.get("nonpositive_steps"): flags.append("TIME_NONMONOTONIC")
            for k, v in met.items():
                if v.get("missing_nonfinite"): flags.append(k + "_MISSING:" + str(v["missing_nonfinite"]))
                if v.get("negative_values"): flags.append(k + "_NEGATIVE:" + str(v["negative_values"]))
                if v.get("outside_0_100_percent"): flags.append(k + "_RH_OUTSIDE_100")
                if v.get("outside_180_340_kelvin"): flags.append(k + "_T_OUTSIDE_RANGE")
            print(" SAMPLE", Path(sample["path"]).name, "OPEN", sample.get("open", sample.get("open_error")),
                  "TIME_N", t.get("n"), "MET", ",".join(met), "FLAGS", ",".join(flags[:10]) or "NONE_SCREENED")
        for issue in row["issues_to_review"][:25]:
            print(" REVIEW", issue)
        print(" SCIENCE_RELEASE HOLD")
    output = {
        "stage": "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC",
        "source_stage02b": str(args.stage02b),
        "science_release": False, "read_only": True, "slurm_submitted": False,
        "input_modified": False, "candidate_case_auto_selected": False,
        "python_executable": sys.executable, "numpy_version": np.__version__,
        "netcdf4_version": netCDF4.__version__, "samples_per_directory": args.samples_per_directory,
        "sites": rows
    }
    if args.report:
        path = args.report.expanduser().resolve()
        if not path.parent.is_dir(): p.error("Report parent directory does not exist: " + str(path.parent))
        with path.open("x", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            f.write("\n")
        print("NEW STAGE02C REPORT:", path)
    print("SOURCE/CASES/SLURM UNCHANGED; NO METEOROLOGY SCIENCE APPROVAL")


if __name__ == "__main__":
    main()
