#!/bin/bash
# READ ONLY. Progress of every new Normal400: the Normal cases that carry NLF_STATE.json (made by scripts 20, 20b,
# 21, 22, 23). The original Normals of the UNCHANGED sites have no state file and are not listed.
#   bash normal400_progress.sh        one line per case, then a summary
#   bash normal400_progress.sh -s     summary only
# Status: DONE (400 y archived, nothing queued) | RUNNING | PENDING (run queued) | ARCHIVING (only st_archive left)
#         DEAD (st_archive DependencyNeverSatisfied: run job failed -> triage_failed_chains.sh)
#         STALLED (< 400 y and nothing queued -> sacct / CaseStatus) | phase (not submitted yet)
CASES=${CASES:-/iridisfs/scratch/ly3n24/CLM_FATES/cases}
OUT=${OUT:-/scratch/ly3n24/CTSM_FATES_OUTPUTS}
U=${USER:-$(whoami)}
Q=$(squeue -u "$U" -h -o "%j %T %r")
rows=$(mktemp); trap 'rm -f "$rows"' EXIT
for d in "$CASES"/*_NORMAL400*; do
  [ -f "$d/NLF_STATE.json" ] || continue
  c=$(basename "$d")
  ph=$(grep -oE '"phase": *"[A-Z_]+"' "$d/NLF_STATE.json" | head -1 | grep -oE '[A-Z_]+"$' | tr -d '"')
  if [ "$ph" != SUBMITTED ]; then echo "$c|0|-|${ph:-NO_PHASE}" >> "$rows"; continue; fi
  rest=$OUT/archive/$c/rest
  [ -d "$rest" ] || rest=$(cd "$d" && ./xmlquery --value DOUT_S_ROOT 2>/dev/null)/rest
  n=$(ls -1 "$rest" 2>/dev/null | wc -l); y=$((n * 5))
  last=$(ls -1 "$rest" 2>/dev/null | sort | tail -1 | cut -c1-4)
  run=$(echo "$Q" | awk -v j="run.$c" '$1==j{print $2; exit}')
  arc=$(echo "$Q" | awk -v j="st_archive.$c" '$1==j{print $2 "_" $3; exit}')
  if [ "$y" -ge 400 ] && [ -z "$run$arc" ]; then st=DONE
  elif [ -n "$run" ]; then st=$run
  elif [[ "$arc" == *DependencyNeverSatisfied* ]]; then st=DEAD
  elif [ -n "$arc" ]; then st=ARCHIVING
  else st=STALLED; fi
  echo "$c|$y|${last:--}|$st" >> "$rows"
done
if [ "$1" != -s ]; then
  printf "%-58s %9s %-6s %s\n" CASE YEARS LAST STATUS
  sort -t'|' -k4,4 -k2,2nr "$rows" | awk -F'|' '{
    bar=""; for (i=0; i<int($2/20); i++) bar=bar "#"
    printf "%-58s %3d/400 %-6s %-10s %s\n", $1, $2, $3, $4, bar }'
  echo
fi
tot=$(wc -l < "$rows")
echo "== $(date -u '+%F %H:%M UTC')  new Normal400 cases: $tot"
cut -d'|' -f4 "$rows" | sort | uniq -c | awk '{printf "   %-12s %3d\n", $2, $1}'
awk -F'|' '{s+=$2} END{if (NR) printf "   mean progress %.0f / 400 y, total %d of %d years\n", s/NR, s, NR*400}' "$rows"
bad=$(awk -F'|' '$4=="DEAD"||$4=="STALLED"||$4 ~ /ATTEMPT|VERIFIED|NO_PHASE/{print "   " $1 " (" $4 ")"}' "$rows")
[ -n "$bad" ] && { echo "== need attention:"; echo "$bad"; }
true
