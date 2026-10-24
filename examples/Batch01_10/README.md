# Batch01_10 — Ten-site fixed-biogeography / no-competition CLM-FATES

**Maintained Batch example | 24 October 2026**

This example prepares ten forest-tower experiments with observed/literature-informed tree PFT composition and representative mineral soil texture. It uses the **successful DE-Tha Stage12 private FATES AD namelist-overlay recovery method**, adapted to a ten-case batch, rather than the earlier unpatched direct CIME staging code.

**Status and scope**

- **10/10 new, versioned FIXNC surface NetCDFs: CREATED successfully on IRIDIS6**, as confirmed by `SURFACES SUMMARY success=10 issues=0`.
- **Ten-site FATES AD configuration problem: operator reports RESOLVED** using the recovered private-overlay workflow. The exact ten-case success log and Slurm accounting are not archived in this README; do not infer ten completed AD5 jobs from that statement.
- **AD5 model/archive completion: NOT independently verified here.** First segment is 5 years at each site. AD395 continuation and Normal400 must be treated as separate, restart-dependent steps.
- No shared CTSM source modification is permitted. Do not delete or recreate existing model cases, restart files, original surfaces, historical forcing or private recovery ledgers merely to tidy up this repository.

## Current, retained example code

| File | Purpose | Status |
| --- | --- | --- |
| [`11_batch10_AD400_oneclick.py`](scripts/11_batch10_AD400_oneclick.py) | `self-test`, `plan`, ten versioned `surfaces`, validated `submit-smoke`, `status` | **RETAINED**. Its original direct `stage` implementation was removed; no direct-staging action remains. |
| [`12_batch10_recover_FATES_AD_private_overlay.py`](scripts/12_batch10_recover_FATES_AD_private_overlay.py) | Create one private CTSM build-namelist overlay, recover ten existing isolated cases, validate generated AD namelists, restore CIME XML lock; no Slurm submission | **RETAINED — successful recovery method**, based on the proven DE-Tha Stage12 |
| [`01`–`08` historical scripts](scripts/) | Read-only source inventory, PFT/soil and CIME input provenance, including successful CZ-BK1/RU-Fyo soil preflight | **RETAINED** as independent historical evidence/diagnostics, not required before each new submission |

**Do not rerun `surfaces`, `recover`, or `submit-smoke` if the original action succeeded.** Private overlay recovery and job submission are stateful; consult the existing per-site receipts, attempt ledgers, jobs and restarts. For a non-writing summary:

```bash
cd ~/Non-Competition-CLM-experiment || exit 1
python3 -B examples/Batch01_10/scripts/11_batch10_AD400_oneclick.py status
```

`status` reports the case and controller/Slurm state, **not** authoritative confirmation that an AD5 model/archive pair completed with a valid CLM/DATM/CPL restart. Completion requires exact Slurm and restart evidence.

### Successful workflow design (not instructions to repeat completed steps)

1. `Stage11 surfaces` builds **ten isolated forest-point surfaces**, each with its own SHA256 receipt, and leaves the original point NetCDF untouched.
2. `Stage12 recover` uses one independent **private CTSM namelist overlay** based on [DE-Tha Stage12](../DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py). The source is pinned and only two narrow modifications are allowed: accept `use_cn OR use_fates` for `spinup_state=2`, and gate CN-specific `reseed_dead_plants` under `use_cn`. It temporarily directs each *new* CIME case to this overlay; generates FATES AD namelists; restores the locked `env_case.xml`; and marks valid cases `PREPARED_NOT_SUBMITTED`.
3. `Stage11 submit-smoke` accepts only recovery receipts with restored CIME XML locks. It uses `case.submit --skip-preview-namelist` to preserve the verified `spinup_state=2` namelist and submits **only one 5-year run per station**, `RESUBMIT=0`. Submission is guarded against duplicates.
4. After confirmed **run and st_archive success plus CLM/DATM/CPL restarts**, continue the remaining 395 AD years separately. A distinct Normal400 case should start from the verified final AD restart, initially as a 5-year transition smoke. No continuation is automatic here.

