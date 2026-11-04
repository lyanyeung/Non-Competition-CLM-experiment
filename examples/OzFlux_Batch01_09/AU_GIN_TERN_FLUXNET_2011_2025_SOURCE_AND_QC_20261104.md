# AU-Gin — new TERN FLUXNET 2011–2025 source selection and safe transfer

**Operator source selection, 2026-11-04:** prioritise newly available `TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip`, located on their own Windows machine at `D:\Fluxes_Tower_Experiment\Ozflux\AU-Gin\TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip`, over older AU-Gin `Gingin_L6.nc` **for further science QC**, **not for instant forcing, repair, or AD400 model approval**. AU-ASM and AU-DaS are on HOLD; separate AU-Dry work may proceed later but AU-Gin new source is currently prioritised.

## Official existence and eligibility warning

FLUXNET data explorer lists **AU-Gin 2011–2025 inclusive = 15 calendar year labels** (<https://www.keenangroup.info/fluxnet-data-explorer/>). Original OzFlux station description gives established **June 2011** (<https://www.ozflux.org.au/monitoringsites/gingin/index.html>). If 2025-12-31 is last observation and first actual station records start 2011-06, elapsed continuous duration is only about **14.5 years**, less than a strict **>=15 elapsed years** study threshold. **15 calendar labels != 15 full elapsed years**. Do not assume this new archive clears the 15-year eligibility gate; inspect actual file header/time axis, missingness, source hourly/half-hourly coverage, per-variable QC and land-use/canopy changes. The existing older `Gingin_L6.nc` has ~16 file-year rows but **0 strictly complete forcing-structure candidates in Stage07**, which is a MET completeness/QC issue, not evidence the original observation period is necessarily too short. Don't automatically force new product over old or combine periods.

New-style `v1.3_r1` FLUXNET pack resembles late 2025+ ONEFlux updates with `FLUXMET_HH`, `METEO`, metadata files as present; **only actual ZIP inventory may establish actual members**. See AmeriFlux revised product notes <https://ameriflux.lbl.gov/resource/details-for-improved-ameriflux-fluxnet/>. Official AU-Gin FLUXNET site <https://fluxnet.org/sites/siteinfo/AU-Gin>.

## Exact separate files

Windows/WSL immutable source:
`/mnt/d/Fluxes_Tower_Experiment/Ozflux/AU-Gin/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip`.

Dedicated IRIDIS6 original archive:
`/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip`.

**Never overwrite** `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc` or existing model cases.

Stage00 SHA-verified Windows WSL → IRIDIS upload:
`scripts/00_au_gin_tern_FLUXNET_2011_2025_WSL_UPLOAD_SHA256.sh` at commit `537abbf31ae88ec916e7d39516edb74292ebf951`, blob `99f7ab896189b22402a5e1715350e9f2ddfb08dc`. First use `--preflight-only`; then run again with no flag; existing target is read-only hash-checked; sha mismatch fails closed. Saved local receipt under WSL `$HOME/ozflux_AU_Gin_TERN_2011_2025_stage00_sha256.txt`.

Stage01 read-only ZIP source/member/year-audit:
`scripts/01_au_gin_tern_zip_native_HH_source_audit_READONLY.py` at commit `688c4e47ed6cee110fb1c4ab6904b40d3d7b8b8a`, blob `7b629bf262d91291979970fe0637a286f5a72496`. Requires actual **local WSL-source SHA256** passed as `--expected-sha`, must match uploaded remote ZIP bytes; it checks archive member names for traversal/duplicate, CSV variable names, unique `FLUXMET_HH` candidate if present, native start/last labels, 2011–2025 row count, missing strings and non-30-minute native intervals. It does not extract or modify the ZIP; existing `Gingin_L6.nc` is verified present and hashed (read only); report is a unique new `$HOME/ozflux_AU_Gin_stage01_...` folder. Optional `--full-crc` reads every compressed member, may take longer; use after light source inventory. If `FLUXMET_HH` absent, no assumption of equivalent CSV, continue with schema-specific Stage02.

## Next science QC after upload

1. Verify actual first and last HH native timestamps and exact 15-year eligibility standard (calendar years vs elapsed time; do not fake).
2. Inspect tower versus gapfilled fields `TA_F`, `VPD_F`, `PA_F`, `P_F`, `SW_IN_F`, `LW_IN_F`, `WS_F` with quality flags and original variable-metadata descriptions. Confirm local versus UTC label and interval convention.
3. Cross-compare new FLUXMET source and older OzFlux L6 on genuinely comparable source-clock times; no automatic mixing of release processing/QC codes or blind donor substitutions.
4. Repeat NOAA/BoM regional corroboration only for real outliers, matched actual station identity/location and time. ACCESS/ERA must not be treated as independent if shared source.
5. Release science-gated forcing only after the research duration/land cover/meteorological QC criteria pass. No Slurm AD400 or Normal400 submission in Stage00/01.

**Neither Stage00 nor Stage01 has been run on the operator's actual Windows/IRIDIS system yet.** No checksum for the new operator-owned ZIP is known prior to WSL preflight.
