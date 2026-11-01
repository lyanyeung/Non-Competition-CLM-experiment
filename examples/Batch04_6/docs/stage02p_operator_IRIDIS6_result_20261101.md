# ICOS Batch04 CH-Aws Stage02P — actual source inventory result (2026-11-01)

**User-provided operator output:** Stage02P download SHA was verified, `STAGE02P SELF-TEST PASS`, read-only inventory completed. The original source files, forcing NC, Git worktree, CIME cases and Slurm jobs were not changed.

- JSON `/home/ly3n24/ICOS_Batch04_stage02p_D6TUjQg7/results/stage02p_CH_Aws_native_source_availability.json`
- CSV `/home/ly3n24/ICOS_Batch04_stage02p_D6TUjQg7/results/stage02p_CH_Aws_source_file_headers.csv`
- LOG `/home/ly3n24/ICOS_Batch04_stage02p_D6TUjQg7/stage02p_console.log`

`SITE_FILES_SCANNED 169`, `TRUNCATED False`. Recognized candidate-file categories:

| Category | Files |
|---|---:|
| DISTRIBUTED_PROCESSED_FLUXMET_NOT_NATIVE | 2 |
| DISTRIBUTED_PRODUCT_METADATA | 4 |
| EXPLORATORY_REVISION_EVIDENCE_NOT_TOWER | 12 |
| MERGED_PROCESSED_CANDIDATE_NOT_NATIVE | 12 |
| MODEL_DATM_ANNUAL_NOT_RAW | 72 |
| UNCLASSIFIED_SOURCE_OR_METADATA | 1 (site point surface NC) |
| POSSIBLE_TOWER_OR_SOURCE_PRODUCT_UNVERIFIED | **0** |

**Caution:** these categorized counts total 103; `FILES_SCANNED` includes additional files that did not match the scanner's supported extensions or output classifications. An unclassified `subset_data/surfdata_CH-Aws_hist_2000_16pfts_c261014.nc` is a model **surface** not a humidity source.

The site-scoped directory contains an original *distributed* EUF/FLUXNET product `raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv` (372,131,800 bytes), weekly FLUXMET, BIF/BIFVARINFO metadata and status/manifests/processed repair candidate tables. **Distributed FLUXMET_HH is a processed/gap-filled source, not automatically raw/native measured tower RH.** The earlier Stage02L showed source `VPD_F_QC=1` and original `RH` missing for all 20 high-difference anchors.

Crucial newly surfaced **clock convention lead:** legacy Stage21 and Stage25 revision ledgers use the explicit CSV header **`time_local_standard_UTCplus1`**, while later Stage34/38/42 use generic `time`, and original FLUXMET has both `TIMESTAMP_START` and `TIMESTAMP_END`. Stage02K/L showed numerical agreement with same-label START-indexed processed VPD_F, but no independent real UTC/native time basis was established. Treat Stage21/25 +1 hour as a hypothesis to test against DATM, not an automatic conversion.

## Next Stage02Q

[Stage02Q source-metadata / original-local-time comparison tool](../scripts/02q_CH_Aws_original_BIF_localtime_and_native_source_search_readonly.py) reads the saved Stage02P+O JSONs, the two small original EUF BIF and BIFVARINFO_HH metadata CSVs, and Stage21 and Stage25 local-standard-time revision ledgers. It reports how many raw ledger timestamps fall near the exact Stage02O 20 DATM event labels under **separate literal 0, ±30, ±60 min candidates**, preserving all original columns and refusing to choose a clock. Optionally inspects candidate filenames under a user-selected **small-depth HOME directory**; no ZIP extraction or full FLUXMET input scan. Only new JSON/CSV in a fresh empty HOME output directory; no source or Slurm changes.

Stage02P found **no positively identified native unfilled sensor RH/QC file under the one scanned CH-Aws site directory**. It does **not** establish that tower data are unavailable elsewhere, including archives/local Windows copies or the official source provider. Scientific release for all six Batch04 sites remains HOLD, and neither RH34A, RH38A nor RH42A may be chosen from source similarity alone.
