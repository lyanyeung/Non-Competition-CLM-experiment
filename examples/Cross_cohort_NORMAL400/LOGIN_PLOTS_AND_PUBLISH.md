# Run the missing-figure analysis and upload from the login node

This run reads the current cases and archives on the login node, without Slurm
submission. It checks that original analysis job 4764252 and supplementary job
4766277 are no longer running. It reuses their completed PNGs where both case
names and the three expected figures match; it re-scans and plots any other
currently completed AD400→Normal400 cases. If a previous job has no readable
summary, the analysis can still proceed from the live cases.

Paste the complete block into the IRIDIS6 login shell. Keep the session open;
the analysis may take time. On completion it automatically runs the publisher on
the login node. The publisher uploads only the already-generated PNGs, a README
index and SHA256SUMS, to a new directory in the GitHub repository. It lists
missing/partial results and never uploads raw or derived data tables. If the
plotting process is interrupted before its completion marker, it does not push.

```bash
(
set -euo pipefail
BASE='https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/login_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$TOOL/scan.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/04_retry_missing_sites.py" -o "$TOOL/retry.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/05_publish_completed_figures.py" -o "$TOOL/publish.py"
OUT="$HOME/CLM_FATES_PLOTS/Login_completed_AD400_NORMAL400_$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$TOOL/analysis.log"
printf 'Analysis output: %s\nAnalysis log: %s\nPublish script: %s\n' "$OUT" "$LOG" "$TOOL/publish.py"
if "$PY" -u -B "$TOOL/retry.py" --login --previous-job 4764252 --extra-job 4766277 --output-root "$OUT" 2>&1 | tee "$LOG"; then
  echo 'Analysis finished without reported completed-case errors.'
else
  echo 'Analysis returned a nonzero status; inspect the log and summary.'
fi
if [ -f "$OUT/RUN_COMPLETE.json" ]; then
  "$PY" -u -B "$TOOL/publish.py" --login --run "$OUT" --publish
else
  echo 'Analysis did not reach its completion marker; GitHub upload was not started.'
  echo "Inspect $LOG and retain all existing outputs."
  exit 1
fi
)
```

`PUSH SUCCESS` plus a commit and GitHub URL means upload succeeded. A completed
analysis may still have missing figures: inspect `all_sites_summary.csv` and the
GitHub index. Reaching 400+400 years is not an equilibrium certificate; missing
carbon fields cannot be reconstructed, and NT GPP may fall back to DT when NT
is unavailable. Check the clock and forcing provenance before interpretation.

If the GitHub push fails because of credentials or a non-fast-forward update,
the analysis outputs remain unchanged. After addressing Git authentication on
the login node, repeat only the publisher command using the paths printed at
the start:

```bash
"$HOME/.conda/envs/clm_fates_env/bin/python" -B '<Publish script>' \
  --login --run '<Analysis output>' --publish
```

Do not send passwords or access tokens in chat. This code update has synthetic
unit tests; it has not yet been run against the actual IRIDIS files or GitHub
credentials. The tail of the old job showing only Slurm resource usage does not
explain why it exited 1; inspect the earlier log lines for the actual errors.

