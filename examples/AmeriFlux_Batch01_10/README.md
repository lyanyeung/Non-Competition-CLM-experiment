# AmeriFlux Batch01 — fixed biogeography + no competition, AD400 → Normal400 (planning)

## Status, 24 October 2026

This **new cohort** consists of BR-Ma2, CA-Ca3, CA-Cbo, CA-LP1, CA-Man, CA-TP1, CA-TP3, CA-TP4, US-Aud, and US-Bar. It is **not** the separate European/ICOS `examples/Batch01_10` cohort. Do NOT run the older ten-European-site `11_batch10_AD400_oneclick.py`, `12_batch10_recover_FATES_AD_private_overlay.py`, or `13_batch10_continue_verified_AD395.py` for these AmeriFlux sites; those tools hardcode European site IDs, existing cases, surfaces, model runs, and restarts.

**Confirmed by user IRIDIS6 logs:** the corresponding [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10) completed:
- **Stage80**: final ten-site forcing selected: **18 original half-hour RH<1%** records replaced with native ERA5 internally consistent five-field meteorology; **1,091 original RH 1–5%** and all other Stage75 values retained; four new full station CSVs and six unchanged selected CSVs
- **Stage81**: ten-site **213 annual NetCDF** meteorological files generated, 17,520 half-hour records/year, NOLEAP, 10 legacy DATM XML stream **templates** (not activated)
- **Stage82**: all **213/213** NC files verified by SHA256; sample NetCDF year/time/SHUM variables passed, report at `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/`
- An NL-Loo **recovery folder**, checked as a possible CIME reference, reported `DATM_MODE=1PT`, `CALENDAR=NO_LEAP`, but **`stream_mode=NOT_IDENTIFIED` and no CaseDocs stream files**. Its `DATM_YR_START=2018`, `DATM_YR_END=2019`, `RUN_STARTDATE=1997` are **NL-Loo-specific**, not suitable AmeriFlux assignments.

All ten NetCDFs intentionally **omit ZBOT**. The previous AmeriFlux BASE-height Stage31 metadata yielded five static and three dynamic **provisional sensor-height profiles**; CA-Cbo and CA-Man have multi-layer temperature heights but **no verified crosswalk of FLUXNET TA_F to a specific source sensor**. Stage31 dates for some sites have month/year uncertainty. Do not silently assume 2m or 30m, the WS/EC height, or an upper-canopy TA sensor is the forcing air temperature measurement level.

## Stage10 user-verified solar clock and Stage11 independent UTC forcing preview (25 October 2026)

**Operator-confirmed Stage10 self-test + read-only audit PASS:** unchanged `CA-TP4_AMF_FIXNC_AD400_PILOT` 5-year FATES AD startup, CDEPS `offset=0`, constant `CCSM_CO2_PPMV=363.04` ppm (inherited 1997 NOAA global-mean reference, not purpose-selected for 2002). 2002 global NOAA annual mean **372.58 ppm** is a proposed fixed-spinup common reference, NOT yet applied to this case.

**Solar evidence from the actual pinned CA-TP4 Stage04 FSDS data:**

| Year | Real FSDS energy during astronomical night if labels are LST (UTC−5) | If mistakenly interpreted as UTC |
|---|---:|---:|
| 2002 | 0.212% | 29.099% |
| 2010 | 0.000% | 29.157% |
| 2019 | 0.028% | 29.091% |
| **Three-year mean** | **0.080%** | **29.116%** |

Thus measured source solar radiation **unambiguously follows local standard time (UTC−5)**. CTSM's documented astronomical zenith hour-angle uses the day fraction at **0Z 1 January** and longitude; the real compiled CIME coupler convention still merits review ([CTSM solar technical note](https://escomp.github.io/CTSM/release-clm5.0/tech_note/Surface_Albedos/CLM50_Tech_Note_Surface_Albedos.html)). [CDEPS stream docs](https://escomp.github.io/CDEPS/versions/master/html/streams.html) say a **positive offset advances** timestamps by that number of seconds; `+18000` is a potential direct UTC+5h solution, but with a whole-year cyclic dataset timestamps on Dec31 extend into the following year, and real CDEPS boundary treatment has NOT been validated. The incomplete site-geometry and model-solar-clock release gates remain.

