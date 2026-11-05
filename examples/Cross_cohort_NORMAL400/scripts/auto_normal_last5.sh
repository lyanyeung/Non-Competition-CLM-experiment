#!/bin/bash
# Waits for the five AD chains resumed on 2026-11-05 (TIMEOUT on red6085) and starts each site's Normal400 as soon as
# its AD has 400 years. It only calls the normal-run actions: 20b for CZ-BK1 / US-Me6 / US-MtB (KEEP_NLF) and 22 for
# CA-TP4 / IT-Lav (NLFP). Their own checks decide; a site whose AD is not finished is a HOLD and is tried again later,
# a submitted one is never submitted twice.
# Run on the login node, NOT inside bash -c (script 22's single-action guard would see its name):
#   cd $HOME/CLM_FATES_PLOTS/diag_rerun_tool
#   setsid nohup bash auto_normal_last5.sh > $HOME/CLM_FATES_PLOTS/auto_normal_last5.log 2>&1 < /dev/null &
# Check: pgrep -af auto_normal_last5; tail -30 $HOME/CLM_FATES_PLOTS/auto_normal_last5.log
# Stops when all five Normals are submitted, after MAX_HOURS (default 30), or when a site is stuck in
# PREPARE_ATTEMPTED (a prepare failed: inspect it, do not loop).
cd "$(dirname "$0")" || exit 1
PY=${PY:-$HOME/.conda/envs/clm_fates_env/bin/python}
KEEP=${KEEP:-"CZ-BK1 US-Me6 US-MtB"}
PATCH=${PATCH:-"CA-TP4 IT-Lav"}
EVERY=${EVERY:-1200}          # seconds between checks
MAX_HOURS=${MAX_HOURS:-30}
end=$(( $(date +%s) + MAX_HOURS * 3600 ))

state() {   # $1 = 20 or 22, $2 = site -> SUBMIT... / PREPARE_ATTEMPTED / other
  if [ "$1" = 20 ]; then line=$($PY -B 20_needleleaf_rerun_AD400_NORMAL400.py status --sites "$2" 2>/dev/null | grep "^$2 ")
  else line=$($PY -B 22_phenology_patch_rollout.py status --sites "$2" 2>/dev/null | grep "^$2 "); fi
  echo "$line" | grep -oE "NORMAL [A-Z_a-z]+" | head -1 | awk '{print $2}'
}

while :; do
  echo "#### $(date -u '+%F %H:%M UTC')"
  left20=""; left22=""; stuck=""
  for s in $KEEP; do
    st=$(state 20 "$s"); echo "  $s Normal: ${st:-?}"
    case "$st" in SUBMIT*) ;; PREPARE_ATTEMPTED) stuck="$stuck $s" ;; *) left20="$left20 $s" ;; esac
  done
  for s in $PATCH; do
    st=$(state 22 "$s"); echo "  $s Normal: ${st:-?}"
    case "$st" in SUBMIT*) ;; PREPARE_ATTEMPTED) stuck="$stuck $s" ;; *) left22="$left22 $s" ;; esac
  done
  [ -n "$stuck" ] && echo "  WARNING: prepare failed earlier (PREPARE_ATTEMPTED), not retried:$stuck"
  if [ -z "$left20$left22" ]; then echo "done: no site left to start${stuck:+ (stuck:$stuck)}"; break; fi
  [ -n "$left20" ] && $PY -B 20b_normal_spinup_state_tolerance.py normal-run --sites $left20 2>&1 | grep -aE "SUBMITTED|HOLD|accepted"
  [ -n "$left22" ] && $PY -B 22_phenology_patch_rollout.py normal-run --sites $left22 2>&1 | grep -aE "SUBMITTED|HOLD|error"
  if [ "$(date +%s)" -ge "$end" ]; then echo "stopped after $MAX_HOURS h; still waiting:$left20$left22"; break; fi
  sleep "$EVERY"
done
