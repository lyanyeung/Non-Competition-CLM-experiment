# Batch02_10 — second European/ICOS cohort, AD400 → Normal400

**Updated 25 October 2026.** The operator requested the next ten sites after the previous Batch01 run. This example activates the ten sites already reserved in the repository; it does not reuse or change any Batch01 case. These are European/ICOS-linked tower sites; the exact network membership is preserved in the [site register](../../data/batch02_10_sites.csv), rather than claiming that every site has identical ICOS status.

**Latest recovery reference:** the operator supplied Batch03's matched-source high-submitting-stack recovery and ten jobs RUNNING beyond the old startup failure on red6083. **Current next step:** [Stage09 applies that method to the four failed Batch02 AD5 cases](docs/stage09_Batch03_success_method_for_Batch02_20261025.md). It preserves scientific inputs/executable/MPI command, never lowers a high stack and records the actual submit-process limits. The old Stage08 wrapper/probe route is superseded. No Batch02 retry outcome is claimed; six other scientific input choices remain open.

## Current next step: Stage09 four-site recovery using Batch03's working method

Use the actual successful Batch03 submission-stack method for FI-Hyy, FR-Hes, CH-Fru and IT-MBo:

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

Expected: `STAGE09 RESUBMIT SUMMARY submitted= 4 uncertain= []`. This validates all four failed cases, preserves inputs/executable/MPI command, raises only a low current submitting-process stack, cancels only their verified blocked old archives and submits only AD5 with RESUBMIT0. It does not run a probe or alter Batch03 jobs. Use `python3 -B "$HOME/Batch02_10_stage09.py" status` for the new IDs. [Source match, operator evidence and recovery record](docs/stage09_Batch03_success_method_for_Batch02_20261025.md).

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