**Safer technical solution — [Stage11 UTC aligned CA-TP4 full-year NetCDF candidate](scripts/11_CA_TP4_build_UTC_aligned_DATM_candidate.py):** 
- `--self-test` checks exact 10-half-hour/5h cyclic mapping across all 22 years; `--check` verifies 22 original Stage04 annual SHA files, new Stage08 non-submitted status/locked original effective inputs, local midpoint time geometry/variables and the candidate CDEPS stream.
- Optional `--build-preview --outdir BRAND_NEW --ack-cyclic-utc-5-shift` writes **22 independent UTC-year NetCDF copies**. Each UTC year uses the previous LST-year's final 10 records for Jan 1 00:15–04:45 UTC and the present LST-year's first 17,510 records for Jan 1 05:15 through Dec31 23:45 UTC. The 2002 cyclic previous year is **2023** (the loop wraps 2023→2002), clearly identified as a **model cyclic-boundary assumption**, *not* a 2001 meteorological observation. ALL 10 time-dependent fields (TBOT, QBOT/SHUM/RH, PSRF, WIND, FSDS, FLDS, PRECTmms, ZBOT) get the *same* exact 10-slot permutation; midpoint `time` itself remains at 00:15/00:45/... in each UTC year.
- Each copied NetCDF is checked against both immutable local-year source files for **all time-dependent values**. The script also recomputes the **UTC astronomical-night FSDS fraction in 2002, 2010 and 2019 after transformation** and stops if any of those years has more than 5% night-time shortwave energy; the detached XML points at the 22 UTC copies and sets `cycle + linear`, `offset=0`. No change to the Stage08 active CIME case, original Stage04 pilot, Stage06 surface, and **no model/Slurm jobs**.
- After Stage11 success, the separate **next step** is to create a **new V2 CIME AD5 case** with the UTC files, explicit 2002 baseline CO2 if selected, valid point geography, generated `preview_namelists` and only then an independent five-year smoke test. Do not mutate/re-run the existing Stage08 `--stage` case; it remains an immutable baseline.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/11_CA_TP4_build_UTC_aligned_DATM_candidate.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/11_CA_TP4_build_UTC_aligned_DATM_candidate.py --check
# Only after PASS and explicit consent: --build-preview --ack-cyclic-utc-5-shift --outdir BRAND_NEW
```

## Stage09 actual read-only PASS; Stage10 solar-diurnal/CO2 review (25 October 2026)

**Operator-confirmed Stage09 PASS:** `CA-TP4_AMF_FIXNC_AD400_PILOT` CIME XML: `DATM_MODE=1PT`, `GRID=a%CLM_USRDAT_l%CLM_USRDAT_oi%null...`, `NO_LEAP`, `ATM_NCPL=48`, `RUN_TYPE=startup`, `RUN_STARTDATE=2002-01-01`, `STOP_N=REST_N=5`, `RESUBMIT=0`, `CLM_ACCELERATED_SPINUP=on`, `DATM_YR_START=2002`, `DATM_YR_END=2023`, `DATM_YR_ALIGN=2002`. CIME `env_case.xml` lock restored; FATES `spinup_state=2`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `finidat` blank; generated CDEPS met stream `CLM_USRDAT.UNSET` maps 8 fields and exactly 22 CA-TP4 pilot NetCDF files 2002–2023 `cycle/linear` `offset=0`; **no CH-Dav met file references**. Four non-meteorology reference streams preserved. First/last CA-TP4 met & surface coordinates **42.7102 N, -80.3574 E** agree. The actual pinned CA-TP4 FLUXNET BIF `d2d7c4fca452031e5da584a8b504084c04757697e436627b0ed7e8fa52b10fa9` records `UTC_OFFSET=-5` (local STANDARD time without DST). The existing CIME point-grid NAME `CLM_USRDAT` and `LND_DOMAIN_FILE=UNSET` **do not independently verify the coupled model's actual solar-clock convention/point geometry**. No Slurm jobs submitted.

**Specific CO2 correction pending:** The inherited `CCSM_CO2_PPMV=363.04` matches NOAA **1997 GLOBAL mean**, a carryover from the 1997-start CH-Dav reference; the NOAA **2002 GLOBAL annual mean is 372.58 ppm** ([NOAA global annual atmospheric CO2 data](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv)). For a 2002-reference fixed CO2 technical spin-up a transparently sourced **372.58 ppm is recommended**, pending explicit model configuration/namelist re-preview and a common ensemble science convention. Never call it measured CA-TP4 tower CO2. Existing Stage08 case was NOT changed at Stage09.

**Next: [Stage10 read-only CA-TP4 FSDS solar LST/UTC diagnostic and CO2 review](scripts/10_CA_TP4_solar_clock_CO2_readonly.py).** A +18000 **seconds** CDEPS `offset` advances FLUXNET UTC-5 time axis to UTC if, and ONLY if, the actual coupled CTSM model solar hour uses UTC. The effective current `offset=0` may be appropriate if the model site clock is deliberately in local standard time. Stage10 scores the proportion of real CA-TP4 2002/2010/2019 shortwave `FSDS` energy coinciding with astronomical night under the LST and UTC interpretations. It verifies Stage08 CaseDocs hashes, case lock and source NC SHA. **This is evidence about observed FSDS phase, not proof of which clock the compiled coupler uses.** It writes nothing and does not submit jobs. Before a model smoke, verify model and station clock/geometry, year-crossing `cycle+linear` stream behavior, explicit CO2 choice; soil and vegetation/28m-height proxies remain unverified field science.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/10_CA_TP4_solar_clock_CO2_readonly.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/10_CA_TP4_solar_clock_CO2_readonly.py --check
```

**Stage10 is read-only; AD5 not submitted.** No resubmission of Stage08 --stage. Do not scale to AD395/Normal400 until validated 5-year pilot & restart triplet and scientific adequacy.

