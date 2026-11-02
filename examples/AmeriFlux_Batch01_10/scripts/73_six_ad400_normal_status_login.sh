#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
PY="$HOME/.conda/envs/clm_fates_env/bin/python"; test -x "$PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/six_ad_normal_status.XXXXXXXX")
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
for pair in '72_six_ad400_normal_status.py:status.py' '45_prepare_six_normal400.py:normal.py' \
            '26_six_ad5_case_preparation.py:stage26.py' '36_six_direct_ad400.py:direct.py' \
            '21_laneA_AD400_NORMAL400_controller.py:lane.py'; do
  curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/${pair%%:*}" -o "$TOOL/${pair#*:}"
done
curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
ARGS=(--normal "$TOOL/normal.py" --stage26 "$TOOL/stage26.py" --direct "$TOOL/direct.py" --lane "$TOOL/lane.py" --helper "$TOOL/helper.py")
printf 'Tool: %s\nLog: %s\nSource commit: %s\n' "$TOOL" "$TOOL/status.log" "$VERSION"
"$PY" -B "$TOOL/status.py" --self-test "${ARGS[@]}"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/status.py" "${ARGS[@]}" 2>&1 | tee "$TOOL/status.log"
