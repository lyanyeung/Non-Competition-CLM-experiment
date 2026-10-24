#!/usr/bin/env python3
"""Batch01 Stage03: READ ONLY audit of candidate PFT mixtures and source surfaces.

Reads Stage02 case_trace.json and the *model scenario* CSV, not the raw field
evidence CSV. Checks source fsurdat, host landunits, conditional natural-PFT
fractions and source soil texture. NEVER builds/writes surfaces, changes CIME,
submits Slurm, or changes old cases. Reports go only to a new HOME directory.

Usage:
  python3 -B examples/Batch01_10/scripts/03_audit_surface_soil_pft.py --self-test
  python3 -B examples/Batch01_10/scripts/03_audit_surface_soil_pft.py \
    --case-trace "$HOME/Batch01_10_stage02_case_trace_YYYYMMDDTHHMMSSZ/case_trace.json"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "data/batch01_10_pft_scenarios.csv"
SITES = ("CZ-BK1", "IT-Ren", "RU-Fyo", "CH-Dav", "IT-Col",
         "FR-Fon", "FI-Sod", "FR-Pue", "DE-Hai", "BE-Vie")
GROUPS = ("ENF", "DNF", "DBF", "EBF")
SURFACE_FIELDS = ("PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT",
                  "PCT_SAND", "PCT_CLAY", "PCT_LAKE",
                  "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")


def fail(message):
    raise RuntimeError(str(message))


def sha256(path: Path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(part)
    return hasher.hexdigest()


def scenario_rows():
    if not SCENARIOS.is_file():
        fail("Missing model-only scenario table: " + str(SCENARIOS))
    with SCENARIOS.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if tuple(row.get("site") for row in rows) != SITES or len(rows) != 10:
        fail("Scenario list must have exactly the ten ordered Batch01 sites")
    expected = {row["site"]: row for row in rows}
    for row in rows:
        numbers = [float(row[g]) for g in GROUPS]
        if any(not math.isfinite(v) or v < 0 or v > 100 for v in numbers):
            fail("Nonfinite/out-of-range tree PFT fraction: " + row["site"])
        if abs(sum(numbers) - 100) > 1e-8:
            fail("Tree PFT group total not 100: " + row["site"])
        if row.get("scenario_status") != "CANDIDATE_HOLD_SURFACE":
            fail("Scenario status unexpectedly changed: " + row["site"])
    assert expected["FI-Sod"]["ENF"] == "100"
    assert expected["BE-Vie"]["ENF"] == "64"
    assert expected["FR-Pue"]["EBF"] == "95"
    return expected


def clean_path(value):
    if not isinstance(value, str):
        return None
    value = value.strip().strip("'\"").strip()
    if not value.startswith("/") or "\n" in value:
        return None
    return str(Path(value))


def case_surface_paths(case):
    """Enumerate, but DO NOT select a preferred source case/surface."""
    found = []
    old = clean_path(case.get("stage01_fsurdat"))
    if old:
        found.append(("stage01_lnd_in", old))
    for tag in ("runtime_docs", "case_docs"):
        for doc in case.get(tag, []):
            if not doc.get("present"):
                continue
            val = clean_path(doc.get("values", {}).get("fsurdat"))
            if val:
                found.append((tag + ":" + str(doc.get("path", "")), val))
    result = []
    seen = set()
    for source, path in found:
        if path not in seen:
            seen.add(path)
            result.append({"discovered_via": source, "path": path})
    return result


def netcdf_review(path):
    """Only read a source file. Never write, copy or open in append mode."""
    answer = {"source_path": str(path), "exists": path.is_file(),
              "checked_with": "READ_ONLY"}
    if not path.is_file():
        answer["error"] = "MISSING_SOURCE_SURFACE"
        return answer
    answer["bytes"] = path.stat().st_size
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        answer["error"] = "NETCDF4_OR_NUMPY_NOT_AVAILABLE: " + str(exc)
        return answer
    try:
        with Dataset(str(path), mode="r") as ds:
            answer["dimensions"] = {k: len(v) for k, v in ds.dimensions.items()}
            values = {}
            for name in SURFACE_FIELDS:
                if name not in ds.variables:
                    continue
                variable = ds.variables[name]
                entry = {"shape": list(variable.shape),
                         "dimensions": list(variable.dimensions),
                         "units": str(getattr(variable, "units", ""))}
                if variable.size > 100000:
                    entry["status"] = "LARGE_FIELD_NOT_MATERIALIZED"
                    values[name] = entry
                    continue
                try:
                    a = np.asarray(np.ma.filled(variable[:], np.nan),
                                   dtype="float64").ravel()
                    finite = a[np.isfinite(a)]
                    entry["sample_first_12"] = [float(v) if math.isfinite(v) else None
                                               for v in a[:12]]
                    if finite.size:
                        entry["min"] = float(finite.min())
                        entry["max"] = float(finite.max())
                        entry["n_finite"] = int(finite.size)
                    if name == "PCT_NAT_PFT":
                        # Sum only a single vector; multi-cell arrays cannot be
                        # safely flattened and treated as a 100% single point.
                        if a.size in range(10, 33) and finite.size == a.size:
                            entry["single_point_conditional_pft_sum"] = float(a.sum())
                        else:
                            entry["pft_sum_status"] = "AMBIGUOUS_SIZE_OR_MASK"
                    if name in ("PCT_SAND", "PCT_CLAY"):
                        entry["layer1_candidate"] = (
                            float(a[0]) if a.size and math.isfinite(a[0]) else None)
                        entry["caveat"] = "SOURCE_GRID_INPUT_NOT_FIELD_VALIDATED"
                except Exception as exc:
                    entry["read_error"] = repr(exc)
                values[name] = entry
            answer["fields"] = values
            answer["read_status"] = "READ_OK"
    except Exception as exc:
        answer["error"] = "NETCDF_READ_ERROR: " + repr(exc)
    return answer


def input_report(path):
    if path.name != "case_trace.json" or not path.parent.name.startswith(
            "Batch01_10_stage02_case_trace_"):
        fail("Use the original Stage02 case_trace.json inside its timestamped directory")
    if not path.is_file():
        fail("Stage02 report does not exist: " + str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("files_changed_outside_new_report") is not False or (
            data.get("slurm_submitted") is not False):
        fail("Stage02 provenance/safety flags invalid")
    if tuple(row.get("site") for row in data.get("sites", [])) != SITES:
        fail("Stage02 does not have exactly the Batch01 ten sites in order")
    return data


def inspect_site(site_data, scenario):
    site = site_data["site"]
    cases = site_data.get("cases", [])
    refs = []
    for case in cases:
        refs.append({
            "case": case.get("case"),
            "path": case.get("path"),
            "case_path_check": case.get("case_path_check"),
            "run_configuration": case.get("source_case_config", {}),
            "sources": case_surface_paths(case),
            "case_fsurdat_exists_stage02": case.get("case_fsurdat_exists"),
        })
    available = {}
    for case in refs:
        for source in case["sources"]:
            available[source["path"]] = source
    for entry in site_data.get("stage01_candidate_surfaces", []):
        candidate = clean_path(entry.get("path"))
        if candidate and candidate not in available:
            available[candidate] = {"discovered_via": "stage01_surface_candidate",
                                    "path": candidate}
    # Avoid large/read-many source files, while showing all discovered path names.
    previews = [netcdf_review(Path(p)) for p in list(available)[:12]]
    issues = []
    if len(cases) == 0:
        issues.append("NO_ORIGINAL_CIME_CASE")
    if len(cases) > 1:
        issues.append("MULTIPLE_BASELINE_CASES_MANUAL_SELECTION_REQUIRED")
    if any(case["case_path_check"] != "PASS" for case in refs):
        issues.append("INVALID_CASE_PATH")
    if not available:
        issues.append("NO_SOURCE_FSURDAT_FOUND")
    if not any(p.get("read_status") == "READ_OK" for p in previews):
        issues.append("NO_READABLE_SOURCE_SURFACE")
    for surface in previews:
        f = surface.get("fields", {})
        nat = f.get("PCT_NATVEG", {}).get("sample_first_12", [])
        crop = f.get("PCT_CROP", {}).get("sample_first_12", [])
        if nat and nat[0] is not None and nat[0] < 99.999:
            issues.append("NATURAL_LANDUNIT_NOT_100_REVIEW_AREA")
        if crop and crop[0] is not None and crop[0] > 0.001:
            issues.append("NONZERO_CROP_FRACTION_REVIEW")
        pft_sum = f.get("PCT_NAT_PFT", {}).get(
            "single_point_conditional_pft_sum")
        if pft_sum is not None and abs(pft_sum - 100) > 0.01:
            issues.append("HOST_NAT_PFT_NOT_100_REVIEW")
        if ("PCT_SAND" not in f) or ("PCT_CLAY" not in f):
            issues.append("SOURCE_SOIL_TEXTURE_FIELDS_MISSING_OR_UNREADABLE")
    return {
        "site": site,
        "candidate_tree_pft_pct": {g: float(scenario[g]) for g in GROUPS},
        "scenario_basis": scenario["scenario_basis"],
        "scenario_status": scenario["scenario_status"],
        "cases": refs,
        "discovered_surface_paths": list(available),
        "surface_reviews": previews,
        "issues": sorted(set(issues)),
        "scientific_gate": "HOLD_NOT_A_PRODUCTION_SURFACE",
        "next_science_decisions": [
            "Choose and verify original CIME source case and forcing/calendar",
            "Distinguish conditional tree-PFT assumption from horizontal landunit area",
            "Validate field-measured soil sand/silt/clay and sampling depth or document grid fallback",
            "Check FATES HLM-PFT mapping against case executable and prescribed-biogeography implementation",
            "Approve new versioned surface only after explicit human review",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-trace", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    scenarios = scenario_rows()
    if args.self_test:
        assert tuple(scenarios) == SITES
        assert all(round(sum(float(row[g]) for g in GROUPS), 8) == 100
                   for row in scenarios.values())
        print("STAGE03 SELF-TEST PASS: exactly ten sites; sums 100; scenarios remain HOLD")
        print("NO SOURCE FILES WRITTEN. NO SLURM/CIME.")
        return
    if args.case_trace is None:
        parser.error("--case-trace is required unless --self-test")
    source = args.case_trace.expanduser().resolve()
    report = input_report(source)
    items = [inspect_site(d, scenarios[d["site"]]) for d in report["sites"]]
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path.home().resolve() / ("Batch01_10_stage03_surface_soil_" + now)
    destination.mkdir(mode=0o700, exist_ok=False)
    summary = []
    print("=== STAGE03 TEN-SITE SURFACE/SOIL/PFT AUDIT | ORIGINAL INPUTS READ ONLY ===")
    print("SITE     CASES  SRC  NC_OK  PFT TREE MIX                 SCIENCE")
    for item in items:
        mix = item["candidate_tree_pft_pct"]
        n_ok = sum(p.get("read_status") == "READ_OK" for p in item["surface_reviews"])
        description = " ".join(f"{g}{mix[g]:g}" for g in GROUPS if mix[g] > 0)
        summary.append({
            "site": item["site"], "original_cases": len(item["cases"]),
            "surface_paths": len(item["discovered_surface_paths"]),
            "netcdf_read_ok": n_ok, "candidate_tree_PFT": description,
            "issues": ";".join(item["issues"]),
            "release_status": "HOLD_REVIEW_AREA_SOIL_MAPPING",
        })
        print(f"{item['site']:<8} {len(item['cases']):>5} "
              f"{len(item['discovered_surface_paths']):>4} {n_ok:>6} "
              f"{description:<28} HOLD")
    out = {
        "title": "Batch01 Stage03: model-tree assumptions and existing surface/soil",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "stage02_case_trace": str(source),
        "stage02_sha256": sha256(source),
        "scenario_csv_sha256": sha256(SCENARIOS),
        "original_inputs_modified": False, "slurm_submitted": False,
        "production_surfaces_approved": False, "sites": items,
    }
    (destination / "all_sites.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (destination / "summary.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print("SUMMARY:", destination / "summary.csv")
    print("DETAIL :", destination / "all_sites.json")
    print("ORIGINAL INPUT FILES UNCHANGED. NO CASE, SURFACE OR SLURM ACTION.")


if __name__ == "__main__":
    main()
