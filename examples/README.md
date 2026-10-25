# Site examples and batch cohorts — Fixed Biogeography & no competition FATES experiment

**Standard new-site protocol:** [AD400 → NORMAL400](../docs/AD400_NORMAL400_PROTOCOL.md), total **800 model years per site**, with a strict first-five-year + 395-year continuation gate for each mode. No PRE50 is planned for new batches. Every station requires a separate versioned source audit and a scientifically accepted fixed-PFT mapping, not just a land-cover label.

| Example/cohort | Evidence or science | Operational status |
| --- | --- | --- |
| [DE-Tha](DE-Tha/README.md) | Tower stand species mapped ENF87/DNF10/DBF3; literature soil 17/71/12 proxy | Direct AD5 1996–2001 verified and independent AD5→Normal5 verified; remaining AD395 submitted, completion unverified |
| NL-Loo (scripts 09–15) | 500-m-radius surveyed species/ground area; open-ground allocation unresolved | Existing legacy PRE50/AD200 workflow protected; **not standardized or altered** |
| **[Batch 01 — 10 sites](Batch01_10/README.md)** | CZ-BK1, IT-Ren, RU-Fyo, CH-Dav, IT-Col, FR-Fon, FI-Sod, FR-Pue, DE-Hai, BE-Vie | Ten surfaces and guarded AD workflow implemented; operator reports previous run finished on 25 October. Final remote AD/Normal checkpoint status not reverified in this update. |
| **[Batch 02 — 10 sites](Batch02_10/README.md)** | DK-Sor, FR-Hes, FR-FBn, BE-Bra, IT-Noe, CH-Fru, CH-Lae, ES-LJu, FI-Hyy, IT-MBo | **Runnable input audit available**; AD400 → Normal400 planned. PFT/soil/mapping decisions remain before site surface or submission-code adaptation. |

**Core science gate:** The [38-site PFT evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv) contains 22 *numeric-evidence candidates*, **not** 22 measured EC-ground-area PFT maps. Published species, basal-area or biomass composition may be used to *inform* a defensible site proxy, but must not silently become `PCT_NAT_PFT`.

Keep original and model-specific site files separate. Require read-only source audit, original and output SHA256, exact FATES functional map, documented landunit fractions, vetted DATM years, and the [site measured-soil-first policy](../docs/observed_soil_texture_policy.md). Preserve original case status. Existing DE-Tha/NL-Loo scripts hard-code site-specific paths and **must not be executed for Batch01 without adaptation and scientific approval**.

- [Master 22-site cohort assignment](../data/22_site_cohort.csv)
- [Batch01 numerical evidence register](../data/batch01_10_sites.csv)
- [Batch02 updated evidence register](../data/batch02_10_sites.csv)
- [Batch02 current PFT/soil input gates](../data/batch02_10_input_gates.csv)

