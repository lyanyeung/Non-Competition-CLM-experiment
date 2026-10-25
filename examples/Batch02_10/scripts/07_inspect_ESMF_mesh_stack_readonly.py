#!/usr/bin/env python3
"""Inspect the shared four-site ESMF mesh SIGSEGV; no case/job changes.

Reuse Stage06 evidence, trace declared meshes in current/source/successful
reference inputs, read only mesh headers/small coordinates, inspect stack-related
batch/environment lines and the local ESMF source. Write one new HOME report.
"""
import argparse
import hashlib
import json
import os
import re
import resource
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
OUTPUTS = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
EVIDENCE = Path.home() / "Batch02_10_AD5_failure_diagnosis_um3gr1l2/failure_diagnosis.json"
REF = {"FI-Hyy": "FI-Hyy_FATES_SPINUP1000_S30SHARED", "FR-Hes": "FR-Hes_FATES_SPINUP500",
       "CH-Fru": "CH-Fru_FATES_SPINUP500_11P", "IT-MBo": "IT-MBo_FATES_SPINUP1000_S30SHARED"}
EXTRA_REFERENCES = ("FI-Sod_B01_FIXNC_AD400", "FR-Fon_B01_FIXNC_AD400")
ESMF = BASE / "ESMF_8_8_1_OMPI/src/Infrastructure/Mesh/src/ESMCI_ESMFMesh_Util.C"
TEXT_FILES = ("datm.streams.xml", "datm_in", "nuopc.runconfig", "drv_in", "lnd_in", "atm_in")
CASE_FILES = ("user_nl_datm", "user_nl_datm_streams", ".case.run", ".env_mach_specific.sh",
              ".env_mach_specific.csh", "env_mach_specific.xml", "env_mach_pes.xml", "env_batch.xml")


def read_small(p):
    if not p.is_file():
        return ""
    if p.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Unexpectedly large input text: " + str(p))
    return p.read_text(errors="replace")


def mesh_paths(text):
    # Require a mesh declaration in the local context. Never scan forcing years.
    paths = set()
    pattern = r"/[^\s\"'<>;,=]+\.nc"
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        root = None
    if root is not None:
        for e in root.iter():
            if "mesh" in e.tag.rsplit("}", 1)[-1].lower():
                paths.update(re.findall(pattern, " ".join(e.itertext())))
        return paths
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search("mesh", line, re.I) and not line.lstrip().startswith("</"):
            context = line if re.search(pattern, line) else "\n".join(lines[i:i + 3])
            paths.update(re.findall(pattern, context))
    return paths


def selected_lines(text):
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if re.search(r"mesh|ulimit|stack|RLIMIT|OMP_|KMP_|PROPAGATE", line, re.I)]
    take = set()
    for i in hits[:24]:
        take.update(range(max(0, i - 1), min(len(lines), i + 2)))
    return [str(i + 1) + ": " + lines[i][:700] for i in sorted(take)[:64]]


def mesh_header(value):
    path = Path(value)
    out = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return out
    out.update(resolved=str(path.resolve()), bytes=path.stat().st_size)
    try:
        from netCDF4 import Dataset
        with Dataset(path, "r") as ds:
            out["dimensions"] = {k: len(v) for k, v in ds.dimensions.items()}
            out["variables"] = {}
            for key in ("centerCoords", "nodeCoords", "elementConn", "numElementConn", "elementMask", "elementArea"):
                if key not in ds.variables:
                    continue
                v = ds.variables[key]
                entry = {"dimensions": list(v.dimensions), "shape": list(v.shape), "dtype": str(v.dtype)}
                if key in ("centerCoords", "nodeCoords") and v.size <= 16:
                    entry["small_values"] = str(v[:].tolist())
                out["variables"][key] = entry
            dims = out["dimensions"]
            if "elementCount" in dims and "coordDim" in dims:
                out["cc_offsets_bytes_if_all_elements_local_and_PIO_Offset_8bytes"] = dims["elementCount"] * dims["coordDim"] * 8
                out["estimate_scope"] = "Array-size estimate only; does not measure failed-job stack limit or actual num_elems argument"
    except Exception as exc:
        out["header_error"] = type(exc).__name__ + ": " + str(exc)
    return out


