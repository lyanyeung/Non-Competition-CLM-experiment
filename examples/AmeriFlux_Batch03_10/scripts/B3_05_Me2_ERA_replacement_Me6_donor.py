#!/usr/bin/env python3
"""AmeriFlux Batch03 B3_05: US-Me2 replacement of the broken FULLSET ERA gap fill (Me6 tower donor + own climatology).

Evidence (B3_04, 2026-10-29): the US-Me2 FULLSET_HH 2002-2022 ERA columns (and the companion ERA5 file, identical) do not
match the tower: r(lag 0) TA 0.57, SW 0.20, LW 0.22, PA 0.01, WS -0.02; no consistent time lag explains it (best lags differ
by variable); SW_IN_ERA is 4-17 % of the tower by month. Every Me2 X_F_QC = 2 row (ERA fill) therefore carries wrong values
(SW 15228, LW 79110, TA 14540, VPD 17321, WS 22814, PA 98553, P 18874 rows), incl. 2022-08..12 entirely. US-Me6 (15 km,
same UTC-8 clock) tower QC0 agrees with Me2 QC0 (daily r TA 0.96, SW 0.97, LW 0.93) and is 99 % QC0 in 2022-07..12.

Rules, fixed before the run (only rows whose Me2 source is ERA, X_F_QC = 2, are touched; measured and MDS rows never):
  R5 donor   Me6 FLUXMET QC0 at the same timestamp, adjusted with Me2-Me6 relations fitted on rows where both are QC0:
             TA, LW additive and e (vapour pressure) ratio per (month, 3-h block); SW ratio per month; WS ratio per
             (month, 3-h block); PA one ratio; P one ratio (Me2/Me6 overlap total). Validated before use: fit on even
             years, test on odd years against Me2 QC0, and against the climatology below.
  R6 clim    where no Me6 QC0 value exists (2002-2009, Me6 gaps): Me2's own QC0 mean for (month, half-hour of day)
             for TA, SW, LW, WS, PA and e. P keeps its source value (ERA P total is scaled to the site; timing unknown).
  R1' P      2010-2022 months with >= 90 % P_F_QC = 0, Me6-based P > 25 mm and Me2 P < 25 % of it -> Me6-based P
             (dead gauge, same rule as B3_03 R1 with the Me6 tower instead of the broken ERA).
  humidity   e = esw(TA_F) - VPD_F (after the CL05/CL07 ledger); a QC2 VPD row takes the R5/R6 e, a QC2 TA row keeps e;
             VPD = esw(TA_new) - e, e capped at DATM saturation; QBOT/TBOT recomputed (qcv5 formulas).
check  READ ONLY: validation table, rows per rule/variable, annual T/P/SW/LW before -> after, B3_01 QC of the result.
run --confirm APPLY_AMF_B03_ME2_METFIX_V1: writes the base Me2 shadow (if absent) and science_trials/b3_US-Me2_metfix_v1/.
"""
import argparse, importlib.util, json, shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b301", HERE / "B3_01_direct_AD400_FIXNC_80x5.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
ACK = "APPLY_AMF_B03_ME2_METFIX_V1"
VARS = ("TA", "VPD", "SW_IN", "LW_IN", "WS", "PA", "P")


def num(s):
    a = pd.to_numeric(s, errors="coerce"); return a.where(a > -9990)


def read(p, key):
    cols = [f"{v}_F" for v in VARS] + [f"{v}_F_QC" for v in VARS]
    hdr = list(pd.read_csv(p, nrows=0).columns); use = ["TIMESTAMP_START"] + [c for c in cols if c in hdr]
    d = pd.read_csv(p, usecols=use, dtype={"TIMESTAMP_START": str}, low_memory=False)
    for c in use[1:]: d[c] = num(d[c])
    return d.drop_duplicates("TIMESTAMP_START").set_index("TIMESTAMP_START").reindex(key)


def fit(kind, a, b, grp, mask):
    """a = Me2, b = Me6; returns adjustment factor/offset per group (pd.Series) from rows in mask."""
    df = pd.DataFrame({"a": a[mask], "b": b[mask], "g": grp[mask]})
    g = df.groupby("g")
    return (g.a.mean() - g.b.mean()) if kind == "add" else (g.a.sum() / g.b.sum())


def apply(kind, b, grp, adj):
    k = pd.Series(grp).map(adj).to_numpy(float)
    return b + k if kind == "add" else b * k


