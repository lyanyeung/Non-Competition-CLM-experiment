#!/usr/bin/env python3
"""ICOS38 soil texture evidence, following the OzFlux/JapanFlux Soil topic rules
(CLM-FATES-single-site-workflows, examples/OzFlux_JapanFlux_Soil, branch oz-jp-soil-texture-20261103).

Evidence sources (numbers only from records that state them; texture classes are never converted to numbers):
  BIF  our own FLUXNET v1.3 BIF files, GRP_SOIL_TEX (ICOS-ETC or site lab): sand / silt / clay by depth, rock
       fraction, wilting point / field capacity / saturation; plus GRP_SOIL_DEPTH and soil classification groups.
       verification SOURCE_FILE_READ.
  FL20 Flechard et al. (2020) Biogeosciences 17:1583, supplement Table S4 (one value per site, depth not stated,
       so use_numeric=NO until a depth is assigned by hand). verification PUBLISHED_TABLE_READ.
  PRO  PROFOUND v0.3 SOIL view (CZ-BK1, IT-Col, FI-Hyy, DK-Sor): layers with depths. FI-Hyy fractions include
       gravel and are renormalised to the fine earth. verification DATABASE_READ.

Tiers as in the OZ/JP topic: T1 site measured (depth stated) > T3 SoilGrids at the tower (script 07 coordinates +
the OZ/JP SoilGrids script) > T4 keep surface. Particle-size scheme is kept as reported: ICOS-ETC follows
ISO 11277 (silt 2-63 um), close to but not identical to USDA (2-50 um); CLM expects USDA.

Outputs (post_spinup/ICOS38/soil/):
  ICOS38_soil_texture_evidence.csv   one row per record (OZ/JP literature_soil_evidence layout)
  ICOS38_soil_site_summary.csv       per site: T1 numeric coverage, 0-30 cm T1 sand/clay, soil depth, class, flags

Usage:
  python3 08_ICOS38_soil_texture_evidence.py --bif-rows ~/BIF_inventory/bif_key_groups_rows.csv \\
          --profound-soil <PROFOUND_DIR>/ICOS38_extract/SOIL.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "ICOS38"
PROFOUND_ICOS = {3: "CZ-BK1", 5: "IT-Col", 12: "FI-Hyy", 21: "DK-Sor"}
FIELDS = ["evidence_id", "site", "evidence_type", "use_numeric", "depth_top_cm", "depth_bottom_cm", "sand_pct",
          "silt_pct", "clay_pct", "size_scheme", "texture_class", "bulk_density_g_cm3", "organic_carbon_pct",
          "coarse_fragments_pct", "soil_depth_cm", "soil_classification", "wilting_point_m3m3",
          "field_capacity_m3m3", "saturation_m3m3", "tower_specific", "spatial_scope", "method", "citation", "url",
          "locator", "verification", "note", "curation"]
FL20_URL = "https://doi.org/10.5194/bg-17-1583-2020-supplement"
PRO_URL = "https://doi.org/10.5880/PIK.2020.006"
# depth fields in the BIF: SOIL_TEX_PROFILE_MIN/MAX in cm, except where they are clearly metres (DE-Gri 2002)
METRE_GROUPS = {"DE-Gri": {"4469", "4470", "4471"}}


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def bif_records(rows, sites):
    out = []
    t = rows[rows.SITE_ID.isin(sites) & (rows.VARIABLE_GROUP == "GRP_SOIL_TEX")]
    w = t.pivot_table(index=["SITE_ID", "source", "GROUP_ID"], columns="VARIABLE", values="DATAVALUE",
                      aggfunc="first").reset_index()
    for c in ["SOIL_TEX_SAND", "SOIL_TEX_SILT", "SOIL_TEX_CLAY", "SOIL_TEX_ROCK", "SOIL_TEX_SAND_STATISTIC",
              "SOIL_TEX_PROFILE_MIN", "SOIL_TEX_PROFILE_MAX", "SOIL_TEX_HORIZON", "SOIL_TEX_DATE",
              "SOIL_TEX_APPROACH", "SOIL_TEX_COMMENT", "SOIL_TEX_WILT", "SOIL_TEX_FIELD_CAP", "SOIL_TEX_SAT"]:
        if c not in w:
            w[c] = np.nan
    w = w[w.SOIL_TEX_SAND_STATISTIC.fillna("Mean").str.lower().isin(["mean", "single observation"])]
    # ICOS-ETC stores sand, clay (and their SDs) in separate groups at the same depth/date: merge per depth
    key = ["SITE_ID", "source", "SOIL_TEX_DATE", "SOIL_TEX_PROFILE_MIN", "SOIL_TEX_PROFILE_MAX"]
    for k, g in w.groupby(key, dropna=False):
        site = k[0]
        vals = {c: pd.to_numeric(g[c], errors="coerce").dropna() for c in
                ("SOIL_TEX_SAND", "SOIL_TEX_SILT", "SOIL_TEX_CLAY", "SOIL_TEX_ROCK", "SOIL_TEX_WILT",
                 "SOIL_TEX_FIELD_CAP", "SOIL_TEX_SAT")}
        first = {c: (v.iloc[0] if len(v) else np.nan) for c, v in vals.items()}
        top, bot = f(k[3]), f(k[4])
        if set(g.GROUP_ID.astype(str)) & METRE_GROUPS.get(site, set()):
            top, bot = top * 100, bot * 100
        sand, silt, clay = first["SOIL_TEX_SAND"], first["SOIL_TEX_SILT"], first["SOIL_TEX_CLAY"]
        note = []
        if np.isnan(silt) and not np.isnan(sand) and not np.isnan(clay):
            silt = round(100 - sand - clay, 2)
            note.append("silt by difference")
        if site == "DE-Hai" and silt < 10 and sand + silt + clay < 80:
            note.append("one 0-5 cm record has silt 4.59 (sum 59 %), a likely typo of 45.9; the duplicate record "
                        "with 45.9 is kept")
            continue
        has_num = not (np.isnan(sand) and np.isnan(clay))
        has_depth = not (np.isnan(top) or np.isnan(bot))
        if not has_num and np.isnan(first["SOIL_TEX_ROCK"]):
            continue
        out.append({
            "site": site, "evidence_type": "MEASURED_SITE_LAYER" if has_num else "MEASURED_SITE_ROCK_ONLY",
            "use_numeric": "YES" if has_num and has_depth else "NO",
            "depth_top_cm": top, "depth_bottom_cm": bot, "sand_pct": sand, "silt_pct": silt, "clay_pct": clay,
            "size_scheme": "ISO 11277 (silt 2-63 um)" if "ISO" in str(g.SOIL_TEX_APPROACH.iloc[0]) or
            "ICOS" in str(g.SOIL_TEX_APPROACH.iloc[0]) else "UNSTATED",
            "coarse_fragments_pct": first["SOIL_TEX_ROCK"], "texture_class": "",
            "wilting_point_m3m3": first["SOIL_TEX_WILT"], "field_capacity_m3m3": first["SOIL_TEX_FIELD_CAP"],
            "saturation_m3m3": first["SOIL_TEX_SAT"], "tower_specific": "YES", "spatial_scope": "station plots",
            "method": str(g.SOIL_TEX_APPROACH.dropna().iloc[0]) if g.SOIL_TEX_APPROACH.notna().any() else "",
            "citation": f"BIF GRP_SOIL_TEX ({Path(str(k[1])).name})", "url": "",
            "locator": f"GROUP_ID {','.join(sorted(g.GROUP_ID.astype(str)))}; date {k[2]}",
            "verification": "SOURCE_FILE_READ", "note": "; ".join(note),
            "curation": "USED (T1)" if has_num and has_depth else
            ("NOT USED: no depth" if has_num else "rock fraction only (context)")})
    return out


def bif_class_depth(rows, sites):
    out = {}
    for s in sites:
        r = rows[(rows.SITE_ID == s) & rows.VARIABLE_GROUP.isin(
            ["GRP_SOIL_CLASSIFICATION", "GRP_SOIL_WRB_GROUP", "GRP_SOIL_ORDER", "GRP_SOIL_DEPTH"])]
        cls = r[r.VARIABLE.isin(["SOIL_CLASSIFICATION", "SOIL_WRB_GROUP", "SOIL_ORDER"])].DATAVALUE.unique()
        dep = r[(r.VARIABLE == "SOIL_DEPTH")].DATAVALUE
        d = pd.to_numeric(dep, errors="coerce").dropna()
        out[s] = {"bif_class": "; ".join(cls), "bif_soil_depth_cm": d.max() if len(d) else np.nan}
    return out


def flechard_records(fl):
    out = []
    for r in fl.itertuples():
        out.append({
            "site": r.site, "evidence_type": "MEASURED_SITE_BULK", "use_numeric": "NO",
            "depth_top_cm": np.nan, "depth_bottom_cm": np.nan, "sand_pct": f(r.s4_sand_pct),
            "silt_pct": f(r.s4_silt_pct), "clay_pct": f(r.s4_clay_pct), "size_scheme": "UNSTATED",
            "texture_class": r.s4_texture, "soil_depth_cm": r.s4_soil_depth_m, "soil_classification": r.s4_fao_class,
            "wilting_point_m3m3": f(r.s4_wp_m3m3), "field_capacity_m3m3": f(r.s4_fc_m3m3),
            "saturation_m3m3": f(r.s4_sat_m3m3), "tower_specific": "YES", "spatial_scope": "site",
            "method": "not stated", "citation": "Flechard et al. (2020) Biogeosciences 17:1583, supplement",
            "url": FL20_URL, "locator": "Table S4", "verification": "PUBLISHED_TABLE_READ",
            "note": "soil depth column is in m; texture depth not stated",
            "curation": "NOT USED: depth not stated (assign by hand, or use as check)"})
    return out


def profound_records(soil):
    out = []
    for r in soil.itertuples():
        site = PROFOUND_ICOS.get(r.site_id)
        if site is None or pd.isna(r.upperDepth_cm) or pd.isna(r.lowerDepth_cm):
            continue
        sand, silt, clay = f(r.sand_percent), f(r.silt_percent), f(r.clay_percent)
        if np.isnan(sand) and np.isnan(clay):
            continue
        top, bot = sorted([f(r.upperDepth_cm), f(r.lowerDepth_cm)])
        gravel = f(getattr(r, "gravel_percent", np.nan))
        note = ""
        tot = np.nansum([sand, silt, clay])
        if site == "FI-Hyy" and tot < 95:  # fractions of the whole soil incl. gravel -> fine earth
            sand, silt, clay = (round(100 * x / tot, 1) for x in (sand, silt, clay))
            note = f"renormalised to fine earth (reported sum {tot:.1f} %, gravel {gravel} %)"
        out.append({
            "site": site, "evidence_type": "MEASURED_SITE_LAYER", "use_numeric": "YES",
            "depth_top_cm": top, "depth_bottom_cm": bot, "sand_pct": sand, "silt_pct": silt, "clay_pct": clay,
            "size_scheme": "UNSTATED", "texture_class": str(r.texture) if pd.notna(r.texture) else "",
            "bulk_density_g_cm3": f(r.density_gcm3), "organic_carbon_pct": f(r.c_percent),
            "coarse_fragments_pct": gravel, "soil_classification": str(r.type_fao) if pd.notna(r.type_fao) else "",
            "tower_specific": "YES", "spatial_scope": "PROFOUND site profile", "method": "not stated",
            "citation": "PROFOUND DB v0.3 (Reyer et al. 2020), SOIL view", "url": PRO_URL,
            "locator": f"site_id {r.site_id}, horizon {r.horizon}", "verification": "DATABASE_READ", "note": note,
            "curation": "USED (T1)"})
    return out


def layer_mean(ev, top=0, bot=30):
    """Thickness-weighted 0-30 cm sand/clay from use_numeric=YES layers of one source."""
    w = []
    for r in ev.itertuples():
        ov = min(bot, r.depth_bottom_cm) - max(top, r.depth_top_cm)
        if ov > 0 and not np.isnan(r.sand_pct) and not np.isnan(r.clay_pct):
            w.append((ov, r.sand_pct, r.clay_pct))
    if not w:
        return np.nan, np.nan, 0
    t = sum(x[0] for x in w)
    return (round(sum(x[0] * x[1] for x in w) / t, 1), round(sum(x[0] * x[2] for x in w) / t, 1), t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bif-rows", required=True, type=Path)
    ap.add_argument("--profound-soil", type=Path)
    ap.add_argument("--out", type=Path, default=HERE / "soil")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    info = pd.read_csv(HERE / "ICOS38_post_spinup_start_info.csv")
    sites = list(info.site)
    rows = pd.read_csv(a.bif_rows, dtype=str, low_memory=False)
    ev = bif_records(rows, sites)
    ev += flechard_records(pd.read_csv(HERE / "Flechard2020_supplement_ICOS38.csv", dtype=str))
    if a.profound_soil and a.profound_soil.is_file():
        ev += profound_records(pd.read_csv(a.profound_soil))
    E = pd.DataFrame(ev)
    E = E.sort_values(["site", "verification", "depth_top_cm"]).reset_index(drop=True)
    E["evidence_id"] = E.site + "-S" + (E.groupby("site").cumcount() + 1).map("{:02d}".format)
    for c in FIELDS:
        if c not in E:
            E[c] = ""
    E[FIELDS].to_csv(a.out / "ICOS38_soil_texture_evidence.csv", index=False, lineterminator="\n")

    cd = bif_class_depth(rows, sites)
    summ = []
    for s in sites:
        e = E[E.site == s]
        t1 = e[(e.use_numeric == "YES")]
        srcs = sorted(t1.verification.unique())
        best = None
        for v in ("SOURCE_FILE_READ", "DATABASE_READ"):  # BIF first, then PROFOUND
            sub = t1[t1.verification == v]
            if len(sub):
                best = (v, *layer_mean(sub), sub.depth_bottom_cm.max())
                break
        fl = e[e.verification == "PUBLISHED_TABLE_READ"]
        flags = []
        if best and len(fl) and not np.isnan(fl.sand_pct.iloc[0]):
            if abs(fl.sand_pct.iloc[0] - best[1]) > 25 or abs(fl.clay_pct.iloc[0] - best[2]) > 20:
                flags.append(f"CONFLICT Flechard S4 {fl.sand_pct.iloc[0]:.0f}/{fl.clay_pct.iloc[0]:.0f} vs T1 "
                             f"{best[1]}/{best[2]} (sand/clay)")
        pro = t1[t1.verification == "DATABASE_READ"]
        if len(pro) and len(fl) and not np.isnan(fl.clay_pct.iloc[0]):
            ps, pc, _ = layer_mean(pro)
            if not np.isnan(pc) and abs(pc - fl.clay_pct.iloc[0]) > 20:
                flags.append(f"CONFLICT PROFOUND 0-30 cm {ps}/{pc} vs Flechard S4 "
                             f"{fl.sand_pct.iloc[0]:.0f}/{fl.clay_pct.iloc[0]:.0f}")
        nodepth = e[(e.use_numeric == "NO") & e.sand_pct.notna() & (e.verification == "SOURCE_FILE_READ")]
        if len(nodepth):
            flags.append("measured numbers without depth in BIF (assign depth by hand)")
        if s == "CZ-BK1":
            flags.append("BIF ICOS-ETC and PROFOUND agree; Flechard S4 sand/silt probably swapped")
        if s == "IT-Col":
            flags.append("Humic Alisol on limestone (argic, clay-enriched) supports Flechard; PROFOUND sandy "
                         "values suspect")
        depth = fl.soil_depth_cm.iloc[0] if len(fl) else ""
        cls = "; ".join(x for x in [cd[s]["bif_class"], fl.soil_classification.iloc[0] if len(fl) else ""] if x)
        if "peat" in cls.lower() or "histosol" in cls.lower() or (len(fl) and "Peat" in str(fl.texture_class.iloc[0])):
            flags.append("ORGANIC/peat soil: mineral texture not representative")
        summ.append({"site": s, "ecosystem": info.loc[info.site == s, "ecosystem"].iloc[0],
                     "t1_numeric_sources": ";".join(srcs) or "NONE",
                     "t1_source_used": best[0] if best else "",
                     "t1_sand_0_30cm": best[1] if best else np.nan, "t1_clay_0_30cm": best[2] if best else np.nan,
                     "t1_deepest_cm": best[4] if best else np.nan,
                     "flechard_S4_sand_silt_clay": "" if not len(fl) else
                     f"{fl.sand_pct.iloc[0]}/{fl.silt_pct.iloc[0]}/{fl.clay_pct.iloc[0]}",
                     "flechard_S4_texture": fl.texture_class.iloc[0] if len(fl) else "",
                     "soil_depth_m_flechard": depth, "bif_soil_depth_cm": cd[s]["bif_soil_depth_cm"],
                     "soil_classification": cls,
                     "proposed_tier": ("HOLD: measured sources disagree" if s == "IT-Col" else
                                       "T1" if best else
                                       "T3 SoilGrids (pending script 07 + OZ/JP SoilGrids run)"),
                     "flags": "; ".join(flags)})
    S = pd.DataFrame(summ)
    S.to_csv(a.out / "ICOS38_soil_site_summary.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 220)
    print(S[["site", "t1_numeric_sources", "t1_sand_0_30cm", "t1_clay_0_30cm", "t1_deepest_cm",
             "flechard_S4_sand_silt_clay", "flags"]].to_string(index=False))
    print(f"\n{len(E)} evidence rows; {(E.use_numeric == 'YES').sum()} usable numeric layers; "
          f"{(S.t1_numeric_sources != 'NONE').sum()} sites with T1")


if __name__ == "__main__":
    main()
