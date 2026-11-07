#!/bin/bash
# READ ONLY. What a fresh NL-Loo AD400 (+ Normal400) can be built from: the remaining NL-Loo cases, and the
# DE-Tha AD400 of the same OBSPFT_NC lineage as the reference for how a cold-start FATES AD case is set up here.
#   bash nlloo_inspect.sh 2>&1 | tee ~/CLM_FATES_PLOTS/nlloo_inspect_$(date -u +%Y%m%dT%H%MZ).txt
C=/iridisfs/scratch/ly3n24/CLM_FATES/cases
E=/iridisfs/scratch/ly3n24/CLM_FATES/experiments
VARS="CASE COMPSET RES MACH CLM_ACCELERATED_SPINUP RUN_TYPE RUN_STARTDATE STOP_OPTION STOP_N REST_N RESUBMIT
CONTINUE_RUN CLM_FORCE_COLDSTART CLM_BLDNML_OPTS CLM_USRDAT_NAME DATM_YR_START DATM_YR_END DATM_YR_ALIGN
PTS_LAT PTS_LON ATM_DOMAIN_MESH LND_DOMAIN_MESH MASK_MESH EXEROOT RUNDIR DOUT_S_ROOT COMP_ROOT_DIR_LND
JOB_WALLCLOCK_TIME NTASKS"
show() {
  local d=$C/$1
  echo "################ $1"
  [ -d "$d" ] || { echo "  (no case)"; return; }
  cd "$d" || return
  for v in $VARS; do printf "  %-24s %s\n" "$v" "$(./xmlquery --value "$v" 2>/dev/null | cut -c1-160)"; done
  echo "  -- user_nl_clm (non-comment)"; grep -vE '^\s*(!|$)' user_nl_clm 2>/dev/null | cut -c1-200 | sed 's/^/    /'
  for f in user_nl_datm user_nl_datm_streams; do
    [ -f "$f" ] && { echo "  -- $f (non-comment)"; grep -vE '^\s*(!|$)' "$f" | cut -c1-200 | sed 's/^/    /'; }
  done
  echo "  -- CaseDocs/lnd_in keys"
  grep -E "^\s*(fsurdat|fates_paramfile|finidat|spinup_state|use_fates[a-z_]*|fates_spitfire_mode|hist_fincl1|hist_nhtfrq|hist_mfilt|use_bedrock|paramfile|co2_ppmv|calc_human_stress_indices|use_init_interp)\s*=" CaseDocs/lnd_in 2>/dev/null | sed 's/^ */    /' | cut -c1-220
  echo "  -- CLM_USRDAT stream (CaseDocs/datm.streams.xml)"
  grep -A12 'CLM_USRDAT' CaseDocs/datm.streams.xml 2>/dev/null | grep -E "year_|<file>|meshfile|offset" | head -8 | sed 's/^ */    /' | cut -c1-200
  rd=$(./xmlquery --value RUNDIR 2>/dev/null); ar=$(./xmlquery --value DOUT_S_ROOT 2>/dev/null)
  echo "  -- RUNDIR datm.streams.xml: $([ -f "$rd/datm.streams.xml" ] && echo present || echo none)"
  echo "  -- SourceMods: $(find SourceMods -type f 2>/dev/null | tr '\n' ' ')"
  echo "  -- last restart: $(ls "$ar/rest" 2>/dev/null | sort | tail -1)  hist files: $(ls "$ar/lnd/hist" 2>/dev/null | wc -l)"
  echo "  -- CaseStatus tail:"; tail -3 CaseStatus 2>/dev/null | sed 's/^/    /' | cut -c1-160
  cd - >/dev/null
}
for c in NL-Loo_OBSPFT_NC_V2_PRE50 NL-Loo_OBSPFT_NC_PRE50 DE-Tha_OBSPFT_NC_V1_AD400 DE-Tha_OBSPFT_NC_V1_AD400_NLFP; do show $c; done
echo "################ private FATES-AD namelist overlays"
find $E -maxdepth 4 -type d -name "_private_ctsm_FATES_AD400_namelist_overlay" 2>/dev/null | head -20
find $HOME -maxdepth 3 -type d -iname "*overlay*" 2>/dev/null | grep -i -E "loo|fates|ad" | head -10
echo "################ NL-Loo inputs"
ls -la $E/NonCompetitionObserved22/NL-Loo/surface/ 2>/dev/null | tail -n +2 | head -10
ls -d /iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/NL-Loo/forcing/* 2>/dev/null | head -10
echo "################ NL-Loo controller folders in HOME"
ls -d $HOME/NL_Loo* 2>/dev/null
