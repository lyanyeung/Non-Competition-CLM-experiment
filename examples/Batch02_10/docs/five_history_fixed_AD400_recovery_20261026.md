# Five Batch02 history-output failures: isolated AD400 recovery

Operator Stage42 output confirms all five failed during initial land history
construction: `GPP in fincl(4) ... history tape 1 ... not found`, followed by
`histFileMod.F90:899`. Each exact failed-run registry contains 1141 fields,
includes FATES_GPP and FATES_NPP, and excludes plain GPP/NPP. CaseDocs and
RUNDIR land inputs match, and all five report no restart/pointer/archive dates.
These are confirmed history-output failures; the downstream Slurm Killed
message does not establish OOM or a low-stack cause for these runs.

[Stage43 controller](../scripts/43_five_GPP_NPP_histfix_AD400.py) uses the proven
IT-Noe Stage40 same-site clone/keep-executable/private AD namelist workflow.
It pins the exact five effective land-input and failure-log SHA256 values from
the operator output before preparing any new case.

| Site | Failed job | New independent case |
| --- | --- | --- |
| ES-LJu | 4734425 | ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_AD400 |
| DK-Sor | 4734485 | DK-Sor_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400 |
| FR-FBn | 4734487 | FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400 |
| BE-Bra | 4734696 | BE-Bra_B02_FIXNC_MET34_GPPNPP_HISTFIX_AD400 |
| CH-Lae | 4734856 | CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_AD400 |

## Change and preservation contract

- Replace only tape1 names `GPP -> FATES_GPP` and `NPP -> FATES_NPP`; preserve
  TOTSOMC, TOTSOMN, TLAI, TWS and H2OSNO. The exact failed run must confirm all
  seven corrected fields registered before a clone is made.
  Downstream analyses must use the new FATES field names and their NetCDF
  units; do not carry over assumptions about the unavailable CLM GPP/NPP fields.
- Reuse each failed site's own existing configuration and executable. Preserve
  surface/PFT/soil, FATES parameter file, fixed CO2, coordinates, calendar,
  selected annual meteorology, MPI command and AD/FIXNC settings. Input files
  are hashed and compared during preparation and again before submission.
- Preview only new cases using the existing private AD namelist overlay,
  restore their original CTSM root/lock, and compare every effective land
  input line outside tape1. The only permitted extra delta is the single
  proven CIME `build-namelist` provenance comment with exact old-to-new case
  path substitution, as in IT-Noe Stage41/40.
- Preserve the exact effective source CDEPS XML byte for byte in the new
  CaseDocs and new RUNDIR after preview. This retains ES-LJu MET24, BE-Bra
  MET34 and CH-Lae MET36 selections already installed in effective XML by
  their controllers, instead of regenerating older candidate paths. Both
  files are checked again before `case.submit --skip-preview-namelist`.
- New run/archive directories must have no output. Old cases, their logs,
  receipts and pending archive jobs 4734426/4734486/4734488/4734697/4734857
  remain untouched. Only those exact old pending archive jobs are tolerated;
  any active old run/archive or queued new-case job stops recovery.
- Exclude the four completed Batch02 sites, current IT-Noe run, resolved old
  low-stack submissions and the separate AmeriFlux_Batch02_10 campaign.

## Run on IRIDIS6 Login: preparation without Slurm submission

No repository clone or pull is required. Download the standalone script:

```bash
(
  set -euo pipefail
  TOOL="$HOME/batch02_five_history_fixed_AD400_20261026.py"
  curl -fSL --retry 3 \
    https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/43_five_GPP_NPP_histfix_AD400.py \
    -o "$TOOL"
  python3 -B "$TOOL" --self-test
  python3 -u -B "$TOOL" --audit-source
  python3 -u -B "$TOOL" --prepare \
    --confirm PREPARE_FIVE_BATCH02_HISTORY_ONLY_NEW_CASES_NO_SUBMIT
  python3 -u -B "$TOOL" --verify
)
```

Require five `PREPARE PASS ... NO JOBS` and five `VERIFY PASS` lines. Preparation
uses CIME and reads input hashes; it does not compile a model or submit jobs.
All source cases pass before the first clone. Each new case has a create-only
attempt receipt **before** cloning. If the process fails partway, preserve
partial cases and receipts, inspect the reported difference, and do not rerun
the full preparation. `--sites ES-LJu DK-Sor ...` can select exact remaining
sites that have not been attempted; it must not bypass an uncertain receipt.

## Submit the new AD400 cases once

After all selected new cases verify, in the same Login shell:

```bash
(
  set -euo pipefail
  CURRENT_STACK_KB="$(ulimit -s)"
  if [[ "$CURRENT_STACK_KB" != unlimited && "$CURRENT_STACK_KB" -lt 65536 ]]; then
    ulimit -s unlimited 2>/dev/null || ulimit -s 65536
  fi
  ulimit -s
  python3 -u -B "$HOME/batch02_five_history_fixed_AD400_20261026.py" --start \
    --confirm SUBMIT_FIVE_BATCH02_HISTORY_FIXED_AD400_ONCE
)
```

This follows the operator-requested AmeriFlux Batch01 Stage21 submitter-stack
method: require at least 65536 KB soft stack or unlimited, preserve an already
higher limit, and reject an explicit SBATCH_PROPAGATE setting that excludes
STACK. It also inspects any batch-script propagation override. OMP_STACKSIZE
alone is not the submitter's process stack limit.

Preparation leaves RESUBMIT=0. The one-time start first revalidates the new
history/meteorology and source fingerprints, creates an exclusive submission
attempt receipt, sets RESUBMIT=79 and submits through CIME with skip-preview.
Each site is AD400 in 80 five-year segments, following the working IT-Noe
direct-AD400 pattern. No previous simulated years are discarded because these
five failed source runs have no checkpoint. Returned job IDs establish only
submission; inspect the first segment and subsequent archives for progress.
This stage does not start Normal400.

An error, timeout, missing job ID or lost connection after a submission attempt
must not be followed by another `--start`. Some sites may already be submitted.
Use status and receipts to reconcile the actual state. A failed skip-preview
persistence check can happen after jobs were submitted; it is not permission
to submit again.

## Read-only status

```bash
python3 -u -B "$HOME/batch02_five_history_fixed_AD400_20261026.py" --status
```

Status reads new-case receipts and Slurm accounting/queue only; it does not
submit, cancel or repair jobs and does not infer AD400 completion from a job
state. AD400 requires the final coordinated model restart at start-year+400
and successful archiving. Independent Normal400 remains a later operation.

## Validation

Local tests exercise all five source snapshots, fresh same-site clone/preview,
exact selected-stream restoration, history-only effective differences, input
preservation, 80x5 submission and duplicate prevention through mocked CIME and
Slurm boundaries. They also test altered final-source logs blocking all clones,
unintended scientific differences blocking a prepared case, uncertain
submission refusing a retry, low/high/unlimited stack policy and propagation
rejection. No real IRIDIS preparation or submission has been performed by
publishing this controller. Existing exploratory PFT and meteorology science
qualifications remain unchanged.
