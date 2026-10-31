#!/usr/bin/env python3
"""Stage02 ICOS Batch04: sample candidate forcing NetCDF and compare source-case provenance.

Read-only. Does not select a CIME template or modify any input. Optional
--report creates ONE NEW JSON file only. Sampled values are NOT full science QC.
Requires a real Stage01 report created by Stage01 on IRIDIS6.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
SITE_COUNTS_STAGE01 = {
    "CH-Aws": (8, 14), "DE-Gri": (2, 2), "DE-RuR": (2, 2),
    "IT-Tor": (2, 2), "ES-Agu": (2, 2), "GL-ZaH": (1, 5)
}
MET_NAMES = {
    "TBOT", "QBOT", "PRECTMMS", "PRECT", "FSDS", "FLDS",
    "WIND", "PSRF", "RH", "RH_F", "TA_F", "TA", "VPD",
    "VPD_F", "PRECIP", "P_F", "SW_IN", "LW_IN", "PRESS"
}
FORCING_MAX_WALK_FILES = 7000
NC_READ_MAX_ELEMENTS = 250000
DATA_LIST_MAX_LINES = 30000


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def report_stage01(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("sites")
    if data.get("batch") != "ICOS_BATCH04_SIX" or not data.get("inspection_only"):
        raise ValueError("not the expected read-only ICOS Batch04 Stage01 report")
    if not isinstance(rows, list):
        raise ValueError("Stage01 sites is not an array")
    found = [r.get("site") for r in rows]
    if len(found) != 6 or tuple(found) != SITES:
        raise ValueError("Stage01 site coverage differs from the exact six sites")
    if not data.get("source_register_sha256") or not data.get("gate_register_sha256"):
        raise ValueError("Stage01 lacks source/gate provenance")
    return data, {r["site"]: r for r in rows}


def source_refs(path):
    out = {"exists": path.is_file(), "path": str(path)}
    if not path.is_file():
        return out
    if path.stat().st_size > 3000000:
        out["status"] = "SKIPPED_LARGE_DATA_LIST"
        return out
    lines = path.read_text(errors="replace").splitlines()
    out["sha256"] = digest(path)
    out["total_lines"] = len(lines)
    if len(lines) > DATA_LIST_MAX_LINES:
        out["status"] = "TOO_MANY_LINES"
        return out
    references = []
    for row in lines:
        if ".nc" in row.lower() or ".xml" in row.lower():
            references.append(row.strip()[:450])
    out["nc_or_xml_reference_lines"] = references[:25]
    out["reference_lines_total"] = len(references)
    out["scope"] = "INPUT_DATA_LIST_CANDIDATES_NOT_CONFIRMED_ACTIVE_STREAM"
    return out


def metadata_case(case, from_stage01):
    record = {"case": case.name, "case_path": str(case), "exists": case.is_dir()}
    if not case.is_dir():
        record["status"] = "MISSING_CASE"
        return record
    docs = case / "CaseDocs"
    record["datm_list"] = source_refs(case / "Buildconf/datm.input_data_list")
    record["land_file"] = str(docs / "lnd_in")
    record["datm_file"] = str(docs / "datm_in")
    record["static_xml_stage01"] = from_stage01.get("xml", {})
    record["point_check_stage01"] = from_stage01.get("point_check", "UNVERIFIED")
    record["effective_namelists_from_stage01"] = {
        "land": from_stage01.get("land", {}),
        "datm": from_stage01.get("datm", {})
    }
    record["stream_documents"] = []
    if docs.is_dir():
        for path in sorted(docs.glob("*stream*"))[:25]:
            if path.is_file():
                row = {"path": str(path), "bytes": path.stat().st_size}
                if path.stat().st_size <= 2000000:
                    text = path.read_text(errors="replace")
                    row["sha256"] = digest(path)
                    # Keep only structural / first lines rather than full XML.
                    row["excerpt"] = [x.strip()[:400] for x in text.splitlines()[:18]]
                    row["years_mentions"] = sorted(set(re.findall(
                        r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)))[:40]
                else:
                    row["status"] = "STREAM_TOO_LARGE"
                record["stream_documents"].append(row)
    return record


def walk_netcdf(folder):
    found = []
    truncated = False
    if folder.is_dir():
        for root, dirs, files in os.walk(folder, topdown=True, followlinks=False):
            # Some forcing folders contain symlinked archived subtrees;
            # never chase them.
            dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
            for fname in sorted(files):
                if fname.lower().endswith(".nc"):
                    p = Path(root) / fname
                    if p.is_file():
                        found.append(p)
                        if len(found) >= FORCING_MAX_WALK_FILES:
                            truncated = True
                            break
            if truncated:
                break
    return sorted(found), truncated


def sample_netcdf(path):
    result = {"path": str(path), "exists": path.is_file()}
    if not result["exists"]:
        return result
    result["bytes"] = path.stat().st_size
    result["source_sha256"] = "NOT_HASHED_FOR_LARGE_MET_FILE"
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        result["read_error"] = "Need clm_fates_env/netCDF4/numpy: " + str(exc)
        return result
    try:
        with Dataset(str(path), "r") as ds:
            result["dimensions"] = {key: len(dim) for key, dim in ds.dimensions.items()}
            result["calendar"] = "UNVERIFIED_UNLESS_TIME_HAS_CALENDAR"
            for key in ("time", "DTIME", "dtime", "TIME"):
                var = ds.variables.get(key)
                if var is None:
                    continue
                t = {"name": key, "units": getattr(var, "units", None),
                     "calendar": getattr(var, "calendar", None),
                     "elements": int(var.size)}
                if var.size <= NC_READ_MAX_ELEMENTS:
                    x = np.ma.filled(np.ma.asarray(var[:]).astype(float), np.nan).reshape(-1)
                    finite = x[np.isfinite(x)]
                    if len(finite):
                        t["numeric_first"] = float(finite[0])
                        t["numeric_last"] = float(finite[-1])
                        t["finite_count"] = int(len(finite))
                        if len(finite) > 1:
                            d = np.diff(finite)
                            t["nonincreasing_steps"] = int(np.sum(d <= 0))
                            t["median_numeric_step"] = float(np.median(d))
                    else:
                        t["status"] = "ALL_MISSING_OR_NONNUMERIC"
                else:
                    t["status"] = "TIME_TOO_LONG_FOR_SAMPLE"
                result["time"] = t
                break
            result["meteorology"] = {}
            for key, var in ds.variables.items():
                upper = key.upper()
                if upper not in MET_NAMES:
                    continue
                info = {"units": str(getattr(var, "units", "")),
                        "dimensions": list(var.dimensions),
                        "elements": int(var.size)}
                if not var.size or var.size > NC_READ_MAX_ELEMENTS:
                    info["status"] = "NOT_READ_SIZE_LIMIT"
                    result["meteorology"][key] = info
                    continue
                try:
                    data = np.ma.filled(np.ma.asarray(var[:]).astype(float), np.nan)
                    finite = data[np.isfinite(data)]
                    info["finite_count"] = int(finite.size)
                    info["missing_or_nonfinite_count"] = int(data.size - finite.size)
                    info["missing_percent"] = round(100 * (data.size - finite.size) / data.size, 5)
                    if finite.size:
                        info["min"] = float(finite.min())
                        info["max"] = float(finite.max())
                        info["mean"] = float(finite.mean())
                        unit = info["units"].lower()
                        if upper in ("QBOT", "PRECTMMS", "PRECT", "P_F", "PRECIP"):
                            info["negative_count"] = int(np.sum(finite < -1e-12))
                        if upper in ("RH", "RH_F") and ("%" in unit or "percent" in unit):
                            info["outside_0_100_count"] = int(np.sum((finite < 0) | (finite > 100)))
                        if upper in ("TBOT", "TA", "TA_F") and unit in ("k", "kelvin"):
                            info["outside_180_340K_count"] = int(np.sum(
                                (finite < 180) | (finite > 340)))
                    else:
                        info["status"] = "NO_FINITE_VALUES"
                except (TypeError, ValueError, OSError, IndexError) as exc:
                    info["read_error"] = str(exc)
                result["meteorology"][key] = info
            if not result["meteorology"]:
                result["warning"] = "NO_RECOGNISED_MET_VARIABLES_CHECK_SOURCE"
    except Exception as exc:
        result["read_error"] = type(exc).__name__ + ": " + str(exc)
    return result


def audit_site(base, row, max_sample):
    site = row["site"]
    root = base / "sites/MY_EC_SITE" / site / "forcing"
    inputs = row.get("source_case_candidates", [])
    candidate_cases = []
    case_base = base / "cases"
    for entry in inputs:
        name = entry.get("case", "")
        if not name.startswith(site + "_") or "/" in name or "\\" in name:
            raise ValueError("Invalid case name in Stage01 report: " + name)
        candidate_cases.append(metadata_case(case_base / name, entry))
    candidate_dirs = []
    for dirname in row.get("forcing_dir_candidates", []):
        if "/" in dirname or "\\" in dirname or dirname in (".", ".."):
            raise ValueError("Invalid Stage01 forcing directory name: " + dirname)
        folder = root / dirname
        paths, cut = walk_netcdf(folder)
        indices = ([0] if max_sample == 1 else
                   [0, len(paths)-1] if max_sample == 2 else
                   [0, len(paths)//2, len(paths)-1] if max_sample == 3
                   else []) if paths else []
        selected = [paths[i] for i in dict.fromkeys(indices)]
        candidate_dirs.append({
            "name": dirname, "path": str(folder),
            "nc_file_count_discovered": len(paths), "listing_truncated": cut,
            "observed_year_tokens_in_filenames": sorted(set(
                year for p in paths for year in re.findall(
                    r"(?<!\d)(?:19|20)\d{2}(?!\d)", p.name)))[:200],
            "first_file": str(paths[0]) if paths else None,
            "last_file": str(paths[-1]) if paths else None,
            "sampled_netcdf": [sample_netcdf(p) for p in selected],
            "binding_status": "UNVERIFIED_ACTIVE_CIME_DATM_STREAM",
        })
    return {
        "site": site, "source_case_count": len(candidate_cases),
        "candidate_forcing_folder_count": len(candidate_dirs),
        "case_provenance": candidate_cases,
        "forcing_folders": candidate_dirs,
        "selection": "HOLD_NO_AUTOMATIC_CASE_SELECTION",
        "source_vs_ERA_QC": "NOT_PERFORMED",
        "full_forcing_annual_HH_QC": "NOT_PERFORMED",
        "soil_science": "NOT_RELEASED",
        "surface_PFT_science": "NOT_RELEASED",
        "next_gate": "COMPARE_CASE_STREAMS_THEN_NATIVE_SOURCE_FULL_HH_QC",
    }


def selftest():
    assert set(SITES) == set(SITE_COUNTS_STAGE01)
    assert sum(v[0] for v in SITE_COUNTS_STAGE01.values()) == 17
    assert sum(v[1] for v in SITE_COUNTS_STAGE01.values()) == 27
    assert re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", "DE-Gri_2018.nc") == ["2018"]
    assert re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", "abc2018000.nc") == []
    print("STAGE02 SELF-TEST PASS: 6 sites, 17 original case candidates, 27 forcing folders; no I/O writes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stage01", type=Path, help="Existing Stage01 JSON inventory")
    p.add_argument("--base", type=Path, help="Override report's CLM_FATES base")
    p.add_argument("--sites", nargs="+", choices=SITES, default=list(SITES))
    p.add_argument("--max-samples-per-dir", type=int, choices=(0, 1, 2, 3),
                   default=2)
    p.add_argument("--report", type=Path, help="New JSON report, must not exist")
    args = p.parse_args()
    if args.self_test:
        if args.report or args.stage01:
            p.error("self-test accepts no stage01/report")
        selftest()
        return
    if not args.stage01 or not args.stage01.is_file():
        p.error("--stage01 must name an existing Stage01 report")
    source, by_site = report_stage01(args.stage01)
    base = args.base or Path(source["base"])
    if not base.is_dir():
        p.error("CLM_FATES base missing: " + str(base))
    results = [audit_site(base, by_site[site], args.max_samples_per_dir)
               for site in dict.fromkeys(args.sites)]
    report = {
        "stage": "STAGE02_CANDIDATE_SOURCE_FORCING_SAMPLES",
        "read_only": True, "model_submitted": False,
        "source_case_selected": False, "scientific_release": False,
        "stage01_path": str(args.stage01), "stage01_sha256": digest(args.stage01),
        "base": str(base), "sample_limit": args.max_samples_per_dir,
        "sampling_caveat": "Only candidate directories and a few files are sampled; active DATM files and full source-QC remain unverified.",
        "sites": results,
    }
    for row in results:
        print(row["site"], "CASE_CANDIDATES", row["source_case_count"],
              "FORCING_DIRS", row["candidate_forcing_folder_count"],
              "HOLD_ACTIVE_STREAM_AND_FULL_HH_QC")
        for case in row["case_provenance"]:
            print("  CASE", case["case"], "POINT", case.get("point_check_stage01"),
                  "DATM_REF_LINES", case["datm_list"].get("reference_lines_total", "NA"))
        for folder in row["forcing_folders"]:
            print("  FORCING", folder["name"], "NC", folder["nc_file_count_discovered"],
                  "SAMPLED", len(folder["sampled_netcdf"]),
                  "TRUNCATED", folder["listing_truncated"])
            for sampled in folder["sampled_netcdf"]:
                flags = []
                if sampled.get("read_error"):
                    flags.append("READ_ERROR")
                t = sampled.get("time", {})
                if t.get("nonincreasing_steps", 0):
                    flags.append("NONMONOTONIC_TIME")
                for met, info in sampled.get("meteorology", {}).items():
                    if info.get("missing_percent", 0):
                        flags.append(met + "_MISSING=" + str(info["missing_percent"]) + "%")
                    for key in ("negative_count", "outside_0_100_count",
                                "outside_180_340K_count"):
                        if info.get(key, 0):
                            flags.append(met + "_" + key + "=" + str(info[key]))
                print("    SAMPLE", Path(sampled["path"]).name,
                      "TIME_COUNT", t.get("elements", "NA"),
                      "FLAGS", ",".join(flags[:15]) if flags else "NO_CHECKED_FLAGS")

    if args.report:
        output = args.report.expanduser().resolve()
        if not output.parent.is_dir():
            p.error("Report parent directory does not exist: " + str(output.parent))
        with output.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        print("NEW STAGE02 REPORT:", output)
    print("NO MODEL JOBS; NO MODIFIED INPUTS; ALL SITES REMAIN HOLD.")


if __name__ == "__main__":
    main()
