# OzFlux AU-ASM new soil texture v2 vs prior GRID_REFERENCE (2026-11-03)

## Upstream authority

Authoritative science recommendation is **NOT** an edit to `Non-Competition-CLM-experiment/main` v1.1 PFT file; it is the new dedicated **unmerged branch** `oz-jp-soil-texture-20261103` at [upstream source](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/oz-jp-soil-texture-20261103/examples/OzFlux_JapanFlux_Soil), pinned commit `ba79a8cd86a0c20425f520754a6d221c64ed8fc5`. It includes 20-site tower evidence, original source L6 soil string, current 9 OzFlux surfaces, SoilGrids 250 m, stage02 verified results; Australian SLGA 90 m is not yet acquired (TERN key required). This is **v1 recommended soil**, not new NetCDF inputs or formal science approval.

Freeze upstream exact Git blobs before building:
- `OZ_JP_RECOMMENDED_CLM10_SOIL_TEXTURE_WIDE_20261103.csv` = `427f5eac76e5a49ded03859fd7238da927f064d1`
- `OZ_JP_RECOMMENDED_CLM10_SOIL_TEXTURE_LONG_20261103.csv` = `d730b06c35fe11f5e2179d6e65dc6e8d64f26c8e`
- `data/manual_depth_assignments_20261103.csv` = `cf68ee4f6fb2ca0f7e5b2aa5c48c23d568660bf3`.

## AU-ASM v2 ten-layer source decision

- Existing Stage02 PFT/soil reference surface immutable SHA256 `d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1`, 29% bare, 65% EBT FATES4, 2% C3 FATES13, 4% C4 FATES14. **Keep all old NetCDF files unmodified.**
- New **`PCT_SAND` L1–L7 = 74.0%; L8–L10 = 70.6%**; new **`PCT_CLAY` L1–L7 = 15.0%; L8–L10 = 23.9%**; silt remainder. L1–L7 at CLM node depth 0.0071–0.6198m apply 74:11:15 tower-specific literature texture, **but reported sampling depth/particle-size method is unspecified**. Upstream explicitly labels 0–100cm a *manual profile-model assumption*, not seven independent field samples. L8–L10 use SoilGrids; L10 is extended below SoilGrids reported depth of 200cm.
- The **hardpan at ~1m** is not identical to a bedrock depth; `zbedrock` and hydraulic handling are a separate unresolved model-science decision. Neither `ORGANIC` (not updated) nor soil color, landunits, PFTs, forcing are changed. A 2018 wind isolated spike also remains an independent *forcing* science QC issue.
- Source Stage02 GRID_REFERENCE soil 90/89% sand and 6/7% clay is **not** the latest v1 site-soil choice; preserve as a technical baseline only, not as the newly chosen AU-ASM soil.
- Upstream recommendation conflicts between various soil sources and ISSS/USDA particle size possible; a later SLGA or independently sourced depth profile may supersede v1. Do not silently call the 74/15 first seven layers *field-measured at each layer*.

## Safe isolated AU-ASM v2 builder

Script `scripts/13_asm_stage13_GitHub_site_soil_v2_isolated.py` checks the three upstream Git blobs, actual 10-layer source and PFT SHA, then `plan` (read-only) or `build` (new direct-HOME directory) to create **one separate v2 interim point Surface** by copying exact source and modifying only `PCT_SAND`/`PCT_CLAY`. Every other NetCDF variable, variable attribute, global attribute and dimension must be identical to frozen Stage02; extra machine-readable receipt records provenance and candidate SHA256. `verify` independently rechecks source, CSVs, receipt and all NetCDF fields. **No original/candidate forcing, original Surface, FATES parameters, CIME cases or Slurm job modified.**

## Science gates, operator decision and next action

1. Record upstream v1 20-site soil recommendations and all unresolved soil-science assumptions; build and verify isolated v2 only after exact hash checks. A built file is a **candidate**, not automatic adoption.
2. Audit the exact three QC0 2018 source wind spikes from `/home/ly3n24/ozflux_nc_stage12_20261103T074301Z/stage12_original_QC0_wind_isolated_candidate_review.tsv` and Stage12 original seven-met boundary evidence. Stage12 found 2018-03-10 20:30 Ws average 16.29613m/s, QC0, neighbouring 4h median 3.6628965m/s; a `Wd` direction series is NOT an independent wind-speed replacement.
3. Confirm PyFluxPro source time and AWS(410)/ACCESS(420) overlapping donor independence, long radiation substitution handling, wind QC0 spike decision, total forcing invariance and any new repair provenance.
4. **Direct AD400 without AD5 only after independent science approval of forcing and final soil profile**, and a new CIME case controller explicitly binding verified v2, rather than reusing the older `AU-ASM_OZ_FIXNC_GRIDREF_AD400_DIRECT` path or old GRIDREF Surface by accident. Prior protected AD400 controller in PR #64 remains fail-closed.

**Current authorization: `soil_science_approval=false`, `forcing_science_approval=false`, `AD400_authorised=false`.**

## Actual Stage13 IRIDIS6 operator evidence — PASS on 2026-11-03

Exact source-pinned stage13 script `32a23136ff4bab13a97dd0002a6a80c1fae83939` returned **SELF-TEST, PLAN, ISOLATED BUILD and INDEPENDENT VERIFY PASS**. The operator verified all three upstream WIDE/LONG/manual Git blobs; frozen old Stage02 surface SHA256 `d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1`.

New independent Surface:
`/home/ly3n24/ozflux_nc_stage13_soil_20261103T130125Z/surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_20261103_INTERIM.nc`

**Candidate SHA256:** `2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1`

Stage13 receipt:
`/home/ly3n24/ozflux_nc_stage13_soil_20261103T130125Z/stage13_AU_ASM_v2_SITE_SOIL_candidate_NOT_MODEL_APPROVED.json`

Changed *only* `PCT_SAND` L1–L7 74%, L8–L10 70.6%; `PCT_CLAY` L1–L7 15%, L8–L10 23.9%. Independent verification asserts **87 other NetCDF variables unchanged** (including PFT, NATVEG/CROP, ORGANIC), original reference SHA intact and exact upstream provenance. No forced `zbedrock` or `ORGANIC` edits; prior GRIDREF remains unchanged. **This is scientifically provisional**: L1–L7 0–100 cm extrapolation is not depth-resolved tower observations; ~1m siliceous hardpan / hydraulic effects, SLGA, soil particle-size scheme are unresolved.

The next model case, when authorized, must use this SHA-pinned **new v2** or a documented later scientifically improved variant; old GRIDREF CIME/AD400 controller remains invalid for any v2 scientific model claim. Source forcing QC remains HOLD (Stage12 unresolved WS QC0 spikes and 2018 AWS/ACCESS joins). **NO CASE, AD400 OR Slurm SUBMITTED.**
