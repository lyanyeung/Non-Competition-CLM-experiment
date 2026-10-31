#!/usr/bin/env python3
"""Stage02F CH-Aws: all-hour saturation screens and every changed QBOT half-hour.

Scientific READ-ONLY TRIAGE, NOT acceptance. Stage02C provides exact operator
source-case candidate annual NetCDF references. Compare seven 2006–2024 forcing
path sets against an ARBITRARY unapproved SPINUP500_11P numerical reference.
Calculate water/ice saturation and VPD from T, P, q; log every changed half
hour in CSV for later tower-native/ERA5 QC review. NO forcing, CIME, Git or
Slurm changes. --out-dir must be a pre-existing empty directory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import math
import re
import sys
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
REFERENCE = "CH-Aws_FATES_SPINUP500_11P"
YEARS = tuple(range(2006, 2025))
EVENT_THRESHOLD = 1e-12
EVP_MOLECULAR_RATIO = 0.622
FIELDS = ("QBOT", "TBOT", "PSRF")
COLUMNS = [
    "year", "HH_index", "time", "candidate_group", "candidate_path", "reference_path",
    "QBOT_original_kgkg", "QBOT_candidate_kgkg", "delta_QBOT_gkg",
    "TBOT_C", "PSRF_Pa",
    "original_vapor_hPa", "candidate_vapor_hPa", "delta_vapor_hPa",
    "saturation_water_hPa", "saturation_ice_hPa",
    "original_RH_water_pct", "candidate_RH_water_pct",
    "original_RH_ice_pct", "candidate_RH_ice_pct",
    "original_VPD_water_hPa", "candidate_VPD_water_hPa", "delta_VPD_water_hPa",
    "candidate_RH_water_gt100", "candidate_RH_ice_gt100_if_subzero",
    "source_tower_QC_verified", "ERA5_source_verified",
]


def parse_input(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stage") != "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC":
        raise ValueError("Wrong Stage02C report marker")
    if data.get("read_only") is not True or data.get("science_release") is not False:
        raise ValueError("Stage02C source cannot be considered released")
    rows = [row for row in data.get("sites", []) if row.get("site") == "CH-Aws"]
    if len(rows) != 1:
        raise ValueError("CH-Aws row absent or duplicated")
    source_cases = rows[0].get("cases", [])
    if len(source_cases) != 8:
        raise ValueError("CH-Aws requires eight pinned CIME candidate cases")
    mapping = {}
    for c in source_cases:
        case = c.get("case")
        if not isinstance(case, str) or not case.startswith("CH-Aws_FATES_"):
            raise ValueError("Unexpected CIME case in source register")
        by_year = {}
        for item in c.get("site_datm", []):
            y = item.get("year")
            path = item.get("path")
            if not isinstance(path, str) or not Path(path).is_absolute():
                raise ValueError("Expected absolute input NetCDF path")
            m = re.match(r"^CH-Aws_DATM_((?:19|20)\d{2})(?:[_.-]|$)", Path(path).name)
            if m is None or int(m.group(1)) != y or y in by_year:
                raise ValueError("Year/path collision or wrong station: " + path)
            by_year[y] = path
        if tuple(sorted(by_year)) != YEARS:
            raise ValueError(case + ": incomplete 19-year register")
        mapping[case] = by_year
    if REFERENCE not in mapping:
        raise ValueError("Diagnostic numerical reference absent")
    signatures = collections.defaultdict(list)
    for case, byyear in mapping.items():
        signatures[tuple(byyear[y] for y in YEARS)].append(case)
    if len(signatures) != 7:
        raise ValueError("Expected seven distinct annual DATM path sets")
    groups = sorted(
        [{"cases": sorted(names), "by_year": dict(zip(YEARS, signature))}
         for signature, names in signatures.items()],
        key=lambda item: tuple(item["cases"]))
    return groups, mapping[REFERENCE]


def read_field(ds, wanted, np):
    matches = [k for k in ds.variables if k.upper() == wanted]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous " + wanted)
    v = ds.variables[matches[0]]
    if int(v.size) != 17520:
        raise ValueError("Expected 17520 half-hours in " + wanted)
    arr = np.ma.filled(np.ma.asarray(v[:]).astype("float64"), np.nan).reshape(-1)
    if not np.all(np.isfinite(arr)):
        raise ValueError(wanted + " contains missing/nonfinite; quarantine")
    return arr, str(getattr(v, "units", "")).lower().strip()


def load_annual(path, np, Dataset):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    with Dataset(str(path), "r") as ds:
        name = next((x for x in ("time", "DTIME", "dtime", "TIME")
                     if x in ds.variables), None)
        if name is None:
            raise ValueError("No annual time variable")
        var = ds.variables[name]
        if int(var.size) != 17520:
            raise ValueError("Annual forcing must have 17520 timestamps")
        times = np.ma.filled(np.ma.asarray(var[:]).astype("float64"), np.nan).reshape(-1)
        if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise ValueError("Nonmonotonic or missing forcing time")
        values = {key: read_field(ds, key, np) for key in FIELDS}
        if values["QBOT"][1] not in ("kg/kg", "kg kg-1", "kg kg^-1", "kg kg**-1", "1"):
            raise ValueError("QBOT not confirmed kg/kg: " + values["QBOT"][1])
        if values["TBOT"][1] not in ("k", "kelvin"):
            raise ValueError("TBOT not confirmed K")
        if values["PSRF"][1] not in ("pa", "pascal", "pascals"):
            raise ValueError("PSRF not confirmed Pa")
        return {"path": str(path), "time": times,
                "time_units": str(getattr(var, "units", "")),
                "calendar": str(getattr(var, "calendar", "UNSPECIFIED")),
                "values": values}


def vapor_pressure_hpa(q, p, np):
    return (q * p / (EVP_MOLECULAR_RATIO + (1-EVP_MOLECULAR_RATIO)*q)) / 100.0


def saturation_hpa(TK, np):
    # Buck (1981) forms for liquid water and ice, with T in Celsius.
    TC = TK - 273.15
    esw = 6.1121 * np.exp((18.678 - TC/234.5) * TC / (257.14 + TC))
    esi = 6.1115 * np.exp((23.036 - TC/333.7) * TC / (279.82 + TC))
    return esw, esi


def physics(item, np):
    q, _ = item["values"]["QBOT"]
    t, _ = item["values"]["TBOT"]
    p, _ = item["values"]["PSRF"]
    if np.any((t < 180) | (t > 340)):
        raise ValueError("Temperature outside bounded saturation formula range")
    if np.any((p < 40000) | (p > 110000)):
        raise ValueError("Pressure outside expected input range")
    if np.any((q < 0) | (q >= 0.08)):
        raise ValueError("QBOT outside numerical physical domain")
    e = vapor_pressure_hpa(q, p, np)
    esw, esi = saturation_hpa(t, np)
    return {
        "vapor": e, "esw": esw, "esi": esi,
        "rh_water": 100*e/esw, "rh_ice": 100*e/esi,
        "vpd_water": esw-e, "below0": t < 273.15,
    }


def when(item, i, netCDF4):
    if " since " not in item["time_units"].lower():
        return "INDEX_" + str(i) + "_CF_UNITS_ABSENT"
    try:
        cal = item["calendar"]
        if cal == "UNSPECIFIED":
            cal = "standard"
        return str(netCDF4.num2date(
            float(item["time"][i]), units=item["time_units"],
            calendar=cal, only_use_cftime_datetimes=True))
    except Exception as exc:
        return "INDEX_" + str(i) + "_CF_DECODE_" + type(exc).__name__


def screen_counts(phys, np):
    return {
        "RH_water_gt100_HH": int(np.count_nonzero(phys["rh_water"] > 100.0 + 1e-8)),
        "RH_water_gt105_HH": int(np.count_nonzero(phys["rh_water"] > 105.0)),
        "RH_ice_gt100_in_subzero_HH": int(np.count_nonzero(
            (phys["rh_ice"] > 100.0+1e-8) & phys["below0"])),
        "negative_water_VPD_HH": int(np.count_nonzero(phys["vpd_water"] < -1e-8)),
        "max_RH_water_pct": float(np.max(phys["rh_water"])),
        "min_RH_water_pct": float(np.min(phys["rh_water"])),
        "min_VPD_water_hPa": float(np.min(phys["vpd_water"])),
    }


def per_year(y, groups, reference, np, Dataset, netCDF4, writer, summary):
    ref = load_annual(reference[y], np, Dataset)
    base_phys = physics(ref, np)
    bq, _ = ref["values"]["QBOT"]
    bt, _ = ref["values"]["TBOT"]
    bp, _ = ref["values"]["PSRF"]
    record = {"year": y, "numerical_baseline_case": REFERENCE,
              "baseline_is_scientifically_approved": False,
              "variant_results": [], "compare_holds": []}
    for group in groups:
        path = group["by_year"][y]
        label = ",".join(group["cases"])
        entry = {"cases": group["cases"], "path": path}
        try:
            alt = ref if path == reference[y] else load_annual(path, np, Dataset)
            if (alt["time_units"] != ref["time_units"] or
                alt["calendar"] != ref["calendar"] or
                not np.array_equal(alt["time"], ref["time"])):
                raise ValueError("Time axis/units/calendar mismatch")
            if any(alt["values"][name][1] != ref["values"][name][1] for name in FIELDS):
                raise ValueError("Physical units differ from reference")
            q, _ = alt["values"]["QBOT"]
            t, _ = alt["values"]["TBOT"]
            p, _ = alt["values"]["PSRF"]
            if not np.array_equal(t, bt) or not np.array_equal(p, bp):
                raise ValueError("TBOT/PSRF differ: cannot isolate QBOT VPD effects")
            ph = physics(alt, np)
            changed = np.flatnonzero(np.abs(q-bq) > EVENT_THRESHOLD)
            entry.update({
                "status": "ALIGNED",
                "changed_HH": int(changed.size),
                "max_abs_delta_QBOT_gkg": float(np.max(np.abs(q-bq)))*1000,
                "max_abs_delta_vapor_hPa": float(np.max(np.abs(ph["vapor"]-base_phys["vapor"]))),
                "overall_physical_screen": screen_counts(ph, np),
            })
            for i0 in changed:
                i = int(i0)
                writer.writerow({
                    "year": y, "HH_index": i, "time": when(ref, i, netCDF4),
                    "candidate_group": label, "candidate_path": path,
                    "reference_path": reference[y],
                    "QBOT_original_kgkg": float(bq[i]),
                    "QBOT_candidate_kgkg": float(q[i]),
                    "delta_QBOT_gkg": float((q[i]-bq[i])*1000),
                    "TBOT_C": float(t[i]-273.15), "PSRF_Pa": float(p[i]),
                    "original_vapor_hPa": float(base_phys["vapor"][i]),
                    "candidate_vapor_hPa": float(ph["vapor"][i]),
                    "delta_vapor_hPa": float(ph["vapor"][i]-base_phys["vapor"][i]),
                    "saturation_water_hPa": float(ph["esw"][i]),
                    "saturation_ice_hPa": float(ph["esi"][i]),
                    "original_RH_water_pct": float(base_phys["rh_water"][i]),
                    "candidate_RH_water_pct": float(ph["rh_water"][i]),
                    "original_RH_ice_pct": float(base_phys["rh_ice"][i]),
                    "candidate_RH_ice_pct": float(ph["rh_ice"][i]),
                    "original_VPD_water_hPa": float(base_phys["vpd_water"][i]),
                    "candidate_VPD_water_hPa": float(ph["vpd_water"][i]),
                    "delta_VPD_water_hPa": float(ph["vpd_water"][i]-base_phys["vpd_water"][i]),
                    "candidate_RH_water_gt100": bool(ph["rh_water"][i] > 100.0+1e-8),
                    "candidate_RH_ice_gt100_if_subzero": bool(
                        ph["rh_ice"][i] > 100.0+1e-8 and ph["below0"][i]),
                    "source_tower_QC_verified": False, "ERA5_source_verified": False,
                })
            summary["changed_event_rows"] += int(changed.size)
        except Exception as exc:
            entry["status"] = "HOLD_" + type(exc).__name__
            entry["error"] = str(exc)
            record["compare_holds"].append(entry)
        record["variant_results"].append(entry)
    return record


def selftest():
    assert len(YEARS) == 19 and len(COLUMNS) == len(set(COLUMNS))
    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit("Activate clm_fates_env: " + str(exc))
    t = np.array([273.15, 263.15])
    a, b = saturation_hpa(t, np)
    assert abs(a[0] - 6.1121) < 0.001
    assert abs(b[0] - 6.1115) < 0.001
    assert a[1] > b[1]  # saturation over supercooled water > ice
    assert 5 < float(vapor_pressure_hpa(np.array([.004]), np.array([80000]), np)[0]) < 6
    print("STAGE02F SELF-TEST PASS: water/ice saturation, HH event ledger schema; no files written")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage02c", type=Path, help="Actual saved Stage02C JSON")
    ap.add_argument("--out-dir", type=Path, help="Existing EMPTY output directory only")
    args = ap.parse_args()
    if args.self_test:
        if args.out_dir:
            ap.error("self-test has no output")
        selftest()
        return
    if not args.stage02c or not args.stage02c.is_file():
        ap.error("Need existing Stage02C JSON")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY; no overwriting")
    try:
        import numpy as np
        import netCDF4
        from netCDF4 import Dataset
    except ImportError as exc:
        ap.error("Activate clm_fates_env for numpy/netCDF4: " + str(exc))
    source = json.loads(args.stage02c.read_text(encoding="utf-8"))
    groups, reference = parse_input(source)
    output = {
        "stage": "STAGE02F_CH_AWS_QBOT_SATURATION_EVENT_TRIAGE",
        "source_stage02c": str(args.stage02c),
        "reference_case_arbitrary_unapproved": REFERENCE,
        "version_groups": [x["cases"] for x in groups],
        "read_only": True, "science_release": False,
        "original_input_modified": False, "slurm_submitted": False,
        "methods": "Buck water/ice saturation; q->e from exact P; reference comparison is only numerical",
        "limits": "No original tower RH/VPD/QC or ERA5 source pairing; does not authorize repairs",
        "annual_reports": [],
    }
    csvpath = args.out_dir / "stage02f_all_changed_HH.csv"
    jsonpath = args.out_dir / "stage02f_summary.json"
    tally = {"changed_event_rows": 0}
    with csvpath.open("x", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=COLUMNS)
        writer.writeheader()
        for year in YEARS:
            record = per_year(year, groups, reference, np, Dataset, netCDF4, writer, tally)
            output["annual_reports"].append(record)
            total = sum(x.get("changed_HH", 0) for x in record["variant_results"])
            risk = sum(x.get("overall_physical_screen", {}).get("RH_water_gt100_HH", 0)
                       for x in record["variant_results"])
            print("YEAR",year,"DISTINCT_PATHS",len(record["variant_results"]),
                  "DIFF_ROWS_ALL_VARIANTS",total,
                  "RH_WATER_GT100_ROWS_ALL_VARIANTS",risk,
                  "COMPARE_HOLDS",len(record["compare_holds"]))
            for e in record["compare_holds"][:3]:
                print("  HOLD", ",".join(e["cases"]), e.get("error", ""))
    output["changed_event_rows"] = tally["changed_event_rows"]
    output["candidate_HH_comparison_holds"] = sum(
        len(x["compare_holds"]) for x in output["annual_reports"])
    with jsonpath.open("x", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
    print("CHANGED_EVENT_ROWS",tally["changed_event_rows"],
          "COMPARISON_HOLDS",output["candidate_HH_comparison_holds"])
    print("CSV",csvpath)
    print("JSON",jsonpath)
    print("ALL SCIENCE HOLD: MUST VERIFY ORIGINAL TOWER/ERA PHYSICAL SOURCES")


if __name__ == "__main__":
    main()
