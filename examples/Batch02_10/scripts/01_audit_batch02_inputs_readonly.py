#!/usr/bin/env python3
"""Batch02 ICOS/European FIXNC input inventory; model inputs are read only.

Audit actual CIME XML, generated land/DATM namelists, active surface and
FATES parameter files. Only a NEW report directory is created. No xmlquery,
preview_namelists, case cloning, NetCDF writes, Slurm or shell calls occur.
An inventory PASS is not scientific approval or AD400 readiness.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REGISTER = REPO / "data/batch02_10_sites.csv"
DECISIONS = REPO / "data/batch02_10_input_gates.csv"
SITES = ("DK-Sor", "FR-Hes", "FR-FBn", "BE-Bra", "IT-Noe",
         "CH-Fru", "CH-Lae", "ES-LJu", "FI-Hyy", "IT-MBo")
EXCLUDED = {"NL-Loo", "DE-Tha", "CZ-BK1", "IT-Ren", "RU-Fyo", "CH-Dav",
            "IT-Col", "FR-Fon", "FI-Sod", "FR-Pue", "DE-Hai", "BE-Vie"}
BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
XML_KEYS = ("CASE", "CASEROOT", "SRCROOT", "CIMEROOT", "DIN_LOC_ROOT",
            "CIME_OUTPUT_ROOT", "EXEROOT", "RUNDIR", "DOUT_S_ROOT",
            "RUN_TYPE", "RUN_STARTDATE", "RUN_REFCASE", "RUN_REFDATE",
            "CONTINUE_RUN", "RESUBMIT", "STOP_OPTION", "STOP_N",
            "REST_OPTION", "REST_N", "CALENDAR", "ATM_NCPL", "DATM_MODE",
            "DATM_CLMNCEP_YR_START", "DATM_CLMNCEP_YR_END",
            "DATM_CLMNCEP_YR_ALIGN", "CLM_ACCELERATED_SPINUP", "CLM_CO2_TYPE",
            "CCSM_CO2_PPMV", "CCSM_BGC", "DATM_CO2_TSERIES", "COMPSET",
            "BUILD_COMPLETE", "LND_TUNING_MODE", "MPI_RUN_COMMAND",
            "NTASKS_LND", "NTHRDS_LND", "NTASKS_ATM", "NTHRDS_ATM")
NML_KEYS = ("fsurdat", "finidat", "fates_paramfile", "paramfile",
            "spinup_state", "use_cn", "use_fates", "use_fates_sp",
            "use_fates_nocomp", "use_fates_fixed_biogeog", "co2_type",
            "co2_ppmv", "fates_spitfire_mode")
LAND_FIELDS = ("PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND",
               "PCT_GLACIER", "PCT_URBAN", "PCT_NAT_PFT", "PCT_SAND",
               "PCT_CLAY", "ORGANIC", "SOIL_COLOR", "LATIXY", "LONGXY")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_register(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if tuple(r["site"] for r in rows) != SITES or len(set(SITES)) != 10:
        raise ValueError("Expected exactly ten Batch02 sites in selected order: " + str(path))
    if set(SITES) & EXCLUDED:
        raise ValueError("Batch02 overlaps protected examples or Batch01")
    return rows


def resolve_value(value, entries):
    """Resolve simple CIME $NAME/${NAME} references; never execute XML code."""
    pattern = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")
    for _ in range(20):
        new = pattern.sub(lambda m: entries.get(m.group(1) or m.group(2), m.group(0)), value)
        if new == value:
            break
        value = new
    return value


def xml_metadata(case):
    entries, errors = {"CASEROOT": str(case)}, []
    for filename in ("env_case.xml", "env_build.xml", "env_run.xml",
                     "env_mach_pes.xml", "env_batch.xml"):
        p = case / filename
        if not p.is_file():
            continue
        try:
            for ent in ET.parse(p).getroot().iter("entry"):
                key, val = ent.get("id"), ent.get("value")
                if key and val is not None:
                    entries[key] = val
        except (ET.ParseError, OSError) as exc:
            errors.append(filename + ": " + str(exc))
    return {
        "raw": {k: entries[k] for k in XML_KEYS if k in entries},
        "resolved": {k: resolve_value(entries[k], entries) for k in XML_KEYS if k in entries},
        "errors": errors,
        "scope": "static entry values only; conditional XML defaults are not a runtime CIME query",
    }


def nml_values(text, keys):
    values = {}
    for key in keys:
        found = re.findall(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*([^\r\n]*)", text)
        if len(found) == 1:
            # Preserve ! inside quoted filenames; remove unquoted comments only.
            quote, chars = None, []
            for char in found[0]:
                if char in "'\"":
                    quote = None if quote == char else (char if quote is None else quote)
                if char == "!" and quote is None:
                    break
                chars.append(char)
            values[key] = "".join(chars).strip().rstrip(",").strip().strip("'\"")
        elif found:
            values[key] = "AMBIGUOUS_DUPLICATE_KEY"
    return values


def file_record(path, *, text=False):
    record = {"path": str(path), "exists": path.is_file(), "is_symlink": path.is_symlink()}
    if not path.is_file():
        return record
    size = path.stat().st_size
    record["bytes"] = size
    if size <= 200_000_000:
        record["sha256"] = sha256(path)
    else:
        record["sha256_status"] = "SKIPPED_OVER_200MB"
    if text and size <= 2_000_000:
        content = path.read_text(encoding="utf-8", errors="replace")
        record["values"] = nml_values(content, NML_KEYS + ("year_first", "year_last", "year_align", "streams"))
        lines = []
        for line in content.splitlines():
            low = line.lower()
            if any(s in low for s in ("password", "token", "secret", "private_key")):
                continue
            if any(s in low for s in (".nc", "datafiles", "datadir", "domain", "year_", "stream")):
                lines.append(line.strip()[:300])
            if len(lines) == 24:
                break
        record["reference_excerpt"] = lines
    return record


def netcdf_summary(path, fields):
    out = file_record(path)
    if not out["exists"]:
        return out
    try:
        import numpy as np
        from netCDF4 import Dataset
        with Dataset(path, "r") as ds:
            out["dimensions"] = {k: len(v) for k, v in ds.dimensions.items()}
            out["variables"] = {}
            for key in fields:
                if key not in ds.variables:
                    continue
                v = ds.variables[key]
                info = {"dimensions": v.dimensions, "shape": v.shape}
                if v.size <= 2000:
                    data = np.ma.asarray(v[:])
                    if data.dtype.kind in "biuf":
                        a = np.ma.filled(data.astype(float), np.nan).reshape(-1)
                        info["values"] = [float(x) if np.isfinite(x) else None for x in a]
                    else:
                        info["text"] = str(data.tolist())[:3000]
                else:
                    info["read_status"] = "SKIPPED_NOT_SMALL_POINT_FIELD"
                out["variables"][key] = info
            if "PCT_NAT_PFT" in ds.variables:
                out["interpretation"] = "Original model grid PFTs; NOT observed station composition"
    except ImportError as exc:
        out["read_error"] = str(exc) + "; activate clm_fates_env with numpy and netCDF4"
    except Exception as exc:
        out["read_error"] = type(exc).__name__ + ": " + str(exc)
    return out


def absolute_reference(value):
    if not value or value == "AMBIGUOUS_DUPLICATE_KEY" or "$" in value:
        return None
    p = Path(value)
    # Relative namelist inputs are resolved by the model in RUNDIR, not CASEROOT.
    # Record them but do not guess a source path.
    return p if p.is_absolute() else None


def inspect_case(case, base):
    meta = xml_metadata(case)
    docs = case / "CaseDocs"
    lnd = docs / "lnd_in"
    lnd_text = lnd.read_text(errors="replace") if lnd.is_file() else ""
    values = nml_values(lnd_text, NML_KEYS)
    out = {"name": case.name, "path": str(case), "xml": meta, "land_namelist": values}
    sources = [case / "user_nl_clm", case / "user_nl_datm", case / "user_nl_datm_streams",
               lnd, docs / "datm_in", docs / "datm.streams.xml",
               case / "Buildconf/datm.input_data_list"]
    sources += sorted(docs.glob("*stream*"))[:30]
    rd = meta["resolved"].get("RUNDIR", "")
    if rd.startswith("/") and "$" not in rd:
        run = Path(rd)
        sources += [run / "lnd_in", run / "datm_in"]
        sources += sorted(run.glob("*stream*"))[:30]
    out["input_documents"] = [file_record(p, text=True) for p in dict.fromkeys(sources) if p.is_file()]
    for key in ("fsurdat", "fates_paramfile"):
        p = absolute_reference(values.get(key))
        if p is not None:
            out[key] = netcdf_summary(p, LAND_FIELDS if key == "fsurdat" else
                                     ("fates_hlm_pft_map", "fates_pftname"))
        else:
            out[key + "_status"] = "MISSING_OR_UNRESOLVED_REFERENCE"
    exe = meta["resolved"].get("EXEROOT", "")
    if exe.startswith("/") and "$" not in exe:
        out["executable"] = file_record(Path(exe) / "cesm.exe")
    run_script = case / ".case.run"
    if run_script.is_file():
        out["SBATCH"] = [x.strip() for x in run_script.read_text(errors="replace").splitlines()
                         if x.lstrip().startswith("#SBATCH")]
    status = case / "CaseStatus"
    if status.is_file():
        # Historical success is an inventory clue, not a completion certificate.
        out["CaseStatus_tail"] = status.read_text(errors="replace").splitlines()[-8:]
    return out


def source_case_match(name, site):
    # Repaired source cases such as IT-Noe_ERA5_ABW_BRANCH2009 need not
    # contain FATES/SPINUP in their names. Inventory every exact site prefix.
    return (name.startswith(site + "_")
            and not any(x in name.upper() for x in ("FIXNC", "OBSPFT", "NOCOMP")))


def audit(base, report_root):
    register, decisions = read_register(REGISTER), read_register(DECISIONS)
    by_site = {r["site"]: r for r in decisions}
    case_root = base / "cases"
    candidates = sorted((p for p in case_root.iterdir() if p.is_dir()), key=lambda p: p.name) if case_root.is_dir() else []
    rows = []
    for r in register:
        site = r["site"]
        folder = base / "sites/MY_EC_SITE" / site
        cases = [p for p in candidates if source_case_match(p.name, site)]
        row = {"site": site, "site_exists": folder.is_dir(), "evidence": r,
               "input_decision": by_site[site], "cases": [], "errors": [],
               "scientific_readiness": "HOLD_PFT_SOIL_AND_ACTIVE_MAPPING",
               "case_selection": "REQUIRES_REVIEW_NO_LATEST_CASE_AUTOSELECTION"}
        for case in cases:
            try:
                row["cases"].append(inspect_case(case, base))
            except Exception as exc:
                row["errors"].append(str(case) + ": " + str(exc))
        fallback = sorted((folder / "subset_data").glob("*.nc"))[:20]
        row["surface_candidates"] = [netcdf_summary(p, LAND_FIELDS) for p in fallback]
        forcing = folder / "forcing"
        row["forcing_directories"] = sorted(p.name for p in forcing.iterdir() if p.is_dir()) if forcing.is_dir() else []
        row["forcing_audit_scope"] = "Active generated stream references only; no annual/hourly forcing revalidation"
        rows.append(row)
    out = report_root.expanduser().resolve() / ("Batch02_10_preflight_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"))
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {"cohort": "ICOS_EUROPE_BATCH02", "protocol": "AD400_THEN_NORMAL400",
              "segments_per_mode": {"smoke_years": 5, "continuation_years": 395,
                                    "STOP_N": 5, "smoke_RESUBMIT": 0, "continuation_RESUBMIT": 78},
              "register_sha256": sha256(REGISTER), "decision_sha256": sha256(DECISIONS),
              "script_sha256": sha256(Path(__file__)), "base": str(base),
              "original_model_files_modified": False, "model_jobs_submitted": False,
              "audit_completed_is_not_model_readiness": True, "sites": rows}
    (out / "all_sites.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    fields = ["site", "site_exists", "cases", "active_surfaces", "surface_read_errors", "scientific_gate", "PFT_issue"]
    with (out / "summary.csv").open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        print("SITE     EXISTS  CASES  ACTIVE_SURF  SCIENTIFIC")
        for row in rows:
            active = [c["fsurdat"] for c in row["cases"] if "fsurdat" in c]
            errors = sum(bool(p.get("read_error")) for p in active)
            writer.writerow({"site": row["site"], "site_exists": row["site_exists"],
                             "cases": len(row["cases"]), "active_surfaces": sum(p["exists"] for p in active),
                             "surface_read_errors": errors, "scientific_gate": row["scientific_readiness"],
                             "PFT_issue": row["input_decision"]["unresolved_PFT"]})
            print(f"{row['site']:<8} {str(row['site_exists']):<6} {len(row['cases']):>5} {sum(p['exists'] for p in active):>12}  HOLD")
            for c in row["cases"]:
                print("  CASE", c["name"])
                print("  FSURDAT", c.get("land_namelist", {}).get("fsurdat", "UNKNOWN"))
                print("  START/CO2", c["xml"]["resolved"].get("RUN_STARTDATE", "UNKNOWN"),
                      c["xml"]["resolved"].get("CLM_CO2_TYPE", "UNKNOWN"),
                      c["xml"]["resolved"].get("CCSM_CO2_PPMV", "UNKNOWN"))
            print("  PFT HOLD:", row["input_decision"]["unresolved_PFT"])
    print("REPORT_JSON=" + str(out / "all_sites.json"))
    print("REPORT_CSV=" + str(out / "summary.csv"))
    print("AUDIT COMPLETED. This is NOT an input-readiness PASS.")
    print("No surface/forcing/CIME/source edits; no model jobs submitted.")
    return out


def self_test():
    register, gates = read_register(REGISTER), read_register(DECISIONS)
    assert all(r["readiness"] == "EVIDENCE_ONLY_HOLD_SURFACE" for r in register)
    assert all(r["readiness"] == "HOLD" for r in gates)
    assert len([r for r in gates if r["ecosystem"] == "FOREST"]) == 6
    assert resolve_value("$ROOT/${CASE}/run", {"ROOT": "/scratch", "CASE": "x"}) == "/scratch/x/run"
    assert resolve_value("$A", {"A": "$B", "B": "$A"}).startswith("$")
    assert nml_values(" fsurdat = '/x/a!b.nc' ! comment\n", ("fsurdat",))["fsurdat"] == "/x/a!b.nc"
    assert nml_values("use_fates=.true.\nuse_fates=.false.\n", ("use_fates",))["use_fates"] == "AMBIGUOUS_DUPLICATE_KEY"
    assert source_case_match("IT-Noe_FATES_SPINUP500_11P", "IT-Noe")
    assert source_case_match("IT-Noe_ERA5_ABW_BRANCH2009", "IT-Noe")
    assert not source_case_match("IT-Noe_B02_FIXNC_AD400", "IT-Noe")
    assert not source_case_match("FI-Sod_FATES_SPINUP500", "FI-Hyy")
    assert not source_case_match("DK-Sor2_FATES_SPINUP500", "DK-Sor")
    print("SELF-TEST PASS: exact ten-site cohort; no Batch01 overlap; PFT holds preserved;")
    print("XML expansion, namelist ambiguity and exact source-case matching verified. NO WRITES.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "audit"))
    p.add_argument("--base", type=Path, default=BASE)
    p.add_argument("--report-root", type=Path, default=Path.home())
    a = p.parse_args()
    if a.action == "self-test":
        self_test()
    else:
        audit(a.base.expanduser().resolve(), a.report_root)


if __name__ == "__main__":
    main()
