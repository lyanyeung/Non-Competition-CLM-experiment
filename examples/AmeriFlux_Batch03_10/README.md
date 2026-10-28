# AmeriFlux Batch03 (10-site cohort): forcing-source QA handoff

This is a **cross-repository status pointer**, not a model-input or spin-up approval. It intentionally does **not** reuse the existing `examples/Batch03_10` directory, which serves a different cohort.

## US-Me6 evidence, 27 October 2026

The actual AmeriFlux Batch03 source-QA workflow and pinned Python programs live in [CLM-FATES-single-site-workflows / AmeriFlux_MultiSite_10_Batch03](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10_Batch03). Stage13X has completed an original tower QC0 versus paired ERA RH evaluation and original 2017 QC2-boundary review; it is science-only.

- Twelve 2015 original QC1 source runs / 235 native half-hours were **previously operator-approved in a separate Stage13S research shadow**. Preserve the exact original SHA and do not overwrite.
- Six original source QC1 runs (IDs 12, 14, 15, 16, 17, 18), 782 half-hours total, **still HOLD**. Stage13V/13W identify 768 source ERA-RH physical pointwise passes and 14 native hours failing the strict source site-versus-ERA T difference threshold of 8 C. Pointwise pass is not whole-run acceptance or license to write forcing.
- Stage13V reports 11 provisional contiguous science subepisodes, of which **one** has two directly observed QC0 borders. This is a **potential human-review candidate**, not authorization.
- All eight immediate 2017 VPD QC2 source boundaries remain **unapproved for substitution**, including cases where candidate and retained VPD differ by more than 4 hPa.
- Five historical Stage12AC Jul-2017 half-hours remain protected. No Post-v5 promotion, DATM, AD400, Slurm or model submission is approved for US-Me6 here.

## Stage13Y: strict human review gate

[Python: 13y_Me6_eleven_subepisodes_operator_gate_READONLY.py](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/f12472a2cb174d0fb9f19a9d73e39f8c6c3dc9f3/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13y_Me6_eleven_subepisodes_operator_gate_READONLY.py) examines SHA-sealed actual Stage13V and Stage13X reports and writes **reports only**. Its `--self-test` and `--check` are read-only. A separate new operator-approved forcing change would require independent review.

Run the [Stage13Y mobile-safe pinned runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13y_Me6_mobile_science_gate_READONLY.sh) on IRIDIS6. It downloads the exactly pinned Python commit `f12472a2cb174d0fb9f19a9d73e39f8c6c3dc9f3`, checks its Git blob SHA, and runs self-test, signed verification and the report.

**Status limitation:** these figures establish US-Me6 source/forcing research-science holds only. They do not certify the other nine AmeriFlux Batch03 sites, nor that the whole cohort can submit AD400.


## Stage13Z clarification after successful Stage13Y on IRIDIS6

