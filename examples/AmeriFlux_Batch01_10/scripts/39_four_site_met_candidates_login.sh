#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:?Set VERSION to the pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
USBAR='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/usbar_candidate.22FNmD66/result/manifest.json'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$USBAR"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/four_met_candidates.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
curl -fsSL "$BASE/38_four_site_met_candidates.py" -o "$TOOL/candidates.py"
curl -fsSL "$BASE/29_six_extreme_temperature_context.py" -o "$TOOL/context.py"
curl -fsSL "$BASE/32_usbar_inspectable_candidate.py" -o "$TOOL/physics.py"
printf 'Tool: %s\nOutput: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/review.log" "$VERSION"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/candidates.py" --run "$RUN" --context-helper "$TOOL/context.py" \
  --physics-helper "$TOOL/physics.py" --usbar-manifest "$USBAR" --out "$TOOL/result" 2>&1 | tee "$TOOL/review.log"
echo 'Finished. Candidates are detached; no case or job was modified or submitted.'
