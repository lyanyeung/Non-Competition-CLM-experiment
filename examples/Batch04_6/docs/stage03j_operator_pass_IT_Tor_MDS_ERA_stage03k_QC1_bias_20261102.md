# ICOS Batch04 — Stage03J operator confirmed official original MDS/ERA source selection; Stage03K MDS relative-bias scope (2026-11-02)

## Actual Stage03J PASS on IRIDIS6

Operator source-pinned, Python syntax PASS and self-test PASS for Stage03J, then successfully verified original native network product against the 54 previously selected half-hour source context rows of the **six** IT-Tor large temperature changes. `MDS_SOURCE_FIELDS_MISSING []`: original `TA_F_MDS`, `TA_F_MDS_QC`, `VPD_F_MDS`, `VPD_F_MDS_QC` were all available.

**Every one of six observed QC1↔QC2 source transitions passed all exact checks**:
- Source `TA_F_QC=1` selects `TA_F_MDS`; source `TA_F_MDS_QC=1` at those six QC1 boundaries
- Source `TA_F_QC=2` selects packaged `TA_ERA`
- Analogous consolidated VPD choices: QC1 uses `VPD_F_MDS` and QC2 uses `VPD_ERA`
- The old Stage28 selected forcing equals its original source TA/VPD by the earlier Stage03F/H numerical audits; no new meteorology edits were introduced here
- QC1 `TA_F - TA_ERA` offsets were **−12.403, −12.369, −13.441, −14.095, −13.024, −6.811°C** across six handoffs; QC2 offsets were **exactly 0°C**

The output is consistent with actual official FLUXNET variable construction. `QC1` means **MDS gapfill** and `QC2` **downscaled ERA gapfill** rather than two equally independent direct tower instrument records. **QC2 equals the same source-packaged ERA by definition**, not new independent evidence. More precise question is **why the MDS gap-fill T can be much colder than packaged ERA at six handoff boundaries**, not whether Stage28 corrupted original QC metadata.

Actual PRIVATE reports, never commit original field values:
```
/home/ly3n24/ICOS_Batch04_stage03j_vzDUtipV/results/stage03j_IT_Tor_6_handoffs_MDS_ERA_consolidation_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03j_vzDUtipV/results/stage03j_IT_Tor_54_context_MDS_ERA_fields_PRIVATE.csv
```

## Important unresolved scientific distinction

Six strongly negative QC1 handoff offsets **do not prove that all 558 QC1 values inside the 1,458-HH run, or the separate 29 QC1 values, are biased**. Nor do they establish that packaged ERA represents actual microclimate at the ICOS tower, MDS donor availability, ground sensors or correct time zone. Before proposing any repair or AD5, quantify how pervasive the mismatch is in the previously known QC1-only *science hold* scope, then seek **independent** station/ERA5-Land and original sensor evidence as necessary. Do not use one historical trial under Stage26 to justify an unsourced full-length ERA substitution. IT-Tor original soil `ORGANIC=0` across all ten layers remains an independent surface/soil science hold.

## Stage03K: only original 558+29 QC1 MDS and companion QC2 records

[Stage03K source rule/bias distribution report](../scripts/03k_IT_Tor_QC1_MDS_minus_packaged_ERA_two_runs_READONLY.py) requires the actual passed Stage03F 2025 Oct–Nov original QC1/2 episode manifest and Stage03J original MDS/ERA source-confirmation JSON. It validates the original two exact protected runs:
- **LONG_1458:** 2025-10-21 02:30 to 2025-11-20 11:00, **558 QC1 MDS + 900 QC2 ERA**
- **SHORT_29:** 2025-11-21 17:30 to 2025-11-22 07:30, **29 QC1 MDS + 0 QC2**

It streams one original IT-Tor source network CSV once to extract **only 1,487 original QC1/QC2 half-hours and the four immediately adjacent QC0 anchors**. It does **not** read any Stage28 selected CSV, yearly DATM NC, other station or broad years; it checks the official source branch selection `TA_F/VPD_F` equals MDS/ERA per QC, and whether all QC1 `*_F_MDS_QC` codes remain 1. It reports:
- QC1 **`TA_F_MDS - TA_ERA`** min/p05/median/p95/max/mean and counts below **−5°C** and **−10°C**, **separately for 558 and 29** to test whether the six very cold handoff examples represent a wider pattern
- QC1 **`VPD_F_MDS - VPD_ERA`** relative distributions (hPa, same explicit uncertainty)
- Maximal contiguous QC1 subrun count/length, and original source branch consistency flags
- A private QC1 subinterval CSV with dates and bias summaries, not an approved replacement ledger

**Method limitation:** both MDS and packaged downscaled ERA are products of the same broader ecosystem data-processing system. Their difference is not a scientifically independent accuracy score. The old [Stage26 policy](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage26/26_three_site_MET_conservative_trial.py) only considered very short QC1/2 full-run bracketing and explicitly retained long-run uncertainty. Do not automatically replace any QC1 interval; apply separate science approval only if independent original observation/neighbour/site validation supports it.

This step **creates only new private HOME JSON and CSV**, keeps the previous Stage03B–03J original results immutable, and does not write NetCDF, source forcing, CIME, FATES mapping, PFT surfaces, Slurm or submit AD5. Model source science, soil and independent rainfall timing holds are not lifted by this stage.