## Stage08 preview CONFIRMED PASS and new Stage09 read-only coupler/solar/CO2 review (25 October 2026)

**Actual user-provided IRIDIS6 run success:** Stage08 `--stage --confirm CREATE_ISOLATED_CA_TP4_AD5_CASE_PREVIEW_NO_SLURM` created independent `/iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_PILOT`. It verified exact source Stage04 (22 annual half-hour CA-TP4 met files, NOLEAP/midpoints, 28m experimental ZBOT), Stage06 separate idealized forest surface (NATVEG100,CROP0,ENF93,DBF7, grid soil) and Stage07 CIME detached plan. The proven PRIVATE CTSM FATES AD build-namelist overlay passed its pinned two-change integrity check; **CIME env_case.xml lock was restored** after preview. The actual *new* `CaseDocs/datm.streams.xml` contained **CA-TP4 2002–2023 22/22 yearly NetCDF, all eight exact met mappings, cycle + linear**; generated `CaseDocs/lnd_in` has **the CA-TP4 separate site-proxy surface, FATES fixed-biogeography/no-competition, `spinup_state=2`**. The operator's Stage08 log confirms **no Slurm jobs submitted**.

**Caution:** The inherited available reference executable was built under a generic `CLM_USRDAT` point grid. Stage08 did not prove that **the coupler's actual point lat/lon/solar-clock origin equals CA-TP4**, nor that a site local-standard-time meteorological series should be treated as clock time in CIME. FLUXNET records are site **local standard time** (without DST) while model clocks / CDEPS stream `offset=0` may have distinct timing conventions. Do **not** arbitrarily add +5h to the CDEPS input axis until actual grid solar-clock/coupler convention, year boundary and cycle interpolation are inspected. The CA-TP4 source BIF `UTC_OFFSET` is the documentary input for this next gate. The reference case's inherited `CCSM_CO2_PPMV=363.04` also may reflect the CH-Dav/1997 baseline, not an independently reviewed 2002 CA-TP4 spinup fixed CO2. The 28m TA_F crosswalk, forest stand proportions and grid soil are clearly marked **technical assumptions only**.

**Stage09 [read-only generated CIME/DATM/FATES/UTC and CO2 release audit](scripts/09_CA_TP4_AD5_readonly_coupling_clock_release_audit.py)** now checks Stage08's non-submitted `PREVIEW_VERIFIED_NOT_SUBMITTED` receipt, all original Stage04/06/07 manifests and actual generated CaseDocs SHA, verifies CIME 5yr AD setup, FATES land flags and actual site forcing series without lingering CH-Dav annual input, examines original BIF `UTC_OFFSET`, prints effective model CO2 setting and available point-domain values. **No CIME/Slurm/report files are written.** Stage09 reports STRUCTURAL PASS separately from SOLAR/CLOCK/CO2 scientific HOLD and is not authorization for AD5 until that review.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/09_CA_TP4_AD5_readonly_coupling_clock_release_audit.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/09_CA_TP4_AD5_readonly_coupling_clock_release_audit.py --check
```

**Do not rerun Stage08 `--stage`**, since the independent case and non-overwritable attempt receipt already exist. AD5 remains **not submitted**, and no 395-year AD continuation or Normal400 has begun.

## Stage07 confirmed complete; Stage08 independent CIME AD5 preview (25 October 2026)

**User-confirmed actual IRIDIS6 Stage07 detached plan SUCCESS**, at:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4/stage07_case_plan_20261025T065233585375346Z/`.

It independently checked the **CA-TP4 Stage04 forcing and Stage06 surface point coordinates `42.7102 N, 279.6426 E`**, CDEPS actual field mapping of all eight required meteorological fields and chronological 2002–2023 annual files, 1PT NO_LEAP 48/day, available CH-Dav FIXNC AD reference `cesm.exe` (`/scratch/ly3n24/CTSM_FATES_OUTPUTS/GF-Guy_FATES_SURF2000_CO2405_1PT/bld/cesm.exe`) and site-specific new `cases/CA-TP4_AMF_FIXNC_AD400_PILOT` / RUN / ARCH paths **all unoccupied**. This plan was detached only: **no active case/Slurm**.

**Stage08 [guarded isolated AD5 CIME clone + actual generated namelist preview, NO SUBMISSION](scripts/08_CA_TP4_create_AD5_CIME_case_preview_no_slurm.py)** now supports:

