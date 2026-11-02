# Batch04 IT-Tor — 2025 IT-TrF independent near-station evidence examined LOCALLY (2026-11-02)

## Operator decision — NO MORE IRIDIS6 ZIP TRANSFER

The user explicitly declined any further transfer or work on IRIDIS6. Their uploaded ICOS **`ICOSETC_IT-TrF_METEO_L2(2).zip`** was examined in the assistant's isolated analysis environment. No HPC source/forcing/NC/CIME/FATES/PFT/Slurm files were touched; the original Stage03B–03N program files and all old private reports on IRIDIS6 are unaffected.

**Why the previous `sha256sum -c` failed:** this ICOS web-download package is a *nested outer ZIP*. The outer uploaded file was **16,792,611 bytes**, SHA256 `d41b915371ddb31df7e08ecb95970714369f24480596ff69018e5fa4670603be`, with three members:

- `ICOSETC_IT-TrF_METEO_L2.zip` (inner official ZIP)
- `!TOC.csv`
- `!LICENCE.pdf`

The inner ZIP is **exactly 16,713,915 bytes**, SHA256 **`9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f`**, matching the published authoritative [ICOS ETC L2 Meteo IT-TrF 2011/12–2025](https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl) source. The full nested archive ZIP integrity passed. The inner archive contains one `ICOSETC_IT-TrF_METEO_L2.csv` (53,923,697 bytes uncompressed). **No download corruption or wrong-version claim is justified. The failing checksum was on the outer package, not the inner ICOS data object.**

### Correct time/quality schema — important correction to previous Stage03N assumptions

The *actual* inner CSV headers begin **`TIMESTAMP_START,TIMESTAMP_END,...,RH,...,TA,...`**. It does **not** contain `TIMESTAMP` and does **not** include an explicit `TA_QC` or `TA_F_QC` field. Therefore **do not use the original Stage03N `--archive` parser against this uploaded package**: that implementation expected a *flat inner ZIP* and the non-existent `TIMESTAMP` column, so a future real-data branch would not correctly parse this source. Its prior `--self-test` PASS was only on synthetic metadata and was never evidence the actual package had been parsed. The upload was processed locally using the correct nested-ZIP and `TIMESTAMP_START/TIMESTAMP_END` layout.

