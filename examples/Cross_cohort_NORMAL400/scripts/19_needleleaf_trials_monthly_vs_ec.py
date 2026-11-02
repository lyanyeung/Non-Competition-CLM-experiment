#!/usr/bin/env python3
"""Monthly GPP / NEE of the final needleleaf trials against the EC towers, in the job's monthly-overview style.

Same reading and EC rules as the Stage15 monthly overview (<site>_GPP_NEE_monthly_overview.png): the LAST COMPLETE
forcing cycle of the run is mapped onto the EC observation years with the DATM year_first / year_last / year_align;
GPP NT before DT; EC NEE = NEE_VUT_REF; model NEE = -FATES_NEP; months need >= --min-days EC days; g C m-2 d-1.

Cases per site (ten FINAL_SITES of script 13):
  control  original AD400 case, the same model years as the trials (default parameters)
  D        <AD>_FIXD100  cushion 2.4 + slatop 0.010
  F        <AD>_FIXF100  cushion 2.4 + slatop 0.008   (adopted)
The trials are 100 AD years, so the cycle is the last complete forcing cycle inside those 100 years.

Caveat printed on every figure: these are AD-mode runs. GPP is a valid comparison (AD rescales soil decomposition
only), NEE is indicative only: heterotrophic respiration runs with accelerated soil pools, and a spun-up model NEE
is near 0 over the year by construction (see docs, NEE section).

Outputs (never under scratch):
  <out>/<site>/<site>_trials_GPP_NEE_monthly_vs_EC.png, <site>_trials_monthly_vs_EC.csv
  <out>/ALL_SITES_GPP_seasonal_cycle.png, ALL_SITES_NEE_seasonal_cycle.png
  <out>/trials_monthly_metrics.csv, RUN_COMPLETE.json
Usage (login node or compute node; publish only on the login node):
  python -B 19_...py --output-root DIR [--sites ...]
  python -B 19_...py --publish-run DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIG_DIR = "figures/AD400_NORMAL400_needleleaf_trials_monthly_vs_EC"
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], float)
CASES = [("control", "default parameters"), ("D", "cushion 2.4 + slatop 0.010"), ("F", "cushion 2.4 + slatop 0.008, adopted")]
STYLE = {"EC": dict(color="k", lw=1.8), "control": dict(color="0.6", lw=1.1, ls="--"),
         "D": dict(color="tab:blue", lw=1.2), "F": dict(color="tab:red", lw=1.8)}
CAVEAT = ("AD-mode runs: GPP comparable; NEE indicative only (accelerated soil decomposition, "
          "spun-up model NEE ~0 over the year)")
T13 = F7 = P = R = None


def load_modules():
    global T13, F7, P, R
    spec = importlib.util.spec_from_file_location("trial13", HERE / "13_needleleaf_param_trials.py")
    T13 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T13)
    T13.load09()
    R = T13.R
    F7, P = R.load07()


# ------------------------------------------------------------------ data
def case_monthly(case, cycle_from, args, cycle=None):
    """Model GPP/NEE for the last complete forcing cycle (or the given cycle) mapped onto EC dates. cycle_from =
    (case name, run dir) whose DATM settings define the forcing years (the trial; its streams equal the AD case's)."""
    first, last, align = P.forcing_years(args.cases_root / cycle_from[0], cycle_from[1])
    fidx = P.history_index(args.archive_root, case)
    if cycle is None:
        cycle = P.last_complete_cycle(sorted(fidx), first, last, align)
    missing = [y for y in cycle if y not in fidx]
    if missing:
        raise ValueError(f"{case}: model years {missing[:3]}... missing for cycle {cycle[0]}-{cycle[-1]}")
    model, freq = P.fates_samples([(y, fidx[y]) for y in cycle], first, last, align)
    return model, freq, cycle, (first, last, align)


def metrics(mon, flux, col):
    sc = P.metrics(mon[f"EC_{flux}"], mon[col]) if P is not None else _metrics(mon[f"EC_{flux}"], mon[col])
    ok = mon[[f"EC_{flux}", col]].dropna()
    sc["Mean_EC"] = float(ok[f"EC_{flux}"].mean()) if len(ok) else np.nan
    sc["Mean_model"] = float(ok[col].mean()) if len(ok) else np.nan
    sc["Ratio"] = sc["Mean_model"] / sc["Mean_EC"] if flux == "GPP" and sc["Mean_EC"] > 1e-9 else np.nan
    return sc


def _metrics(obs, mod):   # same formulas as the Stage15 module (used only when it is not loaded, i.e. in tests)
    x, y = np.asarray(obs, float), np.asarray(mod, float)
    ok = np.isfinite(x) & np.isfinite(y); x, y = x[ok], y[ok]
    out = {"N": int(len(x)), "R": np.nan, "R2": np.nan, "RMSE": np.nan, "MAE": np.nan, "Bias": np.nan}
    if len(x) < 2:
        return out
    d = y - x; den = float(np.sum((x - x.mean()) ** 2))
    out.update(R=float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else np.nan,
               R2=float(1 - np.sum(d ** 2) / den) if den > 0 else np.nan,
               RMSE=float(np.sqrt(np.mean(d ** 2))), MAE=float(np.mean(np.abs(d))), Bias=float(d.mean()))
    return out


def seasonal(mon, col):
    """Mean seasonal cycle over the months that have EC data (paired), 12 values."""
    x = mon.dropna(subset=[col]).copy()
    x["m"] = pd.to_datetime(x["date"]).dt.month
    return x.groupby("m")[col].mean().reindex(range(1, 13))


# ------------------------------------------------------------------ plots
def plot_site(site, mon, labels, first, last, cycle, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    for ax, flux in zip(axs, ("GPP", "NEE")):
        ax.plot(mon.date, mon[f"EC_{flux}"], label="EC tower" + (f" ({labels['gpp']})" if flux == "GPP" else
                                                                 " (NEE_VUT_REF)"), **STYLE["EC"])
        parts = []
        for v, desc in CASES:
            col = f"{v}_{flux}"
            if col not in mon or not mon[col].notna().any():
                continue
            sc = metrics(mon, flux, col)
            ax.plot(mon.date, mon[col], label=f"FATES {v} ({desc}): R²={sc['R2']:.2f}, RMSE={sc['RMSE']:.2f}, "
                                              f"bias={sc['Bias']:+.2f}", **STYLE[v])
            if v == "F":
                parts.append(f"F: N={sc['N']}, R²={sc['R2']:.3f}, RMSE={sc['RMSE']:.3f}, bias={sc['Bias']:.3f}"
                             + (f", model/EC={sc['Ratio']:.2f}" if flux == "GPP" else ""))
        if flux == "NEE":
            ax.axhline(0, ls="--", lw=0.8, color="0.5")
        ax.set_ylabel(f"{flux} (g C m$^{{-2}}$ d$^{{-1}}$)")
        ax.set_title(f"{flux} | monthly | " + " ".join(parts), fontsize=11)
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.005, 1.0), fontsize=8.5)
    axs[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axs[-1].set_xlim(pd.Timestamp(first, 1, 1), pd.Timestamp(last + 1, 1, 1))
    axs[-1].set_xlabel("EC observation year")
    fig.suptitle(f"{site}: EC tower vs FATES needleleaf trials (monthly means, {first}-{last})\n"
                 f"Last complete forcing cycle of the 100-year AD trials, model years {cycle[0]}-{cycle[-1]}; "
                 f"control = original AD400 case, same years\n{CAVEAT}", fontsize=12)
    fig.tight_layout()
    p = dest / f"{site}_trials_GPP_NEE_monthly_vs_EC.png"
    fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return p


def plot_seasonal(mons, flux, root):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sites = sorted(mons)
    if not sites:
        return None
    ncol = 5; nrow = int(np.ceil(len(sites) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.0 * nrow), squeeze=False, sharex=True)
    for ax, s in zip(axs.flat, sites):
        mon = mons[s]
        ax.plot(range(1, 13), seasonal(mon, f"EC_{flux}"), label="EC", **STYLE["EC"])
        title = s
        for v, _ in CASES:
            col = f"{v}_{flux}"
            if col in mon and mon[col].notna().any():
                ax.plot(range(1, 13), seasonal(mon.dropna(subset=[f"EC_{flux}"]), col), label=v, **STYLE[v])
        if flux == "GPP" and "F_GPP" in mon:
            sc = metrics(mon, "GPP", "F_GPP")
            title += f"  (F/EC {sc['Ratio']:.2f}, R² {sc['R2']:.2f})"
        if flux == "NEE":
            ax.axhline(0, color="0.6", lw=0.6)
        ax.set_title(title, fontsize=9.5)
        ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(["Jan", "Apr", "Jul", "Oct"])
        ax.tick_params(labelsize=8); ax.grid(alpha=0.2)
    for ax in list(axs.flat)[len(sites):]:
        ax.set_visible(False)
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Needleleaf trial sites | mean seasonal cycle of monthly {flux} (g C m-2 d-1), months with EC data only\n"
                 f"black = EC, grey dashed = control (default), blue = D, red = F (adopted). {CAVEAT}", fontsize=11.5)
    fig.tight_layout()
    p = root / f"ALL_SITES_{flux}_seasonal_cycle.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


