# AmeriFlux Batch01 — fixed biogeography + no competition, AD400 → Normal400 (planning)

## Status, 24 October 2026

This **new cohort** consists of BR-Ma2, CA-Ca3, CA-Cbo, CA-LP1, CA-Man, CA-TP1, CA-TP3, CA-TP4, US-Aud, and US-Bar. It is **not** the separate European/ICOS `examples/Batch01_10` cohort. Do NOT run the older ten-European-site `11_batch10_AD400_oneclick.py`, `12_batch10_recover_FATES_AD_private_overlay.py`, or `13_batch10_continue_verified_AD395.py` for these AmeriFlux sites; those tools hardcode European site IDs, existing cases, surfaces, model runs, and restarts.

**Confirmed by user IRIDIS6 logs:** the corresponding [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10) completed:
- **Stage80**: final ten-site forcing selected: **18 original half-hour RH<1%** records replaced with native ERA5 internally consistent five-field meteorology; **1,091 original RH 1–5%** and all other Stage75 values retained; four new full station CSVs and six unchanged selected CSVs
- **Stage81**: ten-site **213 annual NetCDF** meteorological files generated, 17,520 half-hour records/year, NOLEAP, 10 legacy DATM XML stream **templates** (not activated)
- **Stage82**: all **213/213** NC files verified by SHA256; sample NetCDF year/time/SHUM variables passed, report at `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/`
- An NL-Loo **recovery folder**, checked as a possible CIME reference, reported `DATM_MODE=1PT`, `CALENDAR=NO_LEAP`, but **`stream_mode=NOT_IDENTIFIED` and no CaseDocs stream files**. Its `DATM_YR_START=2018`, `DATM_YR_END=2019`, `RUN_STARTDATE=1997` are **NL-Loo-specific**, not suitable AmeriFlux assignments.

All ten NetCDFs intentionally **omit ZBOT**. The previous AmeriFlux BASE-height Stage31 metadata yielded five static and three dynamic **provisional sensor-height profiles**; CA-Cbo and CA-Man have multi-layer temperature heights but **no verified crosswalk of FLUXNET TA_F to a specific source sensor**. Stage31 dates for some sites have month/year uncertainty. Do not silently assume 2m or 30m, the WS/EC height, or an upper-canopy TA sensor is the forcing air temperature measurement level.

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
