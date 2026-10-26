#!/usr/bin/env bash
# Batch02 bootstrap (no git pull), source-pinned to both repositories.
# Modes audit(default), soil10, check-surfaces, build-surfaces.
# None of these modes submits a Slurm job or creates a FIXNC CIME case.
set -euo pipefail
MODE="${1:-audit}"
case "$MODE" in audit|soil10|check-surfaces|build-surfaces) ;; *) echo 'Use audit | soil10 | check-surfaces | build-surfaces' >&2; exit 2;; esac
NCREV=3b165ec39558525a072fbc8e6f3619b09052139e
MAINREV=f4a17c66cc2a07d933edfbc03efcbb503187907b
NCROOT="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$NCREV"
MAINROOT="https://raw.githubusercontent.com/lyanyeung/CLM-FATES-single-site-workflows/$MAINREV"
WORK="$HOME/AMF_Batch02_FIXNC_bootstrap"
NC="$WORK/nc/examples/AmeriFlux_Batch02_10"
SRC="$WORK/soil_source/examples/Ameriflux_Site"
SOIL="$SRC/Ameriflux_Soil"
OUT="$HOME/CLM_FATES_SOIL/AmeriFlux50_20261026"
fetch(){ mkdir -p "$(dirname "$3")"; curl -fLsS --retry 3 "$1/$2" -o "$3"; }
fetch "$NCROOT" examples/AmeriFlux_Batch02_10/scripts/03_stack_guard_and_FIXNC_submission.py "$NC/scripts/03_stack_guard_and_FIXNC_submission.py"
fetch "$NCROOT" examples/AmeriFlux_Batch02_10/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py"
fetch "$NCROOT" examples/AmeriFlux_Batch02_10/data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv "$NC/data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv"
test "$(git hash-object "$NC/scripts/03_stack_guard_and_FIXNC_submission.py")" = b622eae34bdcbefb0b82117fb4120b81a1380c62
test "$(git hash-object "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py")" = 84ee53d68b71b0d54d5e0fb888636fb3e941910d
fetch "$MAINROOT" examples/Ameriflux_Site/Ameriflux_Soil/scripts/01_collect_soil_texture_evidence.py "$SOIL/scripts/01_collect_soil_texture_evidence.py"
test "$(git hash-object "$SOIL/scripts/01_collect_soil_texture_evidence.py")" = 231aedd5d7105c6d7557de0cff6287ee61ad361b
for f in literature_soil_evidence_20261026.csv reesh_records_found_20261026.csv badm_manual_depth_assignments_20261026.csv site_proxy_assignments_20261026.csv; do
 fetch "$MAINROOT" "examples/Ameriflux_Site/Ameriflux_Soil/data/$f" "$SOIL/data/$f"
done
fetch "$MAINROOT" examples/Ameriflux_Site/Ameriflux_PFT/metadata/sites_50_manifest.csv "$SRC/Ameriflux_PFT/metadata/sites_50_manifest.csv"
SOFT="$(ulimit -s)"
if [[ "$SOFT" != unlimited ]] && (( SOFT < 65536 )); then
  ulimit -s 300000 || ulimit -s 65536 || { echo 'HARD STACK LIMIT TOO LOW; use another login node' >&2; exit 4; }
fi
echo "AMF_B02_SHELL_STACK SOFT=$(ulimit -s) HARD=$(ulimit -Hs) KB"
python3 -B -m py_compile "$NC/scripts/03_stack_guard_and_FIXNC_submission.py" "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py" "$SOIL/scripts/01_collect_soil_texture_evidence.py"
python3 -B "$NC/scripts/03_stack_guard_and_FIXNC_submission.py" --self-test
python3 -B "$NC/scripts/03_stack_guard_and_FIXNC_submission.py" --audit
python3 -B "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py" --self-test
python3 -B "$SOIL/scripts/01_collect_soil_texture_evidence.py" --self-test
echo 'AMF_B02_STACK_AND_SOURCE_CHECK_PASS | no jobs'
if [[ "$MODE" == soil10 ]]; then
 python3 -B "$SOIL/scripts/01_collect_soil_texture_evidence.py" --sites US-BZS US-CMW US-EML US-GLE US-Ha1 US-Ho1 US-Ho2 US-Ho3 US-ICh US-ICt --output-root "$OUT"
fi
if [[ "$MODE" == soil10 || "$MODE" == check-surfaces || "$MODE" == build-surfaces ]]; then
 WIDE="$OUT/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv"
 test -s "$WIDE" || { echo "MISSING 10-LAYER SOURCE $WIDE" >&2; exit 5; }
 python3 -B "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py" --check --soil-wide "$WIDE"
fi
if [[ "$MODE" == build-surfaces ]]; then
 python3 -B "$NC/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py" --build --soil-wide "$WIDE"
fi
echo "AMF_B02_BOOTSTRAP_$MODE COMPLETED | NO CIME/SLURM MODEL JOBS"
