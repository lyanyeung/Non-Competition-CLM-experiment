# Maintenance log: deleted output, stopped runs and replaced cases

This log records every deletion of model output, every stopped run and every case that replaced another. The diagnosis
and the reasons for each decision are in [NEEDLELEAF_COLLAPSE_DIAGNOSIS.md](../docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md).

Files in this folder:
- [`RULES_FOR_NEW_CASES.md`](RULES_FOR_NEW_CASES.md) explains how any new case gets the phenology patch and the
  needleleaf parameters. Neither is in the shared source, so a default case runs the old code.
- [`20261102_purge_and_replace.sh`](20261102_purge_and_replace.sh) records the stop, delete and replace commands run on
  2026-11-02. It downloads every script at the exact commit used. The deletion code itself is `purge_old()` /
  `old_nc_files()` in script 20 and `purge_old()` / `cancel_nlf()` in script 22 (branch `full-sequence-gpp-nee-ec`). Failed
  Normal prepares are removed by `clean_failed()` in scripts 20b and 23 (branch `normal400-rollout-20261105`).
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

### 2026-11-03 06:38 UTC: five segment chains resumed after node failures (`resume_failed_segment.sh`)

- **NODE_FAIL** on node red6131, 2026-11-03 05:13–05:17 UTC; no model error. The chain was resumed from its last
  archived restart:

  | Case | Resumed from | New run / archive jobs |
  |---|---|---|
  | `US-Uaf_AMF_B04_FIXNC_AD400_BASETA_V1_NLFP` | 2048-01-01 | 4812992 / 4812993 |
  | `FR-Hes_B02_FIXNC_AD400_PHEN` | 2052-01-01 | 4812994 / 4812995 |
  | `US-SRM_AMF_B04_FIXNC_AD400_BASETA_V1_PHEN` | 2064-01-01 | 4812996 / 4812997 |
  | `US-ICt_AMF_B02_FIXNC_AD400_DIRECT_PHEN` | 2062-01-01 | 4813005 / 4813006 |

- **CZ-BK1:** `CZ-BK1_B01_FIXNC_AD400_NLF` died 22 s into segment 10 (2026-11-02 22:58, red6081).
  - It was a segmentation fault during land initialisation (Prigent roughness stream), after 9 good segments with the
    same executable and inputs, so it was treated as transient.
  - Resumed from 2049-01-01: 4813007 / 4813008.
  - If it fails at the same point again, it is investigated instead of resumed.
- **Orphaned st_archive jobs cancelled:** 4812574, 4812572, 4812570, 4812569, 4809520.
- **Checks before each resubmission:** the latest archived restart, the dated rpointer files (`rpointer.<comp>.<date>`;
  Fortran pads the file name with blanks), `CONTINUE_RUN=TRUE`, RESUBMIT left (67–70), and an empty queue.
- **Ledger:** `Needleleaf_F_rerun/resubmits.log`.

### 2026-11-03 06:50 UTC: rollout complete; every replacement case submitted

- **Overnight `22 ad-run`:** 72/76 sites OK, 4 HOLD.
  - CA-TP4, CZ-Stn and DE-Hzd were HOLD lines left by the duplicate process (22:26–22:59 UTC, two `ad-run`
    processes ran at once). All three had been built, verified and submitted by the other process; at 06:41 UTC they
    were at 80 years.
  - DE-Tha's build had been interrupted when the duplicate process was stopped.
- **DE-Tha:** `22 ad-run --sites DE-Tha` repaired the interrupted build (spinup on, user_nl_clm line restored).
  - The build log shows the SourceMods copy of `EDPhysiologyMod.F90` compiled, not the shared copy.
  - `DE-Tha_OBSPFT_NC_V1_AD400_NLFP` was submitted: run 4813067, archive 4813068.
- **GL-ZaH:** the original unpatched AD was stopped. `GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT_PHEN` is running and was at
  75 years at 06:41 UTC.
- **Result:** all 42 replacement AD400 cases are submitted:
  - 23 `_NLFP`;
  - 18 `_PHEN` (75-site screening);
  - GL-ZaH `_PHEN`.

  The 18 KEEP_NLF `_NLF` cases and US-Aud `_HINONE` continue.
- **Since then, script 22 refuses a second concurrent action**, and `watch_rollout.sh` warns about duplicate `ad-run`
  processes.

### 2026-11-04 07:00–13:00 UTC: five AD chains stopped by TIMEOUT on a slow node (red6085)

