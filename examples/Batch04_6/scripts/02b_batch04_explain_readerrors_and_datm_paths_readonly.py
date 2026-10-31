#!/usr/bin/env python3
"""ICOS Batch04 Stage02B — explain Stage02A READ_ERROR and trace CIME DATM references.

Read-only diagnostic. Reads the existing Stage02A JSON and original CIME
Buildconf/datm.input_data_list. Only --report writes a NEW JSON file under a
pre-existing directory (exclusive create). Does not modify Git, NC, CIME,
surface or Slurm, and does not select any production forcing.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
EXPECTED_CASES = {"CH-Aws": 8, "DE-Gri": 2, "DE-RuR": 2,
                  "IT-Tor": 2, "ES-Agu": 2, "GL-ZaH": 1}
MAX_LINES = 30000
NC_PATTERN = re.compile(r"/[A-Za-z0-9_.+~:%@/=-]+\.nc(?:4)?(?=$|[\s'\"<>,;])", re.I)
MET_KEYS = {"TBOT", "QBOT", "PRECTMMS", "FSDS", "FLDS", "WIND", "PSRF",
            "RH", "TA", "VPD"}


def read_stage02(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stage") != "STAGE02_CANDIDATE_SOURCE_FORCING_SAMPLES" or not data.get("read_only"):
        raise ValueError("incorrect Stage02A JSON")
    rows = data.get("sites")
    if not isinstance(rows, list) or len(rows) != 6:
        raise ValueError("must provide complete six-site Stage02A JSON")
    if tuple(r.get("site") for r in rows) != SITES:
        raise ValueError("wrong site order or incomplete data")
    for row in rows:
        if row.get("source_case_count") != EXPECTED_CASES[row["site"]]:
            raise ValueError(row["site"] + ": Stage02A case count mismatch")
    return data


def direct_nc_from_case(case: Path):
    source = case / "Buildconf/datm.input_data_list"
    out = {"source": str(source), "exists": source.is_file()}
    if not source.is_file():
        return out
    size = source.stat().st_size
    out["bytes"] = size
    if size > 3_000_000:
        out["status"] = "TOO_LARGE_FOR_BOUNDED_SOURCE_SCAN"
        return out
    lines = source.read_text(errors="replace").splitlines()
    out["line_count"] = len(lines)
    if len(lines) > MAX_LINES:
        out["status"] = "TOO_MANY_LINES"
        return out
    refs = sorted(set(match.group(0) for line in lines for match in NC_PATTERN.finditer(line)))
    out["absolute_NC_path_count"] = len(refs)
    out["absolute_NC_paths"] = [{
        "path": name, "exists": Path(name).is_file(),
        "site_token_in_filename": case.name.split("_", 1)[0].lower() in Path(name).name.lower(),
    } for name in refs[:120]]
    out["paths_truncated"] = len(refs) > 120
    out["caveat"] = "CIME input file list references are candidates; XML stream and runtime namelist still require binding audit"
    return out


def probe_file(path: Path):
    result = {"path": str(path), "exists": path.is_file(),
              "symlink": path.is_symlink()}
    if not result["exists"]:
        result["status"] = "MISSING"
        return result
    result["bytes"] = path.stat().st_size
    try:
        with path.open("rb") as f:
            head = f.read(8)
        result["first8_hex"] = head.hex()
        result["container_signature"] = ("NETCDF3_CDF" if head.startswith(b"CDF")
                                         else "NETCDF4_HDF5" if head.startswith(b"\x89HDF")
                                         else "OTHER_OR_UNKNOWN")
    except OSError as exc:
        result["header_error"] = type(exc).__name__ + ": " + str(exc)
    try:
        import netCDF4
        result["netCDF4_python_version"] = getattr(netCDF4, "__version__", "unknown")
        result["netcdf_c_version"] = getattr(netCDF4, "__netcdf4libversion__", "unknown")
    except Exception as exc:
        result["import_error"] = type(exc).__name__ + ": " + str(exc)
        return result
    try:
        with netCDF4.Dataset(str(path), "r") as ds:
            result["open"] = "PASS"
            result["data_model"] = ds.data_model
            result["dimensions"] = {k: len(v) for k, v in ds.dimensions.items()}
            result["variables_names"] = list(ds.variables)[:50]
            result["field_probes"] = {}
            for key, var in ds.variables.items():
                if key.upper() not in MET_KEYS and key.lower() not in ("time", "dtime"):
                    continue
                field = {"shape": list(var.shape), "dtype": str(var.dtype),
                         "units": str(getattr(var, "units", ""))}
                try:
                    if var.ndim == 0:
                        sample = var[...]
                    elif var.ndim and var.size and var.size // max(int(var.shape[0]), 1) <= 10000:
                        sample = var[0: min(2, int(var.shape[0]))]
                    else:
                        field["status"] = "SKIPPED_BIG_SLICE"
                        result["field_probes"][key] = field
                        continue
                    import numpy as np
                    numeric = np.ma.filled(np.ma.asarray(sample).astype(float), np.nan)
                    finite = numeric[np.isfinite(numeric)]
                    field["first_two_records_read"] = "PASS"
                    field["finite_sample_count"] = int(finite.size)
                    if finite.size:
                        field["sample_min"] = float(finite.min())
                        field["sample_max"] = float(finite.max())
                except Exception as exc:
                    field["read_error"] = type(exc).__name__ + ": " + str(exc)
                result["field_probes"][key] = field
    except Exception as exc:
        result["open_error"] = type(exc).__name__ + ": " + str(exc)
    return result


def process_site(data, base: Path, max_nc_probes: int):
    site = data["site"]
    errors = []
    samples = []
    for folder in data["forcing_folders"]:
        for item in folder.get("sampled_netcdf", []):
            if item.get("read_error"):
                errors.append({"folder": folder["name"], "file": item.get("path"),
                               "stage02a_error": item["read_error"]})
                if item.get("path"):
                    samples.append(Path(item["path"]))
            for key, value in item.get("meteorology", {}).items():
                if value.get("read_error"):
                    errors.append({"folder": folder["name"], "file": item.get("path"),
                                   "field": key, "stage02a_error": value["read_error"]})
    # One representative file for each distinct error and file-signature family,
    # capped to avoid repeated probing of multiple RH candidate versions.
    selected = []
    seen = set()
    for path in samples:
        k = (path.name, str(path.parent))
        if k not in seen:
            selected.append(path)
            seen.add(k)
        if len(selected) >= max_nc_probes:
            break
    cases = []
    for item in data["case_provenance"]:
        name = item["case"]
        if not name.startswith(site + "_") or "/" in name or "\\" in name:
            raise ValueError("Unsafe CIME case name in report: " + name)
        cases.append({"case": name,
                      "datm_references": direct_nc_from_case(base / "cases" / name),
                      "effective_datm_stage02a": item.get("effective_namelists_from_stage01", {}).get("datm", {}),
                      "static_xml_stage02a": item.get("static_xml_stage01", {}),
                      "stream_docs_stage02a": item.get("stream_documents", [])[:12]})
    summary = collections.Counter(x["stage02a_error"] for x in errors)
    return {"site": site, "error_count": len(errors),
            "error_groups": [{"message": key, "count": n} for key, n in summary.most_common()],
            "error_examples": errors[:16],
            "representative_NC_metadata_probes": [probe_file(p) for p in selected],
            "original_CIME_candidate_refs": cases,
            "scientific_release": False,
            "status": "HOLD_MUST_VERIFY_ACTUAL_DATM_STREAM_AND_FULL_SOURCE_QC"}


def self_test():
    assert len(SITES) == 6 and sum(EXPECTED_CASES.values()) == 17
    assert NC_PATTERN.findall("foo = /scratch/site/2023.nc,") == ["/scratch/site/2023.nc"]
    assert NC_PATTERN.findall("src=/a/2000.nc4\n") == ["/a/2000.nc4"]
    assert not NC_PATTERN.findall("file = relative/2000.nc")
    print("STAGE02B SELF-TEST PASS: 6 sites, 17 cases, bounded NC path parser; no writes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stage02", type=Path, help="Stage02A JSON produced on IRIDIS6")
    p.add_argument("--base", type=Path, help="Override CLM_FATES base")
    p.add_argument("--max-probes-per-site", type=int, choices=(0, 1, 2, 3), default=2)
    p.add_argument("--report", type=Path, help="NEW JSON output, never overwrite")
    x = p.parse_args()
    if x.self_test:
        if x.report:
            p.error("self-test cannot write report")
        self_test()
        return
    if x.stage02 is None or not x.stage02.is_file():
        p.error("provide existing --stage02 JSON")
    source = read_stage02(x.stage02)
    base = x.base or Path(source["base"])
    if not base.is_dir():
        p.error("CLM_FATES base not found: " + str(base))
    rows = [process_site(item, base, x.max_probes_per_site)
            for item in source["sites"]]
    result = {"stage": "STAGE02B_EXPLAIN_ERRORS_AND_TRACE_CIME_NC_PATHS",
              "read_only": True, "case_created": False, "slurm_submitted": False,
              "source_modified": False, "selection": "NONE",
              "stage02": str(x.stage02), "source_base": str(base),
              "scientific_release": False, "sites": rows}
    for item in rows:
        print("SITE", item["site"], "STAGE02A_READ_ERRORS", item["error_count"])
        for entry in item["error_groups"][:5]:
            print("  ERROR", entry["count"], entry["message"])
        for case in item["original_CIME_candidate_refs"]:
            refs = case["datm_references"]
            files = refs.get("absolute_NC_paths", [])
            exists = sum(x["exists"] for x in files)
            print("  CIME", case["case"],
                  "ABS_NC_REFS", refs.get("absolute_NC_path_count", "UNKNOWN"),
                  "EXISTING_IN_DISPLAYED", exists,
                  "FIRST_REF", (files[0]["path"] if files else "NONE"))
        for probe in item["representative_NC_metadata_probes"]:
            print("  NC_PROBE", Path(probe["path"]).name,
                  "SIGNATURE", probe.get("container_signature", "UNKNOWN"),
                  "OPEN", probe.get("open", probe.get("open_error", probe.get("import_error", "UNKNOWN"))),
                  "TIME_KEYS", ",".join(k for k in probe.get("field_probes", {})
                                       if k.lower() in ("time", "dtime")))
        print("  FINAL_STATUS HOLD; NO SOURCE DATA APPROVED")
    if x.report is not None:
        path = x.report.expanduser().resolve()
        if not path.parent.is_dir():
            p.error("Output parent must already exist: " + str(path.parent))
        with path.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        print("NEW DIAGNOSTIC REPORT:", path)
    print("NO SOURCE/CASE/GIT/SLURM MODIFICATIONS")


if __name__ == "__main__":
    main()
