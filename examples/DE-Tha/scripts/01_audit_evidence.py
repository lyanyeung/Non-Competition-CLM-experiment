#!/usr/bin/env python3
"""Read-only scientific preflight for the DE-Tha standard FATES FIXNC example.

Validates reported ICOS composition and provenance. Optional --surface and
--fates-params inspect *existing* local inputs without writing them. This is
NOT permission to prescribe canopy proportions as CLM natural-landunit PFT
area, and does not prepare cases or submit Slurm jobs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/observed_tree_composition.csv"
MANIFEST = ROOT / "config/experiment_manifest.json"
EXPECTED_SPECIES = {
    "Picea abies": 72.0,
    "Pinus sylvestris": 15.0,
    "Larix decidua": 10.0,
    "Betula sp.": 1.0,
    "Other deciduous trees (unidentified)": 2.0,
}
EXPECTED_GROUPS = {"ENF": 87.0, "DNF": 10.0, "DBF": 1.0,
                   "UNRESOLVED_DECIDUOUS": 2.0}


def fail(message: str) -> None:
    raise RuntimeError(message)


def audit_evidence() -> dict:
    meta = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if meta.get("site") != "DE-Tha":
        fail("Incorrect site ID")
    if meta.get("scientific_status") != "TOWER_FOREST_PROXY_SELECTED_WITH_UNRESOLVED_2PCT_ASSUMPTION":
        fail("Scientific approval status changed: manual review required")
    if meta.get("scenario_approval") != "USER_SELECTED_ONE_FOREST_PROXY; TWO_ASSUMPTION_ACKNOWLEDGEMENTS_REQUIRED_FOR_WRITE":
        fail("Unexpected scientific scenario approval; inspect edits")

    with CSV.open(newline="", encoding="utf-8") as fp:
        entries = list(csv.DictReader(fp))
    if len(entries) != len(EXPECTED_SPECIES):
        fail("Unexpected evidence row count")
    groups = defaultdict(float)
    species = {}
    for row in entries:
        name = row["species_or_group"]
        if name in species or row["site"] != "DE-Tha":
            fail("Duplicate species or mismatched site")
        pct = float(row["reported_percent"])
        if name not in EXPECTED_SPECIES or not math.isclose(
                pct, EXPECTED_SPECIES[name], abs_tol=1e-8):
            fail(f"Unexpected ICOS species percent: {name} {pct}")
        if row["reference_url"] != "https://meta.icos-cp.eu/resources/stations/ES_DE-Tha":
            fail(f"Missing exact ICOS provenance for {name}")
        species[name] = pct
        groups[row["provisional_fates_group"]] += pct
    if not math.isclose(sum(species.values()), 100.0, abs_tol=1e-8):
        fail("Observed composition not equal to 100")
    for k, v in EXPECTED_GROUPS.items():
        if not math.isclose(groups[k], v, abs_tol=1e-8):
            fail(f"Unexpected grouped proportion: {k} {groups[k]}")
    if set(groups) != set(EXPECTED_GROUPS):
        fail("Unexpected FATES group labels")
    reference = meta["grouped_observed_percent"]
    if (reference["ENF"], reference["DNF"], reference["DBF_identified"],
            reference["UNRESOLVED_DECIDUOUS"]) != (87, 10, 1, 2):
        fail("Manifest disagrees with original source")
    expected = meta["observed_tree_species_percent"]
    alias = {"Other deciduous trees (unidentified)": "other deciduous unidentified"}
    for name, value in species.items():
        if expected.get(alias.get(name, name)) != value:
            fail("Manifest and CSV percent disagree: " + name)
    if meta["source_evidence"]["is_measured_clm_natpft_area"] is not False:
        fail("Unsupported claim that observations measure CLM PFT area")
    print("PASS: ICOS source-composition entries 72+15+10+1+2 = 100%")
    print("PASS: ENF 87%, DNF 10%, identified DBF 1%, unidentified deciduous 2%")
    print("HOLD: 2% unidentified; tree canopy shares are NOT verified PFT area shares")
    return meta


def audit_surface(path: Path) -> None:
    if not path.is_file():
        fail("Original surface does not exist: " + str(path))
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as e:
        fail("Surface inspection requires numpy + netCDF4: " + str(e))

    with Dataset(path, "r") as ds:
        for key in ("PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT"):
            if key not in ds.variables:
                fail("Surface missing " + key)
        natural = np.ma.filled(ds.variables["PCT_NATVEG"][:], np.nan).ravel()
        crop = np.ma.filled(ds.variables["PCT_CROP"][:], np.nan).ravel()
        v = ds.variables["PCT_NAT_PFT"]
        a = np.ma.filled(v[:], np.nan)
        dim = [i for i, d in enumerate(v.dimensions) if d.lower() == "natpft"]
        if len(dim) != 1 or v.shape[dim[0]] != 15:
            fail("Unexpected CLM natpft indexing: " + str(v.dimensions))
        if any(x != 1 for i,x in enumerate(v.shape) if i != dim[0]):
            fail("Not a verified single-point surface")
        shares = np.moveaxis(a, dim[0], 0).reshape(15)
        if not np.isfinite(shares).all() or not np.isclose(shares.sum(), 100, atol=0.02):
            fail("Original natural PFT shares invalid")
        if natural.size != 1 or crop.size != 1:
            fail("Original landunit fractions are not single-point")
        print(f"SURFACE READ ONLY: {path}")
        print(f"  PCT_NATVEG={natural[0]:.4f}; PCT_CROP={crop[0]:.4f}")
        print("  CLM natpft indices 1/3/7 (ENF/DNF/DBF):",
              [round(float(shares[i]), 4) for i in (1,3,7)])
        print("  NOTE: these are original MODEL fractions, not ICOS tower percentages")


def audit_params(path: Path, meta: dict) -> None:
    if not path.is_file():
        fail("FATES parameter JSON does not exist: " + str(path))
    try:
        import numpy as np
    except ImportError as e:
        fail("FATES parameter map inspection requires numpy: " + str(e))
    doc = json.loads(path.read_text(encoding="utf-8"))
    prm = doc["parameters"]
    names = prm["fates_pftname"]["data"]
    mapping = np.asarray(prm["fates_hlm_pft_map"]["data"], dtype=float)
    if mapping.ndim != 2 or mapping.shape[0] != 14 or mapping.shape[1] != len(names):
        fail(f"Unexpected pinned FATES HLM-to-PFT mapping shape {mapping.shape}")
    found = {}
    for group, idx in meta["potential_clm_natpft_index"].items():
        row = mapping[int(idx)-1]
        hit = np.flatnonzero(row > 0)
        if len(hit) != 1 or not np.isclose(row[hit[0]], 1, atol=1e-8):
            fail(f"{group}: CLM index {idx} does not map to one FATES PFT")
        found[group] = names[int(hit[0])]
    if len(set(found.values())) != 3:
        fail("Expected distinct ENF, DNF, DBF FATES model PFTs")
    print("FATES mapping READ ONLY (verify taxonomy with this pinned parameter file):")
    for group, name in sorted(found.items()):
        print(f"  {group} -> {name}")
    print("  NOTE: verified map structure alone does not authorize surface rewriting")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--surface", type=Path,
                    help="Optional actual pre-existing DE-Tha CLM surface (read only)")
    ap.add_argument("--fates-params", type=Path,
                    help="Optional active FATES parameter JSON (read only)")
    ap.add_argument("--scenario", choices=("tower_forest_proxy_ENF87_DNF10_DBF3",),
                    help="Display selected tower-forest proxy; area/2pct remain assumptions")
    args = ap.parse_args()
    meta = audit_evidence()
    if args.scenario:
        scenario = meta["scenario_candidates"][args.scenario]
        if sum(scenario.values()) != 100:
            fail("Candidate scenario does not sum to 100")
        print("SELECTED FOREST PFT PROXY (NOT MEASURED GRID AREA):", args.scenario, scenario)
        print("For isolated new-surface write, use script 05 with two explicit assumption acknowledgements")
    if args.surface:
        audit_surface(args.surface)
    if args.fates_params:
        audit_params(args.fates_params, meta)
    print("READ ONLY COMPLETE: no input writes, no case build, no Slurm submissions")
    print("SITE STATUS: SINGLE_TOWER_FOREST_PROXY_SELECTED; SURFACE_WRITE_REQUIRES_EXPLICIT_ACK")


if __name__ == "__main__":
    main()
