# Batch04 CH-Aws Stage02Q — BIF metadata >5000-row bounded-reader bug and correction (2026-11-01)

## Actual IRIDIS6 failure

Operator verified the original pinned Stage02Q source blob and reported:
```
SOURCE VERIFIED
STAGE02Q SELF-TEST PASS: 20 science HOLD events ...
Traceback ... main() -> describe_metadata(...) -> read_csv(...)
ValueError: Unexpected >5000-row bounded metadata file
```

This is **a software scanner limit**, not a scientific observation, corrupt-data flag, source SHA failure, or model failure. The original Stage02Q shared a hard `MAX_META_ROWS=5000` read-all CSV routine across large distributed **BIF/BIFVARINFO** source metadata and small Stage21/25 revision ledgers. One of the BIF sources exceeded 5000 rows; the original traceback does not identify which source, and neither Stage21/25 time matching nor HOME filename discovery was reached. The old failed execution produced **no Stage02Q output JSON/CSV** (the code writes only after the entire audit).

## Fixed Stage02Q, same experiment, no source edits

Corrected `02q_CH_Aws_original_BIF_localtime_and_native_source_search_readonly.py`:
- BIF and BIFVARINFO now use a **streaming** CSV metadata reader with a true per-file **100,000-row upper guard** and the existing **2 MB file-size guard**, preserving total and relevant row counts but no full table in memory.
- Original Stage21 and Stage25 ledger CSVs continue to use a separate strict bounded reader (up to **25,000 rows**), preserving exact original row numbers, raw `time_local_standard_UTCplus1` labels and ±30/60-minute *hypothesis* alignment.
- A deterministic source metadata sampler retains up to ten examples per topic `RH, VPD, TIME, QC, INSTRUMENT, TA_PA, OTHER`, with separate keyword-topic counts and explicit source/QC status HOLD. The terminal prints these topics independently rather than allowing late VPD/RH lines to be obscured by generic BIF rows.
- Expanded `--self-test` covers **6,003 synthetic BIF metadata rows**, including RH/VPD samples appearing beyond row 5,000; requires streaming complete and retention of late important entries.
- No modification to original source metadata, native tower files, annual DATM NetCDF, CIME cases, Git working tree or Slurm. Still only outputs a new JSON and CSV under a standalone **new EMPTY HOME directory**.
- No automatic 1-hour time conversion; no ERA or model-forcing selection or AD5/AD400 authorization.

Re-run with the **new immutable merge-commit and Git blob SHA** rather than modifying or rerunning the old verified code in place. Use the same saved Stage02P/Stage02O source reports:

```bash
P="$HOME/ICOS_Batch04_stage02p_D6TUjQg7/results/stage02p_CH_Aws_native_source_availability.json"
O="$HOME/ICOS_Batch04_stage02o_hLF8GLFP/results/stage02o_CH_Aws_20_event_risk_triage.json"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --stage02p "$P" --stage02o "$O" --extra-root "$HOME" --out-dir "$NEW_EMPTY_DIR"
```

Check `METADATA ... ROWS ... TOPICS ... COMPLETE True`, `LEDGER STAGE21/STAGE25`, `TIME_CANDIDATE`, `EXTERNAL_FILENAME_SEARCH` and the final two artifact paths. Until the full operator audit succeeds, science status is **HOLD**.
