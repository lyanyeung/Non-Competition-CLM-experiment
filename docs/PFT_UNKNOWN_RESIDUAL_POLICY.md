# Policy: unobserved PFT remainder must NOT default to grass (GRA)

**Status:** mandatory Batch01/Batch02 evidence gate; 24 October 2026.  
**Scope:** FATES `use_fates_nocomp=.true.` plus `use_fates_fixed_biogeog=.true.`; applies to the 20 new evidence towers, not retroactively to active NL-Loo/DE-Tha simulations.

## Scientific answer

**NO: unclassified species percentage is not a measured grassland area fraction.** In FATES nocomp with prescribed biogeography, the input PFT distribution determines how much model area is allocated to each PFT. Treating unclassified **forest stand composition / biomass / basal area** as grass artificially allocates patches to GRA and changes water, light, biomass and soil responses. `PCT_NAT_PFT` is a *conditional natural-vegetation fractional composition*, not raw tree stem counts or tree basal area.

Distinguish:
1. `TREE_SPECIES_REMAINDER` — unidentified fraction of a **tree** inventory/stand. Can be broadleaf/needleleaf/other woody species, but is **not GRA without ground vegetation survey**.
2. `BASAL_AREA_REMAINDER` — unidentified tree basal area. Never convert to horizontal grass cover.
3. `BIOMASS_REMAINDER` — tree carbon / biomass not attributed to known tree species. Never convert to horizontal grass cover.
4. `GROUND_COVER_REMAINDER` — unclassified surveyed ground fraction. Could be grass, litter, bare soil, bryophytes, shrubs, rock, open water, etc. GRA only where quadrat/transect or mapped vegetation **identifies actual grass-covered area** and its denominator.
5. `NO_REMAINDER_BUT_UNKNOWN_LANDUNIT` — 100% of identified **trees** belong to one class. This is **not** evidence the whole CLM gridcell/EC footprint is 100% natural tree patches; examine crop, bare, roads, grassland and other landunits separately.

### Batch01 table — NEVER auto-fill with GRA

| Site | Known numerical evidence | Remaining uncertainty | GRA default? |
| --- | --- | --- | --- |
| CZ-BK1 | Picea 99% + Abies 1% (investigated stand) | Tree-level known; ground-area, nonforest landunit unknown | **No** |
| IT-Ren | 85% spruce + 12% Pinus cembra + 3% larch | Tree-level known; natural-landunit area unknown | **No** |
| RU-Fyo | Spruce 85% + birch 15% | Stand metric and spatial scope unresolved | **No** |
| CH-Dav | Spruce >99.5% | Remaining <0.5% tree inventory; landunit area unknown | **No** |
| IT-Col | Fagus 100% (stand species) | Ground area not necessarily 100% DBF patches | **No** |
| FR-Fon | Oak 79% + hornbeam 18% by basal area | Other <3% of tree basal area, not grass | **No** |
| FI-Sod | Pinus 95% | Other 5% of stand species unspecified | **No** |
| FR-Pue | Quercus ilex 95% (stand composition) | Other 5% and alternative canopy-cover denominators | **No** |
| DE-Hai | Fagus 64% + Fraxinus 28% + Acer 7% | ~1% *tree carbon* not assigned | **No** |
| BE-Vie | Fagus 43% + Pseudotsuga 37% | **20%** remaining unidentified forest stand composition | **No** |

## How to make a scientific model-input decision

- **First**: identify the observation **denominator**, survey area, year, data uncertainty, known species and reported unknown share. Avoid mixing different studies with different sampling metrics.
- **Then**: find independent canopy/understory ground-cover or vegetation inventory. If it reports grass ground-area %, and the pinned FATES parameter-file `fates_hlm_pft_map` supports the appropriate cool/arctic C3 or C4 grass representation, assign that **measured** part to grass; account for possible canopy-understory overlap and zero double counting.
- **If there is no source data**: mark `UNRESOLVED` and keep the site on **HOLD** for a scientifically justified assumption or sensitivity study. Do not declare that an unknown remainder is GRA merely to make fractions sum to 100.
- **For conditional tree percentages**, one can *consider* an explicitly labelled **forest-only conditional PFT scenario** after confirming that the unknown species have the same broad PFT or evaluating meaningful alternatives. Example: a stand known entirely to consist of two ENF species can conditionally be ENF100 **within the sampled trees**, while NATVEG100 needs its *own land-area evidence*. Do not automatically renormalize missing tree species to 100.
- **For ground cover**, do not confuse observed 10% open ground with all grass, all natural vegetation, or all nonforest crop. It may be bare soil or natural shrub/grass; require a separate landunit decision.

The model PFT allocation must satisfy the actual surface format's conditional percent sums, but that mathematical constraint does not license fabricated ecological classes. Preserve alternatives as named **proxy/scenario** surface versions, rather than silently modifying observed data.

## Sources and standard inputs

- [FATES technical documentation — no competition with prescribed biogeography](https://fates-users-guide.readthedocs.io/projects/tech-doc/en/stable/fates_tech_note.html)
- [FATES host-model PFT mapping, including grasses](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html)
- [CTSM surface dataset percent reference](https://escomp.github.io/CTSM/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html)
- [Project 38-site numeric evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv)
- [Batch01 ten-site register](../data/batch01_10_sites.csv)

**No automatic GRA fill. No PFT surface writes or Slurm jobs are authorized by this policy.**
