# IL-Yat (Yatir) — bare ground and PFT allocation, literature review

**Date:** 25 October 2026. **Decision:** replace the first Batch03 IL-Yat case (`ENF 100`, full canopy) with `IL-Yat_B03_FIXNC_BARE52_AD400`: **HLM bare ground 52% / ENF 48%** of the model point, `PCT_NATVEG=100`, soil 31/41/28 (unchanged). The ENF100 AD5 is cancelled and its ledger marked `RETIRED_CANCELLED_REPLACED_BY_BARE52`; files are kept for provenance and the case is never continued.

## Why ENF 100 was wrong

ENF 100 came only from tree **species** composition (Aleppo pine >90% of trees). Yatir is a sparse semi-arid plantation: about half the ground is not under tree crowns, and roughly a third of the surface is limestone outcrop. A fully vegetated ENF point would overstate canopy cover, LAI per ground area, GPP, transpiration and carbon pools. The project protocol ([AD400_NORMAL400_PROTOCOL](../../../docs/AD400_NORMAL400_PROTOCOL.md)) already states that stand composition alone cannot justify `NATVEG=100` with no open ground; the [residual-PFT policy](../../../docs/PFT_UNKNOWN_RESIDUAL_POLICY.md) forbids filling unknown ground with grass.

## Evidence

| Quantity | Value | Source |
| --- | --- | --- |
| **Crown (canopy) cover** | Mean **48%** from measured crown widths, 72 field plots; satellite fractional vegetation cover mean 0.48 (SD 0.07), range **0.40–0.70** across the forest | Sprintsin et al., *Relationships between stand density and canopy structure in a dryland forest as estimated by ground-based measurements and multi-spectral spaceborne images* ([record](https://www.researchgate.net/publication/222415057)) |
| Species | Mainly *Pinus halepensis* (>90% of trees); planted 1965–69; 2,800 ha | [Weizmann Yatir site description](https://www.weizmann.ac.il/EPS/Yakir/research-activities/field-research/yatir-forest-location-and-background) |
| Density | ~300 trees/ha after thinning; five 900-m² plots lost ~10 trees each between 2001 and 2016 (drought mortality + thinning) | Weizmann; [Qubaja PhD thesis 2019](https://www.weizmann.ac.il/EPS/Yakir/sites/EPS.Yakir/files/publications/rafat_qubaja_phd_thesis_11_dec_2019.pdf) (Table A2.2b) |
| LAI (per ground area) | ~1.5 (2004, 2016) to ~1.7 ± 0.3 | Weizmann; Qubaja thesis; [arXiv:2511.22720](https://arxiv.org/pdf/2511.22720) |
| **Rock outcrop** | **36.8%** of surface; stoniness 48% to 1.2 m | Qubaja thesis, citing Preisler et al. (2019) |
| Understory | Dwarf shrubs, herbs, annuals, biological crust; minor share of ecosystem biomass; grazing removes ~50% of aboveground understory by end of dry season; **no cover percentages published** | Weizmann; Qubaja thesis |
| Soil | Clay loam 31/41/28 (sand/silt/clay), 0.2–1.0 m over chalk/limestone | Qubaja et al. (2020) as cited in arXiv:2511.22720 |
| Flux footprint | 95% of flux from within the forest boundary; 95% within ~1300 m of tower | arXiv:2511.22720; Qubaja thesis |

## Allocation

| HLM natpft | Share | Reasoning |
| --- | ---: | --- |
| 0 bare ground | **52** | 100 − 48 measured crown cover. Lumps rock outcrop (36.8%), inter-canopy soil, biocrust and sparse grazed understory. No grass-cover measurement exists, so none is assigned to C3 grass. |
| 1 ENF | **48** | Measured crown cover; all trees mapped to `needleleaf_evergreen_extratrop_tree` (>90% Aleppo pine; other planted conifers not quantified). |

**Consistency check:** ground-mean LAI ~1.5 concentrated on 48% crown area gives ~3.1 within crowns, a plausible value for *P. halepensis*.

## Uncertainties and sensitivities

- Crown cover was measured around the mid-2000s. Density fell after the 2008–09 drought while LAI rose ~44% over a decade; no newer crown-cover figure was found. The 0.40–0.70 spatial range is the natural sensitivity envelope (BARE 60/ENF 40 to BARE 30/ENF 70).
- In FATES nocomp/fixed-biogeography mode the ENF patch can still close its canopy *within* the 48%; whether water limitation keeps within-patch LAI realistic must be checked in output.
- **Technical gate:** the pinned FATES/CTSM must pass HLM natpft 0 to FATES as a nocomp bare-ground patch. Stage11 checks the source (`nocomp_bareground` in FATES and `pft_areafrac`/`baregroundfrac` in `clmfates_interfaceMod.F90`) and refuses to build the surface otherwise. After AD5, confirm in history that the bare patch exists and has no vegetation.
- The retired ENF100 case may be reused only as a named full-canopy sensitivity in a separate, explicitly approved run — never continued in place.
