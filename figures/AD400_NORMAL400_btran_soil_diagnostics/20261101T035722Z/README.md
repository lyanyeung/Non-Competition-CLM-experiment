# BTRAN and soil diagnostics: collapsing needleleaf re-runs vs living references

BTRAN is recomputed per layer with the FATES/CLM non-hydro formula from liquid water, ice, soil temperature,
fine-root distribution (FATES_FROOTC_SL) and the PFT's smpso/smpsc. JJA = growing season. Screening numbers.

- [All cases comparison](ALL_CASES_08_btran_soil_comparison.png)

| Case | Years | PFT | BTRAN JJA model | estimate | veg. area | roots 90% above (m) | most limiting (JJA) | check | Figures |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| DE-Obe (DE-Obe_B03_FIXNC_AD400_DIAG50) | 2008-2057 | 2 needleleaf_evergreen_extratrop_tree | 0.0504 | 1 | 1 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | MISMATCH: estimate 1.00 vs model 0.05 | [time series](DE-Obe/DE-Obe_06_btran_soil_timeseries.png) [profiles](DE-Obe/DE-Obe_07_btran_soil_profiles.png) [inventory](DE-Obe/DE-Obe_inventory.txt) |
| FI-Sod (FI-Sod_B01_FIXNC_AD400_DIAG50) | 2001-2050 | 2 needleleaf_evergreen_extratrop_tree | 0.00814 | 0.999 | 1 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | MISMATCH: estimate 1.00 vs model 0.01 | [time series](FI-Sod/FI-Sod_06_btran_soil_timeseries.png) [profiles](FI-Sod/FI-Sod_07_btran_soil_profiles.png) [inventory](FI-Sod/FI-Sod_inventory.txt) |
| DE-Hai_ref (DE-Hai_B01_FIXNC_NORMAL400) | 2750-2799 | 6 broadleaf_colddecid_extratrop_tree | 0.975 | 0.984 | 1 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | estimate matches model BTRAN | [time series](DE-Hai_ref/DE-Hai_ref_06_btran_soil_timeseries.png) [profiles](DE-Hai_ref/DE-Hai_ref_07_btran_soil_profiles.png) [inventory](DE-Hai_ref/DE-Hai_ref_inventory.txt) |
| FI-Hyy_ref (FI-Hyy_B02_FIXNC_NORMAL400) | 2747-2796 | 6 broadleaf_colddecid_extratrop_tree | 0.0489 | 1 | 1 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | MISMATCH: estimate 1.00 vs model 0.05 | [time series](FI-Hyy_ref/FI-Hyy_ref_06_btran_soil_timeseries.png) [profiles](FI-Hyy_ref/FI-Hyy_ref_07_btran_soil_profiles.png) [inventory](FI-Hyy_ref/FI-Hyy_ref_inventory.txt) |
