#!/usr/bin/env python3
"""Compare monthly GPP/NEE skill: earlier full-FATES competition runs vs the fixed-PFT no-competition runs.

Old (competition) metrics: <site>_monthly_metrics.csv files in a checkout of
  https://github.com/lyanyeung/CLM-FATES-single-site-workflows
  preferring spinup1000_final > spinup500_final > latest convergence snapshot per site.
New (no-competition) metrics: read by OCR (tesseract) from the titles of the published
  <site>_GPP_NEE_monthly_overview.png figures of job 4764252, because only PNGs were published.
  Each value is checked (RMSE >= |bias|); a figure whose titles cannot be read is reported, not guessed.
Old dominant PFT: carbon_flux_convergence_diagnostics/data/15_site_ec_observed_vegetation_and_fates_match.csv.

Outputs in --outdir: nocomp_EC_metrics_from_figure_titles.csv, competition_vs_nocomp_GPP_NEE_monthly_metrics.csv,
and a printed summary (overall and by IGBP class from this repository's site registers).

Differences to keep in mind (not corrected here):
  - EC GPP: old runs default GPP_DT_VUT_REF, new runs GPP_NT_VUT_REF first (NEE_VUT_REF in both).
  - Old metrics come from 1000-year, 500-year or snapshot cycles; new from the last complete Normal400 cycle.
  - Model NEE = -FATES_NEP in both. R2 = 1 - SSE/SST.

Usage:
  python 02_compare_competition_vs_nocomp_flux_metrics.py --new-figs <repo>/figures/AD400_NORMAL400/20261030T053000Z_job4764252 \
      --old-repo <checkout of CLM-FATES-single-site-workflows> --registers <repo>/data --outdir OUT
  [--extra SITE:GPP_N,GPP_R2,GPP_RMSE,GPP_BIAS,NEE_N,NEE_R2,NEE_RMSE,NEE_BIAS]  e.g. NL-Loo V3 PRE50 values
Requires: tesseract, Pillow, pandas.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from PIL import Image

NUM = r"(-?\d+\.\d+)"
PAT = re.compile(r"(GPP|NEE)\s*\|?\s*monthly\s*N\s*=\s*(\d+)\s*,\s*R\S{0,2}\s*=\s*" + NUM +
                 r"\s*,\s*RMSE\s*=\s*" + NUM + r"\s*,\s*bias\s*=\s*" + NUM)
KEYS = ("N", "R2", "RMSE", "Bias")


def ocr_titles(png):
    """Scan the two subplot-title bands of a Stage15 EC overview figure."""
    im = Image.open(png).convert("L")
    w, h = im.size
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        t_png = os.path.join(tmp, "band.png")
        for flux, lo, hi in (("GPP", 0.05, 0.13), ("NEE", 0.48, 0.57)):
            y = lo
            while y < hi and flux not in out:
                band = im.crop((int(w * 0.25), int(h * y), int(w * 0.78), int(h * (y + 0.032))))
                band.resize((band.width * 3, band.height * 3), Image.LANCZOS).save(t_png)
                txt = subprocess.run(["tesseract", t_png, "-", "--psm", "7"], capture_output=True, text=True).stdout
                m = PAT.search(txt.replace("−", "-").replace("—", "-"))
                if m and m.group(1) == flux:
                    vals = (int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)))
                    if vals[2] + 1e-3 >= abs(vals[3]):  # RMSE >= |bias| sanity check
                        out[flux] = vals
                y += 0.004
    return out


def new_metrics(fig_dir):
    rows = []
    for p in sorted(glob.glob(os.path.join(fig_dir, "*", "*", "*_GPP_NEE_monthly_overview.png"))):
        site = os.path.basename(p).split("_")[0]
        r = ocr_titles(p)
        row = {"Site": site, "Figure": os.path.relpath(p, fig_dir)}
        for f in ("GPP", "NEE"):
            for i, k in enumerate(KEYS):
                row[f"{f}_{k}"] = r[f][i] if f in r else None
        row["OCR_complete"] = len(r) == 2
        rows.append(row)
        print(f"  OCR {site}: {r}", flush=True)
    return pd.DataFrame(rows)


def old_metrics(old_repo):
    rank = lambda p: (2 if "spinup1000_final" in p else 1 if "spinup500_final" in p else 0, p)
    best = {}
    for p in glob.glob(os.path.join(old_repo, "examples", "**", "*_monthly_metrics.csv"), recursive=True):
        s = os.path.basename(p).split("_")[0]
        if s not in best or rank(p) > rank(best[s]):
            best[s] = p
    rows = []
    for s, p in sorted(best.items()):
        d = pd.read_csv(p)
        r = {"Site": s, "Old_metrics_source": os.path.relpath(os.path.dirname(os.path.dirname(p)), old_repo)}
        for _, x in d.iterrows():
            for k in KEYS:
                r[f"{x['Flux']}_{k}"] = x[k]
            r["Old_model_cycle"] = f"{x.get('ModelCycleFirst')}-{x.get('ModelCycleLast')}"
        rows.append(r)
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new-figs", required=True)
    ap.add_argument("--old-repo", required=True)
    ap.add_argument("--registers", help="directory with batch0*_10_sites.csv (igbp column)")
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--extra", nargs="*", default=[], help="SITE:8 comma-separated new metrics (see docstring)")
    ap.add_argument("--igbp", nargs="*", default=["DE-Tha:ENF", "NL-Loo:ENF"], help="SITE:CLASS overrides")
    a = ap.parse_args(argv)
    a.outdir.mkdir(parents=True, exist_ok=True)
    new = new_metrics(a.new_figs)
    for e in a.extra:
        s, vals = e.split(":", 1)
        v = [float(x) for x in vals.split(",")]
        row = {"Site": s, "Figure": "manual --extra", "OCR_complete": True}
        row.update({f"{f}_{k}": v[i * 4 + j] for i, f in enumerate(("GPP", "NEE")) for j, k in enumerate(KEYS)})
        new = pd.concat([new[new.Site != s], pd.DataFrame([row])], ignore_index=True)
    new.to_csv(a.outdir / "nocomp_EC_metrics_from_figure_titles.csv", index=False)
    old = old_metrics(a.old_repo)
    m = old.merge(new[new.OCR_complete], on="Site", suffixes=("_old", "_new"))
    ig = {}
    if a.registers:
        for f in glob.glob(os.path.join(a.registers, "batch0*_10_sites.csv")):
            d = pd.read_csv(f)
            if "igbp" in d:
                ig.update(dict(zip(d.site, d.igbp)))
    ig.update(dict(x.split(":", 1) for x in a.igbp))
    m.insert(1, "IGBP", m.Site.map(ig).fillna("?"))
    dom_csv = Path(a.old_repo) / "carbon_flux_convergence_diagnostics/data/15_site_ec_observed_vegetation_and_fates_match.csv"
    if dom_csv.is_file():
        dom = pd.read_csv(dom_csv)[["Site", "FATES_Frozen_DominantPFT", "FATES_Frozen_Dominant_PFT_VegC_pct", "Final_Match_Status"]]
        dom.columns = ["Site", "Old_dominant_FATES_PFT", "Old_dominant_PFT_VegC_pct", "Old_PFT_vs_tower"]
        m = m.merge(dom, on="Site", how="left")
    for f in ("GPP", "NEE"):
        m[f"{f}_dRMSE_new_minus_old"] = m[f"{f}_RMSE_new"] - m[f"{f}_RMSE_old"]
        m[f"{f}_dR2_new_minus_old"] = m[f"{f}_R2_new"] - m[f"{f}_R2_old"]
    m.sort_values(["IGBP", "Site"]).round(4).to_csv(a.outdir / "competition_vs_nocomp_GPP_NEE_monthly_metrics.csv", index=False)
    print(f"\n{len(m)} paired sites; unreadable new figures: {list(new.loc[~new.OCR_complete, 'Site'])}")
    for f in ("GPP", "NEE"):
        print(f"{f}: new RMSE lower at {(m[f'{f}_dRMSE_new_minus_old'] < 0).sum()}, higher at {(m[f'{f}_dRMSE_new_minus_old'] > 0).sum()} | "
              f"median RMSE {m[f'{f}_RMSE_old'].median():.2f} -> {m[f'{f}_RMSE_new'].median():.2f} | "
              f"median R2 {m[f'{f}_R2_old'].median():.2f} -> {m[f'{f}_R2_new'].median():.2f} | "
              f"mean bias {m[f'{f}_Bias_old'].mean():+.2f} -> {m[f'{f}_Bias_new'].mean():+.2f}")
    for g, d in m.groupby("IGBP"):
        print(f"  {g:4} n={len(d):2}  GPP lower/higher RMSE {(d.GPP_dRMSE_new_minus_old < 0).sum()}/{(d.GPP_dRMSE_new_minus_old > 0).sum()}  "
              f"GPP mean bias {d.GPP_Bias_old.mean():+.2f} -> {d.GPP_Bias_new.mean():+.2f}  "
              f"NEE lower/higher RMSE {(d.NEE_dRMSE_new_minus_old < 0).sum()}/{(d.NEE_dRMSE_new_minus_old > 0).sum()}")
    print("OUTPUT:", a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
