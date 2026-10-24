#!/usr/bin/env python3
"""Batch01 Stage07 — find soil-observation evidence in EXISTING station source files.

READ ONLY: walks each station's existing MY_EC_SITE directory, examines bounded
soil/BIF/ancillary CSV files and relevant members inside ZIP archives without
extracting them. No old surface/NetCDF reads; no network or CIME/Slurm actions.
Writes only new, timestamped HOME inventory JSON/CSV reports. A candidate
keyword hit is NOT a verified soil profile, and missing hits are NOT evidence
that site observations do not exist.

Run:
  python3 -B examples/Batch01_10/scripts/07_inventory_local_soil_evidence_readonly.py --self-test
  python3 -B examples/Batch01_10/scripts/07_inventory_local_soil_evidence_readonly.py
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SITE_ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
SITES = ("CZ-BK1", "IT-Ren", "RU-Fyo", "CH-Dav", "IT-Col", "FR-Fon",
         "FI-Sod", "FR-Pue", "DE-Hai", "BE-Vie")
SCAN_DEPTH = 7
MAX_FILES_PER_SITE = 5000
MAX_ZIPS_PER_SITE = 30
MAX_ZIP_MEMBERS = 5000
MAX_TEXT_BYTES = 2_000_000
MAX_PREVIEW_LINES = 10000
MAX_HITS_PER_FILE = 12
INTERESTING_NAME = re.compile(r"(soil|ancill|bif|badm|metadata)", re.I)
SOIL_VALUE = re.compile(
    r"(?:^|[,_\s\"'])"
    r"(?:SOIL_TEX|SOIL_TEXTURE|SOIL_DEPTH|SOIL_SAND|SOIL_CLAY|"
    r"SAND_PCT|CLAY_PCT|SILT_PCT|PCT_SAND|PCT_CLAY|"
    r"SAND|SILT|CLAY|SOIL_HORIZON|SOIL_PROFILE|COARSE_FRAGMENT)"
    r"(?:[,_\s\"']|$)", re.I
)


def candidates(site):
    root = SITE_ROOT / site
    if not root.is_dir():
        return None, []
    entries = []
    count = 0
    for here, dirs, files in os.walk(root, followlinks=False):
        p = Path(here)
        if len(p.relative_to(root).parts) >= SCAN_DEPTH:
            dirs[:] = []
            continue
        dirs[:] = sorted(
            x for x in dirs
            if not x.startswith(".") and x not in
            ("output", "run", "archive", "hist", "history", "plots", "figures"))
        for name in sorted(files):
            count += 1
            if count > MAX_FILES_PER_SITE:
                return "FILE_SCAN_LIMIT_EXCEEDED", entries
            item = p / name
            if item.is_symlink():
                continue
            suffix = item.suffix.lower()
            if suffix == ".zip":
                entries.append(item)
            elif suffix in (".csv", ".txt", ".tsv") and (
                    INTERESTING_NAME.search(name)):
                entries.append(item)
    return "OK", entries


def text_preview(data):
    text = data.decode("utf-8-sig", errors="replace")
    hits = []
    header = next((line[:350] for line in text.splitlines() if line.strip()), "")
    for idx, line in enumerate(text.splitlines()[:MAX_PREVIEW_LINES], start=1):
        if SOIL_VALUE.search(line):
            hits.append({"line_number": idx, "content": line.strip()[:450]})
            if len(hits) == MAX_HITS_PER_FILE:
                break
    return {"first_nonempty_line": header, "soil_value_keyword_hits": hits}


def scan_plain(path):
    result = {"container": str(path), "kind": "plain_text"}
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            result["status"] = "TEXT_TOO_LARGE"
        else:
            result.update(text_preview(path.read_bytes()))
            result["status"] = "SCANNED"
    except OSError as exc:
        result["status"] = "READ_ERROR: " + str(exc)
    return [result]


def scan_zip(path):
    results = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            members = archive.infolist()
            if len(members) > MAX_ZIP_MEMBERS:
                return [{"container": str(path),
                         "status": "ZIP_MEMBER_LIMIT_EXCEEDED",
                         "number_of_members": len(members)}]
            picked = [
                m for m in members
                if not m.is_dir() and INTERESTING_NAME.search(
                    Path(m.filename).name) and
                Path(m.filename).suffix.lower() in (".csv", ".txt", ".tsv")
            ][:25]
            for m in picked:
                item = {"container": str(path), "kind": "zip_member",
                        "member": m.filename, "uncompressed_bytes": m.file_size}
                if m.file_size > MAX_TEXT_BYTES:
                    item["status"] = "MEMBER_TOO_LARGE"
                else:
                    with archive.open(m) as stream:
                        data = stream.read(MAX_TEXT_BYTES + 1)
                    if len(data) > MAX_TEXT_BYTES:
                        item["status"] = "DECOMPRESSED_TOO_LARGE"
                    else:
                        item.update(text_preview(data))
                        item["status"] = "SCANNED"
                results.append(item)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        results.append({"container": str(path), "status": "ZIP_ERROR: " + str(exc)})
    return results


def run():
    rows = []
    site_details = []
    print("BATCH01 STAGE07 | EXISTING STATION SOIL EVIDENCE | READ ONLY")
    print("Candidate keyword hits are not approved numerical soil measurements.")
    for site in SITES:
        status, files = candidates(site)
        examined = []
        zips = 0
        for file in files:
            if file.suffix.lower() == ".zip":
                zips += 1
                if zips > MAX_ZIPS_PER_SITE:
                    continue
                examined.extend(scan_zip(file))
            else:
                examined.extend(scan_plain(file))
        keyword_files = [
            x for x in examined if x.get("soil_value_keyword_hits")]
        rows.append({
            "site": site, "scan_status": status,
            "source_candidates": len(files),
            "scanned_entries_or_zip_members": len(examined),
            "entries_with_soil_keywords": len(keyword_files),
            "soil_texture_accepted": "NO_NOT_VERIFIED",
        })
        site_details.append({
            "site": site, "scan_status": status,
            "candidate_paths": list(map(str, files[:100])),
            "examined": examined[:180], "keyword_hit_entries": keyword_files[:50],
            "next_action": "CHECK_UNIT_DEPTH_DENOMINATOR_SITE_AND_SOURCE; "
                           "NO_GRID_FALLBACK",
        })
        print(f"{site:<8} sources={len(files):>3} "
              f"inspected={len(examined):>3} soil_keyword_entries={len(keyword_files):>3} "
              f"scan={status}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path.home().resolve() / ("Batch01_10_stage07_soil_discovery_" + stamp)
    out.mkdir(mode=0o700, exist_ok=False)
    (out / "all_sites.json").write_text(
        json.dumps({"run_utc": datetime.now(timezone.utc).isoformat(),
                    "original_files_modified": False,
                    "no_old_surface_used": True,
                    "no_slurm_action": True,
                    "sites": site_details},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    with (out / "summary.csv").open("x", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("SUMMARY:", out / "summary.csv")
    print("DETAIL:", out / "all_sites.json")
    print("NO MODEL INPUTS MODIFIED. NO AD SUBMITTED.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        assert len(SITES) == len(set(SITES)) == 10
        assert SOIL_VALUE.search("SOIL_TEX,3,0.1,0.2")
        assert SOIL_VALUE.search("depth,soil_sand,soil_clay")
        assert not SOIL_VALUE.search("TA_F,25")
        print("STAGE07 SELF-TEST PASS: source names and soil keyword recognizer")
        return
    run()


if __name__ == "__main__":
    main()
