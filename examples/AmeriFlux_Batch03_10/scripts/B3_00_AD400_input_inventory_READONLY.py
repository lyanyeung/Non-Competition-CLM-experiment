#!/usr/bin/env python3
"""AmeriFlux Batch03 (10 sites) AD400 step 0: READ-ONLY inventory of every model input.

User decision 2026-10-29: run AD400 for Batch03, FIXNC arm only, direct 80 x 5 years, US-Me2 forcing 2002-2022.
This script writes nothing and submits nothing. It reports, per site:
  forcing   the selected research shadow (path pattern below), sha256, rows, step, first/last time, NaN per field,
            min/max of TBOT QBOT PSRF FSDS FLDS WIND PRECTmms, Feb-29 rows, NOLEAP completeness
  clock     release BIF UTC_OFFSET and LOCATION_LAT/LONG (release folder via the Stage07 manifest)
  ZBOT      every TA* row of the AmeriFlux BASE measurement-height table (Batch02 Stage06 pinned copy)
  surface   original Stage03 point surface sites/MY_EC_SITE/<SITE>/subset_data_batch03_surf2000/surfdata*.nc
  soil      rows of the AmeriFlux50 Stage01 CLM10 sand/clay wide table
  model     AD400 template case, private FATES AD overlay, CO2 table, any existing Batch03 FIXNC case
  Me2       FULLSET HH meteorology columns and QC needed to build its forcing
"""
import csv, glob, hashlib, json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SRC = B / "experiments/AmeriFlux_MultiSite_10_Batch03"
ST = SRC / "science_trials"
S07 = SRC / "qcv5_native_trial_20261022T024559Z_36c46e58/exact_input_manifest.json"
B02D06 = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400"
HEIGHTS = B02D06 / "BASE_MeasurementHeight_20260908.csv"
CO2 = B02D06 / "co2_annmean_gl.csv"
TEMPLATE = B / "cases/CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5"
OVERLAY = B / "experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay"
SOIL = [Path.home() / "CLM_FATES_SOIL/AmeriFlux50_20261026/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv",
        Path.home() / "CLM_FATES_SOIL/AmeriFlux50_20261026_full_BADM/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv"]
SHADOW = {
    "US-Kon": "US_Kon_14T_last_May26_ERA5_research_only_20261029T073611Z_8d42d243/*.csv",
    "US-MMS": "US_MMS_MANUAL_ISOLATED_16_FILLED_47QC1_*/US-MMS_219000_ISOLATED_NUMERIC_SENSITIVITY_NOT_DATM.csv",
    "US-Me2": None,
    "US-Me6": "cl03_US-Me6_research_shadow_20261029T044209Z_6513e2db/US-Me6_CL03_RESEARCH_SHADOW_NOLEAP.csv",
    "US-MOz": "US_MOz_Jan09_49QC1_TWO_REANALYSIS_RESEARCH_ONLY_20261029T043831Z_397227c6/FLUXNET_COMPANION_ERA_315360_FULL_RESEARCH_ONLY_NOT_DATM.csv",
    "US-Mpj": "stage13o_Mpj_20HH_operator_approved_ERA_RH_20261026T210746Z_5c3c8653/US-Mpj_CLM_forcing_2008_2025_STAGE13O_20HH_ERA_RH_RESEARCH_SHADOW.csv",
    "US-MtB": "mtb04_US-MtB_research_shadow_20261029T034057Z_ed54796b/US-MtB_MTB04_RESEARCH_SHADOW_NOLEAP.csv",
    "US-NC2": "stage11q_US-NC2_auto9_RH_only_20261024T112211Z_cd95c65a/US-NC2_humidity_only_auto9_shadow_NOLEAP.csv",
    "US-NR1": "cl03_US-NR1_research_shadow_20261029T044240Z_88750f74/US-NR1_CL03_RESEARCH_SHADOW_NOLEAP.csv",
    "US-NR3": "nr3_10_claude_research_shadow_v2_20261029T070254Z_63df7497/US-NR3_NR3_10_MAIN_RESEARCH_SHADOW_V2_NOLEAP.csv"}
MET = ("TBOT", "QBOT", "PSRF", "FSDS", "FLDS", "WIND", "PRECTmms")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def say(k, v): print(k, json.dumps(v, default=str), flush=True)


