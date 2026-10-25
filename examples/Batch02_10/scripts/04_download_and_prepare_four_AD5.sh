#!/usr/bin/env bash
# Stage04 v2: pinned code/config + DATM XML regression fixtures; no Slurm.
set -euo pipefail
ACTION="${1:-plan}"
if [[ "$#" -gt 1 || ( "$ACTION" != "plan" && "$ACTION" != "prepare" ) ]]; then
  echo "Usage: bash $0 [plan|prepare]" >&2
  exit 2
fi
for command in curl python3 sha256sum mktemp tee; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done
REV="03be51d994cdd7323ec0beb29465f8eea6ab4ece"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV"
WORK="$(mktemp -d "$HOME/Batch02_10_stage04.XXXXXXXX")"
mkdir -p "$WORK/examples/Batch02_10/scripts" "$WORK/examples/Batch02_10/tests" "$WORK/data"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py" -o "$WORK/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/03_build_four_surface_candidates.py" -o "$WORK/examples/Batch02_10/scripts/03_build_four_surface_candidates.py"
curl -fLsS --retry 3 "$RAW/data/batch02_four_surface_candidates_v1.json" -o "$WORK/data/batch02_four_surface_candidates_v1.json"
curl -fLsS --retry 3 "$RAW/data/batch02_10_stage02_source_snapshot_20261025.json" -o "$WORK/data/batch02_10_stage02_source_snapshot_20261025.json"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/tests/test_stage04_streams.py" -o "$WORK/examples/Batch02_10/tests/test_stage04_streams.py"
printf '%s  %s\n' \
  "728eeca4c47a880a07906ed44aad214443687c7c5c85cf84201c0ab9b4069445" "$WORK/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py" \
  "48dc150392f7095a2d0c72d8f79e795aef0ff938dac14cd9453c9e12b5743c54" "$WORK/examples/Batch02_10/scripts/03_build_four_surface_candidates.py" \
  "3145ac777c8043483acb776c8c72b7d86c7c6a29176441736a3c5224702d869e" "$WORK/data/batch02_four_surface_candidates_v1.json" \
  "a32d410144089ab49079dc7231885cc8221ce4262805352d87a528d98d86721c" "$WORK/data/batch02_10_stage02_source_snapshot_20261025.json" \
  "b093df665ac44ef68e6198abdd49d6a54146ba4144eacd4323cac3259db82816" "$WORK/examples/Batch02_10/tests/test_stage04_streams.py" \
  | sha256sum -c -
SCRIPT="$WORK/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py"
python3 -B "$SCRIPT" self-test
python3 -B "$WORK/examples/Batch02_10/tests/test_stage04_streams.py"
echo "PINNED_SOURCE=$REV"
echo "STAGE04_WORK=$WORK"
echo "CONSOLE_LOG=$WORK/stage04_$ACTION.log"
python3 -B "$SCRIPT" "$ACTION" 2>&1 | tee "$WORK/stage04_$ACTION.log"
