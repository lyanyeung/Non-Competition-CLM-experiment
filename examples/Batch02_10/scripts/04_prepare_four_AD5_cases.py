#!/usr/bin/env python3
"""Prepare four independent Batch02 AD5 cases from verified Stage03 candidates.

No model submission. Reuse source executables/forcing, never source restarts.
The pinned, two-change Batch01 FATES build-namelist overlay is private. Restore
the exact new-case env_case.xml lock after preview. Candidate assumptions remain
proxies. AD395/Normal400 require later run/archive/restart validation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("b02_surface", HERE / "03_build_four_surface_candidates.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = BASE / "CTSM"
OUTPUTS = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OUT = S.OUTPUT
OVERLAY = OUT / "_private_ctsm_FATES_AD5_namelist_overlay_v1"
SHARED_BLOB = "698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
SNAPSHOT = REPO / "data/batch02_10_stage02_source_snapshot_20261025.json"
BGC_OPTS = "--bgc fates --no-megan --no-drydep --no-fire_emis"
OLD = "if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
NEW = "if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
RESEED = 'if ( $nl_flags->{$var} ne "off" ) {'
RESEED_NEW = 'if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'
HISTORY = ("TOTSOMC", "TOTSOMN", "TLAI", "FATES_GPP", "FATES_NPP", "TWS", "H2OSNO")
VERSION = "batch02-four-AD5-prepare-v2-20261025-stream-layout-fix"


def fail(message):
    raise RuntimeError(message)


def call(args, cwd=None, timeout=120):
    p = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode:
        fail("Command failed: " + str(list(map(str, args))) + "\n" + (p.stdout + p.stderr)[-3500:])
    return p.stdout.strip()


def query(case, key):
    return call([case / "xmlquery", key, "--value"], cwd=case)


def nml_get(text, key):
    matches = re.findall(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[ \t]*([^\r\n]*)", text)
    if len(matches) > 1:
        fail("Duplicate namelist key: " + key)
    if not matches:
        return None
    # Values used here are single-line scalars/list; preserve ! in quoted paths.
    quote, chars = None, []
    for char in matches[0]:
        if char in "'\"":
            quote = None if quote == char else (char if quote is None else quote)
        if char == "!" and quote is None:
            break
        chars.append(char)
    return "".join(chars).strip().rstrip(",").strip().strip("'\"").strip()


def nml_set(text, key, value):
    nml_get(text, key)  # reject duplicates, including in inherited user_nl_clm
    pattern = r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*$"
    line = key + " = " + value
    return re.sub(pattern, lambda _: line, text) if re.search(pattern, text) else text.rstrip() + "\n" + line + "\n"


def write_json(path, data, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")


def name(site):
    return site + "_B02_FIXNC_AD400"


def paths(site):
    return (BASE / "cases" / name(site), OUTPUTS / name(site) / "run",
            OUTPUTS / "archive" / name(site), OUT / site / "AD5_case_state.json")


def desired(row, data):
    return {"fsurdat": "'" + str(S.destination(row, OUT)) + "'",
            "fates_paramfile": "'" + data["active_parameter_path"] + "'",
            "finidat": "''", "use_fates": ".true.", "use_fates_sp": ".false.",
            "use_fates_fixed_biogeog": ".true.", "use_fates_nocomp": ".true.",
            "spinup_state": "2", "hist_fincl1": ",".join("'" + v + "'" for v in HISTORY)}


def settings(source, site):
    _, run, archive, _ = paths(site)
    return {"RUN_TYPE": "startup", "RUN_STARTDATE": source["start_date"],
            "CONTINUE_RUN": "FALSE", "CLM_FORCE_COLDSTART": "on",
            "CLM_ACCELERATED_SPINUP": "on", "CLM_BLDNML_OPTS": BGC_OPTS,
            "STOP_OPTION": "nyears", "STOP_N": "5", "REST_OPTION": "nyears", "REST_N": "5",
            "RESUBMIT": "0", "DOUT_S": "TRUE", "RUNDIR": str(run), "DOUT_S_ROOT": str(archive),
            "MPI_RUN_COMMAND": "srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"}


def fingerprint(case):
    files = list(case.glob("env_*.xml")) + list(case.glob("user_nl*"))
    files += [case / "CaseDocs/lnd_in", case / "CaseDocs/datm.streams.xml"]
    return {str(p): S.sha256(p) for p in files if p.is_file()}


def xml_signature(element):
    return (element.tag, tuple(sorted(element.attrib.items())), (element.text or "").strip(),
            tuple(xml_signature(c) for c in element))


def local_tag(element):
    return element.tag.rsplit("}", 1)[-1]


def direct_child(element, tag):
    matches = [c for c in element if local_tag(c) == tag]
    if len(matches) != 1:
        fail("Expected one " + tag + " in selected tower stream; found " + str(len(matches)))
    return matches[0]


def stream_check(path, source):
    root = ET.parse(path).getroot()
    # Include root and namespaced nodes, and distinguish the tower stream from
    # ancillary aerosol/etc streams. The Stage02 source excerpt names this stream.
    streams = [e for e in root.iter() if local_tag(e) == "stream_info"]
    selected = [e for e in streams if e.get("name") == "CLM_USRDAT.UNSET"]
    if len(selected) != 1:
        fail("Expected exactly one selected CLM_USRDAT.UNSET tower stream: " + str(path)
             + "; root=" + root.tag + "; stream_names=" + repr([e.get("name") for e in streams])
             + "; matches=" + str(len(selected)))
    st = selected[0]
    first, last = source["stream_year_first"], source["stream_year_last"]
    if len(first) != 1 or len(last) != 1:
        fail("Ambiguous source stream years")
    for key, expected in (("year_first", first[0]), ("year_last", last[0]), ("year_align", first[0])):
        if (direct_child(st, key).text or "").strip() != str(expected):
            fail("Stream year mismatch: " + key + " " + str(path))
    datafiles = direct_child(st, "datafiles")
    if any(local_tag(v) != "file" for v in datafiles):
        fail("Unexpected selected datafiles structure: " + str(path))
    files = [Path((v.text or "").strip()) for v in datafiles]
    if len(files) != last[0] - first[0] + 1:
        fail("Unexpected annual file count: " + str(path))
    allowed = [Path(p).resolve() for p in source["recorded_forcing_folders"]]
    # S30 source files for these two sites carry a documented PROVISIONAL label.
    # Match each ordered year, retain the suffix and compare the FULL XML below;
    # never rename files, infer a new forcing release, or silently reorder years.
    suffix = r"(?:_PROVISIONAL)?" if source["site"] in ("FI-Hyy", "IT-MBo") else ""
    for p, year in zip(files, range(first[0], last[0] + 1)):
        if not re.fullmatch(re.escape(source["site"]) + r"_DATM_" + str(year) + suffix + r"\.nc", p.name):
            fail("Annual filename/order differs from selected site/year: " + str(p))
    for p in files:
        if not p.is_absolute() or p.parent.resolve() not in allowed or not p.is_file() or p.stat().st_size == 0:
            fail("Selected forcing file missing/changed folder: " + str(p))
    print(source["site"], "DATM_STREAM_PASS", "root=" + root.tag,
          "total_streams=" + str(len(streams)), "selected=" + st.get("name"),
          "years=" + str(first[0]) + "-" + str(last[0]), "files=" + str(len(files)),
          "provisional_names=" + str(sum(p.name.endswith("_PROVISIONAL.nc") for p in files)), flush=True)
    # Existence/stream references only. Do not rescan annual meteorology values.
    return xml_signature(root)


def candidate_check(data, row):
    candidate = S.destination(row, OUT)
    receipt = candidate.with_suffix(".json")
    if candidate.is_symlink() or receipt.is_symlink():
        fail("Candidate/receipt must be independent files")
    rec = json.loads(receipt.read_text())
    if (rec.get("candidate") != str(candidate) or rec.get("candidate_sha256") != S.sha256(candidate)
            or rec.get("configuration_sha256") != S.sha256(S.CONFIG)
            or rec.get("parameter_sha256") != data["active_parameter_sha256"]
            or rec.get("site_inputs_and_assumptions") != row
            or rec.get("status") != "CANDIDATE_ONLY_NO_CASE_NO_SUBMISSION"):
        fail("Stage03 candidate receipt mismatch: " + row["site"])
    if S.sha256(Path(row["source_surface"])) != row["source_surface_sha256"]:
        fail("Original surface changed")
    S.verify_values(row, candidate)
    S.verify_unchanged(Path(row["source_surface"]), candidate)
    return S.sha256(candidate)


def source_check(source, row, data):
    old = BASE / "cases" / source["configuration_reference"]
    expected = {"CASE": source["configuration_reference"], "BUILD_COMPLETE": "TRUE",
                "RUN_STARTDATE": source["start_date"], "CLM_CO2_TYPE": source["co2_type"],
                "CALENDAR": "NO_LEAP", "ATM_NCPL": "48", "TOTALPES": "1", "NTHRDS_LND": "1"}
    for key, value in expected.items():
        if query(old, key).lower() != value.lower():
            fail("Source CIME value changed: " + row["site"] + " " + key)
    if not abs(float(query(old, "CCSM_CO2_PPMV")) - source["co2_ppm"]) <= 1e-8:
        fail("Source CO2 concentration changed")
    exe = Path(query(old, "EXEROOT")) / "cesm.exe"
    if not exe.is_file():
        fail("Existing built executable missing: " + str(exe))
    source_lnd = (old / "CaseDocs/lnd_in").read_text()
    param = nml_get(source_lnd, "fates_paramfile")
    if not param or Path(param).resolve() != Path(data["active_parameter_path"]).resolve():
        fail("Source FATES parameter path differs from verified Stage03 map")
    stream = stream_check(old / "CaseDocs/datm.streams.xml", source)
    # create_clone must retain the exact effective user stream overrides.
    user_files = {p.name: S.sha256(p) for p in old.glob("user_nl_datm*") if p.is_file()}
    if not user_files:
        fail("Source has no user DATM override files")
    return {"old": str(old), "exe": str(exe), "exe_sha256": S.sha256(exe),
            "source_fingerprint": fingerprint(old), "user_DATM_files": user_files,
            "stream_signature": stream}


def patched_text(raw):
    text = raw.decode("utf-8")
    lo = text.index("sub setup_cmdl_spinup {")
    hi = text.index("sub setup_cmdl_simulation_year {", lo)
    section = text[lo:hi]
    if section.count(OLD) != 1 or section.count(RESEED) != 1:
        fail("Pinned spinup guard/reseed signatures differ")
    return text[:lo] + section.replace(OLD, NEW, 1).replace(RESEED, RESEED_NEW, 1) + text[hi:]


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def overlay_check(create=False):
    shared = CTSM / "bld/CLMBuildNamelist.pm"
    raw = shared.read_bytes()
    if git_blob(raw) != SHARED_BLOB:
        fail("Shared CTSM namelist source is not the pinned Batch01 revision")
    patch = patched_text(raw)
    if OVERLAY.is_symlink():
        fail("Overlay root is a symlink")
    if not OVERLAY.exists():
        if not create:
            return
        OVERLAY.mkdir(parents=True, exist_ok=False)
        for p in CTSM.iterdir():
            if p.name not in (".git", "bld"):
                (OVERLAY / p.name).symlink_to(p.resolve())
        (OVERLAY / "bld").mkdir()
        for p in (CTSM / "bld").iterdir():
            if p.name not in ("build-namelist", "CLMBuildNamelist.pm"):
                (OVERLAY / "bld" / p.name).symlink_to(p.resolve())
        shutil.copy2(CTSM / "bld/build-namelist", OVERLAY / "bld/build-namelist")
        (OVERLAY / "bld/CLMBuildNamelist.pm").write_text(patch, encoding="utf-8")
    if (OVERLAY / "bld/CLMBuildNamelist.pm").is_symlink():
        fail("Private patched file unexpectedly symlinked")
    if (OVERLAY / "bld/CLMBuildNamelist.pm").read_text() != patch:
        fail("Existing private overlay differs; do not overwrite")
    build = OVERLAY / "bld/build-namelist"
    if build.is_symlink() or build.read_bytes() != (CTSM / "bld/build-namelist").read_bytes():
        fail("Private build-namelist is not an unchanged copy")
    for parent, shared_parent, excluded in ((OVERLAY, CTSM, {".git", "bld"}),
                                            (OVERLAY / "bld", CTSM / "bld", {"build-namelist", "CLMBuildNamelist.pm"})):
        for p in shared_parent.iterdir():
            if p.name not in excluded and (not (parent / p.name).is_symlink() or (parent / p.name).resolve() != p.resolve()):
                fail("Private overlay reference differs: " + str(parent / p.name))
    if shared.read_bytes() != raw:
        fail("Shared CTSM changed during private overlay setup")


def generated_check(case, source, row, data, info):
    site = row["site"]
    _, run, archive, _ = paths(site)
    for key, value in settings(source, site).items():
        if query(case, key).lower() != value.lower():
            fail("Prepared CIME setting differs: " + site + " " + key)
    if query(case, "CASE") != name(site) or Path(query(case, "EXEROOT")).resolve() != Path(info["exe"]).parent.resolve():
        fail("Clone identity/executable root differs")
    if S.sha256(Path(info["exe"])) != info["exe_sha256"]:
        fail("Reused executable changed")
    if query(case, "CLM_CO2_TYPE") != source["co2_type"] or not abs(float(query(case, "CCSM_CO2_PPMV")) - source["co2_ppm"]) <= 1e-8:
        fail("Clone fixed CO2 differs")
    if query(case, "CALENDAR") != "NO_LEAP" or query(case, "ATM_NCPL") != "48":
        fail("Clone calendar/coupling differs")
    if archive.exists() or any(run.glob("*.r.*.nc")):
        fail("Target already has archive/restarts")
    docs = case / "CaseDocs/lnd_in"
    if not docs.is_file() or not (run / "lnd_in").is_file() or docs.read_bytes() != (run / "lnd_in").read_bytes():
        fail("Generated case/run land namelists missing or differ")
    text = docs.read_text()
    for key, value in desired(row, data).items():
        if key == "hist_fincl1":
            # CIME may wrap a list over several lines.
            match = re.search(r"(?im)^\s*hist_fincl1\s*=([^\n]*(?:\n(?!\s*\w+\s*=|\s*/)[^\n]*)*)", text)
            if not match or tuple(re.findall(r"'([^']+)'", match[1])) != HISTORY:
                fail("Generated history list differs")
        elif nml_get(text, key) != value.strip("'\""):
            fail("Generated AD/FATES value differs: " + site + " " + key)
    if nml_get(text, "use_cn") != ".false." or nml_get(text, "reseed_dead_plants") is not None:
        fail("Unexpected CN-only configuration")
    if nml_get(text, "co2_type") != source["co2_type"] or not abs(float(nml_get(text, "co2_ppmv") or "nan") - source["co2_ppm"]) <= 1e-8:
        fail("Generated fixed CO2 differs from selected source")
    for filename, sha in info["user_DATM_files"].items():
        if not (case / filename).is_file() or S.sha256(case / filename) != sha:
            fail("Cloned user DATM input differs: " + filename)
    for path in (case / "CaseDocs/datm.streams.xml", run / "datm.streams.xml"):
        if stream_check(path, source) != info["stream_signature"]:
            fail("Generated DATM stream differs from selected source: " + str(path))
    if fingerprint(Path(info["old"])) != info["source_fingerprint"]:
        fail("Original case input changed during preparation")


def lock_bytes(case):
    current, locked = case / "env_case.xml", case / "LockedFiles/env_case.xml"
    if current.read_bytes() != locked.read_bytes():
        fail("New case env_case.xml differs from its lock")
    entries = {e.get("id"): e.get("value") for e in ET.parse(locked).getroot().iter("entry")}
    if entries.get("COMP_ROOT_DIR_LND") != "$SRCROOT" or Path(query(case, "COMP_ROOT_DIR_LND")).resolve() != CTSM.resolve():
        fail("Unexpected COMP_ROOT_DIR_LND; cannot safely restore exact lock")
    return current.read_bytes()


def prepare_one(source, row, data, info, candidate_sha):
    site = row["site"]
    case, run, archive, ledger = paths(site)
    # The exclusive attempt marker prevents duplicate/concurrent creation after any failure.
    attempt = OUT / site / "AD5_prepare_attempt.json"
    for p in (case, run, archive, ledger, attempt):
        if p.exists() or p.is_symlink():
            fail("Target already exists; inspect instead of overwriting: " + str(p))
    write_json(attempt, {"site": site, "phase": "PREPARATION_ATTEMPTED", "version": VERSION,
                         "created_utc": datetime.now(timezone.utc).isoformat()}, exclusive=True)
    call([CTSM / "cime/scripts/create_clone", "--case", case, "--clone", info["old"], "--keepexe"],
         cwd=CTSM / "cime/scripts", timeout=420)
    for key, value in settings(source, site).items():
        call([case / "xmlchange", key + "=" + value], cwd=case)
    nl = case / "user_nl_clm"
    text = nl.read_text()
    for key, value in desired(row, data).items():
        text = nml_set(text, key, value)
    if nml_get(text, "reseed_dead_plants") is not None:
        fail("Inherited CN-only reseed key; inspect isolated clone")
    nl.write_text(text, encoding="utf-8")
    if not (case / ".case.run").is_file():
        call([case / "case.setup"], cwd=case, timeout=300)
    locked = lock_bytes(case)
    try:
        call([case / "xmlchange", "COMP_ROOT_DIR_LND=" + str(OVERLAY)], cwd=case)
        if Path(query(case, "COMP_ROOT_DIR_LND")).resolve() != OVERLAY.resolve():
            fail("Private overlay not effective")
        call([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        call([case / "xmlchange", "COMP_ROOT_DIR_LND=$SRCROOT"], cwd=case)
        if (case / "env_case.xml").read_bytes() != locked or (case / "LockedFiles/env_case.xml").read_bytes() != locked:
            fail("CIME env_case.xml lock was not restored exactly")
    generated_check(case, source, row, data, info)
    if candidate_check(data, row) != candidate_sha:
        fail("Candidate changed during case preparation")
    S.parameter_map(data)
    overlay_check()
    record = {"version": VERSION, "site": site, "phase": "PREPARED_NOT_SUBMITTED",
              "case": str(case), "run": str(run), "archive": str(archive),
              "start_date": source["start_date"], "AD5_end_year": int(source["start_date"][:4]) + 5,
              "AD400_end_year": int(source["start_date"][:4]) + 400,
              "surface": str(S.destination(row, OUT)), "surface_sha256": candidate_sha,
              "candidate_assumptions": row, "parameter_sha256": data["active_parameter_sha256"],
              "source_case": info["old"], "executable": info["exe"], "executable_sha256": info["exe_sha256"],
              "source_input_sha256": info["source_fingerprint"], "user_DATM_files": info["user_DATM_files"],
              "private_overlay": str(OVERLAY), "CIME_env_case_lock_restored": True,
              "generated_lnd_in_sha256": S.sha256(case / "CaseDocs/lnd_in"),
              "generated_stream_sha256": S.sha256(case / "CaseDocs/datm.streams.xml"),
              "spinup_state": 2, "RESUBMIT": 0, "years": 5, "Slurm_jobs_submitted": False,
              "met_values_reaudited": False, "created_utc": datetime.now(timezone.utc).isoformat()}
    write_json(ledger, record, exclusive=True)
    write_json(attempt, {"site": site, "phase": "DONE_NO_JOBS", "version": VERSION})
    print(site, "AD5_PREPARED", source["start_date"], "->", str(record["AD5_end_year"]) + "-01-01",
          "spinup_state=2 FIXED_BIOGEOG=TRUE NOCOMP=TRUE RESUBMIT=0 NO_SUBMISSION", flush=True)


def sources():
    rows = json.loads(SNAPSHOT.read_text())["sites"]
    return {r["site"]: r for r in rows}


def self_test(data):
    assert set(S.SELECTED) == {"FI-Hyy", "FR-Hes", "CH-Fru", "IT-MBo"}
    assert nml_get("fsurdat='a!b' ! note\n", "fsurdat") == "a!b"
    assert nml_get(nml_set("spinup_state=0\n", "spinup_state", "2"), "spinup_state") == "2"
    try:
        nml_set("spinup_state=0\nspinup_state=1\n", "spinup_state", "2")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Duplicate keys accepted")
    fixture = ("sub setup_cmdl_spinup {\n" + OLD + "\n" + RESEED +
               "\n}\nsub setup_cmdl_simulation_year {\n").encode()
    changed = patched_text(fixture)
    assert NEW in changed and RESEED_NEW in changed and changed.count("use_fates") == 1
    src = sources()
    assert [src[s]["start_date"] for s in S.SELECTED] == ["1997-01-01", "1997-01-01", "2005-01-01", "2003-01-01"]
    for row in data["sites"]:
        cfg = settings(src[row["site"]], row["site"])
        assert cfg["RESUBMIT"] == "0" and cfg["CLM_FORCE_COLDSTART"] == "on"
        assert desired(row, data)["finidat"] == "''"
    print("STAGE04 SELF-TEST PASS: four Batch02 cold starts; exact two-change overlay; duplicate-key rejection; NO WRITES")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("self-test", "plan", "prepare"))
    a = p.parse_args()
    data, src = S.configuration(), sources()
    if a.action == "self-test":
        self_test(data)
        return 0
    if a.action == "plan":
        for site in S.SELECTED:
            y = int(src[site]["start_date"][:4])
            print(site, "AD5", y, "->", y + 5, "AD400_TARGET", y + 400, paths(site)[0])
        print("NO case creation or Slurm submission in plan")
        return 0
    # Validate all four inputs before creating any case.
    S.parameter_map(data)
    overlay_check()
    infos = {}
    for row in data["sites"]:
        site = row["site"]
        sha = candidate_check(data, row)
        infos[site] = (source_check(src[site], row, data), sha)
        for target in (*paths(site), OUT / site / "AD5_prepare_attempt.json"):
            if target.exists() or target.is_symlink():
                fail("Existing target; do not rerun prepare blindly: " + str(target))
        print(site, "INPUT_PREFLIGHT_PASS", flush=True)
    overlay_check(create=True)
    failures = []
    for row in data["sites"]:
        site = row["site"]
        info, sha = infos[site]
        try:
            prepare_one(src[site], row, data, info, sha)
        except Exception as exc:
            failures.append(site)
            print(site, "AD5_PREPARE_FAILED", str(exc), flush=True)
    print("AD5_PREPARE_SUMMARY prepared=", len(S.SELECTED) - len(failures), "failed=", failures)
    print("NO SLURM JOBS SUBMITTED. AD395 and Normal400 are later phases.")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
