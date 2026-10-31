#!/usr/bin/env python3
"""ICOS 38-site AD400/Normal400 GPP, NEE, NPP and LAI diagnostic plots.

This script reads model histories and tower files; it does not modify cases.
Only genuine AD400->Normal400 reference pairs are drawn as 800-year sequences.
All 38 requested sites get a manifest row, including missing and ambiguous cases.
"""
import argparse
import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SITES = ("DE-Tha NL-Loo DE-Hai RU-Fyo DK-Sor IL-Yat CZ-BK1 IT-Ren FR-Hes FR-FBn "
         "DE-Hzd CH-Dav BE-Vie IT-Lav BE-Bra FR-Fon GL-ZaH IT-Noe AT-Neu FI-Sod "
         "CH-Aws CH-Cha CH-Fru CH-Lae CZ-Stn DE-Lnf DE-Obe ES-Agu ES-LJu IT-Col "
         "DE-Gri DE-RuR FI-Hyy FI-Let FR-Pue GF-Guy IT-MBo IT-Tor").split()
VARIABLES = {"GPP": ("FATES_GPP", 1), "NEE": ("FATES_NEP", -1),
             "NPP": ("FATES_NPP", 1), "LAI": ("TLAI", 1)}
MONTH_DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def model_year(core, year, spin, phase, paths):
    """Duration-weighted monthly means from one complete native model year."""
    from netCDF4 import Dataset
    dates, weights = [], []
    values = {name: [] for name in VARIABLES}
    missing = set()
    for path in paths:
        with Dataset(str(path)) as ds:
            b = next((n for n in ("time_bounds", "time_bnds") if n in ds.variables), None)
            if not b:
                raise ValueError(f"{path.name}: missing time bounds")
            bounds = np.asarray(ds.variables[b][:], dtype=float)
            if bounds.ndim != 2 or bounds.shape[1] != 2:
                raise ValueError(f"{path.name}: unexpected time bounds")
            durations = bounds[:, 1] - bounds[:, 0]
            if not np.all(np.isfinite(durations) & (durations > 0)):
                raise ValueError(f"{path.name}: invalid time bounds")
            d = core.noleap_dates(ds)
            dates.extend(d); weights.extend(durations)
            for label, (field, sign) in VARIABLES.items():
                if field not in ds.variables:
                    missing.add(label)
                    values[label].extend([np.nan] * len(d))
                    continue
                var = ds.variables[field]
                u = str(getattr(var, "units", "")).replace(" ", "").lower()
                if label != "LAI" and u and not ("kg" in u and ("s-1" in u or "/s" in u)):
                    raise ValueError(f"{path.name}: unexpected {field} units {u!r}")
                scale = 1.0 if label == "LAI" else core.FATES_TO_GCD
                values[label].extend(core.point_series(var) * (sign * scale))
    expected_daily = [(year, m, d) for m, days in enumerate(MONTH_DAYS, 1) for d in range(1, days + 1)]
    expected_monthly = [(year, m, 1) for m in range(1, 13)]
    if dates != expected_daily and dates != expected_monthly:
        raise ValueError(f"{year}: history is not a complete noleap daily or monthly year")
    w = np.asarray(weights); months = np.array([d[1] for d in dates])
    if len(w) != len(dates):
        raise ValueError(f"{year}: time bounds and samples differ")
    expected_weights = np.ones(365) if dates == expected_daily else MONTH_DAYS
    if not np.allclose(w, expected_weights, rtol=0, atol=1e-5):
        raise ValueError(f"{year}: history sample durations do not match calendar days")
    rows = []
    for month in range(1, 13):
        mask = months == month
        row = {"Phase": phase, "SpinupYear": spin, "ModelYear": year, "Month": month}
        for name in VARIABLES:
            v = np.asarray(values[name], dtype=float)
            if len(v) != len(w):
                raise ValueError(f"{year}: {name} sample count mismatch")
            row[name] = float(np.average(v[mask], weights=w[mask])) if np.isfinite(v[mask]).all() else np.nan
        rows.append(row)
    return rows, missing


