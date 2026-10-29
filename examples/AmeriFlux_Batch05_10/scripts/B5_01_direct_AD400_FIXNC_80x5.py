#!/usr/bin/env python3
"""AmeriFlux Batch05 (10 sites): forcing build + full-record QC, point surfaces, FIXNC direct AD400 80 x 5.

Same pipeline that ran AmeriFlux Batch03 to submission on 2026-10-29 (B3_01..B3_05), reusing B3_01 (pinned) for the
QC, surfaces, FATES maps, forcing NetCDF, CIME case and submit code, with the Batch05 cohort tables below.

Forcing (per site, from the immutable original FLUXMET / FULLSET release, Stage05 sha pinned)
  base      qcv5 conversion of TA_F VPD_F PA_F SW_IN_F LW_IN_F WS_F P_F (FSDS/WIND/P clipped >= 0, P / step)
  S84       Stage84 1,675 user-approved T/VPD research overlay (sha pinned), source values must match the release
  S89       Stage89 US-Whs 51 T/VPD (Stage67 user-directed T + joint VPD; merged here as the user decided to proceed)
  H56       Stage104 56 historical humidity HOLDs: QC2 lane -> scenario A (ERA5-Land RH at source T, VPD >= 0);
            QC0 lane -> measured value retained
  T7        Stage104 7 temperature risks: only |source - two-sided QC0 bracket| > 5 C is replaced by the bracket
            (US-Wkg 2025-09-10 13:00, 12.9 vs 26.5 C); e kept, VPD recomputed. The others keep the source value.
  R1/R2/R3  B3_03 rules (dead-gauge month -> P_ERA; ERA-only P > 2 x BIF MAP -> scale to MAP; SW fault month -> SW_ERA),
            applied only if the site's ERA passes the B3_04 alignment test (TA r >= 0.8 at lag 0, best day lag 0,
            SW_ERA / tower within 15 %); a failing ERA stops that site (as US-Me2 in Batch03).
  every row must end with e > 0; B3_01 full QC (clock vs TOA, PSRF vs elevation, DATM clamp, ranges) must pass.
Design (user/Stage100): selected PFT and soil hypotheses (50-site registers), HYDRO_SHRUB for US-Whs / US-Wkg,
US-Vcm static prefire ENF100 for the whole record, US-Wkg 0-30 cm soil = final register T1 BADM 68.8/12.8 (L1-L5)
over the SSURGO deeper layers, static ZBOT per BASE table (US-Vcp 24 m, 2007-2019-04, ~65 % of the record).

Actions
  self-test
  forcing-check                                               READ ONLY
  forcing-write  --confirm WRITE_AMF_B05_AD400_FORCING_V1      new folders only
  surfaces-check | surfaces-run --confirm MAKE_AMF_B05_POINT_SURFACES   CTSM subset_data point, year-2000, new folders
  check                                                       READ ONLY: B3_01 admission on the written forcing
  prepare --confirm PREPARE_AMF_B05_TEN_DIRECT_AD400_CASES_NO_SLURM
  submit  --confirm SUBMIT_AMF_B05_DIRECT_AD400_80x5_ONCE
  status | audit-first5 | audit-ad400
"""
import argparse, glob, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
B301 = HERE / "B3_01_direct_AD400_FIXNC_80x5.py"
B301_SHA = "be9d43e74c5132c9cadd0503a9361657dec466512514ddf3a994ddaf2abbd863"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


if not B301.is_file() or sha(B301) != B301_SHA: raise SystemExit(f"need B3_01 (commit 9b25208, sha {B301_SHA[:12]}) next to this script")
_s = importlib.util.spec_from_file_location("b301", B301); M = importlib.util.module_from_spec(_s); _s.loader.exec_module(M)