- `--self-test`: code syntax/stream transformations only
- `--check`: READ ONLY validate all exact Stage04/06/07 manifests, 22 year-file SHA, the existing compiled reference executable, FATES AD private overlay (two pinned bug guards), and actual original `user_nl_datm_streams`. It prints available original stream override keys and tests the CA-TP4-only substitution, including optional user-level `offset=0`.
- `--stage --confirm CREATE_ISOLATED_CA_TP4_AD5_CASE_PREVIEW_NO_SLURM`: create **exactly one new** independent cold-start case via `create_clone --keepexe`, replace **only** `CLM_USRDAT.UNSET` meteorological CDEPS overrides (retaining global aerosol/N deposition/ozone/topography streams), install site-only Stage06 forest-proxy `fsurdat`, explicitly set FATES `fixed_biogeog+nocomp`, `spinup_state=2`, AD decomposer ON, `RUN_STARTDATE=2002-01-01`, `DATM_YR_START=2002`, `DATM_YR_END=2023`, `DATM_YR_ALIGN=2002`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`. It previews using the **existing proven FATES private AD overlay only on the new case** and must restore locked `env_case.xml`; then it checks actual **generated** `CaseDocs/lnd_in` and `CaseDocs/datm.streams.xml` for exact site-specific inputs and SHA-receipts. **No scheduler calls**.
- A **non-overwritable attempt state** is created *before* making a case. **DO NOT rerun `--stage` on failure**; inspect partial case and the attempt ledger first.
- The successful `PREVIEW_VERIFIED_NOT_SUBMITTED` receipt has `ready_to_submit_AD5=False` because site clock/solar geometry, actual domain coupling, scientifically unverified `TA_F→28m` sensor mapping, CO2 baseline and idealized 93:7/grid-soil hypotheses still require review. Preview success **does not authorize 5yr Slurm submission**. Only then can we audit the new case and decide whether to run **ONE** 5-year technical smoke. 400yr AD/Normal jobs stay deferred.

**Important engineering note:** The original `CH-Dav_B01_FIXNC_AD400` is a generic `CLM_USRDAT` 1PT grid with `CLM_USRDAT_NAME=UNSET`. Reusing its compiled executable does **not** prove CA-TP4 geographic/solar geometry. Do not transplant CH-Dav `fsurdat`, input-year range, `CCSM_CO2_PPMV=363.04`, lat/lon or station forcing to CA-TP4; Stage08 reports inherited CO2 as an **unreviewed science blocker** rather than silently claiming it matches CA-TP4 year 2002. Both the FATES height 28m and grid-soil fallback remain *clearly labeled technical assumptions*.

## Stage06 confirmed complete — Stage07 CIME compatibility/read-only case plan (25 October 2026)

**Actual Stage06 IRIDIS6 execution SUCCESS:** versioned independent CA-TP4 `surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc` and `manifest.json` at:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4/surface_stage06_20261025T064625818881201Z/`.

**Verified by operator log:** source SHA256 and local FATES HLM map pass (`CLM NATPFT index 1 → FATES PFT2 needleleaf evergreen extratropical`, `CLM index 7 → FATES PFT6 deciduous broadleaf extratropical`); altered only NATVEG/CROP and CLM natural PFT shares, retaining all ten original gridded sand/clay layers and unrelated NetCDF variables exactly. Input grid NATVEG 43.15406% / CROP 56.84594% was transformed in a **separate scientific pilot surface** to NATVEG100/CROP0/ENF93/DBF7 by the user's explicit model-proxy opt-in. **93:7 is reported tree species mixture, NOT observed ground-area fractions, and original inherited soil is NOT observed site soil.** No previous model, forcing, case or Slurm job was modified or submitted.

**Stage07 [one-site CIME compatibility and detached effective DATM stream override plan](scripts/07_CA_TP4_AD5_CIME_compatibility_plan.py)** follows Stage06. First run `--self-test`, `--check`, then optionally `--plan --outdir NEW_DIR` to create **standalone** `CA-TP4_user_nl_datm_streams.CANDIDATE_NOT_INSTALLED`, `CA-TP4_user_nl_clm_AD5.CANDIDATE_NOT_INSTALLED`, and `manifest.json` in that new reporting folder. It checks the exact two successful Stage04/06 manifests, 22 yearly NetCDF SHAs, candidate CDEPS stream year/cycle/8 variable mappings, **CA-TP4 forcing/surface coordinates**, already-built CH-Dav reference executable and CIME/XML/model AD flags, and rejects unsafely reused site datasets. Crucially, CDEPS `user_nl_datm_streams` uses overrides like `CLM_USRDAT.UNSET:year_first = 2002` and `CLM_USRDAT.UNSET:datafiles = <22 CA-TP4 files>`; the detached Stage04 `CaseDocs`-style XML **must not be manually copied into an active CaseDocs**. No CIME clone, land-model build, Slurm or source-file write is performed at Stage07; isolated new case / real CDEPS and grid/mesh preview will be the *next* step after its actual output is checked.

