# NL-Loo fresh 550-year FIXNC pipeline — redesign v2

## Decision (23 October 2026)

**Cancel the existing 45-year PRE50 continuation** and **start a separate fresh experiment**, not a continuation of the previous successful 5 years. Existing restarts and archives are retained as evidence. This document does not claim any Slurm job has already been canceled.

Cancel script: `scripts/07_cancel_old_NL_Loo_PRE50.sh`, matching **only** exact Slurm job names `run.NL-Loo_OBSPFT_NC_PRE50` and `st_archive.NL-Loo_OBSPFT_NC_PRE50`. The script performs several queue sweeps to catch follow-on resubmissions. Verify the exact-match queue is empty before proceeding; if auto-resubmissions race the cancellation, stop and investigate. Never `scancel -u` or cancel unrelated sites.

**DEPRECATED / NOT SAFE TO ARM:** `scripts/06_NL_Loo_auto_550_pipeline.py`. Its auto-mode switch and watcher have not been tested end-to-end against CTSM revision `d5ea9d0136530370a62ef267ccfaff6f001ef914`. Do not run its `arm` or `tick`; do not run `scripts/04_NL_Loo_spinup_45_200_300.py` on the canceled experiment.

## New independent case namespace

* `NL-Loo_OBSPFT_NC_V2_PRE50`, **normal** 1997–2047 (50 model years)
* `NL-Loo_OBSPFT_NC_V2_AD200`, **AD** 2047–2247 (200 model years)
* `NL-Loo_OBSPFT_NC_V2_POST300`, **normal** 2247–2547 (300 model years)

Run and archive paths must also contain `_V2_` to prevent any collisions. The original surface is unchanged. Reuse the scientifically documented candidate `surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc` only if acceptable; it assigns 3.5% unresolved heather/grass cover to cool C3 grass and uses a 500m inventory as a flux-footprint proxy. Keep these uncertainties explicit.

## Requested unattended pipeline: engineering design

One **controller**, launched through Slurm, records one append-only durable run ledger and only advances after a complete checkpoint and successful model and archive jobs. The controller must never infer completion from existence of a directory or from a provisional job ID. Each model stage uses a five-year `STOP_N=5` and CIME `RESUBMIT` chain. Independent stage submission is performed only after final restart validation. On any error it must STOP and leave original and new outputs unmodified.

| Phase | Task | Minimum gates |
|---|---|---|
| Preflight | Verify new surface + FATES map, FATES No Competition, local CTSM version, byte hashes, no conflicting jobs, available inode headroom | All pass |
| V2 PRE50 | Fresh startup; 10 × 5-year segments | Check PFT patch area in first 5-y outputs and archive; no fallback to carbon fractions |
| PRE50 → AD200 | Stage **new** model case from 2047 3-component checkpoint | Verify restart names/pointers, version-specific `spinup_state` and initialization semantics, build compatibility |
| V2 AD200 | 40 × 5-year segments | Check soil carbon and state; no unsupported mode conversion |
| AD200 → POST300 | Stage **new** model case from 2247 checkpoint | Verify documented AD-to-normal carbon-pool transformation with a *successful real short test*, not merely namelist generation |
| V2 POST300 | 60 × 5-year segments | Check final restart, carbon/pool trends, PFT area and file quota |

### What is not yet verified

1. At the old 5-year run, observed FATES no-comp PFT **actual modeled patch-area fractions** were not confirmed; passing namelist parsing is insufficient.
2. Whether this exact CTSM+FATES executable may reuse `--keepexe` across changed `CLM_ACCELERATED_SPINUP`, and whether generated namelist emits `spinup_state=2`.
3. Whether a fresh hybrid restart with source-case filenames/pointers and `finidat` is compatible with CIME, DATM, FATES cohorts, CLM soil carbon pools and mode switching.
4. Whether all carbon pools are correctly converted AD → normal in this version (not just whether the model runs).
5. Slurm hourly requeue/watcher behavior, idempotency, deadlines, failure recovery and recurring model/autoresubmit job handling.

**Do not turn the controller into an unattended 550-year submission until these gates have been tested.** The objective is one-click *after a verified implementation*, not 550 years of unverified output.

## Operator commands now

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main

# Cancel ONLY old NL-Loo PRE50 job chain:
bash scripts/07_cancel_old_NL_Loo_PRE50.sh --confirm CANCEL_OLD_NL_LOO_PRE50_ONLY

# Verify no exact old job name remains:
squeue -u "$USER" -h -o '%i|%j|%T' |
  awk -F'|' '$2=="run.NL-Loo_OBSPFT_NC_PRE50" || $2=="st_archive.NL-Loo_OBSPFT_NC_PRE50" {print}'
```

If the last command prints nothing, the old queue is clear. Do **not** delete old case archives or existing valid restarts. The next deliverable is a V2 CIME mode and PFT area compatibility smoke test followed by a state-machine controller with proven stage transitions.
