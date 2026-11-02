#!/usr/bin/env bash
# Stage64 approved NOAA candidates and held-QC0 humidity context; no model jobs.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
BASE_RUN='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/us_aud_stage61_62.p1REVBxA'
REVIEW="$BASE_RUN/boundary"
PREVIOUS="$BASE_RUN/candidates/manifest.json"
test -x "$PY"; test -f "$REVIEW/manifest.json"; test -f "$REVIEW/us_aud_review.csv"; test -f "$PREVIOUS"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/us_aud_stage64.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
for pair in '64_us_aud_user_approved_boundaries.py:stage64.py' '62_us_aud_user_approved_noaa_episodes.py:boundary.py' \
            '59_three_site_extended_met_episode_audit.py:stage59.py' '58_three_site_flagged_boundary_source_forensics.py:stage58.py' \
            '29_six_extreme_temperature_context.py:context.py' '53_approved_q1_and_cbo_merge.py:noaa.py' \
            '43_approved_three_site_candidates.py:humidity.py' '50_user_approved_cbo_caman_candidates.py:merge.py' \
            '32_usbar_inspectable_candidate.py:physics.py'; do
  curl -fsSL "$BASE/${pair%%:*}" -o "$TOOL/${pair#*:}"
done
printf 'Tool: %s\nCandidate output: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/stage64.log" "$VERSION"
ARGS=(--review "$REVIEW" --previous "$PREVIOUS" --stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" \
      --context "$TOOL/context.py" --noaa "$TOOL/noaa.py" --humidity "$TOOL/humidity.py" --merge "$TOOL/merge.py" \
      --physics "$TOOL/physics.py" --boundary "$TOOL/boundary.py")
"$PY" -B "$TOOL/stage64.py" --self-test "${ARGS[@]}"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/stage64.py" "${ARGS[@]}" --out "$TOOL/result" 2>&1 | tee "$TOOL/stage64.log"
echo 'Detached candidates created. The December 19 10:00 QC0 forcing was retained; no case or job was changed.'
