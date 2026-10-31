#!/usr/bin/env python3
"""Read-only NL-Loo V3 full-sequence GPP diagnostic: PRE50 -> AD200 -> POST300.

Design (V3, legacy NL-Loo exception, not the AD400 -> Normal400 standard):
  spin-up years   1-50   PRE50    Normal  model years 1997-2046
  spin-up years  51-250  AD200    AD      model years 2047-2246
  spin-up years 251-550  POST300  Normal  model years 2247-2546

Reads the CLM history files (h0a, or h0 in older CTSM) of the three V3 cases and draws one 550-year axis
with annual-mean GPP (plus the peak-month GPP), NPP, LAI and, where written,
FATES vegetation carbon.

Why this is useful: CLM's AD switch only rescales the soil decomposition pools.
GPP, NPP and LAI are vegetation quantities, so they should run on continuously
across years 50/51 and 250/251. A step there means something other than the AD
rescaling changed at the hybrid restart (e.g. FATES vegetation state, forcing,
parameter file). A slow decline to zero means the vegetation is dying.

Nothing on scratch is written. The live RUNDIR is read only with --include-run
(for the phase still running); a history file being written is skipped, not
repaired.

IRIDIS6:
  conda activate clm_fates_env
  cd ~/Non-Competition-CLM-experiment
  python scripts/17_plot_NL_Loo_GPP_full_sequence.py \
      --output-dir "$HOME/NL_Loo_GPP_full_$(date -u +%Y%m%dT%H%M%SZ)" --include-run
  # optional EC reference lines (g C m-2 d-1), e.g. --ec-gpp-mean 4.2 --ec-gpp-peak 8.5
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SITE = "NL-Loo"
START = 1997
PHASES = (("PRE50", "Normal", 1997, 2047),
          ("AD200", "AD", 2047, 2247),
          ("POST300", "Normal", 2247, 2547))
CASE = {p: f"NL-Loo_OBSPFT_NC_V3_{p}" for p, *_ in PHASES}
COLORS = {"PRE50": "#1f77b4", "AD200": "#d62728", "POST300": "#2ca02c"}
# quantity -> candidate history names, first present wins
CANDIDATES = {
    "GPP": ("FATES_GPP", "GPP"),
    "NPP": ("FATES_NPP", "NPP"),
    "LAI": ("TLAI", "FATES_LAI"),
    "VEGC": ("FATES_VEGC",),
}
PLOT_UNITS = {"GPP": "g C m$^{-2}$ d$^{-1}$", "NPP": "g C m$^{-2}$ d$^{-1}$",
              "LAI": "m$^2$ m$^{-2}$", "VEGC": "g C m$^{-2}$"}
CUM = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])  # noleap month starts


# ---------------------------------------------------------------- reading
class _NC4:
    def __init__(self, ds):
        self.ds = ds
        ds.set_auto_mask(True)

    def has(self, n): return n in self.ds.variables
    def attr(self, n, k, d=""): return str(getattr(self.ds.variables[n], k, d))
    def dims(self, n): return tuple(self.ds.variables[n].dimensions)

    def values(self, n):
        v = self.ds.variables[n][:]
        return np.ma.filled(np.ma.asarray(v, dtype=float), np.nan)

    def close(self): self.ds.close()


class _SciPy:
    def __init__(self, ds): self.ds = ds
    def has(self, n): return n in self.ds.variables

    def attr(self, n, k, d=""):
        v = getattr(self.ds.variables[n], k, d)
        return v.decode() if isinstance(v, bytes) else str(v)

    def dims(self, n): return tuple(self.ds.variables[n].dimensions)

    def values(self, n):
        var = self.ds.variables[n]
        a = np.array(var.data, dtype=float)
        for k in ("_FillValue", "missing_value"):
            fv = getattr(var, k, None)
            if fv is not None:
                a[np.isclose(a, float(np.asarray(fv).ravel()[0]))] = np.nan
        a[np.abs(a) > 1e30] = np.nan
        return a

    def close(self): self.ds.close()


def open_nc(path):
    try:
        from netCDF4 import Dataset
    except ImportError:
        from scipy.io import netcdf_file  # classic / 64-bit-offset files only
        return _SciPy(netcdf_file(str(path), "r", mmap=False))
    return _NC4(Dataset(str(path), "r"))


def decode_days(days, units, calendar):
    """(year, month) of each time value. Own decoder for noleap; cftime otherwise."""
    cal = (calendar or "standard").lower()
    m = re.match(r"\s*days\s+since\s+(-?\d{1,4})-(\d{1,2})-(\d{1,2})", units or "")
    if m and cal in ("noleap", "365_day"):
        y0, m0, d0 = map(int, m.groups())
        t = CUM[m0 - 1] + d0 - 1 + np.asarray(days, dtype=float)
        years = y0 + np.floor(t / 365.0).astype(int)
        doy = t - 365.0 * np.floor(t / 365.0)
        months = np.searchsorted(CUM, doy, side="right")
        return list(zip(years.tolist(), months.tolist()))
    import cftime
    return [(d.year, d.month) for d in cftime.num2date(np.asarray(days, dtype=float), units, cal)]


def flux_factor(units, name):
    """Convert a carbon flux to g C m-2 d-1."""
    u = units.replace(" ", "").replace("^", "").lower()
    if not ("s-1" in u or "/s" in u):
        raise ValueError(f"{name}: flux units not per second: {units!r}")
    if u.startswith("kg"):
        return 1000.0 * 86400.0
    if u.startswith("g"):
        return 86400.0
    raise ValueError(f"{name}: unknown flux units {units!r}")


def stock_factor(units, name):
    u = units.replace(" ", "").lower()
    if u.startswith("kg"): return 1000.0
    if u.startswith("g"): return 1.0
    raise ValueError(f"{name}: unknown carbon stock units {units!r}")


# Recent CTSM: <case>.clm2.h0a.<date>.nc (time-averaged) and .h0i. (instantaneous);
# older CTSM: <case>.clm2.h0.<date>.nc. GPP/NPP/LAI/VEGC are averaged fields -> h0a or h0.
H0_PATTERNS = ("{case}.clm2.h0a.*.nc", "{case}.clm2.h0.*.nc")


def search_dirs(archive_root, case, include_run):
    dirs = [archive_root / case / "lnd" / "hist", archive_root / case]
    if include_run:
        dirs.append(archive_root.parent / case / "run")
    return dirs


def history_files(archive_root, case, include_run):
    found = {}
    for d in search_dirs(archive_root, case, include_run):
        if not d.is_dir():
            continue
        for pat in H0_PATTERNS:
            for p in sorted(d.glob(pat.format(case=case))):
                found.setdefault(p.name, p)  # archived copy wins over RUNDIR copy
    return [found[k] for k in sorted(found)]


def explain_missing(archive_root, case, include_run):
    """Show what is actually there when no h0/h0a file matched."""
    lines = []
    for d in search_dirs(archive_root, case, include_run):
        if not d.is_dir():
            lines.append(f"    {d}: not a directory")
            continue
        nc = sorted(p.name for p in d.glob("*.nc"))
        lines.append(f"    {d}: {len(nc)} .nc files" + (f", e.g. {nc[0]} ... {nc[-1]}" if nc else ""))
    if not (archive_root / case).is_dir():
        sub = sorted(p.name for p in archive_root.glob("NL-Loo*")) if archive_root.is_dir() else []
        lines.append(f"    NL-Loo entries under {archive_root}: {', '.join(sub) or 'none'}")
    return lines


def read_file(path, phase, used):
    ds = open_nc(path)
    try:
        if not ds.has("time"):
            raise ValueError("no time variable")
        t = np.atleast_1d(ds.values("time"))
        bname = ds.attr("time", "bounds", "") or next((b for b in ("time_bounds", "time_bnds") if ds.has(b)), "")
        if bname and ds.has(bname):
            b = ds.values(bname).reshape(len(t), 2)
            mid, weight = b.mean(axis=1), b[:, 1] - b[:, 0]
        else:  # CLM stamps the end of the averaging interval
            mid, weight = t - 0.5, np.full(len(t), np.nan)
        ym = decode_days(mid, ds.attr("time", "units"), ds.attr("time", "calendar", "noleap"))
        cols = {}
        for q, names in CANDIDATES.items():
            name = next((n for n in names if ds.has(n)), None)
            if name is None:
                continue
            dims = ds.dims(name)
            if not dims or dims[0] != "time":
                continue
            a = ds.values(name).reshape(len(t), -1)  # single point: lndgrid=1; extra dims averaged
            with np.errstate(invalid="ignore"):
                a = np.nanmean(a, axis=1)
            units = ds.attr(name, "units")
            if q in ("GPP", "NPP"):
                a = a * flux_factor(units, name)
            elif q == "VEGC":
                a = a * stock_factor(units, name)
            cols[q] = a
            used.setdefault(phase, {}).setdefault(q, set()).add(f"{name} [{units}]")
        rows = []
        for i, (y, mo) in enumerate(ym):
            r = {"Phase": phase, "Year": int(y), "Month": int(mo), "Weight_days": float(weight[i]), "File": path.name}
            r.update({q: float(v[i]) for q, v in cols.items()})
            rows.append(r)
        return rows
    finally:
        ds.close()


# ---------------------------------------------------------------- aggregation
def wmean(g, col):
    v = g[col].to_numpy(float); w = g["Weight_days"].to_numpy(float)
    ok = np.isfinite(v)
    if not ok.any(): return np.nan
    if np.all(np.isfinite(w[ok])) and w[ok].sum() > 0:
        return float(np.sum(v[ok] * w[ok]) / w[ok].sum())
    return float(v[ok].mean())


def aggregate(samples):
    qs = [q for q in CANDIDATES if q in samples]
    monthly = []
    for (p, y, m), g in samples.groupby(["Phase", "Year", "Month"], sort=True):
        r = {"Phase": p, "Year": y, "Month": m, "Weight_days": g["Weight_days"].sum(min_count=1)}
        r.update({q: wmean(g, q) for q in qs})
        monthly.append(r)
    monthly = pd.DataFrame(monthly).sort_values(["Year", "Month"], ignore_index=True)
    annual = []
    for (p, y), g in monthly.groupby(["Phase", "Year"], sort=True):
        w = g["Weight_days"].to_numpy(float)
        complete = g["Month"].nunique() == 12 and (not np.all(np.isfinite(w)) or w.sum() >= 360)
        r = {"Phase": p, "Year": y, "SpinupYear": y - START + 1, "Months": int(g["Month"].nunique()),
             "Complete": bool(complete)}
        for q in qs:
            r[q] = wmean(g, q)
        if "GPP" in qs:
            r["GPP_peak_month"] = float(g["GPP"].max())
        annual.append(r)
    return monthly, pd.DataFrame(annual).sort_values("Year", ignore_index=True)


def transition_summary(annual, n=5):
    lines, a = [], annual[annual.Complete]
    for (p0, *_), (p1, *_ ) in zip(PHASES[:-1], PHASES[1:]):
        before, after = a[a.Phase == p0].tail(n), a[a.Phase == p1].head(n)
        if before.empty or after.empty:
            lines.append(f"{p0} -> {p1}: not enough complete years on both sides")
            continue
        for q in ("GPP", "NPP", "LAI", "VEGC"):
            if q in a and before[q].notna().any() and after[q].notna().any():
                b, c = before[q].mean(), after[q].mean()
                pct = 100 * (c - b) / b if b else np.nan
                lines.append(f"{p0} -> {p1}  {q:4}: last {len(before)}y {b:9.4g}  first {len(after)}y {c:9.4g}  change {pct:+7.1f}%")
    for p, *_ in PHASES:
        s = a[a.Phase == p].tail(30)
        if len(s) >= 10 and "GPP" in s and s["GPP"].notna().sum() >= 10:
            k = np.polyfit(s.SpinupYear, s["GPP"], 1)[0]
            lines.append(f"{p:7} GPP last {len(s)}y: mean {s['GPP'].mean():.4g} g C m-2 d-1, "
                         f"trend {100 * k * 100 / s['GPP'].mean():+.1f}% per 100y" if s["GPP"].mean() else
                         f"{p:7} GPP last {len(s)}y: mean 0")
    return lines


# ---------------------------------------------------------------- plotting
def plot(annual, dest, status, ec_mean, ec_peak):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = annual[annual.Complete]
    qs = [q for q in ("GPP", "NPP", "LAI", "VEGC") if q in a and a[q].notna().any()]
    if not qs:
        raise ValueError("no GPP/NPP/LAI/VEGC values in any complete year")
    fig, axs = plt.subplots(len(qs), 1, figsize=(18, 3.4 * len(qs)), sharex=True, squeeze=False)
    for ax, q in zip(axs[:, 0], qs):
        ax.axvspan(50.5, 250.5, color="0.93", zorder=0)
        for p, mode, *_ in PHASES:
            s = a[a.Phase == p]
            if s.empty or s[q].isna().all():
                continue
            ax.plot(s.SpinupYear, s[q], color=COLORS[p], lw=1.5, label=f"{p} ({mode}) annual mean")
            if q == "GPP" and "GPP_peak_month" in s:
                ax.plot(s.SpinupYear, s["GPP_peak_month"], color=COLORS[p], lw=1, ls="--", alpha=.6,
                        label=f"{p} peak month")
        if q == "GPP":
            if ec_mean is not None:
                ax.axhline(ec_mean, color="k", lw=1, ls=":", label=f"EC annual mean {ec_mean:g}")
            if ec_peak is not None:
                ax.axhline(ec_peak, color="k", lw=1, ls="-.", label=f"EC peak month {ec_peak:g}")
        for x in (50.5, 250.5):
            ax.axvline(x, color="0.35", ls="--", lw=1)
        ax.set_ylabel(f"{q} ({PLOT_UNITS[q]})")
        ax.set_ylim(bottom=0)
        ax.grid(alpha=.25)
        ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.005, 1.0))
    axs[-1, 0].set_xlim(1, 550)
    axs[-1, 0].set_xlabel("Spin-up year: 1–50 PRE50 Normal | 51–250 AD200 (shaded) | 251–550 POST300 Normal")
    fig.suptitle(f"{SITE} V3 | full-sequence vegetation diagnostics | {status}\n"
                 "AD rescales soil pools only; GPP/NPP/LAI should be continuous at the phase boundaries")
    fig.tight_layout()
    out = dest / f"{SITE}_GPP_full_sequence_PRE_AD_POST.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-dir", type=Path, required=True, help="new or empty directory, not on scratch")
    ap.add_argument("--archive-root", type=Path, default=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/archive"))
    ap.add_argument("--include-run", action="store_true", help="also read not-yet-archived h0 files in each RUNDIR")
    ap.add_argument("--ec-gpp-mean", type=float, help="EC annual-mean GPP reference line, g C m-2 d-1")
    ap.add_argument("--ec-gpp-peak", type=float, help="EC peak-month GPP reference line, g C m-2 d-1")
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    dest = a.output_dir.expanduser().resolve()
    if not a.allow_scratch_output and any(dest == s or s in dest.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if dest.exists() and any(dest.iterdir()):
        ap.error("output directory must be new or empty: " + str(dest))

    rows, used, skipped, counts = [], {}, [], {}
    for p, mode, first, stop in PHASES:
        files = history_files(a.archive_root, CASE[p], a.include_run)
        counts[p] = len(files)
        kinds = sorted({f.name.split(".clm2.")[1].split(".")[0] for f in files})
        print(f"{p:7} {CASE[p]}: {len(files)} history files {kinds or ''}", flush=True)
        if not files:
            print("\n".join(explain_missing(a.archive_root, CASE[p], a.include_run)), flush=True)
        for f in files:
            try:
                for r in read_file(f, p, used):
                    if first <= r["Year"] < stop:
                        rows.append(r)
                    else:
                        skipped.append(f"{f.name}: sample year {r['Year']} outside {p} {first}-{stop - 1}")
            except Exception as exc:
                skipped.append(f"{f.name}: {type(exc).__name__}: {exc}")
    if not rows:
        print("ERROR: no readable history samples. Check --archive-root and case names.", file=sys.stderr)
        return 2

    samples = pd.DataFrame(rows)
    monthly, annual = aggregate(samples)
    dest.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(dest / f"{SITE}_GPP_full_sequence_monthly.csv", index=False)
    annual.to_csv(dest / f"{SITE}_GPP_full_sequence_annual.csv", index=False)

    comp = {p: int(annual[(annual.Phase == p) & annual.Complete].shape[0]) for p, *_ in PHASES}
    expected = {p: stop - first for p, _, first, stop in PHASES}
    status = " | ".join(f"{p} {comp[p]}/{expected[p]}y" for p in comp)
    if any(comp[p] < expected[p] for p in comp):
        status += " — INTERIM"
    png = plot(annual, dest, status, a.ec_gpp_mean, a.ec_gpp_peak)

    report = [f"{SITE} V3 full-sequence GPP diagnostic", status, "",
              "Variables used (first present wins):"]
    for p, *_ in PHASES:
        for q, names in sorted(used.get(p, {}).items()):
            report.append(f"  {p:7} {q:4} <- {', '.join(sorted(names))}")
        missing = [q for q in CANDIDATES if q not in used.get(p, {})]
        if counts[p] and missing:
            report.append(f"  {p:7} not in history: {', '.join(missing)}")
    report += ["", "Phase boundaries (vegetation should be continuous):"] + transition_summary(annual)
    inc = annual[~annual.Complete]
    if not inc.empty:
        report += ["", "Incomplete years (not plotted): " +
                   ", ".join(f"{r.Phase}:{r.Year}({r.Months}m)" for r in inc.itertuples())]
    if skipped:
        report += ["", f"Skipped ({len(skipped)}):"] + ["  " + s for s in skipped[:40]]
        if len(skipped) > 40:
            report.append(f"  ... {len(skipped) - 40} more")
    text = "\n".join(report) + "\n"
    (dest / f"{SITE}_GPP_full_sequence_summary.txt").write_text(text, encoding="utf-8")
    print(text, flush=True)
    print("PNG:", png, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
