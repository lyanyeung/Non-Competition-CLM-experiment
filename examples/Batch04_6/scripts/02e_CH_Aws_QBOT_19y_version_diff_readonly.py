#!/usr/bin/env python3
"""Stage02E CH-Aws: read-only per-half-hour QBOT forcing-variant comparison.

Reference SPINUP500_11P is an ARBITRARY diagnostic baseline, NOT an approved
meteorology source. Input is the site-case annual reference inventory Stage02C.
All 19 annual years and all 7 distinct forcing paths are compared for RH
repair size/timing, while TBOT, PSRF and CF time coordinates are checked.
No tower QC / ERA comparison, forcing edits, model cases or Slurm.
Only --report writes one NEW JSON file (exclusive create).
"""
from __future__ import annotations
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

SITE = "CH-Aws"
DEFAULT_REFERENCE = "CH-Aws_FATES_SPINUP500_11P"
EXPECTED_YEARS = tuple(range(2006, 2025))
MAX_POINTS = 20000
EPSILON = 0.622


def validated_case_paths(source):
    if source.get("stage") != "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC":
        raise ValueError("Expected source-pinned Stage02C JSON report")
    if source.get("science_release") is not False or source.get("read_only") is not True:
        raise ValueError("Stage02C still must be in science HOLD/read-only state")
    sites = [x for x in source.get("sites", []) if x.get("site") == SITE]
    if len(sites) != 1:
        raise ValueError("CH-Aws row not unique")
    cases = sites[0].get("cases", [])
    if len(cases) != 8:
        raise ValueError("CH-Aws expected 8 original cases")
    mapping = {}
    for case in cases:
        name = case.get("case", "")
        if not name.startswith(SITE + "_") or "/" in name or "\\" in name:
            raise ValueError("Unsafe or unexpected CH-Aws case name")
        annual = {}
        for item in case.get("site_datm", []):
            path = item.get("path", "")
            year = item.get("year")
            if not isinstance(path, str) or not Path(path).is_absolute():
                raise ValueError("Must use an absolute site-DATM source path")
            match = re.match(r"^CH-Aws_DATM_((?:19|20)\d{2})(?:[_.-]|$)", Path(path).name)
            if not match or int(match.group(1)) != year:
                raise ValueError("CH-Aws source annual year/path mismatch")
            if year in annual:
                raise ValueError("Duplicate year in a candidate case")
            annual[year] = path
        if tuple(sorted(annual)) != EXPECTED_YEARS:
            raise ValueError("Case missing one of the 19 CH-Aws years: " + name)
        mapping[name] = annual
    if len({tuple(mapping[c][y] for y in EXPECTED_YEARS) for c in mapping}) != 7:
        raise ValueError("Expected 7 distinct candidate forcing path sets")
    return mapping


def get_field(ds, field, np):
    lookup = {name.upper(): name for name in ds.variables}
    key = lookup.get(field.upper())
    if key is None:
        raise ValueError("Missing " + field + " in NetCDF")
    v = ds.variables[key]
    if v.size != 17520 or v.size > MAX_POINTS:
        raise ValueError(field + ": expected one-site 17520 half-hour records")
    data = np.ma.filled(np.ma.asarray(v[:]).astype("float64"), np.nan).reshape(-1)
    if not np.all(np.isfinite(data)):
        raise ValueError(field + ": missing or nonfinite records; compare on HOLD")
    return data, str(getattr(v, "units", "")).strip()


def load_annual(path, np, Dataset):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    with Dataset(path, "r") as ds:
        tkey = next((n for n in ("time", "DTIME", "dtime", "TIME")
                     if n in ds.variables), None)
        if tkey is None:
            raise ValueError("No time coordinate: " + path)
        tv = ds.variables[tkey]
        t = np.ma.filled(np.ma.asarray(tv[:]).astype("float64"), np.nan).reshape(-1)
        if t.size != 17520 or not np.all(np.isfinite(t)):
            raise ValueError("Invalid annual time axis: " + path)
        return {
            "path": path,
            "time": t,
            "time_units": str(getattr(tv, "units", "")),
            "calendar": str(getattr(tv, "calendar", "UNSPECIFIED")),
            "QBOT": get_field(ds, "QBOT", np),
            "TBOT": get_field(ds, "TBOT", np),
            "PSRF": get_field(ds, "PSRF", np),
        }


