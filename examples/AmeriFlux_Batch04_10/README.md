# AmeriFlux Batch04 — paired full FATES vs fixed-biogeography/no-competition FATES

**Created 2026-10-26; ten new AmeriFlux station projects. This is NOT the ICOS `examples/Batch03_10` or `examples/Batch01_10` experiment.** Source meteorology and provisional surfaces are newly verified, but **no site has a science-approved ZBOT, active DATM/forcing NetCDF stream, final CLM ten-layer/ORGANIC soil source, verified FATES parameter mapping in a constructed case, production CIME case or Slurm job**. Do not call these experiments running or completed.

## Actual cross-repository source status (operator IRIDIS6 26 October 2026)

The upstream [AmeriFlux Batch04 forcing and surface workflow](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/AmeriFlux_MultiSite_10_Batch04) has:

- **SYVH9**: ten full site source SHAs and seven-met `TA_F, VPD_F, PA_F, SW_IN_F, LW_IN_F, WS_F, P_F` **Gate-0 PASS 10/10**, native 30-min and NOLEAP chronology. It independently replaced **12 half-hours of implausible `LW_IN_F`** in five sites using CDS ERA5-Land `surface_thermal_radiation_downwards`, checked original tower BIF UTC offsets, source and candidate SHAs and row/column differences; **3 source VPD three-decimal saturation-rounding exceptions remain annotated** (Rpf 2, Syv 1) for **output-only** conversion handling.
- **SYVH10/11**: BIF coordinates/UTC offsets PASS 10/10; US-Seg uses previously **user-approved** BIF group **1495**, lat `34.3623`, lon `-106.7020`. No BIF `TA_F/WS_F/WIND` **measured-height pair** was recovered (0/10), so **no observed ZBOT** can be claimed; `HEIGHTC` is canopy only. Surface/case files were not found in the original bounded directory searches (not a global absence claim).
- **SYVH12**: **10/10 isolated provisional CTSM point surface `surfdata*.nc` files actually generated** at exact approved EC tower coordinates, each surface SHA independently verified, and `SYVH12 TEN ISOLATED POINT SURFACE CANDIDATES CREATED 10/10` confirmed by user. These are **year-2000 default gridded PFT/soil**, not measured site-specific PFT/soil or final model cases. Root:
```text
/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch04/stage12_provisional_ctsm_point_surfaces_RESEARCH_ONLY/candidate_20261026T163236Z_5737e505
```
- Final immutable ten-source met manifest:
```text
/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10_Batch04/manual_Batch04_SYVH9_12_low_LW_5sites_independent_ERA5Land_research_not_approved/candidate_20261026T121123Z_a8b8146f/RESEARCH_TEN_SITE_MANIFEST.tsv
```

## Experimental question and paired design

For each site, create **two independent model arms** with the **same version-pinned meteorology, point coordinates, site-recommended *initial* host PFT composition, surface/soil treatment and intended historical/CO2 prescription**. Deliberately vary the FATES competition/fixed-geography switches after case build verifies the installed CTSM branch implements them correctly:

| Arm | Planned model settings (not yet activated) | Model interpretation |
|---|---|---|
| **FULL_FATES_COMPETITION** | `use_fates=.true.`; `use_fates_sp=.false.`; `use_fates_fixed_biogeog=.false.`; `use_fates_nocomp=.false.` | Dynamic competition and emergent PFT composition |
| **FIXED_BIOGEOG_NO_COMPETITION** | `use_fates=.true.`; `use_fates_sp=.false.`; `use_fates_fixed_biogeog=.true.`; `use_fates_nocomp=.true.` | Prescribed initial site functional composition, no competition; site-only FATES map may be required |

For both arms: **AD400 → Normal400**, split **AD5 smoke → AD395**, then **Normal5 smoke → Normal395**. This is **800 model years per arm**, 1,600 model years per site and 16,000 for all 20 arms, **not 10,000**. `spinup_state=2` in the AD accelerator, removed for Normal (as validated in the European Batch03 workflow); five-year forcing-year cycles, CO2, NOLEAP, physical start date, restitution/PTS_DOMAINFILE and spinup-off history must be validated against the actual CIME branch; **never copy another site's case or PTS coordinates**. Neither mode has a case or Slurm job here yet.

**Fair scientific control:** use one shared site-specific PFT starting surface for both arms to attribute downstream difference primarily to competition, not different initial landcover; this **does not imply** that the FULL arm has fixed PFTs throughout integration. **No site's PFT shares are independently measured whole-flux-footprint exclusive ground-cover fractions.** They are labeled model hypotheses (some high uncertainty).

