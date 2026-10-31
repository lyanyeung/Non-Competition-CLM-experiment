# ICOS Batch04 Stage02A — operator IRIDIS6 output, 31 October 2026

This is a **transcription and interpretation of the operator-pasted console output**, not a read of the private full JSON report. The script was fetched from the SHA-pinned GitHub commit; `STAGE02 SOURCE SHA PASS`, `STAGE02 SELF-TEST PASS`. No original inputs or model cases were written and no Slurm jobs submitted.

Operator report path: `/home/ly3n24/ICOS_Batch04_stage01_Dy3qIRjj/stage02_forcing_20261031T003910Z.json`. It has not been uploaded to GitHub.

| Site | Source case candidates | Forcing directories inspected | Stage02A result |
| --- | ---: | ---: | --- |
| CH-Aws | 8 | 14 | 8 directories contain annual NC candidates (7 with 19 files, 1 with 1); **every sampled NC had READ_ERROR**. 6 other directories have no NC in the audited tree. |
| DE-Gri | 2 | 2 | `packages` and `raw` contain 0 NC; each source case has 28 DATM reference lines |
| DE-RuR | 2 | 2 | `packages` and `raw` contain 0 NC; each source case has 21 DATM reference lines |
| IT-Tor | 2 | 2 | `packages` and `raw` contain 0 NC; each source case has 24 DATM reference lines |
| ES-Agu | 2 | 2 | `packages` and `raw` contain 0 NC; each source case has 25 DATM reference lines |
| GL-ZaH | 1 | 5 | `datm_11_provisional_dynamic_zbot_v1` contains 26 annual NC candidates, 2000–2025; the 2000 and 2025 sample files had **READ_ERROR**. Original case has 32 DATM reference lines. |

### Important distinctions

1. `READ_ERROR` is only the CLI summary flag. The **specific Python/netCDF4 exception was not displayed** in the provided output; check `sampled_netcdf[].read_error` inside the private Stage02 JSON. Do not call NC files corrupt before seeing it.
2. No NetCDF in `packages`/`raw` does not imply that FATES has no forcing. CIME DATM streams may reference annual NetCDF outside the site forcing tree, and `packages` may contain compressed source products instead.
3. `DATM_REF_LINES` is a count of candidate input-document references and **does not certify which stream was actually active**. S30SHARED and S30EXCL are not released or automatically ordered.
4. All 17 source cases retain the Stage01 `MATCH_STATIC_XML_EFFECTIVE_CIME_NOT_YET_VERIFIED` point-status classification. All six Batch04 sites remain in **HOLD**: no surface/FATES change, AD5 or AD400 submission is authorized.

### Stage02B gate

Run [the read-only exact-error and CIME source-path probe](../scripts/02b_batch04_explain_readerrors_and_datm_paths_readonly.py). It reads the original Stage02 JSON, prints exact stored error messages, inspects *direct* input-data-list paths for each case, and separately attempts a small NetCDF metadata read for representative failing samples. No full half-hourly science QC or data repair is attempted.