**AD run configuration:** fixed biogeography, no competition, `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `CLM_ACCELERATED_SPINUP=on`, generated `spinup_state=2`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`. CIME `CLM_BLDNML_OPTS` follows the proven DE-Tha `--bgc fates --no-megan --no-drydep --no-fire_emis` option set. The original site-specific DATM stream, CO₂ policy and built executable are inherited; forcing NetCDF files are not reprocessed in this example.

## Failed / retired code — documented only, files removed

These paths describe **historical unsuccessful or superseded attempts and must not be used**. Their file contents were removed from the current branch; history is still available through older Git commits if forensic reconstruction is needed.

| Old code or action | What happened | Current replacement |
| --- | --- | --- |
| `scripts/10_CZ_BK1_candidate_surface_gate.py` **FAILED** | Single-site Stage10 `audit` incorrectly assumed a particular DATM stream XML file-list structure and raised `Expected 22 unique annual forcing files in XML`. This was a parsing assumption, **not** missing forcing data. | Ten-site Stage11 `surfaces`; no redundant 22-year re-audit |
| `scripts/09_CZ_BK1_AD5_input_gate_readonly.py` **RETIRED** | The single-station Stage09 read-only audit completed, but became unnecessary once the user selected a ten-site simultaneous experiment. **Not itself a failed scientific analysis.** | Existing Batch01 site provenance / Stage11 ten-site workflow |
| Original Stage11 `stage` action **FAILED; IMPLEMENTATION REMOVED** | Old pinned `CLMBuildNamelist.pm` checks `use_cn` only for accelerated `spinup_state=2`; FATES uses `use_cn=.false.`. The hardcoded error misleadingly calls this Satellite Phenology, even when `--bgc fates` was configured. | Stage12 private namelist overlay recovery |
| Original Stage11 `plan` CSV read **FAILED; FIXED** | Misspelled Python codec `utf8-sig`, causing `LookupError`. Corrected to `utf-8-sig`; later `self-test` and ten-site `plan` both passed. | Retained corrected Stage11 `self-test` and `plan` |
| Intermediate `-bgc fates` / `--bgc fates`-only attempts **FAILED** | CLI option changes alone did not fix the pinned *Perl FATES spinup guard*. The DE-Tha Stage12 private patch was the actual missing step. | Stage12 private overlay, validated FATES AD namelist |

**Root cause / provenance:** The pinned source Git blob `698f2396aba8e11cbbbdd58c74ad221e6b7e7038` (`CLMBuildNamelist.pm`) had a CN-only accelerated-spinup branch. The already successful [DE-Tha technical example](../DE-Tha/README.md) documents this and the private-overlay recovery that preserved shared CTSM and generated `spinup_state=2`. This batch deliberately reuses that solution.

## Ten-site PFT composition selected for FIXNC

All new points use the **idealized site-stand experiment** `PCT_NATVEG=100%`, `PCT_CROP=0%`, and other top landunits 0. These are experimental point-scale assumptions, **not** measured whole-flux-footprint landcover percentages. Source-grid PFT fractions are not used as observed station composition.

| Station | ENF % | DNF % | DBF % | EBF % |
| --- | ---: | ---: | ---: | ---: |
| CZ-BK1 | 100 | 0 | 0 | 0 |
| IT-Ren | 97 | 3 | 0 | 0 |
| RU-Fyo | 85 | 0 | 15 | 0 |
| CH-Dav | 100 | 0 | 0 | 0 |
| IT-Col | 0 | 0 | 100 | 0 |
| FR-Fon | 2 | 0 | 98 | 0 |
| FI-Sod | 100 | 0 | 0 | 0 |
| FR-Pue | 0 | 0 | 5 | 95 |
| DE-Hai | 0 | 0 | 100 | 0 |
| BE-Vie | 64 | 0 | 36 | 0 |

