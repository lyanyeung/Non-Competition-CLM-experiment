# Batch04 direct AD400 handoff and IT-Tor sensitivity — 2 November 2026

This document records the operator's supplied IRIDIS6 output, not a live cluster query. Licensed half-hourly source data and private diagnostic reports remain on IRIDIS6 and are not included in this repository.

## Observed execution

- DE-Gri: direct AD400 startup from 2004, 80 five-year segments, target 2404. Initial run 4807852 failed during land-history initialization because GPP was unavailable in FATES. Its impossible dependent archive 4807853 was cancelled. The case-specific history list was changed to FATES_GPP and FATES_NPP; the original files were backed up and no DATM stream was changed. Run 4807938 and archive 4807939 subsequently completed successfully; a subsequent segment was reported running. This establishes the first five model years, not completion of AD400.
- DE-RuR: an isolated FIXNC case was prepared with the approved site PFT surface and 15 historical annual DATM files. Direct AD400 starts in 2011 and targets 2411. First run 4808040 and archive 4808041 were reported COMPLETED/0:0; subsequent work was reported running.
- ES-Agu: an isolated FIXNC case was prepared with the approved site bare/grass/shrub proxy and 19 historical annual DATM files. Direct AD400 starts in 2006 and targets 2406. First run 4808042 and archive 4808043 were reported COMPLETED/0:0; subsequent work was reported running.
- The three cases retain scientific limitations: source meteorological provenance and precipitation timing remain uncertain; soil inputs are inherited. These are exploratory simulations, not a scientific release. Source checks, exact parameter/stream provenance and the original private job ledgers remain necessary.
- NL-Loo's V3 PRE50 and AD200 case, run and archive folders were deleted by the operator after a queue and explicit RUN_REFCASE check. Shared build, forcing and other cases were excluded. DE-Tha's AD400 and independent NORMAL400 were retained; their complete runtime status has not been verified here.

## GL-ZaH

An isolated Arctic parameter candidate was created by the operator. Only HLM host PFT rows 9 and 11 were changed to the designated Arctic evergreen and cold-deciduous shrubs; the shared default file was hash-checked unchanged. The reported private candidate SHA256 is 56d9433f5915686b2877367124c39ee1f167d2c5c2cbc88cc5e190f53d31cd62. No GL surface or model case was created by this step. The selected host percentages are a footprint proxy and still need actual case, soil and forcing review.

## IT-Tor sensitivity design

The operator selected constructing and reviewing soil and meteorological sensitivities before any IT-Tor model start. Its existing source surface contains zero ORGANIC at all ten input levels; this is not a measurement of zero soil carbon. The source describes units as kg/m3 and assumes 0.58 gC/g organic matter. A published study reports an IT-Tor 0–20 cm stock of 64.7 Mg C/ha ([paper](https://www.research-collection.ethz.ch/server/api/core/bitstreams/83a9d331-6f2d-47f0-95eb-5b5f0504ebf7/content)). Uniform 0–20 cm and 0.58 carbon fraction would imply approximately 55.78 kg organic matter/m3, but this is an illustrative model assumption, not a measured ten-layer profile. Current upstream CTSM code calculates surface-data interfaces from 10SL_3.5m regardless of the model grid; inspect the actual experiment source and binary provenance before converting values.

Candidate F1 is narrowly scoped to three consecutive 2025-11-13 source labels. It substitutes the packaged ERA TA and VPD at those labels and recomputes QBOT using unchanged pressure, with baseline and all other variables preserved. It does not establish that ERA is the target-site truth, validate the source-to-DATM clock independently, or resolve the full gap-filled period. [The detached F1 script](../scripts/05a_it_tor_make_f1_candidate.py) reads exact source values from the private Stage03J report; no raw source observations are bundled. The earlier 28- and 125-half-hour windows remain separate review questions.

Do not create the soil candidate until the real source soil-layer geometry, interpolation, organic maximum, footprint and sampling assumptions are reviewed. A possible S0/F0, S0/F1, S1/F0, S1/F1 comparison should be costed before committing to four full AD400 chains. None of these IT-Tor cases or NetCDF sensitivity files has been reported created by this document.

## Reproducibility and no-repeat rules

The two site preparation scripts and controller are retained in `scripts/DE-RuR_prepare_ad400.py`, `scripts/ES-Agu_prepare_ad400.py`, and `scripts/run_pair_prepare.py`. They were run by the operator to create the two cases; **do not repeat them** after a case or preparation ledger exists. The tested histories explicitly request FATES_GPP and FATES_NPP. Each script uses the private existing provenance reports and only creates isolated cases; the subsequent two direct AD400 submissions were performed separately with one-time guards.

The earlier `04e` DE-Gri submit helper must not be run against the already submitted case; CaseStatus and the independent submission guard record that an attempt occurred. Do not repeat any submission when status is uncertain. Verify queue, accounting, case status, copied stream/namelist, and three-component restart before concluding a segment or complete chain succeeded.

CH-Aws remains under humidity-source review. The user explicitly chose direct AD400 chains, with the first five years included in the 400-year chain rather than a separate AD5 experiment.

