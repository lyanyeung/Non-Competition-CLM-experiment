# ICOS Batch04 — Stage03C actual IRIDIS6 HOLD inventory, Stage21 rain source recovery and Stage03D targeted science windows (1 Nov 2026)

## Actual Stage03C evidence

The source-verified Stage03C reuse script ran successfully on IRIDIS6; original Stage28/Stage30 forcing remained untouched. It produced **95 science-HOLD action rows**, which are source/documentation review tasks, **not 95 verified instrument faults or unique timestamp events**.

| Site | Old unresolved Stage22 MDS original blocks | Stage28 remaining met-flag rows | Stage29b ZBOT-year audit rows | Current main science risk |
|---|---:|---:|---:|---|
| DE-Gri | **49** | **14** | 22 | 49 original full-contiguous QC1/MDS source intervals and boundary evidence |
| DE-RuR | 0 | 1 | 15 | 2012-07-27 precipitation accumulation/clock and dated TA-sensor height ZBOT |
| IT-Tor | 0 | 7 | 18 | 2025 Oct/Nov QC1/QC2 source discontinuity, 1,458-HH historical interval; high rain; separate 10-soil-layer ORGANIC=0 |
| ES-Agu | 0 | 5 | 19 | 2018-09-15 exceptional precipitation and legacy Stage12/15 source repairs |

Actual private report paths:
- `/home/ly3n24/ICOS_Batch04_stage03c_hONXeEmQ/results/stage03c_four_site_inherited_science_HOLD_episode_index.json`
- `/home/ly3n24/ICOS_Batch04_stage03c_hONXeEmQ/results/stage03c_four_site_QC_incremental_scope.csv`
- `/home/ly3n24/ICOS_Batch04_stage03c_hONXeEmQ/results/stage03c_four_site_original_source_event_HOLD.csv`
- `/home/ly3n24/ICOS_Batch04_stage03c_hONXeEmQ/stage03c_console.log`

Stage03B source verification already established **4/4 original selected Stage28 MET SHA**, **74/74 annual Stage30 DATM paths**, and **12/12 sampled annual NetCDF SHA** matching. Stage02D internal numerical QC and Stage03A site-source listing are also complete. Repeating the original full FLUXMET/QC-v5/74 annual NC scans is not useful.

## Root cause of the four OLD_RAIN_LEDGER MISSING results

**Stage03C looked at a filename that the old Stage22 never claimed to create.** The historical Stage21 source script in
[old FLUXNET13 Stage21](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage21/21_onepass_13site_meteorology_remaining_preBIF.py)
actually wrote:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/FLUXNET_MultiSite_13_meteorology_stage21_trial_v1_20261015/reports/06_all_precip_gt18mm_source_timing_review.csv`

The older [Stage22 code](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage22/22_onepass_full_QC1_envelopes_preBIF.py) read that source and wrote a renamed inherited copy to its reports:

`INHERITED_STAGE21_06_all_precip_gt18mm_source_timing_review.csv`

under `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/FLUXNET_MultiSite_13_stage22_retry_20261018_041156_893243/reports/`.

Stage03C tried the **unprefixed** `06_all_precip_gt18mm_source_timing_review.csv` in Stage22's directory, so its `OLD_RAIN_LEDGER MISSING` is a **path-lookup false negative**, provided the original files still exist. This should not erase old precipitation review results or imply zero historical high-rain events. The new Stage03D checks both actual locations and requires byte-identical SHA256 if both are present. The old report is a **network-product original P_F/P_F_QC vs provisional selected rain source/timestamp diagnostic**, not independently confirmed rain-gauge temporal accumulation.

## Stage03D: only target prior HOLD event windows

[Stage03D read-only targeted source-event audit](../scripts/03d_recover_Stage21_rain_and_targeted_4site_source_event_context_READONLY.py) requires the operator's Stage03B and Stage03C private JSONs. It verifies four historical lineage gates, Stage03C's exact 49 original DE-Gri MDS HOLDs, the **13-site** original source manifest `$HOME/FLUXNET_13_input_audit/site_input_summary.csv` and original Stage28 selected manifest. It checks Stage21/Stage22 inherited rain provenance, recovers old >18 mm events for all four sites without recreating them, and makes **one streaming pass per original source and selected Stage28 CSV**, extracting only named event windows. This is a selection/filtering pass, not a new full-series QC or source repair.

- **DE-Gri**: all **49** known MDS episode intervals, with two-hour boundary context, source TA_F/TA_F_QC/VPD_F/VPD_F_QC/ERA column statistics and selected Stage28 TA_USE/VPD_USE ranges; old QC0 records and HOLD unchanged
- **DE-RuR**: **2012-07-27** precipitation focus with one-day before/after; paired source P_F/P_F_QC against Stage28 PRECTmms `×1800` mm/30 min, plus original dynamic TA-height science note
- **IT-Tor**: **2025-10-01 through 2025-11-30** source QC1/QC2 transition focus; record source QC distribution, selected forcing continuity summary and first/last samples without claiming the 1,458-HH precise sub-interval was numerically proved; 10-layer zero soil ORGANIC remains separate HOLD
- **ES-Agu**: **2018-09-15** rainfall with one-day before/after, original source P_F/QC and selected Stage28 mm/30 min, preserving all old Stage12/15 edits

All original source-product rows and selected force values remain in a **PRIVATE, new, empty IRIDIS6 HOME report directory**; do not commit them or distribute them publicly. Stage03D prints only event counts, source presence and QC summary counts, and outputs:

- `stage03d_four_site_targeted_original_met_rain_MDS_source_review_PRIVATE.json`
- `stage03d_four_site_legacy_rain_events_PRIVATE.csv`
- `stage03d_four_site_target_window_counts.csv`

**Scientific limitations:** a source `P_F` exactly equal to selected rain is not proof that it represents 30-minute accumulation; old network-product `TA_F/VPD_F` and QC flags are not necessarily direct native sensor measurements; equal naive timestamps are not independent UTC-clock validation. Source-packaged `TA_ERA/VPD_ERA` cannot be treated as independent ERA5-Land corroboration. A past Stage28 numerical PASS does not approve the underlying observations or filled periods. No automated RH/temperature/precip changes; no new CIME, forcing, surface, FATES, Slurm or AD5/AD400 work.

**Model status unchanged:** PFT model choices 6/6, four new point PFT surfaces SHA-verified, 0 new Batch04 isolated model cases submitted. Later human decisions should concern only evidence-inconclusive or physically invalid old HOLD events; IT-Tor soil and CH-Aws/GL-ZaH are independent tracks.
