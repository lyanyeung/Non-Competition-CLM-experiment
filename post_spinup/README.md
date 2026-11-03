# Post-spin-up start information

This folder collects what each site needs before a CLM-FATES run can start from its spun-up state (after AD400 → NORMAL400). It holds what we know per site, where each item comes from, and what is still missing.

**Scope now: the 38 ICOS / European sites** (the registry in `examples/Cross_cohort_NORMAL400/scripts/26_site_registry.py`). AmeriFlux follows in a sister folder later.

Status, 3 November 2026: the information tables are built, and a literature layer (site papers, site pages, data-paper supplements) has been added on top of the BADM data. **No post-spin-up run can start yet.** Almost every ICOS site is rerunning AD400 → NORMAL400 with the needleleaf fix and/or the phenology patch (see [maintenance/](../maintenance/README.md)). Only the 7 UNCHANGED sites already have their final NORMAL400 restart.

## What a post-spin-up run needs, and where each item stands

| # | Item | Source in this folder | ICOS 38 status |
|---|---|---|---|
| 1 | **Spun-up restart**: the last restart of the site's NORMAL400 case | `spinup_class_20261102`, `normal400_case_expected`, `spinup_restart_ready` | Ready for 7 sites (AT-Neu, CH-Cha, CH-Fru, ES-LJu, GF-Guy, IT-MBo, IT-Noe). For 24 sites the replacement runs started on 2 Nov. The 6 Batch04 sites are not finished, or have no case yet (CH-Aws). NL-Loo needs a decision (see below). The expected case names must be checked on IRIDIS. |
| 2 | **Same model setup** as the spin-up: surface file, FATES parameter file (needleleaf F), source with the phenology patch | [`maintenance/RULES_FOR_NEW_CASES.md`](../maintenance/RULES_FOR_NEW_CASES.md) | A post-spin-up case must use the same build and parameter file as its spin-up. Otherwise it starts from a state made by different physics. |
| 3 | **Run period and forcing**: the tower years, run once in calendar order (not recycled) | `ec_first_year`, `ec_last_year`, `ec_sources` | Filled for 37/38 sites. GL-ZaH has no EC record in the BIF scan or in the provenance files. |
| 4 | **Atmospheric CO2** | not yet in a table | The spin-ups used a constant `CCSM_CO2_PPMV` (for example 376.95 ppm in the Batch02 scripts). A transient CO2 series for the run period still has to be chosen. |
| 5 | **Stand history**: origin, establishment year, stand-replacing events, management during the EC years | `ICOS38_stand_history_management.csv` | All 26 forest sites now have an origin and a start-mode proposal (IT-Lav and CZ-Stn derived from published ages). Thinning or harvest years inside the EC record are known for 9 forest sites; intensities are often missing. Management is now described for all 12 grassland, shrubland and tundra sites. |
| 6 | **Evaluation targets**: EC fluxes plus observed structure (AGB, basal area, density, DBH, height, LAI, soil C, species) | `ICOS38_BIF_structure_summary.csv`, `ICOS38_BIF_observations_long.csv`, `ICOS38_literature_observations.csv` | 15 forest sites have ICOS ancillary tree data in their BIF. The literature table adds values for 34 of 38 sites (`lit_*` columns in the main table). Only DE-Obe still has neither. Soil carbon is still thin (see open items). |

## Why stand history matters

Fixed biogeography with no competition, run for 800 years, ends in an old-growth-like equilibrium. Most ICOS forests are younger, managed stands. If the run starts directly from the equilibrium, biomass and fluxes are compared with a stand of the wrong age. The column `suggested_start_mode` groups the sites. **It is a proposal for discussion, not a decision:**