B = M.B
ROOT = B / "sites/MY_EC_SITE"
EXP = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch05_10"
HOME = Path.home()
D84 = HOME / "ameriflux_batch05_stage84_Vcp/Vcp_direct582_20261029T062857Z_2211876"
D89 = HOME / "ameriflux_batch05_stage89_Whs/Whs_51_T_plus_four_VPD_20261029T070333Z_2322432"
D104 = HOME / "ameriflux_batch05_stage104_tDz2rXuN/results"
F84 = D84 / "stage84_VERSIONED_1675_USER_APPROVED_RH_VPD_TA_native_overlay.csv"
F89 = D89 / "stage89_SEPARATE_WHS_51_T_RH_VPD_VERSIONED_INTEGRATION_PREVIEW.csv"
F104H = D104 / "humidity_56_alternative_scenarios_NOT_DATM.csv"
F104T = D104 / "temperature_7_disposition_NOT_DATM.csv"
SHA84 = "63809716e8ad452af53b23e38222475d84804e434fa5070e9a02d1eecfaabbce"
SHA89 = "95aefd6027e6f981ac821266bc379b89d9f1299d1c307b7575a17fec65588561"
SHA104H = "4dab12637089e7793e8bafb079ef1906db8df624063052d67c72289a9e2ee4b3"
SHA104T = "77004f1e4da03209fc1b4df5b16033a3a29f08c0f4e463305bb96a5e60cbb1a7"
REL = {"US-UiD": ("2008-2024_v1.3_r1", 2008, 2024, "FLUXMET"), "US-UMB": ("FULLSET_2007-2021_3-5", 2007, 2021, "FULLSET"),
       "US-UMd": ("2007-2025_v1.3_r1", 2007, 2025, "FLUXMET"), "US-Var": ("2000-2025_v1.3_r1", 2000, 2025, "FLUXMET"),
       "US-Vcm": ("2007-2025_v1.3_r1", 2007, 2025, "FLUXMET"), "US-Vcp": ("2007-2025_v1.3_r1", 2007, 2025, "FLUXMET"),
       "US-WCr": ("1999-2025_v1.3_r1", 1999, 2025, "FLUXMET"), "US-Whs": ("2007-2025_v1.3_r1", 2007, 2025, "FLUXMET"),
       "US-Wjs": ("2007-2025_v1.3_r1", 2007, 2025, "FLUXMET"), "US-Wkg": ("2004-2025_v1.3_r1", 2004, 2025, "FLUXMET")}
RAW_SHA = {"US-UiD": "130142a3b19b11115a058b45129c3ffbeec685b3e5a4e30232701cc149daf318", "US-UMB": "ff2d5144e270e3a629d449e26a7796440d91c780c5c6f29ef4d74d84cea24bd6",
           "US-UMd": "e84f61649a1da11b29799d5ad066898d513c0a93da964cd23bb2b48a676ab2f2", "US-Var": "664ffeb53419d5ea7f618b0a4d3bebbd767c2b8406e1d167a7881a256287eed2",
           "US-Vcm": "c12437170ddb54630f87859bb33398994d9eb3f1c84686336e18a26d457e841c", "US-Vcp": "eece5582523be1f875799751cef9d6b55a4635bfde2ebb008afba31a9a208a42",
           "US-WCr": "f20fbb064ff68668693f8dc04eb72034d98fc4e6e25d4dfb64c7f201a30bb506", "US-Whs": "653f757b7037aa3a6a125ab1160430366b9ffc8c84c8cf0e1eca60652b079cca",
           "US-Wjs": "9b23ab803b719dcb55d2525e4c084c53659e9dea42164fe2382507c97f28bdd6", "US-Wkg": "f0359fe0a40a413c15e79a30d1e6264e6e2d36717d7d394db40e818c4e684829"}
ORDER = tuple(REL)
FALLBACK_CLOCK = {"US-UMB": (-5, 45.5598, -84.7138, 234, None)}   # FULLSET has no BIF: AmeriFlux site record, EST
ZBOT5 = {"US-UiD": (4.0, "TA", "TA 4 m"), "US-UMB": (46.0, "TA", "TA 46 m top level (46/34/15 m)"), "US-UMd": (32.0, "TA", "TA 32 m"),
         "US-Var": (2.0, "TA", "TA 2 m"), "US-Vcm": (23.9, "TA", "TA 23.9 m"),
         "US-Vcp": (24.0, "TA", "TA 24 m 2007-2019-04 (~65 % of the record); 28.2 m from 2019-05"),
         "US-WCr": (29.6, "TA_1_1_1", "TA_1_1_1 29.6 m top level"), "US-Whs": (6.0, "TA_1_1_1", "TA_1_1_1 6 m"),
         "US-Wjs": (10.0, "TA", "TA 10 m"), "US-Wkg": (6.0, "TA_1_1_1", "TA_1_1_1 6 m")}
PFT5 = {"US-UiD": ({13: 20, 14: 80}, "DEFAULT14", {13: 20, 14: 80}), "US-UMB": ({1: 9, 7: 91}, "DEFAULT14", {2: 9, 6: 91}),
        "US-UMd": ({1: 10, 7: 90}, "DEFAULT14", {2: 10, 6: 90}), "US-Var": ({13: 100}, "DEFAULT14", {13: 100}),
        "US-Vcm": ({1: 100}, "DEFAULT14", {2: 100}), "US-Vcp": ({1: 100}, "DEFAULT14", {2: 100}), "US-WCr": ({7: 100}, "DEFAULT14", {6: 100}),
        "US-Whs": ({0: 57, 9: 20, 10: 20, 14: 3}, "HYDRO_SHRUB", {7: 20, 8: 20, 14: 3}),
        "US-Wjs": ({1: 26, 14: 74}, "DEFAULT14", {2: 26, 14: 74}), "US-Wkg": ({0: 60, 10: 3, 14: 37}, "HYDRO_SHRUB", {8: 3, 14: 37})}
