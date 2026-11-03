#!/bin/bash
# Resume a 5-year-segment chain whose run job died (NODE_FAIL, transient start-up failure) from its last restart.
# Checks first (read only); submits only with --submit. Never used for a model error (ENDRUN, NaN, ...).
#   bash resume_failed_segment.sh CASE [CASE ...]            # check only
#   bash resume_failed_segment.sh --submit CASE [CASE ...]   # check, then case.submit --skip-preview-namelist
# A line per submission is appended to $EXP22/Needleleaf_F_rerun/resubmits.log.
SUBMIT=0; [ "${1:-}" = "--submit" ] && { SUBMIT=1; shift; }
U=${USER:-$(whoami)}
CASES=/iridisfs/scratch/ly3n24/CLM_FATES/cases
LEDGER=/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Needleleaf_F_rerun/resubmits.log
for C in "$@"; do
  W=$CASES/$C
  echo "=== $C"
  [ -d "$W" ] || { echo "  HOLD: case not found"; continue; }
  cd "$W" || continue
  q=$(squeue -u "$U" -h -o "%i %j %T" | awk -v c="$C" '{n=$2; sub(/^[^.]*\./,"",n); if (n==c) print}')
  if [ -n "$q" ]; then
    stuck=$(echo "$q" | awk '{print $1}' | tr '\n' ' ')
    if echo "$q" | grep -qv "st_archive"; then echo "  HOLD: jobs still queued: $q"; continue; fi
    echo "  only orphaned st_archive job(s) left: $stuck (cancelled before resubmitting)"
    [ $SUBMIT = 1 ] && scancel $stuck
  fi
  last=$(grep -E "case.run (starting|success|error)|st_archive (starting|success|error)" CaseStatus | tail -1)
  echo "  last CaseStatus event: ${last:0:90}"
  if ! echo "$last" | grep -qE "case.run (starting|error)"; then echo "  HOLD: last event is not a failed/aborted run"; continue; fi
  cr=$(./xmlquery --value CONTINUE_RUN); rs=$(./xmlquery --value RESUBMIT); rd=$(./xmlquery --value RUNDIR)
  ar=$(./xmlquery --value DOUT_S_ROOT)
  latest=$(ls "$ar/rest" 2>/dev/null | sort | tail -1)
  ptr=$(head -1 "$rd/rpointer.lnd" 2>/dev/null)
  echo "  CONTINUE_RUN=$cr RESUBMIT=$rs | latest archived restart: ${latest:-none} | rpointer.lnd: ${ptr:-missing}"
  if [ "$cr" != "TRUE" ]; then echo "  HOLD: CONTINUE_RUN is not TRUE (first segment?) - check by hand"; continue; fi
  if [ -z "$latest" ] || ! echo "$ptr" | grep -q "$latest"; then echo "  HOLD: rpointer does not point to the latest archived restart"; continue; fi
  miss=0
  for p in rpointer.lnd rpointer.atm rpointer.cpl; do
    f=$(head -1 "$rd/$p" 2>/dev/null); [ -s "$rd/$f" ] || { echo "  HOLD: $p -> $f missing in RUNDIR"; miss=1; }
  done
  [ $miss = 1 ] && continue
  if [ $SUBMIT = 0 ]; then echo "  OK to resume from $latest (dry run; add --submit)"; continue; fi
  out=$(./case.submit --skip-preview-namelist 2>&1)
  ids=$(echo "$out" | grep -oE "Submitted job [a-z_.]+ with id [0-9]+" | tr '\n' ';')
  echo "  RESUBMITTED from $latest: ${ids:-$(echo "$out" | tail -2)}"
  echo "$(date -u +%FT%TZ) $C from $latest RESUBMIT=$rs $ids" >> "$LEDGER"
done
