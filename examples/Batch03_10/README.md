# Batch03_10 — third ICOS/European cohort, fixed biogeography + no competition (AD400 → Normal400)

**Created 25 October 2026.** Ten further stations chosen from the [38-site ICOS/FLUXNET inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv), after Batch01 (10), Batch02 (10) and the protected NL-Loo/DE-Tha examples (2). It runs **the same CLM-FATES operation as [Batch01_10](../Batch01_10/README.md)**: Stage11 versioned FIXNC surfaces → Stage12 private CTSM namelist-overlay recovery of FATES AD cases → Stage11 guarded AD5 smoke → Stage13 guarded AD395 continuation. Normal400 follows as a separate hybrid case (DE-Tha Stage14 method), not automated here.

**Status (25 October 2026, IRIDIS6):** all 10 surfaces built (`SURFACES SUMMARY success= 10 issues= 0`), all 10 cases recovered to `PREPARED_NOT_SUBMITTED` with generated `spinup_state=2`, fixed-biogeography and no-competition namelists, and the ten AD5 smokes submitted.

**⚠️ AD5 runs not successful (25 October 2026, diagnosis pending).** All ten first AD5 run jobs (4728068–4728086, even IDs) left the queue while their `st_archive` jobs (4728069–4728087) show `DependencyNeverSatisfied`; the retired IL-Yat ENF100 run 4728072 is `FAILED 1:0`, and the IL-Yat BARE52 replacement (run 4728152, archive 4728153) failed the same way. The same day, all four Batch02 AD5 runs failed ~10 s after start with an ESMF mesh SIGSEGV in `get_centerCoords_from_ESMFMesh_file()` (`ESMCI_ESMFMesh_Util.C:1028`) — see [Batch02 Stage06/07](../Batch02_10/docs/stage07_ESMF_mesh_SIGSEGV_targeted_inspection_20261025.md). Batch03 logs confirm the same failure: all 11 `cesm.log` files end in `signal 11` after 8–12 s on red6083. The backtrace runs `DustEmisLeung2023` → `PrigentRoughnessStreamType.F90:105` → `shr_strdata_init_from_inline` → ESMF mesh read of the global 0.25° dust mesh `dust_0.25x0.25_ESMFmesh_cdf5_c240222.nc` (~1.04 M elements).

**Cause (strongly indicated, not proven):** stack size. ESMF's `get_centerCoords_from_ESMFMesh_file()` builds a variable-length array of `num_elems × 2` doubles (~16.6 MB) on the stack, and Slurm here has `PropagateResourceLimits = ALL`, so a job inherits the submitting shell's stack limit. The failing case, its template `IT-Lav_FATES_SPINUP500` and the successful `FI-Sod_B01_FIXNC_AD400` have identical dust settings (`Leung_2023`, `use_prigent_roughness = .true.`, same mesh) and the same executable, and both of the latter read the Prigent stream without error. A shell on login6001 propagates a 300000 KB stack to compute nodes; the common default of 8192 KB is too small. Batch03 was submitted from login6003.

**Fix in the scripts:** every submission (`submit-smoke`, `resubmit-failed-smoke`, Stage13 `continue-395`) now refuses unless the shell's stack soft limit is ≥ 65536 KB, and records the limit in the ledger. `resubmit-failed-smoke` resubmits only cases whose recorded AD5 run is sacct `FAILED` with no restart or pointer written: it cancels the stuck archive, keeps the failed attempt in `failed_AD5_attempts`, and submits the same 5-year smoke once.

