#!/usr/bin/env python3
"""Extract site tables from the Flechard et al. (2020) supplement for the ICOS 38 sites.

Source: Flechard, C. R. et al. (2020) Carbon-nitrogen interactions in European forests and
semi-natural vegetation - Part 1. Biogeosciences 17, 1583-1620. Supplement PDF
(https://doi.org/10.5194/bg-17-1583-2020-supplement, CC BY 4.0). The PDF itself is not committed.

Tables read (page in the 17-page supplement):
  S1 (p6)  site code -> NitroEurope PFT code (DB1, EN3, ...), used to read S7
  S2 (p7)  species composition, density, thinning, DBH, basal area (forests only)
  S3 (p8)  foliar N/C, C/N of organs, topsoil C/N, topsoil SOC concentration (gC/kg dry soil)
  S4 (p9)  soil depth, slope, texture, FAO class, clay/sand/silt, WP/FC/SAT, topsoil pH
  S5 (p10) MAT, GDD5, Rg, MAP, AET, PET, water-availability indices, O3 AOT40
  S7 (p12) published annual soil respiration and Rhet/Rsoil (forests)

Note: S3 gives topsoil SOC *concentration*, not a stock. The stocks are not in the supplement.

The text layer was checked against page images (pages 7 and 9). Requires poppler's pdftotext.

Usage:
  python3 post_spinup/scripts/03_extract_Flechard2020_supplement.py --pdf bg-17-1583-2020-supplement.pdf
Output: post_spinup/ICOS38/Flechard2020_supplement_ICOS38.csv (one row per site, wide)
"""
import argparse
import re
import subprocess
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "ICOS38"
SITE_RE = re.compile(r"^\s*([A-Z]{2}-[A-Za-z0-9]{3})\s+")
NUMYR = r"([\d.]+(?:\s*-\s*[\d.]+)?)\s*\((\d{4})\)"


def page_text(pdf, page):
    return subprocess.run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
                          check=True, capture_output=True, text=True).stdout.splitlines()


def num(x):
    x = (x or "").strip().rstrip("*")
    try:
        return float(x)
    except ValueError:
        return None


def table_s1(lines):
    out = {}
    for ln in lines:
        m = re.match(r"^\s*([A-Z]{2}-[A-Za-z0-9]{3})\s+.*?\s((?:DB|EN|EB|MF|SN)\d+)\s", ln)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def table_s2(lines):
    rows = {}
    for ln in lines:
        m = SITE_RE.match(ln)
        if not m:
            continue
        site = m.group(1)
        toks = re.split(r"\s{2,}", ln.strip())
        # toks: site, pft, dominant species, %, [secondary, %], then value(year) columns
        r = {"pft_code": toks[1], "s2_dominant_species": toks[2], "s2_dominant_pct": toks[3]}
        rest = toks[4:]
        if rest and not re.search(r"\(\d{4}", rest[0]):
            r["s2_secondary_species"] = rest[0]
            pct = rest[1] if len(rest) > 1 else ""
            # FI-Hyy: "5-15 2500 (2002)" - the percentage and the density share one column gap
            mm = re.match(r"^(\d+(?:-\d+)?)\s+(.*\(\d{4}\).*)$", pct)
            if mm:
                pct, rest = mm.group(1), [mm.group(2)] + rest[2:]
            else:
                rest = rest[2:]
            r["s2_secondary_pct"] = pct
        line_rest = "  ".join(rest)
        thin = re.search(r"(\d+)\s*%\s*\(([\d-]+)\)", line_rest)
        if thin:
            r["s2_thinning_fraction_pct"], r["s2_thinning_year"] = thin.group(1), thin.group(2)
            line_rest = line_rest.replace(thin.group(0), " ")
        vals = re.findall(NUMYR, line_rest)
        # order in the table: density, DBH, basal area. CH-Lae has DBH only (checked on the page image).
        names = ["s2_density_trees_ha", "s2_dbh_cm", "s2_basal_area_m2_ha"]
        if site == "CH-Lae":
            names = ["s2_dbh_cm"]
        for (v, y), n in zip(vals, names):
            r[n], r[n + "_year"] = v.replace(" ", ""), y
        rows[site] = r
    return rows


