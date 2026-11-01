# ICOS Batch04 — Stage03D completed: old precipitation and targeted met-QC source contexts (1 November 2026)

## Source-verified actual result

The user's IRIDIS6 log confirms Stage03D v3 Python syntax and self-test PASS followed by a complete read-only event-scoped inspection of original FLUXNET13 source products and the already Stage03B SHA-verified Stage28 forcing. Final line: `STAGE03D SOURCE_CONTEXT_ONLY; SCIENCE_HOLD. NO FORCING/NETCDF/CIME/SLURM CHANGES`.

- Both **Stage21 original** and **Stage22 inherited** rainfall audit reports exist. The Stage03C `OLD_RAIN_LEDGER MISSING` finding was a **filename/path search bug**, not absent source science work.
- **20 historical precipitation exceedances above 18 mm per half-hour** were recovered for these four sites: **12 DE-Gri**, **1 DE-RuR**, **2 IT-Tor**, **5 ES-Agu**. These are historical **review candidates**, not twenty demonstrated bad rain-gauge readings.
- DE-Gri: **49/49** original MDS HOLD episodes overlap original source and selected Stage28 forcing records. Stage28 also retains its older 14 met-flag cases; no automatic ERA replacement/repair.
- DE-RuR: **1/1** targeted original vs Stage28 context present; the historical **2012-07-27** date has **1** old >18-mm/half-hour rainfall observation. **Dynamic BIF TA sensor height ZBOT** remains a separate science/dated mapping caveat.
- IT-Tor: **1/1** original vs Stage28 context present for **all 2025 Oct–Nov** (61 days, **2,928** half-hours). Source `TA_F_QC` and `VPD_F_QC` each have QC0 **1,441**, QC1 **587**, QC2 **900**; source `P_F_QC` has QC0 **1,440**, QC2 **1,488**. **These are quality/provenance code distributions, not physical fault counts.** Do NOT equate all 2,928 source hours to the separate earlier **1,458-HH** QC1/QC2 discontinuity flagged in Stage27: the exact historical subinterval still needs locating. Also **2** historical >18-mm rain observations. The separate all-ten-soil-layer `ORGANIC=0` science issue remains open.
- ES-Agu: **1/1** original vs Stage28 context present; **3** of the 5 historical >18-mm rain observations fall on **2018-09-15**. Preserve Stage28 inherited Stage12/15 meteorology choices and never redistribute the rain gauge accumulation automatically.

**Data handling:** The complete Stage03D source measurements, per-HH rain and private QC details stay at these IRIDIS6 paths **and must not be committed to this public GitHub repository**:

```
/home/ly3n24/ICOS_Batch04_stage03d_v3_olZidJdj/results/stage03d_four_site_targeted_original_met_rain_MDS_source_review_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03d_v3_olZidJdj/results/stage03d_four_site_legacy_rain_events_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03d_v3_olZidJdj/results/stage03d_four_site_target_window_counts.csv
```

## Next: summarize existing evidence only (Stage03E)

[Stage03E narrow PRIVATE source-evidence summary script](../scripts/03e_summarize_existing_Stage03D_private_rain_MDS_QC_no_reread.py) reads **the already completed Stage03D saved JSON only**. No further original FLUXMET CSV, historical Stage28 source, old Stage21 reports, or 74 annual NC rereads.

It creates under a NEW EMPTY private HOME folder:
- `stage03e_4site_private_event_science_HOLD_summary.json`: only source-QC count summaries, inherited past science caveats, no raw half-hourly tower values
- `stage03e_DE-RuR_ES-Agu_focus_rain_HH_PRIVATE.csv`: **actual focus-date** original `P_F/P_F_QC` and Stage28 `PRECTmms × 1800` paired half-hour values, for checking **amount agreement only**, not assuming 30-minute accumulation semantics
- `stage03e_DE-Gri_49_source_MDS_prioritized_PRIVATE.csv`: 49 exact original HOLD windows, source QC categories and selected-T/VPD ranges; the QC counts include the script's **2-hour event context padding**, so they are a triage priority not science-error scores.

The full `2025 Oct–Nov` source QC categories are already established; do NOT redo the 2,928 HH scan. A separate future narrow Stage03F must use the **old exact source transition ledger**, or old Stage27 underlying event/audit, to locate the original **1,458 HH** interval before attempting any repair. Do not infer its start/end from entire October/November source QC counts.

No original QC0 overwrite, ERA5/ERA5-Land replacement, precipitation redistribution, PFT surface/CIME case edit or Slurm submission. Scientific forcing and IT-Tor soil HOLD remain, even though the Stage28/30 model forcing SHA and internal QC passed.

**Portfolio status:** Batch04 PFT scenarios selected 6/6, newly generated PFT point surfaces SHA-verified 4/6, no new isolated AD5/AD400 cases submitted 0/6.
