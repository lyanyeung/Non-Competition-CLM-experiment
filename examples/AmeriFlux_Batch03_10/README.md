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