Stage13Y actual 2026-10-27 report:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13y_Me6_11subgroups_14T_8QC2_STRICT_HUMAN_GATE_READONLY_20261027T142119Z_e2ee7e1b`.

Eleven provisional science subepisodes total **763** native HH: Run12 (2015-09-26) 4, Run14 (2015-11) 464, and four 2017 runs 295; plus 14 strict source temperature failures and five previously approved 2017 records = all 782 HH. At the four 2017 QC2 source runs' eight original immediate edges, two Run18 ERA candidate-vs-retained VPD differences exceed 4hPa (5.349405 and 4.479289). This is an edge-value comparison and **not by itself an adjacent 30-min jump test**.

Important: Stage13Y labels four Sep26 Run12 half-hours *eligible for separate human review*, **not ERA-RH physical acceptance**. The older SHA-signed Stage13T records a **4.800355 hPa maximum VPD step across the six-node sequence, including measured QC0 bookends**, rejecting the complete ERA-RH boundary method at the strict 4hPa rule.

A new source-only [Stage13Z script](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/3f7ad924947801bd050c5a7f56618682289fce49/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_fourHH_complete_QC0_boundary_method_screen_READONLY.py) and [Stage13Z mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_mobile_full_edge_QC0_method_READONLY.sh) compare original tower QC0 anchors, six-node ERA RH, and the Stage13T QC0-anchored linear VPD/QBOT preview against all five full-boundary jumps, native T/PSRF physics, and signed historical output. **No new operator approval or forcing repair is implied.** Run Stage13Z on IRIDIS6 before deciding whether this one interpolation method merits separate scientific approval; the remaining 2015 Run14 and 2017 runs remain HOLD.


## Stage13Z v2 fix after real IRIDIS6 read-only failure

The first Stage13Z IRIDIS6 run terminated after `SELF-TEST PASS` at `non-finite original or proposed site halfhours`. Its overly strict finite-value assertion wrongly required *all four historical unresolved original QC1 selected VPD values* to be present before it could evaluate an independent science candidate. This is an **analysis-code validation issue**, not evidence that ERA/QC0 interpolation succeeded or failed.

[Stage13Z v2](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/77faa359117f50ba400a06ee5d1ce42e8e4a3e1c/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_fourHH_complete_QC0_boundary_method_screen_READONLY.py) now permits missing unresolved original QC1 selected VPD for **diagnostics only**, still requires the **two historical measured QC0 bookends and all hypothetical six-node QC0 interpolation values plus all four interior ERA-RH candidates to be finite**, and tests source QC0 invariance, VPD/QBOT physical validity, and all five original 30-minute steps (threshold unchanged at 4 hPa). It records the count of missing historical QC1 selected VPD. The pinned [v2 mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/1936bea6d2a1e388f433afca28919d3c34c08cfd/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_mobile_full_edge_QC0_method_READONLY.sh) is awaiting rerun on IRIDIS6. No forcing edit, operator approval, Post-v5, DATM, AD400 or Slurm submission has resulted.


## Stage13Z v3 (IRIDIS6 result display correction)

IRIDIS6 rerun of Stage13Z v2 reached `STAGE13Z SIX ORIGINAL SOURCE NODES | 2 TOWER QC0 + 4 QC1` and then failed at the **output table only**, `KeyError: "['native_time'] not in index"`, following `core.reset_index()`. All pre-print SHA/source and numerical candidate validation conditions had executed without stopping; this **does not** itself certify the candidate's physical acceptance, because final report generation was blocked.

The [Stage13Z v3 Python script](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/49dc297db6f8c54911fb1a3019966e7c525ab71b/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_fourHH_complete_QC0_boundary_method_screen_READONLY.py) explicitly emits `native_time` independent of pandas unnamed/named indexes, adds an exact six-timestamp test for both index-name variants, and preserves all prior model/data hold conditions. The [v3 runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/7b5ff940b65aa0c3bfb86e56c090ae20e75b2544/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13z_Me6_mobile_full_edge_QC0_method_READONLY.sh) is SHA-pinned. A separate synthetic pandas-index regression has passed, but **no new IRIDIS6 v3 scientific report is confirmed yet**.

No change to Stage13S, Stage12AC, 4 hPa edge threshold, forcing values, DATM, AD400 or SLURM.

## Operator science decision, 28 October 2026 — Stage13Z v3 PASS, Run12 APPROVED

The operator's actual IRIDIS6 run of `Stage13Z v3` passed source and report SHA checks, full six-node thermodynamics, the original two measured tower QC0 bookends and all five halfhour continuity comparisons. Actual signed report:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13z_Me6_run12_full_boundary_method_GATE_READONLY_20261028T160506Z_a3e87f28`.

The source Run12 2015-09-26 05:00, 05:30, 06:00 and 06:30 native time, between the 04:30 observed VPD=5.413 hPa and 07:00 observed VPD=6.468 hPa bookends, **now has the user's explicit scientific-method approval to use direct QC0-anchored linear VPD interpolation**. Candidate `VPD_USE` values are `5.624, 5.835, 6.046, 6.257` hPa, respectively; any corresponding `QBOT` must be recomputed thermodynamically from unchanged native `TA_USE` and `PSRF`, not interpolated independently. All five adjacent VPD jumps are 0.211 hPa, below the unchanged 4 hPa boundary test. The raw ERA-RH method at this gap remains **REJECTED**, with a measured boundary jump of 4.800355 hPa. The single previous `VPD_USE=NaN` is not evidence against the independently calculated candidate.

[Exact user approval scope and exclusions](decisions/US-Me6_Run12_20150926_QC0_linear_user_approval.json) (commit `ff3e2a9e085dee022d6f129c40e00232b50f3c76`). This **only** authorizes the exact four-halfhour source-method and a separate research-only shadow subject to strict SHA/source/diff revalidation. No shadow has yet been verified as applied, and no Post-v5/DATM/AD400/Slurm run is approved. The older Stage13S 235 and Stage12AC five rows are immutable.

### Remaining source-method scientific review (US-Me6 only)

- **Run14**, 2015-11-04–14 (469 QC1 HH): source physical-ERA preview contains 5 site-vs-ERA `|ΔT|>8C` holds at 2015-11-07 03:00, 04:00, 04:30, 05:00, 08:00. Its four candidate science subgroups contain 124, 1, 5 and 334 HH (464 total). None has two directly observed QC0 bookends. Do not linearly interpolate across this long episode.
- **Run15**, 2017-06-28–30 (95 QC1 HH): eight `|ΔT|>8C` holds, 2017-06-29 23:00 through 2017-06-30 02:30 every 30 minutes; two provisional fragments are 60 and 27 HH. Immediate original VPD source edges are QC2.
- **Run16**, 2017-06-30–07-01 (30 QC1 HH): no strict site–ERA temperature failure among these 30, but both original source VPD immediate boundaries are QC2 and no nearby ±48h QC0 observations were available in Stage13X. Physical pass is not source-method authorization.
- **Run17**, 2017-07-01–04 (137 QC1 HH): one `|ΔT|>8C` hold at 2017-07-03 07:00, two provisional fragments 86 and 45 HH, QC2 original edges.
- **Run18**, 2017-07-04–05 (47 QC1 HH): original source boundaries QC2; paired ERA candidate-versus-retained values differ by 5.349405 and 4.479289 hPa at two immediate edges. These are value differences, not directly proven 30-minute jump failures. Protect five original Stage12AC 2017 Jul04 halfhours (06:00–08:00).

