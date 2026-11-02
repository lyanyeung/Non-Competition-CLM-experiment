#!/bin/bash
# READ ONLY progress view of the phenology rollout (22 ad-run) and the needleleaf/phenology reruns.
#   bash watch_rollout.sh            one snapshot
#   watch -n 60 bash watch_rollout.sh   refresh every minute (Ctrl+C only stops watching)
LOG=${LOG:-$HOME/CLM_FATES_PLOTS/phen_ad_run.log}
CASES=/iridisfs/scratch/ly3n24/CLM_FATES/cases
echo "== $(date -u '+%H:%M UTC')  log: $LOG"

pid=$(pgrep -u "$USER" -f "22_phenology_patch_rollout.py ad-run" | head -1)
if [ -n "$pid" ]; then
  echo "ad-run: RUNNING (pid $pid, $(ps -o etime= -p "$pid" | tr -d ' ') elapsed)"
else
  echo "ad-run: not running$(grep -q 'sites OK' "$LOG" 2>/dev/null && echo ' (finished)')"
fi
b=$(pgrep -u "$USER" -af "case.build" | grep -oE "cases/[^ /]+" | head -1)
[ -n "$b" ] && echo "building now: ${b#cases/}"

cur=$(grep -E "^=== " "$LOG" 2>/dev/null | tail -1)
echo "current site: ${cur:-none yet}"
n_sites=$(grep -cE "^=== " "$LOG" 2>/dev/null)
n_built=$(grep -c "BUILT AND VERIFIED" "$LOG" 2>/dev/null)
n_sub=$(grep -cE "^  SUBMITTED " "$LOG" 2>/dev/null)
n_hold=$(grep -c ": HOLD" "$LOG" 2>/dev/null)
echo "sites started $n_sites / 42 | built+verified $n_built | submitted $n_sub | HOLD $n_hold"
if [ "$n_hold" != "0" ]; then echo "-- HOLD lines:"; grep ": HOLD" "$LOG" | cut -c1-220; fi
echo "-- last submissions:"; grep -E "^  SUBMITTED " "$LOG" 2>/dev/null | tail -3
tail -1 "$LOG" 2>/dev/null | grep "sites OK"

echo "-- queue ($USER): $(squeue -u "$USER" -h | wc -l) jobs; running: $(squeue -u "$USER" -h -t R | wc -l)"
echo "-- first segments finished (case.run success) per new case:"
for c in "$CASES"/*_PHEN "$CASES"/*_NLFP; do
  [ -f "$c/CaseStatus" ] || continue
  s=$(grep -c "case.run success" "$c/CaseStatus"); e=$(grep -c "case.run error" "$c/CaseStatus")
  [ "$e" != "0" ] && echo "   ERROR  $(basename "$c")"
  printf "%s %s\n" "$s" "$(basename "$c")"
done | sort -rn | awk '{n++; if ($1>0) ok++} END {printf "   %d new cases, %d with >= 1 finished 5-year segment\n", n, ok}'