def build(write):
    d, _, src = M.frame("US-Me2", write=False, base=True)
    man = json.loads(M.S07.read_text()); sp = {x["site"]: x for x in man["sites"]}
    key = d._t.dt.strftime("%Y%m%d%H%M").to_numpy()
    A = read(sp["US-Me2"]["primary"], key); Bm = read(sp["US-Me6"]["primary"], key)
    t = d._t; yr = t.dt.year.to_numpy(); mo = t.dt.month.to_numpy(); hh = (t.dt.hour * 2 + t.dt.minute // 30).to_numpy()
    blk = mo * 10 + hh // 6; mhh = mo * 100 + hh
    TA0 = d.TA_USE.to_numpy(float); V0 = d.VPD_USE.to_numpy(float); e0 = M.esw(TA0) - V0
    q = {v: A[f"{v}_F_QC"].to_numpy(float) for v in VARS}
    me2 = {"TA": TA0, "SW_IN": d.FSDS.to_numpy(float), "LW_IN": d.FLDS.to_numpy(float), "WS": d.WIND.to_numpy(float),
           "PA": d.PSRF.to_numpy(float), "e": e0, "P": d.PRECTmms.to_numpy(float) * 1800}
    bq0 = {v: Bm[f"{v}_F_QC"].to_numpy(float) == 0 for v in VARS}
    me6 = {"TA": np.where(bq0["TA"], Bm.TA_F, np.nan), "SW_IN": np.where(bq0["SW_IN"], Bm.SW_IN_F, np.nan),
           "LW_IN": np.where(bq0["LW_IN"], Bm.LW_IN_F, np.nan), "WS": np.where(bq0["WS"], Bm.WS_F, np.nan),
           "PA": np.where(bq0["PA"], Bm.PA_F * 1000, np.nan),
           "e": np.where(bq0["TA"] & bq0["VPD"], M.esw(Bm.TA_F.to_numpy(float)) - Bm.VPD_F.to_numpy(float), np.nan),
           "P": np.where(bq0["P"], Bm.P_F, np.nan)}
    a0 = {"TA": q["TA"] == 0, "SW_IN": q["SW_IN"] == 0, "LW_IN": q["LW_IN"] == 0, "WS": q["WS"] == 0, "PA": q["PA"] == 0,
          "e": (q["TA"] == 0) & (q["VPD"] == 0), "P": q["P"] == 0}
    spec_ = {"TA": ("add", blk), "LW_IN": ("add", blk), "e": ("ratio", blk), "WS": ("ratio", blk), "SW_IN": ("ratio", mo),
             "PA": ("ratio", np.zeros(len(d), int)), "P": ("ratio", np.zeros(len(d), int))}
    # climatology (Me2 QC0, month x half-hour)
    clim = {v: apply("add", np.zeros(len(d)), mhh, pd.DataFrame({"a": me2[v][a0[v]], "g": mhh[a0[v]]}).groupby("g").a.mean()) for v in ("TA", "SW_IN", "LW_IN", "WS", "PA", "e")}
    # validation: fit even years, test odd years
    print("VALIDATION on Me2 QC0 & Me6 QC0, fit even years / test odd years (MAE, r) | Me2 own climatology on the same rows", flush=True)
    val = {}
    for v, (kind, grp) in spec_.items():
        both = a0[v] & np.isfinite(me6[v]) & np.isfinite(me2[v])
        if v == "P":
            mm = pd.DataFrame({"y": yr, "m": mo, "a": np.where(both, me2[v], np.nan), "b": np.where(both, me6[v], np.nan)}).groupby(["y", "m"]).sum(min_count=1).dropna()
            ev = mm.index.get_level_values(0) % 2 == 0; r_ = mm.a[ev].sum() / mm.b[ev].sum(); pr = mm.b[~ev] * r_
            val[v] = dict(N_months=int((~ev).sum()), ratio=round(float(r_), 3), MAE_month_mm=round(float((pr - mm.a[~ev]).abs().mean()), 2),
                          r_month=round(float(np.corrcoef(pr, mm.a[~ev])[0, 1]), 3))
        else:
            tr = both & (yr % 2 == 0); te = both & (yr % 2 == 1)
            p = apply(kind, me6[v], grp, fit(kind, me2[v], me6[v], grp, tr))
            ok = te & np.isfinite(p); err = p[ok] - me2[v][ok]; ce = clim[v][ok] - me2[v][ok]
            val[v] = dict(N=int(ok.sum()), MAE=round(float(np.abs(err).mean()), 3), bias=round(float(err.mean()), 3), r=round(float(np.corrcoef(p[ok], me2[v][ok])[0, 1]), 3),
                          clim_MAE=round(float(np.abs(ce).mean()), 3), clim_r=round(float(np.corrcoef(clim[v][ok], me2[v][ok])[0, 1]), 3))
        print(f"  {v:5} {json.dumps(val[v])}", flush=True)
        if v != "P" and not (val[v]["MAE"] < val[v]["clim_MAE"]): M.fail(f"donor {v} not better than climatology; STOP")
    # final adjustments on all overlap years
    don = {}
    for v, (kind, grp) in spec_.items():
        both = a0[v] & np.isfinite(me6[v]) & np.isfinite(me2[v])
        if v == "P":
            mm = pd.DataFrame({"y": yr, "m": mo, "a": np.where(both, me2[v], np.nan), "b": np.where(both, me6[v], np.nan)}).groupby(["y", "m"]).sum(min_count=1).dropna()
            don[v] = me6[v] * (mm.a.sum() / mm.b.sum())
        else:
            don[v] = apply(kind, me6[v], grp, fit(kind, me2[v], me6[v], grp, both))
    don["SW_IN"] = np.clip(don["SW_IN"], 0, None); don["WS"] = np.clip(don["WS"], 0, None); don["e"] = np.clip(don["e"], 1e-3, None)
    # apply R5 / R6
    new = {k: v.copy() for k, v in me2.items()}; cnt = {}
    for v, qv in (("TA", q["TA"]), ("SW_IN", q["SW_IN"]), ("LW_IN", q["LW_IN"]), ("WS", q["WS"]), ("PA", q["PA"]), ("e", q["VPD"])):
        tgt = qv == 2; r5 = tgt & np.isfinite(don[v]); r6 = tgt & ~r5
        new[v][r5] = don[v][r5]; new[v][r6] = clim[v][r6]; cnt[v] = {"R5_Me6": int(r5.sum()), "R6_clim": int(r6.sum())}
    p2 = q["P"] == 2; r5p = p2 & np.isfinite(don["P"]); new["P"][r5p] = don["P"][r5p]; cnt["P"] = {"R5_Me6": int(r5p.sum()), "kept_source_pre2010": int((p2 & ~r5p).sum())}
    # R1' dead gauge with the Me6-based reference
    g = pd.DataFrame({"y": yr, "m": mo, "P": new["P"], "D": don["P"], "q0": q["P"] == 0, "dn": np.isfinite(don["P"])}).groupby(["y", "m"]).agg(
        P=("P", "sum"), D=("D", "sum"), q0=("q0", "mean"), dn=("dn", "mean"))
    dead = g[(g.q0 >= 0.9) & (g.dn >= 0.9) & (g.D > 25) & (g.P < 0.25 * g.D)]
    for (yy, mm), _ in dead.iterrows():
        m = (yr == yy) & (mo == mm) & np.isfinite(don["P"]); new["P"][m] = don["P"][m]
    cnt["P"]["R1prime_months"] = len(dead)
    if len(dead): print("R1' dead-gauge months (Me2 -> Me6-based): " + " ".join(f"{yy}-{mm:02d}:{r.P:.0f}->{r.D:.0f}" for (yy, mm), r in dead.iterrows()), flush=True)
    # humidity and derived fields
    TA = new["TA"]; e = np.minimum(new["e"], M.datm_es(TA)); V = M.esw(TA) - e
    out = d.copy()
    out["TA_USE"] = TA; out["VPD_USE"] = V; out["TBOT"] = TA + 273.15; out["PSRF"] = new["PA"]; out["QBOT"] = M.q_from_e(e, new["PA"])
    out["FSDS"] = new["SW_IN"]; out["FLDS"] = new["LW_IN"]; out["WIND"] = new["WS"]; out["PRECTmms"] = np.clip(new["P"], 0, None) / 1800.0
    print("ROWS per variable: " + json.dumps(cnt), flush=True)
    led = pd.read_csv(M.ME2_CL05, dtype={"TIMESTAMP_START": str}); ledset = set(led.TIMESTAMP_START)
    lt = np.isin(key, list(ledset)); print(f"CL05/CL07 ledger rows whose e is now replaced by R5/R6: {int((lt & (q['VPD'] == 2)).sum())} of {int(lt.sum())}", flush=True)
    an = lambda x: pd.DataFrame({"y": yr, "T": x.TA_USE, "P": x.PRECTmms * 1800, "SW": x.FSDS, "LW": x.FLDS}).groupby("y").agg(Tm=("T", "mean"), P=("P", "sum"), SW=("SW", "mean"), LW=("LW", "mean"))
    b0, b1 = an(d), an(out)
    print("ANNUAL year: T C, P mm, SW, LW  before -> after", flush=True)
    for yy in b0.index:
        print(f"  {yy} T {b0.Tm[yy]:5.2f}->{b1.Tm[yy]:5.2f}  P {b0.P[yy]:4.0f}->{b1.P[yy]:4.0f}  SW {b0.SW[yy]:5.1f}->{b1.SW[yy]:5.1f}  LW {b0.LW[yy]:5.1f}->{b1.LW[yy]:5.1f}", flush=True)
    o, h = M.qc("US-Me2", out, 30)
    print("B3_01 QC of the repaired Me2 frame: " + json.dumps({k: o[k] for k in ("DATM_RH_gt100_clamped", "RH_min", "RH_lt5pct", "PSRF_median_over_barometric",
          "FSDS_minus_TOA_diurnal_centroid_lag_min", "clearness_FSDS_over_TOA_mean", "FLDS_emissivity_p001_p999", "annual_SW_Wm2_min_max", "annual_P_mm_min_max")}), flush=True)
    if h: M.fail("repaired Me2 fails B3_01 QC: " + "; ".join(h))
    changes = {k: int(np.sum(np.abs(out[k].to_numpy(float) - d[k].to_numpy(float)) > 1e-12)) for k in M.MET}
    print("changed records per forcing field: " + json.dumps(changes), flush=True)
    if not write: return
    od = M.metfix_dir("US-Me2")
    if od.exists(): M.fail(f"{od} exists; refuse overwrite")
    tmp = od.with_name(od.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    name = "US-Me2_B3_METFIX_V1_NOLEAP.csv"; cols = [c for c in M.COLS if c in out]
    out[cols].to_csv(tmp / name, index=False, float_format="%.17g")
    ch = np.zeros(len(d), bool)
    for k in M.MET: ch |= np.abs(out[k].to_numpy(float) - d[k].to_numpy(float)) > 1e-12
    pd.DataFrame({"TIMESTAMP_START": key[ch], **{f"{k}_old": d[k].to_numpy()[ch] for k in M.MET}, **{f"{k}_new": out[k].to_numpy()[ch] for k in M.MET},
                  **{f"{v}_F_QC": q[v][ch] for v in VARS}}).to_csv(tmp / "US-Me2_METFIX_changes.csv", index=False)
    back = pd.read_csv(tmp / name, float_precision="round_trip")
    if not np.array_equal(back[list(M.MET)].to_numpy(float), out[list(M.MET)].to_numpy(float)): M.fail("readback differs")
    (tmp / "RECEIPT.json").write_text(json.dumps({"site": "US-Me2", "csv": name, "csv_sha256": M.digest(tmp / name), "base": src.get("path"),
        "base_sha256": src.get("sha256"), "rules_applied": {"rows": cnt, "changed_records": changes}, "validation": val,
        "rules": "R5 Me6-tower donor (adjusted) for Me2 ERA-filled QC2 rows; R6 Me2 QC0 month x half-hour climatology where no donor; "
                 "R1' dead-gauge months 2010-2022 vs Me6-based P; e-space humidity, QBOT/TBOT recomputed",
        "evidence": "B3_04: Me2 FULLSET/companion ERA uncorrelated with tower (TA r 0.57, SW 0.20, SW ratio 0.13)",
        "user_decision": "2026-10-29 08:40 '按照你的建议'", "created_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    tmp.rename(od); print(f"WRITTEN {od / name}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("check", "run")); ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.action == "run":
        if a.confirm != ACK: M.fail("run requires --confirm " + ACK)
        M.me2_frame(write=True)
    print(f"B3_05 US-Me2 ERA REPLACEMENT | {'WRITE' if a.action == 'run' else 'READ ONLY'}", flush=True)
    build(a.action == "run")
    print("B3_05 DONE", flush=True)


if __name__ == "__main__":
    main()
