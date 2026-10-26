# Batch02: five unresolved AD400 initial failures — operator triage

The operator's latest 26 October status supersedes earlier submission/running
snapshots: four Batch02 sites completed AD400; IT-Noe is running in its new
GPP/NPP history-fix case (operator reported model clock 2039); the five cases
below failed at initial AD execution. This is an operator report, not an
independent live Slurm or restart validation.

| Site | Failed run job | Exact source case |
| --- | --- | --- |
| ES-LJu | 4734425 | ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24 |
| DK-Sor | 4734485 | DK-Sor_B02_FIXNC_FOREST_PROXY_AD5 |
| FR-FBn | 4734487 | FR-FBn_B02_FIXNC_FOREST_PROXY_AD5 |
| BE-Bra | 4734696 | BE-Bra_B02_FIXNC_FOREST_MET34_AD400 |
| CH-Lae | 4734856 | CH-Lae_B02_FIXNC_FOREST_MET36_AD400 |

Exclude the previously resolved first low-stack submissions 4728068–4728108,
IL-Yat 4728152, superseded CA-TP4 V2 4728206, the four completed sites and the
active IT-Noe history-fix case. Do not re-submit a case just because an old
FAILED accounting entry is still visible.

## First obtain exact failure evidence

The standalone [five-case read-only diagnostic](../scripts/42_diagnose_five_failed_AD400_readonly.py)
reads actual CaseDocs/RUNDIR history requests, the exact failed job's land
history-field registry, plain/gzip model logs, accounting stdout/stderr paths,
selected submission-receipt stack metadata, CIME continuation settings, exact
current-case queue rows and restart artifact names. It never calls xmlchange,
case.submit or scancel and writes no case/data/receipt/report files. Terminal
output can be saved explicitly with tee.

On IRIDIS6 Login:

```bash
(
  set -euo pipefail
  TOOL="$HOME/batch02_five_failed_AD400_diagnose_20261026.py"
  curl -fSL --retry 3 \
    https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/42_diagnose_five_failed_AD400_readonly.py \
    -o "$TOOL"
  python3 -B "$TOOL" --self-test
  python3 -u -B "$TOOL" --diagnose 2>&1 | tee "$HOME/batch02_five_failed_AD400_diagnose_20261026.log"
)
```

The current Login shell's ulimit cannot establish the failed submission's
inherited stack. Stage26, Stage31, Stage35 and Stage37 already contain submit
stack guards; a new startup failure is not automatically the earlier 8 MiB
incident. A SIGKILL after CLM abort is also not proof of OOM. The diagnostic
labels only explicit signatures; an ESMF/SIGSEGV remains unclassified with
respect to stack cause.

The operator requested the Claude implementation in
[AmeriFlux_Batch01_10 Stage21](../../AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py)
as the recovery reference. Its `stack_guard()` checks **every submission** for
soft stack >=65536 KB (or unlimited), records soft/hard limits and directs a
low-stack submitter to raise the limit in the **same submitting shell** before
trying the submission action. Its older Stage18/20 scripts have no internal
stack guard; their successful launch relied on an already high-stack shell.
Future five-site recovery should use the Stage21 inheritance/check pattern and
`case.submit --skip-preview-namelist`, with the generated `.case.run` propagation
settings and persisted `skip_pnl` checked as well. This does not replace a
separately verified GPP/NPP history fix. Stage42 prints the relevant actual
batch-script/settings lines and MPI command to support that comparison.

## How the new run must depend on the result

1. **Confirmed missing history field:** Require the exact failed land log to
   report `htapes_fieldlist ERROR`, the effective requested GPP/NPP names to
   be absent from that run's complete registry, and FATES_GPP/FATES_NPP to be
   registered there. Follow the proven IT-Noe Stage40 method using a separate
   same-site clone with a new case/run/archive directory. Change only the
   relevant history-field names; retain the selected site-specific MET24,
   MET34 or MET36 meteorology, PFT, soil, executable, FIXNC and AD settings.
   Compare generated CaseDocs and actual RUNDIR namelists and streams before
   submission. Never copy IT-Noe's surface or forcing into another site.
2. **Segmentation or possible stack failure:** Inspect the first real model
   error, original submission receipt and batch-script stack/propagation
   settings. Preserve an already high/unlimited stack; raise a low soft limit
   only within the hard limit before CIME submits. The existing proven minimum
   is 64 MiB. Do not change meteorology/PFT or call a crash stack-related merely
   from its duration or signal. A standalone Fortran history-field abort must
   be repaired at the history list regardless of stack size.
3. **An existing coordinated checkpoint:** Validate model clock, complete
   land/atmosphere/coupler restart components and matching pointers first.
   Continue from the last validated AD checkpoint and calculate remaining
   years. Do not reset to startup or RESUBMIT=79 over existing progress. Mere
   file presence is not restart validation; the diagnostic reports names only.
4. **No successful checkpoint:** After confirming the failure/fix, use a new
   independently prepared run, initially verify the first five AD years, then
   complete the remaining 395 years. A new cold start must have independent
   empty run/archive paths. Do not repeatedly re-enter old one-shot Stage26,
   Stage31, Stage35 or Stage37 start commands or erase their attempt receipts.

Do not change the four completed AD400 sites or interrupt the current IT-Noe
history-fix run. Do not cancel broad site-prefix job sets: verify exact run and
archive names/IDs before any later queue repair. The correct new case and
submission command require the five actual failure outputs; this diagnostic
does not publish an unverified repair or start new jobs.

## Validation and references

Tests cover multiline/commented history lists, history-error precedence over
downstream SIGKILL, rejection of guessed low-stack causation, exact five-case
selection, plain/gzip failed logs, registry comparison, case-root CIME query
context, and byte/mtime preservation of synthetic source trees.

- [IT-Noe proven history fix](../scripts/40_IT_Noe_new_case_GPP_NPP_histfix_AD400.py)
- [Existing stack-aware forest submitter](../scripts/31_submit_four_forest_exploratory_AD400_once.py)
- [Official FATES history fields](https://escomp.github.io/CTSM/users_guide/setting-up-and-running-a-case/history_fields_fates.html)

Published diagnostics are not proof that these five cases have been restarted
or that AD400 has completed. Scientific forcing/PFT sensitivity qualifications
from their original controllers remain applicable.
