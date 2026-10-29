#!/usr/bin/env python3
"""AmeriFlux Batch03 B3_04: READ-ONLY check that each site's ERA5 companion (used for every QC2 gap fill) is aligned
with the tower in time and magnitude.

Trigger: B3_03 check 2026-10-29 found the US-Me2 FULLSET ERA (and its companion, identical) agree with the tower in mean
for TA/LW/PA/VPD but correlate badly (TA r 0.57, LW 0.22, PA 0.01, WS -0.02) and SW_IN_ERA is 13 % of the tower.
For every site, on tower QC0 rows: correlation at lag 0, the best half-hour lag within +-36 h, and the best day lag
within +-200 days on daily means, for TA, SW_IN, LW_IN, PA, WS; plus SW_ERA / SW tower mean ratio by month.
US-Me2 is also compared with the US-Me6 tower (15 km) over 2010-2022 (daily TA/SW/LW/P), the natural donor if the
Me2 ERA is unusable. Writes nothing.
"""
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

S07 = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/qcv5_native_trial_20261022T024559Z_36c46e58/exact_input_manifest.json")
SITES = ["US-Kon", "US-MMS", "US-Me2", "US-Me6", "US-MOz", "US-Mpj", "US-MtB", "US-NC2", "US-NR1", "US-NR3"]
V = ["TA", "SW_IN", "LW_IN", "PA", "WS"]
BAD = set()


def num(s):
    a = pd.to_numeric(s, errors="coerce"); return a.where(a > -9990)


def read(p, cols):
    hdr = list(pd.read_csv(p, nrows=0).columns); use = ["TIMESTAMP_START"] + [c for c in cols if c in hdr]
    d = pd.read_csv(p, usecols=use, dtype={"TIMESTAMP_START": str}, low_memory=False)
    for c in use[1:]: d[c] = num(d[c])
    return d.drop_duplicates("TIMESTAMP_START").set_index("TIMESTAMP_START")


def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 500 else np.nan


def lagscan(x, y, lags):
    out = []
    for k in lags:
        if k >= 0: out.append(corr(x[:len(x) - k] if k else x, y[k:]))
        else: out.append(corr(x[-k:], y[:k]))
    out = np.array(out); i = int(np.nanargmax(out)) if np.isfinite(out).any() else 0
    return lags[i], out[i]


def load(s, man):
    sp = [x for x in man["sites"] if x["site"] == s][0]
    f = read(sp["primary"], [f"{v}_{k}" for v in V for k in ("F", "F_QC", "ERA")] + ["P_F", "P_ERA"])
    if sp.get("era") and Path(sp["era"]).is_file():
        e = read(sp["era"], [f"{v}_ERA" for v in V] + ["P_ERA"])
        f = f.join(e[[c for c in e.columns if c not in f]], how="left")
    t = pd.to_datetime(pd.Series(f.index, index=f.index), format="%Y%m%d%H%M")
    return f, t


def site(s, man):
    f, t = load(s, man); step = int(round(t.diff().dt.total_seconds().median() / 60)); n_h = 60 // step
    print(f"\n######## {s} step {step} min, rows {len(f)}", flush=True)
    for v in V:
        if f"{v}_F" not in f or f"{v}_ERA" not in f: print(f"  {v:5} not available"); continue
        x = f[f"{v}_F"].to_numpy(float).copy(); q = f.get(f"{v}_F_QC"); y = f[f"{v}_ERA"].to_numpy(float)
        if q is not None: x[q.to_numpy() != 0] = np.nan
        r0 = corr(x, y); lh, rh = lagscan(x, y, list(range(-36 * n_h, 36 * n_h + 1)))
        dx = pd.Series(x, index=t.to_numpy()).resample("D").mean().to_numpy(); dy = pd.Series(y, index=t.to_numpy()).resample("D").mean().to_numpy()
        ld, rd = lagscan(dx, dy, list(range(-200, 201)))
        ratio = np.nanmean(y[np.isfinite(x)]) / np.nanmean(x)
        qc2 = int((q == 2).sum()) if q is not None else -1
        flag = "  <-- MISALIGNED/BROKEN" if (v in ("TA", "SW_IN") and (r0 < 0.8 or ld != 0 or abs(lh) > n_h)) or (v == "SW_IN" and abs(ratio - 1) > 0.15) else ""
        if flag: BAD.add(s)
        print(f"  {v:5} QC2 {qc2:6} | r(lag0) {r0:6.3f} | best HH-lag {lh * step / 60:+5.1f} h r {rh:6.3f} | best day-lag {ld:+4d} r {rd:6.3f} | mean ERA/tower {ratio:5.3f}{flag}", flush=True)
    if "SW_IN_F" in f and "SW_IN_ERA" in f:
        m = t.dt.month.to_numpy(); x = f.SW_IN_F.to_numpy(float); y = f.SW_IN_ERA.to_numpy(float)
        print("  SW ERA/tower by month: " + " ".join(f"{k}:{np.nanmean(y[m == k]) / np.nanmean(x[m == k]):.2f}" for k in range(1, 13)), flush=True)
    return f, t


