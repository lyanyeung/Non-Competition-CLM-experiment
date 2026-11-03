#!/usr/bin/env python3
"""Build the one-row-per-site start-information table for the ICOS 38 post-spin-up runs.

Inputs (all in post_spinup/ICOS38/ unless given):
  ICOS38_BIF_structure_summary.csv        from 01_extract_ICOS38_BIF_observations.py
  ICOS38_stand_history_management.csv     curated stand origin / management history, with sources
  inputs/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv
      copy of CLM-FATES-single-site-workflows/examples/ICOS_sites/ICOS_PFT/ at commit a1579ebc

Constants below record, per site:
  * SPINUP_CLASS: the 2026-11-02 rollout class in maintenance/README.md ("Current case per site").
    It decides which NORMAL400 case will hold the restart the post-spin-up run starts from.
  * NORMAL400_BASE: the NORMAL400 case name in the published provenance files
    (figures/AD400_NORMAL400/20261101T042427Z_88_5996d9c0/<site>/<case>/). The replacement case is
    <base> + suffix (_NLF, _NLFP, _PHEN). Names are expected names and must be checked on IRIDIS.
  * EC_SOURCES: flux/meteo files used for the site (provenance JSON "ec_sources" or BIF package name).

Output: ICOS38_post_spinup_start_info.csv
"""
import argparse
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "ICOS38"

SPINUP_CLASS = {}
for cls, sites in {
    "KEEP_NLF": "CH-Dav CZ-BK1 DE-Obe FI-Sod FR-FBn IL-Yat",
    "RESTART_NLFP": "BE-Bra BE-Vie CH-Lae DE-Tha FI-Hyy FI-Let FR-Fon IT-Lav IT-Ren RU-Fyo",
    "RERUN_PHEN": "CZ-Stn DE-Hai DE-Hzd DE-Lnf DK-Sor FR-Hes FR-Pue IT-Col",
    "UNCHANGED": "AT-Neu CH-Cha CH-Fru ES-LJu GF-Guy IT-MBo IT-Noe",
    "B04_RESTART_AD_PHEN": "GL-ZaH",
    "B04_RUNNING_UNPATCHED_OK": "DE-Gri DE-RuR IT-Tor ES-Agu",
    "B04_NO_CASE_YET": "CH-Aws",
    "LEGACY_EXAMPLE_NOT_IN_ROLLOUT": "NL-Loo",
}.items():
    for s in sites.split():
        SPINUP_CLASS[s] = cls
SUFFIX = {"KEEP_NLF": "_NLF", "RESTART_NLFP": "_NLFP", "RERUN_PHEN": "_PHEN", "UNCHANGED": "",
          "B04_RESTART_AD_PHEN": "", "B04_RUNNING_UNPATCHED_OK": "", "B04_NO_CASE_YET": "",
          "LEGACY_EXAMPLE_NOT_IN_ROLLOUT": ""}

NORMAL400_BASE = {
    "DE-Tha": "DE-Tha_OBSPFT_NC_V1_NORMAL400", "DE-Hai": "DE-Hai_B01_FIXNC_NORMAL400",
    "RU-Fyo": "RU-Fyo_B01_FIXNC_NORMAL400", "DK-Sor": "DK-Sor_B02_FIXNC_ICOS_DBF100_NORMAL400",
    "IL-Yat": "IL-Yat_B03_FIXNC_BARE52_NORMAL400", "CZ-BK1": "CZ-BK1_B01_FIXNC_NORMAL400",
    "IT-Ren": "IT-Ren_B01_FIXNC_NORMAL400", "FR-Hes": "FR-Hes_B02_FIXNC_NORMAL400",
    "FR-FBn": "FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_NORMAL400", "DE-Hzd": "DE-Hzd_B03_FIXNC_NORMAL400",
    "CH-Dav": "CH-Dav_B01_FIXNC_NORMAL400", "BE-Vie": "BE-Vie_B01_FIXNC_NORMAL400",
    "IT-Lav": "IT-Lav_B03_FIXNC_NORMAL400", "BE-Bra": "BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_NORMAL400",
    "FR-Fon": "FR-Fon_B01_FIXNC_NORMAL400", "IT-Noe": "IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_NORMAL400",
    "AT-Neu": "AT-Neu_B03_FIXNC_NORMAL400", "FI-Sod": "FI-Sod_B01_FIXNC_NORMAL400",
    "CH-Cha": "CH-Cha_B03_FIXNC_NORMAL400", "CH-Fru": "CH-Fru_B02_FIXNC_NORMAL400",
    "CH-Lae": "CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_NORMAL400", "CZ-Stn": "CZ-Stn_B03_FIXNC_NORMAL400",
    "DE-Lnf": "DE-Lnf_B03_FIXNC_NORMAL400", "DE-Obe": "DE-Obe_B03_FIXNC_NORMAL400",
    "ES-LJu": "ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_NORMAL400", "IT-Col": "IT-Col_B01_FIXNC_NORMAL400",
    "FI-Hyy": "FI-Hyy_B02_FIXNC_NORMAL400", "FI-Let": "FI-Let_B03_FIXNC_NORMAL400",
    "FR-Pue": "FR-Pue_B01_FIXNC_NORMAL400", "GF-Guy": "GF-Guy_B03_FIXNC_NORMAL400",
    "IT-MBo": "IT-MBo_B02_FIXNC_NORMAL400",
    "GL-ZaH": "GL-ZaH_ICOS_B04_FIXNC_NORMAL400_DIRECT_PHEN",
    "DE-Gri": "DE-Gri_ICOS_B04_FIXNC_NORMAL400_DIRECT", "DE-RuR": "DE-RuR_ICOS_B04_FIXNC_NORMAL400_DIRECT",
    "IT-Tor": "IT-Tor_ICOS_B04_FIXNC_NORMAL400_DIRECT", "ES-Agu": "ES-Agu_ICOS_B04_FIXNC_NORMAL400_DIRECT",
    "CH-Aws": "", "NL-Loo": "",
}

