# ICOS Batch04: Stage03G actual IT-Tor physics QC results and six-jump Stage03H next action (2 November 2026)

## Actual operator-verified Stage03G result

The operator source-SHA verified Stage03G, confirmed `FULL PYTHON SYNTAX PASS` and `STAGE03G SELF-TEST PASS`, and completed the targeted IT-Tor physical screen on IRIDIS6. No source/selected forcing, 74 annual DATM NetCDF, CIME, candidate PFT point-surface, FATES parameter or Slurm model job was changed.

| Original QC1-or-2 interval | Original QC class pairs | Selected reconstructed RH (water saturation) | Internal T steps >5°C | QC0 left/right step |
|---|---|---|---:|---|
| **LONG_1458**: 2025-10-21 02:30 – 2025-11-20 11:00 | (QC1,QC1) **558 HH**, (QC2,QC2) **900 HH** | **37.7128% to 99.0004%** | **6** | left **+1.355°C / +0.472 hPa VPD**, right **−0.195°C / −0.258 hPa VPD** |
| **SHORT_29**: 2025-11-21 17:30 – 2025-11-22 07:30 | (QC1,QC1) **29 HH** | **41.5309% to 59.5545%** | **0** | left **+2.384°C / −0.136 hPa VPD**, right **−0.325°C / −0.020 hPa VPD** |

Stage03G's `SCREENS` printed only `screened` (1,458 and 29 HH) and six `inside_T_step_gt5C` for LONG_1458. The original script also checked negative VPD/derived RH, RH<1%, QBOT–PSRF–humidity closure (diagnostic threshold 1e-5 kg/kg), and internal VPD jumps >8 hPa; these flags were not printed, which supports **no triggered flags within those scripted categories**. This is NOT proof of direct in-situ RH observation accuracy, below-freezing ice saturation realism, original QC1/2 gap-filling reliability, or independent ERA evidence.

All original source `TA_F`, `VPD_F` and Stage28 selected `TA_USE`, `VPD_USE` were numerically equal in **both** runs, including all **558+900+29=1,487 QC1/QC2** half-hours. Source `TA_ERA/VPD_ERA` fields were available for all 1,487 HH. Those fields can be related to network gapfilling; **their presence is not independently corroborated ERA5-Land observation proof**.

This means the inherited selected Stage28 forcing can be maintained **unchanged pending science assessment**, but **there is no unconditional production/scientific model release**: the 1,458-HH source fill and its six temperature jumps still need interpretation. Crucially, there is no basis for bulk ERA replacement or data reprocessing on the present observations.

## Exact private Stage03G report paths

```
/home/ly3n24/ICOS_Batch04_stage03g_vz3cfQig/results/stage03g_IT_Tor_two_runs_physics_anchors_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03g_vz3cfQig/results/stage03g_IT_Tor_two_runs_boundary_values_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03g_vz3cfQig/stage03g_console.log
```

## Next Stage03H: only six internal >5°C step transitions

[Stage03H read-only six-jump original-source vs Stage28 and packaged ERA investigation](../scripts/03h_IT_Tor_1458HH_six_internal_T_jumps_source_ERA_context_READONLY.py) takes the original Stage03G private science-HOLD JSON and the existing Stage03B source SHA register, confirms exactly six `inside_T_step_gt5C` jumps inside **2025-10-21 02:30 to 2025-11-20 11:00**. It hashes and pins the historical selected Stage28 CSV and reads only IT-Tor original source + selected CSV data for this **single 1,458 HH** interval and ±2-hour bounds, in a streaming pass over each CSV.

For each jump, the script names the **second half-hour timestamp** and lists the signed T and VPD differences, original network-product QC codes on both sides, whether the original source equals selected Stage28, packaged `TA_ERA` T-step comparison, derived water saturation RH, and individual ±2-hour context values. All per-HH values are written only to a new **private HOME** directory. Source-packaged ERA is **not** independent ERA5-Land evidence, and a >5°C jump is a review flag, not proof a measured observation is wrong.

Inputs:
- `/home/ly3n24/ICOS_Batch04_stage03g_vz3cfQig/results/stage03g_IT_Tor_two_runs_physics_anchors_PRIVATE.json`
- `/home/ly3n24/ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json`

Private outputs:
- `stage03h_IT_Tor_6_internal_T_jumps_PRIVATE.json`
- `stage03h_IT_Tor_6_jumps_2h_neighborhood_PRIVATE.csv`

Do not commit original sensor values or derived per-event data to this public GitHub repo. No edits, trial replacements, Slurm submission, 74-year NC scan, soil-PFT reconstruction or automatic release. Future scientific decisions should only concern these six exact event times, any original independent corroboration, and the separate original IT-Tor ten-soil-layer `ORGANIC=0` science hold.

## Other four-site priorities

- DE-Gri: 49 old MDS source episodes remain protected and *unapproved*, despite Stage28 numerical hard QC PASS and the 49/49 original-source lineage checks
- DE-RuR 2012-07-27 and ES-Agu 2018-09-15: each original `P_F` versus Stage28 `PRECTmms*1800` had 48/48 numeric matches on the focus date, but **original rain-gauge accumulation interval and site-local timestamp** are still unverified
- Source period and PFT surface were already selected and SHA-verified for DE-Gri/DE-RuR/IT-Tor/ES-Agu; continue to avoid new isolated AD5 until surface+soil+source science and active case binding gates have passed
