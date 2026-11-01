#!/usr/bin/env bash
# Build user-approved detached candidates on login; never submit cases.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
PREVIOUS='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/approved_met_candidates.TVqWqlLi/result/manifest.json'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$PREVIOUS"; test -f "$(dirname "$PREVIOUS")/extended_context.csv"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/approved_cbo_caman.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
curl -fsSL "$BASE/48_ca_man_13_era_candidate.py" -o "$TOOL/man13.py"
curl -fsSL "$BASE/50_user_approved_cbo_caman_candidates.py" -o "$TOOL/candidates.py"
curl -fsSL "$BASE/29_six_extreme_temperature_context.py" -o "$TOOL/context.py"
curl -fsSL "$BASE/32_usbar_inspectable_candidate.py" -o "$TOOL/physics.py"
printf 'Tool: %s\nOutput: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/prepare.log" "$VERSION"
{
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
    "$PY" -u -B "$TOOL/man13.py" --run "$RUN" --previous "$PREVIOUS" \
    --context-helper "$TOOL/context.py" --physics-helper "$TOOL/physics.py" --out "$TOOL/man13"
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
    "$PY" -u -B "$TOOL/candidates.py" --run "$RUN" --previous "$PREVIOUS" --man2007 "$TOOL/man13/manifest.json" \
    --context-helper "$TOOL/context.py" --physics-helper "$TOOL/physics.py" --out "$TOOL/result"
} 2>&1 | tee "$TOOL/prepare.log"
echo 'User-approved candidates generated; no model input, case or Slurm job was changed.'