def forcing(site):
    pat = SHADOW[site]
    if pat is None: return dict(status="TO_BUILD (US-Me2 FULLSET + CL04-CL07 ledger)")
    c = sorted(glob.glob(str(ST / pat)))
    c = [x for x in c if not re.search(r"provenance|change|ledger|decision", Path(x).name, re.I)]
    if len(c) != 1: return dict(status="AMBIGUOUS_OR_MISSING", candidates=c)
    p = Path(c[0]); hdr = list(pd.read_csv(p, nrows=0).columns)
    tcol = "time" if "time" in hdr else next((h for h in hdr if h.lower() in ("time", "timestamp", "timestamp_start", "datetime")), hdr[0])
    use = [tcol] + [m for m in MET if m in hdr]
    d = pd.read_csv(p, usecols=use, low_memory=False)
    t = pd.to_datetime(d[tcol].astype(str).str.replace("T", " "), errors="coerce", format="mixed")
    step = int(round(t.diff().dt.total_seconds().median() / 60)) if len(t) > 1 else None
    yrs = t.dt.year
    out = dict(path=str(p), sha256=sha(p), rows=len(d), columns=hdr, time_col=tcol, step_min=step, first=str(t.iloc[0]), last=str(t.iloc[-1]),
               years=[int(yrs.min()), int(yrs.max())], bad_time=int(t.isna().sum()), feb29=int(((t.dt.month == 2) & (t.dt.day == 29)).sum()),
               missing_fields=[m for m in MET if m not in hdr],
               expected_rows_noleap=int((yrs.max() - yrs.min() + 1) * 525600 // step) if step else None,
               gaps=int((t.diff().dt.total_seconds().iloc[1:] != step * 60).sum()) if step else None,
               incomplete_marker=(p.parent / "INCOMPLETE_DO_NOT_USE_FOR_DATM_OR_SPINUP").is_file())
    out["nan"] = {m: int(d[m].isna().sum()) for m in MET if m in d}
    out["range"] = {m: [round(float(d[m].min()), 6), round(float(d[m].max()), 6)] for m in MET if m in d}
    return out


def release(site, man):
    spec = [x for x in man["sites"] if x["site"] == site]
    if len(spec) != 1: return dict(status="NOT_IN_STAGE07_MANIFEST")
    spec = spec[0]; d = Path(spec["primary"]).parent
    bif = sorted(d.glob("*_BIF_*.csv"))
    out = dict(primary=spec["primary"], era=spec.get("era"), release=spec.get("release"), bif=[str(x) for x in bif])
    if bif:
        b = pd.read_csv(bif[0], keep_default_na=False)
        for k in ("UTC_OFFSET", "LOCATION_LAT", "LOCATION_LONG", "LOCATION_ELEV"):
            out[k] = sorted(set(b.loc[b.VARIABLE == k, "DATAVALUE"].astype(str)))
    return out


def heights(sites):
    if not HEIGHTS.is_file(): return {"status": "MISSING " + str(HEIGHTS)}
    rows = [r for r in csv.DictReader(HEIGHTS.open(encoding="utf-8-sig")) if r.get("Site_ID") in sites and re.match(r"^TA(_|$)", r.get("Variable", ""))]
    out = {"table": str(HEIGHTS), "sha256": sha(HEIGHTS)}
    for s in sites:
        out[s] = [{k: r.get(k) for k in ("Variable", "Height", "Start_Date", "End_Date", "Instrument_Model", "Comment") if k in r} for r in rows if r["Site_ID"] == s]
    return out


def surface(site):
    c = sorted((B / "sites/MY_EC_SITE" / site / "subset_data_batch03_surf2000").glob("surfdata*.nc"))
    if len(c) != 1: return dict(status="NOT_UNIQUE", candidates=[str(x) for x in c])
    from netCDF4 import Dataset
    with Dataset(c[0]) as ds:
        v = ds.variables
        o = dict(path=str(c[0]), sha256=sha(c[0]), lat=float(np.ravel(v["LATIXY"][:])[0]), lon=float(np.ravel(v["LONGXY"][:])[0]),
                 PCT_NAT_PFT_shape=list(v["PCT_NAT_PFT"].shape), PCT_NATVEG=float(np.ravel(v["PCT_NATVEG"][:])[0]),
                 PCT_CROP=float(np.ravel(v["PCT_CROP"][:])[0]) if "PCT_CROP" in v else None,
                 sand_L=np.round(np.ravel(v["PCT_SAND"][:]), 1).tolist(), clay_L=np.round(np.ravel(v["PCT_CLAY"][:]), 1).tolist(),
                 organic_max=float(np.max(v["ORGANIC"][:])) if "ORGANIC" in v else None)
    return o


def soil(sites):
    p = next((x for x in SOIL if x.is_file()), None)
    if not p: return {"status": "MISSING", "looked": [str(x) for x in SOIL]}
    d = pd.read_csv(p)
    sc = next(c for c in d.columns if c.lower() in ("site", "site_id"))
    return {"path": str(p), "sha256": sha(p), "columns": list(d.columns)[:30],
            "rows": {s: d.loc[d[sc] == s].iloc[0].to_dict() if (d[sc] == s).any() else None for s in sites}}


def env(case, key):
    for f in ("env_run.xml", "env_case.xml", "env_build.xml", "env_mach_pes.xml"):
        p = case / f
        if p.is_file():
            for e in ET.parse(p).getroot().iter("entry"):
                if e.get("id") == key: return e.get("value")
    return None


def model():
    o = {"template": str(TEMPLATE), "template_exists": TEMPLATE.is_dir()}
    if TEMPLATE.is_dir():
        for k in ("BUILD_COMPLETE", "DATM_MODE", "CALENDAR", "ATM_NCPL", "EXEROOT", "COMPSET", "CLM_ACCELERATED_SPINUP"): o[k] = env(TEMPLATE, k)
        cs = (TEMPLATE / "CaseStatus").read_text(errors="replace") if (TEMPLATE / "CaseStatus").is_file() else ""
        o["template_run_success"] = bool(re.search(r"case\.run success", cs))
        lnd = TEMPLATE / "CaseDocs/lnd_in"
        if lnd.is_file():
            t = lnd.read_text(); m = re.search(r"fates_paramfile\s*=\s*'([^']+)'", t); o["fates_paramfile"] = m.group(1) if m else None
            if m and Path(m.group(1)).is_file(): o["fates_paramfile_sha256"] = sha(m.group(1))
    o["overlay"] = all((OVERLAY / f).is_file() for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"))
    o["co2_csv"] = str(CO2) if CO2.is_file() else "MISSING"
    o["existing_batch03_cases"] = sorted(x.name for x in (B / "cases").glob("*AMF_B03*"))
    return o


def me2():
    man = json.loads(S07.read_text()); spec = [x for x in man["sites"] if x["site"] == "US-Me2"][0]
    hdr = list(pd.read_csv(spec["primary"], nrows=0).columns)
    want = ["TA_F", "TA_F_QC", "VPD_F", "VPD_F_QC", "PA_F", "PA_F_QC", "SW_IN_F", "SW_IN_F_QC", "LW_IN_F", "LW_IN_F_QC", "WS_F", "WS_F_QC", "P_F", "P_F_QC", "RH", "CO2_F_MDS"]
    d = pd.read_csv(spec["primary"], usecols=["TIMESTAMP_START"] + [c for c in want if c in hdr], dtype={"TIMESTAMP_START": str}, na_values=-9999, low_memory=False)
    o = {"primary": spec["primary"], "rows": len(d), "first": d.TIMESTAMP_START.iloc[0], "last": d.TIMESTAMP_START.iloc[-1], "missing_cols": [c for c in want if c not in hdr]}
    for c in want:
        if c in d and not c.endswith("_QC"): o[c] = dict(nan=int(d[c].isna().sum()), min=float(d[c].min()), max=float(d[c].max()))
        if c in d and c.endswith("_QC"): o[c] = {str(k): int(v) for k, v in d[c].value_counts(dropna=False).items()}
    return o


def main():
    print("B3_00 AD400 INPUT INVENTORY | READ ONLY", flush=True)
    sites = list(SHADOW)
    man = json.loads(S07.read_text())
    H = heights(sites); say("ZBOT_TABLE", {"table": H.get("table"), "sha256": H.get("sha256")})
    So = soil(sites); say("SOIL_TABLE", {k: v for k, v in So.items() if k != "rows"})
    for s in sites:
        print(f"\n######## {s}", flush=True)
        for lab, fn in (("FORCING", lambda: forcing(s)), ("RELEASE", lambda: release(s, man)), ("SURFACE", lambda: surface(s))):
            try: say(lab, fn())
            except Exception as e: say(lab, {"status": "ERROR", "error": f"{type(e).__name__}: {e}"})
        say("TA_HEIGHTS", H.get(s))
        r = (So.get("rows") or {}).get(s); say("SOIL10", {k: v for k, v in (r or {}).items() if re.search(r"site|SAND|CLAY|tier|source", str(k), re.I)} if r else None)
    print(flush=True)
    try: say("MODEL", model())
    except Exception as e: say("MODEL", {"status": "ERROR", "error": str(e)})
    try: say("ME2_FULLSET", me2())
    except Exception as e: say("ME2_FULLSET", {"status": "ERROR", "error": str(e)})
    print("\nB3_00 DONE | no files written, no jobs", flush=True)


if __name__ == "__main__":
    main()
