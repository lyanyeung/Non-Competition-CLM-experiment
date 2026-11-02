#!/usr/bin/env python3
"""Prepare two isolated exploratory Batch04 cases; no Slurm submissions."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

HOME = Path.home()
BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
REPORT_B = HOME / "ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json"
REPORT_Y = HOME / "ICOS_Batch04_stage02y_pT2JPSjW/results/stage02y_four_site_candidate_surface_case_binding_audit.json"
SURFACES = BASE / "experiments/Batch04_GitHub_PFT_Gz7kLAkn"
MANIFESTS = {"STAGE30_CONSOLIDATED": "04_consolidated_13site_271_DATM_SHA256_manifest.csv",
             "STAGE29B": "10_annual_full_DATM_SHA256_manifest.csv"}
SITES = {
    "DE-RuR": (2011, 2025, "2a4685ae3a43323fcff829bd3fdb5d998d58b4e077923a991ee4afd727767414"),
    "ES-Agu": (2006, 2024, "067722b0dc1440abc2e6aef30ca443b04198f697f16e5ba70344e41f89638fa6"),
}
HERE = Path(__file__).resolve().parent

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def command(args, timeout=1200):
    p = subprocess.run([str(x) for x in args], text=True, timeout=timeout)
    need(p.returncode == 0, "Command failed; inspect output and never blindly retry: " + str(args))

def source_info(site, first, last, surface_sha, b, y):
    bm = [x for x in b.get("sites", []) if x.get("site") == site]
    ym = [x for x in y.get("sites", []) if x.get("site") == site]
    need(len(bm) == len(ym) == 1, site + ": missing site evidence")
    site_b, site_y = bm[0], ym[0]
    need(site_b.get("stage28_met_SHA_verified") is True and
         site_b.get("all_current_paths_match_historical") is True and
         site_y.get("PFT_selection_approved") is True,
         site + ": lineage or PFT proxy evidence not verified")
    surface = SURFACES / (site + "_B04_GITHUBPFT_POINT_CANDIDATE.nc")
    surf = site_y.get("surface", {})
    need(surface.is_file() and sha(surface) == surface_sha and
         surf.get("candidate_sha") == surface_sha and surf.get("source_soil_unchanged") is True,
         site + ": candidate surface or inherited soil evidence mismatch")
    template = site + "_FATES_SPINUP1000_S30SHARED"
    matches = [x for x in site_y.get("cases", []) if x.get("case") == template]
    need(len(matches) == 1 and matches[0].get("Stage02V_static_path_match") is True,
         site + ": template path evidence mismatch")
    path = Path(site_b["historical_DATM_manifest"])
    if path.is_dir():
        key = site_b.get("historical_manifest_selected")
        need(key in MANIFESTS, site + ": unknown manifest")
        path = path / MANIFESTS[key]
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = sorted((r for r in csv.DictReader(f) if r.get("site") == site),
                      key=lambda r: int(r["year"]))
    need([int(r["year"]) for r in rows] == list(range(first, last + 1)),
         site + ": incomplete or duplicated years")
    compare = {int(x["year"]): x for x in site_b.get("yearly_path_comparisons", [])}
    need(len(compare) == len(rows), site + ": historical comparisons incomplete")
    annual = []
    for row in rows:
        yr = int(row["year"])
        file = Path(row["datm_nc"])
        c = compare.get(yr, {})
        need(c.get("current") == str(file) and c.get("literal_path_equal") is True and
             file.is_file() and sha(file) == row["sha256"],
             site + ": annual path or hash mismatch " + str(yr))
        annual.append({"year": yr, "path": str(file), "sha256": row["sha256"],
                       "kind": "historical_baseline"})
    return {
        "stage": "STAGE04A_BATCH04_" + site.replace("-", "_").upper() + "_DIRECT_AD400_TECHNICAL_PREFLIGHT",
        "site": site, "science_release": False, "AD400_submission_authorized": False,
        "templates": [{"name": template, "template_technically_candidate": True}],
        "candidate_surface": str(surface), "candidate_surface_sha256": surface_sha,
        "annual_DATM_22_path_list": annual,
        "source_stage03b": str(REPORT_B), "source_stage02y": str(REPORT_Y),
        "scope": "exploratory; inherited soil, precipitation timing and source QC remain uncertain",
    }

def main():
    b, y = json.loads(REPORT_B.read_text()), json.loads(REPORT_Y.read_text())
    need(b.get("read_only") is True and b.get("science_release") is False and
         y.get("read_only") is True and y.get("science_release") is False,
         "Saved reports are not the expected read-only science-HOLD reports")
    jobs = []
    for site, (first, last, surface_sha) in SITES.items():
        code = HERE / (site + "_prepare_ad400.py")
        need(code.is_file(), "Missing prepared script " + str(code))
        payload = source_info(site, first, last, surface_sha, b, y)
        report = HERE / (site + "_pair_preflight_PRIVATE.json")
        with report.open("x", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        jobs.append((site, code, report))
    # Both pass preflight before either case is cloned.
    for site, code, report in jobs:
        print("\nCHECK", site, flush=True)
        command(["python3", "-B", code, "self-test"])
        command(["python3", "-B", code, "check", "--stage04a", report])
    for site, code, report in jobs:
        print("\nPREPARE", site, flush=True)
        ack = "PREPARE_" + site.replace("-", "_").upper() + "_B04_AD400_NO_SLURM"
        command(["python3", "-B", code, "prepare", "--stage04a", report, "--confirm", ack])
    print("BOTH CASES PREPARED AND VERIFIED; NO SLURM SUBMITTED", flush=True)

if __name__ == "__main__":
    main()
