#!/usr/bin/env python3
"""Where does the needleleaf carbon budget fail?  Read-only per-plant / per-leaf carbon
budget comparison between cases, plus a side-by-side of the FATES PFT parameters.

For each case (single-PFT nocomp sites are attributed to their PFT; mixed sites are
flagged) it computes, monthly and per year:
  * per plant:      biomass, GPP, NPP, maintenance respiration, storage (g C plant-1)
  * per leaf:       GPP and maintenance respiration per kg leaf C and per m2 leaf (LAI)
  * carbon use:     shares of GPP going to leaf / fine-root / stem+coarse-root maintenance,
                    growth respiration, and allocation to leaf, roots, stem, storage, seed
  * stand state:    plants ha-1, LAI, canopy cover, height, storage relative to target
  * winter reserve: storage per plant divided by the winter carbon deficit per plant
and lists every PFT parameter that differs between the focal PFTs (ranked by ratio),
plus the cold-start settings found in the case (use_fates_dbh_init, initial density).

Defaults: the two needleleaf diagnostic re-runs, DE-Hai NORMAL400 (mature broadleaf), and
DE-Hai's AD re-run if it exists (same seedling start as the needleleaf re-runs).

Outputs (<out>/): carbon_budget_summary.csv, parameter_differences.csv,
  CB_09_trajectories.png, CB_10_seasonal.png, CB_11_carbon_use.png, per-case monthly CSVs
Usage
  python -B 11_...py --output-root DIR [--cases LABEL:CASE[:first50|last50|all] ...]
  python -B 11_...py --publish-run DIR
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
FIG_DIR = "figures/AD400_NORMAL400_carbon_budget_diagnostics"
DEFAULT_CASES = ["DE-Obe_NET:DE-Obe_B03_FIXNC_AD400_DIAG50:first50",
                 "FI-Sod_NET:FI-Sod_B01_FIXNC_AD400_DIAG50:first50",
                 "DE-Hai_BDT_seedling:DE-Hai_B01_FIXNC_AD400_DIAG50:first50",
                 "DE-Hai_BDT_mature:DE-Hai_B01_FIXNC_NORMAL400:last50"]
FLUX = ["FATES_GPP", "FATES_NPP", "FATES_AUTORESP", "FATES_MAINT_RESP", "FATES_MAINT_RESP_UNREDUCED",
        "FATES_GROWTH_RESP", "FATES_EXCESS_RESP", "FATES_LEAFMAINTAR", "FATES_FROOTMAINTAR", "FATES_CROOTMAINTAR",
        "FATES_LSTEMMAINTAR", "FATES_LEAF_ALLOC", "FATES_FROOT_ALLOC", "FATES_CROOT_ALLOC", "FATES_STEM_ALLOC",
        "FATES_SAPWOOD_ALLOC", "FATES_STRUCT_ALLOC", "FATES_SEED_ALLOC", "FATES_STORE_ALLOC"]
POOL = ["FATES_LEAFC", "FATES_FROOTC", "FATES_STOREC", "FATES_VEGC", "FATES_SAPWOODC", "FATES_STRUCTC"]
OTHER = ["FATES_STOREC_TF", "FATES_LAI", "TLAI", "FATES_CA_WEIGHTED_HEIGHT", "FATES_MEAN_95PCTILE_HEIGHT", "TSA"]
PF = ["FATES_NPLANT_PF", "FATES_GPP_PF", "FATES_NPP_PF", "FATES_LEAFC_PF", "FATES_STOREC_PF", "FATES_VEGC_PF",
      "FATES_NOCOMP_PATCHAREA_PF", "FATES_CANOPYCROWNAREA_PF", "FATES_RECRUITMENT_PF", "FATES_MORTALITY_PF"]
COLD_START_KEYS = ["use_fates_dbh_init", "use_fates_inventory_init", "use_fates_nocomp", "use_fates_fixed_biogeog",
                   "use_fates_planthydro", "fates_paramfile", "spinup_state"]
KEY_PARAMS = ["fates_leaf_vcmax25top", "fates_leaf_slatop", "fates_leaf_slamax", "fates_turnover_leaf_canopy",
              "fates_alloc_storage_cushion", "fates_alloc_store_priority_frac", "fates_maintresp_leaf_atkin2017_baserate",
              "fates_maintresp_leaf_ryan1991_baserate", "fates_maintresp_nonleaf_baserate", "fates_stoich_nitr",
              "fates_allom_l2fr", "fates_allom_la_per_sa_int", "fates_allom_d2ca_coefficient_max", "fates_wood_density",
              "fates_turnover_fnrt", "fates_grperc", "fates_mort_scalar_cstarvation", "fates_mort_upthresh_cstarvation",
              "fates_mort_bmort", "fates_recruit_init_density", "fates_recruit_init_dbh", "fates_recruit_height_min",
              "fates_recruit_seed_alloc", "fates_recruit_seed_alloc_mature"]
WINTER = (12, 1, 2)
GROW = (6, 7, 8)
SEC_D = 86400.0

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
def _arr(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    dims = list(var.dimensions)
    a = np.moveaxis(a, dims.index("time"), 0)
    return a.reshape(a.shape[0], -1)


def factor(name, units):
    u = (units or "").replace(" ", "").lower()
    if u.startswith("kg") and ("s-1" in u or "/s" in u):
        return 1000.0 * SEC_D                    # -> g C m-2 d-1
    if u.startswith("kg") and "m-2" in u:
        return 1000.0                            # -> g C m-2
    return 1.0


def read_case(case, years, archive):
    from netCDF4 import Dataset
    fidx = P.history_index(archive, case)
    rows, have = [], set()
    for k, y in enumerate(years):
        for path in fidx[y]:
            with Dataset(str(path)) as ds:
                b = next((x for x in ("time_bounds", "time_bnds") if x in ds.variables), None)
                if b is None:
                    raise ValueError(f"{path.name}: no time bounds")
                tb = np.asarray(ds.variables[b][:], dtype=float)
                dur = tb[:, 1] - tb[:, 0]
                dates = P.noleap_dates(ds)
                cols = {}
                for n in FLUX + POOL + OTHER:
                    if n in ds.variables and "time" in ds.variables[n].dimensions:
                        v = ds.variables[n]
                        a = _arr(v)
                        if a.shape[1] == 1:
                            cols[n] = a[:, 0] * factor(n, getattr(v, "units", ""))
                for n in PF:
                    if n in ds.variables:
                        v = ds.variables[n]
                        a = _arr(v) * factor(n, getattr(v, "units", ""))
                        for p in range(a.shape[1]):
                            cols[f"{n}__pft{p + 1}"] = a[:, p]
                have |= {c.split("__")[0] for c in cols}
            for i, (yy, mm, _) in enumerate(dates):
                rows.append({"Year": yy, "Month": mm, "w": dur[i], **{c: float(v[i]) for c, v in cols.items()}})
        if (k + 1) % 25 == 0:
            print(f"    {case}: read {k + 1}/{len(years)} years", flush=True)
    raw = pd.DataFrame(rows)
    num = [c for c in raw.columns if c not in ("Year", "Month", "w")]
    vals = raw[num].to_numpy(float)
    w = raw["w"].to_numpy(float)[:, None]
    ok = np.isfinite(vals)
    g = raw[["Year", "Month"]].reset_index(drop=True)
    S = pd.concat([g, pd.DataFrame(np.where(ok, vals, 0) * w, columns=num)], axis=1).groupby(["Year", "Month"]).sum()
    N = pd.concat([g, pd.DataFrame(ok * w, columns=num)], axis=1).groupby(["Year", "Month"]).sum()
    return (S / N.where(N > 0)).reset_index(), have


def case_namelist(case, args):
    for p in (args.archive_root.parent / case / "run" / "lnd_in", args.cases_root / case / "CaseDocs" / "lnd_in"):
        if p.is_file():
            return p.read_text()
    return ""


def nml_value(text, key):
    m = re.search(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\n!]*)", text)
    return m.group(1).strip().rstrip(",").strip().strip("'\"") if m else None


def read_params(path):
    if not path or not Path(path).is_file():
        return {}, []
    d = json.loads(Path(path).read_text())
    prm = d.get("parameters", d)
    names = [str(x).strip() for x in prm.get("fates_pftname", {}).get("data", [])]
    return prm, names


# ------------------------------------------------------------------ analysis
def focal_pft(df):
    pa = {int(c.split("pft")[1]): float(np.nanmean(df[c])) for c in df.columns if c.startswith("FATES_NOCOMP_PATCHAREA_PF__pft")}
    vc = {int(c.split("pft")[1]): float(np.nanmean(df[c])) for c in df.columns if c.startswith("FATES_VEGC_PF__pft")}
    ref = pa if pa and max(pa.values()) > 0 else vc
    if not ref:
        return None, None
    k = max(ref, key=ref.get)
    return k, (pa.get(k) if pa else None)


def derive(df, k):
    """Per-plant and per-leaf quantities for focal PFT k (site fluxes attributed to k for single-PFT sites)."""
    d = pd.DataFrame({"Year": df["Year"], "Month": df["Month"]})
    n = df.get(f"FATES_NPLANT_PF__pft{k}")
    n = n.where(n > 0) if n is not None else None              # plants m-2
    leafc = df.get(f"FATES_LEAFC_PF__pft{k}", df.get("FATES_LEAFC"))
    gpp = df.get(f"FATES_GPP_PF__pft{k}", df.get("FATES_GPP"))
    npp = df.get(f"FATES_NPP_PF__pft{k}", df.get("FATES_NPP"))
    lai = df.get("FATES_LAI", df.get("TLAI"))
    d["plants_ha"] = n * 1e4 if n is not None else np.nan
    d["LAI"] = lai if lai is not None else np.nan
    for src, dst in ((f"FATES_VEGC_PF__pft{k}", "biomass_gC_plant"), (f"FATES_STOREC_PF__pft{k}", "storage_gC_plant"),
                     (f"FATES_LEAFC_PF__pft{k}", "leafC_gC_plant")):
        d[dst] = df[src] / n if (src in df and n is not None) else np.nan
    for x, dst in ((gpp, "GPP"), (npp, "NPP"), (df.get("FATES_MAINT_RESP"), "MR"), (df.get("FATES_GROWTH_RESP"), "GR")):
        d[f"{dst}_gC_plant_d"] = x / n if (x is not None and n is not None) else np.nan
        d[f"{dst}_per_kgleafC_d"] = x / (leafc / 1000.0) if (x is not None and leafc is not None) else np.nan
        d[f"{dst}_per_m2leaf_d"] = x / lai.where(lai > 1e-6) if (x is not None and lai is not None) else np.nan
    if f"FATES_STOREC_PF__pft{k}" in df and leafc is not None:
        d["storage_to_leafC"] = df[f"FATES_STOREC_PF__pft{k}"] / leafc.where(leafc > 0)
    d["storage_to_target"] = df.get("FATES_STOREC_TF", np.nan)
    crown = df.get(f"FATES_CANOPYCROWNAREA_PF__pft{k}")
    pa = df.get(f"FATES_NOCOMP_PATCHAREA_PF__pft{k}")
    d["canopy_cover"] = np.minimum(crown, pa) if (crown is not None and pa is not None) else (crown if crown is not None else np.nan)
    d["height_m"] = df.get("FATES_CA_WEIGHTED_HEIGHT", np.nan)
    return d


def carbon_use(df):
    """Annual shares of GPP (site level)."""
    m = lambda c: float(np.nanmean(df[c])) if c in df and df[c].notna().any() else np.nan
    gpp = m("FATES_GPP")
    out = {"GPP_gC_m2_d": gpp}
    if not np.isfinite(gpp) or gpp <= 0:
        return out
    stem_mr = np.nansum([m("FATES_LSTEMMAINTAR"), m("FATES_CROOTMAINTAR")])
    parts = {"MR leaf": m("FATES_LEAFMAINTAR"), "MR fine root": m("FATES_FROOTMAINTAR"), "MR stem+coarse root": stem_mr,
             "growth resp.": m("FATES_GROWTH_RESP"), "to leaf": m("FATES_LEAF_ALLOC"), "to fine root": m("FATES_FROOT_ALLOC"),
             "to stem/sapwood/struct": np.nansum([m("FATES_STEM_ALLOC"), m("FATES_SAPWOOD_ALLOC"), m("FATES_STRUCT_ALLOC"),
                                                  m("FATES_CROOT_ALLOC")]),
             "to storage": m("FATES_STORE_ALLOC"), "to seed": m("FATES_SEED_ALLOC")}
    for k, v in parts.items():
        out[f"share_{k}"] = v / gpp if np.isfinite(v) else np.nan
    out["MR_over_GPP"] = m("FATES_MAINT_RESP") / gpp
    out["CUE_NPP_over_GPP"] = m("FATES_NPP") / gpp
    return out


def summarize(label, case, years, df, d, k, area, names, nml, have):
    mon = d["Month"].to_numpy()
    first = d["Year"] < d["Year"].min() + 5
    g = np.isin(mon, GROW)
    w = np.isin(mon, WINTER)
    mean = lambda x, m=None: float(np.nanmean(np.asarray(x, float)[m] if m is not None else np.asarray(x, float))) \
        if np.isfinite(np.asarray(x, float)[m] if m is not None else np.asarray(x, float)).any() else np.nan
    r = {"Label": label, "Case": case, "Years": years, "Focal_PFT": f"{k} {names[k - 1] if k and k - 1 < len(names) else ''}".strip(),
         "Focal_patch_area": area, "Single_PFT_site": bool(area is not None and area >= 0.99)}
    for c in ("plants_ha", "LAI", "canopy_cover", "height_m", "biomass_gC_plant"):
        r[f"{c}_first5y"] = mean(d[c], first.to_numpy())
        r[f"{c}_last5y"] = mean(d[c], (d["Year"] > d["Year"].max() - 5).to_numpy())
    for c in ("GPP_per_kgleafC_d", "MR_per_kgleafC_d", "NPP_per_kgleafC_d", "GPP_per_m2leaf_d", "MR_per_m2leaf_d"):
        r[f"{c}_JJA"] = mean(d[c], g)
        r[f"{c}_DJF"] = mean(d[c], w)
        r[f"{c}_annual"] = mean(d[c])
    r["storage_to_target_min"] = float(np.nanmin(d["storage_to_target"])) if d["storage_to_target"].notna().any() else np.nan
    r["storage_to_leafC_mean"] = mean(d.get("storage_to_leafC", np.nan))
    # winter reserve: storage per plant at end of November / winter deficit per plant (Dec-Feb)
    yrs = sorted(d["Year"].unique())
    ratios = []
    for y in yrs[:-1]:
        st = d[(d.Year == y) & (d.Month == 11)]["storage_gC_plant"]
        wn = d[((d.Year == y) & (d.Month == 12)) | ((d.Year == y + 1) & d.Month.isin((1, 2)))]["NPP_gC_plant_d"]
        if len(st) and len(wn) and np.isfinite(st.iloc[0]) and wn.notna().any():
            deficit = -min(0.0, float(wn.mean())) * 90.0
            if deficit > 0:
                ratios.append(float(st.iloc[0]) / deficit)
    r["winter_reserve_ratio_median"] = float(np.median(ratios)) if ratios else np.nan
    r.update(carbon_use(df))
    for key in COLD_START_KEYS:
        r[f"nml_{key}"] = nml_value(nml, key) if nml else None
    r["use_fates_dbh_init_option_present"] = bool(nml and nml_value(nml, "use_fates_dbh_init") is not None)
    r["Variables_missing"] = ", ".join(sorted(set(FLUX + POOL + OTHER + PF) - have))
    return r


def param_differences(prm, names, pfts):
    """Rows for PFT-dimension parameters whose values differ between the focal PFTs."""
    npft = len(names)
    rows = []
    for key, ent in prm.items():
        if not isinstance(ent, dict) or "data" not in ent:
            continue
        try:
            a = np.asarray(ent["data"], dtype=float)
        except (TypeError, ValueError):
            continue
        dims = ent.get("dims") or []
        if npft == 0 or a.ndim == 0 or npft not in a.shape:
            continue
        ax = list(a.shape).index(npft) if "fates_pft" not in dims else dims.index("fates_pft")
        a = np.moveaxis(a, ax, -1).reshape(-1, npft)
        vals = {p: a[:, p - 1] for p in pfts if p and p - 1 < npft}
        if len(vals) < 2:
            continue
        ref = vals[pfts[0]]
        diff = 0.0
        for p, v in vals.items():
            with np.errstate(divide="ignore", invalid="ignore"):
                rr = np.abs(np.log10(np.abs(v) / np.abs(ref)))
            rr = rr[np.isfinite(rr)]
            d = float(rr.max()) if rr.size else (0.0 if np.allclose(v, ref, equal_nan=True) else np.inf)
            diff = max(diff, d)
        if diff == 0 or (np.isfinite(diff) and diff < 1e-6):
            continue
        rows.append({"parameter": key, "max_abs_log10_ratio": diff, "key_parameter": key in KEY_PARAMS,
                     "units": ent.get("units", ""), "long_name": ent.get("long_name", "")[:120],
                     **{f"PFT{p} {names[p - 1]}": " ".join(f"{x:.4g}" for x in v[:6]) for p, v in vals.items()}})
    rows.sort(key=lambda r: (not r["key_parameter"], -(r["max_abs_log10_ratio"] if np.isfinite(r["max_abs_log10_ratio"]) else 99)))
    return rows


# ------------------------------------------------------------------ plots
def plots(root, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ok = [x for x in res if x.get("d") is not None]
    if not ok:
        return
    cmap = plt.get_cmap("tab10")
    # trajectories
    tr = [("biomass_gC_plant", "Biomass per plant (g C, log)", True), ("plants_ha", "Plants per ha (log)", True),
          ("LAI", "LAI (m2 m-2)", False), ("canopy_cover", "Canopy cover (fraction of ground)", False),
          ("height_m", "Crown-area-weighted height (m)", False), ("storage_to_target", "Storage / target", False)]
    fig, axs = plt.subplots(2, 3, figsize=(18, 9))
    for ax, (c, t, lg) in zip(axs.flat, tr):
        for i, x in enumerate(ok):
            a = x["d"].groupby("Year")[c].mean()
            yy = a.index - a.index.min() + 1
            v = a.to_numpy(float)
            if lg:
                v = np.where(v > 0, v, np.nan)
            ax.plot(yy, v, color=cmap(i), lw=1.4, label=x["label"])
        if lg:
            ax.set_yscale("log")
        ax.set_title(t, loc="left"); ax.grid(alpha=0.25); ax.set_xlabel("year of window")
    axs.flat[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Stand and per-plant trajectories (annual means)", fontsize=12)
    fig.tight_layout(); fig.savefig(root / "CB_09_trajectories.png", dpi=140, bbox_inches="tight"); plt.close(fig)
    # seasonal per leaf / per plant
    se = [("GPP_per_kgleafC_d", "GPP per kg leaf C (g C d-1)"), ("MR_per_kgleafC_d", "Maintenance resp. per kg leaf C"),
          ("NPP_per_kgleafC_d", "NPP per kg leaf C"), ("GPP_per_m2leaf_d", "GPP per m2 leaf (g C d-1)"),
          ("NPP_gC_plant_d", "NPP per plant (g C d-1)"), ("storage_gC_plant", "Storage per plant (g C)")]
    fig, axs = plt.subplots(2, 3, figsize=(18, 9))
    for ax, (c, t) in zip(axs.flat, se):
        for i, x in enumerate(ok):
            a = x["d"].groupby("Month")[c].mean()
            ax.plot(a.index, a.values, color=cmap(i), marker="o", ms=3, lw=1.3, label=x["label"])
        ax.axhline(0, color="0.6", lw=0.6); ax.set_title(t, loc="left"); ax.grid(alpha=0.25); ax.set_xlabel("month")
    axs.flat[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Seasonal carbon budget (monthly climatology over each window)", fontsize=12)
    fig.tight_layout(); fig.savefig(root / "CB_10_seasonal.png", dpi=140, bbox_inches="tight"); plt.close(fig)
    # carbon use stacked bars
    keys = ["MR leaf", "MR fine root", "MR stem+coarse root", "growth resp.", "to leaf", "to fine root",
            "to stem/sapwood/struct", "to storage", "to seed"]
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, x in enumerate(ok):
        bottom = 0.0
        for j, k in enumerate(keys):
            v = x["r"].get(f"share_{k}", np.nan)
            v = 0.0 if not np.isfinite(v) else v
            ax.bar(i, v, bottom=bottom, color=plt.get_cmap("tab10")(j % 10), label=k if i == 0 else None)
            bottom += v
    ax.axhline(1, color="k", lw=0.8, ls=":")
    ax.set_xticks(range(len(ok))); ax.set_xticklabels([x["label"] for x in ok], rotation=15)
    ax.set_ylabel("fraction of GPP (window mean)"); ax.legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.set_title("Where GPP goes: maintenance / growth respiration and allocation")
    fig.tight_layout(); fig.savefig(root / "CB_11_carbon_use.png", dpi=140, bbox_inches="tight"); plt.close(fig)


# ------------------------------------------------------------------ driver
def process(spec, args):
    p = spec.split(":")
    label, case, which = p[0], p[1], (p[2] if len(p) > 2 else "first50")
    rec = {"Label": label, "Case": case, "Status": "FAILED"}
    try:
        fidx = P.history_index(args.archive_root, case)
        y0 = int(P.env_value(args.cases_root / case, "RUN_STARTDATE")[:4])
        yrs = P.contiguous(fidx, y0, 10 ** 6) or sorted(fidx)
        yrs = yrs if which == "all" else (yrs[:args.years] if which == "first50" else yrs[-args.years:])
        print(f"[{label}] {case}: years {yrs[0]}-{yrs[-1]} ({len(yrs)})", flush=True)
        df, have = read_case(case, yrs, args.archive_root)
        nml = case_namelist(case, args)
        pf = nml_value(nml, "fates_paramfile")
        prm, names = read_params(pf)
        k, area = focal_pft(df)
        d = derive(df, k)
        r = summarize(label, case, f"{yrs[0]}-{yrs[-1]}", df, d, k, area, names, nml, have)
        rec.update(r, Status="OK")
        out = args.output_root / label
        out.mkdir(parents=True, exist_ok=True)
        d.to_csv(out / f"{label}_carbon_budget_monthly.csv", index=False)
        return rec, {"label": label, "d": d, "r": r, "pft": k, "prm": prm, "names": names}
    except Exception as exc:
        rec["Error"] = f"{type(exc).__name__}: {exc}"
        (args.output_root / f"{label}_ERROR.txt").write_text(traceback.format_exc())
        print(f"[{label}] SKIPPED/FAILED: {rec['Error']}", flush=True)
        return rec, {"label": label, "d": None}


def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    recs, res = [], []
    for s in a.cases:
        r, x = process(s, a)
        recs.append(r); res.append(x)
    first = ["Label", "Status", "Case", "Years", "Focal_PFT", "Single_PFT_site", "plants_ha_first5y", "plants_ha_last5y",
             "biomass_gC_plant_first5y", "biomass_gC_plant_last5y", "LAI_last5y", "canopy_cover_last5y",
             "GPP_per_kgleafC_d_JJA", "MR_per_kgleafC_d_JJA", "MR_per_kgleafC_d_DJF", "NPP_per_kgleafC_d_annual",
             "GPP_per_m2leaf_d_JJA", "MR_over_GPP", "CUE_NPP_over_GPP", "storage_to_target_min", "storage_to_leafC_mean",
             "winter_reserve_ratio_median", "nml_use_fates_dbh_init", "use_fates_dbh_init_option_present", "Error"]
    fields = first + sorted({k for r in recs for k in r} - set(first))
    with (a.output_root / "carbon_budget_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in recs:
            w.writerow(r)
    okres = [x for x in res if x.get("d") is not None]
    if okres:
        prm, names = next(((x["prm"], x["names"]) for x in okres if x["prm"]), ({}, []))
        pfts = list(dict.fromkeys(x["pft"] for x in okres if x["pft"]))
        rows = param_differences(prm, names, pfts) if prm and len(pfts) >= 2 else []
        if rows:
            cols = list(dict.fromkeys(k for r in rows for k in r))
            with (a.output_root / "parameter_differences.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
                for r in rows:
                    w.writerow(r)
            print(f"\nParameters that differ between PFTs {pfts} (key parameters first):", flush=True)
            for r in rows[:25]:
                vals = " | ".join(f"{k.split(' ')[0]}={v}" for k, v in r.items() if k.startswith("PFT"))
                print(f"  {r['parameter']:42s} {vals}", flush=True)
        plots(a.output_root, res)
    f3 = lambda r, k: f"{r[k]:.3g}" if isinstance(r.get(k), (float, int)) and np.isfinite(r[k]) else "–"
    print("", flush=True)
    for r in recs:
        print(f"== {r['Label']}: {r['Status']} | PFT {r.get('Focal_PFT', '')} | plants/ha {f3(r, 'plants_ha_first5y')}→{f3(r, 'plants_ha_last5y')} "
              f"| g C/plant {f3(r, 'biomass_gC_plant_first5y')}→{f3(r, 'biomass_gC_plant_last5y')} | GPP/kg leafC JJA {f3(r, 'GPP_per_kgleafC_d_JJA')} "
              f"| MR/kg leafC JJA {f3(r, 'MR_per_kgleafC_d_JJA')} DJF {f3(r, 'MR_per_kgleafC_d_DJF')} | MR/GPP {f3(r, 'MR_over_GPP')} "
              f"| CUE {f3(r, 'CUE_NPP_over_GPP')} | winter reserve {f3(r, 'winter_reserve_ratio_median')} "
              f"| dbh_init {r.get('nml_use_fates_dbh_init')} {r.get('Error', '')}", flush=True)
    ok = sum(r["Status"] == "OK" for r in recs)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(recs), "cases": a.cases, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(recs)} cases (missing cases are skipped). Summary: {a.output_root / 'carbon_budget_summary.csv'}", flush=True)
    return 0 if ok >= 2 else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    with (run_dir / "carbon_budget_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    fmt = lambda v: f"{float(v):.3g}" if v not in (None, "", "None") and np.isfinite(float(v)) else "–"
    with tempfile.TemporaryDirectory(prefix="cb_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        for n in ("carbon_budget_summary.csv", "parameter_differences.csv"):
            if (run_dir / n).is_file():
                shutil.copyfile(run_dir / n, out / n)
        lines = ["# Carbon budget diagnostics: why the needleleaf PFT cannot grow", "",
                 "Per-plant and per-leaf carbon budget for single-PFT nocomp sites, carbon use shares, winter reserve,",
                 "and the PFT parameters that differ between the focal PFTs. Screening numbers from history output.", ""]
        for n in ("CB_09_trajectories.png", "CB_10_seasonal.png", "CB_11_carbon_use.png"):
            p = run_dir / n
            if p.is_file() and F7.is_png(p):
                shutil.copyfile(p, out / n); lines.append(f"- [{n}]({n})")
        if (out / "parameter_differences.csv").is_file():
            lines.append("- [parameter_differences.csv](parameter_differences.csv)")
        lines += ["", "| Case | PFT | plants/ha (first→last 5 y) | g C/plant | GPP/kg leaf C JJA | MR/kg leaf C JJA / DJF | MR/GPP | CUE | winter reserve | dbh_init |",
                  "| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |"]
        for r in rows:
            c = lambda k: (r.get(k) or "").replace("|", "/")
            lines.append(f"| {c('Label')} ({c('Case')}) | {c('Focal_PFT')} | {fmt(r.get('plants_ha_first5y'))} → {fmt(r.get('plants_ha_last5y'))} | "
                         f"{fmt(r.get('biomass_gC_plant_first5y'))} → {fmt(r.get('biomass_gC_plant_last5y'))} | {fmt(r.get('GPP_per_kgleafC_d_JJA'))} | "
                         f"{fmt(r.get('MR_per_kgleafC_d_JJA'))} / {fmt(r.get('MR_per_kgleafC_d_DJF'))} | {fmt(r.get('MR_over_GPP'))} | "
                         f"{fmt(r.get('CUE_NPP_over_GPP'))} | {fmt(r.get('winter_reserve_ratio_median'))} | {c('nml_use_fates_dbh_init') or c('Error')[:60]} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add carbon budget diagnostics ({len(rows)} cases)", cwd=co)
        sha = F7.git("rev-parse", "HEAD", cwd=co)
        F7.git("push", "origin", "HEAD:main", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish-run", type=Path)
    ap.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    ap.add_argument("--years", type=int, default=50)
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
