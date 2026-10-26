# ES-LJu Stage24 science decisions and completion status (2026-10-26)

## Operator decisions — authoritative for this site's isolated forcing candidate

1. **2013-12-25 extreme precipitation: RETAIN ORIGINAL TOWER, APPROVED BY OPERATOR.** No redistribution, capping, deletion or ERA5 substitution. The operator explicitly elects to trust the original tower gauge (QC0) although ERA5 precipitation magnitude and peak timing diverge substantially. Treat this as a *user-authorized methodological decision*, **not** as independent ERA5 confirmation.
2. **2016-12-06 extreme precipitation: redistribute 2016-12-06 tower daily total of 44.724 mm** across that calendar day's 48 half-hours using same-labeled FLUXNET companion ERA5 `P_ERA` fractions. The Stage24 IRIDIS operator log confirms reconstructed total 44.724 mm, unchanged daily cumulative amount. This is time-distribution modeling, **not** an observational confirmation that the 43.382 mm isolated value was a true half-hour accumulation.
3. **28 rain HOLD days: KEEP ORIGINAL, ACCEPTED BY OPERATOR.** ERA5 precipitation is zero on those days; do not fabricate denominators or arbitrarily distribute a combined 25.140 mm (maximum single day 3.350 mm). Retain explicit provenance and record these as accepted exceptions, not outstanding blocking tasks.
4. **Targeted temperature/VPD repairs: keep Stage21 and Stage23 approved edits.** Stage21 applied 73 targeted paired or bounded edits; Stage23 added 44 half-hour boundary edits. Stage23 reports three `BOUNDED` scopes, zero unresolved scopes, and maximum connection temperature differences of 1.437, 3.562 and 3.462 degrees C respectively. The 2006 extension uses companion ERA5 TA + validated adjacent QC1 median offset 0.852 C; VPD remains from the selected input. The 2019 and 2023 extensions use paired companion ERA5 TA/VPD, with consistent QBOT.
5. **Low RH below 5% is NOT an automatic rejection condition.** Retain original tower records when original data quality and consistency support them, even for RH below 5%. Stage24 notes 412 residual low-RH rows, **293 having both original tower TA_F_QC=0 and VPD_F_QC=0**. QC0 on its own is not proof of physical validity; the remaining 119 need source/QC context if full scientific signoff is required. Do not auto-replace the 412 by ERA5 based solely on RH.

## Evidence and outputs

- Successful Stage21 provisional result:
  `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage21_20261026T011416Z`
  — 334 same-day rain redispersions; 28 ERA-zero accepted exceptions.
- Successful Stage23 provisional result:
  `/iridisfs/home/ly3n24/ES_LJu_stage23_20261026T013605Z`
  — 27 + 9 + 8 new temperature-boundary replacements; zero unresolved boundary scopes.
- Successful Stage24 provisional result:
  `/iridisfs/home/ly3n24/ES_LJu_stage24_20261026T023307Z`
  — operator terminal log reports Stage24 SHA/half-hour timeline PASS, 2016 daily 44.724 mm conserved, 2013 untouched, 28 exceptions untouched; Stage23 meteorological columns unchanged.
- Exact Stage24 isolated candidate file:
  `/iridisfs/home/ly3n24/ES_LJu_stage24_20261026T023307Z/ES-LJu_stage24_full21yr_provisional_candidate.csv`

## Status and remaining gates

**Meteorological candidate generated and main specific corrections completed**; the Stage24 result is not the currently selected live 21-year DATM NetCDF and has not been copied into case streams, nor submitted to Slurm. Do not label the operational simulation as updated until the 21-year NetCDF conversion, full 21-year QA, CDEPS stream provenance verification, and explicit case switch have been performed and recorded.

The remaining 119 low-RH half-hour original source quality combinations are an optional/final QA gate **if a publication-grade all-records clearance is requested**, not a reason to undo the user's instruction to preserve sound low-RH observations. Any current other science concerns (e.g. PFT/site representativeness) are separate from precipitation/operator repair.

**Timestamps/accumulation-period caveat**: The precipitation redistribution uses identical FLUXNET half-hour labels and same-calendar-day ERA weights. The original precipitation gauge's accumulation-day convention and station-local timezone have not been independently established. Retain this caveat in scientific methods.

This note documents the user's decisions; it does not claim changes to the HPC files.
