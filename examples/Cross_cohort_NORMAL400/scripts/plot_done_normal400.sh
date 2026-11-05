#!/bin/bash
# Convergence + EC figures for the NEW Normal400 cases that have finished (same two tools as before):
#   1) Stage15 (examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py, as plot.py):
#      <site>_01_carbon_pools_AD400_NORMAL400.png, <site>_02_carbon_pools_NORMAL400_panels.png,
#      <site>_GPP_NEE_monthly_overview.png (+ convergence / flux metric CSVs)
#   2) 07_plot_full_sequence_GPP_NEE_with_EC.py: 800-year GPP / NEE / NPP / LAI with the EC reference, plus
#      ALL_SITES_*_full_sequence_overview.png
#   3) 24_last_cycle_vs_ec.py: last complete forcing cycle vs EC (monthly series, seasonal cycle, 1:1 scatter;
#      "before fix" Normal drawn where still archived), ALL_SITES_last_cycle_* overviews, last_cycle_metrics.csv
# Inputs are read only; output goes to a new folder on Home. AD case = RUN_REFCASE of the Normal case.
# Finished = NLF_STATE.json phase SUBMITTED (scripts 20/20b/21/22/23), 80 restart sets (400 y), nothing queued.
#
# Login node (as before), not inside bash -c:
#   cd $HOME/CLM_FATES_PLOTS/diag_rerun_tool
#   bash plot_done_normal400.sh --list                     # READ ONLY: which cases are finished
#   setsid nohup bash plot_done_normal400.sh > $HOME/CLM_FATES_PLOTS/plot_done_$(date -u +%Y%m%dT%H%MZ).log 2>&1 < /dev/null &
#   bash plot_done_normal400.sh --sites DE-Obe FI-Sod      # only these sites (must be finished)
#   SKIP_DONE_IN=<earlier output folder> bash plot_done_normal400.sh   # skip sites already plotted there
# Tools are fetched by commit (REF) into a new folder; WORKERS (default 4) sites in parallel for the full sequence.
set -uo pipefail
REF=${REF:-2df56ef68828e70981d119bb79273bd818fe657f}   # any commit that has Stage15 and script 07
CASES=${CASES:-/iridisfs/scratch/ly3n24/CLM_FATES/cases}
OUT_SCR=${OUT_SCR:-/scratch/ly3n24/CTSM_FATES_OUTPUTS}
PY=${PY:-$HOME/.conda/envs/clm_fates_env/bin/python}
WORKERS=${WORKERS:-4}
U=${USER:-$(whoami)}
LIST=0; SITES=""
while [ $# -gt 0 ]; do
  case "$1" in
    --list) LIST=1 ;;
    --sites) shift; while [ $# -gt 0 ] && [[ "$1" != --* ]]; do SITES="$SITES $1"; shift; done; continue ;;
    *) echo "unknown argument $1"; exit 2 ;;
  esac
  shift
done

Q=$(squeue -u "$U" -h -o "%j")
pairs15=(); pairs07=()
echo "== finished new Normal400 cases ($(date -u '+%F %H:%M UTC'))"
for d in "$CASES"/*_NORMAL400*; do
  [ -f "$d/NLF_STATE.json" ] || continue
  grep -qE '"phase": *"SUBMITTED"' "$d/NLF_STATE.json" || continue
  c=$(basename "$d"); site=${c%%_*}
  [ -n "$SITES" ] && [[ " $SITES " != *" $site "* ]] && continue
  n=$(ls -1 "$OUT_SCR/archive/$c/rest" 2>/dev/null | wc -l)
  echo "$Q" | grep -qxE "(run|st_archive)\.$c" && continue
  [ "$n" -ge 80 ] || continue
  if [ -n "${SKIP_DONE_IN:-}" ] && ls "$SKIP_DONE_IN"/convergence_EC/"$site"/*_GPP_NEE_monthly_overview.png >/dev/null 2>&1; then
    echo "  $site: already plotted in $SKIP_DONE_IN, skipped"; continue; fi
  ad=$(cd "$d" && ./xmlquery --value RUN_REFCASE 2>/dev/null)
  if [ -z "$ad" ] || [ ! -d "$CASES/$ad" ]; then echo "  $site: $c has no usable RUN_REFCASE ('$ad'), skipped"; continue; fi
  echo "  $site  AD $ad  ->  Normal $c"
  pairs15+=("$site:$ad:$c"); pairs07+=("$site:$c")
done
echo "== ${#pairs15[@]} case pair(s)"
[ "$LIST" = 1 ] && exit 0
[ ${#pairs15[@]} -gt 0 ] || { echo "nothing to plot"; exit 0; }

RAW=https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REF
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/plot_tool.XXXXXXXX")
curl -fsSL "$RAW/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py" || exit 1
curl -fsSL "$RAW/examples/Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py" -o "$TOOL/fullseq.py" || exit 1
curl -fsSL "$RAW/examples/Cross_cohort_NORMAL400/scripts/24_last_cycle_vs_ec.py" -o "$TOOL/lastcycle.py" || exit 1
"$PY" -m py_compile "$TOOL/plot.py" "$TOOL/fullseq.py" "$TOOL/lastcycle.py" || exit 1
OUT="$HOME/CLM_FATES_PLOTS/NewNormal400_figures_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
printf '%s\n' "${pairs15[@]}" > "$OUT/pairs.txt"
echo "tool $TOOL (commit $REF)"; echo "output $OUT"

echo "######## 1) Stage15 convergence + monthly EC   $(date -u '+%H:%M UTC')"
"$PY" -u -B "$TOOL/plot.py" --pair "${pairs15[@]}" --output-root "$OUT/convergence_EC"
s15=$?
echo "######## 2) full sequence GPP / NEE with EC     $(date -u '+%H:%M UTC')"
"$PY" -u -B "$TOOL/fullseq.py" --pairs "${pairs07[@]}" --output-root "$OUT/full_sequence" \
      --workers "$WORKERS" --plot-module "$TOOL/plot.py"
s07=$?
echo "######## 3) last forcing cycle vs EC            $(date -u '+%H:%M UTC')"
"$PY" -u -B "$TOOL/lastcycle.py" --pairs-file "$OUT/pairs.txt" --output-root "$OUT/last_cycle_EC" --plot-module "$TOOL/plot.py"
s24=$?
echo "######## finished $(date -u '+%H:%M UTC')  stage15 exit $s15, full-sequence exit $s07, last-cycle exit $s24"
echo "PNGs:"; find "$OUT" -name '*.png' | sort | sed 's/^/  /'
echo "summaries: $OUT/convergence_EC/AD400_NORMAL400_summary.csv  $OUT/full_sequence/full_sequence_summary.csv  $OUT/last_cycle_EC/last_cycle_metrics.csv"
