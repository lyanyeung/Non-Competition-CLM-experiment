# Groundwater-influence screening of the 86 sites (4 November 2026)

**Question.** US-CMW was excluded because its vegetation lives on groundwater that a single-point CLM
column cannot supply (tower ET 662 mm/yr against 263 mm/yr precipitation; docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md
section 11). Are there other sites in the five AmeriFlux batches and four ICOS batches where groundwater,
a shallow or perched water table, a river or a wetland strongly controls the water the vegetation gets?

**Answer so far.** No other site meets the US-CMW exclusion criterion with the data checked. Five sites are
flagged **HIGH** (documented groundwater use or a water table in the root zone), nine **MEDIUM** (poorly
drained, perched or mixed wet footprint), seven **PERMAFROST** (water perched on permafrost: a different
problem), six **LOW-WATCH** (setting suggests it, no evidence found). Nothing is excluded or deleted by this
screen. The tower water balance (ET/P) is only available for 25 sites in this repository; the rest needs
the new script below to run on IRIDIS.

## How the sites were screened

1. **Site literature and metadata** (ICOS/DEIMS station pages, AmeriFlux/FLUXNET site pages and the
   site-characterisation papers): river valley or floodplain position, drainage class, gley/stagnic or peat
   soils, reported water-table depth, measured groundwater uptake.
2. **Tower water balance, the US-CMW test.** Mean annual ET/P from the tower (LE → ET, P_F), full years
   only. ET/P well above 1 in most years means an extra water source. Caveats: in drylands ET ≈ P is normal;
   in cold sites snow undercatch inflates ET/P; ET/P < 1 does **not** rule out groundwater use (US-Ton).
   - Values below come from the monthly EC tables already in this repository
     (`figures/AD400_NORMAL400_site_anomaly_diagnostics/*/<SITE>/<SITE>_EC_monthly.csv`, 25 sites).
   - For all 86 sites run
     [`examples/Cross_cohort_NORMAL400/scripts/30_groundwater_screen_tower_ET_P.py`](../examples/Cross_cohort_NORMAL400/scripts/30_groundwater_screen_tower_ET_P.py)
     on IRIDIS (read only; flags `GW_SUBSIDY` at ET/P ≥ 1.2, `CHECK` at 1.0–1.2).
3. **Model check (to do after Normal400).** For HIGH and MEDIUM sites compare model `ZWT`, summer `BTRAN` and
   ET with the tower (script 14 already writes them). The US-CMW signature was model ET ≈ P, water table
   deep (8.6 m) and BTRAN 0.08–0.20 while the tower ET was 2.5 × P.

## Classes

| Class | Meaning | Action |
|---|---|---|
| EXCLUDED | Tower ET ≫ P every year, phreatophytes (US-CMW) | not used to judge GPP |
| HIGH | Groundwater use measured, or water table in/near the root zone (peat, drained wetland, perched table) | keep, flag `GW_INFLUENCED`; read GPP bias together with the model water table; run the model check |
| MEDIUM | Poorly drained or seasonally waterlogged soils, or a wet patch in the footprint | keep; model check if GPP bias appears in dry spells |
| PERMAFROST | Water perched on permafrost or in peat plateaus; no lateral groundwater | judge with the arctic sites after the phenology reruns |
| LOW-WATCH | Valley floor, wetland landscape or ET/P ≈ 1, but no evidence of groundwater use found | no action; re-check if script 30 flags it |
| LOW | Upland, dryland or mountain setting, nothing found in the site descriptions used for the set-up (not researched further) | none |

## Flagged sites

