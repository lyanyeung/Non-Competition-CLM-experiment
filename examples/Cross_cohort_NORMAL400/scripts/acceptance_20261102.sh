#!/bin/bash
# Acceptance check for the experiments submitted on 2026-11-02 (read-only except publishing to GitHub):
#   A. final needleleaf trials   13 run --final --variants D F --years 100   (*_FIXD100, *_FIXF100, ten sites)
#   B. FATES phenology fix       17 run (CZ-Stn, DE-Lnf, US-SRM; *_PHENFIX50, own build)
# Works while runs are still going: everything is evaluated on the years archived so far and marked INTERIM.
#
# Usage on the IRIDIS login node (about 20-40 min, mostly reading history):
#   setsid nohup bash acceptance_20261102.sh > $HOME/CLM_FATES_PLOTS/acceptance.out 2>&1 < /dev/null &
#   tail -f $HOME/CLM_FATES_PLOTS/acceptance.out            # Ctrl+C only stops watching
#   cat $(cat $HOME/CLM_FATES_PLOTS/LAST_ACCEPTANCE_DIR)/ACCEPTANCE_SUMMARY.txt
# Set PUBLISH=0 to skip the GitHub upload.
set -u
SHA=eddb30157906968d52580f1e43514fe6052e808c
PUBLISH=${PUBLISH:-1}
TOOL=$HOME/CLM_FATES_PLOTS/diag_rerun_tool
PY=$HOME/.conda/envs/clm_fates_env/bin/python
CASES=/iridisfs/scratch/ly3n24/CLM_FATES/cases
B=https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$SHA/examples/Cross_cohort_NORMAL400/scripts
R=$HOME/CLM_FATES_PLOTS/acceptance_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$R"; echo "$R" > $HOME/CLM_FATES_PLOTS/LAST_ACCEPTANCE_DIR
S=$R/ACCEPTANCE_SUMMARY.txt
cd "$TOOL" || exit 1
say() { echo "$*" | tee -a "$S"; }

say "ACCEPTANCE $(date -u '+%Y-%m-%d %H:%M UTC')   output: $R"
for f in 13_needleleaf_param_trials.py 15_needleleaf_final_trials_vs_ec.py 16_dbf_collapse_monthly.py 17_phenology_patch_rerun.py; do
  curl -fsSL -o "$f.new" "$B/$f" && mv "$f.new" "$f" || say "WARNING: could not download $f (using the existing copy)"
done

# ---------------------------------------------------------------- 1. status
say ""; say "=== 1. RUN STATUS"
say "--- A. needleleaf final trials (want: SUBMITTED, archived years -> 100)"
$PY -B 13_needleleaf_param_trials.py status --final --variants D F --years 100 2>&1 | tee -a "$S"
say "--- B. phenology fix (want: SUBMITTED, archived years -> 50)"
$PY -B 17_phenology_patch_rerun.py status 2>&1 | tee -a "$S"
say "--- submission logs: HOLD lines (empty = none)"
grep -h "HOLD" $HOME/CLM_FATES_PLOTS/run_final.log $HOME/CLM_FATES_PLOTS/phenfix_run.log 2>/dev/null | tee -a "$S"
squeue -u ly3n24 -o "%i %j %T %M %r" > "$R/squeue.txt"
say "--- queue: $(($(wc -l < "$R/squeue.txt") - 1)) jobs (full list in squeue.txt)"
grep -i "DependencyNeverSatisfied" "$R/squeue.txt" | tee -a "$S"

# ---------------------------------------------------------------- 2. failures
NL=$($PY -B 13_needleleaf_param_trials.py cases --final --variants D F --years 100 2>/dev/null | grep ':all$')
PF=$($PY -B 17_phenology_patch_rerun.py cases 2>/dev/null | grep '_phenfix:')
say ""; say "=== 2. FAILED MODEL RUNS (empty = none)"
for x in $NL $PF; do
  c=$(echo "$x" | cut -d: -f2); f=$CASES/$c/CaseStatus
  [ -f "$f" ] || continue
  if grep -q "case.run error\|model execution error" "$f"; then
    log=$(grep -o "See log file for details: .*" "$f" | tail -1 | sed 's/See log file for details: //')
    say "FAILED $c   log: $log"
    [ -n "$log" ] && [ -f "$log" ] && zgrep -m5 -i "ERROR\|ENDRUN\|abort" "$log" | sed 's/^/      /' | tee -a "$S"
  fi
done

# ---------------------------------------------------------------- 3. analyses
say ""; say "=== 3A. NEEDLELEAF D vs F vs EC (script 15)"
$PY -B 15_needleleaf_final_trials_vs_ec.py --output-root "$R/15_needleleaf" > "$R/15.log" 2>&1
grep -E "INTERIM|RECOMMENDED|with [DF]:|^control|^D |^F |alive [0-9]" "$R/15.log" | tee -a "$S"
grep -E "^  [A-Z][A-Z]-[A-Za-z0-9]+ " "$R/15.log" | tee -a "$S"

FIXCASES=$(echo "$PF" | tr '\n' ' ')
say ""; say "=== 3B. PHENOLOGY FIX: monthly detail, fixed vs original (script 16)"
$PY -B 16_dbf_collapse_monthly.py --output-root "$R/16_phenfix" --years 50 --cases $FIXCASES \
    CZ-Stn_old:CZ-Stn_B03_FIXNC_AD400_DIAG50 DE-Lnf_old:DE-Lnf_B03_FIXNC_AD400_DIAG50 > "$R/16.log" 2>&1
grep -E "collapse year|<--|REFERENCE|FAILED" "$R/16.log" | tee -a "$S"

say ""; say "=== 3C. PHENOLOGY FIX: mortality and survival (script 08)"
AD_ONLY=$(echo "$PF" | sed 's/_phenfix:/_fix:/' | tr '\n' ' ')
$PY -B diag.py --output-root "$R/08_phenfix" --ad-only $AD_ONLY --first-years 50 --workers 1 > "$R/08.log" 2>&1
grep -E "^== |GPP year 1|COMPLETE" "$R/08.log" | tee -a "$S"

say ""; say "=== 4. HOW TO READ"
say "A: pass = needleleaf alive at (almost) all sites with the recommended variant; GPP/EC within 0.75-1.25 at most sites;"
say "   'stable' needs >= 30 years. While runs are still going the decision is INTERIM."
say "B: pass = CZ-Stn_fix / DE-Lnf_fix show no collapse year (or later than the 14-16 of *_old), COLD_STATUS back to 1"
say "   after the warm autumn, and US-SRM_fix shows PFT 6 leaf C / GPP > 0."

# ---------------------------------------------------------------- 5. publish
if [ "$PUBLISH" = "1" ]; then
  say ""; say "=== 5. PUBLISH"
  $PY -B 15_needleleaf_final_trials_vs_ec.py --publish-run "$R/15_needleleaf" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
  $PY -B 16_dbf_collapse_monthly.py --publish-run "$R/16_phenfix" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
  $PY -B diag.py --publish-run "$R/08_phenfix" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
fi
say ""; say "DONE $(date -u '+%H:%M UTC'). Summary: $S"
