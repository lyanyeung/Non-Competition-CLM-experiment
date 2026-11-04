# Land-use and disturbance screening of the 86 sites (4 November 2026)

**Question.** The experiment spins each site up for 800 years with fixed vegetation (AD400 → Normal400)
and then compares the equilibrium model with the tower. That comparison assumes the tower measures an old,
undisturbed stand of the same vegetation. Which sites break that assumption because the land use or the
stand changed: forest cleared for farming, farmland or heath planted with trees, clear-cut and replanted,
burned, killed by insects, or experimentally disturbed?

**Answer.** No site in the five AmeriFlux and four ICOS batches is a forest converted to cropland. But 20
sites have a land-use change or a stand-replacing disturbance that matters for the comparison:

- **8 have a break inside the flux record**: a fire, insect outbreak, girdling, harvest or grassland renewal.
  The model has no such break, so tower years before and after it are not the same ecosystem.
- **7 are young stands after clear-cut, windthrow, fire or planting.** The tower sees a regrowing stand, far from the
  equilibrium the spin-up produces.
- **5 are planted on former farmland, heath or shrubland** (decades ago). The vegetation is old enough, but
  the soil carbon carries the earlier land use, so NEE and soil respiration cannot match an 800-year spin-up.

Nothing is excluded or deleted by this screen. It decides which years and which fluxes to compare.

## Why it matters for this experiment

| What changed | Effect on the comparison | What to do |
|---|---|---|
| Disturbance during the record | Tower GPP/NEE drops or shifts at a known date; model does not | compare pre- and post-disturbance years separately; do not fit parameters across the break |
| Young stand (decades) | Tower LAI, biomass and GPP below a mature stand; NEE strongly negative (regrowth) or positive (after harvest) | compare GPP seasonality, treat GPP magnitude and NEE as not comparable with the equilibrium model |
| Former farmland, heath or shrubland | Soil carbon below (or above) equilibrium; Rh and NEE biased even if GPP fits | judge GPP; leave NEE/TOTSOMC out of the equilibrium check |

## Flagged sites