| Proposed start mode | Meaning | Sites |
|---|---|---|
| `CONTINUE_FROM_EQUILIBRIUM` | Old-growth or uneven-aged with no known stand-replacing event: start the run from the spun-up state | DE-Hai, RU-Fyo (190 yr, reserve since 1931), IT-Ren, GF-Guy |
| `CONTINUE_FROM_EQUILIBRIUM_CHECK` | Old but managed around the tower; check footprint age | CH-Lae (reserve on the upper slope since 1998, storm damage December 1999) |
| `RESET_AT_ESTABLISHMENT` | Even-aged stand with a known start year: keep the spun-up soil, restart the vegetation at the establishment year, grow to the EC start with recycled forcing, then run the EC years | DE-Lnf ~1885, DE-Tha 1887, CZ-Stn ~1903, NL-Loo 1909, DK-Sor 1921, BE-Bra 1929, FR-Pue 1942 (coppice), DE-Obe ~1955, FR-Hes ~1961, FI-Hyy 1962, IL-Yat 1966 (planted 1964–69), FI-Let 1969 (drainage), CZ-BK1 1981 |
| `RESET_AT_DISTURBANCE` | Stand-replacing disturbance just before the EC record | DE-Hzd (40 ha Kyrill windthrow in January 2007, oaks planted) |
| `RESET_COMPLEX` | Several cohorts, or a footprint much younger than the plots | BE-Vie (pine 1882, beech 1908, Douglas fir 1935 and 1950–61); CH-Dav (group selection: EC footprint ~60 yr, 9.9 m; unthinned core plots ~106 yr, 18.3 m) |
| `RESET_UNCERTAIN` | Age known only roughly | FR-FBn (~1954), FR-Fon (~1880, 100–150 yr in 2005), IT-Lav (~1888, mean age 120 yr over 2003–2012), IT-Col (~1890), FI-Sod (60–160 yr after fire) |
| `NOT_APPLICABLE` | Grassland, shrubland, tundra | 12 sites. Mowing and grazing are recorded where known; FATES does not represent them. |

**Management events inside the EC record** that a model without management will not reproduce. Each one changes NEE for several years (less leaf area, more litter and dead roots to decompose):
- BE-Bra: thinning in winter 1999 (stem number −30%, 538 → 375 trees/ha), storm in autumn 2002 (→ 360 trees/ha), thinning in summer 2016.
- CZ-BK1: thinnings in 2002 and 2005–06 (stem number −30%, LAI −26%).
- DE-Lnf: selective harvest 2002–06 (~23 tC/ha, ~10% of biomass); otherwise thinning every 10–20 years.
- DE-Tha: thinnings in April 2002 and February 2011; harvest near the station in September 2020.
- DK-Sor: thinning in 2013 (stem number −10%); earlier thinnings not found yet.
- FI-Hyy: thinnings in 2002, 2019–20, and a commercial thinning in 2020 that removed ~40% of tree biomass. The ICOS CP basal area falls from 28.6 m²/ha (2018) to 17.1 m²/ha (2020).
- FI-Let: spring 2016, partial harvest (~75% of tree biomass in the EC footprint plot) and a 2.35 ha clear-cut next to it.
- FR-Fon: thinning 2010–11 (LAI −36%).
- FR-Hes: thinnings in 1999, 2005, 2010 and 2016 (intensities not found). The EC height also changed: 18 m (1997–99), 23.34 m (2000–12), 27.1 m (2013–20).
- BE-Vie: thinning every 6 years.
- FR-Pue: experiments from 2003.

Grasslands export carbon with every cut or grazing period, so NEE alone is not their carbon balance. CH-Fru, for example, has a mean NEE of −357 ± 76 gC m⁻² yr⁻¹ but a net biome production of only −154 ± 80 gC m⁻² yr⁻¹ (Rogger et al. 2022). CH-Cha had a sward renewal (ploughing and reseeding) in 2012. Event tables exist for CH-Cha (ETH dataset doi:10.3929/ethz-b-000747025) and CH-Fru (CH-FRU_Management_2005-2023.xlsx on the Swiss FluxNet site page). They are not downloaded yet.

How to make a stand-replacing reset (a FATES logging/harvest event, or a new case that keeps soil pools only) is **not chosen yet**. Check what the FATES version in use supports before designing it.

## Files

