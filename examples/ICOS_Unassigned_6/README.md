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
