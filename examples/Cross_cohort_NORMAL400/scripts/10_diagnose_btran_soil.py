#!/usr/bin/env python3
"""Why is BTRAN ~0.05 at the collapsing needleleaf sites?  Read-only soil / root diagnostics.

For each case it reads, by soil layer: liquid water, ice, temperature, and FATES fine-root
carbon (FATES_FROOTC_SL), plus BTRAN, GPP, LAI, precipitation and FATES patch areas.
It then recomputes BTRAN layer by layer with the FATES/CLM non-hydro formula

    s      = max(liq_vol / eff_porosity, 0.01),  eff_porosity = max(watsat - ice_vol, 0.01)
    smp    = max(-sucsat * s^-bsw, smpsc)
    w      = clip(eff_porosity/watsat * (smp - smpsc)/(smpso - smpsc), 0, 1)
    gate   = 1 if T_soil > tfrz - 2 K and liq_vol > 0 else 0
    BTRAN ~= sum over layers  root_fraction * w * gate

(root fraction from FATES_FROOTC_SL; smpso/smpsc of the dominant PFT from the case's
FATES parameter file) and splits the loss into: dry soil (w), frozen/cold soil (gate),
roots (where they are), and patch area (BTRAN is averaged over the whole site).
If the estimate does not match the model's BTRAN, that mismatch is itself the finding.

Default cases: the two 09 diagnostic re-runs (first 50 AD years) and two living
references from NORMAL400 (last 50 years): DE-Hai (broadleaf) and FI-Hyy (needleleaf).

Outputs
  <out>/<label>/<label>_06_btran_soil_timeseries.png   depth x time panels + BTRAN check
  <out>/<label>/<label>_07_btran_soil_profiles.png     growing-season (JJA) profiles
  <out>/<label>/<label>_btran_soil_monthly.csv, _layers_JJA.csv, _inventory.txt
  <out>/ALL_CASES_08_btran_soil_comparison.png, btran_soil_summary.csv, RUN_COMPLETE.json
Usage
  python -B 10_...py --output-root DIR [--cases SITE:CASE[:first50|last50|all] ...] [--max-depth 2]
  python -B 10_...py --publish-run DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIG_DIR = "figures/AD400_NORMAL400_btran_soil_diagnostics"
TFRZ = 273.15
DEFAULT_CASES = ["DE-Obe:DE-Obe_B03_FIXNC_AD400_DIAG50:first50",
                 "FI-Sod:FI-Sod_B01_FIXNC_AD400_DIAG50:first50",
                 "DE-Hai_ref:DE-Hai_B01_FIXNC_NORMAL400:last50",
                 "FI-Hyy_ref:FI-Hyy_B02_FIXNC_NORMAL400:last50"]
SCALARS = ["BTRAN", "FATES_GPP", "TLAI", "TSA", "RAIN", "SNOW", "H2OSNO", "FSDS", "QVEGT"]
LAYERED = ["SOILLIQ", "SOILICE", "H2OSOI", "TSOI", "SMP", "FATES_FROOTC_SL"]
CONSTS = ["ZSOI", "DZSOI", "WATSAT", "SUCSAT", "BSW"]
PFTVARS = ["FATES_NOCOMP_PATCHAREA_PF", "FATES_VEGC_PF", "FATES_GPP_PF"]
SMP_NAMES = [("fates_nonhydro_smpso", "fates_nonhydro_smpsc"), ("fates_smpso", "fates_smpsc")]
JJA = (6, 7, 8)

F7 = None
P = None


def load_modules():
    global F7, P
    for c in (HERE / "fullseq.py", HERE / "07_plot_full_sequence_GPP_NEE_with_EC.py"):
        if c.is_file():
            spec = importlib.util.spec_from_file_location("fullseq07", c)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            F7 = m
            P, _ = m.load_plot_module(None)
            return
    raise FileNotFoundError("module 07 (fullseq.py) not found beside this script")


# ------------------------------------------------------------------ reading
def arr(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    return a


def squeeze_point(var):
    """(time, k) for time-dependent single-point variables; (k,) for constants."""
    a = arr(var)
    dims = list(var.dimensions)
    if "time" in dims:
        a = np.moveaxis(a, dims.index("time"), 0)
        return a.reshape(a.shape[0], -1)
    return a.reshape(-1)


def read_constants(path, nlev_hint=None):
    from netCDF4 import Dataset
    out = {}
    with Dataset(str(path)) as ds:
        for n in CONSTS:
            if n in ds.variables:
                v = squeeze_point(ds.variables[n])
                out[n] = v[0] if v.ndim == 2 else v
        if "ZSOI" not in out and "levgrnd" in ds.variables:
            out["ZSOI"] = arr(ds.variables["levgrnd"]).reshape(-1)
        out["nlevsoi"] = len(ds.dimensions["levsoi"]) if "levsoi" in ds.dimensions else nlev_hint
        names = set(ds.variables)
    if "ZSOI" in out and "DZSOI" not in out:
        z = out["ZSOI"]
        edges = np.concatenate([[0.0], 0.5 * (z[1:] + z[:-1]), [z[-1] + 0.5 * (z[-1] - z[-2])]])
        out["DZSOI"] = np.diff(edges)
    return out, names


def read_file(path, names):
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
        if bname is None:
            raise ValueError(f"{path.name}: no time bounds")
        b = np.asarray(ds.variables[bname][:], dtype=float)
        dur = b[:, 1] - b[:, 0]
        dates = P.noleap_dates(ds)
        vals = {}
        for n in SCALARS + LAYERED + PFTVARS:
            if n in names and n in ds.variables:
                vals[n] = squeeze_point(ds.variables[n])
        units = {n: str(getattr(ds.variables[n], "units", "")) for n in vals}
    return dates, dur, vals, units


def monthly_series(case, years, names, archive):
    fidx = P.history_index(archive, case)
    recs, units = [], {}
    for k, y in enumerate(years):
        for path in fidx[y]:
            dates, dur, vals, u = read_file(path, names)
            units.update(u)
            for i, (yy, mm, _) in enumerate(dates):
                if yy != y:
                    raise ValueError(f"{path.name}: sample year {yy} != {y}")
                recs.append({"Year": y, "Month": mm, "w": dur[i], **{n: v[i] for n, v in vals.items()}})
        if (k + 1) % 25 == 0:
            print(f"    {case}: read {k + 1}/{len(years)} years", flush=True)
    # monthly means (files may hold daily samples)
    out = []
    for (y, m), g in pd.DataFrame(recs).groupby(["Year", "Month"], sort=True):
        w = g["w"].to_numpy(float)
        r = {"Year": int(y), "Month": int(m)}
        for n in g.columns:
            if n in ("Year", "Month", "w"):
                continue
            stack = np.vstack([np.atleast_1d(np.asarray(x, dtype=float)) for x in g[n]])
            ok = np.isfinite(stack)
            num = np.nansum(np.where(ok, stack, 0) * w[:, None], axis=0)
            den = np.sum(ok * w[:, None], axis=0)
            r[n] = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        out.append(r)
    return out, units


# ------------------------------------------------------------------ parameters
def param_file(case, args):
    for p in (args.archive_root.parent / case / "run" / "lnd_in", args.cases_root / case / "CaseDocs" / "lnd_in"):
        try:
            m = re.search(r"fates_paramfile\s*=\s*['\"]([^'\"]+)['\"]", p.read_text())
            if m:
                return Path(m.group(1))
        except OSError:
            continue
    return None


def read_params(path):
    """{name: list} for every PFT parameter; JSON or netCDF parameter file."""
    if path is None or not path.is_file():
        return {}
    if path.suffix == ".json":
        d = json.loads(path.read_text())["parameters"]
        return {k: v.get("data") for k, v in d.items() if isinstance(v, dict)}
    from netCDF4 import Dataset, chartostring
    out = {}
    with Dataset(str(path)) as ds:
        for k, v in ds.variables.items():
            try:
                out[k] = [str(x).strip() for x in chartostring(v[:])] if v.dtype.kind in "SU" else np.asarray(v[:]).tolist()
            except Exception:
                pass
    return out


def smp_params(params, pft):
    for so, sc in SMP_NAMES:
        if so in params and sc in params:
            vo, vc = np.ravel(params[so]), np.ravel(params[sc])
            return float(vo[pft - 1]), float(vc[pft - 1]), f"{so}/{sc}"
    return None, None, "smpso/smpsc not found in parameter file"


# ------------------------------------------------------------------ analysis
def build(case_rows, const, max_depth):
    """Monthly DataFrame of scalars + dict of (time, layer) arrays for the top layers."""
    nl = const.get("nlevsoi") or 20
    z = np.asarray(const["ZSOI"][:nl], float)
    dz = np.asarray(const["DZSOI"][:nl], float)
    keep = z <= max_depth + 1e-9
    lay = {}
    for n in LAYERED:
        if case_rows and n in case_rows[0]:
            a = np.vstack([np.asarray(r[n], float)[:nl] for r in case_rows])
            lay[n] = a[:, :nl]
    df = pd.DataFrame([{k: (float(np.ravel(v)[0]) if k in SCALARS else v) for k, v in r.items()
                        if k in SCALARS or k in ("Year", "Month")} for r in case_rows])
    for n in PFTVARS:
        if case_rows and n in case_rows[0]:
            a = np.vstack([np.asarray(r[n], float) for r in case_rows])
            for p in range(a.shape[1]):
                df[f"{n}__pft{p + 1}"] = a[:, p]
    return df, lay, z, dz, keep


def layer_terms(lay, const, dz, smpso, smpsc):
    """Per-layer liq/ice volumetric water, w, gate and root fraction (time x layer)."""
    nl = len(dz)
    t = {}
    watsat = np.asarray(const.get("WATSAT", np.full(nl, np.nan))[:nl], float)
    sucsat = np.asarray(const.get("SUCSAT", np.full(nl, np.nan))[:nl], float)
    bsw = np.asarray(const.get("BSW", np.full(nl, np.nan))[:nl], float)
    if "SOILLIQ" in lay:
        t["liq_vol"] = lay["SOILLIQ"] / (dz * 1000.0)
    elif "H2OSOI" in lay:
        t["liq_vol"] = lay["H2OSOI"]                       # total water if liquid is not written
    if "SOILICE" in lay:
        t["ice_vol"] = lay["SOILICE"] / (dz * 917.0)
    if "TSOI" in lay:
        t["T_C"] = lay["TSOI"] - TFRZ
    if "FATES_FROOTC_SL" in lay:
        rc = np.clip(lay["FATES_FROOTC_SL"], 0, None) * dz
        tot = rc.sum(axis=1, keepdims=True)
        t["root_frac"] = np.where(tot > 0, rc / np.where(tot > 0, tot, 1), np.nan)
    watsat = np.where(watsat > 0, watsat, np.nan)          # bedrock / missing layers -> NaN, not division by zero
    if "liq_vol" in t and np.isfinite(watsat).any() and np.isfinite(sucsat).any() and np.isfinite(bsw).any() \
            and smpso is not None:
        ice = t.get("ice_vol", np.zeros_like(t["liq_vol"]))
        eff = np.maximum(watsat - ice, 0.01)
        s = np.clip(t["liq_vol"] / eff, 0.01, 1.0)
        smp = np.maximum(-sucsat * s ** (-bsw), smpsc)
        t["smp_est_mm"] = smp
        t["w_dry"] = np.clip((smp - smpsc) / (smpso - smpsc), 0, 1)          # water potential only
        t["ice_factor"] = np.clip(eff / watsat, 0, 1)
        t["w"] = np.clip(t["ice_factor"] * (smp - smpsc) / (smpso - smpsc), 0, 1)
    if "SMP" in lay:
        t["smp_model_mm"] = lay["SMP"]
    if "T_C" in t and "liq_vol" in t:
        t["gate"] = ((t["T_C"] > -2.0) & (t["liq_vol"] > 0)).astype(float)
    if all(k in t for k in ("root_frac", "w", "gate")):
        t["contrib"] = t["root_frac"] * t["w"] * t["gate"]
    return t


def jja(df):
    return df["Month"].isin(JJA).to_numpy()


def summarize(label, case, df, t, z, dz, area, pft, pname, smpso, smpsc, src, window):
    m = jja(df)
    r = {"Label": label, "Case": case, "Years": window, "Dominant_PFT": f"{pft} {pname}",
         "smpso_mm": smpso, "smpsc_mm": smpsc, "smp_params": src}
    def mean(x):
        x = np.asarray(x, float)
        return float(np.nanmean(x)) if np.isfinite(x).any() else np.nan
    for c, lab in (("BTRAN", "BTRAN_model_JJA"), ("FATES_GPP", "GPP_JJA_kgC_m-2_s-1"), ("TLAI", "TLAI_JJA")):
        if c in df:
            r[lab] = mean(df[c][m])
    if "BTRAN" in df:
        r["BTRAN_model_annual"] = mean(df["BTRAN"])
    if "contrib" in t:
        est = np.nansum(t["contrib"], axis=1)
        r["BTRAN_est_vegetated_JJA"] = mean(est[m])
        r["BTRAN_est_annual"] = mean(est)
        if area is not None:
            r["BTRAN_est_x_veg_area_JJA"] = r["BTRAN_est_vegetated_JJA"] * area
    if area is not None:
        r["Vegetated_patch_area_frac"] = area
    if "root_frac" in t:
        rf = np.nanmean(t["root_frac"][m], axis=0)
        cum = np.cumsum(np.nan_to_num(rf))
        zb = np.cumsum(dz)
        for q in (0.5, 0.9):
            i = int(np.searchsorted(cum, q))
            r[f"Root_depth_{int(q * 100)}pct_m"] = float(zb[min(i, len(zb) - 1)])
        r["Root_frac_top10cm"] = float(np.nansum(rf[zb <= 0.10 + 1e-9]))
        for k in ("liq_vol", "ice_vol", "T_C", "w_dry", "ice_factor", "gate", "w", "smp_est_mm", "smp_model_mm"):
            if k in t:
                v = np.nanmean(t[k][m], axis=0)
                ok = np.isfinite(v) & np.isfinite(rf)
                r[f"RootWeighted_{k}_JJA"] = float(np.sum(v[ok] * rf[ok]) / np.sum(rf[ok])) if ok.any() and rf[ok].sum() > 0 else np.nan
    # which factor limits most (growing season, root-weighted; 1 = no limitation)
    fac = {"dry soil (water potential below smpso)": r.get("RootWeighted_w_dry_JJA"),
           "frozen/cold soil (T <= -2 C)": r.get("RootWeighted_gate_JJA"),
           "ice in pores": r.get("RootWeighted_ice_factor_JJA")}
    fac = {k: v for k, v in fac.items() if v is not None and np.isfinite(v)}
    if fac:
        k = min(fac, key=fac.get)
        r["Most_limiting_JJA"] = f"{k}: {fac[k]:.2f}" if fac[k] < 0.95 else "no soil limitation in rooted layers (all factors >= 0.95)"
    if "BTRAN_model_JJA" in r and "BTRAN_est_vegetated_JJA" in r:
        mod, est = r["BTRAN_model_JJA"], r["BTRAN_est_vegetated_JJA"]
        r["Estimate_vs_model"] = ("estimate matches model BTRAN" if abs(est - mod) <= max(0.05, 0.25 * abs(mod)) else
                                  "estimate x vegetated area matches model BTRAN (site average dilutes it)"
                                  if area is not None and abs(est * area - mod) <= max(0.05, 0.25 * abs(mod)) else
                                  f"MISMATCH: estimate {est:.2f} vs model {mod:.2f}")
    return r


# ------------------------------------------------------------------ plots
def plot_timeseries(label, case, df, t, z, keep, dest, smpso, smpsc, r):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = (df["Year"] - df["Year"].iloc[0] + (df["Month"] - 0.5) / 12.0).to_numpy(float)
    zz = z[keep]
    panels = [("BTRAN: model vs estimate", None), ("Liquid water (m3 m-3)", "liq_vol"), ("Ice (m3 m-3)", "ice_vol"),
              ("Soil temperature (°C)", "T_C"), ("Water-stress factor w per layer (0 = closed, 1 = open)", "w"),
              ("Fine-root fraction per layer", "root_frac")]
    fig, axs = plt.subplots(len(panels), 1, figsize=(15, 2.7 * len(panels)), sharex=True)
    for ax, (title, key) in zip(axs, panels):
        ax.set_title(title, loc="left", fontsize=10.5)
        if key is None:
            if "BTRAN" in df:
                ax.plot(x, df["BTRAN"], color="k", lw=1, label="BTRAN (model, site average)")
            if "contrib" in t:
                ax.plot(x, np.nansum(t["contrib"], axis=1), color="tab:red", lw=1, ls="--",
                        label="estimate Σ root×w×gate (vegetated patches)")
            if "FATES_GPP" in df:
                a2 = ax.twinx()
                a2.plot(x, df["FATES_GPP"] * 86400e3, color="tab:green", lw=0.8, alpha=0.7)
                a2.set_ylabel("GPP g C m-2 d-1", color="tab:green")
            ax.set_ylim(0, 1.05); ax.legend(frameon=False, fontsize=8, loc="upper left")
            continue
        if key not in t:
            ax.text(0.5, 0.5, "not in history output", transform=ax.transAxes, ha="center", va="center", color="0.5")
            ax.set_yticks([]); continue
        v = t[key][:, keep].T
        cmap, vmin, vmax = {"liq_vol": ("Blues", 0, None), "ice_vol": ("PuBu", 0, None), "T_C": ("RdBu_r", -15, 15),
                            "w": ("viridis", 0, 1), "root_frac": ("YlOrBr", 0, None)}[key]
        pc = ax.pcolormesh(x, zz, v, shading="nearest", cmap=cmap, vmin=vmin, vmax=vmax)
        if key == "T_C" and np.isfinite(v).any() and np.nanmin(v) < 0 < np.nanmax(v):
            ax.contour(x, zz, v, levels=[-2, 0], colors=["k", "0.4"], linewidths=[0.8, 0.5])
        ax.invert_yaxis(); ax.set_ylabel("depth (m)")
        fig.colorbar(pc, ax=ax, pad=0.01, fraction=0.025)
    axs[-1].set_xlabel(f"Years from {int(df['Year'].iloc[0])} (monthly)")
    fig.suptitle(f"{label} | {case}\nBTRAN JJA model {r.get('BTRAN_model_JJA', np.nan):.3f} | estimate (vegetated) "
                 f"{r.get('BTRAN_est_vegetated_JJA', np.nan):.3f} | vegetated area {r.get('Vegetated_patch_area_frac', np.nan):.2f} | "
                 f"smpso/smpsc {smpso}/{smpsc} mm\n{r.get('Most_limiting_JJA', '')} | {r.get('Estimate_vs_model', '')}", fontsize=11)
    fig.tight_layout()
    p = dest / f"{label}_06_btran_soil_timeseries.png"
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    return p


def jja_profiles(df, t):
    m = jja(df)
    return {k: np.nanmean(v[m], axis=0) for k, v in t.items()}


def plot_profiles(label, case, df, t, z, keep, const, dest, smpso, smpsc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    prof = jja_profiles(df, t)
    zz = z[keep]
    fig, axs = plt.subplots(1, 5, figsize=(19, 6), sharey=True)
    def line(ax, key, lab, **kw):
        if key in prof:
            ax.plot(prof[key][keep], zz, marker="o", ms=3, label=lab, **kw)
            return True
        return False
    line(axs[0], "root_frac", "fine-root fraction", color="tab:brown"); axs[0].set_title("Fine roots (JJA)")
    line(axs[1], "liq_vol", "liquid", color="tab:blue"); line(axs[1], "ice_vol", "ice", color="tab:cyan")
    if "WATSAT" in const:
        axs[1].plot(np.asarray(const["WATSAT"][:len(z)])[keep], zz, color="0.5", ls="--", label="porosity (watsat)")
    axs[1].set_title("Soil water (JJA, m3 m-3)")
    for key, lab, c in (("smp_est_mm", "smp from water content", "tab:purple"), ("smp_model_mm", "SMP (model)", "k")):
        if key in prof:
            axs[2].plot(-prof[key][keep], zz, marker="o", ms=3, color=c, label=lab)
    if smpso is not None:
        axs[2].axvline(-smpso, color="tab:green", ls=":", label=f"smpso {smpso:g} (open)")
        axs[2].axvline(-smpsc, color="tab:red", ls=":", label=f"smpsc {smpsc:g} (closed)")
    axs[2].set_xscale("log"); axs[2].set_title("Soil suction (JJA, −mm, log)")
    line(axs[3], "w_dry", "w from water potential", color="tab:olive")
    line(axs[3], "w", "w incl. ice", color="tab:green")
    line(axs[3], "gate", "temperature gate", color="tab:red", ls="--")
    axs[3].set_xlim(-0.05, 1.05); axs[3].set_title("Stress factors (JJA, 1 = no stress)")
    line(axs[4], "contrib", "root × w × gate", color="k")
    axs[4].set_title("Contribution to BTRAN (JJA)")
    for ax in axs:
        ax.grid(alpha=0.25); ax.legend(frameon=False, fontsize=8)
    axs[0].invert_yaxis(); axs[0].set_ylabel("depth (m)")
    fig.suptitle(f"{label} | {case} | growing-season (JJA) profiles, top {zz.max():.2f} m", fontsize=11)
    fig.tight_layout()
    p = dest / f"{label}_07_btran_soil_profiles.png"
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    return p


def plot_comparison(root, results, max_depth):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ok = [x for x in results if x.get("df") is not None]
    if not ok:
        return None
    fig, axs = plt.subplots(1, 5, figsize=(21, 5.5))
    for i, res in enumerate(ok):
        c = plt.get_cmap("tab10")(i)
        df, t, z, keep, lab = res["df"], res["t"], res["z"], res["keep"], res["label"]
        if "BTRAN" in df:
            clim = df.groupby("Month")["BTRAN"].mean()
            axs[0].plot(clim.index, clim.values, color=c, marker="o", ms=3, label=lab)
        prof = jja_profiles(df, t)
        for ax, key in zip(axs[1:], ("root_frac", "liq_vol", "w", "T_C")):
            if key in prof:
                ax.plot(prof[key][keep], z[keep], color=c, marker="o", ms=3, label=lab)
    axs[0].set_title("BTRAN monthly climatology (model)"); axs[0].set_xlabel("month"); axs[0].set_ylim(0, 1.05)
    for ax, t_ in zip(axs[1:], ("Fine-root fraction (JJA)", "Liquid water (JJA, m3 m-3)", "w incl. ice (JJA)", "Soil T (JJA, °C)")):
        ax.set_title(t_); ax.invert_yaxis(); ax.set_ylabel("depth (m)")
    for ax in axs:
        ax.grid(alpha=0.25); ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"BTRAN and soil: collapsing needleleaf re-runs vs living references (top {max_depth} m)", fontsize=12)
    fig.tight_layout()
    p = root / "ALL_CASES_08_btran_soil_comparison.png"
    fig.savefig(p, dpi=140, bbox_inches="tight"); plt.close(fig)
    return p


# ------------------------------------------------------------------ driver
def select_years(fidx, case, args, which):
    yrs = sorted(fidx)
    y0 = int(P.env_value(args.cases_root / case, "RUN_STARTDATE")[:4])
    yrs = P.contiguous(fidx, y0, 10 ** 6) or yrs
    n = args.years
    return yrs if which == "all" else (yrs[:n] if which == "first50" else yrs[-n:])


def process(spec, args):
    parts = spec.split(":")
    label, case = parts[0], parts[1]
    which = parts[2] if len(parts) > 2 else "first50"
    dest = args.output_root / label
    dest.mkdir(parents=True, exist_ok=True)
    rec = {"Label": label, "Case": case, "Status": "FAILED"}
    try:
        fidx = P.history_index(args.archive_root, case)
        years = select_years(fidx, case, args, which)
        const, names = read_constants(fidx[years[0]][0])
        found = [n for n in SCALARS + LAYERED + CONSTS + PFTVARS if n in names or n in const]
        missing = [n for n in SCALARS + LAYERED + CONSTS + PFTVARS if n not in found]
        print(f"[{label}] {case}: years {years[0]}-{years[-1]} ({len(years)}); missing: {', '.join(missing) or 'none'}", flush=True)
        rows, units = monthly_series(case, years, names, args.archive_root)
        df, lay, z, dz, keep = build(rows, const, args.max_depth)
        pf = param_file(case, args)
        params = read_params(pf)
        names_pft = params.get("fates_pftname") or []
        vc = [c for c in df.columns if c.startswith("FATES_VEGC_PF__pft")]
        pft = max(vc, key=lambda c: np.nanmean(df[c].to_numpy(float)) if df[c].notna().any() else -1) if vc else "pft2"
        pft = int(re.search(r"(\d+)$", pft).group(1))
        pname = names_pft[pft - 1].strip() if pft - 1 < len(names_pft) else ""
        smpso, smpsc, src = smp_params(params, pft)
        ac = [c for c in df.columns if c.startswith("FATES_NOCOMP_PATCHAREA_PF__pft")]
        area = float(np.nanmean(df[ac].sum(axis=1, min_count=1))) if ac else None
        t = layer_terms(lay, const, dz, smpso, smpsc)
        r = summarize(label, case, df, t, z, dz, area, pft, pname, smpso, smpsc, src, f"{years[0]}-{years[-1]}")
        r["Parameter_file"] = str(pf) if pf else "not found"
        r["Missing_variables"] = ", ".join(missing)
        if ac:
            areas = {c.split("pft")[-1]: float(np.nanmean(df[c])) for c in ac}
            r["Patch_area_by_PFT"] = "; ".join(f"PFT{k} {v:.2f}" for k, v in areas.items() if v > 0.001)
        rec.update(r, Status="OK")
        out = df.copy()
        for k, v in t.items():
            if v.ndim == 2 and k in ("contrib",):
                out["BTRAN_est"] = np.nansum(v, axis=1)
        out.to_csv(dest / f"{label}_btran_soil_monthly.csv", index=False)
        prof = jja_profiles(df, t)
        pd.DataFrame({"depth_m": z, "dz_m": dz, **{k: v for k, v in prof.items()}}).to_csv(dest / f"{label}_layers_JJA.csv", index=False)
        lines = [f"case {case}, years {years[0]}-{years[-1]}", f"parameter file: {pf}",
                 f"smpso/smpsc ({src}): {smpso} / {smpsc} mm for PFT {pft} {pname}",
                 "found: " + ", ".join(found), "missing: " + (", ".join(missing) or "none"),
                 "units: " + json.dumps(units),
                 "root/smp parameters in file: " + ", ".join(sorted(k for k in params if re.search(r"smp|zroot|root[ab]", k)))]
        (dest / f"{label}_inventory.txt").write_text("\n".join(lines) + "\n")
        plot_timeseries(label, case, df, t, z, keep, dest, smpso, smpsc, r)
        plot_profiles(label, case, df, t, z, keep, const, dest, smpso, smpsc)
        return rec, {"label": label, "df": df, "t": t, "z": z, "keep": keep}
    except Exception as exc:
        rec["Error"] = f"{type(exc).__name__}: {exc}"
        (dest / "ERROR.txt").write_text(traceback.format_exc())
        print(f"[{label}] FAILED: {rec['Error']}", flush=True)
        return rec, {"label": label, "df": None}


def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    recs, results = [], []
    for spec in a.cases:
        r, res = process(spec, a)
        recs.append(r); results.append(res)
    first = ["Label", "Status", "Case", "Years", "Dominant_PFT", "BTRAN_model_JJA", "BTRAN_est_vegetated_JJA",
             "Vegetated_patch_area_frac", "BTRAN_est_x_veg_area_JJA", "Estimate_vs_model", "Most_limiting_JJA",
             "Root_depth_50pct_m", "Root_depth_90pct_m", "Root_frac_top10cm", "RootWeighted_liq_vol_JJA",
             "RootWeighted_ice_vol_JJA", "RootWeighted_T_C_JJA", "RootWeighted_w_dry_JJA", "RootWeighted_gate_JJA",
             "RootWeighted_ice_factor_JJA", "RootWeighted_smp_est_mm_JJA", "RootWeighted_smp_model_mm_JJA",
             "smpso_mm", "smpsc_mm", "TLAI_JJA", "GPP_JJA_kgC_m-2_s-1", "Patch_area_by_PFT", "Missing_variables", "Error"]
    fields = first + sorted({k for r in recs for k in r} - set(first))
    with (a.output_root / "btran_soil_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in recs:
            w.writerow(r)
    plot_comparison(a.output_root, results, a.max_depth)
    for r in recs:
        f3 = lambda k: f"{r[k]:.3f}" if isinstance(r.get(k), float) and np.isfinite(r[k]) else "–"
        print(f"== {r['Label']}: {r['Status']} | BTRAN JJA model {f3('BTRAN_model_JJA')} est {f3('BTRAN_est_vegetated_JJA')} "
              f"| veg area {f3('Vegetated_patch_area_frac')} | roots 90% above {f3('Root_depth_90pct_m')} m "
              f"| {r.get('Most_limiting_JJA', '')} | {r.get('Estimate_vs_model', r.get('Error', ''))}", flush=True)
    ok = sum(r["Status"] == "OK" for r in recs)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(recs), "cases": a.cases, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(recs)}. Summary: {a.output_root / 'btran_soil_summary.csv'}", flush=True)
    return 0 if ok == len(recs) else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    with (run_dir / "btran_soil_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    fmt = lambda v: f"{float(v):.3g}" if v not in (None, "") and np.isfinite(float(v)) else "–"
    with tempfile.TemporaryDirectory(prefix="btran_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        shutil.copyfile(run_dir / "btran_soil_summary.csv", out / "btran_soil_summary.csv")
        lines = ["# BTRAN and soil diagnostics: collapsing needleleaf re-runs vs living references", "",
                 "BTRAN is recomputed per layer with the FATES/CLM non-hydro formula from liquid water, ice, soil temperature,",
                 "fine-root distribution (FATES_FROOTC_SL) and the PFT's smpso/smpsc. JJA = growing season. Screening numbers.", ""]
        comp = run_dir / "ALL_CASES_08_btran_soil_comparison.png"
        if comp.is_file() and F7.is_png(comp):
            shutil.copyfile(comp, out / comp.name); lines += [f"- [All cases comparison]({comp.name})", ""]
        lines += ["| Case | Years | PFT | BTRAN JJA model | estimate | veg. area | roots 90% above (m) | most limiting (JJA) | check | Figures |",
                  "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |"]
        for r in rows:
            lab = r["Label"]
            if not F7.SAFE.fullmatch(lab):
                raise ValueError(f"unsafe label {lab!r}")
            links = []
            for p in sorted((run_dir / lab).glob(f"{lab}_0[67]_btran_soil_*.png")):
                if F7.is_png(p):
                    (out / lab).mkdir(exist_ok=True); shutil.copyfile(p, out / lab / p.name)
                    links.append(f"[{'time series' if '_06_' in p.name else 'profiles'}]({lab}/{p.name})")
            inv = run_dir / lab / f"{lab}_inventory.txt"
            if inv.is_file():
                (out / lab).mkdir(exist_ok=True); shutil.copyfile(inv, out / lab / inv.name)
                links.append(f"[inventory]({lab}/{inv.name})")
            cell = lambda k: (r.get(k) or "").replace("|", "/")
            lines.append(f"| {lab} ({cell('Case')}) | {cell('Years')} | {cell('Dominant_PFT')} | {fmt(r.get('BTRAN_model_JJA'))} | "
                         f"{fmt(r.get('BTRAN_est_vegetated_JJA'))} | {fmt(r.get('Vegetated_patch_area_frac'))} | "
                         f"{fmt(r.get('Root_depth_90pct_m'))} | {cell('Most_limiting_JJA')} | "
                         f"{cell('Estimate_vs_model') or cell('Error')[:80]} | {' '.join(links) or 'missing'} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add BTRAN/soil diagnostics ({len(rows)} cases, {len(sums)} PNG)", cwd=co)
        sha = F7.git("rev-parse", "HEAD", cwd=co)
        F7.git("push", "origin", "HEAD:main", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish-run", type=Path)
    ap.add_argument("--cases", nargs="+", default=DEFAULT_CASES, metavar="LABEL:CASE[:first50|last50|all]")
    ap.add_argument("--years", type=int, default=50, help="years for first50/last50 windows")
    ap.add_argument("--max-depth", type=float, default=2.0, help="deepest layer shown (m)")
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--cases-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    load_modules()
    a.archive_root = a.archive_root or Path(f"/scratch/{F7.USER}/CTSM_FATES_OUTPUTS/archive")
    a.cases_root = a.cases_root or Path(f"/iridisfs/scratch/{F7.USER}/CLM_FATES/cases")
    if a.publish_run:
        return publish(a.publish_run, a.repo or F7.REPO)
    if not a.output_root:
        ap.error("give --output-root or --publish-run")
    root = a.output_root.expanduser()
    if not root.is_absolute():
        ap.error("output directory must be absolute")
    root = root.resolve()
    if not a.allow_scratch_output and any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty: " + str(root))
    for c in a.cases:
        p = c.split(":")
        if len(p) < 2 or not F7.SAFE.fullmatch(p[0]) or (len(p) > 2 and p[2] not in ("first50", "last50", "all")):
            ap.error(f"bad --cases entry {c!r}")
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