| File | Content |
|---|---|
| [`ICOS38/ICOS38_post_spinup_start_info.csv`](ICOS38/ICOS38_post_spinup_start_info.csv) | **Main table**, one row per site: PFTs, spin-up class and expected NORMAL400 case, EC years, stand history, start-mode proposal, observed structure, sources |
| [`ICOS38/ICOS38_stand_history_management.csv`](ICOS38/ICOS38_stand_history_management.csv) | Curated stand origin and management history with source URLs. `evidence_status`: DOCUMENTED / DERIVED (year computed from an age at a reference year) / DOCUMENTED_AGE_ONLY / DOCUMENTED_PARTIAL(_EVENTS) |
| [`ICOS38/ICOS38_literature_observations.csv`](ICOS38/ICOS38_literature_observations.csv) | One row per value found in a site paper, site page or data-paper supplement: category, variable, value, unit, reference year, scope (which plot or footprint), `preferred` (1 = used in the main table), source and URL |
| [`ICOS38/ICOS38_BIF_structure_summary.csv`](ICOS38/ICOS38_BIF_structure_summary.csv) | One reference value per site and variable from the BADM, with year, plot type and flags |
| [`ICOS38/ICOS38_BIF_observations_long.csv`](ICOS38/ICOS38_BIF_observations_long.csv) | Every mean/single-value BADM record behind the summary |
| [`ICOS38/inputs/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv`](ICOS38/inputs/) | Copy of the PFT register (CLM-FATES-single-site-workflows, commit `a1579ebc`) |
| [`scripts/00_inventory_site_BIF_badm_readonly.py`](scripts/00_inventory_site_BIF_badm_readonly.py) | Read-only scan of every site's BIF on IRIDIS (`MY_EC_SITE/<SITE>/forcing/raw/` or the package zip) |
| [`scripts/01_extract_ICOS38_BIF_observations.py`](scripts/01_extract_ICOS38_BIF_observations.py) | BIF rows → long table and per-site summary |
| [`scripts/02_build_ICOS38_start_info.py`](scripts/02_build_ICOS38_start_info.py) | Merges the summary, the stand history, the literature table (`preferred=1` rows → `lit_*` columns) and the PFT register into the main table |

Regenerate the tables. The raw `bif_key_groups_rows.csv` (96 MB) stays on IRIDIS and is not committed.

```bash
python3 post_spinup/scripts/00_inventory_site_BIF_badm_readonly.py --out ~/BIF_inventory          # on IRIDIS
python3 post_spinup/scripts/01_extract_ICOS38_BIF_observations.py \
        --bif-rows ~/BIF_inventory/bif_key_groups_rows.csv --out post_spinup/ICOS38
python3 post_spinup/scripts/02_build_ICOS38_start_info.py
```

## Observed-data notes

- **Source.** The BIF files that come with the FLUXNET v1.3 packages. For ICOS sites (`ICOS_` prefix) these contain the ICOS ETC ancillary groups (GRP_BIOMASS, GRP_BASAL_AREA, GRP_TREES_NUM, GRP_DBH, GRP_HEIGHTC, GRP_LAI, GRP_SOIL_STOCK, GRP_SPP_O). `EUF_` sites mostly have only site information, height and LAI.
- **Selection.** Continuous measurement plots (CP) are preferred over sparse plots (SP-I), and the latest year is used. The stand total is the record without species (or species "Total"), excluding dead trees. The full rules are in the docstring of script 01.
- **Check against the ICOS report.** CH-Dav 2020 CP gives 341 t DM/ha and 54.4 m²/ha. The ICOS ETC ancillary report gives 339.5 t/ha and 54.1 m²/ha.
- **Biomass units.** Biomass is in kg dry mass m⁻². DE-Hai reports gC m⁻² for wood only; it is converted with a carbon fraction of 0.5 and flagged.
- **Soil carbon.** Soil C is the ETC "Cumulative stock" in kgC m⁻². Flagged as needing checks:
  - BE-Bra and DK-Sor have single records of 1.1–1.3 kgC m⁻² for 0–68.6 cm, implausibly low.
  - CZ-BK1's cumulative value differs from its O + M layer sum.
  - DE-Gri, DE-Hzd and FI-Let records are not in the ETC format.
- **Species percentages.** ETC "tree percentage" values have no stated basis (stem count, basal area or cover). Do not use them as PFT area fractions; the PFT register keeps its own evidence.

