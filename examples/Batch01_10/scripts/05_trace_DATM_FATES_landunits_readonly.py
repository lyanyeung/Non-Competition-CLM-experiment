#!/usr/bin/env python3
"""Batch01 Stage05 — READ ONLY CIME/DATM/FATES/landunit diagnostic.

Reads the existing Stage03 report and each original case's SMALL TEXT config
files. Reads no forcing arrays; does not write NetCDF, restart, cases or Slurm
jobs. Creates only a new timestamped HOME report directory.

Run:
 python3 -B examples/Batch01_10/scripts/05_trace_DATM_FATES_landunits_readonly.py --self-test
 python3 -B examples/Batch01_10/scripts/05_trace_DATM_FATES_landunits_readonly.py \
   --stage03 "$HOME/Batch01_10_stage03_surface_soil_20261024T094433Z/all_sites.json"
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SITES = ("CZ-BK1", "IT-Ren", "RU-Fyo", "CH-Dav", "IT-Col",
         "FR-Fon", "FI-Sod", "FR-Pue", "DE-Hai", "BE-Vie")
CASE_ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
SCALAR_LAND = ("PCT_NATVEG", "PCT_CROP", "PCT_LAKE",
               "PCT_WETLAND", "PCT_GLACIER")
NML_NAMES = ("fsurdat", "finidat", "use_fates", "use_fates_sp",
             "use_fates_nocomp", "use_fates_fixed_biogeog",
             "fates_hlm_pft_map", "fates_paramfile", "spinup_state",
             "year_first", "year_last", "year_align", "streams")
XML_NAMES = ("RUN_STARTDATE", "RUN_TYPE", "CLM_ACCELERATED_SPINUP",
             "CLM_CO2_TYPE", "CCSM_CO2_PPMV", "DATM_MODE",
             "DATM_YR_START", "DATM_YR_END", "DATM_YR_ALIGN",
             "DATM_CO2_TSERIES", "COMPSET", "CALENDAR",
             "RUNDIR", "DOUT_S_ROOT", "EXEROOT", "STOP_OPTION",
             "STOP_N", "RESUBMIT", "REST_OPTION", "REST_N")
DOC_REL = ("CaseDocs/lnd_in", "CaseDocs/datm_in",
           "CaseDocs/datm.streams.xml", "user_nl_clm",
           "user_nl_datm", "user_nl_datm_streams",
           "Buildconf/datm.input_data_list")
MAX_BYTES = 2_000_000
MAX_STREAM_DOCS = 15


def fail(message):
    raise SystemExit(str(message))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_text(path):
    if path.is_symlink():
        return None, "SYMLINK_NOT_FOLLOWED"
    if not path.is_file():
        return None, "ABSENT"
    if path.stat().st_size > MAX_BYTES:
        return None, "TOO_LARGE"
    try:
        return path.read_text(encoding="utf-8", errors="replace"), "OK"
    except OSError as exc:
        return None, "READ_ERROR:" + str(exc)


def nml_values(text):
    values = {}
    for name in NML_NAMES:
        m = re.findall(r"(?im)^\s*" + re.escape(name) +
                       r"\s*=\s*(.*?)\s*(?:!.*)?$", text)
        if m:
            values[name] = m[-1].strip()
    return values


def xml_values(case):
    values = {}
    for filename in ("env_run.xml", "env_case.xml", "env_build.xml"):
        file = case / filename
        raw, status = safe_text(file)
        if status != "OK":
            continue
        try:
            root = ET.fromstring(raw)
            for entry in root.iter("entry"):
                key = entry.attrib.get("id")
                if key in XML_NAMES:
                    values[key] = entry.attrib.get("value", "")
        except ET.ParseError as exc:
            values["_ERROR_" + filename] = str(exc)
    return values


def parse_years(text):
    out = {}
    for key in ("year_first", "year_last", "year_align"):
        m = re.findall(r"(?im)(?:^|[\s<])" + key +
                       r"\s*(?:=|:|>)\s*['\"]?(\d{4})\b", text)
        if m:
            out[key] = m[-1]
    return out


def excerpts(text):
    result = []
    tokens = ("file", "path", "stream", "year", "domain",
              ".nc", "fates", "fsurdat", "co2", "tintalgo")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if any(token in s.lower() for token in
               ("password", "api_key", "private_key", "secret", "token=")):
            continue
        if any(token in s.lower() for token in tokens):
            result.append(s[:260])
            if len(result) >= 16:
                break
    return result


def read_document(file):
    text, status = safe_text(file)
    item = {"path": str(file), "status": status}
    if status != "OK":
        return item
    item["sha256"] = digest(file)
    item["namelist"] = nml_values(text)
    item["year_fields"] = parse_years(text)
    item["input_excerpts"] = excerpts(text)
    # These are only filename hints, NEVER certified contiguous forcing years.
    hints = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", text)
    item["year_hints_NOT_VALIDATED"] = sorted(set(hints))[:30]
    return item


def related_docs(case, original_config):
    result = []
    added = set()

    def add(file):
        s = str(file)
        if s not in added:
            added.add(s)
            result.append(file)

    for relative in DOC_REL:
        add(case / relative)
    for file in sorted((case / "CaseDocs").glob("datm.streams.*"))[:MAX_STREAM_DOCS]:
        add(file)
    # The actual runtime alias may be /scratch rather than /iridisfs/scratch.
    # If absent, report it; never manufacture a replacement.
    rundir = original_config.get("RUNDIR")
    if isinstance(rundir, str) and rundir.startswith("/"):
        root = Path(rundir)
        if root.is_dir():
            for filename in ("datm_in", "lnd_in", "datm.streams.xml"):
                add(root / filename)
            for file in sorted(root.glob("datm.streams.*"))[:MAX_STREAM_DOCS]:
                add(file)
    return result[:65]


def scalar(site, name):
    ok = [item for item in site.get("surface_reviews", [])
          if item.get("read_status") == "READ_OK"]
    if len(ok) != 1:
        return None
    variable = ok[0].get("fields", {}).get(name, {})
    shape = variable.get("shape", [])
    arr = variable.get("sample_first_12", [])
    if not shape or math.prod(shape) != 1 or len(arr) != 1:
        return None
    v = arr[0]
    if v is None or not isinstance(v, (float, int)) or not math.isfinite(v):
        return None
    return float(v)


def inspect_case(site_id, case_entry):
    case = Path(case_entry.get("path", ""))
    cfg = case_entry.get("run_configuration", {})
    output = {"name": case_entry.get("case"), "path": str(case),
              "case_exists": case.is_dir(),
              "case_metadata": cfg, "documents": []}
    if case.parent != CASE_ROOT or not case.name.startswith(site_id + "_"):
        output["error"] = "UNEXPECTED_CASE_PATH"
        return output
    if not case.is_dir():
        output["error"] = "ORIGINAL_CASE_NOT_FOUND"
        return output
    output["xml_values"] = xml_values(case)
    output["documents"] = [read_document(doc) for doc in related_docs(case, cfg)]
    generated_lnd = [
        d for d in output["documents"]
        if d["path"].endswith(("/CaseDocs/lnd_in", "/run/lnd_in")) and
        d.get("status") == "OK"
    ]
    output["lnd_namelist_candidates"] = [
        {"source_path": d["path"], "values": d["namelist"]} for d in generated_lnd
    ]
    calendar = {}
    for doc in output["documents"]:
        if doc.get("status") == "OK":
            for key, value in doc.get("year_fields", {}).items():
                calendar.setdefault(key, value)
            for key, value in doc.get("namelist", {}).items():
                if key in ("year_first", "year_last", "year_align"):
                    calendar.setdefault(key, value)
    for x, k in (("DATM_YR_START", "year_first"),
                 ("DATM_YR_END", "year_last"),
                 ("DATM_YR_ALIGN", "year_align")):
        val = output["xml_values"].get(x)
        if val and k not in calendar:
            calendar[k] = val
    output["reported_datm_years"] = calendar
    output["datm_source_status"] = (
        "YEARS_PRESENT_REQUIRES_STREAM_FILE_VALIDATION" if calendar
        else "YEARS_NOT_FOUND_IN_SCANNED_CONFIG"
    )
    return output


def run(input_path):
    if input_path.name != "all_sites.json" or not (
            input_path.parent.name.startswith("Batch01_10_stage03_surface_soil_")):
        fail("Input must be the timestamped Stage03 all_sites.json")
    if not input_path.is_file():
        fail("Missing Stage03 JSON: " + str(input_path))
    inp = json.loads(input_path.read_text(encoding="utf-8"))
    if any(inp.get(k) is not False for k in (
            "original_inputs_modified", "slurm_submitted",
            "production_surfaces_approved")):
        fail("Stage03 safety flags invalid; abort")
    rows = inp.get("sites", [])
    if tuple(row.get("site") for row in rows) != SITES:
        fail("Unexpected Stage03 site membership/order")
    out = []
    print("=== BATCH01 STAGE05 ORIGINAL CASE / DATM / FATES AUDIT: READ ONLY ===")
    print("DATM dates are evidence fields, not verified contiguous forcing ranges.")
    print("NATVEG/CROP are inherited host-grid landunits, not approved tower areas.")
    for site in rows:
        site_id = site["site"]
        cases = [inspect_case(site_id, x) for x in site.get("cases", [])]
        landunits = {name: scalar(site, name) for name in SCALAR_LAND}
        total = None
        if all(v is not None for v in landunits.values()):
            total = round(sum(landunits.values()), 5)
        summary = {"site": site_id, "old_case_count": len(cases),
                   "candidate_tree_mix": site["candidate_tree_pft_pct"],
                   "source_host_landunits": landunits,
                   "five_landunit_sum_if_all_scalar": total,
                   "cases": cases, "release": "HOLD"}
        out.append(summary)
        print(f"{site_id}: CASES={len(cases)} "
              f"NAT={landunits['PCT_NATVEG']} CROP={landunits['PCT_CROP']} "
              f"OTHER_LANDUNIT_SUM={total}")
        for case in cases:
            years = case.get("reported_datm_years", {})
            xm = case.get("xml_values", {})
            print("  CASE:", case["name"])
            print("  DATM_FIELDS:", "/".join(
                str(years.get(k, "?")) for k in (
                    "year_first", "year_last", "year_align")))
            print("  DATM_MODE:", xm.get("DATM_MODE", "?"),
                  "RUN_STARTDATE:", xm.get("RUN_STARTDATE", "?"),
                  "CO2:", xm.get("CLM_CO2_TYPE", "?"))
            for land in case.get("lnd_namelist_candidates", []):
                pft_fields = {k: v for k, v in land["values"].items()
                              if k.startswith("use_fates") or
                              k in ("fates_hlm_pft_map", "fates_paramfile",
                                    "spinup_state", "fsurdat")}
                print("  GENERATED_LND:", land["source_path"])
                print("  FATES_FIELDS:", json.dumps(
                    pft_fields, ensure_ascii=False)[:650])
            active = [
                d for d in case.get("documents", [])
                if d["status"] == "OK" and
                ("datm" in d["path"].lower() or
                 "input_data_list" in d["path"].lower())
            ]
            print("  DATM_CONFIG_DOCS:", len(active))
            for d in active[:5]:
                print("    ", d["path"])
                for snippet in d.get("input_excerpts", [])[:4]:
                    print("      ", snippet)
            if not active:
                print("  WARNING: NO_READABLE_GENERATED_DATM_DOCUMENTS")
        print("  SCIENTIFIC_GATE: HOLD")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path.home().resolve() / ("Batch01_10_stage05_input_audit_" + stamp)
    folder.mkdir(mode=0o700, exist_ok=False)
    result = {
        "stage03_source": str(input_path),
        "stage03_sha256": digest(input_path),
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "original_model_files_modified": False,
        "model_jobs_submitted": False,
        "cases_or_surfaces_approved": False,
        "sites": out,
    }
    target = folder / "all_sites.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("AUDIT JSON:", target)
    print("NO PRODUCTION SURFACE/CASE/FORCING/SLURM MODIFIED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage03", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert len(SITES) == len(set(SITES)) == 10
        assert nml_values("  use_fates_nocomp = .true.\n") == {
            "use_fates_nocomp": ".true."}
        assert parse_years("year_first = 2001\n year_last=2020\n") == {
            "year_first": "2001", "year_last": "2020"}
        assert parse_years("<year_align>1997</year_align>") == {
            "year_align": "1997"}
        print("STAGE05 SELF-TEST PASS: identifiers and text parsers; no writes")
        return
    if args.stage03 is None:
        parser.error("--stage03 is required unless --self-test")
    run(args.stage03.expanduser().resolve())


if __name__ == "__main__":
    main()
