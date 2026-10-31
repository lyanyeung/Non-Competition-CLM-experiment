# ICOS Batch04 Stage02C — operator IRIDIS6 result (31 October 2026)

**Source:** operator-provided console output; full private JSON at `/home/ly3n24/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json` was NOT available for independent review. The Stage02C SHA verification and self-test passed; local Python `/home/ly3n24/.conda/envs/clm_fates_env/bin/python3`, NumPy 2.2.6 and netCDF4 1.7.4. Read-only; no submitted jobs.

| Site | Original cases | Distinct DATM annual paths | Year span | Path-set variants | Stage02C sampled files | Stage02C issues |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| CH-Aws | 8 | 133 | 2006–2024 | **7** | 14 | `CASE_VARIANTS_REFERENCE_DIFFERENT_DATM_PATHS` |
| DE-Gri | 2 | 22 | 2004–2025 | 1 | 2 | none emitted |
| DE-RuR | 2 | 15 | 2011–2025 | 1 | 2 | none emitted |
| IT-Tor | 2 | 18 | 2008–2025 | 1 | 2 | none emitted |
| ES-Agu | 2 | 19 | 2006–2024 | 1 | 2 | none emitted |
| GL-ZaH | 1 | 26 | 2000–2025 | 1 | 2 | none emitted |

**Total**: 17 original source cases and 233 distinct site-DATM annual file paths (133 CH-Aws candidates are *different variant paths*, not 133 years of observations). All 17 case lists had continuous year tokens within the stated ranges, no missing referenced paths and no duplicate annual filenames per year.

All **24** first/last variant-year NetCDF probes reported `OPEN PASS`, `TIME_N 17520`, `MET TBOT,QBOT,FSDS,FLDS,WIND,PSRF,ZBOT`, `FLAGS NONE_SCREENED`. (CH-Aws 14 samples, five remaining sites 2 each = **24** total.) `17520 = 365×48`, consistent with 30-minute NOLEAP forcing. This is **not yet confirmation** of CF calendar metadata, time-year alignment, year seams, precipitation variable name or source timestamps. `NONE_SCREENED` only means **none of the flags implemented in the limited Stage02C sample was emitted**; it is not a full QA pass, and precipitation (e.g. case-insensitive `PRECTmms`) was not displayed in that MET list.

Case names: CH-Aws 8 cases covering RH21A, RH25A, RH29A, RH34A, RH38A, RH42A_V8, RH25A 16d diagnostic and SPINUP500_11P. Four other sites S30EXCL and S30SHARED share the same DATM candidate path set. **This does not mean those model configurations are physically identical**. GL-ZaH has one SPINUP500_11P source candidate and still requires its private Arctic FATES HLM mapping.

**Scientific state:** Stage02C `SCIENCE_RELEASE HOLD` for all six. No case is chosen; no forcing repair, land surface change or model submission is approved.

## Next stage

[Stage02D read-only all-year numerical and temporal audit](../scripts/02d_batch04_all_annual_DATM_QC_and_variant_diff_readonly.py) enumerates the full annual DATM paths from this Stage02C report, checks all available annual files for missing and nonphysical variables, time-axis/calendar properties, within- and between-year time continuity, and **CH-Aws RH/QBOT forcing variant differences**. Those tests are still only **DATM-internal**: selected native tower observations/QC, ERA5 substitutions, selected active DATM stream binding and site PFT/soil science need later separate review.
