#!/usr/bin/env python3
"""AmeriFlux Batch03 (10 sites): full-record forcing QC + PFT/soil + DATM admission, then FIXNC AD400 DIRECT 80 x 5.

User decisions 2026-10-29: FIXNC arm only; direct AD400 (one case.submit, STOP_N=5, RESUBMIT=79, no AD5 smoke);
US-Me2 forcing 2002-2022 (all years). Method = AmeriFlux Batch02 Stage06 (Batch01 Stage14/21/31), adapted to the
Batch03 research shadows (CSV) instead of Stage95 NetCDF.

Inputs (read only)
  forcing   the selected Batch03 research shadow of each site (table SHADOW); US-Me2 is built here (once) from the
            SHA-pinned FULLSET_HH (qcv5 conversion) + the CL05 (122 EMP_LOYO) / CL07 (243 ERA_E_CAL) humidity ledger,
            into a NEW folder science_trials/b3_US-Me2_FULLSET_CL05_CL07_research_shadow_v1 (nothing overwritten)
  clock     release BIF UTC_OFFSET (US-Me2: -8, BADM + CL clock evidence)
  ZBOT      BASE_MeasurementHeight_20260908.csv (sha pinned), static rule table ZBOT below
  surface   Stage03 sites/MY_EC_SITE/<SITE>/subset_data_batch03_surf2000/surfdata*.nc -> NEW NATVEG100/CROP0 copy with the
            50-site register CLM host PCT_NAT_PFT and the AmeriFlux50 Stage01 CLM10 sand/clay (ORGANIC unchanged)
  FATES     DEFAULT14 = template fates_paramfile; HYDRO_SHRUB (US-Me2, US-Me6) = private copy, host10 -> FATES8 only
  CO2       NOAA annual mean of the first forcing year (Batch02 Stage06 cached table)
  template  CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5, create_clone --keepexe, private FATES AD overlay preview

Full-record QC (check, and again inside prepare; HOLD stops that site)
  timeline NOLEAP complete, no NaN, hard ranges (qcv5), TBOT = TA_USE + 273.15, QBOT closure, e > 0, QBOT > 0,
  DATM saturation (Flatau, ice below 0 C) clamp count, PSRF vs barometric elevation, FSDS vs top-of-atmosphere with the
  UTC shift (diurnal centroid lag must be < 45 min = clock proof), FLDS emissivity, annual P/T/SW table.

Actions
  self-test
  check                                         READ ONLY (Me2 shadow built in memory)
  prepare --confirm PREPARE_AMF_B03_TEN_DIRECT_AD400_CASES_NO_SLURM
  submit  --confirm SUBMIT_AMF_B03_DIRECT_AD400_80x5_ONCE
  status | audit-first5 | audit-ad400           READ ONLY
  quarantine-failed-prepare --sites .. --confirm QUARANTINE_AMF_B03_FAILED_PREPARE_NO_SLURM
Ledgers refuse duplicate stateful actions.
"""
from __future__ import annotations
import argparse, csv, glob, hashlib, json, math, os, re, resource, shutil, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
CIMESCRIPTS = CTSM / "cime/scripts"
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
EXP = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch03_10"
D01 = EXP / "Stage01_direct_AD400"
SRC = B / "experiments/AmeriFlux_MultiSite_10_Batch03"
ST = SRC / "science_trials"
S07 = SRC / "qcv5_native_trial_20261022T024559Z_36c46e58/exact_input_manifest.json"
B02D06 = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400"
BASE_HEIGHTS = B02D06 / "BASE_MeasurementHeight_20260908.csv"
BASE_HEIGHTS_SHA = "1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a"
CO2_CSV = B02D06 / "co2_annmean_gl.csv"
TEMPLATE = B / "cases/CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5"
OVERLAY = B / "experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay"
SOIL_WIDE = Path.home() / "CLM_FATES_SOIL/AmeriFlux50_20261026/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv"
SOIL_WIDE_SHA = "ab142c12b7e200f0f65e9d04354c87acc6593af08373844ad5d9f2d008cc11b7"
TEMPLATE_PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
USER = "ly3n24"
SACCT_START = "2026-10-29"
MIN_STACK_KB = 65536
SEGMENTS, SEG_YEARS = 80, 5

# first, last forcing year; native step (min)
SITES = {"US-Kon": (2004, 2019, 30), "US-MMS": (1999, 2023, 60), "US-Me2": (2002, 2022, 30), "US-Me6": (2010, 2025, 30),
         "US-MOz": (2004, 2021, 30), "US-Mpj": (2008, 2025, 30), "US-MtB": (2009, 2024, 30), "US-NC2": (2005, 2025, 30),
         "US-NR1": (1999, 2025, 30), "US-NR3": (2007, 2024, 30)}
ORDER = tuple(SITES)
SHADOW = {  # research shadows (B3_00 inventory 2026-10-29); sha pinned where printed by B3_00
    "US-Kon": (["US_Kon_14T_last_May26_ERA5_research_only_20261029T073611Z_8d42d243/US-Kon_280320_final_May26_research_NOT_DATM.csv"], None),
    "US-MMS": (["US_MMS_MANUAL_ISOLATED_16_FILLED_47QC1_*/US-MMS_219000_ISOLATED_NUMERIC_SENSITIVITY_NOT_DATM.csv",
                "US_MMS_MANUAL_16H_ISOLATED_SENSITIVITY_*/US_MMS_219000_HR_NUMERIC_SCENARIO_NOT_DATM.csv"], None),
    "US-Me2": (None, None),
    "US-Me6": (["cl03_US-Me6_research_shadow_20261029T044209Z_6513e2db/US-Me6_CL03_RESEARCH_SHADOW_NOLEAP.csv"], "db7ea958fc6c02339e9f594c72b74d0e4b786115a746c6ab018c51c5d0bba3ea"),
    "US-MOz": (["US_MOz_Jan09_49QC1_TWO_REANALYSIS_RESEARCH_ONLY_20261029T043831Z_397227c6/FLUXNET_COMPANION_ERA_315360_FULL_RESEARCH_ONLY_NOT_DATM.csv"], "d00b122c16da202a07b18f7fb40d61edbb288f76322b44d5818872bf4e8ee34e"),
    "US-Mpj": (["stage13o_Mpj_20HH_operator_approved_ERA_RH_20261026T210746Z_5c3c8653/US-Mpj_CLM_forcing_2008_2025_STAGE13O_20HH_ERA_RH_RESEARCH_SHADOW.csv"], "9e4ae998b8572bc9bda39907732d59a6f5fce28c4394931f3bd2e4a540d7aa70"),
    "US-MtB": (["mtb04_US-MtB_research_shadow_20261029T034057Z_ed54796b/US-MtB_MTB04_RESEARCH_SHADOW_NOLEAP.csv"], "d47a5f095146ef23f7dc2238de9952ef1e54dc6992de02a03a175905a22fc613"),
    "US-NC2": (["stage11q_US-NC2_auto9_RH_only_20261024T112211Z_cd95c65a/US-NC2_humidity_only_auto9_shadow_NOLEAP.csv"], "85015c8bb625d894f3b53d7e0fadd690b1f5dec48751613ecea794310ab518f5"),
    "US-NR1": (["cl03_US-NR1_research_shadow_20261029T044240Z_88750f74/US-NR1_CL03_RESEARCH_SHADOW_NOLEAP.csv"], "ece6d6a2698120656b183479ad90f663f23a5cfb0d9ecc5dbd4529825e0feb4d"),
    "US-NR3": (["nr3_10_claude_research_shadow_v2_20261029T070254Z_63df7497/US-NR3_NR3_10_MAIN_RESEARCH_SHADOW_V2_NOLEAP.csv"], "ec9a1da121fed6d91594856649027cd1286fa3c73887a057c03fff3ebf82fd7d")}
# UTC offset (h), latitude, longitude, elevation (m): release BIF (cross-checked at run time); US-Me2 from BADM/CL clock proof
CLOCK = {"US-Kon": (-6, 39.0824, -96.5603, 417), "US-MMS": (-5, 39.3232, -86.4131, 275), "US-Me2": (-8, 44.4523, -121.5574, 1253),
         "US-Me6": (-8, 44.3233, -121.6078, 998), "US-MOz": (-6, 38.7441, -92.2000, 219.4), "US-Mpj": (-7, 34.4385, -106.2377, 2196),
         "US-MtB": (-7, 32.4167, -110.7256, 2573), "US-NC2": (-5, 35.8030, -76.6685, 5), "US-NR1": (-7, 40.0329, -105.5464, 3050),
         "US-NR3": (-7, 40.0520, -105.5864, 3504)}
# static ZBOT: (metres, BASE variable that must carry it, rule)
ZBOT = {"US-Kon": (3.0, "TA_1_1_1", "TA_1_1_1 3 m (both dated rows 3 m)"),
        "US-MMS": (46.0, "TA_1_1_1", "TA_1_1_1 46 m top level (profile 46/34/22/2 m)"),
        "US-Me2": (32.0, "TA_1_1_3", "32 m: TA_1_1_3 2002-01 and TA_1_1_2 2007-12 at 32 m, TA_1_1_1 33 m from 2015-10; "
                                     "post-burn 5.34 m tower from 2022-08-25 (4 months) not represented"),
        "US-Me6": (14.2, "TA_1_1_1", "TA_1_1_1 14.2 m"), "US-MOz": (30.48, "TA_1_1_1", "TA_1_1_1 30.48 m"),
        "US-Mpj": (8.2, "TA", "TA 8.2 m"), "US-MtB": (31.0, "TA_1_1_1", "TA_1_1_1 31 m top level (31/24/16/8.75/1.5 m)"),
        "US-NC2": (23.0, "TA_1_1_1", "TA_1_1_1 23 m from 2012-03-29 (about 65 % of 2005-2025); 18.5 m before"),
        "US-NR1": (21.5, "TA_1_1_1", "TA_1_1_1 21.5 m top level (21.5/8/2 m)"), "US-NR3": (3.0, "TA", "TA 3 m")}
