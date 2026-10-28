# Cross-cohort: verified AD400 → direct NORMAL400 (27 October 2026)

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
