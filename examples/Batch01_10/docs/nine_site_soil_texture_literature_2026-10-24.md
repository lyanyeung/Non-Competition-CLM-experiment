# Batch01: targeted nine-site soil texture literature search (24 Oct 2026)

**Station-observed-first. No inherited source-grid sand/clay used. No new surface or AD job generated.** This is a bibliography-and-candidates report, not an approved per-layer CLM soil profile. See [12-row machine-readable literature candidate table](../../../data/batch01_10_soil_literature_candidates.csv) and [original registered site soil profiles](../../../data/batch01_10_soil_site_observations.csv).

## Research results

| Site | Published soil Sand/Silt/Clay (%) | Study sampling/depth | Scientific status |
| --- | --- | --- | --- |
| **CH-Dav** | **53 / 25 / 22** | Meredith et al. 2018, Table 3, Survey 2: station CH-Dav; uppermost **0–10 cm** excluding litter | **DIRECT_TOWER_SOIL_LAB_CANDIDATE**; cannot assume same composition below 10 cm |
| **FR-Pue** | **26 / 32 / 42** | Meredith et al. 2018, Table 3, Survey 2; **0–10 cm** | **DIRECT_TOWER_SOIL_LAB_CANDIDATE** |
| FR-Pue (alternative) | **26 / 35 / 39** | Jiménez-Rodríguez et al. 2022, Appendix A1, site summary (no isolated layer interval) | Site-level summary; **stone fraction ~0.75 in 0–50 cm and 0.90 below 50 cm**; site soil depth ~50 cm in this representation. Critical hydrologic issue, not resolved by texture alone |
| **DE-Hai** | **4 / 49 / 48** (sums **101** from rounding) | Meredith et al. 2018, Table 3, Survey 2; **0–10 cm** | Direct named tower candidate; must account for published whole-integer rounding explicitly |
| DE-Hai (alternative) | **~3 / 38 / 59** | 2025 Biogeosciences modeling application using Schrumpf et al. studies at Hainich | Different source sampling; don't mix with Meredith series without verifying locations/depths |
| **FR-Fon** upper soil | **41.9 / 38.8 / 19.3** | Delpierre/Fontainebleau Barbeau same CarboEurope site; INRA Arras particle analysis; upper soil, **exact depth not published in excerpt** | Site-specific loam profile, not a generic Fontainebleau soil |
| FR-Fon lower soil | **35.2 / 32.0 / 32.8** | Same source; clay loam lower soil, overall soil depth ~0.8 m | Need precise horizon boundaries for layer mapping |
| **BE-Vie** | **27 / 55 / 18** | Buysse et al. 2013, *Biogeochemistry* Table 1, specifically Vielsalm mixed beech/Douglas forest; 2009 sampling at one forest location | Direct site study, **soil texture horizon not explicitly stated** |
| **IT-Col** | **30 / 40 / ~30** | Chiesi et al. 2018 expressly states Collelongo sand 30%, silt 40%, clay loam texture, soil <1 m | Clay ~30% is **ARITHMETIC COMPLEMENT**, not a separately quoted measurement. Obtain upstream texture dataset and horizons if possible |
| **IT-Ren** | **numeric fractions not yet extracted** | ICOS ETC-Soil 2020 station report explicitly provides mineral particle-size raw export and standardized soil horizons | **Excellent next raw-data target**; obtain site CSV and aggregate ICOS bands clay 0–2 µm, silt 2–50 µm, sand 50–2000 µm |
| **CZ-BK1** | **no tower-specific complete triplet** | ICOS calls soil medium-deep sandy-loamy podzol with skeleton; an adjacent Beskydy spruce-stand study mentions **15–35% clay**, but different plots | **DO NOT use neighboring plot range as tower soil**; obtain station/PI profile or ICOS ancillary `SOIL_TEX` |
| **RU-Fyo** | **no defensible mineral texture triplet** | Jiménez-Rodríguez et al. 2022 Table A1 reports **~50 cm peat layer**, superficial water table, rooting depth ~0.2 m | Soil is **organic/peat-dominated**; require organics/water table and mineral substrate evidence, not fabricated Sand/Clay. Prior JSBACH study also describes Fyodorovskoye as natural peatland |

