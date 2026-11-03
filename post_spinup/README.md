# Post-spin-up start information

This folder collects what each site needs before a CLM-FATES run can start from its spun-up state (after AD400 → NORMAL400). It holds what we know per site, where each item comes from, and what is still missing.

**Scope now: the 38 ICOS / European sites** (the registry in `examples/Cross_cohort_NORMAL400/scripts/26_site_registry.py`). AmeriFlux follows in a sister folder later.

Status, 3 November 2026: the information tables are built. **No post-spin-up run can start yet.** Almost every ICOS site is rerunning AD400 → NORMAL400 with the needleleaf fix and/or the phenology patch (see [maintenance/](../maintenance/README.md)). Only the 7 UNCHANGED sites already have their final NORMAL400 restart.

## What a post-spin-up run needs, and where each item stands

| # | Item | Source in this folder | ICOS 38 status |
|---|---|---|---|
| 1 | **Spun-up restart**: the last restart of the site's NORMAL400 case | `spinup_class_20261102`, `normal400_case_expected`, `spinup_restart_ready` | Ready for 7 sites (AT-Neu, CH-Cha, CH-Fru, ES-LJu, GF-Guy, IT-MBo, IT-Noe). For 24 sites the replacement runs started on 2 Nov. The 6 Batch04 sites are not finished, or have no case yet (CH-Aws). NL-Loo needs a decision (see below). The expected case names must be checked on IRIDIS. |
| 2 | **Same model setup** as the spin-up: surface file, FATES parameter file (needleleaf F), source with the phenology patch | [`maintenance/RULES_FOR_NEW_CASES.md`](../maintenance/RULES_FOR_NEW_CASES.md) | A post-spin-up case must use the same build and parameter file as its spin-up. Otherwise it starts from a state made by different physics. |
| 3 | **Run period and forcing**: the tower years, run once in calendar order (not recycled) | `ec_first_year`, `ec_last_year`, `ec_sources` | Filled for 37/38 sites. GL-ZaH has no EC record in the BIF scan or in the provenance files. |
| 4 | **Atmospheric CO2** | not yet in a table | The spin-ups used a constant `CCSM_CO2_PPMV` (for example 376.95 ppm in the Batch02 scripts). A transient CO2 series for the run period still has to be chosen. |
| 5 | **Stand history**: origin, establishment year, stand-replacing events, management during the EC years | `ICOS38_stand_history_management.csv` | Documented or derived for 24 of 26 forest sites. Missing: IT-Lav and CZ-Stn. Many thinning years are still TODO. |
| 6 | **Evaluation targets**: EC fluxes plus observed structure (AGB, basal area, density, DBH, height, LAI, soil C, species) | `ICOS38_BIF_structure_summary.csv`, `ICOS38_BIF_observations_long.csv` | 15 forest sites have ICOS ancillary tree data in their BIF; others only height/LAI or nothing (list below). |

## Why stand history matters

Fixed biogeography with no competition, run for 800 years, ends in an old-growth-like equilibrium. Most ICOS forests are younger, managed stands. If the run starts directly from the equilibrium, biomass and fluxes are compared with a stand of the wrong age. The column `suggested_start_mode` groups the sites. **It is a proposal for discussion, not a decision:**

| Proposed start mode | Meaning | Sites |
|---|---|---|
| `CONTINUE_FROM_EQUILIBRIUM` | Old-growth or uneven-aged with no known stand-replacing event: start the run from the spun-up state | DE-Hai, RU-Fyo, IT-Ren, GF-Guy |
| `CONTINUE_FROM_EQUILIBRIUM_CHECK` | Old but managed around the tower; check footprint age | CH-Dav (core plots ~106 yr, footprint ~60 yr), CH-Lae |
| `RESET_AT_ESTABLISHMENT` | Even-aged stand with a known start year: keep the spun-up soil, restart the vegetation at the establishment year, grow to the EC start with recycled forcing, then run the EC years | DE-Tha 1887, NL-Loo 1909, DK-Sor 1921, BE-Bra 1929, FR-Pue 1942 (coppice), DE-Obe ~1955, FR-Hes ~1961, FI-Hyy 1962, IL-Yat 1964, FI-Let 1969 (drainage), CZ-BK1 1981, DE-Lnf ~1885 |
| `RESET_AT_DISTURBANCE` | Stand-replacing disturbance just before the EC record | DE-Hzd (2007 windthrow, oaks planted) |
| `RESET_COMPLEX` | Several planted cohorts | BE-Vie (pine 1882, beech 1908, Douglas fir 1935 and 1950–61) |
| `RESET_UNCERTAIN` | Age known only roughly | FR-FBn (~1954), FR-Fon (~1865, assumed reference year), FI-Sod (60–160 yr after fire), IT-Col (~1890) |
| `UNKNOWN_NEEDS_LITERATURE` | No age found yet | IT-Lav, CZ-Stn |
| `NOT_APPLICABLE` | Grassland, shrubland, tundra | 12 sites. Mowing and grazing are recorded where known; FATES does not represent them. |

