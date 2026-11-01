# ICOS Batch04 — reuse the earlier FLUXNET 13-site QC and add five-AmeriFlux-batch delta science checks (1 Nov 2026)

## Why we are changing strategy

The operator correctly challenged the repetition in Stage03A and the proposed wide-FLUXMET Stage03B. The four sites **DE-Gri, DE-RuR, IT-Tor and ES-Agu were already studied together** in the user's `lyanyeung/CLM-FATES-single-site-workflows/examples/FLUXNET_MultiSite_13`. This is not a new meteorological-data cohort. **Do not rerun full generic FLUXMET HH QC or reconstruct original v5 blindly.**

Historical source-of-truth documents:

- [13-site README](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/FLUXNET_MultiSite_13)
- [MET Stage20–28 final selected parent and scientific open issues](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/docs/MET_STAGE20_28_METHOD_AND_OPEN_ISSUES.md)
- [BIF/ZBOT DATM Stage23–30 provenance, true original TA sensor heights and 271 files](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/docs/BIF_HEIGHT_ZBOT_DATM_STAGE23_30.md)
- [Stage28 scientific selection code](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage28/28_onepass_remaining7_MET_finalize.py)
- [Stage29b DATM + BIF dynamic height code](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage29b/29b_onepass_13site_dynamic_static_ZBOT_DATM.py)

The Stage28 selected forcing is descended from **Stage26 -> Stage22 whole-QC1 envelopes** (which in turn tracks the Stage20 58 additional half-hour edits, including 11 in DE-Gri). The Stage28 pass made **zero new** bounded edits in the seven-site trial, while preserving the inherited selected versions for all 13. Stage28 was **13/13 numerical hard-QC PASS**, NOT original-tower-measurement scientific certification. Stage29b generated complete DATM for 11 BIF-supported sites, Stage30 added two non-BIF-height cases, totaling 271 annual files. Each NetCDF preserves Stage28 MET hash and BIF ZBOT policy metadata; using raw FLUXMET_HH alone would discard the old decisions and cause duplicate effort or wrong comparisons.

