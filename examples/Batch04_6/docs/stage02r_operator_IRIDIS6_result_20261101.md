# ICOS Batch04 CH-Aws Stage02R successful IRIDIS6 audit and Stage02S source-clock test

**Operator evidence date:** 1 November 2026. Exact Stage02R source Git SHA verified, `STAGE02R SELF-TEST PASS`, user reports read-only full audit success. The following private HOME outputs were not independently uploaded to GitHub:

- JSON `/home/ly3n24/ICOS_Batch04_stage02r_2zMBe7n8/results/stage02r_CH_Aws_original_metadata_legacy_clock_review.json`
- CSV `/home/ly3n24/ICOS_Batch04_stage02r_2zMBe7n8/results/stage02r_CH_Aws_legacy_time_context_candidates.csv`
- LOG `/home/ly3n24/ICOS_Batch04_stage02r_2zMBe7n8/stage02r_console.log`

## Discovered original input register and science QC

Original Stage03 `CH-Aws_inputs.csv` lists **two** processed distributed EUF sources for a target **2006–2024 NOLEAP window of 332,880 HH**:

- `EUF_F`: `.../forcing/raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv`
- `EUF_ERA5`: `.../forcing/raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv`

**Stage03 listing is path provenance, not live proof of on-disk existence.** Stage03 status of the earlier candidate: `REVIEW_REQUIRED`, original target length 332880; candidate-invalid humidity pair records **559**, fallback to other priority source **77**, source pair changes **86**, `physically_valid_pair 332321`, `missing_any_met 0`. The status specifically warns source `_F` is gapfilled/reanalysis, mixing tower/ERA parts is prohibited, and no DATM was written or scientifically approved from that stage.

## Historical Stage09 grid-reference checks

Stage09 original time-offset correlation results (temperature, QC0/QC1 site points, `n=57581` each):

| Reference | Tested numerical offset hours | Correlation | RMSE °C | Site minus grid °C |
|---|---:|---:|---:|---:|
| ERA5 | 0 | **0.88405** | **3.1953** | 0.7521 |
| ERA5 | +1 | 0.86479 | 3.4145 | 0.7480 |
| ERA5 | +2 | 0.82341 | 3.8441 | 0.7451 |
| ERA5-Land | 0 | **0.87991** | **3.3062** | 0.9864 |
| ERA5-Land | +1 | 0.86346 | 3.4877 | 0.9817 |

The stage's own `04_stage09_status.json` states `reference_time_UTC_offset_hours=1`, **FLUXNET local standard time = UTC + offset; DST not applied**, but **manual clock verification required**. These are different coding conventions: an exploratory offset parameter's 0 shift scoring best does **not by itself** refute the station BIF `UTC_OFFSET=1`. Stage09 reference provider is **Open-Meteo historical archive** (models `era5` and `era5_land`); these related reanalyses are **not independent tower observations**. The earlier 559 RH events have 526 cases supported under an exploratory ±15 percentage-point consistency criterion, **33 unsupported**, and the Stage09 report is `REVIEW_ONLY_NO_FORCING_WRITTEN`.

## Authoritative original EUF/ONEFlux BIF source definitions

BIF: `UTC_OFFSET=1`; processor `EUDB_ICOS`, product `EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2`, ONEFlux version `1.3.5-rc`; network EUF. BIF downscaled ERA VPD correlation **0.74** and RMSE **1.33** (source metadata values; representativeness is not independently verified by these numbers).

BIFVARINFO_HH (original raw source metadata group definitions):

| Variable | Original product definition | Unit and height |
|---|---|---|
| `TA_F` | Consolidated from `TA_F_MDS` and `TA_ERA`; use MDS when its QC is 0 or 1 | °C; 1.5m |
| `TA_F_QC` | 0 measured; 1 good-quality gapfill; 2 downscaled ERA | dimensionless |
| `VPD_F_MDS` | Gapfilled using MDS | hPa; 1.50m |
| `VPD_F_MDS_QC` | 0 measured; 1 good-quality gapfill; 2 medium; 3 poor | dimensionless |
| `VPD_ERA` | Downscaled ERA using linear regression on **measured-only site data** | hPa; 1.50m |
| `VPD_F` | Consolidated `VPD_F_MDS` and `VPD_ERA`; uses MDS when MDS_QC=0 or 1 | hPa; 1.50m |
| `VPD_F_QC` | 0 measured; 1 good-quality gapfill; 2 downscaled ERA | dimensionless |
| `PA_F` | Consolidated measured `PA` with `PA_ERA` | kPa; 1.3m |
| `RH` | Relative humidity, range 0–100 | %; 1.5m |

The Stage02L selected 20 high-variance event rows had `VPD_F_QC=1` (therefore **gapfilled under site-specific actual definition**) and numeric original distributed `RH` missing 20/20. BIF contains `RH` metadata, but this is **not** evidence that there is numeric original unfilled RH at the selected event timestamps, nor that external instrument RH file was recovered.

## Stage21/25 legacy timestamp coverage

Stage21 ledger **779 rows**, spanning 2006-01-09 to 2013-12-11; Stage25 ledger **30 rows**, spanning 2006-01-12 to 2012-02-09, both with `time_local_standard_UTCplus1`. Stage02R reported **zero literal ±60-minute overlap** with the current 20 Stage34/38/42 high-difference anchors; since those are separate event populations, absence of overlap does not independently establish a bad clock.

## Next Stage02S: original-distribution ERA source vs FLUXMET time labels

The [Stage02S source-locked read-only script](../scripts/02s_CH_Aws_original_EUF_ERA5_to_FLUXMET_clock_readonly.py) consumes the already saved Stage02R and Stage02L JSONs, reads Stage03's *exact listed original EUF ERA5_HH path if it is actually present*, and compares its `VPD_ERA` and `TA_ERA` at event labels under independent `TIMESTAMP_START` and `TIMESTAMP_END` and literal -120, -90, -60, -30, 0, +30, +60, +90, +120 minute hypotheses. This is to identify where the earlier 0 vs +1-hour *numerical alignment* results originate, not to choose a canonical UTC convention by lowest MAE. It streams the source file once with an upper bound of 1 million records / 2GB, keeping only 20 × 2 × 9 candidate windows; the 372MB processed FLUXMET file is **not reread**. If the original ERA5 file path is now absent, it reports a transparent **SOURCE_HOLD**, not an invented/mirrored substitute.

Outputs only a new JSON and CSV in an empty HOME output directory. All source/clock/native QC and site-grid-representativeness gates remain HOLD. No AD5/AD400, no CIME, no forcing changes, no network/download and no Slurm.
