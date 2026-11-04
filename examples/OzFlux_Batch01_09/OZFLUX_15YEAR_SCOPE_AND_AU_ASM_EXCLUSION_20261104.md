# OzFlux 15-year scope reset and AU-ASM exclusion — 2026-11-04

## Operator decision (effective immediately)

**EXCLUDE AU-ASM from this experiment.** Do not pursue or reuse its pending NOAA Stage25, previous 2013–2018 provisional six-year DATM files, L3/L4/AWS donor repairs, Site-Soil/PFT/Surface candidate, stage scripts or model settings to prepare or submit AD400/Normal400. There is **no >=15-year continuous original observation interval** for the first tower release (2010-09-03 to 2023-03-08), and the second release is separated by an extended March-2023 to 2024 outage. Do not concatenate separate instrument releases to satisfy the threshold. Historical Stage01–24 evidence and actual operator results are retained **immutable for provenance only**, not deleted. Site source L6 `b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb`, L3 and L4 source checksums are unchanged. Any other AU-ASM scripts in PR #65 are now historical, **not instructions to run**. Stop all future AU-ASM science QC in this project unless the operator issues a separate, explicitly revised selection decision.

## Important site identity correction — crop conversion was AU-DaS

The documented **November 2022 clearing for crop development** applies to **AU-DaS / Daly River Uncleared**, NOT Alice Springs Mulga (AU-ASM). Independent official OzFlux source: <https://tern-ozflux.odoo.com/daly-river>. Official AU-ASM status: observation started 2010-09; hiatus March 2023 to 2024, described by the OzFlux collection <https://data.ozflux.org.au/pub/viewColDetails.jspx?collection.id=152&collection.owner.id=101&viewType=anonymous>.

**AU-DaS LAND-USE HOLD:** Do not merge pre-November-2022 woody savanna and post-clear crop years for a homogeneous ecosystem 15-year requirement. Existing Stage07 conservative structural-year block **2009–2021 only = 13 consecutive full native years**. Post-2022 data must be a separate ecological regime, not an extension of that series. AU-DaS is not formally excluded by the AU-ASM operator instruction; however its eligibility for this specific homogeneous 15-year design is unproven and it must not be picked for new forcing QC/model jobs without a separate decision.

## Remaining OzFlux candidates and eligibility checks

Of original 9 site IDs and 10 original L6 files:
- 1 site **EXCLUDED**: AU-ASM
- 1 site **LAND-USE HOLD**: AU-DaS
- 7 available for a **fresh 15-year eligibility screen**: AU-Cow, AU-Cpr, AU-Dry, AU-Gin, AU-How, AU-Stp, AU-Tum.

Previous Stage07/08 (operator executed 2026-11-01): 169 source file-year rows, 67 **structure-only candidates** and 102 review/HOLD. This does **not** equal 67 approved forcing years and does **not** grant AD400. Previously verified source-level candidate counts:

| Source site | Structural candidate years (not necessarily consecutive) | Largest previously recorded block |
| --- | ---: | --- |
| AU-Cow | 12 | 2015–2019 (5 years), 2022–2025 (4 years) |
| AU-Cpr | 2 | To be computed from operator Stage07 |
| AU-Dry | **14** | **2010–2018 (9 years)**, 2020–2024 (5 years) |
| AU-Gin | 0 | None |
| AU-How | 2 | 2006–2007 (2 years) |
| AU-Stp | 4 | To be computed |
| AU-Tum | 7 | To be computed; original time step 60 minutes, not 30 |
| AU-DaS (land use HOLD) | 16 total across pre/post regimes | Pre-clear 2009–2021 (13 years) |

**Do not equate a file's first-to-last calendar year span with 15 scientifically approved continuous natural-ecosystem years.** Some years fail strict structural screening due to missing meteorology and may later be recoverable under evidence-based donor QC; a failed initial screening does NOT automatically prove a site cannot ever meet the operator's criterion. On the other hand, a 15-year time span alone is never enough. The screening must consider native timestamp cadence, data gaps, physical QC, instrument/processing consistency and land cover history for the selected exact contiguous period.

**Next preferred source-QC target, conditional on the eligibility screen:** AU-Dry (Dry River). Of the seven nonconversion sites it has the most structure-only candidate years (14), with an existing 9-year intact block. It has **not** passed the 15-year contiguous gate; inspect the intervening/missing original years and assess if science-grounded repairs can establish a legitimate 15-year window, rather than building AD400 prematurely. If not, reconsider the site or revise operator scope; never silently relax >=15 years.

**New Stage26:** `scripts/26_ozflux_15yr_eligibility_exclude_ASM_READONLY.py` (source blob `3ff38e8e2293ad025df72accb3539fe3d5d22782`; commit `0a7fee3f5b73914ef336ee3d266107289746779a`). Reads actual original Stage07 operator report `$HOME/ozflux_stage07_20261101T062633Z/stage07_year_status.tsv`, fails closed if 169 rows/67 structure-only candidates or 9 IDs change. Separately reports file-year span and longest consecutive structural block for each site; makes no external source fetch or model writes. Does not force future repairs or scientific acceptance. No original forcing, DATM, Surface, CIME or Slurm modifications. All AD400 remains HOLD.
