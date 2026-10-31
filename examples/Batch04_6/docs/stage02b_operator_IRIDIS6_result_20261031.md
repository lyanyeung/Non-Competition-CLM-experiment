# ICOS Batch04 Stage02B — operator IRIDIS6 results (31 October 2026)

## Provenance and scope

Recorded from the operator-pasted console output of the SHA-pinned Stage02B script. Original full JSON is retained privately on IRIDIS6 at:

- `/home/ly3n24/ICOS_Batch04_stage02b_i2AVcim2/stage02b_diagnostics.json`
- `/home/ly3n24/ICOS_Batch04_stage02b_i2AVcim2/stage02b_console.log`

Script SHA PASS; self-test PASS; no CIME, Slurm, NetCDF or Git working-tree writes. The output was **not independently reproduced on IRIDIS6** and the full JSON has not been provided.

## Evidence table

| Station | Stage02A sample-read errors | Actual error reported | CIME input list status | Interpretation |
| --- | ---: | --- | --- | --- |
| CH-Aws | 15 | `No module named 'numpy'` in Stage02A, `No module named 'netCDF4'` in Stage02B probe | 8/8 cases show 25 absolute NC references, all paths exist | Python dependency error; candidate 2006/2024 annual files have NETCDF4_HDF5 headers, but actual content QC not performed |
| DE-Gri | 0 | No annual file was read by Stage02A | 2/2 cases: 28 NC references, 28 paths exist | Site 2004 provisional DATM annual path found in FLUXNET_13 experiment tree |
| DE-RuR | 0 | No annual file was read by Stage02A | 2/2 cases: 21 NC references, 21 paths exist | Site 2011 provisional DATM annual path found in FLUXNET_13 experiment tree |
| IT-Tor | 0 | No annual file was read by Stage02A | 2/2 cases: 24 NC references, 24 paths exist | Site 2008 provisional DATM annual path found in FLUXNET_13 experiment tree |
| ES-Agu | 0 | No annual file was read by Stage02A | 2/2 cases: 25 NC references, 25 paths exist | Site 2006 provisional DATM annual path found in FLUXNET_13 experiment tree |
| GL-ZaH | 2 | `No module named 'numpy'` in Stage02A, `No module named 'netCDF4'` in Stage02B probe | 1 case: 32 NC references, all paths exist | Candidate 2000/2025 annual files have NETCDF4_HDF5 headers; actual active DATM binding not yet checked |

The first path printed in each CIME input list is **not necessarily the site's DATM forcing**: CH-Aws and GL-ZaH show a generic atmospheric aerosol/deposition input as the first sorted NC reference. For DE-Gri/DE-RuR/IT-Tor/ES-Agu, the output shows the provisional annual DATM file path from `experiments/FLUXNET_13_ZBOT_DATM_20261018_054150_1008203/<SITE>/datm_annual/`. The Stage02B `ABS_NC_REFS` totals include all categories of model inputs, not just meteorological years. All reported referenced paths exist, but that is not a meteorological science pass.

## Decision

1. Confirm actual Python executable and available `numpy`, `netCDF4`, `ncdump` **without installing or changing the environment**. Both observed errors are dependency/import errors, not confirmed NetCDF corruption.
2. Filter CIME absolute references by the **site-specific** DATM annual filename, compare year sets and input roots across all 17 candidate cases. Trace `CaseDocs/datm_in` and stream references before choosing one source case. S30SHARED vs S30EXCL and CH-Aws RH variants remain unselected.
3. Once a working NetCDF reader is available, perform actual selected-DATM annual/half-hourly QC against native tower original data with consistent time/calendar and per-variable QC, not a header-only pass.
4. Keep GL-ZaH private Arctic host-to-FATES mapping requirement, CH-Aws RH/HumanIndexMod HOLD, and ES-Agu uncertain cover denominator. All six remain **HOLD_NO_AD5_AD400**.

Next tool: [Stage02C no-NumPy environment/DATM-reference audit](../scripts/02c_batch04_python_env_and_datm_reference_readonly.py).

## Follow-up after activating the correct Python environment (same day)

The operator reran the **same Stage02B source SHA** in an environment with working `numpy` and `netCDF4`. The new run preserved the same 15+2 **historical Stage02A errors**, but crucially reported **`NC_PROBE ... OPEN PASS TIME_KEYS time`** for all four sampled files:

- CH-Aws: `CH-Aws_DATM_2006.nc` and `CH-Aws_DATM_2024.nc` — both NetCDF4/HDF5 OPEN PASS.
- GL-ZaH: `GL-ZaH_DATM_2000.nc` and `GL-ZaH_DATM_2025.nc` — both NetCDF4/HDF5 OPEN PASS.

New report: `/home/ly3n24/ICOS_Batch04_stage02b_qRFrYeC1/stage02b_diagnostics.json` (not uploaded). **The original Stage02A errors remain historical counts in that input JSON; they are not new Stage02B read failures**. This resolves the narrow library/openability blocker for four probe files, but it does NOT prove their full climate physics or the correctness of other annual files.

Next: use the activated environment to perform a bounded read-only audit of the actual site annual DATM NC references across all six original source cases; record per-year source coverage, mismatched case references and numerical QC, while preserving source-versus-ERA and active-stream HOLDs.
