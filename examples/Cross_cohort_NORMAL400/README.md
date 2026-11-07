# Cross-cohort: verified AD400 → direct NORMAL400 (27 October 2026)

## Normal400 rollout after the needleleaf / phenology reruns (4–5 November 2026)

The decisions and deletions are recorded in the main branch, `maintenance/README.md`. Run everything on the login
node, from `$HOME/CLM_FATES_PLOTS/diag_rerun_tool`, with `PY=$HOME/.conda/envs/clm_fates_env/bin/python`.

**Start scripts 22 and 23 directly with `setsid nohup $PY -B ...`.** Do not start them inside `bash -c "..."`. Their
one-action-at-a-time guard sees its own file name in the wrapper's command line and refuses to run.

| Script | Use |
|---|---|
| `20_...normal-run` | Normal400 of the KEEP_NLF sites (`<Normal>_NLF`, cloned from the original Normal). |
| `20b_normal_spinup_state_tolerance.py` | `normal-run`: the same as script 20, but accepts one difference only: the original Normal `lnd_in` has no `spinup_state` line and the new one has `spinup_state = 0` (CTSM default). This held CA-Ca3, CA-LP1, US-GLE, US-Mpj, US-NR1, US-Vcm, US-Vcp and US-Wjs on 4 Nov. `clean-failed [--confirm REMOVE_FAILED_NORMAL_PREPARE]` removes a `PREPARE_ATTEMPTED` half-made Normal case and writes its file list to the ledger first. |
| `22_...normal-run` | Normal400 of the NLFP / PHEN sites and GL-ZaH. |
| `23_normal400_extra_ad_cases.py` | `check` / `prepare` / `run` / `status` / `clean-failed`: Normal400 of the ICOS Batch04 AD cases (DE-Gri, DE-RuR, IT-Tor, ES-Agu, CH-Aws `_HINONE`). Scripts 20, 21 and 22 cannot take these cases because they have no `NLF_STATE.json`. It uses the script-21 Normal method. AD completion is checked without the state file. `hist_fincl` lists are compared without blanks after commas. |
| `resume_failed_segment.sh` | Resumes a 5-year chain whose run job died (NODE_FAIL or TIMEOUT, not a model error) from its last archived restart. |
| `triage_failed_chains.sh` | Read only. For every `st_archive` job held as `DependencyNeverSatisfied`, shows the case, the dead run job, its Slurm state, its node and the error lines in its logs. |
| `spinup_overview.sh` | Read only. Shows AD400 and Normal400 of every site (scripts 20, 21, 22 and 23), the queue, failures in the last 14 h, the slowest segments, and the HOLD lines of the last normal-run log. |
| `auto_normal_last5.sh` | Runs on the login node with `setsid nohup`. Every 20 min it runs `20b normal-run` for CZ-BK1, US-Me6 and US-MtB, and `22 normal-run` for CA-TP4 and IT-Lav, until each site's Normal400 is submitted. A site whose AD is not yet at 400 years is a HOLD and is tried again at the next check. The script stops after 30 h, or as soon as a prepare has failed (`PREPARE_ATTEMPTED`). |
| `all_sites_status.py` | Read only. Covers every AmeriFlux and ICOS site, the unchanged ones included. For each site it shows the production AD400 → Normal400 pair (from the script-22 classification, plus HINONE and Batch04), the years archived, the queue state and an overall status (DONE, RUNNING, PENDING, ARCHIVING, DEAD, STALLED). A summary per network and per category follows. `--csv` also writes the table to a file. |
| `normal400_progress.sh` | Read only. One line per new Normal400 case (the cases with `NLF_STATE.json`), showing years archived out of 400 and its status: DONE, RUNNING, PENDING, ARCHIVING, DEAD (`DependencyNeverSatisfied`) or STALLED. A summary follows. `-s` prints the summary only. |
| `plot_done_normal400.sh` | Makes the usual figures for the finished new Normal400 cases. A case counts as finished when its phase is SUBMITTED, 400 years are archived and nothing is queued; the AD case is the Normal case's `RUN_REFCASE`. It runs Stage15 (carbon-pool convergence and monthly GPP / NEE against EC) and script 07 (800-year full sequence with the EC reference) on the login node, and writes to a new folder on Home. `--list` is read only. `--sites` restricts the run to the named sites. `SKIP_DONE_IN=<folder>` skips sites already plotted in that folder. |
| `24_last_cycle_vs_ec.py` | Compares the last complete forcing cycle of each new Normal400 with the EC tower. For each site it draws monthly GPP and NEE series, the mean seasonal cycle and a 1:1 scatter, using the same EC rules as Stage15. Where the original Normal400 from before the fix is still archived, it is drawn as "before fix". It also writes `ALL_SITES_last_cycle_*` overviews and `last_cycle_metrics.csv`. It is step 3 of `plot_done_normal400.sh`. |
| `publish_new_normal400_figures.py` | Run on the login node; it pushes over SSH. Publishes a `plot_done_normal400.sh` output folder to `main:figures/NewNormal400/<stamp>/`: every PNG, the metric tables (the two summaries, plus `*_convergence_metrics.csv`, `*_flux_metrics.csv` and `*_metadata.json` per site), a README index and `SHA256SUMS`. Time-series tables that carry EC values are not uploaded. It is a dry run unless `--push` is given. Add `--update` when the folder is already on main: new files are added, changed files are replaced and the README is rebuilt; nothing on main is deleted. |
| `b04_fix_check.py` | Read only. For the Batch04 cases, shows the executable, whether the phenology patch is in SourceMods, the parameter file, the surface PFTs, the FATES PFTs and their `leaf_habit`. Use it to check whether either fix would apply to them. |

