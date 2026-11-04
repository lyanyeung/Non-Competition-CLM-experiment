#!/usr/bin/env python3
"""READ ONLY. Is the precipitation behind the ET/P screen (script 30) and behind the model forcing plausible?

Script 30 (4 Nov 2026) found tower P_F of 2300-3700 mm/yr at CA-Cbo, US-Syv, US-UMd, US-UiD, DE-Hzd,
US-NR3 and US-EML: about 3-4 x the site's mean annual precipitation. In FLUXNET products P_F is the measured
P where it exists and ERA5 P_ERA where it does not (P_F_QC = 2); ERA5 point precipitation can be several times
too high. Batch03/05 forcing scaled such sites back to the BIF MAP (rule R2); other batches may not have.

For every site this prints, per site and optionally per year:
  tower    P_F, share of ERA-filled steps (P_F_QC == 2), P_ERA, measured P where a column exists,
           ET from LE (same day/year rules as script 30) and ET/P
  BIF      MAP (BADM VARIABLE == MAP), or --map SITE=mm
  forcing  PRECTmms summed per year from the datm.streams.xml of every case <SITE>_* under --cases
           (one line per distinct forcing directory; the RUNDIR copy is preferred over CaseDocs)

Verdicts:
  TOWER_P_HIGH     tower P_F > 1.5 x MAP      -> script 30 ET/P is not usable; use ET/MAP instead
  TOWER_P_LOW      tower P_F < 0.67 x MAP     -> ET/P inflated (undercatch, dead gauge)
  FORCING_P_HIGH   forcing P > 1.5 x MAP      -> the model is driven too wet
  FORCING_P_LOW    forcing P < 0.67 x MAP     -> the model is driven too dry
  OK               within 0.67-1.5 x MAP; NO_MAP when no MAP is known (then compare tower with forcing only)

Usage:  python3 -B 32_precip_check_tower_forcing_MAP.py                       # all 86 sites
        python3 -B 32_precip_check_tower_forcing_MAP.py --sites US-Vcp IL-Yat --per-year
        python3 -B 32_precip_check_tower_forcing_MAP.py --sites IL-Yat --map IL-Yat=285
        python3 -B 32_precip_check_tower_forcing_MAP.py --no-forcing           # tower and MAP only (fast)
Writes only --out (default ~/precip_check_tower_forcing_MAP.csv).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "20261104-v1"
HERE = Path(__file__).resolve().parent
HIGH, LOW = 1.5, 0.67


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S30 = _load("gw30", "30_groundwater_screen_tower_ET_P.py")
S31 = _load("ev31", "31_site_events_vs_flux_record.py")


# ----------------------------------------------------------------- tower
def tower_years(path: Path) -> pd.DataFrame:
    """Per counted year: P_F, ERA-filled share, P_ERA, measured P, ET (script 30 rules)."""
    y, _ = S30.yearly(path)                       # counted years with P (P_F) and ET
    if y.empty:
        return y
    cols = S30.header(path)
    want = [c for c in ("P_F_QC", "P_ERA", "P") if c in cols]
    if want:
        d = pd.read_csv(path, usecols=["TIMESTAMP_START"] + want, dtype={"TIMESTAMP_START": str},
                        low_memory=False, encoding="latin-1")
        ts = d["TIMESTAMP_START"].str.strip().str.replace(r"\.0$", "", regex=True)
        d.index = pd.to_datetime(ts, format="%Y%m%d%H%M", errors="coerce")
        d = d[d.index.notna()]
        for c in want:
            v = pd.to_numeric(d[c], errors="coerce").astype(float)
            d[c] = v.where(v > -9990)
        g = d.groupby(d.index.year)
        if "P_F_QC" in want:
            y["era_filled_pct"] = (g["P_F_QC"].apply(lambda x: (x == 2).mean() * 100)).reindex(y.index)
        if "P_ERA" in want:
            y["P_ERA"] = g["P_ERA"].sum(min_count=1).reindex(y.index)
        if "P" in want and "P_F" in cols:          # measured P only where P_F is the gap-filled one
            y["P_meas"] = g["P"].sum(min_count=1).reindex(y.index)
            y["P_meas_missing_pct"] = g["P"].apply(lambda x: x.isna().mean() * 100).reindex(y.index)
    return y


def best_tower(site: str, root: Path, override: dict) -> tuple[pd.DataFrame, str]:
    files = [Path(override[site])] if site in override else S30.candidates(site, root)
    best, src = pd.DataFrame(), "no EC csv"
    for f in files:
        try:
            y = tower_years(f)
        except Exception as e:  # one broken file must not stop the check
            src = f"ERROR {type(e).__name__}: {e}"[:120]
            continue
        if len(y) > len(best):
            best, src = y, f.name
    return best, src


# ----------------------------------------------------------------- BIF MAP
def bif_map(site: str, root: Path) -> tuple[float, str]:
    for p in S31.bif_files(site, root):
        try:
            df = pd.read_csv(p, dtype=str, encoding="latin-1") if p.suffix.lower() == ".csv" \
                else pd.read_excel(p, dtype=str)
        except Exception:
            continue
        cols = {c.upper(): c for c in df.columns}
        if "VARIABLE" not in cols or "DATAVALUE" not in cols:
            continue
        v = pd.to_numeric(df.loc[df[cols["VARIABLE"]].str.upper() == "MAP", cols["DATAVALUE"]], errors="coerce").dropna()
        if not v.empty:
            return float(v.iloc[0]), p.name
    return float("nan"), ""


# ----------------------------------------------------------------- forcing
def stream_precip_files(xml: Path) -> list[str]:
    """Files of the stream(s) that carry PRECTmms; all files if no stream names its variables."""
    root = ET.parse(xml).getroot()
    out, any_vars = [], False
    for st in root.iter("stream_info"):
        vars_ = " ".join((e.text or "") for e in st.iter("var"))
        files = [(e.text or "").strip() for e in st.iter("file") if (e.text or "").strip()]
        if vars_.strip():
            any_vars = True
        if "PRECTmms" in vars_:
            out += files
    if not out and not any_vars:
        out = [(e.text or "").strip() for e in root.iter("file") if (e.text or "").strip()]
    return out


def forcing_years(files: list[str]) -> pd.Series:
    """Annual PRECTmms totals (mm) over the listed files; years with < 360 days of data are dropped."""
    from netCDF4 import Dataset, num2date
    tot, secs = {}, {}
    for f in files:
        if not Path(f).is_file():
            continue
        with Dataset(f) as ds:
            if "PRECTmms" not in ds.variables or "time" not in ds.variables:
                continue
            t = ds.variables["time"]
            pr = np.asarray(ds.variables["PRECTmms"][:], dtype=float).reshape(len(t), -1)[:, 0]
            tv = np.asarray(t[:], dtype=float)
            if len(tv) < 2:
                continue
            dt = float(np.median(np.diff(tv))) * {"days": 86400.0, "hours": 3600.0, "minutes": 60.0,
                                                  "seconds": 1.0}[t.units.split()[0].lower()]
            yrs = np.array([d.year for d in num2date(tv, t.units, getattr(t, "calendar", "standard"))])
            pr = np.where(np.isfinite(pr) & (pr >= 0) & (pr < 1e10), pr, np.nan)
            for yy in np.unique(yrs):
                m = yrs == yy
                tot[int(yy)] = tot.get(int(yy), 0.0) + float(np.nansum(pr[m]) * dt)
                secs[int(yy)] = secs.get(int(yy), 0.0) + float(m.sum() * dt)
    s = pd.Series(tot, dtype=float).sort_index()
    full = pd.Series(secs).reindex(s.index) >= 360 * 86400
    return s[full]


def forcing_sets(site: str, cases: Path, out: Path) -> list[dict]:
    """One entry per distinct forcing directory used by cases named <SITE>_*."""
    seen: dict[tuple, dict] = {}
    if not cases.is_dir():
        return []
    for case in sorted(cases.glob(f"{site}_*")):
        for xml in (out / case.name / "run" / "datm.streams.xml", case / "CaseDocs" / "datm.streams.xml"):
            if xml.is_file():
                break
        else:
            continue
        try:
            files = stream_precip_files(xml)
        except ET.ParseError:
            continue
        if not files:
            continue
        key = tuple(sorted({str(Path(f).parent) for f in files}))
        if key in seen:
            seen[key]["cases"].append(case.name)
            continue
        seen[key] = {"dirs": key, "files": files, "cases": [case.name]}
    for v in seen.values():
        v["years"] = forcing_years(v["files"])
    return list(seen.values())


# ----------------------------------------------------------------- verdict
def verdict(p: float, mp: float, what: str) -> str:
    if not np.isfinite(p):
        return ""
    if not np.isfinite(mp) or mp <= 0:
        return "NO_MAP"
    r = p / mp
    return f"{what}_P_HIGH" if r > HIGH else (f"{what}_P_LOW" if r < LOW else "OK")


def fmt(v, w=6, d=0):
    return f"{v:{w}.{d}f}" if isinstance(v, (float, int, np.floating)) and np.isfinite(v) else " " * (w - 1) + "-"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", nargs="+", default=None)
    ap.add_argument("--sites-root", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE"))
    ap.add_argument("--cases", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases"))
    ap.add_argument("--outputs", type=Path, default=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS"))
    ap.add_argument("--ec-file", action="append", default=[], help="SITE=PATH override (repeatable)")
    ap.add_argument("--map", action="append", default=[], help="SITE=mm MAP override (repeatable)")
    ap.add_argument("--per-year", action="store_true", help="print the yearly table for each site")
    ap.add_argument("--no-forcing", action="store_true", help="skip reading the model forcing")
    ap.add_argument("--out", type=Path, default=Path.home() / "precip_check_tower_forcing_MAP.csv")
    a = ap.parse_args(argv)
    ec_over = dict(x.split("=", 1) for x in a.ec_file)
    map_over = {k: float(v) for k, v in (x.split("=", 1) for x in a.map)}
    sites = a.sites or [s for ss in S30.SITES.values() for s in ss.split()]

    print(f"precip check {VERSION}  sites-root={a.sites_root}  cases={a.cases}")
    print(f"{'SITE':7} {'MAP':>5} {'P_F':>5} {'ERA%':>4} {'P_ERA':>5} {'P_meas':>6} {'ET':>4} {'ET/P':>5} {'ET/MAP':>6} "
          f"{'P_forc':>6} {'TOWER':14} {'FORCING':15} forcing dir (cases)")
    rows = []
    for s in sites:
        y, src = best_tower(s, a.sites_root, ec_over)
        mp, msrc = (map_over[s], "--map") if s in map_over else bif_map(s, a.sites_root)
        n = len(y)
        mean = lambda c: float(y[c].mean()) if n and c in y and y[c].notna().any() else float("nan")
        pf, et, era, pe, pm = mean("P"), mean("ET"), mean("era_filled_pct"), mean("P_ERA"), mean("P_meas")
        sets = [] if a.no_forcing else forcing_sets(s, a.cases, a.outputs)
        if not sets:
            sets = [{"dirs": ("-",), "cases": [], "years": pd.Series(dtype=float)}]
        tv = verdict(pf, mp, "TOWER")
        for k, fs in enumerate(sets):
            pfo = float(fs["years"].mean()) if len(fs["years"]) else float("nan")
            fv = verdict(pfo, mp, "FORCING") if np.isfinite(pfo) else ("not read" if a.no_forcing else "no forcing")
            d = Path(fs["dirs"][0])
            dshort = "/".join(d.parts[-3:]) + (f" +{len(fs['dirs']) - 1}" if len(fs["dirs"]) > 1 else "")
            lead = f"{s:7} {fmt(mp, 5)} {fmt(pf, 5)} {fmt(era, 4)} {fmt(pe, 5)} {fmt(pm, 6)} {fmt(et, 4)} " \
                   f"{fmt(et / pf if pf else np.nan, 5, 2)} {fmt(et / mp if mp else np.nan, 6, 2)}" if k == 0 \
                else " " * 64
            print(f"{lead} {fmt(pfo, 6)} {(tv if k == 0 else ''):14} {fv:15} {dshort} ({len(fs['cases'])})", flush=True)
            rows.append({"site": s, "batch": S30.BATCH.get(s, "?"), "MAP_mm": "" if not np.isfinite(mp) else mp,
                         "MAP_source": msrc, "tower_years": n, "tower_P_F_mm": round(pf, 1) if np.isfinite(pf) else "",
                         "era_filled_pct": round(era, 1) if np.isfinite(era) else "",
                         "tower_P_ERA_mm": round(pe, 1) if np.isfinite(pe) else "",
                         "tower_P_measured_mm": round(pm, 1) if np.isfinite(pm) else "",
                         "tower_ET_mm": round(et, 1) if np.isfinite(et) else "",
                         "ET_over_P": round(et / pf, 3) if np.isfinite(et) and pf else "",
                         "ET_over_MAP": round(et / mp, 3) if np.isfinite(et) and np.isfinite(mp) and mp else "",
                         "forcing_P_mm": round(pfo, 1) if np.isfinite(pfo) else "",
                         "forcing_years": len(fs["years"]), "tower_verdict": tv, "forcing_verdict": fv,
                         "forcing_dir": ";".join(fs["dirs"]), "cases": " ".join(fs["cases"]), "ec_source": src})
        if a.per_year and n:
            print(f"    {'year':>4} {'P_F':>6} {'ERA%':>5} {'P_ERA':>6} {'P_meas':>6} {'miss%':>5} {'ET':>5} {'ET/P':>5} "
                  + " ".join(f"{'P_forc' + str(i + 1):>7}" for i in range(len(sets))))
            yrs = sorted(set(y.index) | {int(i) for fs in sets for i in fs["years"].index})
            for yy in yrs:
                g = lambda c: float(y.loc[yy, c]) if yy in y.index and c in y else float("nan")
                fo = " ".join(fmt(float(fs["years"].get(yy, np.nan)), 7) for fs in sets)
                print(f"    {yy:4d} {fmt(g('P'))} {fmt(g('era_filled_pct'), 5)} {fmt(g('P_ERA'))} {fmt(g('P_meas'))} "
                      f"{fmt(g('P_meas_missing_pct'), 5)} {fmt(g('ET'), 5)} {fmt(g('ET_over_P'), 5, 2)} {fo}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    c = pd.DataFrame(rows)
    print(f"\ntower: {c.drop_duplicates('site')['tower_verdict'].value_counts().to_dict()}")
    print(f"forcing: {c['forcing_verdict'].value_counts().to_dict()}  -> {a.out}")
    print("ERA% = share of half-hours where P_F is ERA5 (P_F_QC == 2). ET/MAP replaces ET/P where TOWER_P_HIGH.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
