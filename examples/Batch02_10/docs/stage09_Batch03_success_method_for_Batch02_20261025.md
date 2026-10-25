# Stage09: adopt the working Batch03 submitting-process stack recovery

## Successful startup reference supplied by the operator

The operator's `Pasted text(20261025-091618).txt` includes Batch03's successful recovery command, stack guard and new job IDs. Ten cases were resubmitted after setting the submitting shell stack to unlimited. The subsequent queue showed all ten run jobs RUNNING for approximately1–3minutes on red6083, past the earlier approximately10second mesh SIGSEGV point. This is successful startup/runtime recovery evidence; full AD5 run/archive/restart completion was not shown in that attachment.

The inspected [Batch03 Stage11 source](../../Batch03_10/scripts/11_batch03_AD400_oneclick.py) has SHA256 `94213ef5f05e6e47b081a98293a0240bf1dc6e884cd981975a6b08d996a34239`, **exactly matching the operator's downloaded recovery source** from commit `3192f562b50942adb4fe13c1b448bb9ccb042f80`. Its key method is a submitting-process minimum64MiB stack guard, retained inputs, exact failed-job/archive checks, cancelled stuck archives and `case.submit --skip-preview-namelist`.

The attachment also directly demonstrates login6001 soft stack300000KiB being inherited by a small task on red6082 and shows `PropagateResourceLimits=ALL`. That is evidence for that current submitting shell/task pair, not a reconstruction of the historical Batch02 submitting process. Initial Batch02 stack limits were not recorded.

## What transfers to Batch02

| Item | Batch03 reference | Stage09 Batch02 adaptation |
| --- | --- | --- |
| Stack control | Raise submitting shell, then Python guard ≥64MiB | Raise only the current Python submit process if low; preserve high/unlimited soft values and the hard limit |
| Slurm propagation | ALL, reported by operator | Verify current configuration and reject overrides excluding STACK |
| Case inputs | Retained original AD5 inputs | Recheck current Batch02 receipt/input/binary hashes and generated fixed-biogeography/no-competition state2 |
| Recovery | Cancel each known blocked old archive, keep failure history, resubmit AD5 | Same operation for the four exact Batch02 initial job pairs |
| Mode/length | Cold start, five years, RESUBMIT0 | Same; no AD395/Normal submission |
| MPI launcher/mesh/science | Original settings retained | No MPI wrapper, XML edit, mesh replacement, forcing/soil/PFT change or model rebuild |

This supersedes the Stage08 fixed256MiB wrapper proposal and the additional probe prerequisite. A high current stack is preserved rather than reduced. Since the successful source already provides the recovery method, a new probe job is not required by Stage09.

## Execute for the four failed Batch02 cases

[Stage09 standalone controller](../scripts/09_resubmit_four_AD5_with_Batch03_stack_guard.py) requires no downloaded helpers.

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage09.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/6ef949393e03e7c09b9be720d89094a268900de6/examples/Batch02_10/scripts/09_resubmit_four_AD5_with_Batch03_stack_guard.py" \
    -o "$SCRIPT"
  echo "d0730ccca1c7728f7b82285fe9da4f120b3dc06c189341f1f015b73151eac5fc  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" resubmit
)
```

It first raises only its own process's low soft stack to unlimited if allowed, or up to300000KiB within the existing hard limit; already-high/unlimited limits are untouched. It records hostname/PID/actual limits before each case.submit. This does not change the parent interactive shell or a global login preference.

All four preflights must pass before any archive cancellation/model submission. Original run/archive pairs remain FI-Hyy4728102/03, FR-Hes4728104/05, CH-Fru4728106/07 and IT-MBo4728108/09. Each run must be the exact known FAILED/1:0 job. A queued old archive must be the exact pending DependencyNeverSatisfied job. Previously cancelled archives may be accepted only when no unexpected active case job exists. Existing Stage08 or Stage09 recovery attempts stop the workflow instead of risking duplicate submission.

The controller snapshots original ledgers/case records/output names, preserves original first-job IDs and failure history, cancels only applicable original archives, and submits each existing cold-start case once with skip-preview. It records new IDs as `active_run_job`/`active_archive_job` plus an independent per-site retry receipt. Six input/science holds elsewhere in Batch02 are not changed. Batch03 model cases/jobs are not operated on.

Expected final line: `STAGE09 RESUBMIT SUMMARY submitted= 4 uncertain= []`.

Read the new IDs with:

```bash
python3 -B "$HOME/Batch02_10_stage09.py" status
```

Stage05 status retains historical first-job IDs, so use Stage09 status for these retries. If submission is partial/ambiguous, the batch and per-site attempt records stop repetition; inspect status/output before any recovery. Do not rerun Stage04/05 or the superseded Stage08 retry.

## Validation and remaining work

Six mocked tests passed: four exact archive cancellations with no XML/science edits and Batch03 jobs untouched; partial-submission stop/output preservation; high/unlimited stack preservation and low-hard-limit rejection; only-low-soft-limit adjustment; immutable-input drift rejection; original-job-ID reuse rejection. A combined fixture also passed the real Stage09 preflight over four generated Stage04 cases and submitted/failed Stage05 receipt structures. Python syntax/self-test passed. No local test submits actual HPC jobs.

Actual Batch02 retry job IDs/outcome are pending. Require run/archive COMPLETED0:0 and the exact AD5 CLM/DATM/CPL archived restart triplets with land state2 before AD395. Full scientific spin-up convergence and independent Normal400 remain separate.
