# NL-Loo V3: PRE50, AD200 and POST300 diagnostic figures

This is a separate experiment from the 400+400 cohort. The V3 design uses
`NL-Loo_OBSPFT_NC_V3_PRE50` (Normal, model 1997–2046),
`NL-Loo_OBSPFT_NC_V3_AD200` (accelerated, 2047–2246), and
`NL-Loo_OBSPFT_NC_V3_POST300` (Normal, 2247–2546). The final restart target is
2547-01-01. The plan is documented in [the V3 protocol](../../docs/NL_Loo_V3_550_pipeline.md);
an older AD continuation record explicitly stated POST300 was not yet scheduled.
Actual current completion must be checked from archived data; the design is not
evidence that POST300 has run.

The script checks each actual V3 case, restart-reference case and contiguous
history years, and plots only available phases. A missing or incomplete phase
marks the figures `INTERIM`; phase boundaries are drawn without connecting the
carbon curves across potentially rescaled pools. Only available carbon fields
are plotted. `TLAI` is not a carbon pool. The Normal-phase trend table treats
PRE50 and POST300 separately and never fits across the accelerated phase.

For the EC comparison, the latest complete forcing cycle in POST300 is preferred.
If no usable POST300 cycle exists, PRE50 may be used and is explicitly labelled
`PRE50 INTERIM`; it is not a post-spin-up evaluation. EC GPP uses NT first,
falling back to DT where NT is unavailable. If fields or observations are
missing, EC comparison is reported unavailable and not fabricated. Model
`FATES_GPP` and `-FATES_NEP` and EC `NEE_VUT_REF` use g C m-2 d-1. A day needs
at least 40 valid half-hours (or 20 hourly values) and a month at least 20 days.
R² is `1 - SSE/SST`, not squared correlation. EC timestamps are used as supplied;
their relationship to the forcing clock should be reviewed.

Run on the IRIDIS6 login node. The first command is read-only preflight; the
second writes a new Home output directory, then pushes any generated PNGs and
an explicitly labelled index to a new GitHub folder using your GitHub SSH key.
Existing model cases, archived history and previously uploaded figures are not
modified; no raw observations or model files are uploaded.

```bash
(
set -euo pipefail
BASE='https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/nl_loo_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/scripts/16_plot_NL_Loo_three_phase.py" -o "$TOOL/nl_plot.py"
OUT="$HOME/CLM_FATES_PLOTS/NL_Loo_V3_$(date -u +%Y%m%dT%H%M%SZ)"
printf 'Output: %s\nScripts: %s\n' "$OUT" "$TOOL"
"$PY" -u -B "$TOOL/nl_plot.py" --preflight
"$PY" -u -B "$TOOL/nl_plot.py" --output-root "$OUT" --publish
)
```

`GITHUB PUSH SUCCESS` and a commit SHA are printed only after a successful Git
push. A missing EC comparison is reported and makes the process exit nonzero,
even if carbon figures were produced and published. Figures and CSV/JSON
diagnostics remain in `OUT` if publication fails. Do not use the generic
AD400+Normal400 plotter for this three-phase experiment. This update has local
synthetic tests; it has not yet been run against the actual V3 archives.
