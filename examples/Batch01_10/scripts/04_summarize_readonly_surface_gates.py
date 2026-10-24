#!/usr/bin/env python3
"""Batch01 Stage04: summarize the existing Stage02/03 reports; READ ONLY.

No model NetCDF, CIME or Slurm job is opened or changed. No output files are
created by this script; redirect terminal output to an operator log if useful.

python3 -B examples/Batch01_10/scripts/04_summarize_readonly_surface_gates.py \
    --stage03 /iridisfs/home/ly3n24/Batch01_10_stage03_surface_soil_20261024T094433Z/all_sites.json
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

SITES = ("CZ-BK1", "IT-Ren", "RU-Fyo", "CH-Dav", "IT-Col",
         "FR-Fon", "FI-Sod", "FR-Pue", "DE-Hai", "BE-Vie")


def validate(path, kind, prefix):
    if path.name != kind or not path.parent.name.startswith(prefix) or not path.is_file():
        raise SystemExit("Unexpected/missing source report: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def first_value(surf, field):
    values = surf.get("fields", {}).get(field, {}).get("sample_first_12", [])
    if not isinstance(values, list) or len(values) != 1 and field in (
            "PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND",
            "PCT_GLACIER", "PCT_URBAN"):
        # Only trust scalar fields, never select one cell of a multi-cell surface.
        return None
    if not values:
        return None
    val = values[0]
    if not isinstance(val, (int, float)) or not math.isfinite(val):
        return None
    return float(val)


def scalar_field(surf, name):
    fld = surf.get("fields", {}).get(name, {})
    shape = fld.get("shape", [])
    if not shape or math.prod(shape) != 1:
        return None
    return first_value(surf, name)


def soil_layer1(surf, name):
    fld = surf.get("fields", {}).get(name, {})
    val = fld.get("layer1_candidate")
    if val is None or not isinstance(val, (int, float)) or not math.isfinite(val):
        return None
    return float(val)


def fmt(value, width=6):
    return f"{value:.2f}".rjust(width) if value is not None else "-".rjust(width)


def case_streams(stage02_site):
    out = []
    for case in stage02_site.get("cases", []):
        keys = {}
        for doc in case.get("case_docs", []) + case.get("runtime_docs", []):
            if not doc.get("present"):
                continue
            for k, v in doc.get("values", {}).items():
                if k in ("year_first", "year_last", "year_align"):
                    keys.setdefault(k, str(v))
        config = case.get("source_case_config", {})
        out.append((case.get("case", "?"), keys, config))
    return out


def run(stage03_path):
    stage03 = validate(stage03_path, "all_sites.json",
                       "Batch01_10_stage03_surface_soil_")
    if any(stage03.get(k) is not False for k in (
            "original_inputs_modified", "slurm_submitted",
            "production_surfaces_approved")):
        raise SystemExit("Stage03 safety flags are not all False")
    stage02_path = Path(stage03.get("stage02_case_trace", "")).expanduser().resolve()
    stage02 = validate(stage02_path, "case_trace.json",
                      "Batch01_10_stage02_case_trace_")
    if any(stage02.get(k) is not False for k in (
            "files_changed_outside_new_report", "slurm_submitted")):
        raise SystemExit("Stage02 safety flags are not both False")

    v3, v2 = stage03.get("sites", []), stage02.get("sites", [])
    if tuple(x.get("site") for x in v3) != SITES or (
            tuple(x.get("site") for x in v2) != SITES):
        raise SystemExit("Report membership/order does not equal exact Batch01 sites")

    print("BATCH01 STAGE04 REPORT EXTRACTION — READ ONLY")
    print("Important: PFT TREE MIX = selected hypothesis, NOT actual fsurdat")
    print("NAT/CROP are source-host landunit percentages; soil is source-grid layer 1")
    print("No soil field observation or FATES index mapping has been certified.")
    print()
    print(f"{'SITE':<8} {'CASES':>5} {'SRC_OK':>6} {'NAT%':>6} "
          f"{'CROP%':>6} {'SAND%':>6} {'CLAY%':>6} "
          f"{'HOST_PFT_SUM':>12} {'ISSUES':>6}")
    for site in v3:
        surfaces = site.get("surface_reviews", [])
        good = [x for x in surfaces if x.get("read_status") == "READ_OK"]
        src = good[0] if len(good) == 1 else {}
        if len(good) > 1:
            # More than one source surface can differ: do not combine.
            print(site["site"], "MULTIPLE_READABLE_SOURCE_SURFACES: review separately")
        pct = src.get("fields", {}).get("PCT_NAT_PFT", {})
        pft_sum = pct.get("single_point_conditional_pft_sum")
        print(f"{site['site']:<8} {len(site.get('cases', [])):>5} "
              f"{len(good):>6} {fmt(scalar_field(src, 'PCT_NATVEG'))} "
              f"{fmt(scalar_field(src, 'PCT_CROP'))} "
              f"{fmt(soil_layer1(src, 'PCT_SAND'))} "
              f"{fmt(soil_layer1(src, 'PCT_CLAY'))} "
              f"{fmt(pft_sum, 12)} {len(site.get('issues', [])):>6}")
        print("   Tree hypothesis: " + ", ".join(
            f"{k}={v:g}%" for k, v in site["candidate_tree_pft_pct"].items()
            if v))
        print("   Source surface(s): " + "; ".join(
            x["source_path"] for x in surfaces) if surfaces else "   No surface")
        for code in site.get("issues", []):
            print("   FLAG: " + str(code))
    print()
    print("CIME CASE / DATM CONFIGURATION (report excerpts; verify actual stream files)")
    for site in v2:
        for name, calendar, config in case_streams(site):
            years = "/".join(calendar.get(k, "?") for k in (
                "year_first", "year_last", "year_align"))
            print(f"{site['site']:<8} {name}")
            print(f"   DATM first/last/align={years}; "
                  f"RUN_STARTDATE={config.get('RUN_STARTDATE', '?')}; "
                  f"CLM_ACCELERATED_SPINUP={config.get('CLM_ACCELERATED_SPINUP', '?')}")
    print()
    print("SCIENCE RELEASE: HOLD FOR ALL 10. NO SURFACE OR JOB MODIFICATIONS.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage03", type=Path, required=True)
    args = parser.parse_args()
    run(args.stage03.expanduser().resolve())


if __name__ == "__main__":
    main()
