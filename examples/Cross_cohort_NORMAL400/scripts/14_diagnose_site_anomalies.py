#!/usr/bin/env python3
"""Why did CZ-Stn and DE-Lnf (broadleaf, DBF 100) collapse, and why is US-CMW GPP low?  Read-only.

Each target site is compared with a reference site whose model works:
  CZ-Stn, DE-Lnf  vs  DE-Hzd  (same batch B03, same DBF 100 set-up, survives)
  US-CMW          vs  US-SRM  (nearby Arizona mesquite site, model GPP close to EC)

Nothing is re-run. For every target and its reference the script reads:

 1. Case set-up (static): the executed lnd_in (run dir, else CaseDocs) of the AD and Normal case,
    key env_*.xml settings, user_nl_* files, the surface file (land-unit and PFT percentages,
    soil texture, organic matter, bedrock depth), the FATES parameter file (SHA-256 and differing
    parameters), finidat / cold start.  Target-vs-reference differences go to <label>_setup_diff.csv.
 2. Meteorological forcing: the CLM_USRDAT DATM stream files actually used (run/datm.streams.xml),
    monthly means of every forcing variable, unit/range checks (K vs degC, mm/s vs mm, Pa vs hPa,
    missing values, negative precipitation, coverage of year_first..year_last), and the same months
    from the EC tower meteorology (TA_F, SW_IN_F, P_F, VPD_F, LE_F_MDS, SWC).
 3. The first --ad-years of the AD history (TLAI, FATES_GPP, FATES_NPP, TOTSOMC, TWS, H2OSNO, ...):
    when the vegetation disappears, and whether snow or water storage runs away.
 4. The last complete forcing cycle of the Normal case, month by month against EC: GPP, ET vs
    precipitation (water balance), LAI, GPP by PFT, BTRAN, soil water by depth, water table,
    phenology variables.  Months with EC GPP well above the model are classified as
    "no leaves" (phenology / drought leaf-off), "leaves but water-stressed" or "leaves, not water-limited".

Outputs (never under scratch):
  <out>/<label>/<label>_01_forcing_vs_EC.png, _02_AD_first_years.png, _03_seasonal_water_carbon.png
  <out>/<label>/<label>_setup_diff.csv, _forcing_monthly.csv, _forcing_checks.csv, _EC_monthly.csv,
                 _AD_annual.csv, _normal_seasonal.csv, _findings.txt
  <out>/site_anomaly_summary.csv, RUN_COMPLETE.json
Usage (login node; ~1-3 min per site, mostly reading the EC csv):
  python -B 14_...py --output-root DIR [--specs LABEL:NORMAL_CASE:REF_LABEL:REF_NORMAL_CASE ...]
  python -B 14_...py --publish-run DIR
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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIG_DIR = "figures/AD400_NORMAL400_site_anomaly_diagnostics"
DEFAULT_SPECS = ["CZ-Stn:CZ-Stn_B03_FIXNC_NORMAL400:DE-Hzd:DE-Hzd_B03_FIXNC_NORMAL400",
                 "DE-Lnf:DE-Lnf_B03_FIXNC_NORMAL400:DE-Hzd:DE-Hzd_B03_FIXNC_NORMAL400",
                 "US-CMW:US-CMW_AMF_B02_FIXNC_NORMAL400_DIRECT:US-SRM:US-SRM_AMF_B04_FIXNC_NORMAL400_BASETA_V1"]
DAYS = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], float)
ENV_KEYS = ["RUN_TYPE", "RUN_STARTDATE", "RUN_REFCASE", "RUN_REFDATE", "CLM_FORCE_COLDSTART", "CLM_ACCELERATED_SPINUP",
            "CLM_BLDNML_OPTS", "CLM_NML_USE_CASE", "CLM_USRDAT_NAME", "CCSM_CO2_PPMV", "DATM_MODE", "DATM_PRESAERO",
            "DATM_CO2_TSERIES", "DATM_YR_ALIGN", "DATM_YR_START", "DATM_YR_END", "PTS_LAT", "PTS_LON",
            "ATM_DOMAIN_MESH", "LND_DOMAIN_MESH", "MASK_MESH", "ATM_NCPL", "COMP_ROOT_DIR_LND", "STOP_OPTION", "STOP_N",
            "RESUBMIT", "RUNDIR"]
USER_NL = ["user_nl_clm", "user_nl_datm", "user_nl_datm_streams"]
SURF_VARS = ["LATIXY", "LONGXY", "PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN",
             "PCT_NAT_PFT", "PCT_SAND", "PCT_CLAY", "ORGANIC", "zbedrock", "FMAX", "SLOPE", "STD_ELEV", "SOIL_COLOR",
             "LANDFRAC_PFT", "PFTDATA_MASK", "AREA"]
AD_VARS = ["TLAI", "FATES_GPP", "FATES_NPP", "FATES_VEGC", "TOTSOMC", "TOTECOSYSC", "TWS", "H2OSNO", "BTRAN",
           "TSA", "RAIN", "SNOW", "FSDS"]
SEAS_SCALARS = ["FATES_GPP", "TLAI", "BTRAN", "RAIN", "SNOW", "QVEGT", "QVEGE", "QSOIL", "QDRAI", "QOVER", "QRUNOFF",
                "ZWT", "ZWT_PERCH", "TWS", "H2OSNO", "FSDS", "TSA", "RH2M", "FATES_LAI"]
SEAS_LAYERED = ["H2OSOI", "SOILLIQ"]
SEAS_PFT = ["FATES_GPP_PF", "FATES_LEAFC_PF", "FATES_NOCOMP_PATCHAREA_PF", "FATES_CANOPYCROWNAREA_PF"]
PHEN_RE = re.compile(r"PHEN|LEAFON|LEAFOFF|DROUGHT|GDD|NCHILL|NCOLD|ELONG", re.I)
BANDS = [(0.0, 0.1), (0.1, 0.5), (0.5, 1.0), (1.0, 3.0)]
EC_MET = {"TA": ("TA_F", "TA_F_MDS", "TA"), "SW_IN": ("SW_IN_F", "SW_IN_F_MDS", "SW_IN"), "P": ("P_F", "P"),
          "VPD": ("VPD_F", "VPD_F_MDS", "VPD"), "LE": ("LE_F_MDS", "LE_CORR", "LE"), "WS": ("WS_F", "WS"),
          "PA": ("PA_F", "PA"), "SWC1": ("SWC_F_MDS_1", "SWC_1"), "SWC2": ("SWC_F_MDS_2", "SWC_2")}
# forcing field -> (plausible range of the monthly mean in the expected units, expected unit text)
FORCING_RANGE = {"TBOT": ((200.0, 330.0), "K"), "PRECTmms": ((0.0, 2e-4), "mm/s"), "FSDS": ((5.0, 450.0), "W/m2"),
                 "FLDS": ((100.0, 500.0), "W/m2"), "QBOT": ((0.0, 0.04), "kg/kg"), "RH": ((1.0, 100.5), "%"),
                 "WIND": ((0.0, 30.0), "m/s"), "PSRF": ((40000.0, 108000.0), "Pa")}

F7 = None
P = None


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


# ------------------------------------------------------------------ small helpers
def arr(var):
    a = var[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    return a


def by_time(var):
    """(time, k) array of a single-point variable with a time dimension."""
    a = arr(var)
    dims = list(var.dimensions)
    a = np.moveaxis(a, dims.index("time"), 0)
    return a.reshape(a.shape[0], -1)


def is_point(var):
    dims = list(var.dimensions)
    return "time" in dims and int(np.prod([n for d, n in zip(dims, var.shape) if d != "time"])) == 1


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def env(case_dir, key):
    try:
        return P.env_value(case_dir, key)
    except Exception:
        return None


def parse_nml(text):
    """{key: value} from a Fortran namelist file (continuation lines joined, whitespace collapsed)."""
    out = {}
    body = "\n".join(l.split("!")[0] if "'" not in l and '"' not in l else l for l in text.splitlines())
    pat = re.compile(r"^\s*([A-Za-z_][\w%]*)\s*=\s*(.*?)\s*(?=^\s*[A-Za-z_][\w%]*\s*=|^\s*/|^\s*&|\Z)", re.M | re.S)
    for m in pat.finditer(body):
        out[m.group(1).lower()] = re.sub(r"\s+", " ", m.group(2)).strip().rstrip(",").strip()
    return out


def unquote(v):
    return (v or "").strip().strip("'\"").strip()


def run_dir_of(case, args):
    rd = env(args.cases_root / case, "RUNDIR")
    if rd and "$" not in rd:
        return Path(rd)
    return args.archive_root.parent / case / "run"


def decode_times(ds):
    """(year, month) arrays of the time coordinate; noleap/365_day or proleptic Gregorian."""
    t = ds.variables["time"]
    v = arr(t).ravel()
    units = str(getattr(t, "units", ""))
    cal = str(getattr(t, "calendar", "standard")).lower()
    m = re.match(r"\s*(days|hours|minutes|seconds)\s+since\s+(\d{1,4})-(\d{1,2})-(\d{1,2})"
                 r"(?:[ T](\d{1,2}):(\d{1,2})(?::(\d{1,2}(?:\.\d*)?))?)?", units)
    if not m:
        raise ValueError(f"unsupported time units {units!r}")
    scale = {"days": 1.0, "hours": 1 / 24, "minutes": 1 / 1440, "seconds": 1 / 86400}[m.group(1)]
    y0, mo0, d0 = int(m.group(2)), int(m.group(3)), int(m.group(4))
    hh = float(m.group(5) or 0) / 24 + float(m.group(6) or 0) / 1440 + float(m.group(7) or 0) / 86400
    d = v * scale + hh + 1e-6
    if cal in ("noleap", "365_day"):
        cum = np.concatenate([[0], np.cumsum(DAYS)])
        k = np.floor(d).astype(int) + int(cum[mo0 - 1]) + d0 - 1
        yy = y0 + k // 365
        mm = np.searchsorted(cum, k % 365, side="right")
        return yy.astype(int), mm.astype(int)
    base = np.datetime64(f"{y0:04d}-{mo0:02d}-{d0:02d}")
    dt = base + (d * 86400).astype("int64").astype("timedelta64[s]")
    return dt.astype("datetime64[Y]").astype(int) + 1970, dt.astype("datetime64[M]").astype(int) % 12 + 1


# ------------------------------------------------------------------ 1. case set-up
def parse_streams(path):
    streams = []
    if not path or not Path(path).is_file():
        return streams
    for e in ET.parse(path).getroot().iter():
        name = e.attrib.get("name")
        if not name:
            continue
        g = {"name": name, "files": [], "vars": []}
        for c in e.iter():
            tag, txt = c.tag, (c.text or "").strip()
            if tag == "file" and txt:
                g["files"].append(txt)
            elif tag == "var" and txt:
                g["vars"].append(txt.split()[0])
            elif tag in ("year_first", "year_last", "year_align", "offset", "tintalgo", "taxmode", "mapalgo", "meshfile",
                         "dtlimit"):
                g[tag] = txt
        streams.append(g)
    return streams


def read_surface(path):
    out = {}
    if not path or not Path(path).is_file():
        return out
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        for n in SURF_VARS:
            if n in ds.variables:
                a = arr(ds.variables[n]).ravel()
                out[n] = a
    return out


def case_setup(case, args):
    cd, rd = args.cases_root / case, run_dir_of(case, args)
    s = {"case": case, "case_dir": str(cd), "run_dir": str(rd)}
    if not cd.is_dir():
        raise FileNotFoundError(f"case directory missing: {cd}")
    s["env"] = {k: env(cd, k) for k in ENV_KEYS}
    src = next((p for p in (rd / "lnd_in", cd / "CaseDocs" / "lnd_in") if p.is_file()), None)
    s["lnd_in_path"] = str(src) if src else "missing"
    s["nml"] = parse_nml(src.read_text()) if src else {}
    s["user_nl"] = {f: ((cd / f).read_text() if (cd / f).is_file() else "") for f in USER_NL}
    sx = next((p for p in (rd / "datm.streams.xml", cd / "CaseDocs" / "datm.streams.xml") if p.is_file()), None)
    s["streams_path"] = str(sx) if sx else "missing"
    s["streams"] = parse_streams(sx)
    fs = unquote(s["nml"].get("fsurdat"))
    s["fsurdat"] = fs
    s["surface"] = read_surface(fs) if fs else {}
    pf = unquote(s["nml"].get("fates_paramfile"))
    s["paramfile"] = pf
    s["param_sha"] = sha256(pf) if pf and Path(pf).is_file() else "missing"
    s["finidat"] = unquote(s["nml"].get("finidat"))
    return s


def read_params(path):
    if not path or not Path(path).is_file():
        return {}
    path = Path(path)
    if path.suffix == ".json":
        d = json.loads(path.read_text())["parameters"]
        return {k: v.get("data") for k, v in d.items() if isinstance(v, dict)}
    from netCDF4 import Dataset
    out = {}
    with Dataset(str(path)) as ds:
        for k, v in ds.variables.items():
            try:
                if getattr(v, "dtype", np.dtype(float)).kind not in "SU":
                    out[k] = np.asarray(v[:]).tolist()
            except Exception:
                pass
    return out


def short(v, n=120):
    if isinstance(v, np.ndarray):
        v = np.round(v[np.isfinite(v)], 3).tolist() if v.size > 1 else (round(float(v[0]), 4) if np.isfinite(v[0]) else "nan")
    t = str(v)
    return t if len(t) <= n else t[:n - 3] + "..."


def setup_diff(t, r, label):
    """Rows (section, key, target, reference, differs, note).  Path values are compared on their file name
    with the site codes removed, so site-specific file names are not reported as set-up differences."""
    def norm(v, sites):
        v = str(v or "")
        if "/" in v:
            v = " ".join(Path(unquote(x)).name for x in re.split(r"[ ,]+", v) if x)
        for sc in sites:
            v = v.replace(sc, "<SITE>").replace(sc.replace("-", "_"), "<SITE>")
        return v
    sites = [label, t.get("ref_label", "")]
    sites = [x for x in sites if x] + [str(t["normal_case"]).split("_")[0], str(r["normal_case"]).split("_")[0]]
    rows = []
    for phase in ("AD", "NORMAL"):
        tn, rn = t[phase]["nml"], r[phase]["nml"]
        for k in sorted(set(tn) | set(rn)):
            a, b = tn.get(k, "<absent>"), rn.get(k, "<absent>")
            if norm(a, sites) != norm(b, sites):
                path_like = "/" in a or "/" in b
                rows.append(("lnd_in_" + phase, k, short(a), short(b), True, "path (site-specific name)" if path_like else ""))
        for k in ENV_KEYS:
            a, b = t[phase]["env"].get(k), r[phase]["env"].get(k)
            if k in ("RUN_REFCASE", "RUNDIR", "CLM_USRDAT_NAME", "PTS_LAT", "PTS_LON"):
                rows.append(("env_" + phase, k, short(a), short(b), norm(a, sites) != norm(b, sites), "site-specific"))
            elif norm(a, sites) != norm(b, sites):
                rows.append(("env_" + phase, k, short(a), short(b), True, ""))
        for f in USER_NL:
            a, b = t[phase]["user_nl"][f], r[phase]["user_nl"][f]
            na = sorted(norm(l, sites) for l in a.splitlines() if l.strip() and not l.strip().startswith("!"))
            nb = sorted(norm(l, sites) for l in b.splitlines() if l.strip() and not l.strip().startswith("!"))
            if na != nb:
                rows.append(("user_nl_" + phase, f, short(" | ".join(sorted(set(na) - set(nb))) or "-", 300),
                             short(" | ".join(sorted(set(nb) - set(na))) or "-", 300), True, "lines only in target | only in reference"))
    ts, rs = t["AD"]["surface"], r["AD"]["surface"]
    for k in SURF_VARS:
        a, b = ts.get(k), rs.get(k)
        diff = (a is None) != (b is None) or (a is not None and (a.shape != b.shape or not np.allclose(a, b, equal_nan=True)))
        rows.append(("surface", k, short(a) if a is not None else "absent", short(b) if b is not None else "absent", bool(diff), ""))
    rows.append(("parameters", "fates_paramfile", Path(t["AD"]["paramfile"]).name, Path(r["AD"]["paramfile"]).name,
                 t["AD"]["param_sha"] != r["AD"]["param_sha"], "SHA-256 compared"))
    if t["AD"]["param_sha"] != r["AD"]["param_sha"]:
        pa, pb = read_params(t["AD"]["paramfile"]), read_params(r["AD"]["paramfile"])
        for k in sorted(set(pa) | set(pb)):
            if json.dumps(pa.get(k), default=str) != json.dumps(pb.get(k), default=str):
                rows.append(("parameters", k, short(pa.get(k)), short(pb.get(k)), True, ""))
    for phase in ("AD", "NORMAL"):
        rows.append(("init_" + phase, "finidat", t[phase]["finidat"] or "(cold start)", r[phase]["finidat"] or "(cold start)",
                     bool(t[phase]["finidat"]) != bool(r[phase]["finidat"]), ""))
    return rows


# ------------------------------------------------------------------ 2. forcing
def met_streams(setup):
    return [s for s in setup["streams"] if re.search(r"USRDAT|1PT", s["name"], re.I) and s["files"]]


def read_forcing(setup):
    """Monthly means of every forcing variable of the site met streams, plus value statistics."""
    from netCDF4 import Dataset
    acc, stats, units, files = {}, {}, {}, 0
    for st in met_streams(setup):
        for f in st["files"]:
            p = Path(f)
            if not p.is_file():
                stats.setdefault("_missing_files", []).append(f)
                continue
            files += 1
            with Dataset(str(p)) as ds:
                yy, mm = decode_times(ds)
                for v in st["vars"]:
                    if v not in ds.variables or "time" not in ds.variables[v].dimensions:
                        continue
                    x = by_time(ds.variables[v])[:, 0]
                    units[v] = str(getattr(ds.variables[v], "units", ""))
                    s = stats.setdefault(v, {"n": 0, "nan": 0, "neg": 0, "min": np.inf, "max": -np.inf})
                    ok = np.isfinite(x)
                    s["n"] += x.size; s["nan"] += int((~ok).sum()); s["neg"] += int((x[ok] < 0).sum())
                    if ok.any():
                        s["min"], s["max"] = min(s["min"], float(x[ok].min())), max(s["max"], float(x[ok].max()))
                    for key in set(zip(yy.tolist(), mm.tolist())):
                        sel = (yy == key[0]) & (mm == key[1]) & ok
                        a = acc.setdefault(key, {})
                        tot, cnt = a.get(v, (0.0, 0))
                        a[v] = (tot + float(x[sel].sum()), cnt + int(sel.sum()))
    rows = [{"Year": y, "Month": m, **{v: (tc[0] / tc[1] if tc[1] else np.nan) for v, tc in d.items()}}
            for (y, m), d in sorted(acc.items())]
    df = pd.DataFrame(rows)
    return df, stats, units, files


def forcing_checks(df, stats, units, setup):
    """Rows (check, value, status, note)."""
    rows = []
    years = sorted(df["Year"].unique().tolist()) if not df.empty else []
    for st in met_streams(setup):
        y1, y2 = st.get("year_first", ""), st.get("year_last", "")
        if y1.isdigit() and y2.isdigit():
            need = set(range(int(y1), int(y2) + 1))
            miss = sorted(need - set(years))
            rows.append((f"coverage {st['name']}", f"{y1}-{y2}, {len(st['files'])} files", "FAIL" if miss else "ok",
                         f"years without data: {miss[:10]}" if miss else ""))
        rows.append((f"time interpolation {st['name']}", f"tintalgo={st.get('tintalgo', '?')} offset={st.get('offset', '?')}",
                     "info", ""))
    if stats.get("_missing_files"):
        rows.append(("missing forcing files", len(stats["_missing_files"]), "FAIL", stats["_missing_files"][0]))
    for v, ((lo, hi), want) in FORCING_RANGE.items():
        if v not in df:
            continue
        s, mean = stats.get(v, {}), float(np.nanmean(df[v]))
        status, note = "ok", f"units {units.get(v, '?')!r} (expected {want})"
        if not (lo <= mean <= hi):
            status = "FAIL"
            if v == "TBOT" and -60 < mean < 60:
                note += "; mean looks like degC, not K"
            elif v == "PSRF" and 400 < mean < 1100:
                note += "; mean looks like hPa, not Pa"
            elif v == "PRECTmms" and mean > hi:
                note += "; mean looks like mm per time step or mm/day, not mm/s"
        if s.get("nan"):
            frac = s["nan"] / max(s["n"], 1)
            if frac > 0.001:
                status = "FAIL" if frac > 0.05 else ("WARN" if status == "ok" else status)
                note += f"; missing/fill {100 * frac:.2f}% of samples"
        if v in ("PRECTmms", "FSDS", "QBOT", "WIND") and s.get("neg"):
            status = "WARN" if status == "ok" else status
            note += f"; {s['neg']} negative samples (min {s['min']:.3g})"
        val = mean
        if v == "PRECTmms":
            val = annual_total_mm(df)
            note += f"; annual precipitation {val:.0f} mm"
            if not (50 <= val <= 5000):
                status = "FAIL"
        rows.append((v, round(val, 6), status, note))
    return rows


def annual_total_mm(df, col="PRECTmms"):
    clim = df.groupby("Month")[col].mean().reindex(range(1, 13))
    return float(np.nansum(clim.to_numpy() * 86400 * DAYS))


def kelvin(units, values):
    """True when the model reads TBOT as Kelvin: CLM always does; only a missing unit with degC-like values is treated as degC."""
    u = (units or "").strip()
    return u.upper().startswith("K") or u == "" and np.nanmean(values) > 150


def forcing_clim(df, units=None):
    """Monthly climatology as the model reads it: TBOT converted K -> degC, P mm/month, others as written."""
    if df.empty:
        return pd.DataFrame({"Month": range(1, 13)})
    c = df.groupby("Month").mean(numeric_only=True).reindex(range(1, 13))
    out = pd.DataFrame({"Month": range(1, 13)})
    if "TBOT" in c:
        t = c["TBOT"].to_numpy(float)
        out["T_C"] = t - 273.15 if kelvin((units or {}).get("TBOT", "K"), t) else t
    if "PRECTmms" in c:
        out["P_mm_month"] = c["PRECTmms"].to_numpy(float) * 86400 * DAYS
    for v in ("FSDS", "FLDS", "QBOT", "RH", "WIND", "PSRF"):
        if v in c:
            out[v] = c[v].to_numpy(float)
    return out


# ------------------------------------------------------------------ EC
def ec_monthly(site, first, last, args):
    """EC meteorology + GPP as monthly values (Year, Month) within the forcing period."""
    srcs = P.ec_sources(args.sites_root / site / "forcing", None)
    obs, prov = P.ec_daily(srcs, first, last, args.min_halfhour)
    obs = obs.set_index("date")
    gpp = pd.to_numeric(obs["EC_GPP"], errors="coerce")
    mm, nd = gpp.resample("MS").mean(), gpp.resample("MS").count()
    mm[nd < args.min_days] = np.nan
    out = pd.DataFrame({"EC_GPP": mm})
    met_src = None
    for p in srcs:
        cols = pd.read_csv(p, nrows=0, encoding="latin-1").columns
        pick = {k: next((c for c in opts if c in cols), None) for k, opts in EC_MET.items()}
        pick = {k: c for k, c in pick.items() if c}
        if "TA" in pick and ("P" in pick or "SW_IN" in pick):
            met_src = (p, pick)
            break
    if met_src:
        p, pick = met_src
        raw = pd.read_csv(p, usecols=["TIMESTAMP_START"] + list(pick.values()), dtype={"TIMESTAMP_START": str},
                          low_memory=False, encoding="latin-1")
        ts = raw["TIMESTAMP_START"].str.strip().str.replace(r"\.0$", "", regex=True)
        raw.index = pd.to_datetime(ts, format="%Y%m%d%H%M", errors="coerce")
        raw = raw[raw.index.notna() & raw.index.year.isin(range(first, last + 1))]
        steps = raw.index.to_series().diff().dropna().dt.total_seconds()
        per_day = 86400 / (steps.mode().iloc[0] if not steps.empty else 1800)
        for k, c in pick.items():
            v = pd.to_numeric(raw[c], errors="coerce").astype(float)
            v[(v <= -9990) | ~np.isfinite(v)] = np.nan
            day_cnt = v.resample("D").count()
            if k == "P":
                d = v.resample("D").sum(min_count=1)
                d[day_cnt < 0.8 * per_day] = np.nan
                mon = d.resample("MS").mean()                    # mm/day, mean over valid days
                mon[d.resample("MS").count() < args.min_days] = np.nan
                out["EC_P_mm_day"] = mon
            else:
                d = v.resample("D").mean()
                d[day_cnt < args.min_halfhour * per_day / 48] = np.nan
                m = d.resample("MS").mean()
                m[d.resample("MS").count() < args.min_days] = np.nan
                out[f"EC_{k}"] = m
        if "EC_LE" in out:
            out["EC_ET_mm_day"] = out["EC_LE"] * 86400 / 2.45e6
    out = out.reset_index().rename(columns={"index": "date", "date": "date"})
    out["Year"], out["Month"] = out["date"].dt.year, out["date"].dt.month
    note = {"EC_sources": "; ".join(Path(x["path"]).name for x in prov),
            "EC_met_source": f"{Path(met_src[0]).name}: {met_src[1]}" if met_src else "no EC meteorology columns found"}
    return out.drop(columns=["date"]), note


# ------------------------------------------------------------------ history reading
def read_history(paths, scalars, layered=(), pftvars=(), pattern=None):
    """Monthly records [{Year, Month, var: value or array}] + constants (ZSOI, DZSOI) + units."""
    from netCDF4 import Dataset
    recs, const, units = [], {}, {}
    for path in paths:
        with Dataset(str(path)) as ds:
            bname = next((b for b in ("time_bounds", "time_bnds") if b in ds.variables), None)
            if bname is None:
                raise ValueError(f"{path.name}: no time bounds")
            b = np.asarray(ds.variables[bname][:], dtype=float)
            dur = b[:, 1] - b[:, 0]
            dates = P.noleap_dates(ds)
            names = list(scalars) + ([n for n in ds.variables if pattern and pattern.search(n) and is_point(ds.variables[n])]
                                     if pattern else [])
            vals = {}
            for n in dict.fromkeys(names):
                if n in ds.variables and is_point(ds.variables[n]):
                    vals[n] = by_time(ds.variables[n])[:, 0]
            for n in list(layered) + list(pftvars):
                if n in ds.variables and "time" in ds.variables[n].dimensions:
                    vals[n] = by_time(ds.variables[n])
            units.update({n: str(getattr(ds.variables[n], "units", "")) for n in vals})
            if not const:
                for n in ("ZSOI", "DZSOI"):
                    if n in ds.variables:
                        a = arr(ds.variables[n])
                        const[n] = (by_time(ds.variables[n])[0] if "time" in ds.variables[n].dimensions else a.reshape(-1))
                if "ZSOI" not in const and "levgrnd" in ds.variables:
                    const["ZSOI"] = arr(ds.variables["levgrnd"]).reshape(-1)
            for i, (yy, mm, _) in enumerate(dates):
                recs.append({"Year": yy, "Month": mm, "w": dur[i], **{n: v[i] for n, v in vals.items()}})
    out = []
    df = pd.DataFrame(recs)
    if df.empty:
        return [], const, units
    for (y, m), g in df.groupby(["Year", "Month"], sort=True):
        w = g["w"].to_numpy(float)
        r = {"Year": int(y), "Month": int(m)}
        for n in g.columns:
            if n in ("Year", "Month", "w"):
                continue
            st = np.vstack([np.atleast_1d(np.asarray(x, dtype=float)) for x in g[n]])
            ok = np.isfinite(st)
            num, den = np.nansum(np.where(ok, st, 0) * w[:, None], axis=0), np.sum(ok * w[:, None], axis=0)
            v = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
            r[n] = v if v.size > 1 else float(v[0])
        out.append(r)
    return out, const, units


def gpp_factor(u):
    u = (u or "").replace(" ", "").lower()
    return 1000.0 * 86400 if u.startswith("kg") else (86400.0 if u.startswith("g") else 1000.0 * 86400)


def mm_s(u):
    return 86400.0  # CLM water fluxes are mm/s (= kg m-2 s-1)


# ------------------------------------------------------------------ 3. AD first years
def ad_first_years(ad_case, args):
    fidx = P.history_index(args.archive_root, ad_case)
    years = sorted(fidx)[: args.ad_years]
    rows, units = [], {}
    for y in years:
        recs, _, u = read_history(fidx[y], AD_VARS)
        units.update(u)
        rows += recs
    mon = pd.DataFrame(rows)
    for n in ("FATES_GPP", "FATES_NPP"):
        if n in mon:
            mon[n] = mon[n] * gpp_factor(units.get(n))
    if "FATES_VEGC" in mon and units.get("FATES_VEGC", "").lower().startswith("kg"):
        mon["FATES_VEGC"] *= 1000.0
    ann = []
    for y, g in mon.groupby("Year", sort=True):
        g = g.sort_values("Month")
        w = DAYS[g["Month"].to_numpy(int) - 1]
        r = {"Year": int(y), "SpinupYear": years.index(y) + 1}
        for n in mon.columns:
            if n in ("Year", "Month"):
                continue
            v = g[n].to_numpy(float)
            r[n] = float(np.nansum(v * w) / w[np.isfinite(v)].sum()) if np.isfinite(v).any() else np.nan
            if n in ("H2OSNO", "TWS"):
                r[n + "_min"] = float(np.nanmin(v)) if np.isfinite(v).any() else np.nan
        ann.append(r)
    return pd.DataFrame(ann), mon, units


def collapse_year(ann, var="TLAI"):
    if var not in ann or ann[var].isna().all():
        return None, None
    v = ann[var].to_numpy(float)
    peak = np.nanmax(v[: min(len(v), 40)])
    if not np.isfinite(peak) or peak <= 0:
        return None, peak
    low = v < 0.05 * peak
    for i in range(len(v)):
        if low[i:].all():
            return int(ann["SpinupYear"].iloc[i]), float(peak)
    return None, float(peak)


# ------------------------------------------------------------------ 4. Normal seasonal cycle
def band_means(lay, z, dz):
    out = {}
    if lay is None or z is None:
        return out
    n = min(lay.shape[-1], len(z))
    for lo, hi in BANDS:
        sel = (z[:n] >= lo) & (z[:n] < hi)
        if sel.any():
            w = dz[:n][sel]
            out[f"{lo:g}-{hi:g}m"] = float(np.nansum(lay[:n][sel] * w) / w.sum())
    return out


def normal_seasonal(normal_case, args):
    cd, rd = args.cases_root / normal_case, run_dir_of(normal_case, args)
    first, last, align = P.forcing_years(cd, rd)
    fidx = P.history_index(args.archive_root, normal_case)
    cycle = P.last_complete_cycle(sorted(fidx), first, last, align)
    n = last - first + 1
    rows, const, units = [], {}, {}
    for y in cycle:
        recs, c, u = read_history(fidx[y], SEAS_SCALARS, SEAS_LAYERED, SEAS_PFT, PHEN_RE)
        const = const or c
        units.update(u)
        for r in recs:
            r["Year_EC"] = first + (r["Year"] - align) % n
        rows += recs
    z = const.get("ZSOI")
    dz = const.get("DZSOI")
    if z is not None and dz is None:
        edges = np.concatenate([[0.0], 0.5 * (z[1:] + z[:-1]), [z[-1] + 0.5 * (z[-1] - z[-2])]])
        dz = np.diff(edges)
    out = []
    for r in rows:
        o = {"ModelYear": r["Year"], "Year": r["Year_EC"], "Month": r["Month"]}
        for k, v in r.items():
            if k in ("Year", "Month", "Year_EC", "w") or k in SEAS_LAYERED or k in SEAS_PFT:
                continue
            o[k] = v
        if "FATES_GPP" in o:
            o["GPP_gC_m2_d"] = o["FATES_GPP"] * gpp_factor(units.get("FATES_GPP"))
        et = [o.get(k) for k in ("QVEGT", "QVEGE", "QSOIL")]
        if all(x is not None for x in et):
            o["ET_mm_day"] = float(np.sum(et)) * mm_s(None)
            o["T_mm_day"] = o["QVEGT"] * 86400
        if "RAIN" in o:
            o["P_model_mm_day"] = (o["RAIN"] + o.get("SNOW", 0.0)) * 86400
        for k in ("H2OSOI",):
            if k in r:
                for b, v in band_means(np.asarray(r[k], float), z, dz).items():
                    o[f"{k}_{b}"] = v
        for k in SEAS_PFT:
            if k in r:
                a = np.atleast_1d(np.asarray(r[k], float))
                for i, v in enumerate(a):
                    if k == "FATES_GPP_PF":
                        v = v * gpp_factor(units.get(k))
                    o[f"{k}_pft{i + 1}"] = v
        out.append(o)
    return pd.DataFrame(out), (first, last, align), units


def classify_months(clim):
    """Months with EC GPP > 1 g C m-2 d-1 and model < 50% of EC."""
    rows = []
    if not {"EC_GPP", "GPP_gC_m2_d"} <= set(clim.columns):
        return rows
    lai_max = np.nanmax(clim["TLAI"]) if "TLAI" in clim and clim["TLAI"].notna().any() else np.nan
    for _, r in clim.iterrows():
        ec, mo = r["EC_GPP"], r["GPP_gC_m2_d"]
        if not (np.isfinite(ec) and ec > 1 and np.isfinite(mo) and mo < 0.5 * ec):
            continue
        lai, bt = r.get("TLAI", np.nan), r.get("BTRAN", np.nan)
        if np.isfinite(lai_max) and lai_max > 0 and np.isfinite(lai) and lai < 0.3 * lai_max:
            why = "no leaves (model leaf-off: phenology or drought deciduousness)"
        elif np.isfinite(bt) and bt < 0.3:
            why = "leaves present but water-stressed (BTRAN < 0.3)"
        else:
            why = "leaves present, not water-limited (light / temperature / capacity)"
        rows.append((int(r["Month"]), ec, mo, lai, bt, why))
    return rows


# ------------------------------------------------------------------ per-site driver
def site_bundle(label, normal_case, args, cache):
    if normal_case in cache:
        return cache[normal_case]
    b = {"label": label, "normal_case": normal_case, "errors": []}
    b["NORMAL"] = case_setup(normal_case, args)
    ad_case = b["NORMAL"]["env"].get("RUN_REFCASE")
    b["ad_case"] = ad_case
    b["AD"] = case_setup(ad_case, args) if ad_case else None
    if b["AD"] is None:
        raise ValueError(f"{normal_case}: RUN_REFCASE (AD case) not set")
    print(f"[{label}] set-up read: AD {ad_case}, Normal {normal_case}", flush=True)
    try:
        df, stats, units, nfiles = read_forcing(b["AD"])
        b["forcing"], b["forcing_checks"] = df, forcing_checks(df, stats, units, b["AD"])
        b["forcing_units"], b["forcing_files"] = units, nfiles
        sa = sorted(f for s in met_streams(b["AD"]) for f in s["files"])
        sn = sorted(f for s in met_streams(b["NORMAL"]) for f in s["files"])
        b["forcing_checks"].append(("AD and Normal use the same forcing files", len(sa), "ok" if sa == sn else "WARN",
                                    "" if sa == sn else f"AD {len(sa)} files, Normal {len(sn)} files differ"))
        print(f"[{label}] forcing: {nfiles} files", flush=True)
    except Exception as exc:
        b["forcing"], b["forcing_checks"] = pd.DataFrame(), [("forcing read", "", "FAIL", f"{type(exc).__name__}: {exc}")]
        b["errors"].append(f"forcing: {exc}")
    try:
        first, last, align = P.forcing_years(args.cases_root / normal_case, run_dir_of(normal_case, args))
        b["years"] = (first, last, align)
        b["ec"], b["ec_note"] = ec_monthly(label, first, last, args)
        print(f"[{label}] EC: {b['ec_note']['EC_met_source']}", flush=True)
    except Exception as exc:
        b["ec"], b["ec_note"] = pd.DataFrame(), {"EC_sources": f"FAILED {exc}"}
        b["errors"].append(f"EC: {exc}")
    try:
        b["ad_ann"], b["ad_mon"], _ = ad_first_years(ad_case, args)
        print(f"[{label}] AD history: {len(b['ad_ann'])} years", flush=True)
    except Exception as exc:
        b["ad_ann"], b["ad_mon"] = pd.DataFrame(), pd.DataFrame()
        b["errors"].append(f"AD history: {exc}")
    try:
        b["seas"], _, b["seas_units"] = normal_seasonal(normal_case, args)
        print(f"[{label}] Normal last cycle: {b['seas']['ModelYear'].min()}-{b['seas']['ModelYear'].max()}", flush=True)
    except Exception as exc:
        b["seas"] = pd.DataFrame()
        b["errors"].append(f"Normal history: {exc}")
    cache[normal_case] = b
    return b


def seasonal_clim(b):
    s, ec = b.get("seas"), b.get("ec")
    if s is None or s.empty:
        return pd.DataFrame()
    df = s.copy()
    if ec is not None and not ec.empty:
        df = df.merge(ec, on=["Year", "Month"], how="left")
    return df.groupby("Month").mean(numeric_only=True).reindex(range(1, 13)).reset_index()


def ec_vs_forcing(b):
    """Same-month comparison of forcing and EC meteorology (paired Year, Month)."""
    f, ec = b.get("forcing"), b.get("ec")
    if f is None or f.empty or ec is None or ec.empty:
        return {}
    m = f.merge(ec, on=["Year", "Month"], how="inner")
    out = {"paired_months": int(len(m))}
    if "TBOT" in m and "EC_TA" in m:
        t = m["TBOT"] - (273.15 if kelvin(b.get("forcing_units", {}).get("TBOT", "K"), m["TBOT"]) else 0)
        out["T_forcing_minus_EC_C"] = float(np.nanmean(t - m["EC_TA"]))
    if "PRECTmms" in m and "EC_P_mm_day" in m:
        ok = m["PRECTmms"].notna() & m["EC_P_mm_day"].notna()
        if ok.sum() >= 12:
            out["P_forcing_over_EC"] = float((m.loc[ok, "PRECTmms"] * 86400).sum() / max(m.loc[ok, "EC_P_mm_day"].sum(), 1e-9))
    if "FSDS" in m and "EC_SW_IN" in m:
        ok = m["FSDS"].notna() & m["EC_SW_IN"].notna()
        if ok.any():
            out["SW_forcing_over_EC"] = float(m.loc[ok, "FSDS"].mean() / max(m.loc[ok, "EC_SW_IN"].mean(), 1e-9))
    return out


def findings(label, t, r, diff_rows):
    F = []
    # set-up
    real = [d for d in diff_rows if d[4] and d[5] not in ("site-specific", "path (site-specific name)")]
    paths = [d for d in diff_rows if d[4] and d[5] == "path (site-specific name)"]
    F.append(f"SETUP: {len(real)} set-up differences vs {r['label']} that are not just site names "
             f"(lnd_in/env/user_nl/surface/parameters); {len(paths)} site-specific file paths differ (expected).")
    for d in real[:25]:
        F.append(f"   {d[0]} {d[1]}: target={d[2]} | reference={d[3]} {('(' + d[5] + ')') if d[5] else ''}")
    s = t["AD"]["surface"]
    if s:
        pct = {k: float(np.nansum(s[k])) for k in ("PCT_NATVEG", "PCT_GLACIER", "PCT_LAKE", "PCT_WETLAND", "PCT_URBAN", "PCT_CROP") if k in s}
        F.append("SURFACE (target AD): " + ", ".join(f"{k} {v:.1f}" for k, v in pct.items()) +
                 (f"; PCT_NAT_PFT {short(s['PCT_NAT_PFT'])}" if "PCT_NAT_PFT" in s else ""))
        if pct.get("PCT_GLACIER", 0) > 0 or pct.get("PCT_NATVEG", 100) < 50:
            F.append("!! surface file: natural vegetation < 50% or glacier present")
    F.append(f"INIT: AD finidat = {t['AD']['finidat'] or '(cold start)'}; reference AD finidat = {r['AD']['finidat'] or '(cold start)'}")
    # forcing
    bad = [c for c in t["forcing_checks"] if c[2] in ("FAIL", "WARN")]
    F.append(f"FORCING ({t.get('forcing_files', 0)} files): " + ("all checks ok" if not bad else f"{len(bad)} problems"))
    for c in bad:
        F.append(f"   {'!!' if c[2] == 'FAIL' else '! '} {c[0]}: {c[1]} {c[3]}")
    for who, b in (("target", t), ("reference", r)):
        e = ec_vs_forcing(b)
        if e:
            msg = ", ".join(f"{k} {v:.2f}" if isinstance(v, float) else f"{k} {v}" for k, v in e.items())
            flag = ""
            if abs(e.get("T_forcing_minus_EC_C", 0)) > 2 or not 0.7 <= e.get("P_forcing_over_EC", 1) <= 1.3 or \
                    not 0.85 <= e.get("SW_forcing_over_EC", 1) <= 1.15:
                flag = "  <-- forcing does not match the tower"
            F.append(f"FORCING vs EC met ({who} {b['label']}): {msg}{flag}")
    fc = forcing_clim(t.get("forcing", pd.DataFrame()), t.get("forcing_units"))
    rc = forcing_clim(r.get("forcing", pd.DataFrame()), r.get("forcing_units"))
    if "T_C" in fc and "T_C" in rc:
        F.append(f"FORCING climate: target T {np.nanmean(fc['T_C']):.1f} C, P {np.nansum(fc.get('P_mm_month', np.nan)):.0f} mm/yr, "
                 f"SW {np.nanmean(fc.get('FSDS', np.nan)):.0f} W/m2 | reference T {np.nanmean(rc['T_C']):.1f} C, "
                 f"P {np.nansum(rc.get('P_mm_month', np.nan)):.0f} mm/yr, SW {np.nanmean(rc.get('FSDS', np.nan)):.0f} W/m2")
    # AD trajectory
    for who, b in (("target", t), ("reference", r)):
        a = b.get("ad_ann")
        if a is None or a.empty:
            F.append(f"AD ({who}): history not readable")
            continue
        cy, peak = collapse_year(a, "TLAI" if "TLAI" in a else "FATES_GPP")
        g5 = a["FATES_GPP"].head(5).mean() if "FATES_GPP" in a else np.nan
        msg = f"AD first {len(a)} years ({who} {b['label']}): peak LAI {peak if peak is None else round(peak, 2)}, " \
              f"GPP years 1-5 {g5:.2f} g C m-2 d-1, " + (f"vegetation gone from AD year {cy}" if cy else "vegetation persists")
        if "H2OSNO_min" in a and len(a) >= 10:
            smin = a["H2OSNO_min"].tail(10)
            if smin.min() > 10 and smin.iloc[-1] > smin.iloc[0]:
                msg += f"; !! snow never melts and grows (summer minimum {smin.iloc[-1]:.0f} mm)"
        if "TWS" in a and len(a) >= 10:
            msg += f"; TWS change {a['TWS'].iloc[-1] - a['TWS'].iloc[0]:+.0f} mm"
        F.append(msg)
    # seasonal / water balance
    for who, b in (("target", t), ("reference", r)):
        c = seasonal_clim(b)
        if c.empty:
            continue
        ann = lambda k: float(np.nansum(c[k].to_numpy(float) * DAYS)) if k in c and c[k].notna().sum() == 12 else np.nan
        Pm, ETm, ETe, Pe = ann("P_model_mm_day"), ann("ET_mm_day"), ann("EC_ET_mm_day"), ann("EC_P_mm_day")
        line = (f"WATER ({who} {b['label']}, last cycle, mm/yr): model P {Pm:.0f}, model ET {ETm:.0f}, "
                f"EC ET {ETe:.0f}, EC P {Pe:.0f}")
        if np.isfinite(ETe) and np.isfinite(Pm) and ETe > 1.1 * Pm:
            line += f"  !! EC ET exceeds precipitation by {100 * (ETe / Pm - 1):.0f}%: the ecosystem uses water beyond rainfall " \
                    f"(groundwater / riparian inflow); a free-draining CLM column cannot supply it"
        F.append(line)
        if "ZWT" in c:
            F.append(f"   model water table depth {np.nanmean(c['ZWT']):.1f} m; "
                     + ", ".join(f"{k.replace('H2OSOI_', 'soil water ')} {np.nanmean(c[k]):.3f}" for k in c if k.startswith("H2OSOI_")))
        for mo, ec, md, lai, bt, why in classify_months(c):
            F.append(f"   month {mo:2d}: EC GPP {ec:.2f}, model {md:.2f}, LAI {lai:.2f}, BTRAN {bt:.2f} -> {why}")
        pf = [k for k in c if k.startswith("FATES_GPP_PF_pft") and np.nansum(c[k]) > 0]
        if pf:
            tot = sum(np.nansum(c[k]) for k in pf)
            F.append("   GPP share by PFT: " + ", ".join(f"{k.split('_')[-1]} {100 * np.nansum(c[k]) / tot:.0f}%" for k in pf))
        ph = [k for k in c if PHEN_RE.search(k) and not k.startswith("FATES_GPP")]
        if ph:
            F.append("   phenology variables (monthly mean Jan..Dec): " +
                     "; ".join(f"{k} " + " ".join(f"{v:.0f}" for v in c[k].to_numpy(float)) for k in ph[:6]))
    for who, b in (("target", t), ("reference", r)):
        for e in b.get("errors", []):
            F.append(f"ERROR ({who}): {e}")
    return F


# ------------------------------------------------------------------ plots
def plots(label, t, r, dest):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mon = np.arange(1, 13)
    # 1 forcing vs EC
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.5), constrained_layout=True)
    panels = [("T_C", "EC_TA", "Air temperature (°C)"), ("P_mm_month", "EC_P_mm_day", "Precipitation (mm month$^{-1}$)"),
              ("FSDS", "EC_SW_IN", "Shortwave in (W m$^{-2}$)"), ("QBOT", None, "Specific humidity (kg kg$^{-1}$)"),
              ("WIND", "EC_WS", "Wind (m s$^{-1}$)"), ("PSRF", "EC_PA", "Pressure (Pa)")]
    for a, (fk, ek, title) in zip(ax.ravel(), panels):
        for b, col, ls in ((t, "C3", "-"), (r, "0.5", "-")):
            fc = forcing_clim(b.get("forcing", pd.DataFrame()), b.get("forcing_units"))
            if fk == "QBOT" and fk not in fc and "RH" in fc:
                fk2, title2 = "RH", "Relative humidity (%)"
            else:
                fk2, title2 = fk, title
            if fk2 in fc:
                a.plot(mon, fc[fk2], color=col, ls=ls, lw=2, label=f"{b['label']} forcing")
            a.set_title(title2)
            ec = b.get("ec")
            if ek and ec is not None and not ec.empty and ek in ec:
                e = ec.groupby("Month")[ek].mean().reindex(mon)
                if ek == "EC_P_mm_day":
                    e = e * DAYS
                elif ek == "EC_PA":
                    e = e * 1000.0
                a.plot(mon, e, color=col, ls="--", lw=1.5, label=f"{b['label']} EC tower")
        a.set_xticks(mon); a.grid(alpha=0.3)
    ax[0, 0].legend(fontsize=8)
    fig.suptitle(f"{label}: site forcing (solid) vs EC tower meteorology (dashed); reference {r['label']} in grey")
    fig.savefig(dest / f"{label}_01_forcing_vs_EC.png", dpi=130); plt.close(fig)
    # 2 AD first years
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.5), constrained_layout=True)
    for a, (k, title) in zip(ax.ravel(), [("TLAI", "LAI (m$^2$ m$^{-2}$)"), ("FATES_GPP", "GPP (g C m$^{-2}$ d$^{-1}$)"),
                                          ("FATES_NPP", "NPP (g C m$^{-2}$ d$^{-1}$)"), ("TOTSOMC", "Soil organic C (g C m$^{-2}$)"),
                                          ("H2OSNO_min", "Annual minimum snow water (mm)"), ("TWS", "Total water storage (mm)")]):
        for b, col in ((t, "C3"), (r, "0.4")):
            an = b.get("ad_ann")
            if an is not None and not an.empty and k in an:
                a.plot(an["SpinupYear"], an[k], color=col, lw=2, label=b["label"])
        a.set_title(title); a.set_xlabel("AD year"); a.grid(alpha=0.3)
    ax[0, 0].legend()
    fig.suptitle(f"{label}: first AD years, target (red) vs reference {r['label']} (grey)")
    fig.savefig(dest / f"{label}_02_AD_first_years.png", dpi=130); plt.close(fig)
    # 3 seasonal water and carbon, last Normal cycle
    ct, cr = seasonal_clim(t), seasonal_clim(r)
    if ct.empty and cr.empty:
        return
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.5), constrained_layout=True)
    def line(a, c, k, **kw):
        if not c.empty and k in c and c[k].notna().any():
            a.plot(mon, c[k], **kw)
    for c, col, nm in ((ct, "C3", t["label"]), (cr, "0.5", r["label"])):
        line(ax[0, 0], c, "GPP_gC_m2_d", color=col, lw=2, label=f"{nm} FATES")
        line(ax[0, 0], c, "EC_GPP", color=col, lw=1.5, ls="--", label=f"{nm} EC")
        line(ax[0, 1], c, "ET_mm_day", color=col, lw=2, label=f"{nm} model ET")
        line(ax[0, 1], c, "EC_ET_mm_day", color=col, ls="--", label=f"{nm} EC ET")
        line(ax[0, 1], c, "P_model_mm_day", color=col, ls=":", label=f"{nm} P")
        line(ax[0, 2], c, "TLAI", color=col, lw=2, label=f"{nm} TLAI")
        line(ax[1, 0], c, "BTRAN", color=col, lw=2, label=nm)
        for i, (lo, hi) in enumerate(BANDS):
            line(ax[1, 1], c, f"H2OSOI_{lo:g}-{hi:g}m", color=col, lw=2.5 - 0.5 * i, alpha=1 - 0.2 * i, label=f"{nm} {lo:g}-{hi:g} m")
        if not c.empty and "EC_SWC1" in c and c["EC_SWC1"].notna().any():
            ax[1, 1].plot(mon, c["EC_SWC1"] / 100.0, color=col, ls="--", label=f"{nm} EC SWC_1")
    if not ct.empty:
        for k in [k for k in ct if k.startswith("FATES_GPP_PF_pft") and np.nansum(ct[k]) > 0]:
            ax[1, 2].plot(mon, ct[k], lw=2, label=f"{t['label']} {k.split('_')[-1]}")
        if "EC_GPP" in ct:
            ax[1, 2].plot(mon, ct["EC_GPP"], color="k", ls="--", label="EC")
    for a, tt in zip(ax.ravel(), ["GPP (g C m$^{-2}$ d$^{-1}$)", "Water (mm d$^{-1}$)", "LAI", "BTRAN",
                                  "Soil water (m$^3$ m$^{-3}$)", f"{t['label']} GPP by PFT"]):
        a.set_title(tt); a.set_xticks(mon); a.grid(alpha=0.3); a.legend(fontsize=7)
    fig.suptitle(f"{label}: last complete Normal forcing cycle, monthly climatology (reference {r['label']} in grey)")
    fig.savefig(dest / f"{label}_03_seasonal_water_carbon.png", dpi=130); plt.close(fig)


# ------------------------------------------------------------------ run / publish
def process(spec, args, cache):
    label, case, rlabel, rcase = spec.split(":")
    dest = args.output_root / label
    dest.mkdir(parents=True, exist_ok=True)
    rec = {"Label": label, "Case": case, "Reference": f"{rlabel} ({rcase})", "Status": "FAILED"}
    try:
        t = site_bundle(label, case, args, cache)
        r = site_bundle(rlabel, rcase, args, cache)
        t["ref_label"] = rlabel
        diff = setup_diff(t, r, label)
        with (dest / f"{label}_setup_diff.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["section", "key", "target", "reference", "differs", "note"]); w.writerows(diff)
        if not t["forcing"].empty:
            t["forcing"].to_csv(dest / f"{label}_forcing_monthly.csv", index=False)
        with (dest / f"{label}_forcing_checks.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["check", "value", "status", "note"]); w.writerows(t["forcing_checks"])
        for key, name in (("ec", "EC_monthly"), ("ad_ann", "AD_annual"), ("seas", "normal_monthly")):
            if t.get(key) is not None and not t[key].empty:
                t[key].to_csv(dest / f"{label}_{name}.csv", index=False)
        c = seasonal_clim(t)
        if not c.empty:
            c.to_csv(dest / f"{label}_normal_seasonal.csv", index=False)
        F = findings(label, t, r, diff)
        head = [f"{label} ({case}; AD {t['ad_case']}) vs reference {rlabel} ({rcase}; AD {r['ad_case']})",
                f"EC: {t.get('ec_note', {})}", ""]
        (dest / f"{label}_findings.txt").write_text("\n".join(head + F) + "\n", encoding="utf-8")
        plots(label, t, r, dest)
        cy, peak = collapse_year(t["ad_ann"]) if not t["ad_ann"].empty else (None, None)
        e = ec_vs_forcing(t)
        rec.update(Status="OK" if not t["errors"] else "PARTIAL", AD_case=t["ad_case"],
                   Setup_differences=sum(1 for d in diff if d[4] and d[5] not in ("site-specific", "path (site-specific name)")),
                   Forcing_problems=sum(1 for x in t["forcing_checks"] if x[2] in ("FAIL", "WARN")),
                   AD_collapse_year=cy or "", AD_peak_LAI=peak if peak is not None else "", **e,
                   Errors="; ".join(t["errors"] + r["errors"]))
        print("\n".join(F), flush=True)
    except Exception as exc:
        rec["Errors"] = f"{type(exc).__name__}: {exc}"
        (dest / "ERROR.txt").write_text(traceback.format_exc())
        print(f"[{label}] FAILED: {rec['Errors']}", flush=True)
    return rec


def run(a):
    a.output_root.mkdir(parents=True, exist_ok=True)
    cache, recs = {}, []
    for spec in a.specs:
        recs.append(process(spec, a, cache))
    fields = list(dict.fromkeys(k for r in recs for k in r))
    with (a.output_root / "site_anomaly_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(recs)
    ok = sum(r["Status"] in ("OK", "PARTIAL") for r in recs)
    (a.output_root / "RUN_COMPLETE.json").write_text(json.dumps(
        {"ok": ok, "total": len(recs), "specs": a.specs, "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"\nCOMPLETE: {ok}/{len(recs)}. Findings: {a.output_root}/<site>/<site>_findings.txt", flush=True)
    return 0 if ok == len(recs) else 1


def publish(run_dir, repo):
    run_dir = run_dir.expanduser().resolve()
    if not (run_dir / "RUN_COMPLETE.json").is_file():
        raise SystemExit("RUN_COMPLETE.json missing: run did not finish; nothing published")
    with (run_dir / "site_anomaly_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path(FIG_DIR) / stamp
    with tempfile.TemporaryDirectory(prefix="anomaly_publish_") as tmp:
        co = Path(tmp) / "repo"
        F7.git("clone", "--depth", "1", "--branch", "main", repo, co)
        out = co / rel; out.mkdir(parents=True)
        shutil.copyfile(run_dir / "site_anomaly_summary.csv", out / "site_anomaly_summary.csv")
        lines = ["# Site anomaly diagnostics: CZ-Stn / DE-Lnf collapse, US-CMW low GPP", "",
                 "Each target is compared with a working reference site: case set-up, forcing vs EC meteorology,",
                 "first AD years, and the last Normal forcing cycle (water balance, LAI, BTRAN, GPP by PFT). Read-only.", "",
                 "| Site | Reference | Status | set-up differences | forcing problems | AD collapse year | Files |",
                 "| --- | --- | --- | ---: | ---: | ---: | --- |"]
        for r in rows:
            lab = r["Label"]
            if not F7.SAFE.fullmatch(lab):
                raise ValueError(f"unsafe label {lab!r}")
            links = []
            (out / lab).mkdir(exist_ok=True)
            for p in sorted((run_dir / lab).glob(f"{lab}_0[123]_*.png")):
                if F7.is_png(p):
                    shutil.copyfile(p, out / lab / p.name); links.append(f"[{p.stem.split('_', 2)[-1]}]({lab}/{p.name})")
            for p in sorted((run_dir / lab).glob(f"{lab}_*.csv")) + sorted((run_dir / lab).glob(f"{lab}_findings.txt")):
                if p.stat().st_size < 5_000_000:
                    shutil.copyfile(p, out / lab / p.name)
            if (out / lab / f"{lab}_findings.txt").is_file():
                links.insert(0, f"[findings]({lab}/{lab}_findings.txt)")
            cell = lambda k: (r.get(k) or "").replace("|", "/")
            lines.append(f"| {lab} | {cell('Reference')} | {cell('Status')} | {cell('Setup_differences')} | "
                         f"{cell('Forcing_problems')} | {cell('AD_collapse_year')} | {' '.join(links)} |")
        (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*.png"))]
        (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        F7.git("add", "--", rel.as_posix(), cwd=co)
        F7.git("commit", "-m", f"Add site anomaly diagnostics ({len(rows)} sites)", cwd=co)
        sha = F7.git("rev-parse", "HEAD", cwd=co)
        F7.git("push", "origin", "HEAD:main", cwd=co)
    print("PUSH SUCCESS", sha)
    print("https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-root", type=Path)
    ap.add_argument("--publish-run", type=Path)
    ap.add_argument("--specs", nargs="+", default=DEFAULT_SPECS, metavar="LABEL:NORMAL_CASE:REF_LABEL:REF_NORMAL_CASE")
    ap.add_argument("--ad-years", type=int, default=60)
    ap.add_argument("--min-halfhour", type=int, default=40)
    ap.add_argument("--min-days", type=int, default=20)
    ap.add_argument("--archive-root", type=Path, default=None)
    ap.add_argument("--cases-root", type=Path, default=None)
    ap.add_argument("--sites-root", type=Path, default=None)
    ap.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--allow-scratch-output", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    load_modules()
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
    for s in a.specs:
        p = s.split(":")
        if len(p) != 4 or not F7.SAFE.fullmatch(p[0]) or not F7.SAFE.fullmatch(p[2]):
            ap.error(f"bad --specs entry {s!r}")
    a.output_root = root
    return run(a)


if __name__ == "__main__":
    raise SystemExit(main())
