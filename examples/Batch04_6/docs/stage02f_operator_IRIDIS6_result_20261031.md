# ICOS Batch04 Stage02F — CH-Aws humidity saturation screening, operator IRIDIS6 result (31 October 2026)

**Provenance:** operator-pasted console output; the private full report and changed-half-hour CSV have **not** been directly examined in GitHub. Existing local files:
- `/home/ly3n24/ICOS_Batch04_stage02f_fixed_ynHMlvrA/results/stage02f_summary.json`
- `/home/ly3n24/ICOS_Batch04_stage02f_fixed_ynHMlvrA/results/stage02f_all_changed_HH.csv`
- `/home/ly3n24/ICOS_Batch04_stage02f_fixed_ynHMlvrA/stage02f_console.log`

Fixed SHA-pinned Stage02F code self-test passed: `decoded Stage02C dict, 8 cases, 7 path sets, water/ice saturation; no writes`. The data run printed 19 annual groups, seven candidate paths per year, **zero comparison holds**, `CHANGED_EVENT_ROWS 5278`, and `ALL SCIENCE HOLD`. No original forcing/CASE/Slurm modifications.

| Year | Changed *candidate-version × HH* rows (sum across 7 paths) | RH relative to liquid water >100% rows (sum across 7 paths) |
| --- | ---: | ---: |
| 2006 | 1272 | 0 |
| 2007 | 559 | 0 |
| 2008 | 575 | 0 |
| 2009 | 551 | 0 |
| 2010 | 832 | 0 |
| 2011 | 261 | 0 |
| 2012 | 691 | 0 |
| 2013 | 380 | 0 |
| 2014 | 92 | 0 |
| 2015 | 0 | 7 |
| 2016 | 1 | 0 |
| 2017 | 42 | 21 |
| 2018 | 4 | 42 |
| 2019 | 4 | 28 |
| 2020 | 14 | 35 |
| 2021 | 0 | 7826 |
| 2022 | 0 | 2835 |
| 2023 | 0 | 658 |
| 2024 | 0 | 217 |
| **Total** | **5278** | **11669** |

**Critical denominator:** each printed RH count is a *sum over seven candidate annual forcing paths*, not seven independent tower observations. Since Stage02E showed **no QBOT differences** among seven versions in 2015 and 2021–2024, counts on those years can be divided by seven to get exact independent half hours:
- 2015: **1 unique HH**
- 2021: **1118 unique HH**
- 2022: **405 unique HH**
- 2023: **94 unique HH**
- 2024: **31 unique HH**
- 2021–2024: **1648 unique HH**, common to the seven candidates.

On the 2017–2020 years, variants have differing QBOT values; *do not* automatically divide the RH totals by seven. The 5278 changed rows likewise repeat time points across candidate variants; they are **not** a count of unique changed timestamps. The Stage02F screen computes water-vapour pressure from QBOT+PSRF and diagnostic RH against Buck saturation over liquid water and ice. **RH_water >100% is a triage indicator, not proof of erroneous native observations**, especially when evaluating cold/wet conditions; require magnitude, consecutive durations, instrument source/QC, ice phase and ERA5 comparison.

### Scientific HOLD / new priority

1. Investigate **2021–2024 common-source humidity**. These years have no candidate differences, so comparing RH21A/25A/42A alone cannot fix this shared signal. Distinguish slight supersaturation/fog from physically implausible high-RH events and check tower RH source QC.
2. Preserve earlier isolated large QBOT changes (2007, 2008, 2016–2020), and scrutinize near-freezing conditions and year-boundary forcing.
3. Do not cap RH, interpolate, relabel QC, write NC, change the shared FATES parameters or release AD5/AD400.
4. **Next step:** [Stage02G seven-variant unique-event/episode screening](../scripts/02g_CH_Aws_RH_supersaturation_unique_events_readonly.py), then source-specific native tower and ERA5 pairing.

All six ICOS Batch04 sites remain science HOLD despite passing the limited DATM internal screens.
