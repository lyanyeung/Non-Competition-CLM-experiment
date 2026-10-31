# ICOS Batch04 Stage02E — CH-Aws 19-year QBOT differential, IRIDIS6 (31 October 2026)

**Provenance:** exact operator-pasted console output of the immutable GitHub Stage02E code after self-test. Not an independent inspection of the full private JSON. Source was verified; report was generated at `/home/ly3n24/ICOS_Batch04_stage02e_ltWaEE72/stage02e_CH_Aws_QBOT.json` and operator log `/home/ly3n24/ICOS_Batch04_stage02e_ltWaEE72/stage02e_CH_Aws.log`. **No source, CIME case or Slurm modification.**

Baseline: `CH-Aws_FATES_SPINUP500_11P`, expressly an **arbitrary numerical comparator, not a recommended or verified source**. Seven distinct DATM candidate paths in each of 19 years, 2006–2024 (8 cases total, RH25A diagnostic and RH25A spinup share an annual path set). All `19 × 7 = 133` file comparisons reported `HOLD_COMPARISONS 0`, including time/field-unit alignment.

| Year | Maximum changed HH among seven variants | Max abs QBOT difference (g/kg) | Max abs vapour-pressure difference (hPa) | Earliest changed timestamp shown |
| --- | ---: | ---: | ---: | --- |
| 2006 | 218 | 2.4719725 | 3.1990718 | 2006-01-09 02:30 |
| 2007 | 107 | 8.6460387 | 11.051293 | 2007-04-06 12:00 |
| 2008 | 98 | 7.3788864 | 9.5482504 | 2008-02-12 02:30 |
| 2009 | 92 | 1.0742009 | 1.3336784 | 2009-01-03 07:00 |
| 2010 | 140 | 1.1026688 | 1.3808647 | 2010-01-03 06:30 |
| 2011 | 44 | 1.0725149 | 1.3630339 | 2011-01-03 08:30 |
| 2012 | 118 | 1.0705861 | 1.3543216 | 2012-01-15 05:00 |
| 2013 | 73 | 2.0980411 | 2.7206975 | 2013-01-26 07:00 |
| 2014 | 23 | 2.0681891 | 2.6578502 | 2014-01-12 21:00 |
| 2015 | 0 | 0 | 0 | — |
| 2016 | 1 | 4.4064682 | 5.6086992 | 2016-07-14 07:00 |
| 2017 | 21 | 4.9939921 | 6.3313418 | 2017-05-20 10:30 |
| 2018 | 4 | 5.6342064 | 7.2003304 | 2018-08-26 10:00 |
| 2019 | 4 | 7.3444298 | 9.2843092 | 2019-07-29 07:30 |
| 2020 | 14 | 7.6110344 | 9.7850231 | 2020-01-18 09:00 |
| 2021 | 0 | 0 | 0 | — |
| 2022 | 0 | 0 | 0 | — |
| 2023 | 0 | 0 | 0 | — |
| 2024 | 0 | 0 | 0 | — |

**Scientific interpretation limitations:**
- A year's `MAX_CHANGED_HH` is the **maximum count from one candidate compared with the baseline**; it does *not* give the count for a particular named version across years. Do not add these maxima to claim a cumulative repaired-row count.
- For 14 years (2006–2014 and 2016–2020), the Stage02D data signatures had identified **QBOT alone** as different across forcing paths; 2015 and 2021–2024 were identical among compared candidate variables. Stage02E then quantified QBOT differences with **no comparison alignment HOLDs**.
- The largest yearwise absolute inferred vapour-pressure difference reached **11.051293 hPa** in 2007 and **9.7850231 hPa** in 2020. These magnitudes warrant checking physical saturation, native tower RH/T/VPD/QC and ERA5, including source provenance and calendar/time basis. They do not by themselves prove the edits are wrong.
- Stage02D generic `FLAGS {}` is **not a derived-RH/saturation pass**. QBOT can be finite/nonnegative yet imply implausible relative humidity at cold temperatures. The atmosphere/ice saturation reference matters for alpine sites; never cap RH or replace data without native observation evidence.
- No actual active CIME DATM stream or surface/soil/PFT release has been established. All six sites still science HOLD; specifically CH-Aws **HOLD_NATIVE_HUMIDITY_SOURCE_QC**.

**Next gate:** [Stage02F read-only CH-Aws humid-air physics and full changed-HH event ledger](../scripts/02f_CH_Aws_QBOT_saturation_and_event_ledger_readonly.py), with a full CSV for operator/source-backed event review. It must *not* assume a chosen RH repair version or modify any forcing.