For the planned AD5 pilot: `RUN_STARTDATE=2002-01-01`, `CALENDAR=NO_LEAP`, `ATM_NCPL=48`, `CLM_ACCELERATED_SPINUP=on`, `FATES spinup_state=2`, `STOP_N=REST_N=5`, `RESUBMIT=0`; 2002–2023 station forcing recycled via `taxmode=cycle`. **Do not copy European reference `DATM_YR_START`/`END`, reference `fsurdat`, grid/domain/mesh or forcing paths.** Even when a binary is reused, it is essential to verify actual new case grid/mesh and site latitude/longitude; the mere existence of a 1PT FATES executable does not certify correct CA-TP4 spatial setup or solar clock.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/07_CA_TP4_AD5_CIME_compatibility_plan.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/07_CA_TP4_AD5_CIME_compatibility_plan.py --check
# optional detached authoring/report, no CIME action:
python3 -B examples/AmeriFlux_Batch01_10/scripts/07_CA_TP4_AD5_CIME_compatibility_plan.py --plan --outdir /brand/new/nonexistent/report/dir
```

**Next gate:** CIME point-grid/mesh and model-local timing. Only after that, create one independent CA-TP4 FATES AD5 cold-start case, inspect real `preview_namelists` via private FATES AD namelist overlay and actual generated `datm.streams.xml` and `lnd_in`, then optionally submit the first five-year smoke. AD395 and independent Normal400 remain deferred until verified 3-component AD5/AD400 restarts.

## Stage05 scientific/CIME input PASS; Stage06 isolated forest-proxy point surface ready (25 October 2026)

**Actual user-confirmed Stage05 read-only PASS**:
- Detached CA-TP4 Stage04 22/22 year NetCDF SHA, sampled +15-min midpoint and provisional 28 m `ZBOT`, actual CDEPS `<file><stream_info>` 2002–2023 `cycle+linear`, eight met field mappings and 22 candidate file paths all PASS. No model jobs and no existing CIME case altered.
- Original CA-TP4 point surface pinned SHA256 `ceaf4ebed72fd5e43e34838f2a360d6524752a631bc925f087af8b7612847748`, landunits **43.154% NATVEG / 56.846% CROP** (LAKE/WETLAND zero). Original gridded CLM natural PFT vector contains mainly C3 grass and broadleaf deciduous tree fractions; these are **grid** fractions, not stand composition.
- Original soil `PCT_SAND` 10 layers **39–43%**, `PCT_CLAY` 10 layers **15–25%**, both **grid-derived**, not site measurements. Published tower **PFT2 93% (white pine 82% + fir 11%), PFT6 7% deciduous broadleaf** is **stand species composition, not observed ground-area cover**. No CA-TP4 independent CIME case exists yet.
- CH-Dav AD technical reference `FATES=.true.`, `use_fates_sp=.false.`, `fixed_biogeog=.true.`, `nocomp=.true.`, land `spinup_state=2`; source 1PT NO_LEAP 48 steps/day and reference stop/rest 5, resubmit 0, **not site-specific inputs**.

**Next:** [Stage06 independent CA-TP4 idealized forest-point surface generator](scripts/06_CA_TP4_build_idealized_forest_surface.py). It first checks the exact input SHA and versioned research stand evidence, verifies the effective local FATES `fates_hlm_pft_map` and then (only on an explicitly acknowledged `--build` to a new directory) writes a **separate, non-production candidate** surface with landunit NATVEG=100%, CROP=0% and model **ENF=93%, DBF=7%**. The HLM CLM natural PFT indices are 1 ENF, 7 DBF, checked against actual FATES PFT slots 2 and 6. **This is a named idealized stand proxy, not observed whole-grid or EC footprint ground fractions**; otherwise the measured 93:7 stand ratio has a different denominator. For this **technical AD5-only pilot**, keep all source soil fields, including the original 10 texture layers, unchanged as `GRID_SOIL_TEXTURE_FALLBACK_NOT_OBSERVED`. The Stage06 tool verifies every unrelated surface variable remains identical to the original and never edits/recreates old surfaces, CIME cases, DATM, restarts or Slurm jobs. Before scientific analyses, independently obtain/approve observed soil, plant cover, height and disturbance/stand age evidence; surface production alone is NOT permission to submit an AD5 case.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/06_CA_TP4_build_idealized_forest_surface.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/06_CA_TP4_build_idealized_forest_surface.py --check
# After the check PASSES, create a NEW versioned technical surface; this is an explicit scientific proxy selection.
python3 -B examples/AmeriFlux_Batch01_10/scripts/06_CA_TP4_build_idealized_forest_surface.py --build \
  --ack-idealized-forest-grid-soil --outdir /absolute/new/nonexistent/output/folder
```

**After Stage06 succeeds:** Build a separate *new* CIME AD5 startup case referencing the Stage04 22-year meteorological pilot and Stage06 distinct surface. Clone only appropriate case-wide machine/binary configuration; never inherit CH-Dav site surface, station years, stream datafiles or site-local clocks. Make `case.setup`, the private FATES AD build-namelist overlay/`preview_namelists`, and validate final generated `CaseDocs/datm.streams.xml` and `CaseDocs/lnd_in` before a **single AD5** submission. Check the original FLUXNET local-standard clock policy against the actual coupler clock; a +15-min midpoint alone does not certify correct solar alignment.

## Stage04 pilot build confirmed SUCCESS; Stage05 pilot-case input gate (25 October 2026)

