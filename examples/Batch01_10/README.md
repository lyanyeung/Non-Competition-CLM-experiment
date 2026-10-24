# Batch01_10 — Site-observed-first fixed-biogeography / no-competition FATES

**Current protocol, 24 October 2026.** Ten forest EC towers; planned **AD400 → NORMAL400** spin-up, 800 model years each, **not started**. NL-Loo and DE-Tha are protected separate examples.

> **OVERRIDING BATCH01 DECISION:** The inherited coarse-grid surface is **not** the scientific benchmark for vegetation or station-measured soil. Never use source-grid `PCT_NATVEG`, `PCT_CROP` or `PCT_NAT_PFT` as a scientific prescription. Source soil `PCT_SAND` and `PCT_CLAY` are used **ONLY for RU-Fyo under the operator-approved, explicitly labelled technical exception**; all other site texture decisions require site-specific evidence. Stage03/04 comparisons were completed once and are **removed from the active workflow**. Their old-grid values are not site observations and are not used to choose new vegetation/soil parameters. **Do not delete or modify any original NetCDF, CIME case, restart or older experiment.** An original NetCDF may be used as the technical structural schema for building a separate versioned surface, **plus the explicitly selected RU-Fyo soil-only fallback**. It is not an observational reference for those soil values.

## 1. New model forest-point assumptions

**Explicit operator-approved idealization:** new Batch01 candidates target `PCT_NATVEG=100%` and `PCT_CROP=0%`, with other landunits set to zero as appropriate for a single idealized forest point and the pinned model's conventions. This is an *experimental assumption*, **not** a claim that all EC footprints have measured 100% forest ground cover. No source-grid fractions are carried over as scientific values.

| Site | ENF % | DNF % | DBF % | EBF % | Basis |
| --- | ---: | ---: | ---: | ---: | --- |
| CZ-BK1 | 100 | 0 | 0 | 0 | Spruce/fir stand |
| IT-Ren | 97 | 3 | 0 | 0 | Evergreen conifers + larch |
| RU-Fyo | 85 | 0 | 15 | 0 | Selected 85/15 (another survey gives 86/14) |
| CH-Dav | 100 | 0 | 0 | 0 | Spruce >99.5%; labelled proxy |
| IT-Col | 0 | 0 | 100 | 0 | Beech stand |
| FR-Fon | 2 | 0 | 98 | 0 | Operator assumption: 2 ENF + 1 DBF from residual |
| FI-Sod | 100 | 0 | 0 | 0 | Operator Scots pine forest proxy |
| FR-Pue | 0 | 0 | 5 | 95 | Operator maps remaining 5% to DBF |
| DE-Hai | 0 | 0 | 100 | 0 | All named sampled trees broadleaf deciduous |
| BE-Vie | 64 | 0 | 36 | 0 | Operator assigns reported rounding residual to ENF |

Proposed fractions: [machine-readable PFT scenarios](../../data/batch01_10_pft_scenarios.csv). Keep the [original numerical tree evidence](../../data/batch01_10_sites.csv) unchanged: literature denominators differ (species counts, carbon stocks, basal area or forest footprint). **No host-to-FATES PFT indices have yet been certified; do not assume broad ENF/DBF labels are exact model indices.**

## 2. Soil: station literature/measurements, with RU-Fyo soil-only exception

**Batch01-specific rule:** use in-situ soil particle-size measurements from the tower footprint or the same forest stand, with documented location, horizon, sampling/analysis, provenance and year. **No routine inherited CLM grid Sand/Clay fallback** and no guessed percentages from soil class labels. **The sole currently selected original-grid texture exception is RU-Fyo**, which lacks published mineral texture (peat site); use only source `PCT_SAND`/`PCT_CLAY` with clear non-observed provenance, and independently check peat thickness, organic layers and soil hydrology. If station values are unavailable, hold that site's soil parameterization for further evidence collection. Unmeasured depths need clearly labelled interpolation/extrapolation choices and appropriate uncertainty: do not call these observed. Other soil quantities (organic matter, coarse fragments, bulk density, thermal/hydraulic properties) also need source-aware treatment.

