# AmeriFlux Batch04: FIXNC only, direct AD400

**Current operator instruction, 26 October 2026: run only prescribed-PFT,
fixed-biogeography/no-competition FATES. Stop all Batch04 FULL cases.**
The previous paired Full/FIXNC rollout is withdrawn. The ten already
submitted FIXNC cases are retained; do not recreate or resubmit them.

## Retained experiment

- Sites: US-Rpf, US-SP1, US-SRG, US-SRM, US-Seg, US-Ses, US-Slt, US-Syv,
  US-Ton and US-Uaf; ten FIXNC cases, no FULL arm.
- `use_fates=.true.`, `use_fates_sp=.false.`,
  `use_fates_fixed_biogeog=.true.`, `use_fates_nocomp=.true.`.
- The [original ten-site PFT snapshot](data/AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv)
  supplies the recommended fractions, including explicit bare ground.
  Uaf uses a private ARCTIC_PURE parameter map. Forward mapping from the
  actual surface to FATES percentages is checked.
- AD400 starts in one submission: 80 five-year CIME segments,
  `STOP_N=5`, `REST_N=5`, `RESUBMIT=79`, `spinup_state=2` and automatic
  continuation/archive. No independent AD5 test or manual AD395 handoff.
- Normal400 follows complete AD400 verification; it is not started by
  this release.

## Stop the unwanted FULL chains

Run [07_stop_FULL_keep_FIXNC.py](scripts/07_stop_FULL_keep_FIXNC.py) with
`--apply` on IRIDIS, then `--check`. It selects only the ten exact Batch04
FULL case names in the current user's queue, cancels their current model
and archive jobs in a batch, sets their `RESUBMIT=0`, and sweeps for any
new chained job IDs. It does not cancel FIXNC jobs or delete model output.

Cancellation is confirmed only by `FULL_STOPPED_FIXNC_PRESERVED`: an empty
FULL queue and disabled automatic resubmissions in existing FULL cases.
The initial twenty submissions are confirmed by operator output; actual
FULL cancellation is awaiting the operator's queue output.
[Cancellation details and retained FIXNC initial job IDs](docs/FIXNC_ONLY_STOP_FULL_20261026.md).

## Reuse the verified inputs

The operator generated and independently verified **207 annual UTC,
NOLEAP NetCDF files for all ten sites**, with exact original met/surface
SHA checks, all fields/timesteps/units checked, and documented TA proxies.
The verified manifest is:

```text
/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10/DATM_UTC_NOLEAP_direct400/candidate_20261026T175820Z_29121/B04_UTC_NOLEAP_DATM_MANIFEST.json
```

The [height policy](data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json)
uses the same exact BASE measurement-height snapshot as Batch01. All ten
TA_F crosswalks remain explicitly unverified proxies. US-Rpf retains the
dated 2.3m to 4m change. No canopy or WS height is substituted for TA.
The [CO2 policy](data/AMF_BATCH04_CO2_POLICY_20261026.json) uses initial
forcing-year NOAA global annual means as fixed backgrounds, as Batch01.
Original gridded soil depth layers remain documented fallbacks, not
invented ten-layer station observations from 0-30cm summaries.
[Full source/protocol details](docs/DIRECT_AD400_BASE_TA_PROXY_20261026.md).

## Controller behavior

[05_prepare_and_submit_direct_AD400.py](scripts/05_prepare_and_submit_direct_AD400.py)
defaults to FIXNC and accepts only `--arms FIXNC`. FULL preparation and
submission are also rejected at function entry, before filesystem or
scheduler operations. [06_fetch_direct_AD400.sh](scripts/06_fetch_direct_AD400.sh)
explicitly passes FIXNC for preparation, verification and submission.
Do not rerun the old 044e5166 `--all` command on these submitted cases.

The live submitter imports the Batch01 stack guard in the same Python
process immediately before each initial `case.submit`, raises only a low
soft stack, never lowers higher/unlimited limits, and verifies Slurm
STACK/ALL propagation. The operator's initial submissions all passed with
unlimited stack and `PropagateResourceLimits=ALL`. No compiler stack
protection is disabled. Exclusive attempt ledgers prevent duplicate
initial submissions.

`status` and `audit-ad400` now default to the retained ten FIXNC cases.
Audit requires all 80 restart/archive sets, final `spinup_state=2`,
exhausted automatic resubmissions and 80 completed model plus 80 archive
jobs. Submission success is not AD400 completion.

Local validation covers real NetCDF round trips, UTC/leap/dynamic-height
conversion, FIXNC runtime geometry and inputs, FULL rejection, Slurm stack
failure, duplicate submission protection, exact cancellation selection,
late chained job IDs and read-only cancellation verification.
