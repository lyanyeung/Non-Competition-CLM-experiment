#!/usr/bin/env bash
# Fresh 38-site ICOS full-sequence diagnostics, foreground on login.
set -euo pipefail
BASE=${BASE:-https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main}
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/icos38_nt_tool.XXXXXXXX")
OUT="$HOME/CLM_FATES_PLOTS/ICOS38_NT_full_sequence_$(basename "$TOOL")"
RUN_ID="login-$("$PY" -c 'import uuid; print(uuid.uuid4().hex)')"
SOURCE_RUN=${SOURCE_RUN:-}
SOURCE_ARGS=()
if [ -n "$SOURCE_RUN" ]; then
  test -f "$SOURCE_RUN/site_status.csv"
  SOURCE_ARGS=(--source-run "$SOURCE_RUN")
fi
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$TOOL/scan.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py" -o "$TOOL/run.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/21_icos38_full_sequence.py" -o "$TOOL/icos38.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/22_publish_icos38_full_sequence.py" -o "$TOOL/publish.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/24_audit_ad_nee_histories.py" -o "$TOOL/audit_ad.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/25_verify_transfer_three_sites.py" -o "$TOOL/verify_transfer.py"
CORE_SHA=$(sha256sum "$TOOL/plot.py" | awk '{print $1}')
SCRIPT_SHA=$(sha256sum "$TOOL/icos38.py" | awk '{print $1}')
printf 'TOOL=%q\nOUT=%q\nPY=%q\nRUN_ID=%q\n' "$TOOL" "$OUT" "$PY" "$RUN_ID" > "$TOOL/run.env"
printf '\nRun: %s\nOutput: %s\nLog: %s\nEnvironment: %s\n\n' "$RUN_ID" "$OUT" "$TOOL/analysis.log" "$TOOL/run.env"
printf '%s\n' 'Checking historical source packages and extracted CSVs (read-only)...'
"$PY" -u -B "$TOOL/verify_transfer.py" 2>&1 | tee "$TOOL/transfer_audit.log"
set +e
"$PY" -u -B "$TOOL/icos38.py" --output-root "$OUT" "${SOURCE_ARGS[@]}" 2>&1 | tee "$TOOL/analysis.log"
STATUSES=("${PIPESTATUS[@]}")
set -e
if [ "${STATUSES[1]}" -ne 0 ]; then
  printf 'Log write failed; completion marker not written.\n' >&2
  exit 1
fi
printf '%s|%s|%s|%s\n' "$RUN_ID" "${STATUSES[0]}" "$CORE_SHA" "$SCRIPT_SHA" > "${OUT}.analysis_exit_status"
printf '\nAnalysis exit status: %s\nOutput: %s\n' "${STATUSES[0]}" "$OUT"
printf 'A nonzero exit records missing sites or EC; inspect site_status.csv and analysis.log.\n'
printf '\nTo publish the actual generated figures and a 38-site index:\n'
printf 'source %q\n' "$TOOL/run.env"
printf '%s\n' '"$PY" -B "$TOOL/publish.py" --run "$OUT" --run-id "$RUN_ID" --core "$TOOL/plot.py" --script "$TOOL/icos38.py"'
printf '\nTo audit representative AD NEE/NEP history fields:\n'
printf 'source %q\n' "$TOOL/run.env"
printf '%s\n' '"$PY" -u -B "$TOOL/audit_ad.py" --run "$OUT" | tee "$TOOL/ad_nee_audit.log"'
exit "${STATUSES[0]}"

