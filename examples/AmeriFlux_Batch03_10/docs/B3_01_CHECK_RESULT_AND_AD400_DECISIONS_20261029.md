# AmeriFlux Batch03 — B3_01 full-record check (PASS 10/10) and AD400 decisions, 2026-10-29

Script: `scripts/B3_01_direct_AD400_FIXNC_80x5.py` (commit dfe4c54, sha256 d9640220…). `check` run on IRIDIS6 08:1x UTC: **CHECK PASS 10/10** (read only).

User decisions (2026-10-29): FIXNC arm only; direct AD400 80 × 5 years (one case.submit, RESUBMIT=79, no AD5 smoke); US-Me2 forcing 2002–2022, all years.

| site | forcing source | years | step | UTC | ZBOT m | FATES profile → PFT % | CO2 | DATM RH>100 clamped | FSDS–TOA lag min |
|---|---|---|---|---|---|---|---|---|---|
| US-Kon | Stage14T May26 final | 2004–2019 | 30 | −6 | 3 | DEFAULT14: cool C3 10, C4 90 | 376.95 | 4099 | +10.5 |
| US-MMS | Stage14C 16H isolated (HR) | 1999–2023 | 60 | −5 | 46 | DEFAULT14: BDT cold-decid 100 | 367.79 | 5473 | +4.0 |
| US-Me2 | **new** FULLSET + CL05 122 EMP + CL07 243 ERA_E_CAL | 2002–2022 | 30 | −8 | 32 | HYDRO_SHRUB: NET 90, hydro shrub 5, evergreen shrub 5 | 372.58 | 6611 | −10.0 |
| US-Me6 | CL03 | 2010–2025 | 30 | −8 | 14.2 | HYDRO_SHRUB: NET 80, hydro shrub 5, C3 15 | 388.75 | 4900 | +2.8 |
| US-MOz | Jan09 49QC1 two-reanalysis | 2004–2021 | 30 | −6 | 30.48 | DEFAULT14: NET 10, BDT 90 | 376.95 | 3475 | +2.7 |
| US-Mpj | Stage13O 20HH ERA RH | 2008–2025 | 30 | −7 | 8.2 | DEFAULT14: NET 60, C4 20, bare 20 | 385.02 | 4871 | −5.6 |
| US-MtB | MTB04 | 2009–2024 | 30 | −7 | 31 | DEFAULT14: NET 100 | 386.50 | 1935 | +13.1 |
| US-NC2 | Stage11q auto9 | 2005–2025 | 30 | −5 | 23 | DEFAULT14: NET 90, BDT 10 | 378.98 | 3770 | +3.8 |
| US-NR1 | CL03 (from 1999) | 1999–2025 | 30 | −7 | 21.5 | DEFAULT14: NET 100 | 367.79 | 28645 | −16.2 |
| US-NR3 | nr3_10 v2 MAIN | 2007–2024 | 30 | −7 | 3 | DEFAULT14: arctic C3 80, bare 20 | 382.90 | 11711 | +12.5 |

All sites: complete NOLEAP timeline, zero NaN, hard ranges pass, TBOT = TA_USE + 273.15 and QBOT closure exact (0 failures), e > 0 everywhere, PSRF within 1.2 % of the barometric value for the BIF elevation, FSDS diurnal centroid within ±17 min of top-of-atmosphere after the UTC shift (clock confirmed), soil L1–L5 means equal the 50-site register, PFT host × map equals the register FATES percentages.

ZBOT judgement calls: US-Me2 32 m (32 m 2002–2015-09, 33 m afterwards; the 5.34 m post-burn tower from 2022-08-25 is not represented); US-NC2 23 m (TA_1_1_1 from 2012-03-29, ~65 % of the record; 18.5 m before).

Upstream guard files (`INCOMPLETE_DO_NOT_USE_FOR_DATM_OR_SPINUP` / `NOT_APPROVED_*`) exist in the Kon, MMS, Me6, MOz, MtB, NC2, NR1, NR3 shadow folders. Per the user's AD400 decision these shadows are used as **research forcing**; the markers are not removed and are recorded in each case ledger.

DATM clamp: rows with e above the DATM saturation (over ice below 0 °C) are clamped by DATM to RH 100 %; counted above, values not changed in the files.

## Open science notes (not blockers for AD400; review before Normal400 / evaluation)

- US-Kon annual P 160 mm (2012), 295 mm (2011): far below the Konza climate (~830 mm); probable gauge gaps filled as zero.
- US-NR3 annual P 2009–3370 mm: high for alpine Niwot Ridge; check the P_F source/QC (blowing-snow overcatch or ERA fill).
- US-Me2 2002 P 204 mm (record start) and 2022 mean SW 113 W m-2 (post-fire tower period) are outliers.
- US-Me6 several years below 200 mm P.