- **What happened:** five run jobs hit the 1 h wall-clock limit on node red6085. They were in the middle of a 5-year
  segment, and there was no model error. The usual segment time is 7–9 min on every node. Between about 07:00 and
  13:00 UTC, red6085 ran about 7× slower, and three other segments there only just finished (56–60 min). By the
  afternoon it was back to 7–9 min.

  | Case | Run job | Last archived restart | Resumed run / archive |
  |---|---|---|---|
  | `IT-Lav_B03_FIXNC_AD400_NLFP` | 4829008 | 2178-01-01 | 4836460 / 4836461 |
  | `CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5_NLFP` | 4829057 | 2372-01-01 | 4836458 / 4836459 |
  | `US-Me6_AMF_B03_FIXNC_AD400_DIRECT_NLF` | 4831116 | 2380-01-01 | 4836456 / 4836457 |
  | `CZ-BK1_B01_FIXNC_AD400_NLF` | 4831135 | 2314-01-01 | 4836454 / 4836455 |
  | `US-MtB_AMF_B03_FIXNC_AD400_DIRECT_NLF` | 4831154 | 2379-01-01 | 4836452 / 4836453 |

- **How they were resumed:** the orphaned `st_archive` jobs (`DependencyNeverSatisfied`) were cancelled, and the
  chains were resumed with `resume_failed_segment.sh --submit` on 2026-11-05 at about 03:55 UTC, from the last
  archived restart. Wall-clock time was not changed. The ledger is `Needleleaf_F_rerun/resubmits.log`.
- **Partial history files:** the killed segments left partial history files in the RUNDIR. The resumed segment writes
  the same file names again.

### 2026-11-04 16:34 UTC: Normal400 rollout, first attempt (scripts 20 / 22 / 21)

- **Script 20 `normal-run`:**
  - 7 sites were submitted: CH-Dav, DE-Obe, FI-Sod, FR-FBn, IL-Yat, US-Me2 and US-SP1.
  - 3 sites were held because their AD was still running: CZ-BK1, US-Me6 and US-MtB.
  - 8 sites were held with `no overlay reproduces the AD lnd_in`: CA-Ca3, CA-LP1, US-GLE, US-Mpj, US-NR1, US-Vcm,
    US-Vcp and US-Wjs. See the next entry.
- **Script 21 `normal-run`:**
  - US-Aud `_NORMAL400_DIRECT_HINONE` was submitted.
  - CH-Aws was held with `not submitted (None)`. Its AD case was made by Batch04 06c and has no `NLF_STATE.json`.
    It is handled by script 23.
- **Script 22 `normal-run` did not run.**
  - The three scripts were started inside one `setsid nohup bash -c "..."`.
  - Script 22's one-action-at-a-time guard found its own file name in that wrapper's command line and refused:
    "another script-22 action is running".
  - **Rule:** start script 22 (and 23) directly with `setsid nohup $PY -B 22_... normal-run`, never inside a `bash -c`
    wrapper.

### 2026-11-05 ~03:50 UTC: script 22 Normal400, started directly

- `22_phenology_patch_rollout.py normal-run` was started directly.
- 40 sites were submitted: every NLFP / PHEN site whose AD had finished 400 years by then (FR-Pue included), and
  GL-ZaH. The run ended `74/76 sites OK, 2 HOLD`.
- CA-TP4 and IT-Lav were held because their AD was still running.
- Log: `~/CLM_FATES_PLOTS/normal_run22_<UTC>.log`.

### 2026-11-05 03:56 UTC: 8 KEEP_NLF Normals; failed prepares removed; script 20b

- **Cause of the 8 holds:** the only difference was `clm_inparm.spinup_state`.
  - The original Normal `lnd_in` has no `spinup_state` line, but the regenerated one has `spinup_state = 0`.
  - Every other key was identical to the original Normal.
  - The two are equivalent. With `CLM_ACCELERATED_SPINUP` off, CTSM uses 0, and script 20 itself accepts `""` or `"0"`
    for the new Normal.
- **New `20b_normal_spinup_state_tolerance.py`** (branch `normal400-rollout-20261105`, commit d1f3b9d; tools at 167adbc):
  - It runs script 20 `normal_prepare` / `submit` unchanged, except that it accepts this one difference: original
    absent, new exactly 0.
  - Any other value, or any other differing key, is still held.
