# DE-Tha — ICOS observed-forest PFT | fixed biogeography + no competition

**Selected scientific experiment:** ONE tower-forest PFT scenario **ENF 87%, DNF 10%, DBF 3%**. No original-grid/cropland/PFT-mix experiments are part of the active DE-Tha experiment. This is an *observationally informed single-point forest proxy*, **not** a measured grid-wide area map.

**Status (24 October 2026):** PFT-only v1 SHA256 verified; final forest + published measured-soil **v2 generated and independently verified** (`0d3d827cc4bbfab277d629fafc33ee26933404a84b56ba1bfcac8b3e6cd5e60a`). **New plan: direct AD400 from cold startup 1996; NO PRE50, NO AD200 or POST300 at this stage.** Stage10 `inspect` passed and new case created. Stage12 **private-overlay repair PASSED on IRIDIS6**: `preview_namelists`/`check_input_data` RC0, real generated `spinup_state=2`, FIXNC, correct FATES GPP/NPP, case XML lock restored; **Stage10 independent `validate` PASSED**. The first 5-year AD smoke is now eligible for one-time submission; **no DE-Tha Slurm job was submitted in these audit/repair steps**. Existing forcing v5 status is still `REVIEW`: the operator explicitly elects to use the unchanged existing forcing for this experiment; 11 LW + 3 VPD manual concerns remain scientifically unresolved.

## 1. Observed PFT targets (single scenario)

