# AmeriFlux Batch01 — fixed biogeography + no competition, AD400 → Normal400 (planning)

## Status, 24 October 2026

This **new cohort** consists of BR-Ma2, CA-Ca3, CA-Cbo, CA-LP1, CA-Man, CA-TP1, CA-TP3, CA-TP4, US-Aud, and US-Bar. It is **not** the separate European/ICOS `examples/Batch01_10` cohort. Do NOT run the older ten-European-site `11_batch10_AD400_oneclick.py`, `12_batch10_recover_FATES_AD_private_overlay.py`, or `13_batch10_continue_verified_AD395.py` for these AmeriFlux sites; those tools hardcode European site IDs, existing cases, surfaces, model runs, and restarts.

**Confirmed by user IRIDIS6 logs:** the corresponding [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10) completed:
- **Stage80**: final ten-site forcing selected: **18 original half-hour RH<1%** records replaced with native ERA5 internally consistent five-field meteorology; **1,091 original RH 1–5%** and all other Stage75 values retained; four new full station CSVs and six unchanged selected CSVs
- **Stage81**: ten-site **213 annual NetCDF** meteorological files generated, 17,520 half-hour records/year, NOLEAP, 10 legacy DATM XML stream **templates** (not activated)
- **Stage82**: all **213/213** NC files verified by SHA256; sample NetCDF year/time/SHUM variables passed, report at `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/`
- An NL-Loo **recovery folder**, checked as a possible CIME reference, reported `DATM_MODE=1PT`, `CALENDAR=NO_LEAP`, but **`stream_mode=NOT_IDENTIFIED` and no CaseDocs stream files**. Its `DATM_YR_START=2018`, `DATM_YR_END=2019`, `RUN_STARTDATE=1997` are **NL-Loo-specific**, not suitable AmeriFlux assignments.

All ten NetCDFs intentionally **omit ZBOT**. The previous AmeriFlux BASE-height Stage31 metadata yielded five static and three dynamic **provisional sensor-height profiles**; CA-Cbo and CA-Man have multi-layer temperature heights but **no verified crosswalk of FLUXNET TA_F to a specific source sensor**. Stage31 dates for some sites have month/year uncertainty. Do not silently assume 2m or 30m, the WS/EC height, or an upper-canopy TA sensor is the forcing air temperature measurement level.

## Stage21 — CA-TP4 AD5 VERIFIED; recommended PFT adopted; AD5 → AD395 → Normal400 controller (26 October 2026)

**CA-TP4 AD5 succeeded** (operator CaseStatus): `model execution success`, `case.run success 4732088`, `st_archive success 4732089`; archived restart `2007-01-01-00000`. The PTS correction worked, and the run passed the Leung_2023 Prigent dust ESMF mesh read (`use_prigent_roughness = .true.`).

**Operator log 26 Oct 2026 ~03:50 UTC:**
- **CA-TP4 AD395 is running**, ledger `AD395_SUBMITTED`. The first continuation segment was 4734365/4734366, submitted 03:07. Four 5-year segments have completed `0:0`, and the latest restart is `2027-01-01-00000`; 4734553 was running with `RESUBMIT=74`. The final AD restart will be 2402. A later `continue-ad395` HOLD ("AD jobs still queued") was the guard correctly refusing a duplicate. Do not resubmit.
- **BR-Ma2, CA-Ca3 and CA-LP1 AD5 passed the audit** with `spinup_state=2` and the recommended PFT gate. Final AD5 restarts: BR-Ma2 2004, CA-Ca3 2006, CA-LP1 2012. `continue-ad395 --sites BR-Ma2 CA-Ca3 CA-LP1` was run, and AD395 handoff folders exist for all three. First AD395 segments (status 03:53 UTC, all RUNNING with archive PENDING): BR-Ma2 4734578/4734579, CA-Ca3 4734580/4734581, CA-LP1 4734582/4734583.
- Next: `audit-ad400` once each chain finishes, then `stage-normal`.

**26 Oct 16:44 UK: interrupted Normal staging.**
- CA-Ca3 and CA-LP1 AD400 passed the audit: 80 + 80 jobs, restarts 2401 and 2407, `spinup_state=2`.
- Their `stage-normal` was interrupted by an SSH disconnect. Both ledgers are left at `STAGE_ATTEMPTED_UNCERTAIN`, with a partial `*_NORMAL400_UTC_V2_PTS` case. No Normal job was submitted. The guard correctly refused `submit-normal5`.
- Recovery uses two new actions. Run `inspect-interrupted` first (read only). It proves the phase, that nothing is queued, and that there is no Slurm accounting and no Normal archive for the Normal case.
- Then `restage-interrupted --sites ... --confirm QUARANTINE_INTERRUPTED_NORMAL_STAGE_AND_RESTAGE_NO_SLURM` moves the partial case, run directory and ledger to `Stage21_AD400_NORMAL400/quarantine_interrupted_stage/<site>_<UTC>/`, writes a receipt, and stages again. It never submits to Slurm. A mock test covers this, including the Slurm-accounting and phase gates.
- Run long steps inside `tmux`.

**PFT inputs for all ten sites now follow** [RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv), copied for Batch01 to [data/amf_batch01_recommended_pft_20261026.csv](../../data/amf_batch01_recommended_pft_20261026.csv). These are model hypotheses, not observations.

| Site | Recommended (FATES) | Host `PCT_NAT_PFT` | FIXNC state |
| --- | --- | --- | --- |
| CA-TP4 | ENF 93 / DBF 7 | 1:93, 7:7 | Surface/case built; **AD5 verified** |
| BR-Ma2 | Tropical EBF 100 | 4:100 | Surface/case built; AD5 not yet submitted |
| CA-Ca3 | ENF 100 | 1:100 | Surface/case built; AD5 not yet submitted |
| CA-LP1 | ENF 100 | recommended 2:100; built 1:100 | Built surface is **FATES-identical** (HLM 1 and 2 both map solely to `needleleaf_evergreen_extratrop_tree`); AD5 not yet submitted |
| US-Bar | ENF 17 / DBF 83 | 1:17, 7:83 | PFT now resolved (3% residual → ENF); forcing ready; **surface and case not built** |
| CA-TP1 | ENF 100 | 1:100 | Blocked: dynamic ZBOT undecided |
| CA-TP3 | ENF 99 / DBF 1 | 1:99, 7:1 | Blocked: dynamic ZBOT undecided |
| US-Aud | C4 70 / bare 30 | 0:30, 14:70 | Blocked: dynamic ZBOT undecided. Bare ground is technically supported (Batch03 IL-Yat BARE52 completed AD400) |
| CA-Cbo | ENF 18.6 / DBF 81.4 | 1:18.6, 7:81.4 | Blocked: multi-level TA source for ZBOT |
| CA-Man | ENF 100 | 2:100 | Blocked: multi-level TA source for ZBOT |

**[Stage21 Lane A controller](scripts/21_laneA_AD400_NORMAL400_controller.py)** ports the Batch03 workflow (AD400 10/10, Normal5 10/10 on IRIDIS6) to CA-TP4, BR-Ma2, CA-Ca3 and CA-LP1:

