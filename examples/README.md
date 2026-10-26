# Site examples and batch cohorts — Fixed Biogeography & no competition FATES experiment

**Standard new-site protocol:** [AD400 → NORMAL400](../docs/AD400_NORMAL400_PROTOCOL.md), total **800 model years per site**, with a strict first-five-year + 395-year continuation gate for each mode. No PRE50 is planned for new batches. Every station requires a separate versioned source audit and a scientifically accepted fixed-PFT mapping, not just a land-cover label.

| Example/cohort | Evidence or science | Operational status |
| --- | --- | --- |
| [DE-Tha](DE-Tha/README.md) | Tower stand species mapped ENF87/DNF10/DBF3; literature soil 17/71/12 proxy | Direct AD5 1996–2001 verified and independent AD5→Normal5 verified; remaining AD395 submitted, completion unverified |
| NL-Loo (scripts 09–15) | 500-m-radius surveyed species/ground area; open-ground allocation unresolved | Existing legacy PRE50/AD200 workflow protected; **not standardized or altered** |
| **[Batch 01 — 10 sites](Batch01_10/README.md)** | CZ-BK1, IT-Ren, RU-Fyo, CH-Dav, IT-Col, FR-Fon, FI-Sod, FR-Pue, DE-Hai, BE-Vie | Ten surfaces and guarded AD workflow implemented; operator reports previous run finished on 25 October. Final remote AD/Normal checkpoint status not reverified in this update. |
| **[Batch 02 — 10 sites](Batch02_10/README.md)** | DK-Sor, FR-Hes, FR-FBn, BE-Bra, IT-Noe, CH-Fru, CH-Lae, ES-LJu, FI-Hyy, IT-MBo | Operator verified shared14-PFT JSON map. **Four independent surface-candidate builder available**, with new FI-Hyy ICOS-target-stand BA evidence; six site choices remain open. No Batch02 AD/Normal submission yet. |
| **[Batch 03 — 10 sites](Batch03_10/README.md)** | IT-Lav, FI-Let, IL-Yat, DE-Obe, CZ-Stn, DE-Lnf, DE-Hzd, GF-Guy, AT-Neu, CH-Cha | AD400 verified complete 10/10 and Normal5 verified 10/10; Normal395 submitted 10/10 (26 October 2026). IL-Yat runs as bare 52 / ENF 48 (48% measured crown cover). |

**[Six ICOS stations outside the existing 30-site FIXNC cohorts](ICOS_Unassigned_6/README.md)** — CH-Aws, DE-Gri, DE-RuR, IT-Tor (four qualitative C3 grass proxies), ES-Agu (bare49/C3 grass29/evergreen shrub22, source-denominator HOLD), GL-ZaH (bare43/Arctic evergreen shrub53/deciduous Arctic shrub3/Arctic grass1; site-only private FATES parameter map mandatory). Source-pinned six-site PFT audit and GL-only parameter candidate: [script](ICOS_Unassigned_6/scripts/01_pft_six_and_GL_arctic_map.py). **No new six-site CIME cases or jobs started.** Distinct from six unresolved AmeriFlux Batch01 stations.

**[AmeriFlux Batch01 — first four UTC FIXNC AD5 candidates](AmeriFlux_Batch01_10/README.md)** — corrected four station-specific `PTS_LAT/LON` from surface; CA-TP4 V3 AD5 model job **4732088** and dependent archive **4732089** successfully *submitted*, actual success not yet established. Other three corrected CIME cases were preview-verified and not submitted.

**[AmeriFlux Batch02 — second US 10-site FIXNC cohort](AmeriFlux_Batch02_10/README.md)** — US-BZS, US-CMW, US-EML, US-GLE, US-Ha1, US-Ho1, US-Ho2, US-Ho3, US-ICh, US-ICt. **NEW (26 Oct 2026):** source-joined recommended PFT and Sand/Clay 0–30cm for all 10 from *CLM-FATES-single-site-workflows* 50-site PFT/soil evidence; original AmeriFlux Batch02 215 annual forcing NC technically generated. US-GLE separate 2005–2020 **historical meteorology** job **4739020** and dependent archive **4739021** were submitted and shown **PD** (NOT yet completed and NOT a FIXNC spin-up). Nine other cases lack complete case/Slurm and sensor/soil science checks; no AmeriFlux Batch02 FIXNC jobs submitted from this repository. Includes read-only [case/source status audit](AmeriFlux_Batch02_10/scripts/01_batch02_10_crossrepo_INPUTS_AND_CASE_STATUS_readonly.py). **Do not confuse with ICOS `Batch02_10`.**

**Core science gate:** The [38-site PFT evidence inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_PFT_evidence.csv) contains 22 *numeric-evidence candidates*, **not** 22 measured EC-ground-area PFT maps. Published species, basal-area or biomass composition may be used to *inform* a defensible site proxy, but must not silently become `PCT_NAT_PFT`.

Keep original and model-specific site files separate. Require read-only source audit, original and output SHA256, exact FATES functional map, documented landunit fractions, vetted DATM years, and the [site measured-soil-first policy](../docs/observed_soil_texture_policy.md). Preserve original case status. Existing DE-Tha/NL-Loo scripts hard-code site-specific paths and **must not be executed for Batch01 without adaptation and scientific approval**.

- [Master 22-site cohort assignment](../data/22_site_cohort.csv)
- [Batch01 numerical evidence register](../data/batch01_10_sites.csv)
- [Batch02 updated evidence register](../data/batch02_10_sites.csv)
- [Batch02 current PFT/soil input gates](../data/batch02_10_input_gates.csv)
- [Batch03 site register](../data/batch03_10_sites.csv), [PFT scenarios](../data/batch03_10_pft_scenarios.csv) and [soil decisions](../data/batch03_10_soil_input_decisions.csv)

