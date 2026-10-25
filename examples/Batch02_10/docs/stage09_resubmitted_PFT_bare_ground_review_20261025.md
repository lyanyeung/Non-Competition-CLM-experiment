# Stage09 submission receipt and PFT / bare-ground review

Date: 25 October 2026. Scope: the ten Batch02 sites. This records the operator's new Stage09 output and compares the four active candidates with the updated 38-site register. It changes no model input, case, job or scientific allocation.

## Reported Stage09 result

The operator reported `submitted=4 uncertain=[]`, with the current Python submit process on `login6001` having soft and hard stack limits `unlimited`. All four preflights passed. This establishes successful submission; no scheduler RUNNING/COMPLETED state or AD5 checkpoint has yet been supplied for these new IDs.

| Site | New AD5 run | New archive | Existing candidate composition | Bare PFT0 |
| --- | ---: | ---: | --- | ---: |
| FI-Hyy | 4728292 | 4728293 | ENF 94.78604818410643 / DBF 5.213951815893564 | 0 |
| FR-Hes | 4728294 | 4728295 | DBF 100 | 0 |
| CH-Fru | 4728296 | 4728297 | cool C3 herbaceous proxy 100 | 0 |
| IT-MBo | 4728298 | 4728299 | cool C3 herbaceous proxy 100 | 0 |

Each run is still AD5 only, `RESUBMIT=0`. AD395 and Normal400 were not submitted. The previous failed run/archive IDs remain historical provenance. Use Stage09 status for the active IDs; do not repeat its `resubmit` action:

```bash
python3 -B "$HOME/Batch02_10_stage09.py" status
```

## Conclusion for the four active candidates

No discrepancy was found between the existing four-site configuration and the four AD5-candidate rows in the new register. The operator-verified active parameter map sends HLM2 to extratropical ENF, HLM7/HLM8 to extratropical cold-deciduous broadleaf tree, and HLM13 to cool C3 grass. The Stage03 builder verifies these exact rows and writes the full 15-element vector, including zero at HLM0. Thus the current four surfaces explicitly assume zero prescribed bare area; this is not evidence that bare area has been measured as zero.

| Site | What supports the current candidate | What remains an assumption |
| --- | --- | --- |
| FI-Hyy | Complete ENF/DBF grouping of the 2015 ICOS target-stand tree basal areas: pine 23.1, spruce 3.26, hardwood 1.45 m2/ha | Tree basal-area shares are used as model patch-area shares. The source excludes treeless area and does not measure whole-footprint bare cover. |
| FR-Hes | Reported beech/oak/hornbeam are DBF and account for approximately 95% of 2020 tree basal area | Approximately 5% unresolved tree basal area is assigned to DBF; a dense point with bare0 is also a separate assumption. |
| CH-Fru | The site is managed mixed herbaceous vegetation, and the active map provides cool C3 grass | All herbs, including forbs and legumes, use the grass parameterization. The paper says the listed mixture covers up to 90% of the surface; that wording does not establish that the remainder is bare ground or that grass alone covers 90%. |
| IT-MBo | ICOS Italy describes a permanent alpine meadow and reports Festuca25, Nardus13, Trifolium14.5% basal cover | C3 grass represents the whole herbaceous community. The unlisted 47.5% of this species statement is not a measured bare fraction or a measured grass fraction. |

These are usable named model candidates, not a certification of observed footprint composition. The title `FINAL_38_SITE_FIXNC_PFT` does not turn its `PROPOSED`, `OPEN` or `AD5 candidate` rows into measurements. The current four may finish their candidate AD5; before AD395, review the numerical output, checkpoints and acceptance of these area assumptions. If an area allocation changes, use a new versioned surface and a separate cold-start candidate rather than changing active inputs or carrying a checkpoint across a silent composition change.

## The other six sites

No new surface or case has been built for these six by the four-site Stage03–09 workflow.