[ICOS ETC submission guidelines](https://icos-etc.eu/home/guidelines/how-to-submit-data/general-information) specify paired interval-start/end labels in **local time without DST**, and [FLUXNET time conventions](https://fluxnet.org/data/fluxnet2015-dataset/) also use local standard time for original half-hour timestamp labels. This supports *like-for-like* label comparisons, although the exact IT-Tor source-manifest clock and sensor height should still be checked before claiming rigorous synchronized station-to-station quantitative bias. A nonmissing IT-TrF `TA` is an **aggregated station meteorological product** and without a variable-specific original sensor flag cannot automatically be asserted as an original **QC0** observation of the same footprint. IT-TrF is a **larch forest station** near the **IT-Tor grassland** station; exposure and canopy/height differences remain real scientific caveats.

## Real available IT-TrF air temperature (Nov 12–20, 2025)

The uploaded source contained all **245,472** original half-hour rows from 2012–2025, including **432** Nov 12–20 2025 time-labelled half-hour rows; **288/432** had numeric `TA`, with three entire days missing `TA` (source literal `-9999`):

| Nov 2025 local standard date | Valid TA HH / 48 | Mean TA (°C) | Range (°C) |
|---|---:|---:|---|
| 12 | 48 | +4.016 | +2.132 to +6.182 |
| 13 | 48 | +6.594 | +3.328 to +10.296 |
| 14 | 48 | +1.809 | +0.390 to +3.717 |
| 15 | **0** | n/a | missing |
| 16 | **0** | n/a | missing |
| 17 | 48 | +1.308 | −3.173 to +4.708 |
| 18 | **0** | n/a | missing |
| 19 | 48 | −3.391 | −7.038 to +0.241 |
| 20 | 48 | −6.967 | −9.068 to −4.765 |

On missing Nov 15, 16 and 18, **RH and T_CANOPY were also wholly missing** (not just TA), so the primary ranked IT-Tor MDS interval has a real neighbour meteorology evidence gap. This is **not permission to impute** those days.

## Coverage in the previously ranked IT-Tor MDS subruns

*Matching local-standard source-label windows, subject to final source clock and sensor-height qualification.*

| Stage03L rank | IT-Tor MDS source-label interval | QC1 HH | Valid IT-TrF TA HH | IT-TrF TA range |
|---|---|---:|---:|---|
| 1 | Nov 15 17:00 – Nov 18 07:00 | 125 | **48/125 = 38.4%** | −3.173 to +4.708°C (Nov 17 only) |
| 2 | Nov 13 17:30 – Nov 14 07:00 | 28 | **28/28 = 100%** | +0.390 to +5.261°C |
| 3 | Nov 13 14:30 – Nov 13 15:30 | 3 | **3/3 = 100%** | +8.494 to +9.288°C |

These top three IT-Tor subruns contain **156 original QC1 MDS HH** of which **98** have MDS−packaged-ERA temperature <−10°C in earlier protected Stage03L (and **138** <−5°C). The actual absolute IT-Tor MDS tower temperatures were **not provided** in the upload; therefore no direct paired station-to-station absolute bias (IT-TrF TA − IT-Tor TA_F_MDS), or comparison to the exact erroneous 98 records, can be computed reliably from this conversation alone.

### Relative source-label 30-minute change at six original Stage03H jump times

Four of the six original IT-Tor MDS↔ERA QC1/2 handoffs have neighboring IT-TrF TA for both adjacent source-label half-hours:

| Original IT-Tor jump second HH | IT-Tor Stage28 source inherited step | IT-TrF same-label step | IT-Tor packaged TA_ERA step |
|---|---:|---:|---:|
| Nov 13 14:30 | −12.440°C | **−0.275°C** | −0.037°C |
| Nov 13 16:00 | +11.959°C | **−0.422°C** | −0.410°C |
| Nov 13 17:30 | −14.312°C | **−0.441°C** | −0.871°C |
| Nov 14 07:30 | +13.963°C | **+0.052°C** | −0.132°C |
| Nov 15 17:00 | −13.142°C | **missing** | −0.118°C |
| Nov 18 17:00 | −6.937°C | **missing** | −0.126°C |

Even checking neighbor same-label half-hour steps within ±60 minutes of each of the four available jump times, the absolute neighbor TA steps remain **≤1.331°C**, much smaller than the corresponding **11.959–14.312°C** original IT-Tor source-family handoff changes. The neighboring source is not physically equivalent to the target station, but this is **additional observationally sourced support for a gapfill-family splice discontinuity**, rather than evidence of an actual simultaneous regional 12–14°C 30-minute event.

## Final science decision within supplied data and user's no-more-IRIDIS constraint

1. **Conclude a real processed-source MDS↔ERA family discontinuity exists** at six previously pinned times; original Stage03H/J separately prove the QC1=MDS and QC2=packaged ERA product branch rules, and Stage03L establishes that significant **relative** negative MDS−ERA differences cluster in three specific QC1 intervals.
2. Neighbor observations **support the continuity concern for Nov 13–14**, but **do NOT provide complete independent validation**, particularly Nov 15–16 and Nov 18 absent data. The L2 aggregated `TA` has no explicit matching QA column in this uploaded CSV; original instrument sensor and height-specific QC are not proven.
3. **Do NOT modify original IT-Tor source or the inherited Stage28 forcing; do NOT automatically replace 156/558/587 QC1 MDS half-hours with source packaged ERA**; do not create a new DATM, CIME, FATES, PFT or Slurm model run. Preserve a scientifically documented **HOLD** for production/publication. No operator request for more IRIDIS6 work is needed.
4. Keep **IT-Tor original all-ten-layer `ORGANIC=0`** soil provenance as an independent model gate. No other Batch04 stations' science HOLDs change. If a future independent IT-Tor original measured `TA` (ETC METEOSENS 2025), sensor QC and original-meteorology release become available through an authorized workflow, restrict re-assessment to the three already pinned MDS subruns; **do not infer repaired model forcing from this neighbor product alone**.

### Source provenance

Official [Galvagno, Ferraris, Filippa (2026), *ETC L2 Meteo from Torgnon-LD, 2011-12-31–2025-12-31*, ICOS RI, PID 11676/mwN98ExGR4uPnaUKi5mWoISl](https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl). Licenced CC BY 4.0. Upload supplied by operator; this GitHub document publishes only non-sensitive scientific summaries and file hashes, **never the original CSV/ZIP or source per-HH records**.
