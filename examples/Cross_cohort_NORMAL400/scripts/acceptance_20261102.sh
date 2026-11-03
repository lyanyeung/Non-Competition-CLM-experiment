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
#
# On a compute node (no internet there): download on the login node first, then
#   srun -p batch -N1 -n1 -c4 --mem=16G -t 02:00:00 --pty bash
#   SKIP_DOWNLOAD=1 PUBLISH=0 PHENFIX=0 bash acceptance_20261102.sh      # PHENFIX=0: skip 3B/3C (fix runs not started)
# NEEDLELEAF=0 skips 3A (script 15; its control = original AD400 output, deleted by script 20 purge-old)
# and back on the login node publish that run:
#   PUBLISH_ONLY=$(cat $HOME/CLM_FATES_PLOTS/LAST_ACCEPTANCE_DIR) bash acceptance_20261102.sh
set -u
SHA=ec3f3b9caf934fc9150f0d2aa0be9c110a31d8b4
PUBLISH=${PUBLISH:-1}
SKIP_DOWNLOAD=${SKIP_DOWNLOAD:-0}
PHENFIX=${PHENFIX:-1}
NEEDLELEAF=${NEEDLELEAF:-1}
PUBLISH_ONLY=${PUBLISH_ONLY:-}
TOOL=$HOME/CLM_FATES_PLOTS/diag_rerun_tool
PY=$HOME/.conda/envs/clm_fates_env/bin/python
CASES=/iridisfs/scratch/ly3n24/CLM_FATES/cases
B=https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$SHA/examples/Cross_cohort_NORMAL400/scripts
cd "$TOOL" || exit 1
say() { echo "$*" | tee -a "$S"; }
publish() {
  say ""; say "=== 5. PUBLISH"
  [ -d "$R/15_needleleaf" ] && $PY -B 15_needleleaf_final_trials_vs_ec.py --publish-run "$R/15_needleleaf" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
  [ -d "$R/16_phenfix" ] && $PY -B 16_dbf_collapse_monthly.py --publish-run "$R/16_phenfix" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
  [ -d "$R/08_phenfix" ] && $PY -B diag.py --publish-run "$R/08_phenfix" 2>&1 | grep -E "PUSH|http|Error|error" | tee -a "$S"
}
if [ -n "$PUBLISH_ONLY" ]; then
  R=$PUBLISH_ONLY; S=$R/ACCEPTANCE_SUMMARY.txt
  [ -f "$S" ] || { echo "no ACCEPTANCE_SUMMARY.txt in $R"; exit 1; }
  publish; say "PUBLISHED $(date -u '+%H:%M UTC')"; exit 0
fi
R=$HOME/CLM_FATES_PLOTS/acceptance_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$R"; echo "$R" > $HOME/CLM_FATES_PLOTS/LAST_ACCEPTANCE_DIR
S=$R/ACCEPTANCE_SUMMARY.txt

say "ACCEPTANCE $(date -u '+%Y-%m-%d %H:%M UTC')   output: $R"
say "host $(hostname)"
if [ "$SKIP_DOWNLOAD" != "1" ]; then
  for f in 13_needleleaf_param_trials.py 15_needleleaf_final_trials_vs_ec.py 16_dbf_collapse_monthly.py 17_phenology_patch_rerun.py; do
    curl -fsSL --connect-timeout 15 --max-time 60 -o "$f.new" "$B/$f" && mv "$f.new" "$f" || { rm -f "$f.new"; say "WARNING: could not download $f (using the existing copy)"; }
  done
fi

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
if [ "$NEEDLELEAF" = "1" ]; then
say ""; say "=== 3A. NEEDLELEAF D vs F vs EC (script 15)"
$PY -B 15_needleleaf_final_trials_vs_ec.py --output-root "$R/15_needleleaf" > "$R/15.log" 2>&1
grep -E "INTERIM|RECOMMENDED|with [DF]:|^control|^D |^F |alive [0-9]" "$R/15.log" | tee -a "$S"
grep -E "^  [A-Z][A-Z]-[A-Za-z0-9]+ " "$R/15.log" | tee -a "$S"
else
say ""; say "=== 3A skipped (NEEDLELEAF=0)"
fi

if [ "$PHENFIX" = "1" ]; then
FIXCASES=$(echo "$PF" | tr '\n' ' ')
say ""; say "=== 3B. PHENOLOGY FIX: monthly detail, fixed vs original (script 16)"
$PY -B 16_dbf_collapse_monthly.py --output-root "$R/16_phenfix" --years 50 --cases $FIXCASES \
    CZ-Stn_old:CZ-Stn_B03_FIXNC_AD400_DIAG50 DE-Lnf_old:DE-Lnf_B03_FIXNC_AD400_DIAG50 > "$R/16.log" 2>&1
grep -E "collapse year|<--|REFERENCE|FAILED" "$R/16.log" | tee -a "$S"

say ""; say "=== 3C. PHENOLOGY FIX: mortality and survival (script 08)"
AD_ONLY=$(echo "$PF" | sed 's/_phenfix:/_fix:/' | tr '\n' ' ')
$PY -B diag.py --output-root "$R/08_phenfix" --ad-only $AD_ONLY --first-years 50 --workers 1 > "$R/08.log" 2>&1
grep -E "^== |GPP year 1|COMPLETE" "$R/08.log" | tee -a "$S"
else
say ""; say "=== 3B/3C skipped (PHENFIX=0)"
fi

say ""; say "=== 4. HOW TO READ"
say "A: pass = needleleaf alive at (almost) all sites with the recommended variant; GPP/EC within 0.75-1.25 at most sites;"
say "   'stable' needs >= 30 years. While runs are still going the decision is INTERIM."
say "B: pass = CZ-Stn_fix / DE-Lnf_fix show no collapse year (or later than the 14-16 of *_old), COLD_STATUS back to 1"
say "   after the warm autumn, and US-SRM_fix shows PFT 6 leaf C / GPP > 0."

# ---------------------------------------------------------------- 5. publish
if [ "$PUBLISH" = "1" ]; then
  publish
else
  say ""; say "not published (PUBLISH=0); on the login node: PUBLISH_ONLY=$R bash acceptance_20261102.sh"
fi
say ""; say "DONE $(date -u '+%H:%M UTC'). Summary: $S"