- **PFT gate:** before every stateful action, the case's actual `fsurdat` is mapped through the pinned `fates_hlm_pft_map` and must reproduce the recommended FATES fractions and bare share, with NATVEG = 100.
- **Stack guard:** every submission requires `ulimit -s` ≥ 65536 KB. Stage18/20 had no such guard; CA-TP4 passed only because it was submitted from a high-stack shell.
- **Actions:** `submit-ad5` (three sites; CA-TP4 is refused) → `audit-ad5` → `continue-ad395` (`RESUBMIT=78`) → `audit-ad400` → `stage-normal` (independent hybrid `<site>_AMF_FIXNC_NORMAL400_UTC_V*_PTS` from the Y+400 restart, `spinup_state` removed, unpatched CTSM, DATM streams checked identical to AD) → `submit-normal5` → `audit-normal5` → `continue-normal395` → `audit-normal400`.
- **Safety:** attempt-before-submit ledgers under `.../AmeriFlux_Batch01_10/Stage21_AD400_NORMAL400/`. A mock run (fake CIME/Slurm/NetCDF) covers the full chain and every HOLD path.

## Stage20 real corrected CA-TP4 AD5 submitted: 4732088 run / 4732089 archive (25 October 2026)

**Actual user-provided CIME output:** `Check case OK`; `case.submit --skip-preview-namelist` successfully submitted the **corrected** `CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5` case, **run Slurm job 4732088**, dependent **short-term archive job 4732089**. This is distinct from the retired, failed original `4728206/4728207` pair. The successful one-time submission guard was passed, including exact original `fsurdat` `PTS_LAT=42.7102` / `PTS_LON=279.6426`, exact effective CaseDocs and RUNDIR `scol_lat/scol_lon`, and original forcing years and CO2.

**No verified model progress or restart supplied yet.** Do not mark as 5yr AD5 success, submit again, extend AD395, or automatically start BR-Ma2/CA-Ca3/CA-LP1. Check actual job and log outputs:
```bash
sacct -j 4732088,4732089 --format=JobID,JobName%48,State,Elapsed,ExitCode,MaxRSS
tail -40 /iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5/CaseStatus
```

**Independent parallel task:** user asked to address the six remaining unassigned **ICOS** PFT entries in the separately maintained 38-station evidence register, not the six outstanding *AmeriFlux* Batch01 stations. This is now recorded in [`../ICOS_Unassigned_6/README.md`](../ICOS_Unassigned_6/README.md): four C3 grass model candidates, ES-Agu bare+grass+shrub conditional proposal, and GL-ZaH Arctic shrub site-only private FATES map candidate. No ICOS six-site case or Slurm model job has been created.

## Stage20 operator-verified four corrected cases PASS (25 October 2026)

**Actual IRIDIS6 operator log confirms all four Stage20 corrected case previews were CREATED and separately `--verify` validated (4/4 PASS, no Slurm jobs):**
- `CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5`: `PTS_LAT=42.7102`, `PTS_LON=279.6426`, 22 annual UTC met files, CO2 372.58 ppm.
- `BR-Ma2_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`: `PTS_LAT=-2.6091`, `PTS_LON=299.7907`, 18 annual UTC met files, CO2 367.79 ppm.
- `CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`: `PTS_LAT=49.5346`, `PTS_LON=235.0996`, 24 annual UTC met files, CO2 370.57 ppm.
- `CA-LP1_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`: `PTS_LAT=55.1119`, `PTS_LON=237.1586`, 18 annual UTC met files, CO2 382.90 ppm.

Each site's PTS values are read directly from the original site-specific `fsurdat` `LATIXY/LONGXY`, matching its forcing. **Actual `CaseDocs/nuopc.runconfig` AND effective `RUNDIR/nuopc.runconfig` `scol_lat/scol_lon` independently matched the original site surface for all four.** CIME env-case locks were restored and the existing FATES accelerator/fixed-biogeography/no-competition input was preserved through private-AD namelist preview. No updated original case/forcing/surface, no model recompilation, no new Slurm jobs. This resolves the specific previously established **CH-Dav PTS geometry mismatch** at input/configuration level; model success still awaits a real run.

The user has already performed:
```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/20_fix_4site_PTS_from_surface_and_submit_CA_TP4.py --stage --site all --confirm FIX_FOUR_AMERIFLUX_PTS_FROM_SURFACE_PREVIEW_NO_SLURM
python3 -B examples/AmeriFlux_Batch01_10/scripts/20_fix_4site_PTS_from_surface_and_submit_CA_TP4.py --verify
```
**Do not repeat `--stage`** (the new case and one-time attempt receipts already exist). The next step is an **opt-in single real AD5 smoke submission of only the corrected CA-TP4**:
```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/20_fix_4site_PTS_from_surface_and_submit_CA_TP4.py --submit-ca-tp4 --confirm SUBMIT_FIXED_CA_TP4_ONE_AD5_SKIP_PREVIEW
```
This will invoke `case.submit --skip-preview-namelist` exactly once with a new independent one-time job-attempt ledger. Submission has **NOT YET been reported** in operator's Stage20 pasted output. It does not touch BR-Ma2, CA-Ca3, CA-LP1 and cannot be taken as a verified AD5 completion; after submission, inspect Slurm job ID, actual logs, 2007 restart and archiving before the remaining AD395/Normal400.
 
## Stage19 conclusive CIME point mismatch; Stage20 new four-case PTS repair (25 October 2026)

**Operator directly confirmed actual CIME + runtime NUOPC** from failed CA-TP4 and original CH-Dav case: both carry `PTS_LAT=46.81533` `PTS_LON=9.85591` with `PTS_DOMAINFILE=UNSET`; effective `run/nuopc.runconfig` and `CaseDocs/nuopc.runconfig` each carry `scol_lat=46.81533, scol_lon=9.85591, single_column_lnd_domainfile=UNSET`. But CA-TP4 source surface is **`LATIXY=42.7102, LONGXY=279.6426`** and UTC forcing matches exactly. The model `lnd.log.4728206.261025-091434` shows actual error **`rmaxlon=269.786690000000`, `rmaxlat=4.10513000000000` degrees**, abort `surfrdMod.F90:122` threshold 0.001°. **CA-TP4 source case still inherits CH-Dav point coordinates**; no remaining doubt about root cause. Dataset auxiliary variable `lat/lon` (grid center metadata) does NOT substitute for the actual `LATIXY/LONGXY` site point variables.

**Immediate scientifically controlled remedy requested by operator:** set each station's `PTS_LAT` and `PTS_LON` from **its own original, site-specific idealized surface's `LATIXY/LONGXY`**, not from other stations or 0.9° grid-center metadata. Do NOT regenerate 82 yearfiles, change 4 surfaces, or rebuild CTSM/FATES.

