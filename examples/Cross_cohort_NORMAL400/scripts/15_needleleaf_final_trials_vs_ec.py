#!/usr/bin/env python3
"""Final needleleaf trials (13, variants D and F, 100 years) against the EC towers: which parameter set to adopt.

For every site it reads, year by year (annual means of monthly history):
  * the original AD400 case, first <years> years = control with default parameters
  * <AD>_FIXD<years> and <AD>_FIXF<years> = trials
quantities: FATES_GPP (total), TLAI, and, where written, needleleaf (PFT 2) GPP, vegetation C and
density (FATES_GPP_PF, FATES_VEGC_PF, FATES_NPLANT_PF). The EC reference is the tower's mean annual
GPP from the 07 / Stage15 readers (NT before DT, same coverage rules as all other figures).

Per case:
  GPP_last20 / EC          ratio of the mean of the last 20 years to the EC mean
  trend_last30_pct_decade  linear trend of annual GPP over the last 30 years, % of the mean per decade
                           (|trend| <= 5 %/decade = "stable")
  needleleaf_alive         needleleaf vegetation C in the last 5 years >= 10 % of its maximum
A variant is ranked by: sites alive, then sites within +/-25 % of EC, then sites stable, then median |log ratio|.

Outputs (never under scratch):
  <out>/<site>/<site>_final_trials_annual.csv, <site>_final_trials.png
  <out>/final_trials_summary.csv, final_trials_decision.txt, ALL_SITES_final_trials_ratio.png, RUN_COMPLETE.json
Usage (login node):
  python -B 15_...py --output-root DIR [--sites ...] [--variants D F] [--years 100]
  python -B 15_...py --publish-run DIR
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
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIG_DIR = "figures/AD400_NORMAL400_needleleaf_final_trials"
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], float)
SCALARS = ["FATES_GPP", "TLAI"]
PFTVARS = ["FATES_GPP_PF", "FATES_VEGC_PF", "FATES_NPLANT_PF"]
NEEDLE = 2
STABLE = 5.0
T13 = None
F7 = P = R = None


def load_modules():
    global T13, F7, P, R
    for c in (HERE / "13_needleleaf_param_trials.py", HERE / "trials.py"):
        if c.is_file():
            spec = importlib.util.spec_from_file_location("trial13", c)
            T13 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(T13)
            break
    else:
        raise FileNotFoundError("13_needleleaf_param_trials.py (trials.py) not found beside this script")
    T13.load09()
    R = T13.R
    F7, P = R.load07()
    F7.P = P


# ------------------------------------------------------------------ reading
def arr(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    return a


def by_time(var):
    a = arr(var)
    dims = list(var.dimensions)
    a = np.moveaxis(a, dims.index("time"), 0)
    return a.reshape(a.shape[0], -1)


def gfac(units):
    u = (units or "").replace(" ", "").lower()
    return 1000.0 * 86400 if u.startswith("kg") else 86400.0


def read_year(paths):
    """Annual means (time-weighted) of the scalars and needleleaf per-PFT quantities."""
    from netCDF4 import Dataset
    acc, wsum = {}, {}
    for path in paths:
        with Dataset(str(path)) as ds:
            bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
            b = np.asarray(ds.variables[bname][:], float)
            w = b[:, 1] - b[:, 0]
            for n in SCALARS + PFTVARS:
                if n not in ds.variables or "time" not in ds.variables[n].dimensions:
                    continue
                v = by_time(ds.variables[n])
                if n in PFTVARS:
                    if v.shape[1] < NEEDLE:
                        continue
                    x = v[:, NEEDLE - 1]
                else:
                    x = v[:, 0]
                u = str(getattr(ds.variables[n], "units", ""))
                if n in ("FATES_GPP", "FATES_GPP_PF"):
                    x = x * gfac(u)
                elif n == "FATES_VEGC_PF" and u.replace(" ", "").lower().startswith("kg"):
                    x = x * 1000.0
                elif n == "FATES_NPLANT_PF" and "m-2" in u.replace(" ", ""):
                    x = x * 1e4
                ok = np.isfinite(x)
                acc[n] = acc.get(n, 0.0) + float(np.sum(x[ok] * w[ok]))
                wsum[n] = wsum.get(n, 0.0) + float(np.sum(w[ok]))
    return {n: acc[n] / wsum[n] for n in acc if wsum[n] > 0}


def annual_series(case, years, args):
    fidx = P.history_index(args.archive_root, case)
    yrs = sorted(fidx)[:years]
    rows = []
    for k, y in enumerate(yrs):
        rows.append({"Year": k + 1, "ModelYear": y, **read_year(fidx[y])})
        if (k + 1) % 25 == 0:
            print(f"    {case}: {k + 1}/{len(yrs)} years", flush=True)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ metrics
def metrics(df, ec):
    m = {"years_read": int(len(df))}
    if df.empty or "FATES_GPP" not in df:
        return m
    g = df["FATES_GPP"].to_numpy(float)
    m["GPP_last20"] = float(np.nanmean(g[-20:]))
    m["GPP_max_annual"] = float(np.nanmax(g))
    m["GPP_ratio_EC"] = m["GPP_last20"] / ec if ec and ec > 0 else np.nan
    if len(g) >= 30:
        y = g[-30:]; x = np.arange(30)
        ok = np.isfinite(y)
        if ok.sum() > 10 and np.nanmean(y) > 1e-3:
            slope = np.polyfit(x[ok], y[ok], 1)[0]
            m["trend_last30_pct_decade"] = float(100 * slope * 10 / np.nanmean(y))
    if "TLAI" in df:
        m["LAI_last20"] = float(np.nanmean(df["TLAI"].to_numpy(float)[-20:]))
    if "FATES_VEGC_PF" in df:
        v = df["FATES_VEGC_PF"].to_numpy(float)
        m["needle_VEGC_last5"] = float(np.nanmean(v[-5:]))
        m["needleleaf_alive"] = bool(np.nanmax(v) > 0 and np.nanmean(v[-5:]) >= 0.1 * np.nanmax(v))
    elif "TLAI" in df:   # control runs without per-PFT output: use LAI
        l = df["TLAI"].to_numpy(float)
        m["needleleaf_alive"] = bool(np.nanmax(l) > 0 and np.nanmean(l[-5:]) >= 0.1 * np.nanmax(l))
    if "FATES_GPP_PF" in df:
        m["needle_GPP_share_last20"] = float(np.nanmean(df["FATES_GPP_PF"].to_numpy(float)[-20:]) / max(m["GPP_last20"], 1e-9))
    if "FATES_NPLANT_PF" in df:
        m["needle_plants_ha_last5"] = float(np.nanmean(df["FATES_NPLANT_PF"].to_numpy(float)[-5:]))
    t = m.get("trend_last30_pct_decade")
    m["stable"] = bool(t is not None and abs(t) <= STABLE)
    return m


def ec_mean(site, normal, args):
    cd = args.cases_root / normal
    rd = R.run_dir(normal) if hasattr(R, "run_dir") else args.archive_root.parent / normal / "run"
    first, last, _ = P.forcing_years(cd, rd)
    ref, _ = F7.ec_reference(site, first, last, args)
    return ref.get("EC_GPP_mean", np.nan), ref


def decide(rows, variants, years=100):
    lines, score = [], {}
    inc = [f"{r['Site']} {r['Variant']} ({r.get('years_read', 0)} y)" for r in rows
           if r.get("Status") == "INCOMPLETE" and r["Variant"] != "control"]
    if inc:
        lines.append(f"INTERIM: {len(inc)} trial cases have fewer than {years} years yet; numbers use the years available "
                     f"(stability needs >= 30 years): " + ", ".join(inc))
    for v in ["control"] + list(variants):
        g = [r for r in rows if r["Variant"] == v and r.get("Status") in ("OK", "INCOMPLETE") and r.get("years_read", 0) >= 20]
        rat = np.array([r.get("GPP_ratio_EC", np.nan) for r in g], float)
        ok = np.isfinite(rat) & (rat > 0)
        s = {"sites": len(g), "alive": sum(bool(r.get("needleleaf_alive")) for r in g),
             "stable": sum(bool(r.get("stable")) for r in g),
             "within25": int(np.sum(np.abs(rat[ok] - 1) <= 0.25)),
             "median_ratio": float(np.median(rat[ok])) if ok.any() else np.nan,
             "median_abs_log_ratio": float(np.median(np.abs(np.log(rat[ok])))) if ok.any() else np.nan}
        score[v] = s
        lines.append(f"{v:8}: alive {s['alive']}/{s['sites']}, stable {s['stable']}/{s['sites']}, within +/-25% of EC "
                     f"{s['within25']}/{s['sites']}, median GPP/EC {s['median_ratio']:.2f}, median |log ratio| {s['median_abs_log_ratio']:.2f}")
    cand = [v for v in variants if v in score and np.isfinite(score[v]["median_abs_log_ratio"])]
    if cand:
        best = sorted(cand, key=lambda v: (-score[v]["alive"], -score[v]["within25"], -score[v]["stable"],
                                            score[v]["median_abs_log_ratio"]))[0]
        lines.append(f"RECOMMENDED: {best} (ranking: most sites alive, most within +/-25 % of EC, most stable, "
                     f"then smallest median |log GPP/EC|)")
        over = [r["Site"] for r in rows if r["Variant"] == best and r.get("GPP_ratio_EC", 0) > 1.25]
        under = [r["Site"] for r in rows if r["Variant"] == best and 0 < r.get("GPP_ratio_EC", 0) < 0.75]
        unstable = [r["Site"] for r in rows if r["Variant"] == best and r.get("Status") in ("OK", "INCOMPLETE")
                    and not r.get("stable")]
        lines.append(f"   with {best}: over-estimate (>1.25) {over or 'none'}; under-estimate (<0.75) {under or 'none'}; "
                     f"not yet stable {unstable or 'none'}")
    return lines, score


# ------------------------------------------------------------------ plots
def plot_site(site, series, ec, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.2), constrained_layout=True)
    col = {"control": "0.4", "D": "C3", "F": "C0"}
    for v, df in series.items():
        if df is None or df.empty:
            continue
        c = col.get(v, None)
        if "FATES_GPP" in df:
            ax[0].plot(df["Year"], df["FATES_GPP"], color=c, lw=2, label=v)
        if "TLAI" in df:
            ax[1].plot(df["Year"], df["TLAI"], color=c, lw=2, label=v)
        if "FATES_VEGC_PF" in df:
            ax[2].plot(df["Year"], df["FATES_VEGC_PF"], color=c, lw=2, label=v)
    if np.isfinite(ec):
        ax[0].axhline(ec, color="k", ls="--", lw=1.5, label="EC mean")
        ax[0].axhspan(0.75 * ec, 1.25 * ec, color="k", alpha=0.07)
    for a, t in zip(ax, ["GPP (g C m$^{-2}$ d$^{-1}$)", "LAI", "needleleaf vegetation C (g C m$^{-2}$)"]):
        a.set_title(t); a.set_xlabel("AD year"); a.grid(alpha=0.3); a.legend(fontsize=8)
    fig.suptitle(f"{site}: default (control) vs trial D (cushion 2.4 + slatop 0.010) vs F (cushion 2.4 + slatop 0.008); "
                 "grey band = EC +/-25 %")
    fig.savefig(dest / f"{site}_final_trials.png", dpi=130); plt.close(fig)


def plot_all(rows, root, variants):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sites = sorted({r["Site"] for r in rows})
    fig, ax = plt.subplots(figsize=(max(8, 1.0 * len(sites) + 3), 4.5), constrained_layout=True)
    w = 0.8 / (len(variants) + 1)
    for k, v in enumerate(["control"] + list(variants)):
        y = [next((r.get("GPP_ratio_EC", np.nan) for r in rows if r["Site"] == s and r["Variant"] == v), np.nan) for s in sites]
        ax.bar(np.arange(len(sites)) + (k - len(variants) / 2) * w, y, w, label=v,
               color={"control": "0.6", "D": "C3", "F": "C0"}.get(v))
    ax.axhline(1, color="k"); ax.axhspan(0.75, 1.25, color="k", alpha=0.07)
    ax.set_xticks(range(len(sites))); ax.set_xticklabels(sites, rotation=30)
    ax.set_ylabel("GPP last 20 y / EC"); ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.savefig(root / "ALL_SITES_final_trials_ratio.png", dpi=130); plt.close(fig)


# ------------------------------------------------------------------ run / publish
def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for site in a.sites:
        dest = a.output_root / site
        dest.mkdir(exist_ok=True)
        series, ec = {}, np.nan
        try:
            i0 = R.ident(site, F7, P, a.years)
            normal, ad = i0["normal"], i0["ad"]
            ec, ref = ec_mean(site, normal, a)
            print(f"[{site}] EC GPP mean {ec:.2f} ({ref.get('EC_sources', '')})", flush=True)
        except Exception as exc:
            print(f"[{site}] FAILED to identify cases / EC: {exc}", flush=True)
            rows.append({"Site": site, "Variant": "-", "Status": "FAILED", "Error": f"{type(exc).__name__}: {exc}"})
            continue
        cases = [("control", ad)] + [(v, T13.ident(site, v, F7, P, a.years)["new"]) for v in a.variants]
        for v, case in cases:
            rec = {"Site": site, "Variant": v, "Case": case, "EC_GPP_mean": ec, "Status": "FAILED"}
            try:
                df = annual_series(case, a.years, a)
                series[v] = df
                df.to_csv(dest / f"{site}_{v}_annual.csv", index=False)
                rec.update(metrics(df, ec), Status="OK" if len(df) >= a.years else "INCOMPLETE")
            except Exception as exc:
                rec["Error"] = f"{type(exc).__name__}: {exc}"
                (dest / f"ERROR_{v}.txt").write_text(traceback.format_exc())
            rows.append(rec)
            f = lambda k: f"{rec[k]:.2f}" if isinstance(rec.get(k), float) and np.isfinite(rec[k]) else "-"
            print(f"  {site} {v:7} {rec['Status']:10} GPP last20 {f('GPP_last20')} / EC {ec:.2f} = {f('GPP_ratio_EC')} | "
                  f"trend {f('trend_last30_pct_decade')} %/dec | LAI {f('LAI_last20')} | alive {rec.get('needleleaf_alive', '-')} "
                  f"{rec.get('Error', '')}", flush=True)
        if series:
            try:
                plot_site(site, series, ec, dest)
            except Exception as exc:
                print(f"  plot failed: {exc}", flush=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (a.output_root / "final_trials_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    lines, score = decide(rows, a.variants, a.years)
    (a.output_root / "final_trials_decision.txt").write_text("\n".join(lines) + "\n")
    try:
        plot_all([r for r in rows if r.get("Status") in ("OK", "INCOMPLETE")], a.output_root, a.variants)
    except Exception as exc:
        print(f"overview plot failed: {exc}", flush=True)
    print("\n" + "\n".join(lines), flush=True)
    ok = sum(r.get("Status") == "OK" for r in rows)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(rows), "sites": a.sites, "variants": a.variants, "years": a.years,
         "score": score, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2, default=str) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(rows)} cases OK. Summary: {a.output_root / 'final_trials_summary.csv'}", flush=True)
    return 0


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    with tempfile.TemporaryDirectory(prefix="final_trials_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        for n in ("final_trials_summary.csv", "final_trials_decision.txt", "ALL_SITES_final_trials_ratio.png"):
            if (run_dir / n).is_file():
                shutil.copyfile(run_dir / n, out / n)
        rows = list(csv.DictReader((run_dir / "final_trials_summary.csv").open(encoding="utf-8")))
        lines = ["# Final needleleaf trials vs EC (D = cushion 2.4 + slatop 0.010, F = cushion 2.4 + slatop 0.008)", "",
                 "Control = original AD400 case (default parameters), same years. GPP_last20 = mean of the last 20 AD years.", "",
                 "```", (run_dir / "final_trials_decision.txt").read_text().rstrip(), "```", "",
                 "![ratio](ALL_SITES_final_trials_ratio.png)", "",
                 "| Site | Variant | GPP last 20 y | EC | ratio | trend %/decade | LAI | needleleaf alive | figure |",
                 "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
        f = lambda r, k: f"{float(r[k]):.2f}" if r.get(k) not in (None, "", "nan") else "–"
        for r in rows:
            s = r["Site"]
            if not F7.SAFE.fullmatch(s):
                continue
            png = run_dir / s / f"{s}_final_trials.png"
            link = ""
            if png.is_file() and F7.is_png(png):
                (out / s).mkdir(exist_ok=True)
                shutil.copyfile(png, out / s / png.name)
                link = f"[png]({s}/{png.name})"
            lines.append(f"| {s} | {r.get('Variant', '')} | {f(r, 'GPP_last20')} | {f(r, 'EC_GPP_mean')} | {f(r, 'GPP_ratio_EC')} | "
                         f"{f(r, 'trend_last30_pct_decade')} | {f(r, 'LAI_last20')} | {r.get('needleleaf_alive', '')} | {link} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add final needleleaf trials vs EC ({len(rows)} cases)", cwd=co)
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
    ap.add_argument("--variants", nargs="+", default=["D", "F"])
    ap.add_argument("--years", type=int, default=100)
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--cases-root", type=Path, default=None)
    ap.add_argument("--sites-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
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
    if not a.allow_scratch_output and any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty: " + str(root))
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
