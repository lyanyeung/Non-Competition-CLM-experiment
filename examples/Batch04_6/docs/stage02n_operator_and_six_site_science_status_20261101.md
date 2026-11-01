# ICOS Batch04 six-site science-gate status, including CH-Aws Stage02N

**Date:** 2026-11-01. This is a planning and evidence note, not a model release.

## Current audit counts

- Exactly six sites: CH-Aws (8 original case candidates), DE-Gri (2), DE-RuR (2), IT-Tor (2), ES-Agu (2), GL-ZaH (1). **17 original case candidates** in total.
- Stage02D inspected **233 unique case-referenced candidate annual DATM files**: CH-Aws 133 (seven distinct forcing path sets, 2006–2024); DE-Gri 22 (2004–2025); DE-RuR 15 (2011–2025); IT-Tor 18 (2008–2025); ES-Agu 19 (2006–2024); GL-ZaH 26 (2000–2025). All printed `FLAGS {}` in the limited *DATM internal numeric/time checker*. This is not source-observation QC, active runtime stream verification, or final science approval.
- Stage01 static site point match reported 17/17, but original natural PFT percentages are operator-selected model proxies, not measured eddy-covariance footprints.

## CH-Aws Stage02N actual IRIDIS6 output — 2026-11-01

Operator-pasted evidence: `SOURCE VERIFIED`; `STAGE02N SELF-TEST PASS`; all three original repair ledgers reopened and verified their SHA256 against their manifest; 20 exact-time event ledger rows matched by CSV row number and source time; `SOURCE_ROW_HOLDS 0`, `LEDGER_SHA_UNVERIFIED NONE`. No source/CASE/FATES/Slurm changes. These are evidence-integrity checks only.

- Report: `/home/ly3n24/ICOS_Batch04_stage02n_sfazK8sU/results/stage02n_CH_Aws_original_ledger_QC_provenance.json`
- CSV: `/home/ly3n24/ICOS_Batch04_stage02n_sfazK8sU/results/stage02n_CH_Aws_exact_20_event_ledger_records.csv`
- Log: `/home/ly3n24/ICOS_Batch04_stage02n_sfazK8sU/stage02n_console.log`

| Exact ledger | Original CSV rows | SHA256 | Original manifest scientific status |
|---|---:|---|---|
| Stage34 | 27 | MATCH | `EXPLORATORY_NOT_OBSERVATION_QC_APPROVED` |
| Stage38 | 21 | MATCH | `EXPLORATORY_NOT_TOWER_VALIDATED` |
| Stage42 | 23 | MATCH | `EXPLORATORY_REANALYSIS_SENSITIVITY` |

The 20 priority events were partitioned as seven Stage34 (2007–2008), five Stage38 (2017), and eight Stage42 (2016, 2018–2020). **A matched source ledger hash, exact row/time, and no row holds DO NOT mean the human/sensor scientific QC has passed.**

Selected original candidate observations/reanalyses, as *printed in original Stage02N ledger*:

| DATM event | Stage | Implied RH from unapproved `VPD_F` (%) | Original ledger ERA5 RH (%) | ERA5-Land RH (%) | Quality warning |
|---|---|---:|---:|---:|---|
| 2007-07-22 07:00 | 34 | 0.320 | 99.326 | 98.655 | `VPD_F_QC=1`, native RH absent |
| 2007-07-22 07:30 | 34 | 3.609 | 99.327 | 98.323 | ~95 percentage-point source conflict |
| 2008-06-27 06:30 | 34 | 9.364 | 91.113 | 94.159 | Abrupt RH vs adjacent HH in ledger |
| 2008-06-28 06:30 | 34 | 0.013 | 82.474 | 88.182 | Serious source-disagreement flag |
| 2017-09-02 12:30 | 38 | 0.202 | 97.530 | 93.838 | No independently verified tower RH |
| 2019-07-29 07:30 | 42 | 9.005 | 88.591 | 90.662 | Exploratory ERA sensitivity only |
| 2020-07-17 10:00 | 42 | 6.726 | 80.535 | 86.090 | Exploratory ERA sensitivity only |

The **20/20** printed events used distributed `FLUXMET VPD_F_QC=1` (standard FLUXNET convention: gapfilled processed VPD), `TA_F_QC=0` and **no numeric source RH** at the selected event anchors. The historical reference DATM was numerically very close to START-indexed processed gapfilled `VPD_F` (Stage02L mean abs deviation **0.003395 hPa**), and far from the distributed product `VPD_ERA` (~6.5714 hPa across these deliberately selected events). Stage02M showed selected RH34A/38A/42A candidates becoming closer to that `VPD_ERA` field (MAE 4.2316/3.2722/1.1942 hPa respectively), but proximity is not proof of observation validity or independent site-grid representativeness. Do not select a variant using MAE alone.

