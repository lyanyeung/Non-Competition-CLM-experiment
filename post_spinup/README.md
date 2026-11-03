# Post-spin-up start information

This folder collects what each site needs before a CLM-FATES run can start from its spun-up state (after AD400 → NORMAL400). It holds what we know per site, where each item comes from, and what is still missing.

**Scope now: the 38 ICOS / European sites** (the registry in `examples/Cross_cohort_NORMAL400/scripts/26_site_registry.py`). AmeriFlux follows in a sister folder later.

Status, 3 November 2026: the information tables are built. On top of the BADM data there is now a literature layer (site papers, site pages, the Flechard et al. 2020 supplement) and the PROFOUND database for four sites (see the progress log below). **No post-spin-up run can start yet.** Almost every ICOS site is rerunning AD400 → NORMAL400 with the needleleaf fix and/or the phenology patch (see [maintenance/](../maintenance/README.md)). Only the 7 UNCHANGED sites already have their final NORMAL400 restart.

## Progress log

**3 November 2026**
1. Read-only BIF scan of all site packages on IRIDIS (script 00) and extraction of the ICOS ancillary data (script 01) → structure summary for the 38 sites.
2. Curated stand-history table and start-mode proposals; main table built (script 02); topic opened as PR #66.
3. Site papers and site pages searched: ages, densities, heights, LAI, NEP means and trends, harvest and thinning events, grassland management, EC heights (`ICOS38_literature_observations.csv`).
4. Flechard et al. (2020) supplement (uploaded PDF) parsed for 17 of our sites (script 03): species, density, DBH, basal area, thinning fractions, tissue and topsoil C/N, soil texture and hydraulics, soil respiration and Rhet/Rsoil.
5. PROFOUND v0.3 downloaded to IRIDIS scratch and backed up to the Research File Store (script 04); CZ-BK1, IT-Col, FI-Hyy and DK-Sor exported (script 05) and turned into yearly stand totals, thinning events, SOC stocks and a CO2 table (script 06).
6. Results merged: 429 literature values for 35 sites; new thinning years for DK-Sor, CZ-BK1 and FI-Hyy; IT-Col established ~1892; SOC for three sites; texture conflicts flagged at IT-Col and CZ-BK1.
7. PROFOUND site data policies read (from `POLICY_SITES_master`): IT-Col, FI-Hyy and DK-Sor follow the standard PROFOUND policy (CC BY-NC 4.0, cite the database). CZ-BK1 asks for a CzeCOS funding acknowledgement and for Lenka Krupkova to be notified of any publication. The derived tables are therefore committed in `ICOS38/PROFOUND/` with a licence note; the raw extract stays on IRIDIS. Script 06 was also run on IRIDIS (`PROFOUND_v0.3/derived/`).

## What a post-spin-up run needs, and where each item stands