Download a script by commit SHA:
`curl -fsSL -O https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/<sha>/examples/Cross_cohort_NORMAL400/scripts/<file>`

## Login-node plotting and publishing

[Login-node retry and publication runbook](LOGIN_PLOTS_AND_PUBLISH.md) reuses available results from jobs 4764252 and 4766277, completes the current analysis interactively, and uploads available PNGs from the login node without submitting Slurm jobs.

## Retry missing plots and publish figures

[Retry and GitHub publication runbook](RETRY_AND_PUBLISH.md) waits for the existing batch job, reuses complete case figures, redraws missing cases, and publishes PNG figures and a missing-output index using a fresh clone.

## Plot all completed sites

[Full-sequence GPP / NEE / NPP / LAI with EC reference](FULL_SEQUENCE_GPP_NEE.md): one 800-year AD400 → Normal400 time series per site for the 54 cases of job 4764252, with EC tower GPP and NEE reference lines, automatic collapse/step/bias flags and all-site overview figures (`scripts/07_plot_full_sequence_GPP_NEE_with_EC.py`).

Collapse diagnostics (`scripts/08_diagnose_collapse_mortality.py`): for a few sites whose GPP goes to ~0, read-only plots of mortality rate by type (carbon starvation, freezing, hydraulic, background, …), carbon fluxes, storage, plant density and recruitment over the full 800 years and monthly for the first AD years, plus an inventory of the FATES history variables actually written.

Diagnostic AD re-run (`scripts/09_clone_AD_diag_rerun.py`): the AD400 cases saved only seven history fields, so the cause of the needleleaf collapse is not recorded. This clones a site's own AD case (same executable, inputs, parameters and AD settings), switches on full FATES history plus per-PFT mortality by type, and runs the first years again in the same 5-year segments. The regenerated land namelist must equal the AD one except for history settings, or nothing is submitted. Read the result with `08_... --ad-only SITE:CASE`.

BTRAN / soil diagnostics (`scripts/10_diagnose_btran_soil.py`): for the re-runs and living reference sites, layer-by-layer liquid water, ice, soil temperature and fine-root distribution, with BTRAN recomputed from the FATES/CLM non-hydro formula (root fraction × water-potential factor × temperature gate) and checked against the model's BTRAN, to show whether low BTRAN comes from dry soil, frozen soil, shallow roots or site-average dilution by patch area.

Carbon budget diagnostics (`scripts/11_diagnose_carbon_budget.py`): per-plant and per-leaf GPP, maintenance respiration, NPP and storage, the share of GPP going to each respiration and allocation term, the winter reserve (storage / winter deficit), the cold-start settings of each case (`use_fates_dbh_init`, initial density), and every FATES PFT parameter that differs between the needleleaf PFT and the broadleaf comparator, ranked.

Carbon-starvation check (`scripts/12_check_cstarvation.py`): month-by-month comparison of the FATES carbon-starvation mortality in the history output with the model's own formula, cmort = scalar × max(0, (upthresh − storage/leafC)/upthresh), plus the namelist settings actually used (`fates_cstarvation_model`, `fates_leafresp_model`, `use_fates_dbh_init`) and the PFT's storage, mortality and leaf parameters. Full write-up: [docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md](../../docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md) (on `main`).

Needleleaf fix trials (`scripts/13_needleleaf_param_trials.py`): clones each site's AD case with a private copy of its FATES parameter file in which only the needleleaf PFT (2) changes — A storage cushion 2.4, B carbon-starvation threshold 0.5, C slatop 0.010, D A+C — runs the first 50 AD years with the diagnostic history, and refuses to submit unless `lnd_in` differs from the AD case only in history settings and `fates_paramfile` and the parameter copy differs only in the intended entries. Controls are the `*_DIAG50` re-runs.

