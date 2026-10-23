# NL-Loo V3 — one-launch gated 550-year automation

This pipeline manages **50 normal years → 200 AD years → 300 post-AD normal years** using three distinct new CIME cases on IRIDIS6. It **does not** use or overwrite the previously canceled V1/V2 cases. `scripts/06` in the existing GitHub repository is an older, unvalidated prototype; do not arm it.

## Scientific and operational safety

- Reuses observed surface `surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc` and the pinned existing FATES build. For the 500m-area surface proxy, the 3.5% unresolved open cover is assigned to cool C3 grass; this is a documented assumption and does **not** establish actual modeled PFT occupied area. Review model PFT output separately.
- Normal PRE50: startup 1997-01-01, `CLM_ACCELERATED_SPINUP=off`, `STOP_N=5`, `RESUBMIT=9` for ten 5-year segments.
- At model year 2047, verify completed final 3-component restart, archive, and saved `spinup_state`. Set up an independent **hybrid** AD case, stage restart pointers and all restart files, point `finidat` at the staged land restart. Start with a **single 5-year test** in AD mode. Only on success and verified AD `spinup_state` continue 195 years with 39 five-year segments.
- At model year 2247, create independent hybrid post-AD case and similarly smoke-test the AD→Normal restart conversion. Only on success and normal `spinup_state=0` continue the remaining 295 years.
- Polling is performed by a Slurm watchdog job once per hour. On an error, the watchdog disables itself, retains error in `~/NL_Loo_V3_auto550/controller.json`, and leaves model results intact. No rollback, no destructive changes, no blind resubmission. No actions affecting unrelated jobs.
- Code passes Python syntax checks, but **has not been executed against the user's IRIDIS6 CTSM revision**. In particular, hybrid FATES cohort state transfer, `finidat` handling, compiler compatibility, and AD pool conversion need empirical verification. An automatic stop at an unverified transition is expected safe behavior, not a promise that all 550 years will complete.

## Install on IRIDIS6

The script is tracked in this GitHub repository. On IRIDIS6, run `git pull --ff-only origin main` from `~/Non-Competition-CLM-experiment`. Do **not** overwrite the old case scripts.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
python -m py_compile scripts/09_NL_Loo_V3_auto550.py
python scripts/09_NL_Loo_V3_auto550.py preflight
```

Only if preflight passes and the old PRE50/V2 tasks are confirmed canceled:

```bash
python scripts/09_NL_Loo_V3_auto550.py launch \
  --confirm LAUNCH_NL_LOO_FRESH_V3_550_YEARS \
  2>&1 | tee "$HOME/NL_Loo_V3_550_launch.log"
```

Do this **once**. No subsequent manual phase submission is part of the intended workflow. Do not rerun `launch` after partial success.

## Monitor

```bash
python ~/Non-Competition-CLM-experiment/scripts/09_NL_Loo_V3_auto550.py status
squeue -u "$USER" | grep -E 'NL-Loo_OBSPFT_NC_V3|NL-Loo-V3-watch' || true
cat ~/NL_Loo_V3_auto550/controller.json
ls -ltr ~/NL_Loo_V3_auto550/watch-*.log | tail
```

To disable **future automatic stage transitions** (not cancel jobs already running):

```bash
python ~/Non-Competition-CLM-experiment/scripts/09_NL_Loo_V3_auto550.py disarm
```

**Important:** If Slurm terminates a watcher unexpectedly (e.g., node outage), the next watcher will not necessarily be scheduled; inspect logs. No guarantee of unattended recovery is implied.