## Exact ten-source recommended fixed-PFT model hypotheses

All numbers below are percent of the *idealized model NATVEG landunit*, including explicit HLM index 0 bare where specified; **model NATVEG100 and CROP0 are experiments, not reconstructed observed landunit shares**.

| Site | Model hypothesis | Bare % | Host/profile caveat |
|---|---|---:|---|
| US-Rpf | DBF 80 / cold-deciduous shrub 20 | 0 | Post-fire forest/shrub prior; HIGH uncertainty |
| US-SP1 | ENF 85 / evergreen shrub 15 | 0 | Pine vs understory mixture assumed; HIGH |
| US-SRG | DBF 11 / C4 44 / bare 45 | 45 | Woody and herbaceous covers may overlap; MEDIUM |
| US-SRM | DBF 35 / C4 20 / bare 45 | 45 | Bare 45 within literature range; MEDIUM |
| US-Seg | C4 60 / bare 40 | 40 | Published model precedent, previously approved site coordinates; MEDIUM |
| US-Ses | evergreen shrub 55 / C4 25 / bare 20 | 20 | Shrub HLM-to-FATES mapping needs checking; HIGH |
| US-Slt | ENF 38 / DBF 62 | 0 | 2018 basal-area composition, not ground fractions; MEDIUM |
| US-Syv | ENF 13 / DBF 87 | 0 | 2002 immediate-tower-tree stem composition; MEDIUM |
| US-Ton | DBF 43 / cool C3 grass 57 | 0 | Ground canopy and understory collapsed to exclusive shares; HIGH |
| US-Uaf | ENF 50 / Arctic evergreen shrub 20 / Arctic deciduous shrub 20 / Arctic C3 10 | 0 | `ARCTIC_PURE` site-only private FATES mapping; moss/peat/permafrost HOLD; HIGH |

**Authoritative source input:** [50-site recommended PFT CSV](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_PFT/RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv), original Git source blob `26fdfda6f1c88c9a134e7853bd70234685665031`; exactly the **10 original Batch04 records copied unchanged** into [local source snapshot](data/AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv). Actual `clm_pct_nat_pft_json`, `mapping_profile`, caveats, sourcing and nonvascular/bare-ground policy must be used, not just this summary table.

## Soil status: recommendations are *0–30cm summaries*, not actual CLM 10-layer profiles

The original [50-site source soil register](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/Ameriflux_Site/Ameriflux_Soil/FINAL_RECOMMENDED_INPUT_SOIL_TEXTURE_50_SITES_20261026.csv), Git blob `6f2e9ff354bf5368083d212ee6aaaee2d75db390`, is snapshotted exactly for the ten Batch04 records in [data/AMF_BATCH04_10_SOIL_SOURCE_SNAPSHOT_20261026.csv](data/AMF_BATCH04_10_SOIL_SOURCE_SNAPSHOT_20261026.csv). The independent surface builder **preserves full original gridded PCT_SAND/PCT_CLAY/ORGANIC arrays** until the measured/recommended original CLM 10-layer soil profile can be matched. It never replicates a 0–30cm mean into ten soil layers as if observed.

| Site | Suggested sand/clay 0–30 cm % | Evidence |
|---|---:|---|
| US-Rpf | 18.2 / 11.9 | SoilGrids T3; permafrost/organic check |
| US-SP1 | 93.2 / 2.5 | Measured ReESH T1; organic layer check |
| US-SRG | 66.0 / 11.0 | SSURGO T2 |
| US-SRM | 85.5 / 7.3 | ReESH T1 |
| US-Seg | 70.8 / 15.8 | ReESH T1 |
| US-Ses | 66.6 / 10.3 | SSURGO T2 |
| US-Slt | 91.5 / 3.5 | SSURGO T2 |
| US-Syv | 61.2 / 10.1 | ReESH T1; organic horizon |
| US-Ton | 20.9 / 23.0 | ReESH T1 |
| US-Uaf | 17.8 / 12.3 | SoilGrids T3; permafrost/organic check |

## Fast single-command setup from immutable GitHub snapshot (no git pull)

GitHub also includes [`scripts/00_fetch_and_prepare_ameriflux_batch04.sh`](scripts/00_fetch_and_prepare_ameriflux_batch04.sh) (published revision `9913d2135887e806be1fec8f9eb084415918f1f2`), which downloads the two source-locked Python scripts and the three exact 10-site original-source tables from single **pinned commit `6a98f209e3608483b79c33141f4fe811a7c36a9a`**. First performs source self-tests and Python syntax check; with `--build` it audits actual SYVH9/SYVH12 10-site source SHAs, writes the 20-arm **planning-only** JSON and makes ten fully audited versioned initial-PFT NetCDF candidates **without** creating any CIME case or Slurm submission. The original CTSM grid surface and every meteorological source remain unchanged.