| Site | Batch | Type | What happened | Source |
|---|---|---|---|---|
| US-Vcm | AmeriFlux B05 | **DISTURBED IN RECORD** | Stand-replacing Thompson Ridge fire in late May 2013 killed every tree; flux gap until Jan 2014; tower rebuilt in the burned stand | [AmeriFlux US-Vcm](https://ameriflux.lbl.gov/sites/siteinfo/US-Vcm), [FLUXNET news](https://fluxnet.org/2014/04/30/thompson-ridge-wildfire-takes-out-ameriflux-core-site/) |
| US-UMd | AmeriFlux B05 | **DISTURBED IN RECORD** | Spring 2008: every aspen and birch (> 6,700 trees, ~35 % of canopy LAI) girdled over the 39 ha treatment plot (FASET) | [OSTI US-UMd](https://www.osti.gov/dataexplorer/biblio/dataset/1246134) |
| US-GLE | AmeriFlux B02 | **DISTURBED IN RECORD** | Decade-long spruce beetle outbreak, peak 2008, killed 85 % of the forest basal area | [OSTI US-GLE](https://www.osti.gov/dataexplorer/biblio/dataset/1246056) |
| CA-LP1 | AmeriFlux B01 | **DISTURBED IN RECORD** | Mountain-pine-beetle-attacked lodgepole pine stand; attack began in summer 2006, five-year disturbance | [OSTI CA-LP1](https://www.osti.gov/biblio/1660337), [Frontiers 2024](https://www.frontiersin.org/articles/10.3389/ffgc.2024.1352853) |
| US-Slt | AmeriFlux B04 | **DISTURBED IN RECORD** | Gypsy moth defoliation 2006–2008, complete in 2007; fire and windstorms are common in the Pinelands | [OSTI US-Slt](https://www.osti.gov/dataexplorer/biblio/dataset/1246096) |
| FI-Let | ICOS B03 | **DISTURBED IN RECORD** | Fen drained for forestry in 1969 (land-use change), partly harvested in March 2016 | [ICOS FI-Let](https://meta.icos-cp.eu/objects/XCbOcz7bn_Fs-SsN1vyner9J/ICOSETC_FI-Let_FLUXNET_HH_L2.zip.json) |
| US-Ho3 | AmeriFlux B02 | **DISTURBED IN RECORD** | Howland "harvest site": commercial shelterwood harvest next to the research forest; uptake reduced for about 7 years | [AmeriFlux US-Ho3](https://ameriflux.lbl.gov/sites/siteinfo/US-Ho3), [USFS Howland](https://research.fs.usda.gov/nrs/forestsandranges/locations/howland) |
| CH-Cha | ICOS B03 | **DISTURBED IN RECORD** | Intensively managed grassland; grassland restoration (renewal) in 2012 | [CH-Cha flux product](https://holukas.github.io/dataset_ch-cha_flux_product/intro.html) |
| DE-Hzd | ICOS B03 | **YOUNG STAND** | Tower set up on a 40 ha windthrow area left by storm Kyrill (2007); oaks planted afterwards; record from 2010 | [DEIMS DE-Hzd](https://deims.org/api/sites/bf152bfd-f7b4-4a4b-9785-282a8f8ba539), [ICOS station](https://meta.icos-cp.eu/resources/stations/ES_DE-Hzd) |
| CA-TP1 | AmeriFlux B01 | **YOUNG STAND + FORMER FARMLAND** | White pine planted in 2002 on a sandy agricultural field abandoned three years earlier | [AmeriFlux CA-TP1](https://ameriflux-new.hyperarts.com/sites/siteinfo/CA-TP1) |
| CA-Ca3 | AmeriFlux B01 | **YOUNG STAND** | Douglas-fir harvested 1987, broadcast-burned, replanted 1988 (pole-sapling stand) | [OSTI CA-Ca3](https://www.osti.gov/dataexplorer/biblio/dataset/1480302), [Humphreys et al. 2006](https://doi.org/10.1016/j.agrformet.2006.03.018) |
| US-Me6 | AmeriFlux B03 | **YOUNG STAND** | Severe fire 1979, salvage-logged, replanted 1990; ~26-year-old ponderosa pine in 2017, LAI 0.6–0.8 | [OSTI US-Me6](https://www.osti.gov/dataexplorer/biblio/dataset/1246128), [OSU TERRA](https://terraweb.forestry.oregonstate.edu/node/239) |
| US-Rpf | AmeriFlux B04 | **YOUNG STAND** | Burned black spruce forest now dominated by deciduous trees and shrubs (succession from a fire scar) | [OSTI US-Rpf](https://www.osti.gov/dataexplorer/biblio/dataset/1579540) |
| US-NC2 | AmeriFlux B03 | **YOUNG STAND (managed rotation)** | Intensively managed loblolly plantation, 15–28 years old during the record, on drained forested wetland; now in its fifth ~30-year rotation | [Forests 2021](https://www.mdpi.com/1238472) |
| CZ-BK1 | ICOS B01 | **YOUNG STAND (plantation)** | Managed secondary pure Norway spruce stand planted in 1981 with 4-year-old seedlings | [DEIMS CZ-BK1](https://training.deims.org/a61dd7df-5fd7-47b4-8172-b7dfaf969748) |
| IL-Yat | ICOS B03 | **FORMER SHRUBLAND** | Aleppo pine planted from 1964 on former semi-arid shrubland; soil carbon still accumulating | [ICOS IL-Yat](https://meta.icos-cp.eu/resources/stations/ES_IL-Yat), [Weizmann](https://www.weizmann.ac.il/EPS/print/3076) |
| BE-Bra | ICOS B02 | **FORMER HEATH** | Scots pine planted in 1929 on former heathland | [DEIMS/LTER Brasschaat](https://deims.org/api/sites/68e6a8e5-d6d2-4c8c-91c4-10e7f87ac556) |
| CA-TP3, CA-TP4 | AmeriFlux B01 | **FORMER FARMLAND** | White pine plantations established 1974 and 1939 on sandy abandoned land | [OSTI CA-TP3](https://www.osti.gov/dataexplorer/biblio/dataset/1881566), [OSTI CA-TP4](https://www.osti.gov/biblio/1246012) |
| US-UiD | AmeriFlux B05 | **RESTORED GRASSLAND** | Restored native prairie at the University of Illinois energy-farm cluster; prior land use most likely cropland (not confirmed in the sources found) | [AmeriFlux US-UiD](https://ameriflux.lbl.gov/sites/siteinfo/US-UiD) |

To check, not yet confirmed: **US-Vcp** (the 2013 Thompson Ridge fire burned the same preserve; whether
the ponderosa site burned was not found). The other open years were settled on 4 November
(the FLUXNET-product BIF files carry no disturbance records, so from the literature): **US-Ho3** shelterwood
harvest in 2002, EC from 2003 ([Scott et al.](https://core.ac.uk/download/71262083.pdf)); **US-Rpf** fire in late
June 2004, tower from August 2008 ([NIPR ADS record](https://data.arcticobserving.org/metsis/metadata/A20140624-028));
**US-UiD** prairie planted on Energy Farm cropland in 2008, the first EC year, mown every winter from 2009
([AmeriFlux US-UiD](https://ameriflux.lbl.gov/sites/siteinfo/US-UiD)). Register: `data/site_special_events.csv`.

All other sites were not flagged: their site descriptions used for the PFT set-up describe old or
semi-natural stands, permanent grassland, or shrubland without a recorded land-use change. They were not
researched beyond that.

## Overlap with the groundwater screen

US-NC2 and BE-Bra are flagged in both screens (see [GROUNDWATER_SCREENING.md](GROUNDWATER_SCREENING.md)), and
FI-Let is a drained peatland in both. These three need the most care before any of their GPP or NEE bias is
attributed to vegetation parameters.

**DE-Hzd is the reference site used for CZ-Stn and DE-Lnf** in the DBF collapse diagnosis. A young oak
plantation on a windthrow area is a weak reference for mature beech stands; and its EC precipitation was
already flagged as implausible (3169 mm/yr). Consider DE-Hai as the reference instead.

## Next steps

1. For the eight sites disturbed in the record, put the disturbance date into the EC comparison scripts and
   report pre- and post-disturbance statistics separately (or drop the post years).
2. For young stands and former farmland/heath, compare GPP and seasonality only; leave NEE and soil carbon out
   of the equilibrium assessment.
3. Run `examples/Cross_cohort_NORMAL400/scripts/31_site_events_vs_flux_record.py --all-sites` on IRIDIS: it
   lines the events up with each site's EC years and prints the BADM `GRP_DM_*` disturbance entries that settle
   the open years. The register is [`data/site_special_events.csv`](../data/site_special_events.csv).