EC_SOURCES = {  # provenance JSON "ec_sources" where the BIF package does not give the whole record
    "DK-Sor": "ICOS_DK-Sor_FLUXNET_FLUXMET_HH_1996-2024; ICOSETC_DK-Sor_FLUXNET_FLUXMET_HH_2021-2026",
    "BE-Bra": "FLX_BE-Bra_FLUXNET2015_FULLSET_HH_1996-2020; ICOS_BE-Bra_FLUXNET_FLUXMET_HH_1999-2024; "
              "ICOSETC_BE-Bra_FLUXNET_FLUXMET_HH_2020-2025",
    "FR-Fon": "FLX_FR-Fon_FLUXNET2015_FULLSET_HH_2005-2020; ICOS_FR-Fon_FLUXNET_FLUXMET_HH_2019-2026",
    "IT-Noe": "FLX_IT-Noe_FLUXNET2015_FULLSET_HH_2004-2023; ICOS_IT-Noe_FLUXNET_FLUXMET_HH_2022-2025",
    "FI-Sod": "FLX_FI-Sod_FLUXNET2015_FULLSET_HH_2001-2014; ICOS_FI-Sod_FLUXNET_FLUXMET_HH_2023-2026",
    "IT-Col": "FLX_IT-Col_FLUXNET2015_FULLSET_HH_1996-2014",
}


def ec_years(src):
    yrs = [int(y) for a, b in re.findall(r"_(\d{4})-(\d{4})", src or "") for y in (a, b)]
    return (min(yrs), max(yrs)) if yrs else (None, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=HERE)
    a = ap.parse_args()
    summ = pd.read_csv(a.dir / "ICOS38_BIF_structure_summary.csv")
    hist = pd.read_csv(a.dir / "ICOS38_stand_history_management.csv", dtype=str, keep_default_na=False)
    pft = pd.read_csv(a.dir / "inputs" / "FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv", dtype=str)
    pft = pft[["site", "fixnc_cohort", "reported_igbp", "final_PCT_NAT_PFT", "status"]].rename(
        columns={"status": "pft_register_status"})

    df = pft.merge(hist, on="site", how="left").merge(summ, on="site", how="left")
    df["spinup_class_20261102"] = df.site.map(SPINUP_CLASS)
    df["normal400_case_expected"] = [
        (NORMAL400_BASE.get(s, "") + SUFFIX[c]) if NORMAL400_BASE.get(s) else "" for s, c in
        zip(df.site, df.spinup_class_20261102)]
    src = [EC_SOURCES.get(s) or (f if isinstance(f, str) and f != "NO_BIF" else "") for s, f in
           zip(df.site, df.bif_source_file)]
    df["ec_sources"] = src
    df["ec_first_year"], df["ec_last_year"] = zip(*[ec_years(x) for x in src])

    est = pd.to_numeric(df.establishment_year, errors="coerce")
    df["stand_age_at_ec_start"] = (df.ec_first_year - est).where(est.notna())
    df["spinup_restart_ready"] = df.spinup_class_20261102.map({
        "UNCHANGED": "YES (original NORMAL400; verify final restart year)",
        "B04_RUNNING_UNPATCHED_OK": "NO (NORMAL400 not finished)",
        "B04_NO_CASE_YET": "NO (no case)",
        "LEGACY_EXAMPLE_NOT_IN_ROLLOUT": "DECIDE (legacy PRE50/AD200/POST300 with default needleleaf parameters)",
    }).fillna("NO (replacement AD400/NORMAL400 running since 2026-11-02)")

    first = ["site", "fixnc_cohort", "reported_igbp", "igbp_bif", "ecosystem", "final_PCT_NAT_PFT",
             "spinup_class_20261102", "normal400_case_expected", "spinup_restart_ready",
             "ec_first_year", "ec_last_year", "ec_sources",
             "stand_origin", "establishment_year", "establishment_year_basis", "stand_age_at_ec_start",
             "age_note", "last_stand_replacing_event", "management_regime", "management_events",
             "suggested_start_mode", "evidence_status"]
    obs = [c for c in summ.columns if c not in ("site", "igbp_bif", "bif_source_file")]
    rest = ["sources", "pft_register_status", "bif_source_file"]
    df = df[first + obs + rest]
    df.to_csv(a.dir / "ICOS38_post_spinup_start_info.csv", index=False)
    print(df[["site", "spinup_class_20261102", "ec_first_year", "ec_last_year", "establishment_year",
              "stand_age_at_ec_start", "suggested_start_mode", "agb_tree_kgDM_m2"]].to_string())


if __name__ == "__main__":
    main()