**[Stage20 four-site PTS correction + guarded single CA-TP4 AD5 smoke](scripts/20_fix_4site_PTS_from_surface_and_submit_CA_TP4.py)**:
- `--self-test`: no filesystem dependencies; `--check`: strict **read-only** inspection of old four case receipts, actual surface-vs-UTC met coordinates, 8 met mappings and zero preexisting corrected case destinations.
- `--stage --site all --confirm FIX_FOUR_AMERIFLUX_PTS_FROM_SURFACE_PREVIEW_NO_SLURM`: creates four **brand-new versioned case clones** from their previously preview-validated site-specific CIME configurations and shared `--keepexe` binary. Sets the true `PTS_LAT/LON` values from the copied site surface, retains `PTS_DOMAINFILE=UNSET`, and gives each independent `RUNDIR/DOUT_S_ROOT`. Uses temporary previously proven private FATES AD build-namelist overlay **only during CIME `preview_namelists`** and restores locked original CTSM root afterward. Aborts unless **both actual generated `CaseDocs/nuopc.runconfig` AND live `RUNDIR/nuopc.runconfig` `scol_lat/lon` match surface to 0.0001°, plus original 1PT CDEPS fields/site-only source-year paths, effective FATES 5yr accelerated spinup, and on-disk runtime namelists. Each case has a **create-only attempt receipt**; never rerun failed stages blindly. **No Slurm submissions in staging**.
- New names: `CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5`, `BR-Ma2_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`, `CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`, `CA-LP1_AMF_FIXNC_AD400_UTC_V2_PTS_AD5`. Existing failed CA-TP4 and 3 older successful-preview case folders are PRESERVED, as are all NetCDF forcing and surface assets.
- `--verify` checks all four new runtime CIME configurations read-only. `--submit-ca-tp4 --confirm SUBMIT_FIXED_CA_TP4_ONE_AD5_SKIP_PREVIEW` is a **REAL, once-only Slurm model submission for corrected CA-TP4 only**, after new geometry/previews pass. Uses `case.submit --skip-preview-namelist` to preserve the private FATES AD generation, checks no restart/source duplicate jobs, and writes an irrevocable attempted-submission stamp first. It neither starts AD395/Normal400 nor starts the other three sites. Once submitted, Slurm job ID, `CaseStatus`, actual coupler geometry and 5yr restart must be checked before extending.

**NOTE:** The original Stage12/16/17 successful preflight was **insufficient** because it checked met-vs-surface, not effective **CIME `PTS_LAT/LON`**. Stage20 adds precisely this missing CIME geometry gate. Original failing job **4728206** and archive job **4728207** remain historical evidence and MUST NOT be resubmitted. The scientific TA_F sensor-height ZBOT, idealized stand fractional cover and grid soil remain provisional and are not corrected by PTS.

## Stage19 operator results: inspect inherited PTS_LAT / PTS_LON first (25 October 2026)

**Operator-supplied 2026-10-25 09:36 actual Stage19 geometry output:** `STAGE19 SELF-TEST PASS`, no writes, failed `CA-TP4` point `fsurdat` `LATIXY=42.7102`, `LONGXY=279.6426`; Stage11 UTC forcing **LATIXY/LONGXY identical** (0.00000° discrepancy). However the source forest surface also retains **grid-coordinate variables** `lat=42.8795811518324`, `lon=280.0`, different from tower centre. The CH-Dav original-template `fsurdat` has `LATIXY=46.81533`, `LONGXY=9.85591` and its own `lat=46.6492146596858`, `lon=10.0`. CA-TP4 surface-vs-CH-Dav original centre delta **4.10513° latitude**, **90.21331° longitude**.

**Actual CLM component log** `lnd.log.4728206.261025-091434` line 6511 identifies `check_domain_attributes surface lon_var=LONGXY lat_var=LATIXY`; line 6512 prints `ERROR: surface dataset vs. land domain lon/lat mismatch error`. The numeric `rmaxlon,rmaxlat` are likely emitted on an immediately following Fortran list-directed line, previously omitted by the Stage19 keyword filter. `nuopc.runconfig` effective `mesh_lnd=UNSET`, `single_column_lnd_domainfile=UNSET`, source `DATM_MODE=1PT`; global auxiliary DATM and dust mesh references are unrelated to determining the main **1pt** land domain. *Do not* infer a land-domain source from the different metadata variables `lat/lon` alone.

