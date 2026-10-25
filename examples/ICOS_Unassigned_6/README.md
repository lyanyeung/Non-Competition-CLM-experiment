# Six unassigned ICOS FIXNC sites — evidence-pinned PFT decision gate (25 October 2026)

## Scope and source authority

The user-provided [ICOS_PFT README](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/ICOS_sites/ICOS_PFT) and its authoritative [FINAL_38_SITE_FIXNC_PFT_20261025.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv) label **six** sites `fixnc_cohort=Not assigned`: **CH-Aws, DE-Gri, DE-RuR, IT-Tor, ES-Agu, GL-ZaH**. These are the six **ICOS** unassigned sites, not the distinct six outstanding AmeriFlux Batch01 stations (CA-Cbo, CA-Man, CA-TP1, CA-TP3, US-Aud, US-Bar).

Pinned source: official CSV Git blob **`63739e00408443bcbb4b286bb3324c76e9fd9100`**, 38 site rows. Additional source: [six-site sparse/bare ground review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/SIX_SITE_BARE_GROUND_PFT_EVIDENCE_20261025.md). Model-source crosswalk: existing original Batch02 [actual FATES matrix](../../data/batch02_verified_HLM_FATES_map_20261025.json), frozen shared JSON SHA256 `0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04`.

**Important distinction:** these are experimental prescribed *host natural PFT* `PCT_NAT_PFT` conditional compositions, NOT true measured footprint PFT-area vectors. A conditional grassland PFT proxy is not observed 100% bare-free tower-area cover. Bare is `PCT_NAT_PFT[0]` *inside* `PCT_NATVEG=100`, NOT a separate crop/lake landunit. Full 15-element vectors sum to 100; do not renormalize only green vegetation.

## Six-site decision matrix and executable model candidate values

| Site | Scientific evidence / denominator | HLM 0..14 nonzero entries (%) | FATES mapping / readiness |
|---|---|---|---|
| **CH-Aws** | Alpine meadow: Festuca rubra, Phleum, Trifolium, qualitative only | **13:C3 cool grass 100** | **TECHNICAL CANDIDATE/HOLD**: original CH-Aws FLUXNET source/negative-RH case failed; must establish stable reference case and forcing QC before model startup; no bare-ground measurement |
| **DE-Gri** | Managed meadow with mixed grasses and forbs, no area fractions | **13:C3 cool grass 100** | **TECHNICAL CANDIDATE** representing all herbs as FATES cool C3 grass; no forb PFT; obtain measured herbaceous cover before quantitative inference |
| **DE-RuR** | Managed meadow (Alopecurus, Lolium, Poa), no area fractions | **13:C3 cool grass 100** | **TECHNICAL CANDIDATE**; no native type for forbs; confirm grass/water/soil management |
| **IT-Tor** | Nardus stricta alpine grassland, other species qualitative | **13:C3 cool grass 100** | **TECHNICAL CANDIDATE**; Alpine/grazing phenology sensitivity remains |
| **ES-Agu** | Published ground: vegetation 51%, bare gravel/rock/soil 49%; Macrochloa 57% **of vegetation** (reported, original Rey 2011 denominator not yet confirmed) | **0:bare 49 / 13:C3 grass 29 / 9:evergreen temperate shrub 22** | **PROPOSED; NOT APPROVED**: 0.51 × 0.57 ≈ 0.2907 (29% of whole ground). The remainder of vegetated 51% is ≈22%; sensitivity ~bare35 for alternate source; before model fix actual source denominator and biocrust |
| **GL-ZaH** | Zackenberg Cassiope heath plots: vascular 57% (Cassiope 53, Salix 3, herbs ~1); moss8 + lichen3, ~32 uncovered; patch extrapolation not tower-footprint measured | **0:bare 43 / 9:Arctic evergreen dwarf shrub 53 / 11:Arctic deciduous shrub 3 / 12:Arctic C3 grass 1** | **PROPOSED; REQUIRES PRIVATE PARAM MAP**: default host9 maps to temperate evergreen shrub; default host11 is a mixture (10% hydrodecid extratrop,10% evergreen Arctic,80% deciduous Arctic), so raw PCT entries alone do NOT reproduce Arctic cover |

