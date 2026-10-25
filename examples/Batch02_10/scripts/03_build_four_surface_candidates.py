#!/usr/bin/env python3
"""Prepare four versioned Batch02 surface CANDIDATES; never creates/submits cases.

plan/self-test need only Python stdlib. build needs the existing clm_fates_env
numpy/netCDF4. Every model input is read only except NEW candidate files under
the independent Batch02 output root. Explicit PFT/landunit/vertical-soil proxies
are stored in sidecar receipts; none is labelled measured footprint composition.
The six other cohort sites are not silently assigned residual PFTs.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / "data/batch02_four_surface_candidates_v1.json"
OUTPUT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10")
SELECTED = ("FI-Hyy", "FR-Hes", "CH-Fru", "IT-MBo")
OTHER = ("PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")
CHANGED = {"PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT", "PCT_SAND", "PCT_CLAY", *OTHER}
VERSION = "batch02-four-surface-candidates-v1-20261025"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def configuration():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data.get("version") != VERSION or tuple(r["site"] for r in data["sites"]) != SELECTED:
        raise ValueError("Candidate configuration version/site membership differs")
    for r in data["sites"]:
        pft = r["host_natpft_percent"]
        if any(int(k) not in (2, 7, 8, 13) or not math.isfinite(v) or v < 0 for k, v in pft.items()):
            raise ValueError("Unsupported/nonfinite host PFT fraction: " + r["site"])
        if abs(sum(pft.values()) - 100) > 1e-8:
            raise ValueError("Candidate PFTs do not sum to100: " + r["site"])
        soil = r["sand_silt_clay_percent"]
        if len(soil) != 3 or any(not math.isfinite(x) or x < 0 for x in soil) or abs(sum(soil) - 100) > 1e-8:
            raise ValueError("Candidate sand/silt/clay invalid: " + r["site"])
        if r["status"] != "CANDIDATE_ONLY_NO_CASE_NO_SUBMISSION":
            raise ValueError("Candidate must not claim operational/scientific approval")
    return data


def parameter_map(data):
    p = Path(data["active_parameter_path"])
    if not p.is_file() or sha256(p) != data["active_parameter_sha256"]:
        raise ValueError("Active FATES JSON missing/changed; expected the operator-verified map")
    params = json.loads(p.read_text(encoding="utf-8"))["parameters"]
    names = params["fates_pftname"]["data"]
    matrix = params["fates_hlm_pft_map"]["data"]
    dims = params["fates_hlm_pft_map"]["dims"]
    if dims != ["fates_hlm_pftno", "fates_pft"] or len(matrix) != 14 or len(names) != 14:
        raise ValueError("Active map dimensions differ from the verified14x14 map")
    for idx, name in data["FATES_expected_for_host_index"].items():
        # CLM natural index0 is bare; map row0 corresponds to CLM natural PFT1.
        row = matrix[int(idx) - 1]
        if len(row) != 14 or any(not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in row):
            raise ValueError("Invalid active HLM map row " + idx)
        if [(names[i], v) for i, v in enumerate(row) if v != 0] != [(name, 1.0)]:
            raise ValueError("Host PFT " + idx + " does not map uniquely to " + name)
    return p


def destination(row, root):
    return root / row["site"] / "surface_candidates" / ("surfdata_" + row["site"] + "_B02_FIXNC_candidate_v1.nc")


def verify_values(row, path):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(path, "r") as ds:
        for k, expected in (("PCT_NATVEG", 100), ("PCT_CROP", 0)):
            a = np.ma.asarray(ds.variables[k][:])
            if a.size != 1 or np.ma.getmaskarray(a).any() or not np.allclose(a, expected, atol=1e-5):
                raise ValueError("Wrong point landunit " + k)
        for k in OTHER:
            if k in ds.variables and not np.allclose(ds.variables[k][:], 0, atol=1e-5):
                raise ValueError("Nonzero other landunit " + k)
        v = ds.variables["PCT_NAT_PFT"]
        if v.size != 15 or not v.dimensions or v.dimensions[0] != "natpft":
            raise ValueError("Expected natpft-first15x1x1 point surface")
        expected = np.zeros(15)
        for k, value in row["host_natpft_percent"].items():
            expected[int(k)] = value
        if not np.allclose(np.asarray(v[:]).reshape(-1), expected, atol=1e-5):
            raise ValueError("Wrong candidate host-PFT distribution")
        sand, _, clay = row["sand_silt_clay_percent"]
        for k, value in (("PCT_SAND", sand), ("PCT_CLAY", clay)):
            v = ds.variables[k]
            if v.size != 10 or not np.allclose(v[:], value, atol=1e-5):
                raise ValueError("Wrong ten-layer texture proxy " + k)


def verify_unchanged(source, candidate):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(source, "r") as a, Dataset(candidate, "r") as b:
        if set(a.variables) != set(b.variables) or set(a.dimensions) != set(b.dimensions):
            raise ValueError("Candidate schema changed")
        for k in a.dimensions:
            if len(a.dimensions[k]) != len(b.dimensions[k]):
                raise ValueError("Candidate dimension changed: " + k)
        for k in a.variables:
            if k in CHANGED:
                continue
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            if x.shape != y.shape or not np.array_equal(np.ma.getmaskarray(x), np.ma.getmaskarray(y)):
                raise ValueError("Unrequested variable mask/shape changed: " + k)
            xx, yy = np.ma.getdata(x), np.ma.getdata(y)
            same = np.array_equal(xx, yy, equal_nan=True) if xx.dtype.kind in "fc" else np.array_equal(xx, yy)
            if not same:
                raise ValueError("Unrequested source variable changed: " + k)


def build_one(data, row, root):
    from netCDF4 import Dataset
    import numpy as np
    src = Path(row["source_surface"])
    expected_sha = row["source_surface_sha256"]
    if not src.is_file() or sha256(src) != expected_sha:
        raise ValueError(row["site"] + ": source surface absent/changed")
    dst = destination(row, root)
    receipt = dst.with_suffix(".json")
    config_sha = sha256(CONFIG)
    if dst.exists() or dst.is_symlink() or receipt.exists() or receipt.is_symlink():
        if dst.is_file() and receipt.is_file() and not dst.is_symlink() and not receipt.is_symlink():
            old = json.loads(receipt.read_text())
            if old.get("candidate_sha256") == sha256(dst) and old.get("configuration_sha256") == config_sha:
                verify_values(row, dst)
                verify_unchanged(src, dst)
                print(row["site"], "EXISTS_VERIFIED_NO_OVERWRITE", dst)
                return
        raise ValueError("Candidate/receipt already exists with inconsistent state: " + str(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix=".candidate-", suffix=".nc", dir=dst.parent)
    os.close(fd)
    tmp = Path(filename)
    try:
        shutil.copyfile(src, tmp)
        with Dataset(tmp, "r+") as ds:
            for k, value in (("PCT_NATVEG", 100), ("PCT_CROP", 0)):
                if ds.variables[k].size != 1:
                    raise ValueError("Not a point surface: " + k)
                ds.variables[k][:] = value
            for k in OTHER:
                if k in ds.variables:
                    ds.variables[k][:] = 0
            pft = ds.variables["PCT_NAT_PFT"]
            if pft.size != 15 or pft.dimensions[0] != "natpft":
                raise ValueError("Unsupported natural-PFT layout")
            values = np.zeros(15)
            for k, value in row["host_natpft_percent"].items():
                values[int(k)] = value
            pft[:] = values.reshape(pft.shape)
            sand, _, clay = row["sand_silt_clay_percent"]
            for k, value in (("PCT_SAND", sand), ("PCT_CLAY", clay)):
                if ds.variables[k].size != 10:
                    raise ValueError("Expected ten input texture layers")
                ds.variables[k][:] = value
            ds.setncattr("batch02_candidate_version", VERSION)
            ds.setncattr("batch02_candidate_status", "MODEL_POINT_PROXY_NOT_MEASURED_FOOTPRINT")
        verify_values(row, tmp)
        verify_unchanged(src, tmp)
        if sha256(src) != expected_sha:
            raise ValueError("Original surface changed during preparation")
        parameter_map(data)
        record = {"version": VERSION, "status": "CANDIDATE_ONLY_NO_CASE_NO_SUBMISSION",
                  "created_utc": datetime.now(timezone.utc).isoformat(),
                  "candidate": str(dst), "candidate_sha256": sha256(tmp),
                  "configuration_sha256": config_sha, "site_inputs_and_assumptions": row,
                  "parameter_sha256": data["active_parameter_sha256"],
                  "original_surface_modified": False, "forcing_modified": False,
                  "CIME_cases_created": False, "Slurm_jobs_submitted": False,
                  "unchanged_fields": "Inherited source-model inputs, not newly validated observations"}
        # Exclusive link prevents overwriting another concurrent/pre-existing file.
        os.link(tmp, dst)
        with receipt.open("x", encoding="utf-8") as f:
            json.dump(record, f, indent=2, allow_nan=False)
            f.write("\n")
        print(row["site"], "CANDIDATE_CREATED", dst)
    finally:
        tmp.unlink(missing_ok=True)


def plan(data):
    print("FOUR INDEPENDENT SURFACE CANDIDATES | no case or Slurm operations")
    for row in data["sites"]:
        print(row["site"], "HOST_PFT", row["host_natpft_percent"], "SAND_SILT_CLAY", row["sand_silt_clay_percent"])
        print("  PFT:", row["PFT_scenario"])
        print("  SOIL:", row["soil_vertical_policy"])
    print("All four: explicit dense-point NATVEG100/CROP0 proxy, not measured whole-footprint land cover.")
    print("OTHER SIX:", data["other_six_sites"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "plan", "build"))
    p.add_argument("--sites", nargs="+", choices=SELECTED)
    p.add_argument("--output-root", type=Path, default=OUTPUT)
    a = p.parse_args()
    data = configuration()
    if a.action == "self-test":
        hyy = data["sites"][0]["host_natpft_percent"]
        assert abs(hyy["2"] - 94.78604818410645) < 1e-10
        assert abs(hyy["8"] - 5.213951815893564) < 1e-10
        assert set(SELECTED).isdisjoint({"NL-Loo", "DE-Tha", "DK-Sor", "IT-Noe"})
        print("SELF-TEST PASS: four explicit candidate PFT/soil choices; FI-Hyy basal-area arithmetic; no automatic other-six allocation. NO WRITES.")
        return 0
    plan(data)
    if a.action == "plan":
        return 0
    if not a.sites or len(set(a.sites)) != len(a.sites):
        p.error("build requires a nonduplicated explicit --sites list")
    parameter_map(data)
    failures = []
    for row in data["sites"]:
        if row["site"] not in a.sites:
            continue
        try:
            build_one(data, row, a.output_root.expanduser().resolve())
        except Exception as exc:
            failures.append(row["site"])
            print(row["site"], "CANDIDATE_FAILED", str(exc))
    print("CANDIDATE_SUMMARY created_or_verified=", len(a.sites) - len(failures), "failed=", failures)
    print("NO case creation, namelist changes or model submission.")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
