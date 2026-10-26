# Batch02_10 — second European/ICOS cohort, AD400 → Normal400

## Stage44 — DK-Sor and BE-Bra rebuilt with ICOS basal-area PFT (26 October 2026)

**Why.** The ICOS ETC ancillary reports give tree basal area by species. Register: [FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv).
- **DK-Sor:** Fagus sylvatica 98.9% (CP 2023) and 100% (SP 2021), so **DBF 100**. The old case ran DBF 80 / ENF 10 / DNF 10.
- **BE-Bra:** Pinus sylvestris 85.2% (CP 2023) and 82.1% (SP 2020), so **ENF 84 / DBF 16**. The old case ran ENF 55 / DBF 45.
- **FR-FBn** keeps its running Stage43 case: ENF 75 / EBF 25 is inside the ICOS range (P. halepensis 70 / Q. ilex 25–28).

**Operator 18:35 UK:** the Stage43 DK-Sor and BE-Bra AD400 jobs were cancelled. All old Batch02 outputs of the two sites are to be deleted. DK-Sor may have been transferred to IRIDIS with only part of the merged multi-source forcing, so its forcing is checked year by year before reuse.

[Stage44 controller](scripts/44_rebuild_DKSor_BEBra_ICOS_PFT_AD400.py) runs these steps:
1. **`inventory`** (read only) prints the template configuration and, for every forcing year, the record count, missing/fill values, means and longest constant run. It lists candidate annual-NC forcing folders with their year ranges and every old folder that `purge-old` would delete.
2. **`prepare`** builds a new surface: a copy of the Stage29 surface with only `PCT_NAT_PFT` changed (soil, landunits and coordinates are verified unchanged). It then clones the Stage43 history-fixed case with `--keepexe` (new names `DK-Sor_B02_FIXNC_ICOS_DBF100_AD400` and `BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_AD400`), previews with the private AD overlay, keeps the approved meteorology XML, and validates that the effective `lnd_in` differs from the template only in `fsurdat`.
   - For DK-Sor, `--forcing-dir DK-Sor=<folder>` installs a complete annual-NC record instead. Every year must be contiguous, carry all stream variables and the template record count, and have no missing or fill values; otherwise nothing is written. If the start year changes, `--co2 DK-Sor=<ppm>` is required.
3. **`purge-old`** deletes every `<SITE>_B02_*` case, run and archive folder except the new one. It is allowed only after the new case is verified, and it refuses if any of those jobs is queued. A receipt is written.
4. **`submit`** applies the stack guard and makes one `case.submit --skip-preview-namelist` with `RESUBMIT=79` (80 × 5 years). `audit-first5` checks the first 5-year restart.

**Operator inventory 19:07 UK:**
- **DK-Sor forcing is complete:** 1996–2024, 29 annual files of 17520 records each, no missing or fill values (`datm_v5_candidate_timevarying_zbot`). BE-Bra has 1996–2025, 30 files, with the four Stage34-curated years.
- **Stale year range:** both Stage43 cases still had `DATM_YR_START/END/ALIGN = 2018/2019/2018`, inherited from the old reference cases. Their effective stream XML nevertheless cycled the full record. Stage44 sets `DATM_YR_*` from the streamed years.
- **Jobs still alive after the cancel:** CIME had already resubmitted, leaving BE-Bra run 4741199 running and archives 4741201, 4741147, 4734697 and 4734486 pending. They must be cancelled before any purge.
- **Purge runs in two rounds:** before prepare, `purge-old` deletes all old outputs and old cases but keeps the Stage43 template case folder. It deletes that folder too once the new case is verified.

A mock test passed. It covered a broken-forcing HOLD, the CO₂ gate, purge-before-prepare refusal, queued-job refusal, duplicate prepare/submit refusal, surface PFT for both sites and the forcing swap.

## Normal400 for the four AD400-complete sites — Normal395 submitted (26 October 2026, 17:12 UK)

Operator IRIDIS6 output from Stage27:
- `audit-normal5` PASS 4/4 with `spinup_state=0`: FI-Hyy 2402, FR-Hes 2402, CH-Fru 2410, IT-MBo 2408.
- `continue-normal395` then submitted the first continuation segments (run/archive): FI-Hyy 4740959/4740960 (→2797), FR-Hes 4740961/4740962 (→2797), CH-Fru 4740963/4740964 (→2805), IT-MBo 4740965/4740966 (→2803).

The Normal `fates_paramfile` content equals each AD source (sha256 `0819f8fddcb3…`). Next: `audit-normal400` after the 79-segment chains finish. Do not rerun `continue-normal395`.

For the five Stage43 history-fix cases (ES-LJu, DK-Sor, FR-FBn, BE-Bra, CH-Lae), the operator reported `--prepare` and `--verify` PASS with no jobs. The one-shot `--start --confirm SUBMIT_FIVE_BATCH02_HISTORY_FIXED_AD400_ONCE` is the next operator step.

## Stage42 operator-confirmed five history-output failures; Stage43 isolated AD400 recovery (26 October 2026)

The actual five-case diagnosis confirms **all five** ES-LJu/DK-Sor/FR-FBn/BE-Bra/CH-Lae jobs failed in `histFileMod.F90:899`: tape1 requests unregistered `GPP,NPP`, while each exact model registry has 1141 fields including `FATES_GPP,FATES_NPP`. Both effective land namelists match and no restart/pointer/archive date exists for any of the five. The downstream Slurm Killed message is not the root cause shown by these logs. The pasted AmeriFlux Batch02 audit is a different campaign and is not a recovery target here.

[Stage43 independent five-case recovery controller](scripts/43_five_GPP_NPP_histfix_AD400.py) and [commands/preservation contract](docs/five_history_fixed_AD400_recovery_20261026.md) pin the actual failure/input hashes, create five separate same-site history-fix cases, preserve selected MET24/MET34/MET36 and PFT/soil/executable inputs, compare all non-history land settings, and follow AmeriFlux Stage21's submitter-stack guard. Preparation and verification submit no jobs; the separate one-shot start launches each new AD400 chain as 80x5 years. Old cases and pending archive jobs, the four completed sites and the active IT-Noe case remain untouched. **Code publication is not evidence of live preparation, submission or AD400 success.**


## Latest operator report: five Batch02 initial AD400 failures — Stage42 diagnosis (26 October 2026)

The operator reports four Batch02 sites completed AD400, IT-Noe running in its separate GPP/NPP history-fix case (model clock 2039), and five unresolved initial AD failures: **ES-LJu 4734425, DK-Sor 4734485, FR-FBn 4734487, BE-Bra 4734696, CH-Lae 4734856**. Earlier running/submission snapshots below are historical for these jobs. The resolved 25 October low-stack first attempts, IL-Yat 4728152 and superseded CA-TP4 V2 4728206 are not new recovery targets.

[Stage42 five-case read-only diagnosis](scripts/42_diagnose_five_failed_AD400_readonly.py) and [recovery decision guide](docs/five_failed_AD400_recovery_triage_20261026.md) collect exact failed logs/registries, effective history fields, original stack receipts, runtime submission settings and restart artifacts before any new submission. Follow the operator-requested [AmeriFlux Stage21 stack-inheritance guard](../AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py): at least 65536 KB in the actual submitter, plus verified skip-preview behavior. The five submit controllers already have stack guards; cause remains unconfirmed until actual logs. Do not repeat old one-shot start commands, modify the four completed runs, or interrupt IT-Noe. This update publishes diagnostics, not new jobs or proven fixes.

## IT-Noe Stage41 actual difference resolved; Stage40 controlled resume of partial preparation (26 October 2026)

Operator's **Stage41 full differential** on original/new IT-Noe effective `lnd_in`: old `a270910c91f55cb492d417109b034a39a1d05ba84c0109434b1c5db7258aeea6`, new CaseDocs and run both `2a205dcaa06dc1c7c255fb12ebaa19aaa2d82f28c962737c4770c56a0a89897b`; original hist_fincl1 `TOTSOMC,TOTSOMN,TLAI,GPP,NPP,TWS,H2OSNO`; new `TOTSOMC,TOTSOMN,TLAI,FATES_GPP,FATES_NPP,TWS,H2OSNO`. **Only one extra changed text line** in the entire namelist is CIME's autogenerated trailing `!# CLM build-namelist` command-line provenance comment, in which case paths change from old to cloned new case. **No actual land namelist parameter differs beyond the intended history fields.** Stage41's misleading `CHANGED_EFFECTIVE_KEY n_melt_glcmec` is because its coarse assignment scanner included the trailing comment after that key; the numeric `1.0d00` is unchanged. Initial Stage40 whole-file comparison was too strict and the case was already cloned, with `prepare_attempt.json` phase `PREPARATION_ATTEMPT_UNCERTAIN`; **no Slurm submission**.

**Updated [Stage40](scripts/40_IT_Noe_new_case_GPP_NPP_histfix_AD400.py):** `compare_effective_except_history` permits **only exactly one** commented `!#     ... CLM build-namelist ...` line whose only text difference is all occurrences of the original full absolute CIME case path replaced with the new full absolute case path; every other line outside `hist_fincl1` remains byte-exact. Built-in self-test asserts that changing a model parameter outside tape1 still FAILS. New `--resume-prepare --confirm RESUME_IT_NOE_STAGE40_EXISTING_PREPARED_CASE_NO_SUBMIT` validates old original SHA, historical field registry, full new effective CaseDocs/RUNDIR and science keys, original 22-y DATM/PFT/executable, CIME settings and Slurm absence, then **updates only the existing uncertain Stage40 preparation receipt** to `PREPARED_NEW_HISTFIX_NOT_SUBMITTED`. It performs **no new clone, XML changes, namelist regeneration or job submission**. Subsequently run `--verify` readonly, and submit using `--start --confirm SUBMIT_IT_NOE_STAGE40_GPPNPP_AD400_ONCE` separately only if all gates PASS and exploratory science approved. Never rerun Stage40 `--prepare` or Stage15 `--start`.

---
## IT-Noe Stage40 partial new case: effective non-history lnd_in mismatch — Stage41 read-only diff

Latest operator output: Stage40 source audit PASS, verifies **both FATES_GPP and FATES_NPP registered** and original (22y QC-v3) DATM/PFT/executable unchanged. Stage40 successfully cloned `IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400`, generated and checked `hist_fincl1` first; then ***failed before writing a success receipt or submitting Slurm*** because `without_tape1(new lnd_in) != without_tape1(original lnd_in)`. The new case and `stage40_IT_Noe_GPPNPP_histfix_AD400/prepare_attempt.json` exist; phase is `PREPARATION_ATTEMPT_UNCERTAIN`. **DO NOT rerun Stage40 --prepare, --start, or old Stage15; do not delete or overwrite partial case**. This may reflect CIME-generated formatting/default differences or a real unintended namelist change; do not presume which.

