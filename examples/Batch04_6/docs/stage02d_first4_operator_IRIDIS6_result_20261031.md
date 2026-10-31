# ICOS Batch04 Stage02D — four-site IRIDIS6 operator result, 31 October 2026

## Provenance and limits

This is an **operator-console evidence record**, not an independently inspected JSON or native tower-product audit. Original Stage02D script was fetched by fixed commit `6f1ec03da455ef82bb99c690aef63f9ffa3339c0` and git blob SHA `f54643001c58f3f27197089bce5d74d34d2079de`; console `SOURCE VERIFIED` and `STAGE02D SELF-TEST PASS`. An initial attempt in the `base` conda environment failed with `No module named 'numpy'`. The operator corrected that by activating **`clm_fates_env`** (not the typo `clm_fates_eenv`), and successfully ran the audit with:

- Python: `/home/ly3n24/.conda/envs/clm_fates_env/bin/python3`
- NumPy: `2.2.6`
- netCDF4: `1.7.4`
- Stage02C input: `/home/ly3n24/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json`
- Stage02D first-four full JSON: `/home/ly3n24/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.json`
- Stage02D first-four console log: `/home/ly3n24/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.log`

**None of those local JSON/log files was uploaded to this public repository.** Console output confirms that the checker was read-only, with no changed inputs or Slurm submissions.

| Site | Unique annual DATM NC examined | Years | Cross-variant differing years | Stage02D flagged-file counts | Scientific release |
| --- | ---: | --- | ---: | --- | --- |
| DE-Gri | 22 | 2004–2025 | 0 | `{}` | HOLD |
| DE-RuR | 15 | 2011–2025 | 0 | `{}` | HOLD |
| IT-Tor | 18 | 2008–2025 | 0 | `{}` | HOLD |
| ES-Agu | 19 | 2006–2024 | 0 | `{}` | HOLD |
| **Total** | **74** | — | — | **No emitted flags** | **HOLD** |

### Interpretation

For **74 distinct referenced annual point DATM NC files**, the Stage02D checker did not emit any failure among its implemented internal checks, including file open, time-axis decoding / step regularity, filename year alignment, candidate year joins, finite required model meteorology and its limited unit-conditioned screening. The script does not establish physical correctness of tower measurements, correctness of ERA5 replacements or whether these listed NC files were the active runtime DATM source.

`VARIANT_DIFF_YEARS 0` on the four sites is expected because the Stage02C inventory identified **one input-file path set** for both S30EXCL and S30SHARED cases. It is not evidence that the two case configurations have identical surface, FATES parameters or physics.

These files are labelled **PROVISIONAL** in their names. Do not convert `FLAGS {}` into unconditional production forcing approval. Remaining gates: source tower original/QC, ERA substitutions and year-seam provenance, effective DATM streams and calendar, 10-layer soil/ORGANIC and PFT landunit decision, and ES-Agu vegetation/biocrust cover denominator.

### Next controlled step

Execute the **same immutable Stage02D read-only script** against **CH-Aws and GL-ZaH** from the Stage02C JSON. CH-Aws comprises 133 distinct candidate annual files in seven forcing-path sets (8 original cases), so expect a per-year, per-variable variant comparison rather than a single source selection. GL-ZaH has 26 annual files and must preserve its private Arctic HLM-to-FATES parameter mapping hold.

Do not resubmit the 74-file first-four audit unnecessarily. Keep new reports under a fresh HOME output folder; do not use `git pull`, `git reset`, `git clean`, `git stash` or overwrite local working files. **No AD5 or AD400 jobs are authorised by this result.**
