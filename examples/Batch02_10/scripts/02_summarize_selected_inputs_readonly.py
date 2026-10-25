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
import math
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


def validate_parameter_arrays(names, rows):
    """Validate stored arrays without changing orientation or index origin."""
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError("Missing/invalid FATES PFT names")
    if len(set(names)) != len(names):
        raise ValueError("Duplicate FATES PFT names")
    if not isinstance(rows, list) or not rows or any(not isinstance(r, list) or not r for r in rows):
        raise ValueError("HLM-FATES map must be a nonempty matrix")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("Ragged HLM-FATES map")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0
           for r in rows for x in r):
        raise ValueError("HLM-FATES map has nonfinite/negative/nonnumeric values")
    shape = [len(rows), width]
    if len(names) not in shape:
        raise ValueError("Neither map axis matches the number of FATES PFT names")
    return shape


def json_parameter_arrays(payload):
    """FATES parameter JSON stores parameters -> variable -> data, not NetCDF."""
    if not isinstance(payload, dict) or not isinstance(payload.get("parameters"), dict):
        raise ValueError("Expected FATES JSON object with a parameters dictionary")
    params = payload["parameters"]
    namevar = params.get("fates_pftname")
    mapvar = params.get("fates_hlm_pft_map")
    if not isinstance(namevar, dict) or not isinstance(mapvar, dict):
        raise ValueError("FATES JSON lacks fates_pftname or fates_hlm_pft_map")
    raw_names = namevar.get("data")
    if not isinstance(raw_names, list) or any(not isinstance(n, str) for n in raw_names):
        raise ValueError("FATES JSON PFT name data must be a list of strings")
    names = [n.strip("\0 ") for n in raw_names]
    rows = mapvar.get("data")
    shape = validate_parameter_arrays(names, rows)
    # Preserve whichever dimension metadata this JSON revision supplies.
    dims = {key: mapvar[key] for key in ("dims", "dimensions", "dimension") if key in mapvar}
    return names, rows, shape, dims


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
    if path.suffix.lower() == ".json":
        names, rows, shape, dimensions = json_parameter_arrays(json.loads(path.read_text(encoding="utf-8-sig")))
        source_format = "FATES_JSON"
    else:
        from netCDF4 import Dataset
        import numpy as np
        with Dataset(path, "r") as ds:
            names = decoded_names(ds.variables["fates_pftname"][:])
            v = ds.variables["fates_hlm_pft_map"]
            matrix = np.ma.asarray(v[:])
            if matrix.ndim != 2 or np.ma.getmaskarray(matrix).any():
                raise ValueError("Invalid/masked HLM-FATES map")
            rows = matrix.tolist()
            shape = validate_parameter_arrays(names, rows)
            dimensions = list(v.dimensions)
        source_format = "NETCDF"
    # Check again after reading: do not print a mapping from a file edited mid-read.
    if sha256(path) != record["sha256"]:
        raise ValueError("Active parameter file changed while being read: " + str(path))
    print("PARAMETER_FORMAT", source_format)
    print("PARAMETER_SHA256", record["sha256"])
    print("FATES_NAMES_ZERO_BASED", json.dumps(dict(enumerate(names)), ensure_ascii=True))
    print("HLM_MAP_DIMENSIONS", json.dumps(dimensions), "SHAPE", json.dumps(shape))
    print("HLM_MAP_STORED_ROWS", json.dumps(rows, allow_nan=False))
    print("MAP_NOTE: stored array positions; host bare/PFT indexing is not inferred here.")


def parameters_only(data, snapshot_only=False):
    groups = {}
    for row, case in selected(data):
        record = case.get("fates_paramfile", {})
        identity = (record.get("path"), record.get("sha256"))
        if identity not in groups:
            groups[identity] = {"sites": [], "record": record}
        groups[identity]["sites"].append(row["site"])
    issues = []
    print("BATCH02 ACTIVE FATES MAPPING ONLY | no soil/forcing rescan")
    print("SELECTED_SITES", 10, "UNIQUE_PARAMETER_FILES", len(groups))
    for group in groups.values():
        print("SITES_SHARING_PARAMETER", ",".join(group["sites"]))
        print("ACTIVE_FATES_PARAMETER", group["record"].get("path", "UNRESOLVED"))
        try:
            parameter_details(group["record"], snapshot_only)
        except Exception as exc:
            issues.append(",".join(group["sites"]) + ": " + str(exc))
    for issue in issues:
        print("MAPPING_HOLD", issue)
    print("MAPPING_READ", "HOLD" if issues else "PASS", "ISSUES", len(issues))
    print("Reading a map does not approve site PFT fractions or prove executable provenance.")
    print("NO model files/cases/jobs created or modified.")
    return 2 if issues else 0


def summarize(data, snapshot_only=False):
    rows = selected(data)
    seen, issues = {}, []
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
            try:
                parameter_details(param, snapshot_only)
                seen[identity] = None
            except Exception as exc:
                seen[identity] = str(exc)
                issues.append(site + ": parameter mapping: " + str(exc))
        elif seen[identity] is not None:
            print("PARAMETER_MAP_UNAVAILABLE: shared file failed earlier:", seen[identity])
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
    p = {"parameters": {"fates_pftname": {"data": ["enf", "dbf"]},
                        "fates_hlm_pft_map": {"data": [[1, 0], [0, 1], [0.5, 0.5]],
                                              "dims": ["hlm", "fates"]}}}
    names, rows, shape, dims = json_parameter_arrays(p)
    assert names == ["enf", "dbf"] and shape == [3, 2] and rows[2] == [0.5, 0.5]
    assert dims == {"dims": ["hlm", "fates"]}
    for malformed in ([], [[1, 0], [1]], [[float("nan"), 0]], [[True, 0]], [[-1, 0]]):
        try:
            validate_parameter_arrays(names, malformed)
        except ValueError:
            pass
        else:
            raise AssertionError("Accepted malformed mapping")
    print("SELF-TEST PASS: ten references; repaired IT-Noe; JSON schema/matrix parsing; invalid and nonfinite maps rejected. NO WRITES.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path)
    ap.add_argument("--snapshot-only", action="store_true")
    ap.add_argument("--parameters-only", action="store_true", help="only print unique active FATES parameter mappings")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.inventory is None:
        ap.error("--inventory is required")
    path = args.inventory.expanduser()
    print("SOURCE_REPORT", str(path), "SHA256", sha256(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    return (parameters_only(data, args.snapshot_only) if args.parameters_only
            else summarize(data, args.snapshot_only))


if __name__ == "__main__":
    raise SystemExit(main())
