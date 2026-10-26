# AmeriFlux Batch02 (10 sites) — FATES fixed-biogeography / no-competition integration

**Started 2026-10-26. This is NOT European/ICOS `examples/Batch02_10`.** Exact AmeriFlux sites: US-BZS, US-CMW, US-EML, US-GLE, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, US-ICt.

## Status: source met is technically prepared, model completion is NOT 10/10

The independent [original AmeriFlux Batch02 source workflow](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10_Batch02) completed Stage95 **215 source-year NOLEAP NC files for the ten sites** (site original record lengths vary; 10/10 files structurally verified through Stage96). Those files **have not been adopted into ten validated CIME FIXNC cases**. Versioned 122 source-QC modifications and independent sources must remain immutable.

**Only US-GLE has a verified new CIME submission in the supplied operator logs**, and that was **a separate exploratory 2005–2020 historical-meteorology run, NOT FIXNC AD/Normal spinup**:
- CIME case: `/iridisfs/scratch/ly3n24/CLM_FATES/cases/US-GLE_FATES_HISTMET_2005_2020_STAGE106`.
- `case.submit success` 2026-10-26 13:25:52; Slurm run **4739020 PD** and archive **4739021 PD (Dependency)** when inspected; no confirmed model success or 16-year completion. Four sequential 4-year segments in the SAME case (3 resubmissions), NOT independent year-window groups.
- Uses source-dated historical ERA 2004 local boundary -> 2005 UTC corrected Stage106, while other variables/forcing years unchanged; **no scientifically equilibrated FATES spinup**, historical meteorology but **fixed CO₂=378.98ppm**, original year2000 gridded NATVEG92.49%/CROP7.51% rather than target FIXNC stand.
- 2020→2005 repeated forcing seam (|ΔTBOT| 3.877K, |ΔPSRF| 259Pa, |ΔWIND| 4.617m/s) intentionally **left unedited** by user's decision to run once-through historical forcing; actual DATM runtime date boundary requires checking from logs.
- **Remaining nine sites have not supplied verified case/Slurm/completion receipts.** Do NOT label all ten simulated, ready for spinup, or successful. US-Ho1 retains 2000-12-27 original QC0/QC1/QC2 extreme temperature jump HOLD (08:00−15.7°C QC0, 08:30−15.1°C QC0, 09:00−15.4°C QC1, 09:30+3.346°C QC2); original sensor heights and local-UTC assumptions require per-site review. US-BZS/US-Ho1 missing official TA/WS time-dated height histories, other sites have gaps.

## The authoritative 50-site PFT and soil inputs are in the OTHER repository

The files **exist now** and have been matched to all ten AmeriFlux Batch02 IDs. Source repository: `lyanyeung/CLM-FATES-single-site-workflows`, Git commit `0bef7854a916daee34948f5b4efc54ad6089482d` (specific retrieved source objects SHA-verified below).

1. [50-site FIXNC recommended PFT](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv), original Git blob `26fdfda6f1c88c9a134e7853bd70234685665031`. Use `recommended_percent`, `mapping_profile`, `clm_pct_nat_pft_json`, `uncertainty`, `basis`, `source_denominator` (NOT just IGBP).
2. [50-site recommended soil texture](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/FINAL_RECOMMENDED_INPUT_SOIL_TEXTURE_50_SITES_20261026.csv), original Git blob `6f2e9ff354bf5368083d212ee6aaaee2d75db390`. Values in `PCT_SAND_0_30cm` and `PCT_CLAY_0_30cm` are **summary 0–30cm recommendations**, NOT CLM `PCT_SAND`/`PCT_CLAY` on all ten layers. See [soil method](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/README.md), which requires per-depth ReESH/BADM/SSURGO/SoilGrids selection and organic matter assessment. Source data for per-layer generation must be independently checked.
3. [Auditable *ten-site* join CSV](data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv). Generated using **exact Batch02 rows only**; maps to FATES functional fractions and host `PCT_NAT_PFT` slots; all ten host fractions independently sum to 100%. It is **input planning**, not a mutation of any source NC, surface, CIME case or FATES parameter.

### Ten-site combined site-stand candidates

