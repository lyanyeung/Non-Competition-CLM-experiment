#!/usr/bin/env python3
"""Turn the PROFOUND extract (script 05) into evaluation targets for CZ-BK1, IT-Col, FI-Hyy and DK-Sor.

Input: the ICOS38_extract folder written by 05_extract_PROFOUND_ICOS38.py (STAND, SOIL, CO2_ISIMIP, ...).
Outputs (in --out):
  PROFOUND_stand_totals.csv     one row per site and year: density, basal area, BA-weighted height and DBH,
                                stem / foliage / branch / root biomass (kg DM m-2), LAI, summed over species
  PROFOUND_thinning_events.csv  year-to-year drops in stem number (> 5 %) with the basal-area change, for the
                                stand total and for the main species alone (mixed FI-Hyy stand).
                                A drop between year t-1 and t is listed under t. Drops with a basal-area
                                increase are flagged as possible mortality of small trees rather than thinning.
  PROFOUND_soil_carbon.csv      SOC stock per layer and summed, from C % x bulk density x thickness.
                                No stone/gravel correction (gravel is reported only at FI-Hyy and is kept in
                                a separate column), so totals are upper bounds.
  co2_global_annual_ISIMIP.csv  global annual CO2 (identical at all sites): historical 1765-2015 and the four
                                RCPs 2006-2100, wide.

Licences: database CC BY-NC 4.0; STAND/TREE/SOIL follow site-specific policies (POLICY_<site_id> views).
Keep these derived tables off public repositories until those policies are checked.

Usage:
  python3 06_derive_PROFOUND_targets.py --extract ICOS38_extract --out PROFOUND_derived
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ICOS = {3: "CZ-BK1", 5: "IT-Col", 12: "FI-Hyy", 21: "DK-Sor"}
BIOMASS = {"stemBiomass_kgha": "stem", "foliageBiomass_kgha": "foliage", "branchesBiomass_kgha": "branches",
           "rootBiomass_kgha": "root", "stumpCoarseRootBiomass_kgha": "stump_coarse_root",
           "aboveGroundBiomass_kgha": "aboveground"}


def wmean(x, w):
    m = x.notna() & w.notna() & (w > 0)
    return float(np.average(x[m], weights=w[m])) if m.any() else np.nan


def stand_totals(st):
    rows = []
    for (sid, yr), g in st.groupby(["site_id", "year"]):
        r = {"site": ICOS[sid], "profound_site": g.site.iloc[0], "year": int(yr),
             "species": "; ".join(sorted(g.species.dropna().unique())),
             "age_main_species": g.age.max(),
             "density_trees_ha": g.density_treeha.sum(min_count=1),
             "basal_area_m2_ha": g.ba_m2ha.sum(min_count=1),
             "height_BAweighted_m": wmean(g.heightBA_m, g.ba_m2ha),
             "dbh_BAweighted_cm": wmean(g.dbhBA_cm, g.ba_m2ha),
             "lai": g.lai.sum(min_count=1)}
        for col, name in BIOMASS.items():
            r[f"{name}_kgDM_m2"] = g[col].sum(min_count=1) / 1e4
        rows.append(r)
    df = pd.DataFrame(rows)
    # aboveground woody + foliage where stem is known (branches often missing -> lower bound)
    parts = df[["stem_kgDM_m2", "foliage_kgDM_m2", "branches_kgDM_m2"]]
    df["agb_from_parts_kgDM_m2"] = parts.sum(axis=1, min_count=1).where(df.stem_kgDM_m2.notna())
    df["agb_parts_note"] = np.where(df.branches_kgDM_m2.isna() & df.stem_kgDM_m2.notna(),
                                    "branches missing: lower bound", "")
    return df


def thinning_events(tot, min_drop=0.05):
    out = []
    for site, g in tot.sort_values("year").groupby("site"):
        g = g.set_index("year")
        yrs = list(g.index)
        for a, b in zip(yrs[:-1], yrs[1:]):
            n0, n1 = g.at[a, "density_trees_ha"], g.at[b, "density_trees_ha"]
            if pd.isna(n0) or pd.isna(n1) or n0 <= 0:
                continue
            drop = (n0 - n1) / n0
            if drop > min_drop:
                ba0, ba1 = g.at[a, "basal_area_m2_ha"], g.at[b, "basal_area_m2_ha"]
                dba = (ba1 - ba0) / ba0 if ba0 else np.nan
                out.append({"site": site, "interval": f"{a}-{b}", "year_listed": b, "density_before": n0,
                            "density_after": n1, "stem_number_change_pct": round(-100 * drop, 1),
                            "basal_area_before": round(ba0, 2), "basal_area_after": round(ba1, 2),
                            "basal_area_change_pct": round(100 * dba, 1),
                            "interpretation": "thinning/harvest (BA fell)" if dba < 0 else
                            "stems lost but BA rose: small-tree removal or mortality",
                            "multi_year_interval": (b - a) > 1})
    return pd.DataFrame(out)


def soil_carbon(soil):
    rows = []
    for sid, g in soil.groupby("site_id"):
        c = g.dropna(subset=["upperDepth_cm", "lowerDepth_cm"]).copy()
        c["top"] = c[["upperDepth_cm", "lowerDepth_cm"]].min(axis=1)
        c["bot"] = c[["upperDepth_cm", "lowerDepth_cm"]].max(axis=1)
        c["cfrac"] = c.c_percent.fillna(c.cOrg_percent) / 100
        bd = c.dropna(subset=["density_gcm3"])[["top", "bot", "density_gcm3"]]
        for r in c.dropna(subset=["cfrac"]).itertuples():
            if r.top < 0 or r.bot <= r.top:
                continue
            dens = r.density_gcm3
            if pd.isna(dens) and len(bd):  # thickness-weighted bulk density from the overlapping layers
                ov = [(min(r.bot, b.bot) - max(r.top, b.top), b.density_gcm3) for b in bd.itertuples()]
                ov = [(t, d) for t, d in ov if t > 0]
                dens = sum(t * d for t, d in ov) / sum(t for t, _ in ov) if ov else np.nan
            stock = r.cfrac * dens * (r.bot - r.top) * 10 if pd.notna(dens) else np.nan  # kg C m-2
            rows.append({"site": ICOS[sid], "top_cm": r.top, "bottom_cm": r.bot, "horizon": r.horizon,
                         "C_percent": round(100 * r.cfrac, 3), "bulk_density_gcm3": round(dens, 3) if pd.notna(dens) else np.nan,
                         "bulk_density_source": "same layer" if pd.notna(r.density_gcm3) else "thickness-weighted from BD profile",
                         "gravel_percent": getattr(r, "gravel_percent", np.nan),
                         "soc_kgC_m2": round(stock, 3) if pd.notna(stock) else np.nan})
    lay = pd.DataFrame(rows)
    tot = (lay.dropna(subset=["soc_kgC_m2"]).groupby("site")
           .agg(soc_kgC_m2_sum=("soc_kgC_m2", "sum"), depth_top_cm=("top_cm", "min"),
                depth_bottom_cm=("bottom_cm", "max"), n_layers=("soc_kgC_m2", "size")).reset_index())
    tot["soc_kgC_m2_sum"] = tot.soc_kgC_m2_sum.round(2)
    lay["layer"] = "layer"
    tot["layer"] = "TOTAL (mineral soil, no stone correction, organic layer excluded)"
    return pd.concat([lay, tot], ignore_index=True)


def co2_table(co2):
    g = co2[co2.site_id == co2.site_id.min()]
    w = g.pivot_table(index="year", columns="forcingCondition", values="co2_ppm")
    w = w[(w.index >= 1765) & (w.index <= 2100)]
    return w.reset_index()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    tot = stand_totals(pd.read_csv(a.extract / "STAND.csv"))
    tot.to_csv(a.out / "PROFOUND_stand_totals.csv", index=False)
    thin = thinning_events(tot)
    thin.insert(1, "level", "stand total")
    # main species alone (largest mean basal area); a thinning of it can be hidden in the stand total
    st = pd.read_csv(a.extract / "STAND.csv")
    main_sp = st.groupby(["site_id", "species"]).ba_m2ha.mean().reset_index().sort_values("ba_m2ha") \
        .groupby("site_id").tail(1)
    sp = st.merge(main_sp[["site_id", "species"]], on=["site_id", "species"])
    sp_thin = thinning_events(stand_totals(sp))
    if len(sp_thin):
        sp_thin.insert(1, "level", "main species: " + sp_thin.site.map(
            dict(zip(main_sp.site_id.map(ICOS), main_sp.species))))
        key = set(zip(thin.site, thin.interval))
        sp_thin = sp_thin[[(s_, i) not in key for s_, i in zip(sp_thin.site, sp_thin.interval)]]
        thin = pd.concat([thin, sp_thin], ignore_index=True).sort_values(["site", "year_listed"])
    thin.to_csv(a.out / "PROFOUND_thinning_events.csv", index=False)
    soc = soil_carbon(pd.read_csv(a.extract / "SOIL.csv"))
    soc.to_csv(a.out / "PROFOUND_soil_carbon.csv", index=False)
    co2 = co2_table(pd.read_csv(a.extract / "CO2_ISIMIP.csv"))
    co2.to_csv(a.out / "co2_global_annual_ISIMIP.csv", index=False)

    pd.set_option("display.width", 220)
    print(tot.groupby("site").agg(first=("year", "min"), last=("year", "max"), n=("year", "size")).to_string())
    print(thin.to_string(index=False))
    print(soc[soc.layer != "layer"].to_string(index=False))


if __name__ == "__main__":
    main()