| Site | Batch | Class | Evidence | Tower ET/P |
|---|---|---|---|---|
| US-CMW | AmeriFlux B02 | **EXCLUDED** | Riparian mesquite on the Upper San Pedro River; groundwater use measured by EC (Scott et al. 2008) | 2.52 |
| US-Ton | AmeriFlux B04 | **HIGH** | Blue oaks are obligate phreatophytes: groundwater at ~8 m supplied about 80 % of June–August ET in 2005–2008 ([Miller et al. 2010, WRR](https://doi.org/10.1029/2009wr008902)). Closest analogue to US-CMW, but annual ET stays below P | 0.67 |
| US-NC2 | AmeriFlux B03 | **HIGH** | Drained loblolly plantation on the lower coastal plain with a high groundwater table; ET exceeded P in the 2007–08 drought and accessible groundwater stabilised ET ([Sun et al., AGU 2017](https://ui.adsabs.harvard.edu/abs/2017AGUFMGC53F..04S); [Liu et al. 2018, AFM](https://doi.org/10.1016/j.agrformet.2018.06.025)) | – |
| BE-Bra | ICOS B02 | **HIGH** | Somewhat poorly drained sandy Arenosol on Campine clay; perched water table at 0.8–2.5 m ([DEIMS/LTER site record](https://deims.org/api/sites/68e6a8e5-d6d2-4c8c-91c4-10e7f87ac556)) | – |
| RU-Fyo | ICOS B01 | **HIGH** | Paludified shallow-peat spruce forest on peaty podzolic gley soil ([Forests 2023](https://www.mdpi.com/1999-4907/14/10/1968)); the wet Fyodorovskoye stand has a 60 cm peat layer and a water table seasonally near or above the surface ([Kurbatova et al. 2008](https://bg.copernicus.org/articles/5/969/2008/)) | – |
| FI-Let | ICOS B03 | **HIGH** | Nutrient-rich fen peatland drained for forestry in 1969, partly harvested 2016; ([ICOS station record](https://meta.icos-cp.eu/objects/XCbOcz7bn_Fs-SsN1vyner9J/ICOSETC_FI-Let_FLUXNET_HH_L2.zip.json)); soil carbon balance depends on how shallow the groundwater level is kept ([EGU 2018 modelling abstract](https://meetingorganizer.copernicus.org/EGU2018/EGU2018-12489.pdf)) | – |
| US-Ho1, US-Ho2, US-Ho3 | AmeriFlux B02 | MEDIUM | Howland: glacial-till soils whose drainage ranges from very poorly to well drained over short distances ([Howland Forest](https://en.wikipedia.org/wiki/Howland_Forest)) | – |
| CA-Man | AmeriFlux B01 | MEDIUM | Old black spruce with larch in poorly drained areas; stunted spruce and shrubs in poorly drained bogs between the upland stands ([AmeriFlux CA-Man](https://ameriflux.lbl.gov/sites/siteinfo/CA-Man); [AMS abstract](https://ams.confex.com/ams/AFAPURBBIO/webprogram/Paper80627.html)) | – |
| US-SP1 | AmeriFlux B04 | MEDIUM | Naturally regenerated longleaf/slash pine **flatwoods** ([Powell et al. 2008, GCB](https://doi.org/10.1111/j.1365-2486.2008.01675.x)); flatwoods soils carry a seasonally high water table (not measured at the tower in the sources found) | – |
| FR-Fon | ICOS B01 | MEDIUM | Oak on a gleyic Luvisol ([ICOS station](https://meta.icos-cp.eu/resources/stations/ES_FR-Fon)); in the 2018 drought layers below 150 cm gave up to 60 % of transpiration and the soil water capacity is about twice the database value ([Maysonnave et al. 2022](https://agris.fao.org/search/fr/records/6798c8a6d6a63682f0458c59)): deep water, a rooting-depth issue as much as a groundwater one | – |
| CH-Fru | ICOS B02 | MEDIUM | Gleysol; a raised bog borders the experimental area ([ETH record](https://www.research-collection.ethz.ch/handle/20.500.11850/269620)) | 0.40 |
| DE-RuR | ICOS B04 | MEDIUM | Stagnic Cambisols and Stagnosols (perched water) on shales in a 40 ha headwater catchment ([TERENO Rollesbroich](https://b2find.eudat.eu/dataset/3b0554f5-e7e5-5636-9e88-a65d7f120eb0)) | – |
| GF-Guy | ICOS B03 | MEDIUM | Hills 10–40 m high; a seasonally flooded forest plot lies inside the tower footprint next to the terra-firme plot ([Stahl et al. 2011](https://doi.org/10.1007/s13595-011-0074-2)) | – |
| US-BZS | AmeriFlux B02 | PERMAFROST | Black spruce on a permafrost peat plateau in the Tanana lowlands, next to the BZF fen ([AmeriFlux US-BZS](https://ameriflux.lbl.gov/sites/siteinfo/US-BZS)); the only ET/P > 1.1 outside US-CMW, likely snow undercatch plus thaw water | 1.11 |
| US-Uaf, US-Rpf, US-EML, US-ICh, US-ICt, GL-ZaH | AmeriFlux B02/B04, ICOS B04 | PERMAFROST | Black spruce or tundra on permafrost; US-Uaf is next to Smith Lake | US-Rpf 0.79, US-ICh 0.64, US-ICt 0.44, US-EML 0.12 (tower P 2258 mm/yr is implausible: check P) |
| CH-Cha | ICOS B03 | LOW-WATCH | Lowland in the broad Reuss river valley, Cambisol ([ETH record](https://www.research-collection.ethz.ch/handle/20.500.11850/269619)) | 0.53 |
| AT-Neu | ICOS B03 | LOW-WATCH | Hay meadow on the Stubai valley floor at 970 m ([LTER Stubai](https://forschungsinfrastruktur.bmfwf.gv.at/de/mapping/?id=4220)) | – |
| FI-Sod | ICOS B01 | LOW-WATCH | Pine on sandy podzol ([FMI](https://en.ilmatieteenlaitos.fi/ghg-sodankyla-forest)); the surrounding landscape mixes forest, wetland, lakes and rivers ([Sodankylä supersite](https://saon.met.no/metsis/metadata/no-met-adc-41209000-c21d-5d64-bcab-fd99615d3e54)) | – |
| US-Syv | AmeriFlux B04 | LOW-WATCH | Old-growth upland forest in a wilderness of lakes, bogs and wetlands ([Sylvania](https://www.oldgrowthforest.net/mi-sylvania-wilderness)) | – |
| BR-Ma2 | AmeriFlux B01 | LOW-WATCH | Tower on a medium-elevation plateau ([K34 record](https://www.osti.gov/biblio/2574357)); valley and slope positions are studied nearby ([NGEE-Tropics](https://ngt-data.lbl.gov/dois/NGT0205)) | – |
| US-Kon | AmeriFlux B03 | LOW-WATCH | Upland tallgrass prairie with ET/P near 1 | 0.98 |

## All sites

| Batch | Sites (class) |
|---|---|
| AmeriFlux B01 | BR-Ma2 (LOW-WATCH), CA-Ca3 (LOW), CA-LP1 (LOW), CA-TP4 (LOW: well-drained sand), CA-Cbo (LOW), **CA-Man (MEDIUM)**, CA-TP1 (LOW), CA-TP3 (LOW), US-Aud (LOW), US-Bar (LOW) |
| AmeriFlux B02 | US-BZS (PERMAFROST), **US-CMW (EXCLUDED)**, US-EML (PERMAFROST), US-GLE (LOW), US-Ha1 (LOW, ET/P 0.36), **US-Ho1, US-Ho2, US-Ho3 (MEDIUM)**, US-ICh, US-ICt (PERMAFROST) |
| AmeriFlux B03 | US-Kon (LOW-WATCH), US-MMS (LOW), US-MOz (LOW), US-Me2 (LOW), US-Me6 (LOW), US-Mpj (LOW, 1.01), US-MtB (LOW), **US-NC2 (HIGH)**, US-NR1 (LOW), US-NR3 (LOW) |
| AmeriFlux B04 | US-Rpf (PERMAFROST), **US-SP1 (MEDIUM)**, US-SRG (LOW, 1.03), US-SRM (LOW, 0.94), US-Seg (LOW, 0.99), US-Ses (LOW, 0.99), US-Slt (LOW, 0.63), US-Syv (LOW-WATCH), **US-Ton (HIGH)**, US-Uaf (PERMAFROST) |
| AmeriFlux B05 | US-UiD (LOW), US-UMB (LOW), US-UMd (LOW), US-Var (LOW, 0.52), US-Vcm (LOW, 1.02), US-Vcp (LOW), US-WCr (LOW), US-Whs (LOW), US-Wjs (LOW, 1.07), US-Wkg (LOW, 0.92) |
| ICOS B01 | BE-Vie, CH-Dav, CZ-BK1, DE-Hai (LOW), FI-Sod (LOW-WATCH), **FR-Fon (MEDIUM)**, FR-Pue (LOW, 0.48), IT-Col, IT-Ren (LOW), **RU-Fyo (HIGH)** |
| ICOS B02 | **BE-Bra (HIGH)**, **CH-Fru (MEDIUM)**, CH-Lae (LOW), DK-Sor (LOW, 0.54), ES-LJu (LOW, 0.44), FI-Hyy, FR-FBn, FR-Hes (LOW), IT-MBo (LOW, 0.45), IT-Noe (LOW, 0.67 from 2 years) |
| ICOS B03 | AT-Neu, CH-Cha (LOW-WATCH), CZ-Stn, DE-Hzd, DE-Lnf, DE-Obe (LOW), **FI-Let (HIGH)**, **GF-Guy (MEDIUM)**, IL-Yat, IT-Lav (LOW) |
| ICOS B04 | CH-Aws (LOW), DE-Gri (LOW), **DE-RuR (MEDIUM)**, ES-Agu (LOW), GL-ZaH (PERMAFROST), IT-Tor (LOW) |

The dryland ET/P values of 0.94–1.07 (US-Wjs, US-SRG, US-Vcm, US-Mpj, US-Seg, US-Ses, US-SRM, US-Wkg) are
what a water-limited site without groundwater looks like; US-CMW is 2.5.

## What this means for the GPP comparison

- Several HIGH/MEDIUM sites are also needleleaf sites (US-NC2, RU-Fyo, BE-Bra, FI-Let, US-Ho1–3, CA-Man,
  US-SP1). Their default-parameter GPP ratios were far below 1 (screening of 1 Nov: US-NC2 0.01, RU-Fyo 0.09,
  US-Ho1 0.10, BE-Bra 0.18, FI-Let 0.21, US-SP1 0.22), which the carbon-starvation diagnosis explains. If a
  bias remains after needleleaf variant F, check hydrology at these sites before blaming the vegetation
  parameters: a free-draining CLM column can be too dry (US-Ton, US-NC2 in drought) or cannot hold a
  near-surface water table in peat (RU-Fyo, FI-Let).
- US-Ton is the one site where the published water balance shows a large groundwater share of summer ET.
  Expect model summer GPP of the oaks to be too low for that reason; do not tune vegetation parameters to it.
- None of these sites is excluded on this evidence. Exclusion needs the US-CMW signature: tower ET/P well
  above 1 every year **and** a model that is water-limited where the tower is not.

Land-use history is screened separately in [LAND_USE_CHANGE_SCREENING.md](LAND_USE_CHANGE_SCREENING.md);
US-NC2 and BE-Bra are flagged in both.

## Next steps

1. On IRIDIS: `python3 -B examples/Cross_cohort_NORMAL400/scripts/30_groundwater_screen_tower_ET_P.py`
   (writes `~/groundwater_screen_tower_ET_P.csv`), then add the ET/P column for the 61 sites marked "–".
2. After Normal400: model `ZWT`, summer `BTRAN` and ET versus tower ET at the HIGH and MEDIUM sites.
3. Re-check US-EML tower precipitation (2258 mm/yr).

## Sources

- Miller, Chen, Rubin, Ma, Baldocchi (2010) Groundwater uptake by woody vegetation in a semiarid oak savanna, *WRR* 46, doi:10.1029/2009WR008902
- Sun et al. (2017) Water and energy balances of loblolly pine plantation forests during a full stand rotation, AGU Fall Meeting GC53F-04
- Liu et al. (2018) Drought and thinning have limited impacts on evapotranspiration in a managed pine plantation, *AFM*, doi:10.1016/j.agrformet.2018.06.025
- DEIMS/LTER-Europe record for Brasschaat (De Inslag), hydrology and soil fields
- Kurbatova, Li, Varlagin, Xiao, Vygodskaya (2008) *Biogeosciences* 5:969; Forests 14(10):1968 (2023) Ru-Fyo footprint study
- He et al. (EGU 2018) drained peatland forests Lettosuo; ICOS Carbon Portal station records for FI-Let, FR-Fon, BE-Bra, DE-RuR, GF-Guy; ETH Research Collection records for CH-Cha and CH-Fru
- Maysonnave et al. (2022) Contribution of deep soil layers to the transpiration of a temperate deciduous forest
- Stahl et al. (2011) *Annals of Forest Science*, Paracou terra-firme and seasonally flooded plots in the Guyaflux footprint
- AmeriFlux site pages: CA-Man, US-BZS, US-BZF, US-SP1, US-Ton, US-Uaf; Powell et al. (2008) *GCB* 14:2523
