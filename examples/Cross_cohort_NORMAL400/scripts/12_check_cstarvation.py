#!/usr/bin/env python3
"""Check that FATES' carbon-starvation formula explains the needleleaf mortality.  Read-only.

FATES (EDMortalityFunctionsMod) sets, per cohort and day,
    linear:       cmort = mort_scalar_cstarvation * max(0, (upthresh - frac) / upthresh)
    exponential:  cmort = mort_scalar_cstarvation * exp(-frac / upthresh)
with frac = storage C / fully flushed target leaf C (bleaf), NOT storage / storage target.
Storage is capped near alloc_storage_cushion x leaf C (default 1.2), so an evergreen that
draws storage down by more than 0.2 x leaf C in winter starts dying.

For each case this compares, month by month for the focal PFT,
    observed  = FATES_MORTALITY_CSTARV_SZPF (summed to the PFT) / FATES_NPLANT_PF   [yr-1]
    predicted = the formula above with frac from FATES_STOREC_PF / FATES_LEAFC_PF,
                and alternatively frac = FATES_STOREC_TF x alloc_storage_cushion
(monthly means of a daily, per-cohort process, so expect agreement in timing and size,
not exact equality). Actual leaf C stands in for the flushed leaf target, which is valid for
evergreen PFTs; for deciduous PFTs leaf-off months (leaf C ~ 0) carry no prediction. It reports the namelist settings actually used
(fates_cstarvation_model, fates_leafresp_model, use_fates_dbh_init, ...) and the PFT's
relevant parameters.

Outputs (<out>/): cstarvation_check_summary.csv, CS_12_<label>.png, CS_12_all_cases_scatter.png
Usage
  python -B 12_...py --output-root DIR [--cases LABEL:CASE[:first50|last50|all] ...]
  python -B 12_...py --publish-run DIR
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
FIG_DIR = "figures/AD400_NORMAL400_cstarvation_check"
DEFAULT_CASES = ["DE-Obe_NET:DE-Obe_B03_FIXNC_AD400_DIAG50:first50",
                 "FI-Sod_NET:FI-Sod_B01_FIXNC_AD400_DIAG50:first50",
                 "DE-Hai_BDT_mature:DE-Hai_B01_FIXNC_NORMAL400:last50"]
NML_KEYS = ["fates_cstarvation_model", "fates_leafresp_model", "use_fates_dbh_init", "use_fates_planthydro",
            "use_fates_nocomp", "use_fates_fixed_biogeog", "fates_history_dimlevel", "spinup_state", "fates_paramfile"]
PARAMS = ["fates_mort_scalar_cstarvation", "fates_mort_upthresh_cstarvation", "fates_alloc_storage_cushion",
          "fates_alloc_store_priority_frac", "fates_leaf_slatop", "fates_turnover_leaf_canopy", "fates_allom_l2fr",
          "fates_maintresp_leaf_ryan1991_baserate", "fates_maintresp_leaf_atkin2017_baserate",
          "fates_maintresp_reduction_intercept", "fates_maintresp_reduction_curvature",
          "fates_maintresp_reduction_upthresh", "fates_stoich_nitr", "fates_mort_bmort", "fates_mort_freezetol"]
VARS_PF = ["FATES_NPLANT_PF", "FATES_STOREC_PF", "FATES_LEAFC_PF", "FATES_VEGC_PF", "FATES_NOCOMP_PATCHAREA_PF"]
VARS_SZPF = ["FATES_MORTALITY_CSTARV_SZPF"]
VARS_SITE = ["FATES_STOREC_TF", "FATES_MORTALITY_CSTARV_SZ", "FATES_STOREC", "FATES_LEAFC"]

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


def _arr(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    dims = list(var.dimensions)
    a = np.moveaxis(a, dims.index("time"), 0)
    return a.reshape(a.shape[0], -1)


def pft_map(ds, n):
    if "fates_pftmap_levscpf" in ds.variables:
        m = np.asarray(ds.variables["fates_pftmap_levscpf"][:], dtype=int).ravel()
        if m.size == n:
            return m
    nscls = len(ds.dimensions["fates_levscls"]) if "fates_levscls" in ds.dimensions else None
    if not nscls or n % nscls:
        raise ValueError(f"cannot map fates_levscpf ({n}) to PFTs")
    return np.arange(n) // nscls + 1


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
                for n in VARS_SITE:
                    if n in ds.variables:
                        a = _arr(ds.variables[n])
                        cols[n] = a[:, 0] if a.shape[1] == 1 else np.nansum(a, axis=1)
                        have.add(n)
                for n in VARS_PF:
                    if n in ds.variables:
                        a = _arr(ds.variables[n])
                        for p in range(a.shape[1]):
                            cols[f"{n}__pft{p + 1}"] = a[:, p]
                        have.add(n)
                for n in VARS_SZPF:
                    if n in ds.variables:
                        a = _arr(ds.variables[n])
                        pm = pft_map(ds, a.shape[1])
                        for p in range(1, int(pm.max()) + 1):
                            cols[f"{n}__pft{p}"] = np.nansum(a[:, pm == p], axis=1)
                        have.add(n)
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


def lnd_in(case, args):
    for p in (args.archive_root.parent / case / "run" / "lnd_in", args.cases_root / case / "CaseDocs" / "lnd_in"):
        if p.is_file():
            return p.read_text()
    return ""


def nml_value(text, key):
    m = re.search(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\n!]*)", text)
    return m.group(1).strip().rstrip(",").strip().strip("'\"") if m else None


def pft_param(prm, key, k):
    ent = prm.get(key)
    if not isinstance(ent, dict):
        return None
    a = np.asarray(ent.get("data"), dtype=float)
    if a.ndim == 0:
        return float(a)
    names = prm.get("fates_pftname", {}).get("data", [])
    npft = len(names)
    if npft in a.shape:
        a = np.moveaxis(a, list(a.shape).index(npft), -1).reshape(-1, npft)[:, k - 1]
        return float(a[0]) if a.size == 1 else a.tolist()
    return a.ravel().tolist() if a.size > 1 else float(a.ravel()[0])


def predict(frac, scalar, upth, model):
    frac = np.asarray(frac, float)
    if model == "exponential":
        return scalar * np.exp(-frac / upth)
    return scalar * np.clip((upth - frac) / upth, 0, None)


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
        nml = lnd_in(case, args)
        settings = {k: nml_value(nml, k) for k in NML_KEYS}
        pf = settings.get("fates_paramfile")
        prm = json.loads(Path(pf).read_text()).get("parameters", {}) if pf and Path(pf).is_file() and pf.endswith(".json") else {}
        names = [str(x).strip() for x in prm.get("fates_pftname", {}).get("data", [])]
        pa = {int(c.split("pft")[1]): float(np.nanmean(df[c])) for c in df.columns if c.startswith("FATES_NOCOMP_PATCHAREA_PF__pft")}
        vc = {int(c.split("pft")[1]): float(np.nanmean(df[c])) for c in df.columns if c.startswith("FATES_VEGC_PF__pft")}
        ref = pa if pa and max(pa.values()) > 0 else vc
        k = max(ref, key=ref.get)
        pars = {key: pft_param(prm, key, k) for key in PARAMS}
        model = (settings.get("fates_cstarvation_model") or "linear").lower()
        scalar = pars.get("fates_mort_scalar_cstarvation") or 0.6
        upth = pars.get("fates_mort_upthresh_cstarvation") or 1.0
        cushion = pars.get("fates_alloc_storage_cushion") or 1.2
        n = df.get(f"FATES_NPLANT_PF__pft{k}")
        n = n.where(n > 0)
        obs_col = f"FATES_MORTALITY_CSTARV_SZPF__pft{k}"
        if obs_col in df:
            obs = df[obs_col] / n
            obs_src = "FATES_MORTALITY_CSTARV_SZPF (focal PFT) / FATES_NPLANT_PF"
        elif "FATES_MORTALITY_CSTARV_SZ" in df:
            tot = df[[c for c in df.columns if c.startswith("FATES_NPLANT_PF__pft")]].sum(axis=1)
            obs = df["FATES_MORTALITY_CSTARV_SZ"] / tot.where(tot > 0)
            obs_src = "FATES_MORTALITY_CSTARV_SZ (all PFTs) / total plants"
        else:
            raise RuntimeError("no carbon-starvation mortality in history output")
        frac_leaf = df[f"FATES_STOREC_PF__pft{k}"] / df[f"FATES_LEAFC_PF__pft{k}"].where(df[f"FATES_LEAFC_PF__pft{k}"] > 0)
        frac_tf = df["FATES_STOREC_TF"] * cushion if "FATES_STOREC_TF" in df else pd.Series(np.nan, index=df.index)
        out = pd.DataFrame({"Year": df.Year, "Month": df.Month, "observed_cstarv_yr": obs,
                            "frac_store_over_leafC": frac_leaf, "frac_from_STOREC_TF": frac_tf,
                            "predicted_from_leafC_yr": predict(frac_leaf, scalar, upth, model),
                            "predicted_from_TF_yr": predict(frac_tf, scalar, upth, model)})
        alive = n.notna() & (n * 1e4 >= 1.0)            # at least 1 plant/ha: rates of near-extinct stands are noise
        rec.update(Status="OK", Years=f"{yrs[0]}-{yrs[-1]}", Focal_PFT=f"{k} {names[k - 1] if k - 1 < len(names) else ''}".strip(),
                   Observed_source=obs_src, Months_used=int(alive.sum()),
                   **{f"nml_{kk}": v for kk, v in settings.items()},
                   **{f"param_{kk}": (json.dumps(v) if isinstance(v, list) else v) for kk, v in pars.items()})
        for col in ("predicted_from_leafC_yr", "predicted_from_TF_yr"):
            a, b = out.loc[alive, "observed_cstarv_yr"].to_numpy(float), out.loc[alive, col].to_numpy(float)
            ok = np.isfinite(a) & np.isfinite(b)
            tag = col.replace("predicted_from_", "").replace("_yr", "")
            if ok.sum() >= 12:
                rec[f"r_{tag}"] = float(np.corrcoef(a[ok], b[ok])[0, 1]) if np.std(a[ok]) > 0 and np.std(b[ok]) > 0 else np.nan
                rec[f"mean_pred_{tag}_yr"] = float(np.mean(b[ok]))
                rec[f"slope_obs_vs_pred_{tag}"] = float(np.sum(a[ok] * b[ok]) / np.sum(b[ok] ** 2)) if np.sum(b[ok] ** 2) > 0 else np.nan
        o = out.loc[alive, "observed_cstarv_yr"]
        rec["mean_observed_yr"] = float(o.mean()) if o.notna().any() else np.nan
        rec["max_observed_yr"] = float(o.max()) if o.notna().any() else np.nan
        fl = out.loc[alive, "frac_store_over_leafC"]
        rec["share_months_frac_below_upthresh"] = float((fl < upth).mean()) if fl.notna().any() else np.nan
        rec["frac_min"] = float(fl.min()) if fl.notna().any() else np.nan
        rec["frac_mean"] = float(fl.mean()) if fl.notna().any() else np.nan
        dm = out.loc[alive].groupby("Month")["frac_store_over_leafC"].mean()
        rec["frac_by_month"] = " ".join(f"{int(m)}:{v:.2f}" for m, v in dm.items())
        rec["Variables_found"] = ", ".join(sorted(have))
        d = args.output_root / label
        d.mkdir(parents=True, exist_ok=True)
        out.to_csv(d / f"{label}_cstarvation_monthly.csv", index=False)
        plot_case(args.output_root, label, case, out, alive, upth, cushion, model, scalar, rec)
        return rec, {"label": label, "out": out, "alive": alive}
    except Exception as exc:
        rec["Error"] = f"{type(exc).__name__}: {exc}"
        (args.output_root / f"{label}_ERROR.txt").write_text(traceback.format_exc())
        print(f"[{label}] FAILED: {rec['Error']}", flush=True)
        return rec, {"label": label, "out": None}


def plot_case(root, label, case, out, alive, upth, cushion, model, scalar, r):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = (out.Year - out.Year.min() + (out.Month - 0.5) / 12).to_numpy(float)
    m = (x < 20)
    fig, axs = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
    axs[0].plot(x[m], out["frac_store_over_leafC"][m], color="tab:purple", lw=1.2, label="storage / leaf C (STOREC_PF / LEAFC_PF)")
    axs[0].plot(x[m], out["frac_from_STOREC_TF"][m], color="tab:purple", lw=0.8, ls=":", label=f"STOREC_TF × cushion ({cushion})")
    axs[0].axhline(upth, color="tab:red", ls="--", lw=1, label=f"mortality threshold upthresh = {upth}")
    axs[0].axhline(cushion, color="tab:green", ls="--", lw=1, label=f"storage cap ≈ cushion = {cushion}")
    axs[0].set_ylabel("ratio"); axs[0].legend(frameon=False, fontsize=8, loc="upper right")
    axs[0].set_title("Storage relative to leaf carbon (what FATES compares to the threshold)", loc="left")
    axs[1].plot(x[m], out["observed_cstarv_yr"][m] * 100, color="k", lw=1.2, label="observed (history)")
    axs[1].plot(x[m], out["predicted_from_leafC_yr"][m] * 100, color="tab:red", lw=1, ls="--", label="predicted from storage / leaf C")
    axs[1].plot(x[m], out["predicted_from_TF_yr"][m] * 100, color="tab:orange", lw=0.8, ls=":", label="predicted from STOREC_TF")
    axs[1].set_ylabel("% of plants yr-1"); axs[1].legend(frameon=False, fontsize=8, loc="upper right")
    axs[1].set_title(f"Carbon-starvation mortality: observed vs {model} formula (scalar {scalar}/yr)", loc="left")
    clim = out[alive].groupby("Month")[["observed_cstarv_yr", "predicted_from_leafC_yr", "frac_store_over_leafC"]].mean()
    axs[2].set_visible(False)
    ax = fig.add_subplot(3, 2, 5)
    ax.plot(clim.index, clim["observed_cstarv_yr"] * 100, "k-o", ms=3, label="observed")
    ax.plot(clim.index, clim["predicted_from_leafC_yr"] * 100, "r--o", ms=3, label="predicted")
    ax.set_xlabel("month"); ax.set_ylabel("% yr-1"); ax.set_title("Monthly climatology", loc="left"); ax.legend(frameon=False, fontsize=8)
    ax2 = fig.add_subplot(3, 2, 6)
    a, b = out.loc[alive, "predicted_from_leafC_yr"] * 100, out.loc[alive, "observed_cstarv_yr"] * 100
    ax2.scatter(a, b, s=6, alpha=0.5)
    lim = np.nanmax([a.max(), b.max(), 1])
    ax2.plot([0, lim], [0, lim], color="0.5", ls=":")
    ax2.set_xlabel("predicted % yr-1"); ax2.set_ylabel("observed % yr-1")
    ax2.set_title(f"All months (r = {r.get('r_leafC', np.nan):.2f}, slope = {r.get('slope_obs_vs_pred_leafC', np.nan):.2f})", loc="left")
    axs[1].set_xlabel("years from start (first 20 shown)")
    fig.suptitle(f"{label} | {case} | focal PFT {r.get('Focal_PFT', '')}\n"
                 f"fates_cstarvation_model = {r.get('nml_fates_cstarvation_model') or 'not in lnd_in (default linear)'} | "
                 f"fates_leafresp_model = {r.get('nml_fates_leafresp_model') or 'n/a'} | storage below threshold in "
                 f"{100 * r.get('share_months_frac_below_upthresh', np.nan):.0f}% of months", fontsize=11)
    fig.tight_layout()
    fig.savefig(root / f"CS_12_{label}.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    recs, res = [], []
    for s in a.cases:
        r, x = process(s, a)
        recs.append(r); res.append(x)
    first = ["Label", "Status", "Case", "Years", "Focal_PFT", "r_leafC", "slope_obs_vs_pred_leafC", "mean_observed_yr",
             "mean_pred_leafC_yr", "max_observed_yr", "share_months_frac_below_upthresh", "frac_min", "frac_mean",
             "frac_by_month", "r_TF", "slope_obs_vs_pred_TF", "nml_fates_cstarvation_model", "nml_fates_leafresp_model",
             "nml_use_fates_dbh_init", "param_fates_mort_scalar_cstarvation", "param_fates_mort_upthresh_cstarvation",
             "param_fates_alloc_storage_cushion", "param_fates_leaf_slatop", "Observed_source", "Error"]
    fields = first + sorted({k for r in recs for k in r} - set(first))
    with (a.output_root / "cstarvation_check_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in recs:
            w.writerow(r)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 6))
    for i, x in enumerate(res):
        if x.get("out") is None:
            continue
        o = x["out"][x["alive"]]
        ax.scatter(o["predicted_from_leafC_yr"] * 100, o["observed_cstarv_yr"] * 100, s=6, alpha=0.5, label=x["label"])
    ax.plot([0, 60], [0, 60], color="0.5", ls=":")
    ax.set_xlabel("predicted carbon-starvation mortality (% yr-1)"); ax.set_ylabel("observed (% yr-1)")
    ax.legend(frameon=False); ax.set_title("FATES carbon-starvation formula vs history output (monthly)")
    fig.tight_layout(); fig.savefig(a.output_root / "CS_12_all_cases_scatter.png", dpi=140); plt.close(fig)
    f3 = lambda r, k: f"{r[k]:.3g}" if isinstance(r.get(k), (int, float)) and np.isfinite(r[k]) else "–"
    print("", flush=True)
    for r in recs:
        print(f"== {r['Label']}: {r['Status']} | PFT {r.get('Focal_PFT', '')} | observed mean {f3(r, 'mean_observed_yr')}/yr "
              f"(max {f3(r, 'max_observed_yr')}) | predicted mean {f3(r, 'mean_pred_leafC_yr')}/yr | r {f3(r, 'r_leafC')} "
              f"slope {f3(r, 'slope_obs_vs_pred_leafC')} | storage/leafC min {f3(r, 'frac_min')} mean {f3(r, 'frac_mean')}, "
              f"below threshold {f3(r, 'share_months_frac_below_upthresh')} of months | cstarv model {r.get('nml_fates_cstarvation_model')} "
              f"| leafresp {r.get('nml_fates_leafresp_model')} | dbh_init {r.get('nml_use_fates_dbh_init')} {r.get('Error', '')}", flush=True)
        if r.get("frac_by_month"):
            print(f"   storage/leafC by month: {r['frac_by_month']}", flush=True)
    ok = sum(r["Status"] == "OK" for r in recs)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(recs), "cases": a.cases, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(recs)}. Summary: {a.output_root / 'cstarvation_check_summary.csv'}", flush=True)
    return 0 if ok == len(recs) else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    with (run_dir / "cstarvation_check_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    fmt = lambda v: f"{float(v):.3g}" if v not in (None, "", "None") and np.isfinite(float(v)) else "–"
    with tempfile.TemporaryDirectory(prefix="cs_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        shutil.copyfile(run_dir / "cstarvation_check_summary.csv", out / "cstarvation_check_summary.csv")
        lines = ["# Carbon-starvation check: FATES formula vs history output", "",
                 "cmort = scalar × max(0, (upthresh − storage/leafC) / upthresh) (linear model); monthly means of a daily, "
                 "per-cohort process, so timing and size should agree, not exact values.", ""]
        for p in sorted(run_dir.glob("CS_12_*.png")):
            if F7.is_png(p):
                shutil.copyfile(p, out / p.name); lines.append(f"- [{p.name}]({p.name})")
        lines += ["", "| Case | PFT | observed mean (yr-1) | predicted mean | r | slope | storage/leafC min / mean | months below threshold | cstarv model | leafresp model |",
                  "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |"]
        for r in rows:
            c = lambda k: (r.get(k) or "").replace("|", "/")
            lines.append(f"| {c('Label')} | {c('Focal_PFT')} | {fmt(r.get('mean_observed_yr'))} | {fmt(r.get('mean_pred_leafC_yr'))} | "
                         f"{fmt(r.get('r_leafC'))} | {fmt(r.get('slope_obs_vs_pred_leafC'))} | {fmt(r.get('frac_min'))} / {fmt(r.get('frac_mean'))} | "
                         f"{fmt(r.get('share_months_frac_below_upthresh'))} | {c('nml_fates_cstarvation_model')} | {c('nml_fates_leafresp_model') or c('Error')[:60]} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add carbon-starvation check ({len(rows)} cases)", cwd=co)
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
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
