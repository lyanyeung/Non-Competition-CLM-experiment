#!/usr/bin/env bash
# Fresh cross-cohort plots in the foreground on the IRIDIS login node.
set -euo pipefail

BASE=${BASE:-https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main}
PLOT_PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PLOT_PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
PLOT_TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/fresh_login_tool.XXXXXXXX")
PLOT_OUT="$HOME/CLM_FATES_PLOTS/Fresh_login_AD_NORMAL_$(basename "$PLOT_TOOL")"
PLOT_ID="login-$("$PLOT_PY" -c 'import uuid; print(uuid.uuid4().hex)')"

curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$PLOT_TOOL/scan.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py" -o "$PLOT_TOOL/run.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$PLOT_TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/18_publish_fresh_AD_NORMAL.py" -o "$PLOT_TOOL/publish.py"

printf 'PLOT_TOOL=%q\nPLOT_OUT=%q\nPLOT_PY=%q\nPLOT_ID=%q\n' \
  "$PLOT_TOOL" "$PLOT_OUT" "$PLOT_PY" "$PLOT_ID" > "$PLOT_TOOL/run.env"
PLOT_SHA=$(sha256sum "$PLOT_TOOL/plot.py" | awk '{print $1}')
printf '\nRun: %s\nOutput: %s\nLog: %s\nEnvironment: %s\n\n' \
  "$PLOT_ID" "$PLOT_OUT" "$PLOT_TOOL/analysis.log" "$PLOT_TOOL/run.env"
printf '%s\n' 'Plotting runs in the foreground; output is also written to the log.'

set +e
"$PLOT_PY" -u -B "$PLOT_TOOL/run.py" --output-root "$PLOT_OUT" 2>&1 | tee "$PLOT_TOOL/analysis.log"
PLOT_STATUSES=("${PIPESTATUS[@]}")
set -e
PLOT_RC=${PLOT_STATUSES[0]}
if [ "${PLOT_STATUSES[1]}" -ne 0 ]; then
  printf 'Log write failed; no completion marker was written. Inspect %s\n' "$PLOT_TOOL" >&2
  exit 1
fi
printf '%s|%s|%s\n' "$PLOT_ID" "$PLOT_RC" "$PLOT_SHA" > "${PLOT_OUT}.analysis_exit_status"
printf '\nAnalysis exit status: %s\nOutput: %s\n' "$PLOT_RC" "$PLOT_OUT"
printf '%s\n' 'A nonzero status can indicate missing EC plots or skipped completed cases; review the summary and log.'
printf '\nTo upload the generated figures and convergence CSVs after review, run:\n'
printf 'source %q\n' "$PLOT_TOOL/run.env"
printf '%s\n' '"$PLOT_PY" -B "$PLOT_TOOL/publish.py" --run "$PLOT_OUT" --login "$PLOT_ID" --plotter "$PLOT_TOOL/plot.py"'
exit "$PLOT_RC"

