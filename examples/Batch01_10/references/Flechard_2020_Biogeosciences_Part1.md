# Flechard et al. (2020) — primary paper and soil/vegetation supplement

## Later operator decision — 24 October 2026

The prior section below records the *historical* original-grid fallback status. **Current binding selection: CZ-BK1 now uses the published Flechard Table S4 22 Sand / 58 Silt / 21 Clay**, retaining the reported sum 101 and recording proportional normalization only for planned model-surface construction. **RU-Fyo alone retains its explicitly selected original soil `PCT_SAND`/`PCT_CLAY` fallback**, with separate peat-soil physics review. This decision changes neither old NetCDF nor any ongoing CIME/Slurm job. [Current decision table](../../../data/batch01_10_soil_input_decisions.csv).


## Citation and permanent sources

**Flechard, C. R., Ibrom, A., Skiba, U. M., de Vries, W., van Oijen, M., et al. (2020).** Carbon–nitrogen interactions in European forests and semi-natural vegetation – Part 1: Fluxes and budgets of carbon, nitrogen and greenhouse gases from ecosystem monitoring and modelling. *Biogeosciences*, **17**, 1583–1620. DOI **10.5194/bg-17-1583-2020**. Published 26 March 2020.

- [Publisher full article / official DOI](https://doi.org/10.5194/bg-17-1583-2020)
- [Official paper PDF](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020.pdf)
- [Official Supplement PDF — contains Tables S1–S6](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf)
- [Supplement DOI](https://doi.org/10.5194/bg-17-1583-2020-supplement)
- Journal labels both the article and supplement **CC BY 4.0**; the supplement notes that individual parts may have different rights.

**Archive method:** this repository stores the permanent publisher links, attribution, a cross-checked extract and interpretation notes. **The original full-text PDF files have not been embedded as GitHub repository binaries.** Use publisher links to access unchanged CC BY materials and avoid duplicate binary versions in a code repository.

## Tables relevant to Batch01

- **Table S2: forest species composition**, supplementary PDF **page 7 (zero-based page index 6)**. CZ-BK1 spruce 99%; IT-Ren spruce 85% and pine 12%; RU-Fyo spruce 85% and birch 15%; FI-Sod Scots pine 95%; FR-Pue holm oak 95%; BE-Vie beech 43%, Douglas fir 37%. Some source fractions do not total 100%: no arbitrary normalization.
- **Table S3: ecosystem C/N and soil organic carbon**, supplementary PDF **page 8**. Useful for later pool plausibility but not a per-depth soil carbon profile.
- **Table S4: site soil physical properties**, supplementary PDF **page 9 (zero-based index 8)**. Columns are **Clay %, Sand %, Silt %**, in that order. In our derived CSV they are reordered **Sand, Silt, Clay**. Other fields include soil depth (m), slope, textural category, FAO soil class, moisture constants and topsoil pH.

[**Machine-readable Batch01 10-site Table S4 transcription**](../../../data/batch01_10_Flechard2020_TableS4_soil.csv). The transcript preserves the original published integer percentages and missing values, rather than applying silent renormalization.

## Table S4 findings by station (Sand / Silt / Clay)

| Site | Sand % | Silt % | Clay % | Depth (m) in S4 | FAO class | Source limitations |
| --- | ---: | ---: | ---: | --- | --- | --- |
| **CZ-BK1** | **22** | **58** | **21** | 0.55 | Ferric Podzol | Published sum **101%** (rounding); site aggregate, not measured layer-by-layer |
| **IT-Ren** | **55** | **34** | **11** | 0.50 | Haplic Podzol | Site aggregate, not measured layer-by-layer |
| **RU-Fyo** | n.a. | n.a. | n.a. | 0.30 | Umbric Albeluvisol; texture = Peat | **Paper provides no mineral fractions**; peat physical model issue remains |
| **CH-Dav** | — | — | — | — | — | **Not in this paper's Table S4**; use separate same-tower soil literature |
| **IT-Col** | **8** | **32** | **59** | 0.30–1.50 | Humic Alisol | Source sum **99%** (rounding); conflicts with separate Chiesi 2018 30/40/~30 estimate |
| **FR-Fon** | n.a. | n.a. | n.a. | 0.80 | Gleyic Luvisol | Soil category reported, fractions **not available**; separate paper has upper/lower horizons |
| **FI-Sod** | **94** | **4** | **0** | 1.50 | Haplic Podzol | Sum **98%** (not necessarily only rounding); separate measured 3-horizon FLUXNET dataset is more granular and has priority |
| **FR-Pue** | **26** | **35** | **39** | 0.50 | Rhodo-chromic luvisol | Same as other 2022 site summary, but not a full depth profile; major rock fraction caveat |
| **DE-Hai** | **4** | **56** | **40** | 0.48–0.71 | Dystric Cambisol | Do not mix with independent 0–10 cm sample (4/49/48) |
| **BE-Vie** | **27** | **55** | **18** | 1.50 | Dystric Cambisol | Matches Buysse 2013, but lacks full profile |

**Interpretation:** Nine of the ten selected stations appear in Table S4; **CH-Dav does not**. Seven of the nine listed have *some* numeric texture triplet (CZ-BK1, IT-Ren, IT-Col, FI-Sod, FR-Pue, DE-Hai, BE-Vie); **FR-Fon and RU-Fyo are explicitly n.a.** for fractions. These nine rows are valuable *station-associated reference values*, **NOT** proof of a complete measured, depth-resolved CTSM soil profile. Table S4's `Depth m` is *soil depth*, not the soil sampling depth interval for each reported particle fraction.

**RU-Fyo peat caution:** Flechard calls its soil texture `Peat` and FAO classification `Umbric Albeluvisol`, while another paper reports a substantially deeper peat layer in the landscape. These are *distinct quantities/sources*: do not reinterpret the 0.30 m table depth as a measurement of all peat thickness or automatically replace organic soil physics with coarse-gridded mineral texture.

## Existing Batch01 model choices

The operator previously selected a **technical source-surface texture exception** for CZ-BK1 and RU-Fyo. This decision remains in [Batch01 soil input decisions](../../../data/batch01_10_soil_input_decisions.csv) **until changed explicitly**. The newly verified CZ-BK1 22/58/21 published value is a **better provenance candidate** for the station than the old surface texture, but it is not silently adopted or assumed to apply to all soil layers. RU-Fyo retains a documented peat mismatch risk. The 10 forest PFT assumptions and new `PCT_NATVEG=100 / PCT_CROP=0` idealized forest-point design remain unchanged.

## Use in scientific workflow

1. For any station, prefer genuine site soil measurements with proven depths; treat S4 values as a reference/possible proxy, not a measured 10-layer profile.
2. Check mismatches between published sources **without averaging incompatible depths or campaigns** (notably IT-Col, DE-Hai and FI-Sod).
3. For CZ-BK1, request a choice between the old-grid technical fallback and site-published 22/58/21 proxy, with a documented soil-layer policy. The current active default remains the user's existing exception until changed.
4. Keep original binary NetCDF, old CIME cases, restart files and forcing untouched. New surfaces must be versioned independently; no AD5/AD400 job is authorized solely by this table.

_Last reviewed: 24 October 2026. Original publisher PDF Table S4 visually checked against the paper._