def table_s3(lines):
    cols = ["s3_foliar_N_pct", "s3_foliar_C_pct", "s3_foliar_CN", "s3_branches_CN", "s3_stems_CN",
            "s3_roots_CN", "s3_topsoil_CN", "s3_topsoil_SOC_gC_per_kg"]
    rows = {}
    for ln in lines:
        m = SITE_RE.match(ln)
        if not m:
            continue
        toks = [t for t in ln.split() if t.strip("*")]  # drop stand-alone footnote markers ("215 *")
        site, vals = toks[0], toks[2:]
        if site == "IT-Col":  # roots given on the next line as "300 / 40" (coarse / fine)
            vals = [v for v in vals if v not in ("§", "¶")]
            vals = vals[:5] + ["coarse 300 / fine 40"] + vals[5:]
        vals = [v.rstrip("*") for v in vals]
        rows[site] = dict(zip(cols, vals))
    return rows


def table_s4(lines):
    rows = {}
    for ln in lines:
        m = SITE_RE.match(ln)
        if not m:
            continue
        toks = re.split(r"\s{2,}", ln.strip())
        # site, pft, depth, slope, texture, FAO class, clay, sand, silt, WP, FC, SAT, pH
        if len(toks) != 13:
            raise ValueError(f"Table S4: unexpected layout: {ln}")
        keys = ["site", "pft", "s4_soil_depth_m", "s4_slope_deg", "s4_texture", "s4_fao_class", "s4_clay_pct",
                "s4_sand_pct", "s4_silt_pct", "s4_wp_m3m3", "s4_fc_m3m3", "s4_sat_m3m3", "s4_topsoil_pH"]
        r = dict(zip(keys, toks))
        r["s4_soil_depth_m"] = r["s4_soil_depth_m"].replace(" ", "")
        rows[r.pop("site")] = {k: v for k, v in r.items() if k != "pft"}
    return rows


def table_s5(lines):
    keys = ["s5_MAT_C", "s5_GDD5", "s5_Rg_GJ_m2_yr", "s5_MAP_mm", "s5_AET_EC_mm", "s5_AET_EB_mm",
            "s5_PET_Penman_mm", "s5_PET_PM_FAO_mm", "s5_IWA1", "s5_IWA2", "s5_O3_AOT40_ppbh"]
    rows = {}
    for ln in lines:
        m = SITE_RE.match(ln)
        if m:
            toks = ln.split()
            if len(toks) == 13:
                rows[toks[0]] = dict(zip(keys, toks[2:]))
    return rows


def table_s7(lines, code2site):
    rows = {}
    for ln in lines:
        m = re.match(r"^\s*((?:DB|EN|EB|MF)\d+)\s+(\S+)\s+(\S+)\s*(.*)$", ln)
        if m and m.group(1) in code2site:
            rows[code2site[m.group(1)]] = {"s7_Rsoil_gC_m2_yr": m.group(2), "s7_Rhet_over_Rsoil": m.group(3),
                                           "s7_references": m.group(4).strip()}
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--sites", type=Path, default=HERE / "ICOS38_post_spinup_start_info.csv")
    ap.add_argument("--out", type=Path, default=HERE / "Flechard2020_supplement_ICOS38.csv")
    a = ap.parse_args()

    s1 = table_s1(page_text(a.pdf, 6))
    parts = [table_s2(page_text(a.pdf, 7)), table_s3(page_text(a.pdf, 8)), table_s4(page_text(a.pdf, 9)),
             table_s5(page_text(a.pdf, 10)), table_s7(page_text(a.pdf, 12), s1)]
    ours = set(pd.read_csv(a.sites).site)
    site2code = {v: k for k, v in s1.items()}
    rows = []
    for site in sorted(ours & set(site2code)):
        r = {"site": site, "flechard_code": site2code[site]}
        for p in parts:
            r.update(p.get(site, {}))
        rows.append(r)
    df = pd.DataFrame(rows).replace({"n.a.": "", "na": ""})
    df.to_csv(a.out, index=False)
    print(f"{len(df)} of our sites are in Flechard et al. (2020): {', '.join(df.site)}")
    print(f"not in it: {', '.join(sorted(ours - set(df.site)))}")


if __name__ == "__main__":
    main()
