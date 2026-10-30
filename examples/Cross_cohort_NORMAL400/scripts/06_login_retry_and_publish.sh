#!/usr/bin/env bash
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

