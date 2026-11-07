# AU-Gin: Stage16 original-source scientific closeout (7 November 2026)

**Scope:** AU-Gin Gingin tower, OzFlux old original `Gingin_L6.nc`, and 2011–2025 TERN FLUXNET FLUXMET product. Report is an evidence register and scientific gate assessment only. **No corrections, no model-ready meteorology, no AD400.**

## Provenance and execution

IRIDIS6 operator Stage16 **read-only PASS**: original immutable TERN ZIP, original old L6, Stage10, Stage14 and Stage15 source/HOLD SHA verified, self-test PASS. Executed report: `/home/ly3n24/ozflux_AU_Gin_stage16_20261107T052337Z`.

Original TERN ZIP SHA256: `acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14`.
Original old L6 SHA256: `0e700e37ead024a7eda4cdf9b47f839d5dc5bfa5578087e9af1ddd09aa510d66`.
Primary Stage16 script commit `a075bc5686cad50f7a02f5fd4af71e6f83b99999`, Git blob `8b4f29da7e145a7e11ca69a61d6ca15b714f9608`. New TERN BIF `UTC_OFFSET=8`; original L6 `time_zone=Australia/Perth` and half-hour clock appears END-labelled: original L6 local END = TERN FLUXMET local START + 30min from four high-precision Ta matches. This is **related-source product lineage**, not independent meteorological confirmation.

Stage10 had 28 original anomaly groups and 44 flagged HH. Seven priority time points received detailed Stage11–16 source forensics. **All 28 groups remain on science HOLD**, including the other 21 not fully resolved by these seven-case checks.

## 1. Isolated 2019 wind source anomaly

New TERN `WS_F=19.95 m/s` at local AWST 2019-09-13 03:00. At corresponding original L6 **END 03:30**, source channels:

| Original L6 channel | Wind m/s | Original QCFlag |
|---|---:|---:|
| `Ws` composite | **19.948950** | 0 |
| `Ws_WS4_16m` | **19.948950** | 0 |
| `Ws_SONIC_Av` | 0.6586267 | 0 |
| `Ws_WS4_10m` | 0.5074776 | 0 |
| `Ws_WS4_7m` | 0.4393113 | 0 |
| `Ws_WS4_2m` | 0.1239203 | 0 |
| `Ws_SONIC_1_Av`, `Ws_SONIC_7m_Av`, `Ws_WS4_4m`, `Ws_from10m_16m` | missing | 1 |

In the previous 30min composite `Ws=0.4321907` and 16m `Ws_WS4_16m=0.4321907`; previous 60min both **1.156399**. At +30min composite `Ws=0.4512651`, **16m input missing QCFlag1**, while 10m `Ws_WS4_10m=0.4512651` — evidence of composite choosing a different source when 16m unavailable. At +60min composite/10m `Ws=0.5857098`, 16m missing QCFlag1. Source center 16m vs median of four simultaneously available other original sensors (0.473394 m/s) ratio **42.14**. Independent NOAA Pearce RAAF hourly ~0.5 m/s after UTC+8 alignment, ~43.35km away (regional context only).

**Scientific classification:** compelling single-channel isolated 16m wind spike and source-selection risk, QCFlag0 false negative candidate; not *proven* hardware mechanism and not automatically justified to replace with 10m/sonic donor (height, exposure, 30-minute support and physical measurement compatibility unverified). Request 16m WS4 maintenance/calibration and QC/source-selection information from site PI.

## 2. Two 2016 temperature anomalies and composite source selection

Old L6 composite `Ta` equals rounded new TERN `TA_F` at +30min old L6 end-clock.

| New TERN START (AWST) | Old L6 END | Composite Ta °C | Original HMP comparison and QC |
|---|---|---:|---|
| 2016-05-07 16:00 | 16:30 | **−4.625476** | HMP 2m **−3.84153**, 4m **−4.625476** (both QC0); 7m/10m/15m TA missing QC1 |
| 2016-05-20 18:00 | 18:30 | **6.19237** | HMP 2m **8.470531**, 4m **9.620131**, 7m **9.981885**, 10m **9.92137**, 15m **6.19237**, all QC0 |

