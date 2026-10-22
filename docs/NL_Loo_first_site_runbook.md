# NL-Loo first-site runbook — gates before the 50-year spin-up

## Status

Repository scripts and plan are published, but **not executed on IRIDIS6**. No approved observed FATES map and no new case exist yet. Do **not** launch the legacy multi-site `09_submit_six_site_spinup500.sh`: it would target existing cases and use previous surface configuration.

## Step 1: read-only inspection (the only safe command now)

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
python scripts/01_inspect_NL_Loo.py --out "$HOME/NL_Loo_NC_audit"
cat "$HOME/NL_Loo_NC_audit/00_overview.json"
```

Audit `COMPSET`, `CLM_ACCELERATED_SPINUP`, `fates_paramfile`, `fates_hlm_pft_map`, full `PCT_NAT_PFT` vector, `PCT_NATVEG`, `PCT_CROP`, remaining landunits, reference CTSM commit and executable. Inspect actual code and/or generated namelist to establish the spelling, allowed values and effect of `use_fates_nocomp` and `use_fates_fixed_biogeog`; a missing option is **not** evidence that it is off.

## Step 2: site composition mapping (not yet approved)

Observed inventory in a 500-m circle (Moors 2012, later Loobos data description):
* ENF 93.6% of the surveyed area (Scots pine 89, Corsican/black pine 3.3, Douglas fir 1.3).
* DBF 2.9% (birch 2.3, oak 0.6).
* Remaining 3.5%: open heather / grass mosaic, **not yet separable into FATES shrub versus C3 grass**.

The 500-m circular census is not a footprint-weighted PFT map; compare landunits against the tower-relevant survey and record source year/uncertainty. Do not copy 93.6/2.9/3.5 blindly into `PCT_NAT_PFT`. `fates_hlm_pft_map` can map a host PFT to eligible FATES types and may not implement observed abundance. If model input cannot represent both shrub and grass accurately, define an explicit sensitivity experiment rather than a fabricated 'measured' split.

## Step 3: prepare a NEW case only once the mapping is verified

Desired case name: `NL-Loo_OBSPFT_NC_PRE50`. Keep original `NL-Loo_FATES_SPINUP500` untouched.

**Template settings for an approved, independent new case** (do not apply to existing baseline):

```fortran
use_fates = .true.
use_fates_sp = .false.
use_fates_fixed_biogeog = .true.
use_fates_nocomp = .true.
```

CIME XML targets: same verified compset, forcing calendar `NO_LEAP`, `ATM_NCPL=48`, same historical NL-Loo DATM 1997–2025 stream files and year cycling, fixed CO2 363.04 ppm if the original case uses it; `STOP_OPTION=nyears`, `STOP_N=5`, `REST_OPTION=nyears`, `REST_N=5`, `RESUBMIT=9` **only after a successful 5-year gate**. Start with a single five-year segment and `RESUBMIT=0` to validate model physics and archive, then extend carefully with coordinated restart and remaining 45 years; never accidentally reset the original startup or run segment again. Use **independent RUNDIR, DOUT_S_ROOT and output filenames** and unique CIME case path. Check 1-core/8G `srun --mpi=pmix` Slurm resources rather than inheriting exclusive-node mistakes. `check_input_data` and `preview_namelists` must succeed. Re-using executable through `--keepexe` is prohibited unless mode compatibility is proven; changed build components require a fresh build.

Check actual `CaseDocs/lnd_in` has the intended new surface, new FATES mapping and *both* no-competition flags. Confirm PFT areal coverage with output matching the model's actual area metric; carbon shares are not area.

## Step 4: PRE50 -> AD200 -> POST300

**Do not use one CIME case with an in-flight resubmission loop across mode switches**; create separate stage cases with audited restart handoffs:

* PRE50: normal spinup, 50 y after the 5-y gate, remaining 45y. `CLM_ACCELERATED_SPINUP=off`.
* AD200: 200 y, `CLM_ACCELERATED_SPINUP=on`; restart/hybrid from PRE50 **and validate AD-specific carbon pool transformations**. Only run if the checked-out FATES version supports AD restart semantics and generated `spinup_state`.
* POST300: 300 y normal, `CLM_ACCELERATED_SPINUP=off`; restart/hybrid from AD200 with the appropriate AD-to-normal soil-carbon pool adjustment. **Direct restart is not assumed correct**; inspect CTSM's official AD transition handling for the exact version, otherwise STOP.
* Convergence requirement: separately track FATES VEGC, soil carbon, litter/CWD, biomass size structure, LAI, GPP/NEE; 550 years is a target, not a proven equilibrium.

Manual authorisation gates are mandatory between case creation, first `case.submit`, 50y, AD200 and POST300. Use `squeue` and `sacct` to confirm no duplicate jobs. Monitor inode/file count (`myfiles`) and archive history with checksum verification, preserving all coordinated restart parts.

## Two batches later

`data/22_site_cohort.csv` is an evidence cohort and deliberately has `HOLD_MAPPING` on **all 22 sites**. After NL-Loo passes, additional site surface maps must be approved independently. The batch script must not infer quantitative PFT area from tree species %, carbon share, basal area or vegetation total cover.

## Scientific note

PRE50 is normal spin-up, not merely an expendable technical smoke-test. The first 5-year PRE50 chunk doubles as the short infrastructure test. This avoids accidentally running 5 years normal then resetting before the 50-year schedule.

## Output and reproducibility

Keep the original model and cases in their current directories. Store tiny metadata/receipts and scripts in GitHub, but never raw NetCDF input/outputs, user data packages or licensed tower datasets. Pin the current CTSM/FATES hash, surface SHA256, FATES JSON sha, required CIME XML and actual submitted Slurm job IDs in the operator ledger.