**IL-Yat revision (same day):** the first IL-Yat case used ENF 100 from species composition only, ignoring Yatir's ~48% crown cover and ~37% rock outcrop. Its AD5 is cancelled and retired; IL-Yat now runs as **`IL-Yat_B03_FIXNC_BARE52_AD400` with HLM bare ground 52% / ENF 48%**. Evidence and reasoning: [IL-Yat bare-ground literature review](docs/IL_Yat_bare_ground_PFT_literature_20261025.md). The other nine sites are unchanged.

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
| 3 | IL-Yat | `IL-Yat_FATES_SPINUP500` | **Bare 52 (0) / ENF 48 (1)**; case `IL-Yat_B03_FIXNC_BARE52_AD400` | Measured mean crown cover 48% (72 plots); Aleppo pine >90% of trees; 36.8% rock outcrop | **31 / 41 / 28** (Qubaja 2020) |
| 4 | DE-Obe | `DE-Obe_FATES_SPINUP1000_S30SHARED` | ENF 100 | Norway-spruce-dominated stand | Grid fallback |
| 5 | CZ-Stn | `CZ-Stn_FATES_SPINUP500_11P` | DBF 100 | Beech monoculture | Grid fallback |
| 6 | DE-Lnf | `DE-Lnf_FATES_SPINUP1000_S30SHARED` | DBF 100 | Pure ~130-yr beech; occasional oak/maple (all DBF) | Grid fallback |
| 7 | DE-Hzd | `DE-Hzd_FATES_SPINUP500` | DBF 100 | Oak planted on 2007 windthrow | Grid fallback |
| 8 | GF-Guy | `GF-Guy_FATES_SPINUP1000_S30SHARED` | Tropical EBF 100 (4) | Undisturbed evergreen rainforest | Grid fallback |
| 9 | AT-Neu | `AT-Neu_FATES_SPINUP500_11P` | Cool C3 grass 100 (13) | Graminoids 35 / forbs 42 / other 23% of phytomass | Grid fallback |
| 10 | CH-Cha | `CH-Cha_FATES_SPINUP500_11P` | Cool C3 grass 100 (13) | Managed ryegrass/clover sward | Grid fallback |

Binding inputs: [site register](../../data/batch03_10_sites.csv), [PFT scenarios](../../data/batch03_10_pft_scenarios.csv), [soil decisions with sources tried](../../data/batch03_10_soil_input_decisions.csv). Expected FATES mapping (verified for the same JSON in Batch02): HLM 1→`needleleaf_evergreen_extratrop_tree`, 4→`broadleaf_evergreen_tropical_tree`, 7→`broadleaf_colddecid_extratrop_tree`, 13→`cool_c3_grass`. Stage11 aborts if the pinned parameter file maps any used class differently.

**Proxy labels, not measured ground area.** As in Batch01, all points are `PCT_NATVEG=100`, `PCT_CROP=0`, other landunits 0. Specific caveats the operator should accept or revise **before** running `surfaces`:

- **IL-Yat** is a sparse plantation: 48% measured crown cover (range 0.40–0.70), 36.8% rock outcrop. It now uses HLM bare ground 52% / ENF 48%; this requires FATES nocomp bare-ground support, which Stage11 checks in the pinned source before building. The superseded ENF 100 case is retired, not continued.
- **FI-Let** was selection-harvested in March 2016, inside its 2010–2025 forcing; post-harvest ENF 53 / DBF 47 is the recorded alternative. Its peat physics are unverified, like RU-Fyo.
- **DE-Hzd** is a young post-windthrow oak stand; an 800-year fixed-DBF spin-up is a mature-stand proxy.
- **GF-Guy** collapses a hyper-diverse forest (and 13% seasonally flooded footprint) into one tropical evergreen PFT.
- **AT-Neu, CH-Cha**: FATES has no forb/legume PFT, so the whole herbaceous sward is cool C3 grass **by explicit modelling assumption**. This is the only place the [residual-PFT policy](../../docs/PFT_UNKNOWN_RESIDUAL_POLICY.md) is touched: no unknown *tree* remainder is assigned to grass.

