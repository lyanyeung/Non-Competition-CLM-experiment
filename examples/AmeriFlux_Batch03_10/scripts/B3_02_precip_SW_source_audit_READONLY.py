#!/usr/bin/env python3
"""AmeriFlux Batch03 B3_02: READ-ONLY source audit of precipitation and incoming shortwave before AD400.

User request 2026-10-29 08:20: check the B3_01 outliers before running (Kon P 2011/2012, NR3 P 2000-3400 mm/yr,
Me2 2002 P and 2022 SW, Me6 dry years) and make sure the meteorology is sound. All ten sites are audited the same way.

Per site and year it prints
  P_forc   annual P of the AD400 forcing (B3_01 frame: research shadow / Me2 build), mm
  P_F      release P_F, with the share of P_F_QC 0 (measured) / 2 (ERA)
  P_ERA    ONEFlux-downscaled ERA5 P (FLUXMET column, else the companion ERA5 file)
  BASE     raw BASE precipitation sum and its missing share (if a BASE file is in forcing/raw)
  SW       SW_IN_F and SW_IN_ERA annual means, SW_IN_F QC2 share
and lists months where tower P < 25 % of ERA (ERA > 25 mm: dead gauge / zero fill) or > 300 % (ERA > 0, tower > 50 mm),
and months where SW_IN_F differs from SW_IN_ERA by > 25 % (ERA month mean > 50 W m-2). BIF MAP/MAT are printed.
Writes nothing.
"""
import glob, hashlib, importlib.util, re, sys, json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
B301 = HERE / "B3_01_direct_AD400_FIXNC_80x5.py"
B301_SHA = "d96402209412de23c795917c1ba70b4fd897e2de1383daf54fdba83beddf64f9"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


if sha(B301) != B301_SHA: raise SystemExit("B3_01 script sha differs (download commit dfe4c54 next to this script)")
spec = importlib.util.spec_from_file_location("b301", B301); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def num(s):
    a = pd.to_numeric(s, errors="coerce"); return a.where(a > -9990)


def read_ts(p, cols, comment=None):
    hdr = list(pd.read_csv(p, nrows=0, comment=comment).columns)
    use = ["TIMESTAMP_START"] + [c for c in cols if c in hdr]
    d = pd.read_csv(p, usecols=use, dtype={"TIMESTAMP_START": str}, comment=comment, low_memory=False)
    for c in use[1:]: d[c] = num(d[c])
    d["_t"] = pd.to_datetime(d.TIMESTAMP_START.str.slice(0, 12), format="%Y%m%d%H%M", errors="coerce")
    return d.dropna(subset=["_t"]), hdr


