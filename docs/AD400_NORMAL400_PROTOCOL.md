# Standard FIXNC protocol: 400-year AD + 400-year Normal

**Project title:** Fixed Biogeography & no competition FATES experiment  
**Decision date:** 24 October 2026  
**New standardized design for the 20 previously unrun evidence sites:** `AD400 → NORMAL400`, 800 **model** years total.  
**No automatic case creation or model submission from this document.**

## Motivation and precise scope

Run **FATES with prescribed vegetation/PFT biogeography and no inter-PFT competition** at the EC station; constrain the site PFT distribution with transparent in-situ/tower evidence rather than assuming original land-use fractions are correct. Forest structure (stem number, tree size, pool evolution) can still evolve under this configuration. Fixed-PFT area is *not* a promise of fixed biomass/DBH or zero ecological dynamics.

Never confuse:
- Reported tree-species **carbon stock**, **basal area**, **stand composition**, **vegetated-cover**, or **investigated-area fraction**;
- True model **ground-area fraction**, natural-vegetated versus crop area, bare fraction, EC flux footprint, or FATES per-PFT carbon outputs.

The [original 38-site evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv) provides a **screening list**, not 22 verified fractional PFT surface maps. A source with percentages may still be on HOLD until its denominator and representativeness are resolved.

## Two independent and sequential phases

| Phase | Years | Climate forcing | Mode and target restart state | Number of 5-year segments | Preconditions |
| --- | ---: | --- | --- | ---: | --- |
| **AD400** | 400 | Recycle **each site's** vetted site-specific forcing years (not hardcoded 1996–2025) | `CLM_ACCELERATED_SPINUP=on`; FATES `spinup_state=2` in real generated `lnd_in` and archived restart | 80 | site PFT/soil/forcing/mapping approved; exact CTSM revision; isolated case; 5-year cold-start smoke |
| **NORMAL400** | 400 | Recycle the **same site** forcing stream as AD unless scientifically justified and explicitly documented | `CLM_ACCELERATED_SPINUP=off`; resulting Normal restart `spinup_state=0` | 80 | **only after all AD400 archived segments and final three-component restart validated**, isolated hybrid branch from final AD checkpoint; first Normal five-year smoke |

For a site's model start year `Y`, the AD restart target is `Y+400` and Normal restart target is `Y+800`. Model-calendar years **are artificial repeated-forcing time**, not a historical simulation period. No preparatory Normal50, and no PRE50/AD200/POST300 in the **new Batch01/02 design**. A future historical/transient run should start from a scientifically selected spin-up restart and follow the chronological observation-era forcing **once**; historical forcing runs are not part of these 800 years.

### First five years, then continuation

