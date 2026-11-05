#!/usr/bin/env python3
"""READ ONLY. For ICOS Batch04 AD400 cases: which executable / phenology code / FATES parameters they ran with,
and whether either adopted fix (phenology patch, needleleaf F) would change anything for their vegetation."""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np
import netCDF4

CASES = Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
DEFAULT = ["DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT", "DE-RuR_ICOS_B04_FIXNC_AD400_DIRECT", "IT-Tor_ICOS_B04_FIXNC_AD400_DIRECT",
           "ES-Agu_ICOS_B04_FIXNC_AD400_DIRECT", "CH-Aws_ICOS_B04_FIXNC_AD400_DIRECT_HINONE",
           "GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT_PHEN"]


def nml(text, key):
    m = re.search(rf"^\s*{key}\s*=\s*(.+?)\s*$", text, re.M | re.I)
    return m.group(1).strip().strip("'\"") if m else ""


def xq(case, var):
    return subprocess.run(["./xmlquery", "--value", var], cwd=case, capture_output=True, text=True).stdout.strip()


def find(obj, key):
    """The entry of `key` in a FATES JSON parameter file: {"data": ..., "dims": [...]} (or the bare value)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v if isinstance(v, dict) else {"data": v}
            r = find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find(v, key)
            if r is not None:
                return r
    return None


def params(pf):
    """{key: {"data": ..., "dims": [...]}} for the keys below, from a JSON or NetCDF parameter file."""
    keys = ("fates_pftname", "fates_phen_leaf_habit", "fates_phen_season_decid", "fates_hlm_pft_map")
    out = {}
    if pf.endswith(".json"):
        d = json.loads(Path(pf).read_text())
        for k in keys:
            out[k] = find(d, k)
    else:
        with netCDF4.Dataset(pf) as ds:
            for k in keys:
                if k in ds.variables:
                    v = ds.variables[k]
                    data = ["".join(c.decode() if isinstance(c, bytes) else str(c) for c in row).strip()
                            for row in np.ma.filled(v[:], b" ")] if k == "fates_pftname" else np.asarray(v[:]).tolist()
                    out[k] = {"data": data, "dims": list(v.dimensions)}
    return out


def pft_axis(ent, npft):
    """Same rule as script 13 / 22: the 'fates_pft' dimension, else the axis whose length is the PFT count."""
    dims = ent.get("dims") or []
    if "fates_pft" in dims:
        return dims.index("fates_pft")
    shape = np.shape(ent["data"])
    if npft in shape:
        return list(shape).index(npft)
    raise ValueError("no PFT dimension in fates_hlm_pft_map")


for name in (sys.argv[1:] or DEFAULT):
    case = CASES / name
    print("=" * 100 + f"\n{name}")
    if not case.is_dir():
        print("  case not found"); continue
    lnd = (case / "CaseDocs" / "lnd_in").read_text()
    exe = xq(case, "EXEROOT")
    sm = case / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90"
    patched = sm.is_file() and "nchill_threshold" in sm.read_text(errors="replace")
    print(f"  EXEROOT       {exe}")
    print(f"  SourceMods EDPhysiologyMod.F90: {'PATCHED (nchill_threshold)' if patched else ('present, not patched' if sm.is_file() else 'none -> shared/unpatched FATES code')}")
    pf, fs = nml(lnd, "fates_paramfile"), nml(lnd, "fsurdat")
    print(f"  fates_paramfile {pf}\n  fsurdat         {fs}")
    print(f"  use_fates_nocomp={nml(lnd, 'use_fates_nocomp')} fixed_biogeog={nml(lnd, 'use_fates_fixed_biogeog')} "
          f"spinup_state={nml(lnd, 'spinup_state')} calc_human_stress_indices={nml(lnd, 'calc_human_stress_indices') or 'default'}")
    with netCDF4.Dataset(fs) as ds:
        pct = np.asarray(ds.variables["PCT_NAT_PFT"][:]).reshape(ds.variables["PCT_NAT_PFT"].shape[0], -1)[:, 0]
    hlm = {i: round(float(p), 2) for i, p in enumerate(pct) if p > 0}
    print(f"  surface PCT_NAT_PFT (HLM index: %)  {hlm}")
    try:
        P = params(pf)
    except Exception as e:
        print(f"  cannot read parameter file: {e}"); continue
    names = [str(x).strip() for x in (P.get("fates_pftname") or {}).get("data", [])]
    hab = P.get("fates_phen_leaf_habit") or P.get("fates_phen_season_decid")
    flag = 2 if P.get("fates_phen_leaf_habit") else 1
    habit = np.asarray(hab["data"], float).ravel() if hab else None
    ent = P.get("fates_hlm_pft_map")
    if not ent or not names:
        print("  parameter file has no fates_hlm_pft_map / fates_pftname"); continue
    # rows = HLM natural PFTs 1..n (bare ground excluded), columns = FATES PFTs; same as script 22 decid_share
    m = np.moveaxis(np.asarray(ent["data"], float), pft_axis(ent, len(names)), -1)
    print(f"  fates_hlm_pft_map dims {ent.get('dims')} -> rows HLM 1..{m.shape[0]}, columns FATES 1..{m.shape[1]}")
    for i, p in hlm.items():
        if i == 0:
            print(f"    HLM  0 {p:5.1f} %  bare ground")
            continue
        if i - 1 >= m.shape[0]:
            print(f"    HLM {i:2d} {p:5.1f} %  outside the map"); continue
        for j in np.nonzero(m[i - 1] > 0)[0]:
            h = habit[j] if habit is not None else float("nan")
            flags = ("  <- cold-deciduous (phenology patch applies)" if h == flag else "") + \
                    ("  <- PFT 2 (needleleaf F applies)" if j + 1 == 2 else "")
            print(f"    HLM {i:2d} {p:5.1f} %  -> FATES {j + 1:2d} {names[j]:40s} weight {m[i - 1, j]:.2f} "
                  f"leaf_habit={h:g}{flags}")