Historical original Stage28 reports (private IRIDIS6):
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/FLUXNET_MultiSite_13_MET_stage28_20261018_052344_851367/reports/`
- `01_selected_13site_STAGE28_provisional_manifest.csv`
- `02_all13_full_numeric_QC_after_stage28.csv`
- `03_13site_science_risk_and_decisions.csv`
- `08_DEGri_FILet_82_MDS_original_blocks_science_pending.csv`
- `11_provenance_and_science_gates.json`

Historical DATM manifests:
- Stage29b: `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/FLUXNET_13_ZBOT_DATM_20261018_054150_1008203/reports/10_annual_full_DATM_SHA256_manifest.csv`
- Stage30: `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/FLUXNET_13_ZBOT_DATM_STAGE30_20261018_055940_1008203/reports/04_consolidated_13site_271_DATM_SHA256_manifest.csv`

## What historical QC has *actually* resolved — and what is outstanding

| Site | Historical meteorological source/QC done | Unresolved DELTA-QC / science check | BIF TA sensor ZBOT |
|---|---|---|---|
| **DE-Gri** | QC-v5, whole contiguous QC1 MDS run review, source QC0 donor and reanalysis crosschecks; Stage20 included **11** conservative candidate edits, Stage28 numeric PASS | **49 original MDS blocks** still scientifically unapproved; compare full QC1 envelopes, edges, source QC0, independent ERA5/Land only where truly needed; no blanket replacement | **2.0 m static** |
| **DE-RuR** | Stage28 inherited selected forcing, numeric PASS and annual DATM checked | **2012-07-27** measured rainfall event needs original P/P_F/P_F_QC, units/accumulation window and timing; check dynamic ZBOT epoch transitions | **dynamic**, first **2.58 m** |
| **IT-Tor** | Stage28 inherited selected forcing, numeric PASS | Preserve flagged high precipitation pending source/provenance/accumulation audit; **ten 0.0 ORGANIC soil layers** are separate soil science issue, not a met-QC failure | **1.8 m static** |
| **ES-Agu** | QC-v5 + earlier Stage12/Stage15 targeted source edits; Stage28 inherited selected forcing, numeric PASS | **2018-09-15** extraordinary rainfall concentration/accumulation interval source science question; verify selected Stage15/22/26 lineage and do not revert trial edits by selecting original FLUXMET | **2.7 m static** |

Stage03A (new Batch04) only located BIF/BIFVARINFO and FLUXMET_HH products; its `MISSING_OR_TOO_MANY_FIELDS` was the **140-field header-reader limit**, not evidence of source corruption. These old release files and previous source decisions must remain pinned; downloading a separate ERA5_HH is not automatically necessary if the old source-selected manifest and archived ERA evidence already suffice.

## Lessons from five AmeriFlux groups (apply incrementally, not blindly)

| Batch | Reusable strengthened science QC approach | How we apply it to these 4 ICOS sites |
|---|---|---|
| **AmeriFlux 01** | Preserve every native **QC0 edit** and physical low-RH/QBOT event with SHA+time+variable ledger; reanalysis divergence is a review flag, not automatic observed-value error | Recheck only unresolved QC0/near-zero RH and old Stage28 modified records |
| **AmeriFlux 02** | Explicit **site-local clock/UTC and dated BIF ZBOT**, hourly/half-hourly boundaries; distinguish actual original rain and ERA-filled rain | Priority DE-RuR dynamic TA-height epochs, all four precipitation accumulation times |
| **AmeriFlux 03** | Evaluate **same-time saturation consistency** of original T, VPD, RH with original QC0/QC1/MDS and ERA; consider cold/ice saturation; preserve whole gap-fill runs and protected HOLD | DE-Gri 49 original MDS blocks, IT-Tor alpine temperature/VPD; no pointwise repair inside a longer QC1 run |
| **AmeriFlux 04** | Repair invalid humidity using **paired source TA/VPD/RH and QC provenance**, protect measured temperature; independent ERA5-Land is distinct from source-packaged ERA5 | Target only physics-invalid events, not all original FLUXMET rows; no automatic source T replacement |
| **AmeriFlux 05** | Distinguish **raw source measurement, ONEFlux-consolidated/MDS and source-packaged ERA**, use BIFVARINFO to interpret quality codes; group HOLDs by contiguous episodes and require science decision | Versioned event ledger for DE-Gri gap-fills, DE-RuR/ES-Agu rainfall, IT-Tor mountain events; never auto-upgrade research numeric PASS into model science approval |

The 13-site Stage22 already implemented the whole-QC1-envelope topology. Reuse it rather than inventing a sixth variant. The five AmeriFlux batches' original raw site files and repairs are **not shared** with these four ICOS sites and their intervention thresholds/approval outcomes must not be silently ported.

## Immediate Stage03B-REUSE: preflight without generic meteorology rescan

[Stage03B-REUSE read-only source-lineage checker](../scripts/03b_reuse_FLUXNET13_stage28_stage29b_source_lineage_readonly.py) compares the **old 13-site Stage28 selected MET manifest** (four site source SHA256 values) and **old Stage29b/Stage30 original annual DATM manifest** against exactly the current four sites' Stage02C CIME input references, using saved Stage02D internal QC and Stage03A bounded discovery as audit prerequisites. It compares **all 74 annual filename/path pairs** in memory, SHA-hashes only **four historical selected MET files** and **three annual NetCDF samples per site** (12 total), then captures limited NC provenance attributes `stage28_meteorology_sha256`, `zbot_policy_sha256`, `provenance_status`. It does **not** reread all FLUXMET HH rows or re-audit 74 years of numerical weather fields.

If `STAGE28_MET_SHA PASS`, `CURRENT_PATH_MATCH 22/22,15/15,18/18,19/19` and representative source hash evidence passes, the old Stage28/29b source-QC provenance can be reused as the current Batch04 baseline. **That is not a new observational QC scientific PASS.** Proceed directly to an event-scoped **Stage03C-DELTA** auditing only inherited risk ledgers and targeted original source/QC0/ERA evidence; retain the precise original MET/NC SHA and all unapproved source decisions. If any lineage differs, inventory exact changed years/files and original provenance before any data fixes, without modifying anything.

No source data, unlicensed tower records, CIME, forcing, NetCDF or Slurm writes; outputs one new JSON+CSV only to a brand-new empty HOME report directory. No AD5/AD400 or IT-Tor soil release from this preflight.

## Already completed / not to be repeated

- GitHub PFT choices accepted for four sites, plus new isolated NATVEG100/CROP0 point-surface SHA256 verified 4/4.
- Original S30EXCL and S30SHARED cases' eight DATM static lists, 74 distinct annual file paths and stream XML examined; current cases still point to old surface.
- Stage03A wide FLUXMET header reader limit is not a source anomaly. Do **not** merge a proposed redundant Stage03B wide FLUXMET census as the next step.

Next after Stage03C only: independent site-specific unresolved scientific review, IT-Tor soil provenance, then new isolated correct surface/CIME case preflight before any new AD5 jobs.
