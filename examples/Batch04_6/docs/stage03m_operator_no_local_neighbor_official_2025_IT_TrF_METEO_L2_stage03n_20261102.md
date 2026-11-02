# ICOS Batch04 — Stage03M actual 0 local IT-TrF folders; verified official 2025 Meteo L2 alternative (2026-11-02)

## Actual Stage03M run

Operator's Stage03M script passed original source SHA, Python syntax and synthetic self-test, and completed exact Stage03L top-three priority source event inventory:

| IT-Tor original source-label interval | QC1 MDS HH | MDS < packaged ERA minus 5°C | MDS < packaged ERA minus 10°C |
|---|---:|---:|---:|
| 2025-11-15 17:00 to 2025-11-18 07:00 | 125 | 107 | 67 |
| 2025-11-13 17:30 to 2025-11-14 07:00 | 28 | 28 | 28 |
| 2025-11-13 14:30 to 2025-11-13 15:30 | 3 | 3 | 3 |
| **Total** | **156** | **138** | **98** |

`IT_TRF_CANDIDATES 0` **AND** `TARGET_DIRECTORIES_SHALLOW_SCANNED 0` means the preconfigured IT-TrF station-specific directories were **not present/readable**, not that all scratch storage or external ICOS was searched. The script did not claim the site lacked actual 2025 measurements. No original IT-Tor source or selected forcing was modified.

Private result:
```
/home/ly3n24/ICOS_Batch04_stage03m_lMcbRkGG/results/stage03m_IT_Tor_top3_neighbor_independent_source_inventory_PRIVATE.json
```

## External official source verified after operator's Stage03M result

The correct next product to source is **ICOS ETC L2 Meteo from Torgnon-LD (IT-TrF)**, not another filled meteorological product. Official authoritative metadata:

- [ICOS ETC L2 Meteo from Torgnon-LD, 2011-12-31–2025-12-31](https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl)
- Filename: **`ICOSETC_IT-TrF_METEO_L2.zip`**
- File size: **16,713,915 bytes**; SHA-256 **`9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f`**
- PID: **`11676/mwN98ExGR4uPnaUKi5mWoISl`**; 245,472 metadata rows; published 2026-04-01, acquisition ends 2025-12-31
- Includes **`TA`**, `RH`, **`TIMESTAMP` = UTC** and **`TIMESTAMP_END` = site local NON-DST**. Note half-hour interval start/end may contribute an extra 30-minute offset; verify against the actual product time columns before joining.
- Product description: one aggregated meteorological TA value calculated from underlying station sensor half-hour measurements, unlike gap-filled **`TA_F`** from ONEFlux FLUXMET. A missing-value/quality flag and specific height still need to be inspected, not assumed.
- Licence: **ICOS CC BY 4.0**, and the official download uses an explicit acceptance page. Operator should access the linked source in their browser, read and accept the licence themselves, save ZIP, and transfer ZIP to their private IRIDIS6 HOME directory. No software tool should bypass or accept the licence on the operator's behalf.
- Alternative [ICOS L2 Fluxnet 2012–2025 (100 MB)](https://meta.icos-cp.eu/objects/EUCf30NjOFzu2N1by918KJPF) includes `TA_F/TA_F_QC` but is a **gapfill composite**, less primary for independent observed temperature than ETC L2 Meteo `TA`.
- Official [IT-TrF Torgnon-LD station](https://meta.icos-cp.eu/resources/stations/ES_IT-TrF) is a 2,100-m larch forest, **distinct from IT-Tor** open alpine grassland about 2,168 m, with different microclimate/measurement height.

Proper data citation: *Galvagno, M., Ferraris, D., Filippa, G. (2026). ETC L2 Meteo from Torgnon-LD, 2011-12-31–2025-12-31, ICOS RI, https://hdl.handle.net/11676/mwN98ExGR4uPnaUKi5mWoISl.* Source metadata and exact licence link should accompany scientific derivatives.

## Stage03N: source-verified ZIP and time-field preflight ONLY

[Stage03N exact official ZIP source-hash + targeted 2025 TA preflight](../scripts/03n_IT_TrF_official_2025_L2_METEO_SHA_and_TA_time_preflight_READONLY.py):

- `--source-info`: no file required, prints official product PID, filename, expected SHA256 and licence requirement.
- `--archive PATH --out-dir NEW_EMPTY_PRIVATE_DIR`: operator provides the original downloaded official zip. Script rejects wrong SHA/oversized or unsafe ZIP, lists members, extracts **only Nov 12 to Nov 20, 2025 TA rows** directly into private reports without extracting or overwriting original zip, and identifies any `TA_QC`/TA quality flag columns **if present**.
- Collects both `TIMESTAMP` (UTC) and `TIMESTAMP_END` (local non-DST) and reports the actual offset distribution **rather than hardcoding the offset or autojoining IT-Tor's `TIMESTAMP_START`**.
- Does **not** read IT-Tor source, old Stage28, or annual DATM NetCDF, and **does not compare/replace any model forcings** until independent timestamp, sensor height and quality-flag science gates are reviewed.
- No user data uploaded to public GitHub. Private output only: `stage03n_IT_TrF_official_2025_meteo_inventory_PRIVATE.json`, `stage03n_IT_TrF_2025Nov_TA_UTC_context_PRIVATE.csv`.

The anticipated **2025 archive is publicly listed**, but it is **NOT downloaded or present on IRIDIS6 as a result of Stage03M**. Do not claim the independent measurement comparison is complete or that raw IT-Tor MDS temps are wrong without actual neighbor data and sensor/time QC.

Current science HOLDs: severe IT-Tor MDS minus packaged ERA differences across three source subruns, original 10-layer `ORGANIC=0` source soil provenance; DE-Gri 49 old MDS blocks; DE-RuR and ES-Agu precipitation accumulation timing; CH-Aws/GL-ZaH independent forcing, PFT and site science. No AD5/AD400 authorization.
