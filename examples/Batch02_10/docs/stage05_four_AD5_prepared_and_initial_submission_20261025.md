# Stage05: four real AD5 previews passed; submit first five years only

**Later operator result:** all four submissions succeeded with run/archive pairs4728102/03,4728104/05,4728106/07,4728108/09. Subsequent accounting reported all four runs FAILED/1:0 and all four archives PENDING. [Proceed to Stage06 diagnosis](stage06_four_AD5_failed_readonly_diagnosis_20261025.md); do not repeat submission. Pending-execution language below records the earlier state.

## Operator Stage04 result, 25 October 2026

The operator supplied `/home/ly3n24/Batch02_10_stage04.lo9bISc0/stage04_prepare.log` output. All five downloaded dependencies passed SHA256, nine XML regression tests passed, all four input preflights passed, and actual CIME previews completed:

| Site | AD5 interval | Generated mode | Submission at this report |
| --- | --- | --- | --- |
| FI-Hyy | 1997-01-01 → 2002-01-01 | AD state2, fixed biogeography, no competition | None |
| FR-Hes | 1997-01-01 → 2002-01-01 | AD state2, fixed biogeography, no competition | None |
| CH-Fru | 2005-01-01 → 2010-01-01 | AD state2, fixed biogeography, no competition | None |
| IT-MBo | 2003-01-01 → 2008-01-01 | AD state2, fixed biogeography, no competition | None |

Final operator lines: `AD5_PREPARE_SUMMARY prepared= 4 failed= []`; `NO SLURM JOBS SUBMITTED`. This is real operator-reported preparation success, not a completed model run.

All four actual XML files have **five stream_info sections**, with one selected `CLM_USRDAT.UNSET`. This explains v1's erroneous exactly-one-total-stream gate. The other streams remain unchanged. FI-Hyy has29 provisional-named annual files; IT-MBo has23; FR-Hes29 and CH-Fru20 have plain annual names. The provisional label remains provenance, not a new meteorological-validation claim.

## Next: guarded submission

[Stage05 controller](../scripts/05_submit_four_AD5_cases.py) supports `check`, `submit`, `status` and `self-test`. No Stage04 rerun is needed. It requires all four existing Stage04 receipts to be `PREPARED_NOT_SUBMITTED` and rechecks the independent case identity, current XML AD5 settings, resource geometry, restored CIME lock, candidate/executable/parameter hashes, generated input hashes and inherited user DATM overrides. It does not re-read annual meteorology.

```bash
conda activate clm_fates_env
(
  set -euo pipefail
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/a325fea1b6d32b7b5f6dfba3f85c082260337913/examples/Batch02_10/scripts/05_download_and_submit_four_AD5.sh" \
    -o "$HOME/Batch02_10_stage05.sh"
  bash "$HOME/Batch02_10_stage05.sh" submit
)
```

Every case is submitted once with `case.submit --skip-preview-namelist`, preserving the verified AD land namelist. Each remains `STOP_N=REST_N=5`, `RESUBMIT=0`. No AD395 or Normal400 is submitted.

The launcher verifies six pinned dependencies, runs the self-test and seven mocked submission tests, then performs the requested action. Use `check` instead of `submit` for only the preflight. Use `bash "$HOME/Batch02_10_stage05.sh" status` later for read-only scheduler/accounting status.

### Expected output and retained records

Each success prints `<site> AD5_SUBMITTED RUN=<actual ID> ARCHIVE=<actual ID> YEARS=5 RESUBMIT=0 SKIP_PREVIEW_PERSISTED=TRUE`, followed by:

```text
AD5_SUBMIT_SUMMARY submitted= 4 failed= []
FIRST FIVE AD YEARS ONLY. AD395 and Normal400 NOT submitted.
```

Under the existing Batch02 experiment root, the controller updates each site's `AD5_case_state.json` and creates `AD5_submit_attempt.json` plus `AD5_case_submit_output.txt`. The batch gets `_four_initial_AD5_submission_attempt.json`. These capture actual run/archive IDs; no Batch01 job IDs are reused.

Exclusive attempt markers are written before external submission. A timeout, partial/unparseable response, nonzero CIME exit or missing persistent `skip_pnl` stops the batch and preserves the output/state. Do not rerun `submit` after an uncertain outcome; use `status` and the retained records. Successful IDs are preserved even if a later options check requires review. No existing surface, forcing, old source case or shared CTSM is modified.

## Verification and limits

Seven mocked tests passed: four distinct run/archive submissions and receipts; partial-submission stop; timeout output preservation; nonzero return with IDs retained; missing persistent skip-preview options with IDs retained; active-target queue rejection; and prior-case-submission rejection. The real Stage05 preflight code also accepted all four simulated Stage04 cases/receipts in the combined local fixture. The shell launcher passed syntax, six-file checksum/layout/dispatch and corrupted-dependency rejection tests. Tests do not contact Slurm or CIME.

**Pending:** actual Stage05 execution and job IDs, successful exact run/archive accounting, all three archived AD5 component restarts with land state2, then AD395 continuation and independent Normal400. Actual model success and carbon equilibrium have not been established. The six other Batch02 sites still have no automatic candidate.