Current actionable scientific status: four herbaceous single-PFT *model proxies* can be coded for candidate surfaces after source-case/input/landunit preflight; ES-Agu can be modelled as **explicit conditional sensitivity scenarios only** pending primary-source denominator check. GL-ZaH requires a **site-only private parameter** to avoid temperate shrub trait mismatch; no CIME case should be submitted until generated `lnd_in` points at its private file and actual FATES model output demonstrates the intended Arctic and bare patch areas.

## Primary-source confirmation: CH-Aws, DE-Gri and DE-RuR — grassland YES, grass area fraction 100% NOT measured (25 October 2026)

Following direct review of **official Swiss FluxNet, ICOS, FLUXNET, university and peer-reviewed site publications**, all three towers are demonstrably **grassland (IGBP GRA)**, but assigning host natural PFT index13 to **100%** is a **conditional single-PFT model representation of mixed C3 HERBACEOUS vegetation**, not proof of 100% Poaceae ground cover, 100% canopy or bare-free EC footprint.

| Site | Direct primary evidence | Herbaceous vegetation includes | Numerical species/area evidence | PFT release interpretation |
|---|---|---|---|---|
| **CH-Aws (Alp Weissenstein)** | [Swiss FluxNet official station](https://www.swissfluxnet.ethz.ch/index.php/sites/site-info-ch-aws-2/); [Li et al. 2023, *Frontiers in Plant Science*](https://pmc.ncbi.nlm.nih.gov/articles/PMC10203623/); [Swiss FluxNet 2024 public data](https://www.swissfluxnet.ethz.ch/index.php/2024/11/01/now-available-new-fluxnet-icos-datasets/) | Grazed alpine grassland at 1900–2500m; **Festuca rubra, Phleum rhaeticum, Poa alpina** grasses, **Trifolium repens** legume, **Taraxacum officinale, Alchemilla vulgaris** broadleaf forbs | Descriptions and dominant species; NO measured grass/forb/bare cover percentages of full EC footprint found in these sources | **GRA CONFIRMED**; HLM13 C3 grass 100 conditional HERBACEOUS proxy only. CH-Aws unstable original case/negative RH remains separate technical HOLD |
| **DE-Gri (Grillenburg)** | [ICOS station metadata](https://meta.icos-cp.eu/resources/stations/ES_DE-Gri) | ~40 ha permanent unfertilised mesophytic hay meadow, mown 1–3 times yearly, occasionally autumn-grazed. Grasses **Elymus repens, Alopecurus pratensis**; forbs **Achillea millefolium, Rumex acetosa**; legume **Trifolium repens**. Forest surrounds meadow but footprint investigation indicates target grassland well represented | No plant functional-group cover percent, no bare cover fraction or full footprint 100% herbaceous fraction in the source | **GRA CONFIRMED**; HLM13 100 conditional mixed-herbaceous proxy, not grasses-only or spatially measured |
| **DE-RuR (Rollesbroich)** | [ICOS station metadata](https://meta.icos-cp.eu/resources/stations/ES_DE-RuR); [FLUXNET station metadata](https://fluxnet.org/sites/siteinfo/DE-RuR); [HESS 2022 vegetation functional-group lysimeter survey](https://hess.copernicus.org/articles/26/2277/2022/) | Permanent grazed/mown grassland. Grasses **Lolium perenne, Poa pratensis, Alopecurus pratensis, Poa trivialis, Dactylis glomerata**; forbs **Rumex acetosa, Taraxacum officinale, Ranunculus repens**; legumes **Trifolium repens** | **YES, function-group quantitative observation exists:** HESS 2022 annual **2011–2016** **64 × 10cm grid cells** on **1m² lysimeter plots**, grouping grasses vs legumes vs non-legume herbs; composition changed over time. Important: those lysimeters are **NOT the whole EC tower footprint**. Neither 100% grass area nor zero bare area was established | **GRA CONFIRMED**; HLM13 100 conditional HERBACEOUS proxy; stronger scope for grass/legume/forb sensitivity or observational validation using HESS supplementary Fig. S2 |

**What is and is not correct for FIXNC:**

1. **Correct:** classify these sites as perennial managed **C3 grassland ecosystems** and run a *clearly labelled* simplified FATES setup with HLM13 `cool_c3_grass=100` **conditional on the model natural vegetation landunit**. This maps all herbaceous species (including forbs and legumes, since the current 14-class FATES map lacks a distinct forb/legume class) into one C3-grass functional type.
2. **Not evidence-based:** claim the site **actually measured 100% grasses (Poaceae)**; claim `PCT_NATVEG=100` or `PCT_NAT_PFT[0]=0` proves whole EC footprint is free of bare rock/soil, shrubs, or forest-edge flux; or claim a mixed-herb PFT proxy preserves observed legume N fixation / forb physiology / species management effects.
3. **Evidence grading:** site land cover **HIGH confidence** all 3; site-specific PFT horizontal area shares **UNVERIFIED** all 3. DE-RuR has an additional **PFT-group quantitative evidence lead** (2011–2016 lysimeters) worth extracting, with *sampled-area denominator* and survey dates stored. Do not relabel its incomplete coverage as 100% grass.
4. **Next action:** CH-Aws source/negative-RH/unstable template fixed separately; DE-Gri, DE-RuR may proceed to **input/surface preflight as MODEL PROXIES only**, not directly to long AD395/Normal400 spinup before the 5yr and bare/management checks. Consider separate seasonal mowing/forb/legume sensitivity if ecosystem flux realism is the goal.

**Proposed defensible methods wording:** “Grassland tower vegetation was represented using a single `cool_c3_grass` FATES PFT for all herbaceous cover, as a modelling simplification rather than an observed 100% grass-species or flux-footprint area fraction.”

---

## Operator-selected FIXNC model proxy assignment for all six stations (25 October 2026)

**User decision (25 Oct 2026):** keep the six PFT model candidate fractions listed in the current ICOS evidence register as the **selected FIXNC experimental proxy configuration** without revising their scientific evidence. This authorizes **PFT scenario selection**, not bypassing unresolved original forcing/surface inputs, measured-area evidence, local FATES parameter-mapping requirements, or automatic model submission. Original authoritative 38-station evidence remains unchanged. Current machine-readable frozen choice: **[`data/six_site_FIXNC_operator_selected_PFT_20261025.csv`](data/six_site_FIXNC_operator_selected_PFT_20261025.csv)**.

- CH-Aws, DE-Gri, DE-RuR, IT-Tor: **`PCT_NAT_PFT[13]=100`**, clear model label **`C3_HERBACEOUS_COMMUNITY_PROXY`**. It represents grass+forb+legume functionality using the model's sole cool C3 grass PFT, not measured 100% grass species cover; CH-Aws original negative RH/template instability separately blocks a run.
- ES-Agu: **`PCT_NAT_PFT[0]=49`, `[9]=22`, `[13]=29`**, explicit conditional `BARE_GRASS_SHRUB_GROUND_COVER_PROXY`. User accepts candidate despite still-unverified Macrochloa 57% coverage denominator; record competing alternate sensitivity.
- GL-ZaH: **`PCT_NAT_PFT[0]=43`, `[9]=53`, `[11]=3`, `[12]=1`**, explicit `ARCTIC_HEATH_PRIVATE_FATES_MAPPING_PROXY`. Use **GL-only private JSON**, never default HLM9→temperate shrub or shared parameter modifications; patch host index9→Arctic evergreen shrub and index11→Arctic deciduous shrub before case preview.
- All 15-element `PCT_NAT_PFT` totals sum to 100 *conditional on model NATVEG*. Do not auto-renormalize vegetated part or reinterpret species evidence as whole footprint.

**Operational readiness remains distinct from choosing model PFT fractions:** first obtain site-specific template, correct `PTS_LAT/LON` matching `fsurdat LATIXY/LONGXY` and forcing, stable forcing quality, original source-year/CO2, soil proxy/source provenance, verified GL private parameter where needed, then 5-year technical smoke **before** AD395. No six-site model job was launched by recording this operator choice.

---

## Exact GL-ZaH host / FATES map correction

Shared FATES parameter JSON uses names in fixed order (14 FATES PFTs). For **GL-ZaH only**, private JSON should set:

- **Host natural index9** → **100% `broadleaf_evergreen_arctic_shrub`** (instead of the shared default temperate evergreen shrub);
- **Host natural index11** → **100% `broadleaf_colddecid_arctic_shrub`** (instead of default 0.1 hydrodecid-extratrop, 0.1 evergreen-Arctic and 0.8 colddecid-Arctic);
- **Host natural index12** → unchanged **100% `arctic_c3_grass`**;
- **Host bare index0** → 43% bare-ground patch, not included in 14-by-14 FATES host mapping.

Do not mutate shared `CTSM/src/fates/parameter_files/fates_params_default.json`; the next FATES case would use a new site-only file and verify CIME `fates_paramfile` in generated `CaseDocs/lnd_in`. Do not change other stations' host9 mapping.

## Script (no model jobs)

[Source-checked six-site PFT and GL private-map tool](scripts/01_pft_six_and_GL_arctic_map.py) has three modes: `--self-test` (no files), `--check --source CSV` (read-only site/PFT/FATES map audit), `--make-private-gl --source CSV --outdir NEW --ack-gl-proxy` (only new candidate private GL-ZaH JSON with provenance manifest, no surface/case/Slurm).

```bash
DIR="$HOME/Non-Competition-CLM-experiment/examples/ICOS_Unassigned_6"
mkdir -p "$DIR/scripts"
curl -fLsS https://raw.githubusercontent.com/lyanyeung/CLM-FATES-single-site-workflows/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv -o "$DIR/FINAL_38_SITE_FIXNC_PFT_20261025.csv"
# Download the exact pinned script into "$DIR/scripts/01_pft_six_and_GL_arctic_map.py"
python3 -B "$DIR/scripts/01_pft_six_and_GL_arctic_map.py" --self-test
python3 -B "$DIR/scripts/01_pft_six_and_GL_arctic_map.py" --check --source "$DIR/FINAL_38_SITE_FIXNC_PFT_20261025.csv"
# Only if check passes and a private GL file candidate is desired (DOES NOT start a model):
python3 -B "$DIR/scripts/01_pft_six_and_GL_arctic_map.py" --make-private-gl --source "$DIR/FINAL_38_SITE_FIXNC_PFT_20261025.csv" --ack-gl-proxy --outdir "/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/ICOS_Unassigned_6/GL-ZaH_private_arctic_map_candidate_v1"
```

## Required steps *before* six-site FIXNC case rollout

For each of six: inventory original site-specific CIME case, forcing years/UTC and QC, actual site-specific surface and **`PTS_LAT/LON` versus surface `LATIXY/LONGXY`**, available soil fallback/observations, correct datm cycle, active FATES parameter matrix and site-specific stand percentages. This explicit CIME point check is mandatory because the AmeriFlux CA-TP4 AD5 first run **failed at `surfrdMod.F90:122` due to inherited CH-Dav PTS_LAT/LON**. CH-Aws remains HOLD until its negative RH/underlying source template is stable. GL-ZaH must also pass physically plausible Arctic C3/shrub trait behavior and coldstart, plus 1–5-year smoke; bare-ground patches must not develop woody cover. Use Batch03 IL-Yat BARE52 source-verified builder and verification approach where applicable; **do not copy IL-Yat's percentages**.

No original ICOS runs, AmeriFlux cases, forcing NetCDF, site surfaces, CTSM/FATES shared code, jobs or existing restarts have been changed by this six-site work.

## Separate CA-TP4 job status note (2026-10-25)

Corrected CA-TP4 **V3 PTS** case has successfully submitted `case.run` Slurm job **4732088** and dependent `case.st_archive` **4732089**, using verified `PTS_LAT=42.7102`, `PTS_LON=279.6426`, `case.submit --skip-preview-namelist`. **Do not mark as model success or start AD395 until `sacct`, `CaseStatus`, model `lnd.log`/NUOPC and the 2007 restart are verified.** Original failed job 4728206 remains unchanged.
