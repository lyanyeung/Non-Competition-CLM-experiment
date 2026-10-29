# Plot all completed AD400 → Normal400 FIXNC sites

The cross-cohort tool scans the live status of cases tagged `_FIXNC_` or
`_OBSPFT_NC_`. For each Normal case it follows its `RUN_REFCASE` to its actual
AD case; it does not independently choose the longest case for each mode.
Each pair has its own directory, even if several completed cases share a site.

The scanner requires both phases to show DONE, checks the final three-component
restart, and requires a continuous 400 years of archived land history per phase.
It refuses to proceed if `squeue` cannot be queried. This is a quick scan and
history check, not the cohort's formal Slurm/chain audit or proof of equilibrium.
Stopped, running, or unresolved cases remain in the summary without plots.

To run on IRIDIS6, paste the entire block below into a login shell. It submits
one analysis job to the `batch` partition, reading the existing cases and
archives without changing them. Adjust memory/time/partition to local policy if
needed. The job writes to a **new** timestamped folder on Home.

```bash
(
set -euo pipefail
BASE='https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/all_sites_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$TOOL/scan.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py" -o "$TOOL/run.py"
OUT="$HOME/CLM_FATES_PLOTS/All_completed_AD400_NORMAL400_$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$HOME/CLM_FATES_PLOTS/all_sites_%j.log"
JOB=$(sbatch --parsable --partition=batch --job-name=all_site_plots --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G --time=12:00:00 --output="$LOG" --wrap="'$PY' -u -B '$TOOL/run.py' --output-root '$OUT'")
JOB_ID=${JOB%%;*}
printf 'Job: %s\nOutput: %s\nLog: %s\n' "$JOB_ID" "$OUT" "${LOG/\%j/$JOB_ID}"
)
```

Check job progress with `squeue -u "$USER"` and read the printed log path.
When finished, inspect `all_sites_summary.csv` in the printed output directory.
Each completed pair writes under `<output>/<site>/<Normal-case>/`. `OK` means
the carbon and EC routines finished; `CARBON_OK_EC_ERROR` means carbon figures
exist but EC comparison failed; `SKIPPED` includes incomplete cases and errors.
The script exits nonzero if a DONE Normal case fails or no case is fully plotted.
It records results as it goes so earlier products survive later failures.

The archive contains only the fields originally requested at run time. Carbon
plots therefore show only available carbon variables; e.g. if only `TOTSOMC`
is present, no vegetation-carbon or ecosystem-carbon trajectory can be inferred.
`TLAI` is not plotted as a carbon pool. Metadata list missing primary pools.
The last complete aligned Normal forcing cycle is compared with available EC
GPP and NEE; NT outranks DT across sources, with explicit DT fallback. HH and HR
observations use equivalent 20-hour minimum daily coverage (40 half-hours or
20 hours), with at least 20 valid days for a month.

The Normal case's runtime DATM stream is preferred over its CaseDocs fallback.
The manifest records whether the AD and Normal stream files match; a difference
or missing comparison requires scientific review. Dates use the recorded EC
timestamps without timezone adjustment, so verify clock provenance, especially
for AmeriFlux cases with UTC-shifted forcing. Monthly model histories are
compared to available EC daily observations, which need not have identical
temporal support. R² is `1 - SSE/SST`, not squared correlation.

The local tests use synthetic inputs. The full live cross-cohort run and its
figures must still be checked on IRIDIS6 before they are used scientifically.

