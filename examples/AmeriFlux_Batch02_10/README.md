# AmeriFlux Batch02 (10 sites) — FATES fixed-biogeography / no-competition integration

**Started 2026-10-26. This is NOT European/ICOS `examples/Batch02_10`.** Exact AmeriFlux sites: US-BZS, US-CMW, US-EML, US-GLE, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, US-ICt.

## Status: source met is technically prepared, model completion is NOT 10/10

The independent [original AmeriFlux Batch02 source workflow](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10_Batch02) completed Stage95 **215 source-year NOLEAP NC files for the ten sites** (site original record lengths vary; 10/10 files structurally verified through Stage96). Those files **have not been adopted into ten validated CIME FIXNC cases**. Versioned 122 source-QC modifications and independent sources must remain immutable.

**Only US-GLE has a verified new CIME submission in the supplied operator logs**, and that was **a separate exploratory 2005–2020 historical-meteorology run, NOT FIXNC AD/Normal spinup**:
- CIME case: `/iridisfs/scratch/ly3n24/CLM_FATES/cases/US-GLE_FATES_HISTMET_2005_2020_STAGE106`.
- `case.submit success` 2026-10-26 13:25:52; Slurm run **4739020 PD** and archive **4739021 PD (Dependency)** when inspected; no confirmed model success or 16-year completion. Four sequential 4-year segments in the SAME case (3 resubmissions), NOT independent year-window groups.
- Uses source-dated historical ERA 2004 local boundary -> 2005 UTC corrected Stage106, while other variables/forcing years unchanged; **no scientifically equilibrated FATES spinup**, historical meteorology but **fixed CO₂=378.98ppm**, original year2000 gridded NATVEG92.49%/CROP7.51% rather than target FIXNC stand.
- 2020→2005 repeated forcing seam (|ΔTBOT| 3.877K, |ΔPSRF| 259Pa, |ΔWIND| 4.617m/s) intentionally **left unedited** by user's decision to run once-through historical forcing; actual DATM runtime date boundary requires checking from logs.
- **Remaining nine sites have not supplied verified case/Slurm/completion receipts.** Do NOT label all ten simulated, ready for spinup, or successful. US-Ho1 retains 2000-12-27 original QC0/QC1/QC2 extreme temperature jump HOLD (08:00−15.7°C QC0, 08:30−15.1°C QC0, 09:00−15.4°C QC1, 09:30+3.346°C QC2); original sensor heights and local-UTC assumptions require per-site review. US-BZS/US-Ho1 missing official TA/WS time-dated height histories, other sites have gaps.

## The authoritative 50-site PFT and soil inputs are in the OTHER repository

The files **exist now** and have been matched to all ten AmeriFlux Batch02 IDs. Source repository: `lyanyeung/CLM-FATES-single-site-workflows`, Git commit `0bef7854a916daee34948f5b4efc54ad6089482d` (specific retrieved source objects SHA-verified below).

1. [50-site FIXNC recommended PFT](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv), original Git blob `26fdfda6f1c88c9a134e7853bd70234685665031`. Use `recommended_percent`, `mapping_profile`, `clm_pct_nat_pft_json`, `uncertainty`, `basis`, `source_denominator` (NOT just IGBP).
2. [50-site recommended soil texture](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/FINAL_RECOMMENDED_INPUT_SOIL_TEXTURE_50_SITES_20261026.csv), original Git blob `6f2e9ff354bf5368083d212ee6aaaee2d75db390`. Values in `PCT_SAND_0_30cm` and `PCT_CLAY_0_30cm` are **summary 0–30cm recommendations**, NOT CLM `PCT_SAND`/`PCT_CLAY` on all ten layers. See [soil method](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/README.md), which requires per-depth ReESH/BADM/SSURGO/SoilGrids selection and organic matter assessment. Source data for per-layer generation must be independently checked.
3. [Auditable *ten-site* join CSV](data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv). Generated using **exact Batch02 rows only**; maps to FATES functional fractions and host `PCT_NAT_PFT` slots; all ten host fractions independently sum to 100%. It is **input planning**, not a mutation of any source NC, surface, CIME case or FATES parameter.

### Ten-site combined site-stand candidates

