# Batch02: mapping passed, PFT/soil choices and four candidate surfaces

## Completed technical step

The operator ran the corrected JSON reader and reported `MAPPING_READ PASS ISSUES 0`: ten source cases share one FATES JSON parameter file, SHA256 `0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04`. The [transcribed 14×14 map](../../../data/batch02_verified_HLM_FATES_map_20261025.json) preserves the actual operator result. No additional Stage01/02 rerun is needed for the next surface step.

The file contains 14 FATES types. CLM natural-PFT index0 is bare and has no row in this map; stored row0 corresponds to host natural-PFT1. Relevant mappings from the actual matrix are:

| CLM host natural-PFT index | Host type | FATES zero-based index | FATES type |
| ---: | --- | ---: | --- |
| 1 or 2 | Temperate or boreal evergreen needleleaf tree | 1 | needleleaf_evergreen_extratrop_tree |
| 3 | Boreal deciduous needleleaf tree | 2 | needleleaf_colddecid_extratrop_tree |
| 5 | Temperate evergreen broadleaf tree | 3 | broadleaf_evergreen_extratrop_tree |
| 7 or 8 | Temperate or boreal deciduous broadleaf tree | 5 | broadleaf_colddecid_extratrop_tree |
| 9 | Evergreen broadleaf shrub | 6 | broadleaf_evergreen_extratrop_shrub |
| 10 | Temperate deciduous broadleaf shrub | 8 | broadleaf_colddecid_extratrop_shrub |
| 13 | Non-arctic C3 grass | 12 | cool_c3_grass |

The [FATES host-map documentation](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html) establishes the host-type ordering. Its online example is not substituted for the operator's newer 14-type matrix. Actual host11 splits into FATES columns8/9/10 at0.1/0.1/0.8. FATES column7, `broadleaf_hydrodecid_extratrop_shrub`, has **no nonzero host mapping** in this parameter file. Having a named FATES PFT is therefore not enough to make it reachable from the current surface map. There is also no dedicated evergreen needleleaf shrub or forb PFT. No parameter file is modified by this update.

## FI-Hyy: new direct ICOS-target-stand evidence

