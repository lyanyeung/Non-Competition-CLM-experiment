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

## Actual operator Stage00–01: new AU-Gin 2011–2025 source verified (2026-11-04)

IRIDIS WSL->remote transfer **PASS**, exact source `TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip`, 127,239,943 bytes; source ZIP SHA256 **`acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14`**; `Gingin_L6.nc` remained untouched. Operator transfer receipt: `/home/ly3n24/ozflux_AU_Gin_TERN_2011_2025_stage00_sha256.txt` in WSL.

**Actual Stage01 ZIP inventory/source-time audit PASS**, IRIDIS report `/home/ly3n24/ozflux_AU_Gin_stage01_20261104T053930Z`. The unique native `TERN_AU-Gin_FLUXNET_FLUXMET_HH_2011-2025_v1.3_r1.csv` has **262,992** HH rows from `TIMESTAMP_START=2011-01-01 00:00` through `2025-12-31 23:30`; precise total 15 calendar years **including 2012, 2016, 2020, 2024 leap days**; annual 17,520/17,568 standard/leap rows and **0 non-30-minute time steps**. Contains 221 columns; seven forcing met columns `TA_F,VPD_F,SW_IN_F,LW_IN_F,PA_F,P_F,WS_F`, original raw `P,PA,WS`, and `*_ERA` with `*_F_QC`; a separate original `ERA5_HH_1981-2025` file and `BIF`, `BIFVARINFO_HH` files are present. Stage01 printed `MISSING_MET_FIELD_STRINGS {}`, which only means its limited exact sentinel-string test found none; **does NOT mean no missing values and DOES NOT prove 2011 early original tower measurement**. There is no source-level science approval, DATM conversion or AD400.

**Source-identity caveat:** official OzFlux AU-Gin information states that Gingin flux station was *established in June 2011* <https://www.ozflux.org.au/monitoringsites/gingin/index.html>. The 2011-01-01 FLUXMET source timeline may contain ERA-/MDS-filled values before site operation. User's >=15 calendar-year criterion can only be evaluated after 2011 early QC0 and metadata provenance review; original ecological/meteorological availability remains a separate scientific requirement. Do NOT call the whole 15-year window 15 years of true observed meteorology merely because 262,992 HH rows exist.

Official FLUXNET variable codebook: <https://fluxnet.org/data/fluxnet2015-dataset/fullset-data-product/> and <https://fluxnet.org/data/fluxnet2015-dataset/variables-quick-start-guide/>. At HH, consolidated `TA_F_QC,VPD_F_QC,SW_IN_F_QC,LW_IN_F_QC` normally encode **0=measured,1=high-quality gapfill,2=downscaled ERA**; `PA_F_QC,P_F_QC,WS_F_QC` normally **0=measured,2=downscaled ERA**. `*_F_QC` on DD or YY have fraction semantics and must NOT be interpreted as half-hour classes.

**Stage02 prepared; real IRIDIS execution pending:** `scripts/02_au_gin_FLUXNET_15yr_QC0_ERA_source_audit_READONLY.py`, commit `28170ce7c81e74a598349879797cf149f2c5faf9`, blob `3b2224be7cf56c08622c2ccc2983af4c2af15026`. Pins actual 127 MB ZIP SHA and operator Stage01 receipt. Streams all source half-hours (no extraction); validates START/END 30min steps, annual/monthly 7 MET variables consolidated F numerical validity and QC0/QC1/QC2/other/missing counts; 2011 Jan–May observed class and first QC0 date per field; longest non-QC0/ERA/missing spells, F-versus-packaged-ERA QC0 fit metrics **not independent fit validation**, conservative physical range screens, and source BIF/BIFVARINFO provenance excerpts. Writes only new HOME TSV/JSON; no original source, old L6, Surface, CIME, Slurm changes. If early 2011 is all QC2, the full 15-year source clock is not a 15-year tower met observation record. Next Stage03 will verify actual BIF source instrument height/location and native UTC/time semantics before any candidate forcing.

**AU-ASM/AU-DaS remain separate HOLD**. Other OzFlux case/physics work is not included in this new AU-Gin ZIP source audit.

## Actual Stage02 failure and byte-safe Stage02v2 fix (2026-11-04)

The operator ran source SHA-verified Stage02, syntax and selftest PASS, but the **real-data run halted BEFORE the HH source analysis** in `bif_samples(z)` at a BIF metadata member: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb5 in position 1009`. This is a metadata **encoding mismatch**, not evidence that the meteorological time series or ZIP is corrupted. Because the exception occurred while parsing BIF before the HH loop, **there is no Stage02 annual/monthly QC result yet**. The old source bytes and former Stage02 remain untouched.

**Fix:** new `scripts/02v2_au_gin_FLUXNET_15yr_QC0_ERA_BIF_encoding_READONLY.py`, Git commit `d3dc846241b5104528adcb4ae81f59018bcdd909`, blob SHA `e1048729d561187e93c1cc352333d2b1672b2701`. Decode BIF metadata from bounded original member bytes, strict UTF-8-SIG preferred; on invalid byte, strict CP1252; for undefined CP1252 bytes, Latin-1 one-to-one; **never `errors=replace`/ignore**. Record the original uncompressed BIF member SHA256, exact byte count, inferred decoder, non-ASCII byte count and decoding warning in final science receipt. Its `--self-test` includes a synthetic ZIP BIF CSV containing real `0xB5` and verifies SHA and µ decoding. `FLUXMET_HH` original CSV continues strict UTF-8-SIG and unchanged scientific computation; raw ZIP SHA pinned `acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14` and Stage01 receipt pinned. Because inferred BIF text encoding is not an original official encoding declaration, preserve these decoding provenance diagnostics as **interpretive metadata**, not independent scientific validation.

**Next:** operator reruns with an unused output folder using Stage02v2 and reports the original first/last QC0 timestamps, 2011 Jan–May QC0/ERA2, each year QC0/MDS/ERA, and longest non-QC0 spells. Confirm 15 *original observed years* separately from a 15-year continuous processed time grid before AD400. NO source writes, no DATM or Slurm.
