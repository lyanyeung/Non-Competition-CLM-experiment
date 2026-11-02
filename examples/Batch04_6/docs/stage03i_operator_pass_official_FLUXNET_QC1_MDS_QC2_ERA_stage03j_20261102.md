# ICOS Batch04 — Stage03I actual six-handoff result, FLUXNET official variable semantics and Stage03J next action (2026-11-02)

## Stage03I actual read-only success

Operator's source-verified IRIDIS6 `FULL PYTHON SYNTAX PASS`, `STAGE03I SELF-TEST PASS`, followed by successful six-event source-vs-packaged-ERA comparison. Original source / selected Stage28 / yearly DATM NC / CIME cases / PFT / Slurm were not changed.

| Exact jump | Original product QC switch | Stage28 30-min TA step (°C) | TA_ERA 30-min step (°C) | QC1 − TA_ERA (°C) | QC2 − TA_ERA (°C) |
|---|---|---:|---:|---:|---:|
| TJ1128 — 2025-11-13 14:30 | 2→1 | −12.440 | −0.037 | **−12.403** | **0** |
| TJ1131 — 2025-11-13 16:00 | 1→2 | +11.959 | −0.410 | **−12.369** | **0** |
| TJ1134 — 2025-11-13 17:30 | 2→1 | −14.312 | −0.871 | **−13.441** | **0** |
| TJ1162 — 2025-11-14 07:30 | 1→2 | +13.963 | −0.132 | **−14.095** | **0** |
| TJ1229 — 2025-11-15 17:00 | 2→1 | −13.142 | −0.118 | **−13.024** | **0** |
| TJ1373 — 2025-11-18 17:00 | 2→1 | −6.937 | −0.126 | **−6.811** | **0** |

Six source transitions are **4×QC2→QC1 + 2×QC1→QC2**. All packaged `TA_ERA` steps smaller than 1°C while selected/original `TA_F` changes 6.937–14.312°C. Source-original equals Stage28 at both sides. **This is strong evidence of discontinuity between two upstream meteorological processing/gapfill families rather than a new Stage28 processing error.** It does not independently verify site instrument readings or identify which missing-data method is meteorologically correct.

Private reports, never publish:
```
/home/ly3n24/ICOS_Batch04_stage03i_hWGXau1Y/results/stage03i_IT_Tor_six_switches_ERA_relative_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03i_hWGXau1Y/results/stage03i_IT_Tor_six_switches_review_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03i_hWGXau1Y/stage03i_console.log
```

## Official FLUXNET meteorology QC definitions — now explicitly verified

Primary public source: [FLUXNET2015 FULLSET product variables](https://fluxnet.org/data/fluxnet2015-dataset/fullset-data-product/) and [SUBSET product variables](https://fluxnet.org/data/fluxnet2015-dataset/subset-data-product/).

For **half-hourly consolidated TA_F and VPD_F**:

- `*_F_QC=0`: original **measured** network data
- `*_F_QC=1`: **good-quality MDS gap-fill** (not a direct measured record)
- `*_F_QC=2`: **downscaled ERA gap-fill** (not an independent measurement)

Per FULLSET rule, `TA_F` is taken from `TA_F_MDS` if `TA_F_MDS_QC` is 0 or 1; otherwise it is taken from `TA_ERA`. Analogous VPD rule: `VPD_F` from `VPD_F_MDS` for MDS QC 0/1, else `VPD_ERA`. **Thus the six QC2−TA_ERA=0 findings are expected by product construction, NOT independent scientific corroboration.** The scientifically meaningful uncertainty is the **cold (−6.81 to −14.10°C) QC1 MDS filling method** relative to the packaged ERA branch and the 1,458-HH mixed-fill continuity. The historical [Stage26 three-site trial](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage26/26_three_site_MET_conservative_trial.py) already protected original QC0 and refused arbitrary long-run interpolation. Do **not** override that policy.

Important caveat: the user's IT-Tor ICOS-FLUXNET v1.3 r1 release follows a more recent network release than original FLUXNET2015 docs; the script should **verify the actual release's `TA_F_MDS`/QC and VPD source columns** when present, and report missing fields rather than assuming metadata are identical.

## Stage03J — verify exact source product consolidation on six existing events ONLY

[Stage03J source MDS-vs-ERA consolidation verifier](../scripts/03j_IT_Tor_six_original_MDS_vs_ERA_source_rules_PRIVATE_READONLY.py):

- Consumes **only** the user's already-completed Stage03H event JSON, its exact **54 private half-hour boundary/context rows**, and completed Stage03I JSON
- Validates SHA256 of original Stage03H private reports stored in Stage03I, validates original six event identities and QC1/2 transitions
- Streams **IT-Tor original network FLUXMET product once**, selects ONLY those 54 context timestamps and captures relevant consolidated `TA_F`, `VPD_F`, source `*_F_MDS`, `*_F_MDS_QC` and packaged `*_ERA` columns **if available**
- Rechecks that original rows have not changed from Stage03H and, for each event, verifies QC1 consolidated values came from original MDS if source columns exist, QC2 from packaged ERA, matching the official rule. Confirms VPD separately, and flags absent source MDS fields explicitly
- Writes one PRIVATE JSON report and one PRIVATE 54-row CSV in a new empty HOME directory, prints six summary outcomes. **No edits, alternative forcing candidates, independent ERA requests or model jobs.**

If Stage03J confirms the original release's source selection, classify these six source transitions as **MDS↔ERA method splice artifacts for targeted science review**, not as newly introduced Stage28 errors. Whether to keep MDS, evaluate independent station observations, or formulate a scientifically justified QC1-only sensitivity trial is a separate decision. Never blanket-replace 558 original QC1 half-hours or the entire 1,458-HH interval based solely on packaged ERA discrepancy.

Separate open scientific issues: IT-Tor original ten-layer `ORGANIC=0`, DE-Gri 49 original MDS holds, DE-RuR/ES-Agu precipitation accumulation time, and four-site candidate surface/active case gates. No AD5/AD400 model submission approved.
