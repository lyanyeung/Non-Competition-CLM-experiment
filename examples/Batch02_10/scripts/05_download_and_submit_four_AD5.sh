#!/usr/bin/env bash
# Batch02 Stage05: check/submit/status of four existing AD5 cases.
set -euo pipefail
ACTION="${1:-check}"
if [[ "$#" -gt 1 || ( "$ACTION" != "check" && "$ACTION" != "submit" && "$ACTION" != "status" ) ]]; then
  echo "Usage: bash $0 [check|submit|status]" >&2
  exit 2
fi
for command in curl python3 sha256sum mktemp tee; do
  command -v "$command" >/dev/null || { echo "Missing command: $command" >&2; exit 1; }
done
REV="7fffc5297002cc9be90401ef66035397436656f8"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV"
WORK="$(mktemp -d "$HOME/Batch02_10_stage05.XXXXXXXX")"
mkdir -p "$WORK/examples/Batch02_10/scripts" "$WORK/examples/Batch02_10/tests" "$WORK/data"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/05_submit_four_AD5_cases.py" -o "$WORK/examples/Batch02_10/scripts/05_submit_four_AD5_cases.py"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py" -o "$WORK/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/scripts/03_build_four_surface_candidates.py" -o "$WORK/examples/Batch02_10/scripts/03_build_four_surface_candidates.py"
curl -fLsS --retry 3 "$RAW/data/batch02_four_surface_candidates_v1.json" -o "$WORK/data/batch02_four_surface_candidates_v1.json"
curl -fLsS --retry 3 "$RAW/data/batch02_10_stage02_source_snapshot_20261025.json" -o "$WORK/data/batch02_10_stage02_source_snapshot_20261025.json"
curl -fLsS --retry 3 "$RAW/examples/Batch02_10/tests/test_stage05_submission.py" -o "$WORK/examples/Batch02_10/tests/test_stage05_submission.py"
printf '%s  %s\n' \
  "e24a80906bb706325b54aea4e773f2f1cb35b3b4ff1075e374b24f180a612d93" "$WORK/examples/Batch02_10/scripts/05_submit_four_AD5_cases.py" \
  "728eeca4c47a880a07906ed44aad214443687c7c5c85cf84201c0ab9b4069445" "$WORK/examples/Batch02_10/scripts/04_prepare_four_AD5_cases.py" \
  "48dc150392f7095a2d0c72d8f79e795aef0ff938dac14cd9453c9e12b5743c54" "$WORK/examples/Batch02_10/scripts/03_build_four_surface_candidates.py" \
  "3145ac777c8043483acb776c8c72b7d86c7c6a29176441736a3c5224702d869e" "$WORK/data/batch02_four_surface_candidates_v1.json" \
  "a32d410144089ab49079dc7231885cc8221ce4262805352d87a528d98d86721c" "$WORK/data/batch02_10_stage02_source_snapshot_20261025.json" \
  "aa5ca6f046ff287e4d5a52a3c630cc1f0629f4b8de32757226605dad2fa71939" "$WORK/examples/Batch02_10/tests/test_stage05_submission.py" \
  | sha256sum -c -
SCRIPT="$WORK/examples/Batch02_10/scripts/05_submit_four_AD5_cases.py"
python3 -B "$SCRIPT" self-test
python3 -B "$WORK/examples/Batch02_10/tests/test_stage05_submission.py"
echo "PINNED_SOURCE=$REV"
echo "STAGE05_WORK=$WORK"
echo "CONSOLE_LOG=$WORK/stage05_$ACTION.log"
python3 -B "$SCRIPT" "$ACTION" 2>&1 | tee "$WORK/stage05_$ACTION.log"
