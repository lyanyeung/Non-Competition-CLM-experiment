# Batch01 — four-site forest inventory follow-up, 2026-10-24

**Scientific evidence only. All production fixed-PFT surfaces remain HOLD.** Tree inventory and EC footprint percentages are not automatically CLM `PCT_NAT_PFT`.

| Site | Verified new inventory evidence | PFT conclusion | Remaining audit |
| --- | --- | --- | --- |
| BE-Vie | ESSD 2026 §2.1: within **70% cumulative EC footprint**, 2018 drone multispectral classification: spruce 38%, beech 36%, silver fir 14%, Douglas fir 9%, Scots pine 2%. 2019 extensive inventory independently provided tree heights. | **ENF=63%, DBF=36%, reported total=99%**. Remaining 1% may be rounding or unreported; do not normalize automatically. Different denominator from old stand figures DBF43%, ENF37%, other20%. | Verify classified-tree denominator, missing 1%, EC footprint seasonality, model area basis and PFT mapping. **FOOTPRINT_QUANTIFIED_CANDIDATE, not APPROVED.** |
| FR-Fon | GMD PHOREAU (2025) Appendix R used exhaustive winter 2006–2007 tree inventory from **9 × 1,000 m²** plots. Delpierre (2016) basal area: oak 79% DBF, hornbeam 18% DBF; miscellaneous <3% includes ENF pine and deciduous woods. | DBF at least 97% of reported *basal area*, ENF part unknown. | Obtain species-specific source inventory; plot basal area is not horizontal land area. |
| FR-Pue | GMD PHOREAU (2025) Appendix O: **12 × 100 m²** monitored plots; annual tree diameter since 2003, dense holm-oak coppice. | Mainly EBF; original 95% stand statistic not commensurate with >80% canopy cover or unverified alternate 90/10 EBF/DBF. | Retrieve inventory species list and check site/EC footprint. |
| FI-Sod | Finnish Meteorological Institute official forest station: Scots pine forest, **~2,100 stems/ha**, 80–180 year tree ages, ~12 m height. | Prior ENF pine 95%, unknown 5% tree types. | Retrieve species-resolved *tower stand* tree census; ground-layer lichen/moss/shrub percentages are not tree shares. |

## Sources

- BE-Vie, explicit 70% footprint percentages: https://essd.copernicus.org/articles/18/617/2026/essd-18-617-2026.html ; on-site inventory noted at https://deims.org/c4c1c0ca-5a43-4d19-ab50-34dad0af44e8
- FR-Fon & FR-Pue: https://gmd.copernicus.org/articles/18/7603/2025/ ; inventory archive for *European-scale* evaluation https://doi.org/10.5281/zenodo.15241618 is **not yet verified** as containing the specific FR-Fon/FR-Pue site plots; authors say certain local evaluation datasets must be requested from ICOS site PIs. FR-Fon tree basal-area figures https://nph.onlinelibrary.wiley.com/doi/10.1111/nph.13771
- FI-Sod: https://en.ilmatieteenlaitos.fi/ghg-sodankyla-forest
- WARNING: Grand Bois de Vielsalm reference forest report https://askafor.eu/wp-content/uploads/2021/09/BE-VIELSALM-english.pdf has **not been shown to overlap BE-Vie tower footprint**; its statistics must NOT be transferred.

No forcing, fsurdat, CIME cases, restart, or Slurm jobs changed.
