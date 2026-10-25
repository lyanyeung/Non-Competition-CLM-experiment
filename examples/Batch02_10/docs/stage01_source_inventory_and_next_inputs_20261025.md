# Batch02 Stage01 operator result and next input decisions — 25 October 2026

## Reported execution

The operator ran the corrected launcher and reported all three dependency SHA256 checks `OK`, self-test success, and an inventory with **10/10 site directories present and 10/10 sites having at least one source case and an active surface reference**. The terminal table is not a certificate that the NetCDF arrays, FATES parameter mappings, forcing clocks or soil choices passed scientific checks. The detailed JSON has not yet been supplied to this repository.

Report location on IRIDIS:

`/iridisfs/home/ly3n24/Batch02_10_preflight_20261025T070625_933191Z/all_sites.json`

No new surface, CIME case, model job or shared CTSM modification was made. `SCIENTIFIC=HOLD` is a fixed unresolved-input label in Stage01, not an exception or a newly detected model failure. Do not rerun Stage01 just to change that label.

## Explicit configuration references to inspect next

| Site | Reference case | Reported start | Reported fixed CO₂ ppm | AD400 endpoint if start retained | Normal400 endpoint |
| --- | --- | --- | ---: | ---: | ---: |
| DK-Sor | DK-Sor_FATES_SPINUP500 | 1996-01-01 | 361.93 | 2396 | 2796 |
| FR-Hes | FR-Hes_FATES_SPINUP500 | 1997-01-01 | 363.04 | 2397 | 2797 |
| FR-FBn | FR-FBn_FATES_SPINUP500 | 2008-01-01 | 385.02 | 2408 | 2808 |
| BE-Bra | BE-Bra_FATES_SPINUP500_11P | 1996-01-01 | 361.93 | 2396 | 2796 |
| IT-Noe | IT-Noe_ERA5_ABW_BRANCH2009 | 2004-01-01 | 376.95 | 2404 | 2804 |
| CH-Fru | CH-Fru_FATES_SPINUP500_11P | 2005-01-01 | 378.98 | 2405 | 2805 |
| CH-Lae | CH-Lae_FATES_SPINUP500_11P | 2004-01-01 | 376.95 | 2404 | 2804 |
| ES-LJu | ES-LJu_FATES_SPINUP1000_S30SHARED | 2004-01-01 | 376.95 | 2404 | 2804 |
| FI-Hyy | FI-Hyy_FATES_SPINUP1000_S30SHARED | 1997-01-01 | 363.04 | 2397 | 2797 |
| IT-MBo | IT-MBo_FATES_SPINUP1000_S30SHARED | 2003-01-01 | 375.14 | 2403 | 2803 |

These are explicit **candidate configuration references**, not final approved inputs or restart donors. Endpoints are arithmetic Y+400 and Y+800 derived from the operator's XML snapshot, not completed or submitted simulations. Notably, `BRANCH2009` is part of IT-Noe's case name, whereas the reported `RUN_STARTDATE` remains **2004**; the name alone must not change new cold-start dates or forcing alignment. Verify its actual repaired streams and the ES-LJu corrected forcing stream before cloning. DK-Sor historical/diagnostic CO₂ cases and the old 367-ppm `1PT` cases at ES-LJu/FI-Hyy are not the selected defaults for the new constant-CO₂ spin-up.

## Next executable step

[`02_summarize_selected_inputs_readonly.py`](../scripts/02_summarize_selected_inputs_readonly.py) reads the existing Stage01 JSON and prints the exact ten selected references, full recorded small soil/PFT arrays, CO₂/start metadata and recorded DATM stream references. It reads only the SHA256-matched active FATES parameter files to decode PFT names and display the stored HLM-map dimensions/matrix; it does not rescan forcing or open all surfaces again. Shared parameter files are decoded once per path/hash. Missing keys, missing/changed parameters, unreadable arrays or absent streams produce explicit technical-detail issues and a nonzero exit status.

All array positions are reported as stored. The script does not silently infer a host bare-soil offset, transpose a matrix or assign a shrub/grass to a tree PFT. Source-grid soil and PFT arrays remain model provenance, not observed tower fractions. It writes nothing; the example shell command uses `tee` only for its console log.

## PFT evidence checked in this update

- **DK-Sor:** the [ICOS station description](https://meta.icos-cp.eu/resources/stations/ES_DK-Sor) confirms a beech-dominated surrounding forest with scattered spruce stands and individual larch. It does not provide a numeric spruce/larch split. The old combined ENF+DNF20 remains unresolved.
- **FR-Hes:** [Bitton et al. 2026, section 2.1](https://bg.copernicus.org/articles/23/6491/2026/) directly describes the 2005 beech90 stand and, separately, the 2020 basal area shares beech75/oak≈10/hornbeam≈10. These named species are all DBF; the remaining≈5 is not identified quantitatively there. **DBF100 could be an explicit idealized stand proxy**, following Batch01's model-scenario approach, but is not a newly verified 100% measured footprint composition. The paper also gives clay ranges by depth, which alone cannot supply a full sand/silt/clay profile.
- **FR-FBn:** [Gavinet et al. 2025, study-site methods](https://academic.oup.com/aob/article/135/7/1361/8063930) reports pine as almost75% of basal area and less than one-third of stems, with holm oak and evergreen shrubs in lower strata. This confirms why basal area and stem fractions cannot be interchanged. The [site-based medfate example by CREAF/INRA authors](https://emf-creaf.github.io/medfate/articles/workedexamples/FontBlanche.html) supplies a three-species demonstration inventory including Phillyrea. Its simplified plot-specific inputs are a lead, not a complete tower PFT-area map.
- **BE-Bra:** [ICOS station metadata](https://meta.icos-cp.eu/resources/stations/ES_BE-Bra) distinguishes the local 2-ha Scots-pine stand from a surrounding 150-ha mixed forest with several broadleaf species. A local ENF stand proxy and a broader forest mixture would be different experiments. The metadata do not numerically resolve the old55/23/22 stand record.
- **CH-Lae:** [Scapucci et al. 2024, section 2.1](https://bg.copernicus.org/articles/21/3571/2024/) confirms beech40/ash19/maple13/linden8 (**DBF80**) and fir8/spruce4 (**ENF12**), on a species-cover denominator. The remaining8 is not specified in that passage. No closure was inferred.
- **FI-Hyy:** a [SMEAR II thinning-methods record](https://zenodo.org/records/8283057) is a local-inventory lead. Its detailed PDF was not successfully retrieved in this check; it is **not** used to validate60/25/15 or any replacement numerical mixture.

The existing IT-Noe, CH-Fru, ES-LJu and IT-MBo evidence holds remain unchanged in this update. No new complete ten-site field PFT table is claimed. Measured evidence, candidate modelling proxies and verified operational readiness remain separate.

AD400 → independent Normal400 remains the requested design. Building new surfaces and the submission implementation follows actual input/mapping decisions; the inventory itself neither selects new PFT fractions nor submits the experiment.
