#!/usr/bin/env bash
# Pinned one-command Batch04 FULL FATES/FIXNC project preparation.
# bash .../00_fetch_and_prepare_ameriflux_batch04.sh [--check-only|--build]
set -euo pipefail
MODE="--check-only"
if [[ $# -ge 1 ]]; then MODE="$1"; fi
if [[ "$MODE" != "--check-only" && "$MODE" != "--build" ]]; then
  echo "ERROR: use --check-only or --build" >&2; exit 2
fi
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment"
COMMIT="a51ece95c6cdcce6a6fba07f22980d4e277014d8"
REL="examples/AmeriFlux_Batch04_10"
TARGET="$HOME/ameriflux_batch04_fates_pair_setup_a51ece95c6cd"
mkdir -p "$TARGET/data" "$TARGET/scripts"
for filename in \
    AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv \
    AMF_BATCH04_10_SOIL_SOURCE_SNAPSHOT_20261026.csv \
    AMF_BATCH04_10_SOURCE_SURFACE_REGISTER_20261026.tsv; do
  curl -fLsS --retry 3 "$RAW/$COMMIT/$REL/data/$filename" \
    -o "$TARGET/data/$filename"
done
for filename in \
    01_audit_source_PFT_soil_surface_and_pair_plan.py \
    02_build_paired_PFT_surface_candidates_NO_CASES.py \
    b04_stack_guard.py; do
  curl -fLsS --retry 3 "$RAW/$COMMIT/$REL/scripts/$filename" \
    -o "$TARGET/scripts/$filename"
done
ONE="$TARGET/scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py"
TWO="$TARGET/scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py"
python3 -B -m py_compile "$ONE" "$TWO" "$TARGET/scripts/b04_stack_guard.py"
python3 -u -B "$TARGET/scripts/b04_stack_guard.py" --self-test
python3 -u -B "$ONE" --self-test
python3 -u -B "$TWO" --self-test
echo "B04 SOURCE PACKAGE PIN+SELFTEST PASS"
if [[ "$MODE" == "--check-only" ]]; then
  python3 -u -B "$ONE" --audit 2>&1 | tee "$TARGET/B04_source_input_10site_readonly.log"
  echo "B04 source audit done; no new surfaces or cases."
else
  python3 -u -B "$ONE" --plan 2>&1 | tee "$TARGET/B04_PAIRED_20ARM_PLAN.log"
  python3 -u -B "$TWO" --build 2>&1 | tee "$TARGET/B04_TEN_SHARED_PFT_SURFACE_BUILDS.log"
  echo "B04 PAIR PREPARATION: 10 versioned PFT start surfaces + 20 arm plan."
fi
echo "B04 ACTIVE_CASES=0, AD400_SUBMITTED=0, NORMAL400_SUBMITTED=0"
echo "B04 HOLDS: ZBOT, UTC DATM NC, FATES parameter maps, observed soil10/ORGANIC, CIME PTS."
