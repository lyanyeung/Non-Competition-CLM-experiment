# ICOS Batch04 CH-Aws — actual Stage02S missing original EUF ERA5 source (2026-11-01)

**Operator-provided IRIDIS6 result:** `SOURCE VERIFIED`, `STAGE02S SELF-TEST PASS`, full read-only command completed (no source or CIME/Slurm changes).

Stage03 originally registered the separate distributed ERA-input file:
```
/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing/raw/EUF_CH-Aws_FLUXNET_2006-2024_v1.3_r2/EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv
```
Stage02S reported **`DISTRIBUTED_ERA5_INPUT MISSING_ORIGINAL_DISTRIBUTED_ERA5_HH_INPUT`**, `SOURCE_HOLD`, `ROWS_SCANNED 0`, `COMPARISONS 0`.

- Original output: `/home/ly3n24/ICOS_Batch04_stage02s_krFdN4ko/results/stage02s_CH_Aws_original_EUF_ERA_time_comparison.json`
- Comparison CSV (no data rows): `/home/ly3n24/ICOS_Batch04_stage02s_krFdN4ko/results/stage02s_CH_Aws_ERA5_FLUXMET_two_clock_offsets.csv`
- Log: `/home/ly3n24/ICOS_Batch04_stage02s_krFdN4ko/stage02s_console.log`

The **file at the exact legacy path** is missing. This does **not** prove that ERA5 forcing is generally absent: the existing EUF FLUXMET_HH contains `TA_ERA` and `VPD_ERA` at the 20 reviewed event rows, and earlier Open-Meteo historical archive JSONs are also present in HOME. Those are **processed or related ERA products**, not independent sensor RH/QC truth. The missing separate original ERA5_HH file prevented the exact cross-product clock comparison intended by Stage02S and must not be silently bypassed by substituting other products, renaming a file, reconstructing a new source CSV, or claiming timing was verified.

The previous Stage02R audit independently confirmed BIF `UTC_OFFSET=1` and its original `VPD_F_QC=1` gapfill semantics, while Stage09 correlated ERA5 meteorology with an exploratory 0-hour shift more strongly than +1 hour. These conventions are not automatically interchangeable.

## Next: bounded Stage02T original source package discovery

[Stage02T source-archive checker](../scripts/02t_CH_Aws_missing_EUF_ERA_source_archive_readonly.py) reads saved Stage02S and Stage02R JSONs, requires the exact missing-source status and original Stage03 file pin, then scans **only the CH-Aws original site tree and `$HOME/FLUXNET_MultiSite_11`** for plausible original ERA5_HH CSV and ZIP archives. ZIP central directory is inspected for `EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv` or similar candidate members: no data extraction, file modification or download. There is a bounded traversal depth (6), 25,000 files/root, 350 candidate files/root, and 50 ZIPs/root, with explicit truncation flags; a missing candidate in these limits is not proof of absence elsewhere. Archive CRC/name or matching pathname alone is not a source SHA/instrument QC certification.

If the exact original EUF input (or archive member) is recovered later, only *then* perform checksummed, source-pinned and separately approved time/QC comparison. Otherwise CH-Aws remains science HOLD; it can be paused while the four less-complex Batch04 sites DE-Gri, DE-RuR, IT-Tor and ES-Agu undergo independent original forcing/PFT/soil effective-input audits. GL-ZaH also retains private Arctic FATES map requirements.

### Scientific status

- No new ERA5 scientific result from Stage02S.
- No source/clock/tower RH observation QC validated.
- No RH34A/38A/42A repair selected; all exploratory.
- No AD5/AD400/Slurm submission.
