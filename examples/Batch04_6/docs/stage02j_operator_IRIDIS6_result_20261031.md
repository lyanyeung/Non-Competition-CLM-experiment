# ICOS Batch04 Stage02J — CH-Aws original FLUXMET_HH product source contexts

**Operator run:** 31 October 2026. Source SHA verified and self-test passed; actual IRIDIS6 read-only full-source stream reported success.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02j_oXzrILXw/results/stage02j_original_FLUXMET_HH_event_review.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02j_oXzrILXw/results/stage02j_original_FLUXMET_HH_source_matches.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02j_oXzrILXw/stage02j_console.log`

The source-pinned EUF `raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv` was **372,131,800 bytes** and contained **333,120 scanned rows**, `FULL_SCAN True`. It has **181 columns**, with independent `TIMESTAMP_START` and `TIMESTAMP_END`. All **20 ranked QBOT variant-difference anchor events** matched five nearby source half-hour rows within ±60 minutes under *both* START and END readings (**10 time-column candidate matches per event = 200**; NOT 200 independent observations).

### Calendar/time caveat

The original source's 333,120 half hours vs candidate DATM's 19 × 17,520 = 332,880 half hours differ by exactly **240 HH = five 48-HH leap days** (2008, 2012, 2016, 2020, 2024). This is consistent with the DATM NOLEAP procedure, but is not proof that actual timestamp alignment, 29 February removal or START-vs-END conventions are correct. Directly comparing original-vs-DATM rows by raw index is forbidden until time evidence is verified.

### Original product fields found

`TA_F_MDS`, `TA_F_MDS_QC`, `TA_ERA`, `TA_F`, `TA_F_QC`, `VPD_F_MDS`, `VPD_F_MDS_QC`, `VPD_ERA`, `VPD_F`, `VPD_F_QC`, `PA`, `PA_ERA`, `PA_F`, `PA_F_QC`, `RH` and many others. The product is **FLUXMET_HH**, i.e. a processed original-distribution product, **not necessarily direct unfilled tower QC0 observations**. QC flags and field units must be verified from data dictionaries rather than assigning meaning based on `0` or `1`.

Console source examples from **TIMESTAMP_END** candidate context (not yet established as the DATM time convention):

| DATM event time | `TA_F` raw | `TA_F_QC` raw | `VPD_F` raw | `VPD_F_QC` raw | `PA_F` raw |
|---|---:|---|---:|---|---:|
| 2007-07-22 07:30 | 7.520 | 0 | 10.344 | 1 | 79.941 |
| 2007-07-22 07:00 | 6.838 | 0 | 8.376 | 1 | 79.947 |
| 2008-06-27 06:30 | 6.981 | 0 | 3.245 | 1 | 80.911 |
| 2019-07-29 07:30 | 8.169 | 0 | 6.678 | 1 | 79.043 |
| 2020-07-17 10:00 | 9.081 | 0 | 7.223 | 1 | 80.400 |

**These are only displayed examples** (one of ten alternative source temporal matches per event). No unit conversion, native time-zone assumption, tower QC0 determination, ERA5 assignment, source-vs-candidate moisture verdict or active case approval has been made.

### Scientific next steps

Read the saved Stage02J report, inspect actual metadata on units where available, then compare START and END at offset=0 separately against same-datetime DATM TBOT/PSRF/QBOT by named event, reporting original `RH`, original/filled `TA_F` and `VPD_F`, `TA_ERA`/`VPD_ERA`, `PA`/`PA_F` and the actual QC/MDS fields. Diagnose only conditional/metadata-backed specific-humidity reconstructions from VPD or RH. **Do not conclude VPD_F_QC=1 is accepted observed tower data without authoritative definitions.** Event-specific source provenance and pressure/time conversions must be evidence-backed.

[Stage02K read-only event source vs DATM comparison](../scripts/02k_CH_Aws_FLUXMET_DATM_event_physics_readonly.py). No forcing edits, no Slurm jobs, no automatic source-case selection. CH-Aws and all six Batch04 sites remain **HOLD**.