| Site | Recommended natural-soil FATES PFT % | Soil Sand/Clay 0–30cm % | Evidence tier | PFT uncertainty |
|---|---|---|---|---|
| US-BZS | ENF20 / Arctic evergreen shrub60 / Arctic deciduous shrub10 / Arctic C3 10 | 40.0/8.9 | T3 SoilGrids | HIGH |
| US-CMW | DBF74 / C4 26 | 9.8/20.5 | T2 SSURGO | HIGH |
| US-EML | Arctic evergreen shrub20 / Arctic deciduous shrub30 / Arctic C3 50 | 38.2/11.8 | T3 SoilGrids | HIGH |
| US-GLE | ENF100 | 17.5/17.4 | T1 ReESH | MEDIUM |
| US-Ha1 | ENF27.3 / DBF72.7 | 66.1/10.7 | T1 ReESH | MEDIUM |
| US-Ho1 | ENF91.9 / DBF8.1 | 58.4/10.9 | T1 ReESH | MEDIUM |
| US-Ho2 | ENF90 / DBF10 | 58.4/10.9 | T1N US-Ho1 ReESH near-tower proxy | HIGH |
| US-Ho3 | ENF80 / DBF20 | 58.4/10.9 | T1N US-Ho1 ReESH near-tower proxy | MEDIUM |
| US-ICh | Arctic evergreen shrub30 / Arctic deciduous shrub20 / Arctic C3 50 | 6.0/1.0 | T2 SSURGO | HIGH |
| US-ICt | Arctic evergreen shrub15 / Arctic deciduous shrub25 / Arctic C3 60 | 6.0/1.0 | T2 SSURGO | HIGH |

**Arctic PFT parameter map:** US-BZS, US-EML, US-ICh, US-ICt use `ARCTIC_PURE`, **not** the default DEFAULT14 FATES HLM PFT mapping. Verify the source [three mapping profiles](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/metadata/recommended_hlm_profiles_v1_20261026.json) and isolate any necessary site-only FATES parameter edits. Do not map moss/lichen/biocrust silently to bare or C3 grass. Dryland US-CMW tree/grass coverage and Arctic percentages contain model priors, NOT fully measured exclusive vegetation-area shares.

**Soil physics caveats:** US-BZS and US-EML are organic/permafrost-relevant; US-ICh and US-ICt are peat over mineral silt/till. Sand/Clay without reviewed `ORGANIC`, hydrology and layer structure is insufficient. US-GLE ReESH 17.5/17.4 conflicts with independent ~46–48% sand surveys: keep a soil-texture sensitivity alternative instead of asserting certainty. US-Ho2/Ho3 use nearby Ho1 measured soil as *neighbour proxy*, not direct local cores.

**US-GLE site vegetation:** user-supplied AmeriFlux BIF says ENF with 85% Engelmann spruce and 15% subalpine fir tree-species composition, not measured EC-footprint area cover; beetle peak 2008 caused loss of ~85% of forest basal area (NOT 85% land area). Existing 2005–2020 history was not run on this separate recommended FIXNC PFT/soil surface, and must not be used as evidence it was.

## Next steps for the separate FIXNC experiment

- **(1) Read-only inventory** original ten-site 215 NC manifest, per-site clock/sensor-height and unresolved QC logs, existing cases and Slurm/restart state; no false claim of 10 simulated sites. A specific GLE job `4739020` is only submitted/pending.
- **(2) Per-layer PFT/soil surface candidates**, creating new SHA-versioned natural-soil tower-point surfaces from the recommendations, explicitly choosing modeled NATVEG100/CROP0 **if** pursuing the idealized same-stand FIXNC experiment. Do not overwrite existing GLE historical or default surfaces. Infer neither measured tower crop nor full footprint PFT from gridded `PCT_CROP`.
- **(3) Check each site actual forcing file time phase, source sensor heights, true 10-layer soil/ORGANIC, FATES PFT map and scientific decision receipts; read-only CIME preview.** Only then choose site-specific AD400→Normal400 per [standard protocol](../../docs/AD400_NORMAL400_PROTOCOL.md) in independent FIXNC cases with 5y smoke gates.
- **(4) Avoid user-instructed proliferating unrelated test groups**; ten-site cohort is one workflow, model comparisons later between competition and FIXNC. Existing full-FATES/history runs and ten original weather files are not touched. No FIXNC jobs have been submitted as a result of the documentation/CSV preparation here.

**Never invoke** `examples/Batch02_10` for AmeriFlux: that directory is the **second ICOS/European cohort**, with completely different site list/cases/PFT and soil.