For efficient *next* batch evidence, the existing [six-run method validation](ME6_BATCH_METHOD_VALIDATION.md) compares raw ERA RH, buffered QC0-residual-calibrated ERA RH, and the short Run12 direct QC0 interpolation in one read-only IRIDIS6 run. This provides empirical method screens and explicit timestamp-level review without silently approving 2017 QC2 neighbours or the five long 2015 source subepisodes. It had **not** been confirmed executed at the time of this handoff.

Other sites in the ten-site AmeriFlux Batch03 are not covered by these US-Me6 method decisions.


## 28 October 2026 — actual six-run batch method validation completed

IRIDIS6 successfully ran the SHA-pinned `13_validation_Me6_six_run_repair_candidates.py`, producing:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13_validation_Me6_six_run_repair_candidates_20261028T162002Z_4a34daf8`.

Exactly 13 method comparisons (1,568 candidate-value rows representing 782 unique native QC1 source times) were checked. **Only Run12 direct two-original-QC0-boundary shortgap VPD interpolation was classified `CANDIDATE_FOR_GROUPED_REVIEW`** (empirical validation PASS, 0.211 hPa max step). This method was explicitly operator-approved for the exact four 2015-09-26 HH as documented in [the decision JSON](decisions/US-Me6_Run12_20150926_QC0_linear_user_approval.json). All 12 other method/run comparisons remained HOLD. No forcing was written by the batch method validation.

| Held original run | Original HH | Best tested bounded method and key blockers |
| --- | ---: | --- |
| Run14 (2015-11-04–14) | 469 | Raw/adjusted ERA maximum native 30-min VPD steps 2.512/2.955 hPa, but **5 source site–ERA T >8C exceptions**, long-run source independence and empirical validation unproven |
| Run15 (2017-06-28–30) | 95 | Adjusted ERA empirical screen PASS, but **8 T>8C rows**, native 30-min VPD jump 5.924 hPa, original immediate VPD QC2 edges |
| Run16 (2017-06-30–07-01) | 30 | Adjusted ERA empirical screen PASS, but max VPD step 4.535 hPa and original QC2 borders |
| Run17 (2017-07-01–04) | 137 | Adjusted ERA empirical screen PASS, but **1 T>8C**, 4.191 hPa max step and QC2 borders |
| Run18 (2017-07-04–05) | 47 | Adjusted ERA empirical screen PASS, but 7.588 hPa max step and QC2 borders |

An adjusted-ERA empirical PASS does **not** override independent physical checks or original QC2 provenance. Do not apply any five held full runs as a blanket correction.

Two **new, independent scripts**, maintained only in the source-workflow repository, are available:
- [Stage13AA separate Run12 research-only shadow](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/e3351cacb1ac67d6652ba09042650d3cbb26e746/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13aa_Me6_Run12_fourHH_operator_approved_QC0_linear_SHADOW.py). Its mobile runner [13aa](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/2b83607cbcb2a5ac8dab9f840cd9448b74ef425c/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13aa_Me6_mobile_approved_Run12_fourHH_research_shadow.sh) downloads the exact earlier user approval JSON, checks source SHA, preserves Stage13S 235HH and Stage12AC 5HH, changes only VPD_USE/QBOT at the approved four original source times, and writes an independent complete NOLEAP research-only CSV. **Prepared but not yet confirmed run on IRIDIS6**.
- [Stage13AB 14 source-T exception and four 2017 QC2-edge source review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/b80a86c3d43e31d71a6ac584e67dbbd75ebc9f45/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ab_Me6_14_exception_and_QC2_edge_review_READONLY.py) and [mobile read-only runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/01fbe7bd0bc580156bd7eefc82a14062a37a24c0/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ab_Me6_mobile_review_14T_QC2_edges_READONLY.sh). It checks signed method-report and original source receipts, then builds a compact exact-time decision table; **not yet run on IRIDIS6**.

Scientific HOLD: Run14–18 source repair requires separate method review. All original tower/ERA files, approved Stage13S prior shadow, prior five 2017 observations, DATM/Post-v5 and model remain protected.


## Stage13AC — actual 28 October US-Me6 original tower and companion ERA context review

The operator's **successful** Stage13AA applied four 2015-09-26 operator-approved Run12 QC0-anchored halfhours to a **separate** new research-only shadow. Exact directory:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/science_trials/stage13aa_Me6_Run12_4HH_QC0_LINEAR_APPROVED_RESEARCH_ONLY_20261028T162945Z_25df5b3a`.
The actual run declared 4 changed `VPD_USE` cells and 4 thermodynamically recalculated `QBOT` cells, original Stage13S SHA unchanged, and no production/model admission.