# 50-site register (clm-fates repo examples/Ameriflux_Site/Ameriflux_PFT/RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv)
PFT = {"US-Kon": ({13: 10, 14: 90}, "DEFAULT14", {13: 10, 14: 90}), "US-MMS": ({7: 100}, "DEFAULT14", {6: 100}),
       "US-Me2": ({1: 90, 10: 5, 9: 5}, "HYDRO_SHRUB", {2: 90, 7: 5, 8: 5}), "US-Me6": ({1: 80, 10: 5, 13: 15}, "HYDRO_SHRUB", {2: 80, 8: 5, 13: 15}),
       "US-MOz": ({1: 10, 7: 90}, "DEFAULT14", {2: 10, 6: 90}), "US-Mpj": ({0: 20, 1: 60, 14: 20}, "DEFAULT14", {2: 60, 14: 20}),
       "US-MtB": ({1: 100}, "DEFAULT14", {2: 100}), "US-NC2": ({1: 90, 7: 10}, "DEFAULT14", {2: 90, 6: 10}),
       "US-NR1": ({2: 100}, "DEFAULT14", {2: 100}), "US-NR3": ({0: 20, 12: 80}, "DEFAULT14", {12: 80})}
SOIL030 = {"US-Kon": (6.4, 29.0), "US-MMS": (2.4, 21.7), "US-Me2": (62.7, 9.7), "US-Me6": (69.8, 6.9), "US-MOz": (2.0, 26.2),
           "US-Mpj": (35.9, 22.2), "US-MtB": (37.5, 25.5), "US-NC2": (66.8, 11.3), "US-NR1": (57.2, 16.8), "US-NR3": (63.0, 10.8)}
# US-Me2 humidity ledger (Claude CL04-CL07, clm-fates repo docs/US_ME2_CL04_FOUR_EVENT_DECISION_20261029.md)
ME2_FULLSET_SHA = "5b29b04da37960a1640c19b75fc2a8ffbffd703ada89ba6c36689d86f834ae3e"
ME2_CL05 = SRC / "reports/cl05_US-Me2_nonphysical_scan_20261029T065536Z_25495c8d/Me2_flagged_rows_decisions.csv"
ME2_CL07 = SRC / "reports/cl07_US-Me2_ERA_E_calibrated_20261029T071618Z_3480c075/Me2_243_calibrated_ERA_decisions.csv"
ME2_OUT = ST / "b3_US-Me2_FULLSET_CL05_CL07_research_shadow_v1"
ME2_CSV = "US-Me2_B3_FULLSET_CL05_CL07_RESEARCH_SHADOW_NOLEAP.csv"

COLS = ["time", "TBOT", "QBOT", "PSRF", "FSDS", "FLDS", "WIND", "PRECTmms", "TA_USE", "VPD_USE"]
MET = ("TBOT", "QBOT", "PSRF", "FSDS", "FLDS", "WIND", "PRECTmms")
UNITS = {"TBOT": "K", "QBOT": "kg/kg", "PSRF": "Pa", "FSDS": "W/m2", "FLDS": "W/m2", "WIND": "m/s", "PRECTmms": "mm/s", "ZBOT": "m"}
FIELDS = {"PRECTmms": "Faxa_precn", "FSDS": "Faxa_swdn", "ZBOT": "Sa_z", "TBOT": "Sa_tbot",
          "WIND": "Sa_wind", "QBOT": "Sa_shum", "PSRF": "Sa_pbot", "FLDS": "Faxa_lwdn"}
FATES_FLAGS = {"use_fates": ".true.", "use_fates_sp": ".false.", "use_fates_fixed_biogeog": ".true.",
               "use_fates_nocomp": ".true.", "use_cn": ".false."}
FATES_NAMES = ["broadleaf_evergreen_tropical_tree", "needleleaf_evergreen_extratrop_tree", "needleleaf_colddecid_extratrop_tree",
               "broadleaf_evergreen_extratrop_tree", "broadleaf_hydrodecid_tropical_tree", "broadleaf_colddecid_extratrop_tree",
               "broadleaf_evergreen_extratrop_shrub", "broadleaf_hydrodecid_extratrop_shrub", "broadleaf_colddecid_extratrop_shrub",
               "broadleaf_evergreen_arctic_shrub", "broadleaf_colddecid_arctic_shrub", "arctic_c3_grass", "cool_c3_grass", "c4_grass"]
DEFAULT14 = np.zeros((14, 14))   # rows = CLM host natpft 1..14, cols = FATES PFT 1..14 (0-based)
for _h, _f in {1: 1, 2: 1, 3: 2, 4: 0, 5: 3, 6: 4, 7: 5, 8: 5, 9: 6, 10: 8, 12: 11, 13: 12, 14: 13}.items():
    DEFAULT14[_h - 1, _f] = 1.0
DEFAULT14[10, 8], DEFAULT14[10, 9], DEFAULT14[10, 10] = 0.1, 0.1, 0.8
HYDRO_SHRUB = DEFAULT14.copy(); HYDRO_SHRUB[9, :] = 0.0; HYDRO_SHRUB[9, 7] = 1.0   # host 10 -> broadleaf_hydrodecid_extratrop_shrub
MAPS = {"DEFAULT14": DEFAULT14, "HYDRO_SHRUB": HYDRO_SHRUB}
LAND_OTHER = ("PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")
HARD = {"TBOT": (180, 340), "QBOT": (0, 0.08), "PSRF": (49000, 111000), "FSDS": (0, 1600), "FLDS": (0, 800), "WIND": (0, 75)}
A_W = (6.107799961, 4.436518521e-01, 1.428945805e-02, 2.650648471e-04, 3.031240396e-06, 2.034080948e-08, 6.136820929e-11)
A_I = (6.109177956, 5.034698970e-01, 1.886013408e-02, 4.176223716e-04, 5.824720280e-06, 4.838803174e-08, 1.838826904e-10)
ACK_PREP = "PREPARE_AMF_B03_TEN_DIRECT_AD400_CASES_NO_SLURM"
ACK_SUB = "SUBMIT_AMF_B03_DIRECT_AD400_80x5_ONCE"
ACK_Q = "QUARANTINE_AMF_B03_FAILED_PREPARE_NO_SLURM"
POINTERS = ("clm2", "datm", "cpl")
RUN_RE = re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE = re.compile(r"Submitted job case\.st_archive with id (\d+)")


def fail(s): raise RuntimeError(str(s))
def utc(): return datetime.now(timezone.utc).isoformat()
def stamp(y): return f"{y:04d}-01-01-00000"