**FI-Sod measured horizons now found** in the [FLUXNET FI-Sod site description](https://fluxnet.org/sites/siteinfo/FI-Sod):

| Depth | Sand % | Silt % | Clay % | Stones % |
| --- | ---: | ---: | ---: | ---: |
| 0–10 cm | 88.12 | 6.0 | 0.5 | 5.4 |
| 10–20 cm | 93.5 | 4.1 | 0.3 | 2.1 |
| 20–40 cm | 91.9 | 2.8 | 0.2 | 5.1 |

These observed percentages include **stones**, unlike the fine-earth `PCT_SAND`/`PCT_CLAY` inputs. Process each horizon as `sand/(sand+silt+clay)*100`, `clay/(sand+silt+clay)*100` (same for silt), preserving stones and original values in evidence. Tiny non-100 totals reflect reporting precision. **No depth below 40 cm has been documented from this record**, and no full model soil profile has been approved yet.

[Station soil measured-horizon CSV](../../data/batch01_10_soil_site_observations.csv) retains FI-Sod's three explicitly depth-bounded records, while [site-published soil fractions](../../data/batch01_10_Flechard2020_TableS4_soil.csv) and [binding soil decisions](../../data/batch01_10_soil_input_decisions.csv) additionally specify CZ-BK1 and other station-level candidates; its **9 remaining placeholder rows reflect missing depth-bounded measurements, not that all nine lack literature soil values** (no invented values). [ICOS ETC Level-II site soil dataset gateway](https://traitementinfosol.pages-forge.inrae.fr/icos/index.html) is a potential source for the other ICOS towers; check whether the observations represent each target tower, review sample depths and respect site PI/data use conditions.

Run the **evidence-only soil validator**:

~~~bash
python3 -B examples/Batch01_10/scripts/06_audit_observed_soil_only.py
~~~

It computes fine-earth percentages for *observed horizons only*, flags missing stations, and never reads or writes a source surface.

## 3. What is finished, and what to do next

| Stage | Status | Role in CURRENT workflow |
| --- | --- | --- |
| Stage01 | Completed | Original site-file inventory, historical provenance |
| Stage02 | Completed | Original CIME/DATM cases: 12 candidates for 10 sites |
| Stage03/04 | Completed historically; **retired** | Readable old NetCDF, grid-landunit/soil comparisons **not used further** |
| **Stage05** | Completed | Original CIME/DATM flags traced; old cases are not FIXNC |
| **Stage06** | Completed | FI-Sod measured depth profiles; other sites' source literature in separate register |
| Stage07 | Available | Read-only local site-soil discovery, optional | 
| **Stage08** | **Next** | CZ-BK1 and RU-Fyo soil input preflight; schema and peat warnings only | 
| Future separate surface builder | Not yet approved | Versioned FIXNC forest surface after FATES/DATM/soil-layer gates |
| AD400 → Normal400 | Not started | 5-year first AD smoke, then verified continuation, then independent Normal branch |

**Historical Stage05/Stage06 commands (already executed successfully; no need to repeat):**

~~~bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1

S2="$HOME/Batch01_10_stage02_case_trace_20261024T094433Z/case_trace.json"
SCRIPT=examples/Batch01_10/scripts/05_trace_DATM_FATES_readonly.py
test -f "$S2" || { echo "Stage02 report missing"; exit 1; }

python3 -B "$SCRIPT" --self-test || exit 1
set -o pipefail
python3 -B "$SCRIPT" --stage02 "$S2" \
  2>&1 | tee "$HOME/Batch01_10_stage05_latest.log"

python3 -B examples/Batch01_10/scripts/06_audit_observed_soil_only.py \
  2>&1 | tee "$HOME/Batch01_10_stage06_soil_evidence.log"
~~~

Stage05 writes **only** a new report under `~/Batch01_10_stage05_station_inputs_<UTCSTAMP>/all_sites.json`. It audits old CIME metadata for technical consistency (especially true DATM stream/calendar and FATES parameter-map evidence), not the old gridded vegetation or soil. **Years found in CIME config are candidates and must be verified against actual forcing files/NO_LEAP treatment.** IT-Col and FR-Pue have two original cases (`S30EXCL` vs `S30SHARED`); compare the actual DATM/CIME input configuration, not their source-surface values. FR-Fon, FI-Sod, IT-Col and FR-Pue's shallow folder scan missed some CSV/DATM paths — **not proof that forcing is absent**.

## Stage05/06 completed — AD readiness decision (24 October 2026)

**Actual results:** [Stage05/06 status, soil source priorities and AD gate](docs/stage05_06_status_and_AD_gate_2026-10-24.md). Stage05 checked 12 reference cases for 10 sites: every old generated lnd_in has `use_fates_nocomp=.false.` and `use_fates_fixed_biogeog=.false.`; none is a ready-to-run new Batch01 FIXNC case. Old DATM XML lists 2018–2019 but contains conflicting effective stream-year hints; verify exact DATM source files/calendars. Stage06 confirms FI-Sod has **three measured soil horizons only**, and the other **nine** sites still lack registered site-specific numeric soil texture. **No AD400 or even AD5 smoke is yet authorized.**

**Optional soil-document discovery:** [Stage07 station-soil metadata search](scripts/07_inventory_local_soil_evidence_readonly.py) can examine existing local BIF/ancillary/ZIP files, but CZ-BK1 already has a selected published candidate and RU-Fyo has an explicit soil-only fallback. **Stage08 below is the immediate next step**. Then obtain missing site-specific measured soil, check soil layer and coarse-fragment handling, verify actual forcing and FATES parameter-map support, and build an isolated versioned site surface and new AD case. FI-Sod is the best first *preparation* candidate, not yet a launch-ready AD case.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
S7=examples/Batch01_10/scripts/07_inventory_local_soil_evidence_readonly.py
python3 -B "$S7" --self-test || exit 1
set -o pipefail
python3 -B "$S7" 2>&1 | tee "$HOME/Batch01_10_stage07_soil_discovery.log"
```

## Nine-site measured soil literature checkpoint — 24 October 2026

**New targeted literature review:** [nine-site published soil texture and sampling-depth evidence](docs/nine_site_soil_texture_literature_2026-10-24.md), with a separate [12-row site literature candidate register](../../data/batch01_10_soil_literature_candidates.csv). **Six of the nine previously missing stations now have station-related numerical soil texture candidates** (CH-Dav, IT-Col, FR-Fon, FR-Pue, DE-Hai and BE-Vie). Some are direct laboratory topsoil values; others have undetermined horizon boundaries or derived components, so they have **NOT been silently transferred into the production soil register**. Original FI-Sod three-horizon record remains intact.

Important new results: CH-Dav 0–10 cm Sand/Silt/Clay 53/25/22; FR-Pue 0–10 cm 26/32/42, plus alternate site study 26/35/39 with 75% stones at 0–50 cm; DE-Hai 0–10 cm 4/49/48 (published rounding makes 101%); FR-Fon same tower top/bottom soil 41.9/38.8/19.3 and 35.2/32.0/32.8; BE-Vie 27/55/18, layer unspecified; IT-Col 30/40/about 30, with clay **inferred** by closure not independently reported. **IT-Ren** has an ICOS ETC station particle-size data export with numeric values not yet extracted. **CZ-BK1** still needs a tower-matched texture profile. **RU-Fyo** has ~50 cm peat and should not be forced into a fabricated mineral-soil texture.

**Updated scientific work:** verify actual CLM soil-layer mapping, examine RU-Fyo peat representation and FR-Pue stone volume, and settle incompatible literature reports. **RU-Fyo alone retains original soil PCT_SAND/PCT_CLAY as an explicit modelling fallback; original-grid vegetation and all other station soil texture remain excluded.** **No AD job authorized yet.**

**IT-Ren source-provenance correction, 24 October 2026:** A widely copied soil description, **Andosol (16% clay, 56% silt, 28% sand)**, belongs to **FR-Lqu Laqueuille grassland**, NOT IT-Ren. Authoritative station match: [ICOS FR-Lqu](https://meta.icos-cp.eu/resources/stations/ES_FR-Lqu). For **IT-Ren**, Flechard et al. (2020) [supplementary Table S4, PDF p. 9](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf) reports **Haplic Podzol; clay 11%, sand 55%, silt 34%**. This is a **published site-level soil texture candidate, sample-depth unspecified**, not a validated full CLM soil profile; ICOS 2020 measured soil-horizon CSV remains to be extracted. Do not use the FR-Lqu Andosol values for IT-Ren.

## Flechard et al. (2020) — publisher literature reference and verified Table S4

**Primary literature archived as a citation/index with direct publisher PDF links:** [Flechard (2020) source record and Table S4 audit](references/Flechard_2020_Biogeosciences_Part1.md). Machine-readable [10-site Table S4 transcription](../../data/batch01_10_Flechard2020_TableS4_soil.csv) contains original published **Sand/Silt/Clay values**, missing cells, soil depths and rounding warnings. It does **not** embed the binary full-text PDFs in GitHub; it links the publisher originals under CC BY 4.0.

**Crucial correction:** Table S4 covers **9 of our 10** Batch01 sites; **CH-Dav is absent**. Among the nine, **RU-Fyo and FR-Fon have n.a. for all three texture fractions**. The most relevant values: **CZ-BK1 22/58/21** (Sand/Silt/Clay, published total **101%**), **IT-Ren 55/34/11**, **IT-Col 8/32/59** (total **99%**, conflicts with the separate Chiesi paper), **DE-Hai 4/56/40**, **FR-Pue 26/35/39**, **BE-Vie 27/55/18**, **FI-Sod 94/4/0** (total **98%**, less reliable than the recorded fine-earth horizon dataset).

**Latest operator decisions:** **CZ-BK1 is now explicitly assigned Flechard (2020) Table S4 Sand/Silt/Clay 22/58/21; the previous original-grid soil fallback is discontinued for CZ-BK1.** The 101% published total requires transparent normalization to 100% **when preparing the new surface**, and an explicitly labelled vertical-layer assumption because Table S4 does not resolve each CLM depth. **RU-Fyo alone retains the old-surface PCT_SAND/PCT_CLAY exception** in [soil decisions CSV](../../data/batch01_10_soil_input_decisions.csv). RU-Fyo remains a peat-model caveat because Flechard provides no numeric mineral texture. No sourced land-cover fractions are reactivated, and no AD5 launch is approved based on these published whole-site soil parameters alone.

## Stage08 — CZ-BK1 published texture and RU-Fyo original-soil exception

**Effective model soil decisions (operator, 24 October 2026):**

| Site | Soil composition policy | Important limit |
| --- | --- | --- |
| **CZ-BK1** | Use **Flechard et al. (2020) Table S4**: **Sand 22%, Silt 58%, Clay 21%** | The **101%** published sum is retained in provenance. Candidate for CLM input after proportional normalization: **Sand 21.782178%, Silt 57.425743%, Clay 20.792079%**; this is a **modelling normalization, not an additional observation**. Published soil depth 0.55 m does not establish measured texture in every CLM layer. |
| **RU-Fyo** | **Use original surface soil `PCT_SAND` and `PCT_CLAY` for the new model as an explicit fallback**, unchanged until the source-layer audit | No observed mineral texture in Flechard Table S4 (Peat). Original surface may lack appropriate peat/organic-layer representation; peat thickness/hydrology remain a **separate physical-model gate**. |

**Important:** New Batch01 PFT fractions and forest idealization (`PCT_NATVEG=100%`, `PCT_CROP=0%`) remain independent of the old surface in both sites. All prior source CIME cases have fixed-biogeography/no-competition flags set to `.false.` and must never be recycled as launch-ready FIXNC cases. A fresh isolated case, verified actual DATM files and FATES mapping are still needed.

**Next on IRIDIS6:** [Stage08 read-only two-site preflight script](scripts/08_preflight_CZ_BK1_RU_Fyo_soil_readonly.py) verifies both science decisions, previews the CZ rounding correction, reads old NetCDF schema, and reads **only RU-Fyo's** authorized original sand/clay profile values. **It does not create a new surface, CIME case or Slurm job.**

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
S8=examples/Batch01_10/scripts/08_preflight_CZ_BK1_RU_Fyo_soil_readonly.py
S5="$HOME/Batch01_10_stage05_station_inputs_20261024T100531Z/all_sites.json"
test -f "$S5" || exit 1
python3 -B "$S8" --self-test || exit 1
set -o pipefail
python3 -B "$S8" --stage05 "$S5" 2>&1 | tee "$HOME/Batch01_10_stage08_soil_preflight.log"
```

Stage08 resulting report is written only to `~/Batch01_10_stage08_soil_preflight_<UTCSTAMP>/all_sites.json`. After the preflight, resolve CZ-BK1 soil-layer vertical assumption, RU-Fyo peat/organic-soil compatibility and the actual FATES/DATM setup; only then construct new **versioned** surface candidates and run one-site AD5 smoke. The **AD400 multi-site production remains on HOLD**.

## Stage08 observed results; next Stage09 CZ-BK1 AD5 readiness audit — 24 October 2026

**Operator Stage08 actually PASSED**: the self-test passed; original CZ-BK1 and RU-Fyo point-NetCDF source files were readable (`READ_OK`); new source files and CIME/Slurm were untouched. Saved JSON: `/iridisfs/home/ly3n24/Batch01_10_stage08_soil_preflight_20261024T104122Z/all_sites.json`. **This is NOT an approved new AD run.**

| Site | Stage08 result | Remaining soil gate |
| --- | --- | --- |
| CZ-BK1 | Flechard2020 S4 Sand 22 / Silt 58 / Clay 21, total 101; preview normalization **21.782178 / 57.425743 / 20.792079**. One existing CIME reference case. | Set/label vertical texture allocation and check soil depth and physical parameter treatment; new surface not yet generated. |
| RU-Fyo | Old source `PCT_SAND` 10 layers = **43,43,43,43,45,45,49,51,55,55**; `PCT_CLAY` = **12,12,12,12,15,19,20,19,18,18**. One existing CIME reference case. | Original-grid soil-only fallback approved as **non-observed**, but peat organic layers and hydrology remain unverified. |

**Current release state: new FIXNC surfaces 0/10, independent AD cases 0/10.** Four blocking phases to first AD5: (1) choose CZ depth-to-CLM-layer treatment; (2) inspect actual existing DATM streams, forcing calendar/year list, CO2 setup and executable/FATES PFT mapping; (3) create and validate new **isolated** CZ-BK1 `PCT_NATVEG=100`, `PCT_CROP=0`, `ENF100` surface; (4) create a separate verified `CLM_ACCELERATED_SPINUP=on`, fixed-biogeography/no-competition AD cold-start case and submit **only 5 years** (`STOP_N=5`, `REST_N=5`, `RESUBMIT=0`) once checks pass. Existing old reference cases have non-competition and fixed-biogeography flags `.false.`; never directly submit these as new experiments.

**Next command**: the new [Stage09 CZ AD5 input-gate script](scripts/09_CZ_BK1_AD5_input_gate_readonly.py) reads original case small text docs and Stage08 output only. It checks whether the executable, FATES parameter source, original DATM stream and case references can be located. It **does not** build surfaces, cases or submit jobs, and data found in text is not yet a validated annual forcing stream.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
S9=examples/Batch01_10/scripts/09_CZ_BK1_AD5_input_gate_readonly.py
S8="$HOME/Batch01_10_stage08_soil_preflight_20261024T104122Z/all_sites.json"
test -f "$S8" || exit 1
python3 -B "$S9" --self-test || exit 1
set -o pipefail
python3 -B "$S9" --stage08 "$S8" \
  2>&1 | tee "$HOME/Batch01_10_stage09_CZ_inputs.log"
```

**Decision after Stage09:** resolve any stream/soil/FATES blockers, then implement an explicitly versioned fixed-PFT surface builder with write/verify separation. Do not infer AD readiness from a self-test alone.
## Stage09 observed result → Stage10 CZ candidate surface gate — 24 October 2026

**Actual operator Stage09 result** (`/iridisfs/home/ly3n24/Batch01_10_stage09_CZ_AD5_inputs_20261024T104558Z/all_sites.json`): Existing CZ-BK1 **CaseDocs/datm.streams.xml** and runtime stream both specify **2004–2025 inclusive** (22 annual `CZ-BK1_DATM_YYYY.nc` files) with `year_align=2004`; source folder `forcing/datm_v5_candidate_timevarying_zbot`. This replaces the misleading generic old XML fields `DATM_YR_START=2018/DATM_YR_END=2019` as the effective station-stream *configuration*. Annual files themselves still need validity/time inspection. Old `lnd_in` pins CO2 **376.95 ppm** constant and `soil_layerstruct_predefined='20SL_8.5m'`. `flds_co2=.false.` is in DATM namelist. Old case is ordinary competition/dynamic-biogeography FATES, NOT a new AD5 case.

**Next Stage10**, [CZ forcing/FATES audit and guarded versioned surface builder](scripts/10_CZ_BK1_candidate_surface_gate.py), offers four distinct modes: `self-test`, `audit`, **separately acknowledged** `build`, and `verify`. It checks **all 22 source DATM NetCDF files**, annual half-hourly record counts, actual FATES JSON host-to-PFT index1 mapping, CZ source NetCDF technical structure, and the published Flechard S4 22/58/21 soil decision. The strict audit does **not** modify any old model input and only writes a small HOME report. Even 22/22 plausible time lengths are NOT a full forcing QC or calendar validation.

**Run only Stage10 self-test and audit now:**

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
S10=examples/Batch01_10/scripts/10_CZ_BK1_candidate_surface_gate.py
S9="$HOME/Batch01_10_stage09_CZ_AD5_inputs_20261024T104558Z/all_sites.json"
test -f "$S9" || exit 1
python3 -B "$S10" --action self-test || exit 1
set -o pipefail
python3 -B "$S10" --action audit --stage09 "$S9" \
  2>&1 | tee "$HOME/Batch01_10_stage10_CZ_audit.log"
```

The **optional `build` action must NOT be treated as approved by this log**. It explicitly requires selecting a uniform proxy texture over all 10 CLM texture-input layers, although Flechard S4 reports only a site-level soil texture and 0.55 m soil depth. Any extension below 0.55 m is a **model extrapolation**; an alternative depth-aware scheme could be chosen instead. The builder checks the FATES `fates_hlm_pft_map` 1:1 ENF tree assignment and creates only a new **versioned** isolated candidate in `experiments/NonCompetitionObserved22/Batch01_10/CZ-BK1/surface/`, never overwriting source, existing cases or forcing. Even `build` alone does not submit Slurm or establish AD5 readiness.

**Current next-stage checklist**: check Stage10 audit; select soil vertical profile assumption with depth/bedrock cautions; verify annual forcing actual time axes and QC plus fixed CO2 policy; create versioned surface; clone new CIME AD case with actual `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`, `CLM_ACCELERATED_SPINUP=on`, generated `spinup_state=2`, `STOP_N=5`, `RESUBMIT=0`; validate then one isolated AD5 smoke only.

## 4. Gates before new versioned surfaces and spin-up

1. Verify original forcing streams, years, time conversion, QC, CO2 baseline, pinned executable and actual host↔FATES PFT map; **original cases are only technical provenance sources**.
2. Complete station **soil measurements** for remaining sites and depth-aware mapping; no old grid Sand/Clay substitution. Require decisions on all other physically necessary soil/hydraulic/organic parameters before production.
3. Create **new isolated surfaces** with the above experiment NATVEG/CROP assumption, chosen tree PFT fractions and proven site soil; validate numerical landunit/PFT sums, exact CTSM NetCDF schema, fixed-biogeography/no-competition flags and unchanged protected old inputs. Binary schema compatibility checks remain required even though old ecological values are discarded.
4. Run a **single site's** 5-year AD400 test first: `CLM_ACCELERATED_SPINUP=on`, correct generated `spinup_state=2`, `STOP_N=5`, `RESUBMIT=0`. Verify run and archival restart success. Only then complete the remaining AD395.
5. Start **a separate Normal400 case** from the verified AD400 restart, with normal state (`spinup_state=0`), 5-year smoke then Normal395, and convergence diagnostics. [Detailed spin-up protocol](../../docs/AD400_NORMAL400_PROTOCOL.md).

**Current science release: HOLD (10/10).** The 10 PFT mixtures and forest idealization are **chosen**; station soil is only *partly measured* for FI-Sod; DATM and mapping are still being verified. No new Batch01 cases, fsurdat, forcing or Slurm jobs have been generated by these steps.

## Supporting evidence and historical material

- [Seven-site PFT literature review](docs/seven_site_PFT_residual_followup_2026-10-24.md)
- [Four-site forest inventory evidence](docs/four_site_forest_inventory_search_2026-10-24.md)
- [Original ICOS PFT inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/ICOS_sites/ICOS_PFT)
- [General field-soil policy](../../docs/observed_soil_texture_policy.md); Batch01 uses station evidence except explicitly RU-Fyo original-soil-only fallback
- Historic [Stage01](scripts/01_audit_iridis_batch01_sources.py), [Stage02](scripts/02_trace_actual_case_inputs.py), [Stage03](scripts/03_audit_surface_soil_pft.py) and [Stage04](scripts/04_summarize_readonly_surface_gates.py) scripts are retained to reproduce prior audits but **are not part of the active site-first pipeline**.