## Stage02: ten independent FIXNC candidate surfaces

Operator read-only Stage01 audit completed (2026-10-26):
- `AMF_B02_SELF_TEST_PASS`, `AMF_B02_REGISTER_PASS 10/10`, original Stage95 215 NC receipt present, **not** evidence ten CIME cases or ten AD spinups.
- **US-GLE HIST2005-2020** Slurm run `4739020 RUNNING` and archive `4739021 PENDING` at audit time; it is separate from FIXNC. **US-Ha1_FATES_1PT** has at least one prior `model execution success`, not proof of a full spinup or this batch's fixed-NC configuration.
- Other eight sites had zero discovered cases. Original US-Ho1 QC/height science and Arctic/permafrost physics still HOLD.

**[Stage02 source-gated 10-site surface candidate builder](scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py)** source Git blob `84ee53d68b71b0d54d5e0fb888636fb3e941910d` (initial commit `57c3848bc2366c1723abbea502d58bbfff77ce07`) uses:
1. Exact source-pinned 10-site PFT + soil recommendation [register](data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv), 100% sum under host PFT index 0..14 and correct DEFAULT14 or ARCTIC_PURE *candidate* mapping.
2. **Actual original Stage01 50-site depth-profile output** `$HOME/CLM_FATES_SOIL/AmeriFlux50_20261026/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv` (or use `--soil-wide /absolute/path`). Checks site layer1..10 sand/clay complete, physical, mean first five layer values agree with independently pinned 50-site 0–30cm recommendations to 0.11 percentage point. If no genuine source 10-layer profile, holds: does **not** fill all layers with 0–30cm mean.
3. Original station surface `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/<SITE>/subset_data_batch02_surf2000/surfdata*.nc`. Only if one valid point NetCDF with `PCT_NAT_PFT natpft15` and `PCT_SAND/PCT_CLAY` ten nodes, copies it to new independent `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/<SITE>/surface/*stage02_v1.nc`. Creates idealized NATVEG100/CROP0 stand surface, actual complete soil profile, candidate PFT host distribution. All original other landunits become zero; **this is a model hypothesis, not observed tower footprint proportions**.
4. Preserves all other source variables, including `ORGANIC` (which is **not approved as site-realistic** at US-BZS, US-EML, US-ICh and US-ICt); reports absolute source and candidate SHA. Existing original surfaces, GLE historical case and all existing CIME/Slurm jobs remain untouched.
5. For four Arctic sites, PFT map **ARCTIC_PURE** requires separate per-site FATES parameter file activation and verification before any FIXNC CIME. Creating a host-PFT surface alone does **not** install the FATES HLM map or justify AD400.
6. All commands are non-submitting. `--self-test` synthetic invariants, `--check` read-only all-site preflight, `--build` copy+validate independent new surfaces only. Does not overwrite existing candidate outputs; missing/uncertain site source produces named HOLD rather than guessed values.

Use pinned raw source rather than Git pull, as usual. Example:
```bash
python3 -B 02_prepare_ten_independent_FIXNC_surface_candidates.py --self-test
python3 -B 02_prepare_ten_independent_FIXNC_surface_candidates.py --check
python3 -B 02_prepare_ten_independent_FIXNC_surface_candidates.py --build
```
Only build when the Stage01 10-layer source exists and all applicable science assumptions are explicit. A 10/10 candidate surface PASS does **not** imply CIME namelist/mapping/actual climate science is ready for AD400.

If Stage01 output is missing, **DO NOT substitute the 0–30 cm means**. Run the *existing* original Stage01 collector with full BADM/download cache per [soil README](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/README.md), or locate an earlier authoritative `09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv` and pass `--soil-wide`. These source files have not been confirmed on the cluster from this chat; the script will report the missing exact path.


## 2026-10-26 operator decision: DIRECT AD400, no separate AD5 pilot

The operator explicitly cancelled the earlier AD5 → AD395 two-step manual workflow for AmeriFlux Batch02. **ONE SCIENCE-APPROVED FIXNC CIME case, ONE `case.submit`, 400 model years**. CIME runs **80 consecutive 5-year Slurm segments**, automatic `RESUBMIT=79`, `RESUBMIT_SETS_CONTINUE_RUN=TRUE`, `STOP_OPTION=nyears`, `STOP_N=5`, `REST_N=5`. **The 5-year interval is just a scheduler/restart increment, NOT an independently submitted or manually approved AD5 experiment.**

