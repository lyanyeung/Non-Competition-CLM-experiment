# Fixed Biogeography & no competition FATES experiment

**Research aim:** Evaluate forest- and ecosystem-carbon responses in FATES under **fixed biogeography** and **no inter-PFT competition**, using the best available EC-station vegetation evidence and transparently versioned site surface data.

**Standard spin-up for all NEW sites: 400 years of accelerated decomposition (AD400), followed by 400 years of Normal decomposition (NORMAL400). Total: 800 model years per site.** This is an experimental design, **not** evidence of convergence or a chronological 800-year historical simulation.

**Project status — 24 October 2026:**
- **38 original European/FLUXNET experiment sites:** [38-site PFT evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv). Of these, **22 have some numerical vegetation evidence**, but **not all have verified PFT horizontal ground-area fractions**; 16 have only qualitative evidence.
- **Protected examples (2):** **NL-Loo** and **DE-Tha**, with their existing operational histories retained unchanged. DE-Tha direct AD first five years 1996→2001 and independent AD5→Normal5 test 2001→2006 both succeeded technically; the AD395 continuation 2001→2396 was **submitted** (initial run 4713885 and archive 4713886), not proven finished at this documentation update. NL-Loo's previous PRE50/AD200 model is a **legacy exception**, not the new standard.
- **Batch 01 (10 sites):** documented and selected for detailed site evidence checks; **no new Batch01 model case, surface or Slurm jobs created**.
- **Batch 02 (10 sites):** documented and reserved, with unresolved measurement-denominator and/or conflicting evidence issues.

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

| **Batch01: investigate first** | **Batch02: reserve for later** |
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

- [Batch01 site evidence and runbook](examples/Batch01_10/README.md)
- [Batch01 10-site register and source URLs](data/batch01_10_sites.csv)
- [Batch02 10-site reserve register](data/batch02_10_sites.csv)
- [Master 22-candidate role ledger](data/22_site_cohort.csv)

**Scientific disclaimer:** the original 38-site inventory is a *screening aid*, not a completed PFT area map. **No stand-species, tree-carbon-stock, basal-area or vegetated-cover percentage may be silently treated as CLM `PCT_NAT_PFT` ground area.** Even when a stand reports 100% spruce or beech, that does **not** by itself justify a 100% natural-landunit fraction for the tower footprint. Batch01 numeric grouping remains on **`EVIDENCE_ONLY_HOLD_SURFACE`** until each site's scientific provenance and surface mapping are accepted.

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

**HPC safety:** independent case/run/archive directories, SHA256-pinned inputs, single-core or explicitly requested resources, and exact Slurm accounting, run/archive log, three-component restart and mode verification before each stage transition. Protect scratch inode/storage limits and archive verified results to Research Filestore where appropriate. **Nothing in the new Batch01/02 documentation submits a model job.**

## Proven examples and why new sites must be independently adapted

**DE-Tha — Tharandt**: [site example](examples/DE-Tha/README.md) documents the published forest mixture proxy **ENF 87%, DNF 10%, DBF 3%**, NATVEG100/CROP0 as a local tower proxy and measured-soil literature proxy **sand17/silt71/clay12** (10 texture input layers; deeper extrapolation noted). Its first AD5 1996–2001 achieved `spinup_state=2`, and separate AD5→Normal5 2001–2006 achieved `spinup_state=0`. Remaining AD395 was **submitted**, not confirmed complete. The [Stage10](examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py), [Stage11](examples/DE-Tha/scripts/11_DE_Tha_AD400_continue_after_smoke.py), [Stage12](examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py), [Stage13](examples/DE-Tha/scripts/13_check_AD5_jobs_and_restart.py) and [Stage14](examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) scripts are **DE-Tha-specific** and must not be run unchanged for another station.

**NL-Loo — Loobos**: older PRE50/AD200 experiment in [scripts/](scripts/) with its own case history. Its [500-m-radius ground area study](https://essd.copernicus.org/articles/18/2023/2026/) reported pine/conifer, broadleaf and open-ground fractions; unresolved grass-versus-heath area and local footprint interpretation must be preserved. NL-Loo is **excluded** from the new Batch01/02 list; no running cases are changed.

The older [NL-Loo three-stage runbook](docs/NL_Loo_V3_550_pipeline.md) remains available as **archival example documentation**, not the universal current protocol.

## Origin, methods and no-overwrite policy

Original site forcing preparation, 6/8/11/13-site experiment development, ICOS site PFT research and diagnostics are in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows). This repository adds isolated **fixed-biogeography/no-competition** scientific cases. Never rewrite earlier experiments or infer a successful 800-year run from successful CIME submission. Site inventory, raw meteorological packages, generated NetCDF, restarts and binaries do not belong in this source-code GitHub repository.

**Reference reading:** [FATES prescribed biogeography/no-competition](https://fates-users-guide.readthedocs.io/projects/tech-doc/en/stable/fates_tech_note.html), [HLM↔FATES PFT map](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html), [Flechard et al. 2020 site inventory supplement](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf).