For May 7 center, old L6 composite 30 min before **15.42317 °C** and 30 min after **12.44366 °C**; 2m/4m both show sharp low values at the center. On May 20, composite 30 min before **18.13714 °C** and 30 min after **17.73450 °C**; **all five HMP heights show large temperature decreases**, not solely 15m, although 15m remains additionally lower than 2–10m by ~2.3–3.8°C. This suggests both event-wide measurement/processing changes and height/channel selection require review. **Do not claim only a single faulty sensor** without data logger/instrument/processing records.

At both 2016 centers new TERN `VPD_F=0 hPa`; original old L6 concurrent same-height HMP temperature and RH (~52–74% depending event/channel) yield strictly positive **~2.01–3.53 hPa** VPD diagnostic values (not applied). This broadens the issue to temperature/humidity provenance, even where individual HMP raw QCFlag is 0.

**Scientific classification:** likely event-local acquisition or channel selection/processing anomaly; no approved source substitution, interpolation, or VPD repair.

## 3. Two 2013 QC1 VPD saturation conflicts

| New TERN START local AWST | TERN VPD_F, QC1 (hPa) | old L6 2m HMP T, QC0 (°C) | esat(T), hPa | implied RH | Original old L6 HMP RH |
|---|---:|---:|---:|---:|---|
| 2013-02-05 06:30 | 22.071 | 13.60853 | 15.5726 | −41.73% | missing (QCFlag1) at all 5 heights |
| 2013-02-16 07:00 | 26.870 | 19.09408 | 22.0894 | −21.64% | missing (QCFlag1) at all 5 heights |

The new TERN product's original standalone RH field is also missing for both centers. VPD > saturation vapor pressure is **physically incompatible with the corresponding same-time temperature** for ordinary ambient humidity (negative inferred RH). This is a **QC1 gap-fill/variable-pair consistency failure**. Cannot derive a validated source RH-based replacement when all original HMP RH channels are unavailable at the event centers; obtain documented upstream gap-fill method and science-approved thermodynamic constraints.

## 4. Two 2012 PA cases

- **2012-06-09 08:00**: original TERN `PA_F=102.9 kPa` QC0, prev 101.005 kPa **QC2**, next 101.1 kPa QC0. Original old L6 37-channel sensor-focused inventory has no PA-class data channel. The originally flagged 08:30 pressure recovery 101.1 kPa is likely less anomalous than 08:00. Never assume two QC0 flanks for 08:00.
- **2012-06-10 13:30**: original TERN `PA_F=101.4 kPa` QC0, prev 99.0 and next 99.6 kPa QC0, isolated spike. Regional NOAA Pearce original station-level pressure ~988.7 hPa at closest available AWST-aligned +/−90min observation; 43km distance/time/elevation differences prevent direct value replacement.

**Scientific classification:** on-site pressure instrument log or exact Gingin Aero (BoM station 009178) independently sourced matching meteorology needed; PA single-point neighbor interpolation remains non-applied mathematical diagnostic only.

## Stop/go: actual tower-year criterion and current modeling status

- New TERN FLUXMET is processed/filled over nominal **2011–2025** calendar years; source tower QC0 time support actually begins ~2011-10-13 and ends ~2025-06-27: **~13.7 elapsed calendar years**, not 15 years of actual observation; may be further incomplete within that interval.
- If the study criterion is **≥15 elapsed real tower-measured meteorological years**, **AU-Gin is ineligible** independent of whether seven or all 28 anomalies are resolved. No production AD400 should be prepared/submitted.
- Keep full original/source and Stage05–16 evidence for reproducible method development; archive the seven-case gate as **SCIENCE HOLD / NOT A REPAIRED DATASET / NOT PUBLICATION QC PASS**.
- For scientific closure, request from PI: sensor/source selector log and calibration/maintenance for 2019 16m WS4, 2016 2m/4m/15m HMP, 2013 VPD gapfill/humidity provenance, 2012 pressure sensor, and precise old-to-new timestamp methods. Await external first-party evidence before any *separate* correction protocol.
- Deprioritize AU-Gin from current model submission cohort; use the freed review time to evaluate other OzFlux stations against the **15-real-year / meteorological-source QC** gate before scheduling costly model runs. This is a pause, **not deletion or permanent ban**.
- AU-ASM and AU-DaS remain separately held. TERN Support's AU-ASM dendrometer caution must **not** be transferred to AU-Gin.

**Preservation:** original `Gingin_L6.nc` / TERN ZIP immutable by SHA; no original, DATM, surface, CIME case, Slurm/AD400 changes; no automatic replacement, donor, or gap-fill was approved.