The same rule applies to NORMAL400 after the ACTUAL AD400 final restart is archived, using a separate hybrid restart case, CLM_ACCELERATED_SPINUP=off, FATES `spinup_state=0` or absent, and its own one-time submission with RESUBMIT=79. Never interpret the Slurm submission as a completed 400y run.

[Direct400 64-MiB stack-protected submit controller](scripts/03_stack_guard_and_FIXNC_submission.py) at source commit `ecb58d4c0a69df9d541ce087c26cc2fff00f8675`, Git blob `de15f89932107f153082bafdf17fcbdd1f8264c8` accepts `--phase AD400` or `--phase NORMAL400`; the old phase choices AD5/AD395/NORMAL5/NORMAL395 are NO LONGER USED for this cohort. It verifies **actual CIME XML=80×5**, FATES FIXNC flags and AD spinup_state=2, exact compiled exe/FATES parameter/DATM stream SHAs, source science releases, full source point geometry, stage-private FATES `skip_pnl` and Slurm stack propagation before any one-time case.submit. Normal400 additionally requires the **400-year** AD final restart and SHA-verified handoff; there is no 5-year handoff.

**Scientific case readiness not waived.** The existing 10-site Stage95 forcing is technically generated but original height/UTC and soil organic/per-layer/ARCTIC_PURE data is not 10/10 approved. No AmeriFlux Batch02 dedicated FIXNC cases or per-case RELEASE receipts were present in the last user-provided audit; therefore this change **does not itself start AD400**. Original US-GLE historical job 4739020 and previous US-Ha1 case are different jobs, unaffected.

To submit a vetted site after its independent case/receipt exists:

```bash
python3 -B 03_stack_guard_and_FIXNC_submission.py --submit \
  --site US-GLE --phase AD400 \
  --case /iridisfs/scratch/ly3n24/CLM_FATES/cases/US-GLE_<NEW_FIXNC_AD400_CASE> \
  --receipt /iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/<SITE>/AD400_RELEASE.json \
  --confirm SUBMIT_AMF_BATCH02_ONE_SCIENCE_APPROVED_FIXNC_CASE_WITH_STACK_GUARD
```

The command above is a **template**, not runnable while placeholder paths remain. Do NOT point it to the historical GLE case or invent a release receipt.

## Stage03 — Batch01-style stack guard

The user explicitly requests the same stack mechanism as [AmeriFlux Batch01 Stage21](../AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py), which successfully controls AD400 (one submission with 79 automatic restarts) → Normal400 (one submission after verified AD400 completion) submissions.

**Exactly as Batch01:** minimum submitting-process `RLIMIT_STACK` soft **65536 KiB** (64 MiB), required because insufficient stack can segfault at ESMF/Prigent roughness input. On IRIDIS6, Slurm normally inherits submitted process limits via `PropagateResourceLimits=ALL`. This is separate from the old CA-TP4 incorrect point-domain PTS and scientific PFT/soil approval.

[Batch02 Stage03 guarded submit](scripts/03_stack_guard_and_FIXNC_submission.py), Git blob `de15f89932107f153082bafdf17fcbdd1f8264c8`, provides:

- `--self-test`: no CIME or job changes.
- `--audit`: verifies stack limit, raises **only** a low process soft limit (target 300000 KiB where hard limit permits), never decreases an existing high or unlimited stack or changes hard limit; verifies a child inherits it; inspects actual Slurm `PropagateResourceLimits`.
- `--submit`: all four AD400/Normal400 model phases use that guard **inside the SAME Python process as the child `case.submit`**, fail-closed if Slurm stack propagation not confirmed.
- Before any CIME submission, require SHA-pinned per-case science release receipt, including **real ten-layer soil and organic decision**, FATES HLM/Arctic private mapping, source UTC/ZBOT, CIME PTS geometry, CIME preview, and exact prepared 5-year smoke or a verified 5-year restart with 395-year continuation.
- As in Stage21, requires `.submit_options` `skip_pnl=true` before invoking `case.submit --skip-preview-namelist` (do not accidentally regenerate approved private AD namelists). Creates an exclusive attempt-before-submit ledger to prevent blind duplicates after a disconnect.
- Does NOT submit any case until separate science receipts and independent FIXNC cases actually exist. Existing US-GLE historical job and US-Ha1 old case are untouched. Passing stack checks does NOT make ten site inputs/model conditions approved.

