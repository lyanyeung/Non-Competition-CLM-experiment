#!/usr/bin/env python3
"""Read-only NL-Loo V3 PRE50 -> AD200 -> POST300 diagnostics.

Place the shared Stage15 plot.py beside this script. A missing POST300 is
plotted explicitly as an interim PRE50+AD200 result, never as completed 550y.
The script may compare the last complete *observed normal-phase* forcing cycle
to tower EC; PRE50 comparisons are clearly labelled interim.
"""
import argparse
import importlib.util
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SITE = "NL-Loo"
START = 1997
PHASES = (("PRE50", "NORMAL", 1997, 2047), ("AD200", "AD", 2047, 2247),
          ("POST300", "NORMAL", 2247, 2547))
CASES = {stage: f"NL-Loo_OBSPFT_NC_V3_{stage}" for stage, _, _, _ in PHASES}
LABELS = {"PRE50": "PRE50 · Normal", "AD200": "AD200 · accelerated", "POST300": "POST300 · Normal"}
REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"


def load_core():
    path = Path(__file__).resolve().parent / "plot.py"
    spec = importlib.util.spec_from_file_location("stage15", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inspect(core, cases_root, archive_root):
    out = {}
    for stage, mode, first, stop in PHASES:
        name = CASES[stage]; case = cases_root / name
        entry = {"stage": stage, "name": name, "mode": mode, "start": first,
                 "stop": stop, "expected_years": stop - first, "years": [], "found": {}, "issue": ""}
        if not case.is_dir():
            entry["issue"] = "case directory absent"
            out[stage] = entry
            continue
        try:
            start = core.env_value(case, "RUN_STARTDATE")
            if start != f"{first}-01-01":
                raise ValueError(f"unexpected RUN_STARTDATE {start}")
            expected_ref = {"AD200": CASES["PRE50"], "POST300": CASES["AD200"]}.get(stage)
            if expected_ref and core.env_value(case, "RUN_REFCASE") != expected_ref:
                raise ValueError("RUN_REFCASE does not match preceding V3 phase")
            found = core.history_index(archive_root, name)
            entry["found"] = found
            entry["years"] = core.contiguous(found, first, stop - first)
            missing = stop - first - len(entry["years"])
            if missing:
                entry["issue"] = f"{missing} years not in contiguous history"
        except Exception as exc:
            entry["issue"] = f"{type(exc).__name__}: {exc}"
        out[stage] = entry
    return out


def latest_normal_cycles(core, stages, cases_root, archive_root):
    """Return newest candidate cycle first; do not use accelerated histories."""
    options, notes = [], []
    for stage in ("POST300", "PRE50"):
        info = stages[stage]
        if not info["years"]:
            notes.append(f"{stage}: no archived years")
            continue
        try:
            case = cases_root / info["name"]
            run = archive_root.parent / info["name"] / "run"
            first, last, align = core.forcing_years(case, run)
            cycle = core.last_complete_cycle(info["years"], first, last, align)
            options.append((stage, first, last, align, cycle))
        except Exception as exc:
            notes.append(f"{stage}: {type(exc).__name__}: {exc}")
    return options, notes


def annual_data(core, stages):
    frames, meta, availability = [], {}, {}
    for stage, _, _, _ in PHASES:
        data = stages[stage]
        if not data["years"]:
            continue
        files = [(y - START + 1, y, stage, data["found"][y]) for y in data["years"]]
        frame, names, units = core.annual_carbon(files, SITE)
        availability[stage] = names
        for name, details in units.items():
            if name in meta and meta[name]["csv_units"] != details["csv_units"]:
                raise ValueError(f"Carbon units differ between phases for {name}")
            meta[name] = details
        frames.append(frame)
    if not frames:
        raise ValueError("No readable contiguous NL-Loo V3 phase histories")
    return pd.concat(frames, ignore_index=True), meta, availability


def phase_metrics(core, data, meta):
    rows = []
    for stage in ("PRE50", "POST300"):
        df = data[data.Phase == stage]
        for var in meta:
            if df.empty or var not in df or df[var].notna().sum() == 0:
                continue
            v = df[var].to_numpy(float)
            s30, p30 = core.trend(v, 30); s100, p100 = core.trend(v, 100)
            rows.append({"Phase": stage, "Variable": var, "Units": meta[var]["csv_units"],
                         "Years": len(v), "Last30y_slope_per_year": s30,
                         "Last30y_trend_pct_per_100y": p30,
                         "Last100y_slope_per_year": s100, "Last100y_trend_pct_per_100y": p100})
    return pd.DataFrame(rows)


def plot_carbon(core, data, meta, dest, interim):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(meta)
    tag = "INTERIM — final Normal phase incomplete" if interim else "all 550 archived years"
    show = [n for n in ("TOTECOSYSC", "TOTSOMC", "FATES_VEGC") if n in names] or names[:3]
    if len({meta[n]["plot_units"] for n in show}) > 1:
        raise ValueError("Cannot plot carbon variables with different units on one axis")
    fig, ax = plt.subplots(figsize=(16, 5.9))
    colors = dict(zip(show, plt.get_cmap("tab10").colors))
    for name in show:
        for i, (stage, _, _, _) in enumerate(PHASES):
            p = data[data.Phase == stage]
            if name in p and p[name].notna().any():
                ax.plot(p.SpinupYear, p[name], color=colors[name], lw=1.4,
                        label=core.LABELS.get(name, name) if i == next(
                            j for j, (st, _, _, _) in enumerate(PHASES)
                            if name in data[data.Phase == st] and data.loc[data.Phase == st, name].notna().any()) else None)
    ax.axvline(50.5, color="0.35", ls="--", lw=1)
    ax.axvline(250.5, color="0.35", ls="--", lw=1)
    ax.set(xlim=(1, 550), xlabel="Spin-up year: 1–50 PRE, 51–250 AD, 251–550 POST",
           ylabel=f"Annual mean ({meta[show[0]]['plot_units']})")
    ax.set_title(f"NL-Loo V3 | carbon pools by phase — {tag}\nAD transitions can rescale pools; phases are not joined")
    ax.grid(alpha=.25); ax.legend(frameon=False); fig.tight_layout()
    fig.savefig(dest / "NL-Loo_01_carbon_pools_PRE_AD_POST.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    nrow = math.ceil(min(len(names), 6) / 2)
    fig, axs = plt.subplots(nrow, 2, figsize=(16, 4 * nrow), sharex=True, squeeze=False)
    for ax, name in zip(axs.flat, names[:6]):
        for stage, _, _, _ in PHASES:
            p = data[data.Phase == stage]
            if name in p and p[name].notna().any():
                ax.plot(p.SpinupYear, p[name], lw=1.3, label=LABELS[stage])
        ax.axvline(50.5, color="0.5", ls="--", lw=.8); ax.axvline(250.5, color="0.5", ls="--", lw=.8)
        ax.set(title=name, ylabel=meta[name]["plot_units"], xlim=(1, 550)); ax.grid(alpha=.2)
    for ax in list(axs.flat)[min(len(names), 6):]: ax.set_visible(False)
    axs.flat[0].legend(frameon=False)
    for ax in axs[-1]: ax.set_xlabel("Spin-up year")
    fig.suptitle(f"NL-Loo V3 | available carbon fields — {tag}")
    fig.tight_layout(); fig.savefig(dest / "NL-Loo_02_carbon_pools_phase_panels.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def plot_ec(core, mon, stage, cycle, first, last, gpp, dest, interim):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    fig, axs = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    scores = []
    for ax, flux in zip(axs, ("GPP", "NEE")):
        score = core.metrics(mon[f"EC_{flux}"], mon[f"FATES_{flux}"])
        scores.append({"Phase": stage, "Flux": flux, "Scale": "monthly", **score})
        ax.plot(mon.date, mon[f"EC_{flux}"], label=("EC " + gpp if flux == "GPP" else "EC NEE_VUT_REF"))
        ax.plot(mon.date, mon[f"FATES_{flux}"], label="FATES")
        ax.set_ylabel(f"{flux} (g C m$^{{-2}}$ d$^{{-1}}$)")
        ax.set_title(f"N={score['N']}, R²={score['R2']:.3f}, RMSE={score['RMSE']:.3f}, bias={score['Bias']:.3f}")
        if flux == "NEE": ax.axhline(0, color="0.5", ls="--", lw=.8)
        ax.grid(alpha=.25); ax.legend(frameon=False)
    axs[-1].xaxis.set_major_locator(mdates.YearLocator(2)); axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axs[-1].set_xlim(pd.Timestamp(first, 1, 1), pd.Timestamp(last + 1, 1, 1)); axs[-1].set_xlabel("EC observation year")
    tag = " INTERIM" if interim else ""
    fig.suptitle(f"NL-Loo | {stage} normal phase vs EC{tag}\nModel years {cycle[0]}–{cycle[-1]}; forcing {first}–{last}")
    fig.tight_layout(); fig.savefig(dest / "NL-Loo_GPP_NEE_monthly_overview.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    return pd.DataFrame(scores)


def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True, text=True)
    if p.returncode: raise RuntimeError("git " + args[0] + " failed: " + p.stderr[-3000:])
    return p.stdout.strip()


def publish(dest, meta):
    import tempfile
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path("figures") / "NL-Loo_PRE50_AD200_POST300" / stamp
    plots = sorted(dest.glob("NL-Loo_*.png"))
    if not plots: raise RuntimeError("No PNG plots to publish")
    with tempfile.TemporaryDirectory(prefix="nl_loo_publish_", dir=dest.parent) as tmp:
        checkout = Path(tmp) / "repo"
        git("clone", "--depth", "1", "--branch", "main", REPO, checkout)
        folder = checkout / rel; folder.mkdir(parents=True)
        for p in plots: shutil.copyfile(p, folder / p.name)
        lines = ["# NL-Loo V3 carbon and EC diagnostics", "",
                 "Phase design: PRE50 Normal, AD200 accelerated, POST300 Normal.",
                 "Spin-up INTERIM: " + str(meta["interim"]) + "; EC phase: " + str(meta["ec_phase"] or "not available") + "; EC INTERIM: " + str(meta["ec_interim"]),
                 "EC GPP columns: " + (", ".join(meta["gpp_columns"]) or "none"),
                 "Absent carbon fields are not reconstructed. Simulation completion does not prove convergence.", ""]
        lines += [f"- [{p.name}]({p.name})" for p in plots]
        (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        git("add", "--", rel.as_posix(), cwd=checkout)
        git("commit", "-m", "Add NL-Loo V3 spin-up and EC figures", cwd=checkout)
        sha = git("rev-parse", "HEAD", cwd=checkout)
        git("push", "origin", "HEAD:main", cwd=checkout)
        print("GITHUB PUSH SUCCESS", sha, flush=True)
        print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix(), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--cases-root", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases"))
    ap.add_argument("--archive-root", type=Path, default=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/archive"))
    ap.add_argument("--sites-root", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE"))
    a = ap.parse_args(); core = load_core(); stages = inspect(core, a.cases_root, a.archive_root)
    for phase, _, _, _ in PHASES:
        s = stages[phase]
        print(f"{phase:7} {s['name']}: {len(s['years'])}/{s['expected_years']} contiguous years; {s['issue'] or 'history complete'}", flush=True)
        if a.preflight and s["years"]:
            try:
                from netCDF4 import Dataset
                with Dataset(str(s["found"][s["years"][0]][0])) as ds:
                    fields = [name for name in ("TOTECOSYSC", "TOTSOMC", "FATES_VEGC", "FATES_GPP", "FATES_NEP") if name in ds.variables]
                print("  First history fields:", ", ".join(fields) or "none of the requested fields", flush=True)
            except Exception as exc:
                print("  First history inspection failed:", type(exc).__name__, str(exc), flush=True)
    if a.preflight: return int(not any(stages[p]["years"] for p, *_ in PHASES))
    if a.output_root is None or not a.output_root.is_absolute(): ap.error("absolute --output-root required")
    dest = a.output_root.resolve()
    for scratch in (Path("/scratch"), Path("/iridisfs/scratch")):
        if dest == scratch or scratch in dest.parents: ap.error("output under scratch is not allowed")
    if dest.exists() and any(dest.iterdir()): ap.error("output directory must be new or empty")
    dest.mkdir(parents=True, exist_ok=True)
    df, meta, available = annual_data(core, stages)
    interim = any(len(stages[p]["years"]) != stages[p]["expected_years"] for p, *_ in PHASES)
    df.to_csv(dest / "NL-Loo_carbon_annual_means.csv", index=False)
    phase_metrics(core, df, meta).to_csv(dest / "NL-Loo_normal_phase_trends.csv", index=False)
    plot_carbon(core, df, meta, dest, interim)
    candidates, notes = latest_normal_cycles(core, stages, a.cases_root, a.archive_root)
    ec_phase, gpp_cols, prov, frequency, cycle = None, [], [], "", []
    for stage, first, last, align, cy in candidates:
        try:
            model, frequency = core.fates_samples([(y, stages[stage]["found"][y]) for y in cy], first, last, align)
            src = core.ec_sources(a.sites_root / SITE / "forcing")
            obs, prov = core.ec_daily(src, first, last, 40)
            daily, monthly = core.paired_monthly(model, obs, frequency, 20)
            for flux in ("GPP", "NEE"):
                if len(monthly[[f"EC_{flux}", f"FATES_{flux}"]].dropna()) < 2:
                    raise ValueError(f"{flux}: fewer than two paired months")
            gpp_cols = sorted({c for c in obs.EC_GPP_column.dropna() if c})
            monthly.to_csv(dest / "NL-Loo_monthly_FATES_vs_EC.csv", index=False)
            if daily is not None: daily.to_csv(dest / "NL-Loo_daily_FATES_vs_EC.csv", index=False)
            plot_ec(core, monthly, stage, cy, first, last, " + ".join(gpp_cols), dest,
                    interim or stage != "POST300").to_csv(dest / "NL-Loo_flux_metrics.csv", index=False)
            ec_phase, cycle = stage, cy
            break
        except Exception as exc:
            notes.append(f"{stage} EC: {type(exc).__name__}: {exc}")
    meta_out = {"site": SITE, "interim": interim, "ec_phase": ec_phase,
                "ec_interim": interim or ec_phase != "POST300",
                "phase_years": {p: len(stages[p]["years"]) for p, *_ in PHASES},
                "phase_issues": {p: stages[p]["issue"] for p, *_ in PHASES},
                "carbon_variables_by_phase": available, "carbon_units": meta,
                "missing_primary_carbon_by_phase": {p: [n for n in ("TOTECOSYSC", "TOTSOMC", "FATES_VEGC") if n not in available.get(p, [])] for p in available},
                "ec_model_cycle": [cycle[0], cycle[-1]] if cycle else [], "model_frequency": frequency,
                "ec_sources": prov, "gpp_columns": gpp_cols, "ec_notes": notes,
                "caveat": "Phase transitions may rescale carbon pools; no trajectory is drawn across the discontinuity. EC day pairing uses native timestamps; check clock provenance."}
    (dest / "NL-Loo_metadata.json").write_text(json.dumps(meta_out, indent=2, default=str) + "\n", encoding="utf-8")
    print("OUTPUT:", dest, "EC:", ec_phase or "UNAVAILABLE", "INTERIM:", interim, flush=True)
    if notes: print("NOTES:", " | ".join(notes), flush=True)
    if a.publish: publish(dest, meta_out)
    return int(ec_phase is None)


if __name__ == "__main__":
    raise SystemExit(main())
