# Maintenance log: deleted output, stopped runs and replaced cases

This log records every deletion of model output, every stopped run and every case that replaced another. The diagnosis
and the reasons for each decision are in [NEEDLELEAF_COLLAPSE_DIAGNOSIS.md](../docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md).

Files in this folder:
- [`20261102_purge_and_replace.sh`](20261102_purge_and_replace.sh) records the stop, delete and replace commands run on
  2026-11-02. It downloads every script at the exact commit used. The deletion code itself is `purge_old()` /
  `old_nc_files()` in script 20 and `purge_old()` / `cancel_nlf()` in script 22 (branch `full-sequence-gpp-nee-ec`).
- [`summarize_purge_ledger.py`](summarize_purge_ledger.py) (read only) reads the file lists written before every deletion
  and reports files and GB per site and case. It also lists files that still exist, which means that purge was
  interrupted.

**What a "purge" deletes:** only `*.nc` files (history and restart) in the RUNDIR and the short-term archive of the case
named.

**What a purge never deletes:**
- case directories, `CaseDocs`, `user_nl_*`, `datm.streams.xml`, logs, `CaseStatus`;
- any build directory (executables are shared between cases);
- the diagnostic and trial cases (`*_DIAG50`, `*_FIX?50`, `*_FIXD100`, `*_FIXF100`, `*_PHENFIX50`).

