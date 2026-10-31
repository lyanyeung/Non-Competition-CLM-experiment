# ICOS Batch04 CH-Aws Stage02G — 19-year unique supersaturation screening (31 October 2026)

**Evidence:** operator-pasted IRIDIS6 console output, not an independent read of the complete private JSON/CSV:
- JSON: `/home/ly3n24/ICOS_Batch04_stage02g_BOTDZjEh/results/stage02g_unique_RH_events.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02g_BOTDZjEh/results/stage02g_unique_RH_gt100_HH.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02g_BOTDZjEh/stage02g_console.log`

Source-pinned self-test PASS, annual Stage02F agreement TRUE in all 19 years, `STAGE02F_MISMATCHES 0`, 7 aligned candidate inputs per year, no modified forcing/cases/Slurm. The output `UNIQUE_YEAR_HH_TOTAL 1667` includes one record per year-HH with RH relative to liquid water above 100% in at least one candidate.

| Year | Unique RH-water >100% HH (union) | All 7 variants >100% HH (intersection) | Max RH-water (%) | Distinct consecutive episodes | Ice-reference RH >100% below 0 C (unique HH) |
|---|---:|---:|---:|---:|---:|
| 2006 | 0 | 0 | 99.449 | 0 | 4 |
| 2007 | 0 | 0 | 99.988 | 0 | 19 |
| 2008 | 0 | 0 | 99.945 | 0 | 0 |
| 2009 | 0 | 0 | 99.939 | 0 | 35 |
| 2010 | 0 | 0 | 95.481 | 0 | 29 |
| 2011 | 0 | 0 | 95.617 | 0 | 2 |
| 2012 | 0 | 0 | 95.910 | 0 | 0 |
| 2013 | 0 | 0 | 96.516 | 0 | 0 |
| 2014 | 0 | 0 | 99.960 | 0 | 11 |
| 2015 | 1 | 1 | 100.002 | 1 | 349 |
| 2016 | 0 | 0 | 99.999 | 0 | 871 |
| 2017 | 3 | 3 | 100.013 | 3 | 1148 |
| 2018 | 6 | 6 | 100.035 | 5 | 938 |
| 2019 | 4 | 4 | 100.030 | 4 | 981 |
| 2020 | 5 | 5 | 100.053 | 5 | 522 |
| 2021 | 1118 | 1118 | 100.071 | 136 | 2242 |
| 2022 | 405 | 405 | 100.069 | 47 | 1234 |
| 2023 | 94 | 94 | 100.007 | 8 | 1662 |
| 2024 | 31 | 31 | 100.011 | 7 | 1335 |
| **Total unique/year-HH** | **1667** | **1667** | **100.071 max** | **216 episodes summed by year** | — |

Across **all 19 years**, every unique RH-water >100% HH was common to all seven paths (union = intersection), even in 2017–2020 when some other QBOT values differ between candidate versions. **All years had 0 HH above 105% and above 110% RH-water** (the same is true for thresholds 120%, 150%). The high counts in 2021–2024 (1648 unique HH) are inherited by all variants; they are **not created by RH21A/RH42A differences**. Magnitudes are very small: maximum diagnostic RH-water 100.071%, likely sensitive to saturation formula, thermodynamics, floating precision or near-saturated conditions. This alone does NOT justify deleting/capping those records.

**Critical science nuance:** saturation relative to ice can exceed 100% below freezing while relative to supercooled liquid water remains <=100%. Ice-supersaturation flags may be physically plausible and should be checked with site conditions and phase convention, not automatically repaired. The tool provides threshold and episode diagnostics, not direct source validation or an observation-based acceptance test. Unit/calendar metadata and actual 30-minute origin (UTC vs site-native) still need source verification. All six sites remain **science HOLD** despite previously passing DATM internal numerical screens.

### Priority change

1. Do **not** bulk change 2021–2024 forcing for marginal RH-water exceedances (all <0.1 percentage points). Verify tower-source RH derivation and saturation convention when comparing if needed.
2. Highest scientific uncertainty remains **2007, 2008 and 2016–2020 QBOT changes** (prior Stage02E up to 11.051 hPa diagnosed vapour-pressure difference); a low saturation count does not make such revisions correct.
3. [Stage02H read-only provenance discovery and event review manifest](../scripts/02h_CH_Aws_tower_ERA_source_manifest_readonly.py) will locate candidate source products without scanning/altering model data, and emit a ranked list of extreme CH-Aws time events from the saved Stage02E/QBOT and Stage02G/Humidity JSONs. **Do not infer original tower/ERA values from filenames or variant labels.** Final paired half-hour validation remains blocked until raw source, source QC, calendar basis and ERA5 evidence are positively identified.

No new model cases, surface/forcing edits, QC relabels, AD5/AD400 or Slurm submissions were approved.
