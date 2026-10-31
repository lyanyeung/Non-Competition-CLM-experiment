#!/usr/bin/env python3
"""Read-only diagnostics for FIXNC AD400 + NORMAL400 spin-ups (Batch03 first).

Same figure style as CLM-FATES-single-site-workflows examples
(FLUXNET_MultiSite_6/8/11): carbon-pool convergence panels and a monthly
EC-tower vs CLM-FATES GPP/NEE overview, adapted to a TWO-CASE spin-up:

  spin-up years   1-400  : AD case     <site>_..._AD400      (model Y .. Y+399)
  spin-up years 401-800  : Normal case <site>_..._NORMAL400  (model Y+400 .. Y+799)

A step in soil/litter pools at year 400/401 is expected: CLM rescales the
accelerated pools when leaving accelerated decomposition. Convergence metrics
therefore use the NORMAL phase only.

EC comparison uses the LAST COMPLETE forcing cycle inside the Normal phase,
mapped to observation years with the DATM year_first/year_last/year_align.
GPP partition (corrected policy): GPP_NT_VUT_REF first; GPP_DT_VUT_REF only
when a source file has no usable NT values. Model NEE = -FATES_NEP; EC NEE =
NEE_VUT_REF. Units g C m-2 d-1.

Outputs (per site, under --output-root, never under scratch):
  <site>_01_carbon_pools_AD400_NORMAL400.png
  <site>_02_carbon_pools_NORMAL400_panels.png
  <site>_GPP_NEE_monthly_overview.png
  <site>_carbon_annual_means.csv  <site>_convergence_metrics.csv
  <site>_daily_FATES_vs_EC.csv    <site>_monthly_FATES_vs_EC.csv
  <site>_flux_metrics.csv         <site>_metadata.json
  AD400_NORMAL400_summary.csv

Usage on IRIDIS6 (clm_fates_env):
  python3 -B 15_...py --preflight                      # read-only inventory
  python3 -B 15_...py --output-root /path/on/RFS       # complete sites only
  python3 -B 15_...py --output-root ... --allow-incomplete   # INTERIM figures
  python3 -B 15_...py --pair SITE:AD_CASE:NORMAL_CASE ...    # other cohorts
800 model years do not prove equilibrium; read the metrics.
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, math, os, re, sys, traceback
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EC_TO_GCD = 86400.0 * 12.0107e-6     # umol CO2 m-2 s-1 -> g C m-2 d-1
FATES_TO_GCD = 86400.0 * 1000.0      # kg C m-2 s-1     -> g C m-2 d-1
HIST_RE = re.compile(r"\.clm2\.h0a?\.(\d{4})-(\d{2})(?:-(\d{2})-(\d{5}))?\.nc$")
PHASE = 400
CANDIDATES = ["TOTECOSYSC", "TOTSOMC", "FATES_VEGC", "TOTVEGC", "TOTLITC", "TOTSOILC",
              "SOILC", "FATES_STOREC", "FATES_STRUCTC", "FATES_NONSTRUCTC", "TOTROOTC"]
LABELS = {"TOTECOSYSC": "Total ecosystem carbon", "TOTSOMC": "Soil organic carbon",
          "FATES_VEGC": "FATES vegetation carbon", "TOTVEGC": "Total vegetation carbon",
          "TOTLITC": "Litter carbon", "TLAI": "Total LAI"}
GPP_NT, GPP_DT = "GPP_NT_VUT_REF", "GPP_DT_VUT_REF"
SOURCE_PRIORITY = {"ICOS": 0, "ICOSETC": 1, "EUF": 2, "FLX": 3, "AMF": 4}


# ------------------------------------------------------------------ registry
def batch03_pairs(sites):
    spec = importlib.util.spec_from_file_location("b03s14", HERE / "14_batch03_AD400_to_NORMAL400.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    out = []
    for s in m.B.pick_sites(sites):
        out.append({"site": s, "ad": m.B.case_name(s), "normal": m.ncase_name(s),
                    "ad_case_dir": m.B.case_path(s), "cohort": "Batch03"})
    return out


def env_value(case_dir, key):
    for f in ("env_run.xml", "env_case.xml", "env_build.xml"):
        p = Path(case_dir) / f
        if p.is_file():
            for e in ET.parse(p).getroot().iter("entry"):
                if e.attrib.get("id") == key:
                    return e.attrib.get("value")
    raise KeyError(f"{key} not found in {case_dir}")


def forcing_years(case_dir, run_dir=None):
    """year_first, year_last, year_align of the site met stream (CLM_USRDAT)."""
    # The runtime copy is authoritative when curated after preview. CaseDocs is
    # the fallback; user overrides alone may not reflect the executed stream.
    for x in ([Path(run_dir) / "datm.streams.xml"] if run_dir else []) + [Path(case_dir) / "CaseDocs" / "datm.streams.xml"]:
        if x.is_file():
            for e in ET.parse(x).getroot().iter():
                name = e.attrib.get("name", "")
                if "CLM_USRDAT" in name:
                    g = {c.tag: (c.text or "").strip() for c in e.iter()}
                    if all(g.get(k, "").isdigit() for k in ("year_first", "year_last", "year_align")):
                        return int(g["year_first"]), int(g["year_last"]), int(g["year_align"])
    p = Path(case_dir) / "user_nl_datm_streams"
    if p.is_file():
        txt = p.read_text()
        vals = {}
        for k in ("year_first", "year_last", "year_align"):
            m = re.findall(rf"(?m)^\s*CLM_USRDAT[^:]*:{k}\s*=\s*(\d+)", txt)
            if len(set(m)) == 1:
                vals[k] = int(m[0])
        if len(vals) == 3:
            return vals["year_first"], vals["year_last"], vals["year_align"]
    raise ValueError(f"Cannot determine CLM_USRDAT year_first/last/align in {case_dir}")


# ------------------------------------------------------------------ model
def history_index(archive, case):
    """{model_year: [paths]}; a year is usable when it has ONE annual file
    (<case>.clm2.h0[a].YYYY-01-01-00000.nc, daily or monthly samples) or
    TWELVE monthly files (<case>.clm2.h0[a].YYYY-MM.nc)."""
    hist = archive / case / "lnd" / "hist"
    if not hist.is_dir():
        raise FileNotFoundError(f"No archived history: {hist}")
    annual, mon = {}, {}
    for p in hist.glob(f"{case}.clm2.h0*.nc"):
        m = HIST_RE.search(p.name)
        if not m:
            continue
        y, mo = int(m.group(1)), int(m.group(2))
        if m.group(3) is not None:
            if mo != 1 or m.group(3) not in ("01", "02"):
                raise ValueError(f"Unexpected non-annual h0 file layout: {p.name}")
            if y in annual:
                raise ValueError(f"Duplicate annual history for {y} in {hist}")
            annual[y] = [p]
        else:
            mon.setdefault(y, {})
            if mo in mon[y]:
                raise ValueError(f"Duplicate monthly history {p.name}")
            mon[y][mo] = p
    if annual and mon:
        raise ValueError(f"Mixed annual and monthly h0 files in {hist}; refusing to guess")
    found = dict(annual)
    for y, d in mon.items():
        if sorted(d) == list(range(1, 13)):
            found[y] = [d[k] for k in range(1, 13)]
    if not found:
        raise FileNotFoundError(f"No complete annual h0/h0a history under {hist}")
    return found


def contiguous(found, start, n):
    yrs = []
    for y in range(start, start + n):
        if y not in found:
            break
        yrs.append(y)
    return yrs


def point_series(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    dims = list(var.dimensions)
    if "time" not in dims:
        raise ValueError(f"{getattr(var, 'name', '?')}: no time dimension")
    a = np.moveaxis(a, dims.index("time"), 0).reshape(a.shape[dims.index("time")], -1)
    if a.shape[1] != 1:
        raise ValueError(f"{getattr(var, 'name', '?')}: not a single point {a.shape}")
    return a[:, 0]


def unit_factor(units):
    u = units.lower().replace(" ", "").replace("^", "")
    if "kg" in u and ("m-2" in u or "/m2" in u):
        return 1000.0, "g C m$^{-2}$", "g C m-2"
    if ("gc" in u or u.startswith("g")) and ("m-2" in u or "/m2" in u):
        return 1.0, "g C m$^{-2}$", "g C m-2"
    return 1.0, units or "unit not recorded", units or "unknown"


def is_point_timeseries(var):
    dims = list(var.dimensions)
    return "time" in dims and int(np.prod([n for d, n in zip(dims, var.shape) if d != "time"])) == 1


def annual_carbon(files, site):
    from netCDF4 import Dataset
    rows, chosen, meta = [], None, {}
    for i, (spin, model_year, phase, paths) in enumerate(files):
        vals, weights, dates = {}, [], []
        for path in paths:
            with Dataset(str(path)) as ds:
                bounds_name = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
                if bounds_name is None:
                    raise ValueError(f"{path.name}: time bounds missing; cannot calculate a duration-weighted annual mean")
                bounds = np.asarray(ds.variables[bounds_name][:], dtype=float)
                if bounds.ndim != 2 or bounds.shape[1] != 2:
                    raise ValueError(f"{path.name}: unexpected time bounds shape {bounds.shape}")
                duration = bounds[:, 1] - bounds[:, 0]
                if not np.all(np.isfinite(duration) & (duration > 0)):
                    raise ValueError(f"{path.name}: invalid time interval lengths")
                weights.append(duration)
                dates.extend(noleap_dates(ds))
                if chosen is None:
                    chosen = []
                    for n in CANDIDATES:
                        if n in ds.variables and is_point_timeseries(ds.variables[n]):
                            u = str(getattr(ds.variables[n], "units", ""))
                            f, pu, cu = unit_factor(u)
                            chosen.append(n)
                            meta[n] = {"factor": f, "plot_units": pu, "csv_units": cu, "original_units": u}
                    if not chosen:
                        raise RuntimeError(f"No scalar carbon variables among {CANDIDATES} in {path.name}")
                    print(f"  carbon variables: {chosen}", flush=True)
                for n in chosen:
                    if n not in ds.variables:
                        raise RuntimeError(f"{path.name} lacks {n} (history fields changed between cases?)")
                    u = str(getattr(ds.variables[n], "units", ""))
                    f, _, cu = unit_factor(u)
                    if f != meta[n]["factor"] or cu != meta[n]["csv_units"]:
                        raise ValueError(f"{path.name}: {n} units {u!r} differ from first history file "
                                         f"({meta[n]['original_units']!r})")
                    vals.setdefault(n, []).append(point_series(ds.variables[n]))
        row = {"Site": site, "SpinupYear": spin, "ModelYear": model_year, "Phase": phase}
        w = np.concatenate(weights)
        expected = ([(model_year, month, day) for month, days in enumerate(
            (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31), 1)
            for day in range(1, days + 1)] if len(dates) == 365 else
            [(model_year, month, 1) for month in range(1, 13)])
        if dates != expected:
            raise ValueError(f"{site} {model_year}: history is not a complete daily or monthly year")
        for n in chosen:
            v = np.concatenate(vals[n]); good = np.isfinite(v)
            if len(v) != len(w) or not np.all(good):
                raise ValueError(f"{site} {model_year} {n}: incomplete samples; annual mean not calculated")
            row[n] = float(np.average(v, weights=w)) * meta[n]["factor"]
        rows.append(row)
        if (i + 1) % 100 == 0:
            print(f"  read {i + 1}/{len(files)} model years", flush=True)
    return pd.DataFrame(rows), chosen, meta


def noleap_dates(ds):
    t = ds.variables["time"]
    bnd = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
    if bnd is None:
        raise ValueError("No time_bounds/time_bnds; refusing ambiguous end-of-interval dates")
    start = np.asarray(ds.variables[bnd][:], dtype=float)[:, 0]
    units = str(getattr(t, "units", ""))
    cal = str(getattr(t, "calendar", "noleap")).lower()
    m = re.match(r"days since (\d{1,4})-(\d{1,2})-(\d{1,2})", units)
    if not m or cal not in ("noleap", "365_day"):
        raise ValueError(f"Unsupported time units/calendar: {units!r} {cal!r}")
    y0, mo0, d0 = map(int, m.groups())
    cum = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30])
    base = int(cum[mo0 - 1]) + d0 - 1
    out = []
    for v in start:
        k = int(math.floor(v + 1e-6)) + base
        yy, doy = y0 + k // 365, k % 365
        mm = int(np.searchsorted(cum, doy, side="right"))
        out.append((yy, mm, doy - cum[mm - 1] + 1))
    return out


def fates_samples(cycle, first, last, align):
    """Model GPP/NEE for the cycle mapped onto EC calendar years.
    Returns (DataFrame, 'daily'|'monthly'): daily when every year holds 365
    daily samples (hist_nhtfrq=-24), monthly when it holds 12 monthly means."""
    from netCDF4 import Dataset
    n = last - first + 1
    rows, freqs = [], set()
    for model_year, paths in cycle:
        ec_year = first + (model_year - align) % n
        dates, gpp, nee = [], [], []
        for path in paths:
            with Dataset(str(path)) as ds:
                for name in ("FATES_GPP", "FATES_NEP"):
                    if name not in ds.variables:
                        raise KeyError(f"{path.name}: {name} not in history")
                    u = str(getattr(ds.variables[name], "units", "")).replace(" ", "").lower()
                    if u and not ("kg" in u and ("s-1" in u or "/s" in u)):
                        raise ValueError(f"{path.name} {name} units {u!r}: check conversion")
                dates += noleap_dates(ds)
                gpp.append(point_series(ds.variables["FATES_GPP"]) * FATES_TO_GCD)
                nee.append(-point_series(ds.variables["FATES_NEP"]) * FATES_TO_GCD)
        gpp, nee = np.concatenate(gpp), np.concatenate(nee)
        if any(d[0] != model_year for d in dates):
            raise ValueError(f"model year {model_year}: sample dates outside the year (check time_bounds)")
        if len(dates) == 365:
            freqs.add("daily")
        elif len(dates) == 12 and [d[1] for d in dates] == list(range(1, 13)) and all(d[2] == 1 for d in dates):
            freqs.add("monthly")
        else:
            raise ValueError(f"model year {model_year}: {len(dates)} samples; need 365 daily or 12 monthly")
        rows.append(pd.DataFrame({"date": [pd.Timestamp(ec_year, d[1], d[2]) for d in dates],
                                  "FATES_GPP": gpp, "FATES_NEE": nee, "model_year": model_year}))
    if len(freqs) != 1:
        raise ValueError(f"Mixed history frequencies in cycle: {freqs}")
    out = pd.concat(rows, ignore_index=True).sort_values("date").reset_index(drop=True)
    if out["date"].duplicated().any():
        raise ValueError("Duplicated mapped EC dates; check year_align")
    return out, freqs.pop()


def last_complete_cycle(normal_years, first, last, align):
    n = last - first + 1
    have = set(normal_years)
    starts = [y for y in normal_years if (y - align) % n == 0 and all(y + k in have for k in range(n))]
    if not starts:
        raise ValueError(f"No complete aligned {n}-year forcing cycle in the Normal phase yet")
    s = max(starts)
    return list(range(s, s + n))


# ------------------------------------------------------------------ EC
def ec_sources(forcing_dir, override=None):
    def header(p):
        with p.open("r", encoding="latin-1", newline="") as f:
            return set(next(csv.reader(f)))
    if override:
        p = Path(override)
        if not p.is_file():
            raise FileNotFoundError(f"EC override missing: {p}")
        return [p]
    if not forcing_dir.is_dir():
        raise FileNotFoundError(f"Missing forcing directory {forcing_dir}")
    cands = []
    for raw in sorted(d for d in forcing_dir.iterdir() if d.is_dir() and d.name.lower().startswith("raw")):
        for p in sorted(raw.rglob("*.csv")):
            up = p.name.upper()
            if not any(k in up for k in ("FULLSET_HH", "FLUXMET_HH", "FLUXES_HH", "FLUX_HH",
                                          "FULLSET_HR", "FLUXMET_HR", "FLUXES_HR", "FLUX_HR")):
                continue
            if any(k in up for k in ("ERA5", "ERAI", "AUX", "BIF")):
                continue
            try:
                cols = header(p)
            except (OSError, UnicodeError, StopIteration):
                continue
            if {"TIMESTAMP_START", "NEE_VUT_REF"} <= cols and (GPP_NT in cols or GPP_DT in cols):
                cands.append((SOURCE_PRIORITY.get(up.split("_", 1)[0], 9), str(p), p))
    if not cands:
        raise FileNotFoundError(f"No HH/HR EC file with NEE_VUT_REF and GPP NT/DT under {forcing_dir}/raw*")
    return [p for _, _, p in sorted(cands)]


def ec_daily_one(path, first, last, min_hh):
    cols = pd.read_csv(path, nrows=0, encoding="latin-1").columns
    use = ["TIMESTAMP_START", "NEE_VUT_REF"] + [c for c in (GPP_NT, GPP_DT) if c in cols]
    raw = pd.read_csv(path, usecols=use, dtype={"TIMESTAMP_START": str}, low_memory=False, encoding="latin-1")
    ts = raw["TIMESTAMP_START"].str.strip().str.replace(r"\.0$", "", regex=True)
    raw["date"] = pd.to_datetime(ts, format="%Y%m%d%H%M", errors="raise")
    raw = raw[raw["date"].dt.year.between(first, last) & ~((raw["date"].dt.month == 2) & (raw["date"].dt.day == 29))]
    if raw.empty:
        return None, None, None
    if raw["date"].duplicated().any():
        raise ValueError(f"{path.name}: duplicated timestamps")
    raw = raw.set_index("date").sort_index()
    steps = raw.index.to_series().diff().dropna().dt.total_seconds()
    if steps.empty:
        raise ValueError(f"{path.name}: insufficient timestamps to determine EC cadence")
    cadence = int(steps.mode().iloc[0])
    if cadence not in (1800, 3600) or (steps % cadence != 0).any():
        raise ValueError(f"{path.name}: unsupported or inconsistent EC cadence")
    minimum = int(math.ceil(min_hh * 1800 / cadence))

    def daily(col):
        v = pd.to_numeric(raw[col], errors="coerce").astype(float)
        v[(v <= -9990) | ~np.isfinite(v)] = np.nan
        mean, cnt = v.resample("D").mean(), v.resample("D").count()
        mean[cnt < minimum] = np.nan
        return mean * EC_TO_GCD

    nee = daily("NEE_VUT_REF")
    gpp_col = None
    if GPP_NT in raw.columns:
        g = daily(GPP_NT)
        if g.notna().any():
            gpp_col = GPP_NT
    if gpp_col is None and GPP_DT in raw.columns:
        g = daily(GPP_DT)
        if g.notna().any():
            gpp_col = GPP_DT
    if gpp_col is None:
        g = pd.Series(np.nan, index=nee.index)
    df = pd.DataFrame({"EC_GPP": g, "EC_NEE": nee})
    df["EC_GPP_column"] = np.where(df["EC_GPP"].notna(), gpp_col or "", "")
    df["EC_GPP_source"] = np.where(df["EC_GPP"].notna(), path.name, "")
    df["EC_source"] = path.name
    return df, gpp_col, cadence


def ec_daily(paths, first, last, min_hh):
    combined, prov = None, []
    for p in paths:
        d, col, cadence = ec_daily_one(p, first, last, min_hh)
        if d is None:
            prov.append({"path": str(p), "gpp_column": "NONE", "reason": "no timestamps in forcing period"})
            continue
        prov.append({"path": str(p), "gpp_column": col or "NONE", "sample_interval_seconds": cadence,
                     "valid_GPP_days": int(d["EC_GPP"].notna().sum()), "valid_NEE_days": int(d["EC_NEE"].notna().sum())})
        if combined is None:
            combined = d
        else:
            combined = combined.reindex(combined.index.union(d.index)).sort_index()
            d = d.reindex(combined.index)
            # An NT value from any source outranks a DT value from an earlier
            # source. Within the same partition, the original source order wins.
            take = d["EC_GPP"].notna() & (
                combined["EC_GPP"].isna() |
                ((d["EC_GPP_column"] == GPP_NT) & (combined["EC_GPP_column"] == GPP_DT)))
            fields = ["EC_GPP", "EC_GPP_column", "EC_GPP_source"]
            combined.loc[take, fields] = d.loc[take, fields]
            combined["EC_NEE"] = combined["EC_NEE"].combine_first(d["EC_NEE"])
            combined["EC_source"] = combined["EC_source"].combine_first(d["EC_source"])
    if combined is None:
        raise ValueError(f"No EC timestamps in forcing period {first}-{last}")
    return combined.reset_index().rename(columns={"index": "date"}), prov


def metrics(obs, mod):
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


def monthly(daily, obs, mod, min_days):
    """Paired days only (as in the FLUXNET_MultiSite examples): a month is kept
    when >= min_days days have both EC and model values."""
    x = daily[["date", obs, mod]].dropna().set_index("date")
    m = x.resample("MS").mean(); nd = x[obs].resample("MS").count()
    m.loc[nd < min_days, [obs, mod]] = np.nan
    m[f"{obs}_NDAY"] = nd
    return m.reset_index()


def paired_monthly(model, obs, freq, min_days):
    if freq == "daily":
        daily = model.merge(obs, on="date", how="left", validate="one_to_one")
        mon = monthly(daily, "EC_GPP", "FATES_GPP", min_days).merge(
            monthly(daily, "EC_NEE", "FATES_NEE", min_days), on="date", how="outer")
        return daily, mon.sort_values("date").reset_index(drop=True)
    o = obs.set_index("date")[["EC_GPP", "EC_NEE"]]
    em = o.resample("MS").mean(); nd = o.resample("MS").count()
    for f in ("EC_GPP", "EC_NEE"):
        em.loc[nd[f] < min_days, f] = np.nan
        em[f"{f}_NDAY"] = nd[f]
    mon = model[["date", "FATES_GPP", "FATES_NEE", "model_year"]].merge(
        em.reset_index(), on="date", how="left", validate="one_to_one")
    return None, mon


# ------------------------------------------------------------------ convergence
def trend(v, w):
    a = np.asarray(v[-w:], float); ok = np.isfinite(a)
    if len(a) < w or ok.sum() < max(15, int(0.8 * w)):
        return np.nan, np.nan
    s = float(np.polyfit(np.arange(len(a))[ok], a[ok], 1)[0]); mu = float(np.nanmean(a))
    return s, (np.nan if abs(mu) < 1e-8 else 100 * s * 100 / abs(mu))


def convergence(carbon, names, meta, n_force, align):
    nor = carbon[carbon.Phase == "NORMAL"]
    ad = carbon[carbon.Phase == "AD"]
    nN = len(nor)
    recs = []
    for name in names:
        v = nor[name].to_numpy(float)
        s30, r30 = trend(v, 30); s100, r100 = trend(v, 100)
        years = nor.ModelYear.to_numpy(int)
        starts = [i for i, y in enumerate(years)
                  if (y - align) % n_force == 0 and i + n_force <= nN]
        k = len(starts)
        last = v[starts[-1]:starts[-1] + n_force] if k >= 1 else np.array([])
        prev = v[starts[-2]:starts[-2] + n_force] if k >= 2 else np.array([])
        first = v[starts[0]:starts[0] + n_force] if k >= 1 else np.array([])
        cyc = (100 * np.nanmean(np.abs(last - prev)) / max(np.nanmean(np.abs(prev)), 1e-8)) if len(prev) else np.nan
        pct = lambda a, b: np.nan if not (np.isfinite(a) and np.isfinite(b)) or abs(b) < 1e-8 else 100 * (a - b) / abs(b)
        recs.append({
            "Variable": name, "Units": meta[name]["csv_units"],
            "AD_end_value_spinup400": float(ad[name].iloc[-1]) if len(ad) else np.nan,
            "Normal_start_value_spinup401": float(v[0]) if nN else np.nan,
            "Normal_end_value": float(v[-1]) if nN else np.nan,
            "Normal_years_available": nN,
            "Last30y_slope_per_year": s30, "Last30y_trend_pct_per_100y": r30,
            "Last100y_slope_per_year": s100, "Last100y_trend_pct_per_100y": r100,
            "Abs_last100y_slope_lt_1gC_m2_yr": (bool(abs(s100) < 1.0) if np.isfinite(s100) and meta[name]["csv_units"] == "g C m-2" else ""),
            "Normal_complete_cycles": k,
            "Last_two_aligned_cycles_mean_abs_change_pct": cyc,
            "Last_two_aligned_cycles_mean_change_pct": pct(np.nanmean(last), np.nanmean(prev)) if k >= 2 else np.nan,
            "Last_aligned_cycle_start_model_year": int(years[starts[-1]]) if k >= 1 else np.nan,
            "Previous_aligned_cycle_start_model_year": int(years[starts[-2]]) if k >= 2 else np.nan,
            "First_vs_last_aligned_Normal_cycle_mean_change_pct": pct(np.nanmean(last), np.nanmean(first)) if k >= 2 else np.nan,
        })
    return pd.DataFrame(recs)


# ------------------------------------------------------------------ plots
def plot_overview(carbon, names, meta, site, title_cases, dest, interim):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    nrow = math.ceil(len(names) / 2)
    fig, axs = plt.subplots(nrow, 2, figsize=(16, 3.5 * nrow), sharex=True, squeeze=False)
    ad = carbon[carbon.Phase == "AD"]
    nor = carbon[carbon.Phase == "NORMAL"]
    xmax = max(800, int(carbon.SpinupYear.max()))
    for ax, n in zip(axs.flat, names):
        ax.plot(ad.SpinupYear, ad[n], lw=1.15, color="#2878b5", label="AD")
        ax.plot(nor.SpinupYear, nor[n], lw=1.15, color="#db7b2b", label="Normal")
        ax.axvline(PHASE + 0.5, color="0.35", ls="--", lw=1.0)
        ax.set(xlim=(1, xmax), title=f"{n} ({LABELS.get(n, n)})")
        ax.set_ylabel(meta[n]["plot_units"]); ax.grid(alpha=0.22)
    for ax in list(axs.flat)[len(names):]:
        ax.set_visible(False)
    for ax in axs[-1]:
        if ax.get_visible(): ax.set_xlabel("Spin-up year (1–400 AD; 401–800 Normal)")
    axs.flat[0].legend(frameon=False, loc="best")
    tag = " — INTERIM (incomplete)" if interim else ""
    fig.suptitle(f"{site} | AD400 + NORMAL400: annual mean carbon pools{tag}\n{title_cases}\n"
                 "Dashed line: AD → Normal; accelerated pools may be rescaled, not a physical annual gain", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); p = dest / f"{site}_01_carbon_pools_AD400_NORMAL400.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig); return p


def plot_panels(carbon, names, meta, site, dest, interim, conv, n_force):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    nor = carbon[carbon.Phase == "NORMAL"]
    nrow = math.ceil(len(names) / 2)
    fig, axs = plt.subplots(nrow, 2, figsize=(16, 4.2 * nrow), sharex=True, squeeze=False)
    x = nor.SpinupYear.to_numpy()
    for ax, n in zip(axs.flat, names):
        ax.plot(x, nor[n].to_numpy(float), lw=1.35)
        if len(nor) >= 100:
            ax.axvspan(x[-100], x[-1], color="0.8", alpha=0.22)
        r = conv.loc[conv.Variable == n].iloc[0]
        def fmt(v, suffix, signed=True):
            return (f"{v:+.2f}" if signed else f"{v:.2f}") + suffix if np.isfinite(v) else "N/A"
        txt = (f"Last 100 y trend: {fmt(r.Last100y_trend_pct_per_100y, '% / 100 y')}\n"
               f"Last two aligned {n_force}-y cycles: {fmt(r.Last_two_aligned_cycles_mean_change_pct, '% mean change')}\n"
               f"Mean absolute paired-year change: {fmt(r.Last_two_aligned_cycles_mean_abs_change_pct, '%', False)}  "
               f"(complete cycles: {int(r.Normal_complete_cycles)})")
        ax.set(xlim=(PHASE + 1, max(800, x.max())))
        ax.set_title(f"{n} ({LABELS.get(n, n)})\n{txt}", fontsize=9.5)
        ax.set_ylabel(meta[n]["plot_units"]); ax.grid(alpha=0.22)
    for ax in list(axs.flat)[len(names):]:
        ax.set_visible(False)
    for ax in axs[-1]:
        if ax.get_visible(): ax.set_xlabel("Spin-up year (Normal phase: 401–800)")
    tag = " — INTERIM" if interim else ""
    fig.suptitle(f"{site} | NORMAL phase: annual mean carbon pools and diagnostics{tag}\n"
                 "Final 100 years shaded when available; metrics describe drift, not an automatic convergence verdict", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); p = dest / f"{site}_02_carbon_pools_NORMAL400_panels.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig); return p


def plot_flux(mon, site, cycle, first, last, gpp_label, dest, interim):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.dates as mdates
    fig, axs = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    stats = []
    for ax, flux in zip(axs, ("GPP", "NEE")):
        o, m = f"EC_{flux}", f"FATES_{flux}"
        sc = metrics(mon[o], mon[m])
        stats.append({"Site": site, "Scale": "monthly", "Flux": flux, **sc})
        ax.plot(mon.date, mon[o], lw=1.45, label="EC tower" + (f" ({gpp_label})" if flux == "GPP" else " (NEE_VUT_REF)"))
        ax.plot(mon.date, mon[m], lw=1.45, label="FATES")
        if flux == "NEE":
            ax.axhline(0, ls="--", lw=0.8, color="0.5")
        ax.set_ylabel(f"{flux} (g C m$^{{-2}}$ d$^{{-1}}$)")
        ax.set_title(f"{flux} | monthly N={sc['N']}, R²={sc['R2']:.3f}, RMSE={sc['RMSE']:.3f}, bias={sc['Bias']:.3f}", fontsize=11)
        ax.grid(alpha=0.25); ax.legend(frameon=False, loc="upper left")
    axs[-1].xaxis.set_major_locator(mdates.YearLocator(2)); axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axs[-1].set_xlim(pd.Timestamp(first, 1, 1), pd.Timestamp(last + 1, 1, 1)); axs[-1].set_xlabel("EC observation year")
    tag = " — INTERIM" if interim else ""
    fig.suptitle(f"{site}: EC tower vs FATES (monthly means, {first}-{last}){tag}\n"
                 f"Last complete Normal-phase model cycle {cycle[0]}-{cycle[-1]}; GPP: NT preferred, DT only if NT unavailable", fontsize=13)
    fig.tight_layout(); p = dest / f"{site}_GPP_NEE_monthly_overview.png"
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig)
    return pd.DataFrame(stats), p


# ------------------------------------------------------------------ driver
def inventory(pair, args):
    s = pair["site"]
    y0 = int(env_value(pair["ad_case_dir"], "RUN_STARTDATE")[:4])
    normal_dir = args.cases_root / pair["normal"]
    if env_value(normal_dir, "RUN_REFCASE") != pair["ad"]:
        raise ValueError(f"{s}: Normal RUN_REFCASE does not match AD case")
    if int(env_value(normal_dir, "RUN_STARTDATE")[:4]) != y0 + PHASE:
        raise ValueError(f"{s}: Normal start is not the AD400 handoff year")
    first, last, align = forcing_years(normal_dir, args.archive_root.parent / pair["normal"] / "run")
    fad = history_index(args.archive_root, pair["ad"])
    try:
        fno = history_index(args.archive_root, pair["normal"])
    except FileNotFoundError:
        fno = {}
    ad_years = contiguous(fad, y0, PHASE)
    no_years = contiguous(fno, y0 + PHASE, PHASE)
    return {"site": s, "start": y0, "forcing": (first, last, align), "fad": fad, "fno": fno,
            "ad_years": ad_years, "normal_years": no_years,
            "complete": len(ad_years) == PHASE and len(no_years) == PHASE}


def process(pair, args):
    s = pair["site"]; inv = inventory(pair, args)
    first, last, align = inv["forcing"]; n = last - first + 1
    if not inv["complete"] and not args.allow_incomplete:
        raise RuntimeError(f"AD {len(inv['ad_years'])}/400, Normal {len(inv['normal_years'])}/400 years; "
                           "rerun later or use --allow-incomplete for INTERIM figures")
    if len(inv["ad_years"]) < PHASE:
        raise RuntimeError(f"AD phase incomplete ({len(inv['ad_years'])}/400); no Normal-phase diagnostics possible")
    interim = not inv["complete"]
    dest = args.output_root / s
    if getattr(args, "case_subdirectories", False):
        dest = dest / pair["normal"]
    dest.mkdir(parents=True, exist_ok=False)
    files = [(i + 1, y, "AD", inv["fad"][y]) for i, y in enumerate(inv["ad_years"])] + \
            [(PHASE + i + 1, y, "NORMAL", inv["fno"][y]) for i, y in enumerate(inv["normal_years"])]
    print(f"  AD {inv['ad_years'][0]}–{inv['ad_years'][-1]} ({len(inv['ad_years'])}), Normal "
          f"{(inv['normal_years'] or ['-'])[0]}–{(inv['normal_years'] or ['-'])[-1]} ({len(inv['normal_years'])}); "
          f"forcing {first}-{last} align {align}", flush=True)
    carbon, names, meta = annual_carbon(files, s)
    carbon.to_csv(dest / f"{s}_carbon_annual_means.csv", index=False)
    conv = convergence(carbon, names, meta, n, align); conv.to_csv(dest / f"{s}_convergence_metrics.csv", index=False)
    cases = f"{pair['ad']} → {pair['normal']} | model years {inv['start']}–{inv['start'] + len(files) - 1}"
    plot_overview(carbon, names, meta, s, cases, dest, interim)
    if inv["normal_years"]:
        plot_panels(carbon, names, meta, s, dest, interim, conv, n)
    status, err, prov, scores, cycle, gpp_cols, freq = "CARBON_ONLY", "", [], None, [], [], ""
    if not args.carbon_only:
        try:
            cycle = last_complete_cycle(inv["normal_years"], first, last, align)
            model, freq = fates_samples([(y, inv["fno"][y]) for y in cycle], first, last, align)
            srcs = ec_sources(args.sites_root / s / "forcing", args.obs_csv.get(s))
            obs, prov = ec_daily(srcs, first, last, args.min_halfhour)
            gpp_cols = sorted({c for c in obs["EC_GPP_column"].dropna() if c})
            daily, mon = paired_monthly(model, obs, freq, args.min_days)
            for flux in ("GPP", "NEE"):
                matched = mon[[f"EC_{flux}", f"FATES_{flux}"]].dropna()
                if len(matched) < 2:
                    raise ValueError(f"{flux}: fewer than two matched monthly observations")
            mon.to_csv(dest / f"{s}_monthly_FATES_vs_EC.csv", index=False)
            label = " + ".join(gpp_cols) if gpp_cols else "no GPP"
            scores, _ = plot_flux(mon, s, cycle, first, last, label, dest, interim)
            if daily is not None:
                daily.to_csv(dest / f"{s}_daily_FATES_vs_EC.csv", index=False)
                daily_sc = pd.DataFrame([{"Site": s, "Scale": "daily", "Flux": f,
                                          **metrics(daily[f"EC_{f}"], daily[f"FATES_{f}"])} for f in ("GPP", "NEE")])
                scores = pd.concat([scores, daily_sc], ignore_index=True)
            scores.to_csv(dest / f"{s}_flux_metrics.csv", index=False)
            status = "OK"
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"; status = "CARBON_OK_EC_ERROR"
            print(f"  EC comparison skipped: {err}", file=sys.stderr, flush=True)
    meta_out = {"site": s, "cohort": pair.get("cohort", ""), "ad_case": pair["ad"], "normal_case": pair["normal"],
                "status": status, "interim": interim, "ec_error": err,
                "ad_years": [inv["ad_years"][0], inv["ad_years"][-1]] if inv["ad_years"] else [],
                "normal_years": [inv["normal_years"][0], inv["normal_years"][-1]] if inv["normal_years"] else [],
                "forcing_first_last_align": [first, last, align], "model_history_frequency": freq, "ec_cycle_model_years": [cycle[0], cycle[-1]] if cycle else [],
                "gpp_policy": "NT takes priority across all sources; DT only when the source has no usable NT and no NT is available for that day",
                "ec_gpp_columns_used": gpp_cols, "ec_sources": prov, "ec_source_priority": SOURCE_PRIORITY,
                "model_gpp": "FATES_GPP", "model_nee": "-FATES_NEP", "ec_nee": "NEE_VUT_REF",
                "flux_units": "g C m-2 d-1", "carbon_variables": names, "carbon_units": meta,
                "missing_primary_carbon_variables": [n for n in ("TOTECOSYSC", "TOTSOMC", "FATES_VEGC") if n not in names],
                "caveat": "AD/Normal transition may include pool rescaling. 800 years is not proof of equilibrium. EC/model day alignment uses native timestamps without a timezone conversion; verify the clock basis, especially for UTC-shifted AmeriFlux forcing.",
                "files": sorted(p.name for p in dest.iterdir() if p.is_file())}
    (dest / f"{s}_metadata.json").write_text(json.dumps(meta_out, indent=2, default=str) + "\n")
    row = {"Site": s, "Status": status, "Interim": interim, "NormalYears": len(inv["normal_years"]),
           "GPP_columns": "+".join(gpp_cols), "ECError": err}
    for _, r in conv[conv.Variable.isin(["TOTECOSYSC", "TOTSOMC", "FATES_VEGC"])].iterrows():
        row[f"{r.Variable}_last100y_trend_pct_per_100y"] = r.Last100y_trend_pct_per_100y
    if scores is not None:
        for _, r in scores[scores.Scale == "monthly"].iterrows():
            row[f"{r.Flux}_monthly_R2"] = r.R2; row[f"{r.Flux}_monthly_RMSE"] = r.RMSE; row[f"{r.Flux}_monthly_bias"] = r.Bias
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", nargs="+", help="Batch03 sites (default all ten)")
    ap.add_argument("--pair", nargs="*", default=[], metavar="SITE:AD_CASE:NORMAL_CASE",
                    help="explicit case pairs for other cohorts (replaces the Batch03 registry)")
    ap.add_argument("--user", default="ly3n24")
    ap.add_argument("--archive-root", type=Path); ap.add_argument("--cases-root", type=Path)
    ap.add_argument("--sites-root", type=Path)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--preflight", action="store_true", help="read-only completeness/EC inventory")
    ap.add_argument("--allow-incomplete", action="store_true", help="make INTERIM figures before Normal400 ends")
    ap.add_argument("--carbon-only", action="store_true")
    ap.add_argument("--obs-csv", nargs="*", default=[], metavar="SITE=/abs/HH.csv")
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    a = ap.parse_args()
    a.archive_root = a.archive_root or Path(f"/scratch/{a.user}/CTSM_FATES_OUTPUTS/archive")
    a.cases_root = a.cases_root or Path(f"/iridisfs/scratch/{a.user}/CLM_FATES/cases")
    a.sites_root = a.sites_root or Path(f"/iridisfs/scratch/{a.user}/CLM_FATES/sites/MY_EC_SITE")
    a.obs_csv = {x.partition("=")[0]: x.partition("=")[2] for x in a.obs_csv}
    if a.pair:
        pairs = []
        for p in a.pair:
            s, ad, no = p.split(":")
            pairs.append({"site": s, "ad": ad, "normal": no, "ad_case_dir": a.cases_root / ad, "cohort": "explicit"})
    else:
        pairs = batch03_pairs(a.sites)
    if a.preflight:
        issues = 0
        for p in pairs:
            try:
                inv = inventory(p, a)
                f1, f2, al = inv["forcing"]
                nfile = len(next(iter(inv["fad"].values())))
                line = (f"{p['site']:7} AD {len(inv['ad_years'])}/400  Normal {len(inv['normal_years'])}/400  "
                        f"{'annual-files' if nfile == 1 else 'monthly-files'}  "
                        f"{'COMPLETE' if inv['complete'] else 'INCOMPLETE'}  forcing {f1}-{f2} align {al}")
                try:
                    srcs = ec_sources(a.sites_root / p["site"] / "forcing", a.obs_csv.get(p["site"]))
                    cols = []
                    for sp in srcs:
                        c = pd.read_csv(sp, nrows=0, encoding="latin-1").columns
                        have = "+".join(k for k, col in (("NT", GPP_NT), ("DT", GPP_DT)) if col in c)
                        cols.append(f"{sp.name}[cols {have}; NT used if it has valid days]")
                    line += "  EC: " + ", ".join(cols)
                except Exception as e:
                    issues += 1
                    line += f"  EC NEEDS REVIEW: {e}"
                if not inv["complete"]:
                    issues += 1
                print(line, flush=True)
            except Exception as e:
                issues += 1
                print(f"{p['site']:7} FAIL {type(e).__name__}: {e}", flush=True)
        return int(issues > 0)
    if a.output_root is None or not a.output_root.is_absolute():
        ap.error("--output-root must be an absolute path (Research Filestore or home), not scratch")
    out = a.output_root.expanduser().resolve()
    for scratch in (Path("/scratch"), Path("/iridisfs/scratch")):
        if out == scratch or scratch in out.parents:
            ap.error("Refusing to write under scratch: " + str(out))
    if out.exists() and any(out.iterdir()):
        ap.error("Output root is not empty; choose a new directory to avoid overwriting results: " + str(out))
    out.mkdir(parents=True, exist_ok=True); a.output_root = out
    rows = []
    for p in pairs:
        print("\n" + "=" * 16 + f" {p['site']} " + "=" * 16, flush=True)
        try:
            rows.append(process(p, a))
        except Exception as exc:
            print(f"  SKIP {p['site']}: {type(exc).__name__}: {exc}", flush=True)
            if os.environ.get("DEBUG"):
                traceback.print_exc()
            rows.append({"Site": p["site"], "Status": "SKIPPED", "ECError": str(exc)})
    pd.DataFrame(rows).to_csv(out / "AD400_NORMAL400_summary.csv", index=False)
    print("\nSUMMARY written:", out / "AD400_NORMAL400_summary.csv")
    print(pd.DataFrame(rows).to_string(index=False))
    if any(r["Status"] not in ("OK", "CARBON_ONLY") for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