- **What was deleted (`20b clean-failed --confirm REMOVE_FAILED_NORMAL_PREPARE`):** the 8 half-made Normal cases from
  the 16:34 attempt.
  - Their phase was `PREPARE_ATTEMPTED`. They were never submitted and had no output.
  - Each had 204 files, 0.02 GB in total: the case directory, plus `<OUT>/<case>/run` with copies of the year-400 AD
    restarts. The originals stay in the AD archive.
  - Removed directories:
    - `CA-Ca3_AMF_FIXNC_NORMAL400_UTC_V2_PTS_NLF`
    - `CA-LP1_AMF_FIXNC_NORMAL400_UTC_V2_PTS_NLF`
    - `US-GLE_AMF_B02_FIXNC_NORMAL400_DIRECT_NLF`
    - `US-Mpj_AMF_B03_FIXNC_NORMAL400_DIRECT_NLF`
    - `US-NR1_AMF_B03_FIXNC_NORMAL400_DIRECT_NLF`
    - `US-Vcm_AMF_B05_FIXNC_NORMAL400_DIRECT_NLF`
    - `US-Vcp_AMF_B05_FIXNC_NORMAL400_DIRECT_NLF`
    - `US-Wjs_AMF_B05_FIXNC_NORMAL400_DIRECT_NLF`
  - File lists: `Needleleaf_F_rerun/<site>_failed_normal_prepare_removed_2026-11-05T0356*.txt`.
- **Result:** `20b normal-run` verified and submitted all 8, with run jobs 4836486 to 4836516.

### 2026-11-05: Normal400 of the ICOS Batch04 AD cases (script 23)

- **Why a new script:** DE-Gri, DE-RuR, IT-Tor, ES-Agu and CH-Aws (`_HINONE`) were made by the Batch04 scripts.
  Scripts 20, 21 and 22 cannot take them.
- **New `23_normal400_extra_ad_cases.py`** (same commit):
  - It uses the script-21 Normal method: a clone `--keepexe` of the AD, hybrid from the year-400 restarts,
    spinup off, and the parameter file pinned to the AD's file.
  - AD completion is checked without `NLF_STATE.json`.
  - The AD RUNDIR and archive are read from the case.
  - Normal names: `<AD name with _AD400 -> _NORMAL400>`.
- **Why the fixes are not used:** these sites have neither PFT 2 nor a cold-deciduous PFT (entry of 2026-11-02 22:36).
  They keep the shared unpatched executable and their own parameter files.
- **First `prepare`:** DE-RuR, IT-Tor, ES-Agu and CH-Aws were verified.
- **DE-Gri was held:** `hist_fincl1` had the same 7 fields in the same order, but with blanks after the commas in the
  AD `lnd_in` and none in the new one.
  - Script 23 now compares `hist_fincl` lists without those blanks.
  - Its half-made Normal case was removed with `23 clean-failed --confirm REMOVE_FAILED_NORMAL_PREPARE`. The file list
    is in the ledger.
- **2026-11-05 04:07 UTC:** DE-Gri's failed prepare was removed (183 files, 0.02 GB). The file list is in
  `Needleleaf_F_rerun/DE-Gri_ICOS_B04_FIXNC_NORMAL400_DIRECT_failed_normal_prepare_removed_2026-11-05T040715*.txt`.
  `23 run` then submitted all 5:

  | Case | Run / archive job |
  |---|---|
  | DE-Gri `_NORMAL400_DIRECT` | 4836555 / 4836556 |
  | DE-RuR | 4836557 / 4836558 |
  | IT-Tor | 4836560 / 4836561 |
  | ES-Agu | 4836562 / 4836563 |
  | CH-Aws `_NORMAL400_DIRECT_HINONE` | 4836564 / 4836565 |

- **Check that the fixes do not apply:** `b04_fix_check.py` at d1f3b9d confirmed the shared unpatched executable, no
  SourceMods and `fates_params_default.json` for all five. It also confirmed that GL-ZaH `_PHEN` is patched.
  - Its PFT lines were wrong: it read `fates_hlm_pft_map` transposed and one row off. HLM 13 C3 grass came out as
    `c4_grass`, and ES-Agu's HLM 9 evergreen shrub as `broadleaf_colddecid_arctic_shrub`.
  - Fixed at 167adbc, with the same reading as script 22.
  - **To do:** rerun the check. If ES-Agu shows a cold-deciduous FATES PFT, its AD400 and Normal400 ran without the
    phenology patch and must be redone. Script 22's 2026-11-02 classification of the Batch04 sites says 0 %.
- **Still to start:** the Normal400 of CZ-BK1, US-Me6 and US-MtB (`20b normal-run`), and of CA-TP4 and IT-Lav
  (`22 normal-run`). `auto_normal_last5.sh` (167adbc) starts each one once its resumed AD reaches 400 years.