The operator's **successful** Stage13AB (read-only) produced:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13ab_Me6_14_T_exceptions_QC2_and_4hPa_REVIEW_ONLY_20261028T163021Z_65ad5c8b`.
Original source strict `|TA_F - TA_ERA|>8C` 14 events: 5 on Nov07 2015 (Run14), 8 on June29–30 2017 (Run15), one Jul03 2017 (Run17). Nine distinct 30-minute candidate VPD jumps exceed 4hPa across Runs15–18; Stage13AB emits 18 method-specific rows. Four 2017 held original source runs have QC2 immediate bookends and no directly observed QC0 bookends.

To answer the operator's request for **before/after actual tower and ERA values**, the new [Stage13AC source-only script](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/2f9b984d603fc9c4d548c3757b9c42e0368870af/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ac_Me6_tower_ERA_original_vs_candidate_neighbor_review_READONLY.py) and [SHA-pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/83c79d969538bcab4827e3c75bd020527b466c48/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ac_Me6_mobile_original_tower_ERA_neighbors_READONLY.sh) combine *original* `TA_F`, `VPD_F`, `*_QC`; companion source `TA_ERA`, `VPD_ERA` and ERA-derived RH; prior Stage13S selected values; current independently approved Stage13AA research shadow; and the **two unapproved** ERA source-humidity candidates for all 14 anomalous halfhours and nine candidate jump boundaries, with ±2 hour source context and each held run's start/end. It checks SHA provenance of source/data/reports and writes **read-only reports only**. The independent ERA5-Land external series is **not equated** to the `TA_ERA/VPD_ERA` source companion without additional verification. The script has not been run on IRIDIS6 yet.

Neither Stage13AB nor Stage13AC approves any Run14–18 forcing replacement.


## Source-before/after rule and Stage13AD one-point conditional isolated interpolation (2026-10-28)

The operator requested a change of diagnostic policy: **do not infer a bad tower observation merely from a large jump between two hypothetical ERA-based candidates; examine several native source observations before and after the event and only interpolate an isolated bad center if both sides are demonstrably normal.**

From the operator's **successful Stage13AC read-only actual context**:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13ac_Me6_original_tower_ERA_prepost_14T_9edges_5runs_READONLY_20261028T163544Z_31baa0aa`.

- **Strong isolated source pattern, Run18 immediate left QC2 boundary 2017-07-04 12:00**: original tower/source VPD in hPa at 11:00 = 27.711 (QC1), 11:30 = 28.983 (QC1), 12:00 = 21.840 (**QC2**, same number as companion `VPD_ERA`), 12:30 = 29.150 (QC1), and 13:00 = 28.664 (QC1). The single-point 11:30–12:30 linear interpolation is **29.0665 hPa**, replacing 21.840 at precisely 12:00. The two immediate neighbor VPD values are **QC1, not directly measured QC0**. Even if their thermodynamic and native contextual checks pass, this is weaker-than-QC0 source evidence and must not be mislabeled as independently measured QC0.
- **Not an isolated original tower spike**: Run16 2017-06-30 19:00,19:30,20:00 original source VPD 13.358,9.231,9.270 hPa, while the originally tested ERA-sourced trial has 22.713,18.526,14.037 hPa. The ERA proposal's two >4hPa jumps do NOT establish one erroneous tower center.
- **Do not interpolate an extended temperature discrepancy**: Run14 2015-11-07 five site–ERA >8C hours and Run15 2017-06-29/30 eight consecutive such records are not solitary erroneous original tower VPD observations.
- **Existing protected Stage12AC five Jul04 values and all earlier Stage13S/Stage13AA approved 2015 entries are immutable.** Run17's 07:00–07:30 candidate jump is across previous protected five; not eligible for this isolated center policy.

The operator's conditional single-point rule and exact held scenario are in [policy JSON](decisions/US-Me6_conditional_isolated_spike_interpolation_20261028.json), commit `04a563e6ef463c935ddd207f4f4ffa974e256008`.

[New Stage13AD Python](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/39b768b1e233b7f7b62b2ac28fe8fd8200fec1e5/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ad_Me6_isolated_QC2_single_spike_user_conditional_shadow.py) and [SHA-pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/67adf01ea69986b031271a3e23ca876d0f250d6c/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ad_Me6_mobile_one_QC2_isolated_interpolation.sh) test this **one** exact candidate with five original site source time/temperature/QC records, both surrounding two-HH tower VPD continuity tests, thermodynamic QBOT, unchanged original native TA/P, and a strict full-site old-versus-new diff. Only after all pass may it create a **new versioned full-site NOLEAP research shadow with only the single original Jul04 12:00 `VPD_USE` and `QBOT` changed**, based on the already separately approved Stage13AA shadow. The user's conditional authorization does not imply approval for any of the other seven original 2017 QC2 boundaries, full Run18, or Run14-17.

