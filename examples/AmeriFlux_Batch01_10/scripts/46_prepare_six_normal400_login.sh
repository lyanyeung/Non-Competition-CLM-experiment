#!/usr/bin/env bash
# Audit AD400 and prepare eligible independent Normal400 cases; no Slurm.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
ACTION=${1:-prepare}
[[ "$ACTION" == prepare || "$ACTION" == audit ]] || { echo 'Use audit or prepare' >&2; exit 1; }
RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"; test -f "$RUN/COMPLETE.json"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/six_normal400_stage.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/45_prepare_six_normal400.py" -o "$TOOL/normal.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/36_six_direct_ad400.py" -o "$TOOL/direct.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/26_six_ad5_case_preparation.py" -o "$TOOL/stage26.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py" -o "$TOOL/lane.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
printf 'Tool: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/normal.log" "$VERSION"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/normal.py" "$ACTION" --run "$RUN" --helper "$TOOL/helper.py" \
  --direct "$TOOL/direct.py" --stage26 "$TOOL/stage26.py" --lane "$TOOL/lane.py" \
  2>&1 | tee "$TOOL/normal.log"