# ------------------------------------------------------------------ driver
def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    rows, mons = [], {}
    for site in a.sites:
        dest = a.output_root / site
        dest.mkdir(exist_ok=True)
        try:
            i0 = R.ident(site, F7, P, 100)
            names = {"control": i0["ad"], **{v: T13.ident(site, v, F7, P, a.years)["new"] for v in ("D", "F")}}
            trial_case = names["F"]
            cycle_from = (trial_case, a.archive_root.parent / trial_case / "run")
            fmod, freq, cycle, (first, last, align) = case_monthly(trial_case, cycle_from, a)
            print(f"[{site}] cycle {cycle[0]}-{cycle[-1]} -> EC {first}-{last} ({freq})", flush=True)
            srcs = P.ec_sources(a.sites_root / site / "forcing", None)
            obs, prov = P.ec_daily(srcs, first, last, a.min_halfhour)
            gpp_cols = sorted({c for c in obs["EC_GPP_column"].dropna() if c})
            mon = None
            for v in ("control", "D", "F"):
                try:
                    model = fmod if v == "F" else case_monthly(names[v], cycle_from, a, cycle=cycle)[0]
                    _, m = P.paired_monthly(model, obs, freq, a.min_days)
                    m = m.rename(columns={"FATES_GPP": f"{v}_GPP", "FATES_NEE": f"{v}_NEE"})
                    keep = ["date", f"{v}_GPP", f"{v}_NEE"]
                    mon = m if mon is None else mon.merge(m[keep], on="date", how="outer")
                except Exception as exc:
                    print(f"  {site} {v}: {type(exc).__name__}: {exc}", flush=True)
                    rows.append({"Site": site, "Case": v, "Status": "FAILED", "Error": f"{type(exc).__name__}: {exc}"})
            if mon is None:
                continue
            mon = mon.sort_values("date").reset_index(drop=True)
            mon.to_csv(dest / f"{site}_trials_monthly_vs_EC.csv", index=False)
            mons[site] = mon
            for v, _ in CASES:
                for flux in ("GPP", "NEE"):
                    col = f"{v}_{flux}"
                    if col in mon:
                        sc = metrics(mon, flux, col)
                        rows.append({"Site": site, "Case": v, "CaseName": names[v], "Flux": flux, "Status": "OK",
                                     "Cycle": f"{cycle[0]}-{cycle[-1]}", "EC_years": f"{first}-{last}", **sc})
                        f2 = lambda k: f"{sc[k]:.2f}" if np.isfinite(sc[k]) else "-"
                        print(f"  {site} {v:7} {flux}: N {sc['N']} R² {f2('R2')} RMSE {f2('RMSE')} bias {f2('Bias')} "
                              f"model {f2('Mean_model')} / EC {f2('Mean_EC')}", flush=True)
            plot_site(site, mon, {"gpp": " + ".join(gpp_cols) or "no GPP"}, first, last, cycle, dest)
        except Exception as exc:
            print(f"[{site}] FAILED: {type(exc).__name__}: {exc}", flush=True)
            (dest / "ERROR.txt").write_text(traceback.format_exc())
            rows.append({"Site": site, "Case": "-", "Status": "FAILED", "Error": f"{type(exc).__name__}: {exc}"})
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (a.output_root / "trials_monthly_metrics.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    for flux in ("GPP", "NEE"):
        try:
            plot_seasonal(mons, flux, a.output_root)
        except Exception as exc:
            print(f"seasonal {flux} plot failed: {exc}", flush=True)
    summary = summarize(rows)
    (a.output_root / "trials_monthly_summary.txt").write_text("\n".join(summary) + "\n")
    print("\n" + "\n".join(summary), flush=True)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"sites_plotted": sorted(mons), "sites": a.sites, "finished_utc": datetime.now(timezone.utc).isoformat()},
        indent=2) + "\n")
    print(f"\nCOMPLETE: {len(mons)}/{len(a.sites)} sites plotted. Output: {a.output_root}", flush=True)
    return 0