**Stage13AD has not been run on IRIDIS6 yet.** No production forcing, Post-v5, DATM or model jobs are authorized.


### Stage13AD pinned source correction and next IRIDIS6 gated run

The current floating-point-safe Stage13AD source is [the pinned Python script at commit `eda999a4254c6eeb29fb78d29c835cdef3c6f4b5`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/eda999a4254c6eeb29fb78d29c835cdef3c6f4b5/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ad_Me6_isolated_QC2_single_spike_user_conditional_shadow.py), run by [the pinned mobile runner at commit `cc044e51f2fc65bd590e203e7f7d106183b69067`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/cc044e51f2fc65bd590e203e7f7d106183b69067/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ad_Me6_mobile_one_QC2_isolated_interpolation.sh). The self-test correctly compares the calculated 29.0665 hPa interpolation using floating-point tolerance rather than `==`.

After exact source, context, physics and signed approval gates pass, the runner performs a read-only full input check **before** attempting a separate research-only shadow copy; **do not claim it was completed until the actual IRIDIS6 log confirms**. The original tower/ERA, prior Stage13S 235 approved halfhours, prior Stage13AA four approved halfhours and five earlier 2017 Stage12AC values remain immutable. No repair of full Run18 or any other QC2 boundary is authorized.


## Operator-verified Stage13AD research-only shadow (2026-10-28 17:09 UTC)

The operator executed SHA-pinned Stage13AD `--self-test`, `--check` and `--apply` on IRIDIS6; all passed. Exactly **one original native source VPD QC2 boundary** (2017-07-04 12:00) with otherwise locally stable **QC1** VPD neighbors was replaced **only in a new complete research shadow** with VPD=29.066499999999998 hPa (old=21.840 hPa), and QBOT recomputed to 0.007642593602108391 kg/kg. Retained site T, PSRF, original tower/ERA sources, all earlier Stage13S 235 original 2015 QC1 HH, Stage13AA 4 approved Sep2015 HH and Stage12AC five protected Jul2017 HH remained unchanged. The five original local source VPD were 27.711,28.983,21.840,29.150,28.664 hPa; original VPD QC are 1,1,2,1,1. **These are not two measured QC0 humidity anchors**; this is a science-reviewed, lower-confidence isolated-spike research trial, not production or blanket QC2 repair.

