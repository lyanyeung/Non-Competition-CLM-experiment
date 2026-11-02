# ICOS Batch04 — actual Stage03L subrun priorities and independent source inventory (2 November 2026)

## Stage03L actual scientific HOLD outcome

The user reported `FULL PYTHON SYNTAX PASS`, Stage03L full in-memory self-test PASS and complete private report success. No FLUXMET, selected Stage28 forcing, 74 annual DATM NetCDF, CIME/FATES/PFT or Slurm inputs were read or changed by Stage03L.

All **98 / 558 QC1 MDS half-hours** colder than packaged `TA_ERA` by over 10°C in the LONG_1458 mixed gapfill were found in **just the following three** of nine LONG QC1 subintervals:

| Priority | Original IT-Tor source label interval (2025) | QC1 HH | MDS − packaged ERA < −5°C | < −10°C | Median MDS − packaged ERA |
|---|---|---:|---:|---:|---:|
| 1 | Nov 15 17:00 – Nov 18 07:00 | **125** | **107** | **67** | −10.073°C |
| 2 | Nov 13 17:30 – Nov 14 07:00 | **28** | **28** | **28** | −12.385°C |
| 3 | Nov 13 14:30 – Nov 13 15:30 | **3** | **3** | **3** | −12.403°C |

Together the top three account for **156 QC1 HH**, **138/183 (75.4%)** of all < −5°C QC1-vs-packaged-ERA differences, and **98/98 (100%)** of < −10°C comparisons. Remaining long-run subintervals: 11/18 17:00–11/20 11:00 (85 HH, 31 < −5, 0 < −10), 10/21–10/25 (208 HH, 14 < −5, 0 < −10), and four other long-run subintervals (46,23,38,2 HH, all 0 < −5). SHORT_29 11/21–22 (29 HH, 0 < −5). Stage03L confirms 9+1 original QC1 periods: source MDS and packaged downscaled ERA follow official product mixing; discrepancy **between two gap-filled products** is *not a demonstrated error of the raw tower instrument*. All remain science HOLD, with zero authorised numerical repairs.

Private Stage03L results, never publish raw time-series or sensitive source paths:
```
/home/ly3n24/ICOS_Batch04_stage03l_jRPnLQCn/results/stage03l_IT_Tor_QC1_MDS_priority_summary_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03l_jRPnLQCn/results/stage03l_IT_Tor_10_QC1_subruns_ranked_PRIVATE.csv
```

## Real nearby independent-source lead (station identity is essential)

**IT-Tor Torgnon** is an alpine **grassland** ICOS/FLUXNET station, about 2,160 m elevation (45.8444 N, 7.5781 E). ICOS also has a *different station*, **IT-TrF Torgnon-LD**, **larch forest**, about 2,150 m elevation (45.8238 N, 7.5609 E). These are not interchangeable point-site IDs, and canopy and cold-air drainage may cause temperature differences. Sources:

- Official FLUXNET IT-Tor site: https://fluxnet.org/sites/siteinfo/IT-Tor
- ICOS 2025-covering Torgnon-LD L2 FLUXNET HH package published in 2026: https://meta.icos-cp.eu/objects/EUCf30NjOFzu2N1by918KJPF
- Torgnon basin site comparison and elevations: https://inarch.usask.ca/science-basins/torgnon.php

**Next useful science question:** do actually **measured (QC0) IT-TrF air temperatures**, when correctly timestamp-aligned and height/forest context is understood, show a high-altitude cold spell in **Nov 13–18, 2025** closer to IT-Tor's QC1 MDS fill than the IT-Tor packaged ERA fill? This independent source is a *corroborative neighbor*, not proof of same-footprint tower temperature. IT-TrF QC1 MDS or QC2 ERA gap-filled rows must NOT be described as independent measurements. Data-clock documentation is crucial: source `TIMESTAMP_START` may differ from ICOS standardized UTC `TIMESTAMP` or local non-DST `TIMESTAMP_END`. Do not silently join by literal timestamps until the offset has been established from station metadata.

## Stage03M — inventory only, no meteorological comparison yet

[Stage03M read-only IT-TrF source file inventory](../scripts/03m_IT_Tor_top3_MDS_neighbor_IT_TrF_source_inventory_READONLY.py) takes original Stage03L private JSON and 10-row ranked CSV. It strictly verifies the three top priority intervals and original 183 / 98 and 558+29 totals, then performs only a **non-recursive** directory listing of the explicitly named IT-TrF candidate station folders under `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE` (and one optional operator-supplied directory). It filters likely files `IT-TrF`/`Torgnon-LD` in names with zip/CSV/NetCDF extensions, noting if the filename refers to 2025. It does **NOT** assert contents, QC0, exact calendar coverage, timestamps or sensor height from filenames alone. If no files are found, that is a **local source availability gap**, not evidence no public ICOS product exists.

This is intentionally **not** a new data request/download, file unpack, numerical science QC, ERA reconstruction or a new forcing experiment. It writes only a private JSON with ranked original problem dates, checked directory inventory and source evidence requirements. Once candidate 2025 IT-TrF file availability and metadata are confirmed, a distinct subsequent narrowly scoped QC0-only measured comparison can be proposed with explicit time mapping. No automatic source substitution or AD5 submission.

Outstanding separate gates: IT-Tor original ten-layer `ORGANIC=0` soil provenance, DE-Gri 49 original MDS source episodes, DE-RuR and ES-Agu rainfall accumulation clock, CH-Aws and GL-ZaH independent PFT/forcing source gates. Never treat Stage03M as full Batch04 science release.
