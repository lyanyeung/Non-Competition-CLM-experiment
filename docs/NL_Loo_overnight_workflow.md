# NL-Loo overnight workflow (2026-10-23)

The pilot first segment (five years) has been **reported completed by the user**; it is **not verified remotely**. Do not assume the exact `CaseStatus` archive entries or rpointer staging until audited on IRIDIS6.

The only presently authorized automated extension is **remaining PRE50 45 years** in nine 5-year segments. Script `04_NL_Loo_spinup_45_200_300.py` includes modes `status`, `audit5`, `continue45`, `ad200`, `post300`. AD200 and post300 are **deliberately submission-blocked** until the pinned CTSM/FATES revision's mode transition, restart initialization and AD carbon pool semantics are validated. They do not auto-chain after PRE50. Do not manually disable this safety check simply to submit 550 years overnight.

## On the IRIDIS login node

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git status --short
git pull --ff-only origin main
bash scripts/05_NL_Loo_overnight_PRE50.sh 2>&1 | tee ~/NL_Loo_PRE50_overnight_20261023.log
```

If the audit says STOP, **do not blindly resubmit**. It may mean a Slurm job is still running/archiving, the final 2002 restart is incomplete, `CaseStatus` uses a different success string, or CIME moved rpointer files to its archive. If the script reports already-submitted, do not rerun. Both `sacct` IDs 4671182/4671183 must be COMPLETED; check final 2002 checkpoint and first PFT history output where possible. The 45y continuation uses `CONTINUE_RUN=TRUE`, `STOP_N=5`, `RESUBMIT=8` (initial 5-y continuation plus 8 CIME resubmissions). It expects the **existing latest restart pointer in RUNDIR**. It intentionally stops when this is absent to avoid a false startup.

## Check next morning

```bash
cd ~/Non-Competition-CLM-experiment
python scripts/04_NL_Loo_spinup_45_200_300.py status
squeue -u "$USER" -o '%.12i %.40j %.10T %R'
tail -40 /iridisfs/scratch/ly3n24/CLM_FATES/cases/NL-Loo_OBSPFT_NC_PRE50/CaseStatus
myfiles
```

If PRE50 reaches final 2047-01-01-00000, the **next separate action** is to validate mode switch and create AD200 from that particular three-component checkpoint. **AD200 and postAD300 have not been run, queued, or guaranteed.**
