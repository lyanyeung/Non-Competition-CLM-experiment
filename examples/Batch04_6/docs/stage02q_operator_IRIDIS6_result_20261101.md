# ICOS Batch04 CH-Aws Stage02Q — successful 2026-11-01 IRIDIS6 result and Stage02R scope

The source-pinned repaired Stage02Q ran successfully on IRIDIS6. This document reflects the operator-provided terminal output; the privately saved Stage02Q JSON and CSV have not been independently imported.

- `/home/ly3n24/ICOS_Batch04_stage02q_fixed_bsOEPjTg/results/stage02q_CH_Aws_clock_and_source_provenance.json`
- `/home/ly3n24/ICOS_Batch04_stage02q_fixed_bsOEPjTg/results/stage02q_CH_Aws_stage21_25_time_hypotheses.csv`
- `/home/ly3n24/ICOS_Batch04_stage02q_fixed_bsOEPjTg/stage02q_fixed_console.log`

The verified script passed its **6,003-row BIF streaming regression test** and completed the full read-only audit.

## Original distributed product metadata

| Source | CSV records | Source detail |
|---|---:|---|
| EUF BIF | **5,192**, complete | `GRP_UTC_OFFSET`, `UTC_OFFSET = 1` for CH-Aws; `GRP_ONEFLUX PRODUCT_SOURCE_NETWORK = EUF`; `GRP_ERA_DOWN` `ERA_VARIABLE` for TA, PA and VPD |
| EUF BIFVARINFO_HH | **1,027**, complete | `RH` appears in variable source metadata (`VAR_INFO_AGG_NUMLOC = [TA] 1. [SW_IN] 1. [RH] 1` and `VAR_INFO_MODEL = ... [RH] RH-Other`); `TA_ERA` definition explicitly says downscaled from ERA using regression on measured-only site data; source contains extensive QC and VPD field definitions |

**Crucial caveat:** the BIF UTC offset of +1 and the Stage21/25 name `time_local_standard_UTCplus1` establish compatible *metadata labels*, but do **not** independently prove the offset and interval conventions used by actual selected DATM forcing or ERA-grid queries. `RH` appearing in BIFVARINFO_HH shows the presence of RH information in metadata, not numeric native RH at the 20 event anchors. FLUXMET `VPD_F_QC=1` is a processed gap-filled measurement under standard ONEFlux conventions, not original unfilled tower VPD.

## Legacy Stage21/25 time ledger test

- Stage21 revision ledger: **779 rows** with `time_local_standard_UTCplus1`.
- Stage25 revision ledger: **30 rows** with the same field name.
- Literal 0, ±30, ±60-minute matching against the chosen 20 Stage02O DATM event labels: **0 matches** in each ledger.

**Do not treat zero event overlap as a timezone failure.** These are earlier revision ledgers and likely contain a different event population. Inspect their actual min/max dates and source-selection columns first, and compare independently with the earlier Stage09 timezone-alignment output.

## Crucial newly discovered earlier investigation files

Stage02Q scanned **5,357** filenames in bounded HOME search, found **128** candidate CH-Aws source-related files and reported `search_truncated = false`. In the existing `FLUXNET_MultiSite_11` historical workflow it found:

- `stage09_CH_Aws/01_timezone_alignment.csv` — **349 bytes**, original earlier time-alignment test.
- `stage09_CH_Aws/02_CH_Aws_559_event_reference_comparison.csv` — ~154 KB, 559 RH-event comparison candidates.
- `stage09_CH_Aws/04_stage09_status.json` — original audit status/provenance.
- `stage03_merge_qc/CH-Aws_inputs.csv`, `CH-Aws_status.json`, and `CH-Aws_humidity_review.csv` — earlier source/merged humidity QC evidence.
- `stage06_science_diagnostics/CH-Aws_RH_episodes.csv` — event-group reference.
- `stage09_CH_Aws/raw_openmeteo/era5_2006.json` through `era5_2020.json` and corresponding `era5_land` JSON — **historical Open-Meteo response snapshots**, not independently validated ERA5 or official tower source truth.

These are **additional historical provenance** in an authorized user HOME directory, not certified original sensor RH observations. The named output records can be read without downloading new meteorological data or changing existing model/forcing files.

## Next stage: Stage02R

[Read-only Stage02R source/clock audit](../scripts/02r_CH_Aws_historical_timezone_and_RH_provenance_readonly.py) uses the *saved verified Stage02Q JSON to pin the discovered filenames* and reads seven small legacy Stage03/06/09 CSV/JSON files, plus the original BIF/BIFVARINFO metadata and Stage21/25 ledgers. It will report original Stage09 timezone-alignment rows, stage03 original input/source status, BIF group-level RH/VPD/QC/UTC definitions, Stage21/25 actual date ranges, and any same-label ±30/60-minute event-context candidate timestamps. All matches explicitly remain **unverified time-basis hypotheses**.

Only new JSON and CSV are generated in a fresh empty HOME report folder. No original file edits, no ZIP extraction, no 372 MB FLUXMET reread, no Slurm jobs, and no science approval. This audit cannot declare missing tower source data nonexistent elsewhere. If the old files expose a verifiable original sensor-level RH source, investigate it at exact timestamps with native QC next. If no such sensor-level source can be established, CH-Aws original humidity release remains HOLD while separately processing the remaining four lower-risk station science preflights.

## Scientific gate

CH-Aws RH34A/38A/42A remain **exploratory**. The 20/20 selected high-QBOT-difference events had implied RH below 10% and >50 percentage-point discordance with ERA5 and ERA5-Land; these are **selected extreme disagreements**, not representative all-site error prevalence. Neither the old gapfilled VPD nor ERA proximity alone proves native truth. All six Batch04 stations are still on scientific HOLD and no AD5/AD400 can be submitted solely on this evidence.
