# OzFlux Non-Competition: operator-selected direct AD400 from 2026-11-03

**Operator policy:** All future OzFlux FIXNC cases should target **direct accelerated spinup AD400** (80 successive 5-year segments; `STOP_OPTION=nyears`, `STOP_N=5`, `REST_N=5`, `RESUBMIT=79`), **without any AD5 pilot**. Each site must still pass its independently validated real CIME configuration checks; no accidental submission of other sites is authorised. This overrides historical AD5-first wording in previous Stage07 READONLY plans and README sections. No prior Stage07 checks need rerunning merely because their _plan name_ was AD5; the previous Stage07 report is retained as immutable source provenance, not as the selected run protocol.

## First target: AU-ASM

- **New case name:** `AU-ASM_OZ_FIXNC_GRIDREF_AD400_DIRECT`; new case/config/run/archive/ledger paths, separate from old AU-How and other existing studies.
- **Model startup:** `2013-01-01`; **target year:** `2413-01-01`, 80×5 years; **MET years:** six distinct Stage14 provisional NOLEAP files 2013–2018, cycling over 400 model years. No re-transform and no new DATM derived file generation.
- **Candidate Surface:** `/home/ly3n24/ozflux_nc_stage02_ASM_20261102T215809Z/surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc`, SHA256 `d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1`; 29% natural-land bare host0, host5 65% (FATES4), host13 2% (FATES13), host14 4% (FATES14); 10-layer grid-referenced soil only.
- **Stage04 / Stage05 PASS:** `/home/ly3n24/ozflux_nc_stage04_20261102T223221Z_FIX` and `/home/ly3n24/ozflux_nc_stage05_20261102T224556Z_FIX`; six annual input SHA files unchanged; 196 source QC variable-years reconciled; 2017 FLDS 395h ACCESS-forcing episode remains a science review issue.
- **Stage07 PASS:** `/home/ly3n24/ozflux_nc_stage07_20261103T061721Z` was a source/CIME inventory only. Historical AD5 label is **superseded**; it did not create any model case or submit Slurm.
- **Stage06 Surface science hold:** 10-layer grid soil sand 89–90%, clay 6–7%, silt 3–4%, `ORGANIC` 1.69–6.84 kg/m³. Site soil is not validated; recent TERN source described ~74:11:15 sand:silt:clay. The GRIDREF case is an **exploratory model hypothesis** rather than a site-soil-approved production forcing study.
- **Other open science gates:** original local END → UTC-center timing remains a provisional science hypothesis; actual CDEPS effective generated stream offset, coupler geometry, FATES DEFAULT14 mapping and installed FATES parameters must be checked against the real case and referenced NetCDFs before any submission. Do not automatically label source QC0 as original measured data.
- **Engineering script:** [Stage08 direct AD400 source](./scripts/08_asm_GRIDREF_direct_AD400_80x5_guarded.py) in [PR #64](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/64), which pins the proven Batch02 helper blob `decc61898a89109c3819faca2c8c3134ebed77ee`, uses `CH-Dav_B01_FIXNC_AD400` solely as a CIME/EXE/reference template, and checks the actual input SHA/provenance. No historic reference site meteorology, soil, PFT fractions or model case identity is intentionally copied.
- **Actions:** `self-test` (no external data), `check` (read-only); `prepare` (consent-gated isolated CIME clone + generated runtime namelist verification without Slurm), `submit` (consent-gated, one `case.submit` and `RESUBMIT=79`), `status` (read-only). The script must pass real IRIDIS6 operator checks before claiming that the target case was created or submitted.

**Scientific status:** exploratory GRIDREF/met provisional `science_approval=false`, **direct AD400 requested**, no AD5. Submission requires explicit acknowledgment of the provisional inputs and exact confirmed case settings.

## Extension to remaining eight OzFlux sites

Use the same direct AD400 protocol only after each site's actual forcing/candidate/soil/PFT/clock/CIME checks pass; do not assume that AU-ASM success applies to AU-DaS, AU-Dry, AU-Gin, AU-How, AU-Cpr, AU-Cow, AU-Stp or AU-Tum. Preserve all original data and old AU-How experiment.
