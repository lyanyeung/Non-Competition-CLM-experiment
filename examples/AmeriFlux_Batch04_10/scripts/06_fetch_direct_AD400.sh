#!/usr/bin/env bash
# Download an immutable release; no git pull. --all prepares and submits
# directly to AD400. --inputs only builds forcing, --prepare never submits.
set -euo pipefail
COMMIT=""
MODE="inputs"
MANIFEST=""
BASE="${HOME}/ameriflux_batch04_direct400"
while (($#)); do
  case "$1" in
    --commit) COMMIT="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --inputs|--prepare|--submit|--all) MODE="${1#--}"; shift ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo 'Use --commit with the published full 40-character commit'; exit 2; }
RELEASE="$BASE/$COMMIT"
PKG="$RELEASE/examples/AmeriFlux_Batch04_10"
mkdir -p "$PKG/scripts" "$PKG/data" "$RELEASE/metadata"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/AmeriFlux_Batch04_10"
FILES=(
 scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py
 scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py
 scripts/b04_stack_guard.py
 scripts/04_build_UTC_NOLEAP_DATM_and_inventory.py
 scripts/05_prepare_and_submit_direct_AD400.py
 data/AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv
 data/AMF_BATCH04_10_SOIL_SOURCE_SNAPSHOT_20261026.csv
 data/AMF_BATCH04_10_SOURCE_SURFACE_REGISTER_20261026.tsv
 data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json
 data/AMF_BATCH04_CO2_POLICY_20261026.json
)
for file in "${FILES[@]}"; do
  # A separate download plus cmp makes a resumed install reject source drift.
  temp="$(mktemp "$PKG/$file.download.XXXXXX")"
  curl -fLsS --retry 3 "$RAW/$file" -o "$temp"
  if [[ -e "$PKG/$file" ]]; then
    cmp -s "$temp" "$PKG/$file" || { echo "Existing release changed: $file"; exit 2; }
    rm -- "$temp"
  else
    mv -- "$temp" "$PKG/$file"
  fi
done
HEIGHT_SOURCE="$RELEASE/metadata/BASE_MeasurementHeight_20260908.csv"
if [[ ! -f "$HEIGHT_SOURCE" ]]; then
  curl -fLsS --retry 3 'https://raw.githubusercontent.com/lyanyeung/CLM-FATES-single-site-workflows/06c75f28f1b894db81ddb03a9a0ec8c4be9fc528/examples/AmeriFlux_sites/metadata/BASE_MeasurementHeight_20260908.csv' -o "$HEIGHT_SOURCE"
fi
printf '1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a  %s\n' "$HEIGHT_SOURCE" | sha256sum -c -
python3 -B -c 'import csv,json,sys; rows=list(csv.DictReader(open(sys.argv[1],encoding="utf-8-sig",newline=""))); policy=json.load(open(sys.argv[2])); assert len(policy)==10; [(None if rows[r["csv_line"]-2]=={k:v for k,v in r.items() if k!="csv_line"} else (_ for _ in ()).throw(RuntimeError("BASE source-row mismatch"))) for p in policy.values() for r in p["source_rows"]]; print("B04 ALL TEN HEIGHT POLICIES MATCH ORIGINAL BASE ROWS")' "$HEIGHT_SOURCE" "$PKG/data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json"
python3 -B "$PKG/scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py" --self-test
python3 -B "$PKG/scripts/04_build_UTC_NOLEAP_DATM_and_inventory.py" --self-test
python3 -B "$PKG/scripts/05_prepare_and_submit_direct_AD400.py" self-test
M="$PKG/scripts/04_build_UTC_NOLEAP_DATM_and_inventory.py"
C="$PKG/scripts/05_prepare_and_submit_direct_AD400.py"
if [[ -z "$MANIFEST" ]]; then
  [[ "$MODE" == inputs || "$MODE" == all ]] || { echo '--prepare/--submit need --manifest from the inputs step'; exit 2; }
  OUTDIR="/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10/DATM_UTC_NOLEAP_direct400/candidate_$(date -u +%Y%m%dT%H%M%SZ)_${RANDOM}"
  python3 -B "$M" --build --height-config "$PKG/data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json" --outdir "$OUTDIR"
  MANIFEST="$OUTDIR/B04_UTC_NOLEAP_DATM_MANIFEST.json"
fi
python3 -B "$M" --verify --manifest "$MANIFEST"
printf '%s\n' "$MANIFEST" > "$RELEASE/CURRENT_DATM_MANIFEST.txt"
printf 'B04 CURRENT MANIFEST: %s\n' "$MANIFEST"
if [[ "$MODE" == prepare || "$MODE" == all ]]; then
  python3 -B "$C" prepare --manifest "$MANIFEST" --confirm PREPARE_BATCH04_DIRECT_AD400_CASES_NO_SLURM
fi
if [[ "$MODE" == submit || "$MODE" == all ]]; then
  python3 -B "$C" verify --manifest "$MANIFEST"
  # The actual submitter raises only its own LOW soft stack and checks
  # Slurm propagation immediately before each case.submit, as Batch01.
  python3 -B "$C" submit-ad400 --manifest "$MANIFEST" --confirm SUBMIT_BATCH04_DIRECT_AD400_80x5_WITH_STACK_GUARD_ONCE
fi
printf 'B04 FINISHED MODE=%s; AD400 uses 80x5 years; no AD5 test/handoff.\n' "$MODE"