**PINNED SOURCE PROOF FOUND after reading Stage19 results:** CTSM `d5ea9d0` [`src/cpl/nuopc/lnd_comp_nuopc.F90` lines 423–459 and 647–649](https://github.com/ESCOMP/CTSM/blob/d5ea9d0/src/cpl/nuopc/lnd_comp_nuopc.F90#L423-L459) reads `scol_lon/scol_lat` from CMEPS coupler `NUOPC_CompAttributeGet`, then initializes `ldomain%lonc/latc` through `lnd_set_decomp_and_domain_for_single_column`. Pinned [`src/cpl/share_esmf/lnd_set_decomp_and_domain.F90` lines 397–401](https://github.com/ESCOMP/CTSM/blob/d5ea9d0/src/cpl/share_esmf/lnd_set_decomp_and_domain.F90#L397-L401) assigns **`ldomain%lonc(1)=scol_lon`**, **`ldomain%latc(1)=scol_lat`** in 1pt mode. CMEPS [`cime_config/namelist_definition_drv.xml`](https://github.com/ESCOMP/CMEPS/blob/main/cime_config/namelist_definition_drv.xml) explicitly maps `scol_lon` ← CIME `PTS_LON` and `scol_lat` ← CIME `PTS_LAT`, and `single_column_lnd_domainfile` ← `PTS_DOMAINFILE`.

**Likely actual error in our CIME case creation**: Stage08/12 copied **CH-Dav** case to CA-TP4 but `xml_settings()` does NOT update `PTS_LAT` or `PTS_LON`. Stage16 then cloned that CA-TP4 template for BR-Ma2/CA-Ca3/CA-LP1 and likewise did NOT update `PTS_LAT/LON`. Therefore **ALL FOUR independently previewed AmeriFlux cases require explicit CIME `PTS_LAT/LON` verification and likely new correctly located case clones**, even though all four pass original data and CaseDocs SHA gates. The 3 Stage16 cases are **HOLD — DO NOT SUBMIT** until their effective `scol_lat/scol_lon` agree with their actual original site `LATIXY/LONGXY` to **0.001°**. A successful preview is not sufficient.

**Immediate single operator read-only command, no further meteorology QC:**
```bash
CA=/iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5
REF=/iridisfs/scratch/ly3n24/CLM_FATES/cases/CH-Dav_B01_FIXNC_AD400
RUN=/scratch/ly3n24/CTSM_FATES_OUTPUTS/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5/run
for C in "$CA" "$REF"; do
  echo "=== $C ==="
  (cd "$C" && for KEY in PTS_LAT PTS_LON PTS_DOMAINFILE; do printf "%s = " "$KEY"; ./xmlquery "$KEY" --value; done)
done
grep -niE 'scol_lat|scol_lon|single_column_lnd_domainfile' "$RUN/nuopc.runconfig" "$CA/CaseDocs/nuopc.runconfig"
sed -n '6505,6516p' "$RUN/lnd.log.4728206.261025-091434"
```

**Do not alter old `fsurdat` or `CaseDocs`/run inputs or resubmit job 4728206**; preserve Stage18 one-time receipt and failed case for provenance. Do not generate or guess a new mesh until exact `PTS`/effective coupler data are confirmed. If they inherited CH-Dav, create **new versioned CA-TP4 case** with correct `PTS_LAT=42.7102`, `PTS_LON=279.6426`, `PTS_DOMAINFILE` consistent with point mode, and add the same guard to the future 3 LaneA case clones before any pilot submission. Revalidate effective `nuopc.runconfig` and surface-point geometry at strict **0.001°** (not Stage13's loose 0.1° grid-vs-tower check).

**Stage19 diagnostic script updated:** [`scripts/19_CA_TP4_surfrd122_geometry_readonly.py`](scripts/19_CA_TP4_surfrd122_geometry_readonly.py) prints actual PTS values, coupler `scol_lon/scol_lat`, and following line of land log after mismatch, still read-only.

## Stage18 root cause localized to surfrdMod line 122: land-domain vs surface point coordinate mismatch (25 October 2026)

**Actual operator-provided authoritative Slurm and model log**:
- `4728206` `FAILED 1:0` after **00:00:06**; `4728206.0` `cesm.exe` `FAILED 1:0` after **00:00:04**, max RSS **14972K**. `4728207` short-term archive `PENDING` (unsatisfied run dependency). No restart pointers/files.
- Startup abort `ERROR in surfrdMod.F90 at line 122`; backtrace `surfrdmod_mp_chec 122` → `surfrdmod_mp_surf 270` → `clm_initializemod 258` → NUOPC. `srun` cancellation after this abort is downstream, **NOT evidence of memory exhaustion or a dust/Prigent ESMF mesh SIGSEGV**.

**Source-level pin/verification**: [ESCOMP/CTSM at d5ea9d0, src/main/surfrdMod.F90](https://github.com/ESCOMP/CTSM/blob/d5ea9d0/src/main/surfrdMod.F90#L108-L124). Lines **120–122** compute surface coordinate-vs-`ldomain%lonc/latc` differences and `endrun` whenever either absolute longitude (360° wrap handled) or latitude mismatch exceeds **0.001°**. Thus the *failed check* is specifically surface-vs-land-domain geometry. Exact actual runtime domain coordinates/differences were not printed in the supplied `cesm.log` (the error statement is emitted to `iulog`, often in `lnd.log`); do NOT invent actual mismatch degrees until the runtime domain/mesh input is inspected.

**Why user-referenced original working [Batch01](../Batch01_10/README.md) and Claude-reproduced [Batch03](../Batch03_10/README.md) matter**: their Stage11 case builders clone **each tower's own preexisting, working FATES case** and derive `fsurdat` from the original tower-specific `CaseDocs/lnd_in`. They retain a congruent per-site inherited 1PT atmospheric/land grid. By contrast, the AmeriFlux CA-TP4 Stage08 CIME case **cloned a CH-Dav Batch01 case** and reused a GF-Guy *compiled executable*, while substituting a CA-TP4 point surface and climate years. Its Stage07 documentation explicitly warned `CIME GRID/DOMAIN GATE` and marked `grid_domain_site_geometry_approved=False`; Stage08/12/17 checked *surface-vs-forcing* coordinates but **never verified the effective coupler land-domain-vs-surface**. This is the now identified missing pre-submit gate. It is not fixed by altering PFT percentages, soil, forcing UTC, CO2 or Slurm memory.

**NEW one-pass read-only [Stage19 CA-TP4 surfrd122 domain/mesh source comparison](scripts/19_CA_TP4_surfrd122_geometry_readonly.py)**:
1. Print the actual local pinned source `surfrdMod.F90` lines 119–123.
2. Show effective original CH-Dav and failed CA-TP4 CIME mesh/domain XML settings, actual surface NetCDF 1PT coordinates, independent CA-TP4 Stage11 UTC forcing coordinate match and CH-Dav source surface coordinate differences.
3. Search all available land/CIME logs and CDEPS/CIME runtime files for actual mesh/domain location; read only a tiny slice of candidate domain file coordinate variables.
4. Never creates/modifies files or submits Slurm. May leave exact land-domain coordinate unresolved if CIME's active mesh location does not appear in the inspected files; use `lnd.log` or a more targeted actual component trace in that case.

**Recovery policy**: Freeze failed `CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5` and its Stage18 single-submit ledger and `4728206/4728207`; preserve all Stage11 UTC data and Stage06 model-stand surface. After exact domain mismatch confirmed, create a **new, distinct versioned corrected CA-TP4 point domain/mesh/case** using the established tower-specific template conventions, scientifically correct 42.7102N/-80.3574E land/forcing coordinates, with explicit CIME coupler/domain preflight `<0.001°` before new 5-year smoke. Do not change old ldomain checks or fudge surface coordinates to match CH-Dav. The Batch03 stack-limit workaround is a separate issue for Prigent dust ESMF SIGSEGV and **does not explain this surfrd check**. Only when a corrected 5yr smoke is run successfully and checkpoint validated should AD395/Normal400 resume.

## Stage18 CA-TP4 model started then failed after ~4 seconds — diagnosis required (25 October 2026)

**Operator-provided actual CIME `CaseStatus`** (no root cause established yet):
- **09:13:14** `case.submit success case.run:4728206, case.st_archive:4728207`
- **09:14:34** `case.run starting 4728206`
- **09:14:35** `model execution starting 4728206`
- **09:14:39** `model execution error`, `case.run error`
- Failed launcher: `srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores /scratch/ly3n24/CTSM_FATES_OUTPUTS/GF-Guy_FATES_SURF2000_CO2405_1PT/bld/cesm.exe >> cesm.log.$LID 2>&1`
- Root-cause log **NOT YET SEEN**: `/scratch/ly3n24/CTSM_FATES_OUTPUTS/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5/run/cesm.log.4728206.261025-091434`.

**Status is FAILED at model execution, not Slurm scheduling failure.** No evidence exists for advancing any model years or producing a 2007 AD5 restart. Do **NOT** resubmit Stage18 (`stage18_CA_TP4_ONE_AD5_SUBMISSION_ATTEMPT.json` is a one-shot non-overwritable receipt), do not modify original Stage11 UTC forcing, new surface or private model overlay before diagnosis. First read full final 150–200 lines of exact `cesm.log`, initial runtime lines, relevant `ERROR/FATAL/NetCDF/FATES` matches, Slurm job `sacct -j 4728206,4728207`, and Slurm `.out`/`.err` in the CIME case; archive dependency 4728207 may become `DependencyNeverSatisfied`. Determine if error is geometry, I/O, CDEPS date/calendar, FATES namelist, MPI or resources **based on actual model logs only**, not inference from generic `srun` wrapper error. Retain existing case for controlled recovery after diagnosing.

```bash
CASE=/iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5
RUN=/scratch/ly3n24/CTSM_FATES_OUTPUTS/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5/run
LOG="$RUN/cesm.log.4728206.261025-091434"
test -f "$LOG" && { head -80 "$LOG"; tail -180 "$LOG"; grep -niE 'error|fatal|abort|stop|netcdf|fates|assert|nan|failed|not found|missing' "$LOG" | tail -80 || true; }
sacct -j 4728206,4728207 --format=JobID,JobName%42,State,Elapsed,ExitCode,MaxRSS
tail -40 "$CASE/CaseStatus"
```

## Stage18 CA-TP4 AD5 actually submitted — job 4728206 (25 October 2026)

**Operator-confirmed 2026-10-25 09:13:14 IRIDIS6 CIME output:**
`case.submit success case.run:4728206, case.st_archive:4728207`.
Actual `squeue -u ly3n24` at submission: **4728206 `run.CA-T...` PD (Priority)**, **4728207 `st_archive` PD (Dependency)**. This is **successful submission only**; job 4728206 has **NOT started at the observed queue snapshot**, and neither Slurm run completion, actual CIME/FATES model success nor restart availability is yet established. The unrelated older `DependencyNeverSatisfied` st_archive entries in the queue are other jobs and not proof of a CA-TP4 failure.

**Scope is 2002-01-01 startup to target 2007-01-01** (NO_LEAP; `STOP_OPTION=nyears`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`), fixed biogeography + no competition FATES accelerated decomposition (`spinup_state=2`), fixed background CO2 372.58 ppm, exact 22-year Stage11 UTC meteorology. This is a **5-year AD smoke within planned AD400**; remaining AD395 and independent Normal400 have **NOT started**. The other three Stage16 Lane A cases BR-Ma2, CA-Ca3, CA-LP1 remain at preview stage only.

**Observe only (never resubmit while uncertain):**
```bash
squeue -j 4728206,4728207 -o "%.12i %.45j %.4t %.12M %R"
sacct -j 4728206,4728207 --format=JobID,JobName%45,State,Elapsed,ExitCode,MaxRSS
tail -40 /iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5/CaseStatus
```
After model and archive finish, independently verify **log termination**, elapsed simulation dates, output NetCDF, CIME restart, FATES state and CDEPS coupler clock/geography; do not infer an acceptable long FATES spin-up from `COMPLETED` alone. Avoid any second Stage18 submit; its one-time attempt ledger exists on IRIDIS6. Check job 4728207 archive dependency normally changes from PD only after 4728206 completes.

## Stage17 corrected four cases PASS; Stage18 single CA-TP4 AD5 smoke (25 October 2026)

**User-confirmed actual corrected Stage17 IRIDIS6 RUN PASS 4/4**, all actual CIME cases remained unsubmitted:
- `CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5`: Stage12 pinned effective FATES `lnd_in` and CDEPS `datm.streams.xml` matches actual RUNDIR, verified 22 UTC files, fixed NOAA2002 372.58 ppm, 5-year accelerated FATES AD startup, `RESUBMIT=0`.
- `BR-Ma2_AMF_FIXNC_AD400_UTC_AD5`: exact 18 UTC files, fixed 1999 background CO2 367.79 ppm, 51.1m provisional ZBOT, FATES PFT1 candidate.
- `CA-Ca3_AMF_FIXNC_AD400_UTC_AD5`: exact 24 UTC files, fixed 2001 background CO2 370.57 ppm, 12m provisional ZBOT, FATES PFT2 candidate.
- `CA-LP1_AMF_FIXNC_AD400_UTC_AD5`: exact 18 UTC files, fixed 2007 background CO2 382.90 ppm, 26m provisional ZBOT, FATES PFT2 candidate.

For ALL 4 Stage17 checks: RUNDIR DATM + CDEPS effective streams exist; actual `case.submit --help` **supports `--skip-preview-namelist`**; hidden `.case.run` executable-job script exists, private AD namelist preview inputs/sha and CIME env_case lock all PASS. Slurm `#SBATCH` jobs each request 1 node, 1 task, 1 CPU, **8 GB RAM**, **1h walltime** on batch. Stage17 itself submits no Slurm. No site has run AD5 yet.

**CIME semantics confirmed from official [case.submit docs](https://esmci.github.io/cime/versions/cesm2.2/html/Tools_user/case.submit.html) and [case_submit.py implementation](https://esmci.github.io/cime/versions/master/_modules/CIME/case/case_submit.html):** `--skip-preview-namelist` keeps the already reviewed private-FATES-patched namelist instead of regenerating it against original shared CTSM; the case still checks input availability and uses CIME job submission workflow, normally including dependent short-term archive when `DOUT_S=TRUE`.

**Next: [Stage18 CA-TP4 ONE guarded AD5 technical smoke submission](scripts/18_CA_TP4_submit_one_AD5_skip_preview_guarded.py)**. It has `--self-test`, read-only `--check` and explicit *one-time* `--submit --confirm SUBMIT_ONE_CA_TP4_AD5_TECHNICAL_SMOKE_SKIP_PREVIEW`. It first checks exact Stage12 validated case/CaseDocs/RUNDIR SHA, UTC met stream 22 years + 8 fields + `offset=0`, FATES flags + coldstart + fixed CO2, CIME lock/build/5-yr flags, one independent `RUNDIR`, `DOUT_S=TRUE`, no existing restart pointers, and checks Slurm queue for an existing same case. Before calling `./case.submit --skip-preview-namelist` for **only CA-TP4**, it creates a non-overwritable `stage18_CA_TP4_ONE_AD5_SUBMISSION_ATTEMPT.json` ledger. This is an **opt-in REAL job submission** (unlike all earlier 1–17), with possibly a dependent archive job. On nonzero exit or lost connection ledger may remain `ATTEMPTED_UNCERTAIN`: **NEVER blindly rerun**, audit `squeue/sacct/CaseStatus` and original receipt first. A command returning zero is **NOT model success**; verify real Slurm run state, coupler/site coordinates/time, log diagnostics and 5-year FATES restart before extending AD395 or starting independent Normal400.

Crucial distinction: **CIME coupling grid/solar-clock convention has not yet been validated by an actual model run**. The Stage18 five-year submission is a technical smoke to obtain such evidence, not an endorsement of FATES landunit/stand fractions, point soil, TA_F source sensor height or actual flux/biome realism. No other three Lane-A sites should submit until first smoke proven.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/18_CA_TP4_submit_one_AD5_skip_preview_guarded.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/18_CA_TP4_submit_one_AD5_skip_preview_guarded.py --check
# This is the only action that submits a real Slurm model job (CA-TP4 only):
python3 -B examples/AmeriFlux_Batch01_10/scripts/18_CA_TP4_submit_one_AD5_skip_preview_guarded.py --submit --confirm SUBMIT_ONE_CA_TP4_AD5_TECHNICAL_SMOKE_SKIP_PREVIEW
```

## Stage17 first run: false CLI name error fixed, no CIME or Slurm failure (25 October 2026)

Actual user IRIDIS6 Stage17 source/syntax and pure self-test PASS. The first case `CA-TP4` passed generated/runtime `lnd_in` SHA, `RUNDIR/datm_in` exists and `RUNDIR/datm.streams.xml` exists. Its actual local `case.submit --help` **supports `--skip-preview-namelist`**. The original Stage17 script then incorrectly tried to locate **`case.run`** as a public CIME CLI and stopped. CIME instead generates a *hidden* **`.case.run`** batch payload. This is a **Stage17 audit script bug, not a failed model, failed Slurm or a missing new case**, and no case was submitted.

**[Corrected Stage17 four-case read-only runtime gate](scripts/17_four_AD5_runtime_submission_gate_readonly.py)** now checks `case.submit --help` only; checks `.case.run` by file existence/SHA and prints scheduler directives without executing it or calling `--help` on a batch script. Retains all four generated CaseDocs/runtime LND/UTC/CIME/CO2 checks, **no file mutations, no submission**. Run `--self-test` and `--check` using the corrected pinned revision. If every case passes, proceed to a separately controlled single CA-TP4 AD5 smoke after examining job/resource and coupler-grid prerequisites; **do not use normal `./case.submit` without a safe namelist strategy**.

## Stage16 actual three AD5 preview success; Stage17 CIME runtime-gate (25 October 2026)

**Actual operator-provided three Stage16 case previews confirmed SUCCESS**:
- `BR-Ma2_AMF_FIXNC_AD400_UTC_AD5`: 18 annual UTC years, FATES PFT1, provisional ZBOT 51.1 m, 1999 fixed NOAA global CO2 367.79 ppm.
- `CA-Ca3_AMF_FIXNC_AD400_UTC_AD5`: 24 annual UTC years, FATES PFT2, provisional ZBOT 12 m, 2001 fixed NOAA global CO2 370.57 ppm.
- `CA-LP1_AMF_FIXNC_AD400_UTC_AD5`: 18 annual UTC years, FATES PFT2, provisional ZBOT 26 m, 2007 fixed NOAA global CO2 382.90 ppm.
- Existing `CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5`: 22 annual UTC years, forest PFT2/PFT6 idealized 93:7; provisional ZBOT 28 m; 2002 fixed NOAA global CO2 372.58 ppm.

Every Stage16 case executed `preview_namelists` against the verified FATES private AD override, then explicitly restored `env_case.xml` lock. Actual `lnd_in` had `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `spinup_state=2`, cold start, `CLM_ACCELERATED_SPINUP=on`, `STOP_N=REST_N=5`, `RESUBMIT=0`, and the station-local surface. Every DATM stream contains only its site-specific UTC forcing, valid year cycling, eight met variables, and original ancillary streams. **No model job has been submitted.**

**HIGH PRIORITY before first run:** CIME documentation states that ordinary `./case.submit` regenerates namelists and checks input data (CIME [running a case](https://esmci.github.io/cime/versions/cesm2.2/html/users_guide/running-a-case.html)). The AD correction was activated **temporarily via a private FATES build-namelist overlay for preview**, then the case source lock was restored to the **unpatched** CTSM root; an ordinary submit can overwrite the successfully generated accelerated-decomposition FATES namelist or fail in buildnml. CIME supports `--skip-preview-namelist` for submission [case.submit help](https://esmci.github.io/cime/versions/cesm2.2/html/Tools_user/case.submit.html), but we must check both the **installed** submit/run help and *actual run-directory lnd_in* before using that mode; there may also be machine-specific input staging requirements.

**[Stage17 four-case READ-ONLY CIME actual-run namelist + skip-preview gate](scripts/17_four_AD5_runtime_submission_gate_readonly.py)** performs *one* shared audit of the 4 existing case receipts, current CaseDocs SHA, model `RUNDIR/lnd_in` SHA equality, `case.submit --help` and `case.run --help`, configured 5yr AD cold start and independent CIME run folders, source year/CO2, and actual effective 1PT met stream path list. **It has no submit command and does not reprocess climate data.**

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/17_four_AD5_runtime_submission_gate_readonly.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/17_four_AD5_runtime_submission_gate_readonly.py --check
```

**If Stage17 passes**: independently review installed CIME skip-preview submit behavior, per-site point geometry and batch resources, then submit **a single CA-TP4 5yr AD technical smoke**, ideally by supported `./case.submit --skip-preview-namelist` after source/run staging is verified. Monitor Slurm run + archive jobs and check model log, restart triplet, expected time/cycle before touching AD395/Normal400 or launching remaining 3 pilots. The current original 28m/stand composition/grid soil assumptions have not become field observations simply because namelist checks passed.

## Stage15 actual three independent surfaces PASS; Stage16 AD5 case previews (25 October 2026)

**User-confirmed Stage15 IRIDIS6 SUCCESS:** Three independent pilot source surfaces, all NetCDF variables except deliberate stand/landunit changes bit-identical in array contents to existing point grids. Output:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage15_LaneA_SURF_20261025T084151593400561Z/`

| Site | Verified effective FATES HLM mapping, technical stand proxy | Source NAT/CROP | Original gridded PCT_SAND / PCT_CLAY | Stage15 |
|---|---|---|---|---|
| BR-Ma2 | CLM host idx4 → FATES PFT1 tropical evergreen broadleaf, 100% experimental NATVEG | 100.000 / 0.000 | sand 40–53% / clay 35–49% | PASS |
| CA-Ca3 | CLM host idx1 → FATES PFT2 extratropical evergreen needleleaf, 100% NATVEG | 98.804 / 1.196 | sand 67–80% / clay 5–7% | PASS |
| CA-LP1 | CLM host idx1 → FATES PFT2 extratropical evergreen needleleaf, 100% NATVEG | 98.380 / 1.620 | sand 53% / clay 16% | PASS |
| US-Bar | FATES PFT6 83%, PFT2 ≥14%, residual ≈3% unresolved | not altered | no copy | HOLD, no surface |

The generated three site forests are **IDEALIZED technical landunit/PFT hypotheses, not EC footprint area measurements, stand age/biomass initialization or observed station soil**. The original gridded texture remains a known fallback. No CIME case or Slurm jobs were created by Stage15. Four-site Stage14 UTC forcing remains independently preserved.

**Next: [Stage16 one shared Lane A three-site FATES AD5 case creator and namelist preview](scripts/16_laneA_three_AD5_CIME_preview_no_slurm.py)**. It imports *only the exact pinned successful Stage08 FATES private AD helper*, clones the unchanged **CA-TP4 UTC-V2 Stage12 FATES CIME case** as a generic machine executable template, substitutes each of the **60 total annual site-specific Stage14 UTC files**, the exact Stage15 site surface, and year-specific `CLM_USRDAT.UNSET` cycle/linear, offset0, noleap and 48 time steps/day. Stops at **5 accelerated decomposition FATES years** (`spinup_state=2`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=0`) with fixed biogeog, nocomp and independent run/archive paths. It uses published NOAA GML 2026-10 global-background CO2 for *each site's first forcing year*, not a copied CA-TP4 CO2:

| Site | First forcing year | NOAA GLOBAL annual fixed CO2 (ppm) | 5yr preflight interval |
|---|---:|---:|---|
| BR-Ma2 | 1999 | 367.79 | 1999–2004 |
| CA-Ca3 | 2001 | 370.57 | 2001–2006 |
| CA-LP1 | 2007 | 382.90 | 2007–2012 |

Source: [NOAA GML global annual CO2](https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv), revision 2026-10. These are **global**, not tower-measured and not a common fixed-CO2 experiment. This model baseline policy must remain the same when comparing alternative ensembles.

Safety: `--self-test` and `--check` do not write any files. `--stage --site ONE --confirm CREATE_ONE_LANEA_AD5_CASE_PREVIEW_NO_SLURM` is a **single new case preview only**, with a separate one-time attempt receipt, no Slurm or actual model execution, and guaranteed CIME environment lock restoration validation. A failed stage leaves an unrepeatable attempt stamp and possibly partial case; diagnose/repair manually, do not rerun the same stage. Successful stage checks 8 DATM source mappings, exact annual UTC files, 4 unchanged ancillary CDEPS streams, effective FATES `lnd_in` and absence of restart, local site `fsurdat`, fixed CO2 and all CIME run settings. US-Bar is excluded. The user should run one `--check` then individually process BR-Ma2, CA-Ca3, CA-LP1. Actual Slurm AD5 smoke and coupler geometry are subsequent work, and AD395 + Normal400 still have **NOT** started.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/16_laneA_three_AD5_CIME_preview_no_slurm.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/16_laneA_three_AD5_CIME_preview_no_slurm.py --check
# Only after successful check and explicit operator opt-in, stage one site at a time:
python3 -B examples/AmeriFlux_Batch01_10/scripts/16_laneA_three_AD5_CIME_preview_no_slurm.py --stage --site BR-Ma2 --confirm CREATE_ONE_LANEA_AD5_CASE_PREVIEW_NO_SLURM
```

## Stage14 actual 80/80 UTC pilots PASS; Stage15 three-forest proxy surfaces (25 October 2026)

**User-confirmed actual Stage14 on IRIDIS6: SUCCESS — four independent UTC+ZBOT pilot datasets** at:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage14_LaneA_UTC_20261025T083517624796820Z/`

- **BR-Ma2:** 1999–2016, 18 years, BIF UTC−4, provisional BASE ZBOT=51.1 m; sampled UTC FSDS astronomical-night 1999 **0.001%**, 2007 **0.018%**, 2016 **0.017%**.
- **CA-Ca3:** 2001–2024, 24 years, BIF UTC−8, provisional BASE ZBOT=12m; UTC solar night 2001 **0.000%**, 2012 **0.304%**, 2024 **0.000%**.
- **CA-LP1:** 2007–2024, 18 years, BIF UTC−8, provisional BASE ZBOT=26m; UTC solar night 2007 **0.445%**, 2015 **0.012%**, 2024 **0.011%**.
- **US-Bar:** 2004–2023, 20 years, BIF UTC−5, provisional BASE ZBOT=23.8m; UTC solar night 2004 **0.101%**, 2013 **0.084%**, 2023 **0.556%**.

**All 80/80 yearly UTC/ZBOT NetCDF generated, each source-year SHA and both cyclic-in/out variable slices verified**; `STAGE14 BATCH MANIFEST PASS`. Original 213 annual Stage81 NetCDF unchanged; no PFT surface, CIME case or Slurm created. Stage14 timestamps assume original Stage81 local interval-START for three non-CA-TP4 sites without having separately independently verified the raw native timestamp convention. Technical meteorological pilot only.

**Next: [Stage15 three independent idealized Lane A forest surface pilots; US-Bar held](scripts/15_laneA_three_forest_surfaces_USBar_hold.py)**. Uses pinned original Stage81 surface SHA, pinned Stage14 four-site receipt, published observed/assumed PFT evidence, and **effective private FATES AD `fates_hlm_pft_map`** to conditionally create:

| Site | Stand scientific basis | Explicit technical surface-only hypothesis | Note |
|---|---|---|---|
| BR-Ma2 | ORCHIDEE published PFT1=100% model assumption, not an independent K34 botanical area survey | 100% NATVEG, FATES PFT1 tropical evergreen broadleaf; verify its CLM host-index-4 map | Grid soil and unknown stand age remain inherited proxies |
| CA-Ca3 | Douglas-fir 75%, cedar 21%, grand fir 4% as species of common functional group | 100% NATVEG, FATES PFT2 extratropical evergreen needleleaf; CLM host-index-1 candidate | Observed site tree composition **not observed whole grid ground-cover fraction** |
| CA-LP1 | Lodgepole pine-dominated, data on three seedling/sapling conifers | 100% NATVEG, FATES PFT2 extratropical evergreen needleleaf; CLM host-index-1 candidate | Beetle mortality and actual cohort structure **not resolved by this surface** |
| **US-Bar** | PFT6 83%, PFT2≥14%, ~3% unknown | **HOLD — NO SURFACE WRITTEN** | Never silently force the missing ~3% into ENF/DBF/grass/bare |

The Stage15 script only builds three new NetCDF surfaces in a brand-new directory on explicitly acknowledged `--build-preview`, checks **every unrelated gridded soil/terrain variable byte-equivalent in logical array values**, and emits one site provenance file each plus a four-site receipt with US-Bar scientific HOLD. Stage15 does not modify Stage14 forcing, old CA-TP4 cases, source surfaces, FATES params or Slurm. Original gridded soil sand/clay remains inherited fallback; this is not an observation-based FATES biomass/stand age initialization. Later case preparation is a separate batch-gated operation.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/15_laneA_three_forest_surfaces_USBar_hold.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/15_laneA_three_forest_surfaces_USBar_hold.py --check
# Only after read-only checks and consent:
python3 -B examples/AmeriFlux_Batch01_10/scripts/15_laneA_three_forest_surfaces_USBar_hold.py --build-preview --ack-idealized-three-forest-proxies --outdir NEW_DIR
```

## Lane A four-site batch UTC technical forcing prepared for operator trial (25 October 2026)

**Actual IRIDIS6 Stage13 nine-site matrix user-confirmed PASS**. All nine source Stage81 annual NC have contiguous years and source BIF UTC offset, original point-surface geolocation BIF_GRID_GEO=OK, 0 new CIME cases, and are backed by ten-site Stage82 213-year SHA inventory. Exact nine-site classification remains 4 static BASE height candidates, 3 event-varying heights, 2 unresolved multi-level sites. This is not 9 approved sensor crosswalks.

**[Stage14 Lane A one-shot, four-site UTC/ZBOT TECHNICAL NetCDF candidate builder](scripts/14_laneA_four_static_UTC_DATM_proxies.py)**. Avoid 4 repeats of all 12 CA-TP4 stages and do not redo Stage80 ERA5/RH corrections. Read the exact old Stage31 BASE height policies, Stage81 per-site annual source paths, Stage82 original SHA receipt, raw AmeriFlux BIF UTC offsets and point-surface coordinates. Four candidates with proposed technical `ZBOT` height:

| Site | Local forcing years | BIF UTC offset | BASE ZBOT proxy | 22-year CA-TP4 parameters forbidden |
|---|---|---|---|---|
| BR-Ma2 | 1999–2016 (18) | UTC−4 | 51.1 m STATIC | must use -4 and site-specific year cycle |
| CA-Ca3 | 2001–2024 (24) | UTC−8 | 12.0 m STATIC | must use -8 and site-specific year cycle |
| CA-LP1 | 2007–2024 (18) | UTC−8 | 26.0 m STATIC | must use -8 and site-specific year cycle |
| US-Bar | 2004–2023 (20) | UTC−5 | 23.8 m STATIC | must use its own 20-year cycle and mixed-forest PFT |

**Stage14**, only on explicit `--build-preview --outdir NEW --ack-four-static-sensor-proxies`, copies all **80 annual source NC into a separate output**. It treats original Stage81 `time=local interval start` as a **technical timestamp assumption** (only the original CA-TP4 pilot had independent raw FLUXNET local-start timestamp checks); assigns +15-min midpoint, shifts all **nine** source met fields by exactly the individual BIF local→UTC offset across every annual wrap, sets site-specific explicit static ZBOT as **unverified TA_F sensor crosswalk**, creates a detached `CLM_USRDAT.UNSET` CDEPS stream with `cycle/linear` and `offset=0`, validates all source input annual SHA, every new field/annual mapping against both previous and current local year, and checks UTC astronomical night FSDS sanity in the first/mid/last years for each site. Source NC and Stage12 CA-TP4 case remain unchanged. **No surface/PFT/model case/restart/Slurm is produced.**

**Critical unresolved before model deployment:** Original `TA_F` vs actual sensor height crosswalk for all 4; local-start versus local-end native timestamps for these 4 (the Stage81 label still says unverified, even though it uses 00:00 time); stand PFT design requires **site-specific** local point surface and FATES HLM map, not CA-TP4 ENF93/DBF7. BR-Ma2 tropical EBF 100 model-assumed tree; CA-Ca3 conifer FATES2-only; CA-LP1 conifer FATES2-only with beetle disturbance; US-Bar PFT6≈83%, PFT2≥14%, leftover ≈3% unresolved — no silent percentages normalization. Preserve site soil as documented fallback if no independent observed profiles. US-Aud, a C4 grass+barren site, remains separately designed; CA-Cbo/CA-Man remain held.

```bash
python3 -B examples/AmeriFlux_Batch01_10/scripts/14_laneA_four_static_UTC_DATM_proxies.py --self-test
python3 -B examples/AmeriFlux_Batch01_10/scripts/14_laneA_four_static_UTC_DATM_proxies.py --check
# On PASS only; materialises all 80 independent NC without touching CIME:
python3 -B examples/AmeriFlux_Batch01_10/scripts/14_laneA_four_static_UTC_DATM_proxies.py --build-preview --ack-four-static-sensor-proxies --outdir ABSOLUTE_NEW_DIR
```

The next shared batch function after a successful Stage14 should generate each site's independent justified PFT/landunit/soil PROXY surfaces then provision separate AD5 cases, still gated for a short run before AD395 + Normal400. **DO NOT copy the CA-TP4 2002 CO2 372.58 ppm to a 1999/2001/2007/2004 start as if it were automatically site-specific**; choose and cite CO2 reference years in a common experimental baseline policy. The CA-TP4 2002 pilot itself has only `preview_namelists` passed and has not submitted AD5.

## Remaining 9 AmeriFlux sites: batch rollout after CA-TP4 (25 October 2026)

**Confirmed from operator-provided Stage12 SUCCESS:** CA-TP4 `/iridisfs/scratch/ly3n24/CLM_FATES/cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5` was independently cloned and its actual CIME FATES/CDEPS namelists previewed, with exact Stage11 22-year UTC forcing, local Stage06 forest stand proxy, NOAA 2002 **fixed CO2 372.58 ppm**, `spinup_state=2`, `STOP_N=REST_N=5`, `RESUBMIT=0`. The previous CA-TP4 Stage08 LST-labeled case was kept unchanged. **No AD5/AD400 or Normal400 jobs have been submitted**.

**The other NINE AmeriFlux Batch01 sites have NOT been initialized as AD5 cases**. All ten stations' Stage80 original QC, Stage81 annual NetCDF (**213 total**) and Stage82 integrity audit are already complete. Reuse those results. Do **NOT** duplicate Stage80 QC, rerun the CA-TP4 12 stage scripts nine times, or assume all nine sites are CA-TP4 forest/sensor/UTC variants.

**[One-pass nine-site rollout inventory](scripts/13_remaining9_AD400_rollout_matrix_readonly.py)**, `--self-test` and `--check`, reads only the pinned Stage31 height candidate policy, Stage81/Stage82 213-NC receipts, original each-site BIF `UTC_OFFSET` and coordinate, individual point-surface landunit percentages and the pinned [published FATES PFT candidates](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/649eb960475ff77944e42c559ff1ebbe6d2f1004/examples/AmeriFlux_sites/metadata/Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv). It prints one **nine-row readiness matrix**, and is strictly READ-ONLY; no new forcing/NC/surface/case/reports or Slurm jobs.

The original Stage31 provisional BASE air-temperature height classifications (sensor crosswalk with FLUXNET `TA_F` remains **UNVERIFIED**):

| Lane | Sites | Existing height policy | Next action |
|---|---|---|---|
| A, four static-height technical pilot candidates | BR-Ma2 (51.1m), CA-Ca3 (12m), CA-LP1 (26m), US-Bar (23.8m) | STATIC BASE candidate; not `TA_F` verified | Site-specific BIF UTC/year shift and stand/landunit/soil *explicit model hypothesis*, then batch separate AD5 case preview |
| B, three height-sensitive pilots | CA-TP1 (4m baseline, 3 events), CA-TP3 (16m baseline, 1 event), US-Aud (1.25m baseline, 1 event) | DYNAMIC events / uncertain halfhour periods | Decide time-varying source height from original dated evidence; US-Aud is C4 grass + bare ground, **not forest** |
| C, two blocked height-source mappings | CA-Cbo, CA-Man | BASE multi-level ambient temperature; no scientifically chosen `TA_F` source | Resolve which actual TA measurement layer or use an explicitly justified/independently supported experiment height; do not fabricate ZBOT |

The published PFT ratios in the pinned site evidence differ materially: BR-Ma2 tropical evergreen broadleaf, CA-Ca3/CA-LP1 conifer, US-Bar mixed deciduous/conifer, CA-Cbo mixed, CA-Man spruce with unknown ~1%, CA-TP1 plantation, CA-TP3 white pine/oak, US-Aud grass/bare. These are **stand/model-candidate composition, not observed land-cover fractions**. There is **no** scientifically valid 100% NATVEG/ENF93/DBF7 template for all nine.

**Rollout plan:** use *one common nine-site engine* after the one-pass matrix, grouping four static-height experimental assumptions first while investigating the other five in parallel. For every station use its actual BIF UTC offset and original Stage81 year range (not blindly `UTC−5` / `2002−2023`), site-specific point-surface and FATES PFT mapping, explicit baseline constant CO2 policy, isolated `AD5` `RESUBMIT=0` first. Do not make 400+400 year jobs until short pilot and restart archive checks.

## Stage11 actual UTC forcing PASS; Stage12 independent AD5 preview (25 October 2026)

**Operator-confirmed actual IRIDIS6 Stage11 success:** NEW 22/22 *separate* CA-TP4 2002–2023 annual NetCDF written at

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage11_CA_TP4_DATM_UTC_20261025T080240825734395Z/`

The immutable original Stage04 half-hour FLUXNET **UTC−5 local standard time** data were reindexed as 22 entire UTC-year NOLEAP files with mid-interval timestamps and **+5h/10-half-hour cyclic permutation** of all meteorological fields including TBOT/QBOT/SHUM/RH/ZBOT, FSDS/FLDS, precipitation, wind, and pressure. 22 annual file SHA/row-provenance checks PASS; UTC solar shortwave energy falling at astronomical night is **2002 0.2122%, 2010 0.0002%, 2019 0.0277%**. The 2002 Jan1 00:15–04:45 UTC source comes from final 5h of **2023** local forcing, a clearly identified 22-year forcing loop boundary assumption (NOT actual 2001 meteorology). A **detached** candidate CDEPS stream refers to those 22 UTC files with `cycle+linear`, `offset=0`; **original Stage08 CA-TP4 case/Stage04/Stage06 unchanged; no Slurm or CIME changes**.

**Next: [Stage12 independent CA-TP4 UTC-V2 AD5 case CIME namelist preview, no Slurm](scripts/12_CA_TP4_UTC_V2_AD5_CIME_preview_no_slurm.py).** This is a NEW case `CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5`, not an alteration or retry of existing Stage08 `CA-TP4_AMF_FIXNC_AD400_PILOT`. The verified Stage08 script is imported from its existing local file, with CIME source/CaseDocs/lock SHA checked. Stage12 reads exact Stage11 detached manifest/22 NC SHA, reuses verified site Stage06 surface, and checks original FATES private AD overlay. `--check` runs strictly read-only. Explicit `--stage --confirm CREATE_NEW_CA_TP4_UTC_V2_AD5_PREVIEW_NO_SLURM` makes **one new clone with its own run/archive, replaces only 1PT meteorology paths**, sets fixed **2002 global-background CO2 = 372.58 ppm** as explicitly selected **technical spinup** value, NO_LEAP, ATM_NCPL48, FATES `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `spinup_state=2`, AD mode ON, STOP_N=5, REST_N=5, RESUBMIT=0, startup 2002, and `CLM_USRDAT.UNSET:offset=0`. A private FATES AD overlay is used only for `preview_namelists`; after preview the `env_case.xml` lock is restored. It verifies actual **generated** `CaseDocs/lnd_in`, `CaseDocs/datm.streams.xml`, all 22 Stage11 UTC NC paths, all 8 variables, ancillary stream preservation, case settings and fixed CO2. No Slurm job is started.

**Stage12 is ONE-TIME**: after any `--stage` failure, DO NOT simply rerun; an attempt ledger and partial clone may be present. Inspect them. Even when `PREVIEW_VERIFIED_NOT_SUBMITTED`, case remains held for independent actual coupler/solar geometry and cross-year interpolation runtime verification; scientific CA-TP4 28m ZBOT sensor crosswalk, stand-groundcover ratios and site soil remain **experimental proxies**, not validated observations. First future model run should only be ONE five-year AD smoke, before AD395 and independent Normal400.

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