The University of Helsinki site wiki links to [Kolari et al., Hyytiälä SMEAR II site characteristics, Zenodo5909681](https://zenodo.org/records/5909681). The original `Hyytiala stand characteristics.xlsx` was downloaded and its MD5 verified as `5fad5b5de566907b8005b956156aa87d`, matching the repository. No source workbook was edited. Relevant basal-area cells are stored numeric values, not uncached formulas.

The `Stand_ICOS` worksheet explicitly identifies 62 ICOS-target-stand line plots for2008–2015, trees with DBH>5cm, and excludes treeless road/stand fractions. In2015, cells **H8/H16/H24** give pine23.10, spruce3.26 and all deciduous hardwood1.45m²/ha. Thus:

`ENF = 100 × (23.10 + 3.26) / 27.81 = 94.7860481841%`

`DBF = 100 × 1.45 / 27.81 = 5.2139518159%`

The [five-survey derivation](../../../data/batch02_FI_Hyy_ICOS_target_stand_BA_derivation.csv) keeps the original values, exact cells, plot definitions and checksums. The2018 CP and SP surveys remain separate and are not pooled with2015. The2015 mixture is a complete functional grouping **on a tree-basal-area denominator**. Its use as a fixed model-ground-PFT mixture is a stated stand proxy, not a claim of measured footprint area or unchanged composition since the forcing start in1997. The old unverified60/25/15 mixture is superseded for this candidate.

## Four explicit surface candidates

The ten-site membership is unchanged. Four sites now have complete **candidate modelling choices** in [this configuration](../../../data/batch02_four_surface_candidates_v1.json):

| Site | Candidate PFT percentages | Sand / silt / clay % | Interpretation |
| --- | --- | --- | --- |
| FI-Hyy | ENF94.7860481841 / DBF5.2139518159 | 57 /38 /5 |2015 ICOS-target-stand basal-area proxy |
| FR-Hes | DBF100 |7 /64 /29 | Idealized deciduous stand; approximately5% unclassified basal area assumed DBF |
| CH-Fru | Cool C3 herbaceous proxy100 |37 /56 /7 | Idealized dense herbaceous point; grass parameterization also represents forbs/legumes |
| IT-MBo | Cool C3 herbaceous proxy100 |14 /76 /10 | Same explicitly simplified functional representation |

All four use **NATVEG100/CROP0/other landunits0** as a dense stand/grassland point experiment, following the modelling approach of Batch01. These are not measured whole-footprint landunits. For the grasslands,100% model C3 grass is not a new measurement of grass-species cover; the original mixed-herbaceous evidence and the lack of a dedicated forb PFT remain explicit limitations. FR-Hes's missing≈5% is an assumption for this candidate, not resolved field evidence.

Soil values for FI-Hyy, FR-Hes and IT-MBo were checked against [Flechard2020 TableS4, PDF page9](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf), including visual table inspection. These are representative station texture aggregates with unspecified sample horizon. CH-Fru uses the site summary37/56/7 in [Riedl et al.2022, section2.1](https://hess.copernicus.org/articles/26/91/2022/); other field surveys differ, so this choice is not asserted to be uniquely correct. Each selected texture is repeated across ten CLM input layers as a **vertical modelling proxy**, not ten observed horizons. Source-grid organics, soil depth, rock and other non-replaced fields remain inherited model inputs, not newly validated site observations.

The [ten-site soil-candidate table](../../../data/batch02_10_soil_candidates_20261025.csv) also records DK-Sor, BE-Bra and CH-Lae station-texture candidates, plus a FR-FBn model-example lead. IT-Noe/ES-LJu have no complete verified texture selected here. A model tutorial value is not labelled a field measurement, and no soil is inferred from a textural class alone.

## Remaining six sites

| Site | Decision still open before a new candidate is chosen |
| --- | --- |
| DK-Sor | Separate the reported ENF+DNF20 or define a documented sensitivity allocation; larch must not be silently mapped to ENF |
| FR-FBn | Allocate non-pine composition across broadleaf trees/shrubs on a chosen consistent denominator |
| BE-Bra | Classify the unresolved22%; do not renormalize the known55+23 |
| CH-Lae | Classify the unresolved8% or select an explicitly labelled residual scenario |
| IT-Noe | Decide how to represent evergreen coniferous Juniperus shrub without a matching needleleaf-shrub PFT, and choose compatible total cover |
| ES-LJu | Reconcile survey-specific ground/vegetation cover and shrub phenology; keep bare rock/soil and remaining vegetation explicit |

No automatic surface candidate is generated for these six. The core protocol remains AD400 → independent Normal400 for each of the ten sites once its inputs are selected. Four candidate files do not establish readiness of the whole ten-site batch.

## Runnable next step: new candidate files only

[`03_build_four_surface_candidates.py`](../scripts/03_build_four_surface_candidates.py) supports `self-test`, `plan`, and `build --sites FI-Hyy FR-Hes CH-Fru IT-MBo`. It needs the candidate JSON in the repository `data` directory. `plan`/`self-test` require only standard Python; `build` uses numpy/netCDF4 already available in `clm_fates_env`.

Each build verifies the pinned original surface and active FATES JSON SHA256, checks the exact host→FATES mapping for used PFTs, writes a temporary copy, verifies landunits/PFTs/soil and **all non-replaced variable values/masks**, and checks that the original is unchanged before an exclusive no-overwrite publication. A JSON sidecar retains the complete candidate assumptions and hashes. A verified existing output is reused; conflicting/partial outputs stop rather than being overwritten.

Default output per site:

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/<site>/surface_candidates/surfdata_<site>_B02_FIXNC_candidate_v1.nc`

The script creates no CIME case, edits no old namelist/forcing/parameter file, and submits no Slurm job. It does not reuse any old competition restart.

**Validation scope:** Python self-test and candidate-plan arithmetic passed locally; the original FI-Hyy workbook checksum/cell extraction and BA fractions were independently checked. Actual candidate NetCDF generation is guarded by runtime verification but has not yet been run on IRIDIS. This local environment lacks netCDF4, so a local end-to-end NetCDF write is not claimed. Technical construction is separate from selecting a scientifically suitable final experiment and testing convergence.
