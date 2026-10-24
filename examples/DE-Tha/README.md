# DE-Tha — ICOS observed-forest PFT | fixed biogeography + no competition

**Selected scientific experiment:** ONE tower-forest PFT scenario **ENF 87%, DNF 10%, DBF 3%**. No original-grid/cropland/PFT-mix experiments are part of the active DE-Tha experiment. This is an *observationally informed single-point forest proxy*, **not** a measured grid-wide area map.

**Status:** Input provenance and FATES PFT map audited; new forest surface generator `scripts/05_build_forest_observed_surface.py` available; **surface not yet created on IRIDIS6 and no DE-Tha FIXNC case or Slurm job submitted**. Forcing v5 QC status is still `REVIEW` (14 manual-review rows, 32 replacement events), so inspect QC before any launch.

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

After a successful single write, **do not rerun `write`**. Instead verify the saved NetCDF and SHA256 receipt without changing anything:

```bash
python3 -B examples/DE-Tha/scripts/05_build_forest_observed_surface.py verify
```

If successful the one-time write creates a *new* surface (never overwrites an existing one):

```text
/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/DE-Tha/surface/
  surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.nc
  surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.json
```

The JSON receipt stores both NetCDF SHA256 values, fixed percentages and assumptions. This operation creates **no case or Slurm jobs**. A subsequent script must verify output hashes before binding the new `fsurdat`.

## 3. Remaining model design: 50 → 200 AD → 300 normal

Use **new isolated DE-Tha case names**, with no edits to `DE-Tha_FATES_SPINUP500` or its output and no dependency on the NL-Loo Slurm jobs.

| Proposed case | Years | Mode | Technical gate |
| --- | ---: | --- | --- |
| `DE-Tha_OBSPFT_NC_V1_PRE50` | 50 | Normal | 5-year first segment, check no competition/fixed biogeography and saved restart |
| `DE-Tha_OBSPFT_NC_V1_AD200` | 200 | Accelerated `spinup_state=2` | 5-year hybrid smoke, FATES_GPP/FATES_NPP, verify three-component restart and pointer |
| `DE-Tha_OBSPFT_NC_V1_POST300` | 300 | Normal `spinup_state=0` | 5-year hybrid smoke and validated restart |

`RUN_STARTDATE=1996-01-01` with 1996–2025 no-leap forcing files is a verified **existing legacy case** setup. For new PRE50 we can reuse that same audited cycle after checking stream/QC, rather than copying NL-Loo's 1997 calendar. 50 spin-up years are 10 five-year jobs; the next 200 are 40; the final 300 are 60. These durations are research design choices, not guarantees of convergence.

**Required FATES namelist flags**: `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`.

**Important:** the legacy `DE-Tha_FATES_SPINUP500` case is *ordinary FATES*: both `use_fates_nocomp` and `use_fates_fixed_biogeog` are `.false.`. It can supply forcing/case configuration references only, not serve as the requested FIXNC run. The validated NL-Loo scripts `scripts/09`–`scripts/15` contain incident-specific absolute paths and Slurm job IDs; **never execute them unchanged** for DE-Tha.

## 4. Forcing QC and other launch gates

Existing `forcing/processed_v5/DE-Tha_CLM_forcing_1996_2025.csv` has 525,600 records, 17,520 half hours per no-leap year; 30 candidate yearly DATM files have been found. The `qc_v5/DE-Tha_status.json` is currently **`REVIEW`** with 14 manual-review events, 32 replacement events, and 0 new low-RH decisions. These are not automatically fatal, but require event-by-event scientific interpretation before a new run.

The earlier `01_audit_evidence.py`, `02_inventory_iridis_inputs.py`, `03_audit_live_inputs.py` and `04_review_landunit_scenarios.py` remain as **read-only provenance and exploratory archives**, not additional active experiment configurations. `04` examines alternative grid/forest scenarios only to document why they were not chosen.

Next scientific gate: review the 14 manual cases and 32 substitutions, confirm the actual DATM use and site run streams, validate the output new surface `fsurdat` and supported FIXNC mode. Do not submit jobs or modify the old spin-up until these checks pass.

## Folder index

```text
examples/DE-Tha/
  README.md
  data/observed_tree_composition.csv
  config/experiment_manifest.json
  scripts/
    01_audit_evidence.py
    02_inventory_iridis_inputs.py
    03_audit_live_inputs.py
    04_review_landunit_scenarios.py
    05_build_forest_observed_surface.py    # selected single forest scenario
```
