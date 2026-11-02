#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
PREVIOUS='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/us_aud_stage64.qQc9qhf5/result/manifest.json'
REVIEW='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/us_aud_stage61_62.p1REVBxA/boundary/us_aud_review.csv'
test -x "$PY"; test -f "$PREVIOUS"; test -f "$REVIEW"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/us_aud_stage66.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
for pair in '66_us_aud_humidity_only.py:stage66.py' '64_us_aud_user_approved_boundaries.py:stage64.py' \
            '62_us_aud_user_approved_noaa_episodes.py:boundary.py' '59_three_site_extended_met_episode_audit.py:stage59.py' \
            '58_three_site_flagged_boundary_source_forensics.py:stage58.py' '29_six_extreme_temperature_context.py:context.py' \
            '53_approved_q1_and_cbo_merge.py:noaa.py' '43_approved_three_site_candidates.py:humidity.py' \
            '50_user_approved_cbo_caman_candidates.py:merge.py' '32_usbar_inspectable_candidate.py:physics.py'; do
  curl -fsSL "$BASE/${pair%%:*}" -o "$TOOL/${pair#*:}"
done
printf 'Tool: %s\nCandidate output: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/stage66.log" "$VERSION"
ARGS=(--previous "$PREVIOUS" --review "$REVIEW" --stage64 "$TOOL/stage64.py" --stage59 "$TOOL/stage59.py" \
      --stage58 "$TOOL/stage58.py" --context "$TOOL/context.py" --noaa "$TOOL/noaa.py" --humidity "$TOOL/humidity.py" \
      --merge "$TOOL/merge.py" --physics "$TOOL/physics.py" --boundary "$TOOL/boundary.py")
"$PY" -B "$TOOL/stage66.py" --self-test "${ARGS[@]}"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/stage66.py" "${ARGS[@]}" --out "$TOOL/result" 2>&1 | tee "$TOOL/stage66.log"
echo 'Detached humidity-only candidate created; no case or job was changed.'