# Stage01 CLM10 wide-table L1-L5 means (= FINAL register except US-Wkg, whose FINAL is T1 BADM 68.8/12.8)
SOIL5 = {"US-UiD": (8.0, 22.0), "US-UMB": (93.9, 3.3), "US-UMd": (91.1, 5.1), "US-Var": (20.1, 19.0), "US-Vcm": (70.0, 7.0),
         "US-Vcp": (41.9, 21.1), "US-WCr": (58.1, 15.3), "US-Whs": (66.1, 10.9), "US-Wjs": (65.2, 18.1), "US-Wkg": (39.0, 33.1)}
WKG_FINAL = (68.8, 12.8)
VARS = ["TA_F", "VPD_F", "PA_F", "SW_IN_F", "LW_IN_F", "WS_F", "P_F"]
QCS = ["TA_F_QC", "VPD_F_QC", "P_F_QC", "SW_IN_F_QC"]
ERAV = ["TA_ERA", "SW_IN_ERA", "P_ERA"]
HARD = {"TA_F": (-80, 65), "VPD_F": (-0.1, 125), "PA_F": (50, 110), "SW_IN_F": (-5, 1600), "LW_IN_F": (60, 800), "WS_F": (-0.1, 75), "P_F": (-0.001, 300)}
ACK_F, ACK_S = "WRITE_AMF_B05_AD400_FORCING_V1", "MAKE_AMF_B05_POINT_SURFACES"
ACK_P, ACK_SUB = "PREPARE_AMF_B05_TEN_DIRECT_AD400_CASES_NO_SLURM", "SUBMIT_AMF_B05_DIRECT_AD400_80x5_ONCE"
SURF_DIR = "subset_data_batch05_surf2000"


def fdir(s): return EXP / s / "forcing_shadow_b05_v1"
def fcsv(s): return fdir(s) / f"{s}_B05_AD400_FORCING_V1_NOLEAP.csv"


def num(s):
    a = pd.to_numeric(s, errors="coerce"); return a.where(a > -9990)


def raw(s):
    rel, first, last, prod = REL[s]; d = ROOT / s / "forcing/raw" / f"AMF_{s}_FLUXNET_{rel}"
    c = [p for p in d.iterdir() if p.is_file() and re.fullmatch(rf"AMF_{re.escape(s)}_FLUXNET_{prod}_(HH|HR)_.+\.csv", p.name, re.I)]
    if len(c) != 1: M.fail(f"{s}: primary not unique in {d}")
    era = sorted(p for p in d.glob(f"AMF_{s}_FLUXNET_ERA5_H*_*.csv"))
    bif = sorted(d.glob("*_BIF_*.csv"))
    return c[0], (60 if "_HR_" in c[0].name.upper() else 30), (era[0] if era else None), (bif[0] if bif else None)


def clock(s, bif):
    if bif is None:
        if s not in FALLBACK_CLOCK: M.fail(f"{s}: no BIF and no fallback clock")
        return FALLBACK_CLOCK[s], "FALLBACK AmeriFlux site record (no BIF in release)"
    b = pd.read_csv(bif, keep_default_na=False); g = lambda k: [x for x in b.loc[b.VARIABLE == k, "DATAVALUE"].astype(str) if x.strip()]
    tz = {float(x) for x in g("UTC_OFFSET")}
    if len(tz) != 1: M.fail(f"{s}: BIF UTC_OFFSET {tz}")
    lat, lon = float(g("LOCATION_LAT")[-1]), float(g("LOCATION_LONG")[-1])
    elev = float(g("LOCATION_ELEV")[-1]) if g("LOCATION_ELEV") else 0.0
    mp = float(g("MAP")[0]) if g("MAP") else None
    return (int(tz.pop()), lat, lon, elev, mp), f"BIF {bif.name}"


def overlays():
    for p, h in ((F84, SHA84), (F89, SHA89), (F104H, SHA104H), (F104T, SHA104T)):
        if not p.is_file() or sha(p) != h: M.fail(f"input missing or sha differs: {p}")
    rd = lambda p: pd.read_csv(p, dtype={"native_time": str}, keep_default_na=False)
    o84, o89, h56, t7 = rd(F84), rd(F89), rd(F104H), rd(F104T)
    if (len(o84), len(o89), len(h56), len(t7)) != (1675, 51, 56, 7): M.fail("overlay row counts changed")
    return o84, o89, h56, t7


