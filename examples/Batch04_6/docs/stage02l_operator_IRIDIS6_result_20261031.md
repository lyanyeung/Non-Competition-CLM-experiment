# ICOS Batch04 CH-Aws — Stage02L 20-event seven-version source-clock summary (31 October 2026)

**Evidence origin:** operator-pasted IRIDIS6 console output. Original saved JSON/CSV are held in HOME but were not independently uploaded or inspected via GitHub. Source SHA verification and Stage02L regression self-test both PASS. The script produced 20 × 7 distinct-forcing-version data-point comparisons; no forcing inputs, CIME cases, Slurm or Git working files changed.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02l_PDjpMDmW/results/stage02l_source_clock_QC_matrix.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02l_PDjpMDmW/results/stage02l_seven_models_twenty_events.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02l_PDjpMDmW/stage02l_console.log`

## Exact printed Stage02L summary

| Metric | Operator result |
| --- | ---: |
| Number of selected high-QBOT-difference events | 20 |
| Mean abs difference, reference DATM VPD vs FLUXMET `TIMESTAMP_START VPD_F` | **0.0033947658 hPa** |
| Mean abs difference, reference DATM VPD vs FLUXMET `TIMESTAMP_END VPD_F` | **1.9789035422 hPa** |
| Maximum absolute START difference | 0.0069677784 hPa |
| Maximum absolute END difference | 7.3428081817 hPa |
| Reference within 0.01 hPa of START VPD_F | **20/20** |
| Reference within 0.01 hPa of END VPD_F | 1/20 |
| START closer than END | 19 |
| END closer than START | 0 |
| Exact error tie | 1 |
| START source `VPD_F_QC` raw values | **1 at 20/20 events** |
| START source `TA_F_QC` raw values | **0 at 20/20 events** |
| Numeric original-distribution `RH` present at selected START events | **0/20** |
| Numeric `VPD_ERA` present at selected START events | **20/20** |
| Verified native tower RH, actual clock convention, or release | **No** |

These 20 events were **selected for high QBOT changes**, not a statistically representative sample of all 2006–2024 half-hours. Conditional on the standard FLUXNET2015 definitions, `VPD_F_QC=1` marks high-quality gap filling, *not* original measured VPD; `TA_F_QC=0` indicates observed TA for the same selected rows. Verify these meanings against this EUF product's own metadata before making science approval decisions. Extremely close numerical agreement indicates the unapproved reference forcing likely inherited the **START-indexed processed VPD_F**, not that the reference is more accurate.

The presence of a numeric `VPD_ERA` in all 20 rows enables a separate comparison with an ERA-derived **context series**, but it does NOT validate ERA5-Land collocation, the instrument source, source QC, or a model version. Likewise `RH` absent at all 20 event anchors blocks an original-tower-RH repair justification from these distributed FLUXMET rows alone.

## Next decision gate

Use [Stage02M read-only multi-source matrix](../scripts/02m_CH_Aws_seven_forcings_ERA_and_repair_ledger_readonly.py) to:
1. Compare all seven candidate DATM VPD values numerically with START-indexed processed `VPD_F` **and** `VPD_ERA` at the same 20 selected anchors, retaining QC and clock uncertainty.
2. Join the existing Stage02I candidate Stage34/38/42 revision-ledger rows by verified *event ID* only; display exact-offset rows distinctly from ±30/60-minute context, without treating any match as an independently verified tower observation.
3. Produce a per-variant **diagnostic** mean absolute difference for both sources, never a scientific ranking or automatic "best" forcing, and preserve missing RH as a source-data HOLD.

Next after Stage02M: verify actual native tower unfilled RH/TA measurements and their QC/chronology, Stage34/38/42 scientific justification, ERA source provenance/units and effective DATM stream. All six Batch04 sites remain science HOLD. No AD5/AD400, no forcing repair, no change to original case/source or parameter mapping.
