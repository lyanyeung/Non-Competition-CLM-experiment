#!/usr/bin/env python3
"""Why does GPP collapse at needleleaf sites?  Read-only FATES diagnostics over the
full AD400 -> NORMAL400 sequence for a few sites: mortality by type, carbon balance,
storage, plant density and recruitment.

Same cases as 07 (job 4764252 list; AD case = the Normal case's RUN_REFCASE).
Only reads history files; light enough for a login node with 1-3 sites.

Outputs
  <out>/<site>/<site>_04_collapse_diagnostics_full800.png     annual means, years 1-800
  <out>/<site>/<site>_05_collapse_diagnostics_first<N>y.png   monthly, first N AD years
  <out>/<site>/<site>_collapse_annual.csv, _collapse_monthly.csv
  <out>/<site>/<site>_history_inventory.txt   every FATES_* variable found (dims, units)
  <out>/collapse_summary.csv, RUN_COMPLETE.json

Mortality is read for each type T from FATES_MORTALITY_<T>_SZPF (else _SZ, else _PF).
Rates are deaths / plant density of the same PFT (% of individuals per year).
"Focal PFT" = the needleleaf PFT with the most vegetation carbon in year 1 (else the
largest PFT).  Attribution window = the 20 years up to the focal PFT's collapse
(first two years monthly when it dies at once).  These are screening numbers.

Usage
  python -B 08_...py --output-root DIR [--sites DE-Obe FI-Sod] [--first-years 30]
  python -B 08_...py --output-root DIR --ad-only DE-Obe:<DIAG case> FI-Sod:<DIAG case> --first-years 50
  python -B 08_...py --publish-run DIR        # login node, SSH push like 07
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIG_DIR = "figures/AD400_NORMAL400_collapse_diagnostics"
DEFAULT_SITES = ["DE-Obe", "FI-Sod"]

SCALARS = ["FATES_GPP", "FATES_NPP", "FATES_AUTORESP", "FATES_MAINT_RESP", "FATES_GROWTH_RESP",
           "FATES_VEGC", "FATES_STOREC", "FATES_LEAFC", "FATES_STOREC_TF", "FATES_SEED_BANK",
           "BTRAN", "TSA", "TLAI", "FATES_NCOHORTS", "FATES_NPATCHES"]
PFT_VARS = ["FATES_NPLANT_PF", "FATES_RECRUITMENT_PF", "FATES_MORTALITY_PF", "FATES_VEGC_PF",
            "FATES_LEAFC_PF", "FATES_STOREC_PF", "FATES_GPP_PF", "FATES_NPP_PF"]
PFT_FALLBACK = {"FATES_NPLANT_PF": "FATES_NPLANT_SZPF", "FATES_VEGC_PF": "FATES_VEGC_SZPF"}
MORT_RE = re.compile(r"^FATES_MORTALITY_([A-Z]+)_(SZPF|SZ|PF)$")
MORT_SKIP = {"CANOPY", "USTORY", "CFLUX"}       # canopy/understory are splits of the total
SUFFIX_RANK = {"SZPF": 0, "SZ": 1, "PF": 2}
SUGGESTED_FINCL = ["FATES_MORTALITY_CSTARV_SZPF", "FATES_MORTALITY_HYDRAULIC_SZPF",
                   "FATES_MORTALITY_FREEZING_SZPF", "FATES_MORTALITY_BACKGROUND_SZPF",
                   "FATES_MORTALITY_IMPACT_SZPF", "FATES_MORTALITY_TERMINATION_SZPF",
                   "FATES_MORTALITY_SENESCENCE_SZPF", "FATES_NPLANT_PF", "FATES_RECRUITMENT_PF",
                   "FATES_VEGC_PF", "FATES_STOREC_PF", "FATES_STOREC_TF", "FATES_GPP_PF", "FATES_NPP_PF",
                   "FATES_MAINT_RESP", "FATES_AUTORESP", "BTRAN"]
DEFAULT_PFT_NAMES = [
    "broadleaf_evergreen_tropical_tree", "needleleaf_evergreen_extratrop_tree", "needleleaf_colddecid_extratrop_tree",
    "broadleaf_evergreen_extratrop_tree", "broadleaf_hydrodecid_tropical_tree", "broadleaf_colddecid_extratrop_tree",
    "broadleaf_evergreen_extratrop_shrub", "broadleaf_hydrodecid_extratrop_shrub", "broadleaf_colddecid_extratrop_shrub",
    "broadleaf_evergreen_arctic_shrub", "broadleaf_colddecid_arctic_shrub", "arctic_c3_grass", "cool_c3_grass", "c4_grass"]
SEC_PER_YEAR = 365.0 * 86400.0

F7 = None   # module 07 (case list, PHASE, publish helpers)
P = None    # Stage15 module (inventory, noleap_dates, env_value)


# ------------------------------------------------------------------ setup
def load_modules(explicit07=None):
    global F7, P
    cands = ([Path(explicit07)] if explicit07 else []) + [HERE / "fullseq.py", HERE / "07_plot_full_sequence_GPP_NEE_with_EC.py"]
    for c in cands:
        if c.is_file():
            spec = importlib.util.spec_from_file_location("fullseq07", c)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            F7 = mod
            P, _ = mod.load_plot_module(None)
            return c
    raise FileNotFoundError("module 07 not found; tried: " + ", ".join(map(str, cands)))


# ------------------------------------------------------------------ units / arrays
def convert(units):
    """(factor, offset, label) to plotting units."""
    raw = units or ""
    u = raw.replace(" ", "").replace("^", "").lower()
    if raw.strip() == "K":
        return 1.0, -273.15, "°C"
    if u.startswith("kg") and ("s-1" in u or "/s" in u):
        return 1000.0 * 86400.0, 0.0, "g C m-2 d-1"
    if u.startswith("kg") and ("m-2" in u or "/m2" in u):
        return 1000.0, 0.0, "g C m-2"
    # plant counts: FATES uses "m-2" / "m-2 yr-1" (older: "N/ha", "N/ha/yr")
    if u.startswith("m-2") or u.startswith("/m2") or u.startswith("n/m2") or u.startswith("nm-2"):
        f = 1e4
    elif "ha" in u and (u.startswith("n") or u.startswith("ha") or u.startswith("/ha")):
        f = 1.0
    else:
        return 1.0, 0.0, raw
    if "s-1" in u or "/s" in u:
        return f * SEC_PER_YEAR, 0.0, "ha-1 yr-1"
    if "d-1" in u or "/d" in u or "day" in u:
        return f * 365.0, 0.0, "ha-1 yr-1"
    if "yr" in u or "y-1" in u:
        return f, 0.0, "ha-1 yr-1"
    return f, 0.0, "ha-1"


def dim_kind(var):
    """('scalar'|'pf'|'szpf'|'sz'|None, array (time, k)) for a single-point history variable."""
    dims = list(var.dimensions)
    if "time" not in dims:
        return None, None
    extra = [(d, n) for d, n in zip(dims, var.shape) if d != "time" and n != 1]
    if not extra:
        kind = "scalar"
    elif len(extra) == 1 and "levscpf" in extra[0][0]:
        kind = "szpf"
    elif len(extra) == 1 and "levpft" in extra[0][0]:
        kind = "pf"
    elif len(extra) == 1 and "levscls" in extra[0][0]:
        kind = "sz"
    else:
        return None, None
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a = np.moveaxis(a, dims.index("time"), 0)
    return kind, a.reshape(a.shape[0], -1)


def pft_index_szpf(ds, n):
    """1-based PFT of each scpf index."""
    if "fates_pftmap_levscpf" in ds.variables:
        m = np.asarray(ds.variables["fates_pftmap_levscpf"][:], dtype=int).ravel()
        if m.size == n:
            return m
    nscls = len(ds.dimensions["fates_levscls"]) if "fates_levscls" in ds.dimensions else None
    if not nscls or n % nscls:
        raise ValueError(f"cannot map fates_levscpf ({n}) to PFTs")
    return np.arange(n) // nscls + 1


def build_spec(names):
    """Which variables to read, decided from the variable names of sample files."""
    spec = {n: "scalar" for n in SCALARS if n in names}
    for n in PFT_VARS:
        if n in names:
            spec[n] = n
        elif PFT_FALLBACK.get(n) in names:
            spec[PFT_FALLBACK[n]] = n            # read SZPF, store under the _PF name
    best = {}
    for n in names:
        m = MORT_RE.match(n)
        if m and m.group(1) not in MORT_SKIP:
            t, suf = m.groups()
            if t not in best or SUFFIX_RANK[suf] < SUFFIX_RANK[best[t][1]]:
                best[t] = (n, suf)
    for t, (n, _) in best.items():
        spec[n] = f"MORT_{t}"
    for n in names:
        if n.startswith("FATES_MORTALITY_") and "CFLUX" in n:
            spec[n] = n
    return spec


def read_file(path, spec):
    """Rows (one per time sample) of converted values for every spec variable present."""
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
        if bname is None:
            raise ValueError(f"{path.name}: no time bounds")
        b = np.asarray(ds.variables[bname][:], dtype=float)
        dur = b[:, 1] - b[:, 0]
        dates = P.noleap_dates(ds)
        cols, units = {}, {}
        for name, key in spec.items():
            if name not in ds.variables:
                continue
            v = ds.variables[name]
            kind, a = dim_kind(v)
            if kind is None:
                continue
            f, off, lab = convert(str(getattr(v, "units", "")))
            a = a * f + off
            if kind == "scalar":
                cols[key if key != "scalar" else name] = a[:, 0]
                units[key if key != "scalar" else name] = lab
                continue
            if kind == "szpf":
                pmap = pft_index_szpf(ds, a.shape[1])
                npft = int(pmap.max())
                red = np.zeros((a.shape[0], npft))
                for p in range(1, npft + 1):
                    red[:, p - 1] = np.nansum(a[:, pmap == p], axis=1)
                a, kind = red, "pf"
            if kind == "pf":
                for p in range(a.shape[1]):
                    cols[f"{key}__pft{p + 1}"] = a[:, p]
                units[key] = lab
            elif kind == "sz":
                cols[f"{key}__all"] = np.nansum(a, axis=1)
                units[key] = lab
        rows = []
        for i, (y, mo, _) in enumerate(dates):
            r = {"Year": y, "Month": mo, "w": dur[i]}
            r.update({k: float(c[i]) for k, c in cols.items()})
            rows.append(r)
    return rows, units


def inventory_text(path):
    from netCDF4 import Dataset
    lines = [f"# {path}"]
    with Dataset(str(path)) as ds:
        for n in sorted(ds.variables):
            if n.startswith("FATES_") or n in SCALARS or n.startswith("fates_"):
                v = ds.variables[n]
                lines.append(f"{n:45s} {str(tuple(v.dimensions)):55s} {getattr(v, 'units', '')}")
        names = set(ds.variables)
    return lines, names


def pft_names(normal, args):
    for p in (args.archive_root.parent / normal / "run" / "lnd_in", args.cases_root / normal / "CaseDocs" / "lnd_in"):
        try:
            m = re.search(r"fates_paramfile\s*=\s*['\"]([^'\"]+)['\"]", p.read_text())
            if not m:
                continue
            f = Path(m.group(1))
            if f.suffix == ".json":
                d = json.loads(f.read_text())["parameters"]["fates_pftname"]["data"]
                return [str(x).strip() for x in d], str(f)
            from netCDF4 import Dataset, chartostring
            with Dataset(str(f)) as ds:
                return [str(x).strip() for x in chartostring(ds.variables["fates_pftname"][:])], str(f)
        except Exception:
            continue
    return list(DEFAULT_PFT_NAMES), "default 14-PFT names (parameter file not read)"


# ------------------------------------------------------------------ series
def read_series(inv, spec):
    phase = F7.PHASE
    years = [(i + 1, y, "AD", inv["fad"][y]) for i, y in enumerate(inv["ad_years"])] + \
            [(phase + i + 1, y, "NORMAL", inv["fno"][y]) for i, y in enumerate(inv["normal_years"])]
    rows, units = [], {}
    for k, (spin, y, ph, paths) in enumerate(years):
        for path in paths:
            rr, u = read_file(path, spec)
            units.update(u)
            for r in rr:
                if r["Year"] != y:
                    raise ValueError(f"{path.name}: sample in year {r['Year']}, expected {y}")
                r.update(SpinupYear=spin, Phase=ph)
                rows.append(r)
        if (k + 1) % 200 == 0:
            print(f"    read {k + 1}/{len(years)} model years", flush=True)
    raw = pd.DataFrame(rows)
    # monthly means (daily samples allowed), weighted by sample duration
    mon = weighted_mean(raw, ["SpinupYear", "Phase", "Year", "Month"])
    return add_derived(mon), units


def weighted_mean(df, keys):
    """NaN-aware duration-weighted mean of every numeric column per group; 'w' = summed weight."""
    num = [c for c in df.columns if c not in set(keys) | {"Year", "Month", "w", "SpinupYear", "Phase"}]
    vals = df[num].to_numpy(float)
    w = df["w"].to_numpy(float)[:, None]
    ok = np.isfinite(vals)
    s = pd.DataFrame(np.where(ok, vals, 0.0) * w, columns=num)
    n = pd.DataFrame(ok * w, columns=num)
    g = df[keys].reset_index(drop=True)
    S = pd.concat([g, s], axis=1).groupby(keys, sort=True).sum()
    N = pd.concat([g, n], axis=1).groupby(keys, sort=True).sum()
    out = S / N.where(N > 0)
    out["w"] = df.groupby(keys, sort=True)["w"].sum()
    return out.reset_index()


def add_derived(df):
    df = df.copy()
    def pcols(prefix):
        return [c for c in df.columns if c.startswith(prefix + "__pft")]
    for pre in ("FATES_NPLANT_PF", "FATES_VEGC_PF", "FATES_RECRUITMENT_PF", "FATES_STOREC_PF"):
        if pcols(pre):
            df[pre + "__total"] = df[pcols(pre)].sum(axis=1, min_count=1)
    for t in sorted({c.split("__")[0][5:] for c in df.columns if c.startswith("MORT_")}):
        cs = [c for c in df.columns if c.startswith(f"MORT_{t}__")]
        df[f"MORT_{t}__total"] = df[cs].sum(axis=1, min_count=1)
    return df


def annual_from_monthly(mon):
    keys = ["SpinupYear", "Phase", "Year"]
    ann = weighted_mean(mon.drop(columns=["Month"]), keys)
    for c in ("BTRAN", "TSA"):
        if c in mon:
            ann[c + "_min"] = mon.groupby(keys, sort=True)[c].min().to_numpy()
    return ann


def mort_types(df):
    return sorted({c.split("__")[0][5:] for c in df.columns if c.startswith("MORT_")})


def mort_series(df, t, focal):
    """deaths (ha-1 yr-1) of type t for the focal PFT (total if only SZ available), and the column used."""
    for c in (f"MORT_{t}__pft{focal}", f"MORT_{t}__all", f"MORT_{t}__total"):
        if c in df:
            return df[c], c
    return None, None


def choose_focal(mon, names):
    pcols = [c for c in mon.columns if re.match(r"FATES_(VEGC|NPLANT)_PF__pft\d+$", c)]
    have = mon[mon[pcols].notna().any(axis=1)] if pcols else mon.iloc[:0]
    if have.empty:
        return None
    first = have[have.SpinupYear == have.SpinupYear.min()]
    size = {}
    for c in first.columns:
        m = re.match(r"FATES_(VEGC|NPLANT)_PF__pft(\d+)$", c)
        if m:
            k = int(m.group(2))
            val = float(first[c].max()) if first[c].notna().any() else 0.0
            size.setdefault(k, {})[m.group(1)] = val
    if not size:
        return None
    key = lambda k: (size[k].get("VEGC", 0.0), size[k].get("NPLANT", 0.0))
    alive = [k for k in size if key(k) > (0.0, 0.0)]
    needle = [k for k in alive if k - 1 < len(names) and "needleleaf" in names[k - 1]]
    pool = needle or alive
    return max(pool, key=key) if pool else None


def output_note(ann, focal):
    """Plain statement of which years carry vegetation-state output and whether it is all zero."""
    c = f"FATES_VEGC_PF__pft{focal}" if focal else "FATES_VEGC"
    if c not in ann:
        return "no vegetation-carbon output in any year"
    v = ann[c].to_numpy(float); ok = np.isfinite(v)
    if not ok.any():
        return "no vegetation-carbon output in any year"
    yrs = ann.SpinupYear.to_numpy()[ok]
    span = f"{c} written only for spin-up years {yrs.min()}-{yrs.max()}" if ok.sum() < len(v) else f"{c} written for all years"
    if np.nanmax(v) <= 1e-6:
        return span + "; it is zero in all of them (vegetation already gone)"
    return span


def collapse_year(ann, focal):
    """First spin-up year after which focal-PFT VEGC stays below 1 % of its maximum (tail >= 30 y)."""
    c = f"FATES_VEGC_PF__pft{focal}" if focal else None
    if c not in ann:
        c = "FATES_VEGC" if "FATES_VEGC" in ann else None
    if c is None:
        return None, None
    sub = ann[np.isfinite(ann[c].to_numpy(float))]
    v = sub[c].to_numpy(float)
    if not len(v) or np.nanmax(v) <= 1e-6:
        return None, c          # no usable output, or already zero wherever written: see Output_note
    if sub.SpinupYear.iloc[0] != ann.SpinupYear.iloc[0]:
        return None, c          # output starts late: the true maximum may be unrecorded
    ann = sub
    low = v < 0.01 * np.nanmax(v)
    if len(v) < 30 or not low[-30:].all():
        return None, c
    k = len(v) - 1
    while k > 0 and low[k - 1]:
        k -= 1
    return int(ann.SpinupYear.iloc[k]), c


def attribution(mon, ann, focal, cy):
    """Mean deaths by type in the window before collapse (or the last 100 years if no collapse)."""
    if focal is None:
        return {"Attribution_window": "none", "Dominant_mortality": "n/a: no living plants in any year with per-PFT output"}
    if cy is None:
        win = mon[mon.SpinupYear > mon.SpinupYear.max() - 100]
        label = "last 100 years"
    elif cy <= 2:
        win = mon[mon.SpinupYear <= 2]
        label = "spin-up years 1-2 (monthly)"
    else:
        win = mon[(mon.SpinupYear >= max(1, cy - 19)) & (mon.SpinupYear <= cy)]
        label = f"spin-up years {max(1, cy - 19)}-{cy}"
    out = {"Attribution_window": label}
    nplant = win.get(f"FATES_NPLANT_PF__pft{focal}") if focal else None
    w = win["w"].to_numpy(float)
    deaths = {}
    for t in mort_types(win):
        s, col = mort_series(win, t, focal)
        if s is None:
            continue
        v = s.to_numpy(float); ok = np.isfinite(v)
        if ok.any():
            deaths[t] = float(np.average(v[ok], weights=w[ok]))
            if not col.endswith(f"pft{focal}"):
                out[f"Note_{t}"] = "all PFTs (no per-PFT output)"
    tot = sum(max(d, 0.0) for d in deaths.values())
    for t, d in sorted(deaths.items(), key=lambda kv: -kv[1]):
        out[f"Deaths_{t}_ha-1_yr-1"] = d
        out[f"Share_{t}_pct"] = 100.0 * d / tot if tot > 0 else np.nan
    if deaths and tot > 0:
        top = sorted(deaths.items(), key=lambda kv: -kv[1])
        out["Dominant_mortality"] = top[0][0]
        out["Dominant_share_pct"] = 100.0 * top[0][1] / tot
        out["Top3_mortality"] = "; ".join(f"{t} {100 * d / tot:.0f}%" for t, d in top[:3])
    else:
        out["Dominant_mortality"] = "n/a (no mortality-by-type output)"
    if nplant is not None:
        n = nplant.to_numpy(float); ok = np.isfinite(n)
        out["Focal_density_mean_ha-1"] = float(np.average(n[ok], weights=w[ok])) if ok.any() else np.nan
    for c, lab in ((f"FATES_NPP_PF__pft{focal}", "Focal_NPP_mean_gC_m-2_d-1"),
                   (f"FATES_GPP_PF__pft{focal}", "Focal_GPP_mean_gC_m-2_d-1"),
                   ("FATES_STOREC_TF", "Storage_fraction_of_target_mean")):
        if c in win and win[c].notna().any():
            v = win[c].to_numpy(float); ok = np.isfinite(v)
            out[lab] = float(np.average(v[ok], weights=w[ok]))
    for c, lab in (("FATES_STOREC_TF", "Storage_fraction_of_target_min"), ("BTRAN", "BTRAN_min_month"),
                   ("TSA", "TSA_min_month_C")):
        if c in win and win[c].notna().any():
            out[lab] = float(win[c].min())
    return out


# ------------------------------------------------------------------ plots
def _logplot(ax, x, y, **kw):
    y = np.asarray(y, dtype=float)
    y = np.where(y > 0, y, np.nan)
    if np.isfinite(y).any():
        ax.plot(x, y, **kw)
        return True
    return False


def plot_site(site, pair, df, names, focal, cy, att, dest, monthly, first_years):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    phase = F7.PHASE
    if monthly:
        df = df[df.SpinupYear <= first_years]
        x = (df.SpinupYear - 1 + (df.Month - 0.5) / 12.0).to_numpy(float)
        xlim, xlab = (0, first_years), f"Spin-up year (AD; monthly, first {first_years} years)"
    elif pair.get("ad_only"):
        x = df.SpinupYear.to_numpy(float)
        n = int(df.SpinupYear.max()) if len(df) else 1
        xlim, xlab = (0.5, n + 0.5), f"AD spin-up year (diagnostic re-run, {n} years)"
    else:
        x = df.SpinupYear.to_numpy(float)
        xlim, xlab = (0.5, 2 * phase + 0.5), "Spin-up year (1–400 AD, shaded | 401–800 Normal)"
    pfts = sorted({int(m.group(1)) for c in df.columns for m in [re.search(r"__pft(\d+)$", c)] if m})
    pfts = [k for k in pfts if any(c in df and df[c].abs().max() > 0 for c in
                                   (f"FATES_VEGC_PF__pft{k}", f"FATES_NPLANT_PF__pft{k}"))] or pfts
    pname = lambda k: f"PFT{k} {names[k - 1] if k - 1 < len(names) else ''}".strip() + (" (focal)" if k == focal else "")
    cmap = plt.get_cmap("tab10")
    panels = []

    def p_flux(ax):
        ok = False
        for c, lab, col in (("FATES_GPP", "GPP", "k"), ("FATES_NPP", "NPP", "tab:green"),
                            ("FATES_AUTORESP", "autotrophic resp.", "tab:orange"),
                            ("FATES_MAINT_RESP", "maintenance resp.", "tab:red")):
            if c in df and df[c].notna().any():
                ax.plot(x, df[c], color=col, lw=1, label=lab); ok = True
        if f"FATES_NPP_PF__pft{focal}" in df:
            ax.plot(x, df[f"FATES_NPP_PF__pft{focal}"], color="tab:green", ls="--", lw=1, label="NPP focal PFT"); ok = True
        if "ORIGINAL_AD_FATES_GPP" in df and df["ORIGINAL_AD_FATES_GPP"].notna().any():
            ax.plot(x, df["ORIGINAL_AD_FATES_GPP"], color="0.55", ls=":", lw=1.6, label="GPP original AD400 run"); ok = True
        ax.axhline(0, color="0.6", lw=0.6)
        return ok, "g C m-2 d-1", "Stand carbon fluxes"
    panels.append(p_flux)

    def p_pft(prefix, title, unit, log=True):
        def f(ax):
            ok = False
            for i, k in enumerate(pfts):
                c = f"{prefix}__pft{k}"
                if c in df:
                    lw = 1.6 if k == focal else 0.9
                    ok |= (_logplot(ax, x, df[c], color=cmap(i % 10), lw=lw, label=pname(k)) if log
                           else bool(ax.plot(x, df[c], color=cmap(i % 10), lw=lw, label=pname(k))))
            if log and ok:
                ax.set_yscale("log")
            if not ok and any(f"{prefix}__pft{k}" in df and df[f"{prefix}__pft{k}"].notna().any() for k in pfts):
                ok = None
            return ok, unit, title
        return f
    panels.append(p_pft("FATES_VEGC_PF", "Vegetation carbon by PFT (log)", "g C m-2"))
    panels.append(p_pft("FATES_STOREC_PF", "Storage carbon by PFT (log)", "g C m-2"))

    def p_storetf(ax):
        if "FATES_STOREC_TF" in df and df["FATES_STOREC_TF"].notna().any():
            ax.plot(x, df["FATES_STOREC_TF"], color="tab:purple", lw=1, label="storage / target (stand)")
            ax.axhline(1, color="0.6", lw=0.6, ls=":")
            return True, "fraction", "Storage carbon relative to target"
        return False, "", ""
    panels.append(p_storetf)
    panels.append(p_pft("FATES_NPLANT_PF", "Plant density by PFT (log)", "plants ha-1"))

    def p_mort(ax):
        ok = False
        dens = df.get(f"FATES_NPLANT_PF__pft{focal}") if focal else None
        for i, t in enumerate(mort_types(df)):
            s, col = mort_series(df, t, focal)
            if s is None:
                continue
            same_pft = col.endswith(f"pft{focal}")
            d = dens if (same_pft and dens is not None) else df.get("FATES_NPLANT_PF__total")
            if d is not None:
                rate = 100.0 * s.to_numpy(float) / np.where(d.to_numpy(float) > 0, d.to_numpy(float), np.nan)
                ok |= _logplot(ax, x, rate, color=cmap(i % 10), lw=1, label=t.lower() + ("" if same_pft else " (all PFTs)"))
            else:
                ok |= _logplot(ax, x, s, color=cmap(i % 10), lw=1, label=t.lower() + " (deaths ha-1 yr-1)")
        if ok:
            ax.set_yscale("log")
        elif any(c.startswith("MORT_") and df[c].notna().any() for c in df.columns):
            ok = None
        unit = "% of plants yr-1" if (focal and dens is not None) else "% yr-1 / deaths"
        return ok, unit, "Mortality rate by type (focal PFT, log)"
    panels.append(p_mort)
    panels.append(p_pft("FATES_RECRUITMENT_PF", "Recruitment by PFT (log)", "plants ha-1 yr-1"))

    def p_stress(ax):
        ok = False
        if "BTRAN" in df and df["BTRAN"].notna().any():
            ax.plot(x, df["BTRAN"], color="tab:blue", lw=1, label="BTRAN (mean)"); ok = True
            if not monthly and "BTRAN_min" in df:
                ax.plot(x, df["BTRAN_min"], color="tab:blue", lw=0.8, ls="--", label="BTRAN (min month)")
            ax.set_ylim(0, 1.05)
        if "TSA" in df and df["TSA"].notna().any():
            a2 = ax.twinx()
            col = "TSA" if monthly or "TSA_min" not in df else "TSA_min"
            a2.plot(x, df[col], color="tab:cyan", lw=0.8, label="2 m air T " + ("" if monthly else "(min month)"))
            a2.set_ylabel("°C", color="tab:cyan"); a2.tick_params(axis="y", colors="tab:cyan")
            a2.axhline(0, color="tab:cyan", lw=0.5, ls=":")
            ok = True
        return ok, "BTRAN (0–1)", "Water stress (BTRAN) and air temperature"
    panels.append(p_stress)

    fig, axs = plt.subplots(len(panels), 1, figsize=(15, 2.6 * len(panels)), sharex=True)
    shown = 0
    for ax, fn in zip(axs, panels):
        if not monthly and not pair.get("ad_only"):
            ax.axvspan(0.5, phase + 0.5, color="0.94", zorder=0)
            ax.axvline(phase + 0.5, color="0.3", ls="--", lw=1)
        if cy is not None and cy <= (first_years if monthly else xlim[1]):
            ax.axvline(cy - (1 if monthly else 0), color="#b00000", ls=":", lw=1.2)
        ok, unit, title = fn(ax)
        if not ok:
            msg = ("written, but zero in every year that has output (no living plants)" if ok is None
                   else "not in history output")
            ax.text(0.5, 0.5, msg, transform=ax.transAxes, ha="center", va="center", color="0.5")
            ax.set_yticks([])
        else:
            shown += 1
            ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(1.06, 1.0))
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.set_ylabel(unit)
        ax.grid(alpha=0.25)
    axs[-1].set_xlim(*xlim)
    axs[-1].set_xlabel(xlab)
    top = att.get("Top3_mortality") or att.get("Dominant_mortality", "")
    span = "monthly, first %d y" % first_years if monthly else ("annual, AD re-run" if pair.get("ad_only") else "annual, 800 y")
    fig.suptitle(f"{site} | collapse diagnostics ({span})\n"
                 f"{pair['ad'] if pair.get('ad_only') else pair['ad'] + ' → ' + pair['normal']}\n"
                 f"focal PFT: {pname(focal) if focal else 'n/a'} | collapse (VEGC<1% of max): "
                 f"{'year %d' % cy if cy else 'not determinable'} (red dotted)\n"
                 f"{output_note(df if not monthly else annual_from_monthly(df), focal)}\n"
                 f"mortality in {att.get('Attribution_window', '')}: {top}", fontsize=11)
    fig.tight_layout()
    tag = (f"_05_collapse_diagnostics_first{first_years}y.png" if monthly else
           "_04_collapse_diagnostics_ADrerun.png" if pair.get("ad_only") else "_04_collapse_diagnostics_full800.png")
    p = dest / f"{site}{tag}"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p, shown


# ------------------------------------------------------------------ driver
def ad_only_inventory(case, args):
    """Inventory of a single AD case (e.g. the 09 diagnostic re-run): no Normal phase."""
    y0 = int(P.env_value(args.cases_root / case, "RUN_STARTDATE")[:4])
    fad = P.history_index(args.archive_root, case)
    return {"fad": fad, "fno": {}, "ad_years": P.contiguous(fad, y0, F7.PHASE), "normal_years": []}


def add_original_gpp(mon, case, inv, args, rec):
    """For a *_DIAG<n> re-run, add the original AD case's GPP for the same years (reproduction check)."""
    m = re.match(r"^(.*)_DIAG\d+$", case)
    if not m:
        return mon
    orig = m.group(1)
    rec["Original_AD_case"] = orig
    try:
        fad = P.history_index(args.archive_root, orig)
        years = [y for y in inv["ad_years"] if y in fad]
        if not years:
            raise FileNotFoundError("no overlapping history years")
        o, _ = read_series({"fad": fad, "fno": {}, "ad_years": years, "normal_years": []}, {"FATES_GPP": "scalar"})
    except Exception as exc:
        rec["GPP_vs_original"] = f"not compared: {type(exc).__name__}: {exc}"
        return mon
    o = o[["Year", "Month", "FATES_GPP"]].rename(columns={"FATES_GPP": "ORIGINAL_AD_FATES_GPP"})
    mon = mon.merge(o, on=["Year", "Month"], how="left")
    a, b = mon["FATES_GPP"].to_numpy(float), mon["ORIGINAL_AD_FATES_GPP"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.any():
        d = float(np.max(np.abs(a[ok] - b[ok])))
        scale = float(np.max(np.abs(b[ok]))) or 1.0
        rec["GPP_vs_original_max_abs_diff_gC_m-2_d-1"] = d
        rec["GPP_vs_original"] = (f"identical over {ok.sum()} months" if d <= 1e-9 else
                                  f"max |diff| {d:.3g} g C m-2 d-1 ({100 * d / scale:.2g}% of peak) over {ok.sum()} months")
    return mon


def process(task):
    site, normal, args = task[:3]
    ad_only = len(task) > 3 and task[3]
    if F7 is None:
        load_modules(args.module07)
    rec = {"Site": site, "Normal_case": "" if ad_only else normal, "Status": "FAILED", "Error": ""}
    dest = args.output_root / site
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if ad_only:
            ad = normal
            rec["AD_case"] = ad
            pair = {"site": site, "ad": ad, "normal": ad, "ad_case_dir": args.cases_root / ad, "ad_only": True}
            inv = ad_only_inventory(ad, args)
        else:
            ndir = args.cases_root / normal
            if not ndir.is_dir():
                raise FileNotFoundError(f"Normal case dir missing: {ndir}")
            ad = P.env_value(ndir, "RUN_REFCASE")
            rec["AD_case"] = ad
            pair = {"site": site, "ad": ad, "normal": normal, "ad_case_dir": args.cases_root / ad}
            inv = P.inventory(pair, args)
        if not inv["ad_years"]:
            raise RuntimeError("no AD history years")
        rec["AD_years"], rec["Normal_years"] = len(inv["ad_years"]), len(inv["normal_years"])
        samples = [inv["fad"][inv["ad_years"][0]][0]]
        if inv["normal_years"]:
            samples.append(inv["fno"][inv["normal_years"][0]][0])
        lines, names_all = [], set()
        for s in samples:
            l, n = inventory_text(s)
            lines += l + [""]
            names_all |= n
        spec = build_spec(names_all)
        missing = [v for v in SUGGESTED_FINCL if v not in names_all and not (v == "FATES_NPLANT_PF" and "FATES_NPLANT_SZPF" in names_all)]
        lines += ["# variables used:"] + [f"  {k} -> {v}" for k, v in spec.items()]
        lines += ["", "# suggested but missing (add to hist_fincl1 in user_nl_clm for the next run;",
                  "# _SZPF variables may also need fates_history_dimlevel = 2,2):"] + [f"  {v}" for v in missing]
        (dest / f"{site}_history_inventory.txt").write_text("\n".join(lines) + "\n")
        rec["Mortality_types_found"] = ", ".join(sorted(v[5:] for v in spec.values() if str(v).startswith("MORT_"))) or "none"
        rec["Missing_suggested_vars"] = ", ".join(missing)
        print(f"[{site}] AD {len(inv['ad_years'])}y + Normal {len(inv['normal_years'])}y; "
              f"{len(spec)} variables; mortality types: {rec['Mortality_types_found']}", flush=True)
        names, src = pft_names(pair["normal"], args)
        rec["PFT_names_from"] = src
        mon, units = read_series(inv, spec)
        if ad_only:
            mon = add_original_gpp(mon, ad, inv, args, rec)
        ann = annual_from_monthly(mon)
        focal = choose_focal(mon, names)
        cy, cy_col = collapse_year(ann, focal)
        rec["Focal_PFT"] = f"{focal} {names[focal - 1]}" if focal and focal - 1 < len(names) else str(focal)
        rec["Collapse_year"] = cy if cy is not None else ""
        rec["Collapse_based_on"] = cy_col or ""
        rec["Output_note"] = output_note(ann, focal)
        g = ann["FATES_GPP"] if "FATES_GPP" in ann else None
        if g is not None and g.notna().any():
            rec["GPP_year1_gC_m-2_d-1"] = float(g.iloc[0])
            rec["GPP_max_annual_gC_m-2_d-1"] = float(g.max())
            rec["GPP_max_year"] = int(ann.SpinupYear[g.idxmax()])
        att = attribution(mon, ann, focal, cy)
        rec.update(att)
        mon.to_csv(dest / f"{site}_collapse_monthly.csv", index=False)
        ann.to_csv(dest / f"{site}_collapse_annual.csv", index=False)
        (dest / f"{site}_collapse_units.json").write_text(json.dumps(units, indent=2) + "\n")
        plot_site(site, pair, ann, names, focal, cy, att, dest, False, args.first_years)
        plot_site(site, pair, mon, names, focal, cy, att, dest, True, args.first_years)
        rec["Status"] = "OK"
    except Exception as exc:
        rec["Error"] = f"{type(exc).__name__}: {exc}"
        (dest / "ERROR.txt").write_text(traceback.format_exc())
        print(f"[{site}] FAILED: {rec['Error']}", flush=True)
    return rec


def save_summary(root, rows):
    first = ["Site", "Status", "Focal_PFT", "Collapse_year", "GPP_vs_original", "Output_note", "GPP_year1_gC_m-2_d-1",
             "GPP_max_annual_gC_m-2_d-1", "GPP_max_year", "Attribution_window", "Dominant_mortality",
             "Dominant_share_pct", "Top3_mortality", "Focal_NPP_mean_gC_m-2_d-1", "Focal_GPP_mean_gC_m-2_d-1",
             "Focal_density_mean_ha-1", "Storage_fraction_of_target_mean", "Storage_fraction_of_target_min",
             "BTRAN_min_month", "TSA_min_month_C", "Mortality_types_found", "Missing_suggested_vars",
             "Normal_case", "AD_case", "Error"]
    fields = first + sorted({k for r in rows for k in r} - set(first))
    with (root / "collapse_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["Site"]):
            w.writerow(r)


def run(a):
    cases = dict(F7.JOB_CASES)
    unknown = [] if a.ad_only else [s for s in a.sites if s not in cases]
    if unknown:
        raise SystemExit("not in the 07 case list: " + ", ".join(unknown))
    a.output_root.mkdir(parents=True, exist_ok=True)
    tasks = [(s, cases[s], a) for s in a.sites]
    if a.ad_only:
        tasks = [(s, c, a, True) for s, c in (x.split(":", 1) for x in a.ad_only)]
        a.sites = [t[0] for t in tasks]
    if a.workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=min(a.workers, len(tasks))) as ex:
            rows = list(ex.map(process, tasks))
    else:
        rows = [process(t) for t in tasks]
    save_summary(a.output_root, rows)
    for r in rows:
        if r.get("GPP_vs_original"):
            print(f"   {r['Site']}: GPP vs original AD case: {r['GPP_vs_original']}", flush=True)
        print(f"== {r['Site']}: {r['Status']} | focal {r.get('Focal_PFT', '')} | collapse {r.get('Collapse_year') or 'n/a'} | "
              f"{r.get('Top3_mortality') or r.get('Dominant_mortality', '')} {r.get('Error', '')}", flush=True)
        if r.get("Output_note"):
            print(f"   {r['Site']}: {r['Output_note']}; GPP year 1 = {r.get('GPP_year1_gC_m-2_d-1', float('nan')):.3g}, "
                  f"max annual = {r.get('GPP_max_annual_gC_m-2_d-1', float('nan')):.3g} g C m-2 d-1 (year {r.get('GPP_max_year', '?')})", flush=True)
    ok = sum(r["Status"] == "OK" for r in rows)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(rows), "sites": a.sites, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(rows)} sites. Summary: {a.output_root / 'collapse_summary.csv'}", flush=True)
    return 0 if ok == len(rows) else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: the diagnostic run did not finish; nothing published")
    with (run_dir / "collapse_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    with tempfile.TemporaryDirectory(prefix="collapse_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        shutil.copyfile(run_dir / "collapse_summary.csv", out / "collapse_summary.csv")
        lines = ["# Collapse diagnostics: mortality by type, carbon balance, storage, density, recruitment", "",
                 "Full AD400 → NORMAL400 sequence (annual) and the first AD years (monthly).",
                 "Focal PFT = needleleaf PFT with most vegetation carbon in year 1. Collapse = focal-PFT VEGC stays < 1 % of its maximum.",
                 "Mortality shares are means over the 20 years before collapse (first two years monthly if it dies at once).",
                 "Screening numbers from history output, not conclusions.", "",
                 "| Site | Focal PFT | Collapse year | Window | Mortality (top 3) | Focal NPP | Storage/target min | BTRAN min | Figures |",
                 "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |"]
        fmt = lambda v: f"{float(v):.3g}" if v not in (None, "") and np.isfinite(float(v)) else "–"
        for r in sorted(rows, key=lambda r: r["Site"]):
            s = r["Site"]
            if not F7.SAFE.fullmatch(s):
                raise ValueError(f"unsafe site {s!r}")
            links = []
            for p in sorted((run_dir / s).glob(f"{s}_0[45]_collapse_diagnostics_*.png")):
                if F7.is_png(p):
                    (out / s).mkdir(exist_ok=True)
                    shutil.copyfile(p, out / s / p.name)
                    links.append(f"[{'800 y' if 'full800' in p.name else 'AD re-run' if 'ADrerun' in p.name else 'first years'}]({s}/{p.name})")
            inv = run_dir / s / f"{s}_history_inventory.txt"
            if inv.is_file():
                (out / s).mkdir(exist_ok=True)
                shutil.copyfile(inv, out / s / inv.name)
                links.append(f"[variables]({s}/{inv.name})")
            top = (r.get("Top3_mortality") or r.get("Dominant_mortality") or r.get("Error", "")[:80]).replace("|", "/")
            note = (r.get("Output_note") or "").replace("|", "/")
            lines.append(f"| {s} | {r.get('Focal_PFT', '')} | {r.get('Collapse_year') or 'n/a'} {('(' + note + ')') if note else ''} | {r.get('Attribution_window', '')} | "
                         f"{top} | {fmt(r.get('Focal_NPP_mean_gC_m-2_d-1'))} | {fmt(r.get('Storage_fraction_of_target_min'))} | "
                         f"{fmt(r.get('BTRAN_min_month'))} | {' '.join(links) or 'missing'} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add collapse diagnostics ({len(rows)} sites, {len(sums)} PNG)", cwd=co)
        sha = F7.git("rev-parse", "HEAD", cwd=co)
        F7.git("push", "origin", "HEAD:main", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path, help="new or empty directory (Home/RFS, not scratch)")
    ap.add_argument("--publish-run", type=Path, help="publish PNGs + summary of a finished run to GitHub (login node)")
    ap.add_argument("--sites", nargs="+", default=DEFAULT_SITES)
    ap.add_argument("--ad-only", nargs="+", metavar="SITE:CASE",
                    help="read a single AD case (e.g. the 09 diagnostic re-run) instead of the 07 AD/Normal pair")
    ap.add_argument("--first-years", type=int, default=30, help="years shown in the monthly zoom figure")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--module07", help="path to 07_plot_full_sequence_GPP_NEE_with_EC.py (default: fullseq.py beside this file)")
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--cases-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    load_modules(a.module07)
    a.archive_root = a.archive_root or Path(f"/scratch/{F7.USER}/CTSM_FATES_OUTPUTS/archive")
    a.cases_root = a.cases_root or Path(f"/iridisfs/scratch/{F7.USER}/CLM_FATES/cases")
    if a.publish_run:
        return publish(a.publish_run, a.repo or F7.REPO)
    if not a.output_root:
        ap.error("give --output-root (new run) or --publish-run")
    root = a.output_root.expanduser()
    if not root.is_absolute():
        ap.error("output directory must be absolute")
    root = root.resolve()
    if not a.allow_scratch_output and any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty: " + str(root))
    a.output_root = root
    try:
        os.nice(10)
    except OSError:
        pass
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
