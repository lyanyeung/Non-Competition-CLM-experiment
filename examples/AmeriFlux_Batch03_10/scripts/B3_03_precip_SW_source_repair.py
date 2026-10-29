#!/usr/bin/env python3
"""AmeriFlux Batch03 B3_03: precipitation / shortwave source repair for the AD400 forcing (new versioned shadows).

Why (B3_02 audit 2026-10-29): measured-flagged (QC0) gauge months with ~0 mm while ERA5 has rain (dead gauge / zero
fill: US-Kon 2011, 2012, 2016-2018; US-NC2 2022; Me2, Me6, MOz and others a few months); US-NR3 has no measured P at all
and its ERA-only P_F averages 2764 mm/yr against a BIF MAP of 884 mm; the US-Me2 FULLSET SW_IN_ERA is ~25 W m-2 (broken),
and FULLSET filled SW_IN_F QC2 rows with it (Aug-Dec 2022 FSDS 41 -> 2 W m-2).

Rules, fixed before the run (temperature, humidity and timing never touched; HIGH tower months are kept):
  R1 dead gauge   month with >= 90 % P_F_QC = 0 rows, P_ERA month > 25 mm and tower P < 25 % of P_ERA
                  -> every record of that month takes P_ERA (ONEFlux-downscaled ERA5, already scaled to the site record).
  R2 NR3 scale    site with no measured P (P_F_QC = 0 share 0 %) and mean annual P > 2 x BIF MAP
                  -> P x (MAP / mean annual P), timing unchanged.
  R3 SW fault     month with >= 90 % SW_IN_F_QC = 0, reference SW_ERA month mean > 50 W m-2 and SW_F < 75 % of it
                  -> that month takes the reference SW_IN_ERA.
  R4 Me2 ERA      each FULLSET X_ERA is compared with the tower (QC0 rows) and with the companion ERA5 file; if the
                  FULLSET value fails (SW/LW mean ratio off > 15 % or r < 0.7; WS ratio outside 0.5-2; PA off > 3 %) and the
                  companion passes, every X_F QC2 row takes the companion value (PA -> QBOT recomputed from TA_USE/VPD_USE).
                  A failing TA/VPD stops (humidity chain).  The companion is also the R3 reference for US-Me2.
check  READ ONLY: diagnostics, rows/months per rule, annual P / SW before -> after.
run --confirm APPLY_AMF_B03_METFIX_V1_NEW_SHADOWS: writes science_trials/b3_<SITE>_metfix_v1/ (CSV + changes + RECEIPT) for
       changed sites only; base shadows are never modified. B3_01 then uses them automatically (receipt + base sha checked).
"""
import argparse, hashlib, importlib.util, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
B301 = HERE / "B3_01_direct_AD400_FIXNC_80x5.py"
ACK = "APPLY_AMF_B03_METFIX_V1_NEW_SHADOWS"
VARS = {"SW_IN": "FSDS", "LW_IN": "FLDS", "WS": "WIND", "PA": "PSRF", "TA": None, "VPD": None}

spec = importlib.util.spec_from_file_location("b301", B301); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def num(s):
    a = pd.to_numeric(s, errors="coerce"); return a.where(a > -9990)


def read_ts(p, cols):
    hdr = list(pd.read_csv(p, nrows=0).columns); use = ["TIMESTAMP_START"] + [c for c in cols if c in hdr]
    d = pd.read_csv(p, usecols=use, dtype={"TIMESTAMP_START": str}, low_memory=False)
    for c in use[1:]: d[c] = num(d[c])
    return d.drop_duplicates("TIMESTAMP_START")


def ratio_stats(x, t):
    ok = np.isfinite(x) & np.isfinite(t)
    if ok.sum() < 1000: return dict(n=int(ok.sum()))
    return dict(n=int(ok.sum()), ratio=float(x[ok].mean() / t[ok].mean()), bias=float((x[ok] - t[ok]).mean()), r=float(np.corrcoef(x[ok], t[ok])[0, 1]))


