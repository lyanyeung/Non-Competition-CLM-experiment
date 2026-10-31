#!/usr/bin/env python3
"""Read-only six-site ICOS Batch04 forcing/surface/source inventory.
No model cases, surfaces, existing inputs or Slurm jobs are changed.
Only --report PATH writes a new file in an existing directory.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SITES = ("CH-Aws", "DE-Gri", "DE-RuR", "IT-Tor", "ES-Agu", "GL-ZaH")
EXPECTED = {
    "CH-Aws": {13: 100},
    "DE-Gri": {13: 100},
    "DE-RuR": {13: 100},
    "IT-Tor": {13: 100},
    "ES-Agu": {0: 49, 9: 22, 13: 29},
    "GL-ZaH": {0: 43, 9: 53, 11: 3, 12: 1},
}
BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
REPO = Path(__file__).resolve().parents[3]
OPERATOR = REPO / "examples/ICOS_Unassigned_6/data/six_site_FIXNC_operator_selected_PFT_20261025.csv"
GATES = Path(__file__).resolve().parents[1] / "data/batch04_review_gates.csv"
SOURCE_BLOB = "63739e00408443bcbb4b286bb3324c76e9fd9100"
XML_FILES = ("env_case.xml", "env_run.xml", "env_build.xml", "env_mach_pes.xml")
XML_KEYS = ("CASE", "CASEROOT", "RUNDIR", "EXEROOT", "DIN_LOC_ROOT", "RUN_TYPE",
            "RUN_STARTDATE", "DATM_MODE", "DATM_CLMNCEP_YR_START",
            "DATM_CLMNCEP_YR_END", "DATM_CLMNCEP_YR_ALIGN", "CALENDAR",
            "PTS_LAT", "PTS_LON", "RESUBMIT", "STOP_N",
            "CLM_ACCELERATED_SPINUP", "CCSM_CO2_PPMV")
LAND_KEYS = ("fsurdat", "fates_paramfile", "finidat", "use_fates",
             "use_fates_fixed_biogeog", "use_fates_nocomp",
             "use_fates_sp", "spinup_state", "hist_fincl1")
DATM_KEYS = ("year_first", "year_last", "year_align", "streams", "taxmode")
NC_FIELDS = ("LATIXY", "LONGXY", "PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT",
             "PCT_SAND", "PCT_CLAY", "ORGANIC", "SOIL_COLOR")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_mix(text):
    out = {}
    for item in text.split("|"):
        key, value = item.split(":")
        index, number = int(key), float(value)
        if index in out or not 0 <= index < 15 or not math.isfinite(number) or number < 0:
            raise ValueError("invalid PFT: " + item)
        out[index] = number
    if not math.isclose(sum(out.values()), 100, abs_tol=1e-7):
        raise ValueError("PFT composition not 100")
    return out


def load_register():
    ops, gates = read_csv(OPERATOR), read_csv(GATES)
    if tuple(r["site"] for r in ops) != SITES or tuple(r["site"] for r in gates) != SITES:
        raise ValueError("exact 6-site register/order changed")
    for row in ops:
        site = row["site"]
        if row["source_git_blob"] != SOURCE_BLOB:
            raise ValueError(site + ": source provenance changed")
        if parse_mix(row["host_natpft_nonzero_percent"]) != EXPECTED[site]:
            raise ValueError(site + ": operator-selected PFT changed")
        if not row["operator_decision"].startswith("ACCEPTED_PROXY"):
            raise ValueError(site + ": no selected proxy")
    return {r["site"]: r for r in ops}, {r["site"]: r for r in gates}


def assignments(text, keys):
    out = {}
    for key in keys:
        matches = re.findall(r"(?im)^[ \t]*" + re.escape(key) +
                             r"[ \t]*=[ \t]*([^\r\n]*)", text)
        if len(matches) > 1:
            out[key] = "AMBIGUOUS_DUPLICATE"
        elif matches:
            quote, clean = None, []
            for char in matches[0]:
                if char in ("'", '"'):
                    quote = None if quote == char else (char if quote is None else quote)
                if char == "!" and quote is None:
                    break
                clean.append(char)
            out[key] = "".join(clean).strip().rstrip(",").strip().strip("'\"")
    return out


def xml_metadata(case):
    all_values = {}
    for fname in XML_FILES:
        path = case / fname
        if path.is_file():
            for entry in ET.parse(path).getroot().iter("entry"):
                key, value = entry.get("id"), entry.get("value")
                if key and value is not None:
                    all_values[key] = value
    return {key: all_values[key] for key in XML_KEYS if key in all_values}


def file_info(path, hash_limit=20_000_000):
    result = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        result["bytes"] = path.stat().st_size
        result["sha256"] = (sha256(path) if result["bytes"] <= hash_limit
                            else "NOT_HASHED_SIZE_LIMIT")
    return result


def surface_info(path):
    result = file_info(path)
    if not path.is_file():
        return result
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        result["read_error"] = "numpy/netCDF4 required in clm_fates_env: " + str(exc)
        return result
    try:
        with Dataset(path, "r") as ds:
            result["fields"] = {}
            for key in NC_FIELDS:
                if key not in ds.variables:
                    result["fields"][key] = {"status": "MISSING"}
                    continue
                var = ds.variables[key]
                if var.size > 50000:
                    result["fields"][key] = {"shape": list(var.shape),
                                             "status": "SKIPPED_NOT_SITE_POINT_SIZE"}
                    continue
                data = np.ma.asarray(var[:])
                array = np.ma.filled(data.astype(float), np.nan)
                finite = array[np.isfinite(array)]
                item = {"shape": list(array.shape), "elements": int(array.size)}
                if finite.size:
                    item.update(min=float(finite.min()), max=float(finite.max()))
                    if array.size <= 20:
                        item["values"] = [float(v) if np.isfinite(v) else None
                                          for v in array.flat]
                else:
                    item["error"] = "NO_FINITE_VALUES"
                result["fields"][key] = item
            if ds.variables.get("PCT_NAT_PFT") is not None:
                var = np.ma.asarray(ds.variables["PCT_NAT_PFT"][:])
                if var.size == 15:
                    vals = np.ma.filled(var.astype(float), np.nan).reshape(-1)
                    result["original_natpft_vector"] = [float(v) for v in vals]
                    result["original_natpft_sum"] = float(np.nansum(vals))
    except Exception as exc:
        result["read_error"] = type(exc).__name__ + ": " + str(exc)
    return result


def static_path(value):
    if not value or "$" in value or value == "AMBIGUOUS_DUPLICATE":
        return None
    path = Path(value)
    return path if path.is_absolute() else None


def point_check(xml, surface):
    try:
        fields = surface["fields"]
        lat, lon = float(xml["PTS_LAT"]), float(xml["PTS_LON"]) % 360
        surface_lat = fields["LATIXY"]["values"][0]
        surface_lon = fields["LONGXY"]["values"][0] % 360
        delta_lon = abs((lon - surface_lon + 180) % 360 - 180)
        if abs(lat - surface_lat) > 0.001 or delta_lon > 0.001:
            return "MISMATCH_STOP"
        return "MATCH_STATIC_XML_EFFECTIVE_CIME_NOT_YET_VERIFIED"
    except (KeyError, IndexError, TypeError, ValueError):
        return "UNVERIFIED_MISSING_POINT_OR_SURFACE"


def candidates(base, site):
    case_root = base / "cases"
    if not case_root.is_dir():
        return []
    return sorted((p for p in case_root.iterdir()
                   if p.is_dir() and p.name.startswith(site + "_") and
                   all(tag not in p.name.upper() for tag in ("FIXNC", "OBSPFT", "NOCOMP"))),
                  key=lambda p: p.name)


def inspect_case(case):
    result = {"case": case.name, "path": str(case),
              "status": "SOURCE_CANDIDATE_UNSELECTED"}
    try:
        result["xml"] = xml_metadata(case)
    except (ET.ParseError, OSError) as exc:
        result["xml_error"] = str(exc)
        result["xml"] = {}
    docs = case / "CaseDocs"
    lnd, datm = docs / "lnd_in", docs / "datm_in"
    result["case_documents"] = [file_info(p) for p in (lnd, datm)]
    result["land"] = assignments(lnd.read_text(errors="replace"), LAND_KEYS) if lnd.is_file() else {}
    result["datm"] = assignments(datm.read_text(errors="replace"), DATM_KEYS) if datm.is_file() else {}
    fsurdat = static_path(result["land"].get("fsurdat"))
    result["original_surface"] = (surface_info(fsurdat) if fsurdat else
                                  {"status": "UNRESOLVED_FSURDAT"})
    result["point_check"] = point_check(result["xml"], result["original_surface"])
    fates = static_path(result["land"].get("fates_paramfile"))
    result["fates_paramfile"] = (file_info(fates) if fates else
                                 {"status": "UNRESOLVED_FATES_PARAMFILE"})
    data_list = case / "Buildconf/datm.input_data_list"
    result["datm_input_list"] = file_info(data_list)
    if data_list.is_file():
        lines = data_list.read_text(errors="replace").splitlines()
        result["datm_source_references_excerpt"] = [x[:300] for x in lines[:30]]
        result["datm_input_list_total_lines"] = len(lines)
    result["datm_stream_documents"] = [file_info(p) for p in sorted(docs.glob("*stream*"))[:30]
                                        if p.is_file()] if docs.is_dir() else []
    result["forcing_qc"] = "HOLD_NO_HALF_HOURLY_OR_ANNUAL_QC_PERFORMED"
    return result


def inspect_site(base, site, operator, gate):
    site_root = base / "sites/MY_EC_SITE" / site
    forcing = site_root / "forcing"
    dirs = sorted(x.name for x in forcing.iterdir() if x.is_dir()) if forcing.is_dir() else []
    case_records = []
    for case in candidates(base, site):
        try:
            case_records.append(inspect_case(case))
        except (OSError, ValueError) as exc:
            case_records.append({"case": case.name, "error": str(exc), "status": "HOLD"})
    return {
        "site": site, "source_site_dir": str(site_root),
        "source_site_present": site_root.is_dir(),
        "operator_PCT_NAT_PFT": operator["host_natpft_nonzero_percent"],
        "PFT_semantics": "CONDITIONAL_NATVEG_MODEL_PROXY_NOT_OBSERVED_EC_AREA",
        "scientific_hold": gate["scientific_hold"],
        "technical_hold": gate["technical_hold"],
        "forcing_dir_candidates": dirs,
        "source_case_candidates": case_records,
        "template_selection": "UNSELECTED_NO_IMPLICIT_LATEST_CASE",
        "forcing_status": "HOLD_SOURCE_HH_QC_TIME_SEAMS_VPD_RH_T_PRECIP",
        "surface_status": "HOLD_SITE_POINT_PFT_LANDUNIT_SOIL_FATES_MAP",
        "release": "HOLD_NO_SURFACE_OR_AD5_OR_AD400_AUTHORIZATION",
    }


def self_test():
    rows, gates = load_register()
    assert set(rows) == set(gates) == set(SITES)
    assert sum(EXPECTED["GL-ZaH"].values()) == 100
    assert not set(SITES) & {"DE-Tha", "NL-Loo"}
    assert assignments("fsurdat = '/x/surf.nc' ! comment\n", ("fsurdat",))["fsurdat"] == "/x/surf.nc"
    assert assignments("a=1\na=2", ("a",))["a"] == "AMBIGUOUS_DUPLICATE"
    data = {"fields": {"LATIXY": {"values": [50]}, "LONGXY": {"values": [358]}}}
    assert point_check({"PTS_LAT": "50", "PTS_LON": "-2"}, data).startswith("MATCH")
    assert point_check({"PTS_LAT": "40", "PTS_LON": "-2"}, data) == "MISMATCH_STOP"
    print("SELF-TEST PASS: 6 exact sites, selected PFT proxies, source guards and point check; NO WRITES")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--base", type=Path, default=BASE)
    p.add_argument("--sites", nargs="+", choices=SITES, default=list(SITES))
    p.add_argument("--report", type=Path, help="New report path with existing parent; refuse overwrite")
    x = p.parse_args()
    if x.self_test:
        if x.report:
            p.error("self-test does not write a report")
        self_test()
        return
    rows, gates = load_register()
    if not x.base.is_dir():
        p.error("source root not found: " + str(x.base))
    report = {
        "batch": "ICOS_BATCH04_SIX", "inspection_only": True,
        "slurm_submitted": False, "surface_created": False, "case_created": False,
        "source_changed": False, "science_release": False,
        "source_register": str(OPERATOR), "source_register_sha256": sha256(OPERATOR),
        "gate_register": str(GATES), "gate_register_sha256": sha256(GATES),
        "base": str(x.base), "protected_examples": ["DE-Tha", "NL-Loo"],
        "sites": [inspect_site(x.base, site, rows[site], gates[site])
                  for site in dict.fromkeys(x.sites)]
    }
    for item in report["sites"]:
        print(item["site"], "source_present=", item["source_site_present"],
              "source_cases=", len(item["source_case_candidates"]),
              "forcing_dirs=", len(item["forcing_dir_candidates"]), "HOLD")
        for case in item["source_case_candidates"]:
            print("  ", case["case"], "point=", case.get("point_check", "UNVERIFIED"))
    if x.report:
        path = x.report.expanduser().resolve()
        if not path.parent.is_dir():
            p.error("report parent does not exist; do not create folders: " + str(path.parent))
        with path.open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        print("NEW JSON REPORT:", path)
    print("READ-ONLY; NO CIME/SLURM OR SOURCE CHANGES; ALL SITES HOLD")


if __name__ == "__main__":
    main()
