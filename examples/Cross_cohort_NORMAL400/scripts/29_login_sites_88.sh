#!/usr/bin/env bash
# Prepare on the login node; run the analysis in an interactive compute session.
set -euo pipefail
if [ "${1:-}" = '--run-prepared' ]; then
  [ "$#" -eq 2 ] || { echo 'Usage: --run-prepared /path/to/run.env' >&2; exit 2; }
  source "$2"
  : "${TOOL:?}" "${OUT:?}" "${PY:?}" "${RUN_ID:?}" "${VERSION:?}"
else
VERSION=${VERSION:?Set VERSION to a 40-character GitHub commit SHA}
[[ "$VERSION" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid source revision' >&2; exit 1; }
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$VERSION"
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
test -x "$PY"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/sites88_tool.XXXXXXXX")
OUT="$HOME/CLM_FATES_PLOTS/ICOS38_AmeriFlux50_$(basename "$TOOL")"
RUN_ID="login-$("$PY" -c 'import uuid; print(uuid.uuid4().hex)')"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$TOOL/scan.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py" -o "$TOOL/run.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/26_site_registry.py" -o "$TOOL/registry.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/27_plot_sites_88.py" -o "$TOOL/driver.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/28_publish_sites_88.py" -o "$TOOL/publish.py"
"$PY" - "$TOOL" <<'PY'
import hashlib, json, sys
from pathlib import Path
tool = Path(sys.argv[1]); names = ('plot.py','scan.py','run.py','registry.py','driver.py')
digests = {name: hashlib.sha256((tool / name).read_bytes()).hexdigest() for name in names}
(tool / 'initial_code_hashes.json').write_text(json.dumps(digests), encoding='utf-8')
PY
printf 'TOOL=%q\nOUT=%q\nPY=%q\nRUN_ID=%q\nVERSION=%q\n' "$TOOL" "$OUT" "$PY" "$RUN_ID" "$VERSION" > "$TOOL/run.env"
printf '\nRun: %s\nOutput: %s\nLog: %s\nEnvironment: %s\nSource commit: %s\n\n' \
  "$RUN_ID" "$OUT" "$TOOL/analysis.log" "$TOOL/run.env" "$VERSION"
if [ "${PREPARE_ONLY:-0}" = 1 ]; then
  printf 'Preparation complete. On an interactive compute node run:\n'
  printf 'bash %q --run-prepared %q\n' "$(realpath "$0")" "$TOOL/run.env"
  exit 0
fi
fi
printf '%s\n' 'Running in the foreground; a new snapshot is written without touching previous results.'
set +e
"$PY" -u -B "$TOOL/driver.py" --output-root "$OUT" 2>&1 | tee "$TOOL/analysis.log"
STATUSES=("${PIPESTATUS[@]}")
set -e
if [ "${STATUSES[1]}" -ne 0 ]; then
  echo 'Log write failed; no completion marker was written.' >&2; exit 1
fi
"$PY" - "$OUT" "$TOOL" "$RUN_ID" "$VERSION" "${STATUSES[0]}" <<'PY'
import csv, hashlib, json, sys
from pathlib import Path
out, tool, run_id, commit, rc = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
with (out / 'site_status.csv').open(newline='', encoding='utf-8') as f: sites = list(csv.DictReader(f))
with (out / 'case_status.csv').open(newline='', encoding='utf-8') as f: cases = list(csv.DictReader(f))
if len(sites) != 88 or len({r['Site'] for r in sites}) != 88 or any(r['Status'] == 'NOT_YET_CHECKED' for r in sites):
    raise SystemExit('Analysis did not finish the full 88-site inventory; not marking complete')
if {r['Site'] for r in cases} != {r['Site'] for r in sites}:
    raise SystemExit('Case inventory is incomplete; not marking complete')
names = ('plot.py','scan.py','run.py','registry.py','driver.py')
digests = {name: hashlib.sha256((tool / name).read_bytes()).hexdigest() for name in names}
if digests != json.loads((tool / 'initial_code_hashes.json').read_text(encoding='utf-8')):
    raise SystemExit('Analysis code changed during execution; not marking complete')
(out / 'RUN_COMPLETE.json').write_text(json.dumps({'run_id': run_id, 'source_commit': commit,
    'exit_code': rc, 'code_sha256': digests}, indent=2) + '\n', encoding='utf-8')
PY
printf '\nAnalysis exit status: %s\nOutput: %s\n' "${STATUSES[0]}" "$OUT"
printf '%s\n' 'A nonzero status may represent incomplete cases or missing EC data; inspect both status tables.'
printf '\nTo publish this snapshot after review, run:\n'
printf 'source %q\n' "$TOOL/run.env"
printf '%s\n' '"$PY" -B "$TOOL/publish.py" --run "$OUT" --run-id "$RUN_ID" --tool "$TOOL"'
exit "${STATUSES[0]}"

