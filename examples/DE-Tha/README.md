# DE-Tha — ICOS observed-forest PFT | fixed biogeography + no competition

**Selected scientific experiment:** ONE tower-forest PFT scenario **ENF 87%, DNF 10%, DBF 3%**. No original-grid/cropland/PFT-mix experiments are part of the active DE-Tha experiment. This is an *observationally informed single-point forest proxy*, **not** a measured grid-wide area map.

**Status (24 October 2026):** PFT-only **v1 generated and SHA256 verified** (`6d415b420ece0f18dca051c91849dcd5a3a5748779f9ee349c98e84e52e80600`); **v2 with published site-specific soil texture is the selected next model input**, with GitHub builder script 07 available but **not yet executed on IRIDIS6**. No DE-Tha FIXNC CIME case or Slurm job submitted. Forcing v5 QC status is `REVIEW` (14 manual events, 32 replacements; triage script 08 ready).

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

## 3. Soil texture consistency — READ ONLY preflight (before running PRE50)

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

The new PRE50 case must reference the verified `surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_SoilField17_71_12_v2.nc`, NOT the older v1 or the original grid soil.

### Stage 08: interpret existing forcing QC before PRE50 submission

The site forcing receipt has `status=REVIEW`. A [strictly read-only 08 audit](scripts/08_audit_forcing_v5_review.py) prints **all 14 manual-review rows**, **all 32 replacement events**, the seven-variable QC summaries and a 525,600-record continuous NO_LEAP / gross-physical-range check. No forcing files are changed and `REVIEW` is never automatically promoted to PASS.

```bash
python3 -B examples/DE-Tha/scripts/08_audit_forcing_v5_review.py \
  2>&1 | tee ~/DE-Tha_forcing_v5_manual_QC_review.log
```



## 4. Remaining model design: 50 → 200 AD → 300 normal

Use **new isolated DE-Tha case names**, with no edits to `DE-Tha_FATES_SPINUP500` or its output and no dependency on the NL-Loo Slurm jobs.

| Proposed case | Years | Mode | Technical gate |
| --- | ---: | --- | --- |
| `DE-Tha_OBSPFT_NC_V1_PRE50` | 50 | Normal | 5-year first segment, check no competition/fixed biogeography and saved restart |
| `DE-Tha_OBSPFT_NC_V1_AD200` | 200 | Accelerated `spinup_state=2` | 5-year hybrid smoke, FATES_GPP/FATES_NPP, verify three-component restart and pointer |
| `DE-Tha_OBSPFT_NC_V1_POST300` | 300 | Normal `spinup_state=0` | 5-year hybrid smoke and validated restart |

`RUN_STARTDATE=1996-01-01` with 1996–2025 no-leap forcing files is a verified **existing legacy case** setup. For new PRE50 we can reuse that same audited cycle after checking stream/QC, rather than copying NL-Loo's 1997 calendar. 50 spin-up years are 10 five-year jobs; the next 200 are 40; the final 300 are 60. These durations are research design choices, not guarantees of convergence.

**Required FATES namelist flags**: `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`.

**Important:** the legacy `DE-Tha_FATES_SPINUP500` case is *ordinary FATES*: both `use_fates_nocomp` and `use_fates_fixed_biogeog` are `.false.`. It can supply forcing/case configuration references only, not serve as the requested FIXNC run. The validated NL-Loo scripts `scripts/09`–`scripts/15` contain incident-specific absolute paths and Slurm job IDs; **never execute them unchanged** for DE-Tha.

## 5. Forcing QC and other launch gates

Existing `forcing/processed_v5/DE-Tha_CLM_forcing_1996_2025.csv` has 525,600 records, 17,520 half hours per no-leap year; 30 candidate yearly DATM files have been found. The `qc_v5/DE-Tha_status.json` is currently **`REVIEW`** with 14 manual-review events, 32 replacement events, and 0 new low-RH decisions. These are not automatically fatal, but require event-by-event scientific interpretation before a new run.

The earlier `01_audit_evidence.py`, `02_inventory_iridis_inputs.py`, `03_audit_live_inputs.py` and `04_review_landunit_scenarios.py` remain as **read-only provenance and exploratory archives**, not additional active experiment configurations. `04` examines alternative grid/forest scenarios only to document why they were not chosen.

Next scientific gate: verify the newly created **v2 forest+observed-soil surface** using script 07, review the 14 manual cases and 32 substitutions using script 08, then confirm actual DATM streams, `fsurdat` and FIXNC namelists in a new isolated CIME PRE50 case. Do not submit jobs or modify the old spin-up until these checks pass.

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
```
