#!/bin/bash
# READ ONLY. For every st_archive job held as DependencyNeverSatisfied, find the case and the run job it waited for,
# then show why that run job ended (Slurm state, CaseStatus, error lines in cesm.log / lnd.log) and where the chain is.
#   bash triage_failed_chains.sh            all such jobs of $USER
#   bash triage_failed_chains.sh 4831155    only these st_archive job ids
U=${USER:-$(whoami)}
CASES=/iridisfs/scratch/ly3n24/CLM_FATES/cases
if [ $# -gt 0 ]; then IDS="$*"; else
  IDS=$(squeue -u "$U" -h -t PD -o "%i %r" | awk '$2=="DependencyNeverSatisfied"{print $1}'); fi
[ -z "$IDS" ] && { echo "no DependencyNeverSatisfied jobs"; exit 0; }
for J in $IDS; do
  name=$(squeue -h -j "$J" -o "%j" 2>/dev/null); dep=$(squeue -h -j "$J" -o "%E" 2>/dev/null)
  C=${name#st_archive.}; W=$CASES/$C
  R=$(echo "$dep" | grep -oE "[0-9]{6,}" | head -1)
  echo "=================================================================="
  echo "st_archive $J  case: $C"
  echo "  waits on: $dep"
  [ -n "$R" ] && sacct -j "$R" -X -n -P -o JobID,JobName%60,State,ExitCode,Elapsed,Timelimit,NodeList,End 2>/dev/null \
    | awk -F'|' '{printf "  run job %s  %s  exit %s  elapsed %s / %s  node %s  end %s\n",$1,$3,$4,$5,$6,$7,$8}'
  [ -d "$W" ] || { echo "  case dir not found: $W"; continue; }
  cd "$W" || continue
  echo "  CaseStatus (last 3):"; tail -3 CaseStatus | cut -c1-140 | sed 's/^/    /'
  rd=$(./xmlquery --value RUNDIR); ar=$(./xmlquery --value DOUT_S_ROOT)
  echo "  RUN_STARTDATE=$(./xmlquery --value RUN_STARTDATE) STOP_N=$(./xmlquery --value STOP_N) CONTINUE_RUN=$(./xmlquery --value CONTINUE_RUN) RESUBMIT=$(./xmlquery --value RESUBMIT)"
  echo "  last archived restart: $(ls "$ar/rest" 2>/dev/null | sort | tail -1)  ($(ls "$ar/rest" 2>/dev/null | wc -l) restart sets)"
  cl=$(ls -t "$rd"/cesm.log.${R}* 2>/dev/null | head -1); [ -z "$cl" ] && cl=$(ls -t "$rd"/cesm.log.* 2>/dev/null | head -1)
  ll=$(ls -t "$rd"/lnd.log.${R}* 2>/dev/null | head -1); [ -z "$ll" ] && ll=$(ls -t "$rd"/lnd.log.* 2>/dev/null | head -1)
  echo "  cesm.log: ${cl:-none}"
  [ -n "$cl" ] && zgrep -aiE "ENDRUN|ERROR|SIGSEGV|segmentation|forrtl|NaN|abort|killed|out of memory|oom|negative|failed|CANCELLED|TIME LIMIT" "$cl" \
    | grep -v "^ *$" | awk '!s[$0]++' | head -12 | cut -c1-200 | sed 's/^/    /'
  echo "  lnd.log last model date / tail:"
  [ -n "$ll" ] && { zgrep -aE "nstep|model date|Date:" "$ll" | tail -1 | cut -c1-160 | sed 's/^/    /'; zcat -f "$ll" | tail -4 | cut -c1-160 | sed 's/^/    /'; }
  so=$(ls -t "$W"/*"$R"* 2>/dev/null | head -1)
  [ -n "$so" ] && { echo "  slurm output $(basename "$so") tail:"; tail -6 "$so" | cut -c1-200 | sed 's/^/    /'; }
done
