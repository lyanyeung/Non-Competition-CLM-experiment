#!/usr/bin/env bash
# Stage61 boundaries and Stage62 user-approved detached candidates; no jobs.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to the pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
REVIEW='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/stage60_us_aud.tqIrP3ib/result'
test -x "$PY"; test -f "$REVIEW/manifest.json"; test -f "$REVIEW/us_aud_review.csv"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/us_aud_stage61_62.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
for pair in '61_us_aud_gap_boundary_review.py:stage61.py' '62_us_aud_user_approved_noaa_episodes.py:stage62.py' \
            '60_us_aud_noaa_extended_review.py:stage60.py' '59_three_site_extended_met_episode_audit.py:stage59.py' \
            '58_three_site_flagged_boundary_source_forensics.py:stage58.py' '29_six_extreme_temperature_context.py:context.py' \
            '53_approved_q1_and_cbo_merge.py:noaa.py' '43_approved_three_site_candidates.py:humidity.py' \
            '50_user_approved_cbo_caman_candidates.py:merge.py' '32_usbar_inspectable_candidate.py:physics.py'; do
  curl -fsSL "$BASE/${pair%%:*}" -o "$TOOL/${pair#*:}"
done
printf 'Tool: %s\nBoundary output: %s\nCandidate output: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/boundary" "$TOOL/candidates" "$TOOL/stage61_62.log" "$VERSION"
{
  "$PY" -B "$TOOL/stage61.py" --self-test --stage60 "$TOOL/stage60.py" --stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" --context-helper "$TOOL/context.py"
  "$PY" -B "$TOOL/stage62.py" --self-test --review "$REVIEW" --stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" --context "$TOOL/context.py" --noaa "$TOOL/noaa.py" --humidity "$TOOL/humidity.py" --merge "$TOOL/merge.py" --physics "$TOOL/physics.py"
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
    "$PY" -u -B "$TOOL/stage61.py" --stage60 "$TOOL/stage60.py" --stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" --context-helper "$TOOL/context.py" --out "$TOOL/boundary"
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
    "$PY" -u -B "$TOOL/stage62.py" --review "$REVIEW" --stage59 "$TOOL/stage59.py" --stage58 "$TOOL/stage58.py" --context "$TOOL/context.py" --noaa "$TOOL/noaa.py" --humidity "$TOOL/humidity.py" --merge "$TOOL/merge.py" --physics "$TOOL/physics.py" --out "$TOOL/candidates"
} 2>&1 | tee "$TOOL/stage61_62.log"
echo 'Both stages complete; no original input or case was changed, and no job was submitted.'
