# Fixed Biogeography & no competition FATES experiment

## Needleleaf collapse diagnosis (1 November 2026)

[Diagnosis log](docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md): needleleaf-dominated sites lose their vegetation in AD400 through FATES carbon-starvation mortality (storage falls below 1 × leaf carbon every winter with the default needleleaf parameters), not water stress — the history BTRAN ≈ 0.05 is canopy-cover dilution. Figures, numbers, source-code references, corrections and the fix plan are in the log.

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