def summarize(rows):
    ok = pd.DataFrame([r for r in rows if r.get("Status") == "OK"])
    lines = []
    if ok.empty:
        return ["no results"]
    for flux in ("GPP", "NEE"):
        lines.append(f"{flux} (monthly, last cycle vs EC; median over sites):")
        for v, desc in CASES:
            s = ok[(ok.Flux == flux) & (ok.Case == v)]
            if s.empty:
                continue
            extra = f", median model/EC {s.Ratio.median():.2f}" if flux == "GPP" else ""
            lines.append(f"  {v:7} ({desc}): sites {len(s)}, median R² {s.R2.median():.2f}, median RMSE {s.RMSE.median():.2f}, "
                         f"median bias {s.Bias.median():+.2f}{extra}")
    return lines


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    with tempfile.TemporaryDirectory(prefix="trials_monthly_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        for n in ("trials_monthly_metrics.csv", "trials_monthly_summary.txt", "ALL_SITES_GPP_seasonal_cycle.png",
                  "ALL_SITES_NEE_seasonal_cycle.png"):
            if (run_dir / n).is_file():
                shutil.copyfile(run_dir / n, out / n)
        rows = list(csv.DictReader((run_dir / "trials_monthly_metrics.csv").open(encoding="utf-8")))
        lines = ["# Needleleaf trials: monthly GPP / NEE vs EC (last complete forcing cycle)", "",
                 "control = original AD400 case (default parameters); D = cushion 2.4 + slatop 0.010; "
                 "**F = cushion 2.4 + slatop 0.008 (adopted)**. Same EC rules as the job's monthly overview "
                 "(GPP NT before DT, NEE_VUT_REF, model NEE = -FATES_NEP, g C m-2 d-1).", "",
                 f"**Caveat:** {CAVEAT}.", "",
                 "```", (run_dir / "trials_monthly_summary.txt").read_text().rstrip(), "```", "",
                 "![GPP seasonal cycle](ALL_SITES_GPP_seasonal_cycle.png)", "",
                 "![NEE seasonal cycle](ALL_SITES_NEE_seasonal_cycle.png)", "",
                 "| Site | Case | Flux | N months | R² | RMSE | bias | model mean | EC mean | model/EC | figure |",
                 "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        f = lambda r, k: f"{float(r[k]):.2f}" if r.get(k) not in (None, "", "nan") else "–"
        for r in rows:
            s = r["Site"]
            if r.get("Status") != "OK" or not F7.SAFE.fullmatch(s):
                continue
            png = run_dir / s / f"{s}_trials_GPP_NEE_monthly_vs_EC.png"
            link = ""
            if png.is_file() and F7.is_png(png):
                (out / s).mkdir(exist_ok=True)
                if not (out / s / png.name).exists():
                    shutil.copyfile(png, out / s / png.name)
                link = f"[png]({s}/{png.name})"
            lines.append(f"| {s} | {r['Case']} | {r['Flux']} | {r.get('N', '')} | {f(r, 'R2')} | {f(r, 'RMSE')} | "
                         f"{f(r, 'Bias')} | {f(r, 'Mean_model')} | {f(r, 'Mean_EC')} | {f(r, 'Ratio')} | {link} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", "Add needleleaf trials monthly GPP/NEE vs EC", cwd=co)
        for attempt in range(5):
            try:
                F7.git("push", "origin", "HEAD:main", cwd=co)
                break
            except RuntimeError:
                if attempt == 4:
                    raise
                F7.git("pull", "--rebase", "origin", "main", cwd=co)
        sha = F7.git("rev-parse", "HEAD", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish-run", type=Path)
    ap.add_argument("--sites", nargs="+", default=None, help="default: FINAL_SITES of script 13")
    ap.add_argument("--years", type=int, default=100)
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--cases-root", type=Path, default=None)
    ap.add_argument("--sites-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    load_modules()
    a.sites = a.sites or list(T13.FINAL_SITES)
    a.archive_root = a.archive_root or Path(f"/scratch/{F7.USER}/CTSM_FATES_OUTPUTS/archive")
    a.cases_root = a.cases_root or Path(f"/iridisfs/scratch/{F7.USER}/CLM_FATES/cases")
    a.sites_root = a.sites_root or Path(f"/iridisfs/scratch/{F7.USER}/CLM_FATES/sites/MY_EC_SITE")
    if a.publish_run:
        return publish(a.publish_run, a.repo or F7.REPO)
    if not a.output_root:
        ap.error("give --output-root or --publish-run")
    root = a.output_root.expanduser()
    if not root.is_absolute():
        ap.error("output directory must be absolute")
    root = root.resolve()
    if any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty: " + str(root))
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
