#!/usr/bin/env bash
# Use US-Bar's verified detached 2015 candidate for a provisional direct AD400.
set -euo pipefail
ACTION=${1:-}
case "$ACTION" in
  --prepare|--run)
    VERSION=${VERSION:?Set VERSION to a pinned GitHub commit}
    [[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
    RUN='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5'
    CAND='/iridisfs/home/ly3n24/CLM_FATES_PLOTS/usbar_candidate.22FNmD66/result/manifest.json'
    PY="$HOME/.conda/envs/clm_fates_env/bin/python"
    test -x "$PY"; test -f "$RUN/COMPLETE.json"; test -f "$CAND"
    mkdir -p "$HOME/CLM_FATES_PLOTS"
    TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/usbar_direct_ad400.XXXXXXXX")
    BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/40_usbar_direct_ad400_candidate.py" -o "$TOOL/usbar.py"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/36_six_direct_ad400.py" -o "$TOOL/direct.py"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/26_six_ad5_case_preparation.py" -o "$TOOL/stage26.py"
    curl -fsSL "$BASE/examples/AmeriFlux_Batch02_10/scripts/06_direct_AD400_ten_site_cases_and_submit.py" -o "$TOOL/helper.py"
    cp "$HOME/CLM_FATES_PLOTS/six_direct_ad400.3cjKoCdd/co2.csv" "$TOOL/co2.csv"
    printf 'TOOL=%q\nRUN=%q\nCAND=%q\nPY=%q\nVERSION=%q\n' "$TOOL" "$RUN" "$CAND" "$PY" "$VERSION" > "$TOOL/run.env"
    printf 'Tool: %s\nEnvironment: %s\nSource commit: %s\n' "$TOOL" "$TOOL/run.env" "$VERSION"
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 "$PY" -u -B "$TOOL/usbar.py" prepare \
      --run "$RUN" --helper "$TOOL/helper.py" --stage26 "$TOOL/stage26.py" --direct "$TOOL/direct.py" --candidate-manifest "$CAND" --co2-csv "$TOOL/co2.csv" 2>&1 | tee "$TOOL/prepare.log"
    if [[ "$ACTION" == --run ]]; then
      echo 'Provisional sensitivity case prepared; submitting once.'
      bash "$0" --submit "$TOOL/run.env"
    else
      echo "Prepared without submitting. To submit: bash $0 --submit $TOOL/run.env"
    fi
    ;;
  --submit|--status)
    ENVFILE=${2:?Expected the run.env path}; test -f "$ENVFILE"; source "$ENVFILE"
    OP=${ACTION#--}
    env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 15 "$PY" -u -B "$TOOL/usbar.py" "$OP" \
      --run "$RUN" --helper "$TOOL/helper.py" --stage26 "$TOOL/stage26.py" --direct "$TOOL/direct.py" --candidate-manifest "$CAND" --co2-csv "$TOOL/co2.csv" 2>&1 | tee "$TOOL/$OP.log"
    ;;
  *) echo 'Usage: VERSION=<commit> bash launcher --prepare|--run; bash launcher --submit|--status <run.env>' >&2; exit 2;;
esac
