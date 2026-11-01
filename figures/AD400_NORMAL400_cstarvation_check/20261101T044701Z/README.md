# Carbon-starvation check: FATES formula vs history output

cmort = scalar × max(0, (upthresh − storage/leafC) / upthresh) (linear model); monthly means of a daily, per-cohort process, so timing and size should agree, not exact values.

- [CS_12_DE-Hai_BDT_mature.png](CS_12_DE-Hai_BDT_mature.png)
- [CS_12_DE-Obe_NET.png](CS_12_DE-Obe_NET.png)
- [CS_12_FI-Sod_NET.png](CS_12_FI-Sod_NET.png)
- [CS_12_all_cases_scatter.png](CS_12_all_cases_scatter.png)

| Case | PFT | observed mean (yr-1) | predicted mean | r | slope | storage/leafC min / mean | months below threshold | cstarv model | leafresp model |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| DE-Obe_NET | 2 needleleaf_evergreen_extratrop_tree | 0.0435 | 0.0402 | 0.996 | 1.04 | 0.68 / 1.03 | 0.383 | linear | ryan1991 |
| FI-Sod_NET | 2 needleleaf_evergreen_extratrop_tree | 0.156 | 0.152 | 1 | 1.02 | 0.32 / 0.801 | 0.663 | linear | ryan1991 |
| DE-Hai_BDT_mature | 6 broadleaf_colddecid_extratrop_tree | 0.331 | 0.00602 | 0.145 | 6.12 | 0.682 / 2.4 | 0.0783 | linear | ryan1991 |