def site(s, man):
    first, last, step = M.SITES[s]
    sp = [x for x in man["sites"] if x["site"] == s][0]
    prim, era = Path(sp["primary"]), Path(sp["era"]) if sp.get("era") else None
    raw = prim.parent
    print(f"\n######## {s} {first}-{last} step {step} min | {prim.name}", flush=True)
    bif = sorted(raw.glob("*_BIF_*.csv"))
    if bif:
        b = pd.read_csv(bif[0], keep_default_na=False)
        print("  BIF " + " ".join(f"{k}={sorted(set(b.loc[b.VARIABLE == k, 'DATAVALUE'].astype(str)))}" for k in ("MAP", "MAT", "CLIMATE_KOEPPEN", "IGBP")), flush=True)
    f, hdr = read_ts(prim, ["P_F", "P_F_QC", "P_ERA", "SW_IN_F", "SW_IN_F_QC", "SW_IN_ERA", "P", "SW_IN_POT"])
    if not {"P_ERA", "SW_IN_ERA"} <= set(f.columns) and era and era.is_file():
        e, _ = read_ts(era, ["P_ERA", "SW_IN_ERA"])
        f = f.merge(e[["TIMESTAMP_START"] + [c for c in ("P_ERA", "SW_IN_ERA") if c in e and c not in f]], on="TIMESTAMP_START", how="left")
    f = f[(f._t.dt.year >= first) & (f._t.dt.year <= last) & ~((f._t.dt.month == 2) & (f._t.dt.day == 29))].copy()
    d, _, src = M.frame(s, write=False)
    pf = pd.DataFrame({"y": d._t.dt.year, "P": d.PRECTmms.to_numpy(float) * step * 60})
    f["y"], f["m"] = f._t.dt.year, f._t.dt.month
    base = sorted(set(glob.glob(str(raw / "**" / f"AMF_{s}_BASE_*.csv"), recursive=True)) | set(glob.glob(str(raw.parent / f"AMF_{s}_BASE_*.csv"))))
    bp = None
    if base:
        try:
            bh = list(pd.read_csv(base[-1], nrows=0, comment="#").columns)
            pc = [c for c in bh if re.fullmatch(r"P(_\d+_\d+_\d+)?", c)]
            if pc:
                bd, _ = read_ts(base[-1], pc[:1], comment="#")
                bd = bd[(bd._t.dt.year >= first) & (bd._t.dt.year <= last)]
                bp = bd.groupby(bd._t.dt.year)[pc[0]].agg(["sum", lambda x: x.isna().mean()]); bp.columns = ["sum", "nan"]
                print(f"  BASE {Path(base[-1]).name} column {pc[0]}", flush=True)
        except Exception as ex:
            print("  BASE read error", ex, flush=True)
    else:
        print("  BASE none in forcing/raw", flush=True)
    has = lambda c: c in f and f[c].notna().any()
    print("  year  P_forc   P_F  QC0%  QC2%  P_ERA  F/ERA |  BASE  miss% | SW_F SW_ERA SWqc2% | deadP_months", flush=True)
    pfy = pf.groupby("y").P.sum()
    mo = f.groupby(["y", "m"]).agg(PF=("P_F", "sum"), PE=("P_ERA", "sum") if has("P_ERA") else ("P_F", "size"),
                                  SF=("SW_IN_F", "mean"), SE=("SW_IN_ERA", "mean") if has("SW_IN_ERA") else ("SW_IN_F", "size"),
                                  q0=("P_F_QC", lambda x: (x == 0).mean()) if has("P_F_QC") else ("P_F", "size"))
    flags_p, flags_s = [], []
    for y in range(first, last + 1):
        g = f[f.y == y]; m = mo.loc[y] if y in mo.index.get_level_values(0) else None
        PF = g.P_F.sum(); PE = g.P_ERA.sum() if has("P_ERA") else np.nan
        q0 = (g.P_F_QC == 0).mean() * 100 if has("P_F_QC") else np.nan; q2 = (g.P_F_QC == 2).mean() * 100 if has("P_F_QC") else np.nan
        dead = 0
        if has("P_ERA") and m is not None:
            for mm, r in m.iterrows():
                if r.PE > 25 and r.PF < 0.25 * r.PE: dead += 1; flags_p.append(f"{y}-{mm:02d} F={r.PF:.0f} ERA={r.PE:.0f} QC0={100 * r.q0:.0f}%")
                elif r.PE > 0 and r.PF > 50 and r.PF > 3 * r.PE: flags_p.append(f"{y}-{mm:02d} HIGH F={r.PF:.0f} ERA={r.PE:.0f} QC0={100 * r.q0:.0f}%")
            if has("SW_IN_ERA"):
                for mm, r in m.iterrows():
                    if r.SE > 50 and abs(r.SF / r.SE - 1) > 0.25: flags_s.append(f"{y}-{mm:02d} SW_F={r.SF:.0f} ERA={r.SE:.0f}")
        sw2 = (g.SW_IN_F_QC == 2).mean() * 100 if has("SW_IN_F_QC") else np.nan
        bs = f"{bp.loc[y, 'sum']:6.0f} {100 * bp.loc[y, 'nan']:5.1f}" if bp is not None and y in bp.index else "     -     -"
        print(f"  {y} {pfy.get(y, np.nan):7.0f} {PF:6.0f} {q0:5.1f} {q2:5.1f} {PE:6.0f} {PF / PE if PE else np.nan:6.2f} | {bs} | "
              f"{g.SW_IN_F.mean():4.0f} {g.SW_IN_ERA.mean() if has('SW_IN_ERA') else np.nan:6.0f} {sw2:6.1f} | {dead}", flush=True)
    tot = lambda a: float(np.nansum(a))
    if has("P_ERA"):
        print(f"  MEAN P_forc {pfy.mean():.0f}  P_F {f.groupby('y').P_F.sum().mean():.0f}  P_ERA {f.groupby('y').P_ERA.sum().mean():.0f} mm/yr; "
              f"forcing-P_F max |diff| {np.nanmax(np.abs(pfy.to_numpy() - f.groupby('y').P_F.sum().reindex(pfy.index).to_numpy())):.2f} mm", flush=True)
    print(f"  P months flagged ({len(flags_p)}): " + "; ".join(flags_p[:40]) + (" ..." if len(flags_p) > 40 else ""), flush=True)
    print(f"  SW months flagged ({len(flags_s)}): " + "; ".join(flags_s[:30]) + (" ..." if len(flags_s) > 30 else ""), flush=True)
    if s == "US-Me2":
        print("  Me2 monthly 2020-2022: ym SW_F SW_ERA SWqc2% | P_F P_ERA", flush=True)
        g = f[f.y >= 2020]
        t = g.groupby(["y", "m"]).agg(SF=("SW_IN_F", "mean"), SE=("SW_IN_ERA", "mean"), q=("SW_IN_F_QC", lambda x: 100 * (x == 2).mean()), PF=("P_F", "sum"), PE=("P_ERA", "sum"))
        print("   " + " | ".join(f"{y}-{mm:02d} {r.SF:.0f}/{r.SE:.0f}/{r.q:.0f}% P{r.PF:.0f}/{r.PE:.0f}" for (y, mm), r in t.iterrows()), flush=True)
        g = f[f.y == 2002]
        t = g.groupby("m").agg(PF=("P_F", "sum"), PE=("P_ERA", "sum"), q=("P_F_QC", lambda x: 100 * (x == 0).mean()))
        print("  Me2 2002 monthly P_F/P_ERA/QC0%: " + " ".join(f"{mm:02d}:{r.PF:.0f}/{r.PE:.0f}/{r.q:.0f}" for mm, r in t.iterrows()), flush=True)


def main():
    print("B3_02 PRECIP / SW SOURCE AUDIT | READ ONLY", flush=True)
    man = json.loads(M.S07.read_text())
    sites = sys.argv[1:] or list(M.SITES)
    for s in sites:
        try: site(s, man)
        except Exception as e: print(f"  {s} ERROR {type(e).__name__}: {e}", flush=True)
    print("\nB3_02 DONE | no files written, no jobs", flush=True)


if __name__ == "__main__":
    main()
