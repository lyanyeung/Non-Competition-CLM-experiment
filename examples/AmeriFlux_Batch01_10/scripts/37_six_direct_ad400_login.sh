#!/usr/bin/env bash
# Prepare or submit direct AD400 cases from the IRIDIS login node.
set -euo pipefail
ACTION=${1:-}
case "$ACTION" in
  --prepare)
    VERSION=${VERSION:?Set VERSION to the pinned GitHub commit}
    [[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'VERSION must be a 40-character commit' >&2; exit 1; }
    RUN=${RUN:-/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5}
    PY="$HOME/.conda/envs/clm_fates_env/bin/python"
    test -x "$PY"; test -f "$RUN/COMPLETE.json"
    mkdir -p "$HOME/CLM_FATES_PLOTS"
    TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/six_direct_ad400.XXXXXXXX")
    BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/36_six_direct_ad400.py" -o "$TOOL/direct.py"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/26_six_ad5_case_preparation.py" -o "$TOOL/stage26.py"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
    if ! curl -fsSL 'https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv' -o "$TOOL/co2.csv"; then
      cp '/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv' "$TOOL/co2.csv"
    fi
    printf 'TOOL=%q\nRUN=%q\nPY=%q\nVERSION=%q\n' "$TOOL" "$RUN" "$PY" "$VERSION" > "$TOOL/run.env"
    echo "Tool: $TOOL"; echo "Environment: $TOOL/run.env"; echo "Source commit: $VERSION"
    shift
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 "$PY" -u -B "$TOOL/direct.py" prepare \
      --run "$RUN" --helper "$TOOL/helper.py" --stage26 "$TOOL/stage26.py" --co2-csv "$TOOL/co2.csv" "$@" 2>&1 | tee "$TOOL/prepare.log"
    echo "Prepared; no jobs submitted. To submit run: bash $0 --submit $TOOL/run.env"
    ;;
  --submit|--status)
    ENVFILE=${2:?Give the run.env path printed during preparation}
    test -f "$ENVFILE"; source "$ENVFILE"; shift 2
    OP=${ACTION#--}
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 "$PY" -u -B "$TOOL/direct.py" "$OP" \
      --run "$RUN" --helper "$TOOL/helper.py" --stage26 "$TOOL/stage26.py" --co2-csv "$TOOL/co2.csv" "$@" 2>&1 | tee "$TOOL/$OP.log"
    ;;
  *) echo 'Usage: VERSION=<commit> bash launcher --prepare [--sites ...]; bash launcher --submit|--status <run.env> [--sites ...]' >&2; exit 2;;
esac