def failed(v, s):
    if "ratio" not in s: return True
    if v in ("SW_IN", "LW_IN"): return abs(s["ratio"] - 1) > 0.15 or s["r"] < 0.7
    if v == "WS": return not (0.5 <= s["ratio"] <= 2)
    if v == "PA": return abs(s["ratio"] - 1) > 0.03
    return abs(s["bias"]) > 3 or s["r"] < 0.8          # TA, VPD


def site(s, man, maps):
    first, last, step = M.SITES[s]; sec = step * 60
    d, _, src = M.frame(s, write=False, base=True)
    sp = [x for x in man["sites"] if x["site"] == s][0]
    prim, era = Path(sp["primary"]), Path(sp["era"]) if sp.get("era") else None
    key = d._t.dt.strftime("%Y%m%d%H%M")
    cols = ["P_F", "P_F_QC", "P_ERA", "SW_IN_F", "SW_IN_F_QC", "SW_IN_ERA"]
    if s == "US-Me2": cols += [f"{v}_{k}" for v in VARS for k in ("F", "F_QC", "ERA")]
    f = read_ts(prim, sorted(set(cols)))
    c = read_ts(era, [f"{v}_ERA" for v in VARS] + ["P_ERA"]) if era and era.is_file() else pd.DataFrame(columns=["TIMESTAMP_START"])
    if s != "US-Me2":   # FLUXMET v1.3: ERA in the companion file
        f = f.merge(c[["TIMESTAMP_START"] + [x for x in ("P_ERA", "SW_IN_ERA") if x in c and x not in f]], on="TIMESTAMP_START", how="left")
    f = f.set_index("TIMESTAMP_START").reindex(key.to_numpy())
    if f.P_F.isna().any(): M.fail(f"{s}: release rows missing for the forcing timeline")
    P0 = d.PRECTmms.to_numpy(float) * sec
    if np.nanmax(np.abs(P0 - f.P_F.to_numpy(float))) > 1e-6: M.fail(f"{s}: forcing P differs from P_F; repair rules assume P = P_F")
    new = d.copy(); log = []; rules = {}
    y, mo = d._t.dt.year.to_numpy(), d._t.dt.month.to_numpy()
    print(f"\n######## {s} | base {src.get('path')}", flush=True)
    # ---- R4 (Me2) first, it defines the SW reference
    swref = f.SW_IN_ERA.to_numpy(float) if "SW_IN_ERA" in f else np.full(len(d), np.nan)
    if s == "US-Me2":
        cc = c.set_index("TIMESTAMP_START").reindex(key.to_numpy())
        for v, out in VARS.items():
            t = f[f"{v}_F"].to_numpy(float); q = f[f"{v}_F_QC"].to_numpy(float); q0 = q == 0; q2 = q == 2
            sf = ratio_stats(f[f"{v}_ERA"].to_numpy(float)[q0], t[q0]) if f"{v}_ERA" in f else {"n": 0}
            sc = ratio_stats(cc[f"{v}_ERA"].to_numpy(float)[q0], t[q0]) if f"{v}_ERA" in cc else {"n": 0}
            ff, fc = failed(v, sf), failed(v, sc)
            print(f"  R4 {v:5} QC2 rows {int(q2.sum()):6} | FULLSET ERA vs tower {json.dumps({k: round(x, 3) for k, x in sf.items()})} {'FAIL' if ff else 'ok'}"
                  f" | companion {json.dumps({k: round(x, 3) for k, x in sc.items()})} {'FAIL' if fc else 'ok'}", flush=True)
            if v == "SW_IN" and not fc: swref = cc["SW_IN_ERA"].to_numpy(float)
            if ff and not fc:
                if out is None: M.fail(f"US-Me2: FULLSET {v}_ERA fails; humidity chain would change - STOP for user decision")
                newv = cc[f"{v}_ERA"].to_numpy(float) * (1000 if v == "PA" else 1)
                m = q2 & np.isfinite(newv)
                if v in ("SW_IN", "WS"): newv = np.clip(newv, 0, None)
                new.loc[m, out] = newv[m]; rules[f"R4_{v}"] = int(m.sum())
                log.append(pd.DataFrame({"time": d.time[m], "rule": f"R4_{v}", "var": out, "old": d.loc[m, out], "new": newv[m]}))
                if v == "PA":
                    new.loc[m, "QBOT"] = M.q_from_e(M.esw(d.TA_USE.to_numpy(float)[m]) - d.VPD_USE.to_numpy(float)[m], newv[m])
            elif ff: print(f"  R4 {v}: FULLSET fails and the companion fails too -> unchanged, REVIEW", flush=True)
    # ---- R1 dead gauge
    PE = f.P_ERA.to_numpy(float); q0p = f.P_F_QC.to_numpy(float) == 0
    g = pd.DataFrame({"y": y, "m": mo, "P": P0, "E": PE, "q0": q0p}).groupby(["y", "m"]).agg(P=("P", "sum"), E=("E", "sum"), q0=("q0", "mean"), nE=("E", "count"), n=("P", "size"))
    dead = g[(g.q0 >= 0.9) & (g.E > 25) & (g.P < 0.25 * g.E) & (g.nE == g.n)]
    Pn = P0.copy()
    for (yy, mm), r in dead.iterrows():
        m = (y == yy) & (mo == mm); Pn[m] = PE[m]
    if len(dead):
        rules["R1_months"] = len(dead)
        print(f"  R1 dead-gauge months -> P_ERA ({len(dead)}): " + " ".join(f"{yy}-{mm:02d}:{r.P:.0f}->{r.E:.0f}" for (yy, mm), r in dead.iterrows()), flush=True)
    # ---- R2 NR3-type scale
    MAP = maps.get(s)
    ann = pd.Series(Pn).groupby(y).sum()
    if MAP and q0p.mean() == 0 and ann.mean() > 2 * MAP:
        fac = MAP / ann.mean(); Pn = Pn * fac; rules["R2_scale"] = round(float(fac), 5)
        print(f"  R2 no measured P, mean {ann.mean():.0f} mm/yr > 2 x MAP {MAP:.0f} -> scale x {fac:.4f}", flush=True)
    chg = np.flatnonzero(np.abs(Pn - P0) > 1e-12)
    if len(chg):
        new["PRECTmms"] = Pn / sec
        log.append(pd.DataFrame({"time": d.time.iloc[chg], "rule": "R1/R2", "var": "PRECTmms", "old": d.PRECTmms.iloc[chg], "new": Pn[chg] / sec}))
    # ---- R3 SW fault
    q0s = (f.SW_IN_F_QC.to_numpy(float) == 0) if "SW_IN_F_QC" in f else np.zeros(len(d), bool)
    F = new.FSDS.to_numpy(float)
    gs = pd.DataFrame({"y": y, "m": mo, "F": F, "E": swref, "q0": q0s}).groupby(["y", "m"]).agg(F=("F", "mean"), E=("E", "mean"), q0=("q0", "mean"), nE=("E", "count"), n=("F", "size"))
    bad = gs[(gs.q0 >= 0.9) & (gs.E > 50) & (gs.F < 0.75 * gs.E) & (gs.nE == gs.n)]
    for (yy, mm), r in bad.iterrows():
        m = (y == yy) & (mo == mm); new.loc[m, "FSDS"] = np.clip(swref[m], 0, None)
        log.append(pd.DataFrame({"time": d.time[m], "rule": "R3", "var": "FSDS", "old": F[m], "new": np.clip(swref[m], 0, None)}))
    if len(bad):
        rules["R3_months"] = len(bad)
        print(f"  R3 SW fault months -> SW_ERA ({len(bad)}): " + " ".join(f"{yy}-{mm:02d}:{r.F:.0f}->{r.E:.0f}" for (yy, mm), r in bad.iterrows()), flush=True)
    # ---- summary
    a0 = pd.DataFrame({"y": y, "P": P0, "S": d.FSDS.to_numpy(float)}).groupby("y").agg(P=("P", "sum"), S=("S", "mean"))
    a1 = pd.DataFrame({"y": y, "P": new.PRECTmms.to_numpy(float) * sec, "S": new.FSDS.to_numpy(float)}).groupby("y").agg(P=("P", "sum"), S=("S", "mean"))
    if rules:
        print("  annual P mm before->after | SW W m-2 before->after: " + " ".join(
            f"{yy}:{a0.P[yy]:.0f}->{a1.P[yy]:.0f}" + (f"/{a0.S[yy]:.0f}->{a1.S[yy]:.0f}" if abs(a0.S[yy] - a1.S[yy]) > 0.5 else "") for yy in a0.index), flush=True)
        print(f"  mean P {a0.P.mean():.0f} -> {a1.P.mean():.0f} mm/yr (BIF MAP {MAP}) | rules {rules}", flush=True)
    else:
        print(f"  no rule fires; unchanged (mean P {a0.P.mean():.0f} mm/yr, BIF MAP {MAP})", flush=True)
    o, h = M.qc(s, new, step)
    if h: M.fail(f"{s}: repaired frame fails B3_01 QC: {h}")
    print(f"  repaired frame B3_01 QC PASS (FSDS-TOA lag {o['FSDS_minus_TOA_diurnal_centroid_lag_min']} min)", flush=True)
    return new, (pd.concat(log, ignore_index=True) if log else None), rules, src


