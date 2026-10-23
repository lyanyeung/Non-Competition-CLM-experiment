# NL-Loo gate 02: observed PFT surface candidate

Pilot source audit confirms existing `NL-Loo_FATES_SPINUP500` compset `2000_DATM%1PT_CLM60%FATES_SICE_SOCN_SROF_SGLC_SWAV_SESP`, normal decomposition, `use_fates=.true.`, `use_fates_fixed_biogeog=.false.`, `use_fates_nocomp=.false.`. Input SHA256s pinned in `scripts/02_build_NL_Loo_obs_surface.py`.

Observed 500-m-radius fractions: 93.6% needleleaf evergreen, 2.9% deciduous broadleaf, 3.5% heath/grass open. The historic coarse surface is 66.83888% NATVEG / 33.16112% CROP, which is unsuitable as a direct surrogate for the tower inventory. The new file, if explicitly accepted, uses 100% NATVEG and maps the surveyed fractions to the **natural-vegetation landunit**, leaving all other nonvegetation landunits at original zero.

No unique classification is available for the 3.5% heather/grass open cover. Two fully disclosed *sensitivity assumptions* are offered:
* `grass_proxy`: all 3.5% mapped to `cool_c3_grass`.
* `heath_proxy`: all 3.5% mapped to `broadleaf_evergreen_extratrop_shrub`.

These are **not two measured distributions**. Select one pilot scenario and document the uncertainty; do not represent either as actual surveyed PFT percentage. The script checks the actual audited 14-PFT JSON `fates_hlm_pft_map` against the intended CLM 15-PFT indices. The model's FATES fixed-biogeography area needs confirming from actual output, not merely host CLM vector.

## IRIDIS commands, no Slurm yet

```bash
cd ~/Non-Competition-CLM-experiment
git fetch origin main
git status --short
# If clean, update:
git pull --ff-only origin main

python -m py_compile scripts/02_build_NL_Loo_obs_surface.py
python scripts/02_build_NL_Loo_obs_surface.py --scenario grass_proxy

# ONLY if the proxy assumptions are scientifically accepted:
python scripts/02_build_NL_Loo_obs_surface.py --scenario grass_proxy \
  --write --accept-open-cover-proxy --accept-500m-radius-as-proxy

# Record actual new filename, hashes, and read-only audit:
cat /iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/NL-Loo/surface/surfdata_NL-Loo_obsPFT_grass_proxy_v1.json
```

## Submission hold

No case may be submitted before a validated CIME clone exists with the NEW surface, FIXNC flags, matching FATES parameter map, original forcing and CO2. A new case must have a unique `RUNDIR`, `DOUT_S_ROOT`, case name and built executable compatible with mode. The PRE50 plan is 50 years normal, initially `STOP_N=5`, `RESUBMIT=0` for a first-segment gate; then continue 45 years only after confirming the archived coordinated restart. AD200/post-AD300 require scientifically correct separate restart handoffs and AD carbon-pool adjustment, not just setting `RUN_TYPE=startup` in new cases.

Do not claim 550-year automatic continuation exists yet: only surface creation is implemented. Existing 6/8/11/13-site Slurm jobs and source cases must remain untouched.
