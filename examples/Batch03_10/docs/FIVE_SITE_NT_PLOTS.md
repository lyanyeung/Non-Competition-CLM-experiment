# Five completed Batch03 sites: AD400 + Normal400 and EC

This is an analysis of AT-Neu, CH-Cha, FI-Let, DE-Obe and GF-Guy from the
operator's completion snapshot. It first checks the actual 400 + 400 years of
continuous archived history for the exact FIXNC case pair. Completion in a
status list alone does not demonstrate convergence or observation availability.

Run these commands on IRIDIS6. The script is downloaded to a new tool directory;
it reads existing cases, archives and EC data and does not submit jobs or change
model input. Use the existing `clm_fates_env` Python environment.

```bash
set -euo pipefail
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOLDIR=$(mktemp -d "$HOME/CLM_FATES_PLOTS/five_site_tool.XXXXXXXX")
curl -fsSL 'https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py' -o "$TOOLDIR/plot.py"
PAIRS=(
  AT-Neu:AT-Neu_B03_FIXNC_AD400:AT-Neu_B03_FIXNC_NORMAL400
  CH-Cha:CH-Cha_B03_FIXNC_AD400:CH-Cha_B03_FIXNC_NORMAL400
  FI-Let:FI-Let_B03_FIXNC_AD400:FI-Let_B03_FIXNC_NORMAL400
  DE-Obe:DE-Obe_B03_FIXNC_AD400:DE-Obe_B03_FIXNC_NORMAL400
  GF-Guy:GF-Guy_B03_FIXNC_AD400:GF-Guy_B03_FIXNC_NORMAL400
)
"$PY" -B "$TOOLDIR/plot.py" --pair "${PAIRS[@]}" --preflight
OUT="$HOME/CLM_FATES_PLOTS/Batch03_AD400_NORMAL400_$(date -u +%Y%m%dT%H%M%SZ)"
"$PY" -u -B "$TOOLDIR/plot.py" --pair "${PAIRS[@]}" --output-root "$OUT"
printf '\nResults: %s\n' "$OUT"
```

The preflight reports missing histories, forcing settings and EC files and exits
nonzero on an incomplete site or inaccessible EC. It checks EC columns but not
their data quality or valid coverage; the actual analysis can still fail. Do not
run the second step until preflight issues have been addressed. To inspect a
specific EC source, use `--obs-csv SITE=/absolute/path/to/HH.csv`. If Research
Filestore is mounted, `OUT` may instead be set to a new absolute directory there.

The established output parent is `~/CLM_FATES_PLOTS/`; this run creates a fresh
timestamped sibling of the previously documented `Batch03_AD400_NORMAL400`
directory. Existing results are not overwritten. See `AD400_NORMAL400_summary.csv`
for per-site status and errors. Per-site outputs include both carbon plots,
monthly GPP/NEE comparison, carbon and flux tables, and metadata. If any site
is skipped or its EC comparison fails, the analysis returns nonzero; inspect the
summary instead of treating a process start as success. `--carbon-only` is an
explicit alternative, not the default.

The last *complete phase-aligned* Normal forcing cycle is mapped to the observed
calendar using DATM `year_first`, `year_last`, and `year_align`. NT GPP values
outrank DT values across all sources. DT is eligible only for a source without
usable NT during the forcing period, and only on days without an available NT
value from another source. Source order resolves ties within each partition.
The daily data record the selected GPP column and source. A day requires at least
40 valid half-hours and a monthly comparison at least 20 valid days; daily model
output uses the same paired days for model and EC. With monthly model output,
the model monthly mean and available EC days do not have identical temporal
support and this distinction should be retained in interpretation.

Model GPP is `FATES_GPP`, model NEE is `-FATES_NEP`, EC NEE is `NEE_VUT_REF`,
and flux units are g C m-2 d-1. Reported R² is `1 - SSE/SST`, and may be
negative; it is not squared correlation. Trends and cycle changes are screening
diagnostics, not a universal proof of equilibrium. The AD→Normal transition may
include pool rescaling, so Normal-phase trends are reported separately.

Code has off-cluster unit tests, but this update has not been run against these
IRIDIS histories or rendered and visually checked there. Inspect the output and
metadata before using the plots for publication.