**Management events inside the EC record** that a model without management will not reproduce:
- DE-Tha: thinnings in April 2002 and February 2011.
- FI-Hyy: thinnings in 2002, 2019–20, and a commercial thinning in 2020 that removed ~40% of tree biomass. The ICOS CP basal area falls from 28.6 m²/ha (2018) to 17.1 m²/ha (2020).
- FI-Let: partial harvest in March 2016.
- CZ-BK1: thinning in 2002.
- BE-Bra: thinning in 2016.
- BE-Vie: thinning every 6 years.
- DE-Lnf: thinning every 10–20 years.
- FR-Pue: experiments from 2003.

How to make a stand-replacing reset (a FATES logging/harvest event, or a new case that keeps soil pools only) is **not chosen yet**. Check what the FATES version in use supports before designing it.

## Files

| File | Content |
|---|---|
| [`ICOS38/ICOS38_post_spinup_start_info.csv`](ICOS38/ICOS38_post_spinup_start_info.csv) | **Main table**, one row per site: PFTs, spin-up class and expected NORMAL400 case, EC years, stand history, start-mode proposal, observed structure, sources |
| [`ICOS38/ICOS38_stand_history_management.csv`](ICOS38/ICOS38_stand_history_management.csv) | Curated stand origin and management history with source URLs. `evidence_status`: DOCUMENTED / DERIVED (year computed from an age at a reference year) / DOCUMENTED_AGE_ONLY / MISSING / NOT_RESEARCHED |
| [`ICOS38/ICOS38_BIF_structure_summary.csv`](ICOS38/ICOS38_BIF_structure_summary.csv) | One reference value per site and variable from the BADM, with year, plot type and flags |
| [`ICOS38/ICOS38_BIF_observations_long.csv`](ICOS38/ICOS38_BIF_observations_long.csv) | Every mean/single-value BADM record behind the summary |
| [`ICOS38/inputs/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv`](ICOS38/inputs/) | Copy of the PFT register (CLM-FATES-single-site-workflows, commit `a1579ebc`) |
| [`scripts/00_inventory_site_BIF_badm_readonly.py`](scripts/00_inventory_site_BIF_badm_readonly.py) | Read-only scan of every site's BIF on IRIDIS (`MY_EC_SITE/<SITE>/forcing/raw/` or the package zip) |
| [`scripts/01_extract_ICOS38_BIF_observations.py`](scripts/01_extract_ICOS38_BIF_observations.py) | BIF rows → long table and per-site summary |
| [`scripts/02_build_ICOS38_start_info.py`](scripts/02_build_ICOS38_start_info.py) | Merges the summary, the stand history and the PFT register into the main table |

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

**Forest sites without tree structure in the BIF** (evaluation targets need literature): RU-Fyo, IL-Yat, IT-Lav, FR-Fon, FI-Sod, CH-Lae, CZ-Stn, DE-Lnf, DE-Obe, IT-Col, FI-Let (understorey only). DE-Hzd has density and DBH only.

## Open items

1. When the replacement NORMAL400 runs finish: write a read-only IRIDIS script that reads each case's final restart (path, model year, `spinup_state`), `CCSM_CO2_PPMV`, DATM years, surface and parameter file. Merge these into the main table.
2. Decide the start-mode design (the table above) and how to make a stand-replacing reset in FATES.
3. Choose the transient CO2 series.
4. **NL-Loo:** its legacy PRE50/AD200/POST300 case used the default needleleaf parameters and is not in the 2 Nov rollout. Rerun it with AD400 → NORMAL400 and variant F, or exclude it.
5. Literature gaps:
   - IT-Lav and CZ-Stn stand age.
   - Thinning years for DK-Sor, FR-Hes, BE-Vie, BE-Bra and DE-Lnf.
   - Structure data for the forest sites listed above.
   - Management of CH-Aws, CH-Cha, CH-Fru, DE-RuR, ES-Agu, ES-LJu, IT-Noe and GL-ZaH.
   - The EC record for GL-ZaH.
6. Sites without a BIF in the scan (FI-Sod, FR-Fon, IT-Col, IT-Noe, GL-ZaH): check whether their ICOS v1.3 packages on IRIDIS contain one.