def read_primary(p, era):
    hdr = list(pd.read_csv(p, nrows=0).columns)
    use = ["TIMESTAMP_START"] + [c for c in VARS + QCS + ERAV if c in hdr]
    f = pd.read_csv(p, usecols=use, dtype={"TIMESTAMP_START": str}, low_memory=False)
    for c in use[1:]: f[c] = num(f[c])
    if era is not None and any(c not in f for c in ERAV):
        eh = list(pd.read_csv(era, nrows=0).columns); eu = ["TIMESTAMP_START"] + [c for c in ERAV if c in eh and c not in f]
        e = pd.read_csv(era, usecols=eu, dtype={"TIMESTAMP_START": str}, low_memory=False)
        for c in eu[1:]: e[c] = num(e[c])
        f = f.merge(e.drop_duplicates("TIMESTAMP_START"), on="TIMESTAMP_START", how="left")
    miss = [c for c in VARS if c not in f]
    if miss: M.fail(f"{p.name}: missing {miss}")
    return f


def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b); return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 500 else np.nan


def era_alignment(f, t):
    x = f.TA_F.where(f.TA_F_QC == 0).to_numpy(float) if "TA_F_QC" in f else f.TA_F.to_numpy(float)
    y = f.TA_ERA.to_numpy(float) if "TA_ERA" in f else np.full(len(f), np.nan)
    r0 = corr(x, y)
    dx = pd.Series(x, index=t.to_numpy()).resample("D").mean().to_numpy(); dy = pd.Series(y, index=t.to_numpy()).resample("D").mean().to_numpy()
    lags = list(range(-10, 11)); rr = [corr(dx[max(0, -k):len(dx) - max(0, k)], dy[max(0, k):len(dy) - max(0, -k)]) for k in lags]
    ld = lags[int(np.nanargmax(rr))] if np.isfinite(rr).any() else None
    sx = f.SW_IN_F.where(f.SW_IN_F_QC == 0).to_numpy(float) if "SW_IN_F_QC" in f else f.SW_IN_F.to_numpy(float)
    sy = f.SW_IN_ERA.to_numpy(float) if "SW_IN_ERA" in f else np.full(len(f), np.nan)
    ok = np.isfinite(sx) & np.isfinite(sy); ratio = float(sy[ok].mean() / sx[ok].mean()) if ok.sum() > 500 else np.nan
    good = bool(np.isfinite(r0) and r0 >= 0.8 and ld == 0 and np.isfinite(ratio) and abs(ratio - 1) <= 0.15)
    return {"TA_r_lag0": round(r0, 3), "TA_best_day_lag": ld, "SW_ERA_over_tower": round(ratio, 3), "aligned": good}


