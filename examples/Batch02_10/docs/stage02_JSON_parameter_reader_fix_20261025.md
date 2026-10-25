# Stage02 result: shared JSON parameter reader fix — 25 October 2026

The operator supplied the selected-input output from Stage02. The original report SHA256 is `17b7808a3a3042a4ab90159f12e38488050eb63e2c1925575ebb1cbc6f7ee4af`. Its compact transcribed source snapshot is [retained here](../../../data/batch02_10_stage02_source_snapshot_20261025.json). The console lists ten source cases; it is not evidence that new Batch02 FIXNC cases have been created or run.

## What the output establishes

- All ten reference cases use `use_fates=.true.`, `use_fates_sp=.false.`, `use_fates_fixed_biogeog=.false.` and `use_fates_nocomp=.false.`. The last two flags must be changed to `.true.` **in new, independent cases** for the requested experiment. Original competition experiments remain unchanged.
- The land surface and ten soil input layers were readable at the time of Stage01. Their texture values and grid PFT fractions are source-model metadata, not measured tower compositions.
- Every reference uses the same `fates_params_default.json` path. Stage02 attempted to read it through `netCDF4.Dataset` and therefore reported one `NetCDF: Unknown file format` issue, associated with the first site DK-Sor. This is a **script file-format bug**, not ten independent missing maps and not a failed CLM run.
- The original Stage02 output did not decode or certify the map. Its old `PARAMETER_MAP_REPEATED` message only meant a path/hash had already been attempted, even if that attempt failed. That wording is corrected: a failed shared map now remains explicitly unavailable.

| Site | Recorded forcing years | Original-grid crop % |
| --- | --- | ---: |
| DK-Sor | 1996–2024 | 44.60 |
| FR-Hes | 1997–2025 | 27.32 |
| FR-FBn | 2008–2024 | 19.85 |
| BE-Bra | 1996–2025 | 37.41 |
| IT-Noe | 2004–2025 | 30.54 |
| CH-Fru | 2005–2024 | 3.94 |
| CH-Lae | 2004–2024 | 22.23 |
| ES-LJu | 2004–2024 | 28.54 |
| FI-Hyy | 1997–2025 | 10.93 |
| IT-MBo | 2003–2025 | 33.57 |

The crop percentages above do not establish actual tower cropland and are not adopted as new stand-level landunit decisions. Recorded stream years do not certify time coverage or source QC. The IT-Noe reference points to `datm_11_IT-Noe_QC_v3_RHcap_20261021_230447`; several other stream paths retain `provisional`/`PROVISIONAL` names. Filenames alone neither invalidate the files nor prove that later repairs are present. In particular, ES-LJu's annual-path spelling does not resolve its corrected forcing file/symlink targets by itself. No new forcing rewrite or large re-audit is triggered by this parser fix.

## Corrected reader and short next command

[`02_summarize_selected_inputs_readonly.py`](../scripts/02_summarize_selected_inputs_readonly.py) now dispatches `.json` to the standard-library JSON parser and retains its NetCDF reader for NetCDF parameter files. It reads `parameters.fates_pftname.data` and `parameters.fates_hlm_pft_map.data`, validates a rectangular finite numeric matrix and matching PFT-name count, and preserves the stored orientation and dimension metadata. It verifies the Stage01 expected SHA256 both before and after reading. An old generic NetCDF `read_error` in the snapshot does not prevent a correctly matched JSON file from being parsed with the correct reader.

Use `--parameters-only` with the **same existing report** to print each distinct parameter file only once and identify all sites sharing it. There is no reason to repeat the long soil/DATM listing or rerun Stage01. No local paths, source files, cases, namelists or jobs are changed by the reader.

```bash
python3 -B "$HOME/Non-Competition-CLM-experiment/examples/Batch02_10/scripts/02_summarize_selected_inputs_readonly.py" \
  --inventory /iridisfs/home/ly3n24/Batch02_10_preflight_20261025T070625_933191Z/all_sites.json \
  --parameters-only
```

**Verification performed:** self-test covers the actual JSON schema and malformed/nonfinite/ragged maps. A filesystem regression fixture used an actual `.json` file shared by ten report entries, including the historical snapshot `read_error`. It produced one decoded map and `MAPPING_READ PASS ISSUES 0`, preserved the file hash, and rejected both changed-file hashes and malformed JSON schemas. The exact HPC parameter contents remain to be read by the operator command; the tests do not claim that the remote map has already passed.

Reading the parameter map is a technical prerequisite, not approval of ten site PFT mixtures or proof of executable/source revision provenance. New surfaces, PFT/soil choices and AD400/Normal400 submission remain separate subsequent work.
