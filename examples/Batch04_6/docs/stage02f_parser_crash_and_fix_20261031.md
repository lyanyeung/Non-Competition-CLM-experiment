# ICOS Batch04 Stage02F first attempt — parser crash and source fix (31 October 2026)

## Operator evidence

Source checksum and `STAGE02F SELF-TEST PASS: water/ice saturation, HH event ledger schema; no files written` were reported from the original Stage02F script at GitHub merge commit `ebf7148a300e400946ba4fab2ad785f801b89b84`, blob SHA `eb01dcea690b272f38a5a4ffb03af8a404c01907`. However, the full Stage02F run on IRIDIS6 failed **before any NetCDF could be opened**:

```text
File ".../02f_CH_Aws.py", line 291, in main
    groups, reference = parse_input(source)
File ".../02f_CH_Aws.py", line 42, in parse_input
    data = json.loads(path.read_text(encoding="utf-8"))
AttributeError: 'dict' object has no attribute 'read_text'
```

Observed failed execution directory: `/home/ly3n24/ICOS_Batch04_stage02f_1FaFC3r0/`. The calling `main()` had already loaded Stage02C JSON into a Python dictionary; `parse_input` wrongly treated it as a `Path`. The error was **code logic**, not evidence of invalid humidity data, corrupt NetCDF, a failed model or a conda environment issue.

**Scientific status:** Stage02F saturation/changed-half-hour outputs **NOT PRODUCED** on this attempt. No RH or VPD results may be inferred from the traceback. Stage02D/E results remain unchanged; no forcing, surface, CIME, Slurm or original Git working tree modifications are implied by this failure.

## Fix and prevention

The corrected `02f_CH_Aws_QBOT_saturation_and_event_ledger_readonly.py` takes the already decoded dictionary in `parse_input(data)`. Its `--self-test` now constructs an **in-memory synthetic Stage02C report** with exactly eight original-like case entries, seven distinct 19-year annual path sets, calls `parse_input(fake_json)`, checks reference map coverage, and rejects a `Path` as an argument. The synthetic input test **does not access real scientific data**.

Follow-up on IRIDIS6: download the new immutable source SHA into a fresh HOME audit directory, verify the exact git blob hash, run `--self-test`, and then run the full Stage02F only with activated `clm_fates_env`. Set `--out-dir` to a **fresh existing empty directory**, not the failed run's directory. Do not edit existing forcing files, submit Slurm or run `git pull`.

Keep CH-Aws **HOLD_NATIVE_TOWER_RH_TA_QC_AND_ERA_PROVENANCE** and all original six-site Batch04 scientific gates on HOLD, even if the corrected Stage02F run successfully produces diagnostic output.
