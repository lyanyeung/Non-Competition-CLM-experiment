# IT-Tor sensitivity design — 2026-11-02

Proposal for review. No forcing, surface, model case or job has been modified.

## Evidence

The inherited surface has ORGANIC = 0 at all ten levels; this is an input value, not a measurement of zero soil carbon. Leolini et al. report 64.7 Mg C ha−1 at 20 cm at Torgnon: [paper](https://www.research-collection.ethz.ch/server/api/core/bitstreams/83a9d331-6f2d-47f0-95eb-5b5f0504ebf7/content). This is an integrated stock, not a measured ten-layer profile. Current [CTSM source](https://github.com/ESCOMP/CTSM/blob/master/src/biogeophys/SoilStateInitTimeConstMod.F90) describes organic matter density in kg/m³ used in soil physics. Verify the actual experiment's pinned source and mapping.

The nearby IT-TrF record supports concern about some MDS/ERA switching jumps, but station exposures and canopy differ, the cross-station clock is not fully verified, and the neighbor source has no per-record TA QC. See the [existing source audit](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/main/examples/Batch04_6/docs/stage03n_actual_uploaded_IT_TrF_nested_archive_verified_Nov2025_neighbor_evidence_final_decision_20261102.md).

## Soil candidates

- S0: original zero-ORGANIC surface as a reproducible baseline, not a physical assertion.
- S1: detached site-informed sensitivity calibrated to the reported 0–20 cm stock; all non-ORGANIC variables preserved.

Illustrative conversion: 64.7 Mg C/ha = 6.47 kg C/m². Under a uniform 0–0.20 m profile this averages 32.35 kg C/m³. Assuming 58% carbon in organic matter gives approximately 55.78 kg organic matter/m³. The 58% factor and uniform distribution are assumptions, not site measurements. Setting below 20 cm to zero would be a bounded sensitivity assumption, not an observation. Do not directly put 55.78 into all ten source levels. Current upstream CTSM code derives source-data interfaces from the 10SL_3.5m structure even when another model-layer structure is selected; the exact pinned experiment source must be inspected before calculating its source-level profile. First verify source-layer interfaces, any layer crossing 20 cm, mapping into model layers, and the upper bounds and units. Check the resulting integrated stock under the declared conversion.

## Meteorology candidates

- F0: retain the inherited Stage28 forcing as the reproducible baseline.
- F1: make a detached 2025 sensitivity for the three original source labels 2025-11-13 14:30, 15:00, and 15:30. Replace MDS TA and VPD with packaged ERA values, respectively TA = 7.531, 7.494, 7.084 °C and VPD = 5.995, 5.921, 5.486 hPa; preserve pressure and recompute specific humidity consistently. Verify the target source clock and exact no-leap indices first, and check no other records or variables change. ERA is an alternative, not established local truth.
- F2, optional and not yet specified: separately examine the adjacent 28-half-hour and later 125-half-hour QC1 windows. IT-TrF coverage is complete for the first window and sparse for the second; do not automatically extrapolate F1 or assume ERA is correct.

The three F1 records total 1.5 hours in the forcing cycle. They test one discontinuity and implementation; they do not resolve the 1,458-half-hour episode or necessarily have a large AD400 effect.

## Comparison and gates

A proposed S0F0, S0F1, S1F0, S1F1 design separates soil and forcing effects. Decide how many full AD400 runs are worthwhile after input validation and cost assessment; report each effect against S0F0. Each candidate must have a distinct checksum and case, with originals preserved.

Before writing candidates, verify (1) pinned CTSM version, soil-layer structure, ORGANIC units, layer interfaces, interpolation and valid bounds; (2) the sampling footprint and treatment of rock fragments for the published stock; (3) target-site time convention, three input records, units and no-leap indices; and (4) array-wide differences, pressure preservation and thermodynamic consistency. Validate the separate case and stream bindings before a one-time direct AD400 submission. The first five-year segment, if submitted, is part of the requested AD400, not a separate smoke test.