| Site | Recommended natural-soil FATES PFT % | Soil Sand/Clay 0–30cm % | Evidence tier | PFT uncertainty |
|---|---|---|---|---|
| US-BZS | ENF20 / Arctic evergreen shrub60 / Arctic deciduous shrub10 / Arctic C3 10 | 40.0/8.9 | T3 SoilGrids | HIGH |
| US-CMW | DBF74 / C4 26 | 9.8/20.5 | T2 SSURGO | HIGH |
| US-EML | Arctic evergreen shrub20 / Arctic deciduous shrub30 / Arctic C3 50 | 38.2/11.8 | T3 SoilGrids | HIGH |
| US-GLE | ENF100 | 17.5/17.4 | T1 ReESH | MEDIUM |
| US-Ha1 | ENF27.3 / DBF72.7 | 66.1/10.7 | T1 ReESH | MEDIUM |
| US-Ho1 | ENF91.9 / DBF8.1 | 58.4/10.9 | T1 ReESH | MEDIUM |
| US-Ho2 | ENF90 / DBF10 | 58.4/10.9 | T1N US-Ho1 ReESH near-tower proxy | HIGH |
| US-Ho3 | ENF80 / DBF20 | 58.4/10.9 | T1N US-Ho1 ReESH near-tower proxy | MEDIUM |
| US-ICh | Arctic evergreen shrub30 / Arctic deciduous shrub20 / Arctic C3 50 | 6.0/1.0 | T2 SSURGO | HIGH |
| US-ICt | Arctic evergreen shrub15 / Arctic deciduous shrub25 / Arctic C3 60 | 6.0/1.0 | T2 SSURGO | HIGH |

**Arctic PFT parameter map:** US-BZS, US-EML, US-ICh, US-ICt use `ARCTIC_PURE`, **not** the default DEFAULT14 FATES HLM PFT mapping. Verify the source [three mapping profiles](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/metadata/recommended_hlm_profiles_v1_20261026.json) and isolate any necessary site-only FATES parameter edits. Do not map moss/lichen/biocrust silently to bare or C3 grass. Dryland US-CMW tree/grass coverage and Arctic percentages contain model priors, NOT fully measured exclusive vegetation-area shares.

**Soil physics caveats:** US-BZS and US-EML are organic/permafrost-relevant; US-ICh and US-ICt are peat over mineral silt/till. Sand/Clay without reviewed `ORGANIC`, hydrology and layer structure is insufficient. US-GLE ReESH 17.5/17.4 conflicts with independent ~46–48% sand surveys: keep a soil-texture sensitivity alternative instead of asserting certainty. US-Ho2/Ho3 use nearby Ho1 measured soil as *neighbour proxy*, not direct local cores.

**US-GLE site vegetation:** user-supplied AmeriFlux BIF says ENF with 85% Engelmann spruce and 15% subalpine fir tree-species composition, not measured EC-footprint area cover; beetle peak 2008 caused loss of ~85% of forest basal area (NOT 85% land area). Existing 2005–2020 history was not run on this separate recommended FIXNC PFT/soil surface, and must not be used as evidence it was.

## Next steps for the separate FIXNC experiment

- **(1) Read-only inventory** original ten-site 215 NC manifest, per-site clock/sensor-height and unresolved QC logs, existing cases and Slurm/restart state; no false claim of 10 simulated sites. A specific GLE job `4739020` is only submitted/pending.
- **(2) Per-layer PFT/soil surface candidates**, creating new SHA-versioned natural-soil tower-point surfaces from the recommendations, explicitly choosing modeled NATVEG100/CROP0 **if** pursuing the idealized same-stand FIXNC experiment. Do not overwrite existing GLE historical or default surfaces. Infer neither measured tower crop nor full footprint PFT from gridded `PCT_CROP`.
- **(3) Check each site actual forcing file time phase, source sensor heights, true 10-layer soil/ORGANIC, FATES PFT map and scientific decision receipts; read-only CIME preview.** Only then choose site-specific AD400→Normal400 per [standard protocol](../../docs/AD400_NORMAL400_PROTOCOL.md) in independent FIXNC cases with 5y smoke gates.
- **(4) Avoid user-instructed proliferating unrelated test groups**; ten-site cohort is one workflow, model comparisons later between competition and FIXNC. Existing full-FATES/history runs and ten original weather files are not touched. No FIXNC jobs have been submitted as a result of the documentation/CSV preparation here.

**Never invoke** `examples/Batch02_10` for AmeriFlux: that directory is the **second ICOS/European cohort**, with completely different site list/cases/PFT and soil.