The CH-Aws Stage02G finding of 1667 unique half hours with RH-water just over 100% (peak 100.071%, none >105%) is **not** the major problem compared with the very low implied RH / huge gapfilled-versus-ERA humidity disagreement. No bulk clipping/interpolation of mild saturation flags.

### Six-site practical severity and action order

| Site | Internal DATM status | Unresolved science or technical issue | Action |
|---|---|---|---|
| **CH-Aws** | 133 annual candidates; time/numeric internal screen pass; seven humidity source variants | Old gap-filled `VPD_F` at QC1 leads to RH near 0–9% at many selected times, whereas reported ERA/ERA5-Land RH is frequently 80–99%; alternative Stage34/38/42 repairs are **EXPLORATORY ONLY**. Grass/forb proxy and actual active DATM stream, case/surface/soil also held. | **P1** Verify true native tower RH/TA/QC and station time basis, independent ERA source/grid/height and actual repair selection rules. Read original Stage34/38/42 ledger source evidence; retain scientifically unresolved events as HOLD. |
| **DE-Gri** | 22 files, `FLAGS {}` | C3-grass-only proxy does not establish actual grass/forb/legume + bare footprint; original tower/ERA half hours, soil/point and S30SHARED vs S30EXCL case science unvalidated | **P2** Smallest-scope site-by-site observation/PFT/soil and CIME active DATM stream preflight |
| **DE-RuR** | 15 files, `FLAGS {}` | Lysimeter species groups do not represent entire EC footprint; source meteorology, soil, management seasonal effects unverified | **P2** Source QC, management timing, soil/PFT map and stream preflight |
| **IT-Tor** | 18 files, `FLAGS {}` | Alpine vegetation bare fraction, snow/temperature, soil, tower location and seasonality unverified | **P2** Mountain forcing seasonality and PFT/soil preflight |
| **ES-Agu** | 19 files, `FLAGS {}` | Conditional NATVEG model proxy **bare 49%, evergreen shrub 22%, C3 grass 29%**; biocrust/bare cover and Macrochloa survey denominator unresolved | **P3** Reconcile land cover denominator and surface/FATES mapping, native source/QC and soil |
| **GL-ZaH** | 26 files, `FLAGS {}` | Conditional NATVEG model proxy **bare 43%, evergreen Arctic shrub 53%, deciduous Arctic shrub 3%, Arctic C3 grass 1%**. **Mandatory site-only private FATES host9/11 Arctic shrub map**, not a shared parameter overwrite. | **P3** Build/validate independent private Arctic FATES mapping and point/soil science; check actual stream and original forcing source |

## Concrete next steps — do NOT submit AD5/AD400 yet

1. **CH-Aws source-science decision**: inspect full original source package and Stage34/38/42 ledgers/manifest rows (verified hashes), seek unfilled tower `RH`/`TA`/VPD and native QC at matched times; independently confirm ERA5/ERA5-Land references, units, time stamps, site-grid representativeness and annual QBOT transitions. Mark each proposed replacement **SUPPORTED / HOLD / REJECTED** only with explicit evidence; never infer source choice from ERA proximity.
2. **In parallel, unblock lower-complexity four**: for DE-Gri, DE-RuR, IT-Tor and ES-Agu identify effective runtime `CaseDocs` DATM streams, actual original tower meteorological QC and gap-fill/ERA periods; verify point PCT_NATVEG, conditional PFT proxy, soil vertical fractions/organic, measured tower coordinates, height/zbot. Resolve S30SHARED vs S30EXCL by effective scientific file selection, not name.
3. **GL-ZaH separate mapping track**: verify/prepare a private **site-only** HLM-to-FATES Arctic shrub map, plus soil/organic/tundra vegetation footprint science and DATM/forcing source, without mutating shared FATES mapping.
4. Only with a **complete per-site scientific release record** can a newly versioned isolated case proceed with controlled **AD5 then AD395, Normal5 then Normal395**; current six are all HOLD. Preserve existing case data, input files, Git worktree and active Slurm jobs unchanged.

This note reflects operator console evidence (not full mounted scientific JSONs) and is **not a final seven-source observation-based validation**.
