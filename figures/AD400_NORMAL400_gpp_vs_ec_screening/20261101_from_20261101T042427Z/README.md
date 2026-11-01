# FATES vs EC tower GPP — 75-site screening

Source figures: `figures/AD400_NORMAL400/20261101T042427Z_88_5996d9c0` (last complete NORMAL400 forcing cycle vs EC monthly means).

`gpp_vs_ec_all_sites.csv` columns:
- `FATES_GPP`: mean of the FATES monthly GPP line, read from each figure.
- `bias`: model − EC bias printed in the figure title (paired months).
- `EC_GPP` = `FATES_GPP − bias`.
- `ratio` = FATES / EC. Classes: A < 0.5, B 0.5–0.8, C 0.8–1.25, D > 1.25.
- `composition`: FATES PFT % of natural vegetated land, from the PFT registers in the repo.
- `needleleaf_pct_of_vegetation`: NET + NDT as % of vegetated (non-bare) land.

Checking against the 07 EC means: median relative difference −0.1%, 90th-percentile absolute difference 3.7%.
US-NR3 has an EC mean ≈ 0 (bias +1.73, R² −5.8), so no ratio is given; the EC record needs checking.

The interpretation is in `docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md`, section 10.

`site_flag`: US-CMW is `EXCLUDED_GROUNDWATER`. It is a riparian mesquite woodland where tower ET is 2.5 × precipitation, and a single-point CLM column cannot supply that water (docs section 11).