## Update 2026-10-29 09:05 UTC — precipitation/SW/ERA repair (metfix_v1) and AD400 submitted

Audit `B3_02` and ERA alignment `B3_04` showed dead-gauge months recorded as measured zeros, an ERA-only NR3 precipitation 3 × the BIF MAP, and a broken US-Me2 FULLSET ERA (TA r 0.57, SW 13 % of tower, no consistent lag) that had filled every Me2 QC2 row. The other nine sites' ERA5 are aligned (TA r 0.87–0.99, day lag 0, SW ratio 0.95–0.97). User approved the predeclared rules ("按照你的建议").

New versioned forcing shadows `science_trials/b3_<SITE>_metfix_v1/` (base shadows unchanged; B3_01 uses them only after receipt + base-sha verification):

| site | rules | annual P mean before → after (BIF MAP) | notes |
|---|---|---|---|
| US-Kon | R1 19 months, R3 1 month | 713 → 792 (867) | 2012 160 → 240, 2016 442 → 783; 2009-01 SW 16 → 104 |
| US-MMS | R1 5 | 1097 → 1106 (1032) | |
| US-Me2 | B3_05: Me6-donor R5 / own-climatology R6 for every ERA-filled row; R1' 2 months vs Me6 | 475 → 480 | 2022 SW 113 → 184; donor beats climatology for all variables (TA MAE 2.4 vs 4.1 °C, SW r 0.968); 2002 P 204 mm kept (no reference) |
| US-Me6 | R1 8 | 320 → 347 (494) | |
| US-MOz | R1 5 | 902 → 913 (986) | |
| US-Mpj | R1 2, R3 1 | 361 → 364 (385) | |
| US-MtB | R1 2 | 588 → 596 (790) | |
| US-NC2 | R1 8 | 1226 → 1258 (1320) | 2022 569 → 954 |
| US-NR1 | R1 2 | 684 → 688 (800) | |
| US-NR3 | R2 × 0.3198 | 2764 → 884 (884) | no measured P at NR3 |

Rules: R1 month with ≥ 90 % QC0, ERA > 25 mm, tower < 25 % of ERA → P_ERA; R2 no measured P and mean > 2 × MAP → scale to MAP; R3 SW month ≥ 90 % QC0, SW < 75 % of ERA → SW_ERA; HIGH months kept. Scripts: `B3_02` (audit), `B3_03` (R1–R3), `B3_04` (ERA alignment), `B3_05` (Me2).

B3_01 check after repair: **PASS 10/10**. Prepare: 10/10 cases verified. Stack guard PASS (unlimited, PropagateResourceLimits=ALL). **Submitted 2026-10-29 ~09:05 UTC, FIXNC direct AD400 80 × 5 (RESUBMIT 79):**

| site | case | first run / archive job | years |
|---|---|---|---|
| US-Kon | US-Kon_AMF_B03_FIXNC_AD400_DIRECT | 4758042 / 4758043 | 2004 → 2404 |
| US-MMS | US-MMS_AMF_B03_FIXNC_AD400_DIRECT | 4758044 / 4758045 | 1999 → 2399 |
| US-Me2 | US-Me2_AMF_B03_FIXNC_AD400_DIRECT | 4758046 / 4758047 | 2002 → 2402 |
| US-Me6 | US-Me6_AMF_B03_FIXNC_AD400_DIRECT | 4758048 / 4758049 | 2010 → 2410 |
| US-MOz | US-MOz_AMF_B03_FIXNC_AD400_DIRECT | 4758050 / 4758051 | 2004 → 2404 |
| US-Mpj | US-Mpj_AMF_B03_FIXNC_AD400_DIRECT | 4758052 / 4758053 | 2008 → 2408 |
| US-MtB | US-MtB_AMF_B03_FIXNC_AD400_DIRECT | 4758054 / 4758055 | 2009 → 2409 |
| US-NC2 | US-NC2_AMF_B03_FIXNC_AD400_DIRECT | 4758056 / 4758057 | 2005 → 2405 |
| US-NR1 | US-NR1_AMF_B03_FIXNC_AD400_DIRECT | 4758058 / 4758059 | 1999 → 2399 |
| US-NR3 | US-NR3_AMF_B03_FIXNC_AD400_DIRECT | 4758060 / 4758061 | 2007 → 2407 |

Next: `B3_01 audit-first5` after the first 5-year segment (restart at start+5, spinup_state=2), `status` while running, `audit-ad400` at the end, then Normal400.
