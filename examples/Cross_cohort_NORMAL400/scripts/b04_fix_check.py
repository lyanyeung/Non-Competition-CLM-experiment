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
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v.get("data", v.get("value", v)) if isinstance(v, dict) else v
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
    keys = ("fates_pftname", "fates_phen_leaf_habit", "fates_phen_season_decid", "fates_alloc_storage_cushion",
            "fates_leaf_slatop", "fates_hlm_pft_map")
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
                    out[k] = ["".join(c.decode() if isinstance(c, bytes) else str(c) for c in row).strip()
                              for row in np.ma.filled(v[:], b" ")] if k == "fates_pftname" else np.asarray(v[:]).tolist()
    return out


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
    names, habit = P.get("fates_pftname") or [], P.get("fates_phen_leaf_habit") or P.get("fates_phen_season_decid")
    hmap = P.get("fates_hlm_pft_map")
    used = set()
    if hmap is not None:
        m = np.asarray(hmap, dtype=float)          # [hlm_pft, fates_pft] or transposed
        if m.shape[0] != len(pct):
            m = m.T
        for i in hlm:
            if i > 0 and i < m.shape[0]:
                used |= {j + 1 for j in np.nonzero(m[i] > 0)[0]}
    print(f"  FATES PFTs used (1-based, via fates_hlm_pft_map): {sorted(used) or 'map not readable'}")
    for j in sorted(used) or range(1, len(names) + 1):
        h = habit[j - 1] if habit is not None and j - 1 < len(habit) else "?"
        nm = names[j - 1] if j - 1 < len(names) else "?"
        print(f"    FATES {j:2d} {nm:45s} leaf_habit={h}{'  <- cold-deciduous (patch applies)' if h == 2 else ''}"
              f"{'  <- PFT 2 (needleleaf F applies)' if j == 2 else ''}")
