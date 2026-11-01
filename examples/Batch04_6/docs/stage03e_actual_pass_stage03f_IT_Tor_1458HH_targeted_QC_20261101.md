# ICOS Batch04 — Stage03E actual result, targeted IT-Tor Stage03F source-run audit (2026-11-01)

## Verified operator Stage03E outcome

The operator ran the Stage03E helper against the previously completed, private Stage03D JSON. Actual `FULL PYTHON SYNTAX PASS`, `STAGE03E SELF-TEST PASS`, and the final read-only science HOLD summary all succeeded. The two one-row rainfall examples printed before the self-test PASS were **synthetic test cases only**. The actual Stage03E result, printed after self-test PASS, is:

| Site / event | Matched source and selected Stage28 half-hours | Both numeric | Numerically equal | Different | Scientific rain accumulation/clock |
|---|---:|---:|---:|---:|---|
| DE-RuR, **2012-07-27** | **48** | **48** | **48** | **0** | **HOLD** |
| ES-Agu, **2018-09-15** | **48** | **48** | **48** | **0** | **HOLD** |

This confirms **at the source-product label timestamp** that all 48 half-hourly values on each selected calendar day were passed into Stage28 unchanged within the scripted numerical equality tolerance. It **does not** prove that source `P_F` records are true original *instrument* half-hour accumulations or that time labels independently correspond to station UTC/local standard time. Old >18 mm/HH historical rain review candidates still comprise DE-Gri **12**, DE-RuR **1**, IT-Tor **2**, ES-Agu **5** (=20). A high numerical rain value is not in itself a physically invalid reading.

DE-Gri: **49 original MDS/QC1 scientifically pending blocks** have now been ranked using existing source/Stage28 context, not repaired or approved.

IT-Tor: **2025 Oct–Nov contains 2,928 HH**; `TA_F_QC` and `VPD_F_QC` each split into QC0/QC1/QC2 **1,441/587/900**. `P_F_QC`: QC0 **1,440**, QC2 **1,488**. These are not physical error counts, and the old Stage27 **1,458-HH** episode's exact start/end have **not** yet been independently located.

Private output (do not commit these licensed measurements):
```
/home/ly3n24/ICOS_Batch04_stage03e_vHjmkT3O/results/stage03e_4site_private_event_science_HOLD_summary.json
/home/ly3n24/ICOS_Batch04_stage03e_vHjmkT3O/results/stage03e_DE-RuR_ES-Agu_focus_rain_HH_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03e_vHjmkT3O/results/stage03e_DE-Gri_49_source_MDS_prioritized_PRIVATE.csv
```

## Why Stage03F is narrow

There is no justification to repeat Stage20–28 full meteorology QC, redo the full 2008–2025 IT-Tor forcing numeric audit or reconstruct 74 files. The old [FLUXNET13 Stage26 trial](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage26/26_three_site_MET_conservative_trial.py) already distinguishes entire source QC1/QC2 fill runs, requires original genuine QC0 anchors for *bounded* hypothetical repairs, and explicitly **refuses** automatic repair of long intervals. [Stage27 frozen source inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage27/27_freeze_13site_met_provisional.py) documents the **1,458-HH** IT-Tor source transition as a scientific HOLD but does not encode an exact timestamp interval in the code.

[Stage03F — IT-Tor 2025 Oct–Nov ORIGINAL QC1/QC2 contiguous run audit](../scripts/03f_IT_Tor_2025_original_QC12_1458HH_interval_readonly.py) therefore:

- reads the previously saved Stage03D private JSON and Stage03E private summary as strict prerequisites, confirming the historical **2,928 HH**, QC category totals and source/Stage28 path evidence;
- streams only IT-Tor's original network-product CSV and old Stage28 selected meteorology CSV once each, keeping only **2025-10-01 to 2025-11-30**, not rereading other site data or reconstructing the 74 DATM files;
- identifies maximal **consecutive 30-min** intervals for paired TA/VPD QC1-or-QC2, paired QC1 only, paired QC2 only, VPD QC1-or-QC2 and P_F QC2;
- records each run's exact start/end/length and whether **both immediately adjacent** original TA+VPD values have QC0 flags (QC0 flag is provenance, not independent proof);
- prints longest paired QC1/QC2 runs and whether **exactly 1,458 HH** occurs in the chosen definition; even if it does, reports only a **duration-matched candidate**. Old Stage27 identity remains unproven without historical original event start/end;
- summarizes, by original TA/VPD QC0/1/2 class, counts of **numerically equal/different** original selected fields to the old Stage28 file at matching source labels; these are QC context statistics, not a new approval, ERA validation or physical correction.

Output is one JSON and one CSV under a **new private HOME directory**, with no original source, Stage28 CSV, DATM NetCDF, CIME, PFT, FATES, Slurm or model-run writes. Do not add private numerical outputs to GitHub. All source, clock, soil `IT-Tor ORGANIC=0 for all 10 layers`, and observational science HOLDs survive.

**Further unresolved independent work:** original meteorological instrument-level rain accumulation/time provenance for DE-RuR and ES-Agu (P_F=Stage28 is only data-lineage confirmation); human review of the 49 DE-Gri MDS scientific holds; specific IT-Tor original long-run interpretation and whether physical T/VPD/RH and ERA evidence warrants intervention. No automatic replacements, rain reshaping or AD5/AD400 submissions.

Current Batch04 status: 6/6 observed-model proxy PFT decisions, 4/6 new point surface candidate NetCDF SHA verified, 0/6 isolated new case submissions.
