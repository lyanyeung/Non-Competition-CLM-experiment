#!/usr/bin/env python3
"""READ ONLY. Did the needleleaf (FATES PFT 2) vegetation die in a default-parameter run? Quick check before a rerun.

Per case:
  1) last archived restart (<case>.clm2.r.<date>.nc): live FATES cohorts per PFT - number, plants per m2
     (fates_nplant summed over cohorts; patch-area weighting is not applied, so read it as "alive or not")
  2) history (archive lnd/hist): mean FATES_GPP (g C m-2 d-1) and TLAI over the first 5 and last 5 archived years,
     so a collapse shows as GPP / LAI falling to ~0.
  python -B pft2_health_check.py                     # the five AmeriFlux Batch01 sites (AD and Normal cases)
  python -B pft2_health_check.py --cases CASE ...
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import numpy as np

CASES = Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
DEFAULT = ["CA-TP1_AMF_B01SIX_FIXNC_AD400_DIRECT", "CA-TP1_AMF_B01SIX_FIXNC_NORMAL400_DIRECT",
           "CA-TP3_AMF_B01SIX_FIXNC_AD400_DIRECT", "CA-TP3_AMF_B01SIX_FIXNC_NORMAL400_DIRECT",
           "US-Bar_AMF_B01SIX_FIXNC_AD400_DIRECT", "US-Bar_AMF_B01SIX_FIXNC_NORMAL400_DIRECT",
           "CA-Cbo_AMF_B01SIX_FIXNC_AD400_DIRECT", "CA-Man_AMF_B01SIX_FIXNC_AD400_DIRECT"]
PFTNAME = {1: "BET_trop", 2: "NEEDLELEAF_evg (PFT2)", 3: "NDT_colddec", 4: "BET_extratrop", 5: "BDT_trop_hydro",
           6: "BDT_colddec", 7: "BES_extratrop", 8: "BDS_hydro", 9: "BDS_colddec", 10: "BES_arctic",
           11: "BDS_arctic_colddec", 12: "arctic_C3", 13: "C3_grass", 14: "C4_grass"}
HIST = re.compile(r"\.clm2\.h0[a-z]?\.(\d{4})-(\d{2})(?:-(\d{2})-\d{5})?\.nc$")
KG_S_TO_G_D = 1000.0 * 86400.0


def xq(case, var):
    r = subprocess.run(["./xmlquery", "--value", var], cwd=case, capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def cohorts(restart):
    from netCDF4 import Dataset
    with Dataset(str(restart)) as ds:
        v = ds.variables
        pk = next((k for k in ("fates_pft", "fates_PFT") if k in v), None)
        nk = next((k for k in ("fates_nplant", "fates_n") if k in v), None)
        if not pk or not nk:
            return None, sorted(k for k in v if k.startswith("fates_"))[:15]
        pft = np.asarray(v[pk][:]).ravel().astype(float)
        npl = np.asarray(v[nk][:], float).ravel()
    ok = np.isfinite(pft) & np.isfinite(npl) & (pft >= 1) & (pft <= 99) & (npl > 0) & (npl < 1e30)
    out = {}
    for p in np.unique(pft[ok]).astype(int):
        m = ok & (pft == p)
        out[p] = (int(m.sum()), float(npl[m].sum()))
    return out, None


def hist_years(hist, case):
    yrs = {}
    for p in hist.glob(f"{case}.clm2.h0*.nc"):
        m = HIST.search(p.name)
        if m:
            yrs.setdefault(int(m.group(1)), []).append(p)
    return yrs


def flux_mean(paths):
    from netCDF4 import Dataset
    g, l = [], []
    for p in paths:
        with Dataset(str(p)) as ds:
            if "FATES_GPP" in ds.variables:
                g.append(np.asarray(ds.variables["FATES_GPP"][:], float).ravel() * KG_S_TO_G_D)
            if "TLAI" in ds.variables:
                l.append(np.asarray(ds.variables["TLAI"][:], float).ravel())
    f = lambda a: (float(np.nanmean(np.concatenate(a))), float(np.nanmax(np.concatenate(a)))) if a else (np.nan, np.nan)
    return f(g), f(l)


def check(name):
    case = CASES / name
    print("=" * 100 + f"\n{name}", flush=True)
    if not case.is_dir():
        print("  case not found"); return
    arch = Path(xq(case, "DOUT_S_ROOT"))
    rest = sorted(d for d in (arch / "rest").glob("*") if d.is_dir())
    if rest:
        r = next(iter(sorted(rest[-1].glob(f"{name}.clm2.r.*.nc"))), None)
        print(f"  last restart {rest[-1].name}  ({len(rest)} restart sets)")
        if r:
            co, other = cohorts(r)
            if co is None:
                print(f"  cohort variables not found; fates_* in restart: {other}")
            elif not co:
                print("  NO LIVE COHORTS AT ALL")
            else:
                for p, (n, npl) in sorted(co.items()):
                    print(f"    FATES PFT {p:2d} {PFTNAME.get(p, '?'):24s} cohorts {n:4d}  plants {npl:10.4g} per m2-ish")
                if 2 not in co:
                    print("    -> PFT 2 has NO live cohort (needleleaf died)")
    hist = arch / "lnd" / "hist"
    yrs = hist_years(hist, name)
    if not yrs:
        print(f"  no history in {hist}"); return
    ys = sorted(yrs)
    for lab, sel in (("first 5 y", ys[:5]), ("last 5 y ", ys[-5:])):
        (gm, gx), (lm, lx) = flux_mean([p for y in sel for p in yrs[y]])
        print(f"  {lab} {sel[0]}-{sel[-1]}: GPP mean {gm:6.2f} max {gx:6.2f} g C m-2 d-1 | TLAI mean {lm:5.2f} max {lx:5.2f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", nargs="+", default=DEFAULT)
    a = ap.parse_args(argv)
    for c in a.cases:
        try:
            check(c)
        except Exception as exc:
            print(f"  ERROR {type(exc).__name__}: {exc}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
