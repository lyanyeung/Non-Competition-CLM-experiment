# Batch02_10 — second European/ICOS cohort, AD400 → Normal400

**Updated 25 October 2026.** The operator requested the next ten sites after the previous Batch01 run. This example activates the ten sites already reserved in the repository; it does not reuse or change any Batch01 case. These are European/ICOS-linked tower sites; the exact network membership is preserved in the [site register](../../data/batch02_10_sites.csv), rather than claiming that every site has identical ICOS status.

**Implemented now:** a runnable, read-only combined source inventory and actual-input trace, a current ten-site science decision table, a checksum-verified raw-GitHub downloader, and the staged AD400/Normal400 runbook below. **Not implemented or submitted yet:** new site surfaces, Batch02 AD cases, AD continuation or Normal submission scripts. Their site-specific adaptation needs the actual IRIDIS case/input report and resolved PFT decisions. The audit is the same entry step used for Batch01, with its later actual-input tracing combined so a second source scan is unnecessary.

## Selected ten sites

**Stage01 execution reported successful on 25 October:** all ten site directories and active source-surface references were found; SHA checks and self-test passed. The printed `HOLD` labels concern unresolved scientific inputs, not an audit runtime error. See [the source-reference table, reported start/CO₂ values and PFT follow-up](docs/stage01_source_inventory_and_next_inputs_20261025.md). The next script summarizes the existing report; Stage01 does not need to be rerun.

```bash
DIR="$HOME/Non-Competition-CLM-experiment/examples/Batch02_10/scripts"
mkdir -p "$DIR"
curl -fLsS \
  https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/02_summarize_selected_inputs_readonly.py \
  -o "$DIR/02_summarize_selected_inputs_readonly.py" || exit 1
python3 -B "$DIR/02_summarize_selected_inputs_readonly.py" --self-test || exit 1
set -o pipefail
python3 -B "$DIR/02_summarize_selected_inputs_readonly.py" \
  --inventory /iridisfs/home/ly3n24/Batch02_10_preflight_20261025T070625_933191Z/all_sites.json \
  2>&1 | tee "$HOME/Batch02_10_selected_input_details.log"
```

| Site | Original group | Ecosystem | Input decision still needed |
| --- | ---: | --- | --- |
| DK-Sor | 6 | Deciduous forest | DBF80; split the combined ENF/DNF20 |
| FR-Hes | 8 | Deciduous forest | DBF ≳95 of 2020 basal area; classify remainder and select survey date |
| FR-FBn | 8 | Mixed Mediterranean forest | Pine ENF ≈75 of basal area; remaining25 is not all verified EBF |
| BE-Bra | 11 | Mixed forest | ENF55/DBF23; remaining22 unresolved |
| IT-Noe | 11 | Mediterranean shrubland | Vegetated-only species shares; variable total cover; shrub mapping |
| CH-Fru | 11 | Managed grassland | Total mixed herb cover up to90 does not give grass/forb fractions |
| CH-Lae | 11 | Mixed forest | Listed DBF80/ENF12; remaining8 unresolved |
| ES-LJu | 13 | Open shrubland/grass mosaic | Grass19/shrub12; other vegetation≈19; nonvegetated≈50 |
| FI-Hyy | 13 | Boreal forest | Tower-local dated conifer/birch inventory; old60/25/15 unverified |
| IT-MBo | 13 | Alpine meadow | Grass38/Trifolium14.5 of basal cover; remaining47.5 unresolved |

These figures retain their **original reported denominators**, not CLM ground-area fractions. No remaining share is silently assigned to grass, and no incomplete species list is normalized to 100. The two grassland sites and two shrubland sites cannot use the forest-only Batch01 surface builder unchanged. The newer [38-site reviewed inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/38_site_observed_PFT_percent_evidence_v2_20261024.csv) supersedes the old unverified FI-Hyy mixture and the older IT-Noe species-completeness claim. Exact source blob: `9e0dd27b8ba4a7e0c80aea9258133bcce2eb7745`.

Binding status: [Batch02 source evidence](../../data/batch02_10_sites.csv) and [Batch02 input gates](../../data/batch02_10_input_gates.csv). All ten are **HOLD for new surface creation** until an evidence-supported composition or explicitly documented experimental proxy is selected. This is a missing-input constraint, not a new request for permission to carry out the already requested experiment.

## Run this first on IRIDIS

The maintained downloader below fetches exactly three small files (the audit and its two CSVs), checks their embedded SHA256 values, and runs both self-test and inventory. It uses raw GitHub downloads; a cluster `git pull` is unnecessary.

**25 October checksum fix:** the initial launcher hashed the local site CSV with CRLF line endings, while the published Git blob contains LF. Only that CSV checksum was wrong. The corrected launcher checks the actual published bytes (`28606b0a5899e1b4fc7a75a57cdfc927e3b21a93af7289f523d5983a32eb7841`) and pins its three dependencies to input revision `6a355eaf8c9f055eeacd8f9d110b54c71850492e`. The dependency revision is correct; the launcher itself must be downloaded from the newer fix commit or current `main`. A checksum failure occurs before any checkout input is installed or any audit/model action runs. Source data contents are unchanged.