Actual output:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/science_trials/stage13ad_Me6_isolated_originalQC2_Jul04_1200_QC1_anchor_trial_20261028T170952Z_4ac00fee`.

**Still not complete:** US-Me6 original held Run14 (469 QC1 HH), Run15 (95), Run16 (30), Run17 (137), Run18 (47). The old five approved Stage12AC Jul2017 HH must not be counted as still unapproved or overwritten. Current full-site remaining missing/invalid counts must be regenerated from the exact latest Stage13AD full NOLEAP CSV, not inferred by reusing the older Stage12AI all-ten census (Me6 baseline 65 missing at 2026-10-26). All ten AmeriFlux Batch03 sites remain unadmitted for Post-v5/DATM/AD400 pending independent full-source and PFT/ZBOT science.

For ten-site history use the [last reconciled cohort status](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/AmeriFlux_MultiSite_10_Batch03/docs/BATCH03_TEN_SITE_CURRENT_STATUS_20261026_1939UTC.md): last common baseline had three sites numerically complete (US-MOz, US-Mpj, US-NC2), six selected-source sites humidity-incomplete (US-Kon, US-Me6, US-MMS, US-MtB, US-NR1, US-NR3), and US-Me2 requiring its own FULLSET source admission. Later separate trials on Kon, Me6, NR1 do not yet constitute a new comparable ten-site production report.


## Two independent science workstreams (28 Oct 2026)

**US-Me6 — ChatGPT owns this strand.** After the user's actual IRIDIS6 Stage13AD success, its research-only site shadow has the earlier Stage13S approved 235 2015 source HH, the Stage13AA additionally approved 4 native 2015-09-26 HH, five previously protected Stage12AC 2017 July04 HH, and a newly screened single original source 2017-07-04 12:00 QC2 spike corrected from VPD 21.840 to 29.0665 hPa. Stage13AD is **not** Post-v5 / DATM / spinup admission.

The next [Stage13AE source-context review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/aced432514f861e20e7960e61843f9660dbbcb0e/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ae_Me6_all_five_held_runs_isolated_original_spike_screen_READONLY.py) covers **all remaining five original held Run14-18 source runs = 778 QC1 native records**, plus QC2 time points near five run boundaries. It independently verifies the full-source Stage13S and actual latest Stage13AD SHA/280320-row schema, protects all 10 separately approved Stage13AA/Stage12AC/Stage13AD native timestamps, classifies isolation using **two source-native time steps before and after** the center, and reports source tower VPD_F/QC, TA_F/QC, paired source ERA T/VPD, retained selection, hypothetical one-point VPD/QBOT, five-point physics and native jump. **No new forcing/approval/model writes.** [One-click pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/87c6e9c1871f5e3e378fe7fa9d3e03490eb3899a/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ae_Me6_mobile_all_held_source_single_spike_review_READONLY.sh). Prepared; not yet run on IRIDIS6.

**US-MtB — Claude independently investigates high elevation and humidity evidence only**, while the human user retains all final science approval. [Full independent Claude high-altitude handoff](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/214ad58b64927db6d9241bfb568b80809b319921/examples/AmeriFlux_MultiSite_10_Batch03/docs/US_MTB_CLAUDE_INDEPENDENT_HIGH_ALTITUDE_RESEARCH_HANDOFF_20261028.md) records tower 2573m, observed ~1060m pressure-derived tower/grid height mismatch (diagnostic only), 2020/2022/2024 Stage12j **four failed measured-QC0 humidity transfers**, 1035 remaining Stage12g target holds, unusual subzero ice supersaturation with conditional user authorization requiring **actual installed-model acceptance**, and existing sealed Stage12h/i/j/k reports. No model or forcing release, and no workstream should modify the other site's files.


### Stage13AE v1 reader regression diagnosed; v2 pinned fix awaiting IRIDIS6

Operator ran the original pinned Stage13AE runner on IRIDIS6. Source Git blobs, syntax, and synthetic `--self-test` all PASS; then original *script* stopped before the scientific source review with `AttributeError: module 'me6_13_validation_for_13ae' has no attribute 'S'`. The upstream `13_validation` module deliberately returns five selected columns via `load_inputs()`; its source Stage13S path lives in predecessor Stage13x, not an exported `S` module attribute. This is a software reader defect, **not** a new scientific US-Me6 hold or failed source datum. No Stage13AE source review report or forcing output was created.

Fixed Stage13AE v2 explicitly pins `science_trials/stage13s_Me6_12x2015_235HH_ERA_RH_operator_approved_20261027T065056Z_6890a105/US-Me6_STAGE13S_12x2015_QC1_235HH_ERA_RH_OPERATOR_APPROVED_RESEARCH_ONLY_NOLEAP.csv` and verifies SHA256 `02e80edf89af35874a5cfb2c134e42fbe771b9b2ccc0899bfc4fe19bc2e18565` before reading the **full site** source table, so the SHA-guarded comparison with the already-successful Stage13AD full-site shadow covers all columns, not just the previously selected five. The original Stage13 validation's strict r/x tower and companion ERA source verification remains unchanged.

[Fixed v2 Python](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/09692df08b19e5b272716cd4ab38dc95b3de684c/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ae_Me6_all_five_held_runs_isolated_original_spike_screen_READONLY.py) (Git blob `c560812006239731372ee1456045eacdbc14613d`); [mobile wrapper](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/4bc60c35d8eded2af473e492eadbf8eb21423fca/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ae_Me6_mobile_all_held_source_single_spike_review_READONLY.sh) (Git blob `ec64fe39b7018303047731fbfec3f9cce29ec943`). Neither the code change nor the earlier failed source review authorizes any new source repair, Post-v5, DATM, AD400 or Slurm. The fixed v2 source review itself is **not yet verified to have run on IRIDIS6**.


## 28 October 2026 Stage13AE actual verified and Stage13AF next one-point trial

Operator successfully ran the pinned Stage13AE v2 on IRIDIS6: syntax, source SHA, full 793 row original tower+ERA source context and five-run review, and independent Stage13AD 280320-row original full-shadow comparison **PASS**. Output:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13ae_Me6_five_held_runs_source_isolated_spike_scan_READONLY_20261028T172442Z_911b2468`.

