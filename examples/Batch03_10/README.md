# Batch03_10 — third ICOS/European cohort, fixed biogeography + no competition (AD400 → Normal400)

**Created 25 October 2026.** Ten further stations chosen from the [38-site ICOS/FLUXNET inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv), after Batch01 (10), Batch02 (10) and the protected NL-Loo/DE-Tha examples (2). It runs **the same CLM-FATES operation as [Batch01_10](../Batch01_10/README.md)**: Stage11 versioned FIXNC surfaces → Stage12 private CTSM namelist-overlay recovery of FATES AD cases → Stage11 guarded AD5 smoke → Stage13 guarded AD395 continuation. Normal400 follows as a separate hybrid case (DE-Tha Stage14 method), not automated here.

**Status:** code, site register, PFT proxies and soil decisions are in this repository; the mocked end-to-end surface build and all three self-tests pass off-cluster. **Nothing has been run on IRIDIS6 yet** — no surfaces, cases or Slurm jobs exist for Batch03.

## How the ten were chosen

The 22 numeric-evidence sites are already used. Of the remaining 16 (all formerly “qualitative” in the v1 inventory), the [reviewed v2 inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_observed_PFT_percent_evidence_v2_20261024.csv) and [16-site leads](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/16_site_further_research_leads.csv) were ranked by:

1. **Functional-type determinacy** — numeric tree composition, or a stand whose every named species maps to a single FATES PFT (so a species percentage is not needed to set the PFT);
2. **Compatibility with the Batch01 surface method** (100% NATVEG point, prescribed PFTs);
3. **An existing built template case** with a working DATM stream and executable on IRIDIS6.

| Excluded | Reason |
| --- | --- |
| CH-Aws | Three failed first segments and a negative-RH `HumanIndexMod` crash history in its template case |
| GL-ZaH | Cassiope dwarf-shrub heath: HLM 11 splits 0.1/0.1/0.8 across three FATES shrubs; plot cover is not footprint |
| ES-Agu | 65% total cover with unquantified bare/biocrust remainder; no landunit decision possible |
| IT-Tor, DE-Gri, DE-RuR | Grasslands with species lists only; DE-Gri also has 74 unresolved MDS forcing blocks. Reserve for a later grassland cohort |

## Selected sites, PFT proxies and soil

| # | Site | Template case (clone `--keepexe`) | PFT proxy (HLM index) | Evidence basis | Soil texture input |
| ---: | --- | --- | --- | --- | --- |
| 1 | IT-Lav | `IT-Lav_FATES_SPINUP500` | ENF 85 (1) / DBF 15 (7) | Abies 70 + Picea 15 / Fagus 15, Cescatti & Marcolla 2004 | Grid fallback |
| 2 | FI-Let | `FI-Let_FATES_SPINUP1000_S30SHARED` | ENF 80 / DBF 20 | Pre-harvest basal area pine 60 + spruce 20 / birch 20 | Grid fallback; **drained peat** |
| 3 | IL-Yat | `IL-Yat_FATES_SPINUP500` | ENF 100 | Aleppo pine >90% of trees (conditional tree proxy) | **31 / 41 / 28** (Qubaja 2020) |
| 4 | DE-Obe | `DE-Obe_FATES_SPINUP1000_S30SHARED` | ENF 100 | Norway-spruce-dominated stand | Grid fallback |
| 5 | CZ-Stn | `CZ-Stn_FATES_SPINUP500_11P` | DBF 100 | Beech monoculture | Grid fallback |
| 6 | DE-Lnf | `DE-Lnf_FATES_SPINUP1000_S30SHARED` | DBF 100 | Pure ~130-yr beech; occasional oak/maple (all DBF) | Grid fallback |
| 7 | DE-Hzd | `DE-Hzd_FATES_SPINUP500` | DBF 100 | Oak planted on 2007 windthrow | Grid fallback |
| 8 | GF-Guy | `GF-Guy_FATES_SPINUP1000_S30SHARED` | Tropical EBF 100 (4) | Undisturbed evergreen rainforest | Grid fallback |
| 9 | AT-Neu | `AT-Neu_FATES_SPINUP500_11P` | Cool C3 grass 100 (13) | Graminoids 35 / forbs 42 / other 23% of phytomass | Grid fallback |
| 10 | CH-Cha | `CH-Cha_FATES_SPINUP500_11P` | Cool C3 grass 100 (13) | Managed ryegrass/clover sward | Grid fallback |

