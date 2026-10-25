# Stage04: four Stage03 candidates created; prepare independent AD5 cases

## Operator result, 25 October 2026

The operator supplied the successful Stage03 console output from `/home/ly3n24/Batch02_10_stage03.rQ6RzXYe/stage03_build.log`. Both downloaded inputs passed SHA256 checks and the builder reported:

```text
FI-Hyy CANDIDATE_CREATED
FR-Hes CANDIDATE_CREATED
CH-Fru CANDIDATE_CREATED
IT-MBo CANDIDATE_CREATED
CANDIDATE_SUMMARY created_or_verified= 4 failed= []
NO case creation, namelist changes or model submission.
```

Each surface and adjacent JSON receipt is under `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/<site>/surface_candidates/`. The four PFT, landunit and vertical-soil proxies remain exactly as documented in [Stage03](stage03_mapping_PFT_soil_and_four_candidates_20261025.md). This is operator-reported construction success. The console did not print candidate byte hashes; Stage04 reads and verifies the actual files against their receipts on IRIDIS.

## Next executable step

[The four-site preparer](../scripts/04_prepare_four_AD5_cases.py) creates only new `<site>_B02_FIXNC_AD400` CIME cases, with independent run/archive directories and five-year cold starts. These are technical pilots of the candidate scenarios, not a claim that the proxies are measured footprint composition.

| Site | Configuration reference | AD5 calendar | AD400 target |
| --- | --- | --- | --- |
| FI-Hyy | FI-Hyy_FATES_SPINUP1000_S30SHARED | 1997 → 2002 | 2397 |
| FR-Hes | FR-Hes_FATES_SPINUP500 | 1997 → 2002 | 2397 |
| CH-Fru | CH-Fru_FATES_SPINUP500_11P | 2005 → 2010 | 2405 |
| IT-MBo | IT-MBo_FATES_SPINUP1000_S30SHARED | 2003 → 2008 | 2403 |

Before creating cases, Stage04 verifies all four candidate receipts/arrays, the original surfaces, the active parameter map, source start/CO₂/calendar/coupling, the existing executable, and the selected DATM stream years/paths/file existence. Annual meteorological values are not rescanned. The source executables and forcing are reused; source restarts are not used. Source CO₂ stays fixed at 363.04/363.04/378.98/375.14 ppm respectively.

The private build-namelist overlay reuses the two narrowly pinned Batch01 changes, guarded by shared CTSM blob `698f2396aba8e11cbbbdd58c74ad221e6b7e7038`. Shared CTSM is not patched. Each new case temporarily selects this private overlay for `preview_namelists`, then restores its exact original `env_case.xml` lock even if preview fails. Generated land namelists must match in CaseDocs and RUNDIR and use `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `use_fates_sp=.false.`, `use_cn=.false.`, `spinup_state=2`, empty `finidat`, `STOP_N=REST_N=5`, `RESUBMIT=0`. Generated DATM stream semantics and user DATM overrides must match the selected source.

### Run on IRIDIS

```bash
conda activate clm_fates_env
(
  set -euo pipefail
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/a4c2f28c80cd1e2e334cc640fc6a0542d61c41cc/examples/Batch02_10/scripts/04_download_and_prepare_four_AD5.sh" \
    -o "$HOME/Batch02_10_stage04.sh"
  bash "$HOME/Batch02_10_stage04.sh" prepare
)
```

The launcher downloads all four code/data dependencies from one pinned revision and checks every SHA256. No cluster `git pull` or Stage01/02/03 rerun is needed.

Expected success:

```text
AD5_PREPARE_SUMMARY prepared= 4 failed= []
NO SLURM JOBS SUBMITTED. AD395 and Normal400 are later phases.
```

A successful case gets `<Batch02 root>/<site>/AD5_case_state.json`. Each preparation has an exclusive attempt marker; existing targets or partial attempts stop instead of being overwritten or retried automatically. If it fails, retain the printed `CONSOLE_LOG` and inspect the error. The preparer has no submission action.

## Verification and remaining work

Local validation passed: Python syntax/self-test/plan; a simulated four-case CIME preparation flow with source/executable/stream preservation, exact XML restoration, duplicate-attempt and changed-candidate rejection, missing-forcing rejection, and preview-failure lock restoration. The launcher passed an offline download/layout/checksum/plan test and rejected corrupted dependencies. These fixtures mock CIME and NetCDF calls; they do not establish a real IRIDIS CIME preview or model integration.

**Pending:** real Stage04 prepare output, then guarded first AD5 submission, run/archive/restart validation, AD395 continuation and independent Normal400. No AD5 has been submitted by this update. DK-Sor, FR-FBn, BE-Bra, IT-Noe, CH-Lae and ES-LJu still have no selected automatic candidate. The requested ten-site AD400 → Normal400 experiment remains unfinished.
