# ICOS Batch04 CH-Aws — Stage02K operator event physics result (31 Oct 2026)

## Provenance and data scope

Operator-provided exact console output of Stage02K run (not independent inspection of its private full JSON/CSV). `SOURCE VERIFIED`, `STAGE02K SELF-TEST PASS`, `EVENT_COUNT 20`, `MODEL_READ_HOLDS 0`, `EXACT_START_END_SOURCE_CANDIDATE_ROWS 40`. Source FLUXMET BIFVARINFO_HH metadata read successfully, **34 candidate metadata rows**. No input data, model cases, Slurm or original Git working tree modified.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02k_dbo0MGh4/results/stage02k_CH_Aws_source_DATM_event_physics.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02k_dbo0MGh4/results/stage02k_CH_Aws_source_DATM_two_clock_candidates.csv`
- Log: `/home/ly3n24/ICOS_Batch04_stage02k_dbo0MGh4/stage02k_console.log`

20 event anchors were indexed to original Stage02E candidate DATM time-series positions. All seven candidate file groups were opened for each anchor, with time label and TBOT/PSRF consistency enforced; zero internal source-read holds. The unapproved `CH-Aws_FATES_SPINUP500_11P` was used **only** as a numerical reference.

## Strong START-time / source processing hypothesis

All **20/20** printed events have model-reference water-VPD within **0.007 hPa** of the same-label FLUXMET **`TIMESTAMP_START` `VPD_F`**, whereas `TIMESTAMP_END` differs considerably on many events. This is direct quantitative evidence consistent with the reference DATM being derived from a source product indexed by START time and using `VPD_F`; it does **not by itself establish native UTC/local clock convention, raw measured VPD, QC validity, or whether that reference is the best scientific forcing**.

| Stage02K event | Year/event time | Reference DATM VPD (hPa) | FLUXMET START VPD_F | FLUXMET END VPD_F | largest QBOT difference from reference (g/kg) |
|---|---|---:|---:|---:|---:|
| E001 | 2007-07-22 07:30 | 11.253246 | 11.247 | 10.344 | 8.646039 |
| E002 | 2007-07-22 07:00 | 10.348831 | 10.344 | 8.376 | 7.978555 |
| E003 | 2020-07-17 10:00 | 11.506968 | 11.500 | 7.223 | 7.611034 |
| E004 | 2008-06-27 06:30 | 10.211817 | 10.206 | 3.245 | 7.378886 |
| E005 | 2007-07-04 07:00 | 9.823093 | 9.818 | 6.921 | 7.465058 |
| E006 | 2019-07-29 07:30 | 10.351942 | 10.346 | 6.678 | 7.344430 |
| E007 | 2008-06-28 06:30 | 10.377808 | 10.373 | 3.035 | 7.044541 |
| E008 | 2007-08-04 07:00 | 8.783580 | 8.780 | 6.941 | 6.217885 |
| E009 | 2007-05-17 13:00 | 8.511708 | 8.509 | 9.504 | 6.014588 |
| E010 | 2018-09-22 09:30 | 8.323411 | 8.320 | 5.614 | 5.634206 |
| E011 | 2020-08-04 09:00 | 7.772641 | 7.770 | 6.356 | 5.583564 |
| E012 | 2020-08-04 12:00 | 8.700959 | 8.698 | 8.350 | 5.535026 |
| E013 | 2020-08-04 11:30 | 8.352828 | 8.350 | 7.278 | 5.356276 |
| E014 | 2020-08-04 14:00 | 8.354307 | 8.351 | 7.607 | 5.064290 |
| E015 | 2017-09-02 12:30 | 6.748759 | 6.748 | 6.145 | 4.993992 |
| E016 | 2017-08-12 09:30 | 7.906725 | 7.904 | 7.501 | 4.890837 |
| E017 | 2017-09-02 13:30 | 6.570814 | 6.570 | 7.226 | 4.853220 |
| E018 | 2017-09-02 14:00 | 6.367891 | 6.367 | 6.570 | 4.763867 |
| E019 | 2017-09-02 14:30 | 6.367895 | 6.367 | 6.367 | 4.725791 |
| E020 | 2016-07-14 07:00 | 6.203673 | 6.203 | 5.679 | 4.406468 |

Displayed original FLUXMET context samples for every event had `VPD_F_QC=1` and prior Stage02J `TA_F_QC=0`; under the standard FLUXNET processed-product convention, `VPD_F_QC=1` denotes a high-quality **gapfilled** value, **not directly observed native VPD**, and TA QC 0 denotes observed TA. Field definitions/source-product metadata must be explicitly corroborated (Stage02K's BIFVARINFO inventory contains 34 candidate rows, not yet operator-reviewed individually).

The large changes in some alternate QBOT versions (as high as 8.646 g/kg or 11.051 hPa equivalent vapor pressure) **are not adjudicated by numerical similarity to FLUXMET VPD_F alone**: revision ledgers may reference measured `RH`, inferred source, or other QC rules. The next gate should quantify per-variant agreement separately with FLUXMET START/END VPD_F, `VPD_ERA`, raw `RH` and source pressure/temperature at the 20 anchors, with units and QC flags retained; **no source or case is automatically selected**.

## Next stage

[Stage02L read-only quantitative START-vs-END / candidate VPD and RH source evidence matrix](../scripts/02l_CH_Aws_event_QC_source_comparison_readonly.py). It reads only the preserved Stage02K JSON, emits a 20-event × 7-version matrix and numerical diagnostic summary, leaving all time basis, native tower RH, original instrument QC, ERA5 provenance and model case-release decisions as HOLD. No changes to forcing/surface/soil/FATES/Slurm, no AD5 or AD400 authorization.
