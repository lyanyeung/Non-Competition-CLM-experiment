# ICOS Batch04 Stage03K — Actual operator results and next Stage03L (2 November 2026)

## Confirmed actual Stage03K PASS

Operator-verified `FULL PYTHON SYNTAX PASS`, `STAGE03K SELF-TEST PASS`, and complete source-scoped result on IRIDIS6. Original source, all selected Stage28 forcing and yearly DATM NetCDF, CIME/FATES/PFT cases and Slurm remained untouched.

The official FLUXNET source `QC1` represents MDS gapfill, `QC2` a packaged downscaled ERA fill; Stage03J established the six QC1↔QC2 transitions each followed the official product selection. Stage03K tested the **full known QC1 portions** of the two previously located, protected runs:

| Metric | IT-Tor long 1,458-HH run | IT-Tor short 29-HH run |
|---|---:|---:|
| Original source QC1 (MDS) | **558 HH** | **29 HH** |
| Original source QC2 (ERA) | **900 HH** | **0 HH** |
| Contiguous QC1 subintervals | **9** | **1** |
| Longest contiguous QC1 subinterval | **208 HH** | **29 HH** |
| MDS − packaged ERA T median | **−3.135°C** | **−0.806°C** |
| Mean T difference | **−3.903509°C** | **−0.374690°C** |
| Minimum T difference | **−14.498°C** | **−1.741°C** |
| MDS colder than packaged ERA by more than 5°C | **183/558 (32.8%)** | **0/29** |
| MDS colder than packaged ERA by more than 10°C | **98/558 (17.6%)** | **0/29** |
| MDS − packaged ERA VPD median | **−0.999 hPa** | **−0.384 hPa** |

Original source product source-rule counts: long run `{1: 558, 2: 900}`, short run `{1: 29}`, with **no source-selection error flags**. The six extreme source handoffs are **not merely isolated discontinuity spikes**; a notable subset of the long-run QC1 MDS filled records has large negative differences relative to the packaged ERA reference. **But not all QC1 MDS records are severely different**, and the short 29-HH block is comparatively close. A difference from **packaged** ERA is *not a measured-temperature error*; there is no proof that replacing 183 or 98 HH is meteorologically appropriate.

Original private results (do not publish per-record/episode licensed data):
```
/home/ly3n24/ICOS_Batch04_stage03k_6NcC66KW/results/stage03k_IT_Tor_QC1_MDS_vs_ERA_bias_2_runs_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03k_6NcC66KW/results/stage03k_IT_Tor_QC1_contiguous_segments_PRIVATE.csv
```

## Stage03L: prioritise the ten *already documented* QC1 subintervals without rereading source

[Stage03L existing-report-only priority tool](../scripts/03l_rank_existing_Stage03K_QC1_MDS_bias_intervals_PRIVATE_READONLY.py) reads **only those two private Stage03K reports**. It validates the exact two-run 558+29 QC1 counts, 9+1 subintervals, strict 30-minute durations and nonoverlap, aggregate 183/98 threshold counts and count-weighted QC1 MDS-relative mean. It then prints the precise subrun dates/rank, number below −5°C and −10°C, median/mean and a conservative science HOLD class. It writes only one private aggregate JSON and one private ten-subinterval priority CSV into a NEW EMPTY HOME output directory.

The goal is to determine whether the 98 very negative relative differences cluster in one or a few QC1 subruns, so that **independent original tower/neighbouring-station measurements or site metadata** can be gathered for only the most critical dates. An interval with many negative MDS−ERA differences is a **higher review priority**, not an approved sensor correction or ERA5 substitution. **No full FLUXMET or Stage28 source reread, 74-DATM numeric QC, data/NetCDF replacement, CIME edit or Slurm submission.**

Separate scientifically open issues include IT-Tor original ten-soil-layer `ORGANIC=0` source, DE-Gri 49 MDS HOLD episodes, DE-RuR 2012-07-27 and ES-Agu 2018-09-15 rain accumulation clock, and CH-Aws/GL-ZaH site-specific source/PFT. This ranking neither approves nor launches AD5/AD400.
