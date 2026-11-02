# BTRAN and soil diagnostics: collapsing needleleaf re-runs vs living references

BTRAN is recomputed per layer with the FATES/CLM non-hydro formula from liquid water, ice, soil temperature,
fine-root distribution (FATES_FROOTC_SL) and the PFT's smpso/smpsc. JJA = growing season. Screening numbers.

- [All cases comparison](ALL_CASES_08_btran_soil_comparison.png)

| Case | Years | PFT | BTRAN JJA model | estimate (plants) | canopy cover | estimate × cover | roots 90% above (m) | most limiting (JJA) | check | Figures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| CZ-Stn (CZ-Stn_B03_FIXNC_AD400_DIAG50) | 2010-2059 | 6 broadleaf_colddecid_extratrop_tree | 0.262 | 0.3 | 0.267 | 0.266 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | estimate x canopy cover matches model BTRAN: plants are not water-limited; history BTRAN is diluted by bare soil between crowns (BTRAN=0 there) | [time series](CZ-Stn/CZ-Stn_06_btran_soil_timeseries.png) [profiles](CZ-Stn/CZ-Stn_07_btran_soil_profiles.png) [inventory](CZ-Stn/CZ-Stn_inventory.txt) |
| DE-Lnf (DE-Lnf_B03_FIXNC_AD400_DIAG50) | 2002-2051 | 6 broadleaf_colddecid_extratrop_tree | 0.249 | 0.28 | 0.249 | 0.249 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | estimate x canopy cover matches model BTRAN: plants are not water-limited; history BTRAN is diluted by bare soil between crowns (BTRAN=0 there) | [time series](DE-Lnf/DE-Lnf_06_btran_soil_timeseries.png) [profiles](DE-Lnf/DE-Lnf_07_btran_soil_profiles.png) [inventory](DE-Lnf/DE-Lnf_inventory.txt) |
| DE-Hai_ref (DE-Hai_B01_FIXNC_NORMAL400) | 2750-2799 | 6 broadleaf_colddecid_extratrop_tree | 0.975 | 0.984 | 0.996 | 0.98 | 0.92 | no soil limitation in rooted layers (all factors >= 0.95) | estimate x canopy cover matches model BTRAN: plants are not water-limited; history BTRAN is diluted by bare soil between crowns (BTRAN=0 there) | [time series](DE-Hai_ref/DE-Hai_ref_06_btran_soil_timeseries.png) [profiles](DE-Hai_ref/DE-Hai_ref_07_btran_soil_profiles.png) [inventory](DE-Hai_ref/DE-Hai_ref_inventory.txt) |
