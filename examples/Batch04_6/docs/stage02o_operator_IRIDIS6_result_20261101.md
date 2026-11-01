# ICOS Batch04 CH-Aws — actual Stage02O risk triage, 1 November 2026

**Source:** user-supplied, SHA-pinned IRIDIS6 console result from Stage02O. Saved output files below are local to IRIDIS6 and have not been uploaded into this GitHub repository:

- JSON: `/home/ly3n24/ICOS_Batch04_stage02o_hLF8GLFP/results/stage02o_CH_Aws_20_event_risk_triage.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02o_hLF8GLFP/results/stage02o_CH_Aws_20_event_risk_triage.csv`
- Log: `/home/ly3n24/ICOS_Batch04_stage02o_hLF8GLFP/stage02o_console.log`

`SOURCE VERIFIED` and `STAGE02O SELF-TEST PASS`. The script did not write source files, CIME cases or Slurm jobs. Strict 20 original Stage02N source-ledger event identity/time/integrity checks passed.

## Actual observed summary

| Diagnostic | Count |
|---|---:|
| Selected high-QBOT-contrast event anchors | 20 |
| Old processed-VPD-derived RH under 10% | **20/20** |
| Ledger ERA5 minus derived RH absolute difference >= 50 percentage points | **20/20** |
| Ledger ERA5-Land minus derived RH absolute difference >= 50 pp | **20/20** |
| Original ledger neighboring RH jump >= 40 pp | **6/20** |
| Original ledger explicit source seam | **1/20** |
| Events classified REVIEW_FIRST | **20/20** |
| Independently verified original tower sensor RH | **0/20** |
| Any scientific forcing/case selection approved | **No** |

Stage provenance of the 20 selected events: Stage34 7 (2007–2008), Stage38 5 (2017), Stage42 8 (2016, 2018–2020). The respective ledgers have original SHA256 integrity and exact-event row/time verification from Stage02N, **but all original scientific statuses remain EXPLORATORY**.

Key examples (all numbers are *candidate source products or previous derived RH*, not validated sensor-level observations):

| Event | Time | Original processed VPD-implied RH % | Ledger ERA5 RH % | Ledger ERA5-Land RH % | Additional |
|---|---|---:|---:|---:|---|
| E002 | 2007-07-22 07:00 | 0.3196 | 99.3261 | 98.6551 | no seam |
| E001 | 2007-07-22 07:30 | 3.6094 | 99.3266 | 98.3227 | 93.27 pp neighbor jump |
| E009 | 2007-05-17 13:00 | 0.2335 | 88.6453 | 89.8410 | 73.95 pp neighbor jump; **source seam present** |
| E007 | 2008-06-28 06:30 | 0.01285 | 82.4742 | 88.1817 | 72.34 pp neighbor jump |
| E015 | 2017-09-02 12:30 | 0.20185 | 97.5299 | 93.8379 | native source absent |
| E003 | 2020-07-17 10:00 | 6.7265 | 80.5351 | 86.0903 | native source absent |

The 20 events were selected specifically for major version disagreements. Their 100% low-RH rate is **not** a site-wide abnormal-HH prevalence estimate. Their close agreement with previous START-indexed, QC1 gap-filled `VPD_F` is source-derivation evidence, not evidence of an accurate measured RH. ERA5 and ERA5-Land may share biases, differ in vertical level, pressure/saturation reference, grid elevation, or timestamp convention. Neither one is an automatically validated replacement.

## Next: do not repeat Stage02E–O comparisons

[Stage02P site-scoped, read-only native-tower source availability inventory](../scripts/02p_CH_Aws_native_tower_source_availability_readonly.py) will search the **CH-Aws site folder only** for possible original instrument data packages, source products, archives and metadata. It inventories filenames, lightweight headers, NetCDF variable names, archive member names and JSON provenance references, without archive extraction or full FLUXMET data scans. `raw/EUF...FLUXMET_HH` is explicitly **processed FLUXNET product** and must not be mistaken for original unfilled tower measurements.

It will NOT prove the absence of tower data outside the scanned directory, nor certify QC for any discovered candidate. The following gate is manual/source-specific extraction of matched-time unfilled RH/TA and QC, or an explicit **SOURCE_NOT_AVAILABLE** HOLD if no such records can be located. Do not approve AD5/AD400, change forcing, select an ERA version, or modify GL-ZaH or any of the four simpler site cases.
