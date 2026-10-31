# ICOS Batch04 Stage02D — remaining CH-Aws and GL-ZaH, 31 October 2026

## Provenance

Operator-provided terminal output, **not** an independent inspection of full JSON. Same source-pinned Stage02D reader previously checked on the first four sites; environment `/home/ly3n24/.conda/envs/clm_fates_env/bin/python3` (NumPy 2.2.6 and netCDF4 1.7.4).

- Stage02C source: `/home/ly3n24/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json`.
- Stage02D remaining two JSON: `/home/ly3n24/ICOS_Batch04_stage02d_remaining_iyjEJeDP/stage02d_remaining2.json`.
- Corresponding console log: `/home/ly3n24/ICOS_Batch04_stage02d_remaining_iyjEJeDP/stage02d_remaining2.log`.
- `READ-ONLY COMPLETE` and `SCIENCE_RELEASE HOLD` both reported. No Slurm jobs, NetCDF or CIME files modified.

| Site | Distinct annual candidate NC | Year range | Cross-variant differing years | Stage02D flags | Decision |
| --- | ---: | --- | --- | --- | --- |
| CH-Aws | 133 | 2006–2024 | **14** | `{}` | **HOLD_QBOT_VERSION_SCIENCE** |
| GL-ZaH | 26 | 2000–2025 | 0 | `{}` | **HOLD_ARCTIC_PRIVATE_PFT_AND_SOURCE_QC** |

CH-Aws's exact changed years: **2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2018, 2019, 2020**. Each printed `DIFF_FIELDS QBOT` only. There were **no reported differences among the compared variants in 2015 or 2021–2024**. The seven candidate 19-year path sets span 2006–2024, yielding 133 unique annual input paths across eight case choices. The audit performed per-variable exact numerical-signature comparison, **not** tower-QC validation. The difference itself cannot tell which candidate is correct or if the variants have equivalent physics.

GL-ZaH: 26 annual files, years 2000–2025, no internal flags. Still requires a site-only **FATES Arctic shrub map** replacing shared host PFT 9/11 mapping, as well as tundra site metadata, original source QC and stream-binding review.

## Six-site cumulative Stage02D technical summary

The first four stations had 22 + 15 + 18 + 19 = **74** distinct annual DATM candidates. CH-Aws/GL-ZaH add 133 + 26 = **159**, giving **233** unique candidate annual input paths in the full six-site audit. All six printed `FLAGS {}` under the *implemented DATM-internal, read-only* screens. File existence and time consistency are promising but **not proof of tower accuracy, ERA5 substitution validity, active DATM stream, complete science release or readiness for AD5/AD400**.

## Next audit

[Stage02E CH-Aws per-half-hour QBOT version-difference audit](../scripts/02e_CH_Aws_QBOT_19y_version_diff_readonly.py): compare 7 candidate forcing paths against a clearly named **reference original case, solely as a diagnostic baseline**, quantify changed timestamps and magnitudes (g/kg and approximate vapour-pressure/VPD hPa), check TBOT/PSRF/time alignment, report maximal events. It must **not** automatically select a repaired humidity variant, modify the forcing or submit Slurm. Tower native RH/VPD/QC and ERA5 remain separate next scientific evidence.
