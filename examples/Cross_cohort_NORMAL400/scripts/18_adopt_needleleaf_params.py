#!/usr/bin/env python3
"""Adopt the needleleaf fix (variant F) as the production FATES parameter set and list the sites that need a rerun.

Decision (docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md, section 9, 2026-11-02): for the needleleaf evergreen PFT
(PFT 2, needleleaf_evergreen_extratrop_tree) only:
    fates_alloc_storage_cushion  1.2   -> 2.4
    fates_leaf_slatop            0.005 -> 0.008
Every other PFT and every other parameter is unchanged (checked entry by entry). With fixed biogeography / no
competition a PFT only exists where the surface data put it, so the change is used for ALL sites (one adopted file per
source parameter file) and only sites that contain PFT 2 need to be rerun; at the others the model output is
unchanged.

  plan   (read-only)  every site of the screening: AD case, source parameter file, surface data, PFT-2 share of the
                      vegetated area (PCT_NAT_PFT mapped with fates_hlm_pft_map) -> RERUN or UNCHANGED.
                      Writes needleleaf_adoption_plan.csv beside the adopted files.
  write               creates (or verifies) the adopted parameter copy for every source file used by a RERUN site:
                      experiments/NonCompetitionObserved22/params_adopted/fates_params_needleleaf_F_<sha10>.json
                      + .receipt.json; the source files and existing cases are never touched.
  check  (read-only)  re-verifies every adopted file against its source (only PFT 2 cushion / slatop differ).

Usage (login node):
  python -B 18_adopt_needleleaf_params.py plan
  python -B 18_adopt_needleleaf_params.py write
  python -B 18_adopt_needleleaf_params.py check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADOPTED_VARIANT = "F"
PFT = 2
CHANGES = {"fates_alloc_storage_cushion": 2.4, "fates_leaf_slatop": 0.008}
DECISION = ("needleleaf fix F adopted 2026-11-02 (10-site 100-year trials, docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md "
            "section 9): PFT 2 storage cushion 2.4, slatop 0.008")
MIN_PCT = 0.01        # PFT-2 share of the vegetated area (%) above which a site needs a rerun
T = None              # module 13 (parameter writer / checker)
R = None              # module 09


def load():
    global T, R
    spec = importlib.util.spec_from_file_location("trial13", HERE / "13_needleleaf_param_trials.py")
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    T.load09()
    R = T.R
    T.PARAM_DIR = R.B / "experiments/NonCompetitionObserved22/NeedleleafFixTrials/params"
    if T.VARIANTS[ADOPTED_VARIANT][1] != CHANGES:
        raise RuntimeError(f"variant {ADOPTED_VARIANT} in script 13 is {T.VARIANTS[ADOPTED_VARIANT][1]}, expected {CHANGES}")


def adopted_dir():
    return R.B / "experiments/NonCompetitionObserved22/params_adopted"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pft2_share(pct_nat_pft, params):
    """PFT-2 share (%) of the vegetated area. pct_nat_pft: natpft 0 (bare) .. n. FATES maps HLM PFT h (1..n) to its PFTs
    with fates_hlm_pft_map; without that map the CLM convention (NET temperate 1 + NET boreal 2) is used."""
    import numpy as np
    pct = np.asarray(pct_nat_pft, float).ravel()
    veg = pct[1:].sum()
    if veg <= 0:
        return 0.0, "no vegetation"
    prm = params["parameters"]
    ent = prm.get("fates_hlm_pft_map")
    if ent is None:
        return float((pct[1:3].sum()) / veg * 100), "CLM natpft 1+2 (no fates_hlm_pft_map)"
    npft = len(prm["fates_pftname"]["data"])
    m = np.moveaxis(np.asarray(ent["data"], float), T.pft_axis(ent, npft), -1)   # (hlm, fates_pft)
    if m.ndim != 2:
        raise ValueError(f"fates_hlm_pft_map has shape {m.shape}")
    n = min(m.shape[0], len(pct) - 1)
    share = float((pct[1:1 + n] * m[:n, PFT - 1]).sum() / veg * 100)
    return share, f"fates_hlm_pft_map ({m.shape[0]} HLM PFTs)"


def read_pct(fsurdat):
    import netCDF4
    with netCDF4.Dataset(fsurdat) as ds:
        v = ds.variables["PCT_NAT_PFT"][:]
        return [float(v[k].ravel()[0]) for k in range(v.shape[0])]


def site_rows(F7, P):
    rows = []
    for site, normal in F7.JOB_CASES:
        r = {"site": site, "normal_case": normal}
        try:
            i = R.ident(site, F7, P, 50)
            ad = i["ad_case"]
            nl = R.parse_nml((ad / "CaseDocs" / "lnd_in").read_text())
            pick = lambda key: next((v for k, v in nl.items() if k.endswith("." + key)), "").strip("'\" ")
            base, fsur = pick("fates_paramfile"), pick("fsurdat")
            params = json.loads(Path(base).read_text())
            share, how = pft2_share(read_pct(fsur), params)
            r.update(ad_case=i["ad"], base_param=base, base_sha10=sha(base)[:10], fsurdat=fsur,
                     pft2_pct_of_veg=round(share, 2), mapping=how,
                     action="RERUN" if share > MIN_PCT else "UNCHANGED")
        except Exception as exc:   # report, never guess
            r.update(action="CHECK", error=str(exc).strip().splitlines()[-1][:200])
        rows.append(r)
    return rows


def plan(F7, P):
    rows = site_rows(F7, P)
    out = adopted_dir()
    out.mkdir(parents=True, exist_ok=True)
    cols = ["site", "action", "pft2_pct_of_veg", "ad_case", "normal_case", "base_sha10", "base_param", "fsurdat",
            "mapping", "error"]
    with open(out / "needleleaf_adoption_plan.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["action"], -float(r.get("pft2_pct_of_veg") or 0), r["site"])))
    for act in ("RERUN", "UNCHANGED", "CHECK"):
        sel = [r for r in rows if r["action"] == act]
        print(f"\n{act}: {len(sel)} sites")
        for r in sorted(sel, key=lambda r: -float(r.get("pft2_pct_of_veg") or 0)):
            extra = r.get("error") or f"PFT2 {r['pft2_pct_of_veg']:6.2f} % of vegetation | param {r['base_sha10']}"
            print(f"  {r['site']:8s} {extra}")
    bases = sorted({r["base_param"] for r in rows if r["action"] == "RERUN"})
    print(f"\nsource parameter files used by RERUN sites: {len(bases)}")
    for b in bases:
        print(f"  {sha(b)[:10]}  {b}")
    print(f"\nplan written: {out / 'needleleaf_adoption_plan.csv'}")
    return rows


def adopted_name(base):
    return adopted_dir() / f"fates_params_needleleaf_{ADOPTED_VARIANT}_{sha(base)[:10]}.json"


def ensure_adopted(base, sites=()):
    """Create (or verify) the adopted copy of one source parameter file; returns (path, sha256). Used by script 20 too."""
    trial, tsha, _ = T.make_param(base, ADOPTED_VARIANT, hashed=True)    # all checks of script 13
    dest = adopted_name(base)
    if dest.exists():
        if sha(dest) != tsha:
            R.fail(f"{dest} exists with different content; not overwritten")
        print(f"  exists, verified: {dest.name}", flush=True)
    else:
        adopted_dir().mkdir(parents=True, exist_ok=True)
        tmp = Path(str(dest) + ".tmp")
        shutil.copyfile(trial, tmp)
        if sha(tmp) != tsha:
            R.fail(f"copy of {trial} differs")
        tmp.replace(dest)
        print(f"  written: {dest.name}", flush=True)
    rec = Path(str(dest) + ".receipt.json")
    old = json.loads(rec.read_text()) if rec.is_file() else {}
    srcs = sorted(set(old.get("sources", [])) | {str(base)})
    rec.write_text(json.dumps({"decision": DECISION, "sources": srcs, "source_sha256": sha(base), "adopted": str(dest),
                               "adopted_sha256": tsha, "pft": PFT, "changes": CHANGES,
                               "sites": sorted(set(old.get("sites", [])) | set(sites))}, indent=1) + "\n")
    return dest, tsha


def write(F7, P):
    rows = plan(F7, P)
    if any(r["action"] == "CHECK" for r in rows):
        print("\nWARNING: some sites could not be classified (CHECK); their source files are not written")
    bases = sorted({r["base_param"] for r in rows if r["action"] == "RERUN"})
    manifest = {}
    for b in bases:
        dest, tsha = ensure_adopted(b, sorted(r["site"] for r in rows if r["action"] == "RERUN" and r["base_param"] == b))
        manifest[b] = {"adopted": str(dest), "sha256": tsha,
                       "sites": sorted(r["site"] for r in rows if r["action"] == "RERUN" and r["base_param"] == b)}
    (adopted_dir() / "ADOPTED_NEEDLELEAF_PARAMS.json").write_text(
        json.dumps({"decision": DECISION, "pft": PFT, "changes": CHANGES, "files": manifest}, indent=1) + "\n")
    print(f"\nmanifest: {adopted_dir() / 'ADOPTED_NEEDLELEAF_PARAMS.json'}")


def check(F7, P):
    man = adopted_dir() / "ADOPTED_NEEDLELEAF_PARAMS.json"
    if not man.is_file():
        R.fail(f"{man} not found; run 'write' first")
    files = json.loads(man.read_text())["files"]
    bad = 0
    for base, e in files.items():
        try:
            _, tsha, _ = T.make_param(base, ADOPTED_VARIANT, hashed=True)      # re-derives and checks the change
            if sha(e["adopted"]) != tsha or e["sha256"] != tsha:
                R.fail("adopted file does not match the re-derived copy")
            print(f"OK   {Path(e['adopted']).name}  ({len(e['sites'])} sites)")
        except Exception as exc:
            bad += 1
            print(f"FAIL {Path(e['adopted']).name}: {exc}")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("plan", "write", "check"))
    a = ap.parse_args(argv)
    load()
    F7, P = R.load07()
    if a.action == "plan":
        plan(F7, P)
        return 0
    if a.action == "write":
        write(F7, P)
        return 0
    return check(F7, P)


if __name__ == "__main__":
    raise SystemExit(main())