**Soil.** Following the [generic soil policy](../../docs/observed_soil_texture_policy.md) (point 3; the Batch01-only override does not apply), only IL-Yat has a published site sand/silt/clay, replicated across the 10 texture layers as a labelled proxy. The other nine keep the template surface's `PCT_SAND`/`PCT_CLAY` unchanged, marked `SOIL_TEXTURE_GRID_FALLBACK`; Stage11 verifies they are byte-identical to the source. The soil CSV lists every source tried. Flechard et al. (2020), used for Batch01, covers none of these ten sites. If site data turn up (e.g. ICOS ETC soil texture for GF-Guy/FI-Let/DE-Hzd, Swiss FluxNet for CH-Cha), change the CSV row to `SITE_LITERATURE_UNIFORM_10_LAYER_PROXY` with values and source **before** `surfaces`.

## What differs from the Batch01 scripts

| Item | Batch01 | Batch03 |
| --- | --- | --- |
| Source surface | Hard-coded `surfdata_<site>_hist_2000_16pfts_c<date>.nc` | Read from the template case's `CaseDocs/lnd_in` `fsurdat`; must be `surfdata_<site>_*.nc` and not already a FIXNC file |
| PFT classes | ENF, DNF, EBF, DBF | + bare ground (HLM 0, gated on FATES nocomp bare-ground support), tropical EBF (HLM 4), cool C3 grass (HLM 13) |
| Site subsets | All ten at once | `--sites` on surfaces/submit-smoke/status (Stage11), `recover-sites` (Stage12) and audit/continue (Stage13) |
| Replacement cases | — | `VARIANTS` gives a site a named case (IL-Yat → `BARE52`); `retire-legacy` cancels the superseded case's jobs and marks its ledger |
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
#    (after the IL-Yat revision, run the nine and IL-Yat as separate --sites groups)
python3 -B "$S13" audit --sites IT-Lav FI-Let DE-Obe CZ-Stn DE-Lnf DE-Hzd GF-Guy AT-Neu CH-Cha || exit 1
python3 -B "$S13" continue-395 --sites IT-Lav FI-Let DE-Obe CZ-Stn DE-Lnf DE-Hzd GF-Guy AT-Neu CH-Cha \
  --confirm CONTINUE_BATCH03_TEN_VERIFIED_AD5_BY_395_YEARS
```

New paths: cases `/iridisfs/scratch/ly3n24/CLM_FATES/cases/<site>_B03_FIXNC_AD400`; surfaces, ledgers and overlay under `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch03_10/`; run/archive under `/scratch/ly3n24/CTSM_FATES_OUTPUTS/`. Template cases, original surfaces, forcing, shared CTSM and executables are only read.

**Template cases may still be running** their own 1000-year continuations. Cloning with `--keepexe` only reads them, but check scratch inode/storage quota before step 2: ten new cases add ten run and archive trees.

## IL-Yat replacement: cancel ENF100, build BARE52 (run once each)

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment || exit 1
D=examples/Batch03_10/scripts
python3 -B $D/11_batch03_AD400_oneclick.py self-test
# R1. cancel + retire the ENF100 AD5 (only run./st_archive.IL-Yat_B03_FIXNC_AD400)
python3 -B $D/11_batch03_AD400_oneclick.py retire-legacy --sites IL-Yat \
  --confirm RETIRE_BATCH03_LEGACY_VARIANT_CASES 2>&1 | tee ~/Batch03_IL-Yat_retire.log
# R2. read-only: FATES bare-ground support must show SUPPORTED
python3 -B $D/11_batch03_AD400_oneclick.py plan 2>&1 | grep IL-Yat
# R3. bare 52 / ENF 48 surface
python3 -B $D/11_batch03_AD400_oneclick.py surfaces --sites IL-Yat 2>&1 | tee ~/Batch03_IL-Yat_surface.log
# R4. one new case, reusing the verified Batch03 overlay (no Slurm)
python3 -B $D/12_batch03_recover_FATES_AD_private_overlay.py recover-sites --sites IL-Yat \
  --confirm RECOVER_BATCH03_SITES_REUSE_OVERLAY_NO_SLURM 2>&1 | tee ~/Batch03_IL-Yat_recover.log
# R5. its AD5 smoke
python3 -B $D/11_batch03_AD400_oneclick.py submit-smoke --sites IL-Yat \
  --confirm SUBMIT_BATCH03_TEN_FIRST_FIVE_YEAR_AD_SMOKES 2>&1 | tee ~/Batch03_IL-Yat_AD5.log
```