**Where the record of each deletion is:** before deleting, the script writes the full file list (path and size) to
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Needleleaf_F_rerun/`:
- `<site>_purged_files_<UTC>.txt` (script 20);
- `<site>_phen_purged_files_<UTC>.txt` (script 22).

Published figures and CSVs in `figures/` stay the record of the deleted runs.

## Current case per site (2026-11-02 22:20 UTC)

| Class | Sites | Active cases | Replaced (output purged) |
|---|---|---|---|
| KEEP_NLF (18): needleleaf, no cold-deciduous PFT | CA-Ca3, CA-LP1, CH-Dav, CZ-BK1, DE-Obe, FI-Sod, FR-FBn, IL-Yat, US-GLE, US-Me2, US-Me6, US-Mpj, US-MtB, US-NR1, US-SP1, US-Vcm, US-Vcp, US-Wjs | `<AD>_NLF` (running) → `<Normal>_NLF` (script 20 `normal-run`) | original AD400 + NORMAL400 |
| RESTART_NLF (23): needleleaf + cold-deciduous PFT | BE-Bra, BE-Vie, CA-TP4, CH-Lae, DE-Tha, FI-Hyy, FI-Let, FR-Fon, IT-Lav, IT-Ren, RU-Fyo, US-BZS, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-MOz, US-NC2, US-Slt, US-Syv, US-UMB, US-UMd, US-Uaf | `<AD>_NLFP` (phenology patch + needleleaf F; script 22) → `<Normal>_NLFP` | original AD400 + NORMAL400; `<AD>_NLF` (stopped) |
| RERUN_PHEN (18): cold-deciduous, no PFT 2 | CZ-Stn, DE-Hai, DE-Hzd, DE-Lnf, DK-Sor, FR-Hes, FR-Pue, IT-Col, US-EML, US-ICh, US-ICt, US-MMS, US-NR3, US-Rpf, US-SRG, US-SRM, US-Ton, US-WCr | `<AD>_PHEN` (phenology patch only; script 22) → `<Normal>_PHEN` | original AD400 + NORMAL400 |
| UNCHANGED (15) | AT-Neu, BR-Ma2, CH-Cha, CH-Fru, ES-LJu, GF-Guy, IT-MBo, IT-Noe, US-Kon, US-Seg, US-Ses, US-UiD, US-Var, US-Whs, US-Wkg | original AD400 + NORMAL400 | – |
| EXCLUDED (1) | US-CMW (groundwater-dependent, docs section 11) | original, flagged | – |
| RESTART_AD (1): ICOS Batch04, AD-only, cold-deciduous | GL-ZaH (arctic deciduous shrub 5.3 % + arctic C3 grass 1.8 %, private parameter file) | `GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT_PHEN` (script 22) → `GL-ZaH_ICOS_B04_FIXNC_NORMAL400_DIRECT_PHEN` | `GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT` stopped after about 10 years (unpatched) |
| ICOS Batch04, no cold-deciduous PFT, no PFT 2 | DE-Gri, DE-RuR, IT-Tor, ES-Agu (CH-Aws has no Batch04 case yet; cool C3 grass, not cold-deciduous) | their `*_ICOS_B04_FIXNC_AD400_DIRECT` keep running: the patch and the needleleaf fix do not apply | – |
| Separate fix | US-Aud (not in the 75-site screening) | `US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT_HINONE` (script 21) → `..._NORMAL400_DIRECT_HINONE` | original AD400 failed in its first segment (no output to keep) |

The classification is read from each site's surface data and parameter file:
- needleleaf = PFT 2 present;
- cold-deciduous = `fates_phen_leaf_habit == 2`.

It was printed by `22_phenology_patch_rollout.py plan` on 2026-11-02 22:11 UTC (75/75 sites, 0 HOLD).

## Entries

### 2026-11-02 19:48–22:15 UTC: needleleaf rerun, original output of the 41 PFT-2 sites (script 20)

- **Why:** the needleleaf parameters were changed (fix F, section 9). The original default-parameter AD400 and
  NORMAL400 runs of every site with PFT 2 are superseded. Disk space was short (operator decision, 2026-11-02).
- **What was started:** `20_needleleaf_rerun_AD400_NORMAL400.py ad-run` created and submitted `<AD>_NLF` at all 41
  sites (41/41 verified and submitted, 0 HOLD).
- **What was deleted:** `purge-old --confirm DELETE_OLD_NEEDLELEAF_OUTPUTS` ran in several runs:
  - BE-Bra, BE-Vie and CA-Ca3 were deleted first; CA-Ca3 alone was 2175 files, 5.4 GB.
  - Two foreground runs were interrupted with Ctrl+C, so a site could be left partly deleted. Any `.nc` left over is
    removed by the script-22 purge below.
- **Consequence:**
  - Scripts 15 and 19 can no longer read the "control" (the original AD400, first 100 years) of the ten trial sites.
  - The published final-trial results (`figures/AD400_NORMAL400_needleleaf_final_trials/20261102T191319Z`) keep the
    control numbers.

### 2026-11-02 ~22:12 UTC: 23 `<AD>_NLF` runs stopped (script 22 `cancel-nlf`)

- **Why:** the FATES phenology patch was adopted (section 16). These 23 sites also have a cold-deciduous PFT. Their
  `_NLF` runs, about 2–3 hours old and without the patch, were stopped so that each site runs 800 years once, with patch
  and needleleaf F together, as `<AD>_NLFP`.
- **How:** `RESUBMIT=0`, then `scancel` of the run and st_archive jobs. Each case's `NLF_STATE.json` is marked
  `CANCELLED_REPLACED`, with the years archived at the time it was stopped.

### 2026-11-02 22:19 UTC: purge before the patched rebuilds (script 22 `purge-old`)

- **What:** `22_phenology_patch_rollout.py purge-old --confirm DELETE_OLD_PHENOLOGY_OUTPUTS`, covering:
  - RERUN_PHEN (18): the original AD400 and NORMAL400;
  - RESTART_NLF (23): the stopped `<AD>_NLF`, plus anything left of the original AD400 and NORMAL400;
  - KEEP_NLF (18): anything left of the original AD400 and NORMAL400. The running `<AD>_NLF` is not touched.
- **Safety:** cases with queued or running jobs are refused. A new case needs only the original's `CaseDocs`,
  `user_nl_clm` and stream xml, none of which is deleted.
- **Consequence:** DE-Hai's original NORMAL400 was the "healthy DBF" reference of script 16. Once `DE-Hai_..._PHEN`
  has run, script 16 will use it as the reference instead.
- **Totals:** to be added when the purge log ends (`TOTAL freed`).

### 2026-11-02 20:09 UTC: US-Aud

- The stuck `st_archive` job 4800874 of `US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT` was cancelled. Its run had stopped in
  the first segment (HumanIndexMod negative RH, section 17), so there was no output to keep.
- It was replaced by `..._HINONE` (`calc_human_stress_indices = 'NONE'`), which was submitted.

### 2026-11-02 22:36 UTC: ICOS Batch04 checked, GL-ZaH to be stopped and replaced (script 22 `cancel-ad`)

- **Check:** none of the Batch04 cases is built with the phenology patch. They all use the shared executable
  `GF-Guy_FATES_SURF2000_CO2405_1PT/bld`.
- **Unaffected:** the running FIXNC AD400 cases of DE-Gri (70 y), DE-RuR (60 y), IT-Tor (10 y) and ES-Agu (45 y) have
  0 % cold-deciduous and 0 % PFT 2. The old code gives the same result for them, so they keep running.
- **GL-ZaH:** `GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT` (about 10 y, `fates_params_GL-ZaH_arctic_private_candidate.json`) has
  7.1 % cold-deciduous vegetation (arctic deciduous shrub 5.3 %, arctic C3 grass 1.8 %).
  - It is stopped (RESUBMIT=0, scancel). A JSON record of the stop goes to the ledger.
  - It is replaced by `..._PHEN`: patch only, same private parameter file.
- **Older exploratory cases are not part of the nocomp experiment and are not touched:** `*_FATES_SPINUP*`,
  `*_FATES_RH*`, `*_S30SHARED`, `*_S30EXCL` (different surfaces, accelerated spin-up off).
