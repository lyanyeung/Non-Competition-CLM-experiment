# ICOS Batch04 Stage01 — operator IRIDIS6 console result (31 October 2026)

**Evidence provenance:** operator pasted terminal summary of the source-pinned Stage01 script on IRIDIS6; full JSON contents were **not available in this chat** and have not been independently inspected. This record contains only directly observed console counts and static point-match statuses. The successful script self-test and source-blob checks are separate from the scientific model-data release.

- Download SHA checks **PASS 3/3** (Stage01 script, six-site review-gates CSV, six-site operator PFT CSV).
- `--self-test`: **PASS**, no source writes.
- `--base /iridisfs/scratch/ly3n24/CLM_FATES`: six site directories present; 17 original CIME case candidates; 27 candidate forcing subdirectories.
- All 17 candidates printed `MATCH_STATIC_XML_EFFECTIVE_CIME_NOT_YET_VERIFIED`.
- JSON generated on IRIDIS6: `/home/ly3n24/ICOS_Batch04_stage01_Dy3qIRjj/stage01_report.json`. **Report not copied into this public GitHub repo.**
- Script declared: `NO CIME/SLURM OR SOURCE CHANGES; ALL SITES HOLD`.

| Site | Site directory | Original case candidates | Forcing directories | Static point result |
| --- | --- | ---: | ---: | --- |
| CH-Aws | present | 8 | 14 | 8/8 static point MATCH |
| DE-Gri | present | 2 | 2 | 2/2 static point MATCH |
| DE-RuR | present | 2 | 2 | 2/2 static point MATCH |
| IT-Tor | present | 2 | 2 | 2/2 static point MATCH |
| ES-Agu | present | 2 | 2 | 2/2 static point MATCH |
| GL-ZaH | present | 1 | 5 | 1/1 static point MATCH |

Original case names observed:
- CH-Aws: `CH-Aws_FATES_RH25A_DIAG16D_20261020`; `CH-Aws_FATES_SPINUP1000_RH21A`, `RH25A`, `RH29A`, `RH34A`, `RH38A_CONT2016`, `RH42A_V8_CONT2016`; `CH-Aws_FATES_SPINUP500_11P`.
- DE-Gri: `DE-Gri_FATES_SPINUP1000_S30EXCL`, `DE-Gri_FATES_SPINUP1000_S30SHARED`.
- DE-RuR: `DE-RuR_FATES_SPINUP1000_S30EXCL`, `DE-RuR_FATES_SPINUP1000_S30SHARED`.
- IT-Tor: `IT-Tor_FATES_SPINUP1000_S30EXCL`, `IT-Tor_FATES_SPINUP1000_S30SHARED`.
- ES-Agu: `ES-Agu_FATES_SPINUP1000_S30EXCL`, `ES-Agu_FATES_SPINUP1000_S30SHARED`.
- GL-ZaH: `GL-ZaH_FATES_SPINUP500_11P`.

## Interpretation and next gate

Stage01 shows *source presence and consistent static model point coordinates*, not proof that a source case, active forcing stream or soil is suitable. Both S30SHARED and S30EXCL remain **unselected**; do not assume SHARED is automatically preferred. CH-Aws's RH variants still need a separate provenance/QC comparison before release. GL-ZaH still requires the private Arctic HLM→FATES mapping. ES-Agu's bare/grass/shrub percentages remain a documented model proxy with unresolved cover denominator. No AD5/AD400 submissions approved.

Next: [Stage02 sampled forcing inventory and case comparison](../scripts/02_batch04_forcing_source_sample_readonly.py), followed by a **full native-source versus selected DATM half-hour audit** only when the correct stream and source-QC provenance are identified. This public summary is deliberately distinct from local full JSON report and does not publish home/scratch file hashes or unreviewed source content.
