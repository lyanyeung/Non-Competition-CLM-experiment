#!/usr/bin/env python3
"""READ ONLY. Tower water-balance screen for groundwater subsidy, the criterion that excluded US-CMW.

US-CMW was excluded because tower ET was 2.5 x precipitation every year (662 vs 263 mm/yr): the
vegetation drinks groundwater that a single-point CLM column (no lateral inflow) cannot supply.
This script computes the same number for every site from its EC FLUXNET half-hourly file:

  annual P  = sum of P_F (fallback P) over the year
  annual ET = sum of LE_F_MDS (fallback LE_CORR, LE) x step / 2.45e6
  a day counts when >= 80 % of its steps have both P and LE; a year counts when >= 330 days count;
  totals of a counted year are scaled to 365 days.

Flags (per site, over counted years):
  GW_SUBSIDY   mean ET/P >= 1.2, or ET/P >= 1.2 in at least half of the years (US-CMW: 2.5)
  CHECK        mean ET/P 1.0-1.2: in drylands ET ~ P is normal; in cold sites snow undercatch
               inflates ET/P; read together with docs/GROUNDWATER_SCREENING.md
  OK           mean ET/P < 1.0 (does NOT rule out groundwater use, e.g. US-Ton blue oaks)
  NO_DATA      no usable EC file / no full year

EC files are looked up like the other Cross_cohort scripts: <sites-root>/<SITE>/forcing/raw*/**
*_FULLSET_HH|FLUXMET_HH|FLUXES_HH|FLUX_HH (or _HR) csv, ERA5/AUX/BIF excluded; else any such csv under
<sites-root>/<SITE>. Nothing is written except the --out csv (default in Home).

Usage:  python3 -B 30_groundwater_screen_tower_ET_P.py                 # all 86 sites
        python3 -B 30_groundwater_screen_tower_ET_P.py --sites US-Ton BE-Bra
        python3 -B 30_groundwater_screen_tower_ET_P.py --ec-file US-CMW=/path/file.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "20261104-v1"
SITES = {
    "AmeriFlux_B01": "BR-Ma2 CA-Ca3 CA-LP1 CA-TP4 CA-Cbo CA-Man CA-TP1 CA-TP3 US-Aud US-Bar",
    "AmeriFlux_B02": "US-BZS US-CMW US-EML US-GLE US-Ha1 US-Ho1 US-Ho2 US-Ho3 US-ICh US-ICt",
    "AmeriFlux_B03": "US-Kon US-MMS US-MOz US-Me2 US-Me6 US-Mpj US-MtB US-NC2 US-NR1 US-NR3",
    "AmeriFlux_B04": "US-Rpf US-SP1 US-SRG US-SRM US-Seg US-Ses US-Slt US-Syv US-Ton US-Uaf",
    "AmeriFlux_B05": "US-UiD US-UMB US-UMd US-Var US-Vcm US-Vcp US-WCr US-Whs US-Wjs US-Wkg",
    "ICOS_B01": "BE-Vie CH-Dav CZ-BK1 DE-Hai FI-Sod FR-Fon FR-Pue IT-Col IT-Ren RU-Fyo",
    "ICOS_B02": "BE-Bra CH-Fru CH-Lae DK-Sor ES-LJu FI-Hyy FR-FBn FR-Hes IT-MBo IT-Noe",
    "ICOS_B03": "AT-Neu CH-Cha CZ-Stn DE-Hzd DE-Lnf DE-Obe FI-Let GF-Guy IL-Yat IT-Lav",
    "ICOS_B04": "CH-Aws DE-Gri DE-RuR ES-Agu GL-ZaH IT-Tor",
}
BATCH = {s: b for b, ss in SITES.items() for s in ss.split()}
NAME_RE = re.compile(r"(FULLSET|FLUXMET|FLUXES|FLUX)_H[HR]")
SKIP_RE = re.compile(r"ERA5|ERAI|AUX|BIF")
P_COLS = ("P_F", "P")
LE_COLS = ("LE_F_MDS", "LE_CORR", "LE")
LV = 2.45e6
MIN_DAY_FRAC, MIN_DAYS = 0.8, 330


def header(p: Path) -> list[str]:
    with p.open("r", encoding="latin-1", newline="") as f:
        return next(csv.reader(f))


def candidates(site: str, root: Path) -> list[Path]:
    out = []
    forcing = root / site / "forcing"
    bases = [d for d in sorted(forcing.iterdir()) if d.is_dir() and d.name.lower().startswith("raw")] \
        if forcing.is_dir() else []
    if not bases and (root / site).is_dir():
        bases = [root / site]
    for b in bases:
        for p in sorted(b.rglob("*.csv")):
            up = p.name.upper()
            if not NAME_RE.search(up) or SKIP_RE.search(up):
                continue
            try:
                cols = set(header(p))
            except (OSError, UnicodeError, StopIteration):
                continue
            if "TIMESTAMP_START" in cols and any(c in cols for c in P_COLS) and any(c in cols for c in LE_COLS):
                out.append(p)
    return out


def yearly(path: Path) -> tuple[pd.DataFrame, str]:
    cols = header(path)
    pc = next(c for c in P_COLS if c in cols)
    lc = next(c for c in LE_COLS if c in cols)
    raw = pd.read_csv(path, usecols=["TIMESTAMP_START", pc, lc], dtype={"TIMESTAMP_START": str},
                      low_memory=False, encoding="latin-1")
    ts = raw["TIMESTAMP_START"].str.strip().str.replace(r"\.0$", "", regex=True)
    raw.index = pd.to_datetime(ts, format="%Y%m%d%H%M", errors="coerce")
    raw = raw[raw.index.notna()]
    step = raw.index.to_series().diff().dropna().dt.total_seconds()
    step = float(step.mode().iloc[0]) if not step.empty else 1800.0
    per_day = 86400.0 / step
    p = pd.to_numeric(raw[pc], errors="coerce").astype(float)
    le = pd.to_numeric(raw[lc], errors="coerce").astype(float)
    p[(p <= -9990) | (p < 0)] = np.nan
    le[le <= -9990] = np.nan
    ok = p.notna() & le.notna()
    day_n = ok.resample("D").sum()
    day_p = p.where(ok).resample("D").sum(min_count=1)
    day_et = (le.where(ok) * step / LV).resample("D").sum(min_count=1)
    good = day_n >= MIN_DAY_FRAC * per_day
    # scale each day's partial totals to a full day
    scale = per_day / day_n.where(good)
    d = pd.DataFrame({"P": day_p * scale, "ET": day_et * scale})[good]
    g = d.groupby(d.index.year)
    y = pd.DataFrame({"days": g.size(), "P": g["P"].mean() * 365, "ET": g["ET"].mean() * 365})
    y = y[y["days"] >= MIN_DAYS]
    y["ET_over_P"] = y["ET"] / y["P"].replace(0, np.nan)
    return y, f"{path.name} [{pc}, {lc}]"


def flag(y: pd.DataFrame) -> str:
    if y.empty or y["P"].sum() <= 0:
        return "NO_DATA"
    mean = y["ET"].mean() / y["P"].mean()
    if mean >= 1.2 or (y["ET_over_P"] >= 1.2).mean() >= 0.5:
        return "GW_SUBSIDY"
    return "CHECK" if mean >= 1.0 else "OK"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", nargs="+", default=None)
    ap.add_argument("--sites-root", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE"))
    ap.add_argument("--ec-file", action="append", default=[], help="SITE=PATH override (repeatable)")
    ap.add_argument("--out", type=Path, default=Path.home() / "groundwater_screen_tower_ET_P.csv")
    a = ap.parse_args(argv)
    override = dict(x.split("=", 1) for x in a.ec_file)
    sites = a.sites or [s for ss in SITES.values() for s in ss.split()]
    rows = []
    print(f"groundwater ET/P screen {VERSION}  sites-root={a.sites_root}")
    print(f"{'SITE':7} {'BATCH':14} {'FLAG':10} {'YRS':>3} {'P_mm':>6} {'ET_mm':>6} {'ET/P':>5} {'maxET/P':>7}  SOURCE")
    for s in sites:
        try:
            files = [Path(override[s])] if s in override else candidates(s, a.sites_root)
            best, src = pd.DataFrame(), "no EC csv with TIMESTAMP_START + P + LE"
            for f in files:
                y, desc = yearly(f)
                if len(y) > len(best):
                    best, src = y, desc
        except Exception as e:  # keep going: one broken file must not stop the screen
            best, src = pd.DataFrame(), f"ERROR {type(e).__name__}: {e}"[:160]
        fl = flag(best)
        n = len(best)
        P = best["P"].mean() if n else np.nan
        ET = best["ET"].mean() if n else np.nan
        r = ET / P if n and P else np.nan
        mx = best["ET_over_P"].max() if n else np.nan
        rows.append({"site": s, "batch": BATCH.get(s, "?"), "flag": fl, "years": n,
                     "P_mm_yr": round(P, 1) if n else "", "ET_mm_yr": round(ET, 1) if n else "",
                     "ET_over_P": round(r, 3) if n else "", "max_year_ET_over_P": round(mx, 3) if n else "",
                     "years_list": " ".join(str(i) for i in best.index) if n else "", "source": src})
        fmt = lambda v, w, d: f"{v:{w}.{d}f}" if isinstance(v, float) and np.isfinite(v) else " " * (w - 1) + "-"
        print(f"{s:7} {BATCH.get(s, '?'):14} {fl:10} {n:3d} {fmt(P, 6, 0)} {fmt(ET, 6, 0)} {fmt(r, 5, 2)} "
              f"{fmt(mx, 7, 2)}  {src}", flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    counts = pd.Series([r["flag"] for r in rows]).value_counts().to_dict()
    print(f"\n{counts}  -> {a.out}")
    print("Reference: US-CMW (excluded) has ET/P 2.5. ET/P < 1 does not rule out groundwater use (US-Ton).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