def digest(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def cmd(argv, cwd=None, timeout=300):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode: fail(f"rc={p.returncode} {' '.join(map(str, argv))}\nOUT {p.stdout[-1500:]}\nERR {p.stderr[-1500:]}")
    return p.stdout


def xq(case, k): return cmd(["./xmlquery", k, "--value"], cwd=case, timeout=90).strip()
def xc(case, k, v): cmd([Path(case) / "xmlchange", f"{k}={v}"], cwd=case, timeout=90)


def nml_get(text, key):
    hits = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", text)
    if len(hits) > 1: fail("duplicate namelist key " + key)
    return hits[0].strip().rstrip(",").strip().strip("'\"").strip() if hits else None


def nml_set(text, key, val):
    hits = list(re.finditer(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*$", text))
    if len(hits) > 1: fail("duplicate user_nl key " + key)
    line = f"{key} = {val}"
    if hits: return text[:hits[0].start()] + line + text[hits[0].end():]
    return text.rstrip() + "\n" + line + "\n"


def nml_del(text, key): return re.sub(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*\r?\n?", "", text)
def load(p): return json.loads(Path(p).read_text()) if Path(p).is_file() else {}


def save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp"); tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n"); tmp.replace(p)


def pick(sites):
    if not sites: return ORDER
    bad = [s for s in sites if s not in SITES]
    if bad: fail("unknown sites " + ",".join(bad))
    return tuple(s for s in ORDER if s in sites)


# ------------------------------------------------------------- identities
def name(s): return f"{s}_AMF_B03_FIXNC_AD400_DIRECT"
def case_dir(s): return B / "cases" / name(s)
def run_dir(s): return OUT / name(s) / "run"
def arch_dir(s): return OUT / "archive" / name(s)
def ledger(s): return D01 / f"{s}_AD400_DIRECT_state.json"
def surface(s): return EXP / s / "surface" / f"surfdata_{s}_FIXNC_PFT_soil10_b03_v1.nc"
def forcing_dir(s): return EXP / s / "forcing_UTC_midpoint_ZBOT_b03_v1"
def hydro_param(s, ext=".json"): return EXP / s / f"fates_params_HYDRO_SHRUB_b03_v1{ext}"


# ------------------------------------------------------------- physics
def esw(t): t = np.asarray(t, float); return 6.112 * np.exp(17.67 * t / (t + 243.5))
def q_from_e(e_hpa, p_pa): e = 100 * np.asarray(e_hpa, float); return 0.622 * e / (np.asarray(p_pa, float) - 0.378 * e)


def datm_es(tc):
    t = np.asarray(tc, float); x = np.clip(t, -50, 50)
    f = lambda k: k[0] + x * (k[1] + x * (k[2] + x * (k[3] + x * (k[4] + x * (k[5] + x * k[6])))))
    return np.where(t < 0, f(A_I), f(A_W))


def toa(ts_utc, lat, lon):
    """Top-of-atmosphere shortwave (W m-2) at UTC times (Spencer 1971)."""
    doy = ts_utc.dt.dayofyear.to_numpy(float); hr = (ts_utc.dt.hour + ts_utc.dt.minute / 60).to_numpy(float)
    g = 2 * np.pi / 365 * (doy - 1 + (hr - 12) / 24)
    eot = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    dec = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
           - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    e0 = 1.000110 + 0.034221 * np.cos(g) + 0.001280 * np.sin(g) + 0.000719 * np.cos(2 * g) + 0.000077 * np.sin(2 * g)
    ha = np.radians((hr * 60 + eot + 4 * lon) / 4 - 180)
    phi = np.radians(lat)
    cz = np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(ha)
    return 1361 * e0 * np.clip(cz, 0, None)


def centroid_min(minute, w):
    th = 2 * np.pi * np.asarray(minute, float) / 1440
    return (np.degrees(np.arctan2((w * np.sin(th)).sum(), (w * np.cos(th)).sum())) % 360) * 4


def qc(s, d, step):
    """Full-record physical QC of one forcing frame. Returns (summary, holds)."""
    first, last, _ = SITES[s]; tz, lat, lon, elev = CLOCK[s]; holds = []
    t = d["_t"]
    exp = pd.date_range(f"{first}-01-01", f"{last + 1}-01-01", freq=f"{step}min", inclusive="left")
    exp = exp[~((exp.month == 2) & (exp.day == 29))]
    if len(t) != len(exp) or not np.array_equal(t.to_numpy(), exp.to_numpy()): holds.append("timeline is not complete NOLEAP")
    nan = {k: int(d[k].isna().sum()) for k in MET}
    if any(nan.values()): holds.append(f"NaN {nan}")
    rng = {}
    for k, (lo, hi) in HARD.items():
        bad = int(((d[k] < lo) | (d[k] > hi)).sum()); rng[k] = [float(d[k].min()), float(d[k].max())]
        if bad: holds.append(f"{k} {bad} rows outside [{lo},{hi}]")
    pmax = 300 / (step * 60); rng["PRECTmms"] = [float(d.PRECTmms.min()), float(d.PRECTmms.max())]
    if ((d.PRECTmms < 0) | (d.PRECTmms > pmax)).any(): holds.append("PRECTmms outside [0, 300 mm/step]")
    TC = d.TBOT.to_numpy(float) - 273.15; P = d.PSRF.to_numpy(float); Q = d.QBOT.to_numpy(float)
    if (~np.isfinite(Q) | (Q <= 0)).any(): holds.append(f"QBOT <= 0 in {int((Q <= 0).sum())} rows")
    e = Q * P / (0.622 + 0.378 * Q) / 100                    # hPa, exact inverse of q_from_e
    o = {"rows": len(d), "step_min": step, "years": [first, last], "range": rng, "QBOT_min": float(np.nanmin(Q))}
    if "TA_USE" in d and "VPD_USE" in d:
        ta = d.TA_USE.to_numpy(float); vpd = d.VPD_USE.to_numpy(float)
        o["TBOT_neq_TA_USE"] = int((np.abs(TC - ta) > 1e-6).sum())
        qq = q_from_e(esw(ta) - vpd, P)
        o["QBOT_closure_fail"] = int((~np.isclose(qq, Q, rtol=1e-5, atol=1e-8)).sum())
        o["e_le_0_from_TA_VPD"] = int((esw(ta) - vpd <= 0).sum())
        if o["e_le_0_from_TA_VPD"]: holds.append(f"e = esw(TA_USE) - VPD_USE <= 0 in {o['e_le_0_from_TA_VPD']} rows")
        o["VPD_lt_0"] = int((vpd < 0).sum())
    es_d = datm_es(TC)
    rh = 100 * e / es_d
    o["DATM_RH_gt100_clamped"] = int((rh > 100.0001).sum()); o["DATM_RH_max"] = float(np.nanmax(rh))
    o["RH_lt1pct"] = int((rh < 1).sum()); o["RH_lt5pct"] = int((rh < 5).sum()); o["RH_min"] = float(np.nanmin(rh))
    pexp = 101325 * (1 - 2.25577e-5 * elev) ** 5.25588
    o["PSRF_median_over_barometric"] = round(float(np.median(P) / pexp), 4)
    if abs(o["PSRF_median_over_barometric"] - 1) > 0.06: holds.append(f"PSRF median / barometric({elev} m) = {o['PSRF_median_over_barometric']}")
    tu = t + pd.Timedelta(minutes=step / 2) - pd.Timedelta(hours=tz)       # interval midpoint in UTC
    tu = pd.Series(tu).reset_index(drop=True)
    S0 = toa(tu, lat, lon); F = d.FSDS.to_numpy(float)
    mins = (tu.dt.hour * 60 + tu.dt.minute).to_numpy()
    cf = pd.Series(F).groupby(mins).mean(); ct = pd.Series(S0).groupby(mins).mean()
    lag = (centroid_min(cf.index, cf.to_numpy()) - centroid_min(ct.index, ct.to_numpy()) + 720) % 1440 - 720
    o["FSDS_minus_TOA_diurnal_centroid_lag_min"] = round(float(lag), 1)
    if abs(lag) > 45: holds.append(f"FSDS diurnal centroid lags TOA by {lag:.0f} min (clock?)")
    o["FSDS_gt_TOA_plus50_share"] = round(float(((F > S0 + 50) & (F > 20)).mean()), 5)
    o["FSDS_night_gt20_share"] = round(float(((S0 <= 0) & (F > 20)).mean()), 5)
    o["clearness_FSDS_over_TOA_mean"] = round(float(F.sum() / S0.sum()), 3)
    eps = d.FLDS.to_numpy(float) / (5.670374e-8 * d.TBOT.to_numpy(float) ** 4)
    o["FLDS_emissivity_p001_p999"] = [round(float(np.quantile(eps, .001)), 3), round(float(np.quantile(eps, .999)), 3)]
    yr = t.dt.year
    ann = pd.DataFrame({"y": yr, "T": TC, "P": d.PRECTmms * step * 60, "SW": F}).groupby("y").agg(T=("T", "mean"), P=("P", "sum"), SW=("SW", "mean"))
    o["annual_T_C_min_max"] = [round(float(ann["T"].min()), 2), round(float(ann["T"].max()), 2)]
    o["annual_P_mm_min_max"] = [round(float(ann["P"].min()), 1), round(float(ann["P"].max()), 1)]
    o["annual_SW_Wm2_min_max"] = [round(float(ann.SW.min()), 1), round(float(ann.SW.max()), 1)]
    o["annual_table"] = {int(k): [round(float(v["T"]), 2), round(float(v["P"]), 0), round(float(v["SW"]), 1)] for k, v in ann.iterrows()}
    return o, holds


# ------------------------------------------------------------- forcing frames
def resolve_shadow(s):
    pats, want = SHADOW[s]
    if pats is None: return None
    c = sorted({x for p in pats for x in glob.glob(str(ST / p))})
    if len(c) != 1: fail(f"{s}: research shadow not unique: {c}")
    p = Path(c[0]); h = digest(p)
    if want and h != want: fail(f"{s}: shadow sha {h} != pinned {want}")
    return p, h


def read_frame(p, s):
    hdr = list(pd.read_csv(p, nrows=0).columns)
    if not set(["time", *MET]) <= set(hdr): fail(f"{s}: shadow columns {hdr}")
    d = pd.read_csv(p, usecols=[c for c in COLS if c in hdr], low_memory=False, float_precision="round_trip")
    d["_t"] = pd.to_datetime(d["time"].astype(str).str.replace("T", " "), format="mixed")
    for k in MET: d[k] = pd.to_numeric(d[k], errors="coerce")
    return d


def me2_build():
    """US-Me2 2002-2022 forcing frame from FULLSET_HH (qcv5 conversion) + CL05/CL07 humidity ledger (365 rows)."""
    man = json.loads(S07.read_text()); spec = [x for x in man["sites"] if x["site"] == "US-Me2"]
    if len(spec) != 1: fail("US-Me2 not once in Stage07 manifest")
    fp = Path(spec[0]["primary"])
    if digest(fp) != ME2_FULLSET_SHA: fail("US-Me2 FULLSET sha differs")
    use = ["TIMESTAMP_START", "TA_F", "VPD_F", "VPD_F_QC", "PA_F", "SW_IN_F", "LW_IN_F", "WS_F", "P_F"]
    f = pd.read_csv(fp, usecols=use, dtype={"TIMESTAMP_START": str}, na_values=[-9999, "-9999"], low_memory=False)
    f["row"] = np.arange(len(f)) + 2
    f["_t"] = pd.to_datetime(f.TIMESTAMP_START, format="%Y%m%d%H%M")
    f = f[(f._t.dt.year >= 2002) & (f._t.dt.year <= 2022) & ~((f._t.dt.month == 2) & (f._t.dt.day == 29))].reset_index(drop=True)
    if len(f) != 21 * 17520: fail(f"US-Me2 NOLEAP rows {len(f)}")
    if f[use[1:]].isna().any().any(): fail("US-Me2 FULLSET _F variables have NaN")
    for k, (lo, hi) in {"TA_F": (-80, 65), "VPD_F": (-0.1, 125), "PA_F": (50, 110), "SW_IN_F": (-5, 1600), "LW_IN_F": (60, 800),
                        "WS_F": (-0.1, 75), "P_F": (-0.001, 300)}.items():
        if not f[k].between(lo, hi).all(): fail(f"US-Me2 FULLSET {k} outside qcv5 HARD range")
    L5 = pd.read_csv(ME2_CL05, dtype={"TIMESTAMP_START": str}); L7 = pd.read_csv(ME2_CL07, dtype={"TIMESTAMP_START": str})
    c5 = L5.decision.value_counts().to_dict()
    if len(L5) != 365 or c5 != {"HOLD": 243, "EMP_LOYO": 122}: fail(f"CL05 ledger {len(L5)} {c5}")
    hold = set(L5.loc[L5.decision == "HOLD", "TIMESTAMP_START"])
    if len(L7) != 243 or set(L7.TIMESTAMP_START) != hold: fail("CL07 ledger is not exactly the 243 CL05 HOLD rows")
    if not L7.decision.str.match(r"^(ERA_E_CAL_M[12]|EMP_LOYO_LOW_CONFIDENCE)").all(): fail("CL07 ledger still has HOLD/unknown decisions")
    led = pd.concat([L5.loc[L5.decision == "EMP_LOYO"], L7], ignore_index=True)
    led = led.assign(ledger=np.where(led.index < 122, "CL05", "CL07"))
    pos = pd.Series(np.arange(len(f)), index=f.TIMESTAMP_START)
    if not led.TIMESTAMP_START.isin(pos.index).all() or led.TIMESTAMP_START.duplicated().any(): fail("ledger times not in FULLSET")
    i = pos[led.TIMESTAMP_START].to_numpy()
    T = f.TA_F.to_numpy(float); V = f.VPD_F.to_numpy(float).copy()
    if not (np.allclose(T[i], led.TA_F, atol=1e-6) and np.allclose(V[i], led.VPD_F, atol=1e-6)
            and (f.row.to_numpy()[i] == led.source_row.to_numpy()).all()):
        fail("ledger TA_F/VPD_F/source_row differ from FULLSET")
    if (f.VPD_F_QC.to_numpy()[i] == 0).any(): fail("ledger would change a measured VPD_F_QC=0 row")
    enew = led.e_proposed.to_numpy(float)
    if not (np.isfinite(enew).all() and (enew > 0).all()): fail("ledger e_proposed not finite/positive")
    if (enew > datm_es(T[i]) * (1 + 1e-9)).any(): fail("ledger e above DATM saturation")
    vnew = esw(T[i]) - enew
    if not np.allclose(vnew, led.VPD_proposed, atol=1e-6): fail("ledger VPD_proposed != esw(TA_F) - e_proposed")
    V[i] = vnew
    psrf = f.PA_F.to_numpy(float) * 1000
    d = pd.DataFrame({"time": f._t.dt.strftime("%Y-%m-%d %H:%M:%S"), "TBOT": T + 273.15, "QBOT": q_from_e(esw(T) - V, psrf), "PSRF": psrf,
                      "FSDS": f.SW_IN_F.clip(lower=0), "FLDS": f.LW_IN_F, "WIND": f.WS_F.clip(lower=0),
                      "PRECTmms": f.P_F.clip(lower=0) / 1800.0, "TA_USE": T, "VPD_USE": V})
    prov = led[["TIMESTAMP_START", "source_row", "ledger", "decision", "TA_F", "VPD_F", "VPD_F_QC", "e_proposed"]].assign(VPD_new=vnew)
    info = {"fullset": str(fp), "fullset_sha256": ME2_FULLSET_SHA, "cl05": str(ME2_CL05), "cl05_sha256": digest(ME2_CL05),
            "cl07": str(ME2_CL07), "cl07_sha256": digest(ME2_CL07), "changed_rows": int(len(led)),
            "decisions": led.decision.value_counts().to_dict(), "VPD_new_lt_0": int((vnew < 0).sum())}
    return d, prov, info


def me2_frame(write):
    d, prov, info = me2_build()
    csvp = ME2_OUT / ME2_CSV; rec = ME2_OUT / "RECEIPT.json"
    if csvp.is_file() and rec.is_file():
        r = json.loads(rec.read_text())
        if r.get("csv_sha256") != digest(csvp): fail("US-Me2 B3 shadow differs from its receipt")
        old = pd.read_csv(csvp, float_precision="round_trip")
        if len(old) != len(d) or not np.allclose(old[list(MET)].to_numpy(float), d[list(MET)].to_numpy(float), rtol=1e-12, atol=0):
            fail("existing US-Me2 B3 shadow differs from a fresh rebuild; move it aside")
        info.update(path=str(csvp), sha256=r["csv_sha256"], status="REUSED")
    elif write:
        if ME2_OUT.exists(): fail(f"partial {ME2_OUT}; move it aside")
        tmp = ME2_OUT.with_name(ME2_OUT.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
        d.to_csv(tmp / ME2_CSV, index=False, float_format="%.17g"); prov.to_csv(tmp / "US-Me2_365_humidity_ledger_applied.csv", index=False)
        back = pd.read_csv(tmp / ME2_CSV, float_precision="round_trip")
        if not np.array_equal(back[list(MET)].to_numpy(float), d[list(MET)].to_numpy(float)): fail("US-Me2 shadow readback differs")
        h = digest(tmp / ME2_CSV)
        (tmp / "RECEIPT.json").write_text(json.dumps({**info, "csv": ME2_CSV, "csv_sha256": h, "rows": len(d), "years": [2002, 2022],
            "conversion": "qcv5: TBOT=TA_F+273.15, PSRF=PA_F*1000, QBOT=0.622e/(p-0.378e) Magnus, FSDS/WIND clip>=0, PRECT=P_F/1800",
            "user_decision": "2026-10-29 Me2 2002-2022 all years, AD400 FIXNC research forcing", "created_utc": utc()}, indent=2) + "\n")
        tmp.rename(ME2_OUT)
        info.update(path=str(csvp), sha256=h, status="WRITTEN")
    else:
        info.update(path=str(csvp), status="IN_MEMORY_CHECK_ONLY")
    d["_t"] = pd.to_datetime(d.time); return d, info


def frame(s, write=False):
    if s == "US-Me2":
        d, info = me2_frame(write)
    else:
        p, h = resolve_shadow(s); d = read_frame(p, s)
        info = {"path": str(p), "sha256": h,
                "markers": sorted(x.name for x in p.parent.iterdir() if x.is_file() and re.match(r"(INCOMPLETE|NOT_APPROVED)", x.name))}
    step = SITES[s][2]
    return d, step, info


# ------------------------------------------------------------- clock / height / soil / pft
def bif_check(s, man):
    tz, lat, lon, elev = CLOCK[s]
    if s == "US-Me2": return "US-Me2 BADM UTC-8 (no FULLSET BIF; CL clock evidence)"
    spec = [x for x in man["sites"] if x["site"] == s][0]
    bif = sorted(Path(spec["primary"]).parent.glob("*_BIF_*.csv"))
    if len(bif) != 1: fail(f"{s}: BIF not unique")
    b = pd.read_csv(bif[0], keep_default_na=False)
    got = {float(x) for x in b.loc[b.VARIABLE == "UTC_OFFSET", "DATAVALUE"]}
    if got != {float(tz)}: fail(f"{s}: BIF UTC_OFFSET {got} != {tz}")
    la = [float(x) for x in b.loc[b.VARIABLE == "LOCATION_LAT", "DATAVALUE"]]
    if not any(abs(x - lat) < 0.002 for x in la): fail(f"{s}: BIF LAT {la}")
    return f"BIF {bif[0].name} UTC_OFFSET {tz}"


def height_check(s, rows):
    z, var, rule = ZBOT[s]
    hs = {float(r["Height"]) for r in rows if r["Variable"] == var and (r.get("Height") or "").strip()}
    if z not in hs: fail(f"{s}: BASE {var} heights {hs} do not contain ZBOT {z}")
    return z, f"BASE {var} {z:g} m; {rule}"


def soil_rows():
    if digest(SOIL_WIDE) != SOIL_WIDE_SHA: fail("soil wide table sha differs")
    out = {}
    for r in csv.DictReader(SOIL_WIDE.open(encoding="utf-8-sig")):
        if r["site"] in SITES:
            sa = [float(r[f"PCT_SAND_L{i}"]) for i in range(1, 11)]; cl = [float(r[f"PCT_CLAY_L{i}"]) for i in range(1, 11)]
            out[r["site"]] = {"sand": sa, "clay": cl, "tier": r.get("tier", "")}
    for s in SITES:
        x = out.get(s)
        if not x: fail(f"{s}: no soil row")
        if not all(a > 0 and c >= 0 and a + c > 0 and a + c <= 100.0001 for a, c in zip(x["sand"], x["clay"])): fail(f"{s}: invalid/zero soil layer")
        m = (round(sum(x["sand"][:5]) / 5, 1), round(sum(x["clay"][:5]) / 5, 1))
        if abs(m[0] - SOIL030[s][0]) > .11 or abs(m[1] - SOIL030[s][1]) > .11: fail(f"{s}: soil L1-L5 mean {m} != register {SOIL030[s]}")
    return out


def pft_check(s):
    host, prof, fates = PFT[s]
    if not math.isclose(sum(host.values()), 100, abs_tol=1e-6): fail(f"{s}: host sum")
    M = MAPS[prof]; got = {}
    for h, v in host.items():
        if h == 0: continue
        for j in np.flatnonzero(M[h - 1]): got[j + 1] = got.get(j + 1, 0) + v * M[h - 1, j]
    if {k: round(v, 6) for k, v in got.items()} != {k: float(v) for k, v in fates.items()}: fail(f"{s}: host x {prof} = {got} != register {fates}")
    if len(got) > 4: fail(f"{s}: > 4 live FATES PFTs")
    if prof == "DEFAULT14" and any(host.get(i, 0) > 0 for i in (10, 11)): fail(f"{s}: DEFAULT14 uses host 10/11")
    return {FATES_NAMES[k - 1]: v for k, v in got.items()}


def original_surface(s):
    c = sorted(x for x in (B / "sites/MY_EC_SITE" / s / "subset_data_batch03_surf2000").glob("surfdata*.nc") if x.is_file() and not x.is_symlink())
    if len(c) != 1: fail(f"{s}: Stage03 surface not unique {c}")
    return c[0]


def verify_surface(s, p, soil):
    from netCDF4 import Dataset
    host = PFT[s][0]
    with Dataset(p) as ds:
        for k, tgt in (("PCT_NATVEG", 100.), ("PCT_CROP", 0.)):
            if abs(float(np.ravel(ds[k][:])[0]) - tgt) > 1e-4: fail(f"{s}: {k}")
        for k in LAND_OTHER:
            if k in ds.variables and not np.allclose(np.ma.filled(ds[k][:], np.nan), 0, atol=1e-4): fail(f"{s}: {k} != 0")
        if not np.allclose(np.ma.filled(ds["PCT_NAT_PFT"][:], np.nan).ravel(), [host.get(i, 0.) for i in range(15)], atol=1e-4): fail(f"{s}: PCT_NAT_PFT")
        for k, v in (("PCT_SAND", soil["sand"]), ("PCT_CLAY", soil["clay"])):
            if not np.allclose(np.ma.filled(ds[k][:], np.nan).ravel(), v, atol=1e-4): fail(f"{s}: {k}")
        return float(np.ravel(ds["LATIXY"][:])[0]), float(np.ravel(ds["LONGXY"][:])[0]) % 360


def build_surface(s, soil):
    from netCDF4 import Dataset
    old = original_surface(s); dst = surface(s); rec = dst.with_suffix(".json")
    if dst.is_file() and rec.is_file():
        if json.loads(rec.read_text()).get("surface_sha256") != digest(dst): fail(f"{s}: surface != receipt")
        lat, lon = verify_surface(s, dst, soil); print(f"  {s}: surface reused {dst}", flush=True)
        return {"path": dst, "sha256": digest(dst), "lat": lat, "lon": lon}
    if dst.exists() or rec.exists(): fail(f"{s}: partial surface {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True); osha = digest(old)
    fd, tmp = tempfile.mkstemp(suffix=".nc", dir=dst.parent, prefix=f".{s}."); os.close(fd); tmp = Path(tmp)
    try:
        shutil.copyfile(old, tmp)
        with Dataset(tmp, "r+") as ds:
            ds["PCT_NATVEG"][:] = 100.; ds["PCT_CROP"][:] = 0.
            for k in LAND_OTHER:
                if k in ds.variables: ds[k][:] = 0.
            v = ds["PCT_NAT_PFT"]; a = np.zeros(v.shape); ax = v.dimensions.index("natpft")
            for i, val in PFT[s][0].items():
                sl = [0] * a.ndim; sl[ax] = i; a[tuple(sl)] = val
            v[:] = a
            for k, vals in (("PCT_SAND", soil["sand"]), ("PCT_CLAY", soil["clay"])):
                if ds[k].size != 10: fail(f"{s}: {k} not 10 layers")
                ds[k][:] = np.asarray(vals).reshape(ds[k].shape)
            ds.AMF_B03_FIXNC = "NATVEG100_CROP0; register host PCT_NAT_PFT; AmeriFlux50 Stage01 CLM10 sand/clay; ORGANIC unchanged"
            ds.AMF_B03_PFT_profile = PFT[s][1]
        lat, lon = verify_surface(s, tmp, soil)
        if digest(old) != osha: fail(f"{s}: original surface mutated")
        os.link(tmp, dst)
        with rec.open("x") as f:
            json.dump({"site": s, "source_surface": str(old), "source_sha256": osha, "surface": str(dst), "surface_sha256": digest(dst),
                       "host_PCT_NAT_PFT": PFT[s][0], "fates_profile": PFT[s][1], "fates_natland": PFT[s][2], "soil": soil,
                       "ORGANIC": "unchanged from Stage03 surface", "created_utc": utc()}, f, indent=2)
        print(f"  {s}: surface built {dst}", flush=True)
        return {"path": dst, "sha256": digest(dst), "lat": lat, "lon": lon}
    finally:
        tmp.unlink(missing_ok=True)


def _json_map(obj):
    p = obj["parameters"]; names = [str(x).strip() for x in p["fates_pftname"]["data"]]
    m = np.asarray(p["fates_hlm_pft_map"]["data"], dtype=float)
    if names != FATES_NAMES or m.shape != (14, 14): fail(f"FATES param names/map shape {m.shape}")
    return m


def build_hydro_param(s, base):
    base = Path(base)
    if base.suffix.lower() != ".json": fail("template FATES paramfile is not JSON")
    p = hydro_param(s); rec = Path(str(p) + ".receipt.json")
    def verify(q):
        a, b = json.loads(Path(q).read_text()), json.loads(base.read_text())
        if not np.allclose(_json_map(a), HYDRO_SHRUB): fail(f"{q}: HYDRO_SHRUB map wrong")
        pa, pb = dict(a["parameters"]), dict(b["parameters"]); pa.pop("fates_hlm_pft_map"); pb.pop("fates_hlm_pft_map")
        if pa != pb or {k: v for k, v in a.items() if k != "parameters"} != {k: v for k, v in b.items() if k != "parameters"}:
            fail(f"{q}: parameters other than fates_hlm_pft_map differ")
    if p.is_file() and rec.is_file():
        r = json.loads(rec.read_text())
        if r.get("sha256") != digest(p) or r.get("base_sha256") != digest(base): fail(f"{s}: HYDRO param receipt mismatch")
        verify(p); print(f"  {s}: HYDRO_SHRUB param reused {p}", flush=True); return p
    if p.exists(): fail(f"{s}: partial HYDRO param")
    p.parent.mkdir(parents=True, exist_ok=True); obj = json.loads(base.read_text())
    if not np.allclose(_json_map(obj), DEFAULT14): fail("template FATES map is not DEFAULT14")
    obj["parameters"]["fates_hlm_pft_map"]["data"] = HYDRO_SHRUB.tolist()
    tmp = Path(str(p) + ".partial"); tmp.write_text(json.dumps(obj, indent=2) + "\n"); verify(tmp); tmp.rename(p)
    rec.write_text(json.dumps({"site": s, "path": str(p), "sha256": digest(p), "base": str(base), "base_sha256": digest(base),
                               "profile": "HYDRO_SHRUB", "changed_row_host": 10, "to": "broadleaf_hydrodecid_extratrop_shrub", "created_utc": utc()}, indent=2) + "\n")
    print(f"  {s}: HYDRO_SHRUB param built {p}", flush=True)
    return p


def co2_table():
    vals = {}
    for ln in CO2_CSV.read_text().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) >= 2 and p[0].isdigit(): vals[int(p[0])] = float(p[1])
    if any(SITES[s][0] not in vals for s in SITES): fail("CO2 table lacks a first forcing year")
    return vals, f"{CO2_CSV} sha256={digest(CO2_CSV)}"


# ------------------------------------------------------------- forcing NC
def build_forcing(s, d, step, srf, z, zsrc, src):
    from netCDF4 import Dataset
    first, last, _ = SITES[s]; tz = CLOCK[s][0]; dd = forcing_dir(s); man = dd / "manifest.json"
    if man.is_file():
        m = json.loads(man.read_text())
        if (m.get("complete") and m.get("source_sha256") == src["sha256"] and m.get("zbot_m") == z and m.get("utc_offset_h") == tz
                and all(digest(x["path"]) == x["sha256"] for x in m["files"])):
            print(f"  {s}: forcing reused {dd}", flush=True); return m
        fail(f"{s}: existing forcing {dd} differs; move it aside")
    if dd.exists(): fail(f"{s}: partial forcing {dd}")
    n = 525600 // step; shift = int(round(-tz * 60 / step))
    if not (0 < shift < n): fail(f"{s}: shift {shift}")
    yrs = d._t.dt.year.to_numpy(); arr = {y: {k: d[k].to_numpy(float)[yrs == y] for k in MET} for y in range(first, last + 1)}
    if any(len(arr[y]["TBOT"]) != n for y in arr): fail(f"{s}: a year is not {n} records")
    tmp = dd.with_name(dd.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True); out = []
    for y in range(first, last + 1):
        prev = last if y == first else y - 1; q = tmp / f"{y}.nc"
        with Dataset(q, "w", format="NETCDF4_CLASSIC") as ds:
            ds.createDimension("time", n); ds.createDimension("lat", 1); ds.createDimension("lon", 1)
            t = ds.createVariable("time", "f8", ("time",)); t.units = f"days since {y}-01-01 00:00:00"; t.calendar = "noleap"
            t.long_name = f"UTC interval midpoint ({step} min); source local standard time shifted by {-tz} h"
            t[:] = np.arange(n) * step / 1440.0 + step / 2880.0
            for k, dims, val in (("lat", ("lat",), srf["lat"]), ("lon", ("lon",), srf["lon"]), ("LATIXY", ("lat", "lon"), srf["lat"]), ("LONGXY", ("lat", "lon"), srf["lon"])):
                v = ds.createVariable(k, "f8", dims); v[:] = val
            for k in MET:
                v = ds.createVariable(k, "f8", ("time", "lat", "lon"), zlib=True, complevel=2); v.units = UNITS[k]
                v[:] = np.concatenate([arr[prev][k][n - shift:], arr[y][k][:n - shift]]).reshape(n, 1, 1)
            v = ds.createVariable("ZBOT", "f8", ("time", "lat", "lon"), zlib=True, complevel=2); v.units = "m"; v.long_name = "static: " + zsrc
            v[:] = np.full((n, 1, 1), z)
            for k, val in (("site_id", s), ("utc_offset_hours", tz), ("zbot_source", zsrc), ("source_csv", src["path"]), ("source_sha256", src["sha256"]),
                           ("utc_year_start_policy", f"first {shift} records from forcing year {prev} (cyclic spin-up)"),
                           ("stage", "AmeriFlux Batch03 B3_01 direct AD400 forcing v1")):
                ds.setncattr(k, val)
        with Dataset(q) as ds:
            for k in MET:
                a = np.asarray(ds.variables[k][:], float).ravel()
                if not (np.array_equal(a[shift:], arr[y][k][:n - shift]) and np.array_equal(a[:shift], arr[prev][k][n - shift:])): fail(f"{s}: readback {y} {k}")
        out.append({"year": y, "path": str(dd / q.name), "sha256": digest(q)})
    m = {"site": s, "complete": True, "step_minutes": step, "records_per_year": n, "shift_records": shift, "utc_offset_h": tz,
         "zbot_m": z, "zbot_source": zsrc, "years": [first, last], "source": src["path"], "source_sha256": src["sha256"], "files": out, "created_utc": utc()}
    (tmp / "manifest.json").write_text(json.dumps(m, indent=2) + "\n"); tmp.rename(dd)
    print(f"  {s}: forcing built {len(out)} y step={step} shift={shift} ZBOT={z} -> {dd}", flush=True)
    return m


# ------------------------------------------------------------- template / case
def template_info():
    for k, want in (("BUILD_COMPLETE", "TRUE"), ("DATM_MODE", "1PT"), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48")):
        if xq(TEMPLATE, k).upper() != want: fail(f"template {k} != {want}")
    exe = Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe"
    if not exe.is_file(): fail("template executable missing " + str(exe))
    lnd = (TEMPLATE / "CaseDocs/lnd_in").read_text()
    for k, v in FATES_FLAGS.items():
        if nml_get(lnd, k) != v: fail(f"template lnd_in {k}={nml_get(lnd, k)}")
    if nml_get(lnd, "spinup_state") != "2": fail("template is not an AD case")
    pf = Path(nml_get(lnd, "fates_paramfile") or "")
    if not pf.is_file() or digest(pf) != TEMPLATE_PARAM_SHA: fail("template fates_paramfile missing or sha differs")
    if not np.allclose(_json_map(json.loads(pf.read_text())), DEFAULT14): fail("template FATES map is not DEFAULT14")
    for f in ("user_nl_clm", "user_nl_datm_streams", "LockedFiles/env_case.xml"):
        if not (TEMPLATE / f).is_file(): fail("template missing " + f)
    for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"):
        if not (OVERLAY / f).is_file(): fail("overlay missing " + f)
    cs = (TEMPLATE / "CaseStatus").read_text(errors="replace") if (TEMPLATE / "CaseStatus").is_file() else ""
    if not re.search(r"case\.run success", cs): fail("template has no successful case.run")
    return {"exe": exe, "exe_sha256": digest(exe), "paramfile": pf, "param_sha256": digest(pf)}


def stream_text(files, first, last):
    t = (TEMPLATE / "user_nl_datm_streams").read_text()
    rex = re.compile(r"(?m)^[ \t]*([A-Za-z][\w.-]*):([A-Za-z_]\w*)[ \t]*=")
    starts = list(rex.finditer(t)); found = {}
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        found.setdefault(m.group(1) + ":" + m.group(2), []).append((m.start(), end))
    pre = "CLM_USRDAT.UNSET:"
    repl = {"year_first": str(first), "year_last": str(last), "year_align": str(first), "offset": "0", "taxmode": "cycle",
            "tintalgo": "linear", "mapalgo": "none", "meshfile": "none", "datafiles": ",".join(str(p) for p in files)}
    for k in (*repl, "datavars"):
        c = len(found.get(pre + k, []))
        if c != 1 and not (k == "offset" and c == 0): fail(f"template stream key {k} count {c}")
    subs = [(found[pre + k][0][0], found[pre + k][0][1], f"{pre}{k} = {v}\n") for k, v in repl.items() if found.get(pre + k)]
    for a, b, v in sorted(subs, reverse=True): t = t[:a] + v + t[b:]
    if not found.get(pre + "offset"): t = t.rstrip() + f"\n{pre}offset = 0\n"
    if "CA-Ca3" in t: fail("template site path leaked into DATM streams")
    return t


def clm_text(s, param):
    t = (TEMPLATE / "user_nl_clm").read_text()
    if nml_get(t, "reseed_dead_plants") is not None: fail("template user_nl_clm has reseed_dead_plants")
    t = nml_del(t, "finidat")
    for k, v in {"fsurdat": f"'{surface(s)}'", **FATES_FLAGS, "spinup_state": "2", "fates_paramfile": f"'{param}'"}.items():
        t = nml_set(t, k, v)
    if "CA-Ca3" in t: fail("template site path leaked into user_nl_clm")
    return t


def xml_settings(s, srf, co2):
    first, last, _ = SITES[s]
    return {"RUN_TYPE": "startup", "RUN_STARTDATE": f"{first:04d}-01-01", "CONTINUE_RUN": "FALSE", "CLM_FORCE_COLDSTART": "on",
            "CLM_ACCELERATED_SPINUP": "on", "STOP_OPTION": "nyears", "STOP_N": str(SEG_YEARS), "REST_OPTION": "nyears", "REST_N": str(SEG_YEARS),
            "RESUBMIT": str(SEGMENTS - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE", "DOUT_S": "TRUE",
            "DATM_YR_START": str(first), "DATM_YR_END": str(last), "DATM_YR_ALIGN": str(first),
            "CLM_CO2_TYPE": "constant", "DATM_CO2_TSERIES": "none", "CCSM_CO2_PPMV": f"{co2:.2f}",
            "PTS_LAT": f"{srf['lat']:.6f}", "PTS_LON": f"{srf['lon']:.6f}", "PTS_DOMAINFILE": "UNSET",
            "RUNDIR": str(run_dir(s)), "DOUT_S_ROOT": str(arch_dir(s))}


def canon(e): return (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(canon(k) for k in e))


def validate_case(s, srf, files, param, co2, settings):
    case = case_dir(s); first, last, _ = SITES[s]
    for k, v in settings.items():
        got = xq(case, k)
        if k in ("PTS_LAT", "PTS_LON", "CCSM_CO2_PPMV"):
            if abs(float(got) - float(v)) > 1e-5: fail(f"{s}: XML {k}={got}")
        elif got.lower() != v.lower(): fail(f"{s}: XML {k}={got} expected {v}")
    if Path(xq(case, "EXEROOT")).resolve() != Path(xq(TEMPLATE, "EXEROOT")).resolve(): fail(s + ": EXEROOT differs")
    doc, run = case / "CaseDocs/lnd_in", run_dir(s) / "lnd_in"
    if not doc.is_file() or not run.is_file() or digest(doc) != digest(run): fail(s + ": lnd_in CaseDocs != RUNDIR")
    t = doc.read_text()
    for k, v in {**FATES_FLAGS, "spinup_state": "2", "fsurdat": str(surface(s)), "fates_paramfile": str(param)}.items():
        if nml_get(t, k) != v: fail(f"{s}: lnd_in {k}={nml_get(t, k)}")
    if nml_get(t, "finidat") not in (None, "", " "): fail(s + ": finidat set")
    c = nml_get(t, "co2_ppmv")
    if c is not None and abs(float(c) - co2) > 0.03: fail(f"{s}: co2_ppmv {c}")
    new = {e.attrib.get("name"): e for e in ET.parse(case / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    old = {e.attrib.get("name"): e for e in ET.parse(TEMPLATE / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    if set(new) != set(old) or "CLM_USRDAT.UNSET" not in new: fail(s + ": DATM stream set differs")
    for k in set(new) - {"CLM_USRDAT.UNSET"}:
        if canon(new[k]) != canon(old[k]): fail(s + ": ancillary stream changed " + k)
    m = new["CLM_USRDAT.UNSET"]
    for k, v in (("year_first", str(first)), ("year_last", str(last)), ("year_align", str(first)), ("offset", "0"),
                 ("taxmode", "cycle"), ("tintalgo", "linear"), ("mapalgo", "none"), ("meshfile", "none")):
        e = m.find(k)
        if e is None or (e.text or "").strip() != v: fail(f"{s}: stream {k}")
    pairs = {}
    for e in m.find("datavars"):
        a = (e.text or "").split()
        if len(a) != 2 or a[0] in pairs: fail(s + ": datavars malformed")
        pairs[a[0]] = a[1]
    if pairs != FIELDS: fail(f"{s}: datavars {pairs}")
    if [Path((x.text or "").strip()) for x in m.find("datafiles")] != [Path(p) for p in files]: fail(s + ": datafiles differ")
    return {"lnd_in_sha256": digest(doc), "datm_streams_sha256": digest(case / "CaseDocs/datm.streams.xml")}


def queued(n):
    out = cmd(["squeue", "-u", USER, "-h", "-o", "%i|%j|%T"], timeout=45)
    return [r for r in (ln.split("|") for ln in out.splitlines()) if len(r) >= 3 and r[1] in ("run." + n, "st_archive." + n)]


def sacct_name(n):
    out = cmd(["sacct", "-X", "-n", "-P", "-u", USER, "-S", SACCT_START, "--name", f"run.{n},st_archive.{n}",
               "--format=JobIDRaw,JobName%100,State,ExitCode"], timeout=90)
    rows = []
    for ln in out.splitlines():
        p = [x.strip() for x in ln.split("|")]
        if len(p) >= 4 and p[0].isdigit() and p[1] in ("run." + n, "st_archive." + n): rows.append((int(p[0]), p[1], p[2], p[3]))
    return rows


def stack_guard():
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft != resource.RLIM_INFINITY and soft < MIN_STACK_KB * 1024:
        target = hard if hard == resource.RLIM_INFINITY or hard >= MIN_STACK_KB * 1024 else None
        if target is None: fail(f"stack hard limit {hard // 1024} KiB < {MIN_STACK_KB}; run `ulimit -s unlimited` first")
        resource.setrlimit(resource.RLIMIT_STACK, (target, hard)); soft = target
    child = subprocess.run([sys.executable, "-c", "import resource;print(resource.getrlimit(resource.RLIMIT_STACK)[0])"],
                           capture_output=True, text=True, timeout=30, check=True)
    if int(child.stdout.strip()) != soft: fail("child does not inherit the stack limit")
    cfg = cmd(["scontrol", "show", "config"], timeout=45)
    m = re.search(r"(?im)^\s*PropagateResourceLimits\s*=\s*(\S+)", cfg); prop = m.group(1) if m else ""
    if prop.upper() != "ALL" and "STACK" not in prop.upper().split(","): fail("Slurm PropagateResourceLimits lacks STACK: " + repr(prop))
    lab = "unlimited" if soft == resource.RLIM_INFINITY else f"{soft // 1024}KiB"
    print("STACK GUARD PASS soft=", lab, "PropagateResourceLimits=", prop, flush=True)
    return {"soft": lab, "propagate": prop}


# ------------------------------------------------------------- check / prepare / submit
def context(sites, write=False):
    man = json.loads(S07.read_text()); base = {}
    if digest(BASE_HEIGHTS) != BASE_HEIGHTS_SHA: fail("BASE height table sha differs")
    for r in csv.DictReader(BASE_HEIGHTS.open(encoding="utf-8-sig")):
        if r["Site_ID"] in SITES: base.setdefault(r["Site_ID"], []).append(r)
    soil = soil_rows(); co2, co2src = co2_table(); tpl = template_info()
    print(f"TEMPLATE PASS {TEMPLATE.name} exe_sha={tpl['exe_sha256'][:12]} param_sha={tpl['param_sha256'][:12]}", flush=True)
    ctx = {"tpl": tpl, "co2": co2, "co2_src": co2src, "soil": soil, "site": {}}; held = {}
    for s in sites:
        print(f"\n=== {s}", flush=True)
        try:
            clk = bif_check(s, man); z, zsrc = height_check(s, base.get(s, [])); fates = pft_check(s)
            d, step, src = frame(s, write=write)
            o, h = qc(s, d, step)
            surf = original_surface(s)
            for p in (case_dir(s), OUT / name(s), arch_dir(s)):
                if (p.exists() or p.is_symlink()) and not load(ledger(s)): fail(f"unexpected existing {p}")
            print(f"  source  {src.get('path')} sha={str(src.get('sha256'))[:12]} {src.get('status', '')} markers={src.get('markers', [])}", flush=True)
            if s == "US-Me2": print(f"  Me2 ledger {src['decisions']} VPD_new<0={src['VPD_new_lt_0']}", flush=True)
            print(f"  clock   UTC{CLOCK[s][0]:+d} ({clk}) | ZBOT {z} m ({zsrc})", flush=True)
            print(f"  PFT     {PFT[s][1]} host={PFT[s][0]} -> {fates}", flush=True)
            print(f"  soil    {soil[s]['tier']} sand L1-10={soil[s]['sand']} clay={soil[s]['clay']} | orig surface {surf.name}", flush=True)
            print(f"  CO2     {co2[SITES[s][0]]:.2f} ppm ({SITES[s][0]}) | AD400 {SITES[s][0]}->{SITES[s][0] + 400}", flush=True)
            print("  QC      " + json.dumps({k: v for k, v in o.items() if k != "annual_table"}), flush=True)
            print("  ANNUAL  year:[T_C,P_mm,SW] " + json.dumps(o["annual_table"]), flush=True)
            if h: fail("QC HOLD: " + "; ".join(h))
            ctx["site"][s] = {"frame": d, "step": step, "src": src, "z": z, "zsrc": zsrc, "qc": o, "fates": fates}
            print(f"  RESULT  {s} ADMITTED", flush=True)
        except Exception as e:
            held[s] = str(e); print(f"  RESULT  {s} HOLD {e}", flush=True)
    return ctx, held


def prepare_one(s, ctx):
    led = ledger(s)
    if led.exists(): fail(f"{s}: ledger exists ({load(led).get('phase')})")
    for p in (case_dir(s), OUT / name(s), arch_dir(s)):
        if p.exists() or p.is_symlink(): fail(f"{s}: path exists: {p}")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": jobs exist")
    c = ctx["site"][s]; srf = build_surface(s, ctx["soil"][s])
    if abs(srf["lat"] - CLOCK[s][1]) > 0.01 or abs((srf["lon"] - CLOCK[s][2] % 360 + 180) % 360 - 180) > 0.01: fail(f"{s}: surface point != tower")
    fm = build_forcing(s, c["frame"], c["step"], srf, c["z"], c["zsrc"], c["src"])
    param = build_hydro_param(s, ctx["tpl"]["paramfile"]) if PFT[s][1] == "HYDRO_SHRUB" else ctx["tpl"]["paramfile"]
    first, last, _ = SITES[s]; co2 = ctx["co2"][first]; nc = [Path(x["path"]) for x in fm["files"]]
    stream, land, settings = stream_text(nc, first, last), clm_text(s, param), xml_settings(s, srf, co2)
    save(led, {"site": s, "case": str(case_dir(s)), "phase": "PREPARE_ATTEMPTED_UNCERTAIN", "at": utc()})
    case = case_dir(s)
    cmd([CIMESCRIPTS / "create_clone", "--case", case, "--clone", TEMPLATE, "--keepexe"], cwd=CIMESCRIPTS, timeout=420)
    if xq(case, "CASE") != name(s): fail(s + ": clone identity")
    for k, v in settings.items(): xc(case, k, v)
    (case / "user_nl_datm_streams").write_text(stream); (case / "user_nl_clm").write_text(land)
    run_dir(s).mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file(): cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles/env_case.xml"
    if not lock.is_file() or env.read_bytes() != lock.read_bytes(): fail(s + ": env_case lock inconsistent")
    orig = env.read_bytes()
    if Path(xq(case, "COMP_ROOT_DIR_LND")).resolve() != CTSM.resolve(): fail(s + ": land root is not shared CTSM")
    try:
        xc(case, "COMP_ROOT_DIR_LND", str(OVERLAY)); cmd([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
        if env.read_bytes() != orig or lock.read_bytes() != orig: fail(s + ": STOP env_case.xml lock not restored")
    h = validate_case(s, srf, nc, param, co2, settings)
    save(led, {"site": s, "case": str(case), "phase": "CASE_VERIFIED_NOT_SUBMITTED", "name": name(s), "start_year": first,
               "forcing_years": [first, last], "ad400_target_year": first + 400, "surface": str(srf["path"]), "surface_sha256": srf["sha256"],
               "host_PCT_NAT_PFT": PFT[s][0], "fates_profile": PFT[s][1], "fates_natland": c["fates"], "PTS_LAT": srf["lat"], "PTS_LON": srf["lon"],
               "co2_ppmv": co2, "co2_source": ctx["co2_src"], "fates_paramfile": str(param), "fates_paramfile_sha256": digest(param),
               "utc_offset_h": CLOCK[s][0], "zbot_m": c["z"], "zbot_source": c["zsrc"], "forcing_source": c["src"].get("path"),
               "forcing_source_sha256": c["src"].get("sha256"), "forcing_manifest": str(forcing_dir(s) / "manifest.json"),
               "forcing_step_minutes": c["step"], "qc": c["qc"], "executable_sha256": ctx["tpl"]["exe_sha256"], "template": str(TEMPLATE), **h,
               "protocol": "DIRECT_AD400_80x5_RESUBMIT79_NO_AD5_SMOKE", "created_utc": utc()})
    print(f"{s} CASE VERIFIED {name(s)} start={first} CO2={co2:.2f} UTC{CLOCK[s][0]:+d} ZBOT={c['z']} FATES={PFT[s][1]} | NO SLURM", flush=True)


def submit_one(s, stack):
    led = ledger(s); obj = load(led)
    if obj.get("phase") != "CASE_VERIFIED_NOT_SUBMITTED": fail(f"{s}: ledger phase {obj.get('phase')}")
    case = case_dir(s); cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs): fail(s + ": CaseStatus shows a submission")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": jobs exist")
    if digest(case / "CaseDocs/lnd_in") != obj["lnd_in_sha256"] or digest(case / "CaseDocs/datm.streams.xml") != obj["datm_streams_sha256"]:
        fail(s + ": CaseDocs changed after verification")
    if digest(obj["surface"]) != obj["surface_sha256"] or digest(obj["fates_paramfile"]) != obj["fates_paramfile_sha256"]: fail(s + ": inputs changed")
    for k, v in (("RESUBMIT", str(SEGMENTS - 1)), ("STOP_N", "5"), ("CONTINUE_RUN", "false"), ("CLM_ACCELERATED_SPINUP", "on")):
        if xq(case, k).lower() != v.lower(): fail(f"{s}: {k}={xq(case, k)}")
    obj.update(phase="SUBMIT_ATTEMPTED_UNCERTAIN", submit_attempt_utc=utc(), stack=stack); save(led, obj)
    out = cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=650)
    r, a = RUN_RE.search(out), ARCH_RE.search(out)
    if not r or not a: fail(s + ": job IDs not parsed; DO NOT RETRY. " + out[-600:])
    obj.update(phase="AD400_SUBMITTED", first_run_job=r.group(1), first_archive_job=a.group(1), cime_submit_tail=out[-800:]); save(led, obj)
    print(f"{s} AD400 DIRECT SUBMITTED {stamp(obj['start_year'])} -> {stamp(obj['ad400_target_year'])} (80x5) run={r.group(1)} archive={a.group(1)}", flush=True)


def restart_state(p):
    from netCDF4 import Dataset
    with Dataset(str(p)) as ds:
        if "spinup_state" in ds.variables: return int(np.asarray(ds.variables["spinup_state"][:]).ravel()[0])
        if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
    return None


def triplet(s, y):
    f = arch_dir(s) / "rest" / stamp(y); files = {c: f / f"{name(s)}.{c}.r.{stamp(y)}.nc" for c in POINTERS}
    for c, p in files.items():
        if not p.is_file() or p.stat().st_size < 1024: fail(f"{s}: missing {p}")
    return files


def latest(s):
    r = arch_dir(s) / "rest"; n = sorted(x.name for x in r.iterdir() if x.is_dir()) if r.is_dir() else []
    return (n[-1] if n else None), len(n)


def first5_one(s):
    obj = load(ledger(s))
    if obj.get("phase") != "AD400_SUBMITTED": fail(f"{s}: phase {obj.get('phase')}")
    rows = [r for r in sacct_name(name(s)) if r[0] >= int(obj["first_run_job"])]
    bad = [r for r in rows if r[2] not in ("COMPLETED", "RUNNING", "PENDING") or (r[2] == "COMPLETED" and r[3] != "0:0")]
    if bad: fail(f"{s}: failed jobs {bad[:4]}")
    y = obj["start_year"] + SEG_YEARS; st = restart_state(triplet(s, y)["clm2"])
    if st != 2: fail(f"{s}: first-segment spinup_state={st}")
    l, n = latest(s)
    return {"case": name(s), "final": stamp(y), "spinup_state": st, "latest": l, "rest_dirs": n,
            "runs": sum(r[1].startswith("run.") and r[2] == "COMPLETED" for r in rows)}


def ad400_one(s):
    obj = load(ledger(s))
    if obj.get("phase") != "AD400_SUBMITTED": fail(f"{s}: phase {obj.get('phase')}")
    n = name(s)
    if queued(n): fail(s + ": jobs still queued")
    rows = [r for r in sacct_name(n) if r[0] >= int(obj["first_run_job"])]
    bad = [r for r in rows if (r[2], r[3]) != ("COMPLETED", "0:0")]
    if bad: fail(f"{s}: non-COMPLETED jobs {bad[:4]}")
    runs = sum(r[1].startswith("run.") for r in rows); arcs = sum(r[1].startswith("st_archive.") for r in rows)
    if runs < SEGMENTS or arcs < SEGMENTS: fail(f"{s}: {runs} run / {arcs} archive; need {SEGMENTS}")
    if xq(case_dir(s), "RESUBMIT") != "0": fail(s + ": RESUBMIT not exhausted")
    y = obj["ad400_target_year"]; l, nd = latest(s)
    if l != stamp(y): fail(f"{s}: latest restart {l}, expected {stamp(y)}")
    files = triplet(s, y); st = restart_state(files["clm2"])
    if st != 2: fail(f"{s}: final spinup_state={st}")
    return {"case": n, "runs": runs, "archives": arcs, "final": stamp(y), "spinup_state": st, "rest_dirs": nd}


def status(sites):
    for s in sites:
        o = load(ledger(s))
        try: q = "; ".join("|".join(r) for r in queued(name(s))) or "-"
        except Exception: q = "scheduler unavailable"
        print(f"{s:7} PHASE={o.get('phase', '-')} run={o.get('first_run_job', '-')} latest={latest(s)[0]} QUEUE={q}")


def table(title, sites, fn):
    ok, held = {}, {}; print(title)
    for s in sites:
        try:
            r = fn(s); ok[s] = r
            print(f"  PASS {s:7} " + " ".join(f"{k}={r[k]}" for k in ("case", "runs", "archives", "final", "spinup_state", "latest", "rest_dirs") if k in r))
        except Exception as e:
            held[s] = str(e); print(f"  HOLD {s:7} {str(e)[-400:]}")
    print(f"SUMMARY pass={len(ok)} hold={len(held)}", ("HOLD: " + ",".join(held)) if held else "")
    return ok, held


def batch(label, sites, fn):
    bad = []
    for s in sites:
        try: fn(s)
        except Exception as e:
            print(s, label, "HOLD - DO NOT RETRY BLINDLY:", str(e)[-1500:], flush=True); bad.append(s)
    print(label, "SUMMARY ok=", len(sites) - len(bad), "hold=", bad, flush=True)
    if bad: raise SystemExit(2)


def quarantine_one(s):
    o = load(ledger(s))
    if o.get("phase") != "PREPARE_ATTEMPTED_UNCERTAIN": fail(f"{s}: phase {o.get('phase')}; only failed prepares")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": Slurm knows this case")
    cs = (case_dir(s) / "CaseStatus").read_text(errors="replace") if (case_dir(s) / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit|case\.run", cs): fail(s + ": CaseStatus shows submission")
    q = D01 / "quarantine_failed_prepare" / f"{s}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"; q.mkdir(parents=True); moved = {}
    for label, p in (("case", case_dir(s)), ("run_parent", OUT / name(s)), ("ledger", ledger(s))):
        if p.exists(): shutil.move(str(p), str(q / label)); moved[label] = str(p)
    (q / "RECEIPT.json").write_text(json.dumps({"site": s, "moved": moved, "utc": utc()}, indent=2) + "\n")
    print(f"  {s}: quarantined to {q} (surface/forcing/param kept; reused if verified)")


def self_test():
    assert len(SITES) == 10 and set(SITES) == set(SHADOW) == set(CLOCK) == set(ZBOT) == set(PFT) == set(SOIL030)
    assert np.allclose(DEFAULT14.sum(1), 1) and np.allclose(HYDRO_SHRUB.sum(1), 1)
    assert [int(r) for r in sorted({r for r, _ in np.argwhere(~np.isclose(DEFAULT14, HYDRO_SHRUB))})] == [9] and HYDRO_SHRUB[9, 7] == 1
    for s in SITES: pft_check(s)
    for step in (30, 60):
        n = 525600 // step
        for tz in (-5, -6, -7, -8):
            sh = int(-tz * 60 / step); prev, today = np.arange(n) + 10 ** 6, np.arange(n)
            arr = np.concatenate([prev[n - sh:], today[:n - sh]]); assert arr.size == n and arr[sh] == 0 and arr[sh - 1] == prev[-1]
    T = np.array([-30., -5, 0, 20]); P = np.full(4, 9e4); e = 0.6 * esw(T); q = q_from_e(e, P)
    assert np.allclose(q * P / (0.622 + 0.378 * q) / 100, e)
    assert abs(float(datm_es(np.array([20.]))[0]) - float(esw(20.))) < 0.05 and float(datm_es(np.array([-10.]))[0]) < float(esw(-10.))
    # synthetic clock test: FSDS = clear-sky fraction of TOA, local standard time labels, tz -7
    t = pd.Series(pd.date_range("2010-01-01", "2011-01-01", freq="30min", inclusive="left"))
    tu = t + pd.Timedelta(minutes=15) + pd.Timedelta(hours=7); S0 = toa(tu, 40.0, -105.5)
    mins = (tu.dt.hour * 60 + tu.dt.minute).to_numpy()
    for shift_h, ok in ((0, True), (1, False)):
        F = 0.7 * toa(tu - pd.Timedelta(hours=shift_h), 40.0, -105.5)
        cf = pd.Series(F).groupby(mins).mean(); ct = pd.Series(S0).groupby(mins).mean()
        lag = (centroid_min(cf.index, cf.to_numpy()) - centroid_min(ct.index, ct.to_numpy()) + 720) % 1440 - 720
        assert (abs(lag) < 10) == ok and (abs(lag) > 45) == (not ok), lag
    noon = pd.Series(S0).groupby(((t.dt.hour * 60 + t.dt.minute) + 15).to_numpy()).mean().idxmax()   # LST minute of peak
    assert float(S0.max()) > 1000 and 11 * 60 <= noon <= 13 * 60, noon
    tx = "a = 1\n finidat = 'x'\nb = 2\n"; assert nml_get(nml_del(tx, "finidat"), "finidat") is None and nml_get(nml_set(tx, "a", "3"), "a") == "3"
    assert SEGMENTS * SEG_YEARS == 400 and name("US-NR3") == "US-NR3_AMF_B03_FIXNC_AD400_DIRECT"
    print("AMF B03 B3_01 SELF-TEST PASS (maps, PFT register, UTC shift, humidity inverse, DATM esat, TOA clock test; no files, no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "prepare", "submit", "status", "audit-first5", "audit-ad400", "quarantine-failed-prepare"))
    ap.add_argument("--sites", nargs="+"); ap.add_argument("--confirm", default="")
    a = ap.parse_args(); sites = pick(a.sites)
    if a.action == "self-test": return self_test()
    if a.action == "status": return status(sites)
    if a.action == "audit-first5":
        _, h = table("AMF B03 DIRECT AD400 FIRST 5-YEAR AUDIT (read only)", sites, first5_one); raise SystemExit(2 if h else 0)
    if a.action == "audit-ad400":
        _, h = table("AMF B03 DIRECT AD400 AUDIT (read only)", sites, ad400_one); raise SystemExit(2 if h else 0)
    if a.action == "quarantine-failed-prepare":
        if a.confirm != ACK_Q or not a.sites: fail("requires --sites and --confirm " + ACK_Q)
        return batch("QUARANTINE", sites, quarantine_one)
    if a.action == "check":
        _, h = context(sites, write=False)
        print("\nAMF B03 B3_01 CHECK", "PASS 10/10" if not h else f"HOLD {len(h)}: " + ",".join(h), "| READ ONLY, no files, no Slurm", flush=True)
        raise SystemExit(2 if h else 0)
    if a.action == "prepare":
        if a.confirm != ACK_PREP: fail("requires --confirm " + ACK_PREP)
        ctx, h = context(sites, write=True)
        if h: fail("preflight HOLD for " + ",".join(h) + "; use --sites with admitted sites only")
        return batch("PREPARE", sites, lambda s: prepare_one(s, ctx))
    if a.action == "submit":
        if a.confirm != ACK_SUB: fail("requires --confirm " + ACK_SUB)
        stack = stack_guard()
        return batch("SUBMIT", sites, lambda s: submit_one(s, stack))


if __name__ == "__main__":
    main()