- The five held original QC1 full-run populations are Run14 469, Run15 95, Run16 30, Run17 137, Run18 47 (778 records), plus 15 separate native QC2 boundary-neighborhood source records. Run17 contains 5 original prior approved source times and one Run18-neighborhood QC2 time is already the separately approved Stage13AD correction. **No 793 new repairs**.
- Only **ONE new strictly isolated original source spike** passes the exact five-node site T QC0, original VPD QC0-or-QC1 flanking source, thermodynamics and native continuity screen: **Run14 2015-11-12 13:30**, source VPD QC1. The original native tower/source VPD values at 12:30, 13:00, 13:30, 14:00, 14:30 are **8.028, 8.373, 3.501, 6.653, 5.542 hPa**. Paired ERA source VPD at 13:00/13:30/14:00 are **5.037, 5.714, 6.392 hPa** (NOT true QC0 observations). Two-neighbor linear VPD **7.513 hPa** yields a full five-node max step **1.111 hPa**, and QBOT should be computed using **the original site tower TA_USE and PSRF**, not interpolated independently.
- **Neither flank is proven measured QC0 on both sides**; the original source QC is QC0 or QC1 (specific grades are in full signed Stage13AE CSV). The isolated interpolation is allowed only as a science-gated *research shadow trial* per user's established isolated-spike policy. Source tower time/QC and all other source data immutable; preserve prior Stage13S 235 native 2015 HH, Stage13AA 4 Sep2015 HH, Stage12AC 5 Jul2017 HH and Stage13AD 1 Jul2017 QC2 correction.
- [Stage13AF strict one-point shadow Python](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/32f66b4c7fee5efc72cd8c78a3fb904bea5cb203/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13af_Me6_Run14_one_source_QC1_spike_conditional_LINEAR_SHADOW.py) and [SHA-pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/543a06e078e5cff05d3879c297ba6296b7038b8f/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13af_Me6_mobile_single_2015_QC1_conditional_linear_research.sh) are now prepared. Stage13AF will recheck SHA of the exact signed 793-row source report, verified Stage13AD shadow `8ea065e690b35cdbf2722c436211ab43627dfdcb2e202f159be9d22a7396241b`, original five tower T/QC/VPD/ERA observations, full-site diff EXACTLY one VPD_USE/QBOT native time and NO other changes, then create a *new research-only shadow*. **Stage13AF has NOT yet been run on IRIDIS6.**
- Do not equate failing isolated-spike criteria with good or repaired source records. Most Run14–18 observations remain long-duration QC1 source gapfill/methodologically held; additional source-grade evidence and cross-validation are necessary before release. All Post-v5/DATM/AD400/Slurm permissions remain false.


## 2026-10-28 17:28 UTC — ACTUAL Stage13AF SUCCESS; Stage13AG next group review prepared

Operator's IRIDIS6 terminal confirms Stage13AF original pinned source SHA, Python syntax, self-test, full science `--check`, exact one-HH `--apply`, output reread and complete full-site differential **PASS**. New SHA-receipted research-only site NOLEAP shadow:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/science_trials/stage13af_Me6_20151112_1330_originalQC1_single_spike_RESEARCH_ONLY_20261028T172815Z_c5ca5d8d`.

Exactly one source-original **Run14 2015-11-12 13:30 VPD QC1** original gapfilled/derived source VPD from **3.501 to 7.513 hPa**, the corresponding physical `QBOT` recalculated **0.0010634893277193197 kg/kg** at unchanged original measured site `TA_USE` and preserved `PSRF`. Original site VPD five-node source times 12:30,13:00,13:30,14:00,14:30 show **8.028,8.373,3.501,6.653,5.542 hPa** with **all source VPD QC1, all site T QC0**; companion ERA VPD at 13:00,13:30,14:00 is 5.037,5.714,6.392 hPa. Interpolated five-node maximum step **1.111 hPa**. This is a **conditional QC1-anchored single-point research repair**, NOT double independently measured QC0 humidity observations. `change_counts`: 1 VPD_USE and 1 QBOT; previous approved 2015/2017 times and original source files immutable.

**Next:** [Stage13AG five remaining Run14–18 native source/day/QC0/ERA science group review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/d84f1303aa00840564caa80162db6a4955725356/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ag_Me6_five_held_long_runs_daily_QC0_ERA_group_review_READONLY.py) and [mobile SHA runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/9e68709433b8b05c9e1b83ff53afa06a0866b52a/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ag_Me6_mobile_daily_five_run_QC0_ERA_READONLY.sh). It uses Stage13AF actual full source shadow SHA receipts, Stage13AD predecessor, signed upstream original tower and paired same-release ERA, plus previous original measured QC0 held-out validation. It will compute **current** whole-site VPD_USE/QBOT missing counts, five-run current missing and 14 site–ERA T anomaly counts, full-run original QC0 bookends, original 2017 QC2 direct source borders, **daily source tower/ERA stats, ±2h boundaries and ±1h for 14 T exceptions**. All five original QC1 runs remain HOLD until a separate method passes science review and user approves; 778 original QC1 halfhours are not necessarily 778 defective observations. Stage13AG code prepared but not yet run on IRIDIS6. No Post-v5/DATM/AD400/Slurm.


## 28 October 2026 19:13 UTC — Operator-verified US-Me6 Stage13AG, next Stage13AH