| # | Item | Source in this folder | ICOS 38 status |
|---|---|---|---|
| 1 | **Spun-up restart**: the last restart of the site's NORMAL400 case | `spinup_class_20261102`, `normal400_case_expected`, `spinup_restart_ready` | Ready for 7 sites (AT-Neu, CH-Cha, CH-Fru, ES-LJu, GF-Guy, IT-MBo, IT-Noe). For 24 sites the replacement runs started on 2 Nov. The 6 Batch04 sites are not finished, or have no case yet (CH-Aws). NL-Loo needs a decision (see below). The expected case names must be checked on IRIDIS. |
| 2 | **Same model setup** as the spin-up: surface file, FATES parameter file (needleleaf F), source with the phenology patch | [`maintenance/RULES_FOR_NEW_CASES.md`](../maintenance/RULES_FOR_NEW_CASES.md) | A post-spin-up case must use the same build and parameter file as its spin-up. Otherwise it starts from a state made by different physics. |
| 3 | **Run period and forcing**: the tower years, run once in calendar order (not recycled) | `ec_first_year`, `ec_last_year`, `ec_sources` | Filled for 37/38 sites. GL-ZaH has no EC record in the BIF scan or in the provenance files. |
| 4 | **Atmospheric CO2** | not yet in a table | The spin-ups used a constant `CCSM_CO2_PPMV` (for example 376.95 ppm in the Batch02 scripts), the global level of about 2004. A transient series for the run period still has to be chosen. PROFOUND's ISIMIP series ends in 2015, so it is a cross-check only (see open item 3). |
| 5 | **Stand history**: origin, establishment year, stand-replacing events, management during the EC years | `ICOS38_stand_history_management.csv` | All 26 forest sites now have an origin and a start-mode proposal (IT-Lav and CZ-Stn derived from published ages). Thinning or harvest years inside the EC record are known for 10 forest sites (DK-Sor, CZ-BK1 and FI-Hyy confirmed or added from PROFOUND's yearly inventories); intensities are often missing. Management is now described for all 12 grassland, shrubland and tundra sites. |
| 6 | **Evaluation targets**: EC fluxes plus observed structure (AGB, basal area, density, DBH, height, LAI, soil C, species) | `ICOS38_BIF_structure_summary.csv`, `ICOS38_BIF_observations_long.csv`, `ICOS38_literature_observations.csv` | 15 forest sites have ICOS ancillary tree data in their BIF. The literature table adds values for 35 of 38 sites (`lit_*` columns in the main table), including yearly stand series for CZ-BK1, DK-Sor, FI-Hyy and IT-Col from PROFOUND. Only DE-Obe still has neither. Soil carbon stocks: computed from PROFOUND profiles for DK-Sor, FI-Hyy and IT-Col; BIF values (some implausible) for the ICOS sites; topsoil SOC concentration only for the other Flechard sites. |

## Why stand history matters

Fixed biogeography with no competition, run for 800 years, ends in an old-growth-like equilibrium. Most ICOS forests are younger, managed stands. If the run starts directly from the equilibrium, biomass and fluxes are compared with a stand of the wrong age. The column `suggested_start_mode` groups the sites. **It is a proposal for discussion, not a decision:**

| Proposed start mode | Meaning | Sites |
|---|---|---|
| `CONTINUE_FROM_EQUILIBRIUM` | Old-growth or uneven-aged with no known stand-replacing event: start the run from the spun-up state | DE-Hai, RU-Fyo (190 yr, reserve since 1931), IT-Ren, GF-Guy |
| `CONTINUE_FROM_EQUILIBRIUM_CHECK` | Old but managed around the tower; check footprint age | CH-Lae (reserve on the upper slope since 1998, storm damage December 1999) |
| `RESET_AT_ESTABLISHMENT` | Even-aged stand with a known start year: keep the spun-up soil, restart the vegetation at the establishment year, grow to the EC start with recycled forcing, then run the EC years | DE-Lnf ~1885, DE-Tha 1887, IT-Col ~1892 (age 100 in 1992, PROFOUND), CZ-Stn ~1903, NL-Loo 1909, DK-Sor 1921, BE-Bra 1929, FR-Pue 1942 (coppice), DE-Obe ~1955, FR-Hes ~1961, FI-Hyy 1962, IL-Yat 1966 (planted 1964–69), FI-Let 1969 (drainage), CZ-BK1 1981 |
| `RESET_AT_DISTURBANCE` | Stand-replacing disturbance just before the EC record | DE-Hzd (40 ha Kyrill windthrow in January 2007, oaks planted) |
| `RESET_COMPLEX` | Several cohorts, or a footprint much younger than the plots | BE-Vie (pine 1882, beech 1908, Douglas fir 1935 and 1950–61); CH-Dav (group selection: EC footprint ~60 yr, 9.9 m; unthinned core plots ~106 yr, 18.3 m) |
| `RESET_UNCERTAIN` | Age known only roughly | FR-FBn (~1954), FR-Fon (~1880, 100–150 yr in 2005), IT-Lav (~1888, mean age 120 yr over 2003–2012), FI-Sod (60–160 yr after fire) |
| `NOT_APPLICABLE` | Grassland, shrubland, tundra | 12 sites. Mowing and grazing are recorded where known; FATES does not represent them. |

**Management events inside the EC record** that a model without management will not reproduce. Each one changes NEE for several years (less leaf area, more litter and dead roots to decompose):
- BE-Bra: thinning in winter 1999 (stem number −30%, 538 → 375 trees/ha), storm in autumn 2002 (→ 360 trees/ha), thinning in summer 2016.
- CZ-BK1: PROFOUND's yearly inventory shows thinnings in 2000–01 (stems −23%) and 2011–12 (stems −15%). The literature gives 2002 and 2005–06 (stems −30%, LAI −26%); PROFOUND shows only a gradual loss of small trees in 2003–07.
- DE-Lnf: selective harvest 2002–06 (~23 tC/ha, ~10% of biomass); otherwise thinning every 10–20 years.
- DE-Tha: thinnings in April 2002 (stem number −~30%; Flechard et al. 2020 give 15% removed) and February 2011; harvest near the station in September 2020.
- DK-Sor: PROFOUND's stand reconstruction shows thinnings in 1996–97 (stems −6%), 2000–01 (−15%, BA −12%), 2006–07 (−12%, BA −8%) and 2013–14 (−31%, BA −25%).
- FI-Hyy: thinnings in 2002 (25% removed; PROFOUND stems −17%), a Scots pine reduction in 2009–10 (stems −9%, PROFOUND only), 2019–20, and a commercial thinning in 2020 that removed ~40% of tree biomass. The ICOS CP basal area falls from 28.6 m²/ha (2018) to 17.1 m²/ha (2020).
- FI-Let: spring 2016, partial harvest (~75% of tree biomass in the EC footprint plot) and a 2.35 ha clear-cut next to it.
- FR-Fon: thinning 2010–11 (LAI −36%).
- FR-Hes: thinnings in 1999–2000 (25% removed), 2005, 2010 and 2016 (later intensities not found). The EC height also changed: 18 m (1997–99), 23.34 m (2000–12), 27.1 m (2013–20).
- BE-Vie: thinning every 6 years.
- FR-Pue: experiments from 2003; thinning in 2005 (15% removed).

Grasslands export carbon with every cut or grazing period, so NEE alone is not their carbon balance. CH-Fru, for example, has a mean NEE of −357 ± 76 gC m⁻² yr⁻¹ but a net biome production of only −154 ± 80 gC m⁻² yr⁻¹ (Rogger et al. 2022). CH-Cha had a sward renewal (ploughing and reseeding) in 2012. Event tables exist for CH-Cha (ETH dataset doi:10.3929/ethz-b-000747025) and CH-Fru (CH-FRU_Management_2005-2023.xlsx on the Swiss FluxNet site page). They are not downloaded yet.

How to make a stand-replacing reset (a FATES logging/harvest event, or a new case that keeps soil pools only) is **not chosen yet**. Check what the FATES version in use supports before designing it.

## Files

| File | Content |
|---|---|
| [`ICOS38/ICOS38_post_spinup_start_info.csv`](ICOS38/ICOS38_post_spinup_start_info.csv) | **Main table**, one row per site: PFTs, spin-up class and expected NORMAL400 case, EC years, stand history, start-mode proposal, observed structure, sources |
| [`ICOS38/ICOS38_stand_history_management.csv`](ICOS38/ICOS38_stand_history_management.csv) | Curated stand origin and management history with source URLs. `evidence_status`: DOCUMENTED / DERIVED (year computed from an age at a reference year) / DOCUMENTED_AGE_ONLY / DOCUMENTED_PARTIAL(_EVENTS) |
| [`ICOS38/ICOS38_literature_observations.csv`](ICOS38/ICOS38_literature_observations.csv) | One row per value found in a site paper, site page or data-paper supplement: category, variable, value, unit, reference year, scope (which plot or footprint), `preferred` (1 = used in the main table), source and URL |
| [`ICOS38/PROFOUND/`](ICOS38/PROFOUND/) | Derived from PROFOUND v0.3 for CZ-BK1, IT-Col, FI-Hyy, DK-Sor: `PROFOUND_stand_totals.csv` (yearly density, basal area, height, DBH, biomass by component, LAI), `PROFOUND_thinning_events.csv`, `PROFOUND_soil_carbon.csv`, `co2_global_annual_ISIMIP.csv`. **CC BY-NC 4.0; read [`DATA_LICENSE.md`](ICOS38/PROFOUND/DATA_LICENSE.md) before use** (CZ-BK1 has publication conditions) |
| [`ICOS38/Flechard2020_supplement_ICOS38.csv`](ICOS38/Flechard2020_supplement_ICOS38.csv) | Tables S2–S5 and S7 of the Flechard et al. (2020) supplement for the 17 of our sites it covers, one row per site. Also merged into the literature table |
| [`ICOS38/ICOS38_BIF_structure_summary.csv`](ICOS38/ICOS38_BIF_structure_summary.csv) | One reference value per site and variable from the BADM, with year, plot type and flags |
| [`ICOS38/ICOS38_BIF_observations_long.csv`](ICOS38/ICOS38_BIF_observations_long.csv) | Every mean/single-value BADM record behind the summary |
| [`ICOS38/inputs/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv`](ICOS38/inputs/) | Copy of the PFT register (CLM-FATES-single-site-workflows, commit `a1579ebc`) |
| [`scripts/00_inventory_site_BIF_badm_readonly.py`](scripts/00_inventory_site_BIF_badm_readonly.py) | Read-only scan of every site's BIF on IRIDIS (`MY_EC_SITE/<SITE>/forcing/raw/` or the package zip) |
| [`scripts/01_extract_ICOS38_BIF_observations.py`](scripts/01_extract_ICOS38_BIF_observations.py) | BIF rows → long table and per-site summary |
| [`scripts/02_build_ICOS38_start_info.py`](scripts/02_build_ICOS38_start_info.py) | Merges the summary, the stand history, the literature table (`preferred=1` rows → `lit_*` columns) and the PFT register into the main table |
| [`scripts/03_extract_Flechard2020_supplement.py`](scripts/03_extract_Flechard2020_supplement.py) | Parses the Flechard et al. (2020) supplement PDF (not committed) into `Flechard2020_supplement_ICOS38.csv` |
| [`scripts/04_get_PROFOUND_on_IRIDIS.sh`](scripts/04_get_PROFOUND_on_IRIDIS.sh) | Downloads PROFOUND v0.3 (2.6 GB zip) to IRIDIS scratch, checks and unzips it, optionally copies the zip to Research File Storage, then runs script 05 |
| [`scripts/05_extract_PROFOUND_ICOS38.py`](scripts/05_extract_PROFOUND_ICOS38.py) | Read-only export of CZ-BK1, IT-Col, FI-Hyy and DK-Sor from the PROFOUND SQLite (stand, tree, soil, N deposition, CO2, site description, data policies) |
| [`scripts/06_derive_PROFOUND_targets.py`](scripts/06_derive_PROFOUND_targets.py) | Extract → yearly stand totals, detected thinnings, SOC stocks, global CO2 table (written to `ICOS38/PROFOUND/`) |

Regenerate the tables. The raw `bif_key_groups_rows.csv` (96 MB) stays on IRIDIS and is not committed.

```bash
python3 post_spinup/scripts/00_inventory_site_BIF_badm_readonly.py --out ~/BIF_inventory          # on IRIDIS
python3 post_spinup/scripts/01_extract_ICOS38_BIF_observations.py \
        --bif-rows ~/BIF_inventory/bif_key_groups_rows.csv --out post_spinup/ICOS38
python3 post_spinup/scripts/02_build_ICOS38_start_info.py
python3 post_spinup/scripts/03_extract_Flechard2020_supplement.py --pdf bg-17-1583-2020-supplement.pdf
bash post_spinup/scripts/04_get_PROFOUND_on_IRIDIS.sh      # on an IRIDIS login node; RFS_DIR=... to back up the zip
python3 post_spinup/scripts/06_derive_PROFOUND_targets.py --extract <PROFOUND_DIR>/ICOS38_extract --out <PROFOUND_DIR>/derived
```

PROFOUND v0.3 is on IRIDIS at `/iridisfs/scratch/ly3n24/CLM_FATES/external/PROFOUND_v0.3/` (zip, unzipped SQLite, `ICOS38_extract/`). A backup copy of the zip is on the Research File Store at `/research/xclimatetbm/ly3n24/CLM_FATES/External_Data/PROFOUND_v0.3/`.

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

`ICOS38_literature_observations.csv` holds 429 values for 35 sites (223 from the Flechard et al. 2020 supplement, 52 from PROFOUND). Every row has a source and a URL. A value is used in the main table only if `preferred=1`. Rows with `preferred=0` are kept as cross-checks: secondary compilations, values for a plot that is not the EC footprint, or values that look wrong.

What the literature changes for the NEE comparison:

- **Footprint versus plot.** At CH-Dav the EC footprint is younger and smaller (~60 yr, 9.9 m) than the unthinned core plots (~106 yr, 18.3 m), which is where the BIF biomass (35.8 kg DM m⁻²) comes from. Compare simulated biomass with the footprint values, not the plot values.
- **NEE trends.** Fernández-Martínez et al. (2017) give NEP trends for 13 of our forests. Strong increases at IT-Lav (+41.8 gC m⁻² yr⁻¹ per year), IT-Ren (+37.9), DK-Sor (+27.3) and FR-Hes (+26.4); declines at FR-Pue (−10.3) and DE-Hai (−7.3). Run with constant CO2, an unmanaged model cannot produce these trends. This is one reason the transient CO2 series (item 4) matters.
- **Long-term means for checks.** Mean NEP: DE-Lnf 590 ± 190, DE-Hai 512 ± 89, DE-Tha 430, DK-Sor 115 (1996–2008), DE-Gri 90 gC m⁻² yr⁻¹. A secondary compilation (Biogeosciences 22:4729, 2025, Table S1) gives NEE/GPP/Reco for 10 of our forests. These are `preferred=0`: GPP − Reco does not match −NEE at four sites, and IT-Lav (−1844 gC m⁻² yr⁻¹) is implausible. Use them to sense-check our own FLUXNET means, not as targets.
- **Non-biological CO2 signals.** At DE-Hai, advection makes the EC sink 100–200 gC m⁻² yr⁻¹ larger than bottom-up estimates. At ES-LJu and ES-Agu (also called Balsa Blanca), turbulence ventilates CO2 out of the subsoil and the tower records it. CLM-FATES will not reproduce either; expect a bias there that is not a model error.
- **Soil texture and water.** Flechard et al. (2020) Table S4 gives clay/sand/silt and wilting point, field capacity and saturation for 17 sites. Soil water stress drives summer NEE, so compare these with `PCT_SAND`/`PCT_CLAY` in each site's surface file before the runs. Check the extremes first: BE-Bra and NL-Loo are almost pure sand (89–96% sand), DE-Hai and IT-Col are clay-rich (40–59% clay; but see the IT-Col conflict below), and RU-Fyo is peat.
- **Soil respiration partitioning.** Published annual soil respiration (Table S7) exists for 12 of our forests and the heterotrophic fraction for 11, for example DE-Hai 884 gC m⁻² yr⁻¹ with Rhet/Rsoil 0.52, and FR-Hes 620 with 0.37. These help tell whether an NEE bias comes from photosynthesis or from respiration.
- **Leaf C:N.** Foliar C/N ranges from 20 (DK-Sor, IT-Col) to 47 (BE-Vie) across the 17 sites. Compare it with the leaf C:N in the FATES parameter file for each site's PFT.
- **Yearly stand data for four sites (PROFOUND).** CZ-BK1 (1997–2015, yearly), DK-Sor (1994–2017, yearly, reconstructed from tree rings), FI-Hyy (1995–2011, yearly, three species groups) and IT-Col (1992–2012, every 5 years). They give density, basal area, height, DBH and biomass by component, so the regrowth after a reset and the effect of each thinning can be checked year by year, not only against a single value. Latest aboveground biomass (stem + branches + foliage): CZ-BK1 12.0 (2015), FI-Hyy 11.7 (2011), DK-Sor 30.8 (2017, stem + branches; no foliage for beech) kg DM m⁻².
- **Soil carbon for three sites (PROFOUND).** From C %, bulk density and layer thickness: DK-Sor 8.4 kgC m⁻² (0–55 cm), FI-Hyy 7.2 (0–89 cm, gravel and O horizon not handled), IT-Col 23.8 (0–80 cm, stony soil, so an overestimate). The DK-Sor BIF value (1.1–1.3 kgC m⁻²) is therefore wrong. Compare these with the spun-up soil C before the runs: a large mismatch will show up as a bias in heterotrophic respiration and NEE.
- **Soil texture disagrees between sources** at IT-Col (PROFOUND: sandy, clay 2–23%; Flechard: silty clay, clay 59%) and CZ-BK1 (PROFOUND sand 54–64%; Flechard sand 22%, silt 58%). Resolve these before using either to check the surface file.
- **CO2 during the spin-up versus history.** The spin-ups used a constant 376.95 ppm, which is the global level of about 2004. A reset at establishment means regrowth under much lower CO2 (about 294 ppm in 1887, 307 ppm in 1929, 340 ppm in 1981; ISIMIP series in PROFOUND). The soil pools, however, were spun up under 2004 CO2. Keep this in mind when reading soil respiration after a reset.
- **Measurement height.** FR-Hes raised its EC system twice (18 → 23.34 → 27.1 m). The forcing reference height should follow the year.

## Open items

1. When the replacement NORMAL400 runs finish: write a read-only IRIDIS script that reads each case's final restart (path, model year, `spinup_state`), `CCSM_CO2_PPMV`, DATM years, surface and parameter file. Merge these into the main table.
2. Decide the start-mode design (the table above) and how to make a stand-replacing reset in FATES.
3. Choose the transient CO2 series. PROFOUND's ISIMIP series (global annual, historical 1765–2015, RCPs from 2006) ends in 2015, before most EC records end. Prefer CTSM's own CMIP6 historical + SSP CO2 stream for the runs (check which file the installed CTSM uses), and use the ISIMIP series only as a cross-check; the two agree in 2015 (399.4 ppm).
4. **NL-Loo:** its legacy PRE50/AD200/POST300 case used the default needleleaf parameters and is not in the 2 Nov rollout. Rerun it with AD400 → NORMAL400 and variant F, or exclude it.
5. Remaining literature gaps:
   - **Soil organic carbon stocks.** The Flechard et al. (2020) supplement has only topsoil SOC *concentration* (gC/kg). Their main Table 1 (site characteristics and multi-year NEP, GPP, Reco per site) is published as a spreadsheet: https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-t01.xlsx. It cannot be downloaded from here; it needs to be uploaded.
   - **PROFOUND, CZ-BK1 publication condition.** Any paper that uses the CZ-BK1 stand, tree or soil data must carry the CzeCOS acknowledgement (grant LM2015061), and Lenka Krupkova must be notified (see `ICOS38/PROFOUND/DATA_LICENSE.md`).
   - **FATES inventory initialisation.** PROFOUND's TREE view has individual tree DBH and height for the 4 sites (CZ-BK1 8131 records 1997–2015, DK-Sor 7514 records 1994–2017). If our FATES version supports inventory initialisation (`use_fates_inventory_init`), these could start the EC-period run from the observed size distribution instead of a reset at establishment. Check before designing the start modes.
   - DE-Obe: no structure beyond ~53 yr / 15 m around 2008.
   - Thinning intensities for FR-Hes after 2000; thinning years before 2013 for DK-Sor; harvest extent at DE-Tha in 2020; planting year and density at DE-Hzd; IL-Yat thinning years.
   - Management event tables for CH-Cha and CH-Fru (exist, not downloaded).
   - The EC record for GL-ZaH.
6. Sites without a BIF in the scan (FI-Sod, FR-Fon, IT-Col, IT-Noe, GL-ZaH): check whether their ICOS v1.3 packages on IRIDIS contain one.
