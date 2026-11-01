#!/usr/bin/env bash
# Prepare six new AD5 cases from reviewed Stage23 inputs; never submit Slurm jobs.
set -euo pipefail
VERSION=${VERSION:?Set VERSION to a pinned repository commit}
RUN=${RUN:?Set RUN to the completed Stage23 input directory}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid source revision' >&2; exit 1; }
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"
test -f "$RUN/COMPLETE.json"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/amf_six_ad5_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/26_six_ad5_case_preparation.py" -o "$TOOL/ad5.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
if ! curl -fsSL 'https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv' -o "$TOOL/co2.csv"; then
  PREVIOUS='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv'
  test -s "$PREVIOUS" || { echo 'NOAA CO2 download failed and no previous table was found.' >&2; exit 1; }
  cp "$PREVIOUS" "$TOOL/co2.csv"
  echo 'Using previous Batch02 NOAA CO2 table:' "$PREVIOUS"
fi
printf 'TOOL=%q\nRUN=%q\nPY=%q\n' "$TOOL" "$RUN" "$PY" > "$TOOL/run.env"
printf '\nTool: %s\nInput: %s\nLog: %s\nSource revision: %s\n' "$TOOL" "$RUN" "$TOOL/prepare.log" "$VERSION"
echo 'Preparing six detached AD5 cases; NO Slurm jobs will be submitted.'
set +e
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 \
  "$PY" -u -B "$TOOL/ad5.py" prepare --run "$RUN" --helper "$TOOL/helper.py" \
  --co2-csv "$TOOL/co2.csv" 2>&1 | tee "$TOOL/prepare.log"
STATUSES=("${PIPESTATUS[@]}")
set -e
if [ "${STATUSES[1]}" -ne 0 ]; then echo 'Log write failed.' >&2; exit 1; fi
if [ "${STATUSES[0]}" -eq 0 ]; then
  echo 'SIX AD5 CASE PREVIEWS COMPLETE; no model jobs were submitted.'
else
  echo 'PREVIEW STOPPED. Do not rerun blindly; preserve output and show the error.' >&2
fi
exit "${STATUSES[0]}"

