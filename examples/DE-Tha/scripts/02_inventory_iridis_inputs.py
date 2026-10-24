#!/usr/bin/env python3
"""DE-Tha (Tharandt) read-only IRIDIS6 input and case inventory.

Lists actual site files, legacy run cases and active FATES parameter provenance.
Nothing is written or modified: no Git actions, no CIME xmlchange, no Slurm
cancellation/submission, no netCDF edits or directory creation.

Run after 01_audit_evidence.py. The 87/10/1/2 tree shares are *not* yet
approved natural PFT-area fractions.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from pathlib import Path

SITE = "DE-Tha"
SUBDIRS = ("subset_data", "forcing", "surface", "surfaces", "input", "data")
SUFFIXES = {".nc", ".nc4", ".cdf", ".csv", ".zip", ".json", ".txt", ".nml"}
SKIP = {".git", "__pycache__", ".conda", "build", "bld", "node_modules"}
MAX_DEPTH = 4
MAX_VISITS_PER_ROOT = 2000
MAX_OUTPUTS_PER_ROOT = 85


def headline(label: str) -> None:
    print("\n" + "=" * 78)
    print(label)
    print("=" * 78)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_tree(folder: Path) -> None:
    if not folder.is_dir():
        print("MISSING:", folder)
        return
    print("SOURCE:", folder)
    pending = [(folder, 0)]
    visited = printed = 0
    while pending:
        current, depth = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda x: x.name.casefold())
        except OSError as exc:
            print("  UNREADABLE:", current, exc)
            continue
        for path in children:
            visited += 1
            if visited > MAX_VISITS_PER_ROOT:
                print(f"  STOP: reached {MAX_VISITS_PER_ROOT} entries; no deep scan")
                return
            if path.is_symlink():
                # Never follow an arbitrary symlink into unrelated datasets.
                continue
            if path.is_dir() and path.name not in SKIP and depth < MAX_DEPTH:
                pending.append((path, depth + 1))
            elif path.is_file() and path.suffix.lower() in SUFFIXES:
                if printed >= MAX_OUTPUTS_PER_ROOT:
                    print("  ... further matches omitted; increase narrowness of root")
                    return
                try:
                    size = path.stat().st_size
                except OSError:
                    size = -1
                print(f"  {path} [{size} bytes]")
                printed += 1
    if not printed:
        print("  No recognized forcing or surface files in bounded search")


def case_inventory(cases: Path) -> None:
    headline("Existing DE-Tha cases — READ ONLY / DO NOT MODIFY")
    if not cases.is_dir():
        print("MISSING:", cases)
        return
    found = [p for p in sorted(cases.iterdir())
             if p.is_dir() and p.name.startswith("DE-Tha")]
    if not found:
        print("No existing DE-Tha case directories found here")
    for p in found[:50]:
        print("CASE:", p)
        namelist = p / "CaseDocs" / "lnd_in"
        if namelist.is_file():
            value = namelist.read_text(errors="replace")
            for key in ("fsurdat", "use_fates", "use_fates_nocomp",
                        "use_fates_fixed_biogeog", "spinup_state"):
                m = re.search(r"(?im)^\s*" + re.escape(key) +
                              r"\s*=\s*([^\r\n]*)$", value)
                if m:
                    print(f"  {key}: {m.group(1).strip()[:240]}")
        stream = p / "user_nl_datm_streams"
        if stream.is_file():
            print("  DATM streams file:", stream)
        state = p / "CaseStatus"
        if state.is_file():
            text = state.read_text(errors="replace")
            interesting = [line.strip() for line in text.splitlines()
                           if re.search(r"case.run (?:success|error|starting)|st_archive (?:success|error)",line)]
            for line in interesting[-3:]:
                print("  HISTORY:",line)
    if len(found) > 50:
        print(f"  {len(found)-50} additional case directories not displayed")


def parameter_inventory(ctsm: Path) -> None:
    headline("Shared CTSM revision and FATES parameter hash — READ ONLY")
    if not ctsm.is_dir():
        print("MISSING:",ctsm)
        return
    try:
        p = subprocess.run(["git","-C",str(ctsm),"rev-parse","HEAD"],
                           capture_output=True,text=True,timeout=15,check=False)
        print("CTSM HEAD:",p.stdout.strip() if p.returncode==0 else "UNAVAILABLE")
    except (OSError,subprocess.TimeoutExpired) as exc:
        print("CTSM Git unavailable:",exc)
    param = ctsm/"src/fates/parameter_files/fates_params_default.json"
    if param.is_file():
        print("FATES params:",param)
        print("FATES SHA256:",sha256(param))
    else:
        print("MISSING default FATES parameter JSON:",param)
    print("NOTE: active FATES parameter path from the actual DE-Tha namelist")
    print("must still be matched against this and fates_hlm_pft_map verified.")


def queue_inventory() -> None:
    headline("Active DE-Tha jobs — READ ONLY")
    try:
        p=subprocess.run(["squeue","-u",os.environ.get("USER","ly3n24"),
                          "-h","-o","%i|%j|%T|%R"],
                         capture_output=True,text=True,timeout=15,check=False)
        if p.returncode:
            print("Could not query queue:",p.stderr[-400:])
        else:
            hits=[line for line in p.stdout.splitlines() if SITE in line]
            for hit in hits[:30]:
                print(hit)
            if not hits:
                print("No active DE-Tha jobs found")
    except (OSError,subprocess.TimeoutExpired) as exc:
        print("Could not query Slurm:",exc)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-root",type=Path,
                        default=Path("/iridisfs/scratch/ly3n24/CLM_FATES"))
    args=parser.parse_args()
    root=args.scratch_root
    if not root.is_dir():
        raise SystemExit("Target scratch CLM_FATES directory does not exist: "+str(root))
    headline("DE-Tha legacy inputs — bounded READ ONLY inventory")
    site=root/"sites/MY_EC_SITE"/SITE
    scan_tree(site)
    # Some workflows save CLM surfaces and forcing in a separate
    # dedicated experiment subtree; list names only, no recursive scan.
    experiments=root/"experiments"
    if experiments.is_dir():
        headline("Named experiment directories containing DE-Tha")
        matches=[p for p in experiments.iterdir() if SITE in p.name]
        for p in sorted(matches)[:30]:
            print(p)
    case_inventory(root/"cases")
    parameter_inventory(root/"CTSM")
    queue_inventory()
    headline("SCIENTIFIC HOLD")
    print("Evidence sums to 100%, but unresolved deciduous 2% and canopy")
    print("tree composition vs natural PFT AREA must be resolved before")
    print("writing a candidate surface or submitting any new case.")
    print("READ ONLY COMPLETE: no files changed and no Slurm jobs submitted")


if __name__=="__main__":
    main()