Binding inputs: [site register](../../data/batch03_10_sites.csv), [PFT scenarios](../../data/batch03_10_pft_scenarios.csv), [soil decisions with sources tried](../../data/batch03_10_soil_input_decisions.csv). Expected FATES mapping (verified for the same JSON in Batch02): HLM 1→`needleleaf_evergreen_extratrop_tree`, 4→`broadleaf_evergreen_tropical_tree`, 7→`broadleaf_colddecid_extratrop_tree`, 13→`cool_c3_grass`. Stage11 aborts if the pinned parameter file maps any used class differently.

**Proxy labels, not measured ground area.** As in Batch01, all points are `PCT_NATVEG=100`, `PCT_CROP=0`, other landunits 0. Specific caveats the operator should accept or revise **before** running `surfaces`:

- **IL-Yat** is a sparse plantation (~50% crown cover, ~⅓ limestone outcrop, >45% stones). ENF 100 on a fully vegetated point overstates canopy; a bare-soil (HLM 0) sensitivity would need a builder change.
- **FI-Let** was selection-harvested in March 2016, inside its 2010–2025 forcing; post-harvest ENF 53 / DBF 47 is the recorded alternative. Its peat physics are unverified, like RU-Fyo.
- **DE-Hzd** is a young post-windthrow oak stand; an 800-year fixed-DBF spin-up is a mature-stand proxy.
- **GF-Guy** collapses a hyper-diverse forest (and 13% seasonally flooded footprint) into one tropical evergreen PFT.
- **AT-Neu, CH-Cha**: FATES has no forb/legume PFT, so the whole herbaceous sward is cool C3 grass **by explicit modelling assumption**. This is the only place the [residual-PFT policy](../../docs/PFT_UNKNOWN_RESIDUAL_POLICY.md) is touched: no unknown *tree* remainder is assigned to grass.

**Soil.** Following the [generic soil policy](../../docs/observed_soil_texture_policy.md) (point 3; the Batch01-only override does not apply), only IL-Yat has a published site sand/silt/clay, replicated across the 10 texture layers as a labelled proxy. The other nine keep the template surface's `PCT_SAND`/`PCT_CLAY` unchanged, marked `SOIL_TEXTURE_GRID_FALLBACK`; Stage11 verifies they are byte-identical to the source. The soil CSV lists every source tried. Flechard et al. (2020), used for Batch01, covers none of these ten sites. If site data turn up (e.g. ICOS ETC soil texture for GF-Guy/FI-Let/DE-Hzd, Swiss FluxNet for CH-Cha), change the CSV row to `SITE_LITERATURE_UNIFORM_10_LAYER_PROXY` with values and source **before** `surfaces`.

## What differs from the Batch01 scripts

| Item | Batch01 | Batch03 |
| --- | --- | --- |
| Source surface | Hard-coded `surfdata_<site>_hist_2000_16pfts_c<date>.nc` | Read from the template case's `CaseDocs/lnd_in` `fsurdat`; must be `surfdata_<site>_*.nc` and not already a FIXNC file |
| PFT classes | ENF, DNF, EBF, DBF | + tropical EBF (HLM 4), cool C3 grass (HLM 13) |
| Soil | Per-site constants in code | From the soil decision CSV; grid fallback checked unchanged |
| AD5 job IDs for Stage13 | Hard-coded dictionary | Parsed from `case.submit` output and stored in each ledger |
| Template start date | Not checked in Stage11 | `RUN_STARTDATE` must be `YYYY-01-01` before any case is created |
| Overlay | `.../Batch01_10/_private_ctsm_...` | Its own `.../Batch03_10/_private_ctsm_...` (Batch01 untouched) |