| Site | Current evidence / updated proposal | Decision status |
| --- | --- | --- |
| ES-LJu | Direct site literature reports non-vegetated soil/gravel/rock49.1%, Festuca18.8%, Hormathophylla6.8%, Genista5.5% of ground. The remaining19.8% is vegetation not allocated by those three species percentages. | Bare area must be represented in an observation-informed candidate. Bare49/grass31/shrub20 is a rounded proxy that allocates unnamed vegetation in proportion to named grass:shrub, not an observed three-class inventory. Evergreen versus deciduous shrub remains a choice. |
| IT-Noe | Reported vegetation cover is spatially42–91%; a separate paper gives45–95%. Juniper53 and lentisk22 are conditional vegetation/species evidence. | Bare34/shrub66 is a rounded midpoint scenario: the exact midpoint of42–91 is vegetation66.5/bare33.5. It is not a footprint mean. Keep the range endpoints as sensitivity options. Juniper is a shrub; assigning it to an ENF tree is inappropriate. Using broadleaf evergreen shrub is a parameterization proxy. |
| DK-Sor | DBF80 / combined ENF+DNF20 | Spruce/larch split remains open; the20% is not bare. |
| FR-FBn | Pine ENF approximately75% of tree basal area | The remaining25% is not established as all EBF or as bare. |
| BE-Bra | ENF55 / DBF23 / unresolved22 of reported stand composition | Do not assign the22% to bare or grass without area evidence. |
| CH-Lae | Listed DBF80 / ENF12 / unreported8 | Do not assume the8% is bare or grass. Cover overlap and survey scope also need to be retained. |

## Surface implementation requirement for future sparse candidates

For the all-natural point convention used here, `PCT_NATVEG=100` can coexist with bare ground: the bare share belongs in `PCT_NAT_PFT` index0, and bare plus all vegetated entries sum to100 within that natural landunit. Do not renormalize the vegetated entries to100 after removing measured bare area. A canopy gap, unlisted species share or missing tree basal area is not automatically bare ground.

The existing Batch02 four-site builder is deliberately restricted to host indices2/7/8/13 and cannot build a bare/shrub candidate unchanged. A separate versioned extension is needed for HLM0/9 and must check the active host/FATES interface and inspect the resulting bare-patch area and absence of vegetation in model output. Batch03's IL-Yat BARE52 branch supplies a method and source check; its52% must not be copied to another site. A model bare patch also does not, by itself, validate the physical treatment of exposed rock.

## Sources checked

Updated evidence repository revision: [`7f7a5328e8f904d745cbd1ddf73f02e21f38442e`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/7f7a5328e8f904d745cbd1ddf73f02e21f38442e/examples/ICOS_sites/ICOS_PFT).

- [38-site scenario register](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/7f7a5328e8f904d745cbd1ddf73f02e21f38442e/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv), blob `63739e00408443bcbb4b286bb3324c76e9fd9100`.
- [Six-site bare-ground review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/7f7a5328e8f904d745cbd1ddf73f02e21f38442e/examples/ICOS_sites/ICOS_PFT/SIX_SITE_BARE_GROUND_PFT_EVIDENCE_20261025.md), blob `7449cba548489faf9ea7401d5f588026c31f354f`.
- [Existing four-site configuration](../../../data/batch02_four_surface_candidates_v1.json), blob `b417fef0e15d399a060a1b4a3167ae8d5a614a7f`; [verified active parameter map](../../../data/batch02_verified_HLM_FATES_map_20261025.json), blob `06df274c832d815f03868f111f870c58d21c0958`.
- ES-LJu: [Serrano-Ortiz et al.2009, section2.1](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2009JG000983) directly confirms ground-cover numbers; [Were et al.2010](https://bg.copernicus.org/articles/7/859/2010/) is also listed in the new review.
- IT-Noe: [Chiesi et al.2012, Study areas](https://iforest.sisef.org/contents/?id=ifor0605-009) directly reports sparse shrub patches and45–95% cover. The new review and an indexed [2022 conference study](https://flore.unifi.it/retrieve/0346b6b0-d5d9-4f24-98bb-e691c4309671/978-3-031-30329-6.pdf) report42–91%; the original book-chapter PDF returned403 in this review.
- CH-Fru: [Gharun et al.2020, site description](https://pmc.ncbi.nlm.nih.gov/articles/PMC7485103/), indexed full-text passage listing grasses, forbs and clover with up to90% surface cover.
- IT-MBo: [ICOS Italy site description](https://www.icos-italy.it/monte-bondone-it-mbo/), the three reported basal-cover numbers.
- [FATES host-model mapping documentation](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html); the pinned local parameter map, rather than an assumed documentation version, controls the Batch02 choices.
- [Batch03 IL-Yat BARE52 source/interface and output verification requirement](../../Batch03_10/docs/IL_Yat_bare_ground_PFT_literature_20261025.md).

Review validation: compared the new register with all four explicit configuration rows, inspected the builder's full PFT vector and host-map checks, and recomputed the ES-LJu remainder and IT-Noe midpoint. No new runtime result or scientific measurement is inferred from successful submission.