```bash
conda activate clm_fates_env
curl -fLsS \
  https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/main/examples/Batch02_10/scripts/00_download_and_audit.sh \
  -o "$HOME/ICOS_Batch02_download_and_audit.sh" || exit 1
bash "$HOME/ICOS_Batch02_download_and_audit.sh"
```

The default source-code checkout is `$HOME/Non-Competition-CLM-experiment`. Set `B02_REPO_DIR` only if the checkout is elsewhere. The launcher prints `REPORT_JSON=.../all_sites.json`, `REPORT_CSV=.../summary.csv`, and `CONSOLE_LOG=...`. Reports get a new timestamped HOME directory; original model files are opened read-only. Only the three maintained source-code files and new reports are written.

To run already downloaded code:

```bash
cd "$HOME/Non-Competition-CLM-experiment" || exit 1
python3 -B examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py self-test || exit 1
python3 -B examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py audit
```

The report contains all matching original source cases, generated `fsurdat`, actual FATES parameter path and HLM map when readable, full small point soil/PFT arrays, XML start/CO₂/forcing metadata, executable fingerprint when small enough, Slurm resource directives, and actual DATM stream document paths/checksums/excerpts. It does not choose the newest case automatically. In particular, inspect IT-Noe's repaired/ERA5 branch and ES-LJu's corrected forcing branch instead of choosing an obsolete case by filename.

**Audit limits:** no annual/hourly meteorological revalidation; static XML values are expanded without executing CIME and conditional defaults remain unverified. Missing numpy/netCDF4 or unreadable NetCDFs are explicit `read_error` records, not a successful PFT/soil check. `AUDIT COMPLETED` means the report was generated; it is **not** a model-readiness PASS. Source-grid crop or PFT fractions are recorded as model provenance, not tower observations. Soil follows [observed first, documented grid fallback if none](../../docs/observed_soil_texture_policy.md); no fallback or measured-soil replacement is selected by this inventory.

## Same operational method as Batch01

| Step | Mode | Model years | Submit policy / required evidence |
| --- | --- | ---: | --- |
| Source and scientific inputs | Read-only inventory; choose PFT, landunits, soil and active mapping | 0 | This example's current executable step |
| New isolated surface + AD case | FIXNC; cold start; `CLM_ACCELERATED_SPINUP=on`; generated `spinup_state=2` | 0 | Adapt successful Batch01 private overlay; preserve original/shared files |
| First AD segment | AD | 5 | `STOP_N=REST_N=5`, `RESUBMIT=0` |
| AD continuation | AD | 395 | Verify exact run/archive `COMPLETED 0:0`, CLM/DATM/CPL AD5 restarts and state2; then 79 segments, `RESUBMIT=78` |
| Separate Normal case | Hybrid from final AD400 checkpoint; `CLM_ACCELERATED_SPINUP=off` | 0 | Exact Y+400 restart triplet and state2; own case/run/archive |
| First Normal segment | Normal | 5 | `RESUBMIT=0`; generated normal namelist; resulting restart state0 |
| Normal continuation | Normal | 395 | Verify exact Normal5 run/archive and restarts; then 79 segments, `RESUBMIT=78` |

Total per site: **5+395 AD, then 5+395 Normal = 800 model years**. For each site's actual start year Y, phase targets are Y+400 and Y+800; forcing years remain each station's own recycled, documented stream. There is no Normal50 preparation. AD400/Normal400 duration does not certify carbon equilibrium.

Proposed **new** case names: `<site>_B02_FIXNC_AD400` and `<site>_B02_FIXNC_NORMAL400`, with independent output roots. These are future names, not claims that cases already exist. Validate actual fixed-biogeography/no-competition flags and the parameter file used by the executable. For shrub/grass sites, verify the active HLM→FATES mapping before making any new surface.

Reuse the **method**, not unedited site-specific code:

- [Batch01 Stage11 surface/AD smoke controller](../Batch01_10/scripts/11_batch10_AD400_oneclick.py): forest-only inputs and Batch01 paths; **do not run for Batch02**.
- [Batch01 Stage12 private overlay](../Batch01_10/scripts/12_batch10_recover_FATES_AD_private_overlay.py): successful pinned two-change FATES AD namelist workaround. Use only after confirming the same CTSM source blob `698f2396aba8e11cbbbdd58c74ad221e6b7e7038`; never edit shared CTSM.
- [Batch01 Stage13 AD395](../Batch01_10/scripts/13_batch10_continue_verified_AD395.py): reuse archive/mode/duplicate-submit gates, but **never its hardcoded Batch01 job IDs**. Batch02 IDs must come from its own submission receipts.
- [DE-Tha independent AD→Normal hybrid example](../DE-Tha/scripts/14_AD_to_Normal_independent_branch.py): proven transition method; its dates/paths/hashes are DE-Tha-specific. Normal must not inherit explicit AD `spinup_state=2` in `user_nl_clm`.

See [the common protocol](../../docs/AD400_NORMAL400_PROTOCOL.md) for scientific criteria and continuation details. Original Batch01 status documents remain historical records. The operator's report that the prior run finished is not used here to infer which archived AD/Normal checkpoints exist; this update does not inspect the remote HPC filesystem or certify that completion.