**Operator-confirmed Stage04 isolated build SUCCESS:** All **22/22** CA-TP4 annual `.nc` files (2002–2023) were independently generated with verified half-hour FLUXNET `TIMESTAMP_START+15min` midpoint coordinates and **ZBOT=28m** labeled **provisional technical proxy only**. An independently checksummed *DETACHED*, unactivated `<file><stream_info>` CDEPS XML candidate and source-provenance `manifest.json` were written to:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z/`

The user verified `PILOT MANIFEST PASS`, `model_case_created=False`, `Slurm_submitted=False`, and `modified_stage81_files=False`. **Original 213 annual Stage81 NetCDF and original cases unchanged.**

**NEXT: [Stage05 CA-TP4 AD5 scientific/CIME input gate](scripts/05_CA_TP4_AD5_case_input_gate.py)**. It reads the exact successful detached Stage04 pilot, all 22 annual SHA files and midpoint/28m samples, the actual stream CDEPS main map, CA-TP4 original point-surface `PCT_NATVEG/PCT_CROP/PCT_NAT_PFT` and `PCT_SAND/PCT_CLAY` layer values, the exact **version-pinned** [AmeriFlux stand evidence](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/649eb960475ff77944e42c559ff1ebbe6d2f1004/examples/AmeriFlux_sites/metadata/Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv) and the already-created CH-Dav fixed-biogeography/no-competition FATES AD reference-case flags. User must download the **pinned evidence TSV beside the Stage05 script**; Stage05 checks its Git blob SHA1 and rejects stale evidence.

CA-TP4 published **PFT2=93% needleleaf evergreen (pine+fir), PFT6=7% deciduous broadleaf** reflect reported tree species mixture and **are NOT independently measured ground-area fractions**. Its original coarse-grid surface has significant crop and should not automatically be used for a tower forest point, or replaced by a made-up observed `NATVEG100`/PFT93:7 surface without an explicitly named forest-point proxy scenario. Stage05 is **read-only** and is a necessary checkpoint before any site-specific surface production, model clone, `preview_namelists` or AD5 job submission.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/05_CA_TP4_AD5_case_input_gate.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/05_CA_TP4_AD5_case_input_gate.py --check
```

**Remaining release gates:** actual coupled-model solar clock/local standard time, scientifically defensible 28m `TA_F` source proxy, tower-specific landunit/PFT area scenario and soil treatment, case-native `datm.streams.xml` placement/`preview_namelists`, independent AD5 cold-start/numerical smoke and restart validation before any AD395/Normal stage.

## Stage04 read-only check confirmed PASS (25 October 2026)

**Operator-confirmed on IRIDIS6:** `04_build_CA_TP4_DATM_midpoint_ZBOT28_pilot.py --self-test` and `--check` **PASS**. All **385,440** CA-TP4 half-hour Stage80 forcing time stamps match exact raw FLUXNET `TIMESTAMP_START` rows 2002–2023; **240** leap-day observations from five leap years skipped for NOLEAP. All **22 annual Stage81 NetCDF** source dimensions and native time axes PASS and reference CH-Dav's effective NetCDF `ZBOT` dimensions match `(time,lat,lon)`. Actual main met CDEPS stream confirms `taxmode=cycle`, `tintalgo=linear`, `QBOT → Sa_shum`, `ZBOT → Sa_z`.

**Next action, with operator choice:** Run `--build-preview --ack-provisional-height --outdir NEW_NONEXISTING_DIR` to create **22 independent** CA-TP4 year-file copies with `time=TIMESTAMP_START+15min` and `ZBOT=28m` from BASE `TA_PI_F_1_1_1` **ONLY AS PROVISIONAL TECHNICAL TEST ASSUMPTION**. The new detached CDEPS XML is a reference-case-derived **candidate, not activated**. This creates **no CIME case, model job, or modified original Stage81 files**. The existing observed-height `TA_F` crosswalk remains unverified. Do not call a successful DATM file build evidence of model correctness, actual local-standard-time alignment to coupled model clock, scientific suitability of 28m, or AD5/AD400 completion.

Before AD5 submission, inspect new stream XML and site-specific surface/soil/PFT; verify actual case `preview_namelists` and correct `spinup_state=2` on private FATES AD build-namelist overlay, calendar `NO_LEAP` and site-specific 2002–2023 forcing cycle. Submit at most one independent AD5 test (`STOP_N=5`, `REST_N=5`, `RESUBMIT=0`) and verify archived CLM/CPL/DATM restarts before AD395.

## Stage03 user-confirmed successful — Stage04 isolated CA-TP4 DATM pilot next (24 October 2026)

**Observed Stage03 results:**
- CA-TP4 BASE TA sensors explicitly include `TA_1_1_1 = 28m`, `TA_1_2_1 = 14m`, `TA_1_3_1 = 2m`, plus `TA_PI_F_1_1_1 = 28m` in official 2026-09-08 source snapshot. All lack dated relocations. The **scientific mapping to the combined FLUXNET `TA_F` variable has not been proven**, so 28m is a defensible **provisional technical test option**, not a verified height or permission for science production.
- Stage80 selected CSV first times `2002-01-01 00:00`, `00:30`, `01:00`, while official original `FLUXMET_HH` records have `TIMESTAMP_START=200201010000`/`END=200201010030` etc. Stage81 unchanged time coordinates begin at `0, 1/48, 2/48` **days**. FLUXNET documentation says HH records carry both explicit start/end and are **site local standard time**. Thus a CDEPS `tintalgo=linear` native-time midpoint candidate requires **+15 minutes**, but the complete 22-year per-record provenance and coupler local-clock behavior need checking first.
- Actual CH-Dav FIXNC AD reference `CaseDocs/datm.streams.xml` is `<file><stream_info>`, first stream `taxmode=cycle`, `tintalgo=linear`, `mapalgo=none`, `year_first=1997`, `year_last=2025`, `year_align=1997`, `offset=0`. The model mapping includes **`QBOT Sa_shum`** and **`ZBOT Sa_z`** with `PRECTmms`, `FSDS`, `TBOT`, `WIND`, `PSRF`, `FLDS`. Stage81 already contains `QBOT` and `SHUM`, but lacks `ZBOT`, and its simple `<streamstemplate>` is **not** the case's effective CDEPS XML schema. Ancillary aero/N deposition/ozone/topo streams also appear in the effective reference case.