[All-completed AD400 + Normal400 plotting runbook](ALL_COMPLETED_PLOTS.md): live status and reference-pair selection, NT-first EC comparison, and separate per-case carbon diagnostics. The analysis runs as a read-only-input Slurm job and writes new derived files under Home. Completion is not convergence.


This is one controller for the AD400 cases that have no Normal stage of their own yet.

| Cohort | Sites | AD case (ledger) |
| --- | --- | --- |
| AmeriFlux Batch02 | US-BZS, US-CMW, US-EML, US-GLE, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, US-ICt | `<SITE>_AMF_B02_FIXNC_AD400_DIRECT` (Stage06, after the Stage07 repair for ICh/ICt) |
| ICOS Batch02 | IT-Noe | `IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400` (Stage40) |
| ICOS Batch02 | ES-LJu, FR-FBn, CH-Lae | `<SITE>_B02_FIXNC_*_GPPNPP_HISTFIX_AD400` (Stage43) |
| ICOS Batch02 | DK-Sor, BE-Bra | `DK-Sor_B02_FIXNC_ICOS_DBF100_AD400`, `BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_AD400` (Stage44) |

Added 28 Oct: **AmeriFlux Batch04** FIXNC arm (US-Rpf, US-SP1, US-SRG, US-SRM, US-Seg, US-Ses, US-Slt, US-Syv, US-Ton, US-Uaf; `<SITE>_AMF_B04_FIXNC_AD400_BASETA_V1`) and **DE-Tha** (`DE-Tha_OBSPFT_NC_V1_AD400`). These cases have no ledger in this repository, so the chain's first job is the 80th-last `run.<case>` job in Slurm accounting, and every job from there on must be `COMPLETED 0:0`. For all sites `audit-ad400` now also requires the full restart sequence Y+5 … Y+400 and an AD case whose land root is the shared CTSM.

The 28 Oct [read-only progress scan](scripts/02_scan_all_spinup_progress_readonly.py) (only `_FIXNC_` / `_OBSPFT_NC_` cases) found **34 sites with NORMAL400 done**. Nineteen sites have AD400 done but no Normal yet: BE-Bra, CH-Lae, DK-Sor, ES-LJu, US-Ha1, US-Ho1, US-Ho2, US-Ho3, the ten Batch04 sites and DE-Tha. BR-Ma2's Normal400 was at 380 years and still running. US-ICh had failed, and NL-Loo is the legacy PRE50/AD200 example.

**28 Oct: DATM streams set after preview.** Stage-normal held ES-LJu, CH-Lae, DK-Sor and BE-Bra with `Normal DATM streams differ from AD case`. Batch02 Stage25/34/36/44/45 wrote the curated forcing list straight into the AD case's `CaseDocs/datm.streams.xml` and RUNDIR, then submitted with `--skip-preview-namelist`. The case's stream source still names the original forcing, so the regenerated Normal streams pointed back to it:
- ES-LJu: FLUXNET_13 instead of the Stage24 meteorology.
- DK-Sor: 1996–2024 instead of the Stage45 1996–2025.
- BE-Bra and CH-Lae: the original files for their curated years.

`stage-normal --carry-ad-streams` therefore copies the AD case's exact effective `datm.streams.xml` into the Normal CaseDocs and RUNDIR. This is the same method those stages used. Two conditions must hold: the AD RUNDIR copy equals the AD CaseDocs copy byte for byte, and every listed data file exists. `submit` refuses if the streams changed after staging. The [progress scan](scripts/02_scan_all_spinup_progress_readonly.py) `--streams` option compares every existing Normal case with its AD case.

The following are **not** handled here:
- **AmeriFlux Batch01** (CA-TP4, BR-Ma2, CA-Ca3, CA-LP1) uses its own [Stage21 controller](../AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py) (`stage-normal` → `submit-normal400-direct`).
- **ICOS Batch01/03** and the four original ICOS Batch02 sites already have Normal cases.

**Operator decision:** Normal400 runs directly as 80 × 5 years (`STOP_N=5`, `RESUBMIT=79`, one `case.submit`), with no Normal5 smoke. The first segment is audited instead (`audit-first5`: restart Y+405, `spinup_state=0`), which is the check Normal5 would have made.

## Operator status, 27 October 2026 14:25 UK

`audit-ad400`: PASS for 7 sites (US-BZS, US-CMW, US-EML, US-GLE, US-ICt, IT-Noe, FR-FBn). HOLD (still queued) for US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, ES-LJu, CH-Lae, DK-Sor and BE-Bra. `stage-normal`: 7/7. `submit`: 7/7, with `skip_pnl` persisted.

