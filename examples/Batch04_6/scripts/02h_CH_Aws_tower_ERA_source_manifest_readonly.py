#!/usr/bin/env python3
"""ICOS Batch04 Stage02H — source discovery + CH-Aws priority events (READ ONLY).

Input: existing Stage02E QBOT differences + Stage02G unique-RH episodes.
Discover potential original tower/ERA evidence under one CH-Aws forcing tree
without reading all source data, or inferring their scientific suitability.
Rank a bounded manifest of top QBOT change half-hours and RH episodes.
This is a provenance DISCOVERY gate, not native-tower/ERA5 pairing/QC.
Only --out-dir writes new reports into an existing EMPTY HOME directory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import os
from pathlib import Path
import tarfile
import zipfile

STAGE_E = "STAGE02E_CH_AWS_QBOT_VARIANT_DIFF"
STAGE_G = "STAGE02G_CH_AWS_UNIQUE_SUPERSATURATION_EVENT_QC"
ALLOWED_EXT = (".zip", ".csv", ".csv.gz", ".txt", ".nc", ".nc4", ".json",
               ".xlsx", ".xls", ".gz", ".tar", ".tar.gz", ".tgz", ".md")
STOP_DIRS = {".git", "__pycache__", ".cache", "outputs", "logs", "archive"}
MAX_VISIT = 12000
MAX_MANIFEST = 650
MAX_ARCHIVE_NAMES = 40
MAX_DEPTH = 5
MAX_CSV_SIZE = 50_000_000
EVENT_FIELDS = ["year", "half_hour_index", "time", "qbot_abs_delta_gkg",
                "vapour_pressure_abs_delta_hPa", "candidate_cases", "candidate_file",
                "original_case_is_scientifically_approved", "native_tower_QC_status",
                "ERA5_evidence_status"]


def verify_reports(e, g):
    if not isinstance(e, dict) or e.get("stage") != STAGE_E:
        raise ValueError("Expected verified Stage02E QBOT report JSON")
    if e.get("science_release") is not False or e.get("baseline_only_not_scientific_selection") is not True:
        raise ValueError("Stage02E baseline must remain an unapproved comparator")
    if len(e.get("year_reports", [])) != 19:
        raise ValueError("Stage02E must contain 19 complete annual reports")
    if not isinstance(g, dict) or g.get("stage") != STAGE_G:
        raise ValueError("Expected verified Stage02G unique RH report JSON")
    if g.get("science_release") is not False or g.get("stage02f_year_mismatch") != []:
        raise ValueError("Stage02G source QC state/matches are not acceptable")
    if len(g.get("annual_reports", [])) != 19:
        raise ValueError("Stage02G must contain 19 annual reports")
    years_e = sorted(x.get("year") for x in e["year_reports"])
    years_g = sorted(x.get("year") for x in g["annual_reports"])
    if years_e != list(range(2006, 2025)) or years_g != years_e:
        raise ValueError("Stage02E and Stage02G year sets differ")
    if sum(x.get("unique_union_RH_water_gt100_HH", 0)
           for x in g["annual_reports"]) != g.get("total_unique_flagged_year_HH"):
        raise ValueError("Stage02G unique annual RH count mismatch")


def qb_events(e):
    rows = {}
    for year in e["year_reports"]:
        y = year["year"]
        for compare in year.get("comparisons", []):
            if compare.get("comparison_status") != "ALIGNED":
                raise ValueError("Stage02E unaligned QBOT candidate comparison")
            for point in compare.get("largest_5_HH", []):
                i = point.get("index")
                if not isinstance(i, int) or not 0 <= i < 17520:
                    raise ValueError("Bad half-hour position")
                key = (y, i)
                cur = rows.get(key)
                change = abs(float(point["delta_QBOT_gkg"]))
                candidate = {
                    "year": y, "half_hour_index": i,
                    "time": point.get("time", ""),
                    "qbot_abs_delta_gkg": change,
                    "vapour_pressure_abs_delta_hPa": abs(float(point["delta_vapor_pressure_hPa"])),
                    "candidate_cases": ",".join(compare.get("cases", [])),
                    "candidate_file": compare.get("path", ""),
                    "original_case_is_scientifically_approved": False,
                    "native_tower_QC_status": "NOT_CHECKED",
                    "ERA5_evidence_status": "NOT_CHECKED"
                }
                if cur is None or (change, candidate["vapour_pressure_abs_delta_hPa"]) > (
                        cur["qbot_abs_delta_gkg"], cur["vapour_pressure_abs_delta_hPa"]):
                    rows[key] = candidate
    return sorted(rows.values(), key=lambda row:(
        -row["vapour_pressure_abs_delta_hPa"], -row["qbot_abs_delta_gkg"],
        row["year"], row["half_hour_index"]))


def rh_episodes(g):
    result = []
    for year in g["annual_reports"]:
        for episode in year.get("longest_12_union_episodes", []):
            result.append({
                "year": year["year"], **episode,
                "native_tower_RH_QC_verified": False,
                "ERA5_source_verified": False,
                "status": "HOLD_SOURCE_PROVENANCE"
            })
    return sorted(result, key=lambda x: (-x.get("n_HH", 0),
                                         -x.get("maximum_RH_water_pct", 0),
                                         x["year"]))


def file_kind(name):
    n = name.lower()
    for ext in sorted(ALLOWED_EXT, key=len, reverse=True):
        if n.endswith(ext):
            return ext
    return None


def archive_member_examples(path, kind):
    result = {"members": [], "archive_status": "NOT_INSPECTED"}
    try:
        if kind == ".zip":
            with zipfile.ZipFile(path, "r") as f:
                members = f.namelist()
                result["archive_members_total"] = len(members)
                result["members"] = members[:MAX_ARCHIVE_NAMES]
                result["archive_status"] = "NAMES_READ"
        elif kind in (".tar", ".tar.gz", ".tgz"):
            # Tar archives may require full decompression to list all; only
            # inspect small archives; no extract and no external commands.
            if path.stat().st_size > 50_000_000:
                result["archive_status"] = "SKIPPED_TAR_OVER_50MB"
            else:
                with tarfile.open(path, "r:*") as f:
                    names = [m.name for m in f if m.isfile()]
                    result["archive_members_total"] = len(names)
                    result["members"] = names[:MAX_ARCHIVE_NAMES]
                    result["archive_status"] = "NAMES_READ"
    except Exception as exc:
        result["archive_status"] = type(exc).__name__ + ": " + str(exc)
    return result


def discover(root):
    if not root.is_dir():
        raise FileNotFoundError("Expected existing CH-Aws forcing directory: " + str(root))
    visited = 0
    all_count = collections.Counter()
    candidates = []
    truncated = False
    baseparts = len(root.parts)
    for folder, dirs, files in os.walk(root, topdown=True, followlinks=False):
        level = len(Path(folder).parts) - baseparts
        dirs[:] = [d for d in sorted(dirs)
                   if d not in STOP_DIRS and not (Path(folder) / d).is_symlink()] if level < MAX_DEPTH else []
        for name in sorted(files):
            visited += 1
            if visited > MAX_VISIT:
                truncated = True
                break
            kind = file_kind(name)
            if kind is None:
                continue
            p = Path(folder) / name
            if not p.is_file():
                continue
            all_count[kind] += 1
            # Full DATM NC paths already pinned in Stage02C; inventory
            # only original-package/metadata files and avoid huge log content.
            if kind in (".nc", ".nc4") or len(candidates) >= MAX_MANIFEST:
                continue
            row = {"path": str(p), "relative_path": str(p.relative_to(root)),
                   "bytes": p.stat().st_size, "extension": kind}
            if kind in (".zip", ".tar", ".tar.gz", ".tgz"):
                row["archive"] = archive_member_examples(p, kind)
            elif kind == ".csv" and p.stat().st_size <= MAX_CSV_SIZE:
                try:
                    with p.open("r", encoding="utf-8-sig", errors="replace") as f:
                        row["header_excerpt"] = f.readline(4096).strip()[:4096]
                except Exception as exc:
                    row["header_error"] = type(exc).__name__ + ": " + str(exc)
            candidates.append(row)
        if truncated:
            break
    return {
        "root": str(root),
        "files_seen": visited, "listing_truncated": truncated,
        "file_type_counts_in_scanned_tree": dict(all_count),
        "candidate_source_or_metadata_files": candidates,
        "candidate_manifest_truncated": len(candidates) >= MAX_MANIFEST,
        "interpretation": "Presence, archive-member filenames or CSV columns are NOT proof of tower QC/ERA5 provenance"
    }


def selftest():
    fake_e = {
        "stage": STAGE_E, "science_release":False,
        "baseline_only_not_scientific_selection":True,
        "year_reports":[{"year":y,"comparisons":[{
            "comparison_status":"ALIGNED","cases":["CH-Aws_TEST"],
            "path":"/fake/CH-Aws_DATM_2007.nc",
            "largest_5_HH":[{"index":4,"time":"test",
            "delta_QBOT_gkg":0.2,
            "delta_vapor_pressure_hPa":0.3}] if y==2007 else []
        }]} for y in range(2006,2025)]
    }
    fake_g = {
        "stage": STAGE_G, "science_release":False,
        "stage02f_year_mismatch":[],
        "total_unique_flagged_year_HH":1,
        "annual_reports":[{"year":y,
            "unique_union_RH_water_gt100_HH":1 if y==2021 else 0,
            "longest_12_union_episodes":[
                {"start":"2021-01-01","end":"2021-01-01",
                 "n_HH":1,"maximum_RH_water_pct":100.01}
            ] if y==2021 else []} for y in range(2006,2025)]
    }
    verify_reports(fake_e, fake_g)
    events = qb_events(fake_e)
    assert len(events)==1 and events[0]["year"]==2007
    assert len(rh_episodes(fake_g))==1
    assert file_kind("AMF_CH-Aws_MET.csv.gz")==".csv.gz"
    print("STAGE02H SELF-TEST PASS: 19-year E/G source markers, risk-event ordering, safe file-classification; NO WRITES")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--stage02e", type=Path)
    ap.add_argument("--stage02g", type=Path)
    ap.add_argument("--forcing-root", type=Path,
                    default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing"))
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--event-limit", type=int, default=80,
                    help="Top unique QBOT event timestamps in CSV (1..500)")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        return
    if not 1 <= args.event_limit <= 500:
        ap.error("--event-limit must be 1..500")
    if not args.stage02e or not args.stage02e.is_file():
        ap.error("--stage02e missing")
    if not args.stage02g or not args.stage02g.is_file():
        ap.error("--stage02g missing")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must already exist and be EMPTY")
    e = json.loads(args.stage02e.read_text(encoding="utf-8"))
    g = json.loads(args.stage02g.read_text(encoding="utf-8"))
    verify_reports(e,g)
    events = qb_events(e)
    eps = rh_episodes(g)
    sources = discover(args.forcing_root)
    output = {
        "stage": "STAGE02H_CH_AWS_SOURCE_DISCOVERY_AND_EVENT_PRIORITISATION",
        "read_only": True, "scientific_release": False,
        "native_tower_data_validated": False, "ERA5_collocation_validated": False,
        "source_modified": False, "slurm_submitted": False,
        "stage02e": str(args.stage02e), "stage02g": str(args.stage02g),
        "source_manifest": sources,
        "qbot_unique_top_event_candidates_total": len(events),
        "qbot_top_events": events[:args.event_limit],
        "rh_episodes_ranked": eps[:50],
        "scope": "Read-only discovery only; do not interpret file names as tower/ERA source science evidence.",
    }
    out = args.out_dir / "stage02h_source_event_manifest.json"
    csvpath = args.out_dir / "stage02h_ranked_QBOT_HH.csv"
    with out.open("x", encoding="utf-8") as h:
        json.dump(output,h,indent=2)
        h.write("\n")
    with csvpath.open("x", encoding="utf-8", newline="") as h:
        writer=csv.DictWriter(h,fieldnames=EVENT_FIELDS)
        writer.writeheader()
        writer.writerows(events[:args.event_limit])
    print("CH_AWS_SOURCE_ROOT", sources["root"])
    print("FILES_SEEN", sources["files_seen"], "TRUNCATED", sources["listing_truncated"])
    print("FILE_TYPES",json.dumps(sources["file_type_counts_in_scanned_tree"],sort_keys=True))
    for x in sources["candidate_source_or_metadata_files"][:25]:
        print(" SOURCE_CANDIDATE",x["relative_path"],"SIZE_BYTES",x["bytes"],
              "ARCHIVE_MEMBERS",x.get("archive",{}).get("archive_members_total","NA"))
    for row in events[:15]:
        print(" QBOT_EVENT",row["year"],row["time"],
              "DELTA_GKG",round(row["qbot_abs_delta_gkg"],6),
              "DELTA_HPA",round(row["vapour_pressure_abs_delta_hPa"],6),
              "CANDIDATE",row["candidate_cases"])
    for row in eps[:10]:
        print(" RH_EPISODE",row["year"],row["start"],"DURATION_HH",
              row["n_HH"],"MAX_RH",row["maximum_RH_water_pct"])
    print("NEW_JSON",out)
    print("NEW_CSV",csvpath)
    print("ALL DATA/CASE/ERA SCIENCE GATES HOLD; NO SOURCE/SLURM WRITES")


if __name__=="__main__":
    main()