def bif_map(man):
    out = {}
    for x in man["sites"]:
        if x["site"] not in M.SITES: continue
        b = sorted(Path(x["primary"]).parent.glob("*_BIF_*.csv"))
        if b:
            t = pd.read_csv(b[0], keep_default_na=False); v = t.loc[t.VARIABLE == "MAP", "DATAVALUE"]
            if len(v): out[x["site"]] = float(v.iloc[0])
    return out


def write(s, new, log, rules, src):
    od = M.metfix_dir(s)
    if od.exists(): M.fail(f"{s}: {od} exists; refuse overwrite")
    tmp = od.with_name(od.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    name = f"{s}_B3_METFIX_V1_NOLEAP.csv"; cols = [c for c in M.COLS if c in new]
    new[cols].to_csv(tmp / name, index=False, float_format="%.17g"); log.to_csv(tmp / f"{s}_METFIX_changes.csv", index=False)
    back = pd.read_csv(tmp / name, float_precision="round_trip")
    if not np.array_equal(back[list(M.MET)].to_numpy(float), new[list(M.MET)].to_numpy(float)): M.fail(f"{s}: readback differs")
    (tmp / "RECEIPT.json").write_text(json.dumps({"site": s, "csv": name, "csv_sha256": M.digest(tmp / name), "base": src.get("path"),
        "base_sha256": src.get("sha256"), "rules_applied": rules, "changed_records": int(len(log)),
        "rules": "R1 dead-gauge month->P_ERA; R2 no-measured-P scale to BIF MAP; R3 SW fault month->SW_ERA; R4 Me2 broken FULLSET ERA->companion ERA5",
        "user_request": "2026-10-29 08:20 check P/SW before AD400", "created_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    tmp.rename(od); print(f"  {s}: WRITTEN {od / name}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("check", "run")); ap.add_argument("--confirm", default=""); ap.add_argument("--sites", nargs="+")
    a = ap.parse_args()
    if a.action == "run" and a.confirm != ACK: M.fail("run requires --confirm " + ACK)
    man = json.loads(M.S07.read_text()); maps = bif_map(man); sites = M.pick(a.sites)
    print(f"B3_03 P/SW SOURCE REPAIR | {'WRITE NEW SHADOWS' if a.action == 'run' else 'READ ONLY'} | BIF MAP {maps}", flush=True)
    if a.action == "run" and "US-Me2" in sites: M.me2_frame(write=True)   # base Me2 shadow, so the metfix has a base sha
    res, bad = {}, []
    for s in sites:
        try: res[s] = site(s, man, maps)
        except Exception as e: bad.append(s); print(f"  {s} HOLD {type(e).__name__}: {e}", flush=True)
    if a.action == "run":
        if bad: M.fail("HOLD sites " + ",".join(bad) + "; nothing written")
        for s, (new, log, rules, src) in res.items():
            if rules: write(s, new, log, rules, src)
    print(f"\nB3_03 DONE | changed sites {[s for s, r in res.items() if r[2]]} | hold {bad} | {'written' if a.action == 'run' else 'no files written'}", flush=True)
    if bad: raise SystemExit(2)


if __name__ == "__main__":
    main()