The [ICOS Tharandt station record](https://meta.icos-cp.eu/resources/stations/ES_DE-Tha) reports **87% evergreen conifers**, made of 72% *Picea abies* and 15% *Pinus sylvestris*, and **13% deciduous species**, composed of 10% *Larix decidua*, 1% *Betula* and 2% unspecified other trees. See also [ICOS Germany's flux-footprint description](https://www.icos-infrastruktur.de/en/icos-d/components/ecosystem/study-sites/tharandt-c1).

| Recorded species / taxon | Reported % | Requested modeling PFT | Proxy mapping note |
| --- | ---: | --- | --- |
| *Picea abies* | 72 | ENF | Direct functional group |
| *Pinus sylvestris* | 15 | ENF | Direct functional group |
| *Larix decidua* | 10 | DNF | Cold-deciduous needleleaf |
| *Betula* sp. | 1 | DBF | Direct functional group |
| Unspecified 2% within deciduous class | 2 | **DBF (assumed)** | Species identity unavailable; explicit proxy assumption |
| **Total** | **100** | **ENF 87 / DNF 10 / DBF 3** | Tower-forest proxy |

The unresolved 2% is **not** asserted to be measured DBF. Likewise, assuming that forest species composition describes 100% of the new single-point natural vegetation area is a **scientific representation choice**, not a claim that a spatial map was observed. This fixed composition is held constant in the *spin-up*, despite documented stand management; a historical analysis must review changing composition over time.

## 2. Exactly one new forest surface

The output **must be a new file**. Preserve the original legacy NetCDF to provide coordinates, soil texture, topography and other compatible surface metadata, but **do not carry its old PFT or cropland percentages into the new forest model scenario**.

| Surface field | Single selected DE-Tha forest-proxy value |
| --- | --- |
| `PCT_NATVEG` | 100% |
| `PCT_CROP` | 0% |
| `PCT_NAT_PFT[1]` — ENF | 87% |
| `PCT_NAT_PFT[3]` — DNF | 10% |
| `PCT_NAT_PFT[7]` — DBF | 3% |
| All other `PCT_NAT_PFT` indices | 0% |
| Lake / wetland / glacier / urban landunits | 0% (as already verified) |

**Never overwrite** `surfdata_DE-Tha_hist_2000_16pfts_c261011.nc`; its exact SHA256 is `7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d`. Exact FATES parameter JSON SHA256: `0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04`. Map checked: CLM natpft 1/3/7 correspond to three distinct FATES ENF/DNF/DBF tree types for this pinned model. CTSM source `d5ea9d0136530370a62ef267ccfaff6f001ef914`.

### Read-only new-surface audit

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -B examples/DE-Tha/scripts/05_build_forest_observed_surface.py audit
```

### Generate the ONE isolated forest-proxy surface (explicit acknowledgements required)

```bash
python3 -B examples/DE-Tha/scripts/05_build_forest_observed_surface.py write \
  --ack-2pct ACCEPT_UNIDENTIFIED_DECIDUOUS_2PCT_AS_DBF_PROXY \
  --ack-forest ACCEPT_TOWER_FOREST_PROXY_NATVEG100_CROP0
```

The isolated surface was **already generated once and verified on IRIDIS6**, so **do not rerun `write`**. For any further checking, use the read-only verification instead:

```bash
python3 -B examples/DE-Tha/scripts/05_build_forest_observed_surface.py verify
```

If successful the one-time write creates a *new* surface (never overwrites an existing one):

```text
/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/DE-Tha/surface/
  surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.nc
  surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.json
```

The user-observed generation created SHA256 `6d415b420ece0f18dca051c91849dcd5a3a5748779f9ee349c98e84e52e80600` and read-only verification passed. The JSON receipt stores both NetCDF SHA256 values, fixed percentages and assumptions. This operation creates **no case or Slurm jobs**. A subsequent script must verify output hashes before binding the new `fsurdat`.

## 3. Measured soil texture and verified v2 surface

The `PCT_SAND` and `PCT_CLAY` arrays of the original grid-based surface are inherited *unchanged* by the new observed-forest FIXNC NetCDF. We must compare these inherited **model soil-texture assumptions** to the published field measurements at DE-Tha rather than assuming they represent tower mineral soil.

A Tharandt tower-forest study reports for the **first mineral soil layer** **17% sand, 71% silt, 12% clay**, described as approximately stable through 1.2 m. Source: [Net Ecosystem Exchange and Net Biome Productivity of different land use in eastern Germany](https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany). These are **site-reference measurements**, not layer-by-layer measurements of every model depth, and are *not* soil-water/stone fractions.

Independent measurements in other (non-tower) 2024 plots of the Tharandt Forest found much wider ranges: sand 5.4–64.8 mass-%, silt 25.1–73.9 mass-%, clay 10.1–21.0 mass-%. [Virano-Riquelme et al. 2024](https://onlinelibrary.wiley.com/doi/10.1002/jpln.202400073). These nearby values demonstrate heterogeneity and **must not be treated as field measurements at the DE-Tha tower**. See the [source evidence file](data/observed_soil_texture_references.csv).

The [06_audit_soil_texture_vs_observations.py](scripts/06_audit_soil_texture_vs_observations.py) does **strictly READ-ONLY** comparison: verifies the original and derived surface SHA256 hashes, confirms every inherited soil variable stayed identical, lists PCT_SAND / PCT_CLAY and derived silt `100 − sand − clay` by model layer, computes percentage-point differences from 17/71/12, and reports whether model depth coordinates actually exist. It never changes the validated forest PFT NetCDF.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -m py_compile examples/DE-Tha/scripts/06_audit_soil_texture_vs_observations.py
python3 -B examples/DE-Tha/scripts/06_audit_soil_texture_vs_observations.py \
  2>&1 | tee ~/DE-Tha_soil_texture_reference_vs_surface.log
```

**Read-only result received from IRIDIS6 (24 October 2026):** original and derived soil fields are **identical**, but original NetCDF layers 1–4 have **Sand 24 / Silt 51 / Clay 25%**, versus tower reference **17 / 71 / 12%**, a difference of **+7 / −20 / +13 percentage points**. Model clay increases to 31–36% in later layers, but the corresponding depths are **unknown in the current surface output**. Result: **substantial texture difference**; the historical site measurement is a comparison reference, not a spatially complete soil map. The primary source directly supports 17/71/12 at the forest station: Prescher et al. (2010), *Agricultural and Forest Meteorology* 150, 1016–1025, DOI [10.1016/j.agrformet.2010.03.008](https://doi.org/10.1016/j.agrformet.2010.03.008). **No NetCDF was edited.**

The observed values are in **mass percentages of fine mineral particles**, not stone volume fraction. Their mismatch has led to a specific user decision: **DE-Tha will use site-measured soil texture rather than grid-derived sand/clay for the new FIXNC run**. The [project-wide policy](../../docs/observed_soil_texture_policy.md) applies the same principle to all future sites when reliable site measurements exist (otherwise explicitly retain the grid estimate).

### Selected v2 input — PFTs unchanged, measured soil proxy

Use [07_build_site_soil_surface_v2.py](scripts/07_build_site_soil_surface_v2.py) to produce a **new immutable v2**, starting from the SHA256-pinned verified v1. This modifies **only `PCT_SAND` and `PCT_CLAY` across all 10 input texture layers**; other variables including `PCT_NAT_PFT` remain bit-for-bit equal to v1.

| Surface field | Selected DE-Tha value |
| --- | --- |
| `PCT_NATVEG` / `PCT_CROP` | 100% / 0% |
| ENF / DNF / DBF | 87% / 10% / 3% |
| `PCT_SAND` for 10 input layers | 17% |
| `PCT_CLAY` for 10 input layers | 12% |
| Silt (derived, not separate `PCT_SILT` write) | 71% |

**Crucial depth limitation:** Prescher et al. (2010) measured **first mineral horizon** and described stable texture down to about **1.2 m**; filling all ten CLM surface texture inputs with a single 17/71/12 profile is an explicitly documented **extrapolated soil proxy**, *not* ten independent measurements. Actual CIME `soil_layerstruct` and model-layer depths still require audit before scientific interpretation. Nearby plots show spatial variability. No other soil fields, e.g., organic carbon or gravel content, become measured by this change.

Run **preflight first**:

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -m py_compile examples/DE-Tha/scripts/07_build_site_soil_surface_v2.py
python3 -B examples/DE-Tha/scripts/07_build_site_soil_surface_v2.py audit
```

After successful audit, create **exactly one** new v2 file with a scientific acknowledgement of the depth extrapolation:

```bash
python3 -B examples/DE-Tha/scripts/07_build_site_soil_surface_v2.py write \
  --ack-uniform-10-layer-soil-proxy ACCEPT_DE_THA_PUBLISHED_SOIL_TEXTURE_17SAND_71SILT_12CLAY_ALL10_AS_PROXY
```

Then **do not rerun write**. Verify NetCDF and its JSON receipt read-only:

```bash
python3 -B examples/DE-Tha/scripts/07_build_site_soil_surface_v2.py verify
```

The new direct AD400 case must reference the verified `surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_SoilField17_71_12_v2.nc`, NOT the older v1 or the original grid soil.

### Stage 08: interpret existing forcing QC before PRE50 submission

The site forcing receipt has `status=REVIEW`. A [strictly read-only 08 audit](scripts/08_audit_forcing_v5_review.py) prints **all 14 manual-review rows**, **all 32 replacement events**, the seven-variable QC summaries and a 525,600-record continuous NO_LEAP / gross-physical-range check. No forcing files are changed and `REVIEW` is never automatically promoted to PASS.

```bash
python3 -B examples/DE-Tha/scripts/08_audit_forcing_v5_review.py \
  2>&1 | tee ~/DE-Tha_forcing_v5_manual_QC_review.log
```



## 4. Selected run design — DIRECT AD400 only (no PRE50)

**Explicit operator change (24 October 2026):** Do not run a 50-year normal stage first. Perform **400 model years in accelerated decomposition mode** with independent **cold start** from 1996-01-01, `RUN_TYPE=startup`, `CLM_FORCE_COLDSTART=on`, `CLM_ACCELERATED_SPINUP=on` and explicitly verified `spinup_state=2`. The old NL-Loo hybrid AD200 procedure is **NOT** directly reusable here because it has a PRE50 restart and requires private namelist fixes. This direct-cold-start case requires its *own* smoke test.

| Case | First model year | Final target | Duration | Segment rule |
| --- | ---: | ---: | ---: | --- |
| `DE-Tha_OBSPFT_NC_V1_AD400` | 1996 | 2396 | **400 AD years** | 80 × 5y: 1 smoke, then 79 after scientific+technical gate |

No PRE50 or POST phase is created; separate decisions about post-AD normal relaxation and scientific convergence are deferred until the AD400 checkpoint is achieved and checked. AD pool turnover acceleration is *not* proof of soil-carbon equilibrium.

**Model science inputs:** `fsurdat` = the SHA256-pinned `...SoilField17_71_12_v2.nc`, `PCT_NATVEG=100`, ENF87/DNF10/DBF3 and ten input texture layers with sand17/clay12. Site forcing loops over the existing 1996–2025 NO_LEAP 30-year, half-hour DATM stream files. The existing `DE-Tha_FATES_SPINUP500` provides the CIME/machine/forcing baseline and built executable *only*; its original normal-FATES case is never overwritten or submitted. No NL-Loo jobs/cases are touched.

### Stage10 — Inspect and stage independent AD400 cold-start case

[10_DE_Tha_direct_AD400.py](scripts/10_DE_Tha_direct_AD400.py) enforces sha256 of the v2 surface, FATES parameters, preprocessed forcing CSV, source CTSM revision and built legacy executable; reads the original DE-Tha site DATM streams. It clones using `create_clone --keepexe` and sets a **unique case/run/archive**. It forces the correct FIXNC mode and **explicit `spinup_state=2`** in `user_nl_clm`, regenerates namelists and refuses staging if actual generated `CaseDocs/lnd_in` or RUNDIR `lnd_in` lack the requested mode. `hist_fincl1` uses `FATES_GPP,FATES_NPP`, NOT original `GPP,NPP`. It does not patch shared CTSM or change any existing cases.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -m py_compile examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py
python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py inspect
```

Only if `inspect` passes, clone and stage without submitting:

```bash
python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py stage \
  --confirm STAGE_DE_THA_DIRECT_AD400_COLDSTART_REVIEWED_FORCING
```

If the pinned CIME build-namelist cannot produce `spinup_state=2` for **FATES cold-start**, `preview_namelists` or `validate` stops. **Do not bypass it or manually edit shared CTSM.** Submit nothing until the case validates.

```bash
python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py validate
```

### Stage12 — Recover the encountered FATES accelerated cold-start namelist error

**Real IRIDIS6 incident, 24 October 2026:** Stage10 `inspect` verified the v2 surface, FATES parameters, 1996–2025 forcing, compiled legacy executable and original DATM streams. `stage` **created** a new independent `DE-Tha_OBSPFT_NC_V1_AD400` case; `case.setup` succeeded, but `./preview_namelists` failed **BEFORE any Slurm submission**:

```text
spinup_state is accelerated (=1 or 2) which is for a BGC mode of CN or BGC,
but the BGC mode is Satellite Phenology
```

The exact pinned upstream `CLMBuildNamelist.pm` (Git blob `698f2396aba8e11cbbbdd58c74ad221e6b7e7038`) **incorrectly checks only `use_cn`**, rather than `use_cn OR use_fates`, before supporting AD state. This reproduces the underlying NL-Loo AD namelist error. The *wording* about Satellite Phenology is hardcoded in the source's `else` branch and **does not prove** the CIME `-bgc` flag was actually `sp`; Stage12 also audits `CLM_BLDNML_OPTS` and accepts **either `--bgc fates` (the format actually observed on IRIDIS6) or `-bgc fates`**, rejecting `--bgc sp`.

**Follow-up audit incident (24 October 2026):** an early Stage12 read-only run stopped at `CLM_BLDNML_OPTS='--bgc fates --no-megan --no-drydep --no-fire_emis'` because its regex erroneously allowed only one leading hyphen. This was an **audit false negative**: `--bgc fates` is the expected FATES option. The GitHub script was corrected in commit `e043011` to accept both option spellings, while preserving all other fail-closed checks. That interrupted `audit` made **no changes**, and `repair` has **not** been attempted; a fresh read-only `audit` is safe.

**Do NOT rerun Stage10 `stage` or delete/re-clone the CIME case.**

The guarded [12_DE_Tha_AD400_recover_failed_preview.py](scripts/12_DE_Tha_AD400_recover_failed_preview.py) performs a strictly read-only `audit`, then (only with exact user confirmation) creates a private build-namelist overlay with the two previously verified NL-Loo patches:

1. Allow FATES **or** CN to use `spinup_state=2` in `setup_cmdl_spinup`.
2. Keep `reseed_dead_plants` CN-only; do not add that CN namelist to FATES.

It checks source Git blob, CIME `--bgc fates` or `-bgc fates`, no previous Slurm jobs or attempted `case.submit`, `RESUBMIT=0`, locked `env_case.xml`, correct original executable and pinned site inputs. During recovery it temporarily sets ONLY the independent case's `COMP_ROOT_DIR_LND` to the private overlay, regenerates `CaseDocs/lnd_in` and `RUN/lnd_in`, verifies real FATES `spinup_state=2` and the history fields, then **restores the literal `$SRCROOT` locked case XML**. Only after both generated namelists and CIME locks validate does it create the initial submission state ledger. **No Slurm job is submitted by Stage12.**

```bash
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -m py_compile examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py
python3 -B examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py audit \
  2>&1 | tee ~/DE-Tha_AD400_12_readonly_audit.log
```

**ONLY IF** audit prints `AUDIT PASSED`:

```bash
python3 -B examples/DE-Tha/scripts/12_DE_Tha_AD400_recover_failed_preview.py repair \
  --confirm RECOVER_DE_THA_AD400_FATES_PRIVATE_NAMELIST_NO_SLURM \
  2>&1 | tee ~/DE-Tha_AD400_12_repair.log

python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py validate
```

If audit fails, **stop** and share output. If repair fails partway through, **do not rerun it**: it leaves a non-repeatable attempt ledger and preserves case/overlay for manual diagnosis. Once Stage10 validates, its one-time `submit-smoke` still preserves corrected `spinup_state=2` with `--skip-preview-namelist`.

**Verified Stage12 recovery result (24 October 2026):** audit passed, private overlay repaired the CLMBuildNamelist FATES guard, `./preview_namelists` and `./check_input_data` returned 0, generated `CaseDocs/lnd_in` and `RUN/lnd_in` include `spinup_state=2` and FIXNC, no CN-only reseed, real `env_case.xml` was restored exactly, and an independent Stage10 `validate` passed. Therefore, **do not rerun Stage12 repair or Stage10 stage**. The next operator action is **exactly one** Stage10 `submit-smoke` (5 years, `RESUBMIT=0`), not Stage11 `continue-395`.

### Stage10 — Submit only initial 1996–2001 AD smoke (5 model years)

**This is the first five years of the planned 400**, not a throwaway. `RESUBMIT=0`, and no watcher is enabled. `--skip-preview-namelist` is used to preserve the verified `spinup_state=2` namelist, applying the NL-Loo incident lesson.

```bash
python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py submit-smoke \
  --confirm SUBMIT_DE_THA_AD400_FIRST_FIVE_YEARS_ONLY
```

Submission is one-time and logged at `~/DE_Tha_AD400_controller/submission_state.json`; do not re-run it after uncertain output. Monitor:

```bash
python3 -B examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py status
squeue -u "$USER" -o "%.12i %.60j %.10T %R"
```

### Stage11 — continue the remaining 395 years, only if smoke is proven

[11_DE_Tha_AD400_continue_after_smoke.py](scripts/11_DE_Tha_AD400_continue_after_smoke.py) checks the exact original model/archive Slurm job IDs and their `COMPLETED/0:0` results, `CaseStatus`, archived **2001-01-01** CLM/DATM/CPL restart files, `spinup_state=2`, saved CIME `skip_pnl=True`, generated land namelist hashes, and all current `rpointer` targets. If any prerequisite fails, 395y submission is prohibited. Then it backs up and stages only the verified 2001 component checkpoints in the new case RUNDIR. `CONTINUE_RUN=TRUE` and `RESUBMIT=78` give **2001→2006 + 78×5 years = 395 years**, ending 2396 if all jobs complete.

**Run ONLY AFTER archived five-year success**, with no queued jobs:

```bash
python3 -B examples/DE-Tha/scripts/11_DE_Tha_AD400_continue_after_smoke.py audit
```

After the script reports `AUDIT PASSED`:

```bash
python3 -B examples/DE-Tha/scripts/11_DE_Tha_AD400_continue_after_smoke.py continue-395 \
  --confirm CONTINUE_VERIFIED_DE_THA_AD400_FROM_2001_TO_2396
```

Never repeat the continuation command if submission is uncertain or a handoff folder already exists. There is **no automatic** continuation after first 5y until explicitly requested.

## 5. AD400 progress verification and independent AD → Normal experiment

**Current operator report:** Slurm `squeue -u ly3n24` displayed `4713482 run.NL-L...` in state **R**, and `4713483 st_archive...` state **PD (Dependency)**. These jobs belong to **NL-Loo**, not DE-Tha, and do **not** prove DE-Tha AD completion. A missing DE-Tha row from `squeue` is not evidence of success: use exact `sacct` IDs, CIME `CaseStatus`, the archive and restart contents.

Run the strict **read-only** [13_check_AD5_jobs_and_restart.py](scripts/13_check_AD5_jobs_and_restart.py):

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -B examples/DE-Tha/scripts/13_check_AD5_jobs_and_restart.py \
  2>&1 | tee ~/DE-Tha_AD400_first5_verified_status.log
```

This explicitly distinguishes full `run.DE-Tha_OBSPFT_NC_V1_AD400` and `st_archive.DE-Tha_OBSPFT_NC_V1_AD400` from `run.NL-Loo_...`. It prints the Stage10 controller state and, **only after both exact Slurm jobs finish `COMPLETED/0:0`**, checks three components of the `2001-01-01-00000` archive restart and the land `spinup_state=2`. Expected result for a genuinely completed AD smoke: **`STATUS: VERIFIED_AD5_ARCHIVED`**. Otherwise **do not submit** an AD continuation or Normal branch.

### Separate Normal conversion pilot — source 2001 AD5 (technical feasibility only)

The experiment is **independent of AD400**:

| Case name | AD reference state | Normal target | Design |
| --- | --- | --- | --- |
| `DE-Tha_OBSPFT_NC_AD5_TO_NORMAL5_TEST` | archived AD restart at 2001-01-01 | 2006-01-01 | 5-year Normal hybrid feasibility test |
| `DE-Tha_OBSPFT_NC_AD400_TO_NORMAL5_TEST` | final AD400 restart at 2396-01-01 | 2401-01-01 | 5-year Normal *post-AD400* pilot, only after full AD400 success |

The two cases are **not currently created or submitted**. The first asks *can this CIME/FATES build switch from an AD-state restart to a normal-state hybrid and complete five years?* It is **not** a soil equilibrium test. The second is relevant after completion of all 400 AD years, to assess initial post-AD carbon-pool relaxation; longer Normal time series will likely be necessary.

Use [14_AD_to_Normal_independent_branch.py](scripts/14_AD_to_Normal_independent_branch.py). It clones the original DE-Tha FATES case with `--keepexe`, sets **hybrid** start, references the **separate AD archive** using `RUN_REFCASE`, `RUN_REFDATE`, `finidat` and copies all three restart components into a separate run directory with locally verified pointers. It preserves the approved forest/soil v2 and FATES FIXNC flags. In generated normal `lnd_in`, `CLM_ACCELERATED_SPINUP=off` and `spinup_state` is **0 or omitted**; the exact pinned build rejects an explicitly provided FATES `spinup_state=0` when `use_cn=.false.`, so **do not hard-code that value**. The transition is verified scientifically/technically by the resulting normal restart's `spinup_state=0`, Slurm success and CIME logs.

**Only after Stage13 prints `VERIFIED_AD5_ARCHIVED`**, run strict read-only branch preflight:

```bash
python3 -B examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py \
  audit --source-year 2001 \
  2>&1 | tee ~/DE-Tha_AD5_to_Normal5_readonly_audit.log
```

Only if it prints `PASS: NORMAL branch source and isolation gates`, create a **separate case without submitting any jobs**:

```bash
python3 -B examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py \
  stage --source-year 2001 \
  --confirm CREATE_ISOLATED_DE_THA_AD_TO_NORMAL_5Y_TEST \
  2>&1 | tee ~/DE-Tha_AD5_to_Normal5_stage.log
```

If staging passes, run an **independent validation**:

```bash
python3 -B examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py \
  validate --source-year 2001
```

Only after that validation, you may opt to **submit ONE 5-year Normal** test (no resubmits). This is an explicit action separate from staging:

```bash
python3 -B examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py \
  submit-smoke --source-year 2001 \
  --confirm SUBMIT_ISOLATED_DE_THA_NORMAL_5Y_ONLY
```

When both independent Normal run and archive complete, execute:

```bash
python3 -B examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py \
  verify-run --source-year 2001
```

For the final **AD400→Normal** branch, the same commands use `--source-year 2396`, but **only after** all 80 AD 5-year segments complete, the 2396 CLM/DATM/CPL archive exists and `spinup_state=2`. The full normal simulation, if any, should be planned only after both pilot tests demonstrate model compatibility.

**Safety:** Neither script edits or submits NL-Loo or the existing DE-Tha AD400 source case; do not interpret NL-Loo queue states as DE-Tha progress. The source AD case may separately continue for 395 years after its own Stage11 gate.

## 6. Forcing QC disposition

A previous read-only audit, [08_audit_forcing_v5_review.py](scripts/08_audit_forcing_v5_review.py), found complete 1996–2025 30-min NO_LEAP continuity and no **gross** physical-range violations, but **status remains REVIEW** due to 14 manual-review items (11 low daytime LW in 2005; 3 VPD reconstructions) and 32 replacement events. [09_audit_critical_meteorological_episodes.py](scripts/09_audit_critical_meteorological_episodes.py) provides optional read-only physics-aware episodic checks.

**Operator decision for this AD400 pilot:** accept the existing `processed_v5` forcing and already linked `datm_v5_candidate_timevarying_zbot` files unchanged; **do not repair those 14/32 events now**. This is an operational acceptance for an exploratory spin-up, **not** a scientific certification of the 2005 LW or 2017/2022 VPD. The risks belong in the experiment's methods and limitations. A later historical validation should revisit them.

### Safety scope

- NO edits to old DE-Tha, NL-Loo, CTSM shared source or binaries.
- NO automatic `RESUBMIT` before first AD smoke archive is independently verified.
- A missing `spinup_state=2`, `FATES_GPP/FATES_NPP`, restart mismatch or CIME option check fails closed.
- The AD400 workflow creates NO Normal stage; the separately requested Stage14 experiment may create its own isolated AD→Normal branch only after a verified AD archive.
- Do not confuse accelerated carbon pool spin-up with normal climate–soil equilibrium.

## Folder index

```text
examples/DE-Tha/
  README.md
  data/observed_tree_composition.csv
  data/observed_soil_texture_references.csv
  config/experiment_manifest.json
  scripts/
    01_audit_evidence.py
    02_inventory_iridis_inputs.py
    03_audit_live_inputs.py
    04_review_landunit_scenarios.py
    05_build_forest_observed_surface.py    # selected single forest scenario
    06_audit_soil_texture_vs_observations.py  # READ ONLY soil texture consistency
    07_build_site_soil_surface_v2.py        # selected forest + in-situ-soil v2
    08_audit_forcing_v5_review.py           # READ ONLY 14+32 forcing QC review
    09_audit_critical_meteorological_episodes.py # optional READ ONLY QC episodes
    10_DE_Tha_direct_AD400.py              # direct AD400 cold start, first 5y smoke
    11_DE_Tha_AD400_continue_after_smoke.py # guarded 395y only after 2001 archive
    12_DE_Tha_AD400_recover_failed_preview.py # private FATES AD CIME namelist recovery
    13_check_AD5_jobs_and_restart.py       # READ ONLY DE-Tha exact Slurm/restart audit
    14_AD_to_Normal_independent_branch.py   # separate AD5/AD400 to NORMAL5 hybrid
```