**[Stage04: CA-TP4 isolated DATM midpoint + provisional 28m ZBOT candidate](scripts/04_build_CA_TP4_DATM_midpoint_ZBOT28_pilot.py)** is now available; it must **first pass `--check`** across the entire selected Stage80 CSV and original FLUXNET HH timestamp ledger, validate the CDEPS reference variable/dimension schema, and verify 22 original Stage81 NC SHA256s. If no discrepancies, an explicitly requested `--build-preview --ack-provisional-height --outdir NEW` makes 22 isolated copied/modified CA-TP4 annual NCs with midpoint `time`, provisional `ZBOT=28m`, and a **DETACHED** real-format 5-stream XML candidate. Neither original Stage81 NetCDF nor any active case/streams/jobserver/Slurm is changed; **this is NOT an AD5 submission**.

Keep site-PFT/soil/landunit and exact DATM case build / preview gates separate; do NOT submit a 5-year AD smoke until actual target `lnd_in`, `datm_in`, streams and timer fields are verified. Prior European Batch01 staged/recovery scripts are not transferable unchanged.

## Stage02 user-confirmed successful; Stage03 next (24 October 2026)

**User confirmed that Stage02 self-test and read-only actual CH-Dav reference inspection pass.**

- **CA-TP4 candidate ZBOT** is **28.0 m, STATIC**, from official BASE variable `TA_PI_F_1_1_1`, no documented height events; its equivalence to FLUXNET `TA_F` remains `UNVERIFIED`. Other 8 candidate/blocked station details are in Stage02 output; CA-Cbo and CA-Man remain BLOCKED.
- The real, already-existing `CH-Dav_B01_FIXNC_AD400` has `DATM_MODE=1PT`, `CALENDAR=NO_LEAP`, `ATM_NCPL=48`, `CLM_ACCELERATED_SPINUP=on`, `STOP_N=5`, `REST_N=5`; effective land namelist records `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `spinup_state=2`. Its `RESUBMIT=19` and `DATM_YR_START=2018`, `DATM_YR_END=2019` are **reference values only** and must never be blindly assigned to CA-TP4.
- The **actual** `CaseDocs/datm.streams.xml` is an XML `<file><stream_info ...>` with `taxmode=cycle`, `tintalgo=linear`, `year_first=1997`, `year_last=2025`, `year_align=1997` and explicitly listed annual NetCDF files. This differs from the Stage81 **legacy `<streamstemplate>` prototype**; it cannot be copied into an actual CDEPS case as-is. Do not assume CIME XML DATM_YR settings override the effective generated `stream_info` years.
- The successful 213-file Stage81 NetCDF source labels are **unchanged native half-hour timestamps**; Stage81 did NOT independently prove whether they are interval starts, ends or midpoints, nor the model-to-local time relationship. For `linear` forcing interpolation, source time support and an appropriate offset must be established before active model use.

**[Stage03: read-only real CA-TP4 TA height metadata + raw FLUXNET timestamp/NetCDF axis + actual stream datavars](scripts/03_CA_TP4_height_clock_DATM_stream_readonly.py)** is the immediate next step; it does **not** rewrite NetCDF, create a case, assign ZBOT as verified, or submit Slurm. It shows the precise remaining choice before an independent CA-TP4 AD5 smoke.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/03_CA_TP4_height_clock_DATM_stream_readonly.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/03_CA_TP4_height_clock_DATM_stream_readonly.py --check
```

**Still not authorized:** AD400 bulk submissions, AD395 continuations, Normal branch and model run until time/stream domain/ZBOT and site surface/PFT/soil case inputs are appropriately validated.

## Stage01 user-confirmed successful; Stage02 next (24 October 2026)

The user executed `01_audit_AD400_inputs_readonly.py --check` with **PASS**. Stage80(18 RH<1 replacements) → Stage81(213 annual NC) → Stage82(213/213 SHA) chain verified. Original Stage31 exact report exists: `reports/stage31_provisional_ZBOT_scenarios_20261022T022341481986Z/`.

**Stage31 actual ZBOT status:** 5 static candidates (BR-Ma2, CA-Ca3, CA-LP1, CA-TP4, US-Bar); 3 dynamic candidates (CA-TP1, CA-TP3, US-Aud); and 2 blocked multi-level TA stations (CA-Cbo, CA-Man). **All eight candidates still report TA_F source-sensor crosswalk=UNVERIFIED**, so no approved height should be inserted into model as an observed fact.

