# Batch 01 — Ten quantitative-vegetation-evidence towers

**Project:** Fixed Biogeography & no competition FATES experiment  
**Planned spin-up:** **AD400 → NORMAL400**, 800 model years per tower; **NOT YET STARTED**.  
**Exclusions:** NL-Loo and DE-Tha (protected prior examples).  
**Data sources:** [original 38-site PFT inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/ICOS_sites/ICOS_PFT), the project's [22-candidate cohort](../../data/22_site_cohort.csv), and [Batch01 tabular register](../../data/batch01_10_sites.csv).

## Why these ten?

Twenty **non-example** sites are listed in the 22-site quantitative-evidence cohort. These ten are prioritized because forest tree identities mostly map to ENF, DNF, DBF or EBF without forcing all remaining unknown vegetation into one class. Even so, most measured values are **species composition, tree-carbon shares or basal area**, NOT the EC-tower footprint's measured horizontal PFT area. **All ten surfaces remain on scientific HOLD.** We have **not** created numerical `PCT_NAT_PFT` prescriptions, set crop/natural landunit fractions, altered datasets or submitted jobs.

| Rank | Station | Original batch | Original numeric evidence | Provisional functional grouping **of the reported metric only** | What must be decided before using it as a model-area surface? |
| ---: | --- | --- | --- | --- | --- |
| 1 | **CZ-BK1** | 8 | Picea abies 99%; Abies alba 1% | ENF 100% of investigated tree area | Clear local survey, but verify tower footprint/landunit areas and mapping |
| 2 | **IT-Ren** | 8 | Picea abies ≈85%; Pinus cembra 12%; Larix decidua 3% | ENF ≈97%, **DNF 3%** of trees | Explicit larch DNF; verify survey denominator and exact values |
| 3 | **RU-Fyo** | 6 | Picea abies 85%; Betula pendula 15% | ENF 85%; DBF 15% of reported stand metric | Original Table S2 metric unspecified, Russia site network/access licensing |
| 4 | **CH-Dav** | 8 | Picea abies **over 99.5%** | ENF >99.5% of tree inventory | Do not falsely round inequality to exact 100% model area |
| 5 | **IT-Col** | 13 | Fagus sylvatica 100% | DBF 100% of reported stand species | Tree monoculture is not full grid/footprint ground cover |
| 6 | **FR-Fon** | 11 | Quercus petraea 79%; Carpinus betulus 18%; other <3% | DBF ≥97% **of tree basal area** | Basal area not horizontal area; older study has a different 75/20 report |
| 7 | **FI-Sod** | 11 | Pinus sylvestris 95% | ENF 95% of stand metric | 5% not identified; original survey metric unspecified |
| 8 | **FR-Pue** | 13 | Quercus ilex 95%; other data say >80% cover | EBF 95% of reported stand composition | Stand species vs cover differ; model EBF PFT support must be verified |
| 9 | **DE-Hai** | 6 | Fagus 64%; Fraxinus 28%; Acer 7% | DBF 99% **of tree carbon stock** | Carbon shares are not land area; ~1% unclear |
| 10 | **BE-Vie** | 8 | Fagus 43%; Pseudotsuga 37% | DBF 43%; ENF 37% of reported stand metric | **20% unresolved**, metric unspecified; no silent renormalization |