def inspect(evidence):
    report = {"version": "batch02-ESMF-mesh-stack-inspect-v1-20261025", "created_utc": datetime.now(timezone.utc).isoformat(),
              "model_or_job_changes": False, "login_stack_limits_bytes": list(resource.getrlimit(resource.RLIMIT_STACK)),
              "limit_scope": "Current diagnostic/login Python process ONLY, not the failed compute tasks",
              "current_stack_env": {k: os.environ.get(k) for k in ("OMP_STACKSIZE", "KMP_STACKSIZE", "GOMP_STACKSIZE")},
              "cases": [], "meshes": [], "stage06": {"path": str(evidence)}}
    mesh_refs = set()
    try:
        data = json.loads(evidence.read_text())
        for site in data.get("sites", []):
            if site.get("site") not in REF:
                continue
            logs = [f for f in site.get("files", []) if Path(f["path"]).name.startswith("cesm.log")]
            report["stage06"][site["site"]] = []
            for log in logs:
                text = "\n".join(log.get("tail", []))
                mesh_refs.update(mesh_paths(text))
                report["stage06"][site["site"]].append({"path": log["path"], "tail": text.splitlines()[-100:]})
    except Exception as exc:
        report["stage06"]["read_error"] = str(exc)
    cases = [(s + "_B02_FIXNC_AD400", "FAILED_BATCH02") for s in REF]
    cases += [(name, "ORIGINAL_SITE_CONFIGURATION") for name in REF.values()]
    cases += [(name, "BATCH01_PREVIOUSLY_SUCCESSFUL_REFERENCE") for name in EXTRA_REFERENCES]
    for name, role in cases:
        case = BASE / "cases" / name
        run = OUTPUTS / name / "run"
        record = {"name": name, "role": role, "exists": case.is_dir(), "documents": []}
        files = [case / f for f in CASE_FILES]
        for folder in (case / "CaseDocs", run):
            files += [folder / f for f in TEXT_FILES]
        for p in files:
            try:
                text = read_small(p)
            except Exception as exc:
                record["documents"].append({"path": str(p), "read_error": str(exc)})
                continue
            if not text:
                continue
            paths = mesh_paths(text)
            mesh_refs.update(paths)
            lines = selected_lines(text)
            if lines or paths:
                record["documents"].append({"path": str(p), "mesh_paths": sorted(paths), "relevant_lines": lines})
        report["cases"].append(record)
    if ESMF.is_file():
        raw = ESMF.read_bytes()
        lines = raw.decode(errors="replace").splitlines()
        report["local_ESMF_source"] = {"path": str(ESMF), "sha256": hashlib.sha256(raw).hexdigest(),
                                       "lines_1005_1045": [str(i + 1) + ": " + lines[i] for i in range(1004, min(1045, len(lines)))]}
    else:
        report["local_ESMF_source"] = {"path": str(ESMF), "missing": True}
    for p in sorted(mesh_refs):
        report["meshes"].append(mesh_header(p))
    folder = Path(tempfile.mkdtemp(prefix="Batch02_10_ESMF_mesh_stack_", dir=Path.home()))
    path = folder / "mesh_stack_inspection.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("=== CURRENT LOGIN STACK; FAILED-JOB LIMIT NOT YET KNOWN ===")
    print(json.dumps({k: report[k] for k in ("login_stack_limits_bytes", "current_stack_env", "limit_scope")}, indent=2))
    print("=== LOCAL ESMF SOURCE AT CRASH ===")
    print(json.dumps(report["local_ESMF_source"], indent=2))
    for case in report["cases"]:
        print("\n=== CASE", case["name"], case["role"], "EXISTS", case["exists"], "===")
        for doc in case["documents"]:
            print("DOC", doc["path"])
            print("\n".join(doc.get("relevant_lines", [])))
            if doc.get("read_error"):
                print("READ_ERROR", doc["read_error"])
    print("\n=== DECLARED MESH HEADERS; NO LARGE ARRAY READS ===")
    print(json.dumps(report["meshes"], indent=2))
    if not mesh_refs:
        print("MESH_REFERENCE_UNRESOLVED: do not infer mesh correctness or a stack fix")
    print("REPORT_JSON=" + str(path))
    print("READ ONLY: no case/forcing/mesh edits, job cancellation, model submission or resource-limit changes")


def self_test():
    text = "meshfile = '/inputdata/a.nc'\ndatafiles='/forcing/site_2001.nc'\n"
    assert mesh_paths(text) == {"/inputdata/a.nc"}
    assert mesh_paths("<meshfile>\n/mesh/a.nc\n</meshfile>") == {"/mesh/a.nc"}
    assert not mesh_paths("<datafiles>/forcing/site_2001.nc</datafiles>")
    assert any("ulimit" in x for x in selected_lines("normal\nulimit -s unlimited\nend"))
    assert len(REF) == 4
    print("STAGE07 SELF-TEST PASS: mesh declaration extraction, stack-line context, exact four sites; no model writes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("self-test", "inspect"))
    parser.add_argument("--stage06-report", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    self_test() if args.action == "self-test" else inspect(args.stage06_report)
