# OzFlux meteorological science-QC release gate — 2026-11-03

## Mandatory operator rule

**No OzFlux AD400 `prepare`, CIME `case.submit`, or other 400-year job until the full selected forcing has scientifically passed QC.** Once it passes, use **direct AD400 80×5 years** as requested, with **no separate AD5**. The earlier AU-ASM Stage04/05/07 passes, six-year provisional DATM internal physics, and Stage08 case `check` PASS were **not scientific forcing releases**. The historical direct400 script's older `prepare` / `submit` examples are superseded.

The direct AD400 script in [PR #64](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/64) has been changed in commit `cef48e79b8318a045285bf6dc3d9fd137b544480` to **FAIL CLOSED** for `prepare` and `submit`. An older operator-downloaded Python copy is *not* automatically updated; **do not use any old copy** to bypass this gate. No evidence exists in operator output that AU-ASM case creation or Slurm submission has occurred.

## From 5 AmeriFlux + 4 ICOS batches to OzFlux-specific QC

The prior `AmeriFlux_Batch01_10/scripts/59_three_site_extended_met_episode_audit.py` audited source tower versus ERA, QC, anomalous runs, and expanded before/after windows without promoting unverified donor data. `Batch02_10/scripts/22_ES_LJu_exhaustive_operator_review_tower_ERA_before_after_readonly.py` audited discontinuities, low-RH episodes, rain extremes and previous edits with full source/donor context. `Batch04_6/scripts/03z_de_gri_14_events_tower_ERA_before_after_PRIVATE_READONLY.py` inspected individual original QC classes, before/during/after weather and actual candidate data. These are methodology precedents rather than proof that every network's QC codes have identical meaning.

**OzFlux uses PyFluxPro L6 `*_QCFlag`, not ONEFlux QC0/1/2**. PyFluxPro 50 interpolation; 400 unspecified alternate; 410 AWS, 420 ACCESS, 430 ERA-Interim and 440 ERA5, per the upstream `OzFlux_MultiSite_09/scripts/stage05/05_qcflag_donor_independence_readonly.py`. Neither QC0 nor a model fill can be called independent raw tower truth without original sensor provenance.

**AU-ASM Stage09** in [PR #65](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/65): new `09_asm_native_met_source_event_review_READONLY.py` reads only source original L6 (SHA `b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb`) and Stage05 original-QC receipts; audits 42 year-variable rows over 2013–18, entire 420/440/50 and other QC runs, all source before/during/after context, same-prefix alternate sensor candidates, 2017 395-hour Fld ACCESS series, 2014/2016 source negative Fsd and peak wind, broad physics and humidity RH/VPD. Output is **FORCING_SCIENCE_HOLD** with no CIME/Slurm writes. Six Stage14 DATM hash receipts and source-to-DATM mapping were already independently checked in Stage04, Stage07, and upstream Stage13–14; any subsequent candidate must be versioned and independently cross-checked.

### Science-release requirements per selected OzFlux site

1. Immutable original L6/sensor NetCDF plus native timestamp, variable-unit and PyFluxPro source processing provenance; verify all chosen model years, calendar coverage and exact source-to-DATM mapping, including time-zone/interval semantics.
2. Per-variable/year missing, QC code frequencies, all long non-observation-filled events, valid donor availability and source independence, including before/during/after boundary continuity and off-season solar timing.
3. Derived humidity thermodynamics (TA, SH, ps, RH/VPD), Fsd and Fld physical/solar screening, precipitation accumulation/conservation and extremes, pressure and wind anomalies. Review all flagged events rather than silently rewriting source data.
4. If repair is justified, create a **separate versioned candidate** only with exact per-timestamp original/source/ERA/donor/decision ledger and SHA. Before promoting it, independently prove full-file invariance outside the exact approved scope, correct model-time joins, all variables' physical bounds, input compatibility, and no harm to previous approved edits.
5. Sign off an explicit source-specific operator science decision, with immutable inputs, results and remaining limitations, before releasing any **direct AD400** case action. Do not auto-release from a script exit code alone.

### Current AU-ASM mandatory HOLDs

- Fld 2017-08-17 22:00 to 2017-09-03 08:30: 395 hours continuous PyFluxPro QC420 ACCESS fill; must review original source, alternate sensor evidence and entry/exit joins.
- Fsd/Fld model fill periods 2014, 2016, 2018, including source before/after, retained QC lineage; 2014 359 and 2016 1 derived FSDS zero-floor corrections need the exact original event evidence.
- Original 2018 maximum wind 16.296 m/s; confirm original label/QC, duration and neighbors.
- Provisional local END - 585 min to UTC CENTER convention; solar fit alone is not independent time-source certification.
- Surface remains the GitHub Stage02 SHA-pinned selected PFT and unchanged gridded soil; this is a separate site-soil scientific limitation, **not a reason to mutate existing Surface**.

**Current disposition: `FORCING_SCIENCE_HOLD`; `science_release=false`; `AD400_authorised=false`; `AD5_required=false`.**

## Actual operator Stage09 science-audit result (2026-11-03)

Operator ran the exact Git blob `95a5d7f28ec20f8f36de2e1758a34e55a19ea540` on IRIDIS6; source-hash, syntax and selftest verified. Report: `/iridisfs/home/ly3n24/ozflux_nc_stage09_20261103T070958Z/`. 42/42 original source year-variable QC series reconciled with Stage05; 1,860 contiguous QC spells and 9,291 native meteorology source-context rows recorded; 2017 Fld 395h QC420 ACCESS run reproduced. Native source thermodynamics: RHwater>100% 0; RHwater>105% 0; VPD<-0.1 hPa 0; maximum RHwater 96.523%; source Fsd negative 360 records, corresponding to existing separate, original-preserving Stage14 FSDS0 correction ledger. Peak original Ws 16.29613 m/s at **native source label 2018-03-10 20:30:00**; peak wind by itself is not evidence of corruption. All 1,860 QC spells are *review evidence*, not automatically 1,860 scientifically faulty episodes. Operator reported **NO AU-ASM AD400 CIME case directory**, no model submission. Stage09 explicitly did **not** release forcing science QC.

Next: scrutinise full 395-hour Fld and all longest ACCESS/ERA5 radiation runs (especially 2014/16/18) and model-fill joins; rank the source native QC nonzero segments across all seven variables, check donor independence, and validate original source clock convention. Do not modify Stage02 Surface, original L6 or six Stage14 inputs. `FORCING_SCIENCE_HOLD` continues.

## Stage10 read-only event-priority summary (published; IRIDIS run pending)

Script: `scripts/10_asm_stage09_source_event_priority_and_boundary_READONLY.py`, Git blob `e951d27f47f01b6ef0c705759da908410e3bb3a8` (inside [PR #65](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/65)). Reads **actual successful Stage09 files only**, not inferred examples; pins the 42 year-variable, 1860 source event and 9291 original-context row counts, and validates the complete 2017 790-HH Fld QC420 source context. Produces read-only priority event ledger, annual PyFluxPro source-code proportions including 2018 precipitation, selected exact original boundary windows, and JSON science HOLD. Expected operator focus: long ACCESS/ERA5 Fsd/Fld periods and 2017 FLDS, strongest original QC nonzero-year concentrations, donor availability labels (not donor-independent proof) and 2018 peak wind source context. **No corrections, CIME case, or Slurm jobs authorised.**
