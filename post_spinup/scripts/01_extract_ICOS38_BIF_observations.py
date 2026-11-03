#!/usr/bin/env python3
"""Extract observed vegetation structure and soil carbon for the ICOS 38 sites from BADM (BIF) rows.

Input: bif_key_groups_rows.csv written by 00_inventory_site_BIF_badm_readonly.py
       (on IRIDIS: ~/BIF_inventory/bif_key_groups_rows.csv).

Outputs (to --out):
  ICOS38_BIF_observations_long.csv  one row per BIF record (Mean / single value only) of the groups below
  ICOS38_BIF_structure_summary.csv  one row per site: the reference value chosen for each variable, its year,
                                    plot type and a flag column explaining every choice that is not plain

Groups: GRP_BIOMASS, GRP_BASAL_AREA, GRP_TREES_NUM, GRP_DBH, GRP_HEIGHTC, GRP_LAI, GRP_SOIL_STOCK,
        GRP_SPP_O, GRP_SPP, GRP_IGBP.

Selection rules (also written to the README):
  * Statistic: "Mean", "Expert estimate", "Single observation" or empty. SD, min, max, percentiles are dropped.
  * Plot type from the APPROACH text: ICOS continuous measurement plots (CP) > first-order sparse plots (SP-I) >
    any other survey (OTHER). The reference value is the latest year of the best plot type.
  * Stand level = record without species (or species "Total"), status not Dead, vegetation type Tree / Deciduous Tree / Evergreen
    Tree / empty. If both "Tree" and leaf-type records exist, "Tree" is used; otherwise leaf types are summed.
    Duplicate records of the same key keep the one with the largest STATISTIC_NUMBER.
  * Biomass is converted to kg dry mass m-2. gC m-2 is divided by 1000 and by 0.5 (carbon fraction); such
    values are flagged. Tree biomass is summarised only for forest IGBP classes (ENF, EBF, DBF, DNF, MF); grass harvest biomass stays in
    the long table.
  * LAI: per year the maximum of the mean values (canopy "Total" if reported, else "Overstory"); the site value
    is the median of these annual maxima. LAI_TYPE (LAI / PAI / GAI) is reported with it.
  * Soil organic C: the ETC "Cumulative stock / Full profile" record if present, else the sum of
    non-overlapping ETC layers of the latest date, else the latest non-ETC record starting at the surface
    (flagged). Reported in kg C m-2 (input gC m-2) with its depth; < 3 kgC m-2 over 30+ cm is flagged.
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

ICOS38 = ("DE-Tha NL-Loo DE-Hai RU-Fyo DK-Sor IL-Yat CZ-BK1 IT-Ren FR-Hes FR-FBn DE-Hzd CH-Dav BE-Vie IT-Lav "
          "BE-Bra FR-Fon GL-ZaH IT-Noe AT-Neu FI-Sod CH-Aws CH-Cha CH-Fru CH-Lae CZ-Stn DE-Lnf DE-Obe ES-Agu "
          "ES-LJu IT-Col DE-Gri DE-RuR FI-Hyy FI-Let FR-Pue GF-Guy IT-MBo IT-Tor").split()
GROUPS = {"GRP_BIOMASS": "BIOMASS", "GRP_BASAL_AREA": "BASAL_AREA", "GRP_TREES_NUM": "TREES_NUM",
          "GRP_DBH": "DBH", "GRP_HEIGHTC": "HEIGHTC", "GRP_LAI": "LAI", "GRP_SOIL_STOCK": "SOIL_STOCK_C_ORG",
          "GRP_SPP_O": "SPP_O_PERC", "GRP_SPP": "SPP_O_PERC", "GRP_IGBP": "IGBP"}
KEEP_STAT = {"", "mean", "expert estimate", "single observation"}
TREE_TYPES = {"", "tree", "deciduous tree", "evergreen tree"}
FOREST_IGBP = {"ENF", "EBF", "DBF", "DNF", "MF"}
PLOT_RANK = {"CP": 0, "SP-I": 1, "OTHER": 2}


def newest_source(d):
    """A site can have two BIF files (FI-Hyy: data to 2025 and to 2026). Keep the one with the latest end year."""
    end = d.source.str.extract(r"_BIF_\d{4}-(\d{4})_")[0].astype(float)
    d = d.assign(_end=end)
    best = d.groupby("site")._end.transform("max")
    return d[d._end == best].drop(columns="_end")


def records(d, group, prefix):
    s = d[d.VARIABLE_GROUP == group]
    if s.empty:
        return pd.DataFrame()
    w = s.pivot_table(index=["site", "GROUP_ID", "source"], columns="VARIABLE", values="DATAVALUE",
                      aggfunc="first").reset_index()

    def col(name):
        return w[name].fillna("").astype(str) if name in w else pd.Series("", index=w.index)

    p = "SOIL_STOCK" if group == "GRP_SOIL_STOCK" else ("SPP" if group in ("GRP_SPP_O", "GRP_SPP") else prefix)
    stat = col(f"{prefix}_STATISTIC") if group not in ("GRP_SPP_O", "GRP_SPP") else col("SPP_O_PERC_STATISTIC")
    date = col(f"{p}_DATE").where(col(f"{p}_DATE") != "", col(f"{p}_DATE_END"))
    date = date.where(date != "", col(f"{p}_DATE_START"))
    if group in ("GRP_SPP_O", "GRP_SPP"):
        for alt in ("SPP_O_DATE", "SPP_O_DATE_END", "SPP_DATE_END", "SPP_O_DATE_START", "SPP_DATE_START"):
            date = date.where(date != "", col(alt))
    appr = col(f"{p}_APPROACH") if group not in ("GRP_SPP_O", "GRP_SPP") else col("SPP_O_PERC_APPROACH")
    plot = np.where(appr.str.contains("Continuous Measurement", case=False), "CP",
                    np.where(appr.str.contains("first-order|Sparse", case=False), "SP-I", "OTHER"))
    if group in ("GRP_SPP_O", "GRP_SPP"):   # species name is in SPP_O_SPP (some sites) or SPP_O (ETC layout)
        spp = col("SPP_O_SPP").where(col("SPP_O_SPP") != "", col("SPP_O"))
    else:
        spp = col(f"{prefix}_SPP")
    out = pd.DataFrame({
        "site": w.site, "group": group, "group_id": w.GROUP_ID, "source_file": w.source.str.split("/").str[-1],
        "variable": prefix, "value_raw": col(prefix), "unit": col(f"{prefix}_UNIT"),
        "statistic": stat, "stat_n": pd.to_numeric(col(f"{prefix}_STATISTIC_NUMBER"), errors="coerce"),
        "date": date, "year": pd.to_numeric(date.str[:4], errors="coerce"), "plot_type": plot,
        "approach": appr.str[:160], "species": spp,
        "vegtype": col(f"{prefix}_VEGTYPE") if group not in ("GRP_SPP_O", "GRP_SPP") else
        col("SPP_O_PERC_VEGTYPE").where(col("SPP_O_PERC_VEGTYPE") != "", col("SPP_O_VEGTYPE")),
        "organ": col(f"{prefix}_ORGAN"), "status": col(f"{prefix}_VEG_STATUS"),
        "lai_type": col("LAI_TYPE"), "lai_canopy": col("LAI_CANOPY_TYPE"), "lai_method": col("LAI_METHOD"),
        "soil_horizon": col("SOIL_STOCK_HORIZON"), "soil_comment": col("SOIL_STOCK_COMMENT"),
        "depth_min_cm": pd.to_numeric(col("SOIL_STOCK_PROFILE_MIN"), errors="coerce"),
        "depth_max_cm": pd.to_numeric(col("SOIL_STOCK_PROFILE_MAX"), errors="coerce"),
    })
    if group in ("GRP_SPP_O", "GRP_SPP"):
        # second ETC layout: percentage in SPP_O, species in SPP_O_SPP, statistic/approach without _PERC
        alt = (col("SPP_O_PERC") == "") & (col("SPP_O_SPP") != "")
        out.loc[alt, "value_raw"] = col("SPP_O")[alt]
        out.loc[alt, "statistic"] = col("SPP_O_STATISTIC")[alt]
        a2 = col("SPP_O_APPROACH")[alt]
        out.loc[alt, "approach"] = a2.str[:160]
        out.loc[alt, "plot_type"] = np.where(a2.str.contains("Continuous Measurement", case=False), "CP",
                                             np.where(a2.str.contains("first-order|Sparse", case=False), "SP-I", "OTHER"))
        out = out[~out.approach.str.contains("DEAD", case=False)]
    out["value"] = pd.to_numeric(out.value_raw, errors="coerce")
    out = out[out.statistic.str.strip().str.lower().isin(KEEP_STAT)]
    out = out[(out.value_raw != "")]
    return out


def latest_best(df):
    """Rows of the best plot type and, within it, the latest year."""
    df = df.assign(_r=df.plot_type.map(PLOT_RANK)).dropna(subset=["year"])
    if df.empty:
        return df
    df = df[df._r == df._r.min()]
    return df[df.year == df.year.max()].drop(columns="_r")


def stand_level(df):
    """Stand-level rows (no species, not dead, tree vegetation type), duplicates collapsed."""
    t = df[df.species.str.lower().str.strip(". ").isin({"", "total"}) & (df.status.str.lower() != "dead")
           & df.vegtype.str.lower().isin(TREE_TYPES)]
    if t.empty:
        return t
    t = t.sort_values("stat_n", ascending=False).drop_duplicates(["vegtype", "organ"])
    if (t.vegtype.str.lower() == "tree").any():
        t = t[t.vegtype.str.lower() == "tree"]
    return t


def biomass(df):
    flags = []
    df = df[df.vegtype.str.lower().isin(TREE_TYPES)]
    df = df[~df.organ.str.lower().isin({"roots"})]
    if df.empty:
        return None
    sel = latest_best(df)
    st = stand_level(sel)
    total = st[st.organ.str.lower().isin({"total ag", "total aboveground", "wood ag"})]
    if total.empty:
        total = st[st.organ == ""]
        if total.empty:
            return None
        flags.append("organ not reported")
    if (total.organ.str.lower() == "wood ag").any():
        flags.append("wood AG only (no foliage)")
    v = []
    for _, r in total.iterrows():
        u = r.unit.strip().lower()
        if u in ("gc m-2", "gc/m2"):
            v.append(r.value / 1000 / 0.5); flags.append("gC m-2 converted with C fraction 0.5")
        else:
            v.append(r.value)
            if u not in ("kgdm m-2", ""):
                flags.append(f"unit {r.unit}")
    return {"agb_tree_kgDM_m2": round(sum(v), 3), "agb_year": int(sel.year.iloc[0]),
            "agb_plot": sel.plot_type.iloc[0], "agb_flags": "; ".join(dict.fromkeys(flags))}


def stand_sum(df, name, how="sum"):
    df = df[df.vegtype.str.lower().isin(TREE_TYPES)]
    sel = latest_best(df)
    if sel.empty:
        return None
    st = stand_level(sel)
    flag = ""
    if st.empty:
        st = sel[sel.species != ""].sort_values("stat_n", ascending=False).drop_duplicates("species")
        flag = "summed over species (no stand record)" if how == "sum" else "mean of species values"
        if st.empty:
            return None
    val = st.value.sum() if how == "sum" else st.value.mean()
    return {name: round(float(val), 3), f"{name}_year": int(sel.year.iloc[0]),
            f"{name}_plot": sel.plot_type.iloc[0], f"{name}_flags": flag}


def height(df):
    if df.empty:
        return None
    st = df[(df.species == "") & (df.status.str.lower() != "dead")].dropna(subset=["year"])
    flag = ""
    if st.empty:
        st = df.dropna(subset=["year"]); flag = "mean of species means (no stand record)"
    sel = latest_best(st)
    if sel.empty:
        return None
    val = sel.sort_values("stat_n", ascending=False).value.iloc[0] if not flag else sel.value.mean()
    if (sel.statistic.str.lower() == "expert estimate").all():
        flag = (flag + "; " if flag else "") + "expert estimate"
    return {"canopy_height_m": round(float(val), 2), "canopy_height_year": int(sel.year.iloc[0]),
            "canopy_height_flags": flag}


def lai(df):
    df = df.dropna(subset=["year", "value"])
    if df.empty:
        return None
    canopy = "Total" if (df.lai_canopy == "Total").any() else ("Overstory" if (df.lai_canopy == "Overstory").any() else "")
    df = df[df.lai_canopy == canopy] if canopy else df
    typ = df.lai_type.replace("", "unspecified").value_counts().index[0]
    df = df[df.lai_type.replace("", "unspecified") == typ]
    df = df[df.species == ""] if (df.species == "").any() else df
    annual = df.groupby("year").value.max()
    return {"lai_peak_median": round(float(annual.median()), 2), "lai_type": typ, "lai_canopy": canopy or "unspecified",
            "lai_years": f"{int(annual.index.min())}-{int(annual.index.max())}", "lai_n_years": int(annual.size)}


def soc(df):
    df = df.dropna(subset=["value"])
    if df.empty:
        return None
    flags = []
    etc = df[df.soil_comment.str.contains("Cumulative|Layer aggregation|O and M", case=False)]
    if etc.empty:
        # non-ETC records: use the latest one that starts at the surface
        top = df[df.depth_min_cm.fillna(0) <= 0]
        df = top if not top.empty else df
        flags.append("non-ETC soil record; depth and unit not verified")
    else:
        df = etc
    df = df[df.date == df.date.max()]
    cum = df[df.soil_comment.str.contains("Cumulative", case=False)]
    if not cum.empty:
        r = cum.iloc[0]; val, lo, hi = r.value, r.depth_min_cm, r.depth_max_cm
        lay = df[df.soil_comment.str.contains("O and M", case=False)]
        if len(lay) >= 2 and abs(lay.value.sum() - val) > 0.05 * val:
            flags.append(f"O+M layers sum {lay.value.sum():.0f} differs from cumulative {val:.0f} gC m-2")
    else:
        lay = df[df.soil_comment.str.contains("Layer aggregation", case=False)]
        lay = lay if not lay.empty else df
        lay = lay.drop_duplicates(["depth_min_cm", "depth_max_cm"])
        val, lo, hi = lay.value.sum(), lay.depth_min_cm.min(), lay.depth_max_cm.max()
        if len(lay) == 1:
            flags.append("single record")
    if val < 3000 and (hi or 0) >= 30:
        flags.append("implausibly low for a 30+ cm profile; verify unit")
    return {"soc_kgC_m2": round(float(val) / 1000, 2), "soc_depth_cm": f"{lo:g} to {hi:g}",
            "soc_year": int(str(df.date.iloc[0])[:4]), "soc_flags": "; ".join(flags)}


def species(df):
    df = df.dropna(subset=["value", "year"])
    df = df[~df.species.str.lower().str.strip(". ").isin({"", "total"})]
    if df.empty:
        return None
    sel = latest_best(df).sort_values("value", ascending=False).drop_duplicates("species")
    top = "; ".join(f"{s.split(' (')[0]} {v:.0f}%" for s, v in list(zip(sel.species, sel.value))[:6] if v >= 1)
    return {"species_pct": top, "species_year": int(sel.year.iloc[0]), "species_plot": sel.plot_type.iloc[0]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bif-rows", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(a.bif_rows, dtype=str, keep_default_na=False)
    d = newest_source(d[d.site.isin(ICOS38)])
    recs = {g: records(d, g, p) for g, p in GROUPS.items()}
    long = pd.concat([r for g, r in recs.items() if g != "GRP_IGBP" and not r.empty], ignore_index=True)
    long.drop(columns="value_raw").to_csv(a.out / "ICOS38_BIF_observations_long.csv", index=False)

    rows = []
    for site in ICOS38:
        row = {"site": site}
        sub = {g: (r[r.site == site] if not r.empty else r) for g, r in recs.items()}
        if not sub["GRP_IGBP"].empty:
            row["igbp_bif"] = sub["GRP_IGBP"].sort_values("date").value_raw.iloc[-1]
        forest = row.get("igbp_bif", "") in FOREST_IGBP
        for res in (biomass(sub["GRP_BIOMASS"]) if forest and not sub["GRP_BIOMASS"].empty else None,
                    stand_sum(sub["GRP_BASAL_AREA"], "basal_area_m2_ha") if not sub["GRP_BASAL_AREA"].empty else None,
                    stand_sum(sub["GRP_TREES_NUM"], "tree_density_ha") if not sub["GRP_TREES_NUM"].empty else None,
                    stand_sum(sub["GRP_DBH"], "mean_dbh_cm", how="mean") if not sub["GRP_DBH"].empty else None,
                    height(sub["GRP_HEIGHTC"]) if not sub["GRP_HEIGHTC"].empty else None,
                    lai(sub["GRP_LAI"]) if not sub["GRP_LAI"].empty else None,
                    soc(sub["GRP_SOIL_STOCK"]) if not sub["GRP_SOIL_STOCK"].empty else None,
                    species(pd.concat([sub["GRP_SPP_O"], sub["GRP_SPP"]])) if not (
                        sub["GRP_SPP_O"].empty and sub["GRP_SPP"].empty) else None):
            if res:
                row.update(res)
        row["bif_source_file"] = d[d.site == site].source.str.split("/").str[-1].iloc[0] if (d.site == site).any() else "NO_BIF"
        rows.append(row)
    summ = pd.DataFrame(rows)
    summ.to_csv(a.out / "ICOS38_BIF_structure_summary.csv", index=False)
    print(summ.drop(columns=[c for c in summ if c.endswith("_flags") or c.endswith("_file")]).to_string())


if __name__ == "__main__":
    main()
