#!/bin/bash
# READ ONLY overview: AD400 / Normal400 of every site (scripts 20, 21, 22, 23), queue, recent failures, normal-run HOLDs.
#   bash ~/CLM_FATES_PLOTS/spinup_overview.sh 2>&1 | tee ~/CLM_FATES_PLOTS/overview_$(date -u +%Y%m%dT%H%MZ).txt
T=$HOME/CLM_FATES_PLOTS/diag_rerun_tool
PY=$HOME/.conda/envs/clm_fates_env/bin/python
cd "$T" || exit 1
echo "################ $(date -u '+%F %H:%M UTC')"
echo "======== script 20 (KEEP_NLF; RESTART_NLF rows show the cancelled _NLF)"
$PY -B 20_needleleaf_rerun_AD400_NORMAL400.py status 2>&1 | grep -v "CANCELLED_REPLACED" | grep -v "^$"
echo "======== script 22 (NLFP / PHEN / GL-ZaH)"
$PY -B 22_phenology_patch_rollout.py status 2>&1 | grep -vE "UNCHANGED|EXCLUDED|KEEP_NLF" | grep -v "^$"
echo "======== script 21 (US-Aud HINONE)"
$PY -B 21_fix_humanindex_rerun.py status --cases US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT 2>&1
echo "======== script 23 (ICOS Batch04 + CH-Aws)"
if [ -f 23_normal400_extra_ad_cases.py ]; then
  $PY -B 23_normal400_extra_ad_cases.py status 2>&1
  echo "-- ready for Normal400?"; $PY -B 23_normal400_extra_ad_cases.py check 2>&1
else echo "23_normal400_extra_ad_cases.py not in $T yet"; fi

echo "======== summary"
all=$( { $PY -B 20_needleleaf_rerun_AD400_NORMAL400.py status; $PY -B 22_phenology_patch_rollout.py status; } 2>/dev/null )
echo "AD 400/400 done, Normal not prepared : $(echo "$all" | grep -E "(AD|NLF) SUBMITTED 400(/400)? ?y" | grep -c "NORMAL not prepared")"
echo "AD still running (<400 y)            : $(echo "$all" | grep -E "(AD|NLF) SUBMITTED" | grep NORMAL | grep -vE "SUBMITTED 400(/400)? ?y" | sed -E 's/ +/ /g' | cut -c1-80 | tr '\n' ';')"
echo "Normal submitted                      : $(echo "$all" | grep -c "NORMAL SUBMITTED")"
echo "Normal other states                   : $(echo "$all" | grep -oE "NORMAL (VERIFIED_NOT_SUBMITTED|SUBMIT_ATTEMPTED_UNCERTAIN|PREPARE_ATTEMPTED)" | sort | uniq -c | tr '\n' ' ')"

echo "======== queue"
squeue -u "$USER" -h -o "%T %r" | sort | uniq -c
echo "-- DependencyNeverSatisfied (dead chains):"
squeue -u "$USER" -h -t PD -o "%i %j %r" | awk '$3=="DependencyNeverSatisfied"'
echo "======== run jobs not COMPLETED in the last 14 h"
sacct -u "$USER" -S now-14hours -X -n -P -o JobID,JobName%90,State,Start,Elapsed,NodeList \
  | awk -F'|' '$2~/^run\./ && $3!~/COMPLETED|RUNNING|PENDING/'
echo "======== slowest COMPLETED segments in the last 14 h (normal is 7-9 min)"
sacct -u "$USER" -S now-14hours -X -n -P -o JobName%90,State,Elapsed,NodeList | awk -F'|' '$1~/^run\./&&$2=="COMPLETED"' | sort -t'|' -k3,3r | head -5
L=$(ls -t $HOME/CLM_FATES_PLOTS/normal_run_*.log 2>/dev/null | head -1)
if [ -n "$L" ]; then
  echo "======== last normal-run log: $L"
  echo "submitted: $(grep -ac '^  SUBMITTED' "$L")"
  grep -a ": HOLD" "$L" | cut -c1-220
  pgrep -af "normal-run" | grep -v pgrep || echo "(no normal-run process running)"
fi
