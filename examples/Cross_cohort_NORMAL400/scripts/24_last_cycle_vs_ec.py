#!/usr/bin/env python3
"""Last forcing cycle of each new Normal400 against the EC tower: monthly GPP / NEE, seasonal cycle, 1:1 scatter.

Same reading and EC rules as the Stage15 monthly overview (plot.py = examples/Batch03_10/scripts/
15_plot_AD400_NORMAL400_convergence_and_EC.py): the LAST COMPLETE forcing cycle of the Normal400 is mapped onto
the EC observation years with the DATM year_first / year_last / year_align; EC GPP = GPP_NT_VUT_REF, DT only where
a source has no NT; EC NEE = NEE_VUT_REF; model NEE = -FATES_NEP; a month counts when it has >= --min-days EC days;
g C m-2 d-1. Normal phase, so NEE is comparable too (no accelerated soil pools).

Per site, when the ORIGINAL Normal400 (default parameters / unpatched; the new name without its _NLF / _NLFP /
_PHEN / _HINONE suffix) still has its history archived, its own last complete cycle is drawn as "before".

Outputs (never under scratch):
  <out>/<site>/<site>_last_cycle_GPP_NEE_vs_EC.png      monthly series, seasonal cycle, scatter (GPP and NEE)
  <out>/<site>/<site>_last_cycle_monthly_vs_EC.csv      paired monthly values (EC values: not published)
  <out>/ALL_SITES_last_cycle_GPP_seasonal_cycle.png, ALL_SITES_last_cycle_NEE_seasonal_cycle.png
  <out>/ALL_SITES_last_cycle_mean_vs_EC.png             mean GPP / NEE per site, model vs EC
  <out>/last_cycle_metrics.csv, RUN_COMPLETE.json
Usage (login node), plot.py beside this file or --plot-module:
  python -B 24_last_cycle_vs_ec.py --pairs-file <plot_done output>/pairs.txt --output-root <plot_done output>/last_cycle_EC
  python -B 24_last_cycle_vs_ec.py --pairs SITE:AD:NORMAL ... --output-root DIR
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
USER = "ly3n24"
SUFFIX = re.compile(r"_(NLF|NLFP|PHEN|HINONE)$")
STYLE = {"EC": dict(color="k", lw=1.8), "new": dict(color="tab:red", lw=1.6),
         "old": dict(color="0.55", lw=1.1, ls="--")}
LABEL = {"new": "FATES Normal400 (new)", "old": "FATES Normal400 before fix"}
P = None


def load_plot(path=None):
    global P
    cands = [Path(path)] if path else [HERE / "plot.py",
                                       HERE.parents[1] / "Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py"]
    for c in cands:
        if c.is_file():
            spec = importlib.util.spec_from_file_location("stage15", c)
            P = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(P)
            return c
    raise FileNotFoundError("Stage15 module not found: " + ", ".join(map(str, cands)))


def metrics(mon, flux, col):
    sc = P.metrics(mon[f"EC_{flux}"], mon[col])
    ok = mon[[f"EC_{flux}", col]].dropna()
    sc["Mean_EC"] = float(ok[f"EC_{flux}"].mean()) if len(ok) else np.nan
    sc["Mean_model"] = float(ok[col].mean()) if len(ok) else np.nan
    sc["Ratio"] = sc["Mean_model"] / sc["Mean_EC"] if flux == "GPP" and sc["Mean_EC"] > 1e-9 else np.nan
    return sc


def seasonal(mon, col, paired_with=None):
    x = mon.dropna(subset=[col] + ([paired_with] if paired_with else [])).copy()
    x["m"] = pd.to_datetime(x["date"]).dt.month
    return x.groupby("m")[col].mean().reindex(range(1, 13))


def model_monthly(case, run_dir, a, obs, years):
    """(paired monthly frame, cycle) for the last complete cycle of `case`, mapped on the EC years."""
    first, last, align = years
    idx = P.history_index(a.archive_root, case)
    cycle = P.last_complete_cycle(sorted(idx), first, last, align)
    model, freq = P.fates_samples([(y, idx[y]) for y in cycle], first, last, align)
    _, mon = P.paired_monthly(model, obs, freq, a.min_days)
    return mon, cycle, freq


def f2(v, fmt="{:.2f}"):
    return fmt.format(v) if v is not None and np.isfinite(v) else "-"


def plot_site(site, mon, cases, cycles, first, last, gpp_label, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(17, 11.5))
    gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1.05], hspace=0.38, wspace=0.28)
    unit = "g C m$^{-2}$ d$^{-1}$"
    for r, flux in enumerate(("GPP", "NEE")):
        ax = fig.add_subplot(gs[r, :])
        ax.plot(mon.date, mon[f"EC_{flux}"], label="EC tower (" + (gpp_label if flux == "GPP" else "NEE_VUT_REF") + ")",
                **STYLE["EC"])
        head = []
        for v in cases:
            col = f"{v}_{flux}"
            if col not in mon or not mon[col].notna().any():
                continue
            sc = metrics(mon, flux, col)
            ax.plot(mon.date, mon[col], label=f"{LABEL[v]}: R²={f2(sc['R2'])}, RMSE={f2(sc['RMSE'])}, "
                                              f"bias={f2(sc['Bias'], '{:+.2f}')}", **STYLE[v])
            if v == "new":
                head.append(f"new: N={sc['N']} months, mean model {f2(sc['Mean_model'])} vs EC {f2(sc['Mean_EC'])}"
                            + (f", model/EC={f2(sc['Ratio'])}" if flux == "GPP" else "")
                            + f", R={f2(sc['R'])}")
        if flux == "NEE":
            ax.axhline(0, ls="--", lw=0.8, color="0.5")
        ax.set_ylabel(f"{flux} ({unit})")
        ax.set_title(f"{flux} | monthly | " + "; ".join(head), fontsize=10.5)
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.003, 1.0), fontsize=8.5)
        ax.xaxis.set_major_locator(mdates.YearLocator(1 if last - first < 12 else 2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlim(pd.Timestamp(first, 1, 1), pd.Timestamp(last + 1, 1, 1))
    months = range(1, 13)
    for k, flux in enumerate(("GPP", "NEE")):
        ax = fig.add_subplot(gs[2, 2 * k])
        ax.plot(months, seasonal(mon, f"EC_{flux}"), label="EC", **STYLE["EC"])
        for v in cases:
            col = f"{v}_{flux}"
            if col in mon and mon[col].notna().any():
                ax.plot(months, seasonal(mon, col, f"EC_{flux}"), label=v, **STYLE[v])
        if flux == "NEE":
            ax.axhline(0, color="0.6", lw=0.6)
        ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(["Jan", "Apr", "Jul", "Oct"])
        ax.set_title(f"{flux} mean seasonal cycle (months with EC)", fontsize=10)
        ax.set_ylabel(unit); ax.grid(alpha=0.2); ax.legend(frameon=False, fontsize=8)
        ax = fig.add_subplot(gs[2, 2 * k + 1])
        lo, hi = np.inf, -np.inf
        for v in cases:
            col = f"{v}_{flux}"
            if col not in mon:
                continue
            ok = mon[[f"EC_{flux}", col]].dropna()
            if ok.empty:
                continue
            ax.scatter(ok[f"EC_{flux}"], ok[col], s=14, alpha=0.75, label=v,
                       color=STYLE[v]["color"], marker="o" if v == "new" else "x")
            lo = min(lo, ok.min().min()); hi = max(hi, ok.max().max())
        if np.isfinite(lo):
            pad = 0.05 * (hi - lo + 1e-9)
            ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.4", lw=0.8)
            ax.set_xlim(lo - pad, hi + pad); ax.set_ylim(lo - pad, hi + pad)
        ax.set_xlabel(f"EC {flux}"); ax.set_ylabel(f"model {flux}")
        ax.set_title(f"{flux} monthly, 1:1", fontsize=10); ax.grid(alpha=0.2); ax.legend(frameon=False, fontsize=8)
    cyc = "; ".join(f"{v} model years {c[0]}-{c[-1]}" for v, c in cycles.items())
    fig.suptitle(f"{site}: last complete forcing cycle vs EC tower ({first}-{last})\n{cases['new']} | {cyc}"
                 + (f"\nbefore fix = {cases['old']}" if "old" in cases else ""), fontsize=12)
    p = dest / f"{site}_last_cycle_GPP_NEE_vs_EC.png"
    fig.savefig(p, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_seasonal_all(mons, flux, root):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sites = sorted(mons)
    if not sites:
        return
    ncol = min(5, len(sites)); nrow = int(np.ceil(len(sites) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.1 * nrow), squeeze=False, sharex=True)
    for ax, s in zip(axs.flat, sites):
        mon = mons[s]
        ax.plot(range(1, 13), seasonal(mon, f"EC_{flux}"), label="EC", **STYLE["EC"])
        for v in ("old", "new"):
            col = f"{v}_{flux}"
            if col in mon and mon[col].notna().any():
                ax.plot(range(1, 13), seasonal(mon, col, f"EC_{flux}"), label=v, **STYLE[v])
        title = s
        if "new_" + flux in mon:
            sc = metrics(mon, flux, "new_" + flux)
            title += (f"  (model/EC {f2(sc['Ratio'])}, R² {f2(sc['R2'])})" if flux == "GPP"
                      else f"  (bias {f2(sc['Bias'], '{:+.2f}')}, R² {f2(sc['R2'])})")
        if flux == "NEE":
            ax.axhline(0, color="0.6", lw=0.6)
        ax.set_title(title, fontsize=9.5)
        ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(["Jan", "Apr", "Jul", "Oct"])
        ax.tick_params(labelsize=8); ax.grid(alpha=0.2)
    for ax in list(axs.flat)[len(sites):]:
        ax.set_visible(False)
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"New Normal400, last complete forcing cycle | mean seasonal cycle of monthly {flux} (g C m-2 d-1), "
                 f"months with EC only\nblack = EC, red = new Normal400, grey dashed = before fix (where still archived)",
                 fontsize=11.5)
    fig.tight_layout()
    fig.savefig(root / f"ALL_SITES_last_cycle_{flux}_seasonal_cycle.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_means(rows, root):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    df = pd.DataFrame([r for r in rows if r.get("Status") == "OK"])
    if df.empty:
        return
    fig, axs = plt.subplots(1, 2, figsize=(15, 0.42 * df.Site.nunique() + 2.5), squeeze=False)
    for ax, flux in zip(axs[0], ("GPP", "NEE")):
        d = df[df.Flux == flux]
        sites = sorted(d.Site.unique())
        y = np.arange(len(sites))
        ec = [d[(d.Site == s) & (d.Case == "new")].Mean_EC.mean() for s in sites]
        ax.barh(y + 0.27, ec, height=0.26, color="k", label="EC")
        for off, v in ((0.0, "new"), (-0.27, "old")):
            vals = [d[(d.Site == s) & (d.Case == v)].Mean_model.mean() if not d[(d.Site == s) & (d.Case == v)].empty
                    else np.nan for s in sites]
            if np.isfinite(vals).any():
                ax.barh(y + off, vals, height=0.26, color=STYLE[v]["color"], label=LABEL[v])
        ax.set_yticks(y); ax.set_yticklabels(sites); ax.invert_yaxis()
        ax.axvline(0, color="0.5", lw=0.7)
        ax.set_xlabel(f"mean monthly {flux} over paired months (g C m-2 d-1)")
        ax.set_title(f"{flux}: last cycle mean, model vs EC"); ax.grid(alpha=0.2, axis="x")
        ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    fig.savefig(root / "ALL_SITES_last_cycle_mean_vs_EC.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def run(a, pairs):
    a.output_root.mkdir(parents=True, exist_ok=True)
    rows, mons = [], {}
    for site, ad, normal in pairs:
        dest = a.output_root / site
        dest.mkdir(exist_ok=True)
        try:
            run_dir = a.archive_root.parent / normal / "run"
            years = P.forcing_years(a.cases_root / normal, run_dir)
            first, last, _ = years
            srcs = P.ec_sources(a.sites_root / site / "forcing", None)
            obs, _prov = P.ec_daily(srcs, first, last, a.min_halfhour)
            gpp_cols = sorted({c for c in obs["EC_GPP_column"].dropna() if c})
            cases = {"new": normal}
            old = SUFFIX.sub("", normal)
            if old != normal and (a.cases_root / old).is_dir():
                cases["old"] = old
            mon, cycles = None, {}
            for v, case in cases.items():
                try:
                    m, cyc, freq = model_monthly(case, run_dir, a, obs, years)
                except Exception as exc:
                    msg = f"{type(exc).__name__}: {exc}"
                    print(f"  {site} {v} ({case}): not drawn - {msg}", flush=True)
                    if v == "new":
                        raise
                    rows.append({"Site": site, "Case": v, "CaseName": case, "Status": "NOT_AVAILABLE", "Error": msg})
                    continue
                cycles[v] = cyc
                m = m.rename(columns={"FATES_GPP": f"{v}_GPP", "FATES_NEE": f"{v}_NEE"})
                keep = ["date", f"{v}_GPP", f"{v}_NEE"] if mon is not None else list(m.columns)
                mon = m[keep] if mon is None else mon.merge(m[keep], on="date", how="outer")
            cases = {v: c for v, c in cases.items() if v in cycles}
            mon = mon.sort_values("date").reset_index(drop=True)
            mon.to_csv(dest / f"{site}_last_cycle_monthly_vs_EC.csv", index=False)
            mons[site] = mon
            for v, case in cases.items():
                for flux in ("GPP", "NEE"):
                    sc = metrics(mon, flux, f"{v}_{flux}")
                    rows.append({"Site": site, "Case": v, "CaseName": case, "Flux": flux, "Status": "OK",
                                 "Cycle": f"{cycles[v][0]}-{cycles[v][-1]}", "EC_years": f"{first}-{last}", **sc})
                    print(f"  {site} {v:3} {flux}: N {sc['N']} R² {f2(sc['R2'])} RMSE {f2(sc['RMSE'])} "
                          f"bias {f2(sc['Bias'], '{:+.2f}')} model {f2(sc['Mean_model'])} / EC {f2(sc['Mean_EC'])}",
                          flush=True)
            plot_site(site, mon, cases, cycles, first, last, " + ".join(gpp_cols) or "no GPP", dest)
            print(f"[{site}] OK  cycle {cycles['new'][0]}-{cycles['new'][-1]} -> EC {first}-{last}", flush=True)
        except Exception as exc:
            print(f"[{site}] FAILED: {type(exc).__name__}: {exc}", flush=True)
            (dest / "ERROR.txt").write_text(traceback.format_exc())
            rows.append({"Site": site, "Case": "new", "CaseName": normal, "Status": "FAILED",
                         "Error": f"{type(exc).__name__}: {exc}"})
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (a.output_root / "last_cycle_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    for fn, args in ((plot_seasonal_all, ("GPP",)), (plot_seasonal_all, ("NEE",)), (plot_means, ())):
        try:
            fn(mons, *args, a.output_root) if args else fn(rows, a.output_root)
        except Exception as exc:
            print(f"overview {fn.__name__}{args} failed: {exc}", flush=True)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"sites_plotted": sorted(mons), "pairs": [":".join(p) for p in pairs],
         "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {len(mons)}/{len(pairs)} sites plotted. Output: {a.output_root}", flush=True)
    return 0 if len(mons) == len(pairs) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--pairs", nargs="*", default=[], metavar="SITE:AD:NORMAL")
    ap.add_argument("--pairs-file", type=Path, help="pairs.txt of a plot_done_normal400.sh output (SITE:AD:NORMAL)")
    ap.add_argument("--sites", nargs="+", help="only these sites of the pairs")
    ap.add_argument("--plot-module", help="Stage15 module (default plot.py beside this file, else the repo copy)")
    ap.add_argument("--archive-root", type=Path, default=Path(f"/scratch/{USER}/CTSM_FATES_OUTPUTS/archive"))
    ap.add_argument("--cases-root", type=Path, default=Path(f"/iridisfs/scratch/{USER}/CLM_FATES/cases"))
    ap.add_argument("--sites-root", type=Path, default=Path(f"/iridisfs/scratch/{USER}/CLM_FATES/sites/MY_EC_SITE"))
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    a = ap.parse_args(argv)
    raw = list(a.pairs) + (a.pairs_file.read_text().split() if a.pairs_file else [])
    pairs = [tuple(p.split(":")) for p in raw if p.count(":") == 2]
    if a.sites:
        pairs = [p for p in pairs if p[0] in a.sites]
    if not pairs:
        ap.error("no SITE:AD:NORMAL pairs")
    out = a.output_root.expanduser().resolve()
    if any(out == p or p in out.parents for p in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if out.exists() and any(out.iterdir()):
        ap.error(f"output folder must be new or empty: {out}")
    a.output_root = out
    print("Stage15 module:", load_plot(a.plot_module), flush=True)
    return run(a, pairs)


if __name__ == "__main__":
    raise SystemExit(main())
