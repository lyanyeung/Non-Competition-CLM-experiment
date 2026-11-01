#!/usr/bin/env bash
# Generate only the explicitly user-approved detached Met candidates on login.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
REVIEW='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/manual_met_review.PVTs4H24/result/review.json'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$REVIEW"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/approved_met_candidates.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
curl -fsSL "$BASE/43_approved_three_site_candidates.py" -o "$TOOL/approved.py"
curl -fsSL "$BASE/29_six_extreme_temperature_context.py" -o "$TOOL/context.py"
curl -fsSL "$BASE/32_usbar_inspectable_candidate.py" -o "$TOOL/physics.py"
printf 'Tool: %s\nOutput: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/prepare.log" "$VERSION"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/approved.py" --run "$RUN" --review "$REVIEW" \
  --context-helper "$TOOL/context.py" --physics-helper "$TOOL/physics.py" --out "$TOOL/result" \
  2>&1 | tee "$TOOL/prepare.log"
echo 'Approved detached candidates generated; no model input, case or job was changed.'
