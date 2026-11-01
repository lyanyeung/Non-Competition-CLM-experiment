#!/usr/bin/env python3
"""Read-only Stage56: reconcile all approved detached Batch01 Met candidates.

Seven canonical annual NetCDF replacements, across CA-Cbo, CA-Man, US-Aud.
Verify Stage23 original SHA, candidate SHA, exact approved changed half-hours,
all unchanged fields/times, prior approved-change inheritance, and no overlaps.
This is NOT an input activation, a scientific clearance, or a Slurm submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SITES = ("CA-Cbo", "CA-Man", "US-Aud")
ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5")
HOME = Path("/iridisfs/home/ly3n24/CLM_FATES_PLOTS")
FIELDS = ("TBOT", "QBOT", "SHUM", "RH")
EXPECTED = {
    ("CA-Cbo", 2018): 5,
    ("CA-Man", 1994): 1, ("CA-Man", 2005): 45, ("CA-Man", 2007): 3,
    ("US-Aud", 2012): 1, ("US-Aud", 2019): 3, ("US-Aud", 2023): 6,
}


def check(cond, description):
    if not cond:
        raise ValueError(description)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_json(path):
    path = Path(path).resolve(strict=True)
    return json.loads(path.read_text(encoding="utf-8"))


def rows_prior(report):
    out = []
    for s in report["sites"]:
        for f in s["files"]:
            out.append((s["site"], int(f["year"]), f))
    return out


def rows_files(report):
    return [(f["site"], int(f["year"]), f) for f in report["files"]]


def change_signature(change):
    return (int(change["UTC_index"]),) + tuple(
        round(float(change[key]), 9) for key in
        ("candidate_TA_C", "candidate_VPD_hPa", "candidate_QBOT", "candidate_RH_pct")
    )


def verify_nc(original, candidate, changes, site, year):
    indexes = [int(c["UTC_index"]) for c in changes]
    check(len(indexes) == len(set(indexes)), f"{site} {year}: overlapping half-hours")
    check(all(0 <= idx < 17520 for idx in indexes), f"{site} {year}: invalid UTC index")
    with Dataset(str(original), "r") as a, Dataset(str(candidate), "r") as b:
        check(set(a.variables) == set(b.variables), f"{site} {year}: changed variable set")
        for variable in a.variables:
            av, bv = np.ma.asarray(a[variable][:]), np.ma.asarray(b[variable][:])
            check(av.shape == bv.shape, f"{site} {year}: changed shape {variable}")
            if variable in FIELDS:
                check(av.shape[0] == 17520, f"{site} {year}: unexpected year length")
                mask = np.ones(av.shape[0], dtype=bool)
                mask[indexes] = False
                check(np.ma.allequal(av[mask], bv[mask]),
                      f"{site} {year}: outside-approved change in {variable}")
            else:
                check(np.ma.allequal(av, bv),
                      f"{site} {year}: unauthorized variable change {variable}")
        for c in changes:
            idx = int(c["UTC_index"])
            check(int(c["UTC_year"]) == year and c["site"] == site,
                  f"{site} {year}: change site/year mismatch")
            temperature = float(c["candidate_TA_C"])
            qbot = float(c["candidate_QBOT"])
            rh = float(c["candidate_RH_pct"])
            vpd = float(c["candidate_VPD_hPa"])
            check(170 < temperature + 273.15 < 350 and 0 < qbot < .08 and
                  0 < rh <= 100 and vpd >= 0,
                  f"{site} {year}: nonphysical candidate")
            for field, want in (("TBOT", temperature + 273.15),
                                ("QBOT", qbot), ("SHUM", qbot), ("RH", rh)):
                got = float(b[field][idx, 0, 0])
                check(abs(got - want) < 1e-5,
                      f"{site} {year}: changed-field mismatch {field} at {idx}")
    return len(indexes)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, default=ROOT)
    p.add_argument("--approved", type=Path,
                   default=HOME / "approved_met_candidates.TVqWqlLi/result/manifest.json")
    p.add_argument("--joint", type=Path,
                   default=HOME / "approved_cbo_caman.b5Ve5c8S/result/manifest.json")
    p.add_argument("--merged", type=Path,
                   default=HOME / "approved_q1_cbo.QeDyqeSz/result/manifest.json")
    args = p.parse_args()
    root = args.run.resolve(strict=True)
    old, joint, merged = (checked_json(x) for x in
                          (args.approved, args.joint, args.merged))
    for name, report in (("Stage43", old), ("Stage51", joint), ("Stage54", merged)):
        check(report.get("status") == "DETACHED_NOT_USED_BY_CASES",
              name + ": candidate not marked detached")
    linked_path = Path(joint["linked_CA_Man_2007_13_14_manifest"])
    check(sha256(linked_path) ==
          joint["linked_CA_Man_2007_13_14_manifest_sha256"],
          "CA-Man linked 2007 manifest checksum mismatch")
    linked = checked_json(linked_path)
    check(linked.get("status") == "DETACHED_NOT_USED_BY_CASES" and
          linked.get("site") == "CA-Man" and int(linked["year"]) == 2007,
          "CA-Man linked manifest invalid")
    check(sha256(args.joint) == merged["CA_Cbo_joint_report_sha256"],
          "Stage54 is not based on this exact Stage51 result")
    check(sha256(args.approved) == merged["prior_report_sha256"],
          "Stage54 approved base manifest differs")

    first = rows_prior(old)
    second = rows_files(joint)
    latest = rows_files(merged)
    earlier = first + second + [("CA-Man", 2007, linked)]
    index = {}
    for row in (first + second + latest + [("CA-Man", 2007, linked)]):
        key = row[:2]
        index.setdefault(key, []).append(row[2])
    check(set(index) == set(EXPECTED),
          f"Unexpected site/year inventory {set(index) ^ set(EXPECTED)}")

    # Latest merged CA-Cbo and US-Aud supersede earlier partial candidates;
    # CA-Man uses Stage43 1994 plus Stage51 2005/2007.
    bykey = {
        ("CA-Cbo", 2018): next(f for s, y, f in latest if (s, y) == ("CA-Cbo", 2018)),
        ("CA-Man", 1994): next(f for s, y, f in first if (s, y) == ("CA-Man", 1994)),
        ("CA-Man", 2005): next(f for s, y, f in second if (s, y) == ("CA-Man", 2005)),
        ("CA-Man", 2007): linked,
        ("US-Aud", 2012): next(f for s, y, f in first if (s, y) == ("US-Aud", 2012)),
        ("US-Aud", 2019): next(f for s, y, f in latest if (s, y) == ("US-Aud", 2019)),
        ("US-Aud", 2023): next(f for s, y, f in latest if (s, y) == ("US-Aud", 2023)),
    }
    receipt = checked_json(root / "COMPLETE.json")
    records = {r["site"]: r for r in receipt["sites"]}
    check(set(SITES) <= set(records), "Stage23 receipt missing one or more sites")
    sources = {}
    for site in SITES:
        rec = records[site]
        manifest = Path(rec["manifest"]).resolve(strict=True)
        check(root in manifest.parents and sha256(manifest) == rec["sha256"],
              site + ": Stage23 source manifest invalid")
        details = checked_json(manifest)
        sources[site] = {int(v["year"]): v for v in details["annual_files"]}

    counts = {site: 0 for site in SITES}
    qc0 = []
    canonical = {}
    for (site, year), f in sorted(bykey.items()):
        src = f.get("original", f.get("source"))
        srcsha = f.get("original_sha256", f.get("source_sha256"))
        original = Path(src).resolve(strict=True)
        candidate = Path(f["candidate"]).resolve(strict=True)
        expected = sources[site][year]
        check(root in original.parents and original == Path(expected["path"]).resolve(strict=True),
              f"{site} {year}: non-Stage23 original")
        check(srcsha == expected["sha256"] and sha256(original) == srcsha,
              f"{site} {year}: original SHA mismatch")
        check(sha256(candidate) == f["candidate_sha256"],
              f"{site} {year}: candidate SHA mismatch")
        signatures = {int(c["UTC_index"]): change_signature(c) for c in f["changes"]}
        check(len(signatures) == EXPECTED[(site, year)],
              f"{site} {year}: unexpected number of approved edits")
        for prior in index[(site, year)]:
            for change in prior["changes"]:
                idx = int(change["UTC_index"])
                check(idx in signatures and signatures[idx] == change_signature(change),
                      f"{site} {year}: previously-approved change lost or altered at {idx}")
        count = verify_nc(original, candidate, f["changes"], site, year)
        counts[site] += count
        canonical[(site, year)] = str(candidate)
        if site == "CA-Man" and year == 2005:
            qc0 = [c for c in f["changes"] if float(c.get("original_TA_QC", -1)) == 0]
        print("STAGE56 PASS", site, year, "edits", count,
              "original_sha256", srcsha[:16], "candidate_sha256",
              f["candidate_sha256"][:16], flush=True)
    print("STAGE56 INVENTORY PASS | 7 annual candidates | 64 approved half-hours",
          "| CA-Cbo", counts["CA-Cbo"], "| CA-Man", counts["CA-Man"],
          "| US-Aud", counts["US-Aud"], flush=True)
    print("SCIENCE HOLD | CA-Man 2005 edits with original TA QC0:", len(qc0),
          "| ERA sensitivity must not be silently treated as observed", flush=True)
    print("SCIENCE HOLD | Other unreviewed Met issues, source-height representativeness",
          "and NOAA proxy applicability are NOT cleared by this audit", flush=True)
    print("DETACHED ONLY | no original/active forcing or case modified; no Slurm jobs",
          flush=True)


if __name__ == "__main__":
    main()