AD395 then runs per group: the nine original sites with `13_... audit/continue-395 --sites IT-Lav FI-Let DE-Obe CZ-Stn DE-Lnf DE-Hzd GF-Guy AT-Neu CH-Cha`, and IL-Yat later with `--sites IL-Yat`.

## After AD400 — NORMAL400 (Stage14)

[`14_batch03_AD400_to_NORMAL400.py`](scripts/14_batch03_AD400_to_NORMAL400.py) follows the proven [DE-Tha AD→Normal hybrid branch](../DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) for each site with AD start year Y:

| Step | Action | Gate / result |
| --- | --- | --- |
| Verify AD400 | `audit-ad400` (read only) | 80 run + 80 st_archive jobs `COMPLETED 0:0` since the recorded AD5 job; last CaseStatus events success; `RESUBMIT=0`; latest archived restart = Y+400 with clm2/datm/cpl; land `spinup_state=2`; nothing queued |
| Stage Normal | `stage-normal` (no Slurm) | New case `<site>_B03_FIXNC[_BARE52]_NORMAL400`, cloned from the AD case with `--keepexe`; `RUN_TYPE=hybrid`, `RUN_REFCASE`=AD case, start = refdate = Y+400; `CLM_ACCELERATED_SPINUP=off`; three AD restarts copied (SHA-checked) with rpointers; `finidat` = copied land restart; explicit `spinup_state` removed; namelists generated by the **unpatched shared CTSM** (no overlay) |
| Normal5 | `submit-normal5` | One 5-year run, `RESUBMIT=0` |
| Verify Normal5 | `audit-normal5` (read only) | Run/archive `COMPLETED 0:0`; restart Y+405; land `spinup_state=0` |
| Normal395 | `continue-normal395` | `CONTINUE_RUN=TRUE`, `RESUBMIT=78` (79 × 5 years), submitted once |
| Verify Normal400 | `audit-normal400` (read only) | 80 + 80 successes; restart Y+800; `spinup_state=0` |

All submissions require the stack guard. Each action accepts `--sites`, so a site whose AD400 is held can be left out without blocking the others. The AD400 cases are only read. Mock tests (fake CIME/Slurm/NetCDF) cover the full chain and every HOLD path.

### Notes carried over

Normal400 is a **separate** hybrid case per site from the verified Y+400 AD restart triplet, using the [DE-Tha independent AD→Normal method](../DE-Tha/scripts/14_AD_to_Normal_independent_branch.py) and [protocol](../../docs/AD400_NORMAL400_PROTOCOL.md): Normal5 smoke (`CLM_ACCELERATED_SPINUP=off`, restart `spinup_state=0`), then guarded Normal395. Never carry the explicit AD `spinup_state=2` from `user_nl_clm` into the Normal case. 800 model years is the design, not proof of equilibrium.

## Verification done off-cluster (25 October 2026)

- `self-test` for Stage11/12/13: PASS (CSV consistency, template names, namelist helpers, job-ID parser, overlay path).
- IL-Yat revision: mock tests confirm the bare 52 / ENF 48 surface (index 0 = 52), the FATES bare-ground gate refusing a source without support, unchanged verification of the other nine, and `retire-legacy` cancelling only the two legacy IL-Yat jobs (idempotent on rerun).
- Mock end-to-end `plan` + `surfaces` with fake template cases, a 14-PFT JSON map and NetCDF3 point surfaces: 10/10 built; PFT indices, landunits, IL-Yat texture and unchanged grid-fallback texture validated; second run verified without overwrite; FIXNC-template guard triggers. (Real NetCDF4 I/O and CIME/Slurm behaviour are untested until run on IRIDIS6.)