def me2_me6(man, cache):
    (a, ta), (b, tb) = cache["US-Me2"], cache["US-Me6"]
    print("\n######## US-Me2 vs US-Me6 tower (daily means, 2010-2022; Me6 QC0 only)", flush=True)
    for v in ("TA", "SW_IN", "LW_IN", "WS"):
        if f"{v}_F" not in a or f"{v}_F" not in b: continue
        xb = b[f"{v}_F"].where(b[f"{v}_F_QC"] == 0) if f"{v}_F_QC" in b else b[f"{v}_F"]
        xa = a[f"{v}_F"].where(a[f"{v}_F_QC"] == 0) if f"{v}_F_QC" in a else a[f"{v}_F"]
        A = pd.Series(xa.to_numpy(), index=ta.to_numpy()).resample("D").mean(); Bm = pd.Series(xb.to_numpy(), index=tb.to_numpy()).resample("D").mean()
        E = pd.Series(a[f"{v}_ERA"].to_numpy(), index=ta.to_numpy()).resample("D").mean()
        j = pd.concat([A, Bm, E], axis=1, keys=["me2", "me6", "era"]).loc["2010":"2022"]
        print(f"  {v:5} r(Me2 QC0, Me6 QC0) {corr(j.me2.to_numpy(), j.me6.to_numpy()):.3f} | r(Me2 ERA, Me6) {corr(j.era.to_numpy(), j.me6.to_numpy()):.3f} | "
              f"mean Me2 {j.me2.mean():.2f} Me6 {j.me6.mean():.2f} | Me2-Me6 bias {np.nanmean(j.me2 - j.me6):+.2f}", flush=True)
    if "P_F" in a and "P_F" in b:
        A = pd.Series(a.P_F.to_numpy(), index=ta.to_numpy()).resample("MS").sum(); Bm = pd.Series(b.P_F.to_numpy(), index=tb.to_numpy()).resample("MS").sum()
        j = pd.concat([A, Bm], axis=1, keys=["me2", "me6"]).loc["2010":"2022"]
        print(f"  P     monthly r {corr(j.me2.to_numpy(), j.me6.to_numpy()):.3f} | annual Me2 {j.me2.sum() / 13:.0f} Me6 {j.me6.sum() / 13:.0f} mm/yr", flush=True)
    # 2022-08..12 (Me2 100 % QC2) Me6 availability
    g = b.loc[(tb >= "2022-07-01").to_numpy() & (tb < "2023-01-01").to_numpy()]
    print("  Me6 2022-07..12 QC0 share: " + " ".join(f"{v}={(g[f'{v}_F_QC'] == 0).mean():.2f}" for v in V if f"{v}_F_QC" in g), flush=True)


def main():
    print("B3_04 ERA ALIGNMENT DIAGNOSTIC | READ ONLY", flush=True)
    man = json.loads(S07.read_text()); cache = {}
    for s in (sys.argv[1:] or SITES):
        try: cache[s] = site(s, man)
        except Exception as e: print(f"  {s} ERROR {type(e).__name__}: {e}", flush=True)
    if "US-Me2" in cache and "US-Me6" in cache:
        try: me2_me6(man, cache)
        except Exception as e: print("  Me2/Me6 ERROR", type(e).__name__, e, flush=True)
    other = sorted(BAD - {"US-Me2"})
    print(f"\nB3_04 DONE | TA/SW ERA flagged: {sorted(BAD)} | no files written, no jobs", flush=True)
    if other: print("B3_04 STOP: ERA of", other, "also flagged; do not apply B3_03 to them before review", flush=True); raise SystemExit(3)


if __name__ == "__main__":
    main()
