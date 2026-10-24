# Batch01 Stage05/06 result and AD readiness — 24 October 2026

**Decision: no Batch01 AD400 yet.** The inherited grid surface is not used to select vegetation or texture. Old CIME cases are technical provenance only, not new experiment inputs.

## Stage05 observed

The user ran Stage05 and saved `/iridisfs/home/ly3n24/Batch01_10_stage05_station_inputs_20261024T100531Z/all_sites.json`. The ten stations have 12 original CIME cases (IT-Col and FR-Pue have both S30EXCL and S30SHARED). All twelve returned CONFIG_SCANNED and showed seven readable DATM config documents each, which does not certify effective forcing years or file contents.

Every old case's generated `CaseDocs/lnd_in` reported `use_fates=.true.`, `use_fates_sp=.false.`, **`use_fates_nocomp=.false.`**, and **`use_fates_fixed_biogeog=.false.`**. The old experiments therefore **cannot be reused as finished FIXNC/no-competition AD cases**. Build new isolated cases with verified flags, map, model revision, executable and newly approved site surface.

All old case XML excerpts report `DATM_MODE=1PT` and `DATM_YR_START=2018`, `DATM_YR_END=2019`, but stream configuration excerpts refer to other calendar years. These are **unreconciled config candidates**. Verify the effective generated DATM streams, actual file lists, time/calendar/NO_LEAP handling and repeat forcing period before proceeding.

## Stage06 observed

The user ran Stage06 and saved `~/Batch01_10_stage06_soil_evidence.log`. **Only FI-Sod has 3 station-derived soil texture horizons currently registered to GitHub**:

| Horizon | Fine-earth Sand % | Fine-earth Silt % | Fine-earth Clay % |
| --- | ---: | ---: | ---: |
| 0–10 cm | 93.130 | 6.341 | 0.528 |
| 10–20 cm | 95.506 | 4.188 | 0.306 |
| 20–40 cm | 96.839 | 2.950 | 0.211 |

These values are calculated from FLUXNET reported fractions *excluding stones*; the original percentages, stones and citation live in [station soil data](../../../data/batch01_10_soil_site_observations.csv). Depths below 40 cm are not measured in this source. **The remaining 9 stations are flagged NEED_SITE_OBSERVATION**; GitHub contains *no validated numerical texture for them*.

## Targeted source strategy and warnings

1. First scan locally archived station BIF/SOIL/ancillary sources using [Stage07 metadata inventory](../scripts/07_inventory_local_soil_evidence_readonly.py); candidate hits are NOT verified site soil.
2. Then check [ICOS Ecosystem 2026-1 Level 2 archives](https://www.icos-cp.eu/data-products/ecosystem-release), official [ICOS Soil Database](https://traitementinfosol.pages-forge.inrae.fr/icos/index.html) and [ETC SOIL_TEX / SOIL_DEPTH templates](https://www.icos-etc.eu/icos/documents/templates). Confirm site, depth, method, lab denominator and use permissions with PI as needed.
3. FR-Pue has particularly stony upper soil: [FLUXNET station description](https://fluxnet.org/sites/siteinfo/FR-Pue) notes that under 2 mm soil material constitutes only about **30% of the volume** in the first two layers. This cannot substitute for Sand/Clay measurements. Consider physical rock/coarse-fragment representation and soil-depth limits, not just texture.

## Execution — no changes to original datasets

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
SCRIPT=examples/Batch01_10/scripts/07_inventory_local_soil_evidence_readonly.py
python3 -B "$SCRIPT" --self-test || exit 1
set -o pipefail
python3 -B "$SCRIPT" 2>&1 | tee "$HOME/Batch01_10_stage07_soil_discovery.log"
```

This only reads existing metadata sources; writes a report under a new HOME directory. It does **not** load the old grid surface, modify forcing/cases/restarts or submit Slurm jobs.

## Exact AD release gate

For one-site AD5 technical smoke (FI-Sod is a *candidate*, not yet approved): source-specific soil texture with measured depth / approved deeper-layer extrapolation, coarse fragments and other essential soil fields; exact new `PCT_NATVEG=100` and `PCT_CROP=0` experimental surface; verified host/FATES PFT map and no-competition/fixed-biogeography flags; checked actual site forcing & NO_LEAP loop / CO2 baseline; **new isolated CIME case** with AD `CLM_ACCELERATED_SPINUP=on`, generated `spinup_state=2`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`. Run/archival and restarts must be verified before AD395 or another site. No 10-site bulk AD submission.
