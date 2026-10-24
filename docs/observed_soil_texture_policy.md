# Observed soil texture policy — all future CLM-FATES sites

## Batch01 soil decision revision — CZ-BK1 and RU-Fyo (24 October 2026)

**Most recent operator choice supersedes the earlier universal 'no old-grid fallback' text for exactly one site:** CZ-BK1 now uses **Flechard et al. (2020) Table S4** station-level Sand/Silt/Clay **22/58/21%**, with a **101% published sum** requiring transparent proportional normalization when constructing a *new* site surface. A separate vertical-depth profile assumption is still necessary; Table S4's 0.55 m value is site soil depth, not per-layer texture measurements. **RU-Fyo alone is approved to reuse the original surface `PCT_SAND`/`PCT_CLAY` as a labelled technical fallback**, not an observed soil profile. RU-Fyo peat/organic layers and water-table physics remain a mandatory preflight. This exception is SOIL TEXTURE ONLY: do not reuse old-grid land cover or PFT proportions. Existing files and cases remain untouched. Track the binding site decisions in [Batch01 soil decisions CSV](../data/batch01_10_soil_input_decisions.csv).


## Batch01-specific override (24 October 2026)

**Scope: only [Batch01_10](../examples/Batch01_10/README.md).** The operator explicitly removed the inherited coarse-grid surface as a scientific benchmark. **Do not use the generic fallback in point 3 below** for Batch01. Instead require station/stand-measured soil texture at documented depths; if unavailable mark the station `NEED_SITE_OBSERVATION` and keep soil input parameterization on HOLD. Site-measured depth gaps may be handled only through a separately documented physical interpolation/extrapolation decision, never by silently importing `PCT_SAND` or `PCT_CLAY` from the old grid. The old grid NetCDF may still serve as a *structural schema* for a new independent versioned file, not a source of adopted soil/ecological values. This does not change previously running experiments or the generic policy for other batches.



**Project decision: when reliable in-situ/site-specific sand–silt–clay observations exist, use those measurements in the site's FIXNC surface instead of retaining coarse-grid sand/clay.** Use a versioned, isolated surface. Do not modify raw source surfaces, existing reference experiments or earlier surface versions.

## Scope and evidence hierarchy

1. **Best:** EC-tower-footprint or same stand field-measured mineral soil sand, silt and clay with clear sampling depth, location, date, particle size convention and fractions that sum to ~100%.
2. **Accept with explicit proxy label:** published station / tower study giving composition for one or more horizons, where unsampled model layers need documented interpolation or extrapolation. Record exact assumed layer treatment; do not call extrapolation an observation.
3. **If no suitable measured data:** retain original extracted CLM gridded texture, mark `SOIL_TEXTURE_GRID_FALLBACK`, and record attempted sources. Do not invent numeric texture.
4. If multiple field studies disagree, **do not silently average** different tower locations, depth definitions, years or methods. Preserve their provenance and document a choice or sensitivity experiment.

Keep forest PFT/landunit decisions separate from soil observations. Updating only `PCT_SAND` and `PCT_CLAY` does **not** make inherited organic matter, coarse fragments, soil color, bedrock, hydraulic parameters, etc. observed. CLM can compute hydraulic quantities internally from texture; check the pinned model's parameterization.

## Required reproducibility records

- Site ID and coordinates/spatial sampling footprint if available.
- DOI/official document, verbatim reported fractions, units, method/particle convention, and **depth interval**.
- Layer allocation policy for the pinned CIME `soil_layerstruct`: observed vs. interpolated vs. extrapolated, with boundary depths reviewed in `CaseDocs`/land log. A `PCT_SAND` array of 10 entries is **not** a proof of sampled depths.
- New NetCDF path, original surface and previous version SHA256; list precisely changed variable names.
- Unchanged-variable and input-total checks, NetCDF verification receipt, mode validation and forcing QC before any CIME submission.
- Never commit bulk source forcing, generated NetCDF, restart or binary to GitHub; commit code, small CSV evidence, config, checksums, and decisions.

## DE-Tha implementation (2026-10-24)

- Observed forest PFT proxy: **ENF 87%, DNF 10%, DBF 3%** (2% unspecified deciduous trees provisionally mapped to DBF); NATVEG=100%, CROP=0%.
- Published forest-station mineral topsoil texture: **Sand 17%, Silt 71%, Clay 12%**, reportedly relatively constant down to approximately 1.2 m. Prescher, Grünwald & Bernhofer (2010), *Land use regulates carbon budgets in eastern Germany: From NEE to NBP*, *Agricultural and Forest Meteorology*, 150:1016–1025, DOI [10.1016/j.agrformet.2010.03.008](https://doi.org/10.1016/j.agrformet.2010.03.008) (see text available [here](https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany)).
- Source grid top layers were **24% sand / 51% silt / 25% clay**. The v1 forest surface inherited this mismatching source profile unchanged.
- The **v2 DE-Tha site-soil proxy** applies Sand 17% / Clay 12% to **all 10 input texture layers**, giving derived Silt 71%. **Layers below the study-supported depth are extrapolated, not measured**, and must be described as such in scientific methods.
- Other source soil variables remain unchanged, as do the validated PFTs and landunit fractions.
- Script: [07_build_site_soil_surface_v2.py](../examples/DE-Tha/scripts/07_build_site_soil_surface_v2.py); actions `audit`, explicit `write`, and read-only `verify`.
- New v2 surface is a **separate file**, not a rewrite of `...ENF87_DNF10_DBF3_v1.nc`. PRE50 case must reference **verified v2**, not v1.
- **Operational gate**: use actual CIME `soil_layerstruct` and logs to understand layers and potential 1.2 m extrapolation. CTSM developers explain the 10 texture inputs map onto the model's first 10 soil layers, with deeper active layers sometimes inheriting layer-10 properties ([DiscussCESM technical answer, 2026](https://bb.cgd.ucar.edu/cesm/threads/what-are-the-exact-soil-depths-for-the-10-layer-nlevsoi-10-pct_sand-pct_clay-in-clm5-0-surface-dataset.12119/)). **The layer depths must be checked in the actual case, rather than copied from a generic technical note.**

**IMPORTANT:** This policy applies going forward. It does not retroactively change NL-Loo, existing six-/eight-/eleven-/thirteen-site cases, or any ongoing Slurm job.