def ec_reference(core, site, sites_root, first, last):
    paths = core.ec_sources(sites_root / site / "forcing")
    obs, provenance = core.ec_daily(paths, first, last, 40)
    obs["year"] = obs.date.dt.year; obs["month"] = obs.date.dt.month
    result = {}
    for name in ("GPP", "NEE"):
        col = "EC_" + name
        grp = obs.groupby(["year", "month"])[col]
        monthly = grp.agg(["mean", "count"]).reset_index()
        monthly.loc[monthly["count"] < 20, "mean"] = np.nan
        good = monthly.dropna(subset=["mean"])
        monthly_clim = good.groupby("month")["mean"].mean()
        whole = []
        for year, group in good.groupby("year"):
            if sorted(group.month.tolist()) == list(range(1, 13)):
                whole.append(float(np.average(group["mean"], weights=MONTH_DAYS)))
        # Equal-weight mean of available monthly climatology, not a reconstruction
        # of missing months; no annual reference is shown unless all months exist.
        mean = float(np.average(monthly_clim.loc[list(range(1, 13))], weights=MONTH_DAYS)) if len(monthly_clim) == 12 else np.nan
        result[name] = {"mean": mean, "monthly_min": float(monthly_clim.min()) if len(monthly_clim) == 12 else np.nan,
                        "monthly_max": float(monthly_clim.max()) if len(monthly_clim) == 12 else np.nan,
                        "low": min(whole) if whole else np.nan,
                        "high": max(whole) if whole else np.nan,
                        "complete_years": len(whole), "months": len(monthly_clim)}
    counts = obs.loc[obs.EC_GPP.notna(), "EC_GPP_column"].value_counts().to_dict()
    return result, provenance, {str(k): int(v) for k, v in counts.items()}


def plot_site(frame, ref, counts, site, case, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
    for ax, name in zip(axes, VARIABLES):
        for phase, color in (("AD", "#ba514b"), ("NORMAL", "#246eaa")):
            part = frame[frame.Phase == phase]
            if part.empty:
                continue
            xx = part.SpinupYear.to_numpy() - 1 + (part.Month.to_numpy() - 0.5) / 12
            ax.plot(xx, part[name], lw=.35, color=color, alpha=.5)
            annual = pd.Series({int(y): np.average(g[name], weights=MONTH_DAYS)
                                if len(g) == 12 and np.isfinite(g[name]).all() else np.nan
                                for y, g in part.groupby("SpinupYear", sort=True)})
            ax.plot(annual.index - .5, annual, lw=1.15, color=color, label=phase + " annual mean")
        if name in ref and np.isfinite(ref[name]["mean"]):
            t = ref[name]
            partition = "NT" if counts.get("GPP_NT_VUT_REF", 0) and not counts.get("GPP_DT_VUT_REF", 0) else (
                "NT+DT" if counts.get("GPP_NT_VUT_REF", 0) else "DT")
            lab = f"EC {partition} reference" if name == "GPP" else "EC NEE reference"
            ax.axhline(t["mean"], color="black", lw=1, ls="--", label=lab)
            ax.axhline(t["monthly_min"], color="0.35", lw=.7, ls="-.", label="EC climatological month min/max")
            ax.axhline(t["monthly_max"], color="0.35", lw=.7, ls="-.")
            if t["complete_years"]:
                ax.axhspan(t["low"], t["high"], color="0.6", alpha=.14, label="EC range: years with 12 valid months")
        if frame[name].notna().sum() == 0:
            ax.text(.5, .5, "Not available in history", ha="center", va="center", transform=ax.transAxes)
        ax.axvline(400, ls=":", color="0.3", lw=.9)
        ax.set_ylabel(name + (" (m² m⁻²)" if name == "LAI" else " (g C m⁻² d⁻¹)"))
        ax.grid(alpha=.2)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=8)
    axes[-1].set_xlabel("Spin-up year (AD 1–400; Normal 401–800)")
    fig.suptitle(f"{site} | AD400 → Normal400 | {case}\nThin: monthly mean; thick: annual mean; dashed: EC reference", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .95))
    target = out / f"{site}_03_GPP_NEE_full_sequence_AD400_NORMAL400.png"
    fig.savefig(target, dpi=170, bbox_inches="tight"); plt.close(fig)
    return target


