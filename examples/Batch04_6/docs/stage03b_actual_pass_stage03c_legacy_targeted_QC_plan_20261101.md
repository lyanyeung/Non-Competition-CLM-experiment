# ICOS Batch04 — Stage03B-REUSE operator PASS and Stage03C targeted old-issue ledger (2026-11-01)

## Confirmed actual IRIDIS6 output

Operator ran the merged Stage03B-REUSE against the original `FLUXNET_MultiSite_13` Stage28, Stage29b and Stage30 data and the current Batch04 Stage02C/D/03A evidence. Results:

| Site | Stage28 selected MET SHA | All CURRENT vs historic DATM paths | 3 representative yearly NC SHA |
|---|---|---|---|
| DE-Gri | PASS | **22/22** | **3/3** |
| DE-RuR | PASS | **15/15** | **3/3** |
| IT-Tor | PASS | **18/18** | **3/3** |
| ES-Agu | PASS | **19/19** | **3/3** |

`STAGE03B-REUSE SELF-TEST PASS`; source-verified old MET files `4/4`, current 74 DATM file paths `74/74`, sampled NC hashes `12/12`. **The four sites do not need fresh generic FLUXMET processing**, and their previously selected Stage28/Stage30 meteorology/ZBOT scientific evidence is directly reusable. Source-observation **scientific approval is still HOLD**: original Stage28 numeric QC PASS was explicitly provisional.

Private IRIDIS6 reports:
```
/home/ly3n24/ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json
/home/ly3n24/ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_old_vs_current_DATM_matrix.csv
/home/ly3n24/ICOS_Batch04_stage03b_reuse_PbMYw9CH/stage03b_reuse.log
```

## Scientific items already known from original FLUXNET 13-site reports

Original source of truth:
- [Old Stage20–28 met-QC method and hold list](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/docs/MET_STAGE20_28_METHOD_AND_OPEN_ISSUES.md)
- [Old Stage23–30 source BIF TA-height / DATM](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/docs/BIF_HEIGHT_ZBOT_DATM_STAGE23_30.md)
- [Old Stage27 frozen meteorology source/priority](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage27/27_freeze_13site_met_provisional.py)
- [Old Stage28 selected numerics, original MDS and rain/temperature ledgers](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage28/28_onepass_remaining7_MET_finalize.py)

| Site | Precise inherited issue to investigate further | What NOT to repeat |
|---|---|---|
| **DE-Gri** | Original 49 pending Stage22/28 MDS flagged blocks; examine complete source QC1 spans, original QC0 donors and old already tested paired ERA5/ERA5-Land evidence; protect old 11 Stage20 changes | No re-run of generic QC-v5, no blanket ERA substitution |
| **DE-RuR** | **2012-07-27** original measured-source rain and accumulation/clock; BIF TA-height **dynamic**, initial **2.58m**, preserve exact effective dates/point ZBOT | No forced fixed-ZBOT, no automatic rainfall clipping |
| **IT-Tor** | The old Stage27 explicitly records **2025-10/11 long QC1 vs QC2 source discontinuity involving 1,458 half-hours**; plus heavy-rain provenance; separate inherited soil **ORGANIC=0 ten layers** science HOLD | Do not mistakenly classify everything as precipitation-only, no replacing entire long fill with one ERA series |
| **ES-Agu** | Old **2018-09-15** extreme source rain and original interval/aggregation; preserve earlier Stage12/15/22/26 choices under selected Stage28 | Do not revert to raw FLUXMET or redistribute accumulation automatically |

The original Stage28 code generated `03_13site_science_risk_and_decisions.csv`, `08_DEGri_FILet_82_MDS_original_blocks_science_pending.csv`, `09_DEGri_FILet_stage22_whole_envelope_decisions.csv`, `10_all13_remaining_temperature_pressure_rain_RH_flags.csv` and a **seven-site** `07_7site_heavy_rain_PROVENANCE_NO_EDITS.csv`. Because that last file only covers seven Stage28 target sites, it **must not** be treated as an all-13 no-rain certificate for DE-RuR, IT-Tor, ES-Agu. Stage22 `06_all_precip_gt18mm_source_timing_review.csv` contains the copied earlier 13-site precipitation provenance if actually present; an absent file is a **provenance gap**, not zero precipitation.

## Next: Stage03C historical unresolved science episode extraction (READ ONLY)

[Stage03C script](../scripts/03c_reuse_FLUXNET13_old_MDS_rain_BIF_hold_episode_register_READONLY.py) consumes the **completed** Stage03B-REUSE report and existing historical Stage22/28/29b ledgers. It validates that all 4 met SHA/path/representative NC gates are PASS, 82 exact historical MDS block identities agree between Stage22 and Stage28, and **69 total / DE-Gri 49 still pending** remain preserved. It reads only historical reporting CSV, **not source sensor measurements or full FLUXMET**; extracts site-scoped issues and historical decisions, plus remaining temperature/RH flags and dated BIF height references. It adds explicit historical hold entries for 2012/2018 rainfall, IT-Tor's 1,458-HH QC1/QC2 transition, DE-RuR dynamic TA-height and IT-Tor soil zero ORGANIC.

Three new output files in new empty HOME dir:
- `stage03c_four_site_inherited_science_HOLD_episode_index.json`
- `stage03c_four_site_QC_incremental_scope.csv`
- `stage03c_four_site_original_source_event_HOLD.csv`

Stage03C **does not make new observational QC decisions**, modify the previous Stage28 selected CSV, Stage30 74 DATM, candidate PFT point surfaces, CIME, shared FATES, original source data or Slurm. All old manual HOLDs and decisions retain their status. After its output, we can implement a **Stage03D event-level science comparison**, reading **only targeted original HH source intervals and independent evidence** already relevant under the five AmeriFlux methodologies: original QC0/QC1 anchors, source vs processed ERA distinction, full gap-fill boundaries, saturation and humidity thermodynamics, precipitation units/accumulation-time and dynamic dated BIF ZBOT. Manual operator choices only if genuinely ambiguous. No new AD5/AD400 until separate source-science/soil and CIME binding gates.

**Current model status:** 6/6 selected model PFTs; 4/6 new GitHub-approved point-surface candidates SHA-verified; **0/6 new isolated FIXNC AD5 submissions**. CH-Aws source-RH and GL-ZaH site-only Arctic FATES remain separate.
