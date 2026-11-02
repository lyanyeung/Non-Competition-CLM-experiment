# ICOS Batch04 — Stage03H actual IT-Tor six-jump result and Stage03I source handoff review (2026-11-02)

## Confirmed operator Stage03H outcome

The operator SHA-verified the deployed code on IRIDIS6 and ran full Python syntax PASS, Stage03H self-test PASS and the complete read-only six-event source/Stage28/packaged-ERA audit. **Original forcing/74 annual NC/CIME/FATES/Slurm were not changed.**

All **six** >5°C 30-minute TA temperature jumps occur where the *original network-product* TA QC **changes between 1 and 2**, while the source-packaged ERA temperature is nearly stationary:

| Jump | Source-label second HH (2025) | Source and selected Stage28 T step (°C) | QC transition | Packaged TA_ERA step (°C) | VPD step (hPa) |
|---|---|---:|---|---:|---:|
| TJ1128 | 11-13 14:30 | **-12.440** | **2→1** | -0.037 | -4.516 |
| TJ1131 | 11-13 16:00 | **+11.959** | **1→2** | -0.410 | +3.532 |
| TJ1134 | 11-13 17:30 | **-14.312** | **2→1** | -0.871 | -3.515 |
| TJ1162 | 11-14 07:30 | **+13.963** | **1→2** | -0.132 | +2.348 |
| TJ1229 | 11-15 17:00 | **-13.142** | **2→1** | -0.118 | -0.789 |
| TJ1373 | 11-18 17:00 | **-6.937** | **2→1** | -0.126 | -1.496 |

Five of six jumps exceed 11°C and all six occur exactly at a QC1/QC2 transition. Both native network `TA_F` and Stage28 `TA_USE` **match at both sides of each transition**; so the selected forcing has faithfully inherited the discontinuities already present in the processed source product. The old Stage28 lineage is unmodified by these audits.

**Science interpretation:** this is strong *circumstantial evidence of a discontinuity at a source/gapfilling product handoff*, not proof that every QC1 or QC2 value is a bad *measured* observation. The QC meaning must be interpreted using the product source/variable documentation. `TA_ERA` is *packaged with the network product* and may underpin part of the filling process, so it **is not an independent ground-truth temperature observation or independent ERA5-Land validation**. An implausible step is a flag requiring source context, not automatic authorization to overwrite.

Operator's **PRIVATE** report files (do not commit any source numeric values):
```
/home/ly3n24/ICOS_Batch04_stage03h_fp6eibwz/results/stage03h_IT_Tor_6_internal_T_jumps_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03h_fp6eibwz/results/stage03h_IT_Tor_6_jumps_2h_neighborhood_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03h_fp6eibwz/stage03h_console.log
```

## Next Stage03I — only the existing 54 context rows

[Stage03I read-only handoff/packaged ERA offset review](../scripts/03i_IT_Tor_six_QC12_handoff_ERA_offset_existing_reports_READONLY.py) reads only the **saved Stage03H private JSON plus 54-record CSV**, not a single original FLUXMET, Stage28 or NetCDF source record. It checks original six event IDs, strict jump timestamps, QC1↔QC2 transitions, source/selected equality, and consistency of T/ERA step deltas with the existing context. Each event outputs **TA source minus packaged TA_ERA before and after the handoff**; organizes QC1-side and QC2-side discrepancies and the relative difference between them. This tests whether one QC class follows packaged ERA while the other is displaced; such a finding would help identify which *source family* needs further provenance checks.

Its label `QC1_QC2_HANDOFF_STEP_REVIEW_QC*_NEARER_PACKAGED_ERA` is a **hypothesis for science review**, never a one-sided data replacement verdict. It cannot by itself distinguish a physical local microclimate transition from heterogeneous fill methods, or provide independent tower, neighboring-station or ERA5-Land evidence. If both sides disagree with packaged ERA, it retains the same source uncertainty.

Only a new private HOME JSON and six-row CSV is written. There is **no new model/met forcing file, no automated interpolation or ERA replacement, no 74-NC reread, no source CSV scan, no FATES/PFT change, and no AD5/AD400 permission.** Existing scientific HOLDs remain for IT-Tor 1,458-HH mixed QC1/QC2 run, short 29-HH run, all-ten-layer soil `ORGANIC=0`, DE-Gri 49 MDS blocks and DE-RuR/ES-Agu precipitation timing. Stage03H itself has **completed successfully**; Stage03I must be syntax+self-tested and actually run before results can be reported.
