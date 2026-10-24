# Batch01_10 — Site-observed-first fixed-biogeography / no-competition FATES

**Current protocol, 24 October 2026.** Ten forest EC towers; planned **AD400 → NORMAL400** spin-up, 800 model years each, **not started**. NL-Loo and DE-Tha are protected separate examples.

> **OVERRIDING BATCH01 DECISION:** The inherited coarse-grid surface is **not** the scientific benchmark. Stop all scientific comparisons to its `PCT_NATVEG`, `PCT_CROP`, `PCT_NAT_PFT`, `PCT_SAND` and `PCT_CLAY`. Stage03/04 comparisons were completed once and are **removed from the active workflow**. Their old-grid values are not site observations and are not used to choose new vegetation/soil parameters. **Do not delete or modify any original NetCDF, CIME case, restart or older experiment.** An original NetCDF may be referenced only as a technical structural schema for building a separate versioned surface, not as evidence for its ecological parameter values.

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

## 2. Soil: actual station measurements, NOT the inherited surface

**Batch01-specific rule:** use in-situ soil particle-size measurements from the tower footprint or the same forest stand, with documented location, horizon, sampling/analysis, provenance and year. **No inherited CLM grid Sand/Clay fallback** and no guessed percentages from soil class labels. If station values are unavailable, hold that site's soil parameterization for further evidence collection. Unmeasured depths need clearly labelled interpolation/extrapolation choices and appropriate uncertainty: do not call these observed. Other soil quantities (organic matter, coarse fragments, bulk density, thermal/hydraulic properties) also need source-aware treatment.

**FI-Sod measured horizons now found** in the [FLUXNET FI-Sod site description](https://fluxnet.org/sites/siteinfo/FI-Sod):

| Depth | Sand % | Silt % | Clay % | Stones % |
| --- | ---: | ---: | ---: | ---: |
| 0–10 cm | 88.12 | 6.0 | 0.5 | 5.4 |
| 10–20 cm | 93.5 | 4.1 | 0.3 | 2.1 |
| 20–40 cm | 91.9 | 2.8 | 0.2 | 5.1 |

These observed percentages include **stones**, unlike the fine-earth `PCT_SAND`/`PCT_CLAY` inputs. Process each horizon as `sand/(sand+silt+clay)*100`, `clay/(sand+silt+clay)*100` (same for silt), preserving stones and original values in evidence. Tiny non-100 totals reflect reporting precision. **No depth below 40 cm has been documented from this record**, and no full model soil profile has been approved yet.

[Station soil evidence CSV](../../data/batch01_10_soil_site_observations.csv) contains FI-Sod's 3 published horizons and **9 other sites flagged NEED_SITE_OBSERVATION** (no invented values). [ICOS ETC Level-II site soil dataset gateway](https://traitementinfosol.pages-forge.inrae.fr/icos/index.html) is a potential source for the other ICOS towers; check whether the observations represent each target tower, review sample depths and respect site PI/data use conditions.

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
| **Stage05** | **Next** | Direct Stage02 → original CIME configuration, DATM streams, FATES settings (no surface comparison) |
| **Stage06** | **Next, parallel** | Station-measured soil evidence only; explicitly mark missing data |
| Stage07 surface builder | Not yet approved | Separate versioned stand-site forest surface after science/technical gates |
| AD400 → Normal400 | Not started | 5-year first AD smoke, then verified continuation, then independent Normal branch |

**Execute now on IRIDIS6** (the current Stage05 reads Stage02 **directly**, not Stage03/04):

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
- [General field-soil policy](../../docs/observed_soil_texture_policy.md), **overridden for Batch01 where it permits coarse-grid fallback**
- Historic [Stage01](scripts/01_audit_iridis_batch01_sources.py), [Stage02](scripts/02_trace_actual_case_inputs.py), [Stage03](scripts/03_audit_surface_soil_pft.py) and [Stage04](scripts/04_summarize_readonly_surface_gates.py) scripts are retained to reproduce prior audits but **are not part of the active site-first pipeline**.