[Stage41 targeted read-only diffs](scripts/41_IT_Noe_partial_case_lnd_diff_readonly.py) validates original Stage39 SHA and new tape1 replacement, inspects actual new CaseDocs and RUNDIR lnd_in, computes byte-identical comparisons outside tape1, prints every changed assignment and a bounded unified diff (excludes only the intended tape1 delta), checks untouched submission receipt and partial preparation phase. Source/partial case, CIME configs and Slurm entirely unchanged. Run Stage41 audit, review actual diffs and only then implement a guarded **resume of existing partial prepared case** that checks all non-history science keys and final effective outputs. Do not use earlier Stage40 whole-file condition's failure as proof of scientific mismatch.

---
## IT-Noe Stage40 read-only source audit false blocker — fixed (26 Oct)

Actual operator attempt: `--self-test PASS`, `--audit-source` failed with `user_nl_clm original hist_fincl1 not exactly 7 expected fields`. This was an overconstraint on the **input** `user_nl_clm`: CIME combines templates/defaults/user_nl to produce the **effective** `CaseDocs/lnd_in`, which Stage39 explicitly pinned by SHA and confirmed exactly `TOTSOMC,TOTSOMN,TLAI,GPP,NPP,TWS,H2OSNO`. The source user_nl may specify a different subset or no tape1 list; this does not override the evidence from the effective file.

**Updated Stage40** [script](scripts/40_IT_Noe_new_case_GPP_NPP_histfix_AD400.py): validates all seven **effective** original history fields and exact old namelist/model-log SHA, prints old user_nl tape1 if present, accepts a single nonmatching or missing old user_nl tape1, and injects/replaces **only `hist_fincl1` in the newly cloned case's `user_nl_clm`**. The new effective `CaseDocs/lnd_in` and `RUNDIR/lnd_in` must contain all seven desired entries, all requested model science keys must match original, and **the entire new generated effective lnd_in except tape1 must be byte-identical to original**. Duplicate source tape1 assignments and any failure to generate exact new effective namelist stop before submit. Previous failure happened before writing any new case or Slurm jobs; do not rerun old Stage15. Stage40 scientific basis remains exploratory.

---
## IT-Noe Stage39 exact repair: two missing history fields; isolated Stage40 (26 October)

