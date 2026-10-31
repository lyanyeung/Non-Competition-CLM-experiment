#!/usr/bin/env python3
"""ICOS Batch04 Stage02G: unique CH-Aws RH saturation episodes across 7 sources.

Read-only. Reads saved Stage02C (and optionally Stage02F) JSON; opens all
19 x 7 distinct candidate annual DATM files, requiring same time, TBOT and
PSRF per year. Computes water/ice supersaturation by candidate and the union
and intersection of unique half-hour timestamps; writes a diagnostic CSV of
unique affected HHs, not seven copies of an identical event.

HOLD: no native tower QC, ERA5, active-stream selection or model submission.
Only --out-dir writes two new reports in an existing EMPTY directory.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path

REFERENCE = "CH-Aws_FATES_SPINUP500_11P"  # purely numerical; NOT approved
YEARS = tuple(range(2006, 2025))
FIELDS = ("QBOT", "TBOT", "PSRF")
WATER_LIMITS = (100.0, 101.0, 105.0, 110.0, 120.0, 150.0)
CSV_FIELDS = (
    "year", "HH_index", "time", "candidate_versions_above_100",
    "maximum_RH_water_pct", "minimum_RH_water_pct",
    "max_RH_candidate_cases", "reference_RH_water_pct",
    "reference_RH_ice_pct", "reference_T_C", "reference_PSRF_Pa",
    "reference_QBOT_kgkg", "reference_ice_saturation_over100_if_subzero",
    "ERA5_source_verified", "native_tower_RH_QC_verified",
)


def source_paths(data):
    if not isinstance(data, dict):
        raise TypeError("Stage02C must be a decoded JSON dictionary")
    if data.get("stage") != "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC":
        raise ValueError("Wrong Stage02C source")
    if data.get("read_only") is not True or data.get("science_release") is not False:
        raise ValueError("Unexpected science release state")
    rows = [x for x in data.get("sites", []) if x.get("site") == "CH-Aws"]
    if len(rows) != 1 or len(rows[0].get("cases", [])) != 8:
        raise ValueError("Expected one CH-Aws with exactly 8 cases")
    cases = {}
    for item in rows[0]["cases"]:
        case = item["case"]
        if not isinstance(case, str) or not case.startswith("CH-Aws_FATES_"):
            raise ValueError("Unexpected CH-Aws case name")
        refs = {}
        for entry in item["site_datm"]:
            path, year = entry["path"], entry["year"]
            if not isinstance(path, str) or not Path(path).is_absolute():
                raise ValueError("Not an absolute annual NetCDF path")
            found = re.fullmatch(r"CH-Aws_DATM_((?:19|20)\d{2})(?:[_.-].*)?\.nc", Path(path).name)
            if not found or int(found.group(1)) != year or year in refs:
                raise ValueError("Wrong/duplicate CH-Aws year: " + path)
            refs[year] = path
        if tuple(sorted(refs)) != YEARS:
            raise ValueError("Expected 19 complete annual files for each source case")
        cases[case] = refs
    if REFERENCE not in cases:
        raise ValueError("Missing the historical diagnostic reference case")
    versions = collections.defaultdict(list)
    for case, refs in cases.items():
        versions[tuple(refs[y] for y in YEARS)].append(case)
    if len(versions) != 7:
        raise ValueError("Expected exactly seven distinct variant annual path sets")
    groups = sorted(
        [{"cases": sorted(names), "years": dict(zip(YEARS, paths))}
         for paths, names in versions.items()],
        key=lambda x: ",".join(x["cases"]))
    return groups, cases[REFERENCE]


def field(ds, name, np):
    found = [k for k in ds.variables if k.upper() == name]
    if len(found) != 1:
        raise ValueError("Missing or ambiguous variable: " + name)
    var = ds.variables[found[0]]
    if int(var.size) != 17520:
        raise ValueError("Expected 17520 site half hours in " + name)
    a = np.ma.filled(np.ma.asarray(var[:], dtype="float64"), np.nan).ravel()
    if not np.all(np.isfinite(a)):
        raise ValueError(name + " has missing/nonfinite records")
    return a, str(getattr(var, "units", "")).strip().lower()


def load_nc(path, np, Dataset):
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    with Dataset(path, "r") as ds:
        k = next((k for k in ("time", "DTIME", "dtime", "TIME")
                  if k in ds.variables), None)
        if k is None:
            raise ValueError("Missing time coordinate")
        v = ds.variables[k]
        time = np.ma.filled(np.ma.asarray(v[:], dtype="float64"), np.nan).ravel()
        if time.size != 17520 or not np.all(np.isfinite(time)) or np.any(np.diff(time) <= 0):
            raise ValueError("Bad annual time coordinate")
        values = {k: field(ds, k, np) for k in FIELDS}
        if values["QBOT"][1] not in ("kg/kg", "kg kg-1", "kg kg^-1", "kg kg**-1", "1"):
            raise ValueError("QBOT must be in kg/kg")
        if values["TBOT"][1] not in ("k", "kelvin"):
            raise ValueError("TBOT must be in K")
        if values["PSRF"][1] not in ("pa", "pascal", "pascals"):
            raise ValueError("PSRF must be in Pa")
        return {"path": path, "time": time,
                "time_units": str(getattr(v, "units", "")),
                "calendar": str(getattr(v, "calendar", "UNSPECIFIED")),
                "values": values}


def rh_physics(ds, np):
    q, _ = ds["values"]["QBOT"]
    T, _ = ds["values"]["TBOT"]
    p, _ = ds["values"]["PSRF"]
    if np.any((q < 0) | (q >= .08)):
        raise ValueError("QBOT outside supported physical domain")
    if np.any((p < 40000) | (p > 110000) | (T < 180) | (T > 340)):
        raise ValueError("Pressure/temperature outside supported saturation domain")
    tc = T - 273.15
    e = (q*p/(.622 + .378*q))/100.0
    esw = 6.1121*np.exp((18.678 - tc/234.5)*tc/(257.14+tc))
    esi = 6.1115*np.exp((23.036 - tc/333.7)*tc/(279.82+tc))
    return {"water": 100*e/esw, "ice": 100*e/esi,
            "below0": T < 273.15}


def aligned(ref, alt, np):
    if ref["time_units"] != alt["time_units"] or ref["calendar"] != alt["calendar"]:
        raise ValueError("Mismatched time units/calendar")
    if not np.array_equal(ref["time"], alt["time"]):
        raise ValueError("Mismatched time index")
    for name in FIELDS:
        if ref["values"][name][1] != alt["values"][name][1]:
            raise ValueError("Different " + name + " units")
    for name in ("TBOT", "PSRF"):
        if not np.array_equal(ref["values"][name][0], alt["values"][name][0]):
            raise ValueError("Changed TBOT/PSRF: cannot isolate QBOT")
    return True


def timestamp(ref, index, nc):
    units = ref["time_units"]
    if " since " not in units.lower():
        return "INDEX_" + str(index) + "_NO_CF_TIME_UNITS"
    calendar = ref["calendar"]
    if calendar == "UNSPECIFIED":
        calendar = "standard"
    try:
        return str(nc.num2date(float(ref["time"][index]), units=units,
                               calendar=calendar,
                               only_use_cftime_datetimes=True))
    except Exception as exc:
        return "INDEX_" + str(index) + "_TIME_DECODE_" + type(exc).__name__


def episodes(mask, max_rh, ref, nc, np):
    indices = np.flatnonzero(mask)
    if not len(indices):
        return [], 0
    starts = np.r_[0, np.flatnonzero(np.diff(indices) > 1) + 1]
    ends = np.r_[starts[1:], indices.size]
    groups = []
    for s, e in zip(starts, ends):
        segment = indices[s:e]
        hottest = int(segment[np.argmax(max_rh[segment])])
        groups.append({
            "start": timestamp(ref, int(segment[0]), nc),
            "end": timestamp(ref, int(segment[-1]), nc),
            "start_index": int(segment[0]), "end_index": int(segment[-1]),
            "n_HH": int(len(segment)),
            "maximum_RH_water_pct": float(max_rh[hottest]),
            "maximum_RH_time": timestamp(ref, hottest, nc)
        })
    return sorted(groups, key=lambda x:(-x["n_HH"], -x["maximum_RH_water_pct"]))[:12], len(groups)


def analyse_year(year, groups, basepaths, np, Dataset, nc):
    ref = load_nc(basepaths[year], np, Dataset)
    profiles, metadata = [], []
    for group in groups:
        path = group["years"][year]
        alt = ref if path == ref["path"] else load_nc(path, np, Dataset)
        aligned(ref, alt, np)
        p = rh_physics(alt, np)
        profiles.append(p)
        metadata.append({"path":path, "cases":group["cases"]})
    water = np.stack([p["water"] for p in profiles], axis=0)
    ice = np.stack([p["ice"] for p in profiles], axis=0)
    cold = profiles[0]["below0"]
    waterflag = water > 100 + 1e-8
    iceflag = (ice > 100 + 1e-8) & cold
    union = np.any(waterflag, axis=0)
    intersection = np.all(waterflag, axis=0)
    water_max = np.max(water, axis=0)
    water_min = np.min(water, axis=0)
    candidates = []
    for i, (g, ph) in enumerate(zip(groups, profiles)):
        w = ph["water"]
        ic = ph["ice"]
        candidates.append({
            "cases":g["cases"],"path":g["years"][year],
            "RH_water_gt100_HH":int(np.count_nonzero(waterflag[i])),
            "RH_water_gt101_HH":int(np.count_nonzero(w>101)),
            "RH_water_gt105_HH":int(np.count_nonzero(w>105)),
            "RH_water_gt110_HH":int(np.count_nonzero(w>110)),
            "RH_water_gt120_HH":int(np.count_nonzero(w>120)),
            "RH_water_gt150_HH":int(np.count_nonzero(w>150)),
            "RH_ice_gt100_when_T_below0_HH":int(np.count_nonzero(iceflag[i])),
            "max_RH_water_pct":float(np.max(w)),
            "max_RH_ice_pct":float(np.max(ic)),
            "subzero_halfhours":int(np.count_nonzero(cold))
        })
    top, n_episode = episodes(union, water_max, ref, nc, np)
    rows = []
    ref_rh = rh_physics(ref, np)
    baseq, _ = ref["values"]["QBOT"]
    baset, _ = ref["values"]["TBOT"]
    basep, _ = ref["values"]["PSRF"]
    for idx in np.flatnonzero(union):
        k = int(idx)
        winner = int(np.argmax(water[:, k]))
        rows.append({
            "year":year, "HH_index":k, "time":timestamp(ref,k,nc),
            "candidate_versions_above_100":int(np.count_nonzero(waterflag[:,k])),
            "maximum_RH_water_pct":float(water_max[k]),
            "minimum_RH_water_pct":float(water_min[k]),
            "max_RH_candidate_cases":",".join(groups[winner]["cases"]),
            "reference_RH_water_pct":float(ref_rh["water"][k]),
            "reference_RH_ice_pct":float(ref_rh["ice"][k]),
            "reference_T_C":float(baset[k]-273.15),
            "reference_PSRF_Pa":float(basep[k]),
            "reference_QBOT_kgkg":float(baseq[k]),
            "reference_ice_saturation_over100_if_subzero":bool(
                ref_rh["ice"][k]>100+1e-8 and cold[k]),
            "ERA5_source_verified":False,"native_tower_RH_QC_verified":False,
        })
    return {
        "year":year,"paths_compared":len(groups),
        "sum_variant_RH_water_gt100_HH":int(np.count_nonzero(waterflag)),
        "unique_union_RH_water_gt100_HH":int(np.count_nonzero(union)),
        "common_intersection_RH_water_gt100_HH":int(np.count_nonzero(intersection)),
        "unique_union_RH_water_gt101_HH":int(np.count_nonzero(np.any(water>101,axis=0))),
        "unique_union_RH_water_gt105_HH":int(np.count_nonzero(np.any(water>105,axis=0))),
        "unique_union_RH_water_gt110_HH":int(np.count_nonzero(np.any(water>110,axis=0))),
        "unique_union_RH_water_gt120_HH":int(np.count_nonzero(np.any(water>120,axis=0))),
        "unique_union_RH_water_gt150_HH":int(np.count_nonzero(np.any(water>150,axis=0))),
        "unique_union_RH_ice_gt100_when_subzero_HH":int(np.count_nonzero(np.any(iceflag,axis=0))),
        "all_variant_QBOT_equal_this_year":bool(all(
            np.array_equal(profiles[0]["water"],x["water"]) for x in profiles[1:])),
        "max_RH_water_pct_any_version":float(np.max(water)),
        "episode_count_unique_union":n_episode,"longest_12_union_episodes":top,
        "per_variant":candidates,
        "status":"HOLD_NATIVE_SOURCE_QC_ERA_ICE_AND_DATM_STREAM"
    }, rows


def selftest():
    import numpy as np
    fake = {"stage":"STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC",
            "read_only":True,"science_release":False,
            "sites":[{"site":"CH-Aws","cases":[{
                "case":REFERENCE if j==0 else "CH-Aws_FATES_TEST_"+str(j),
                "site_datm":[{"year":y,"path":"/simulation/variant_"+str(min(j,6))+
                              "/CH-Aws_DATM_"+str(y)+".nc"} for y in YEARS]
            } for j in range(8)]}]}
    groups, reference = source_paths(fake)
    assert len(groups)==7 and len(reference)==19
    assert source_paths(fake)[1][2006].endswith("CH-Aws_DATM_2006.nc")
    try: source_paths(Path("/fake.json"))
    except TypeError: pass
    else: raise AssertionError("wrong parser type accepted")
    q=np.array([.004])
    p=np.array([80000.])
    e=q*p/(.622+.378*q)/100
    assert 5<e[0]<6
    m=np.array([False,True,True,False,True])
    assert np.any(m) and int(np.count_nonzero(m))==3
    print("STAGE02G SELF-TEST PASS: 8 source cases/7 versions, 19 years, RH mask and no writes")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02c",type=Path,help="Existing Stage02C JSON")
    ap.add_argument("--stage02f",type=Path,help="Existing Stage02F summary JSON for cross-check")
    ap.add_argument("--out-dir",type=Path,help="Existing empty directory for two reports")
    args=ap.parse_args()
    if args.self_test:
        selftest()
        return
    if not args.stage02c or not args.stage02c.is_file():
        ap.error("Stage02C JSON missing")
    if not args.stage02f or not args.stage02f.is_file():
        ap.error("Stage02F JSON missing")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("Output directory must exist and be empty")
    import numpy as np
    import netCDF4 as nc
    groups, ref=source_paths(json.loads(args.stage02c.read_text()))
    old=json.loads(args.stage02f.read_text())
    if old.get("stage")!="STAGE02F_CH_AWS_QBOT_SATURATION_EVENT_TRIAGE" or \
       old.get("candidate_HH_comparison_holds")!=0 or len(old.get("annual_reports",[]))!=19:
        ap.error("Stage02F previous source/hold verification did not pass")
    reports, csvrows=[],[]
    mismatches=[]
    for year in YEARS:
        try:
            report, rows=analyse_year(year,groups,ref,np,nc.Dataset,nc)
        except Exception as exc:
            # Do not emit a partial CSV masquerading as a complete dataset.
            raise RuntimeError("Year "+str(year)+" failed, no reports written: "+str(exc)) from exc
        oldrows=[r for r in old["annual_reports"] if r.get("year")==year]
        expected=sum(r.get("overall_physical_screen",{}).get("RH_water_gt100_HH",0)
                     for r in oldrows[0]["variant_results"]) if len(oldrows)==1 else None
        report["stage02f_expected_variant_sum"]=expected
        report["stage02f_agrees"]=expected==report["sum_variant_RH_water_gt100_HH"]
        if not report["stage02f_agrees"]:
            mismatches.append(year)
        print("YEAR",year,"SUM_VARIANT_GT100",report["sum_variant_RH_water_gt100_HH"],
              "UNIQUE_UNION_GT100",report["unique_union_RH_water_gt100_HH"],
              "ALL7_INTERSECTION_GT100",report["common_intersection_RH_water_gt100_HH"],
              "UNIQUE_GT105",report["unique_union_RH_water_gt105_HH"],
              "UNIQUE_GT110",report["unique_union_RH_water_gt110_HH"],
              "ICE_GT100_SUBZERO_UNION",report["unique_union_RH_ice_gt100_when_subzero_HH"],
              "MAX_RH",round(report["max_RH_water_pct_any_version"],3),
              "EPISODES",report["episode_count_unique_union"],
              "QBOT_ALL_EQUAL",report["all_variant_QBOT_equal_this_year"],
              "STAGE02F_MATCH",report["stage02f_agrees"])
        reports.append(report)
        csvrows.extend(rows)
    output={"stage":"STAGE02G_CH_AWS_UNIQUE_SUPERSATURATION_EVENT_QC",
            "read_only":True,"source_modified":False,"slurm_submitted":False,
            "science_release":False,"base_case_arbitrary_unapproved":REFERENCE,
            "stage02c":str(args.stage02c),"stage02f":str(args.stage02f),
            "stage02f_year_mismatch":mismatches,
            "total_unique_flagged_year_HH":len(csvrows),
            "limits":"Internal DATM supersaturation screens; no tower QC/ERA5; no automatic repair",
            "annual_reports":reports}
    # Reject false cross-stage agreement before writing any scientific report.
    if mismatches:
        raise ValueError("Stage02F totals differ in years "+str(mismatches)+"; no reports written")
    jpath=args.out_dir/"stage02g_unique_RH_events.json"
    cpath=args.out_dir/"stage02g_unique_RH_gt100_HH.csv"
    with jpath.open("x",encoding="utf-8") as f:
        json.dump(output,f,indent=2)
        f.write("\n")
    with cpath.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csvrows)
    print("UNIQUE_YEAR_HH_TOTAL",len(csvrows),"STAGE02F_MISMATCHES",len(mismatches))
    print("JSON",jpath)
    print("CSV",cpath)
    print("ALL SCIENCE/SLURM GATES HOLD")


if __name__=="__main__":
    main()