The Stage01 preflight found numerous real completed-style European CIME case directories with `CaseDocs/datm_in`, `CaseDocs/datm.streams*` and `CaseDocs/lnd_in`, including `/iridisfs/scratch/ly3n24/CLM_FATES/cases/CH-Dav_B01_FIXNC_AD400`. These are better reference-config candidates than the prior NL-Loo recovery folder which lacked recognized stream documents.

**Run new [Stage02 read-only exact ZBOT + real DATM/FATES case inspection](scripts/02_inspect_ZBOT_DATM_AD5_reference_readonly.py)** to expose CA-TP4's actual candidate BASE TA height, source variable and any dated events, and the true CH-Dav case `datm_in`, stream, CIME clock and land namelist flags. It does not change cases or generate DATM; European site parameters are reference-only.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/02_inspect_ZBOT_DATM_AD5_reference_readonly.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/02_inspect_ZBOT_DATM_AD5_reference_readonly.py --check \
  --reference-case /iridisfs/scratch/ly3n24/CLM_FATES/cases/CH-Dav_B01_FIXNC_AD400
```

After source ZBOT, stream format/time centering, appropriate point domain, AmeriFlux site PFT and observed/fallback soil are explicitly chosen, prepare **one independent CA-TP4 AD5 smoke case only**. Do not stage or submit a ten-site AD400 job now.

## Plan: do NOT submit AD400 yet

1. Run [AmeriFlux-specific read-only Stage01](scripts/01_audit_AD400_inputs_readonly.py): provenance-link Stage80→Stage81→Stage82, find latest Stage31 provisional ZBOT evidence if it exists on IRIDIS6, and list potentially **complete CIME reference cases**. This script DOES NOT resolve heights or create a case.
2. Determine **ZBOT**: map actual source data contributing to `TA_F` (and possibly wind height treatment) to BASE TA measurement height and effective date at **each** site; accept static/dynamic policy only with explicit provenance. Prioritize a pilot with a single unambiguous height and site-specific PFT parameters. Multi-level CA-Cbo/CA-Man must be held for scientific approval, or use a separately named and justified **proxy ZBOT sensitivity**, not a falsely verified observation.
3. Inspect an actual working CIME case with a populated `CaseDocs/datm_in`, effective DATM streams and `CaseDocs/lnd_in`: determine `DATM_MODE` vs CDEPS, `taxmode=cycle` (avoid accidental permanent end-record `extend`), correct domain file, meterological field mappings and units, year cycling, `RUN_STARTDATE`, and 30-min **TIMESTAMP_START/midpoint interpretation**. The Stage81 timestamp is a source-local half-hour label, *not* an independently verified coupler midpoint. The XML stream **templates cannot be activated as-is** and remain separate from the model.
4. Create a new **AmeriFlux Batch01 isolated case for one site only** with a site-appropriate surface, ecotype and PFT-to-FATES mapping, and soil treatment. The original European `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.` experimental configuration can be used as a **mode reference**; the old ten-site forest-only `PCT_NATVEG=100` and ENF/DNF/DBF/EBF array **are not appropriate general defaults for tropical BR-Ma2 or grassland US-Aud**.
5. Preview generated DATM and land namelists from that actual isolated case. Validate actual physics and forcing timesteps, domain, ZBOT, `ATM_NCPL=48`, CIME `CALENDAR=NO_LEAP`, and `CLM_ACCELERATED_SPINUP=on` with **FATES land `spinup_state=2`** before any job.
6. Only then submit **one independent 5-year AD smoke** (`STOP_N=5`, `REST_N=5`, `RESUBMIT=0`), check BOTH Slurm run + archive success, CLM/DATM/CPL restart triplet, correct model `spinup_state=2`, and biological/soil stability. If successful, a guarded continuation of **395 AD years** gives AD400.
7. At fully verified AD400 checkpoint, build a **separate Normal hybrid case** with accelerated decomposition OFF, verify Normal `spinup_state=0` in namelist/restart, run a **separate Normal5 smoke**, then guarded Normal395. Never flip AD vs Normal within an active resubmitting case.

Per the [standard project protocol](../../docs/AD400_NORMAL400_PROTOCOL.md), per-site total is 400 AD + 400 Normal = 800 model years with a repeated vetted station forcing loop and fixed documented spinup CO2, not a chronological historical simulation or proof of convergence. No 50-year Normal pre-spinup is included. Validate C/N, vegetation, water and GPP/NEE drift after completion. PFT mixtures, soil and other ecological decisions must be independently adapted to the AmeriFlux station evidence rather than copied from the European-site example.

### Read-only first command on IRIDIS6

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
python3 -B examples/AmeriFlux_Batch01_10/scripts/01_audit_AD400_inputs_readonly.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/01_audit_AD400_inputs_readonly.py --check
```

**Model runs submitted by this workflow: 0. All original DATM and CIME files remain unchanged.**
