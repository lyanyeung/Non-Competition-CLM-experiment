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
