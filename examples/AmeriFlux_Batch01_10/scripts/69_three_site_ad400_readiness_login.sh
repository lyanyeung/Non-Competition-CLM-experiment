#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
CO2="$HOME/CLM_FATES_PLOTS/six_direct_ad400.3cjKoCdd/co2.csv"
test -x "$PY"; test -f "$CO2"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/three_site_stage68.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
for pair in '68_three_site_ad400_readiness.py:stage68.py' '59_three_site_extended_met_episode_audit.py:stage59.py' \
            '58_three_site_flagged_boundary_source_forensics.py:stage58.py' '29_six_extreme_temperature_context.py:context.py' \
            '26_six_ad5_case_preparation.py:stage26.py' '36_six_direct_ad400.py:direct.py' \
            '32_usbar_inspectable_candidate.py:physics.py'; do
  curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/${pair%%:*}" -o "$TOOL/${pair#*:}"
done
curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
ARGS=(--stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" --context "$TOOL/context.py" \
      --stage26 "$TOOL/stage26.py" --direct "$TOOL/direct.py" --physics "$TOOL/physics.py" \
      --helper "$TOOL/helper.py" --co2-csv "$CO2")
printf 'Tool: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/stage68.log" "$VERSION"
"$PY" -B "$TOOL/stage68.py" --self-test "${ARGS[@]}"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/stage68.py" "${ARGS[@]}" 2>&1 | tee "$TOOL/stage68.log"
echo 'Read-only readiness audit complete; no case or job was created.'
