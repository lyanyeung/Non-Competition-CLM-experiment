# Non-Competition CLM-FATES experiment

**Status: Pilot NL-Loo in preparation; NO IRIDIS cases or Slurm submissions have been performed from this repository.**

## Objective

Investigate the effect of prescribing EC-tower vegetation distribution in **FATES fixed-biogeography + no-inter-PFT-competition (FIXNC)** spin-up, starting with NL-Loo; eventually extend to **22 quantitative-evidence sites** in two batches. The original CLM-FATES experiments are retained untouched as reference runs.

## Time plan: three distinct restart stages

| Stage | Duration (model years) | Decomposition | Proposed case suffix | Segments |
|---|---:|---|---|---:|
| PRE50 | 50 | Normal / `CLM_ACCELERATED_SPINUP=off` | `_OBSPFT_NC_PRE50` | 10 × 5 years |
| AD200 | 200 | Accelerated decomposition / `CLM_ACCELERATED_SPINUP=on` | `_OBSPFT_NC_AD200` | 40 × 5 years |
| POST300 | 300 | Normal / `CLM_ACCELERATED_SPINUP=off` | `_OBSPFT_NC_POST300` | 60 × 5 years |

Total intended: **550 model years per site**, followed by convergence assessment and a *separate* historical/transient run if justified. Durations are a **research choice**, not a verified equilibrium guarantee. Pre50 is a warm-up; its **validated restarts** must seed AD200, and AD200 must seed POST300. Use **separate case names**, `CONTINUE_RUN=FALSE` and a version-appropriate `RUN_TYPE=hybrid` or equivalent restart initialization for mode transitions. Never simply edit `CLM_ACCELERATED_SPINUP` inside an active self-resubmitting case or treat a new startup as a continuation.

The first complete 5-year segment is a **technical gate**, NOT a separate discarded 5-year spin-up. 50-year PRE50 submission only after observed surface approval and accurate FATES mode have been demonstrated.

## PFT mode

Intended generated `CaseDocs/lnd_in` flags (validate on IRIDIS):

```fortran
use_fates = .true.
use_fates_sp = .false.
use_fates_fixed_biogeog = .true.
use_fates_nocomp = .true.
```

Do **not** presume changing `PCT_NAT_PFT` alone is enough. The active `fates_hlm_pft_map` in the real FATES parameter file is essential. CLM surface PFT numbers and FATES PFT numbers differ. Keep original compset only if the actual FATES code and executable support the requested mode; check before reusing binary with `--keepexe`.

## NL-Loo source observation / unmapped remainder

A published 500-m-radius area inventory reports Scots pine 89%, black pine 3.3%, Douglas fir 1.3%, birch 2.3%, oak 0.6%, and open heather / grass 3.5%. Thus ENF **93.6%**, DBF **2.9%**, open ground **3.5%**. These describe a fixed-radius *ground inventory*, not a footprint-weighted map. The open 3.5% **must be split scientifically** between heather/shrub and grass (or explicitly tested as a sensitivity scenario); this repository does **not** fabricate that split. Verify the original observed `PCT_CROP` and other landunits before defining 100% natural vegetation. See [Loobos original tower dataset](https://essd.copernicus.org/articles/18/2023/2026/) and Moors (2012) as quoted therein.

### What to execute now (read-only)

From an IRIDIS6 login node:

```bash
conda activate clm_fates_env
git clone https://github.com/lyanyeung/Non-Competition-CLM-experiment.git ~/Non-Competition-CLM-experiment
cd ~/Non-Competition-CLM-experiment
python -m py_compile scripts/*.py
python scripts/01_inspect_NL_Loo.py --out "$HOME/NL_Loo_NC_audit"
cat "$HOME/NL_Loo_NC_audit/00_overview.json"
```

If already cloned, use `git -C ~/Non-Competition-CLM-experiment pull --ff-only` **only if the working tree is clean**.

The inspector reads real `NL-Loo_FATES_SPINUP500` metadata, the active surface and PFT map. It does not write input files, modify original cases or start jobs. **Do not run any long spin-up until this audit is reviewed.** See [first-site runbook](docs/NL_Loo_first_site_runbook.md).

## Batch strategy

* **Pilot:** NL-Loo, one original six-site member, validate PFT coverage and first 5-year segment before promoting PRE50.
* **Batch A:** 11 sites total, NL-Loo included; run after pilot gates.
* **Batch B:** remaining 11 sites.
* Batch manifest: [data/22_site_cohort.csv](data/22_site_cohort.csv).
* Quantitative evidence includes species/basal area/biomass/vegetated-cover metrics. **22 evidence sites does not mean 22 accepted PFT areal mixtures**.

## Existing work, unchanged

[CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows) and its [38-site PFT evidence table](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv).

## References

* [FATES technical document: prescribed biogeography/no-competition](https://fates-users-guide.readthedocs.io/projects/tech-doc/en/stable/fates_tech_note.html)
* [FATES HLM-to-PFT mapping guide](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html)
* [CESM 2026 tutorial: modifying FATES surface data](https://ncar.github.io/CESM-Tutorial/notebooks/challenge/clm_ctsm/clm_exercise_3.html)
* [CTSM spin-up modes and restart handoff](https://github.com/ESCOMP/CTSM/blob/master/bld/CLMBuildNamelist.pm)

### Safety

No data licenses are redistributed; do not commit original EC archives, forcing CSV/NetCDF, surfaces, executable binaries, restart or Slurm files. Scratch inodes and Research Filestore archiving should be checked before scale-out.