In short, **6 of 9 stations have site-related numerical soil particle-size evidence** from published research; this does **not** mean 6 have complete, operationally validated, depth-resolved CLM texture columns. **3 of 9** (IT-Ren, CZ-BK1, RU-Fyo) still lack usable numeric site profile triplets in the material retrieved. FI-Sod's earlier independently registered 0–40 cm observations are preserved.

## Primary sources (retrieved and inspected)

- Meredith et al. (2018), *Soil Systems* **2**, 37, Table 3, page 9–10, Survey 2 top 0–10 cm. [Publisher DOI](https://doi.org/10.3390/soilsystems2030037); [author-hosted manuscript PDF](https://www.laurameredith.com/wp-content/uploads/2018/07/soilsystems-02-00037-v3.pdf). It reports **CH-Dav, FR-Pue and DE-Hai separately**. Values are whole percentages, DE-Hai totals 101% through rounding.
- Jiménez-Rodríguez et al. (2022), *Biogeosciences* **19**, 3395–3423, Appendix Table A1, [DOI](https://doi.org/10.5194/bg-19-3395-2022). Gives FR-Pue second texture triplet, 75%/90% stone fractions by depth, and RU-Fyo peat layer.
- Fontainebleau-Barbeau **FR-Fon** same-tower forest, *Increase in aboveground fresh litter quantity over-stimulates soil respiration in a temperate deciduous forest*, source [ScienceDirect record](https://www.sciencedirect.com/science/article/abs/pii/S0929139310000909). Explicit top- and bottom-soil laboratory texture values, overall bedrock depth 0.8 m.
- Buysse et al. (2013), *Biogeochemistry* **112**, 441–455, DOI [10.1007/s10533-012-9739-7](https://doi.org/10.1007/s10533-012-9739-7). [University PDF](https://orbi.uliege.be/bitstream/2268/116838/1/Buysse_Biogeochem_2013.pdf) p. 444 Table 1; explicit Vielsalm column.
- Chiesi et al. (2018), *Advances in Meteorology*, Collelongo section, [DOI](https://doi.org/10.1155/2018/9792609). Sand and silt published, third percentage inferred only.
- [ICOS IT-Ren soil report (2020 measurements)](https://traitementinfosol.pages-forge.inrae.fr/icos/IT-RenCarbonReportv2.html); site raw particle classes/soil layer export indicated, **not yet fetched**.
- [ICOS CZ-BK1 station description](https://meta.icos-cp.eu/resources/stations/ES_CZ-BK1); neighboring Beskydy plots are *not* equivalent to EC tower, [adjacent study](https://www.researchgate.net/publication/275420351_Comparison_of_soil_and_seepage_water_properties_in_the_limed_and_not-limed_spruce_forest_stands_in_the_Beskydy_Mts).
- [Biogeosciences 2025 Hainich alternative](https://doi.org/10.5194/bg-22-1427-2025), descriptive 3/38/59.
- [ICOS CH-Dav ETC-Soil 2018 report](https://traitementinfosol.pages-forge.inrae.fr/icos/CH-DavCarbonReportv2.html) adds substantial 0–100 cm station sampling and rock-fragment profile evidence, but the accessible summary does not directly provide a validated mapped 10-layer CLM profile.

## Follow-up and release gate

1. Add candidates to a **new** versioned scientific evidence register, keeping each publication/measurement campaign as a separate observation; **do not silently overwrite** the original FI-Sod measured-horizon CSV or merge conflicting sources.
2. Retrieve the 2020 IT-Ren ICOS soil texture raw table and CH-Dav deeper raw texture, if public; locate CZ-BK1 stand-measured soil from the station PI/ICOS BADM.
3. For RU-Fyo check the organic peat column and layer thickness, water-table history, underlying mineral sediment and CTMS/FATES organic soil support. Do **not** assume a generic mineral texture is physically appropriate.
4. Decide how each measured depth interval maps to the actual CLM texture input layers and what **explicitly labelled** extrapolations are permissible. Verify soil physical/hydraulic and stone fraction representation for stony FR-Pue.
5. No blanket AD400 or AD5 submission until a new **isolated**, scientifically and technically verified FIXNC surface/case, forcing loop and FATES map are available. A single-site AD5 pilot is the first run gate.
