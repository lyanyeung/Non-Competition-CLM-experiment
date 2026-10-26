# Batch04: retain FIXNC only; stop all unwanted FULL chains

Operator correction on 26 October 2026: FULL (dynamic biogeography and
competition) is unwanted. Stop all ten Batch04 FULL cases, including
current model and dependent archive jobs and future automatic resubmits.
Retain the ten already submitted FIXNC cases with prescribed PFTs.

The controller now accepts only `--arms FIXNC`, defaults to FIXNC, and
refuses FULL in the preparation/submission functions before filesystem or
scheduler access. The downloader also passes `--arms FIXNC` explicitly.
New plans contain ten FIXNC entries; no new FULL arm is constructed.
The fixed settings are `use_fates_fixed_biogeog=.true.` and
`use_fates_nocomp=.true.`, with the site-recommended PFT composition.

## Cancel and verify

Use `scripts/07_stop_FULL_keep_FIXNC.py --apply` on IRIDIS. It reads the
current user's queue and selects exact `run.<case>`,
`st_archive.<case>` or bare case names for the ten cases
`SITE_AMF_B04_FULL_AD400_BASETA_V1` only. All currently selected FULL job
IDs are cancelled in a single scancel call, every existing named FULL
case gets `RESUBMIT=0`, and a second queue sweep cancels any chained job
submitted during the operation. It does not rely on the initial job IDs.

No FIXNC case XML, submission ledger, queued job or model output is
changed/deleted. The tool records its FULL cancellation requests under
`AmeriFlux_Batch04_10/FULL_cancellation_records`.

Run the same tool with `--check` for a read-only confirmation. PASS is
`FULL_STOPPED_FIXNC_PRESERVED`: no FULL job remains in the current queue
and each existing FULL case has `RESUBMIT=0`. A `COMPLETING` job is still
reported as remaining; cancellation requested is not called stopped.
Slurm filtering/cancellation follows the [official scancel documentation](https://slurm.schedmd.com/scancel.html).

**Actual cancellation is not yet verified from operator output.** The
provided output proves the initial twenty submissions, not their later
run state. Run the cancellation on the cluster and inspect the final
queue/receipt. Do not rerun the original 044e5166 `--all` command.

## Retained initial FIXNC submissions

| Site | First run job | First archive job |
|---|---:|---:|
| US-Rpf | 4741196 | 4741197 |
| US-SP1 | 4741204 | 4741205 |
| US-SRG | 4741209 | 4741210 |
| US-SRM | 4741215 | 4741216 |
| US-Seg | 4741219 | 4741220 |
| US-Ses | 4741223 | 4741224 |
| US-Slt | 4741227 | 4741228 |
| US-Syv | 4741231 | 4741232 |
| US-Ton | 4741235 | 4741236 |
| US-Uaf | 4741239 | 4741240 |

These are initial segment IDs; later automatic segments have new IDs.
The existing 207 validated annual forcing files and selected BASE TA
proxy height policies are reused. Do not rebuild inputs or resubmit
FIXNC simply to cancel FULL. Direct AD400 remains 80 x 5 years with 79
automatic resubmissions for each retained FIXNC case, not an AD5 pilot.
