#!/usr/bin/env python3
"""Summarize the existing Batch02 report and ten explicit source references.

Reads the specified Stage01 JSON, not another filesystem inventory. Optionally
reads only the SHA256-matched active FATES parameter files for decoded names and
the HLM map. No file writes, model changes, subprocesses or Slurm operations.
References are configuration templates, not old restart donors or approved PFTs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

SOURCES = {
    "DK-Sor": "DK-Sor_FATES_SPINUP500",
    "FR-Hes": "FR-Hes_FATES_SPINUP500",
    "FR-FBn": "FR-FBn_FATES_SPINUP500",
    "BE-Bra": "BE-Bra_FATES_SPINUP500_11P",
    "IT-Noe": "IT-Noe_ERA5_ABW_BRANCH2009",
    "CH-Fru": "CH-Fru_FATES_SPINUP500_11P",
    "CH-Lae": "CH-Lae_FATES_SPINUP500_11P",
    "ES-LJu": "ES-LJu_FATES_SPINUP1000_S30SHARED",
    "FI-Hyy": "FI-Hyy_FATES_SPINUP1000_S30SHARED",
    "IT-MBo": "IT-MBo_FATES_SPINUP1000_S30SHARED",
}
FLAGS = ("use_fates", "use_fates_sp", "use_fates_nocomp",
         "use_fates_fixed_biogeog", "spinup_state", "finidat")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def selected(data):
    if data.get("cohort") != "ICOS_EUROPE_BATCH02":
        raise ValueError("Wrong cohort; expected the Batch02 Stage01 report")
    if data.get("original_model_files_modified") is not False or data.get("model_jobs_submitted") is not False:
        raise ValueError("Stage01 provenance flags are absent or changed")
    rows = data.get("sites", [])
    if tuple(r.get("site") for r in rows) != tuple(SOURCES):
        raise ValueError("Expected exactly the ten Batch02 sites in original report order")
    output = []
    for row in rows:
        site = row["site"]
        matches = [c for c in row.get("cases", []) if c.get("name") == SOURCES[site]]
        if len(matches) != 1:
            raise ValueError(site + ": explicit source case missing or duplicated: " + SOURCES[site])
        case = matches[0]
        if Path(case.get("path", "")).name != SOURCES[site]:
            raise ValueError(site + ": inconsistent source case path")
        output.append((row, case))
    return output


def decoded_names(value):
    """Handle both NetCDF S1 char matrices and already decoded string arrays."""
    import numpy as np
    arr = np.ma.asarray(value)
    if arr.ndim == 2 and arr.dtype.kind == "S" and arr.dtype.itemsize == 1:
        return [b"".join(np.ma.filled(row, b"").tolist()).decode("utf-8").strip("\0 ") for row in arr]
    if arr.ndim == 1 and arr.dtype.kind in "SUO":
        return [(x.decode("utf-8") if isinstance(x, bytes) else str(x)).strip("\0 ") for x in arr]
    raise ValueError("Unrecognized fates_pftname layout: " + str(arr.shape))


def parameter_details(record, snapshot_only):
    if not record.get("exists"):
        raise ValueError("Active parameter file missing from Stage01 report")
    if snapshot_only:
        if record.get("read_error") or not record.get("variables", {}).get("fates_hlm_pft_map"):
            raise ValueError("Stage01 parameter snapshot has no readable HLM map")
        print("PARAMETER_SNAPSHOT", json.dumps(record, ensure_ascii=True, sort_keys=True))
        return
    path = Path(record["path"])
    if not path.is_absolute() or not record.get("sha256") or not path.is_file():
        raise ValueError("No readable absolute SHA-pinned active parameter file: " + str(path))
    if sha256(path) != record["sha256"]:
        raise ValueError("Active parameter file changed since Stage01: " + str(path))
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(path, "r") as ds:
        names = decoded_names(ds.variables["fates_pftname"][:])
        v = ds.variables["fates_hlm_pft_map"]
        matrix = np.ma.asarray(v[:])
        if matrix.ndim != 2 or np.ma.getmaskarray(matrix).any():
            raise ValueError("Invalid/masked HLM-FATES map")
        print("PARAMETER_SHA256", record["sha256"])
        print("FATES_NAMES_ZERO_BASED", json.dumps(dict(enumerate(names)), ensure_ascii=True))
        print("HLM_MAP_DIMENSIONS", json.dumps(v.dimensions), "SHAPE", json.dumps(v.shape))
        print("HLM_MAP_STORED_ROWS", json.dumps(matrix.tolist(), allow_nan=False))
        print("MAP_NOTE: stored array positions; host bare/PFT indexing is not inferred here.")


def summarize(data, snapshot_only=False):
    rows = selected(data)
    seen, issues = set(), []
    print("BATCH02 SELECTED SOURCE INPUTS | READ ONLY | no new source inventory")
    for row, case in rows:
        site = row["site"]
        xml = case.get("xml", {}).get("resolved", {})
        nl = case.get("land_namelist", {})
        print("\nSITE", site, "SOURCE", case["name"])
        print("START_CO2", *(xml.get(k, "UNKNOWN") for k in ("RUN_STARTDATE", "CLM_CO2_TYPE", "CCSM_CO2_PPMV")))
        print("SOURCE_FLAGS", json.dumps({k: nl.get(k, "ABSENT") for k in FLAGS}, sort_keys=True))
        print("RUN_EXE", xml.get("RUNDIR", "UNKNOWN"), xml.get("EXEROOT", "UNKNOWN"))
        surface = case.get("fsurdat", {})
        print("FSURDAT", surface.get("path", "UNKNOWN"), "SHA256", surface.get("sha256", "MISSING"))
        if not surface.get("exists") or surface.get("read_error"):
            issues.append(site + ": surface missing/unreadable: " + surface.get("read_error", "missing"))
        variables = surface.get("variables", {})
        for key in ("PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT", "PCT_SAND", "PCT_CLAY", "ORGANIC"):
            print(key, json.dumps(variables.get(key, {"status": "NOT_RECORDED"}), sort_keys=True))
        for key in ("PCT_SAND", "PCT_CLAY"):
            if "values" not in variables.get(key, {}):
                issues.append(site + ": no recorded " + key + " layers")
        print("SOIL_NOTE: original model texture, not measured tower soil evidence.")
        docs = [d for d in case.get("input_documents", []) if "stream" in Path(d.get("path", "")).name.lower()]
        print("DATM_XML_YEARS", json.dumps({k: v for k, v in xml.items() if "DATM" in k or k == "CALENDAR"}, sort_keys=True))
        if not docs:
            issues.append(site + ": no DATM stream document recorded")
        for doc in docs:
            print("DATM_DOCUMENT", doc["path"], "SHA256", doc.get("sha256", "MISSING"))
            if doc.get("values"):
                print("DATM_VALUES", json.dumps(doc["values"], sort_keys=True))
            for ref in doc.get("reference_excerpt", []):
                print("  STREAM_REF", ref)
        param = case.get("fates_paramfile", {})
        identity = (param.get("path"), param.get("sha256"))
        print("ACTIVE_FATES_PARAMETER", param.get("path", "UNRESOLVED"))
        if identity not in seen:
            seen.add(identity)
            try:
                parameter_details(param, snapshot_only)
            except Exception as exc:
                issues.append(site + ": parameter mapping: " + str(exc))
        else:
            print("PARAMETER_MAP_REPEATED: see identical file/hash above")
        print("PFT_DECISION", row.get("input_decision", {}).get("unresolved_PFT", "UNRESOLVED"))
    print("\nTECHNICAL_DETAIL_ISSUES", len(issues))
    for issue in issues:
        print("DETAIL_HOLD", issue)
    print("Science decisions remain separate. No surfaces/cases/jobs created or modified.")
    return 2 if issues else 0


def self_test():
    fake = {"cohort": "ICOS_EUROPE_BATCH02", "original_model_files_modified": False,
            "model_jobs_submitted": False, "sites": [
                {"site": site, "cases": [{"name": name, "path": "/cases/" + name}]} for site, name in SOURCES.items()]}
    assert len(selected(fake)) == 10
    for mutation in ("missing", "duplicate", "wrong_cohort"):
        broken = copy.deepcopy(fake)
        if mutation == "missing":
            broken["sites"][0]["cases"] = []
        elif mutation == "duplicate":
            broken["sites"][0]["cases"] *= 2
        else:
            broken["cohort"] = "BATCH01"
        try:
            selected(broken)
        except ValueError:
            pass
        else:
            raise AssertionError("Accepted " + mutation)
    assert SOURCES["IT-Noe"] == "IT-Noe_ERA5_ABW_BRANCH2009"
    assert "HIST" not in SOURCES["DK-Sor"]
    print("SELF-TEST PASS: ten exact source templates; repaired IT-Noe; DK-Sor historical exclusion; invalid reports rejected. NO WRITES.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path)
    ap.add_argument("--snapshot-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.inventory is None:
        ap.error("--inventory is required")
    path = args.inventory.expanduser()
    print("SOURCE_REPORT", str(path), "SHA256", sha256(path))
    return summarize(json.loads(path.read_text(encoding="utf-8")), args.snapshot_only)


if __name__ == "__main__":
    raise SystemExit(main())
