# ICOS Batch04 CH-Aws — Stage02H source discovery and ranked event manifest

Date: **31 October 2026**. Evidence: operator-pasted IRIDIS6 console output from source-pinned Stage02H and its `--self-test` (both PASS). The underlying private JSON/CSV have **not been independently inspected in GitHub**.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02h_UsOLvU01/results/stage02h_source_event_manifest.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02h_UsOLvU01/results/stage02h_ranked_QBOT_HH.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02h_UsOLvU01/stage02h_console.log`
- Read-only scan of `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing`: **164 files** (`19 CSV, 11 JSON, 134 NC`), no truncated scan; no modifications to any original source files, case, job or source Git working tree.

## Important existing local source artifacts

- `merged_multisource_11_landrh11a/CH-Aws_559_RH_trial_ledger.csv` (191,243 bytes); `CH-Aws_33_high_uncertainty.csv` (11,875 bytes); ~64.8 MB merged-multisource candidate half-hour CSV.
- `merged_multisource_11_landrh21a/CH-Aws_stage21_revision_ledger.csv` (306,610 bytes); ~68.6 MB candidate half-hour CSV.
- `merged_multisource_11_landrh25a/CH-Aws_stage25_revision_ledger.csv` (5,063 bytes); ~71.9 MB candidate half-hour CSV.
- `merged_multisource_11_v07a/CH-Aws_multisource_HH_2006_2024_candidate.csv` (~61.1 MB).
- `datm_11_stage28_jan14_trial_v4/CH-Aws_stage28_9row_ledger.csv`
- `datm_11_stage29_all77_rh_sensitivity_v5/stage29_77record_sensitivity_ledger.csv`
- `datm_11_stage34_qc1_27rh_sensitivity_v6/stage34_27_QC1_sensitivity_ledger.csv`
- `datm_11_stage38_qc1_21rh_sensitivity_v7/stage38_21_QC1_ledger.csv`
- `datm_11_stage42_all19year_qc1_low10_sensitivity_v8/stage42_QC1_ledger.csv`
- Revision manifests at stages 22/26/28/29/34/38/42; original product tree `raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/!TOC.csv`.

**Caution:** these paths are candidate evidence, NOT validation of native tower, ERA5, QC provenance, original vs derived variables, or their time-zone bases. Stage02H did not open original observations or compare their values with the models.

## Highest ranked QBOT difference event anchors

All differences are relative to the arbitrary, unapproved `CH-Aws_FATES_SPINUP500_11P` baseline.

| Candidate timestamp as decoded from DATM | Max absolute QBOT delta (g/kg) | Max absolute water-vapour-pressure delta (hPa) | Candidate |
|---|---:|---:|---|
| 2007-07-22 07:30 | 8.646039 | 11.051293 | RH34A |
| 2007-07-22 07:00 | 7.978555 | 10.204440 | RH34A |
| 2020-07-17 10:00 | 7.611034 | 9.785023 | RH42A V8 |
| 2008-06-27 06:30 | 7.378886 | 9.548250 | RH34A |
| 2007-07-04 07:00 | 7.465058 | 9.461268 | RH34A |
| 2019-07-29 07:30 | 7.344430 | 9.284309 | RH42A V8 |
| 2008-06-28 06:30 | 7.044541 | 9.146934 | RH34A |
| 2007-08-04 07:00 | 6.217885 | 8.036378 | RH34A |
| 2007-05-17 13:00 | 6.014588 | 7.642550 | RH34A |
| 2018-09-22 09:30 | 5.634206 | 7.200330 | RH42A V8 |
| 2017-09-02 12:30 | 4.993992 | 6.331342 | RH38A |

The remaining ranked events include 2020-08-04 09:00–14:00 in RH42A, up to ~7.14 hPa vapour-pressure differences.

## Longest RH>100% episodes (water-saturation reference)

- 2022-02-01 19:00: **45 half-hours** = 22.5 h, maximum RH_water 100.05564%.
- 2021-12-08 15:00: **35 half-hours** = 17.5 h, maximum 100.05314%.
- 2022-04-01 16:00: **33 half-hours** = 16.5 h, maximum 100.05840%.
- 2021-04-12 07:00: **32 half-hours** = 16 h, maximum 100.05236%.
- 2021-03-17 16:30: **29 half-hours** = 14.5 h, maximum 100.07126%.

Long episodes with maximum only ~100.07% can reflect small saturation-formula, pressure/temperature or rounding differences and **should not trigger any automatic correction**.

## Science gate

The next task is **Stage02I event-specific source-evidence matching**, beginning with the source CSV headers, time-column conventions and revision ledgers in the known forcing tree. A matched string timestamp is only a candidate observation and not proof of tower QC/ERA timing; native UTC/local/time-end conventions, source QC0/QC1 and ERA5 provenance must be explicitly confirmed prior to model/forcing release. No AD5/AD400, data edits, RH caps, FATES shared-parameter changes or Slurm submission approved.
