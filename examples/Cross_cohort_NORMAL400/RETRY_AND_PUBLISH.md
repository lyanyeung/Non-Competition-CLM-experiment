# Retry missing figures and publish completed PNGs

The initial job is **4764252**. Submit the following as one Slurm job: its
`afterany` dependency waits for that job to finish (successfully or otherwise).
The retry also verifies the terminal state through `sacct` before it reads the
previous results. It locates the old output from that job's log; if this is
unavailable and several possible old runs exist, it stops rather than guessing.

The retry re-scans current FIXNC/OBSPFT_NC cases, follows each Normal case's
`RUN_REFCASE` and validates completeness and final restarts. A previous pair is
reused only when its summary and metadata say OK, match both case names, and
all three standard PNGs exist. Missing or failed pairs are redrawn, provided
their current AD and Normal cases pass the checks. Existing outputs are never
overwritten. Running or incomplete cases are listed but not plotted.

```bash
(
set -euo pipefail
BASE='https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main'
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
mkdir -p "$HOME/CLM_FATES_PLOTS"
TOOL=$(mktemp -d "$HOME/CLM_FATES_PLOTS/retry_tool.XXXXXXXX")
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py" -o "$TOOL/scan.py"
curl -fsSL "$BASE/examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py" -o "$TOOL/plot.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/04_retry_missing_sites.py" -o "$TOOL/retry.py"
curl -fsSL "$BASE/examples/Cross_cohort_NORMAL400/scripts/05_publish_completed_figures.py" -o "$TOOL/publish.py"
OUT="$HOME/CLM_FATES_PLOTS/Missing_completed_AD400_NORMAL400_$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$HOME/CLM_FATES_PLOTS/missing_sites_%j.log"
JOB=$(sbatch --parsable --dependency=afterany:4764252 --partition=batch \
  --job-name=missing_site_plots --nodes=1 --ntasks=1 --cpus-per-task=1 \
  --mem=8G --time=12:00:00 --output="$LOG" \
  --wrap="'$PY' -u -B '$TOOL/retry.py' --previous-job 4764252 --output-root '$OUT'")
JOB_ID=${JOB%%;*}
printf 'Retry job: %s\nRetry output: %s\nRetry log: %s\nPublish script: %s\n' \
  "$JOB_ID" "$OUT" "${LOG/\%j/$JOB_ID}" "$TOOL/publish.py"
)
```

Keep the printed job ID, output directory and publish script path. If Slurm
cannot attach a dependency to an already retired job, verify job 4764252's
terminal state with `sacct -j 4764252`, then submit the same command without
`--dependency=afterany:4764252`; the retry script still verifies the old state.
If the old output cannot be identified uniquely, see the retry log and pass
`--previous-run /absolute/path/to/original/output` to `retry.py` in a fresh job.

## Upload after the retry job stops

Run this on the **login node**, replacing the three placeholders with the exact
values printed above. The publisher checks `sacct` and that the retry job ID
matches `RUN_INFO.json`. It first lists all files, then `--publish` clones a
fresh copy of the GitHub repository, commits and pushes **only PNG figures, a
README index and SHA256SUMS**. It does not touch your existing clone or publish
NetCDF, raw EC data, daily/monthly CSVs, or restart files.

```bash
PY="$HOME/.conda/envs/clm_fates_env/bin/python"
RETRY_JOB='<retry job ID>'
RETRY_OUT='<retry output directory>'
PUBLISH='<printed publish script path>'
"$PY" -B "$PUBLISH" --run "$RETRY_OUT" --retry-job "$RETRY_JOB"
"$PY" -B "$PUBLISH" --run "$RETRY_OUT" --retry-job "$RETRY_JOB" --publish
```

The index reports missing plots and cases with no figure. For each case the
publisher selects the original or retry directory with the most PNGs; on a tie
it uses the retry directory. It never merges individual images across runs.
`PUSH SUCCESS` and a commit are reported only after `git push` succeeds. The
figures stay on Home even if GitHub authentication or the push fails; fix the
login-node Git credentials and rerun the publish command. Do not share passwords
or tokens in chat. A pushed partial collection is explicitly labelled in the
index, and cases without all three plots still require follow-up.

Check scientific caveats before using the figures: missing carbon pools are not
reconstructed; NT GPP is preferred but DT can be used where NT is unavailable;
the figure legend shows the actual source. UTC/local clock and AD/Normal DATM
stream differences can affect the EC comparison. Runtime success and 400+400
years do not prove equilibrium. Tests here are synthetic; real IRIDIS results
and the final GitHub upload have not yet been verified by this code update.

