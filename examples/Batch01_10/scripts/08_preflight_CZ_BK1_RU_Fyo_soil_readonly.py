#!/usr/bin/env python3
"""Batch01 Stage08: read-only preflight for CZ-BK1 and RU-Fyo soil decisions.

Read operator soil decisions, Flechard2020 Table S4, Stage05 case report and
the two old NetCDF surfaces strictly to examine NetCDF schema and RU-Fyo's
explicitly authorized ORIGINAL SOIL-only fallback. CZ-BK1 old grid soil values
are NOT used or compared. No new surface/CIME case/forcing or Slurm change.
Writes only a fresh HOME report directory.

Usage:
  python3 -B examples/Batch01_10/scripts/08_preflight_CZ_BK1_RU_Fyo_soil_readonly.py --self-test
  python3 -B examples/Batch01_10/scripts/08_preflight_CZ_BK1_RU_Fyo_soil_readonly.py \
    --stage05 "$HOME/Batch01_10_stage05_station_inputs_20261024T100531Z/all_sites.json"
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DECISIONS = REPO / "data/batch01_10_soil_input_decisions.csv"
S4 = REPO / "data/batch01_10_Flechard2020_TableS4_soil.csv"
SITE_ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
BASELINE = {
    "CZ-BK1": "surfdata_CZ-BK1_hist_2000_16pfts_c261012.nc",
    "RU-Fyo": "surfdata_RU-Fyo_hist_2000_16pfts_c261011.nc",
}
FIELDS = ("PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT", "PCT_SAND",
          "PCT_CLAY")


def stop(message):
    raise SystemExit(str(message))


def table(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return {row["site"]: row for row in csv.DictReader(file)}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cz_values(row):
    vals = {k: float(row[k]) for k in (
        "sand_pct_reported", "silt_pct_reported", "clay_pct_reported")}
    if (row.get("present_in_table_s4") != "YES" or
            abs(vals["sand_pct_reported"] - 22) > 1e-9 or
            abs(vals["silt_pct_reported"] - 58) > 1e-9 or
            abs(vals["clay_pct_reported"] - 21) > 1e-9):
        stop("CZ-BK1 source Table S4 22/58/21 no longer matches: HOLD")
    total = sum(vals.values())
    if abs(total - 101) > 1e-9:
        stop("CZ published total unexpectedly changed; HOLD")
    return {
        "reported_pct": {"sand": 22, "silt": 58, "clay": 21},
        "reported_sum_pct": total,
        "proposed_clm_fine_earth_normalized_pct": {
            "sand": 100 * 22 / total,
            "silt": 100 * 58 / total,
            "clay": 100 * 21 / total,
        },
        "normalization_rule": "Normalize published 101 by dividing by 101; 101 stems from reported rounding; values are only a candidate for unassigned layers",
        "depth_provenance": "S4 depth=0.55 m is SITE SOIL DEPTH, not sampling interval for each reported texture component",
        "vertical_profile": "NOT_DEFINED_DO_NOT_FILL_ALL_LAYERS",
    }


def source_surface(site):
    return SITE_ROOT / site / "subset_data" / BASELINE[site]


def read_source_schema(site):
    path = source_surface(site)
    out = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        out["status"] = "MISSING_SOURCE_SCHEMA"
        return out
    out["size_bytes"] = path.stat().st_size
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as err:
        out["status"] = "NETCDF4_OR_NUMPY_MISSING: " + str(err)
        return out
    try:
        with Dataset(str(path), mode="r") as ds:
            out["dims"] = {k: len(v) for k, v in ds.dimensions.items()}
            out["fields"] = {
                key: {"dims": list(ds.variables[key].dimensions),
                      "shape": list(ds.variables[key].shape),
                      "dtype": str(ds.variables[key].dtype)}
                for key in FIELDS if key in ds.variables
            }
            out["potential_soil_physics_fields"] = sorted(
                key for key in ds.variables
                if any(q in key.upper() for q in
                       ("ORGANIC", "SOIL", "PEAT", "BEDROCK", "SOIL_COLOR"))
            )[:80]
            if site == "RU-Fyo":
                # The sole soil-numeric fallback allowed by the operator.
                original_soil = {}
                for name in ("PCT_SAND", "PCT_CLAY"):
                    if name not in ds.variables:
                        original_soil[name] = {"error": "MISSING"}
                        continue
                    v = ds.variables[name]
                    if v.size > 10000:
                        original_soil[name] = {"error": "UNEXPECTED_LARGE_GRID"}
                        continue
                    data = np.ma.asarray(v[:], dtype="float64")
                    a = np.ma.filled(data, np.nan)
                    original_soil[name] = {
                        "shape": list(v.shape),
                        "values_all_existing_layers": [
                            float(x) if math.isfinite(float(x)) else None
                            for x in a.ravel()
                        ],
                    }
                out["RU_only_authorized_original_soil_values"] = original_soil
                out["peat_review"] = "REQUIRED: Flechard S4 identifies Peat without mineral texture; grid texture is a technical fallback, NOT proof of peat/organic soil model suitability"
            else:
                out["CZ_old_soil_values"] = "NOT_READ_BY_POLICY"
            out["status"] = "READ_OK"
    except Exception as err:
        out["status"] = "READ_ERROR: " + repr(err)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage05", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    d = table(DECISIONS)
    s4 = table(S4)
    if set(BASELINE) - set(d) or set(BASELINE) - set(s4):
        stop("Missing CZ/RU decision or publication entry")
    if d["CZ-BK1"]["soil_texture_decision"] != "FLECHARD2020_S4_STATION_TEXTURE_SELECTED":
        stop("CZ decision not selected as Flechard2020 S4")
    if d["RU-Fyo"]["soil_texture_decision"] != "ORIGINAL_FSURDAT_TEXTURE_OPERATOR_EXCEPTION":
        stop("RU exception was modified unexpectedly")
    cz = cz_values(s4["CZ-BK1"])
    if s4["RU-Fyo"]["sand_pct_reported"] or s4["RU-Fyo"]["clay_pct_reported"]:
        stop("RU-Fyo mineral composition has changed in S4: manual review needed")
    if args.self_test:
        v = cz["proposed_clm_fine_earth_normalized_pct"]
        assert abs(sum(v.values()) - 100) < 1e-9
        assert len(BASELINE) == 2
        print("STAGE08 SELF-TEST PASS | CZ 22/58/21 published sum101, RU peat/source-only exception")
        print("CZ normalization preview: Sand={sand:.6f} Silt={silt:.6f} Clay={clay:.6f}".format(**v))
        print("NO SOURCE MODEL FILE WRITES; NO AD JOBS")
        return
    if args.stage05 is None:
        ap.error("--stage05 required")
    stage = args.stage05.expanduser().resolve()
    if not stage.is_file() or stage.name != "all_sites.json" or not (
            stage.parent.name.startswith("Batch01_10_stage05_station_inputs_")):
        stop("Expected actual Stage05 timestamped all_sites.json")
    record = json.loads(stage.read_text(encoding="utf8"))
    if record.get("input_sources_modified") is not False or record.get("slurm_submitted") is not False:
        stop("Stage05 safety flags invalid")
    stage_sites = {x["site"]: x for x in record.get("sites", [])}
    if set(BASELINE) - set(stage_sites):
        stop("Stage05 CZ/RU missing")
    print("STAGE08 | CZ-BK1 & RU-Fyo | OBSERVED/EXCEPTION SOIL PREFLIGHT | READ ONLY")
    print("Stage05 reference CIME flags are NOT the final new FIXNC case flags.")
    results = {}
    for site in BASELINE:
        oldcases = stage_sites[site].get("existing_cases", [])
        surface = read_source_schema(site)
        result = {
            "original_case_names": [x.get("case") for x in oldcases],
            "new_site_target_landunits": {"PCT_NATVEG": 100, "PCT_CROP": 0},
            "old_surface_technical_metadata": surface,
            "new_FATES_flags_NOT_APPLIED": {
                "use_fates": True, "use_fates_sp": False,
                "use_fates_nocomp": True, "use_fates_fixed_biogeog": True,
            },
            "new_CIME_case_built": False,
            "new_surface_built": False,
            "AD_smoke_authorized": False,
        }
        if site == "CZ-BK1":
            result["soil_selection"] = cz
            result["release_gate"] = "HOLD_SOIL_VERTICAL_LAYER_POLICY_FATES_MAPPING_DATM"
        else:
            result["soil_selection"] = {
                "policy": "USE_ONLY_OLD_SURFACE_PCT_SAND_AND_PCT_CLAY_AS_TECHNICAL_EXCEPTION",
                "report_as_observed": False,
                "organic_peat_review": "REQUIRED",
            }
            result["release_gate"] = "HOLD_PEAT_PHYSICS_FATES_MAPPING_DATM"
        results[site] = result
        print(site, "source", surface["status"],
              "old_cases", len(oldcases), "release", result["release_gate"])
        if site == "CZ-BK1":
            print("  Selected Table S4: 22/58/21 (reported 101), depth distribution NOT selected")
            print("  Normalized candidate:", cz["proposed_clm_fine_earth_normalized_pct"])
        else:
            print("  RU old SOIL ONLY:", surface.get("RU_only_authorized_original_soil_values",
                                                  "NOT_READABLE"))
            print("  WARNING peat representativeness is UNRESOLVED")
    output_dir = (Path.home().resolve() /
                  ("Batch01_10_stage08_soil_preflight_" +
                   datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    output_dir.mkdir(mode=0o700, exist_ok=False)
    report = {
        "stage05_input": str(stage), "stage05_sha256": digest(stage),
        "soil_decisions_sha256": digest(DECISIONS),
        "Flechard_S4_sha256": digest(S4),
        "site_science": results,
        "old_source_modified": False,
        "new_surface_modified": False,
        "new_case_created": False,
        "slurm_submitted": False,
    }
    output = output_dir / "all_sites.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("REPORT:", output)
    print("HOLD NEW SURFACES / AD JOBS UNTIL SOIL-LAYER, FATES, DATM GATES PASS")


if __name__ == "__main__":
    main()
