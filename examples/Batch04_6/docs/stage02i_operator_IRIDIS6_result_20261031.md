# ICOS Batch04 Stage02I — CH-Aws candidate source CSV event audit (31 October 2026)

This document transcribes the operator-provided IRIDIS6 **terminal output only**. The detailed private JSON/CSV reports have not been imported into GitHub.

- JSON: `/home/ly3n24/ICOS_Batch04_stage02i_lcZXq0Ls/results/stage02i_source_event_matches.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02i_lcZXq0Ls/results/stage02i_source_event_matches.csv`
- LOG: `/home/ly3n24/ICOS_Batch04_stage02i_lcZXq0Ls/stage02i_console.log`
- Pinned script `SOURCE VERIFIED`; `STAGE02I SELF-TEST PASS`; data and Slurm unchanged.

## Observed evidence

- Inspected **19 candidate CSV** entries and **11 JSON metadata** manifests.
- Returned **437 candidate time-matched CSV rows**, **not** 437 unique, source-validated tower records: four 2006–2024 merged multisource half-hour CSVs contributed **100 rows each = 400** repeated and ±60-minute event contexts; Stage34 ledger added 12, Stage38 15 and Stage42 10 rows.
- Stage29 sensitivity ledger (77 rows), 559-RH trial ledger, 33-uncertainty ledger had **zero matches** in the limited top-20 event ±60-minute selection. Zero here does not prove absence of related source evidence outside that window.
- Stage28, Stage21, Stage25 ledgers, EUF BIF metadata and `!TOC.csv` were reported as `NO_RECOGNISED_TIME_COLUMN`. The reader stopped after the first record when a recognized HH time field was missing; **do not interpret ROWS 1 as the true number of rows**.
- The key original EUF/FLUXNET `EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv` was **`SKIP_OVER_MAX_MB`** due to the Stage02I **90 MB** bound; no direct HH source values/QC had yet been read from that product.
- Weekly FLUXMET CSV scanned 988 records and had 0 HH event matches; the weekly product cannot substitute for the original half-hour audit.

Revision manifests at stage22/26/28/29/34/38/42 parsed; their `scientific_status`, SHA and method fields were located but not interpreted as acceptance. The Stage02I matching algorithm compared parsed timestamp strings without proving whether they were UTC, local, start, or end of the native averaging interval; **matched rows are only candidate evidence**.

## Scientific decision

**CH-Aws remains HOLD_NATIVE_SOURCE_QC_TIME_CONVENTION_AND_ERA**. It is premature to approve, reject or replace QBOT in any annual DATM candidate, despite the Stage02D internal file checks and Stage02G tiny shared RH-water >100% flags.

## Stage02J next gate

[Stage02J source-pinned read-only original FLUXMET_HH event extraction](../scripts/02j_CH_Aws_original_FLUXMET_HH_event_evidence_readonly.py) will stream the entire >90 MB original FLUXMET_HH CSV with bounded memory, preserve `TIMESTAMP_START` and `TIMESTAMP_END` separately, extract the candidate exact and ±60-minute windows for the top 20 QBOT events, and list original product TA/RH/VPD/PA plus any QC fields actually present. It also relates those original-record candidates to the 437 Stage02I multi-version/ledger matches **without claiming source UTC provenance or tower-only QC**. FLUXNET FLUXMET_HH is a processed source product, not necessarily unfilled native tower data; any residual QC/ERA5 assessment needs separately corroborated originals.

No original files, CIME cases, soil, PFT, git worktree or Slurm jobs may be modified during this gate.
