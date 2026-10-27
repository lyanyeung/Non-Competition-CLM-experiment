# AmeriFlux Batch03 US-Me6: one batch comparison of repair methods

This entry tests concrete VPD/QBOT candidates for all six held source runs against the preserved Stage13s baseline, using the already completed Stage13X report. It preserves the separately maintained Stage13Y and Stage13Z gates.

[Science code and full method notes](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/31e1c2cea29ecd8c9867e0c26ee114847cf67375/examples/AmeriFlux_MultiSite_10_Batch03/docs/ME6_BATCH_REPAIR_METHOD_VALIDATION_20261027.md)

Run [the pinned launcher](scripts/run_Me6_batch_method_validation.sh) on IRIDIS6 with Bash, from the base environment or the existing CLM environment. It activates `clm_fates_env`, checks three immutable Python source blobs, compiles without bytecode files, runs the self-test and one actual source audit plus candidate comparison. All input checks are included in that run, so a repeated full check is unnecessary.

The comparison includes raw ERA RH, local QC0-median-adjusted ERA RH with buffered held-out-day validation, and direct QC0-anchored interpolation solely within the four-HH September 2015 gap. There are 13 run/method comparisons over 782 distinct source times. The 1,568 candidate rows include alternative methods for the same source times and are **not** 1,568 repairs.

The output is a single batch decision table, explicit before/after candidate values, validation errors and a SHA256 integrity receipt under `reports/stage13_validation_Me6_six_run_repair_candidates_*`. Declared sample-size and skill screens are research choices. No real event is claimed to pass before execution.

The 235 earlier Stage13s approved halfhours and five Stage12ac values remain unchanged. Strict 8 C donor temperature and 4 hPa VPD continuity rules remain; QC2 neighbours and long-gap interpolation are not silently adopted. Neither actual forcing nor model jobs are written. A passing candidate still needs the grouped scientific scope decision before a separate forcing implementation.

Local validation passed seven synthetic regression tests, including full-batch scope and old-value preservation. Actual IRIDIS6 output is pending.
