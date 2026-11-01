#!/usr/bin/env bash
# Generate user-approved detached Q1 and CA-Cbo candidate merges.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
APPROVED='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/approved_met_candidates.TVqWqlLi/result/manifest.json'
INITIAL='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/four_met_candidates.3j2pvGeO/result/manifest.json'
JOINT='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/approved_cbo_caman.oBqQP1GV/result/manifest.json'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$APPROVED"; test -f "$INITIAL"; test -f "$JOINT"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/approved_q1_cbo.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION/examples/AmeriFlux_Batch01_10/scripts"
curl -fsSL "$BASE/53_approved_q1_and_cbo_merge.py" -o "$TOOL/candidates.py"
curl -fsSL "$BASE/29_six_extreme_temperature_context.py" -o "$TOOL/context.py"
curl -fsSL "$BASE/32_usbar_inspectable_candidate.py" -o "$TOOL/physics.py"
curl -fsSL "$BASE/43_approved_three_site_candidates.py" -o "$TOOL/prior.py"
curl -fsSL "$BASE/50_user_approved_cbo_caman_candidates.py" -o "$TOOL/merge.py"
printf 'Tool: %s\nOutput: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/result" "$TOOL/prepare.log" "$VERSION"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/candidates.py" --run "$RUN" --approved "$APPROVED" --initial "$INITIAL" --joint "$JOINT" \
  --context-helper "$TOOL/context.py" --physics-helper "$TOOL/physics.py" --prior-helper "$TOOL/prior.py" \
  --merge-helper "$TOOL/merge.py" --out "$TOOL/result" 2>&1 | tee "$TOOL/prepare.log"
echo 'User-approved Q1 and CA-Cbo candidates generated; no original file, case or Slurm job was modified.'
