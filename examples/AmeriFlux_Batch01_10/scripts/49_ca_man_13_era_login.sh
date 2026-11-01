#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
PREVIOUS='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/approved_met_candidates.TVqWqlLi/result/manifest.json'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$PREVIOUS"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/caman_13_candidate.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
curl -fsSL "$BASE/48_ca_man_13_era_candidate.py" -o "$TOOL/candidate.py"
curl -fsSL "$BASE/29_six_extreme_temperature_context.py" -o "$TOOL/context.py"
curl -fsSL "$BASE/32_usbar_inspectable_candidate.py" -o "$TOOL/physics.py"
printf 'Tool: %s\nOutput: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/prepare.log" "$VERSION"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/candidate.py" --run "$RUN" --previous "$PREVIOUS" \
  --context-helper "$TOOL/context.py" --physics-helper "$TOOL/physics.py" --out "$TOOL/result" \
  2>&1 | tee "$TOOL/prepare.log"
echo 'CA-Man 13 and 14 detached candidate generated; no model case or job was changed.'
