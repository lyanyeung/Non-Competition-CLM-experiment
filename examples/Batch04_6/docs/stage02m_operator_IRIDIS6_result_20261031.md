# ICOS Batch04 CH-Aws — Stage02M selected-event VPD and ERA comparison (31 October 2026)

**Evidence scope:** operator-pasted, source-verified IRIDIS6 run of Stage02M; saved private JSON and CSV were not independently inspected. `STAGE02M SELF-TEST PASS`, 20 high-QBOT-difference events × 7 distinct forcing input-path groups = 140 candidate model values, no source/CIME/Slurm changes.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02m_WIktbwfu/results/stage02m_ERA_gapfill_revision_evidence.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02m_WIktbwfu/results/stage02m_seven_forcings_twenty_events.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02m_WIktbwfu/stage02m_console.log`

## Source-relative diagnostic MAEs

All in hPa. Selection is **conditioned on large between-version QBOT discrepancies**, so these are *not* unbiased site-wide forcing error estimates or model skill scores.

| Forcing path group (case) | MAE vs `VPD_F` at FLUXMET TIMESTAMP_START (QC=1, processed/gap-filled) | MAE vs distributed `VPD_ERA` | Scientific status |
| --- | ---: | ---: | --- |
| `SPINUP500_11P` numerical baseline | 0.003395 | 6.571395 | HOLD |
| RH21A | 0.003395 | 6.571395 | HOLD |
| RH25A (also RH25A diagnostic case: same DATM paths) | 0.003395 | 6.571395 | HOLD |
| RH29A | 0.003395 | 6.571395 | HOLD |
| RH34A | 3.254642 | 4.231642 | HOLD |
| RH38A_CONT2016 | 4.791294 | 3.272194 | HOLD |
| RH42A_V8_CONT2016 | 7.762150 | 1.194150 | HOLD |

The first four path groups show identical behavior **only for these 20 selected timestamps**. They are not necessarily identical throughout 2006–2024. The RH34A/38A/42A changes progressively favor the distributed `VPD_ERA` numeric source at high-difference events; **numerical proximity to ERA or to gap-filled `VPD_F` is not evidence of native tower accuracy, scientific repair approval or true independent ERA5-Land site representativeness**.

## Event-level source and ledgers

All 20 examples had `VPD_F_QC` raw **1**, `RH` unavailable, `VPD_ERA` numeric available and an exact-time candidate revision-ledger row. Counting Stage02I-matched revision records, the operator output showed **20 exact-time matches plus 17 ±30/60-min context matches** in total. These are candidate matched records, not independently approved repair decisions. The nearest candidate to the ERA-product VPD was:
- **RH34A** for the 2007–2008 anchor events (E001, E002, E004, E005, E007, E008, E009).
- **RH38A_CONT2016** for selected 2017 anchors (E015–E019).
- **RH42A_V8_CONT2016** for 2016 and 2018–2020 anchors (E003, E006, E010–E014, E020).

At E001 (2007-07-22 07:30), the distributed `VPD_F=11.247` hPa vs `VPD_ERA=1.497` hPa differ by **9.750 hPa**; the old reference-model VPD was approximately 11.253 hPa. Such an extreme product conflict demands independent source/QC and site-grid representativeness review. Stage02M's "closest" field means numerically closest **among unapproved candidates**, not an approved or best physical answer.

## Priority for next audit

Read the **original Stage34/38/42 repair CSV rows and associated JSON manifests**, including exact site records, QC semantics, source comparisons and any human review/HOLD references; independently verify declared ledger SHA256 where possible. Join actual rows by exact candidate time and retain all unverified source-time conventions; do not rely exclusively on Stage02I's selected columns or assume all included columns are observation values. Review the product's explicit BIF data dictionary and native tower source `RH` provenance if available. Consider targeted physical response and discontinuity across neighboring 30-minute records before any repair acceptance.

[Stage02N read-only ledger provenance audit](../scripts/02n_CH_Aws_revision_ledger_sha_QC_forensic_readonly.py). There is **no scientific release**, no model/forcing edits, no case choice and no Slurm job authorization. All six ICOS Batch04 sites remain HOLD.
