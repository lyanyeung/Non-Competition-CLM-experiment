# AmeriFlux Batch05 — forcing, point surfaces and FIXNC direct AD400 submission (2026-10-29)

Script `scripts/B5_01_direct_AD400_FIXNC_80x5.py` (commit 6902132, sha256 767ee322…) reusing the pinned AmeriFlux Batch03 `B3_01` (commit 9b25208) for QC, surfaces, FATES maps, forcing NetCDF, cases and submit. User decision: Batch05 runs the Batch03 pipeline, FIXNC, direct AD400 80 × 5 (RESUBMIT 79), no AD5 smoke.

## Forcing (new folders `experiments/NonCompetitionObserved22/AmeriFlux_Batch05_10/<SITE>/forcing_shadow_b05_v1/`)

Base: qcv5 conversion of the Stage05-sha-pinned release `*_F` variables. Then: Stage84 1,675 approved T/VPD overlay; Stage89 US-Whs 51 (merged); Stage104 56 HOLDs — 36 QC2 → scenario A (ERA5-Land RH at source T), 20 QC0 retained; Stage104 7 T risks — only US-Wkg 2025-09-10 13:00 (|source − bracket| 13.6 °C) replaced; R0 hard-range (US-WCr 1 LW row → ERA); B3_03 R1 dead-gauge months → P_ERA, R2 ERA-only P scaled to BIF MAP, R3 SW fault months → SW_ERA. ERA alignment gate passed at all ten sites (TA r 0.90–0.99, day lag 0, SW ratio 0.95–1.01; US-UMB FULLSET ERA is fine, unlike US-Me2).

| site | S84 | other | P/SW repairs | FSDS–TOA lag min |
|---|---|---|---|---|
| US-UiD | 0 | — | R2 × 0.268 (no measured P; ERA ≈ 3.7 × MAP) | +28.7 (note: possible 30-min label offset) |
| US-UMB | 23 | clock/coords fallback (no BIF): UTC−5, 45.5598/−84.7138, 234 m | R1 14 months, R3 1 | +1.3 |
| US-UMd | 15 | — | R2 × 0.243 (no measured P) | +5.0 |
| US-Var | 55 | — | R1 6 (gauge absent Jan–May 2000), R3 2 | +2.1 |
| US-Vcm | 474 | H56: 33 QC2 scenario A, 14 QC0 kept | R1 6 | −5.5 |
| US-Vcp | 582 | H56: 3 QC2 scenario A | R1 6 (incl. 2025-06..10 zeros) | −4.5 |
| US-WCr | 92 | H56: 6 QC0 kept; R0 1 LW | — | — |
| US-Whs | — | S89 51 | R1 1 | −3.9 |
| US-Wjs | 415 | — | R1 4 | −1.6 |
| US-Wkg | 19 | T7 1 | R1 3 | −4.9 |

All rows e > 0; B3_01 full QC PASS 10/10 (forcing-write), then admission `check` PASS 10/10.

## Surfaces, PFT, soil, ZBOT

CTSM `subset_data point` year-2000 surfaces created in `sites/MY_EC_SITE/<SITE>/subset_data_batch05_surf2000/`, then NATVEG100/CROP0 copies with the 50-site register host PFT (US-Whs/US-Wkg HYDRO_SHRUB private FATES map; US-Vcm static prefire ENF100) and the CLM10 soil table (US-Wkg L1–L5 = FINAL T1 BADM 68.8/12.8). ZBOT: UiD 4, UMB 46, UMd 32, Var 2, Vcm 23.9, Vcp 24 (2007–2019-04; 28.2 m afterwards), WCr 29.6, Whs 6, Wjs 10, Wkg 6 m.

## Submitted (stack guard PASS unlimited / PropagateResourceLimits=ALL)

| site | case | first run / archive job | years | CO2 |
|---|---|---|---|---|
| US-UiD | US-UiD_AMF_B05_FIXNC_AD400_DIRECT | 4758110 / 4758111 | 2008 → 2408 | 385.02 |
| US-UMB | US-UMB_AMF_B05_FIXNC_AD400_DIRECT | 4758112 / 4758113 | 2007 → 2407 | 382.90 |
| US-UMd | US-UMd_AMF_B05_FIXNC_AD400_DIRECT | 4758114 / 4758115 | 2007 → 2407 | 382.90 |
| US-Var | US-Var_AMF_B05_FIXNC_AD400_DIRECT | 4758116 / 4758117 | 2000 → 2400 | 368.96 |
| US-Vcm | US-Vcm_AMF_B05_FIXNC_AD400_DIRECT | 4758118 / 4758119 | 2007 → 2407 | 382.90 |
| US-Vcp | US-Vcp_AMF_B05_FIXNC_AD400_DIRECT | 4758120 / 4758121 | 2007 → 2407 | 382.90 |
| US-WCr | US-WCr_AMF_B05_FIXNC_AD400_DIRECT | 4758122 / 4758123 | 1999 → 2399 | 367.79 |
| US-Whs | US-Whs_AMF_B05_FIXNC_AD400_DIRECT | 4758125 / 4758126 | 2007 → 2407 | 382.90 |
| US-Wjs | US-Wjs_AMF_B05_FIXNC_AD400_DIRECT | 4758127 / 4758128 | 2007 → 2407 | 382.90 |
| US-Wkg | US-Wkg_AMF_B05_FIXNC_AD400_DIRECT | 4758133 / 4758134 | 2004 → 2404 | 376.95 |

Next: `python3 -B B5_01_direct_AD400_FIXNC_80x5.py audit-first5` after the first segment, `status` while running, `audit-ad400` at the end.
