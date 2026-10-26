# AmeriFlux Batch04 — can we submit now? Operator-confirmed 10/10 source and 20 paired arms: NOT YET AD5-ready

**Scope: AmeriFlux Batch04_10 ONLY.** This is NOT ICOS Batch02/03/04 and no ICOS job is relevant to model readiness.

## Actual operator evidence from 2026-10-26

- Actual `00_fetch_and_prepare_ameriflux_batch04.sh --build` ended with `AMF_B04 TEN SITE SYVH9 MET + SYVH12 SURFACE SOURCE AUDIT PASS 10/10`; ten complete SHA-verified met and year-2000 CTSM point surfaces.
- `AMF_B04 PAIRED EXPERIMENT PLAN 20 ARM ENTRIES CREATED`, from `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10/paired_FATES_FIXNC_AD400_Normal400_plan_20261026T165940Z_1e6b7e17.json`. **Plans are not actual CIME cases.**
- `AMF_B04 TEN SHARED PFT SURFACE CANDIDATES FULL SHA AUDIT PASS`, `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10/PFT_surface_candidate_research_ONLY/candidate_20261026T165944Z_ab70c90d`, exactly ten new, source-independent starting PFT surfaces shared by both planned model arms, soil/organic grids preserved, no original files overwritten. These PFT distributions are site-specific model hypotheses based on recommended 50-site source tables; not a claim of full tower footprint observation.
- `B04 ACTIVE_CASES=0, AD400_SUBMITTED=0, NORMAL400_SUBMITTED=0`; no actual CIME AD5 cases have been created by those steps.
- Operator `b04_stack_guard.py --self-test` PASS; live IRIDIS6 login6001 `soft_at_submit_KiB=unlimited`, `hard_KiB=unlimited`, `PropagateResourceLimits=ALL` PASS. This is a genuine **resource preflight only**, and all future actual submitter processes require their own `require_for_submission(...)` call immediately before every `case.submit`.

## Why NOT yet submit 20 AD5 jobs, let alone 400-year jobs

The source and PFT starter receipts deliberately state `ZBOT_verified=False`, `DATM_timecenter_UTC_ready=False`, `FATES_PRIVATE_MAPPING_ACTIVATED=False`, `CIME_or_DATM_ready=False`, `spinup_authorized=False`. No exact model-ready annual `TBOT/PSRF/WIND/FSDS/FLDS/PRECTmms/SHUM` **NOLEAP DATM netCDF** and time-centred stream mapping has been prepared and checked for these ten original native local-standard HH records. Three original source-precision overroundings of VPD vs saturation (Rpf 2, Syv 1) need **explicit output-only** QBOT conversion. Original source BIF does not report site-specific TA/WS observation ZBOT for these ten tower products, so defaults or canopy HEIGHTC are not approved. The ten source PFT hypotheses have bare ground fractions of 45%/40% etc and US-Uaf Arctic parameter slots; mapping to branch-specific FATES needs verification. Original ten-layer soil texture and ORGANIC remained gridded, not site-observed; neither Full nor FIXNC active cases can currently demonstrate correct source and metadata use. CIME site-specific PTS/domain, user_nl/CaseDocs, active RUNDIR and spinup parameters are not generated/validated.

**Correct sequence:** (1) create SHA-pinned 10-site technical DATM preview (separate output only) and independently verify UTC/time-centering/no-leap humidity and all seven model variables; (2) recover station observation-height evidence or define documented sensitivity scenarios; (3) review FATES PFT mapping + bare/arctic and soil/ORGANIC baseline; (4) create two **AD5-only** model cases per site with exact surface/forcing/PTS/CO2 and archive safety; (5) run case-science and in-process stack guard immediately before Slurm; (6) verify actual archive/restarts before extending AD395, then Normal5/395.

## New executable, read-only launch-gate snapshot

[Stage03 `03_batch04_AD5_readiness_gate_READONLY.py`](../scripts/03_batch04_AD5_readiness_gate_READONLY.py), pinned code revision **`2598dfa26c531010c1c9f227ef649574f0b31054`**. Checks all original source SHA via Stage01 auditor, all ten PFT SHA via operator Stage02 receipt, exact 20 individual arms, actual live RLIMIT_STACK and Slurm propagation; enumerates eight remaining model science/technical holds. It **never submits** CIME/Slurm or rewrites sources. It **intentionally exits code 2** while model inputs are not approved (this is not failure of ten source files).

IRIDIS6 read-only check:
```bash
conda activate clm_fates_env
(
  set -euo pipefail
  BASE="$HOME/ameriflux_batch04_fates_pair_setup_a51ece95c6cd"
  RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment"
  COMMIT="2598dfa26c531010c1c9f227ef649574f0b31054"
  FILE="$BASE/scripts/03_batch04_AD5_readiness_gate_READONLY.py"
  mkdir -p "$BASE/scripts"
  curl -fLsS --retry 3 "$RAW/$COMMIT/examples/AmeriFlux_Batch04_10/scripts/03_batch04_AD5_readiness_gate_READONLY.py" -o "$FILE"
  python3 -B -m py_compile "$FILE"
  python3 -B "$FILE" --self-test
  python3 -B "$FILE" --check || { rc=$?; test "$rc" -eq 2; }
)
```
The source scripts and three science-input snapshots are downloaded in the exact same `$BASE` tree by the updated pinned Stage00 installer. If they aren't present, re-run the Stage00 launcher from the exact pinned GitHub revision **`e0d93de4ccf7279ea8e80a0d9efe2cd955fa174d`** in `--check-only` mode first; this is read-only.

**Current answer:** not enough verified inputs to submit any AmeriFlux Batch04 AD5/AD400 model job yet. The stack gate is PASS but cannot substitute for missing active DATM, ZBOT, FATES parameter maps and CIME cases. The operator can proceed with technical DATM converter and AD5 case construction after resolving the above; do not activate a prototype as production run.
