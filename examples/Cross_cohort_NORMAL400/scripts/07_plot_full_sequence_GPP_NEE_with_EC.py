#!/usr/bin/env python3
"""Read-only full-sequence GPP / NEE / NPP / LAI diagnostics for AD400 -> Normal400, with EC reference.

Covers the Normal cases plotted by job 4764252
(figures/AD400_NORMAL400/20261030T053000Z_job4764252). For every case pair it reads the
monthly land history of BOTH phases and draws one 800-year axis:

  spin-up years   1-400   AD case      (RUN_REFCASE of the Normal case)
  spin-up years 401-800   Normal case

Panels: GPP, NEE, NPP, LAI (and FATES_VEGC where it was written). Thin line = monthly
values (seasonal envelope), thick line = annual mean. GPP and NEE carry the EC tower
reference from the site's own forcing period: climatological annual mean (dotted),
peak month (dash-dot), and the range of complete-year annual means (grey band).

Why: CLM's AD switch rescales only soil decomposition pools, so vegetation fluxes and LAI
should run on continuously across year 400/401. A step there, a decline to zero
(vegetation collapse), or a level far from EC are what this figure is meant to show.

EC handling is NOT re-implemented: the Stage15 module (plot.py =
examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py) supplies the
history index, time decoding, DATM forcing years and EC readers, i.e. the same NT-before-DT
GPP policy, NEE_VUT_REF, minimum daily coverage and source priority as the job's monthly
EC overview. Model NEE = -FATES_NEP. Units g C m-2 d-1.

Outputs (never under scratch):
  <out>/<site>/<Normal case>/<site>_03_GPP_NEE_full_sequence_AD400_NORMAL400.png
                             <site>_full_sequence_annual.csv / _monthly.csv
                             <site>_EC_monthly_climatology.csv, <site>_full_sequence_metadata.json
  <out>/ALL_SITES_GPP_full_sequence_overview.png, ALL_SITES_NEE_full_sequence_overview.png
  <out>/full_sequence_summary.csv, RUN_COMPLETE.json

Usage (see examples/Cross_cohort_NORMAL400/FULL_SEQUENCE_GPP_NEE.md for the Slurm block):
  python -B 07_...py --output-root DIR [--sites A B ...] [--workers 8] [--resume DIR]
  python -B 07_...py --publish-run DIR        # login node: push PNGs + index to GitHub
800 model years do not prove equilibrium.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
USER = "ly3n24"
REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"
FIG_DIR = "figures/AD400_NORMAL400_full_sequence"
SOURCE_JOB = "4764252"
PHASE = 400
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)
PNG_SUFFIX = "_03_GPP_NEE_full_sequence_AD400_NORMAL400.png"
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
COLLAPSE_GPP = 0.05  # g C m-2 d-1: annual-mean GPP below this is treated as ~zero

# (site, Normal case) plotted by job 4764252 (status OK or CARBON_OK_EC_ERROR)
JOB_CASES = [
    ("AT-Neu", "AT-Neu_B03_FIXNC_NORMAL400"),
    ("BE-Bra", "BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_NORMAL400"),
    ("BE-Vie", "BE-Vie_B01_FIXNC_NORMAL400"),
    ("BR-Ma2", "BR-Ma2_AMF_FIXNC_NORMAL400_UTC_V2_PTS"),
    ("CA-Ca3", "CA-Ca3_AMF_FIXNC_NORMAL400_UTC_V2_PTS"),
    ("CA-LP1", "CA-LP1_AMF_FIXNC_NORMAL400_UTC_V2_PTS"),
    ("CA-TP4", "CA-TP4_AMF_FIXNC_NORMAL400_UTC_V3_PTS"),
    ("CH-Cha", "CH-Cha_B03_FIXNC_NORMAL400"),
    ("CH-Dav", "CH-Dav_B01_FIXNC_NORMAL400"),
    ("CH-Fru", "CH-Fru_B02_FIXNC_NORMAL400"),
    ("CH-Lae", "CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_NORMAL400"),
    ("CZ-BK1", "CZ-BK1_B01_FIXNC_NORMAL400"),
    ("CZ-Stn", "CZ-Stn_B03_FIXNC_NORMAL400"),
    ("DE-Hai", "DE-Hai_B01_FIXNC_NORMAL400"),
    ("DE-Hzd", "DE-Hzd_B03_FIXNC_NORMAL400"),
    ("DE-Lnf", "DE-Lnf_B03_FIXNC_NORMAL400"),
    ("DE-Obe", "DE-Obe_B03_FIXNC_NORMAL400"),
    ("DE-Tha", "DE-Tha_OBSPFT_NC_V1_NORMAL400"),
    ("DK-Sor", "DK-Sor_B02_FIXNC_ICOS_DBF100_NORMAL400"),
    ("ES-LJu", "ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_NORMAL400"),
    ("FI-Hyy", "FI-Hyy_B02_FIXNC_NORMAL400"),
    ("FI-Let", "FI-Let_B03_FIXNC_NORMAL400"),
    ("FI-Sod", "FI-Sod_B01_FIXNC_NORMAL400"),
    ("FR-FBn", "FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_NORMAL400"),
    ("FR-Fon", "FR-Fon_B01_FIXNC_NORMAL400"),
    ("FR-Hes", "FR-Hes_B02_FIXNC_NORMAL400"),
    ("FR-Pue", "FR-Pue_B01_FIXNC_NORMAL400"),
    ("GF-Guy", "GF-Guy_B03_FIXNC_NORMAL400"),
    ("IL-Yat", "IL-Yat_B03_FIXNC_BARE52_NORMAL400"),
    ("IT-Col", "IT-Col_B01_FIXNC_NORMAL400"),
    ("IT-Lav", "IT-Lav_B03_FIXNC_NORMAL400"),
    ("IT-MBo", "IT-MBo_B02_FIXNC_NORMAL400"),
    ("IT-Noe", "IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_NORMAL400"),
    ("IT-Ren", "IT-Ren_B01_FIXNC_NORMAL400"),
    ("RU-Fyo", "RU-Fyo_B01_FIXNC_NORMAL400"),
    ("US-BZS", "US-BZS_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-CMW", "US-CMW_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-EML", "US-EML_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-GLE", "US-GLE_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-Ha1", "US-Ha1_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-Ho1", "US-Ho1_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-Ho2", "US-Ho2_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-Ho3", "US-Ho3_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-ICt", "US-ICt_AMF_B02_FIXNC_NORMAL400_DIRECT"),
    ("US-Rpf", "US-Rpf_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-SP1", "US-SP1_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-SRG", "US-SRG_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-SRM", "US-SRM_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Seg", "US-Seg_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Ses", "US-Ses_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Slt", "US-Slt_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Syv", "US-Syv_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Ton", "US-Ton_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
    ("US-Uaf", "US-Uaf_AMF_B04_FIXNC_NORMAL400_BASETA_V1"),
]

# quantity -> [(history name, sign)], first present wins; flux sign applied after unit conversion
QUANT = {
    "GPP": [("FATES_GPP", 1.0), ("GPP", 1.0)],
    "NEE": [("FATES_NEP", -1.0), ("NEE", 1.0)],
    "NPP": [("FATES_NPP", 1.0), ("NPP", 1.0)],
    "LAI": [("TLAI", 1.0), ("FATES_LAI", 1.0)],
    "VEGC": [("FATES_VEGC", 1.0)],
    # written to the monthly/annual CSVs only (drought / snow context for die-back episodes)
    "TWS": [("TWS", 1.0)],
    "H2OSNO": [("H2OSNO", 1.0)],
}
UNITS = {"GPP": "g C m$^{-2}$ d$^{-1}$", "NEE": "g C m$^{-2}$ d$^{-1}$", "NPP": "g C m$^{-2}$ d$^{-1}$",
         "LAI": "m$^2$ m$^{-2}$", "VEGC": "g C m$^{-2}$"}
TITLES = {"GPP": "GPP", "NEE": "NEE (+ = source, model = −FATES_NEP)", "NPP": "NPP", "LAI": "LAI",
          "VEGC": "FATES vegetation carbon"}
C_AD, C_NO = "#d62728", "#1f77b4"

P = None  # Stage15 module, loaded per process


# ------------------------------------------------------------------ setup
def load_plot_module(explicit=None):
    cands = ([Path(explicit)] if explicit else []) + [
        HERE / "plot.py", HERE.parents[1] / "Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py"]
    for c in cands:
        if c.is_file():
            spec = importlib.util.spec_from_file_location("stage15_plot", c)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, c
    raise FileNotFoundError("Stage15 plot module not found; tried: " + ", ".join(map(str, cands)))


def _init_worker(path):
    global P
    P, _ = load_plot_module(path)


def conversion(q, units, name):
    u = (units or "").replace(" ", "").replace("^", "").lower()
    if q in ("GPP", "NEE", "NPP"):
        if not ("s-1" in u or "/s" in u):
            raise ValueError(f"{name}: flux units not per second: {units!r}")
        if u.startswith("kg"):
            return 1000.0 * 86400.0
        if u.startswith("g"):
            return 86400.0
        raise ValueError(f"{name}: unknown flux units {units!r}")
    if q == "VEGC":
        return 1000.0 if u.startswith("kg") else 1.0
    return 1.0


# ------------------------------------------------------------------ model
def read_year(paths, model_year):
    """Monthly means of all quantities for one model year (monthly or daily samples)."""
    from netCDF4 import Dataset
    recs, used = [], {}
    for path in paths:
        with Dataset(str(path)) as ds:
            bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
            if bname is None:
                raise ValueError(f"{path.name}: no time bounds")
            b = np.asarray(ds.variables[bname][:], dtype=float)
            dur = b[:, 1] - b[:, 0]
            dates = P.noleap_dates(ds)
            cols = {}
            for q, opts in QUANT.items():
                for name, sign in opts:
                    if name in ds.variables and P.is_point_timeseries(ds.variables[name]):
                        v = ds.variables[name]
                        cols[q] = P.point_series(v) * conversion(q, str(getattr(v, "units", "")), name) * sign
                        used[q] = name
                        break
            for i, (y, m, _) in enumerate(dates):
                if y != model_year:
                    raise ValueError(f"{path.name}: sample in year {y}, expected {model_year}")
                r = {"Month": m, "w": dur[i]}
                r.update({q: float(a[i]) for q, a in cols.items()})
                recs.append(r)
    df = pd.DataFrame(recs)
    if df.empty or sorted(df.Month.unique()) != list(range(1, 13)):
        raise ValueError(f"model year {model_year}: not a complete year of samples")
    out = []
    for m, g in df.groupby("Month"):
        r = {"Month": int(m)}
        w = g["w"].to_numpy(float)
        for q in QUANT:
            if q in g:
                v = g[q].to_numpy(float); ok = np.isfinite(v)
                r[q] = float(np.average(v[ok], weights=w[ok])) if ok.any() else np.nan
        out.append(r)
    return out, used


def model_series(inv):
    rows, used = [], {}
    years = [(i + 1, y, "AD", inv["fad"][y]) for i, y in enumerate(inv["ad_years"])] + \
            [(PHASE + i + 1, y, "NORMAL", inv["fno"][y]) for i, y in enumerate(inv["normal_years"])]
    for k, (spin, y, phase, paths) in enumerate(years):
        months, u = read_year(paths, y)
        for q, n in u.items():
            used.setdefault(phase, {})[q] = n
        for r in months:
            r.update(SpinupYear=spin, ModelYear=y, Phase=phase)
            rows.append(r)
        if (k + 1) % 200 == 0:
            print(f"    read {k + 1}/{len(years)} model years", flush=True)
    mon = pd.DataFrame(rows)
    for q in QUANT:
        if q not in mon:
            mon[q] = np.nan
    return mon, used


def annual(mon):
    rows = []
    for (spin, y, ph), g in mon.groupby(["SpinupYear", "ModelYear", "Phase"], sort=True):
        g = g.sort_values("Month"); w = DAYS[g.Month.to_numpy(int) - 1]
        r = {"SpinupYear": spin, "ModelYear": y, "Phase": ph}
        for q in QUANT:
            v = g[q].to_numpy(float)
            r[q] = float(np.sum(v * w) / w.sum()) if np.isfinite(v).all() else np.nan
        r["GPP_peak_month"] = float(np.nanmax(g.GPP)) if g.GPP.notna().any() else np.nan
        r["NEE_min_month"] = float(np.nanmin(g.NEE)) if g.NEE.notna().any() else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ EC
def ec_reference(site, first, last, args):
    srcs = P.ec_sources(args.sites_root / site / "forcing", None)
    obs, prov = P.ec_daily(srcs, first, last, args.min_halfhour)
    obs = obs.set_index("date")
    gpp_cols = sorted({c for c in obs["EC_GPP_column"].dropna() if c})
    ref, clim_rows = {"EC_GPP_columns": "+".join(gpp_cols), "EC_sources": "; ".join(Path(p["path"]).name for p in prov)}, {}
    for f in ("GPP", "NEE"):
        col = f"EC_{f}"
        v = pd.to_numeric(obs[col], errors="coerce")
        mm, nd = v.resample("MS").mean(), v.resample("MS").count()
        mm[nd < args.min_days] = np.nan
        mm = mm.dropna()
        if mm.empty:
            continue
        clim = mm.groupby(mm.index.month).mean()
        clim_rows[f] = clim
        if len(clim) == 12:
            ref[f"EC_{f}_mean"] = float(np.sum(clim.sort_index().to_numpy() * DAYS) / 365.0)
        ref[f"EC_{f}_months_in_climatology"] = int(len(clim))
        ref[f"EC_{f}_peak_month"] = float(clim.max())
        ref[f"EC_{f}_min_month"] = float(clim.min())
        yrs = []
        for yr, g in mm.groupby(mm.index.year):
            if len(g) == 12:
                yrs.append(float(np.sum(g.sort_index().to_numpy() * DAYS) / 365.0))
        ref[f"EC_{f}_complete_years"] = len(yrs)
        if len(yrs) >= 2:
            ref[f"EC_{f}_annual_min"], ref[f"EC_{f}_annual_max"] = min(yrs), max(yrs)
    clim = pd.DataFrame({f"EC_{k}": v for k, v in clim_rows.items()}).rename_axis("Month").reset_index()
    return ref, clim


# ------------------------------------------------------------------ diagnostics
def diagnostics(ann, inv, ref):
    first, last, align = inv["forcing"]
    d = {}
    ad, no = ann[ann.Phase == "AD"], ann[ann.Phase == "NORMAL"]
    for q in ("GPP", "NEE", "NPP", "LAI"):
        if len(ad) >= 5 and len(no) >= 5 and ad[q].tail(5).notna().all() and no[q].head(5).notna().all():
            b, a = ad[q].tail(5).mean(), no[q].head(5).mean()
            d[f"{q}_AD_last5"], d[f"{q}_Normal_first5"] = b, a
            d[f"{q}_step_400_401_pct"] = 100 * (a - b) / abs(b) if abs(b) > 1e-9 else np.nan
    try:
        cyc = P.last_complete_cycle(inv["normal_years"], first, last, align)
        c = ann[ann.ModelYear.isin(cyc) & (ann.Phase == "NORMAL")]
        d["Model_last_cycle_years"] = f"{cyc[0]}-{cyc[-1]}"
        for q in ("GPP", "NEE", "NPP", "LAI"):
            d[f"Model_{q}_last_cycle_mean"] = float(c[q].mean())
        d["Model_GPP_last_cycle_peak_month"] = float(c["GPP_peak_month"].mean())
    except Exception as exc:
        d["Model_last_cycle_years"] = f"none ({exc})"
    for f in ("GPP", "NEE"):
        m, e = d.get(f"Model_{f}_last_cycle_mean"), ref.get(f"EC_{f}_mean")
        if m is not None and e is not None and np.isfinite(m):
            d[f"{f}_bias_last_cycle_vs_EC"] = m - e
            if f == "GPP" and abs(e) > 1e-9:
                d["GPP_ratio_last_cycle_to_EC"] = m / e
    g = ann.GPP.to_numpy(float)
    flags = []
    if np.isfinite(g).any():
        gmax = np.nanmax(g)
        d["GPP_annual_max"] = gmax
        below = np.where(np.isfinite(g) & (g < COLLAPSE_GPP))[0]
        tail = g[-30:]
        if np.isfinite(tail).all() and tail.max() < COLLAPSE_GPP:
            k = len(g) - 1
            while k > 0 and np.isfinite(g[k - 1]) and g[k - 1] < COLLAPSE_GPP:
                k -= 1
            d["GPP_near_zero_from_spinup_year"] = int(ann.SpinupYear.iloc[k])
            flags.append(f"GPP≈0 from year {int(ann.SpinupYear.iloc[k])}")
        elif len(below):
            flags.append(f"GPP<{COLLAPSE_GPP} in {len(below)} years")
    for q in ("GPP", "LAI"):
        s = d.get(f"{q}_step_400_401_pct")
        if s is not None and np.isfinite(s) and abs(s) > 10:
            flags.append(f"{q} step {s:+.0f}% at 400/401")
    r = d.get("GPP_ratio_last_cycle_to_EC")
    if r is not None and np.isfinite(r) and (r < 0.5 or r > 2):
        flags.append(f"GPP {r:.2f}× EC")
    for q in ("GPP", "LAI"):
        v = no[q].to_numpy(float)[-100:]
        if len(v) >= 50 and np.isfinite(v).all() and abs(v.mean()) > 1e-6:
            pct = 100 * np.polyfit(np.arange(len(v)), v, 1)[0] * 100 / abs(v.mean())
            d[f"{q}_Normal_last100y_trend_pct_per_100y"] = pct
            if abs(pct) > 10:
                flags.append(f"{q} trend {pct:+.0f}%/100y (last 100y)")
    d["Flags"] = "; ".join(flags)
    return d


# ------------------------------------------------------------------ plots
def plot_site(site, pair, mon, ann, ref, ec_err, diag, dest, model_years):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    qs = [q for q in ("GPP", "NEE", "NPP", "LAI", "VEGC") if ann[q].notna().any() or mon[q].notna().any()]
    if not qs:
        raise ValueError("none of GPP/NEE/NPP/LAI/VEGC in the history")
    xm = mon.SpinupYear + (mon.Month - 0.5) / 12 - 1
    fig, axs = plt.subplots(len(qs), 1, figsize=(18, 3.2 * len(qs)), sharex=True, squeeze=False)
    for ax, q in zip(axs[:, 0], qs):
        ax.axvspan(0.5, PHASE + 0.5, color="0.94", zorder=0)
        for ph, c, lab in (("AD", C_AD, "AD400"), ("NORMAL", C_NO, "NORMAL400")):
            sm, sa = mon.Phase == ph, ann[ann.Phase == ph]
            if mon.loc[sm, q].notna().any():
                ax.plot(xm[sm], mon.loc[sm, q], color=c, lw=0.25, alpha=0.35, label=f"{lab} monthly")
            if sa[q].notna().any():
                ax.plot(sa.SpinupYear, sa[q], color=c, lw=1.6, label=f"{lab} annual mean")
        if q in ("GPP", "NEE"):
            lo, hi = ref.get(f"EC_{q}_annual_min"), ref.get(f"EC_{q}_annual_max")
            if lo is not None:
                ax.axhspan(lo, hi, color="0.55", alpha=0.18, label=f"EC annual-mean range {lo:.2f}–{hi:.2f}")
            m = ref.get(f"EC_{q}_mean")
            if m is not None:
                ax.axhline(m, color="k", ls=":", lw=1.3, label=f"EC annual mean {m:.2f}")
            k = "EC_GPP_peak_month" if q == "GPP" else "EC_NEE_min_month"
            if ref.get(k) is not None:
                ax.axhline(ref[k], color="0.3", ls="-.", lw=1,
                           label=("EC peak month " if q == "GPP" else "EC min month ") + f"{ref[k]:.2f}")
            mm = diag.get(f"Model_{q}_last_cycle_mean")
            if mm is not None and np.isfinite(mm):
                txt = f"model last cycle {mm:.2f}"
                if m is not None:
                    txt += f" | EC {m:.2f} | bias {mm - m:+.2f}"
                ax.text(0.995, 0.03, txt, transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
                        bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.85))
        if q == "NEE":
            ax.axhline(0, color="0.5", lw=0.8)
        if q in ("GPP", "NPP", "LAI", "VEGC"):
            ax.set_ylim(bottom=min(0, np.nanmin(mon[q]) if mon[q].notna().any() else 0))
        ax.axvline(PHASE + 0.5, color="0.3", ls="--", lw=1)
        ax.set_ylabel(f"{q}\n({UNITS[q]})")
        ax.set_title(TITLES[q], fontsize=10.5, loc="left")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.005, 1.0))
    axs[-1, 0].set_xlim(0.5, 2 * PHASE + 0.5)
    axs[-1, 0].set_xlabel("Spin-up year (1–400 AD, shaded | 401–800 Normal)")
    ec_note = f"EC: {ref.get('EC_GPP_columns') or 'GPP n/a'} + NEE_VUT_REF, forcing years {model_years}" if not ec_err \
        else f"EC reference unavailable: {ec_err[:110]}"
    flags = diag.get("Flags") or "no automatic flags"
    fig.suptitle(f"{site} | AD400 → NORMAL400 full sequence: GPP, NEE, NPP, LAI\n"
                 f"{pair['ad']} → {pair['normal']}\n{ec_note}\nFlags: {flags}", fontsize=11.5)
    fig.tight_layout()
    p = dest / f"{site}{PNG_SUFFIX}"
    fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_overview(root, rows, q):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    done = [r for r in rows if r.get("Status") in ("OK", "MODEL_ONLY")]
    if not done:
        return None
    n = len(done); ncol = 6; nrow = math.ceil(n / ncol)
    fig, axs = plt.subplots(nrow, ncol, figsize=(4.0 * ncol, 2.3 * nrow), squeeze=False, sharex=True)
    for ax, r in zip(axs.flat, sorted(done, key=lambda r: r["Site"])):
        try:
            a = pd.read_csv(Path(r["Output_directory"]) / f"{r['Site']}_full_sequence_annual.csv")
        except Exception:
            ax.set_visible(False); continue
        ax.axvspan(0.5, PHASE + 0.5, color="0.94", zorder=0)
        for ph, c in (("AD", C_AD), ("NORMAL", C_NO)):
            s = a[a.Phase == ph]
            ax.plot(s.SpinupYear, s[q], color=c, lw=1)
        e = r.get(f"EC_{q}_mean")
        if e not in (None, "") and np.isfinite(float(e)):
            ax.axhline(float(e), color="k", ls=":", lw=1.1)
        if q == "NEE":
            ax.axhline(0, color="0.6", lw=0.6)
        else:
            ax.set_ylim(bottom=0)
        ax.set_title(r["Site"] + (" ⚑" if r.get("Flags") else ""), fontsize=9,
                     color="#b00000" if "GPP≈0" in (r.get("Flags") or "") else "k")
        ax.tick_params(labelsize=7); ax.grid(alpha=0.2)
    for ax in list(axs.flat)[n:]:
        ax.set_visible(False)
    fig.suptitle(f"All sites | annual-mean {q} (g C m-2 d-1) over AD400 (red, shaded) → NORMAL400 (blue); "
                 f"dotted = EC annual mean; red title = GPP≈0 at the end", fontsize=12)
    fig.tight_layout()
    p = root / f"ALL_SITES_{q}_full_sequence_overview.png"
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return p


# ------------------------------------------------------------------ driver
def process(task):
    site, normal, args = task
    rec = {"Site": site, "Normal_case": normal, "AD_case": "", "Status": "SKIPPED", "Error": ""}
    dest = args.output_root / site / normal
    rec["Output_directory"] = str(dest)
    done = dest / ".full_sequence_done.json"
    if done.is_file():
        rec.update(json.loads(done.read_text()))
        rec["Resumed"] = True
        return rec
    try:
        ndir = args.cases_root / normal
        if not ndir.is_dir():
            raise FileNotFoundError(f"Normal case dir missing: {ndir}")
        ad = P.env_value(ndir, "RUN_REFCASE")
        rec["AD_case"] = ad
        pair = {"site": site, "ad": ad, "normal": normal, "ad_case_dir": args.cases_root / ad}
        inv = P.inventory(pair, args)
        if len(inv["ad_years"]) < PHASE:
            raise RuntimeError(f"AD history {len(inv['ad_years'])}/{PHASE} contiguous years")
        first, last, align = inv["forcing"]
        print(f"[{site}] AD {len(inv['ad_years'])}y + Normal {len(inv['normal_years'])}y; forcing {first}-{last}", flush=True)
        mon, used = model_series(inv)
        ann = annual(mon)
        ref, clim, ec_err = {}, pd.DataFrame(), ""
        try:
            ref, clim = ec_reference(site, first, last, args)
        except Exception as exc:
            ec_err = f"{type(exc).__name__}: {exc}"
            print(f"[{site}] EC reference skipped: {ec_err}", flush=True)
        diag = diagnostics(ann, inv, ref)
        if dest.exists():
            shutil.rmtree(dest)  # partial output from an interrupted earlier attempt (no done marker)
        dest.mkdir(parents=True)
        mon.to_csv(dest / f"{site}_full_sequence_monthly.csv", index=False)
        ann.to_csv(dest / f"{site}_full_sequence_annual.csv", index=False)
        if not clim.empty:
            clim.to_csv(dest / f"{site}_EC_monthly_climatology.csv", index=False)
        png = plot_site(site, pair, mon, ann, ref, ec_err, diag, dest, f"{first}-{last}")
        rec.update(Status="OK" if not ec_err else "MODEL_ONLY", Error=ec_err, AD_years=len(inv["ad_years"]),
                   Normal_years=len(inv["normal_years"]), Forcing=f"{first}-{last}", PNG=png.name, **ref, **diag)
        meta = dict(rec, variables_by_phase=used, model_nee="-FATES_NEP", flux_units="g C m-2 d-1",
                    stage15_module=str(args.plot_module_path),
                    caveat="Vegetation fluxes should be continuous at 400/401; AD rescales soil pools only. "
                           "EC/model use native timestamps (no timezone shift). 800 years is not proof of equilibrium.")
        (dest / f"{site}_full_sequence_metadata.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
        done.write_text(json.dumps({k: v for k, v in rec.items() if k != "Output_directory"}, default=str) + "\n")
    except Exception as exc:
        rec["Error"] = f"{type(exc).__name__}: {exc}"
        print(f"[{site}] SKIP: {rec['Error']}", flush=True)
        if os.environ.get("DEBUG"):
            traceback.print_exc()
    return rec


def save_summary(root, rows):
    fields = ["Site", "Status", "Flags", "EC_GPP_mean", "Model_GPP_last_cycle_mean", "GPP_ratio_last_cycle_to_EC",
              "EC_NEE_mean", "Model_NEE_last_cycle_mean", "GPP_step_400_401_pct", "LAI_step_400_401_pct",
              "GPP_near_zero_from_spinup_year", "Normal_case", "AD_case", "Error"]
    fields += sorted({k for r in rows for k in r} - set(fields))
    tmp = root / ".full_sequence_summary.tmp"
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["Site"]):
            w.writerow(r)
    tmp.replace(root / "full_sequence_summary.csv")


def run(a):
    global P
    P, a.plot_module_path = load_plot_module(a.plot_module)
    root = a.output_root
    root.mkdir(parents=True, exist_ok=True)
    base = [tuple(x.split(":", 1)) for x in a.pairs] if a.pairs else JOB_CASES
    sel = [(s, c) for s, c in base if not a.sites or s in a.sites]
    if a.sites and len({s for s, _ in sel}) != len(set(a.sites)):
        missing = sorted(set(a.sites) - {s for s, _ in sel})
        print("WARNING: not in the case list:", ", ".join(missing), flush=True)
    (root / "RUN_INFO.json").write_text(json.dumps({"source_job": SOURCE_JOB, "cases": sel, "workers": a.workers,
        "stage15_module": str(a.plot_module_path), "started_utc": datetime.now(timezone.utc).isoformat(),
        "slurm_job": os.environ.get("SLURM_JOB_ID", "")}, indent=2) + "\n")
    ns = SimpleNamespace(archive_root=a.archive_root, cases_root=a.cases_root, sites_root=a.sites_root,
                         output_root=root, min_halfhour=a.min_halfhour, min_days=a.min_days,
                         plot_module_path=a.plot_module_path)
    tasks = [(s, c, ns) for s, c in sel]
    rows = []
    if a.workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.workers, initializer=_init_worker, initargs=(str(a.plot_module_path),)) as pool:
            for r in pool.imap_unordered(process, tasks):
                rows.append(r); save_summary(root, rows)
                print(f"== {r['Site']}: {r['Status']} {r.get('Flags') or ''} {r.get('Error') or ''}", flush=True)
    else:
        for t in tasks:
            r = process(t); rows.append(r); save_summary(root, rows)
            print(f"== {r['Site']}: {r['Status']} {r.get('Flags') or ''} {r.get('Error') or ''}", flush=True)
    for q in ("GPP", "NEE"):
        try:
            plot_overview(root, rows, q)
        except Exception as exc:
            print(f"overview {q} failed: {type(exc).__name__}: {exc}", flush=True)
    ok = sum(r["Status"] in ("OK", "MODEL_ONLY") for r in rows)
    (root / "RUN_COMPLETE.json").write_text(json.dumps({"plotted": ok, "total": len(rows),
        "skipped": [r["Site"] for r in rows if r["Status"] == "SKIPPED"],
        "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(rows)} plotted (OK or MODEL_ONLY). Summary: {root / 'full_sequence_summary.csv'}", flush=True)
    return 0 if ok == len(rows) else 1


# ------------------------------------------------------------------ publish
def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError("git " + args[0] + " failed: " + p.stderr[-2000:])
    return p.stdout.strip()


def is_png(p):
    with open(p, "rb") as f:
        return f.read(8) == b"\x89PNG\r\n\x1a\n"


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: the plotting run did not finish; nothing published")
    with (run_dir / "full_sequence_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / f"{stamp}_from_job{SOURCE_JOB}"
    with tempfile.TemporaryDirectory(prefix="fullseq_publish_") as tmp:
        co = Path(tmp) / "repo"
        git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        lines = ["# AD400 → NORMAL400 full-sequence GPP / NEE / NPP / LAI with EC reference", "",
                 f"Source cases: job {SOURCE_JOB} (`figures/AD400_NORMAL400/20261030T053000Z_job4764252`).",
                 "Thin line = monthly, thick = annual mean; AD400 red (shaded), NORMAL400 blue.",
                 "EC: climatological annual mean (dotted), peak/min month (dash-dot), range of complete-year annual means (band).",
                 "Model NEE = −FATES_NEP. Units g C m⁻² d⁻¹. AD rescales soil pools only: vegetation series should be continuous at 400/401.",
                 "Flags are automatic screening hints, not conclusions. 800 years is not proof of equilibrium.", ""]
        for q in ("GPP", "NEE"):
            p = run_dir / f"ALL_SITES_{q}_full_sequence_overview.png"
            if p.is_file() and is_png(p):
                shutil.copyfile(p, out / p.name); lines.append(f"- [All sites {q} overview]({p.name})")
        lines += ["", "| Site | Status | EC GPP | Model GPP (last cycle) | Ratio | EC NEE | Model NEE | Flags | Figure |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
        fmt = lambda v: f"{float(v):.2f}" if v not in (None, "") and np.isfinite(float(v)) else "–"
        for r in sorted(rows, key=lambda r: r["Site"]):
            s, c = r["Site"], r["Normal_case"]
            if not (SAFE.fullmatch(s) and SAFE.fullmatch(c)):
                raise ValueError(f"unsafe identifier {s!r} {c!r}")
            link = "missing"
            src = run_dir / s / c / f"{s}{PNG_SUFFIX}"
            if r["Status"] in ("OK", "MODEL_ONLY") and src.is_file() and is_png(src):
                (out / s / c).mkdir(parents=True)
                shutil.copyfile(src, out / s / c / src.name)
                link = f"[PNG]({s}/{c}/{src.name})"
            flags = (r.get("Flags") or "").replace("|", "/") or (r.get("Error") or "")[:80].replace("|", "/")
            lines.append(f"| {s} | {r['Status']} | {fmt(r.get('EC_GPP_mean'))} | {fmt(r.get('Model_GPP_last_cycle_mean'))} | "
                         f"{fmt(r.get('GPP_ratio_last_cycle_to_EC'))} | {fmt(r.get('EC_NEE_mean'))} | "
                         f"{fmt(r.get('Model_NEE_last_cycle_mean'))} | {flags} | {link} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}"
                for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        git("add", "--", rel.as_posix(), cwd=co)
        git("commit", "-m", f"Add AD400-NORMAL400 full-sequence GPP/NEE figures ({len(sums)} PNG)", cwd=co)
        sha = git("rev-parse", "HEAD", cwd=co)
        git("push", "origin", "HEAD:main", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path, help="new or empty directory (Home/RFS, not scratch)")
    ap.add_argument("--resume", type=Path, help="continue an interrupted run in this directory; finished sites are kept")
    ap.add_argument("--publish-run", type=Path, help="publish PNGs + index of a finished run to GitHub (login node)")
    ap.add_argument("--repo", default=REPO, help=argparse.SUPPRESS)
    ap.add_argument("--sites", nargs="+", help="subset of the job's sites")
    ap.add_argument("--pairs", nargs="+", metavar="SITE:NORMAL_CASE",
                    help="other Normal cases instead of the job 4764252 list (AD case = its RUN_REFCASE)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--plot-module", help="path to the Stage15 plot module (default: plot.py beside this file, else the repo copy)")
    ap.add_argument("--archive-root", type=Path, default=Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS/archive"))
    ap.add_argument("--cases-root", type=Path, default=Path(f"/iridisfs/scratch/{USER}/CLM_FATES/cases"))
    ap.add_argument("--sites-root", type=Path, default=Path(f"/iridisfs/scratch/{USER}/CLM_FATES/sites/MY_EC_SITE"))
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.publish_run:
        return publish(a.publish_run, a.repo)
    if bool(a.output_root) == bool(a.resume):
        ap.error("give exactly one of --output-root (new run) or --resume (continue)")
    root = (a.output_root or a.resume).expanduser()
    if not root.is_absolute():
        ap.error("output directory must be absolute")
    root = root.resolve()
    if not a.allow_scratch_output and any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if a.output_root and root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty (use --resume to continue): " + str(root))
    if a.resume and not (root / "RUN_INFO.json").is_file():
        ap.error("--resume directory has no RUN_INFO.json: " + str(root))
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
