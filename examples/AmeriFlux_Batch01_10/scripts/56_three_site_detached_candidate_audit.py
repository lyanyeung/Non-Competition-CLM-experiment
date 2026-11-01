#!/usr/bin/env python3
"""READ-ONLY audit of three-site Batch01 detached Met candidates.

Reconcile the user-approved Stage43, Stage51 (+ its linked 2007 CA-Man file),
and Stage54 records by site/year. Stage54/51 output supersedes Stage43 only
when every earlier approved changed index is preserved. Check original Stage23
file hashes, candidate SHA256, all unmodified variables and all unapproved
time indices, plus candidate physical-field readback.

This audit DOES NOT select a scientifically approved case forcing dataset.
It does not write a NetCDF, change a CIME case, or submit Slurm jobs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SITES = ("CA-Cbo", "CA-Man", "US-Aud")
STAGE23 = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5")
HOME_OUT = Path("/iridisfs/home/ly3n24/CLM_FATES_PLOTS")
INITIAL_APPROVED = HOME_OUT / "approved_met_candidates.TVqWqlLi/result/manifest.json"
STAGE51 = HOME_OUT / "approved_cbo_caman.b5Ve5c8S/result/manifest.json"
STAGE54 = HOME_OUT / "approved_q1_cbo.QeDyqeSz/result/manifest.json"
EXPECTED = {
    ("CA-Cbo", 2018): 5,
    ("CA-Man", 1994): 1,
    ("CA-Man", 2005): 45,
    ("CA-Man", 2007): 3,
    ("US-Aud", 2012): 1,
    ("US-Aud", 2019): 3,
    ("US-Aud", 2023): 6,
}
MET_FIELDS = ("TBOT", "QBOT", "SHUM", "RH")


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda: f.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def manifest(p: Path, label: str) -> dict:
    p = p.resolve(strict=True)
    j = json.loads(p.read_text())
    if j.get("status") != "DETACHED_NOT_USED_BY_CASES":
        raise ValueError(label + ": not a verified detached source")
    print("MANIFEST", label, p, "SHA256", digest(p), flush=True)
    return j


def from_stage43(j: dict) -> dict:
    d = {}
    for site in j["sites"]:
        s = site["site"]
        if s not in SITES:
            raise ValueError("Unexpected Stage43 site " + str(s))
        for f in site["files"]:
            key = (s, int(f["year"]))
            if key in d:
                raise ValueError("Duplicate Stage43 " + str(key))
            d[key] = f
    return d


def from_files(j: dict) -> dict:
    d = {}
    for f in j["files"]:
        key = (f["site"], int(f["year"]))
        if key in d:
            raise ValueError("Duplicate manifest entry " + str(key))
        d[key] = f
    return d


def changes(f: dict) -> dict:
    vals = {}
    for row in f["changes"]:
        i = int(row["UTC_index"])
        if i in vals:
            raise ValueError("Duplicate changed index " + str(i))
        vals[i] = row
    return vals


def same_previous(prior: dict, later: dict, site: str, year: int) -> None:
    a, b = changes(prior), changes(later)
    if not a.keys() <= b.keys():
        raise ValueError(f"{site} {year}: previously approved indices dropped {sorted(a.keys()-b.keys())}")
    for i, old in a.items():
        new = b[i]
        for field in ("time_local", "candidate_TA_C", "candidate_QBOT", "candidate_RH_pct", "candidate_VPD_hPa"):
            if field not in old or field not in new:
                raise ValueError("Expected prior change field missing " + field)
            if field == "time_local":
                if old[field] != new[field]:
                    raise ValueError(f"{site} {year}: prior timestamp changed at {i}")
            elif abs(float(old[field]) - float(new[field])) > 1e-6:
                raise ValueError(f"{site} {year}: prior candidate value changed at {i}: {field}")


def combine(j43: dict, j51: dict, j2007: dict, j54: dict) -> dict:
    combined = from_stage43(j43)
    for label, part in (
        ("Stage51", from_files(j51)),
        ("Stage51 linked CA-Man 2007", {("CA-Man", 2007): j2007}),
        ("Stage54", from_files(j54)),
    ):
        for key, value in part.items():
            if key not in EXPECTED:
                raise ValueError(label + ": unexpected site-year " + str(key))
            if key in combined:
                same_previous(combined[key], value, *key)
            combined[key] = value
    if set(combined) != set(EXPECTED):
        raise ValueError("Unexpected selected site-years missing=" + str(set(EXPECTED)-set(combined)) +
                         " extra=" + str(set(combined)-set(EXPECTED)))
    for key, item in combined.items():
        if len(changes(item)) != EXPECTED[key]:
            raise ValueError(f"{key}: expected {EXPECTED[key]} unique changes, got {len(changes(item))}")
    return combined


def original_register(root: Path) -> dict:
    obj = json.loads((root / "COMPLETE.json").read_text())
    ans = {}
    for rec in obj["sites"]:
        site = rec["site"]
        if site not in SITES:
            continue
        m = Path(rec["manifest"]).resolve(strict=True)
        if root not in m.parents or digest(m) != rec["sha256"]:
            raise ValueError(site + ": Stage23 site manifest fingerprint mismatch")
        j = json.loads(m.read_text())
        for f in j["annual_files"]:
            year = int(f["year"])
            ans[(site, year)] = (Path(f["path"]).resolve(strict=True), f["sha256"])
    return ans


def audit_file(site: str, year: int, row: dict, origin: tuple[Path, str]) -> int:
    import numpy as np
    from netCDF4 import Dataset

    p = Path(row["source"] if "source" in row else row["original"]).resolve(strict=True)
    c = Path(row["candidate"]).resolve(strict=True)
    o, want_sha = origin
    source_sha = row.get("source_sha256", row.get("original_sha256"))
    if p != o or source_sha != want_sha:
        raise ValueError(f"{site} {year}: Stage23 path/hash identity differs")
    if digest(p) != want_sha or digest(c) != row["candidate_sha256"]:
        raise ValueError(f"{site} {year}: original or candidate SHA256 changed")
    ch = changes(row)
    indices = set(ch)
    with Dataset(str(p)) as a, Dataset(str(c)) as b:
        if set(a.variables) != set(b.variables):
            raise ValueError(f"{site} {year}: candidate variable list differs")
        for v in a.variables:
            x = np.ma.asarray(a[v][:])
            y = np.ma.asarray(b[v][:])
            if x.shape != y.shape:
                raise ValueError(f"{site} {year}: changed shape {v}")
            if v in MET_FIELDS:
                if x.shape[0] != 17520 or any(i < 0 or i >= 17520 for i in indices):
                    raise ValueError(f"{site} {year}: invalid NOLEAP index")
                keep = np.ones(x.shape[0], dtype=bool)
                keep[list(indices)] = False
                if not np.ma.allequal(x[keep], y[keep]):
                    raise ValueError(f"{site} {year}: unapproved change outside selected half-hours: {v}")
            elif not np.ma.allequal(x, y):
                raise ValueError(f"{site} {year}: unexpected change to {v}")
        for i, chg in ch.items():
            expected = {
                "TBOT": float(chg["candidate_TA_C"]) + 273.15,
                "QBOT": float(chg["candidate_QBOT"]),
                "SHUM": float(chg["candidate_QBOT"]),
                "RH": float(chg["candidate_RH_pct"]),
            }
            for k, val in expected.items():
                actual = float(b[k][i, 0, 0])
                if not np.isfinite(actual) or abs(actual-val) > 1e-5:
                    raise ValueError(f"{site} {year}: candidate readback mismatch {k} {i}")
            if not (190 < expected["TBOT"] < 340 and 0 < expected["QBOT"] < 0.08
                    and 0 < expected["RH"] <= 100):
                raise ValueError(f"{site} {year}: candidate outside basic physical bounds {i}")
    print("TECHNICAL_PASS", site, year, "changed_HH", len(indices),
          "SHA256", row["candidate_sha256"], "CANDIDATE", c, flush=True)
    return len(indices)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "audit"))
    p.add_argument("--stage23", type=Path, default=STAGE23)
    p.add_argument("--approved", type=Path, default=INITIAL_APPROVED)
    p.add_argument("--stage51", type=Path, default=STAGE51)
    p.add_argument("--stage54", type=Path, default=STAGE54)
    args = p.parse_args()
    if args.action == "self-test":
        assert len(EXPECTED) == 7 and sum(EXPECTED.values()) == 64
        old = {"changes": [{"UTC_index": 1, "time_local": "2026-01-01", "candidate_TA_C": 2,
                            "candidate_QBOT": 0.01, "candidate_RH_pct": 30, "candidate_VPD_hPa": 3}]}
        newer = {"changes": old["changes"] + [{**old["changes"][0], "UTC_index": 2}]}
        same_previous(old, newer, "TEST", 2026)
        try:
            same_previous(newer, old, "TEST", 2026)
            raise AssertionError("Missing change was not rejected")
        except ValueError:
            pass
        print("STAGE56 SELF-TEST PASS | seven candidate site-years; 64 approved HH changes; NO WRITES")
        return

    root = args.stage23.resolve(strict=True)
    j43 = manifest(args.approved, "Stage43")
    j51 = manifest(args.stage51, "Stage51")
    j54 = manifest(args.stage54, "Stage54")
    j2007 = manifest(Path(j51["linked_CA_Man_2007_13_14_manifest"]), "Stage51 linked CA-Man 2007")
    if digest(Path(j51["linked_CA_Man_2007_13_14_manifest"])) != j51["linked_CA_Man_2007_13_14_manifest_sha256"]:
        raise ValueError("Stage51 linked CA-Man manifest hash mismatch")
    if Path(j54["CA_Cbo_joint_report"]).resolve(strict=True) != args.stage51.resolve(strict=True):
        raise ValueError("Stage54 was not built from the supplied Stage51 manifest")
    if digest(Path(j54["CA_Cbo_joint_report"])) != j54["CA_Cbo_joint_report_sha256"]:
        raise ValueError("Stage54 recorded Stage51 hash differs")
    if Path(j54["prior_report"]).resolve(strict=True) != args.approved.resolve(strict=True):
        raise ValueError("Stage54 approved manifest mismatch")
    if digest(Path(j54["prior_report"])) != j54["prior_report_sha256"]:
        raise ValueError("Stage54 prior report hash differs")
    combined = combine(j43, j51, j2007, j54)
    registered = original_register(root)
    total = 0
    for site, year in sorted(combined):
        total += audit_file(site, year, combined[(site, year)], registered[(site, year)])
    if total != 64:
        raise ValueError("Unexpected approved candidate count")
    print("STAGE56 TECHNICAL AUDIT PASS | 3 sites, 7 annual NetCDF, 64 changed half-hours")
    print("SCIENCE HOLD | CA-Man 2005 QC0 temperature replacement vs ERA; review site representativeness")
    print("SCIENCE HOLD | US-Aud uses nearby NOAA proxies; confirm tower representativeness and remaining Q1/Q0")
    print("SCIENCE HOLD | All other flagged events and annual forcing not yet globally cleared")
    print("NO CASE, ORIGINAL FORCING, OR SLURM JOB MODIFIED. AD400 NOT AUTHORIZED.")


if __name__ == "__main__":
    main()
