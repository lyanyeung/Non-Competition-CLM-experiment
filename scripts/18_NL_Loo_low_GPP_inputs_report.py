#!/usr/bin/env python3
"""READ-ONLY text report for diagnosing the low NL-Loo V3 GPP (about 1/7 of EC, LAI about 0.2).

Collects in ONE text file what is needed to test the main hypotheses:
  1 surface   fsurdat: vegetated-land fraction, PCT_NAT_PFT (bare ground?), soil texture,
              organic matter, bedrock depth          -> sparse cover / sandy-soil water stress
  2 FATES     fates_paramfile: HLM->FATES PFT map for the surface PFTs, and key traits of the
              mapped FATES PFTs (Vcmax, SLA, wilting/opening potentials, init density, ...)
  3 forcing   DATM files of a few years: units, means, annual precipitation, shortwave
                                                     -> unit or scaling errors
  4 history   last year of PRE50 and AD200: annual means of GPP, LAI, BTRAN, soil water,
              transpiration, radiation, temperature, FATES size/PFT fields where written
                                                     -> which limitation is active
Nothing is modified. Output: ~/NL_Loo_low_GPP_report_<UTC>.txt (path printed at the end).

IRIDIS6:
  conda activate clm_fates_env
  python ~/18_NL_Loo_low_GPP_inputs_report.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

U = "ly3n24"
CASES = Path(f"/iridisfs/scratch/{U}/CLM_FATES/cases")
ARCH = Path(f"/scratch/{U}/CTSM_FATES_OUTPUTS/archive")
CASE = {p: f"NL-Loo_OBSPFT_NC_V3_{p}" for p in ("PRE50", "AD200", "POST300")}
DATM_YEARS = (1997, 2003, 2010, 2018, 2025)

HIST_FIELDS = [
    "FATES_GPP", "FATES_NPP", "FATES_AUTORESP", "FATES_NEP", "GPP", "FPSN", "TLAI", "FATES_LAI", "ELAI",
    "FATES_VEGC", "FATES_STOREC", "FATES_LEAFC", "FATES_NPLANT", "FATES_BASALAREA", "FATES_CA_WEIGHTED_HEIGHT",
    "FATES_CANOPY_AREA", "FATES_CROWNAREA_CL", "FATES_PATCHAREA",
    "BTRAN", "BTRANMN", "FATES_BTRAN", "SOILWATER_10CM", "H2OSOI", "SMP", "ZWT", "TWS",
    "QVEGT", "QVEGE", "QSOIL", "QOVER", "QDRAI", "QRUNOFF", "RAIN", "SNOW", "H2OSNO",
    "FSDS", "FSA", "PARVEGLN", "TSA", "TBOT", "TV", "TSOI_10CM", "RH2M", "VPD_CAN", "Q2M",
]
PFT_PARAMS = [
    "fates_pftname", "fates_woody", "fates_phen_evergreen", "fates_phen_season_decid", "fates_phen_stress_decid",
    "fates_leaf_vcmax25top", "fates_leaf_slatop", "fates_leaf_slamax", "fates_leaf_long",
    "fates_leaf_stomatal_slope_ballberry", "fates_leaf_stomatal_intercept",
    "fates_nonhydro_smpsc", "fates_nonhydro_smpso", "fates_allom_smode",
    "fates_recruit_init_density", "fates_recruit_height_min", "fates_mort_bmort", "fates_mort_scalar_cstarvation",
    "fates_alloc_storage_cushion", "fates_turnover_leaf",
    "fates_root_long", "fates_allom_fnrt_prof_a", "fates_allom_fnrt_prof_b",
]
OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    OUT.append(s)
    print(s, flush=True)


def head(t):
    say("")
    say("=" * 78)
    say(t)
    say("=" * 78)


def opennc(p):
    from netCDF4 import Dataset
    ds = Dataset(str(p))
    try:
        ds.set_auto_mask(True)
    except Exception:
        pass
    return ds


def arr(v):
    a = v[:]
    a = a.filled(np.nan) if np.ma.isMaskedArray(a) else np.asarray(a)
    a = np.asarray(a, dtype=float)
    a[np.abs(a) > 1e30] = np.nan
    return a


def att(v, k):
    x = getattr(v, k, "")
    return x.decode() if isinstance(x, bytes) else str(x)


def fmt(x):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "nan"
    ax = abs(x)
    return f"{x:.4g}" if (ax == 0 or 1e-3 <= ax < 1e5) else f"{x:.4e}"


def nml(text, key):
    m = re.search(rf"(?im)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", text)
    return m.group(1).strip().strip("'\"") if m else None


# ---------------------------------------------------------------- 1 surface
def surface(path):
    head(f"1 SURFACE  {path}")
    ds = opennc(path)
    try:
        v = ds.variables
        for n in ("LATIXY", "LONGXY", "PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER",
                  "PCT_OCEAN", "FMAX", "zbedrock", "SOIL_COLOR", "SLOPE", "STD_ELEV", "peatf", "LAKEDEPTH"):
            if n in v:
                say(f"  {n:12} = {fmt(float(np.nansum(arr(v[n]))))} {att(v[n], 'units')}")
        if "PCT_URBAN" in v:
            say(f"  PCT_URBAN    = {fmt(float(np.nansum(arr(v['PCT_URBAN']))))} (sum of density classes)")
        nonzero, n_natpft = [], None
        if "PCT_NAT_PFT" in v:
            a = arr(v["PCT_NAT_PFT"]).reshape(arr(v["PCT_NAT_PFT"]).shape[0], -1)[:, 0]
            n_natpft = len(a)
            say(f"  PCT_NAT_PFT (% of natural vegetated landunit; index 0 = bare ground), sum {fmt(float(np.nansum(a)))}:")
            for i, x in enumerate(a):
                if x > 0:
                    nonzero.append(i)
                    say(f"     HLM pft {i:2d}: {fmt(float(x))} %")
        for n in ("PCT_SAND", "PCT_CLAY", "ORGANIC"):
            if n in v:
                a = arr(v[n]).reshape(arr(v[n]).shape[0], -1)[:, 0]
                say(f"  {n:9} by layer: " + ", ".join(fmt(float(x)) for x in a))
        return nonzero, n_natpft
    finally:
        ds.close()


# ---------------------------------------------------------------- 2 FATES params
def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for x in obj.values():
            r = find_key(x, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for x in obj:
            r = find_key(x, key)
            if r is not None:
                return r
    return None


def pdata(entry):
    """Values of a parameter entry whatever the JSON layout ({'data': ...}, {'value': ...} or a list)."""
    if isinstance(entry, dict):
        for k in ("data", "value", "values"):
            if k in entry:
                return entry[k], entry
        return None, entry
    return entry, None


def fates_params(path, hlm_pfts, n_natpft=None):
    head(f"2 FATES PARAMETERS  {path}")
    p = Path(path)
    if p.suffix.lower() != ".json":
        say("  not a JSON file; skipped (send the file path)")
        return
    obj = json.loads(p.read_text())
    names, _ = pdata(find_key(obj, "fates_pftname"))
    if isinstance(names, list):
        names = ["".join(x) if isinstance(x, list) else str(x) for x in names]
        names = [n.strip() for n in names]
        say("  FATES PFTs: " + "; ".join(f"{i + 1}={n}" for i, n in enumerate(names)))
    mp, meta = pdata(find_key(obj, "fates_hlm_pft_map"))
    mapped = set()
    if mp is None:
        say("  fates_hlm_pft_map not found")
    else:
        if meta:
            say(f"  fates_hlm_pft_map dims: {meta.get('dims', meta.get('dimensions', '?'))}")
        m = np.asarray(mp, dtype=float)
        say(f"  map shape {m.shape}")
        nf = len(names) if isinstance(names, list) else None
        if m.ndim == 2:
            # orient as [hlm_pft, fates_pft]
            if nf and m.shape[0] == nf and m.shape[1] != nf:
                m = m.T
            # the map has no bare-ground row when it has one row fewer than natpft
            off = 1 if (n_natpft and m.shape[0] == n_natpft - 1) else 0
            say(f"  map rows = HLM pfts {'1..' + str(m.shape[0]) if off else '0..' + str(m.shape[0] - 1)}")
            for h in hlm_pfts:
                if off and h == 0:
                    say("  HLM pft  0 -> bare ground (FATES bare-ground patch, no vegetation)")
                    continue
                if 0 <= h - off < m.shape[0]:
                    row = m[h - off]
                    tgt = [(j + 1, row[j]) for j in range(len(row)) if row[j] > 0]
                    mapped |= {j for j, _ in tgt}
                    lab = ", ".join(f"FATES {j} ({names[j - 1] if nf else '?'}) x{fmt(float(w))}" for j, w in tgt)
                    say(f"  HLM pft {h:2d} -> {lab or 'NOTHING (area lost?)'}")
    mapped.discard(0)
    if not mapped and isinstance(names, list):
        mapped = set(range(1, len(names) + 1))
    say(f"  traits for FATES PFT(s) {sorted(mapped)}:")
    for k in PFT_PARAMS[1:]:
        d, meta = pdata(find_key(obj, k))
        if d is None:
            continue
        a = np.asarray(d, dtype=object)
        try:
            a = np.asarray(d, dtype=float)
        except (TypeError, ValueError):
            say(f"    {k}: {str(d)[:120]}")
            continue
        unit = meta.get("units", "") if isinstance(meta, dict) else ""
        npft = len(names) if isinstance(names, list) else None
        if a.ndim == 2 and npft and a.shape[-1] == npft:
            say(f"    {k:38} " + ", ".join(f"pft{j}={fmt(float(a[0, j - 1]))}" for j in sorted(mapped)) +
                f" {unit} (first of {a.shape[0]} rows)")
            continue
        if a.ndim == 0:
            say(f"    {k:38} {fmt(float(a))} {unit}")
        elif a.ndim == 1:
            say(f"    {k:38} " + ", ".join(f"pft{j}={fmt(float(a[j - 1]))}" for j in sorted(mapped) if j - 1 < len(a)) + f" {unit}")
        else:
            say(f"    {k:38} shape {a.shape}: " + str(np.round(a, 4).tolist())[:160])


# ---------------------------------------------------------------- 3 forcing
def forcing(stream_xml):
    head(f"3 FORCING  {stream_xml}")
    txt = Path(stream_xml).read_text()
    files = re.findall(r"<file>\s*([^<]+?)\s*</file>", txt)
    say(f"  {len(files)} files; year_first/last/align: " +
        "/".join(re.findall(r"<year_(?:first|last|align)>\s*(\d+)", txt)))
    mvars = re.findall(r"<var>\s*([^<]+?)\s*</var>", txt)
    if mvars:
        say("  stream variable map (file name -> model name): " + "; ".join(" ".join(x.split()) for x in mvars))
    picked = []
    for y in DATM_YEARS:
        f = next((f for f in files if re.search(rf"(?<!\d){y}(?!\d)", Path(f).name)), None)
        if f:
            picked.append(f)
    for f in picked:
        say(f"  --- {f}")
        try:
            ds = opennc(f)
        except Exception as exc:
            say(f"      cannot open: {exc}")
            continue
        try:
            t = ds.variables.get("time")
            nt = t.shape[0] if t is not None else 0
            dt_s = None
            if t is not None and nt > 1:
                tv = arr(t)
                unit = att(t, "units").lower()
                fac = 86400 if unit.startswith("day") else 3600 if unit.startswith("hour") else 60 if unit.startswith("min") else 1
                dt_s = float(np.median(np.diff(tv))) * fac
                say(f"      time: {nt} steps, step {fmt(dt_s)} s, units '{att(t, 'units')}', calendar '{att(t, 'calendar')}'")
            for n, v in ds.variables.items():
                if n in ("time", "time_bnds", "time_bounds", "LONGXY", "LATIXY", "lon", "lat", "xc", "yc"):
                    continue
                if not v.dimensions or "time" not in v.dimensions:
                    continue
                a = arr(v).ravel()
                line = (f"      {n:10} [{att(v, 'units')}] mean {fmt(float(np.nanmean(a)))} min {fmt(float(np.nanmin(a)))} "
                        f"max {fmt(float(np.nanmax(a)))} nan {int(np.isnan(a).sum())}")
                if n.upper().startswith("PRECT") or n.upper() in ("PRECIP", "RAIN", "PRECTMMS"):
                    line += f"  -> annual total if mm/s: {fmt(float(np.nanmean(a)) * 365 * 86400)} mm"
                say(line)
        finally:
            ds.close()


# ---------------------------------------------------------------- 4 history
def last_hist(case):
    d = ARCH / case / "lnd" / "hist"
    fs = sorted(d.glob(f"{case}.clm2.h0a.*.nc")) or sorted(d.glob(f"{case}.clm2.h0.*.nc"))
    return fs[-1] if fs else None


def history(stage):
    case = CASE[stage]
    f = last_hist(case)
    head(f"4 HISTORY  {stage}: {f}")
    if f is None:
        say("  no h0a/h0 history archived")
        return
    ds = opennc(f)
    try:
        v = ds.variables
        nt = v["time"].shape[0] if "time" in v else 0
        say(f"  {nt} time samples in file")
        fates = sorted(n for n in v if n.startswith("FATES_"))
        say(f"  FATES fields written ({len(fates)}): " + ", ".join(fates)[:3000])
        for n in HIST_FIELDS:
            if n not in v:
                continue
            x = v[n]
            a = arr(x)
            dims = list(x.dimensions)
            if "time" not in dims:
                continue
            a = np.moveaxis(a, dims.index("time"), 0)
            other = [d for d in dims if d != "time"]
            if a.reshape(a.shape[0], -1).shape[1] == 1:
                s = a.reshape(a.shape[0])
                say(f"  {n:24} [{att(x, 'units')}] annual mean {fmt(float(np.nanmean(s)))}  "
                    f"min {fmt(float(np.nanmin(s)))}  max {fmt(float(np.nanmax(s)))}")
            else:
                prof = np.nanmean(a.reshape(a.shape[0], a.shape[1] if a.ndim > 1 else 1, -1), axis=(0, 2))
                say(f"  {n:24} [{att(x, 'units')}] dims {other} annual mean by level: " +
                    ", ".join(fmt(float(p)) for p in prof[:15]))
        # PFT- or size-resolved FATES fields that happen to be written
        for n in fates:
            x = v[n]
            dims = list(x.dimensions)
            extra = [d for d in dims if d not in ("time", "lndgrid", "column", "gridcell")]
            if not extra or not re.search(r"GPP|LAI|VEGC|NPLANT|CROWNAREA|CANOPYAREA|BASALAREA|MORTALITY|DDBH|STOREC", n):
                continue
            a = np.moveaxis(arr(x), dims.index("time"), 0)
            a = a.reshape(a.shape[0], -1)
            m = np.nanmean(a, axis=0)
            nzi = [i for i, val in enumerate(m) if np.isfinite(val) and val != 0]
            lab = (lambda i: f"pft{i + 1}") if extra == ["fates_levpft"] else (lambda i: f"bin{i}")
            say(f"  {n:24} [{att(x, 'units')}] dims {extra}: nonzero " +
                (", ".join(f"{lab(i)}={fmt(float(m[i]))}" for i in nzi[:24]) or "none"))
    finally:
        ds.close()


def main(argv=None):
    global CASES, ARCH
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, help="report path (default ~/NL_Loo_low_GPP_report_<UTC>.txt)")
    ap.add_argument("--cases-root", type=Path, default=CASES)
    ap.add_argument("--archive-root", type=Path, default=ARCH)
    a = ap.parse_args(argv)
    CASES, ARCH = a.cases_root, a.archive_root
    out = a.output or Path.home() / f"NL_Loo_low_GPP_report_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"
    say(f"NL-Loo V3 low-GPP input report  {datetime.now(timezone.utc).isoformat()}  (read only)")
    pre = CASES / CASE["PRE50"]
    lnd = (pre / "CaseDocs" / "lnd_in").read_text()
    for k in ("fsurdat", "fates_paramfile", "paramfile", "co2_ppmv", "finidat", "hist_fincl1", "hist_nhtfrq"):
        say(f"  lnd_in {k} = {nml(lnd, k)}")
    steps = [("forcing", lambda: forcing(pre / "CaseDocs" / "datm.streams.xml")),
             ("history PRE50", lambda: history("PRE50")),
             ("history AD200", lambda: history("AD200"))]
    hlm, n_natpft = [], None
    try:
        hlm, n_natpft = surface(nml(lnd, "fsurdat"))
    except Exception as exc:
        say(f"  SURFACE FAILED: {type(exc).__name__}: {exc}")
    try:
        fates_params(nml(lnd, "fates_paramfile"), hlm, n_natpft)
    except Exception as exc:
        say(f"  FATES PARAMS FAILED: {type(exc).__name__}: {exc}")
    for name, fn in steps:
        try:
            fn()
        except Exception as exc:
            say(f"  {name.upper()} FAILED: {type(exc).__name__}: {exc}")
    out.write_text("\n".join(OUT) + "\n", encoding="utf-8")
    print(f"\nREPORT WRITTEN: {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
