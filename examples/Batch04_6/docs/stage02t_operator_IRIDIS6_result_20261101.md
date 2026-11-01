# ICOS Batch04 CH-Aws Stage02T — original distributed ERA5 source not found in bounded roots (2026-11-01)

**Operator-reported, source-verified IRIDIS6 completion.** Stage02T original Git blob integrity and self-test passed. No source file, forcing NC, case, model parameter, Git worktree or Slurm changes were made.

| Search scope | Filenames visited | Matching candidate paths | Truncated |
|---|---:|---:|---|
| `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws` | 169 | 0 | False |
| `/iridisfs/home/ly3n24/FLUXNET_MultiSite_11` | 252 | 0 | False |

- `EXACT_CSV_FOUND False`
- `EXACT_ZIP_MEMBER_FOUND False`
- Original Stage03-registered expected `EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv` is **not found within these two explicitly limited scan roots/depths**. This does not mean that ERA climate data are absent: processed distributed FLUXMET_HH contains `VPD_ERA` and `TA_ERA`, and older Open-Meteo ERA5/Land JSON snapshots exist. Nor is it evidence that the exact original ERA5 file cannot be recovered from the official product archive, other disks or external institution.
- Stage02S originally scanned 0 source rows, produced 0 clock comparisons; these are **input-provenance blockers**, not new meteorological anomalies.

Existing private output:
- `/home/ly3n24/ICOS_Batch04_stage02t_gcQp60r6/results/stage02t_CH_Aws_ERA5_original_source_location.json`
- `/home/ly3n24/ICOS_Batch04_stage02t_gcQp60r6/results/stage02t_CH_Aws_archive_source_candidates.csv`
- `/home/ly3n24/ICOS_Batch04_stage02t_gcQp60r6/stage02t_console.log`

## Decision

Preserve **CH-Aws science HOLD** and its unchanged source/cases. At the 20 preselected high-QBOT-difference events, processed gapfilled `VPD_F_QC=1` implies RH <10%, whereas related ERA5 and ERA5-Land RH differ by >=50 percentage points; independent sensor RH/QC has not been established, and Stage34/38/42 alternatives explicitly remain EXPLORATORY. No automatic selection of RH34A/38A/42A, no source replacement, no AD5/AD400 submission. Do not repeatedly rerun these completed QC and source-file scans.

**Practical next action:** advance **DE-Gri, DE-RuR, IT-Tor and ES-Agu** using the previously verified 74-file all-year Stage02D internal DATM screen, followed by isolated read-only effective-input/soil/surface/PFT configuration comparison and source-QC provenance. GL-ZaH is separate and retains its mandatory site-only Arctic FATES map. For CH-Aws, acquisition of original station raw RH/QC or exact distributed EUF ERA5 source archive is a separate externally dependent scientific task and should not block the other four.
