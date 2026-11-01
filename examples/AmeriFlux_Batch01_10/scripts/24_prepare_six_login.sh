#!/usr/bin/env bash
# Download on login, then run the detached input preparation on a compute node.
set -euo pipefail
if [ "${1:-}" = '--run-prepared' ]; then
  [ "$#" -eq 2 ] || { echo 'Usage: --run-prepared /path/to/run.env' >&2; exit 2; }
  source "$2"
  : "${TOOL:?}" "${OUT:?}" "${PY:?}"
  printf 'Tool: %s\nCandidate output: %s\nLog: %s\n' "$TOOL" "$OUT" "$TOOL/prepare.log"
  set +e
  "$PY" -u -B "$TOOL/prepare.py" --stage14 "$TOOL/stage14.py" \
    --base-csv "$TOOL/base_heights.csv" --pft-csv "$TOOL/pft.csv" \
    --output "$OUT" --build 2>&1 | tee "$TOOL/prepare.log"
  STATUSES=("${PIPESTATUS[@]}")
  set -e
  if [ "${STATUSES[1]}" -ne 0 ]; then echo 'Log write failed.' >&2; exit 1; fi
  exit "${STATUSES[0]}"
fi

VERSION=${VERSION:?Set VERSION to the pinned Non-Competition repository revision}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid source revision' >&2; exit 1; }
REF='9aa2e578b3d5a539ff6bdc03b0240c4bb090529a'
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
SOURCE="https://raw.githubusercontent.com/lyanyeung/CLM-FATES-single-site-workflows/$REF"
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/amf_six_inputs_tool.XXXXXXXX")
ROOT='/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10'
OUT="$ROOT/Stage23_six_inputs_$(basename "$TOOL")"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/23_prepare_six_batch01_inputs.py" -o "$TOOL/prepare.py"
curl -fsSL "$BASE/examples/AmeriFlux_Batch01_10/scripts/14_laneA_four_static_UTC_DATM_proxies.py" -o "$TOOL/stage14.py"
curl -fsSL "$BASE/data/amf_batch01_recommended_pft_20261026.csv" -o "$TOOL/pft.csv"
curl -fsSL "$SOURCE/examples/AmeriFlux_sites/metadata/BASE_MeasurementHeight_20260908.csv" -o "$TOOL/base_heights.csv"
"$PY" - "$TOOL" <<'PY'
import hashlib, sys
from pathlib import Path
p = Path(sys.argv[1]); data = (p / 'pft.csv').read_bytes()
assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == '14c6352f46c4ed07da1f73dc58474ac0a55ef1ee', 'PFT source checksum mismatch'
assert hashlib.sha256((p / 'base_heights.csv').read_bytes()).hexdigest() == '1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a', 'BASE source checksum mismatch'
PY
printf 'TOOL=%q\nOUT=%q\nPY=%q\n' "$TOOL" "$OUT" "$PY" > "$TOOL/run.env"
printf '\nPrepared. Output: %s\nEnvironment: %s\nSource revision: %s\n' "$OUT" "$TOOL/run.env" "$VERSION"
printf '\nOn the interactive compute node run:\n'
printf 'bash %q --run-prepared %q\n' "$(realpath "$0")" "$TOOL/run.env"
printf '\nThis creates candidate inputs only, not cases or Slurm jobs.\n'

