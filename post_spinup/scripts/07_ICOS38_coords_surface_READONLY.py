#!/usr/bin/env python3
"""Stage07 (IRIDIS6, read only): coordinates, current surface soil / surface fields and spin-up CO2 settings for
the 38 ICOS sites. Modelled on the OzFlux/JapanFlux Soil Stage02 and SurfaceFields Stage01 scripts
(CLM-FATES-single-site-workflows, branch oz-jp-surface-carbon-20261103).

1. Coordinates from our own BIF files (GRP_LOCATION: LOCATION_LAT / LOCATION_LONG / LOCATION_ELEV), found as in
   script 00 (forcing/raw/*/ first, else members of forcing/packages/*.zip; nothing is extracted). If a site has
   no BIF, the point-surface LATIXY / LONGXY of its case is used and marked as such.
   -> ICOS38_COORDINATES.csv in the column layout of the OZ/JP SoilGrids script (site, network, site_name, lat,
      lon, elevation_m, coord_source, coord_verification), so it can be passed to it with --sites.
2. Every case under cases/ whose name starts with "<site>_" and has CaseDocs/lnd_in:
   - lnd_in: fsurdat, use_bedrock, soil_layerstruct_predefined, paramfile, fates_paramfile;
   - env_*.xml: CCSM_CO2_PPMV, CLM_CO2_TYPE, CCSM_BGC, DATM_CO2_TSERIES, RUN_TYPE, RUN_REFCASE, RUN_REFDATE,
     RUN_STARTDATE, STOP_OPTION, STOP_N, and every DATM_*YR* entry.
   -> stage07_cases.tsv
3. Each distinct surface file of those cases (point file: its single cell; grid: the cell nearest the tower):
   PCT_SAND / PCT_CLAY / ORGANIC on the 10 levels, zbedrock, FMAX, SOIL_COLOR, landunit shares, PCT_NAT_PFT.
   -> stage07_surface_soil_long.csv (one row per surface and level) and stage07_surface_fields.tsv

Nothing is modified. Output: a new folder (default $HOME/icos38_stage07_<UTC>) with the files above and
stage07.json.

Usage (login node, conda env clm_fates_env; netCDF4 for step 3, scipy fallback reads NetCDF3 only):
  python3 -B 07_ICOS38_coords_surface_READONLY.py --self-test
  python3 -B 07_ICOS38_coords_surface_READONLY.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
HERE = Path(__file__).resolve().parents[1] / "ICOS38"
LND_KEYS = ("fsurdat", "use_bedrock", "soil_layerstruct_predefined", "paramfile", "fates_paramfile",
            "lower_boundary_condition")
ENV_KEYS = ("CCSM_CO2_PPMV", "CLM_CO2_TYPE", "CCSM_BGC", "DATM_CO2_TSERIES", "RUN_TYPE", "RUN_REFCASE",
            "RUN_REFDATE", "RUN_STARTDATE", "STOP_OPTION", "STOP_N", "CLM_NML_USE_CASE")
ENV_RE = re.compile(r"^DATM_.*(YR|YEAR)", re.I)
SCALARS = ("zbedrock", "FMAX", "SOIL_COLOR", "PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER")
LEVELS = ("PCT_SAND", "PCT_CLAY", "ORGANIC")
COORD_FIELDS = ("site", "network", "site_name", "lat", "lon", "elevation_m", "coord_source", "coord_verification")


def utc():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(p, cap=2 * 1024 ** 3):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        n = 0
        while chunk := f.read(1 << 20):
            h.update(chunk)
            n += len(chunk)
            if n > cap:
                return "TOO_LARGE"
    return h.hexdigest()


# ------------------------------------------------------------------ BIF coordinates (as script 00)
def is_bif(name):
    n = Path(name).name.upper()
    return "_BIF_" in n and "BIFVARINFO" not in n and n.endswith(".CSV")


def find_bif(site_dir):
    raw = sorted(p for p in (site_dir / "forcing" / "raw").glob("*/*") if is_bif(p.name))
    if raw:
        return [(str(p), p.read_bytes()) for p in raw]
    out = []
    for z in sorted((site_dir / "forcing" / "packages").glob("*.zip")):
        try:
            with zipfile.ZipFile(z) as zf:
                out += [(f"{z}::{m}", zf.read(m)) for m in zf.namelist() if is_bif(m)]
        except zipfile.BadZipFile:
            print(f"  WARN bad zip {z}", file=sys.stderr)
    return out


def bif_location(blobs):
    """LOCATION_LAT / _LONG / _ELEV from the BIF files; newest file name wins if they disagree."""
    found = []
    for src, blob in blobs:
        txt = blob.decode("utf-8", errors="replace")
        rows = list(csv.reader(io.StringIO(txt)))
        by_group = {}
        for r in rows[1:]:
            if len(r) >= 5 and r[2].strip() == "GRP_LOCATION":
                by_group.setdefault(r[1].strip(), {})[r[3].strip()] = r[4].strip()
        for g in by_group.values():
            if g.get("LOCATION_LAT") and g.get("LOCATION_LONG"):
                found.append((src, g))
    if not found:
        return None
    vals = {(g["LOCATION_LAT"], g["LOCATION_LONG"]) for _, g in found}
    src, g = sorted(found, key=lambda t: t[0])[-1]
    return {"lat": g["LOCATION_LAT"], "lon": g["LOCATION_LONG"], "elevation_m": g.get("LOCATION_ELEV", ""),
            "coord_source": f"BIF GRP_LOCATION ({Path(src.split('::')[-1]).name})",
            "n_distinct_in_bif": len(vals), "all_values": sorted(vals)}


# ------------------------------------------------------------------ cases
def nml_value(text, key):
    m = re.search(rf"^\s*{key}\s*=\s*(.+?)\s*$", text, re.M | re.I)
    return m.group(1).strip().strip("'\"") if m else ""


def env_values(case):
    vals = {}
    for f in sorted(Path(case).glob("env_*.xml")):
        for m in re.finditer(r"<entry\s+id=\"([^\"]+)\"\s+value=\"([^\"]*)\"", f.read_text(errors="replace")):
            vals.setdefault(m.group(1), m.group(2))
    return vals


def site_cases(site, cases_root):
    out = []
    if not Path(cases_root).is_dir():
        return out
    for case in sorted(Path(cases_root).iterdir()):
        lnd = case / "CaseDocs" / "lnd_in"
        if case.is_dir() and case.name.startswith(site + "_") and lnd.is_file():
            text = lnd.read_text(errors="replace")
            env = env_values(case)
            r = {"site": site, "case": case.name}
            r.update({k: nml_value(text, k) for k in LND_KEYS})
            r.update({k: env.get(k, "") for k in ENV_KEYS})
            r["datm_years"] = ";".join(f"{k}={v}" for k, v in sorted(env.items()) if ENV_RE.match(k))
            out.append(r)
    return out


# ------------------------------------------------------------------ surfaces
def r3(x):
    try:
        x = float(x)
        return None if x != x else round(x, 3)
    except (TypeError, ValueError):
        return None


def open_nc(path, mode="r"):
    """netCDF4 if installed (IRIDIS clm_fates_env); else scipy, which reads NetCDF3 files only."""
    try:
        from netCDF4 import Dataset
        return Dataset(str(path), mode)
    except ImportError:
        from scipy.io import netcdf_file
        return netcdf_file(str(path), mode, mmap=False)


def surface_values(path, lat=None, lon=None):
    import numpy as np
    with open_nc(path) as ds:
        v = ds.variables

        def arr(n):
            return None if n not in v else np.ma.filled(np.ma.asarray(v[n][:], dtype=float), np.nan)

        la, lo = arr("LATIXY"), arr("LONGXY")
        grid = la is not None and la.ndim == 2 and la.size > 1
        i = k = 0
        if grid and lat is not None:
            d = (la - lat) ** 2 + ((((lo - (lon % 360)) + 180) % 360) - 180) ** 2
            i, k = np.unravel_index(np.nanargmin(d), d.shape)

        def at(a):
            if a is None:
                return None
            if a.ndim == 0:
                return a
            if grid:
                return a[..., i, k]
            return a.reshape(a.shape[0], -1)[:, 0] if a.ndim > 1 else a

        out = {"grid": bool(grid), "cell_lat": r3(np.ravel(at(la))[0]) if la is not None else None,
               "cell_lon": r3(np.ravel(at(lo))[0]) if lo is not None else None}
        for n in SCALARS:
            x = at(arr(n))
            out[n] = None if x is None else r3(np.ravel(x)[0])
        u = at(arr("PCT_URBAN"))
        out["PCT_URBAN"] = None if u is None else r3(np.nansum(np.ravel(u)))
        for n in LEVELS:
            x = at(arr(n))
            out[n] = None if x is None else [r3(t) for t in np.ravel(x)]
        p = at(arr("PCT_NAT_PFT"))
        out["PCT_NAT_PFT_nonzero"] = None if p is None else \
            ";".join(f"{j}:{r3(t)}" for j, t in enumerate(np.ravel(p)) if t and t > 0)
    return out


# ------------------------------------------------------------------ run
def run(a):
    sites = [r["site"] for r in csv.DictReader(open(a.start_info))]
    expected = {r["site"]: r.get("normal400_case_expected", "") for r in csv.DictReader(open(a.start_info))}
    out = Path(a.out) if a.out else Path.home() / f"icos38_stage07_{utc()}"
    out.mkdir(parents=True, exist_ok=False)
    coords, cases, surf_rows, surf_long, meta = [], [], [], [], {"run_utc": utc(), "sites": {}}
    seen = {}
    for site in sites:
        loc = bif_location(find_bif(Path(a.sites_root) / site)) if (Path(a.sites_root) / site).is_dir() else None
        sc = site_cases(site, a.cases_root)
        cases += sc
        m = {"bif_location": loc, "n_cases": len(sc), "normal400_case_expected": expected.get(site, ""),
             "expected_case_found": any(c["case"] == expected.get(site) for c in sc)}
        lat = float(loc["lat"]) if loc else None
        lon = float(loc["lon"]) if loc else None
        for c in sc:
            p = Path(c["fsurdat"]) if c["fsurdat"] else None
            if not p or not p.is_file():
                continue
            key = str(p)
            if key not in seen:
                try:
                    seen[key] = {"sha256": sha256(p), **surface_values(p, lat, lon)}
                except Exception as e:  # keep going; record the error
                    seen[key] = {"error": repr(e)}
            s = seen[key]
            surf_rows.append({"site": site, "case": c["case"], "fsurdat": key,
                              **{k: s.get(k) for k in ("sha256", "grid", "cell_lat", "cell_lon", *SCALARS,
                                                       "PCT_URBAN", "PCT_NAT_PFT_nonzero", "error")}})
            for lev in range(10):
                vals = {n: (s.get(n) or [None] * 10)[lev] if s.get(n) and lev < len(s.get(n)) else None
                        for n in LEVELS}
                surf_long.append({"site": site, "case": c["case"], "fsurdat": key, "level": lev + 1, **vals})
        if loc is None and surf_rows and surf_rows[-1]["site"] == site and surf_rows[-1].get("cell_lat") is not None:
            r = surf_rows[-1]
            loc = {"lat": r["cell_lat"], "lon": r["cell_lon"], "elevation_m": "",
                   "coord_source": f"point surface LATIXY/LONGXY of {r['case']} (no BIF)"}
        if loc and loc.get("lon") not in ("", None) and float(loc["lon"]) > 180:  # 0-360 -> -180..180
            loc["lon"] = round(float(loc["lon"]) - 360, 6)
            loc["coord_source"] += "; longitude converted from 0-360"
        coords.append({"site": site, "network": "ICOS", "site_name": "",
                       "lat": loc["lat"] if loc else "", "lon": loc["lon"] if loc else "",
                       "elevation_m": loc.get("elevation_m", "") if loc else "",
                       "coord_source": loc["coord_source"] if loc else "MISSING",
                       "coord_verification": ("IRIDIS6_SOURCE_FILE" if loc and loc["coord_source"].startswith("BIF")
                                              else "IRIDIS6_CASE_SURFACE" if loc else "MISSING")})
        meta["sites"][site] = m
        print(f"{site:7s} coords={coords[-1]['lat']},{coords[-1]['lon']} ({coords[-1]['coord_verification']}) "
              f"cases={len(sc)} expected_found={m['expected_case_found']}", flush=True)

    def write(name, rows, fields=None):
        fields = fields or (list(rows[0].keys()) if rows else ["site"])
        delim = "\t" if name.endswith(".tsv") else ","
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter=delim, lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write("ICOS38_COORDINATES.csv", coords, list(COORD_FIELDS))
    write("stage07_cases.tsv", cases)
    write("stage07_surface_fields.tsv", surf_rows)
    write("stage07_surface_soil_long.csv", surf_long)
    meta["surfaces"] = {k: {kk: vv for kk, vv in v.items() if kk not in LEVELS} for k, v in seen.items()}
    (out / "stage07.json").write_text(json.dumps(meta, indent=1, default=str))
    co2 = sorted({(c["CLM_CO2_TYPE"], c["CCSM_CO2_PPMV"]) for c in cases})
    print(f"\n{len(coords)} sites, {sum(1 for c in coords if c['lat'] != '')} with coordinates; "
          f"{len(cases)} cases; {len(seen)} distinct surfaces")
    print("CO2 settings seen (CLM_CO2_TYPE, CCSM_CO2_PPMV):", co2[:12], "..." if len(co2) > 12 else "")
    print("STAGE07_OUT=" + str(out))
    return out


def self_test():
    import numpy as np
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "info.csv").write_text("site,normal400_case_expected\nXX-Aaa,XX-Aaa_B01_FIXNC_NORMAL400\nYY-Bbb,\n"
                                     "ZZ-Ccc,\n")
        surf2 = td / "surf2.nc"
        with open_nc(surf2, "w") as ds:
            ds.createDimension("lsmlat", 1); ds.createDimension("lsmlon", 1)
            ds.createVariable("LATIXY", "f8", ("lsmlat", "lsmlon"))[:] = 74.473
            ds.createVariable("LONGXY", "f8", ("lsmlat", "lsmlon"))[:] = 339.449
        c2 = td / "cases" / "ZZ-Ccc_B04_NORMAL400"
        (c2 / "CaseDocs").mkdir(parents=True)
        (c2 / "CaseDocs" / "lnd_in").write_text(f" fsurdat = '{surf2}'\n")
        pk = td / "sites" / "XX-Aaa" / "forcing" / "packages"
        pk.mkdir(parents=True)
        bif = ("SITE_ID,GROUP_ID,VARIABLE_GROUP,VARIABLE,DATAVALUE\nXX-Aaa,1,GRP_LOCATION,LOCATION_LAT,50.95\n"
               "XX-Aaa,1,GRP_LOCATION,LOCATION_LONG,13.57\nXX-Aaa,1,GRP_LOCATION,LOCATION_ELEV,380\n")
        with zipfile.ZipFile(pk / "ICOS_XX-Aaa.zip", "w") as z:
            z.writestr("ICOS_XX-Aaa_FLUXNET_BIF_2000-2020_v1.3_r1.csv", bif)
        surf = td / "surf.nc"
        with open_nc(surf, "w") as ds:
            ds.createDimension("lsmlat", 1); ds.createDimension("lsmlon", 1); ds.createDimension("nlevsoi", 10)
            ds.createDimension("natpft", 15)
            for n, val in (("LATIXY", 50.9), ("LONGXY", 13.6), ("zbedrock", 5.0), ("FMAX", 0.39),
                           ("SOIL_COLOR", 15), ("PCT_NATVEG", 100.0)):
                ds.createVariable(n, "f8", ("lsmlat", "lsmlon"))[:] = val
            for n, val in (("PCT_SAND", 40.0), ("PCT_CLAY", 20.0), ("ORGANIC", 10.0)):
                ds.createVariable(n, "f8", ("nlevsoi", "lsmlat", "lsmlon"))[:] = val
            p = np.zeros((15, 1, 1)); p[1] = 100
            ds.createVariable("PCT_NAT_PFT", "f8", ("natpft", "lsmlat", "lsmlon"))[:] = p
        for cname in ("XX-Aaa_B01_FIXNC_NORMAL400", "XX-Aaa_B01_FIXNC_AD400"):
            c = td / "cases" / cname
            (c / "CaseDocs").mkdir(parents=True)
            (c / "CaseDocs" / "lnd_in").write_text(f" fsurdat = '{surf}'\n use_bedrock = .false.\n")
            (c / "env_run.xml").write_text('<entry id="CCSM_CO2_PPMV" value="376.95">\n'
                                           '<entry id="CLM_CO2_TYPE" value="constant">\n'
                                           '<entry id="DATM_YR_START" value="2004">\n')
        o = run(argparse.Namespace(start_info=td / "info.csv", sites_root=td / "sites", cases_root=td / "cases",
                                   out=td / "out"))
        co = list(csv.DictReader(open(o / "ICOS38_COORDINATES.csv")))
        assert co[0]["lat"] == "50.95" and co[0]["coord_verification"] == "IRIDIS6_SOURCE_FILE", co[0]
        assert co[1]["coord_verification"] == "MISSING"
        assert co[2]["coord_verification"] == "IRIDIS6_CASE_SURFACE" and abs(float(co[2]["lon"]) + 20.551) < 1e-6, co[2]
        cs = list(csv.DictReader(open(o / "stage07_cases.tsv"), delimiter="\t"))
        assert len(cs) == 3 and cs[0]["CCSM_CO2_PPMV"] == "376.95" and "DATM_YR_START=2004" in cs[0]["datm_years"]
        sl = list(csv.DictReader(open(o / "stage07_surface_soil_long.csv")))
        assert len(sl) == 20 and float(sl[0]["PCT_SAND"]) == 40.0
        sf = list(csv.DictReader(open(o / "stage07_surface_fields.tsv"), delimiter="\t"))
        assert sf[0]["PCT_NAT_PFT_nonzero"] == "1:100.0" and float(sf[0]["zbedrock"]) == 5.0
    print("SELF-TEST PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--start-info", type=Path, default=HERE / "ICOS38_post_spinup_start_info.csv")
    ap.add_argument("--sites-root", type=Path, default=BASE / "sites" / "MY_EC_SITE")
    ap.add_argument("--cases-root", type=Path, default=BASE / "cases")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    run(a)


if __name__ == "__main__":
    main()