Binding source of model fractions: [PFT scenarios CSV](../../data/batch01_10_pft_scenarios.csv); [site register](../../data/batch01_10_sites.csv); [seven-site PFT residual review](docs/seven_site_PFT_residual_followup_2026-10-24.md), [four-site tree evidence](docs/four_site_forest_inventory_search_2026-10-24.md).

## Soil texture: chosen representative surface horizon or station aggregate

For stations with a sampled mineral upper horizon, use the nearest representative surface observation (e.g. 0–10 cm). Otherwise use the selected published station-level composition. Except RU-Fyo, **one selected Sand/Silt/Clay composition is normalized to fine-earth 100% and replicated as a modelling proxy across the ten CLM texture-input layers**. This is a vertical extrapolation, *not* ten observed depth profiles.

| Station | Selected original Sand / Silt / Clay (%) | Basis |
| --- | --- | --- |
| CZ-BK1 | 22 / 58 / 21 | Flechard2020 Table S4; reported sum **101**; proportional normalization |
| IT-Ren | 55 / 34 / 11 | Flechard2020 Table S4; station aggregate |
| RU-Fyo | original surface 10-layer Sand/Clay | Explicit original-soil-only exception; **peat physics remains an uncertainty** |
| CH-Dav | 53 / 25 / 22 | Meredith2018, 0–10 cm mineral topsoil |
| IT-Col | 8 / 32 / 59 | Flechard2020, reported sum **99**; alternative literature conflicts |
| FR-Fon | 41.9 / 38.8 / 19.3 | Same-tower upper mineral soil |
| FI-Sod | 88.12 / 6.0 / 0.5 | 0–10 cm, with stones excluded from fine-earth normalization |
| FR-Pue | 26 / 32 / 42 | Meredith2018, 0–10 cm; stoniness caveat |
| DE-Hai | 4 / 49 / 48 | Meredith2018, 0–10 cm; sum **101** |
| BE-Vie | 27 / 55 / 18 | Site summary |

References/data: [selected Batch01 soil texture policy](../../data/batch01_10_soil_selected_batchAD.csv), [operator's binding soil decision register](../../data/batch01_10_soil_input_decisions.csv), [Flechard2020 supplement transcription](../../data/batch01_10_Flechard2020_TableS4_soil.csv), [Flechard 2020 literature note and publisher PDFs](references/Flechard_2020_Biogeosciences_Part1.md), [site-soil literature review](docs/nine_site_soil_texture_literature_2026-10-24.md), [original measured horizon register](../../data/batch01_10_soil_site_observations.csv). Unchanged source surface soil/terrain fields not explicitly replaced are inherited as technical schema/physics, **not validated field measurements**.

## Scientific limits, preservation and provenance

- **RU-Fyo** is a peat site. Reusing its original mineral `PCT_SAND`/`PCT_CLAY` layering is an explicitly approved pragmatic fallback, not proof that the model captures peat carbon, organic layers or water table physics.
- **FR-Pue** has notable coarse fragments; **IT-Col** has conflicting published textures; **CZ-BK1** soil sample-depth allocation is unknown. Site texture choice does not close those model-physics uncertainties.
- The site-level forcing loop reuses each tower's already existing DATM streams; no replacement or further per-year checking is performed by this workflow.
- Preserve source files, existing experimental cases, Slurm ledgers, restart NetCDF and recovery receipts. Removal of legacy **GitHub scripts** must not be interpreted as permission to delete historical HPC files.
- The old source/soil preflight history remains in the kept `scripts/01`–`08` and the [Stage05/06 evidence record](docs/stage05_06_status_and_AD_gate_2026-10-24.md). Those are historical checkpoints, **not today's AD readiness decision**.
- This example demonstrates a technical mode and site-input workflow. Scientific convergence and historical model-vs-EC validation require independent diagnostics.