def build(s, ov):
    rel, first, last, prod = REL[s]; p, step, era, bif = raw(s)
    if sha(p) != RAW_SHA[s]: M.fail(f"{s}: release sha differs from Stage05")
    (tz, lat, lon, elev, MAP), csrc = clock(s, bif)
    f = read_primary(p, era)
    t = pd.to_datetime(f.TIMESTAMP_START, format="%Y%m%d%H%M")
    keep = (t.dt.year >= first) & (t.dt.year <= last) & ~((t.dt.month == 2) & (t.dt.day == 29))
    f = f[keep.to_numpy()].reset_index(drop=True); t = t[keep].reset_index(drop=True)
    exp = pd.date_range(f"{first}-01-01", f"{last + 1}-01-01", freq=f"{step}min", inclusive="left"); exp = exp[~((exp.month == 2) & (exp.day == 29))]
    if len(t) != len(exp) or not np.array_equal(t.to_numpy(), exp.to_numpy()): M.fail(f"{s}: not a complete NOLEAP {step}-min timeline")
    nan = {c: int(f[c].isna().sum()) for c in VARS if f[c].isna().any()}
    if nan: M.fail(f"{s}: NaN in release _F variables {nan}")
    bad = {c: int((~f[c].between(lo, hi)).sum()) for c, (lo, hi) in HARD.items() if (~f[c].between(lo, hi)).any()}
    if bad: M.fail(f"{s}: qcv5 HARD range failures {bad}")
    key = f.TIMESTAMP_START.to_numpy(); pos = pd.Series(np.arange(len(f)), index=key)
    T = f.TA_F.to_numpy(float).copy(); V = f.VPD_F.to_numpy(float).copy(); log = []; cnt = {}
    o84, o89, h56, t7 = ov

    def apply(rows, tcol_src, vcol_src, tcol_new, vcol_new, tag):
        r = rows[rows.site == s]
        if not len(r): return 0
        if not r.native_time.isin(pos.index).all(): M.fail(f"{s}: {tag} times outside the forcing timeline")
        i = pos[r.native_time].to_numpy()
        ts, vs = pd.to_numeric(r[tcol_src]).to_numpy(), pd.to_numeric(r[vcol_src]).to_numpy()
        if not (np.allclose(ts, f.TA_F.to_numpy()[i], atol=2e-3) and np.allclose(vs, f.VPD_F.to_numpy()[i], atol=2e-3)): M.fail(f"{s}: {tag} source values differ from release")
        tn, vn = pd.to_numeric(r[tcol_new]).to_numpy(), pd.to_numeric(r[vcol_new]).to_numpy()
        log.append(pd.DataFrame({"TIMESTAMP_START": key[i], "rule": tag, "TA_old": T[i], "TA_new": tn, "VPD_old": V[i], "VPD_new": vn}))
        T[i], V[i] = tn, vn
        return len(r)
    cnt["S84_overlay"] = apply(o84, "source_TA_C", "source_VPD_hPa", "modified_TA_C", "modified_VPD_hPa", "S84")
    cnt["S89_Whs"] = apply(o89, "original_T_C", "original_VPD_hPa", "approved_Stage67_T_C", "proposed_joint_VPD_hPa", "S89")
    hq2 = h56[(h56.site == s) & (h56.lane == "QC2_ERA5LAND_MOISTURE_ALTERNATIVES_REVIEW")].copy()
    hq2["VPD_A"] = hq2["scenario_A_VPD_preserve_grid_RH_hPa"]
    cnt["H56_QC2_scenarioA"] = apply(hq2.assign(TA_keep=hq2.original_T_C), "original_T_C", "original_VPD_hPa", "TA_keep", "VPD_A", "H56_QC2")
    cnt["H56_QC0_retained"] = int(((h56.site == s) & (h56.lane == "QC0_RETAIN_ORIGINAL_PENDING_SENSOR_CONTEXT")).sum())
    oth = h56[(h56.site == s) & ~h56.lane.isin(["QC2_ERA5LAND_MOISTURE_ALTERNATIVES_REVIEW", "QC0_RETAIN_ORIGINAL_PENDING_SENSOR_CONTEXT"])]
    if len(oth): M.fail(f"{s}: {len(oth)} H56 rows in an unhandled lane")
    tr = t7[(t7.site == s)]; cnt["T7_replaced"] = 0
    for _, r in tr.iterrows():
        br = pd.to_numeric(r.bracket_T_C, errors="coerce")
        if np.isfinite(br) and abs(float(r.source_T_C) - br) > 5:
            i = int(pos[r.native_time]); e = M.esw(T[i]) - V[i]
            log.append(pd.DataFrame({"TIMESTAMP_START": [key[i]], "rule": ["T7_bracket"], "TA_old": [T[i]], "TA_new": [br], "VPD_old": [V[i]], "VPD_new": [M.esw(br) - e]}))
            T[i] = br; V[i] = float(M.esw(br) - e); cnt["T7_replaced"] += 1
    e = M.esw(T) - V
    if (e <= 0).any():
        j = np.flatnonzero(e <= 0)
        M.fail(f"{s}: {len(j)} rows still e <= 0 after S84/S89/H56/T7, first {[key[k] for k in j[:6]]} QC {f.VPD_F_QC.to_numpy()[j[:6]].tolist() if 'VPD_F_QC' in f else '-'}")
    e = np.minimum(e, M.datm_es(T)); V = M.esw(T) - e
    psrf = f.PA_F.to_numpy(float) * 1000; sec = step * 60
    d = pd.DataFrame({"time": t.dt.strftime("%Y-%m-%d %H:%M:%S"), "TBOT": T + 273.15, "QBOT": M.q_from_e(e, psrf), "PSRF": psrf,
                      "FSDS": f.SW_IN_F.clip(lower=0).to_numpy(), "FLDS": f.LW_IN_F.to_numpy(), "WIND": f.WS_F.clip(lower=0).to_numpy(),
                      "PRECTmms": f.P_F.clip(lower=0).to_numpy() / sec, "TA_USE": T, "VPD_USE": V})
    d["_t"] = t
    al = era_alignment(f, t)
    rules = {}
    if not al["aligned"]:
        print(f"  ERA alignment FAIL {al} -> no ERA-based P/SW repair; site HOLD for a donor decision", flush=True)
        return d, f, log, cnt, rules, al, (tz, lat, lon, elev, MAP), csrc, p, step, True
    # R1 / R2 / R3 (B3_03 rules)
    y, mo = t.dt.year.to_numpy(), t.dt.month.to_numpy(); P0 = d.PRECTmms.to_numpy() * sec; PE = f.P_ERA.to_numpy(float)
    q0p = (f.P_F_QC == 0).to_numpy() if "P_F_QC" in f else np.ones(len(f), bool)
    g = pd.DataFrame({"y": y, "m": mo, "P": P0, "E": PE, "q0": q0p}).groupby(["y", "m"]).agg(P=("P", "sum"), E=("E", "sum"), q0=("q0", "mean"), nE=("E", "count"), n=("P", "size"))
    dead = g[(g.q0 >= 0.9) & (g.E > 25) & (g.P < 0.25 * g.E) & (g.nE == g.n)]; Pn = P0.copy()
    for (yy, mm), _ in dead.iterrows(): m = (y == yy) & (mo == mm); Pn[m] = PE[m]
    if len(dead): rules["R1_months"] = [f"{yy}-{mm:02d}:{r.P:.0f}->{r.E:.0f}" for (yy, mm), r in dead.iterrows()]
    ann = pd.Series(Pn).groupby(y).sum()
    if MAP and q0p.mean() == 0 and ann.mean() > 2 * MAP:
        fac = MAP / ann.mean(); Pn = Pn * fac; rules["R2_scale"] = round(float(fac), 5)
    ch = np.flatnonzero(np.abs(Pn - P0) > 1e-12)
    if len(ch):
        log.append(pd.DataFrame({"TIMESTAMP_START": key[ch], "rule": "R1/R2", "P_old_mm": P0[ch], "P_new_mm": Pn[ch]})); d["PRECTmms"] = Pn / sec
    SE = f.SW_IN_ERA.to_numpy(float); q0s = (f.SW_IN_F_QC == 0).to_numpy() if "SW_IN_F_QC" in f else np.zeros(len(f), bool); F = d.FSDS.to_numpy()
    gs = pd.DataFrame({"y": y, "m": mo, "F": F, "E": SE, "q0": q0s}).groupby(["y", "m"]).agg(F=("F", "mean"), E=("E", "mean"), q0=("q0", "mean"), nE=("E", "count"), n=("F", "size"))
    badsw = gs[(gs.q0 >= 0.9) & (gs.E > 50) & (gs.F < 0.75 * gs.E) & (gs.nE == gs.n)]
    for (yy, mm), _ in badsw.iterrows():
        m = (y == yy) & (mo == mm); log.append(pd.DataFrame({"TIMESTAMP_START": key[m], "rule": "R3", "SW_old": F[m], "SW_new": np.clip(SE[m], 0, None)}))
        d.loc[m, "FSDS"] = np.clip(SE[m], 0, None)
    if len(badsw): rules["R3_months"] = [f"{yy}-{mm:02d}:{r.F:.0f}->{r.E:.0f}" for (yy, mm), r in badsw.iterrows()]
    return d, f, log, cnt, rules, al, (tz, lat, lon, elev, MAP), csrc, p, step, False


