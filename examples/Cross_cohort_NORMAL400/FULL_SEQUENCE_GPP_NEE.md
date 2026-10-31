# Full-sequence GPP / NEE / NPP / LAI (AD400 → Normal400) with EC reference

`scripts/07_plot_full_sequence_GPP_NEE_with_EC.py` redraws the 54 Normal cases plotted by
job 4764252 ([figures](../../figures/AD400_NORMAL400/20261030T053000Z_job4764252/README.md))
as one 800-year time series per site, from the first AD year to the last Normal year:

- **Panels:** GPP, NEE, NPP and LAI, plus FATES_VEGC where the history has it. The thin line is the monthly value (seasonal envelope) and the thick line is the annual mean. AD400 is red with a shaded background; NORMAL400 is blue.
- **EC tower reference** on the GPP and NEE panels, taken from the site's own forcing years:
  - the climatological annual mean (dotted line);
  - the peak month for GPP, or the minimum month for NEE (dash-dot line);
  - the range of complete-year annual means (grey band).
  - A box gives the model mean over the last complete forcing cycle, next to the EC mean and the bias.
- **EC handling is the job's own.** The Stage15 module (`examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py`, copied in as `plot.py`) supplies the history index, the time decoding, the DATM forcing years and the EC readers. GPP uses NT first and falls back to DT; EC NEE is `NEE_VUT_REF`; model NEE is −`FATES_NEP`. Units are g C m⁻² d⁻¹.
- **Automatic screening flags** are written in each figure title and in `full_sequence_summary.csv`:
  - GPP≈0 from year N (vegetation collapse);
  - a GPP or LAI step of more than 10 % at year 400/401;
  - last-cycle GPP below 0.5× or above 2× the EC value;
  - a GPP or LAI trend of more than 10 % per 100 years over the last 100 Normal years.

  These flags are hints for review, not conclusions.
- **Overview figures:** `ALL_SITES_GPP_full_sequence_overview.png` and `ALL_SITES_NEE_full_sequence_overview.png` show every site at once.

AD only rescales soil decomposition pools, so GPP, NPP and LAI should be continuous across year
400/401. Model and EC days are aligned on native timestamps without a timezone shift. As in the
job's monthly overview, check the clock basis for UTC-shifted AmeriFlux forcing. 800 years is not
proof of equilibrium.

## 1. Run the analysis (Slurm, read-only inputs)

Paste the whole block into an IRIDIS6 login shell. It writes to a new folder on Home. `REF` is the
Git branch or commit the tool is fetched from.

```bash
(
set -euo pipefail
REF="${REF:-main}"
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$REF"
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/fullseq_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py" -o "$TOOL/fullseq.py"
"$PY" -m py_compile "$TOOL/plot.py" "$TOOL/fullseq.py"
OUT="$HOME/CLM_FATES_PLOTS/Full_sequence_GPP_NEE_$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$HOME/CLM_FATES_PLOTS/fullseq_%j.log"
JOB=$(sbatch --parsable --partition=batch --job-name=fullseq_gpp_nee --nodes=1 --ntasks=1 \
      --cpus-per-task=8 --mem=24G --time=08:00:00 --output="$LOG" \
      --wrap="'$PY' -u -B '$TOOL/fullseq.py' --output-root '$OUT' --workers 8")
JOB_ID=${JOB%%;*}
printf 'Job: %s\nOutput: %s\nLog: %s\nTool: %s\n' "$JOB_ID" "$OUT" "${LOG/\%j/$JOB_ID}" "$TOOL"
)
```

- Progress: `squeue -u "$USER"`, then `tail -f` the printed log. Each site ends with a line `== SITE: OK|MODEL_ONLY|SKIPPED flags`.
- Every site reads about 800 × 12 monthly history files, so the whole run takes a while; `--workers` runs that many sites in parallel. Adjust partition, memory and time to local policy.
- **Test one or two sites first:** add `--sites DE-Hai FI-Sod` inside `--wrap` (and use `--workers 2`).
- **If the job stops early:** submit the same command with `--resume '<Output>'` instead of `--output-root`. Finished sites are kept; only unfinished ones are redrawn.
- **Status meanings:** `MODEL_ONLY` means the EC reference could not be read for that site; the figure shows the model only and the reason is in the title. `SKIPPED` means the history could not be read; see the `Error` column in the summary.
- **Other Normal cases:** use `--pairs SITE:NORMAL_CASE ...` in place of the job 4764252 list. The AD case is taken from the Normal case's `RUN_REFCASE`.

## 2. Publish the PNGs to GitHub (login node, SSH)

After `RUN_COMPLETE.json` exists in the output folder:

```bash
"$HOME/.conda/envs/clm_fates_env/bin/python" -B '<Tool>/fullseq.py' --publish-run '<Output>'
```

This clones a fresh copy of `main` and adds `figures/AD400_NORMAL400_full_sequence/<UTC stamp>_from_job4764252/`. The new folder holds:

- the per-site PNGs;
- the two overview PNGs;
- a README table with EC versus model means, the flags and links;
- `SHA256SUMS`.

No CSV, model output or observation data is uploaded. The command prints `PUSH SUCCESS` and the GitHub URL when it is done.

Local tests use synthetic histories, synthetic EC files and a stand-in netCDF reader. The tested cases are: a healthy site, a site whose vegetation dies in year 18, a site without EC data, parallel workers, resume after interruption, and publishing to a local Git remote. The script has not yet been run on IRIDIS6 output.