### Immediate IRIDIS6 command (no new jobs)

```bash
(
 set -euo pipefail
 REV=ecb58d4c0a69df9d541ce087c26cc2fff00f8675
 SRC="$HOME/AMF_Batch02_stage03_stack_guard.py"
 curl -fLsS --retry 3 "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV/examples/AmeriFlux_Batch02_10/scripts/03_stack_guard_and_FIXNC_submission.py" -o "$SRC"
 test "$(git hash-object "$SRC")" = de15f89932107f153082bafdf17fcbdd1f8264c8
 python3 -B -m py_compile "$SRC"
 python3 -B "$SRC" --self-test
 echo "SHELL SOFT=$(ulimit -s)KB HARD=$(ulimit -Hs)KB"
 python3 -B "$SRC" --audit
 scontrol show config | grep -i PropagateResourceLimits
)
```

**Important:** `--audit` changes only its current Python process, not the parent shell. Future real CIME submission MUST run through this guarded submission path, not through an independent unguarded caller.

### Soil10 preparation continues in parallel

[Batch02 Stage02 independent surface builder](scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py) needs the ORIGINAL source-generated 50-site `09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv` with L1–L10 separately. The source is [Ameriflux_Soil Stage01](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/scripts/01_collect_soil_texture_evidence.py) in the other repository, with its data files/manifest. No valid 10/10 depth profile has yet been shown in this chat. Never fill ten layers with the averaged 0–30cm values. The 4 Arctic/permafrost-relevant sites also need explicit organic-soil and ARCTIC_PURE FATES map approval. Preserve original GLE historical job.

## Stage04 — one-paste IRIDIS6 stack/soil10 bootstrap

[Stage04 portable shell bootstrap](scripts/04_iridis_stack_soil10_bootstrap.sh) is pinned to both repos, Git blob `fa6ae72261f62e41381bd13d9650cd8ebf969775`; it downloads Stage02/03 and the original 50-site soil collector + 5 source metadata/soil records through `curl`, **not git pull**.

Five explicit modes: `all` (default) performs stack audit, original 10-site Layer1–10 soil profile collection, science checks and construction of independent candidate surfaces in ONE command; `audit` confirms Stage21 min64MiB stack/child propagation and checks original soil collector selftest, **no Slurm**; `soil10` fetches genuine per-depth ReESH/BADM/USDA/SoilGrids source evidence for exact second-batch ten sites, builds original 10-layer 09-wide CSV, then runs Stage02 **read-only** surface check (isolated Batch02 per-depth evidence at `$HOME/CLM_FATES_SOIL/AmeriFlux_Batch02_10_20261026_Stage04`); `check-surfaces` repeats the read-only check from cached 10-layer evidence; `build-surfaces` writes only independent versioned candidate surfaces if every site passes the original evidence/surface gate. **Never builds or submits any CIME model.**

Quick operator commands (do not run `soil10` until network access and original source packages are available on IRIDIS6):

```bash
COMMIT=aac5984b7de90415649ea330a74f8f89ef249700
SCRIPT="$HOME/AMF_Batch02_04_stack_soil10.sh"
curl -fLsS --retry 3 "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/AmeriFlux_Batch02_10/scripts/04_iridis_stack_soil10_bootstrap.sh" -o "$SCRIPT"
test "$(git hash-object "$SCRIPT")" = fa6ae72261f62e41381bd13d9650cd8ebf969775
bash "$SCRIPT" all
# Only if source data are missing, inspect holds then rerun: bash "$SCRIPT" soil10
# Or reuse cached profiles: bash "$SCRIPT" build-surfaces
```

**Stack persistence:** This bootstrap adjusts its own subshell; it does not change the parent IRIDIS6 shell. Future real `case.submit` must run *within* Stage03 high-stack guarded submit, not independently. Strict Stage03 science release receipts are deliberately not auto-created by Stage04, so successful candidate surfaces cannot accidentally launch 400 years.

