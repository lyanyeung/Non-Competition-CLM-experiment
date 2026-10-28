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
