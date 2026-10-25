#!/usr/bin/env bash
# Batch02 Stage03: pinned four-site candidate inputs; no case or job operations.
set -euo pipefail
ACTION="${1:-plan}"
if [[ "$#" -gt 1 || ( "$ACTION" != "plan" && "$ACTION" != "build" ) ]]; then
  echo "Usage: bash $0 [plan|build]" >&2
  exit 2
fi
for command in curl python3 sha256sum mktemp tee; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done
REV="e3468f1e9d78d34311beb2c9a0e21a4800b2c1bd"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV"
WORK="$(mktemp -d "$HOME/Batch02_10_stage03.XXXXXXXX")"
mkdir -p "$WORK/examples/Batch02_10/scripts" "$WORK/data"
SCRIPT="$WORK/examples/Batch02_10/scripts/03_build_four_surface_candidates.py"
CONFIG="$WORK/data/batch02_four_surface_candidates_v1.json"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/03_build_four_surface_candidates.py" -o "$SCRIPT"
curl -fLsS --retry 3 "$RAW/data/batch02_four_surface_candidates_v1.json" -o "$CONFIG"
printf '%s  %s\n' \
  "48dc150392f7095a2d0c72d8f79e795aef0ff938dac14cd9453c9e12b5743c54" "$SCRIPT" \
  "3145ac777c8043483acb776c8c72b7d86c7c6a29176441736a3c5224702d869e" "$CONFIG" \
  | sha256sum -c -
python3 -B "$SCRIPT" self-test
echo "PINNED_SOURCE=$REV"
echo "STAGE03_WORK=$WORK"
echo "CONSOLE_LOG=$WORK/stage03_$ACTION.log"
if [[ "$ACTION" == "plan" ]]; then
  python3 -B "$SCRIPT" plan 2>&1 | tee "$WORK/stage03_plan.log"
else
  python3 -B "$SCRIPT" build --sites FI-Hyy FR-Hes CH-Fru IT-MBo \
    2>&1 | tee "$WORK/stage03_build.log"
fi
