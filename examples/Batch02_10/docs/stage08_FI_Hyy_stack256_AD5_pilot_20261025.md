# Stage08: FI-Hyy-only AD5 retry with a measured task-side 256 MiB stack

## Stage07 evidence received

Operator attachment `Pasted text(20261025-090232).txt` reports:

- Login Python stack limits: soft8,388,608bytes (8MiB), hard unlimited. These are **not measured limits of the failed tasks**.
- All cases set `OMP_STACKSIZE=64M`, including the previously successful Batch01 references.
- Local ESMF source SHA256 `3ddcafe537a9b006718b6db54a26a0debbed7c9736201832b0c581486fa0538c`; line1024 creates automatic `cc_offsets[num_elems*coordDim]`, and line1028 writes it.
- The declared dust mesh exists and has1,036,800elements, coordinate dimension2. Its offset array would require16,588,800bytes (15.8203125MiB) **if all elements are local and PIO_Offset is8bytes**.
- The failed Batch02 and successful Batch01 references declare the same mesh files. Headers were readable; that does not validate every mesh value or establish which mesh was being read at the crash.

Full Stage07 report: `/home/ly3n24/Batch02_10_ESMF_mesh_stack_amha70m2/mesh_stack_inspection.json`.

The [OpenMP specification](https://www.openmp.org/spec-html/5.1/openmpse63.html) explicitly excludes the initial thread from `OMP_STACKSIZE` control. Thus64M OpenMP worker-stack configuration does not establish a sufficient initial-process stack. A primary-stack limit is now a well-supported hypothesis to test, **not a proven root cause**.

## Concrete controlled retry

[Stage08 standalone controller](../scripts/08_retry_FI_Hyy_AD5_stack256_pilot.py) supports `audit`, `retry`, `status`, `self-test`.

It targets **only FI-Hyy_B02_FIXNC_AD400**. It verifies the exact initial run4728102 FAILED/1:0, exact old archive4728103 PENDING/DependencyNeverSatisfied, original Stage05 state and immutable surface/executable/generated-input hashes, AD cold-start settings, lack of progressed NetCDF output and local ESMF/Stage07 provenance.

On retry it creates an exclusive `FI-Hyy/AD5_stack256_pilot_v1` recovery directory, backs up original state and case output/configuration records, and changes only `MPI_RUN_COMMAND` to place a small wrapper **after srun and before the unchanged cesm.exe**. Inside the actual compute task, the wrapper prints host/soft/hard stack limits, sets the soft primary stack to262,144KiB (256MiB), prints the resulting value and existing OMP_STACKSIZE, then execs the original binary with its original arguments.

The controller cancels **only verified blocked archive4728103**, waits briefly for that exact job to leave the queue, then submits one five-year FI-Hyy cold start with `--skip-preview-namelist`, `RESUBMIT=0`. No mesh, scientific namelist, PFT, soil, forcing, source/library or executable is changed. FR-Hes/CH-Fru/IT-MBo cases and archives remain untouched.

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage08.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/02b39012e7b6f77f55bd51a4c87510b45f1febd1/examples/Batch02_10/scripts/08_retry_FI_Hyy_AD5_stack256_pilot.py" \
    -o "$SCRIPT"
  echo "72d955c9ca5c5682070e570ea546f9375f597c2c233311f29a6c51252e611d70  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" retry
)
```

Expected submission line:

```text
FI-Hyy STACK256_AD5_SUBMITTED RUN=<new ID> ARCHIVE=<new ID> YEARS=5 RESUBMIT=0
```

Inspect **this pilot's new IDs**, not the original failed Stage05 IDs:

```bash
python3 -B "$HOME/Batch02_10_stage08.py" status
```

The original `first_run_job`/`first_archive_job` fields are preserved. A nested `stack256_pilot` record links to the new retry receipt and job IDs. Task evidence appears in the new cesm.log as `[B02_STACK_PILOT] before_kib=...` and `after_kib=262144` (the first line also includes host/hard limit). Submission is not model success; require exact run/archive success, the task-side limits and archived restarts before scaling the repair or continuing AD395.

The retry directory/attempt receipt prevents duplicate recovery. Any ambiguous/cancel/submit failure leaves records for inspection; do not blindly rerun `retry`. Snapshots retain the original `env_run.xml`, state, CaseStatus and overwritten case stdout/stderr names. Original model logs remain under their original job IDs.

## Validation and remaining work

Six local tests passed: a real child wrapper raised its own soft stack to256MiB, preserved arguments/OMP_STACKSIZE and left the parent limit untouched; a mocked successful recovery changed only MPI_RUN_COMMAND and cancelled only4728103; partial submission retained its uncertain attempt/output; unexpected active jobs stopped submission; input drift was rejected; exact failed-run/blocked-archive identities were required. Python syntax and self-test passed. No real HPC retry has been executed by these local tests.

Actual retry outcome is pending. New node/runtime conditions can also differ, so successful operation after a stack increase supports the practical diagnosis but is not a formal single-variable proof. Other three retries, AD395, Normal400 and the six remaining scientific input choices are still unfinished.
