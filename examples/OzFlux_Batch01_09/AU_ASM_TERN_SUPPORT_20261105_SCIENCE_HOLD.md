# AU-ASM Alice Springs Mulga — first-party TERN support scientific HOLD (2026-11-05)

## Scope and current decision

**Site:** AU-ASM, Alice Springs Mulga / Alice Mulga. **Not AU-Gin Gingin.**

**Current workflow status:** **SCIENCE HOLD / EXCLUDED FROM CURRENT OZFLUX AD400 SUBMISSION COHORT**. Keep original raw OzFlux files immutable. This is **not a permanent exclusion or deletion**. Earlier OzFlux multi-site inventory found insufficient strict elapsed tower coverage (~14.18 years with a ~531-day gap) for the working >=15 years continuous-observation criterion; scientific reassessment would require an explicitly changed study rule and source-level checks. The new support replies add *independent reasons for caution on auxiliary datasets*, not new evidence that the tower time-series itself is corrupted.

## TERN Support correspondence: Nicola Lieff

The user supplied first-party reply, date copied 2026-11-05:
- She was not involved in 2014; **defer to Arun** regarding reliability of 2014 measurements.
- **2014 data acquisition methods differ from the planned 2025/2026 publication**; comparing them directly without harmonisation and provenance would be scientifically unsafe.
- **No unpublished archived auxiliary wind data** remain available beyond published sources.
- The published **2018 NetCDF contains three separate wind measurements**, e.g., `Ws_SENTRY_200cm_Av`. Specific other channel names must be inventoried directly from the immutable original NetCDF rather than inferred.
- Wind measurements are **means for the 30-minute interval** and **timestamp marks the interval END**, not start. If 2018 wind is ever reconsidered, use **[timestamp-30min, timestamp)** window in join; independently verify the actual product timezone and units.

## TERN Support correspondence: Arun Singh Ramesh, on behalf of TERN

The user supplied first-party reply:
- Refers explicitly to **Alice Mulga Stem Diameter, Height and Aboveground Woody Biomass dataset (Cleverly, 2022)**.
- **Do not use 2018 dendrometer-informed values for modelling**: their internal audit identified potential quality issues/errors, no documentation of how 2018 dendrometer-derived values were constructed, and those values were published without QC. Author could not be reached.
- New site PI **Dr Anne Griebel** reports some stems listed as measured could not be relocated; old stem inventory or plot-level continuity is therefore uncertain. Avoid assuming original individual stems can be matched to later measurements.
- A **2025/2026 census from a NEW study plot** is planned with stem-level provenance and detailed biomass calculation, subject to ongoing PI/technician QC. It is **not an interchangeable resurvey of the old plot** without verified spatial/stem equivalence.
- TERN expects to notify users once this is made available through the TERN Data Discovery Portal. If still unpublished by **late November / early December 2026**, they invite a follow-up status enquiry. **No guaranteed publication date.**

## Science handling

**Do not conflate the dataset types.**
- This explicit **non-use warning applies to 2018 dendrometer-informed stem biomass/height-related values**, not automatically to every 2018 eddy-covariance met/flux datum.
- Nicola's wind statement implies *already published* 2018 auxiliary channels exist, not new private wind data. Do not treat an instrument named SENTRY 200cm as automatically a standardized 10m forcing; check measurement height and support.
- Retain the OzFlux multi-site AU-ASM science eligibility HOLD separately from the stem-dendrometer warning.
- For any future cross-year biomass work, require documented plot boundaries, stem identities, methods, calibration and uncertainties before direct 2014 / 2018 / 2025–26 comparison.
- No source edits, forcing generation, case creation or Slurm jobs authorised for AU-ASM.

## Related separate site

AU-Gin is a different OzFlux station. Its independently verified Stage10 script/output (as reported by operator on 2026-11-05) passed read-only QC triage for **28 original anomaly groups**, **44 flagged half-hour records**, and **91 half-hour multivariate context records around seven priorities**. All AU-Gin anomalies remain science HOLD, no forcing/AD400 submission. Do not transfer TERN AU-ASM stem/wind advisories to AU-Gin.
