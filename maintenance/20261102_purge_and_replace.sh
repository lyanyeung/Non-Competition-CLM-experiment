#!/bin/bash
# Record of the deletion / stop / replacement commands run on IRIDIS on 2026-11-02 (see README.md in this folder).
# Every script is downloaded at the exact commit that was used. Read-only steps first; destructive ones need --confirm.
# Run on the login node, in $HOME/CLM_FATES_PLOTS/diag_rerun_tool, with setsid nohup for the long steps.
#
# The deletion code itself:
#   20_needleleaf_rerun_AD400_NORMAL400.py  purge_old(), old_nc_files()   (needleleaf rerun, 41 PFT-2 sites)
#   22_phenology_patch_rollout.py           purge_old(), cancel_nlf()     (phenology rollout, 59 sites)
# Both delete ONLY *.nc in the RUNDIR / DOUT_S_ROOT of the named original case (paths must belong to that case),
# refuse cases with queued jobs and any path inside a build directory, and write the file list to
# $EXP22/Needleleaf_F_rerun/<site>_[phen_]purged_files_<UTC>.txt before deleting.
set -eu
PY=$HOME/.conda/envs/clm_fates_env/bin/python
RAW=https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment
S=examples/Cross_cohort_NORMAL400/scripts
get() { curl -fsSL -o "$2" "$RAW/$1/$S/$2"; }

# ---- 1. needleleaf rerun (script 20 at 9482ba4): 41 sites -> <AD>_NLF, then purge of the originals
get 9482ba42e68bd4186f9102e2939828007da0bcc7 18_adopt_needleleaf_params.py
get 9482ba42e68bd4186f9102e2939828007da0bcc7 20_needleleaf_rerun_AD400_NORMAL400.py
# $PY -B 20_needleleaf_rerun_AD400_NORMAL400.py plan                                   # read-only, 41/41 OK
# $PY -B 20_needleleaf_rerun_AD400_NORMAL400.py ad-run                                 # 41/41 submitted
# $PY -B 20_needleleaf_rerun_AD400_NORMAL400.py purge-old                              # dry run
# $PY -B 20_needleleaf_rerun_AD400_NORMAL400.py purge-old --confirm DELETE_OLD_NEEDLELEAF_OUTPUTS

# ---- 2. phenology rollout (script 22 at 3abfee9): stop 23 <AD>_NLF, purge every replaced case, rebuild with the patch
get 3abfee961f988235a77009fcd868e7a3b4d5c76e 17_phenology_patch_rerun.py
get 3abfee961f988235a77009fcd868e7a3b4d5c76e 20_needleleaf_rerun_AD400_NORMAL400.py
get 3abfee961f988235a77009fcd868e7a3b4d5c76e 21_fix_humanindex_rerun.py
get 3abfee961f988235a77009fcd868e7a3b4d5c76e 22_phenology_patch_rollout.py
# $PY -B 22_phenology_patch_rollout.py plan                                            # read-only, 75/75 OK
# $PY -B 22_phenology_patch_rollout.py cancel-nlf --confirm STOP_NLF_FOR_PHENOLOGY_PATCH
# $PY -B 22_phenology_patch_rollout.py purge-old                                       # dry run
# $PY -B 22_phenology_patch_rollout.py purge-old --confirm DELETE_OLD_PHENOLOGY_OUTPUTS
# $PY -B 22_phenology_patch_rollout.py ad-run                                          # after the purge

# ---- 3. US-Aud (script 21 at 7d99f9e)
# scancel 4800874
# $PY -B 21_fix_humanindex_rerun.py ad-run

# ---- 4. what was deleted (read-only summary of the file lists)
# $PY -B summarize_purge_ledger.py
echo "scripts downloaded; the commands above are commented out on purpose (record, not a re-run)"