| Site | run / archive | Model years |
| --- | --- | --- |
| US-BZS | 4748888 / 4748889 | 2410 → 2810 |
| US-CMW | 4748890 / 4748891 | 2401 → 2801 |
| US-EML | 4748892 / 4748893 | 2408 → 2808 |
| US-GLE | 4748896 / 4748897 | 2405 → 2805 |
| US-ICt | 4748898 / 4748899 | 2407 → 2807 |
| IT-Noe | 4748900 / 4748901 | 2404 → 2804 |
| FR-FBn | 4748902 / 4748903 | 2408 → 2808 |

Same session, AmeriFlux Batch01 Stage21: CA-TP4 4748904 (2402 → 2802) and BR-Ma2 4748906 (2399 → 2799). Next check: `audit-first5`.

## Method

[Script](scripts/01_direct_NORMAL400_after_AD400.py). The method is the same one that already produced Normal runs on IRIDIS6: AmeriFlux Batch01 Stage21, ICOS Batch02 Stage27 and DE-Tha Stage14.

1. **`audit-ad400` (read only).** A site passes when all of the following hold:
   - Its own ledger is in the submitted phase.
   - Nothing is queued.
   - Every run and st_archive job since the ledger's first run job is `COMPLETED 0:0`, with ≥ 80 of each.
   - The last CaseStatus events are both success.
   - `RESUBMIT` is 0.
   - The latest archived restart is exactly Y+400 for clm2, datm and cpl.
   - The land restart has `spinup_state = 2`.
2. **`stage-normal` (no Slurm).** Runs only for sites that pass the audit. Each site gets a new case named after the AD case with `_AD400` → `_NORMAL400`. The case is built as follows:
   - `create_clone --keepexe` (same executable).
   - `SourceMods` pinned to the executable-owner case, so it cannot dangle later.
   - Hybrid from the AD case at Y+400-01-01, with `CLM_ACCELERATED_SPINUP=off`.
   - The three AD restarts are copied into the new run directory (sha-checked), with rpointers.
   - `finidat` set to the copied land restart.
   - The explicit `spinup_state` removed.
   - `fates_paramfile` pinned to the AD case's file (this includes the ARCTIC_PURE JSON for BZS/EML/ICh/ICt).

   The namelists are then generated with the shared CTSM. The checks are:
   - `fsurdat`, `fates_paramfile`, `co2_ppmv`, `use_crop`, `fates_spitfire_mode`, `hist_fincl1` and the FATES switches must equal the AD case.
   - The DATM streams must be identical.
   - XML values must match the AD case (PTS, CO₂, DATM years, calendar, EXEROOT).
3. **`submit`.** Before submitting, the script reruns the validation and confirms that `lnd_in`, the surface and the parameter file are unchanged since staging. It then applies the stack guard and makes one `case.submit --skip-preview-namelist`.

The AD cases and their outputs are only read. Ledgers live in `<EXP22>/Cross_cohort_NORMAL400_direct/<SITE>_NORMAL400_state.json` with phases:
- `STAGE_ATTEMPTED_UNCERTAIN`
- `PREPARED_NOT_SUBMITTED`
- `NORMAL400_DIRECT_ATTEMPTED_UNCERTAIN`
- `NORMAL400_DIRECT_SUBMITTED`

A stage that was cut off (SSH drop) is never redone in place. Run `inspect-interrupted`, then `quarantine-interrupted`, then `stage-normal` again.

A mock end-to-end test passed. It covered:
- AD400 PASS and HOLD (failed site, still-running site).
- Interrupted-stage quarantine.
- Refusal of duplicate stage and duplicate submit.
- Refusal on DATM drift.
- `fates_paramfile` pinning and SourceMods pinning.
- The first-5 and Normal400 audits.

## IRIDIS commands

```bash
cd ~ && conda activate clm_fates_env && ulimit -s unlimited
REV=<commit>                                   # see the root README for the pinned commit and sha256
X=~/Non-Competition-CLM-experiment/examples/Cross_cohort_NORMAL400/scripts/01_direct_NORMAL400_after_AD400.py
mkdir -p "$(dirname $X)"
curl -fLsS --retry 3 "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV/examples/Cross_cohort_NORMAL400/scripts/01_direct_NORMAL400_after_AD400.py" -o "$X"
sha256sum "$X"
python3 -B "$X" self-test
python3 -B "$X" audit-ad400                    # read only; prints "PASS: <sites>"
# stage only PASS sites (nohup, ~2-4 min per site)
nohup python3 -B "$X" stage-normal --sites <PASS sites> --confirm STAGE_CROSS_COHORT_NORMAL400_CASES_NO_SLURM > ~/n400_stage.log 2>&1 &
tail -f ~/n400_stage.log                        # wait for "STAGE-NORMAL SUMMARY ok= N hold= []"
python3 -B "$X" submit --sites <staged sites> --confirm SUBMIT_CROSS_COHORT_NORMAL400_DIRECT_80x5_ONCE
python3 -B "$X" status
# later
python3 -B "$X" audit-first5
python3 -B "$X" audit-normal400
```