**Actual IRIDIS6 Stage13AG PASS**: the operator ran Git blob-pinned code with Python AST and science self-test PASS, complete original-source SHA group review PASS and report-only output:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch03/reports/stage13ag_Me6_5run_QC0_ERA_daily_before_after_REVIEW_ONLY_20261028T191352Z_e6cec200`.

Verified **latest Stage13AF** full-site 280320-row research shadow source SHA256:
`3df2fd258157f2a70d8d0b6dd0de865980bf6505c4da0e6a58e6058e2610b1b0`.

- Actual current missing: **46 native half-hours in VPD_USE and 46 in QBOT**, TA_USE and PSRF missing **0**. Earlier 65 humidity gaps were an old census and cannot be used as current.
- Inside original held QC1 long-run groups: Run14 **2/469 missing**, 5 site–ERA T outliers >8°C, immediate source QC0/0 but **adjusted ERA-RH independent QC0 heldout FAIL** and 469HH long duration; Run15 **5/95**, 8 T outliers, immediate boundaries QC2/2 and corrected ERA-RH proposed 5.924hPa native jump; Run16 **1/30**, 0 T outliers, boundaries QC2/2 and jump 4.535hPa; Run17 **6/137**, 1 T outlier, boundaries QC2/2 and jump 4.191hPa; Run18 **3/47**, 0 T outliers, boundaries QC2/2 and jump 7.588hPa. **17** missing inside original five held QC1 runs and **29 missing outside those five runs**, whose native time/source must be identified independently.
- Original tower VPD QC1 gapfilled value is not independently measured humidity QC0; most records in five runs already have finite VPD but are science-HOLD for full-run repair. **Do not mark 778 original QC1 as missing or 778 authorized replacements.** The original 14 site–ERA T discrepancies and eight original QC2 immediate 2017 outer boundaries are still unresolved. Pre-existing five 2017 Jul04 Stage12AC and newer Stage13AD/AF single-point trial values unchanged.
- **No Post-v5, DATM, AD400, Slurm or production forcing writes authorized.**

**Next prepared (NOT yet run on IRIDIS6)**: [Stage13AH original source science audit](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/08d8d1a379be3c983b16ba9467922ea6a6076c8e/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ah_Me6_46_remaining_native_missing_source_ERA_context_READONLY.py), [SHA-pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/77c7a5d8f8c775906fa731f332243cfee25d6d82/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ah_Me6_mobile_all46_original_tower_ERA_before_after_READONLY.sh). Stage13AH SHA reopens **the full original 16-year native tower and release companion ERA**, the actual Stage13AF full-site research output and Stage13AG signed reports. It verifies **exact 46 missing identities**, 17 inside and 29 outside original five held QC1 runs, identifies contiguous missing clusters, and outputs each native HH's original tower TA/VPD/QC, paired original ERA TA/VPD/RH, current selected values, before/after 30-min + **±2-hour** context, and hypothetical interpolation/paired-ERA numerical screening **for further review only**. At NOLEAP/source boundary missing neighbors are flagged explicitly rather than reconstructed. No modification of any original input, previous research shadow or model.


## 2026-10-28 Stage13AH initial full-source timestamp mismatch — code assumption, v3 corrected

The user's actual IRIDIS6 Stage13AH pinned Python/4 Git source SHA, AST syntax, and synthetic `--self-test` all PASS, then `--run` **stopped before any 46-row source review** at `original full 2009–2024 native tower and same-release ERA time mismatch`. Stage13AH v2 erroneously required that the **entire** raw original tower `TIMESTAMP_START` CSV and original companion ERA `TIMESTAMP_START` CSV have equal row counts and exactly identical row positions. The previously independently source-verified Stage13x/Stage13AG only established exact alignment for **2015 and 2017**. Differences in other years' native record coverage are therefore possible; the run log gives no year/time identity of the mismatch yet. Do not infer a particular missing year, a timezone shift, bad QC, or data corruption from this assertion.

Fixed [Stage13AH v3 source](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/678755a182cc0cc015c466564d5a0f66fdbbeb54/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ah_Me6_46_remaining_native_missing_source_ERA_context_READONLY.py) Git blob `c0b7f0429d352c82a10becf8d59d8a5d62987edf` and [SHA-pinned mobile runner](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/02a87d7f682faa86c69f172c4d650345701820a2/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13/13ah_Me6_mobile_all46_original_tower_ERA_before_after_READONLY.sh) Git blob `81f1145f30cdff06ed2725949cd54741483a2524` **independently** index the two SHA-sealed original CSV sources by each original native `TIMESTAMP_START`, drop only original source Feb29 when mapping to the existing selected 16-year NOLEAP source clock, and reindex each to the precise SHA-checked Stage13AF 280320-row native timeline. The output reports source-specific covered/missing native row counts, year groupings and example **actual** unmatched timestamps and differentiates originally missing tower versus ERA time, including ±2h original coverage flags.

The v3 `--self-test` checks a deliberately missing ERA center with intact tower source neighbors and prohibits positional borrowing of a different-time ERA row. It preserves the earlier strict 35040-record raw 2015/2017 source-to-predecessor numerical crosscheck. Any unavailable tower or companion ERA time stays **NaN plus source-availability flag and HOLD**; there is **NO time shift, duplicate native time acceptance, invented source record, estimated temperature, auto-interpolation, humidity repair, forcing write, Post-v5, DATM, AD400 or Slurm**. v3 has been committed but has **NOT yet been executed on IRIDIS6**.

Most recent confirmed model-data status remains **46 VPD_USE/QBOT missing native HH in signed Stage13AF**, 17 inside held original QC1 Runs14–18 and 29 outside. This historical 46 remains reliable because actual Stage13AG already fully counted its latest research shadow. No conclusion about the original per-year tower/companion ERA coverage is possible until the v3 audit executes.