def setup_cohort(clk):
    """Point the pinned B3_01 machinery at the Batch05 cohort."""
    M.SITES = {s: (REL[s][1], REL[s][2], raw(s)[1]) for s in ORDER}
    M.ORDER = ORDER
    M.CLOCK = {s: clk[s][:4] for s in ORDER}
    M.ZBOT, M.PFT, M.SOIL030 = ZBOT5, PFT5, SOIL5
    M.EXP = EXP; M.D01 = EXP / "Stage01_direct_AD400"
    M.name = lambda s: f"{s}_AMF_B05_FIXNC_AD400_DIRECT"
    M.surface = lambda s: EXP / s / "surface" / f"surfdata_{s}_FIXNC_PFT_soil10_b05_v1.nc"
    M.forcing_dir = lambda s: EXP / s / "forcing_UTC_midpoint_ZBOT_b05_v1"
    M.hydro_param = lambda s, ext=".json": EXP / s / f"fates_params_HYDRO_SHRUB_b05_v1{ext}"
    M.SACCT_START = "2026-10-29"

    def original_surface(s):
        c = sorted(x for x in (ROOT / s / SURF_DIR).glob("surfdata*.nc") if x.is_file() and not x.is_symlink())
        if len(c) != 1: M.fail(f"{s}: Batch05 point surface not unique {c}")
        return c[0]
    M.original_surface = original_surface
    M.bif_check = lambda s, man: f"{clk[s][5]} UTC{clk[s][0]:+d}"
    base_soil = M.soil_rows

    def soil_rows():
        out = base_soil(); w = out["US-Wkg"]
        w["sand"] = [WKG_FINAL[0]] * 5 + w["sand"][5:]; w["clay"] = [WKG_FINAL[1]] * 5 + w["clay"][5:]
        w["tier"] = "FINAL_T1_BADM_0-30cm_L1-L5 + Stage01_SSURGO_L6-L10"
        return out
    M.soil_rows = soil_rows

    def frame(s, write=False, base=False):
        rc = fdir(s) / "RECEIPT.json"
        if not rc.is_file(): M.fail(f"{s}: Batch05 forcing not written yet (run forcing-write)")
        r = json.loads(rc.read_text()); p = fcsv(s)
        if sha(p) != r["csv_sha256"]: M.fail(f"{s}: forcing CSV sha differs from receipt")
        d = M.read_frame(p, s)
        return d, M.SITES[s][2], {"path": str(p), "sha256": r["csv_sha256"], "markers": [], "metfix_rules": r.get("counts")}
    M.frame = frame


