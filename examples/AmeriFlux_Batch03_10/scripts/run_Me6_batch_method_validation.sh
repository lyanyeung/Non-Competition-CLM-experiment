#!/usr/bin/env bash
# AmeriFlux Batch03 US-Me6: validated six-run candidate values; report-only.
set -euo pipefail
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate clm_fates_env
BASE="$HOME/ameriflux_batch03_Me6_method_validation"
mkdir -p "$BASE"
PIN="31e1c2cea29ecd8c9867e0c26ee114847cf67375"
RAW="https://raw.githubusercontent.com/lyanyeung/CLM-FATES-single-site-workflows/$PIN/examples/AmeriFlux_MultiSite_10_Batch03/scripts/stage13"
while read -r EXPECTED NAME; do
    curl -fLsS --retry 3 "$RAW/$NAME" -o "$BASE/$NAME"
    test "$(git hash-object "$BASE/$NAME")" = "$EXPECTED"
done <<'SOURCES'
de62b7f6d1001fafa923163e565b2945bb2a8816 13_validation_Me6_six_run_repair_candidates.py
734a9d988f45c9628131e77b669913d9b0f4e8ae 13x_Me6_6run_tower_QC0_vs_ERA_RH_skill_and_2017_QC2_edge_BATCH_READONLY.py
5a8dc69f5fb65015a9b7c9096153935684f466a8 13r_Me6_33_full_original_QC1_runs_QC0_ERA_RH_OPERATOR_SCOPE_READONLY.py
SOURCES
echo "ME6_BATCH_VALIDATION PINNED SOURCE HASHES VERIFIED"
python3 -B - "$BASE" <<'PY'
import sys
from pathlib import Path
for path in Path(sys.argv[1]).glob("*.py"):
    compile(path.read_text(), str(path), "exec")
print("ME6_BATCH_VALIDATION SYNTAX PASS; NO BYTECODE FILES", flush=True)
PY
SCRIPT="$BASE/13_validation_Me6_six_run_repair_candidates.py"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --run 2>&1 | tee "$BASE/Me6_batch_method_validation.log"
grep -qF "ME6_BATCH_VALIDATION SIX-RUN CANDIDATE COMPARISON COMPLETE" "$BASE/Me6_batch_method_validation.log"
echo "ME6_BATCH_VALIDATION COMPLETE | CANDIDATE VALUES AND VALIDATION ONLY; NO FORCING/SLURM"