1. AD phase first test: `STOP_OPTION=nyears`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`. Verify both **exact** Slurm `run` and `st_archive` jobs `COMPLETED/0:0`, `CaseStatus`, CLM/DATM/CPL archived restart and `spinup_state=2`.
2. Only after that first test, resume the remaining **395** AD years (79 five-year segments; first segment followed by 78 automatic re-submissions **only if the pinned CIME semantics validate that count**).
3. At AD400 completion: verify final archived CLM/DATM/CPL restart from the same case at exact `Y+400` and check model history / carbon pools. No model success assertion from submission, squeue disappearance or an initial `COMPLETED` job alone.
4. NORMAL phase is a **new case/run/archive**, `RUN_TYPE=hybrid` (subject to actual CIME compatibility), `RUN_REFCASE` / `RUN_REFDATE` referencing the final AD checkpoint; copy and checksum-check the three component restart files; stage local `rpointer` targets and `finidat` as required by **the pinned CTSM and site setup**.
5. Normal mode: `CLM_ACCELERATED_SPINUP=off`, do **not** reuse an AD-mode `spinup_state=2` land namelist. In the pinned DE-Tha CTSM implementation, a *missing* explicit `spinup_state` is safer than trying to force `spinup_state=0` via user_nl; verify generated normal `lnd_in`, then archived Normal restart `spinup_state=0`.
6. Normal first five years with `RESUBMIT=0`, then **only after verified Normal archive** run the remaining 395 Normal years. Do not modify or resume the AD source case to switch modes.

**Arithmetic:** per site `5 AD + 395 AD + 5 Normal + 395 Normal = 800`. From the user-approved start year, select exact calendar restart timestamps; never copy DE-Tha's 1996/2001/2396 values blindly.

## Strict input/evidence gates for each tower

- **Vegetation:** trace original species shares, date, spatial survey footprint and denominator; map each species to ENF/DNF/DBF/EBF or an actually supported FATES PFT. Keep ambiguous / unreported share unresolved until an approved proxy or sensitivity scenario exists. No silent normalization of a 43+37=80% report to 100% of the grid.
- **Landunits:** scientifically justify `PCT_NATVEG`, `PCT_CROP`, grass/shrub/open ground and nonvegetated fractions; enforce the final fractions sum to valid CLM totals. Stand composition alone cannot support `NATVEG=100`.
- **FATES mapping:** verify effective `fates_hlm_pft_map` in the **actual binary / parameter file**, `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`. The host CLM `PCT_NAT_PFT` index and FATES PFT index may differ.
- **Soil:** [observed-soil-first policy](observed_soil_texture_policy.md). If reliable site measurements exist, use measured sand/clay with explicit measured depth and any extrapolation; otherwise retain grid soil and label the fallback. Do not overwrite source or previously verified surfaces; verify unchanged NetCDF variables and SHA256.
- **Forcing:** exact time, units, NO_LEAP handling and site-year stream audit; record all remaining QC issues. A researcher may explicitly accept documented residual `REVIEW` for a **pilot**, but this is not a publication-quality forcing validation. Preserve original forcing and sources.
- **CO₂:** fixed at a documented baseline concentration for spin-up unless a separate experiment varies it; do not conflate with historical/transient diagnostic CO₂.
- **Versioning and HPC:** own paths for each site/phase; pinned original input hashes; inspect site case, `EXEROOT`, MPI command, real `#SBATCH` resource requests, scratch inode pressure, and Research Filestore provenance before scaling up.
- **Runbook:** first 5-year smoke, explicit independent verification, guarded continuation; do not call `case.submit` twice after ambiguous failure; never edit a queued/resubmitting CIME case to change mode.

## Learn from the two protected examples

- **DE-Tha**: AD5 cold-start 1996–2001 and independent AD5→Normal5 hybrid 2001–2006 both technically succeeded. Land restarts respectively had `spinup_state=2` and `0`. Its remaining AD395 was submitted to Slurm and was not yet verified finished as of 24 Oct 2026. **This is a validated mode-transition example, not a completed 800-year spin-up.**
- **NL-Loo**: earlier PRE50/AD200 workflow, with different stage sequencing. Preserve that live experiment and its logs. **Do not claim it already follows AD400+NORMAL400 or silently retrofit it.**

The source code templates are site-specific. In particular [DE-Tha Stage10](../examples/DE-Tha/scripts/10_DE_Tha_direct_AD400.py), [Stage11](../examples/DE-Tha/scripts/11_DE_Tha_AD400_continue_after_smoke.py) and [Stage14](../examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) pin particular filenames, source revisions, checksums and model calendars. **Never execute them unmodified for a different tower.**

## Research success criteria

Technical success = both full AD400 and Normal400 phases, correct mode/restarts at handoff, fully archived and numerically stable. Scientific acceptability needs depth-aware soil carbon/soil nitrogen, vegetation biomass/canopy, moisture, annual GPP/NEE and pool/flux drift diagnostics over sufficiently long windows, with explicit convergence thresholds and reference EC observations as applicable. 400+400 years is a **chosen protocol, not a guaranteed equilibrium**.

## Batch tracking

- [Batch01 site register](../data/batch01_10_sites.csv), [Batch01 narrative](../examples/Batch01_10/README.md)
- [Batch02 reserve site register](../data/batch02_10_sites.csv)
- [22-candidate cohort and example role ledger](../data/22_site_cohort.csv)

**Operational status as created:** Batch01 and Batch02 documents only. No new Batch01 surface, forcing modification, CIME case or Slurm submission is authorized or performed.
