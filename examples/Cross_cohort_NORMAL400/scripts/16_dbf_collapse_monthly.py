#!/usr/bin/env python3
"""Why does the DBF stand at CZ-Stn and DE-Lnf die in one winter around AD year 15?  Read-only, monthly.

The 09 diagnostic re-runs (*_DIAG50) show 14 healthy years, then storage drains to zero over one
autumn/winter and the whole stand dies of carbon starvation (water and freezing ruled out). This
reads the monthly history for the years before and after the collapse and compares them with the
same calendar months of a living DBF reference (DE-Hai NORMAL400, last years):

  leaf C, fine-root C, storage C and storage / target of the DBF (PFT 6), GPP, NPP, respiration by
  component (every maintenance / growth respiration variable written), plants, canopy vs understory
  plants, cohort / patch counts, and all phenology variables (days since cold leaf-on / -off, GDD,
  chilling / cold days, phenology status flags), plus air temperature.

Automatic checks per year (leaf season = model leaf C > 20 % of that year's maximum):
  * leaves kept into winter      DBF leaf C in Dec-Feb > 20 % of the summer maximum
  * extra leaf flushes           more than one rise of leaf C from < 20 % to > 50 % of the maximum
                                 (and cold leaf-on events from the DAYSINCE counter)
  * storage                      month of the minimum, storage / target at the minimum, months of decline
  * winter respiration           maintenance respiration Nov-Mar (g C m-2 d-1) and its share by tissue
  * stand structure              plants, canopy / understory split, cohorts
and the same numbers for the reference climatology.

Outputs (never under scratch):
  <out>/<label>/<label>_monthly.csv, <label>_16_monthly_window.png, <label>_inventory.txt
  <out>/dbf_collapse_findings.txt, dbf_collapse_yearly.csv, RUN_COMPLETE.json
Usage:
  python -B 16_...py --output-root DIR [--cases LABEL:CASE[:first|last]:YEARS ...] [--reference LABEL:CASE]
  python -B 16_...py --publish-run DIR
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
FIG_DIR = "figures/AD400_NORMAL400_dbf_collapse_monthly"
DEFAULT_CASES = ["CZ-Stn:CZ-Stn_B03_FIXNC_AD400_DIAG50", "DE-Lnf:DE-Lnf_B03_FIXNC_AD400_DIAG50"]
DEFAULT_REF = "DE-Hai_ref:DE-Hai_B01_FIXNC_NORMAL400"
PFT = 6
SCALAR_RE = re.compile(r"^(FATES_(GPP|NPP|AUTORESP|MAINT_RESP|GROWTH_RESP|.*MAINTAR.*|.*_MR$|.*RESP.*|LAI|"
                       r"LEAFC|FROOTC|STOREC|STOREC_TF|VEGC|NPLANT|NCOHORTS|NPATCHES|NCL|CANOPY_SPREAD|"
                       r"DAYSINCE.*|GDD|NCHILLDAYS|NCOLDDAYS|.*PHEN.*|.*STATUS.*|.*LEAFON.*|.*LEAFOFF.*)|TLAI|TSA|TV|T_VEG.*)$")
PF_RE = re.compile(r"^FATES_(LEAFC|FROOTC|STOREC|STOREC_TF|VEGC|NPLANT|GPP|NPP|LAI|CROWNAREA|CANOPYCROWNAREA|"
                   r"MORTALITY_CSTARV|.*MAINT.*|.*RESP.*|.*MR)_PF$")
SZ_RE = re.compile(r"^FATES_NPLANT_(CANOPY|USTORY)_SZ$")
F7 = P = None


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


def conv(name, units):
    """g C m-2 (d-1) for carbon; others unchanged."""
    u = (units or "").replace(" ", "").lower()
    if u.startswith("kg") and ("s-1" in u or "/s" in u):
        return 1000.0 * 86400.0
    if u.startswith("g") and ("s-1" in u or "/s" in u):
        return 86400.0
    if u.startswith("kg") and ("m-2" in u or "/m2" in u or "m^-2" in u):
        return 1000.0
    if name.startswith("FATES_NPLANT") and ("m-2" in u or "/m2" in u):
        return 1e4                     # plants m-2 -> ha-1
    return 1.0


def read_months(paths):
    """Monthly records with every matching variable: scalars as is, *_PF at PFT 6, *_SZ summed over size."""
    from netCDF4 import Dataset
    recs, found = [], set()
    for path in paths:
        with Dataset(str(path)) as ds:
            bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
            b = np.asarray(ds.variables[bname][:], float)
            w = b[:, 1] - b[:, 0]
            dates = P.noleap_dates(ds)
            vals = {}
            for n, v in ds.variables.items():
                if "time" not in v.dimensions or n in ("time", "time_bounds", "time_bnds"):
                    continue
                other = [d for d in v.dimensions if d not in ("time", "lndgrid")]
                try:
                    if not other and SCALAR_RE.match(n):
                        vals[n] = by_time(v)[:, 0] * conv(n, getattr(v, "units", ""))
                    elif PF_RE.match(n) and len(other) == 1:
                        a = by_time(v)
                        if a.shape[1] >= PFT:
                            vals[n] = a[:, PFT - 1] * conv(n, getattr(v, "units", ""))
                    elif SZ_RE.match(n) and len(other) == 1:
                        vals[n] = np.nansum(by_time(v), axis=1) * conv(n, getattr(v, "units", ""))
                except Exception:
                    continue
            found |= set(vals)
            for i, (yy, mm, _) in enumerate(dates):
                recs.append({"ModelYear": yy, "Month": mm, "w": w[i], **{k: x[i] for k, x in vals.items()}})
    df = pd.DataFrame(recs)
    if df.empty:
        return df, found
    g = df.groupby(["ModelYear", "Month"], sort=True)
    out = g.apply(lambda x: pd.Series({c: np.average(x[c], weights=x["w"]) if x[c].notna().all() else np.nan
                                       for c in x.columns if c not in ("ModelYear", "Month", "w")}))
    return out.reset_index(), found


def collapse_year(df, var):
    a = df.groupby("Year")[var].mean()
    if a.max() <= 0:
        return None
    low = a < 0.01 * a.max()
    for y in a.index:
        if low.loc[y:].all():
            return int(y)
    return None


def leaf_col(df):
    return next((c for c in ("FATES_LEAFC_PF", "FATES_LEAFC") if c in df), None)


def store_col(df):
    return next((c for c in ("FATES_STOREC_PF", "FATES_STOREC") if c in df), None)


def mr_cols(df):
    return [c for c in df.columns if re.search(r"MAINT|_MR($|_)|MAINTAR", c) and not c.endswith("_PF")]


def yearly_checks(df, label):
    rows = []
    lc, sc = leaf_col(df), store_col(df)
    tf = "FATES_STOREC_TF_PF" if "FATES_STOREC_TF_PF" in df else ("FATES_STOREC_TF" if "FATES_STOREC_TF" in df else None)
    for y, g in df.groupby("Year"):
        g = g.set_index("Month").reindex(range(1, 13))
        r = {"Label": label, "Year": int(y)}
        if lc:
            leaf = g[lc].to_numpy(float)
            mx = np.nanmax(leaf) if np.isfinite(leaf).any() else np.nan
            r["leafC_max"] = mx
            if mx > 0:
                r["leafC_DecFeb_frac_of_max"] = float(np.nanmean(leaf[[0, 1, 11]]) / mx)
                frac = leaf / mx
                rises = int(np.sum((frac[1:] > 0.5) & (frac[:-1] < 0.2)))
                r["leaf_flushes"] = rises
                on = np.where(frac > 0.2)[0]
                r["leaf_months"] = int(len(on))
        if "FATES_DAYSINCE_COLDLEAFON" in g:
            d = g["FATES_DAYSINCE_COLDLEAFON"].to_numpy(float)
            r["cold_leafon_events"] = int(np.sum(np.diff(d) < -15) + (d[0] < 31))
        if "FATES_DAYSINCE_COLDLEAFOFF" in g:
            d = g["FATES_DAYSINCE_COLDLEAFOFF"].to_numpy(float)
            r["cold_leafoff_events"] = int(np.sum(np.diff(d) < -15) + (d[0] < 31))
        if tf:
            s = g[tf].to_numpy(float)
            if np.isfinite(s).any():
                r["storage_TF_min"] = float(np.nanmin(s))
                r["storage_TF_min_month"] = int(np.nanargmin(s) + 1)
        if sc:
            s = g[sc].to_numpy(float)
            r["storeC_min"] = float(np.nanmin(s)) if np.isfinite(s).any() else np.nan
        mr = mr_cols(g.reset_index())
        win = [0, 1, 2, 10, 11]
        if mr:
            tot = {c: float(np.nanmean(g[c].to_numpy(float)[win])) for c in mr}
            r["winter_MR_components"] = "; ".join(f"{c} {v:.3f}" for c, v in tot.items() if np.isfinite(v))
        if "FATES_NPLANT_PF" in g:
            r["plants_ha_mean"] = float(np.nanmean(g["FATES_NPLANT_PF"]))
        for k in ("FATES_NPLANT_CANOPY_SZ", "FATES_NPLANT_USTORY_SZ", "FATES_NCOHORTS", "FATES_NPATCHES"):
            if k in g:
                r[k + "_mean"] = float(np.nanmean(g[k]))
        if "FATES_GPP" in g:
            r["GPP_mean"] = float(np.nanmean(g["FATES_GPP"]))
        rows.append(r)
    return rows


def ref_climatology(df):
    return df.groupby("Month").mean(numeric_only=True).reset_index()


def findings(results, ref_rows):
    F = []
    ref = pd.DataFrame(ref_rows)
    if not ref.empty:
        F.append("REFERENCE (living DBF, per-year medians): " + ", ".join(
            f"{k} {ref[k].median():.2f}" for k in ("leafC_DecFeb_frac_of_max", "leaf_flushes", "leaf_months",
                                                   "cold_leafon_events", "cold_leafoff_events", "storage_TF_min")
            if k in ref))
    for lab, (df, rows, cy) in results.items():
        F.append(f"\n{lab}: collapse year {cy}")
        for r in rows:
            flags = []
            if r.get("leafC_DecFeb_frac_of_max", 0) > 0.2:
                flags.append("LEAVES KEPT INTO WINTER")
            if r.get("leaf_flushes", 0) > 1 or r.get("cold_leafon_events", 0) > 1:
                flags.append("EXTRA LEAF FLUSH")
            if r.get("cold_leafoff_events", 1) == 0 and r.get("leafC_max", 0) > 0:
                flags.append("no cold leaf-off event")
            if r.get("storage_TF_min", 1) < 0.1:
                flags.append("storage exhausted")
            pr = lambda k, f="{:.2f}": (f.format(r[k]) if isinstance(r.get(k), (int, float)) and np.isfinite(r[k]) else "-")
            F.append(f"  year {r['Year']:3d}: GPP {pr('GPP_mean')}, leaf months {pr('leaf_months', '{}')}, flushes "
                     f"{pr('leaf_flushes', '{}')}, leaf-on/off events {pr('cold_leafon_events', '{}')}/{pr('cold_leafoff_events', '{}')}, "
                     f"Dec-Feb leaf C {pr('leafC_DecFeb_frac_of_max')} of max, storage/target min {pr('storage_TF_min')} "
                     f"(month {pr('storage_TF_min_month', '{}')}), plants {pr('plants_ha_mean', '{:.0f}')}"
                     + (f", canopy/understory {pr('FATES_NPLANT_CANOPY_SZ_mean', '{:.0f}')}/{pr('FATES_NPLANT_USTORY_SZ_mean', '{:.0f}')}"
                        if "FATES_NPLANT_CANOPY_SZ_mean" in r else "")
                     + (f", cohorts {pr('FATES_NCOHORTS_mean', '{:.1f}')}" if "FATES_NCOHORTS_mean" in r else "")
                     + ("  <-- " + "; ".join(flags) if flags else ""))
            if r.get("winter_MR_components"):
                F.append(f"            winter (Nov-Mar) maintenance respiration: {r['winter_MR_components']}")
    return F


def plot(lab, df, ref, cy, found, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = df["Year"] + (df["Month"] - 0.5) / 12
    rc = ref.set_index("Month") if ref is not None and not ref.empty else None
    def refline(ax, col, **kw):
        if rc is not None and col in rc:
            y0, y1 = int(df["Year"].min()), int(df["Year"].max())
            xs = np.concatenate([y + (np.arange(1, 13) - 0.5) / 12 for y in range(y0, y1 + 1)])
            ys = np.tile(rc[col].reindex(range(1, 13)).to_numpy(float), y1 - y0 + 1)
            ax.plot(xs, ys, color="0.6", ls="--", lw=1.2, label="DE-Hai climatology", **kw)
    panels = [("leaf / storage / fine-root C of PFT 6 (g C m-2)", [leaf_col(df), store_col(df), "FATES_FROOTC_PF"]),
              ("storage / target", ["FATES_STOREC_TF_PF", "FATES_STOREC_TF"]),
              ("GPP, NPP (g C m-2 d-1)", ["FATES_GPP", "FATES_NPP"]),
              ("maintenance respiration (g C m-2 d-1)", mr_cols(df)[:6]),
              ("days since cold leaf-on / leaf-off", ["FATES_DAYSINCE_COLDLEAFON", "FATES_DAYSINCE_COLDLEAFOFF"]),
              ("GDD, chilling and cold days", ["FATES_GDD", "FATES_NCHILLDAYS", "FATES_NCOLDDAYS"]),
              ("plants ha-1 (PFT 6; canopy / understory)", ["FATES_NPLANT_PF", "FATES_NPLANT_CANOPY_SZ", "FATES_NPLANT_USTORY_SZ"]),
              ("air temperature (K)", ["TSA"])]
    fig, ax = plt.subplots(len(panels), 1, figsize=(13, 2.3 * len(panels)), sharex=True, constrained_layout=True)
    for a, (title, cols) in zip(ax, panels):
        for c in [c for c in cols if c and c in df]:
            a.plot(t, df[c], lw=1.6, label=c.replace("FATES_", ""))
            if c in (leaf_col(df), "FATES_STOREC_TF_PF", "FATES_STOREC_TF", "FATES_GPP"):
                refline(a, c)
        if cy:
            a.axvline(cy, color="r", ls=":")
        a.set_title(title, fontsize=9, loc="left"); a.grid(alpha=0.3)
        if a.get_legend_handles_labels()[0]:
            a.legend(fontsize=7, ncol=3, loc="upper left")
    ax[-1].set_xlabel("AD year (monthly)")
    fig.suptitle(f"{lab}: monthly detail around the DBF collapse (red dotted = collapse year)")
    fig.savefig(dest / f"{lab}_16_monthly_window.png", dpi=120); plt.close(fig)


def load_case(case, which, years, args):
    fidx = P.history_index(args.archive_root, case)
    ys = sorted(fidx)
    ys = ys[-years:] if which == "last" else ys[:years]
    parts, found = [], set()
    for y in ys:
        d, f = read_months(fidx[y])
        parts.append(d); found |= f
    df = pd.concat(parts, ignore_index=True)
    y0 = ys[0]
    df["Year"] = df["ModelYear"] - y0 + 1
    return df, found


def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    results, all_rows = {}, []
    lab_r, case_r = a.reference.split(":", 1)
    ref, ref_rows = None, []
    try:
        print(f"[{lab_r}] reading last {a.ref_years} years of {case_r}", flush=True)
        rdf, rfound = load_case(case_r, "last", a.ref_years, a)
        ref = ref_climatology(rdf)
        ref_rows = yearly_checks(rdf, lab_r)
        all_rows += ref_rows
        (a.output_root / lab_r).mkdir(exist_ok=True)
        rdf.to_csv(a.output_root / lab_r / f"{lab_r}_monthly.csv", index=False)
    except Exception as exc:
        print(f"[{lab_r}] reference FAILED: {exc}", flush=True)
    for spec in a.cases:
        lab, case = spec.split(":", 1)
        dest = a.output_root / lab
        dest.mkdir(exist_ok=True)
        try:
            print(f"[{lab}] reading first {a.years} years of {case}", flush=True)
            df, found = load_case(case, "first", a.years, a)
            veg = "FATES_VEGC_PF" if "FATES_VEGC_PF" in df else "FATES_VEGC"
            cy = collapse_year(df, veg) if veg in df else None
            lo = max(1, (cy or a.years) - a.before)
            hi = (cy or a.years) + a.after
            win = df[(df["Year"] >= lo) & (df["Year"] <= hi)].reset_index(drop=True)
            win.to_csv(dest / f"{lab}_monthly.csv", index=False)
            (dest / f"{lab}_inventory.txt").write_text(f"case {case}\ncollapse year {cy} (from {veg})\nwindow {lo}-{hi}\n"
                                                       "variables read:\n  " + "\n  ".join(sorted(found)) + "\n")
            rows = yearly_checks(win, lab)
            all_rows += rows
            results[lab] = (win, rows, cy)
            plot(lab, win, ref, cy, found, dest)
        except Exception as exc:
            (dest / "ERROR.txt").write_text(traceback.format_exc())
            print(f"[{lab}] FAILED: {exc}", flush=True)
    F = findings(results, ref_rows)
    (a.output_root / "dbf_collapse_findings.txt").write_text("\n".join(F) + "\n")
    fields = list(dict.fromkeys(k for r in all_rows for k in r))
    with (a.output_root / "dbf_collapse_yearly.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(all_rows)
    print("\n".join(F), flush=True)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"cases": a.cases, "reference": a.reference, "ok": len(results), "total": len(a.cases),
         "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {len(results)}/{len(a.cases)}. Findings: {a.output_root / 'dbf_collapse_findings.txt'}", flush=True)
    return 0 if len(results) == len(a.cases) else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    with tempfile.TemporaryDirectory(prefix="dbf16_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        for n in ("dbf_collapse_findings.txt", "dbf_collapse_yearly.csv"):
            shutil.copyfile(run_dir / n, out / n)
        lines = ["# DBF collapse at CZ-Stn / DE-Lnf: monthly detail vs DE-Hai", "",
                 "```", (run_dir / "dbf_collapse_findings.txt").read_text().rstrip(), "```", ""]
        for d in sorted(p for p in run_dir.iterdir() if p.is_dir()):
            if not F7.SAFE.fullmatch(d.name):
                continue
            (out / d.name).mkdir(exist_ok=True)
            for f in list(d.glob("*.png")) + list(d.glob("*_inventory.txt")) + list(d.glob("*_monthly.csv")):
                if f.suffix == ".png" and not F7.is_png(f):
                    continue
                if f.stat().st_size < 8_000_000:
                    shutil.copyfile(f, out / d.name / f.name)
                    if f.suffix == ".png":
                        lines.append(f"![{d.name}]({d.name}/{f.name})")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", "Add DBF collapse monthly detail (CZ-Stn, DE-Lnf vs DE-Hai)", cwd=co)
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
    global PFT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish-run", type=Path)
    ap.add_argument("--cases", nargs="+", default=DEFAULT_CASES, metavar="LABEL:CASE")
    ap.add_argument("--reference", default=DEFAULT_REF, metavar="LABEL:CASE")
    ap.add_argument("--years", type=int, default=20, help="first N AD years read from each collapsing case")
    ap.add_argument("--ref-years", type=int, default=10, help="last N years of the reference")
    ap.add_argument("--before", type=int, default=5, help="years shown before the collapse year")
    ap.add_argument("--after", type=int, default=1)
    ap.add_argument("--pft", type=int, default=6, help="focal PFT (6 = broadleaf_colddecid_extratrop_tree)")
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    PFT = a.pft
    load_modules()
    a.archive_root = a.archive_root or Path(f"/scratch/{F7.USER}/CTSM_FATES_OUTPUTS/archive")
    if a.publish_run:
        return publish(a.publish_run, a.repo or F7.REPO)
    if not a.output_root:
        ap.error("give --output-root or --publish-run")
    root = a.output_root.expanduser().resolve()
    if not a.allow_scratch_output and any(root == s or s in root.parents for s in (Path("/scratch"), Path("/iridisfs/scratch"))):
        ap.error("output under scratch is not allowed")
    if root.exists() and any(root.iterdir()):
        ap.error("output directory must be new or empty: " + str(root))
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