def plot_overviews(annual_by_site, ref_by_site, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for name in ("GPP", "NEE"):
        fig, axes = plt.subplots(8, 5, figsize=(20, 22), sharex=True, squeeze=False)
        for ax, site in zip(axes.flat, SITES):
            if site not in annual_by_site:
                ax.text(.5, .5, "No verified complete pair", ha="center", va="center", transform=ax.transAxes, fontsize=8)
            else:
                frame = annual_by_site[site]
                for phase, color in (("AD", "#ba514b"), ("NORMAL", "#246eaa")):
                    part = frame[frame.Phase == phase]
                    ax.plot(part.SpinupYear, part[name], color=color, lw=.8)
                ref = ref_by_site.get(site, {}).get(name, {})
                if np.isfinite(ref.get("mean", np.nan)):
                    ax.axhline(ref["mean"], color="0.2", ls="--", lw=.7)
            ax.axvline(400.5, color="0.5", lw=.6, ls=":")
            ax.set_title(site, fontsize=9); ax.grid(alpha=.15)
        for ax in list(axes.flat)[len(SITES):]: ax.set_visible(False)
        fig.suptitle(f"ICOS 38 | {name}: AD (red), Normal (blue), EC reference (dashed)\n"
                     "Annual means; EC GPP uses NT first with explicit DT fallback", fontsize=13)
        fig.supxlabel("Spin-up year"); fig.supylabel(f"{name} (g C m⁻² d⁻¹)")
        fig.tight_layout(rect=(0.03, 0.02, 1, .96))
        fig.savefig(out / f"ALL_38_{name}_full_sequence_overview.png", dpi=150, bbox_inches="tight")
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-root", required=True, type=Path)
    a = ap.parse_args()
    out = a.output_root.expanduser().resolve()
    if any(out == p or p in out.parents for p in (Path("/scratch"), Path("/iridisfs/scratch"))):
        raise ValueError("Output must not be under scratch")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be new or empty")
    core = load("plot_core", HERE / "plot.py")
    scan = load("scan", HERE / "scan.py")
    allsites = load("all_sites", HERE / "run.py")
    q = allsites.verified_queue(scan.USER); scan.queue = lambda: q
    rows = scan.scan(None, True, False)
    by_name = {r["name"]: r for r in rows}
    out.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(archive_root=scan.OUT / "archive", cases_root=scan.BASE / "cases")
    results, annual_by_site, ref_by_site = [], {}, {}
    for site in SITES:
        record = {"Site": site, "Status": "MISSING", "Normal_case": "", "AD_case": "", "Error": ""}
        print(f"\n== {site} ==", flush=True)
        try:
            options = [r for r in rows if r["site"] == site and r["mode"] == "NORMAL" and r["verdict"] == "DONE"
                       and r.get("refcase") in by_name and by_name[r["refcase"]]["site"] == site
                       and by_name[r["refcase"]]["mode"] == "AD" and by_name[r["refcase"]]["verdict"] == "DONE"]
            if len(options) != 1:
                raise ValueError(f"{len(options)} completed AD-to-Normal pairs; choose an explicitly verified case or report unavailable")
            normal = options[0]; ad = by_name[normal["refcase"]]
            record.update(Normal_case=normal["name"], AD_case=ad["name"])
            allsites.restart_check(scan, ad); allsites.restart_check(scan, normal)
            stream, _, _ = allsites.stream_status(scan, ad["name"], normal["name"])
            record["Stream_comparison"] = stream
            pair = {"site": site, "ad": ad["name"], "normal": normal["name"],
                    "ad_case_dir": settings.cases_root / ad["name"]}
            inv = core.inventory(pair, settings)
            if not inv["complete"]:
                raise ValueError(f"Incomplete history: AD {len(inv['ad_years'])}/400; Normal {len(inv['normal_years'])}/400")
            model, missing = [], set()
            jobs = [(i + 1, y, "AD", inv["fad"][y]) for i, y in enumerate(inv["ad_years"])]
            jobs += [(401 + i, y, "NORMAL", inv["fno"][y]) for i, y in enumerate(inv["normal_years"])]
            for i, (spin, year, phase, paths) in enumerate(jobs):
                block, absent = model_year(core, year, spin, phase, paths)
                model.extend(block); missing.update(absent)
                if (i + 1) % 100 == 0: print(f"  model years {i + 1}/800", flush=True)
            frame = pd.DataFrame(model)
            if not frame.GPP.notna().any() and not frame.NEE.notna().any():
                raise ValueError("No model GPP or NEE history")
            ref, provenance, counts = {}, [], {}
            try:
                first, last, _ = inv["forcing"]
                ref, provenance, counts = ec_reference(core, site, scan.BASE / "sites/MY_EC_SITE", first, last)
            except Exception as exc:
                record["EC_error"] = f"{type(exc).__name__}: {exc}"
                print("  EC unavailable:", record["EC_error"], flush=True)
            dest = out / site / normal["name"]; dest.mkdir(parents=True)
            plot_site(frame, ref, counts, site, normal["name"], dest)
            frame.to_csv(dest / f"{site}_model_monthly_derived.csv", index=False)
            metadata = {"site": site, "ad_case": ad["name"], "normal_case": normal["name"],
                        "gpp_policy": "NT preferred each day across sources; DT only on days with no valid NT",
                        "gpp_valid_days_by_partition": counts, "ec_sources": provenance,
                        "ec_reference": ref, "missing_model_fields": sorted(missing),
                        "stream_comparison": stream, "ec_error": record.get("EC_error", "")}
            (dest / f"{site}_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n")
            ec_ok = all(k in ref and np.isfinite(ref[k]["mean"]) for k in ("GPP", "NEE"))
            core_model_ok = frame.GPP.notna().all() and frame.NEE.notna().all()
            status = "PARTIAL_MODEL" if not core_model_ok else ("OK" if ec_ok else "MODEL_ONLY_OR_INCOMPLETE_EC")
            record.update(Status=status, NT_days=counts.get(core.GPP_NT, 0),
                          DT_days=counts.get(core.GPP_DT, 0), Output_directory=str(dest),
                          Missing_model_fields="+".join(sorted(missing)))
            annual_by_site[site] = pd.DataFrame([{"SpinupYear": int(y), "Phase": g.Phase.iloc[0],
                **{n: float(np.average(g[n], weights=MONTH_DAYS)) if len(g) == 12 and np.isfinite(g[n]).all() else np.nan
                   for n in ("GPP", "NEE")}} for y, g in frame.groupby("SpinupYear", sort=True)])
            ref_by_site[site] = ref
            print("  DONE:", record["Status"], "NT days:", record["NT_days"], "DT days:", record["DT_days"], flush=True)
        except Exception as exc:
            record["Error"] = f"{type(exc).__name__}: {exc}"
            print("  UNAVAILABLE:", record["Error"], flush=True)
        results.append(record)
        save(out, results)
    plot_overviews(annual_by_site, ref_by_site, out)
    print(f"\nCompleted {sum(r['Status'] == 'OK' for r in results)} with EC out of {len(SITES)} sites.")
    print("Manifest:", out / "site_status.csv")
    return int(any(r["Status"] != "OK" for r in results))


def save(out, rows):
    fields = sorted({k for row in rows for k in row})
    tmp = out / ".site_status.tmp"
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    tmp.replace(out / "site_status.csv")


if __name__ == "__main__":
    raise SystemExit(main())

