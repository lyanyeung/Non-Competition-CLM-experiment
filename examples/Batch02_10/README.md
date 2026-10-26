# Batch02_10 — second European/ICOS cohort, AD400 → Normal400

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