**Documented proxy correction (Stage02 source commit `63a79d7a80d766a97f87763619f1f216c6607b6e`):** US-Ho2 and US-Ho3 final recommended soil is explicitly **US-Ho1 ReESH measured nearest-neighbour L1–L10**, not their earlier stand-alone Stage01 SoilGrids 0–30 cm values. The script checks the source Ho1 measurement tier before proxying, records Ho1 provenance, and never invents a ten-layer texture. All other sites must match their source-pinned original top-5-node means. The `all` mode creates independent new surfdata only and never submits AD400.

## Stage05 — actual Stage04 US-BZS source coordinate failure repaired

Real operator run 2026-10-26: STACK unlimited soft/hard, child inherits, Slurm `PropagateResourceLimits=ALL`: stack **PASS**. Original ten-site Stage01 source collector PASS for US-CMW, US-EML, US-GLE, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, US-ICt. **US-BZS** lacked geolocation (`coords=None,None`) because released BIF did not provide it. Collector then silently fell back to original surface soil Sand/Clay **23.6/26.2 (T4_KEEP_SURFACE)**, contradicting the independently pinned **40.0/8.9 (T3_SOILGRIDS_250M)** in the final 50-site recommendation. Stage02 correctly rejected this mismatch before writing any candidate surface.

Source method already documents the BZS station-specific override `--coords US-BZS:64.6963:-148.3235` ([original Ameriflux_Soil README](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/README.md)).

**[Stage05 BZS ONLY repair/finish ten surfaces](scripts/05_repair_BZS_soilgrids_and_finish_10_surfaces.py)**, source Git blob `fc74aa14eebc64996440f8f55ddb83261b1092e1`: first finds an independently completed, genuine source-checked original full 50-site Stage01 BZS SoilGrids 10-layer row if available; otherwise re-runs the original pinned 50-site soil collector for **US-BZS only** with explicit source-documented coords, expecting tier T3 and original **per-node L1..L10** values whose first five node mean matches 40.0/8.9. It then writes a **new** versioned merged wide CSV replacing exactly the erroneous BZS source row, preserving the nine correct original Stage04 site rows SHA-for-SHA and does NOT overwrite original data or source report. Invokes Stage02 check + build for all ten; per-site HOLDs are printed. Creates independent FIXNC candidate surfdata only; **no CIME model jobs or AD400**.

Stage02 source selection was also improved (Git blob `255890d4efe5aa1a14b424c93b4dc7be63b40889`): prefer original per-site subset-data point surface; if absent, verify the **specific selected original reference surface** in the existing Stage04 `10_RECOMMENDED_SITE_SUMMARY.csv`, or demand a unique on-site original surface, rather than failing solely because one fixed folder name differs.

Do not invent BZS 10-layer values from its 0–30 cm Sand=40 and Clay=8.9 recommendation. If the external SoilGrids service is unreachable and no source-checked prior 50-site 10-layer row exists, Stage05 stops with an explicit evidence HOLD. Organic layers and four Arctic-specific FATES mapping parameterizations remain separate scientific approval gates even if all ten new candidate surfaces build.

### Immediate operator command

```bash
(
 set -euo pipefail
 REV=ffe1fafbb1b2681c5bc3186bd89186a4005f4cab
 BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REV/examples/AmeriFlux_Batch02_10/scripts"
 WORK="$HOME/AMF_Batch02_FIXNC_bootstrap/nc/examples/AmeriFlux_Batch02_10/scripts"
 mkdir -p "$WORK"
 curl -fLsS --retry 3 "$BASE/02_prepare_ten_independent_FIXNC_surface_candidates.py" -o "$WORK/02_prepare_ten_independent_FIXNC_surface_candidates.py"
 curl -fLsS --retry 3 "$BASE/05_repair_BZS_soilgrids_and_finish_10_surfaces.py" -o "$WORK/05_repair_BZS_soilgrids_and_finish_10_surfaces.py"
 test "$(git hash-object "$WORK/02_prepare_ten_independent_FIXNC_surface_candidates.py")" = 255890d4efe5aa1a14b424c93b4dc7be63b40889
 test "$(git hash-object "$WORK/05_repair_BZS_soilgrids_and_finish_10_surfaces.py")" = fc74aa14eebc64996440f8f55ddb83261b1092e1
 python3 -B "$WORK/05_repair_BZS_soilgrids_and_finish_10_surfaces.py" --self-test
 python3 -B "$WORK/05_repair_BZS_soilgrids_and_finish_10_surfaces.py" --repair-build
)
```
