# Rules for any new case (for people or other assistants working on this experiment)

Status 2026-11-02. Two model changes were adopted, and **neither is in the shared CTSM/FATES source tree**
(`/iridisfs/scratch/ly3n24/CLM_FATES/CTSM`). A case created the standard way (`create_newcase`, or `create_clone --keepexe`
of an existing case, or any case using the shared executable `GF-Guy_FATES_SURF2000_CO2405_1PT/bld/cesm.exe`) therefore
runs the **old** behaviour. The changes must be applied per case:

| Change | Applies when | How it is applied | Check |
|---|---|---|---|
| FATES phenology patch (backport of NGEET/fates 6d9f5b34; docs section 16) | the site has a cold-deciduous PFT: `fates_phen_leaf_habit == 2` in its parameter file (needleleaf deciduous, broadleaf deciduous tree/shrub, arctic deciduous shrub, arctic C3 grass), mapped from the surface data's PCT_NAT_PFT | patched `EDPhysiologyMod.F90` in `<case>/SourceMods/src.clm/` and the case's **own build** (EXEROOT not shared with an unpatched case); never `--keepexe` from an unpatched case | `grep nchill_threshold <case>/SourceMods/src.clm/EDPhysiologyMod.F90`; the lnd build log compiles that file, not `src/fates/biogeochem/EDPhysiologyMod.F90` |
| Needleleaf parameters F (docs section 9) | the site has PFT 2 (`needleleaf_evergreen_extratrop_tree`) | `fates_paramfile` = the adopted copy of the site's own source file: `experiments/NonCompetitionObserved22/params_adopted/fates_params_needleleaf_F_<sha10 of source>.json` (script 18 `ensure_adopted` makes it) | PFT 2 `fates_alloc_storage_cushion` 2.4, `fates_leaf_slatop` 0.008 |
| `calc_human_stress_indices = 'NONE'` (section 17) | only if a run stops with "RH is negative" in HumanIndexMod (very dry air: US-Aud) | user_nl_clm | diagnostics only, no effect on fluxes |

Sites with neither a cold-deciduous PFT nor PFT 2 (e.g. pure C3/C4 grass, evergreen shrub, tropical evergreen) give
identical results with the old and the patched code; the shared executable is fine for them.

**Use the scripts instead of doing it by hand** (branch `full-sequence-gpp-nee-ec`,
`examples/Cross_cohort_NORMAL400/scripts/`): `22_phenology_patch_rollout.py` (classification, patched build, both
changes), `20_...` (needleleaf only), `21_...` (HumanIndex), `18_...` (adopted parameter files). Only one script-22 action
runs at a time. Never edit the shared CTSM/FATES source: every existing case built from it would change on rebuild.

Other standing rules: originals are not modified (new cases are clones with a suffix); prepare → verify → submit, never
submit twice; download scripts by commit SHA; deletions only through the purge actions, recorded in this folder.
