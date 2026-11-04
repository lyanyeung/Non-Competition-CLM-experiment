# Fixed Biogeography & no competition FATES experiment

## Needleleaf collapse diagnosis (1 November 2026)

[Diagnosis log](docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md): needleleaf-dominated sites lose their vegetation in AD400 through FATES carbon-starvation mortality (storage falls below 1 × leaf carbon every winter with the default needleleaf parameters), not water stress — the history BTRAN ≈ 0.05 is canopy-cover dilution. Figures, numbers, source-code references, corrections and the fix plan are in the log.

**Needleleaf fix adopted (2 November 2026):** for PFT 2 (needleleaf evergreen) use `fates_alloc_storage_cushion` 2.4 and `fates_leaf_slatop` 0.008 (default 1.2 / 0.005). In 100-year trials at ten sites this keeps the needleleaf alive and stable everywhere (median GPP/EC 1.09; default 0.04). The adopted parameter file changes only PFT 2, so it is used at every site; only sites containing PFT 2 need rerunning. See [section 9 of the log](docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md#decision-2026-11-02-f-is-the-production-needleleaf-parameter-set).

**Maintenance:** deleted model output, stopped runs and replaced cases are recorded in [maintenance/](maintenance/README.md), together with the deletion code and a read-only summary tool.

**Site flags:** **US-CMW is excluded (groundwater-dependent riparian mesquite woodland: tower ET 662 mm/yr against 263 mm/yr precipitation; a single-point CLM column cannot supply that water).** CZ-Stn and DE-Lnf (DBF 100, vegetation gone in AD years 14–15) are under investigation with a 50-year diagnostic re-run. See [section 11 of the log](docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md#11-site-anomaly-checks-us-cmw-cz-stn-de-lnf-2026-11-01).

## Special site events and conditions (4 November 2026)

The experiment spins every site up for 800 years with fixed vegetation and compares the equilibrium model
with the tower. That is only a fair test where the tower measures an old, undisturbed stand of the modelled
vegetation that lives on local rain. This chapter lists every site where that is not true. **Nothing new is
excluded and no output is deleted**; the entries decide which tower years and which fluxes are compared.

- Machine-readable register: [`data/site_special_events.csv`](data/site_special_events.csv) (one row per event,
  with the comparison rule and the source).
- Evidence and method: [land use and disturbance](docs/LAND_USE_CHANGE_SCREENING.md) ·
  [groundwater](docs/GROUNDWATER_SCREENING.md).
- Scope: all 86 sites of AmeriFlux B01–B05 and ICOS B01–B04. **No site is a forest converted to cropland.**

### A. Events: disturbance and land-use change (8 in the record, 7 young stands, 5 on former land use, 1 to confirm)

Rules: **in the record** → split the EC years at the event and never fit parameters across the break;
**young stand** → compare GPP seasonality, not GPP magnitude or NEE; **former land use** → GPP yes, but NEE and
soil carbon are not an equilibrium test.

**Disturbance inside the flux record** (8)

| Site | Batch | Year | What happened | In flux record | How to compare |
|---|---|---|---|---|---|
| [US-Vcm](https://ameriflux.lbl.gov/sites/siteinfo/US-Vcm) | AmeriFlux B05 | 2013 | Thompson Ridge fire (late May 2013), stand-replacing: every tree killed; flux gap May 2013-Jan 2014; tower rebuilt in the burned stand | yes | split EC at 2013; post-fire years are not the modelled forest |
| [US-UMd](https://www.osti.gov/dataexplorer/biblio/dataset/1246134) | AmeriFlux B05 | 2008 | FASET: every aspen and birch (>6700 trees, ~35% of canopy LAI) girdled over 39 ha in spring 2008 | yes | split EC at 2008 |
| [US-GLE](https://www.osti.gov/dataexplorer/biblio/dataset/1246056) | AmeriFlux B02 | ≤2008 | Decade-long spruce beetle outbreak, peak 2008, 85% of forest basal area killed | yes | split EC around 2008; treat later years as a dead-canopy stand |
| [CA-LP1](https://www.osti.gov/biblio/1660337) | AmeriFlux B01 | 2006–2011 | Mountain pine beetle attack on a pure lodgepole pine stand from summer 2006 (five-year disturbance) | yes | whole record is a disturbed stand; no equilibrium comparison of GPP magnitude |
| [US-Slt](https://www.osti.gov/dataexplorer/biblio/dataset/1246096) | AmeriFlux B04 | 2006–2008 | Gypsy moth defoliation 2006-2008, complete in 2007 | yes | exclude 2006-2008 from GPP statistics |
| [FI-Let](https://meta.icos-cp.eu/objects/XCbOcz7bn_Fs-SsN1vyner9J/ICOSETC_FI-Let_FLUXNET_HH_L2.zip.json) | ICOS B03 | 2016 | Fen drained for forestry in 1969 (land-use change); partial harvest March 2016 | yes | split EC at 2016; drained peat soil carbon not at equilibrium |
| [US-Ho3](https://research.fs.usda.gov/nrs/forestsandranges/locations/howland) | AmeriFlux B02 | to confirm | Howland harvest site: commercial shelterwood harvest; uptake reduced for about 7 years (harvest year to confirm from BADM) | yes | split EC at the harvest year |
| [CH-Cha](https://holukas.github.io/dataset_ch-cha_flux_product/intro.html) | ICOS B03 | 2012 | Intensively managed grassland; grassland restoration (renewal) in 2012 | yes | exclude 2012 (and 2013) from GPP statistics |

**Young stand (clear-cut, windthrow, fire, plantation)** (7)

| Site | Batch | Year | What happened | In flux record | How to compare |
|---|---|---|---|---|---|
| [DE-Hzd](https://deims.org/api/sites/bf152bfd-f7b4-4a4b-9785-282a8f8ba539) | ICOS B03 | 2007 | Storm Kyrill windthrow (40 ha) in 2007; oaks planted afterwards; flux record from 2010 | yes (whole record) | GPP seasonality only; not a reference for mature DBF; not NEE |
| [CA-TP1](https://ameriflux-new.hyperarts.com/sites/siteinfo/CA-TP1) | AmeriFlux B01 | 2002 | White pine planted 2002 on a sandy agricultural field abandoned three years earlier | yes (whole record) | GPP seasonality only; not NEE or soil carbon |
| [CA-Ca3](https://www.osti.gov/dataexplorer/biblio/dataset/1480302) | AmeriFlux B01 | 1987–1988 | Douglas-fir harvested 1987, broadcast-burned, replanted 1988 | before record | GPP seasonality only; not NEE |
| [US-Me6](https://www.osti.gov/dataexplorer/biblio/dataset/1246128) | AmeriFlux B03 | 1979–1990 | Severe fire 1979, salvage-logged, replanted 1990; young ponderosa pine, LAI 0.6-0.8 | before record | GPP seasonality only; not NEE |
| [US-Rpf](https://www.osti.gov/dataexplorer/biblio/dataset/1579540) | AmeriFlux B04 | to confirm | Burned black spruce forest now dominated by deciduous trees and shrubs (fire year to confirm from BADM) | before record | GPP seasonality only; not NEE |
| [US-NC2](https://www.mdpi.com/1238472) | AmeriFlux B03 | to confirm | Intensively managed loblolly plantation on drained forested wetland, 15-28 years old during the record, ~30-year rotations | yes (whole record) | GPP seasonality only; not NEE |
| [CZ-BK1](https://training.deims.org/a61dd7df-5fd7-47b4-8172-b7dfaf969748) | ICOS B01 | 1981 | Managed secondary pure Norway spruce stand planted 1981 with 4-year-old seedlings | before record | GPP seasonality only; not NEE |

**Planted/restored on former farmland, heath or shrubland** (5)

| Site | Batch | Year | What happened | In flux record | How to compare |
|---|---|---|---|---|---|
| [IL-Yat](https://meta.icos-cp.eu/resources/stations/ES_IL-Yat) | ICOS B03 | 1964 | Aleppo pine afforestation from 1964 on former semi-arid shrubland; soil carbon still accumulating | before record | GPP yes; NEE and soil carbon not an equilibrium test |
| [BE-Bra](https://deims.org/api/sites/68e6a8e5-d6d2-4c8c-91c4-10e7f87ac556) | ICOS B02 | 1929 | Scots pine planted 1929 on former heathland | before record | GPP yes; NEE and soil carbon not an equilibrium test |
| [CA-TP3](https://www.osti.gov/dataexplorer/biblio/dataset/1881566) | AmeriFlux B01 | 1974 | White pine plantation established 1974 on sandy abandoned land | before record | GPP yes; NEE and soil carbon not an equilibrium test |
| [CA-TP4](https://www.osti.gov/biblio/1246012) | AmeriFlux B01 | 1939 | White pine plantation established 1939 on sandy abandoned land | before record | GPP yes; NEE and soil carbon not an equilibrium test |
| [US-UiD](https://ameriflux.lbl.gov/sites/siteinfo/US-UiD) | AmeriFlux B05 | to confirm | Restored native prairie on the University of Illinois Energy Farm (prime farmland); restoration year to confirm | unknown | GPP yes; NEE and soil carbon not an equilibrium test |

**To confirm** (1)

| Site | Batch | Year | What happened | In flux record | How to compare |
|---|---|---|---|---|---|
| [US-Vcp](https://fluxnet.org/2014/04/30/thompson-ridge-wildfire-takes-out-ameriflux-core-site/) | AmeriFlux B05 | 2013 | Thompson Ridge fire burned the same Valles Caldera preserve; whether the ponderosa tower footprint burned is not stated | unknown | check BADM disturbance records |

### B. Site conditions: groundwater and water table

US-CMW is excluded because its tower ET is 2.5 × precipitation (riparian phreatophytes on groundwater a
single-point CLM column cannot supply). No other site meets that criterion in the data checked so far.

| Class | Sites | Reading |
|---|---|---|
| EXCLUDED | US-CMW | not used to judge GPP |
| HIGH: groundwater use measured, or water table in the root zone | US-Ton (blue oaks take ~80 % of summer ET from groundwater at ~8 m), US-NC2 (drained coastal-plain plantation, high water table), BE-Bra (perched water table 0.8–2.5 m), RU-Fyo (paludified shallow-peat spruce), FI-Let (drained fen peatland) | check model ZWT/BTRAN before blaming vegetation parameters |
| MEDIUM: poorly drained, perched, or wet patches in the footprint | US-Ho1, US-Ho2, US-Ho3, CA-Man, US-SP1, FR-Fon, CH-Fru, DE-RuR, GF-Guy | model check if a dry-spell GPP bias appears |
| PERMAFROST: water perched on permafrost (separate issue) | US-BZS (ET/P 1.11), US-Uaf, US-Rpf, US-EML, US-ICh, US-ICt, GL-ZaH | judge with the arctic sites |
| LOW-WATCH | CH-Cha, AT-Neu, FI-Sod, US-Syv, BR-Ma2, US-Kon | re-check after the ET/P screen |

### C. Sites flagged more than once

| Site | Flags | Consequence |
|---|---|---|
| US-NC2 | groundwater HIGH + managed young plantation | the least equilibrium-like site; GPP seasonality only |
| BE-Bra | groundwater HIGH + planted on heath (1929) | GPP with model water table check; no NEE equilibrium test |
| FI-Let | groundwater HIGH (drained peat) + harvest 2016 | split at 2016; drained-peat carbon not at equilibrium |
| US-Ho3 | groundwater MEDIUM + harvest site | split at the harvest year |
| US-Rpf | permafrost + fire-scar succession | arctic group; GPP seasonality only |
| **DE-Hzd** | young oak plantation on a 2007 windthrow, EC precipitation implausible (3169 mm/yr) | **it is the reference used for CZ-Stn and DE-Lnf in the DBF diagnosis; use DE-Hai instead** |

### D. What to run on IRIDIS (read only)

```bash
# one-time: a small read-only checkout of main (scripts + data only)
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/lyanyeung/Non-Competition-CLM-experiment ~/nc_main
cd ~/nc_main && git sparse-checkout set examples/Cross_cohort_NORMAL400/scripts data
# later: cd ~/nc_main && git pull
S=examples/Cross_cohort_NORMAL400/scripts
# 1) tower ET/P for all 86 sites (the US-CMW test)  -> ~/groundwater_screen_tower_ET_P.csv
python3 -B $S/30_groundwater_screen_tower_ET_P.py | tee ~/gw_screen.txt
# 2) events against each site's EC years + BADM disturbance/management entries -> ~/site_events_vs_flux_record.csv
python3 -B $S/31_site_events_vs_flux_record.py --all-sites | tee ~/site_events.txt
```

Both need pandas (the `clm_fates_env` environment has it). Reading BADM `.xlsx` files needs openpyxl
(`pip install --user openpyxl` if script 31 says so).

Script 31 settles the open years (US-Ho3 harvest, US-Rpf fire, US-UiD restoration, whether US-Vcp burned) from
the BADM `GRP_DM_*` records and lists BADM disturbances at sites not yet in the register. Its output goes back
into `data/site_special_events.csv` and this chapter.

## NL-Loo V3 three-phase figures

[NL-Loo PRE50 → AD200 → POST300 convergence and EC plotting](docs/NL_LOO_THREE_PHASE_PLOTS.md) checks the actual V3 history, marks incomplete phases and PRE50-based EC comparisons as interim, and uses NT-first tower GPP. It does not infer that POST300 has run.


## Separate AmeriFlux ten-site AD400 planning (24 October 2026)

The user-confirmed AmeriFlux Batch01 **Stage80 forcing selection**, **Stage81 213 annual NetCDF files**, and **Stage82 213/213 SHA audit** are complete. The original NL-Loo case recovery directory is **NOT** a verified full DATM stream template (`DATM_MODE=1PT`, `stream_mode=NOT_IDENTIFIED`), and all ten Stage81 NetCDF files intentionally omit `ZBOT`. **These are not yet scientifically or technically connected to CIME/FATES**; no AD400 run should be submitted just from the NetCDF build result.

[**AmeriFlux-specific ten-site AD400 → Normal400 preflight and runbook**](examples/AmeriFlux_Batch01_10/README.md) is separate from the European/ICOS `examples/Batch01_10` scripts. It explains the safe progression: Stage80/81/82 read-only provenance check → verify static/dynamic site TA_F sensor heights/ZBOT and DATM time/stream/domain → one new isolated FATES fixed-biogeography/no-competition case and AD5 smoke → guarded remaining AD395 → independent hybrid Normal5 → guarded Normal395. **Do not run existing Europe-specific Batch01 submission scripts for AmeriFlux stations**.


## Operator status snapshot — 26 October 2026, 20:00 UK

Submitted means CIME returned job IDs; completion still has to be audited.

| Cohort | AD400 | NORMAL400 |
| --- | --- | --- |
| **ICOS Batch01** (10) | 10/10 done | 10/10 archived to Y+800; `audit-normal400` not yet run |
| **ICOS Batch02** (10) | FI-Hyy, FR-Hes, CH-Fru, IT-MBo PASS. Stage43 history-fix AD400 running: ES-LJu, FR-FBn, CH-Lae (FR-FBn kept at ENF75/EBF25, inside the ICOS range). IT-Noe history-fix AD400 running. **DK-Sor and BE-Bra rebuilt (Stage44)** with ICOS basal-area PFT and 1996–2025 forcing (DK-Sor 2025 added by Stage45), submitted 4741595 and 4741597; all old outputs deleted | FI-Hyy, FR-Hes, CH-Fru, IT-MBo Normal395 running |
| **ICOS Batch03** (10) | 10/10 | 6/10 audited PASS; IT-Lav, FI-Let, DE-Hzd, GF-Guy running |
| **AmeriFlux Batch01** (10) | CA-Ca3, CA-LP1 PASS; CA-TP4, BR-Ma2 AD395 running; 6 not started | CA-Ca3, CA-LP1 direct Normal400 (80×5) queued |
| **AmeriFlux Batch02** (10) | **Stage06 direct AD400 submitted 10/10.** US-ICh and US-ICt failed at init (peat 0/0 sand+clay); repaired by Stage07 (L1–L4 ← L5 mineral texture) and resubmitted as 4741683 and 4741685. The other 8 are running | Not started |

**27 Oct 14:25 UK — Normal400 direct (80 × 5) submitted for 9 sites, all PENDING:** US-BZS 4748888, US-CMW 4748890, US-EML 4748892, US-GLE 4748896, US-ICt 4748898, IT-Noe 4748900, FR-FBn 4748902 (cross-cohort controller), CA-TP4 4748904, BR-Ma2 4748906 (AmeriFlux Batch01 Stage21). AD400 audit PASS for each first. CA-Ca3 and CA-LP1 direct Normal400 reached 2801 / 2807 (80 segments; first segment `spinup_state=0`). Still in AD400: US-Ha1, US-Ho1, US-Ho2, US-Ho3, ES-LJu, CH-Lae, DK-Sor, BE-Bra. US-ICh failed again (pending diagnosis; its st_archive 4741684 is DependencyNeverSatisfied).

**Controller (27 Oct):** [cross-cohort direct Normal400 controller](examples/Cross_cohort_NORMAL400/README.md) for the AmeriFlux Batch02 (Stage06) and ICOS Batch02 Stage40/43/44 AD400 cases. It audits AD400 completion read-only, stages hybrid Normal cases for PASS sites only, and submits 80 × 5 years with no Normal5 smoke. AmeriFlux Batch01 stays on its Stage21 controller.

**PFT register:** 38-site register updated with ICOS ETC basal area ([FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv)):
- Changed: DK-Sor DBF 100, BE-Bra ENF 84 / DBF 16, FR-FBn ENF 70 / EBF 30.
- 11 sites confirmed.
- 24 sites have no ICOS report.
- ICOS reports contain no soil texture.

**Stale jobs:** the seven `DependencyNeverSatisfied` archive jobs were cancelled at 19:54.

**Research aim:** Evaluate forest- and ecosystem-carbon responses in FATES under **fixed biogeography** and **no inter-PFT competition**, using the best available EC-station vegetation evidence and transparently versioned site surface data.

**Standard spin-up for all NEW sites: 400 years of accelerated decomposition (AD400), followed by 400 years of Normal decomposition (NORMAL400). Total: 800 model years per site.** This is an experimental design, **not** evidence of convergence or a chronological 800-year historical simulation.

**Project status — 24 October 2026:**
- **38 original European/FLUXNET experiment sites:** [38-site PFT evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv). Of these, **22 have some numerical vegetation evidence**, but **not all have verified PFT horizontal ground-area fractions**; 16 have only qualitative evidence.
- **Protected examples (2):** **NL-Loo** and **DE-Tha**, with their existing operational histories retained unchanged. DE-Tha direct AD first five years 1996→2001 and independent AD5→Normal5 test 2001→2006 both succeeded technically; the AD395 continuation 2001→2396 was **submitted** (initial run 4713885 and archive 4713886), not proven finished at this documentation update. NL-Loo's previous PRE50/AD200 model is a **legacy exception**, not the new standard.
- **Batch 01 (10 sites):** [implemented ten-site Batch01 example](examples/Batch01_10/README.md). **All 10 independent FIXNC surfaces were created**; the operator reports the private-overlay FATES AD case recovery resolved. AD5 run/archive completion must be independently verified from Slurm and three-component restarts.
- **Batch 02 (10 sites):** [second-cohort example and runnable input inventory](examples/Batch02_10/README.md), initialized 25 October 2026 for the requested **AD400 → Normal400** workflow. Current implemented step is a read-only actual-input trace; site surfaces and submission scripts await actual source-path/PFT/soil decisions. The newer reviewed evidence corrects the old FI-Hyy 60/25/15 lead; no unresolved remainder is silently assigned.
- **Batch 03 (10 sites):** [third-cohort example](examples/Batch03_10/README.md), created 25 October 2026 from the 16 remaining sites of the 38-site inventory: IT-Lav, FI-Let, IL-Yat, DE-Obe, CZ-Stn, DE-Lnf, DE-Hzd, GF-Guy, AT-Neu, CH-Cha. Same operation as Batch01 (FIXNC surfaces → private-overlay FATES AD recovery → AD5 smoke → AD395), with named PFT proxies and documented soil fallbacks. AD400 verified complete 10/10, Normal5 verified and Normal395 submitted 10/10 (26 October 2026); IL-Yat runs as bare ground 52 / ENF 48 from measured crown cover.

## Standard run design: AD400 → NORMAL400

| Stage | Duration | CIME/land mode | Case separation | Submission plan |
| --- | ---: | --- | --- | --- |
| **AD400** | **400 model years** | `CLM_ACCELERATED_SPINUP=on`; FATES generated `spinup_state=2` | Independent AD case, cold-start only after correct site inputs validated | **5-year smoke**, verify archived CLM/DATM/CPL restart; only then guarded **395-year continuation** |
| **NORMAL400** | **400 model years** | `CLM_ACCELERATED_SPINUP=off`; verify Normal restart `spinup_state=0` | A **separate hybrid-restart case** from the final AD400 checkpoint | **5-year Normal smoke**, verify archived Normal restart; only then guarded **395-year continuation** |
| **Total spin-up** | **800 model years/site** | Recycled site forcing; constant documented spin-up CO₂ baseline | The two model modes **must never be interchanged inside an active self-resubmitting case** | 160 validated five-year segments, or 80 per mode |

Use **each site's own vetted forcing years and model start date**. Example DE-Tha uses 1996→2396 for AD400; these dates cannot be reused unmodified for another tower. A site starting at Y reaches AD400 at Y+400 and NORMAL400 at Y+800, using artificial model calendar years and repeated climate forcing rather than historical forcing repeated once. Any chronological historical/transient run is a **different later experiment**, started from an independently chosen spun-up state.

**New Batch01/02 sites do NOT run an initial Normal50.** The old repo's `PRE50→AD200→POST300` plan is retained only as part of the historical NL-Loo example, not the current new-site protocol. The target 400+400 years is not proof of soil or vegetation-carbon equilibrium; track the relevant trends over the final run years.

See the complete [AD400 → NORMAL400 reproducible protocol](docs/AD400_NORMAL400_PROTOCOL.md) before building or submitting a new case.

## Cohort assignment (22 quantitative-evidence leads)

The two existing examples are **NL-Loo** and **DE-Tha**. The remaining 20 are separated into two new **ten-site** cohorts:

| **Batch01: first cohort** | **Batch02: second cohort, input audit initialized** |
| --- | --- |
| CZ-BK1 | DK-Sor |
| IT-Ren | FR-Hes |
| RU-Fyo | FR-FBn |
| CH-Dav | BE-Bra |
| IT-Col | IT-Noe |
| FR-Fon | CH-Fru |
| FI-Sod | CH-Lae |
| FR-Pue | ES-LJu |
| DE-Hai | FI-Hyy |
| BE-Vie | IT-MBo |

**Batch01 core goal:** assess quantitative tree-species evidence and obtain defensible **fixed FATES functional-type distributions**, accounting for the survey denominator, unknown species, nonforest/crop/bare-ground fraction, vegetation footprint, and active FATES PFT mapping.

- [**Batch01 ten-site FIXNC surface, successful private FATES AD recovery, guarded AD5 submit workflow and failed-code record**](examples/Batch01_10/README.md)
- [Batch01 Stage01 ten-site source inventory script](examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py)
- [Batch01 Stage02 actual CIME/DATM case-input tracer](examples/Batch01_10/scripts/02_trace_actual_case_inputs.py) — launched only after Stage01, original model files read-only
- [Policy: never assign unknown forest-PFT remainder to GRA by default](docs/PFT_UNKNOWN_RESIDUAL_POLICY.md)
- [Batch01 10-site register and source URLs](data/batch01_10_sites.csv)
- [Batch02 ten-site example, download commands and AD400 → Normal400 runbook](examples/Batch02_10/README.md)
- [Batch02 10-site evidence register](data/batch02_10_sites.csv) and [unresolved input gates](data/batch02_10_input_gates.csv)
- [Batch03 ten-site example, selection rationale and IRIDIS run commands](examples/Batch03_10/README.md)
- [Batch03 site register](data/batch03_10_sites.csv), [PFT scenarios](data/batch03_10_pft_scenarios.csv) and [soil decisions](data/batch03_10_soil_input_decisions.csv)
- [Master 22-candidate role ledger](data/22_site_cohort.csv) (historical screening statuses; per-batch examples carry current operational status)

**Unclassified percentages are not automatically grass:** see the [mandatory residual-PFT policy](docs/PFT_UNKNOWN_RESIDUAL_POLICY.md). For example, BE-Vie's unresolved 20% is forest stand composition, and FR-Fon's <3% is tree basal area; neither is measured ground grass cover. A GRA fraction requires defensible grass-area observations and a checked HLM→FATES grass mapping.

**Scientific disclaimer:** the original 38-site inventory is a *screening aid*, not a completed PFT area map. **No stand-species, tree-carbon-stock, basal-area or vegetated-cover percentage may be silently treated as CLM `PCT_NAT_PFT` ground area.** Even when a stand reports 100% spruce or beech, that does **not** by itself justify a 100% natural-landunit fraction for the tower footprint. For Batch01, the operator has selected explicit **idealized stand-level forest PFT proxies** and generated ten versioned surfaces. They must not be misrepresented as measured whole-footprint PFT-area fractions; remaining soil/peat and convergence uncertainties are documented in the Batch01 example.

For example, [ICOS CZ-BK1](https://meta.icos-cp.eu/resources/stations/ES_CZ-BK1) reports **99% Norway spruce and 1% silver fir within the investigated area**. Both are ENF, but the survey area and host-grid surface remain distinct. For comparison, DE-Hai's 64/28/7 reported tree composition refers to **carbon-stock shares**, not measured area.

## Required land-model options

FATES must be enabled in the **actual generated** `CaseDocs/lnd_in` and run-directory namelists, not just `user_nl_clm`:

```fortran
use_fates = .true.
use_fates_sp = .false.
use_fates_fixed_biogeog = .true.
use_fates_nocomp = .true.
```

Keep tree types distinct: `Larix decidua` is **DNF**, not ENF; `Quercus ilex` is generally mapped EBF only after checking supported PFT parameters. Verify the active `fates_hlm_pft_map` and the exact CTSM executable/parameter file; host CLM PFT indices are not necessarily FATES indices.

**Soil texture:** [observed first, grid fallback if none](docs/observed_soil_texture_policy.md). Use reliable site sand/silt/clay measurements where they exist, including sampling depth, reference and explicit interpolation/extrapolation. Never overwrite raw surfaces, previously verified NetCDFs, older case files or restart checkpoints.

**Forcing:** preserve the site-specific DATM streams, NO_LEAP calendar, meteorological QC records and concentration policy. A documented exploratory use of forcing still under `REVIEW` (as selected for the DE-Tha pilot) does not certify data quality for final scientific inference.

**HPC safety:** independent case/run/archive directories, SHA256-pinned inputs, single-core or explicitly requested resources, and exact Slurm accounting, run/archive log, three-component restart and mode verification before each stage transition. Protect scratch inode/storage limits and archive verified results to Research Filestore where appropriate. **Batch01 explicitly includes a guarded first-5-year `submit-smoke` action; do not rerun it after an attempted submission.** Batch02 remains separate. Check exact Slurm run/archive states and three-component restart files rather than assuming completion.

## Proven examples and why new sites must be independently adapted

**DE-Tha — Tharandt**: [site example](examples/DE-Tha/README.md) documents the published forest mixture proxy **ENF 87%, DNF 10%, DBF 3%**, NATVEG100/CROP0 as a local tower proxy and measured-soil literature proxy **sand17/silt71/clay12** (10 texture input layers; deeper extrapolation noted). Its first AD5 1996–2001 achieved `spinup_state=2`, and separate AD5→Normal5 2001–2006 achieved `spinup_state=0`. Remaining AD395 was **submitted**, not confirmed complete. The [Stage10](examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py), [Stage11](examples/DE-Tha/scripts/11_DE_Tha_AD400_continue_after_smoke.py), [Stage12](examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py), [Stage13](examples/DE-Tha/scripts/13_check_AD5_jobs_and_restart.py) and [Stage14](examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) scripts are **DE-Tha-specific** and must not be run unchanged for another station.

**NL-Loo — Loobos**: older PRE50/AD200 experiment in [scripts/](scripts/) with its own case history. Its [500-m-radius ground area study](https://essd.copernicus.org/articles/18/2023/2026/) reported pine/conifer, broadleaf and open-ground fractions; unresolved grass-versus-heath area and local footprint interpretation must be preserved. NL-Loo is **excluded** from the new Batch01/02 list; no running cases are changed.

The older [NL-Loo three-stage runbook](docs/NL_Loo_V3_550_pipeline.md) remains available as **archival example documentation**, not the universal current protocol.

## Origin, methods and no-overwrite policy

Original site forcing preparation, 6/8/11/13-site experiment development, ICOS site PFT research and diagnostics are in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows). This repository adds isolated **fixed-biogeography/no-competition** scientific cases. Never rewrite earlier experiments or infer a successful 800-year run from successful CIME submission. Site inventory, raw meteorological packages, generated NetCDF, restarts and binaries do not belong in this source-code GitHub repository.

**Reference reading:** [FATES prescribed biogeography/no-competition](https://fates-users-guide.readthedocs.io/projects/tech-doc/en/stable/fates_tech_note.html), [HLM↔FATES PFT map](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html), [Flechard et al. 2020 site inventory supplement](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf).
