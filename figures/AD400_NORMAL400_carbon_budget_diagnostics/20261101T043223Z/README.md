# Carbon budget diagnostics: why the needleleaf PFT cannot grow

Per-plant and per-leaf carbon budget for single-PFT nocomp sites, carbon use shares, winter reserve,
and the PFT parameters that differ between the focal PFTs. Screening numbers from history output.

- [CB_09_trajectories.png](CB_09_trajectories.png)
- [CB_10_seasonal.png](CB_10_seasonal.png)
- [CB_11_carbon_use.png](CB_11_carbon_use.png)
- [parameter_differences.csv](parameter_differences.csv)

| Case | PFT | plants/ha (first→last 5 y) | g C/plant | GPP/kg leaf C JJA | MR/kg leaf C JJA / DJF | MR/GPP | CUE | winter reserve | dbh_init |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| DE-Obe_NET (DE-Obe_B03_FIXNC_AD400_DIAG50) | 2 needleleaf_evergreen_extratrop_tree | 1.79e+03 → 324 | 309 → 2.27e+03 | 24 | 10.2 / 3.75 | 0.551 | 0.393 | 6.36 | .false. |
| FI-Sod_NET (FI-Sod_B01_FIXNC_AD400_DIAG50) | 2 needleleaf_evergreen_extratrop_tree | 1.43e+03 → 0.69 | 248 → 989 | 25 | 8.9 / 2.74 | 0.557 | 0.375 | 3.84 | .false. |
| DE-Hai_BDT_seedling (DE-Hai_B01_FIXNC_AD400_DIAG50) |  | – → – | – → – | – | – / – | – | – | – | FileNotFoundError: No archived history: /scratch/ly3n24/CTSM |
| DE-Hai_BDT_mature (DE-Hai_B01_FIXNC_NORMAL400) | 6 broadleaf_colddecid_extratrop_tree | 9.23e+03 → 9.2e+03 | 7.47e+03 → 6.73e+03 | 89 | 11.6 / – | 0.171 | 0.735 | 4.81 | .false. |