def aligned(reference, alternate, np):
    if (reference["time_units"] != alternate["time_units"] or
            reference["calendar"] != alternate["calendar"]):
        raise ValueError("Different time units/calendar: do not compare indexed samples")
    if not np.array_equal(reference["time"], alternate["time"]):
        raise ValueError("Non-identical time coordinates: compare rejected")
    for field in ("QBOT", "TBOT", "PSRF"):
        if reference[field][1].lower() != alternate[field][1].lower():
            raise ValueError(field + " units differ")
    punit = reference["PSRF"][1].lower()
    qunit = reference["QBOT"][1].lower()
    tunit = reference["TBOT"][1].lower()
    if punit not in ("pa", "pascal", "pascals"):
        raise ValueError("PSRF must be in Pa for vapour-pressure diagnostic")
    if qunit not in ("kg/kg", "kg kg-1", "kg kg^-1", "kg kg**-1", "1", "kg kg-1"):
        raise ValueError("QBOT units not confirmed kg/kg; no VPD diagnostics: " + qunit)
    if tunit not in ("k", "kelvin"):
        raise ValueError("TBOT units not confirmed Kelvin")
    return True


def vapour_pressure_hpa(q, pressure, np):
    return (q * pressure / (EPSILON + (1 - EPSILON) * q)) / 100.0


def time_label(time_info, index, netCDF4):
    unit = time_info["time_units"]
    calendar = time_info["calendar"]
    if " since " not in unit.lower():
        return "INDEX_" + str(index) + "_NO_CF_TIME"
    try:
        actual = netCDF4.num2date(float(time_info["time"][index]),
                                 units=unit,
                                 calendar=calendar if calendar != "UNSPECIFIED" else "standard",
                                 only_use_cftime_datetimes=True)
        return str(actual)
    except Exception as exc:
        return "INDEX_" + str(index) + "_TIME_DECODE_" + type(exc).__name__


