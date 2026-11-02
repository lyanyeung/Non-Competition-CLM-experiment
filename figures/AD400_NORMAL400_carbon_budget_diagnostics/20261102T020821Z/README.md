# Carbon budget diagnostics: why the needleleaf PFT cannot grow

Per-plant and per-leaf carbon budget for single-PFT nocomp sites, carbon use shares, winter reserve,
and the PFT parameters that differ between the focal PFTs. Screening numbers from history output.

- [CB_09_trajectories.png](CB_09_trajectories.png)
- [CB_10_seasonal.png](CB_10_seasonal.png)
- [CB_11_carbon_use.png](CB_11_carbon_use.png)
- [parameter_differences.csv](parameter_differences.csv)

| Case | PFT | plants/ha (first→last 5 y) | g C/plant | GPP/kg leaf C JJA | MR/kg leaf C JJA / DJF | MR/GPP | CUE | winter reserve | dbh_init |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| DE-Obe_ctrl (DE-Obe_B03_FIXNC_AD400_DIAG50) | 2 needleleaf_evergreen_extratrop_tree | 1.79e+03 → 324 | 309 → 2.27e+03 | 24 | 10.2 / 3.75 | 0.551 | 0.393 | 6.36 | .false. |
| FI-Sod_ctrl (FI-Sod_B01_FIXNC_AD400_DIAG50) | 2 needleleaf_evergreen_extratrop_tree | 1.43e+03 → 0.69 | 248 → 989 | 25 | 8.9 / 2.74 | 0.557 | 0.375 | 3.84 | .false. |
| DE-Obe_A (DE-Obe_B03_FIXNC_AD400_FIXA50) | 2 needleleaf_evergreen_extratrop_tree | 1.95e+03 → 2.25e+03 | 336 → 2.54e+03 | 24.3 | 10.1 / 3.78 | 0.55 | 0.394 | 12.7 | .false. |
| DE-Obe_B (DE-Obe_B03_FIXNC_AD400_FIXB50) | 2 needleleaf_evergreen_extratrop_tree | 1.96e+03 → 2.64e+03 | 309 → 2.53e+03 | 24.4 | 10.1 / 3.75 | 0.546 | 0.398 | 6.27 | .false. |
| DE-Obe_C (DE-Obe_B03_FIXNC_AD400_FIXC50) | 2 needleleaf_evergreen_extratrop_tree | 2.04e+03 → 1.54e+04 | 686 → 7.85e+03 | 39 | 9.18 / 3.8 | 0.346 | 0.579 | 17.8 | .false. |
| DE-Obe_D (DE-Obe_B03_FIXNC_AD400_FIXD50) | 2 needleleaf_evergreen_extratrop_tree | 2.07e+03 → 1.2e+04 | 700 → 1.39e+04 | 37.9 | 9.09 / 3.81 | 0.362 | 0.565 | 29.5 | .false. |
| FI-Sod_A (FI-Sod_B01_FIXNC_AD400_FIXA50) | 2 needleleaf_evergreen_extratrop_tree | 1.88e+03 → 1.15e+03 | 273 → 788 | 25.2 | 8.93 / 2.87 | 0.59 | 0.346 | 8.37 | .false. |
| FI-Sod_B (FI-Sod_B01_FIXNC_AD400_FIXB50) | 2 needleleaf_evergreen_extratrop_tree | 1.79e+03 → 254 | 248 → 920 | 25 | 8.89 / 2.74 | 0.567 | 0.367 | 3.84 | .false. |
| FI-Sod_C (FI-Sod_B01_FIXNC_AD400_FIXC50) | 2 needleleaf_evergreen_extratrop_tree | 1.6e+03 → 331 | 442 → 3.64e+03 | 44.5 | 8.75 / 2.81 | 0.325 | 0.592 | 4.17 | .false. |
| FI-Sod_D (FI-Sod_B01_FIXNC_AD400_FIXD50) | 2 needleleaf_evergreen_extratrop_tree | 1.94e+03 → 1.61e+04 | 464 → 4.23e+03 | 42.2 | 8.25 / 2.89 | 0.361 | 0.558 | 8.73 | .false. |
| CZ-Stn (CZ-Stn_B03_FIXNC_AD400_DIAG50) | 6 broadleaf_colddecid_extratrop_tree | 3.89e+03 → – | 1.85e+03 → – | 107 | – / – | 0.161 | 0.743 | 4.94 | .false. |
| DE-Lnf (DE-Lnf_B03_FIXNC_AD400_DIAG50) | 6 broadleaf_colddecid_extratrop_tree | 3.82e+03 → – | 1.79e+03 → – | 104 | – / – | 0.156 | 0.747 | 5.08 | .false. |
| DE-Hai_ref (DE-Hai_B01_FIXNC_NORMAL400) | 6 broadleaf_colddecid_extratrop_tree | 9.23e+03 → 9.2e+03 | 7.47e+03 → 6.73e+03 | 89 | 11.6 / – | 0.171 | 0.735 | 4.81 | .false. |
