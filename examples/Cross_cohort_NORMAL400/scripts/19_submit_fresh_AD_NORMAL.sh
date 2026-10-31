#!/usr/bin/env bash
# Download a pinned set of tools and submit fresh cross-cohort plots on IRIDIS6.
set -euo pipefail

BASE=${BASE:-https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main}
PLOT_PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PLOT_PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
PLOT_TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/fresh_tool.XXXXXXXX")
PLOT_OUT="$HOME/CLM_FATES_PLOTS/Fresh_AD_NORMAL_$(basename "$PLOT_TOOL")"

curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$PLOT_TOOL/scan.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py" -o "$PLOT_TOOL/run.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$PLOT_TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/18_publish_fresh_AD_NORMAL.py" -o "$PLOT_TOOL/publish.py"

cat > "$PLOT_TOOL/job.sh" <<'EOF'
#!/usr/bin/env bash
set -u
PLOT_SHA=$(sha256sum "$PLOT_TOOL/plot.py" | awk '{print $1}') || exit 1
"$PLOT_PY" -u -B "$PLOT_TOOL/run.py" --output-root "$PLOT_OUT"
PLOT_RC=$?
printf '%s|%s|%s\n' "$SLURM_JOB_ID" "$PLOT_RC" "$PLOT_SHA" > "${PLOT_OUT}.analysis_exit_status"
exit "$PLOT_RC"
EOF

export PLOT_TOOL PLOT_OUT PLOT_PY
PLOT_JOB_RAW=$(sbatch --parsable --partition=batch --job-name=fresh_ad_normal_plots \
  --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G --time=12:00:00 \
  --output="$PLOT_TOOL/slurm-%j.log" "$PLOT_TOOL/job.sh")
PLOT_JOB=${PLOT_JOB_RAW%%;*}
printf 'PLOT_TOOL=%q\nPLOT_OUT=%q\nPLOT_PY=%q\nPLOT_JOB=%q\n' \
  "$PLOT_TOOL" "$PLOT_OUT" "$PLOT_PY" "$PLOT_JOB" > "$PLOT_TOOL/run.env"
printf '\nJob: %s\nOutput: %s\nLog: %s\nEnvironment: %s\n' \
  "$PLOT_JOB" "$PLOT_OUT" "$PLOT_TOOL/slurm-$PLOT_JOB.log" "$PLOT_TOOL/run.env"
printf '\nAfter the job finishes, run:\n'
printf 'source %q\n' "$PLOT_TOOL/run.env"
printf '%s\n' '"$PLOT_PY" -B "$PLOT_TOOL/publish.py" --run "$PLOT_OUT" --job "$PLOT_JOB" --plotter "$PLOT_TOOL/plot.py"'