Operator-completed **Stage39** effective failed case `lnd_in` SHA `a270910c91f55cb492d417109b034a39a1d05ba84c0109434b1c5db7258aeea6`, failed `lnd.log.4733521.*` SHA `be88700306ad1347d20a50c02f7e9fa82e6253c63dc37a68eef6d81d8a7c9158`; 1015 registered history fields. History tape 1 `hist_fincl1` requests exactly `TOTSOMC, TOTSOMN, TLAI, GPP, NPP, TWS, H2OSNO`. All but **GPP (4th), NPP (5th)** registered. FATES `FATES_GPP` registered; [CTSM official history documentation](https://escomp.github.io/CTSM/users_guide/setting-up-and-running-a-case/history_fields_fates.html) includes both `FATES_GPP` and `FATES_NPP` (production in kg C m-2 s-1). **Do not confuse `fincl(4)` (field 4, tape 1) with `hist_fincl4`!** FATES_NPP must additionally be confirmed in *this exact failed-run model registry* before new-case creation.

[Stage40 guarded independent new case controller](scripts/40_IT_Noe_new_case_GPP_NPP_histfix_AD400.py) targets only history tape 1 output names `GPP→FATES_GPP`, `NPP→FATES_NPP`; all other five fields must be unchanged. `--audit-source` verifies exact original model lnd/log/MET/PFT hashes and both replacement names registered, original `user_nl_clm` exact 7 fields. `--prepare --confirm PREPARE_IT_NOE_STAGE40_GPPNPP_NEW_CASE_NO_SUBMIT` clones same-site *previously failed* model into new separate `IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400`, shares original compiled executable, builds FATES accelerated history namelist with private overlay and sets new independent RUNDIR; **no Slurm**. `--verify` checks actual new effective history fields, all other science namelist inputs and original 22-year CDEPS stream, PTS/coupler, startup/reset/rest options and empty restart. It uses non-repeatable preparation and submission ledgers. `--start --confirm SUBMIT_IT_NOE_STAGE40_GPPNPP_AD400_ONCE` performs the **first and only Slurm submission of the new case**, explicit after operator has reviewed PASS. Never run old Stage15 `--start`, delete prior failed job logs/receipts, or claim success at submission (only eventual AD400 restart validates completion).

Scientific caveats: original `QC-v3` tower-forcing branch and Juniperus-conifer-shrub → broadleaf-evergreen FATES PFT proxy remain experimental; solving output selection **does not resolve those science limitations**.

---
## IT-Noe Stage38 actual root cause CONFIRMED: requested unsupported CLM history field GPP (26 October)

Operator supplied complete Stage38 script output. **Actual `lnd.log.4733521.261025-230504`**: `hist_htapes_build Initializing clm2 history files` then **`htapes_fieldlist ERROR: GPP in fincl(4) for history tape 1 not found`**, then **`ERROR in histFileMod.F90 at line 899`**. The indexed `fincl(4)` means **fourth requested field on history tape 1**, **NOT** `hist_fincl4`. CIME fatal ensues at model initialization and triggers `srun 4733521.0 FAILED 1:0`, 19 seconds; no history files, no restart, no completed five-year segments. It is **NOT** 2-m RH, Q/VPD, MPI stack, or OOM; the apparent Slurm SIGKILL is downstream of CLM's Fortran abort. Selected DATM successfully opened IT-Noe 2004 and land source initialized. The exit memory MaxRSS ~16.25MB vs 8GB requested is incompatible with OOM explanation.

**Immediate correction**: inventory actual *effective* `lnd_in` tape1 request list against exact model `lnd.log` registry. [Stage39 read-only](scripts/39_IT_Noe_failed_history_field_inventory_readonly.py) identifies all unregistered requested fields with tape/index, and checks exact original `CaseDocs/lnd_in` equals `RUNDIR/lnd_in`, historical failed log, and registration count. It reports whether FATES alternatives such as `FATES_GPP_PF` exist but does **not** blindly replace plain `GPP`: these are not dimensionally/aggregation equivalent without deliberate history choice. On confirming requested fields, create a **new cloned case** with only science-preserving output-list corrections and original meteorology, PFT, compiled exe, and source SHA retained. **NEVER rerun the one-time failed Stage15 submission or edit original completed CaseStatus/receipt**.

---
## IT-Noe AD400 failed run 4733521: Stage38 actual Slurm/model-log forensics (26 Oct)

Operator confirms CH-Lae Stage37 AD400 is running successfully, following successful BE-Bra Stage35 submission. The remaining Batch02 site **IT-Noe** previously had CIME/Slurm first-run job `4733521` **FAILED ExitCode 1:0** in ≈19 seconds, and companion archive `4733522` **DependencyNeverSatisfied**. **Neither the short elapsed time nor its historical negative-2m-RH aborts identify this particular failure cause.** The Stage14 actual QC-v3 22-year selected CDEPS DATM numeric screen passed broad bounds but cannot exclude CLM HumanIndexMod diagnosed-RH errors; PFT broadleaf-shrub approximation also remains a scientific caveat. A new original-case re-submit via Stage15 is forbidden: a one-shot `stage15_IT_NoE_direct_AD400/submission_attempt.json` ledger exists.

[Stage38 read-only full failure forensics](scripts/38_IT_Noe_4733521_failure_forensics_readonly.py) collects `sacct` job/step state and exit codes/MaxRSS/Reason, `scontrol show job` if retained, actual `sacct` stdout/stderr paths, the original CIME CaseStatus, XML run settings, effective FATES namelist, recent case/rundir logs, error excerpts (fatal, RH, HumanIndex, ESMF, netCDF, segmentation, OOM, stack, MPI) and any restart history. No CIME model edits, no Slurm actions and no writes. Run `python3 -B Stage38.py --self-test` then `python3 -B Stage38.py --diagnose 2>&1 | tee ~/IT_NoE_Stage38_failure_diagnostics.log`. Review actual traceback before preparing a new independently guarded retry case or deciding a model/meteorology fix. Never assume failed 19-second job completed a 5-year chunk.

---
## CH-Lae Stage33 human review → Stage36 constrained Met candidate → Stage37 independent AD400 (26 October)

Operator confirms **BE-Bra Stage35 submitted successfully** (Job ID not yet supplied). DK-Sor and FR-FBn Stage31 AD400 likewise already submitted; do NOT resubmit any of them. **CH-Lae Stage32** actual 2004–2024: 21 provisional-name input files, no invalid physics, zero RH<5, negative VPD or >12°C half-hour changes, but **7 instances >8°C**. Subsequent full Stage33 context shows **three isolated T anomalies** (one with T-only change and two with paired Q) warranting local numerical sensitivity candidates:

- **2012-11-02 14:30** T=10.149°C between 1.076 and −0.728°C; QBOT=0.0054983 between 0.00379997 and 0.00375857. Proposed 1 half-hour TBOT/QBOT midpoint.
- **2015-06-12 15:30** T=14.097°C between 23.020 and 20.350°C; leave QBOT as observed/selected, propose T midpoint only.
- **2017-06-27 14:30** T=15.452°C between 24.386 and 23.970°C; QBOT=0.00504751 between 0.01001135 and 0.01044575. Propose 1 half-hour TBOT/QBOT midpoint.
- **2005-12-31 08:00**, T jumps −5.201°C to 3.388°C and remains ≈3.4°C (sustained step); **2012-11-01 15:30**, abrupt 10.093°C→−0.487°C followed by ≈−0.3°C (sustained step). **Do NOT interpolate these as isolated points, or assert their scientific validity**. Requires native tower/met time-source comparison for publication-grade forcing.

[Stage36 versioned site-specific 21-year DATM candidate](scripts/36_CH_Lae_targeted_3year_DATM_candidate.py) pins exact actual Stage30 CH-Lae source CDEPS stream and source SHA for 2005,2012,2015,2017; reads source NetCDF, checks time, exact timestamps/neighbor T and Q signatures, performs only **TBOT3/QBOT2** sparse half-hour writes into **three new** annual NetCDF, leaves 18 source annual files and all precipitation/time/data variables unchanged, verifies every variable/source count and on-disk float32/float64 quantum equality. Manifest includes source SHA, 21 files and unresolved sustained-source warning. Output `stage36_CH_Lae_targeted_MET_QC_v1`. **Exploratory interpolation, not an original ICOS/ERA5 verified science release.**

[Stage37 independent exact-selected-21-file AD400 controller](scripts/37_CH_Lae_MET36_independent_AD400_prepare_submit.py) clones unsubmitted Stage30 CH-Lae case into new `CH-Lae_B02_FIXNC_FOREST_MET36_AD400`, reuses original exe and FATES proxy PFT ENF12 DBF88, regenerates model AD user_nl via trusted private overlay, rewrites *only* new-case selected CDEPS for three candidate years and verifies all 21 year SHA, nuopc point, effective lnd_in and restart emptiness. `--prepare` creates **NO Slurm jobs**; `--audit` read-only; `--start --confirm SUBMIT_CH_LAE_STAGE37_TARGETED_EXPLORATORY_AD400_ONCE` one-time submits 80×5 years with `--skip-preview-namelist`. Never run prior Stage31 `--start --sites CH-Lae` in parallel and never resubmit after an uncertain Stage37 submission.

---
## 26 October Stage34 NetCDF float32 precision hotfix — **use new v2 candidate path**

Actual operator result: Stage34 `--self-test` and `--audit` PASS; expected source SHA hashes and 1996/1999/2005/2021 intervention counts exactly match (QBOT 27, TBOT 4). The initial `--build` failed on first year 1996 *before publishing its first candidate NetCDF* due to **overly tight `1e-6 K` floating-point exactness** in the post-NetCDF TBOT check. This is a writer/verifier precision issue, not evidence that paired source-anomaly selection was wrong. Old `stage34_BE_Bra_curated_MET_QC_v1` directory may remain empty or partially created; never delete or overwrite it automatically.

**Updated Stage34** [script](scripts/34_BE_Bra_curated_4year_DATM_candidate.py): writes only authorized TBOT/QBOT half-hour indices (not the full 17,520-value variable), guards unscaled float32/64 native storage, validates exact value after cast to actual on-disk dtype, and uses **new `stage34_BE_Bra_curated_MET_QC_v2`** exclusive output. **Updated Stage35** [script](scripts/35_BE_Bra_MET34_independent_AD400_prepare_submit.py) requires the v2 folder, version and four-year per-field count proof, never accepts v1. Audit/prepare do not submit; only `--start` after explicit operator choice can submit the independent direct AD400. The 2002 rain remains original; all edits are labelled EXPERIMENTAL interpolation without source-QC/ERA5 validation.

---
## BE-Bra Stage33 **human review** → Stage34 independent met candidate → Stage35 fresh AD400

User supplied Stage33 all anomaly context, source SHA from actual effective Stage30 BE-Bra data.

**Reviewed decisions:**
- 1996 **12 RH<5%**: many physically implausible paired cold/dry interruptions, e.g. Jul20 19:00 and Aug19 19:00 isolated TBOT drops ≈7–10°C with concurrent QBOT collapse, plus prolonged very dry QBOT at Aug05/Aug09; **modelling proxy**: local bracketing RH>=10 donor interpolation for 12 QBOT rows, plus exactly 2 visually isolated TBOT records Jul20 19:00 and Aug19 19:00. *Native tower-QC / ERA5 donor not independently confirmed*. Some complex 1996 humidity episodes may be scientifically underdetermined; label every modification.
- 1999 **13 RH<1%**: isolated/dropout QBOT to ≈1–5×10^-6 kg/kg between neighboring RH ≈70–98%; interpolate exactly 13 QBOT rows, preserve TBOT.
- 2005-05-26 19:00: isolated TBOT 25.038°C against ≈11.3/11.05°C neighbors and QBOT 0.00969 vs 0.0065/0.00718; replace exactly that T/Q pair with two-neighbor midpoint, preserve other points.
- 2021-11-04 10:00: TBOT 48.06°C and QBOT 0.03321 between ≈10.07 and9.13°C neighbors, and 0.00533/0.00642 QBOT; replace exactly that one T/Q pair.
- 2002-08-24 original **154.5 mm total** is a multihour rainstorm with near 100% RH and smooth T, not an isolated rogue 30-min datum. **Retain original 2002 DATM and precipitation exactly**; not externally rain-gauge certified.

**Science caveat:** Stage34 is an **EXPLORATORY, LOCAL-INTERPOLATED MODEL SENSITIVITY FORCING**, **not** an official source-QC corrected meteorology series. To produce publication-grade forcing, compare flagged times with actual native tower QA/QC plus collocated ERA5/ERA5-L; do not misdescribe interpolation as ERA5 or observation. Independent Stage35 case leaves the original raw data untouched. No modification of the already submitted DK-Sor or FR-FBn jobs.

[Stage34 candidate (4 modified annual NCs / 26 original annual NCs)](scripts/34_BE_Bra_curated_4year_DATM_candidate.py): `--self-test`, `--audit` (read-only); `--build --confirm CREATE_BE_BRA_STAGE34_FOUR_YEAR_EXPLORATORY_MET_OVERLAY` writes a new immutable `stage34_BE_Bra_curated_MET_QC_v1` folder, 4 new annual files, a provenance manifest selecting all 30 years. Pins SHA256 of selected source 1996,1999,2002,2005,2021 and the actual CDEPS stream, verifies EXACT number/position/values of T/Q changes (TBOT4, QBOT27), and all unaffected NetCDF variables/time/rain bitwise-equivalent. Refuses all accidental source changes or second build.

[Stage35 isolated direct AD400 80x5y](scripts/35_BE_Bra_MET34_independent_AD400_prepare_submit.py): `--self-test`, `--prepare --datm-dir .../stage34_BE_Bra_curated_MET_QC_v1 --confirm PREPARE_BE_BRA_STAGE35_INDEPENDENT_MET34_AD400_NO_SUBMIT`, `--audit --datm-dir ...` (READ ONLY), and **only when operator explicitly approves the experimental input** `--start --datm-dir ... --confirm SUBMIT_BE_BRA_STAGE35_CURATED_EXPLORATORY_AD400_ONCE`. Uses proven Stage26 independent create_clone, private AD FATES namelist preview and exact modified Stage34 selected stream, original same-site compiled executable and Stage29 site PFT. No jobs at prepare/audit. The start guard creates exclusive submission-attempt ledger before Slurm; **never retry if stage35 receipt exists, even if a job appears failed/uncertain**.

---

## Stage32 operator output and Stage33 scoped context (26 October)

Stage32 read-only 51-year input scan **completed** on IRIDIS. Exact effective streams: BE-Bra 1996–2025 30 annual files in `datm_11_provisional_dynamic_zbot_v1`, and CH-Lae 2004–2024 21 files in the similarly labelled stream. Both passed the exact 17,520-per-year noleap TIME and 1PT physics inventory. **BE-Bra** `QC_HOLD_FOR_TARGETED_REVIEW`: physical invalid 0; RH<1=14, RH<5=26; 4 jumps >12°C/30min; 38 jumps >8°C/30min; T>45=1; 1 day >100mm; no negative VPD, rain >40mm/30min or spurious 23:00 clustering. Priority: 2021-11-04 10:00 48.06°C/QBOT0.03321 then 10:30 9.13°C, isolated RH0.856% on 1996-08-05 17:30; Jan1999 RH minimum0.026% and 13 RH<1; 2005-05-26 19:00–19:30 25.038°C→11.049°C, one 2002 day with 154.5mm rain. BE-Bra remains **HOLD** for paired source native QC and source-supported candidate replacements, never blind interpolation.

**CH-Lae** `QC_PROVISIONAL_REVIEW`: physical invalid0, RH<5=0, RH>100=0, negative VPD0, >12°C jumps0, >8°C jumps7, rain >40mm/30min0, max annual half-hour rain27.7mm (2023). Could be considered for explicitly experimental proxy-PFT AD400 if source provenance is accepted; **not** a declaration of original-tower met validation.

[Stage33 read-only targeted context](scripts/33_BE_Bra_CH_Lae_targeted_source_context_readonly.py): selected-source SHA + ±2h companion RH/QBOT/T/VPD/precip for all BE-Bra 1996/1999 RH<5, 2005/2021 >12°C jumps and T>45, 2002 daily rain >100mm, plus all CH-Lae >8°C changes. **No input writes, CIME edits or Slurm.** Run after `curl`, `python3 -B -m py_compile`, `--self-test`, then `--check`. Analyze source context before constructing separately versioned humidity- and temperature-repaired annual forcing. Do not reuse Stage31 old case with new forcing without a fresh independent case and provenance manifest.

---

## Stage32: BE-Bra and CH-Lae **selected effective** DATM meteorological QC (26 October)

The operator submitted the DK-Sor and FR-FBn exploratory Stage31 forest-PFT AD400 cases. **Do not resubmit them.** BE-Bra and CH-Lae were held for meteorological review: Stage30 stream manifest listed **30** provisional-named years for BE-Bra (1996–2025), **21** for CH-Lae (2004–2024). These `PROVISIONAL` strings are input provenance labels, *not evidence of invalid physical values*.

[Stage32 read-only QC script](scripts/32_QC_BE_Bra_CH_Lae_effective_DATM_readonly.py) checks all **51 actual source-year selected 1PT annual NetCDFs** referenced by Stage30 independent cases. Requires an exact CaseDocs/RUNDIR DATM stream match, source-year/time axis NOLEAP 17,520 half-hour records, correct selected source, CIME preview receipt. For all 51 years it reports T/Q/PSRF and diagnostic RH/VPD, physically invalid values or missing, RH<1/<5/>100/>110, temperature half-hour jumps >8/>12°C, rain >15/>40mm per half-hour, daily rain >100mm, 23:00–23:59 aggregation fraction, irradiance, winds and extreme temperature. Flagged half-hours include CDEPS time and companion T, Q, P, RH, VPD, rain. No source data repairs, ERA inference, CIME edits, Slurm submissions or user-data modifications.

Run:

```bash
S32="$HOME/Batch02_10_stage32.py"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/32_QC_BE_Bra_CH_Lae_effective_DATM_readonly.py"
curl -fLsS "$RAW" -o "$S32"
python3 -B -m py_compile "$S32"
python3 -B "$S32" --self-test
python3 -B "$S32" --check 2>&1 | tee "$HOME/Batch02_10_stage32_QC.log"
grep -E "STAGE32 SITE_STATUS|STAGE32 RESULTS|SUMMARY BE-Bra|SUMMARY CH-Lae|UNIT_REVIEW_REQUIRED|YEAR_SEAM" "$HOME/Batch02_10_stage32_QC.log"
```

`QC_HOLD_FOR_TARGETED_REVIEW` means numerical critical/outlier flags require investigation; `QC_PROVISIONAL_REVIEW` means no current severe flag found but low-RH, rain spikes or provisional provenance remain; `NUMERIC_SCREEN_CLEAR` means screen did not flag selected coarse criteria, **not** that full source-derived flux meteorology has been source-QC verified. Operators should inspect actual results before authorizing Stage31 direct exploratory AD400 for those sites. Avoid replacing low RH or rain without matching source QC and time metadata. Site PFT residual allocations remain sensitivity assumptions independently.

---

## Stage29–31: four remaining Batch02 forests — scenario surfaces → isolated preview → exploratory AD400

The operator requested using the existing [38-site FINAL FIXNC PFT register](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv) instead of restarting the literature investigation. **That table still labels four forest residuals OPEN**, so this sequence uses named, explicitly *unapproved model proxy/sensitivity* vectors from the [11-option table](data/four_open_PFT_exploratory_closure_sensitivity_20261026.csv), not fabricated complete observations.

| Site | Stage29 exploratory whole-natural-landunit PFT percentage | Unknown fraction treatment |
|---|---|---|
| DK-Sor | DBF80 / ENF10 / DNF10 | ENF+DNF20 observed only as combined amount; assume 10/10 for test |
| FR-FBn | ENF75 / EBF25 | Assume the unknown 25 of tree basal area is holm-oak EBF, upper-bound scenario |
| BE-Bra | ENF55 / DBF45 | Assign the unknown22 to DBF, explicit bound |
| CH-Lae | DBF88 / ENF12 | Assign unreported8 to DBF, explicit bound |

Technical sequence:
1. [Stage29](scripts/29_build_four_open_forest_PFT_sensitivity_surfaces.py): `--self-test`, `--plan` (read-only); `--build --confirm CREATE_FOUR_BATCH02_FOREST_PFT_SCENARIO_SURFACES` creates exactly four independent, manifested NetCDF point surfaces, no case or Slurm changes. NATVEG100%, CROP0%; **original source-grid PCT_SAND/CLAY is inherited and documented as unverified grid input, not site-observed soil**.
2. [Stage30](scripts/30_prepare_four_forest_AD5_proxies_no_slurm.py): `--self-test`, `--check` (read-only), `--prepare --confirm PREPARE_FOUR_BATCH02_FOREST_AD5_PREVIEWS_NO_SLURM` (creates four fresh same-site cloned FIXNC AD startup cases, no Slurm), `--verify` (read-only). Reuses the proven private FATES namelist overlay and explicitly corrects any inherited original CIME point-coordinate mismatch in the new case, then checks actual NUOPC coordinates against the candidate surface. Despite name AD5, prepared case is the first 5-year segment only; no run job yet.
3. [Stage31](scripts/31_submit_four_forest_exploratory_AD400_once.py): `--self-test`, `--audit`, then optionally **explicit one-time exploratory Slurm** `--start --confirm SUBMIT_FOUR_BATCH02_EXPLORATORY_FOREST_AD400_ONCE`. Starts 80×5-year accelerated spinup segments *directly*, with no separately submitted 5-year smoke. Verifies Stage30 source, exact case flags/namelist, stored point geometry, no current matching jobs and no prior submit attempt. A submission receipt is written before submitting; after any uncertain attempt, **never rerun** without investigating the ledger, CIME and Slurm.

**Not a climate QA release.** Stage30 checks the selected original DATM annual files exist, source/year/coordinates/time-loop are coherent; Stage31 does not validate all half-hour meteorology for anomalies. If a site is found to have an unreleased source issue, stop its model submission and validate meteorology first. Model output must be labelled exploratory PFT sensitivity, not an observed-ground-truth stand reconstruction.

---

## 26 October 03:16 UTC: actual Stage25 success, Stage26 prepared, submit preflight bug fixed

Operator IRIDIS6 log: Stage27 self-test passed, but all four Batch02 AD chains are still running/queued; latest archived restart years FI-Hyy **2222**, FR-Hes **2202**, CH-Fru **2335**, IT-MBo **2333** (respective AD400 targets 2397/2397/2405/2403). `audit-ad400` correctly **HOLD 4/4**. Do not stage Normal400 yet.

ES-LJu Stage25 actual audit **PASS 21/21**, then successfully **CREATED 21/21** versioned new annual NetCDF files in:
`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage25_ESLJu_20261026T031624Z_1628022`.
Stage26 self-test, independent case prepare, and read-only audit all **PASS**; case `ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24`, effective new stream SHA256 `d1302407bf5b31e2c16331a4d205a57d97f56b2c09d7375316c80d1b03a63abe`. The first Stage26 `--start` stopped at a **pre-submission Python TypeError**: `subprocess.run(..., at=CASE)` instead of `cwd=CASE`. The failure was **before** a submission receipt, `RESUBMIT=79` change, or `case.submit`. [Stage26 hotfix](scripts/26_ES_LJu_new_Stage24_DATM_AD400_prepare_audit_submit.py) commit [3c5b410](https://github.com/lyanyeung/Non-Competition-CLM-experiment/commit/3c5b4102bfa8adf02a270444637f959f01c5b454) replaces the wrong keyword and adds a regression self-test. Operator should download only the fixed Stage26, run `--self-test`, `--audit --datm-dir <existing Stage25 folder>`, then **one-time** `--start --datm-dir <existing Stage25 folder> --confirm SUBMIT_ES_LJU_STAGE24_DIRECT_AD400_ONCE`. Do not rerun Stage25 build or Stage26 prepare.

---

## 26 October: reported Slurm results, Stage25 hotfix and guarded Normal400

**Operator-provided evidence, not live HPC:** first AD395 continuation run/archive for FI-Hyy (4732398/99), FR-Hes (4732400/01), CH-Fru (4732402/03), and IT-MBo (4732404/05) are all `COMPLETED 0:0`. This is **only the first five-year segment** of each 395-year automatic chain, not proof of AD400. Stage27 [four-site Normal controller](scripts/27_batch02_AD400_to_NORMAL400.py) must first verify **80 AD runs and 80 archives** from original AD5, exhausted RESUBMIT, no queue, complete Y+400 CLM/DATM/CPL archived restarts, and land `spinup_state=2`. It then supports isolated Normal5 hybrid case preparation, one-time Normal5 submission, five-year audit, and one-time Normal395 continuation. This file has been committed to GitHub but is **not yet syntax/self-test/runtime confirmed on IRIDIS**.

- Stage27 `self-test`, `audit-ad400`, and `status` are read-only. For Normal400: `stage-normal --confirm STAGE_BATCH02_NORMAL400_HYBRID_CASES_NO_SLURM` (creates independent cases); `submit-normal5 --confirm SUBMIT_BATCH02_NORMAL5_SMOKES` (Slurm); after Normal5 archive success, `audit-normal5` then `continue-normal395 --confirm CONTINUE_BATCH02_VERIFIED_NORMAL5_BY_395_YEARS`. Select only successful site subsets using `--sites`.
- The new Normal case inherits the verified **same** fixed-biogeography/no-competition site surface, FATES executable and forcing. It copies all three Y+400 restarts with SHA protection and removes explicit AD `spinup_state` before generating unaccelerated Normal namelists.
- IT-Noe initial `4733521` **FAILED 1:0** after 19s; `4733522` archive is `DependencyNeverSatisfied`. Do **not** rerun Stage15 `--start`; use [Stage28 read-only failure diagnostic](scripts/28_diagnose_IT_Noe_failed_AD400_readonly.py) and inspect the actual CESM/Slurm traceback first.
- ES-LJu Stage25 `--audit` stopped before writes with `TypeError: unsupported operand type(s) for +: 'int' and 'str'` at original NetCDF comparison label. [Stage25 hotfix](scripts/25_ES_LJu_Stage24_to_new_21year_DATM_readonly_audit_and_build.py) uses `f"{year} ORIGINAL {key}"` / `f"{year} KEEP {key}"` instead; commit [8cd1b3d](https://github.com/lyanyeung/Non-Competition-CLM-experiment/commit/8cd1b3d76f396c1c7ad23655e7446a2dc824c888). No source NetCDF was changed by the failed audit; download the corrected script and re-run Stage25 audit/build, then Stage26 separately.

**Authoritative full-cohort PFT register**: [ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv). Use its recorded Batch02 inputs and explicit model-proxy labels for the six sites with selected model compositions; preserve their IN USE versus PROPOSED distinction. Its other Batch02 forest sites are still explicitly **OPEN**: DK-Sor (DBF80 / ENF+DNF20 unsplit), FR-FBn (ENF75 / EBF up to25 unverified), BE-Bra (ENF55 / DBF23 / unclassified22), CH-Lae (DBF80 / ENF12 / unclassified8). This register is comprehensive as a **scientific evidence catalogue**, not as four closed 100%-PFT numeric input vectors. Any provisional allocation of the unknown shares must be labelled a sensitivity *scenario* and must never be presented as an observed measurement. Do not silently inject unresolved entries into a 100%-sum land-surface file.

To avoid repeating the literature search, [11 explicitly provisional PFT closure/sensitivity vectors](data/four_open_PFT_exploratory_closure_sensitivity_20261026.csv) are published for these four sites. These vectors have exactly 100% NATPFT arithmetic and identify their unknown-share assumptions, **but are NOT observation-verified or automatically approved for model submission**. Use the original table as observed evidence and these clearly labelled alternative inputs only for exploratory sensitivity case construction.

---


## New ES-LJu Stage24 to AD400 runbook (26 October 2026)

**Newer than the historical October 25 ES-LJu HOLD narrative below.** Operator-approved meteorological candidate was produced successfully in Stage24, and the operator explicitly authorized **retaining** the original 2013-12-25 QC0 tower extreme rain despite disagreement in ERA5 magnitude/timing; the old SCIENCE_HOLD label for that specific rain event is therefore superseded as an operator decision, not independently ERA-validated. The operator also approved the 2016-12-06 44.724 mm daily total redistribution according to same-day ERA5, retention of 28 low-rain ERA-zero days (25.140 mm total), and extended 2006/2019/2023 temperature repairs. Stage24 remains an **isolated CSV**, not a currently selected DATM stream. Very low RH below 5% is not automatically a bad observation: 293 of 412 residual RH-low records had original TA/VPD both QC0, and remaining QC/physics should be explicitly examined before publication-grade signoff.

**Actual IRIDIS operator Stage23/24 logs (26 October):** 3 new temperature boundary scopes (27+9+8=44 half-hours) BOUNDED, 0 unresolved; Stage24 CSV provenance and daily rainfall mass conservation PASS (2016 tower daily 44.724 -> 44.724 mm, companion ERA5 daily 1.730 mm); **28 low-rain days preserved**; no active CIME, DATM or Slurm modifications.

**New mandatory staged path for direct ES-LJu AD400, no AD5 smoke:**
1. [Stage25](scripts/25_ES_LJu_Stage24_to_new_21year_DATM_readonly_audit_and_build.py): `--self-test`, `--audit` then one-time `--build --out NEW_UNIQUE_DIR --confirm BUILD_ES_LJU_STAGE24_DATM_21Y`. Creates **21 isolated SHA-checked annual NOLEAP 1PT NetCDF**, replacing exactly `TBOT`, `QBOT` and `PRECTmms`, preserving source `ZBOT` and all other variables. Original source NetCDF is verified and not changed.
2. [Stage26](scripts/26_ES_LJu_new_Stage24_DATM_AD400_prepare_audit_submit.py): `--self-test`, `--prepare --datm-dir STAGE25_DIR --confirm PREPARE_ES_LJU_STAGE24_INDEPENDENT_AD400_NO_SUBMIT`, `--audit --datm-dir STAGE25_DIR`, then `--start --datm-dir STAGE25_DIR --confirm SUBMIT_ES_LJU_STAGE24_DIRECT_AD400_ONCE`. This clones a **new independent case** named `ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24` using the already-verified Stage13 idealized PFT surface and original executable; 80×5-year AD segments; skip-preview namelists; preserves all other jobs. Preparation/submit is one-time receipt protected. **Scripts were published but IRIDIS Stage25/26 execution is not yet evidenced.** If any audit/preparation fails, stop rather than submit with old forcing.

**Batch02 10-site status based on most recent confirmed operator history, not live telemetry:** FI-Hyy, FR-Hes, CH-Fru, IT-MBo each AD5 COMPLETE and AD395 previously SUBMITTED (job IDs 4732398/400/402/404, archive companions); IT-Noe exploratory direct AD400 SUBMITTED run job 4733521, archive 4733522 (no finished 400-year restart evidence); ES-LJu Stage24 CSV COMPLETE and new Stage25/26 NetCDF/model **not yet run**; DK-Sor, FR-FBn, BE-Bra, CH-Lae blocked by unresolved observational PFT partition. **Do not double-submit ongoing jobs, do not claim full AD400 completion until final coordinated restart is verified.**

---

**Updated 25 October 2026.** The operator requested the next ten sites after the previous Batch01 run. This example activates the ten sites already reserved in the repository; it does not reuse or change any Batch01 case. These are European/ICOS-linked tower sites; the exact network membership is preserved in the [site register](../../data/batch02_10_sites.csv), rather than claiming that every site has identical ICOS status.

## Stage15 actual IT-Noe Slurm 4733521 and ES-LJu Stage16 manual time-of-rain audit (25 October 2026)

**ACTUAL OPERATOR RESULT (Slurm, not model completion):** IT-Noe FIXNC BARE34 / shrub66 research-trial AD400 submitted successfully through Stage15. One-time run Job **4733521**, archive Job **4733522**. The operator's CIME result shows **`skip_preview_persisted True`**, `STACK (307200000,-1)`, `Check case OK`, `STOP_N=5, RESUBMIT=79`, with 80 automatic 5-year segments for requested 400 years (2004→2404). In observed snapshot `run.IT-N...` **PD(Priority)** and archive **PD(Dependency)**. This only establishes **job submission**; zero completed years and no verified restart as of snapshot. **Never repeat Stage15 `--start`**; it has a one-time submitted-attempt ledger. IT-Noe 22-year QC-v3 source and Juniperus-to-broadleaf-shrub FATES science limitations remain recorded independently.

**Now prioritise manual review of ES-LJu, not an AD400 submission:** actual Stage14 on 21 PROVISIONAL 2004–2024 original-selected annual DATM files measured:
- Annual rain wholly concentrated in the **23:00–23:59 model DATM hour** for **2005, 2006, 2007, 2008** (up to several hundred mm in this one hour); cannot interpret as realistic half-hour rainfall storm forcing without original source accumulation/time base. Examine *23:00 vs 23:30* and daily totals, not just output aggregate.
- 2023 neighbouring DATM half-hours `HH=13953` and `13954` on model NOLEAP **Oct 18, 16:30 and 17:00**: **4.040°C→17.823°C** (13.783°C rise in 30min). An earlier raw FLUXNET2023 severe near-−40°C TA_F block had a paired-ERA temperature/VPD repair trial; those are separate sources and this smaller jump is not automatically approved.
- Across 21 years: **460** approximate RH (computed from input TBOT/QBOT/PSRF) <5%, **6** 30-min TBOT jumps >12°C, **9** intense rain half-hours >40mm. All 21 years `INVALID_PHYSICAL=0` under coarse numeric bounds, which does not address rainfall provenance.
- **Important:** earlier 13-site Stage28 documented rain at 23:00 and explicitly forbade redistribution without source-time/accumulation metadata. Do **NOT** retime, smooth or substitute values automatically; preserve original QC and source.

**[NEW Stage16 ES-LJu source-aware manual meteorology review tool](scripts/16_ES_LJu_manual_meteorology_review_readonly.py)** generates only a **new versioned independent review directory** containing:
- `01` annual actual DATM rainfall by hour, 23:00/23:30 split, RH, jumps and extreme counts;
- `02` every day 2005–2008: daily original DATM precipitation vs 23h and outside 23h;
- `03` **all wet halfhours 2005–2008** with noleap DATM timestamp and neighbour context;
- `04` all >40mm/30min extreme precip events (not data edits);
- `05` every >12°C/30min change's +/-6-hour temperature/humidity context, including the 2023 anomaly;
- `06–07` all RH<5 half-hour records and contiguous low-humidity episodes;
- `08` numerical equality and independent SHA provenance of **the Stage28 selected meteorology CSV** vs each active 21 DATM annual NetCDF (Stage29b pipeline); if this passes, rain clustering arose **at or before Stage28 selection** rather than in DATM conversion, not necessarily in original tower observations.
- Optional `--raw-fluxmet /path/to/EXTRACTED_FLUXMET_HH.csv`: independently summarises the **original** `P_F`, P_F_QC source-time hourly rain distribution by year into `09`. Original FLUXNET timestamps need timezone and interval verification before joining to UTC/no-leap DATM events. NO original dataset is committed to GitHub.

Command skeleton:
```bash
python3 -B ~/Batch02_10_stage16.py --self-test
python3 -B ~/Batch02_10_stage16.py --check
python3 -B ~/Batch02_10_stage16.py --report --out /iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage16_ES_LJu_manual_review_v1
```
The strict read-only `--check` produces concise annual/year-priority summaries but no files; `--report` only creates a fresh directory and CSV/JSON/README, never changes source forcing, Stage13 CIME, Slurm or other case. If output path exists, it fails closed; **do not delete an old result to rerun**. A successful report does not scientifically release ES-LJu and will explicitly say `MODEL_SUBMISSION_APPROVAL=NO`. Await actual operator-generated review tables and source metadata before deciding physically meaningful precipitation redistribution or eligible AD400.

---

## Stage14 actual 43y forcing screen; Stage15 conditional direct exploratory AD400 (25 Oct 2026)

**Actual user-provided Stage14 output (`Batch02_Stage14_DATM_QC.log`):**
- **IT-Noe**: active CDEPS 22 annual **2004–2025** files are specifically `datm_11_IT-Noe_QC_v3_RHcap_20261021_230447` (not an older uncertain branch); selected CDEPS sha256 `e095da5c749c57a53bb2ea49a267a0b8635daafe0fc68188acbde1210bbc949d`. All years are NOLEAP at 30min; variables physically bounded under Stage14 rules. Aggregate `invalid=0, jumps (>12°C/30min)=0, rain_gt40 (>40mm/30min)=0, rh_gt100=0, rh_lt5=0`. Source RH diagnostic is NOT the model-diagnosed 2m RH, so historical `HumanIndexMod.F90` negative-RH crashes remain a numerical risk; 208 previous 2004–2025 scientific review episodes and Juniperus conifer shrub represented via evergreen *broadleaf* FATES trait group remain proxies. **NUMERIC PASS**, not scientific validation.
- **ES-LJu**: active CDEPS 21 annual **2004–2024** `*_PROVISIONAL.nc` files, sha256 `92217de7eb708d46cec03945061e0b7c2021c312a08e2e8f13ad18b11c884bab`. Aggregate `invalid=0, rh_lt5=460, jumps (>12°C/30min)=6, rain_gt40 (>40 mm/30min)=9`. **2005, 2006, 2007, 2008 precipitation YEAR-TOTAL = 23:00-23:59 sum**, strongly suggesting hourly/daily accumulation timestamp concentration. This is **not scientifically released for automatic 400-year replay** until time-interval/accumulation metadata reviewed. In 2023 year, 30-min TBOT step near NOLEAP DOY 291, 16:30–17:00 changes approximately 4.04°C→17.823°C (13.783°C in 30 min); independent original tower QC and v7 ERA reconciliation needed. Do NOT blanket retime rainfall, clip RH or reanalysis-replace all questionable records.
- Stage14 `STAGE14 MODEL_SUBMISSION_APPROVAL=NO` means no model or scientific source officially released; numeric thresholds alone do not certify published flux simulation validity.

**User explicitly requested no independent AD5 smoke, instead a full AD400 run.** Technically CIME AD400 can be run by 80 automatic 5yr segments (`STOP_N=REST_N=5`, `RESUBMIT=79`, `RESUBMIT_SETS_CONTINUE_RUN=TRUE`) from the existing independent Stage13 AD5 **STARTUP** case, with no extra 5-year test, but every five years still writes mandatory restarts/archives. This permits multi-job automatic continuation while retaining checkpoints if the model crashes. The old Stage13 case name ends `_AD5` because it was prepared for 5-year chunks, not because there is now a separate smoke run.

**[Stage15 direct IT-Noe 400yr conditional one-time Slurm submission script](scripts/15_IT_Noe_direct_AD400_conditional_submit.py)**:
- `--self-test`: arithmetic/name sanity, no I/O; `--audit`: **read-only** strict Stage13 receipt, immutable Stage12 site surface hash, original FATES spinup flags + CIME lock, actual 1PT NUOPC coupled point, actual CDEPS XML full SHA and selected QC v3 RHcap 22 files, Stage14 complete original numeric log and zero risk-screen summary. It never touches the four existing AD395 sites or ES-LJu.
- `--start --confirm SUBMIT_IT_NOE_EXPLORATORY_DIRECT_AD400_ONCE`: **REAL** once-only Slurm submission, after repeated audit, raises inherited submit-process stack as needed, writes an exclusive receipt **before** modifying the one independent IT-Noe Stage13 case's `RESUBMIT=0→79`, and invokes `case.submit --skip-preview-namelist` to preserve the validated private-AD FATES `spinup_state=2` namelist. This is explicitly a research-only **unapproved shrub/meterological-proxy model run**; the historical source case, global FATES params, original forcing/surface are untouched. DO NOT resubmit on uncertain status or rerun Stage13 `--prepare`.
- If the first segment 2004–2009 fails (negative model-computed RH or FATES/PFT issues), remaining model segments do NOT constitute automatic scientific success. Archive/Slurm must be monitored; final 2404 restart and pool convergence independently verified. No user-supplied Stage15 execution result yet, so no submitted/completed jobs are claimed.

**ES-LJu stays HOLD at Stage13 verified preview.** Its 2005–2008 rain-hour grouping and 2023 temperature edge events need source investigation before launching AD400; no automatic repair, no forced 400-year experiment, and no misrepresentation of model-input science release. `PCT_NAT_PFT` candidates and 21 original annual PROVISIONAL NetCDF remain archived unchanged.

---

## Stage13 runtime-config verification PASS 2/2; Stage14 active DATM numeric/source review (25 October 2026)

**Latest actual operator-supplied IRIDIS6 Stage13 results:**
```text
SOURCE PASS | SYNTAX PASS
STAGE13 SELF-TEST PASS: exact sites, longitude wrap and stable JSON-list PTS receipts; NO WRITES
FATES BATCH02 AD PRIVATE NAMELIST OVERLAY PASS
EFFECTIVE COUPLER PASS IT-Noe CaseDocs surface vs scol (40.606176, 8.151694)
EFFECTIVE COUPLER PASS IT-Noe run surface vs scol (40.606176, 8.151694)
EFFECTIVE COUPLER PASS ES-LJu CaseDocs surface vs scol (36.926594, 357.247885)
EFFECTIVE COUPLER PASS ES-LJu run surface vs scol (36.926594, 357.247885)
STAGE13 VERIFIED TWO BARE/SHRUB AD5 CASES 2/2; NO SLURM
```
The original tuple-vs-list comparison error has been fixed, and *both independently cloned AD5 startup cases* are now technically verified. No Stage13 rerun/preparation, deletions or new surface edits. **No Slurm jobs yet.**

**Stage14 [read-only selected 43-year DATM climate QC](scripts/14_readonly_active_IT_Noe_ES_LJu_43year_DATM_science_QC.py)** now independently checks effective `CaseDocs` and `RUNDIR` `datm.streams.xml` and EXACT 22+21 selected annual NetCDF inputs (rather than selecting arbitrary newest trials). It asserts all files exist, 17,520 noleap half-hour records each, proper year/file identity, meteorological 1PT variables, monotonic 1800s time axis, basic physical bounds; calculates diagnostic approximate RH (QBOT/TBOT/PSRF), half-hour temperature-jump counts and strong rainfall >40 mm/30min. Prints detailed scientific-review indices for the **IT-Noe 2010** and **ES-LJu 2023** years, and ES-LJu apparent 23:00 precipitation concentration. These are screens, not automatic corrections, not observed 2-m RH computed by CLM, and not scientific approval.

**Provenance science gates remain open even if Stage14 numeric QC is clean:**
- [IT-Noe historical RH-abort and QC v2/v3 investigation](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/diagnostics/spinup_failures/IT-Noe/README.md): original CLM diagnosed negative 2-m RH; 208 review episodes in 2004–2025; separately versioned QC v3 candidate `datm_11_IT-Noe_QC_v3_RHcap_20261021_230447` numerically validated as research trial but unapproved. Current Stage13 `IT-Noe_ERA5_ABW_BRANCH2009` DATM files may still reference an older source. *Do not infer v3 use from case label or v3 availability*. FATES host9 is a broadleaf evergreen extratropical shrub proxy for local Juniperus conifer shrub, not confirmed trait equivalence.
- [ES-LJu 13-site forcing method and risks](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/docs/MET_STAGE20_28_METHOD_AND_OPEN_ISSUES.md): all **21 actual source annual NetCDF names are PROVISIONAL** (reported Stage13). The 2023 anomalous TA/VPD record/paired-repair lineage and precipitation clustering at 23:00 have outstanding source-time/accumulation interpretation. The retained 20% evergreen shrub is an explicit proxy for an unclassified vegetation remainder.
- Science and technical gates are separate. Stage14 reports `MODEL_SUBMISSION_APPROVAL=NO` by design, even if basic meteorological units/ranges pass. After review, create a distinct, explicit operator-authorized AD5 one-time submission gate, using CIME `case.submit --skip-preview-namelist`. Do not silently bypass science holds or submit either of the two Stage13 cases now.

Run on IRIDIS: download exact [Stage14 script](scripts/14_readonly_active_IT_Noe_ES_LJu_43year_DATM_science_QC.py) via commit-pinned `raw.githubusercontent.com`, then `python3 -B Stage14.py --self-test` and `python3 -B Stage14.py --check`. Pure read-only; user can capture results with `tee`. Does not run, cancel or resubmit other existing Batch02 AD395 tasks.

---

## Stage13 operator-created IT-Noe and ES-LJu AD5 previews; JSON receipt verification fixed (25 October 2026)

**User-supplied actual Stage13 IRIDIS6 logs:**
- Source-pin, AST and pure self-test PASS. The existing private FATES AD build-namelist overlay PASS.
- `--check`: **2/2 source preflight PASS**, no filesystem/model changes. IT-Noe initial cycle 2004, CDEPS 2004–2025, 0 provisional-named years; ES-LJu initial cycle 2004, CDEPS 2004–2024, all **21 PROVISIONAL**-named years. CO2 fixed **376.95 ppm** at both sites. IT-Noe still has branch meteorology/Juniperus shrub proxy science HOLD; ES-LJu has provisional-year, 19.8% unclassified vegetation and shrub-trait science HOLD.
- `--prepare` **actually succeeded for BOTH new independent AD5 CIME cases**, **without submitting any Slurm**:
  - `IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5`: `CaseDocs` AND `RUNDIR` effective coupler `scol_lat/scol_lon=(40.606176,8.151694)`, same as Stage12 surface. `STAGE13 CASE PREVIEW PASS IT-Noe NO SLURM`.
  - `ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5`: `CaseDocs` AND `RUNDIR` coupler `(36.926594,357.247885)`, same as Stage12 surface. `STAGE13 CASE PREVIEW PASS ES-LJu NO SLURM`.
  - `STAGE13 TWO BARE/SHRUB AD5 PREVIEWS CREATED`. Attempts stored as `PREVIEW_VERIFIED_NOT_SUBMITTED`.
- Immediate original `--verify` had a **FALSE POSITIVE** at `IT-Noe verified source state changed`. Diagnosis was purely **Python tuple-vs-list JSON representation**: `config()` returned Python tuple `point=z["point"]` while JSON persisted it as a list; `(lat,lon) != [lat,lon]` although physical values are identical. All actual effective CIME checks passed before false mismatch.
- **Fixed script Git commit `b8a16bf40d57030d6f14e580af1aef777c3ebf85`** at [Stage13 code](scripts/13_prepare_IT_Noe_ES_LJu_AD5_preview_no_slurm.py) normalizes `config()` output to `"point":list(z["point"])`, adds JSON round-trip self-test and mismatch detail if other fields differ. **No model nor JSON attempt receipt must be edited**. Operator must replace local Stage13 script and run ONLY `--self-test` and `--verify`; no `--prepare` repeat (cases already exist), no model submission.
- **Stage13 verified is a CIME/PTS technical preview only**, NOT a science QC release nor successful 5yr simulation. Following user approval, prepare a separate versioned submit gate only after checking IT-Noe corrected source branch and ES-LJu PROVISIONAL met integrity, site stand/shrub proxy assumptions. Batch02 four ongoing AD395 sites remain unchanged.

---
## Stage12 operator-confirmed two bare/shrub surfaces built; Stage13 independent AD5 CIME preview

**Actual operator-reported Stage11/Stage12 IRIDIS6 logs, 25 Oct 2026:**
- Stage11 six-source `STAGE11 AUDIT COMPLETE 6/6; NO FILE WRITES OR SLURM`. Four forest species/residual partitions remain science OPEN (DK-Sor, FR-FBn, BE-Bra, CH-Lae).
- Stage12 plan verified **IT-Noe original site point `(40.606176,8.151694)` and ES-LJu point `(36.926594,357.247885)`**, source CIME PTS/surface agreement, shared FATES host9 extra-tropical evergreen shrub and host13 cool C3 grass mapping, original grid-soil retention.
- Stage12 generated **two NetCDF-only independent versioned candidate surface files**, and reported `STAGE12 TWO BATCH02 BARE/SHRUB SURFACE CANDIDATES CREATED, NO SLURM`:
  - `IT-Noe` `stage12_remaining6_bare_shrub_candidates_v1/IT-Noe/surfdata_IT-Noe_B02_BARESHRUB_PFT_proxy_v1.nc` SHA256 **`9158bdc492bf09c530193eb2480eab0b72978194314a0c3ee59d1749fc82ed7a`**: `PCT_NAT_PFT[0]=34,[9]=66`; scientific case retains ERA5-ABW-2009 source provenance and evergreen *broadleaf* shrub proxy caveat for Juniperus.
  - `ES-LJu` `stage12_remaining6_bare_shrub_candidates_v1/ES-LJu/surfdata_ES-LJu_B02_BARESHRUB_PFT_proxy_v1.nc` SHA256 **`d44083a1eef069f6c74d389667f8a82802a93c5085665c712245470221e18762`**: `PCT_NAT_PFT[0]=49,[13]=31,[9]=20`; source CDEPS annual forcing `2004–2024` is tagged `PROVISIONAL` and its 19.8% unclassified vegetation proxy remains an explicit assumption.
- The source surface for ES-LJu is not a natural-land-only point (it reports NATVEG 71.461421%, CROP28.538579%). Stage12 *deliberately* produced NATVEG100/CROP0 as a documented **idealized EC-tower representation**; preserve the 49% bare INSIDE the conditional natural PFT fraction and do **not** claim this matches source gridded cropland landunit percentages.
- **DO NOT rerun Stage12 `--build`**; its create-only candidates now exist. Neither old source case, original forcing data, old surfdata, nor existing Batch02 AD395 jobs were modified by Stage12.

**NEW [Stage13](scripts/13_prepare_IT_Noe_ES_LJu_AD5_preview_no_slurm.py):** strictly separate AD5 CIME preparation using the *same-site* original case for each tower (`IT-Noe_ERA5_ABW_BRANCH2009`, `ES-LJu_FATES_SPINUP1000_S30SHARED`), no other-site case cloning. Its `--check` reads only the two Stage12 exact source SHA receipts, original CIME and site-specific DATM source years, original FATES parameter map SHA and private Batch02 AD FATES namelist overlay. `--prepare --confirm PREPARE_TWO_BATCH02_BARE_SHRUB_AD5_NO_SUBMISSION` creates two new independent CIME AD5 preview cases using `create_clone --keepexe`, 5yr `STOP_N=5, RESUBMIT=0, RUN_TYPE=startup, spinup_state=2`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, original site met loop/CO2, and explicitly sets `PTS_LAT/LON` from the new surface. It tests actual `CaseDocs/nuopc.runconfig` **AND** `RUNDIR/nuopc.runconfig` `scol_lat/lon` against original station surface within 0.0001°, protects CIME env_case lock after private FATES AD preview, checks unchanged DATM source stream and original compiled binary. No `case.submit` call is made by `--prepare`; **no Slurm jobs**. `--verify` rechecks both new case directories READ-ONLY. One-shot prepare receipts refuse duplicates/partial retries.

**New intended case names:** `IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5` and `ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5`.

**Crucial scientific release status**: preparing valid CIME namelists does **not** resolve IT-Noe repaired ERA5 branch meteorology/Juniperus conifer shrub mapping or ES-LJu provisional met provenance and mixed shrub phenology. Maintain the scientific HOLD before actual AD5 Slurm submission; only after those input uncertainties are explicitly assessed should these two 5yr cases be considered for real model runs. Four remaining forests still have residual PFT evidence OPEN; do not invent 100% vectors.

---
## Operator-confirmed Stage10 AD395 four jobs submitted; Stage11/12 remaining Batch02 six preparation

**ACTUAL IRIDIS6 operator output 25 October 2026:** Stage10 AD5 and archive/restart `BATCH02 AUDIT PASS 4/4` with `spinup_state=2`; four remaining AD395 continuations **submitted 4/4**, not yet model-completed. Run/archive Slurm IDs:
- FI-Hyy **4732398 / 4732399**, from restart 2002, target 2397.
- FR-Hes **4732400 / 4732401**, from restart 2002, target 2397.
- CH-Fru **4732402 / 4732403**, from restart 2010, target 2405.
- IT-MBo **4732404 / 4732405**, from restart 2008, target 2403.

Observed `squeue` snapshot showed these four run jobs `PD (Priority)`, archives `PD (Dependency)`. Do **not** rerun Stage10 `continue-395`, do not call the four completed AD5s unfinished, and do not start Normal400 until the final AD400 checkpoint is actually verified.

**Next six sites are the six within this SAME Batch02 cohort**, not the stand-alone not-assigned ICOS six: **DK-Sor, FR-FBn, BE-Bra, IT-Noe, CH-Lae, ES-LJu**. Their evidence from the current authoritative 38-site FIXNC PFT table has **four OPEN unresolved forest partitions** (DK-Sor, FR-FBn, BE-Bra, CH-Lae) and **two scientifically labelled proxy candidates** for bare/shrub vegetation (IT-Noe, ES-LJu). Never make unresolved forest residual grass or bare. See [Stage10 result and full six-site science/machine gates](docs/stage10_success_and_remaining6_stage11_stage12_20261025.md).

**New scripts (no Slurm):**
- [Stage11 six remaining sites input audit](scripts/11_audit_remaining_six_PFT_and_source_inputs_readonly.py): source-pinned official 38-site table, six original exact case names, site-surface PTS point coordinates (guard from AmeriFlux CA-TP4 failure), original landunits/soil/compiled FATES and data streams; strictly read-only.
- [Stage12 two versioned bare/shrub model-candidate surface files](scripts/12_build_IT_Noe_ES_LJu_bare_shrub_candidates_only.py): `--plan` read-only then optional `--build --confirm CREATE_TWO_BATCH02_BARE_SHRUB_SURFACE_PROXIES`, **IT-Noe bare34/shrub66** and **ES-LJu bare49/C3-grass31/evergreen-shrub20**, preserve original soil texture and original inputs; no CIME cases, no model submission. Scientific percentage-denominator and shrub-trait caveats retained.

Other four sites do not yet have an evidence-complete 15-PFT host vector and **must not** be copied into an unqualified surface builder. Preparation is independent from the running/pending four AD395 continuations.

---
## Stage10 — AD5 to AD395 continuation (conditional on HPC audit)

The exact Stage09 active run/archive IDs are FI-Hyy `4728292/4728293`,
FR-Hes `4728294/4728295`, CH-Fru `4728296/4728297`, and
IT-MBo `4728298/4728299`. **Submission is not evidence of completion.**
The operator must first verify Slurm run + archive success, archived CLM/DATM/CPL
restarts at the site's Y+5 checkpoint, and CLM `spinup_state=2`.

The new [Stage10 controller](scripts/10_continue_four_verified_AD395.py)
is adapted from the proven Batch01 Stage13 method. It checks Stage09 receipts,
the exact eight jobs, the archived checkpoint and pointers, FIXNC namelists,
and duplicate-submission protection. Its `audit` action is read-only.
It operates only on the four independent Batch02 cases; the six other sites
are not touched. Do not change candidate PFT allocations without starting
a separate versioned experiment.

```bash
conda activate clm_fates_env
SCRIPT="$HOME/Batch02_10_stage10.py"
curl -fLsS --retry 3 \
  "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/367a3131e1dc87c25fa933458faf51905a0351c2/examples/Batch02_10/scripts/10_continue_four_verified_AD395.py" \
  -o "$SCRIPT" || exit 1
python3 -B -m py_compile "$SCRIPT" || exit 1
python3 -B "$SCRIPT" audit
```

**Only if the audit says `BATCH02 AUDIT PASS: 4/4`,** and the
operator accepts the documented candidate surface assumptions, run the
one-time submission (never repeat after an uncertain result):

```bash
python3 -B "$HOME/Batch02_10_stage10.py" continue-395 \
  --confirm CONTINUE_BATCH02_FOUR_VERIFIED_AD5_BY_395_YEARS
```

The CIME handoff preserves stage09 input/compiled executable, stages the
three matching Y+5 restarts, sets `CONTINUE_RUN=TRUE` and `RESUBMIT=78`,
and submits **79 five-year AD segments**, 395 years total. It retains
a per-site submission ledger/attempt and does not submit Normal400.
Expected AD400 endpoint years: FI-Hyy 2397, FR-Hes 2397,
CH-Fru 2405, IT-MBo 2403.

Stage10 code is published and reviewed, but it has **not** been run on IRIDIS
from this chat. If `audit` blocks, inspect the exact failure before trying
to continue; do not bypass a missing restart or failed archive.

**Stage09 resubmission reported successful 4/4:** FI-Hyy4728292/93, FR-Hes4728294/95, CH-Fru4728296/97 and IT-MBo4728298/99 (run/archive). The actual submit process on login6001 had an unlimited stack. These receipts establish submission; new run completion and archived AD5 checkpoints still need verification. [New IDs, PFT/bare-ground review and source evidence](docs/stage09_resubmitted_PFT_bare_ground_review_20261025.md).

## Stage09 status: monitor AD5 and review area assumptions

```bash
python3 -B "$HOME/Batch02_10_stage09.py" status
```

The four candidate PFT allocations match the updated 38-site register and the operator-verified active parameter map. All four currently have **bare0**: this is an explicit dense-point assumption, not observed zero bare area. CH-Fru's up-to90% cover statement does not establish bare10. ES-LJu's measured non-vegetated49.1% must be retained in a future candidate; its rounded49/31/20 split and IT-Noe's34/66 midpoint are proposals with assumptions. The six other sites still have no automatic surface choice. Review acceptance of these area assumptions together with AD5 outputs and checkpoints before AD395.

Do not rerun Stage09 resubmit or the superseded Stage08 route. Model inputs and active cases were not altered by this documentation review.

## Stage09: completed four-site resubmission (historical command)

The following is the completed submission command, retained for reproducibility:

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage09.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/6ef949393e03e7c09b9be720d89094a268900de6/examples/Batch02_10/scripts/09_resubmit_four_AD5_with_Batch03_stack_guard.py" \
    -o "$SCRIPT"
  echo "d0730ccca1c7728f7b82285fe9da4f120b3dc06c189341f1f015b73151eac5fc  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" resubmit
)
```

Reported result: `STAGE09 RESUBMIT SUMMARY submitted= 4 uncertain= []`. This validated all four failed cases, preserves inputs/executable/MPI command, raises only a low current submitting-process stack, cancels only their verified blocked old archives and submits only AD5 with RESUBMIT0. It does not run a probe or alter Batch03 jobs. Use `python3 -B "$HOME/Batch02_10_stage09.py" status` for the new IDs. [Source match, operator evidence and recovery record](docs/stage09_Batch03_success_method_for_Batch02_20261025.md).

## Stage08: superseded single-site wrapper proposal (do not run the command below)

This command verifies and cancels only FI-Hyy's blocked old archive4728103, adds a measured256MiB task-side stack wrapper to that independent case, and submits one new cold-start AD5. It preserves meshes, scientific inputs and the executable. Other three sites are untouched.

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage08.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/02b39012e7b6f77f55bd51a4c87510b45f1febd1/examples/Batch02_10/scripts/08_retry_FI_Hyy_AD5_stack256_pilot.py" \
    -o "$SCRIPT"
  echo "72d955c9ca5c5682070e570ea546f9375f597c2c233311f29a6c51252e611d70  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" retry
)
```

Then use `python3 -B "$HOME/Batch02_10_stage08.py" status` for this pilot's actual new IDs and task stack output. [Evidence, safeguards and expected result](docs/stage08_FI_Hyy_stack256_AD5_pilot_20261025.md). Do not repeat initial Stage05 submission or submit AD395.

## Stage07: completed targeted inspection (historical command)

The supplied Stage06 output localizes all four failures to ESMF mesh-center-coordinate reading. Inspect the actual mesh declarations/headers and stack context before changing a case or retrying:

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage07.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/6d9f9843d434f07b60538063c0750922eceb1410/examples/Batch02_10/scripts/07_inspect_ESMF_mesh_stack_readonly.py" \
    -o "$SCRIPT"
  echo "42fcd8447b71db484cd984848bf5b74f10c721af0fd45a9677f8f92542457028  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" inspect
)
```

[Failure evidence, upstream source comparison and inspection limits](docs/stage07_ESMF_mesh_SIGSEGV_targeted_inspection_20261025.md). This writes only a new HOME report and performs no model or scheduler changes.

## Stage06: completed general failure diagnosis (historical command)

The failed run jobs are FI-Hyy4728102, FR-Hes4728104, CH-Fru4728106 and IT-MBo4728108. The paired archive jobs4728103/05/07/09 are pending. Run the standalone read-only diagnostic:

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage06.py"

  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/9aa24d9cb33bd21bb8e2a515c45e10f32c103174/examples/Batch02_10/scripts/06_diagnose_four_failed_AD5_readonly.py" \
    -o "$SCRIPT"

  echo "2a46fdeb0f8ea830fa8aeaf4f0c1690ada72aca6c0514f598f839f484d84b3c1  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" diagnose
)
```

Paste the printed per-site `FILE` error contexts; fuller logs are retained at the printed `REPORT_TEXT` and `REPORT_JSON` paths. No jobs or cases are modified. [Failure record and diagnostic scope](docs/stage06_four_AD5_failed_readonly_diagnosis_20261025.md).

## Stage05: completed submission, followed by failed model runs (historical command)

Four actual case previews passed. Submit only the first five AD years for FI-Hyy, FR-Hes, CH-Fru and IT-MBo:

```bash
conda activate clm_fates_env
(
  set -euo pipefail
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/a325fea1b6d32b7b5f6dfba3f85c082260337913/examples/Batch02_10/scripts/05_download_and_submit_four_AD5.sh" \
    -o "$HOME/Batch02_10_stage05.sh"
  bash "$HOME/Batch02_10_stage05.sh" submit
)
```

Expected: `AD5_SUBMIT_SUMMARY submitted= 4 failed= []`, with two actual job IDs per site. Stage05 rechecks current prepared-case inputs, retains `RESUBMIT=0` and persists skip-preview options. Do not rerun submission after an uncertain result. Use `bash "$HOME/Batch02_10_stage05.sh" status` to inspect retained IDs and Slurm status. [Runtime result and full Stage05 record](docs/stage05_four_AD5_prepared_and_initial_submission_20261025.md).

## Stage04: completed AD5 case preparation (historical command)

**25 October parser correction:** the first prepare attempt stopped in FI-Hyy source-stream preflight before any case or attempt marker was created. Use the updated pinned command below. Stage04 v2 selects the named tower stream across XML namespaces/root layouts and ancillary streams, accepts the documented FI-Hyy/IT-MBo `_PROVISIONAL.nc` filenames, and retains strict years/order/folder/existence checks plus full source-versus-clone XML comparison. Five downloaded dependencies and nine regression tests are verified by the launcher. Existing Stage03 surfaces need no rebuilding.

Stage03 is complete for four candidate scenarios. Prepare their independent AD5 cases:

```bash
conda activate clm_fates_env
(
  set -euo pipefail
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/cc1fcfa3f4bb7544ad3d279f382ccf2a56e2750d/examples/Batch02_10/scripts/04_download_and_prepare_four_AD5.sh" \
    -o "$HOME/Batch02_10_stage04.sh"
  bash "$HOME/Batch02_10_stage04.sh" prepare
)
```

Expected: `AD5_PREPARE_SUMMARY prepared= 4 failed= []`. This creates and previews the four new cases with `RESUBMIT=0`, and submits no jobs. Do not rerun preparation over existing or partial cases. [Runtime-result record, checks, model calendars and remaining work](docs/stage04_four_candidate_success_and_AD5_prepare_20261025.md).

## Stage03: completed candidate construction (historical command)

The parameter-map read is complete. The next executable step is to create the four independent surface **candidates**, using the existing Stage03 choices. This does not certify final scientific acceptance of these proxies or whole-batch readiness.

```bash
conda activate clm_fates_env
(
  set -euo pipefail
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/80430a9775c4efecfcc5fd66c433203a4eebc084/examples/Batch02_10/scripts/03_download_and_build_four_candidates.sh" \
    -o "$HOME/Batch02_10_stage03.sh"
  bash "$HOME/Batch02_10_stage03.sh" build
)
```

The launcher downloads the Python builder and candidate JSON together into a new HOME working directory, verifies both published SHA256 values, and runs self-test before building FI-Hyy, FR-Hes, CH-Fru and IT-MBo. Use `plan` instead of `build` to print the four assumptions without creating model candidates. No Stage01/02 rerun or cluster `git pull` is required.

Expected final result: `CANDIDATE_SUMMARY created_or_verified= 4 failed= []`. Matching candidate files and JSON receipts may be reused after verification; a conflicting existing file fails. Each surface remains under the independent Batch02 output root described in the [Stage03 record](docs/stage03_mapping_PFT_soil_and_four_candidates_20261025.md). This launcher performs no CIME or Slurm operations.

Launcher validation: shell syntax, end-to-end offline fixture download/checksum/layout/plan, corrupted-download rejection before Python/build, and invalid-action rejection passed. The builder's self-test and plan passed. Actual IRIDIS NetCDF build output is still required before preparing AD5 cases.

## Selected ten sites

**Stage03 candidate construction succeeded 4/4.** The [mapping, PFT/soil choices and four candidate assumptions](docs/stage03_mapping_PFT_soil_and_four_candidates_20261025.md) remain applicable. Continue with Stage04 above; the other six have no automatic surface choice.

**Stage02 JSON-reader correction — resolved:** the corrected `--parameters-only` run returned `MAPPING_READ PASS ISSUES 0` for the ten shared references. The active JSON SHA256 and exact 14-type map are retained in the new Stage03 record above. [The earlier parser bug and source snapshot](docs/stage02_JSON_parameter_reader_fix_20261025.md) remain as history. No Stage01/02 rerun is required; the following old command block is retained for reproducibility.

**Stage01 execution reported successful on 25 October:** all ten site directories and active source-surface references were found; SHA checks and self-test passed. The printed `HOLD` labels concern unresolved scientific inputs, not an audit runtime error. See [the source-reference table, reported start/CO₂ values and PFT follow-up](docs/stage01_source_inventory_and_next_inputs_20261025.md). The next script summarizes the existing report; Stage01 does not need to be rerun.

```bash
DIR="$HOME/Non-Competition-CLM-experiment/examples/Batch02_10/scripts"
mkdir -p "$DIR"
curl -fLsS \
  https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/02_summarize_selected_inputs_readonly.py \
  -o "$DIR/02_summarize_selected_inputs_readonly.py" || exit 1
python3 -B "$DIR/02_summarize_selected_inputs_readonly.py" --self-test || exit 1
set -o pipefail
python3 -B "$DIR/02_summarize_selected_inputs_readonly.py" \
  --inventory /iridisfs/home/ly3n24/Batch02_10_preflight_20261025T070625_933191Z/all_sites.json \
  2>&1 | tee "$HOME/Batch02_10_selected_input_details.log"
```

| Site | Original group | Ecosystem | Input decision still needed |
| --- | ---: | --- | --- |
| DK-Sor | 6 | Deciduous forest | DBF80; split the combined ENF/DNF20 |
| FR-Hes | 8 | Deciduous forest | DBF ≳95 of 2020 basal area; classify remainder and select survey date |
| FR-FBn | 8 | Mixed Mediterranean forest | Pine ENF ≈75 of basal area; remaining25 is not all verified EBF |
| BE-Bra | 11 | Mixed forest | ENF55/DBF23; remaining22 unresolved |
| IT-Noe | 11 | Mediterranean shrubland | Vegetated-only species shares; variable total cover; shrub mapping |
| CH-Fru | 11 | Managed grassland | Total mixed herb cover up to90 does not give grass/forb fractions |
| CH-Lae | 11 | Mixed forest | Listed DBF80/ENF12; remaining8 unresolved |
| ES-LJu | 13 | Open shrubland/grass mosaic | Grass19/shrub12; other vegetation≈19; nonvegetated≈50 |
| FI-Hyy | 13 | Boreal forest | Resolved2015 ICOS tree-BA grouping: ENF94.786/DBF5.214; model-ground-area use is an explicit proxy |
| IT-MBo | 13 | Alpine meadow | Grass38/Trifolium14.5 of basal cover; remaining47.5 unresolved |

These figures retain their **original reported denominators**, not CLM ground-area fractions. No remaining share is silently assigned to grass, and no incomplete species list is normalized to 100. The two grassland sites and two shrubland sites cannot use the forest-only Batch01 surface builder unchanged. The newer [38-site reviewed inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_observed_PFT_percent_evidence_v2_20261024.csv) supersedes the old unverified FI-Hyy mixture and the older IT-Noe species-completeness claim. Exact source blob: `9e0dd27b8ba4a7e0c80aea9258133bcce2eb7745`.

Current evidence: [Batch02 source evidence](../../data/batch02_10_sites.csv) and [Batch02 input gates](../../data/batch02_10_input_gates.csv). The new four-site candidate configuration explicitly supplies modelling assumptions for independent candidate-file construction. The other six have no automatic surface choice. Scientific acceptance of a final surface and model submission are separate from producing a candidate. Old `HOLD` labels do not mean the verified parameter mapping failed.

## Run this first on IRIDIS

The maintained downloader below fetches exactly three small files (the audit and its two CSVs), checks their embedded SHA256 values, and runs both self-test and inventory. It uses raw GitHub downloads; a cluster `git pull` is unnecessary.

**25 October checksum fix:** the initial launcher hashed the local site CSV with CRLF line endings, while the published Git blob contains LF. Only that CSV checksum was wrong. The corrected launcher checks the actual published bytes (`28606b0a5899e1b4fc7a75a57cdfc927e3b21a93af7289f523d5983a32eb7841`) and pins its three dependencies to input revision `6a355eaf8c9f055eeacd8f9d110b54c71850492e`. The dependency revision is correct; the launcher itself must be downloaded from the newer fix commit or current `main`. A checksum failure occurs before any checkout input is installed or any audit/model action runs. Source data contents are unchanged.

```bash
conda activate clm_fates_env
curl -fLsS \
  https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/00_download_and_audit.sh \
  -o "$HOME/ICOS_Batch02_download_and_audit.sh" || exit 1
bash "$HOME/ICOS_Batch02_download_and_audit.sh"
```

The default source-code checkout is `$HOME/Non-Competition-CLM-experiment`. Set `B02_REPO_DIR` only if the checkout is elsewhere. The launcher prints `REPORT_JSON=.../all_sites.json`, `REPORT_CSV=.../summary.csv`, and `CONSOLE_LOG=...`. Reports get a new timestamped HOME directory; original model files are opened read-only. Only the three maintained source-code files and new reports are written.

To run already downloaded code:

```bash
cd "$HOME/Non-Competition-CLM-experiment" || exit 1
python3 -B examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py self-test || exit 1
python3 -B examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py audit
```

The report contains all matching original source cases, generated `fsurdat`, actual FATES parameter path and HLM map when readable, full small point soil/PFT arrays, XML start/CO₂/forcing metadata, executable fingerprint when small enough, Slurm resource directives, and actual DATM stream document paths/checksums/excerpts. It does not choose the newest case automatically. In particular, inspect IT-Noe's repaired/ERA5 branch and ES-LJu's corrected forcing branch instead of choosing an obsolete case by filename.

**Audit limits:** no annual/hourly meteorological revalidation; static XML values are expanded without executing CIME and conditional defaults remain unverified. Missing numpy/netCDF4 or unreadable NetCDFs are explicit `read_error` records, not a successful PFT/soil check. `AUDIT COMPLETED` means the report was generated; it is **not** a model-readiness PASS. Source-grid crop or PFT fractions are recorded as model provenance, not tower observations. Soil follows [observed first, documented grid fallback if none](../../docs/observed_soil_texture_policy.md); no fallback or measured-soil replacement is selected by this inventory.

## Same operational method as Batch01

| Step | Mode | Model years | Submit policy / required evidence |
| --- | --- | ---: | --- |
| Source and scientific inputs | Read-only inventory; choose PFT, landunits, soil and active mapping | 0 | This example's current executable step |
| New isolated surface + AD case | FIXNC; cold start; `CLM_ACCELERATED_SPINUP=on`; generated `spinup_state=2` | 0 | Adapt successful Batch01 private overlay; preserve original/shared files |
| First AD segment | AD | 5 | `STOP_N=REST_N=5`, `RESUBMIT=0` |
| AD continuation | AD | 395 | Verify exact run/archive `COMPLETED 0:0`, CLM/DATM/CPL AD5 restarts and state2; then 79 segments, `RESUBMIT=78` |
| Separate Normal case | Hybrid from final AD400 checkpoint; `CLM_ACCELERATED_SPINUP=off` | 0 | Exact Y+400 restart triplet and state2; own case/run/archive |
| First Normal segment | Normal | 5 | `RESUBMIT=0`; generated normal namelist; resulting restart state0 |
| Normal continuation | Normal | 395 | Verify exact Normal5 run/archive and restarts; then 79 segments, `RESUBMIT=78` |

Total per site: **5+395 AD, then 5+395 Normal = 800 model years**. For each site's actual start year Y, phase targets are Y+400 and Y+800; forcing years remain each station's own recycled, documented stream. There is no Normal50 preparation. AD400/Normal400 duration does not certify carbon equilibrium.

Proposed **new** case names: `<site>_B02_FIXNC_AD400` and `<site>_B02_FIXNC_NORMAL400`, with independent output roots. These are future names, not claims that cases already exist. Validate actual fixed-biogeography/no-competition flags and the parameter file used by the executable. For shrub/grass sites, verify the active HLM→FATES mapping before making any new surface.

Reuse the **method**, not unedited site-specific code:

- [Batch01 Stage11 surface/AD smoke controller](../Batch01_10/scripts/11_batch10_AD400_oneclick.py): forest-only inputs and Batch01 paths; **do not run for Batch02**.
- [Batch01 Stage12 private overlay](../Batch01_10/scripts/12_batch10_recover_FATES_AD_private_overlay.py): successful pinned two-change FATES AD namelist workaround. Use only after confirming the same CTSM source blob `698f2396aba8e11cbbbdd58c74ad221e6b7e7038`; never edit shared CTSM.
- [Batch01 Stage13 AD395](../Batch01_10/scripts/13_batch10_continue_verified_AD395.py): reuse archive/mode/duplicate-submit gates, but **never its hardcoded Batch01 job IDs**. Batch02 IDs must come from its own submission receipts.
- [DE-Tha independent AD→Normal hybrid example](../DE-Tha/scripts/14_AD_to_Normal_independent_branch.py): proven transition method; its dates/paths/hashes are DE-Tha-specific. Normal must not inherit explicit AD `spinup_state=2` in `user_nl_clm`.

See [the common protocol](../../docs/AD400_NORMAL400_PROTOCOL.md) for scientific criteria and continuation details. Original Batch01 status documents remain historical records. The operator's report that the prior run finished is not used here to infer which archived AD/Normal checkpoints exist; this update does not inspect the remote HPC filesystem or certify that completion.