def compare_one_year(year, path_to_cases, baseline_path, np, Dataset, nc):
    base = load_annual(baseline_path, np, Dataset)
    out = {
        "year": year, "baseline_file": baseline_path,
        "baseline_case": DEFAULT_REFERENCE,
        "baseline_is_approved": False, "comparisons": [],
    }
    bq, _ = base["QBOT"]
    bp, _ = base["PSRF"]
    bvp = vapour_pressure_hpa(bq, bp, np)
    for path in sorted(path_to_cases):
        item = {"path": path, "cases": sorted(path_to_cases[path]),
                "comparison_reference": baseline_path}
        try:
            other = base if path == baseline_path else load_annual(path, np, Dataset)
            aligned(base, other, np)
            q, _ = other["QBOT"]
            t, _ = other["TBOT"]
            p, _ = other["PSRF"]
            bt, _ = base["TBOT"]
            dq = q - bq
            changed = np.flatnonzero(np.abs(dq) > 1e-12)
            delta_vp = vapour_pressure_hpa(q, p, np) - bvp
            item.update({
                "comparison_status": "ALIGNED",
                "n_half_hours": int(q.size),
                "changed_QBOT_hh_absgt_1e-12": int(changed.size),
                "changed_QBOT_hh_absgt_1e-7": int(np.count_nonzero(np.abs(dq) > 1e-7)),
                "changed_QBOT_hh_absgt_1e-6": int(np.count_nonzero(np.abs(dq) > 1e-6)),
                "max_abs_delta_QBOT_g_per_kg": float(np.max(np.abs(dq))) * 1000,
                "mean_abs_delta_QBOT_g_per_kg": float(np.mean(np.abs(dq))) * 1000,
                "max_abs_delta_vapour_pressure_hPa": float(np.max(np.abs(delta_vp))),
                "max_abs_delta_VPD_hPa_if_equal_T": float(np.max(np.abs(delta_vp))),
                "TBOT_different_HH_absgt_1e-9": int(np.count_nonzero(np.abs(t-bt) > 1e-9)),
                "PSRF_different_HH_absgt_1e-6": int(np.count_nonzero(np.abs(p-bp) > 1e-6)),
            })
            if changed.size:
                ordered = np.argsort(np.abs(dq[changed]))[-5:][::-1]
                top = []
                for pos in changed[ordered]:
                    i = int(pos)
                    top.append({
                        "index": i,
                        "time": time_label(base, i, nc),
                        "ref_QBOT_kgkg": float(bq[i]),
                        "alt_QBOT_kgkg": float(q[i]),
                        "delta_QBOT_gkg": float(dq[i] * 1000),
                        "delta_vapor_pressure_hPa": float(delta_vp[i]),
                        "delta_VPD_hPa_if_equal_T": float(-delta_vp[i]),
                    })
                item["largest_5_HH"] = top
                item["first_changed_HH"] = {
                    "index": int(changed[0]), "time": time_label(base, int(changed[0]), nc)
                }
                item["last_changed_HH"] = {
                    "index": int(changed[-1]), "time": time_label(base, int(changed[-1]), nc)
                }
        except Exception as exc:
            item["comparison_status"] = "HOLD_" + type(exc).__name__
            item["error"] = str(exc)
        out["comparisons"].append(item)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage02c", type=Path)
    ap.add_argument("--reference-case", default=DEFAULT_REFERENCE)
    ap.add_argument("--report", type=Path, help="New JSON path in existing directory; no overwrites")
    args = ap.parse_args()
    if args.self_test:
        assert len(EXPECTED_YEARS) == 19
        assert len(SITE) == 6 and DEFAULT_REFERENCE.endswith("_11P")
        assert math.isclose(vapour_pressure_hpa(.004, 80000, __import__("math")), 
                            (.004*80000/(.622+.378*.004))/100, abs_tol=1e-12)
        print("STAGE02E SELF-TEST PASS: 19-year CH-Aws QBOT comparison, source HOLD, no writes")
        return
    if not args.stage02c or not args.stage02c.is_file():
        ap.error("Stage02C source JSON required")
    try:
        import numpy as np
        import netCDF4
        from netCDF4 import Dataset
    except ImportError as exc:
        ap.error("Activate clm_fates_env with numpy/netCDF4: " + str(exc))
    src = json.loads(args.stage02c.read_text(encoding="utf-8"))
    cases = validated_case_paths(src)
    if args.reference_case not in cases:
        ap.error("Unknown exact original CH-Aws reference-case")
    output = {"stage":"STAGE02E_CH_AWS_QBOT_VARIANT_DIFF",
              "reference_case":args.reference_case,
              "baseline_only_not_scientific_selection":True,
              "science_release":False,"source_modified":False,
              "CIME_modified":False,"Slurm_submitted":False,
              "source_stage02c":str(args.stage02c),"year_reports":[]}
    holds = 0
    for year in EXPECTED_YEARS:
        by_path = collections.defaultdict(set)
        for case, byyear in cases.items():
            by_path[byyear[year]].add(case)
        base_path = cases[args.reference_case][year]
        result = compare_one_year(year, by_path, base_path, np, Dataset, netCDF4)
        result["baseline_case"] = args.reference_case
        output["year_reports"].append(result)
        aligned = [v for v in result["comparisons"] if v.get("comparison_status")=="ALIGNED"]
        bad = [v for v in result["comparisons"] if v.get("comparison_status")!="ALIGNED"]
        holds += len(bad)
        max_q = max((v["max_abs_delta_QBOT_g_per_kg"] for v in aligned), default=float("nan"))
        max_v = max((v["max_abs_delta_vapour_pressure_hPa"] for v in aligned), default=float("nan"))
        n_changed = max((v["changed_QBOT_hh_absgt_1e-12"] for v in aligned), default=-1)
        print("YEAR",year,"CANDIDATE_FILES",len(result["comparisons"]),
              "MAX_CHANGED_HH",n_changed, "MAX_ABS_DQ_GKG",f"{max_q:.8g}",
              "MAX_ABS_DE_HPA",f"{max_v:.8g}","HOLD_COMPARISONS",len(bad))
        for b in bad[:3]:
            print("  COMPARISON_HOLD",Path(b["path"]).parent.name,b.get("error"))
        if n_changed>0:
            ranked=sorted(aligned,key=lambda x:x["max_abs_delta_QBOT_g_per_kg"],reverse=True)
            for r in ranked[:2]:
                if r["max_abs_delta_QBOT_g_per_kg"]>0:
                    print("  DIFFERENCE", ",".join(r["cases"]),
                          "CHANGED_HH",r["changed_QBOT_hh_absgt_1e-12"],
                          "MAX_DQ_GKG",f'{r["max_abs_delta_QBOT_g_per_kg"]:.8g}',
                          "FIRST",r.get("first_changed_HH",{}).get("time"))
    print("COMPARISON_HOLDS",holds)
    print("BASELINE_CASE_IS_ARBITRARY:",args.reference_case)
    if args.report:
        path=args.report.expanduser().resolve()
        if not path.parent.is_dir():
            ap.error("Report parent must already exist")
        with path.open("x",encoding="utf-8") as file:
            json.dump(output,file,indent=2)
            file.write("\n")
        print("NEW REPORT:",path)
    print("NO SOURCE/CASE/SLURM MODIFICATIONS; NO SCIENCE RELEASE")


if __name__=="__main__":
    main()