Unchanged: the two-line pinned `CLMBuildNamelist.pm` patch (blob `698f2396…`), `--bgc fates --no-megan --no-drydep --no-fire_emis`, `STOP_N=REST_N=5`, `RESUBMIT=0` then `78`, `--skip-preview-namelist`, attempt-before-submit ledgers, and the restored `env_case.xml` lock.

## Run on IRIDIS6

Each step is run **once**. Do not rerun a stateful step after it has been attempted; read the ledgers instead.

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
git pull --ff-only origin main || exit 1
D=examples/Batch03_10/scripts
S11=$D/11_batch03_AD400_oneclick.py
S12=$D/12_batch03_recover_FATES_AD_private_overlay.py
S13=$D/13_batch03_continue_verified_AD395.py

# 0. Read-only checks
python3 -B "$S11" self-test || exit 1
python3 -B "$S12" self-test || exit 1
python3 -B "$S13" self-test || exit 1
python3 -B "$S11" plan 2>&1 | tee ~/Batch03_plan.log
#    Check: 10x template=OK, schema=OK, and the printed fsurdat paths.
#    Any HOLD (e.g. a template already pointing at another FIXNC surface) must be resolved first.

# 1. Ten versioned surfaces + SHA256 receipts (no cases, no jobs)
python3 -B "$S11" surfaces 2>&1 | tee ~/Batch03_surfaces.log
#    Required: SURFACES SUMMARY success= 10 issues= 0

# 2. Private-overlay FATES AD case recovery (clones, preview_namelists; NO Slurm)
python3 -B "$S12" recover --confirm RECOVER_BATCH03_TEN_FATES_AD_CASES_NO_SLURM \
  2>&1 | tee ~/Batch03_recover.log
#    Required: BATCH03 PRIVATE FATES AD RECOVERY 10 / 10 successful

# 3. Exactly one 5-year AD smoke per site
python3 -B "$S11" submit-smoke --confirm SUBMIT_BATCH03_TEN_FIRST_FIVE_YEAR_AD_SMOKES \
  2>&1 | tee ~/Batch03_submit_AD5.log
python3 -B "$S11" status      # read only; shows ledger phase and AD5 job IDs

# 4. After all 10 run + st_archive jobs are COMPLETED 0:0:
python3 -B "$S13" audit || exit 1   # READ ONLY: sacct, 3 restarts, spinup_state=2
python3 -B "$S13" continue-395 --confirm CONTINUE_BATCH03_TEN_VERIFIED_AD5_BY_395_YEARS
```

New paths: cases `/iridisfs/scratch/ly3n24/CLM_FATES/cases/<site>_B03_FIXNC_AD400`; surfaces, ledgers and overlay under `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch03_10/`; run/archive under `/scratch/ly3n24/CTSM_FATES_OUTPUTS/`. Template cases, original surfaces, forcing, shared CTSM and executables are only read.

**Template cases may still be running** their own 1000-year continuations. Cloning with `--keepexe` only reads them, but check scratch inode/storage quota before step 2: ten new cases add ten run and archive trees.

## After AD400

Normal400 is a **separate** hybrid case per site from the verified Y+400 AD restart triplet, using the [DE-Tha independent AD→Normal method](../DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) and [protocol](../../docs/AD400_NORMAL400_PROTOCOL.md): Normal5 smoke (`CLM_ACCELERATED_SPINUP=off`, restart `spinup_state=0`), then guarded Normal395. Never carry the explicit AD `spinup_state=2` from `user_nl_clm` into the Normal case. 800 model years is the design, not proof of equilibrium.

## Verification done off-cluster (25 October 2026)

- `self-test` for Stage11/12/13: PASS (CSV consistency, template names, namelist helpers, job-ID parser, overlay path).
- Mock end-to-end `plan` + `surfaces` with fake template cases, a 14-PFT JSON map and NetCDF3 point surfaces: 10/10 built; PFT indices, landunits, IL-Yat texture and unchanged grid-fallback texture validated; second run verified without overwrite; FIXNC-template guard triggers. (Real NetCDF4 I/O and CIME/Slurm behaviour are untested until run on IRIDIS6.)