def forcing(write):
    ov = overlays(); clk = {}; held = []
    print(f"B5 FORCING {'WRITE' if write else 'CHECK (read only)'} | S84 {SHA84[:12]} S89 {SHA89[:12]} S104 {SHA104H[:12]}/{SHA104T[:12]}", flush=True)
    for s in ORDER:
        print(f"\n=== {s}", flush=True)
        try:
            d, f, log, cnt, rules, al, ck, csrc, p, step, hold = build(s, ov)
            clk[s] = (*ck, csrc); M.SITES = {**getattr(M, "SITES", {}), s: (REL[s][1], REL[s][2], step)}; M.CLOCK = {**M.CLOCK, s: ck[:4]}
            print(f"  release {p.name} step {step} | clock UTC{ck[0]:+d} lat {ck[1]} lon {ck[2]} elev {ck[3]} MAP {ck[4]} ({csrc})", flush=True)
            print(f"  applied {json.dumps(cnt)} | ERA {json.dumps(al)}", flush=True)
            if rules: print(f"  repairs {json.dumps(rules)}", flush=True)
            o, h = M.qc(s, d, step)
            print("  QC " + json.dumps({k: v for k, v in o.items() if k not in ("annual_table", "range")}), flush=True)
            print("  ANNUAL year:[T_C,P_mm,SW] " + json.dumps(o["annual_table"]), flush=True)
            if hold: h = h + ["ERA misaligned: needs donor decision"]
            if h: M.fail("QC HOLD: " + "; ".join(h))
            if write:
                od = fdir(s)
                if (od / "RECEIPT.json").is_file(): print(f"  exists, kept {od}", flush=True); continue
                if od.exists(): M.fail(f"partial {od}")
                tmp = od.with_name(od.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
                d[[c for c in M.COLS if c in d]].to_csv(tmp / fcsv(s).name, index=False, float_format="%.17g")
                if log: pd.concat(log, ignore_index=True).to_csv(tmp / f"{s}_B05_changes.csv", index=False)
                back = pd.read_csv(tmp / fcsv(s).name, float_precision="round_trip")
                if not np.array_equal(back[list(M.MET)].to_numpy(float), d[list(M.MET)].to_numpy(float)): M.fail("readback differs")
                (tmp / "RECEIPT.json").write_text(json.dumps({"site": s, "csv": fcsv(s).name, "csv_sha256": sha(tmp / fcsv(s).name), "release": str(p),
                    "release_sha256": RAW_SHA[s], "clock": ck, "clock_source": csrc, "counts": {**cnt, **{k: (v if not isinstance(v, list) else len(v)) for k, v in rules.items()}},
                    "repairs": rules, "era_alignment": al, "inputs": {"S84": SHA84, "S89": SHA89, "S104H": SHA104H, "S104T": SHA104T},
                    "user_decision": "2026-10-29 Batch05 direct AD400 via the Batch03 pipeline", "created_utc": datetime.now(timezone.utc).isoformat()}, indent=2, default=str) + "\n")
                tmp.rename(od); print(f"  WRITTEN {fcsv(s)}", flush=True)
            print(f"  RESULT {s} ADMITTED", flush=True)
        except Exception as ex:
            held.append(s); print(f"  RESULT {s} HOLD {type(ex).__name__}: {ex}", flush=True)
    print(f"\nB5 FORCING {'WRITE' if write else 'CHECK'} {'PASS 10/10' if not held else 'HOLD ' + ','.join(held)}", flush=True)
    if held: raise SystemExit(2)


# ------------------------------------------------------------- point surfaces (CTSM subset_data, as Batch03 Stage03)
def surfaces(run):
    ctsm, inputdata = M.CTSM, B / "inputdata"; tpl = ctsm / "tools/site_and_regional/default_data_2000.cfg"; sub = ctsm / "tools/site_and_regional/subset_data"
    text = tpl.read_text().replace("dir = lnd/clm2/surfdata_esmf/ctsm5.4.0", "dir = lnd/clm2/surfdata_esmf/ctsm5.3.0")
    if "dir = lnd/clm2/surfdata_esmf/ctsm5.3.0" not in text: M.fail("template surfdata dir changed")
    for k, v in (("surfdat_16pft", "surfdata_0.9x1.25_hist_2000_16pfts_c240908.nc"), ("mesh_surf", "fv0.9x1.25_141008_ESMFmesh.nc")):
        text, n = re.subn(r"(?m)^(\s*" + k + r"\s*=)[^\n]*$", lambda m: m.group(1) + " " + v, text)
        if n != 1: M.fail(f"template key {k} count {n}")
    pre = subprocess.run([sys.executable, "-B", str(sub), "point", "--help"], cwd=str(ctsm), capture_output=True, text=True, timeout=60)
    if pre.returncode: M.fail("subset_data import preflight failed under " + sys.executable + "\n" + pre.stderr[-2000:])
    print("subset_data preflight PASS", sys.executable, flush=True)
    for s in ORDER:
        _, _, _, bif = raw(s); (tz, lat, lon, elev, _), csrc = clock(s, bif); out = ROOT / s / SURF_DIR
        if (out / "batch05_surface_receipt.json").is_file():
            print(f"  {s}: exists {sorted(x.name for x in out.glob('surfdata*.nc'))}", flush=True); continue
        if out.exists(): M.fail(f"{s}: partial {out}; inspect")
        print(f"  {s}: {'GENERATE' if run else 'READY'} lat {lat} lon {lon} ({csrc})", flush=True)
        if not run: continue
        out.mkdir(parents=True); cfg = out / f"{s}_data.cfg"; cfg.write_text(text)
        cmd = [sys.executable, "-B", str(sub), "point", "--lat", str(lat), "--lon", str(lon), "--lon-type", "180", "--site", s, "--surf-year", "2000",
               "--create-surface", "--create-user-mods", "--inputdata-dir", str(inputdata), "--cfg-file", str(cfg), "--outdir", str(out)]
        r = subprocess.run(cmd, cwd=str(ctsm), capture_output=True, text=True, timeout=1800)
        if r.returncode: M.fail(f"{s}: subset_data failed\n{r.stdout[-1500:]}\n{r.stderr[-2000:]}")
        sf = sorted(out.glob("surfdata*.nc"))
        if len(sf) != 1: M.fail(f"{s}: subset_data produced {sf}")
        (out / "batch05_surface_receipt.json").write_text(json.dumps({"site": s, "lat": lat, "lon": lon, "clock_source": csrc, "command": cmd,
            "surface": str(sf[0]), "surface_sha256": sha(sf[0]), "created_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
        print(f"  {s}: CREATED {sf[0]}", flush=True)
    print("B5 SURFACES", "RUN DONE" if run else "CHECK DONE (no files)", flush=True)


def self_test():
    assert len(REL) == 10 and set(REL) == set(RAW_SHA) == set(ZBOT5) == set(PFT5) == set(SOIL5)
    M.PFT = PFT5
    for s in ORDER: M.pft_check(s)
    print("B5_01 SELF-TEST PASS (cohort tables, PFT x map = register, B3_01 pinned)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "forcing-check", "forcing-write", "surfaces-check", "surfaces-run", "check", "prepare", "submit",
                                       "status", "audit-first5", "audit-ad400"))
    ap.add_argument("--confirm", default=""); ap.add_argument("--sites", nargs="+")
    a = ap.parse_args()
    if a.action == "self-test": return self_test()
    if a.action in ("forcing-check", "forcing-write"):
        if a.action == "forcing-write" and a.confirm != ACK_F: M.fail("requires --confirm " + ACK_F)
        M.CLOCK = {}; return forcing(a.action == "forcing-write")
    if a.action in ("surfaces-check", "surfaces-run"):
        if a.action == "surfaces-run" and a.confirm != ACK_S: M.fail("requires --confirm " + ACK_S)
        return surfaces(a.action == "surfaces-run")
    clk = {}
    for s in ORDER:
        _, _, _, bif = raw(s); ck, src = clock(s, bif); clk[s] = (*ck, src)
    setup_cohort(clk); sites = M.pick(a.sites)
    if a.action == "status": return M.status(sites)
    if a.action == "audit-first5": _, h = M.table("AMF B05 DIRECT AD400 FIRST 5-YEAR AUDIT", sites, M.first5_one); raise SystemExit(2 if h else 0)
    if a.action == "audit-ad400": _, h = M.table("AMF B05 DIRECT AD400 AUDIT", sites, M.ad400_one); raise SystemExit(2 if h else 0)
    if a.action == "check":
        _, h = M.context(sites, write=False); print("\nAMF B05 CHECK", "PASS 10/10" if not h else "HOLD " + ",".join(h)); raise SystemExit(2 if h else 0)
    if a.action == "prepare":
        if a.confirm != ACK_P: M.fail("requires --confirm " + ACK_P)
        ctx, h = M.context(sites, write=False)
        if h: M.fail("preflight HOLD " + ",".join(h))
        return M.batch("PREPARE", sites, lambda s: M.prepare_one(s, ctx))
    if a.action == "submit":
        if a.confirm != ACK_SUB: M.fail("requires --confirm " + ACK_SUB)
        st = M.stack_guard(); return M.batch("SUBMIT", sites, lambda s: M.submit_one(s, st))


if __name__ == "__main__":
    main()
