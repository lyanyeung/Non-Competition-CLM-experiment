# Carbon-starvation check: FATES formula vs history output

cmort = scalar × max(0, (upthresh − storage/leafC) / upthresh) (linear model); monthly means of a daily, per-cohort process, so timing and size should agree, not exact values.

- [CS_12_CZ-Stn.png](CS_12_CZ-Stn.png)
- [CS_12_DE-Hai_ref.png](CS_12_DE-Hai_ref.png)
- [CS_12_DE-Lnf.png](CS_12_DE-Lnf.png)
- [CS_12_DE-Obe_A.png](CS_12_DE-Obe_A.png)
- [CS_12_DE-Obe_B.png](CS_12_DE-Obe_B.png)
- [CS_12_DE-Obe_C.png](CS_12_DE-Obe_C.png)
- [CS_12_DE-Obe_D.png](CS_12_DE-Obe_D.png)
- [CS_12_DE-Obe_ctrl.png](CS_12_DE-Obe_ctrl.png)
- [CS_12_FI-Sod_A.png](CS_12_FI-Sod_A.png)
- [CS_12_FI-Sod_B.png](CS_12_FI-Sod_B.png)
- [CS_12_FI-Sod_C.png](CS_12_FI-Sod_C.png)
- [CS_12_FI-Sod_D.png](CS_12_FI-Sod_D.png)
- [CS_12_FI-Sod_ctrl.png](CS_12_FI-Sod_ctrl.png)
- [CS_12_all_cases_scatter.png](CS_12_all_cases_scatter.png)

| Case | PFT | observed mean (yr-1) | predicted mean | r | slope | storage/leafC min / mean | months below threshold | cstarv model | leafresp model |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| DE-Obe_ctrl | 2 needleleaf_evergreen_extratrop_tree | 0.0435 | 0.0402 | 0.996 | 1.04 | 0.68 / 1.03 | 0.383 | linear | ryan1991 |
| FI-Sod_ctrl | 2 needleleaf_evergreen_extratrop_tree | 0.156 | 0.152 | 1 | 1.02 | 0.32 / 0.801 | 0.663 | linear | ryan1991 |
| DE-Obe_A | 2 needleleaf_evergreen_extratrop_tree | 0 | 0 | – | – | 1.88 / 2.23 | 0 | linear | ryan1991 |
| DE-Obe_B | 2 needleleaf_evergreen_extratrop_tree | 0 | 0 | – | – | 0.68 / 1.03 | 0 | linear | ryan1991 |
| DE-Obe_C | 2 needleleaf_evergreen_extratrop_tree | 0.0546 | 0.0124 | 0.743 | 2.22 | 0.803 / 1.08 | 0.245 | linear | ryan1991 |
| DE-Obe_D | 2 needleleaf_evergreen_extratrop_tree | 0.0623 | 0 | – | – | 1.76 / 2.21 | 0 | linear | ryan1991 |
| FI-Sod_A | 2 needleleaf_evergreen_extratrop_tree | 0 | 0 | – | – | 1.51 / 2 | 0 | linear | ryan1991 |
| FI-Sod_B | 2 needleleaf_evergreen_extratrop_tree | 0.0332 | 0.0292 | 0.997 | 1.09 | 0.319 / 0.802 | 0.248 | linear | ryan1991 |
| FI-Sod_C | 2 needleleaf_evergreen_extratrop_tree | 0.103 | 0.1 | 0.999 | 1.01 | 0.431 / 0.912 | 0.507 | linear | ryan1991 |
| FI-Sod_D | 2 needleleaf_evergreen_extratrop_tree | 0.00151 | 0 | – | – | 1.47 / 2.07 | 0 | linear | ryan1991 |
| CZ-Stn | 6 broadleaf_colddecid_extratrop_tree | 2.79 | 0.00759 | 0.0277 | 3.18 | 0.716 / 2.94 | 0.0568 | linear | ryan1991 |
| DE-Lnf | 6 broadleaf_colddecid_extratrop_tree | 0.48 | 0.00885 | 0.0938 | 2.77 | 0.639 / 2.06 | 0.0732 | linear | ryan1991 |
| DE-Hai_ref | 6 broadleaf_colddecid_extratrop_tree | 0.331 | 0.00602 | 0.145 | 6.12 | 0.682 / 2.4 | 0.0783 | linear | ryan1991 |