**Forest sites without tree structure in the BIF**: RU-Fyo, IL-Yat, IT-Lav, FR-Fon, FI-Sod, CH-Lae, CZ-Stn, DE-Lnf, DE-Obe, IT-Col, FI-Let (understorey only). DE-Hzd has density and DBH only. The literature table now gives at least age, height, density or LAI for all of them except DE-Obe.

## Literature layer and NEE

`ICOS38_literature_observations.csv` holds 154 values for 34 sites. Every row has a source and a URL. A value is used in the main table only if `preferred=1`. Rows with `preferred=0` are kept as cross-checks: secondary compilations, values for a plot that is not the EC footprint, or values that look wrong.

What the literature changes for the NEE comparison:

- **Footprint versus plot.** At CH-Dav the EC footprint is younger and smaller (~60 yr, 9.9 m) than the unthinned core plots (~106 yr, 18.3 m), which is where the BIF biomass (35.8 kg DM m⁻²) comes from. Compare simulated biomass with the footprint values, not the plot values.
- **NEE trends.** Fernández-Martínez et al. (2017) give NEP trends for 13 of our forests. Strong increases at IT-Lav (+41.8 gC m⁻² yr⁻¹ per year), IT-Ren (+37.9), DK-Sor (+27.3) and FR-Hes (+26.4); declines at FR-Pue (−10.3) and DE-Hai (−7.3). Run with constant CO2, an unmanaged model cannot produce these trends. This is one reason the transient CO2 series (item 4) matters.
- **Long-term means for checks.** Mean NEP: DE-Lnf 590 ± 190, DE-Hai 512 ± 89, DE-Tha 430, DK-Sor 115 (1996–2008), DE-Gri 90 gC m⁻² yr⁻¹. A secondary compilation (Biogeosciences 22:4729, 2025, Table S1) gives NEE/GPP/Reco for 10 of our forests. These are `preferred=0`: GPP − Reco does not match −NEE at four sites, and IT-Lav (−1844 gC m⁻² yr⁻¹) is implausible. Use them to sense-check our own FLUXNET means, not as targets.
- **Non-biological CO2 signals.** At DE-Hai, advection makes the EC sink 100–200 gC m⁻² yr⁻¹ larger than bottom-up estimates. At ES-LJu and ES-Agu (also called Balsa Blanca), turbulence ventilates CO2 out of the subsoil and the tower records it. CLM-FATES will not reproduce either; expect a bias there that is not a model error.
- **Measurement height.** FR-Hes raised its EC system twice (18 → 23.34 → 27.1 m). The forcing reference height should follow the year.

## Open items

1. When the replacement NORMAL400 runs finish: write a read-only IRIDIS script that reads each case's final restart (path, model year, `spinup_state`), `CCSM_CO2_PPMV`, DATM years, surface and parameter file. Merge these into the main table.
2. Decide the start-mode design (the table above) and how to make a stand-replacing reset in FATES.
3. Choose the transient CO2 series.
4. **NL-Loo:** its legacy PRE50/AD200/POST300 case used the default needleleaf parameters and is not in the 2 Nov rollout. Rerun it with AD400 → NORMAL400 and variant F, or exclude it.
5. Remaining literature gaps:
   - **Soil organic carbon** for most forests. Flechard et al. (2020, Biogeosciences 17:1583, supplement Tables S1–S3) gives SOC and stand data for nearly all of these sites, but the PDF cannot be fetched from here; it needs to be uploaded.
   - **Stand inventory time series** (biomass, density, height by year) for CZ-BK1, IT-Col, FI-Hyy and DK-Sor are in the PROFOUND database (doi:10.5880/PIK.2020.006). Not downloaded yet.
   - DE-Obe: no structure beyond ~53 yr / 15 m around 2008.
   - Thinning intensities for FR-Hes; thinning years before 2013 for DK-Sor; harvest extent at DE-Tha in 2020; planting year and density at DE-Hzd; IL-Yat thinning years.
   - Management event tables for CH-Cha and CH-Fru (exist, not downloaded).
   - The EC record for GL-ZaH.
6. Sites without a BIF in the scan (FI-Sod, FR-Fon, IT-Col, IT-Noe, GL-ZaH): check whether their ICOS v1.3 packages on IRIDIS contain one.
