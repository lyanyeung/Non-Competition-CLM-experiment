# Stage06: all four first AD5 runs failed; diagnose before recovery

**Later operator diagnosis received:** all four cesm tasks segfault in ESMF mesh-center-coordinate initialization at `ESMCI_ESMFMesh_Util.C:1028`; four archives are DependencyNeverSatisfied. AD state2 is printed in land logs. [Stage07 inspects the actual meshes, local source and stack context](stage07_ESMF_mesh_SIGSEGV_targeted_inspection_20261025.md). The root trigger remains unverified; earlier requests for the general log output below are historical.

## Operator submission and scheduler result, 25 October 2026

Stage05 submission completed with four actual run/archive job pairs and persisted skip-preview options. The subsequent operator status check reported:

| Site | Run job | Run accounting | Archive job | Archive accounting |
| --- | ---: | --- | ---: | --- |
| FI-Hyy | 4728102 | FAILED / 1:0 | 4728103 | PENDING / 0:0 |
| FR-Hes | 4728104 | FAILED / 1:0 | 4728105 | PENDING / 0:0 |
| CH-Fru | 4728106 | FAILED / 1:0 | 4728107 | PENDING / 0:0 |
| IT-MBo | 4728108 | FAILED / 1:0 | 4728109 | PENDING / 0:0 |

Operator console: submission `Batch02_10_stage05.yNGjczuH/stage05_submit.log`; status `Batch02_10_stage05.3Js51UmW/stage05_status.log`. The ledger phase `FIRST_5Y_SUBMITTED` describes successful submission only, not model completion. PENDING/0:0 is not a successful archive. The supplied status did not print queue reasons or model error text, so neither a shared root cause nor a repair is established. Four failures suggest a common issue worth checking, but that remains an inference.

Do not rerun Stage05 submit or continue AD395. The original exclusive submission records remain intact.

## Read-only diagnosis

[Stage06](../scripts/06_diagnose_four_failed_AD5_readonly.py) is standalone Python standard library code; it needs no Stage03–05 downloads, NetCDF processing or annual-forcing rescan.

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage06.py"

  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/9aa24d9cb33bd21bb8e2a515c45e10f32c103174/examples/Batch02_10/scripts/06_diagnose_four_failed_AD5_readonly.py" \
    -o "$SCRIPT"

  echo "2a46fdeb0f8ea830fa8aeaf4f0c1690ada72aca6c0514f598f839f484d84b3c1  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" diagnose
)
```

The script reads exactly the eight known jobs with `sacct`, `squeue` and `scontrol`, uses Slurm's stdout/stderr paths, and checks bounded recent logs under each exact case/run directory. It reads CaseStatus, submit options, batch script, selected static XML/land-namelist metadata and cesm/cpl/lnd/atm/med/datm log families, including gzip logs. Error windows are printed, with fuller log tails retained in a new HOME report directory. Compressed expansion and plain-file reads are bounded; any truncation is labelled in JSON.

It writes only `failure_diagnosis.json` and `failure_diagnosis.txt` under a new HOME report directory. No case/forcing edits, CIME execution, cancellation or model submission occur. Missing/purged scheduler records and absent logs are retained as evidence gaps, not silently treated as success.

Self-test and a four-site mocked scheduler/log fixture passed, including gzip error extraction, exact case/job linking, report creation, source-file byte preservation and a read-only scheduler-command whitelist. Actual failure logs on IRIDIS are still needed before choosing a repair or recovering pending archives. AD395, Normal400 and the other six site choices remain unfinished.