```bash
conda activate clm_fates_env
BASE="$HOME/ameriflux_batch04_fates_pair_setup"
mkdir -p "$BASE"
curl -fLsS --retry 3 \
  "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/9913d2135887e806be1fec8f9eb084415918f1f2/examples/AmeriFlux_Batch04_10/scripts/00_fetch_and_prepare_ameriflux_batch04.sh" \
  -o "$BASE/00_fetch_and_prepare_ameriflux_batch04.sh"
bash "$BASE/00_fetch_and_prepare_ameriflux_batch04.sh" --build
```

For read-only confirmation without generating ten new PFT research surfaces, replace `--build` with `--check-only`. **Do not** substitute `git pull` or run European `Batch03_10` scripts on these ten AmeriFlux stations.

## Created scripts and operational gates

[Source and paired-arm planning script](scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py):
- `--self-test` validates science register, 10 source rows, 2 planned arms; **no writes**.
- `--audit` checks all ten met source SHA, Gate0 evidence, all ten SYVH12 new surface SHA and point NetCDF PFT/soil schemas; **no writes**.
- `--plan` repeats audit, creates **only new 20-arm planning JSON** (not CIME cases) under `.../experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10` with 5+395/year stage structure and unresolved science gates.

[Independent shared-PFT candidate builder](scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py):
- `--self-test` and `--check` inspect source/data without writes.
- `--build` checks all ten source SHA, then creates **new, versioned, per-site research-only host PFT surface NetCDF** using the 50-site approved *recommendation* (not default grid PFT), idealized NATVEG100/CROP0 and host index 0 bare where specified. The same surface is referenced by both arms. **All soil texture layers and ORGANIC preserved from original source**; fields and full file SHA audited.
- **No active FATES parameter map; no active cases, DATM XML/NetCDF, Slurm jobs or 400-year simulations**.

Use **raw pinned files (no git pull)** from GitHub to a local directory and execute the following only after downloading both scripts and the three data tables:
```bash
conda activate clm_fates_env
# In local folder: scripts/{01...,02...}.py and data/*.csv/tsv
python3 -B scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py --self-test
python3 -B scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py --audit
python3 -B scripts/01_audit_source_PFT_soil_surface_and_pair_plan.py --plan
python3 -B scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py --self-test
python3 -B scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py --check
python3 -B scripts/02_build_paired_PFT_surface_candidates_NO_CASES.py --build
```

### Next actual technical work before AD5

1. Produce active time-centred **UTC DATM annual NOLEAP NetCDF** from exact SYVH9 final source (TBOT/PSRF/WIND/FSDS/FLDS/PRECTmms/QBOT), documenting the three VPD numerical-precision-only water saturation overroundings, and independently inspect stream time coordinates & true source local-clock offset.
2. Recover **per-site TA measurement height and wind height** from source tower operator/BASE/BADM or published instrumentation; ZBOT must match forcing temperature, not `HEIGHTC` and not copied 2m. If truly unavailable, only an explicit, labeled height sensitivity protocol is scientifically defensible.
3. Complete ten-site per-layer soil/organic decisions; ensure source `ORGANIC` and FATES maps are compatible, especially US-Uaf Arctic permafrost/moss; confirm `ARCTIC_PURE` actual parameter HLM map, bare zero handling for SRG/SRM/Seg/Ses; review PFT scenario uncertainty.
4. Independently build and validate per-site Full and FIXNC **AD5 CIME cases** only when all above have evidence, including PTS_LAT/PTS_LON from selected surface `LATIXY/LONGXY`, correct `CaseDocs` vs effective RUNDIR runconfig, stack soft limit ≥65536 KiB and correct Slurm archival dependencies. No auto-submission from this project creation turn.
5. Only after **each arm** AD5 model restart + archive verified: extend AD395, convert that arm to Normal400, verify Normal5 then Normal395; keep both arms independently guarded against duplicate Slurm submissions and receipt drift.

**Status**: Project directory, science snapshots, two scripts and planning method are now created in GitHub. All actual scientific inputs are **research-only** pending the case-science gates above. No Full/FIXNC CIME case, model/Slurm submission or spinup completion is claimed.
