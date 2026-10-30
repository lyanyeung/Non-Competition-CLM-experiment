#!/usr/bin/env bash
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