**Stand-specific source links** are in the exact [Batch01 CSV](../../data/batch01_10_sites.csv). The strongest primary site-description example is [ICOS CZ-BK1](https://meta.icos-cp.eu/resources/stations/ES_CZ-BK1): it reports a 99/1 split **within the investigated area**. The recurring 2020 stand-composition source is [Flechard et al. (2020) Table S2 supplement](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf); numerical claims listed in the inventory **must still be checked at the source table level**.

## Batch organization and intended site examples

Suggested per-site future structure (directories or scripts should be created **only when the site's evidence and original input file audit is accepted**):

```text
examples/Batch01_10/
    README.md                       # this scientific cohort runbook
    scripts/01_audit_iridis_batch01_sources.py  # existing-site READ ONLY inventory
    scripts/02_trace_actual_case_inputs.py     # Stage02 generated effective CIME / DATM trace
    scripts/03_audit_surface_soil_pft.py        # Stage03 read-only source-surface and soil review
    scripts/04_summarize_readonly_surface_gates.py # Stage04 report summary; no new model writes
data/
    batch01_10_sites.csv            # source evidence, not approved surface fractions
    batch01_10_pft_scenarios.csv     # operator-selected tree-PFT assumptions; HOLD
examples/Batch01_10/<site>/
    README.md                       # site evidence & model-input decisions
    config/site_manifest.json       # per-site forcing years, CO2, case paths & SHA256
    data/evidence.csv               # provenance and denominator
    scripts/02_field_PFT_and_soil_science_review.py  # FUTURE, not built
    scripts/02_build_site_surface_VERSIONED.py
    scripts/03_AD400_smoke_and_resume.py
    scripts/04_Normal400_branch_and_resume.py
```

**No site-specific script from DE-Tha is safe to run unchanged**: DE-Tha hard-codes `1996–2025`, v2 SHA256, its run/case dirs and absolute names. Batch01 must first enumerate each tower's own verified observational forcing, DATM streams, initial date, case baselines, surface dimensions, source soil and compatible FATES PFT mapping.

## Start now on IRIDIS6 — Stage 01 ten-site inventory (model inputs read-only)

**Do this first, without writing any new surface or submitting Slurm jobs.** The purpose is to recover exact 10-site input paths from the original FLUXNET 6/8/11/13 experiments instead of reusing DE-Tha paths or assuming new case states.

Script: [01_audit_iridis_batch01_sources.py](scripts/01_audit_iridis_batch01_sources.py).

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git status --short
git pull --ff-only origin main

python3 -m py_compile \
  examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py

python3 -B examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py \
  --self-test

set -o pipefail
python3 -B examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py audit \
  2>&1 | tee ~/Batch01_10_source_inventory_stage01.log
```

The script reads `data/batch01_10_sites.csv`, verifies exactly ten sites and excludes NL-Loo and DE-Tha; inspects shallow per-site surface/forcing trees, old CIME cases and `CaseDocs/lnd_in` (when present), candidate surface percentages and soil first texture layer, year ranges in `user_nl_datm_streams`, plus existing Slurm `#SBATCH` lines. It writes **only** a new timestamped `~/Batch01_10_source_inventory_<UTCSTAMP>/all_sites.json` and `summary.csv`, prints the exact output path, and does not create, edit, cancel or submit jobs. An inventory hit is a **candidate**: it does not certify forcing quality, soil field observations, tree PFT fraction validity, model readiness or scientific equilibrium.

**Interpretation rules:**

- `EXISTS=False` / zero counts mean the canonical location did not yield the input; source files may live at different paths. Do **not** recreate or overwrite missing inputs until the alternative location is identified.
- `PCT_NAT_PFT` is a CLM surface input, and old-site PFT composition may include high crop fractions. Existing percentages do not prove the target tower's species ground area.
- **Unknown vegetation share is never assigned to GRA by this script or by default.** See [residual PFT policy](../../docs/PFT_UNKNOWN_RESIDUAL_POLICY.md). In particular, BE-Vie's remaining 20% stand species or FR-Fon's remaining <3% *tree basal area* are NOT grassland.
- Next stage: evidence-by-evidence decisions for the 10 sites, plus their site soil measurements and surface landunits, then **versioned** fixed-PFT surfaces and site-specific AD400 five-year smoke tests. Do not immediately launch 10×800 years.

**Operator follow-up:** share the Stage01 summary table, and for any missing/mismatched source cases inspect the corresponding detail in `all_sites.json` so we can construct the exact per-site setup instead of guessing paths.

## Stage01 IRIDIS6 observed result — 24 October 2026

The operator completed the ten-site Stage01 inventory and reported **SELF-TEST PASS**, 10/10 site roots found, no model/source writes and no Slurm jobs submitted. Report files on IRIDIS6 are:

- `/iridisfs/home/ly3n24/Batch01_10_source_inventory_20261024T090713Z/all_sites.json`
- `/iridisfs/home/ly3n24/Batch01_10_source_inventory_20261024T090713Z/summary.csv`

| Site | Existing cases | Candidate point surfaces | Scanned processed CSV count | Scanned DATM directories | Operational attention |
| --- | ---: | ---: | ---: | ---: | --- |
| CZ-BK1 | 1 | 1 | 6 | 1 | confirm surface and exact DATM stream |
| IT-Ren | 1 | 1 | 6 | 1 | confirm surface and exact DATM stream |
| RU-Fyo | 1 | 1 | 10 | 2 | resolve two alternative DATM locations |
| CH-Dav | 1 | 1 | 6 | 1 | confirm surface and exact DATM stream |
| IT-Col | 2 | 1 | 0 | 0 | **two existing cases; trace actual forcing from CIME** |
| FR-Fon | 1 | 1 | 0 | 1 | DATM candidate directory exists; find actual forcing |
| FI-Sod | 1 | 1 | 0 | 1 | DATM candidate directory exists; find actual forcing |
| FR-Pue | 2 | 1 | 0 | 0 | **two existing cases; trace actual forcing from CIME** |
| DE-Hai | 1 | 1 | 10 | 2 | resolve two alternative DATM locations |
| BE-Vie | 1 | 1 | 6 | 1 | confirm surface and exact DATM stream |

**Interpretation:** this scan only checks a few known folder naming conventions. `CSV=0` or `DATM=0` is **not** proof of missing forcing, and two cases do not mean two independent valid baseline datasets. No Batch01 site has passed scientific fixed-PFT area/soil-depth gates yet.

### Stage02 — trace exact baseline CIME inputs before choosing any surface

GitHub script: [02_trace_actual_case_inputs.py](scripts/02_trace_actual_case_inputs.py), **read-only for model inputs**, writes only a new HOME report.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main

INPUT=/iridisfs/home/ly3n24/Batch01_10_source_inventory_20261024T090713Z/all_sites.json
SCRIPT=examples/Batch01_10/scripts/02_trace_actual_case_inputs.py

python3 -m py_compile "$SCRIPT"
python3 -B "$SCRIPT" --inventory "$INPUT" --self-test

set -o pipefail
python3 -B "$SCRIPT" --inventory "$INPUT" \
  2>&1 | tee ~/Batch01_10_stage02_case_trace.log
```

Stage02 reads `CaseDocs/lnd_in`, `CaseDocs/datm_in`, actual DATM stream candidates, `user_nl_datm_streams`, candidate runtime stream files, original `fsurdat` checksums, CIME XML metadata and existing `#SBATCH` lines. It does **not** repair forcing, create PFT surfaces, alter old cases or submit jobs. A source inventory identifies paths but **does not validate tower field soil or EC footprint PFT fractions**.

After Stage02, adjudicate `IT-Col` and `FR-Pue` duplicate cases, determine the actual DATM streams for all ten, and review source-area denominators. Only then advance CZ-BK1, IT-Ren and IT-Col to an explicit site-specific FIXNC surface candidate. Unknown vegetation composition must **not** automatically become GRA.

**Other seven towers:** [Seven-site PFT residual follow-up (24 October 2026)](docs/seven_site_PFT_residual_followup_2026-10-24.md) adds primary/official evidence for RU-Fyo, CH-Dav, FR-Fon, FI-Sod, FR-Pue, DE-Hai and BE-Vie. Main findings: RU-Fyo wet spruce 86/14 versus older 85/15; DE-Hai small remainder belongs to DBF tree species; CH-Dav nearly all ENF trees; FR-Fon other <3% includes ENF pine; FR-Pue secondary 90/10 claim requires reconciliation; FI-Sod 5% trees still unclassified; BE-Vie remaining 20% has ENF and DBF species but no exact shares. **None authorizes automatic GRA or complete EC-footprint PFT-area allocations.**

## Batch01 PFT closure checkpoint — 24 October 2026

This checkpoint separates **forest-tree functional-type closure** from **approval of a CLM-FATES horizontal-area surface**. It summarises the 10-site register and the [seven-site evidence follow-up](docs/seven_site_PFT_residual_followup_2026-10-24.md). No species percentage in this table is automatically `PCT_NAT_PFT`.

| Evidence group | Sites | Reported forest-tree PFT information | Outstanding decision |
| --- | --- | --- | --- |
| Complete reported tree-type grouping (3) | CZ-BK1, IT-Ren, IT-Col | CZ-BK1 ENF 100% (99 spruce + 1 fir); IT-Ren ENF ~97% + DNF ~3%; IT-Col DBF 100% | Confirm denominators, footprint/landunits, soil and original case inputs |
| Functionally near-resolved / conditional proxy (3) | RU-Fyo, DE-Hai, CH-Dav | RU-Fyo ENF/DBF 85/15 (alternate 86/14 with different birch species); DE-Hai named remaining tree species DBF, so DBF 100% **only as a conditional tree-group proxy**; CH-Dav ENF >99.5%, ENF 100% **only as a labelled proxy** | RU-Fyo reconcile source year and birch identity; DE-Hai verify ~1% residual is entirely DBF; CH-Dav retain <0.5% uncertainty |
| Species groups found, residual percentages unresolved (3) | FR-Fon, FR-Pue, BE-Vie | FR-Fon DBF 97% of basal area with other <3% including ENF pine and deciduous species; FR-Pue EBF 95% stand composition vs unverified 90/10 EBF/DBF alternative; BE-Vie DBF 43% + ENF 37% + mixed woody residual 20% | Obtain comparable source-year, denominator-specific quantitative shares; BE-Vie 20% is highest-priority gap |
| Residual trees not identified (1) | FI-Sod | ENF pine 95%, other 5% trees not confirmed; ground-layer lichen/moss/shrub percentages use a different denominator | Identify remaining tree species and fractions; never fill remainder with ground-layer percentages |

**Historical literature note (before operator scenario decisions):** four sites originally lacked complete measured species shares (FR-Fon, FR-Pue, BE-Vie, FI-Sod). **As of 24 October 2026, operator-selected tree-PFT candidate mixtures now exist for all four**, including FI-Sod ENF100. This closes the *scenario selection* gap, NOT the unmeasured species evidence or approval of model surface area fractions. The other six are suitable for *drafting*, not approving, stand-tree PFT proposals. Neither the 3 complete reported groups nor the 3 conditional proxies prove EC-footprint area fractions.

**Scientific release gate remains 0/10**: All sites retain `EVIDENCE_ONLY_HOLD_SURFACE` until source metric/footprint, natural-vs-crop landunits, PFT mapping, soil provenance, actual case inputs and versioned-surface QA are reviewed. There is no authority here to write production `PCT_NAT_PFT`, modify old cases, launch AD400/NORMAL400, or send unknown residual to GRA.


**New forest inventory evidence (24 October 2026):** [Four-site inventory search](docs/four_site_forest_inventory_search_2026-10-24.md) identifies a **BE-Vie 70% cumulative EC-footprint species classification** (2018 drone mapping; published ESSD 2026): Norway spruce 38% ENF, silver fir 14% ENF, Douglas fir 9% ENF, Scots pine 2% ENF, European beech 36% DBF. **ENF 63% + DBF 36% = 99% reported**; residual 1% is not silently normalized. This supersedes the *unknown-20% issue for this footprint-specific evidence*, NOT the older stand-study denominator or the production-surface HOLD. FR-Fon and FR-Pue now have documented tree-inventory plot leads but not minority-species fractions; FI-Sod remains unidentified at 5%. In the **observational inventory** these uncertainties remain; subsequent operator decisions in the next section assign model-only candidate fractions, including FI-Sod ENF100. No inventory evidence has been changed.

## Operator-selected candidate PFT scenarios — 24 October 2026

**Decision type:** operator-specified, **assumption-based TREE-PFT mixture only**. These percentages are *not* newly observed forest inventory and are *not* approved `PCT_NAT_PFT` fractions or cell-area prescriptions. Do not change any production surface, CIME case or Slurm job from this documentation.

| Site | ENF | DBF | EBF | Assumption/evidence |
| --- | ---: | ---: | ---: | --- |
| FR-Fon | **2%** | **98%** | 0% | Operator assigns 2% of the <3% miscellaneous basal-area share to ENF pine and 1% to DBF, added to published DBF 97%. Because original 'other' is **<3%**, the exact 2+1 partition is a convenient 100%-summing model approximation, NOT a measured or mathematically exact reconstruction. |
| FR-Pue | 0% | **5%** | **95%** | Operator allocates all unclassified 5% tree composition to DBF; independent verification of this 5% is unavailable. Alternative published 90/10 from a different denominator should not be silently merged. |
| BE-Vie | **64%** | **36%** | 0% | Operator allocates the 1 percentage point missing from ESSD 2026 rounded drone-classification figures (ENF reported 63%, DBF 36%, sum 99%) to ENF, conditional on a stable 70% cumulative EC footprint. **64% ENF is assumption, not directly measured.** Earlier stand 43/37/20 uses a different denominator. |
| **FI-Sod — selected primary assumption** | **100%** | **0%** | **0%** | **Operator decision, 24 October 2026:** use an all-ENF tree-PFT candidate based on the ICOS Scots pine forest description. This explicitly allocates the 5% not identified in the original 95% stand composition to ENF **as a model assumption, not a measured inventory share**. The previously suggested ENF95/DBF5 sensitivity is **not selected or authorized as an active Batch01 scenario**. |

**FI-Sod operator decision:** ENF100 is the sole selected **primary Batch01 tree-PFT scenario**; ENF95/DBF5 is not an active scenario. The original source record still says pine 95% and unknown 5%, and this difference must remain visible in provenance.

FI-Sod renewed search: [ICOS tower](https://meta.icos-cp.eu/resources/stations/ES_FI-Sod) identifies Scots pine natural-regeneration forest; [FMI](https://en.ilmatieteenlaitos.fi/ghg-sodankylaicos) gives approximately 2,100 stems/ha and ~12 m height, **not** a species inventory; [Finnish NFI](https://www.silvafennica.fi/article/24045) provides only regional mixture evidence. None resolves the tower's tree-species 5%. Distinguish the Sodankylä forest EC tower from the neighboring Halssiaapa wetland tower.

**Scientific gates:** precise inventory denominator, natural landunit area, soil texture and depth, compatible FATES PFT labels and actual model input QA are all still outstanding. **All ten final surfaces remain on HOLD.** For further baseline evidence see [four-site inventory follow-up](docs/four_site_forest_inventory_search_2026-10-24.md).

## Stage03 — ten-site candidate PFT, source surface and soil audit (read only)

**New since Stage02:** [selected ten-site model-tree PFT scenarios](../../data/batch01_10_pft_scenarios.csv) preserve all 10 operator-defined **ENF/DNF/DBF/EBF** candidates **separately** from [raw source evidence](../../data/batch01_10_sites.csv). FR-Fon 2 ENF/98 DBF; FR-Pue 95 EBF/5 DBF; BE-Vie 64 ENF/36 DBF; FI-Sod 100 ENF. Scenario percentages sum to 100 **among modelled tree functional groups**, NOT automatically within the whole footprint/grid cell or current CLM host NATVEG area. No FATES PFT index is assigned at this step.

**Run on IRIDIS6; the Stage01 inventory has already been reported at** `/iridisfs/home/ly3n24/Batch01_10_source_inventory_20261024T090713Z/all_sites.json`. **First run Stage02** if its `case_trace.json` is not already available or current, then **Stage03**. These two scripts read existing source/CIME files and write reports to new timestamped HOME directories only. They never create production fsurdat, change Slurm jobs, or approve any case.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1

S1="$HOME/Batch01_10_source_inventory_20261024T090713Z/all_sites.json"
S2="examples/Batch01_10/scripts/02_trace_actual_case_inputs.py"
S3="examples/Batch01_10/scripts/03_audit_surface_soil_pft.py"

test -f "$S1" || { echo "Stage01 report missing; stop safely"; exit 1; }
python3 -B "$S2" --inventory "$S1" --self-test || exit 1
python3 -B "$S3" --self-test || exit 1

set -o pipefail
python3 -B "$S2" --inventory "$S1" \
  2>&1 | tee "$HOME/Batch01_10_stage02_latest.log" || exit 1

TRACE=$(find "$HOME" -maxdepth 2 -type f -name case_trace.json \
  -path "$HOME/Batch01_10_stage02_case_trace_*/case_trace.json" \
  -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)
test -n "$TRACE" && test -f "$TRACE" || exit 1
echo "Stage02 trace: $TRACE"

python3 -B "$S3" --case-trace "$TRACE" \
  2>&1 | tee "$HOME/Batch01_10_stage03_latest.log"
```

**Read output:** `~/Batch01_10_stage03_surface_soil_<UTCSTAMP>/summary.csv` and `all_sites.json`. Stage03 reports **each** candidate existing fsurdat and exact case path; it flags duplicate baseline cases (notably IT-Col / FR-Pue), missing source surfaces, nonzero crops, non-100 natural landunits, suspicious conditional PFT sums and the first sand/clay grid-layer values. It makes **no case choice** and does **not** claim that source-grid soil is locally measured. A `READ_OK` only confirms NetCDF readability, not scientific adequacy. Review each site's actual forcing calendar and effective DATM stream from Stage02 rather than assuming that the Stage01 shallow folder scan found it.

**Next decision after reviewing these reports:** choose one validated baseline case/forcing configuration per station, verify soil depth/provenance and natural-vs-crop landunit coverage, and validate exact FATES host-PFT indices (ENF, DNF, DBF, EBF are broad ecological groups). Only after explicit scientific review should we implement *new versioned* FIXNC fsurdat candidates and one-site AD400 five-year smoke tests. **All Batch01 sites remain HOLD for production and Slurm.**

## Stage02–03 confirmed IRIDIS6 outcomes and Stage04 extraction — 24 October 2026

**Observed operator results, not an inference about production readiness:** Stage02 self-test passed; Stage03 self-test passed; both main scripts completed without modifying original inputs or submitting Slurm jobs. Stage02 found one candidate baseline case per site **except IT-Col and FR-Pue (two each)**, giving **12 case records for ten sites**. Stage03 read **one candidate original fsurdat successfully per site (10/10)**, and all selected 10-site tree-PFT hypotheses passed the 100% sum validation. All ten remain **HOLD**. A readable NetCDF says nothing about scientific validity of surface PFT, soil provenance or the effective FATES fixed-biogeography mapping.

Operator report references:
- Stage02 `/home/ly3n24/Batch01_10_stage02_case_trace_20261024T094433Z/case_trace.json`
- Stage03 `/iridisfs/home/ly3n24/Batch01_10_stage03_surface_soil_20261024T094433Z/all_sites.json`

Stage02 displayed `CSV=0` for **IT-Col, FR-Fon, FI-Sod, FR-Pue** and `DATM=0` for **IT-Col, FR-Pue**, which are **limitations of the initial shallow inventory, not evidence of missing real forcing**. RU-Fyo and DE-Hai each listed two DATM directory candidates. Duplicate IT-Col/FR-Pue case names refer to `S30EXCL` and `S30SHARED`; do not select by suffix alone.

**Next: Stage04 print-only review of existing reports** (no additional NetCDF reads and no output except stdout). The new [04_summarize_readonly_surface_gates.py](scripts/04_summarize_readonly_surface_gates.py) prints original source-host `PCT_NATVEG`, `PCT_CROP`, first-layer source-grid `PCT_SAND`/`PCT_CLAY`, existing conditional host-PFT sum, Stage03 issue flags and Stage02 case calendar excerpts. Source-soil first layer is **not** verified field soil. For missing fields or ambiguous shapes the display is `-`, not zero.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git status --short
git pull --ff-only origin main || exit 1
STAGE03="$HOME/Batch01_10_stage03_surface_soil_20261024T094433Z/all_sites.json"
test -f "$STAGE03" || exit 1
set -o pipefail
python3 -B examples/Batch01_10/scripts/04_summarize_readonly_surface_gates.py \
  --stage03 "$STAGE03" \
  2>&1 | tee "$HOME/Batch01_10_stage04_review.log"
```

Review the full Stage04 table and flags before deciding whether to retain the old natural/crop landunit percentages, choose a different baseline case, use field-measured soil or a labelled grid fallback, or construct any new versioned FIXNC surface. **No AD400/Normal400 runs yet.**

## Readiness gates to work through, in order

1. **Observed PFT provenance:** retrieve actual station/forest source, verify measurement year, survey method, spatial coverage, specific **denominator** and any species sum. Record the unknown share. A scientific proxy must be proposed and explicitly recorded before it can become a fixed PFT surface.
2. **Existing CLM-FATES evidence:** identify each site's already developed 6/8/11/13-site source forcing, stream calendars, original surface data and CIME case in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows). Validate original file checksums and source data license; never modify old spinups or cases.
3. **Observed soil texture first:** find reliable tower/stand sand, silt and clay data, document depth and particle convention. Build a **new versioned** surface from site evidence when available; otherwise use a labeled source-grid fallback. Do not infer sand/clay percentages from soil classification names alone.
4. **Batch01 individual dry-run:** cross-check 100% landunit totals, `PCT_NAT_PFT`, dynamic FATES mapping, generated `lnd_in`, `spinup_state=2`, source hashes, executable and per-case Slurm single-core launch / real `#SBATCH` parameters.
5. **AD400:** first cold-start 5-year AD smoke and **verified archive**, then 395 years in the **same AD case**, guarded. Use **one** source forcing cycle repeatedly.
6. **NORMAL400:** wait for full AD400 restart, branch into a **separate** new hybrid normal case, 5-year smoke to verify `spinup_state=0`, then separate 395-year continuation. Do **not** transform an active AD resubmitting case in place.
7. **Scientific convergence:** inspect soil C/N, FATES carbon pools/LAI, GPP/NEE and water balance over the final years; normal-pool equilibration is not proven by calendar length alone.

Protocol: [AD400 → NORMAL400](../../docs/AD400_NORMAL400_PROTOCOL.md). All Batch01 sites are currently **EVIDENCE_ONLY_HOLD_SURFACE**. No CIME or Slurm experiments have been generated for the new ten as part of this planning change.

## The separate ten-site Batch02 reserve

[Batch02 CSV](../../data/batch02_10_sites.csv) contains **DK-Sor, FR-Hes, FR-FBn, BE-Bra, IT-Noe, CH-Fru, CH-Lae, ES-LJu, FI-Hyy, IT-MBo**. Several have conflicting temporal stand measurements, unresolved needleleaf mixtures or ground-cover/vegetated-cover denominators; they remain screened leads, not rejected sites. They are not Batch01 and should not be silently swapped into Batch01 without updating the two registers.

## Preserving the two example histories

**NL-Loo** has a historic PRE50/AD200 workflow. **DE-Tha** had a direct AD400 cold start: its first 5-year AD and a separate AD5→Normal5 mode-switch **already succeeded**, and its remaining 395 AD years had been **submitted**, but not confirmed finished at the time this register was created. Both example histories are deliberately retained rather than rewritten into the new 800-year standard.
