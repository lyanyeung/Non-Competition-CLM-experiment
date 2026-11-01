# ICOS Batch04 — Stage03F operator PASS and Stage03G IT-Tor original source science screen (2026-11-01)

## Verified operator Stage03F results

The user completed the SHA-verified Stage03F source/selected comparison on IRIDIS6. `FULL PYTHON SYNTAX PASS`, source `STAGE03F SELF-TEST PASS`, all requested reads and two private report outputs succeeded, with no original data, model case or Slurm changes.

Two original **maximal consecutive TA_F/VPD_F QC1-or-QC2** intervals were identified from the site's own distributed FLUXMET data in 2025 October–November:

| Interval | Exact original source-label start | End | Length | Both adjacent original TA/VPD QC0? |
|---|---|---|---:|---|
| **LONG_1458** | **2025-10-21 02:30:00** | **2025-11-20 11:00:00** | **1,458 half-hours** | **YES** |
| **SHORT_29** | **2025-11-21 17:30:00** | **2025-11-22 07:30:00** | **29 half-hours** | **YES** |

All original QC1 and QC2 TA/VPD counts (**587+900=1,487**) are explained by these two periods (**1,458+29=1,487**). Original source TA and VPD compare numerically equal to the already chosen Stage28 values in **all 2,928 half-hours** by class: QC0 **1,441/1,441**, QC1 **587/587**, QC2 **900/900** for both T and VPD. No evidence of new Stage28 edits in this interval. A matched original source value is **not proof a QC1/QC2 gap-filled record came from a directly measured tower sensor**, nor evidence that all such values are wrong. Avoid automatic source-ERA substitution and avoid blanket masking long gaps.

The historical [FLUXNET13 Stage27 code](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/FLUXNET_MultiSite_13/scripts/stage27/27_freeze_13site_met_provisional.py) had cited a **1,458-HH** IT-Tor source-switch/fill problem without its exact start/end. The unique **1,458-HH** Stage03F interval is a very strong match in duration and subject matter, but no independent historical timestamp comparison has yet established identity. This distinction remains in the science report.

Private original Stage03F result files, never publish:
```
/home/ly3n24/ICOS_Batch04_stage03f_zHyZB1yv/results/stage03f_IT_Tor_exact_QC1_QC2_run_lengths_PRIVATE.json
/home/ly3n24/ICOS_Batch04_stage03f_zHyZB1yv/results/stage03f_IT_Tor_original_QC1_QC2_episodes_PRIVATE.csv
/home/ly3n24/ICOS_Batch04_stage03f_zHyZB1yv/stage03f_console.log
```

## Next Stage03G — substantive physical source QC, NOT another full-site scan

The remaining scientific question is **whether the long source gap-fills have physically plausible moisture/temperature values and acceptable joins to QC0 measured-source segments**, not whether the selected Stage28 file copied the original network data. The latter is already proven.

[Stage03G targeted two-run read-only science screen](../scripts/03g_IT_Tor_two_QC12_runs_thermodynamics_and_anchors_READONLY.py) requires the successful source-pinned original Stage03F private JSON plus Stage03B-REUSE original source SHA record. It cross-checks exact two run time boundaries and **both-sides-QC0** flags, then streams only IT-Tor original network-product source and selected Stage28 CSV, holding **just these two exact runs with 2h on each side** in memory. The original Stage28 selected meteorology SHA256 is reverified. No full meteorology quality rerun, not even the complete 2,928-HH Oct–Nov period, no 74 DATM NetCDF, other three site data, downloads, or source changes.

For each run it reports:
- QC1-vs-QC2 breakdown and source available TA/VPD/network ERA fields (ERA here can derive from the same network filling model, not independent calibration)
- Reconstructed RH from selected TA and VPD using a **water saturation vapour pressure diagnostic** with screening counts for invalid RH, negative VPD, and **RH below 1%**; this is not an independent observed RH or an ice-saturation-adjusted truth at below-freezing temperatures
- `QBOT` consistency from reconstructed vapour pressure and selected `PSRF` with a diagnostic **1e-5 kg/kg threshold**, not an automatic hard failing of the science record
- Internal adjacent half-hour jumps exceeding **5°C T** or **8 hPa VPD** and both left/right **QC0-boundary jumps** exceeding **4°C T** or **5 hPa VPD**
- Source TA/VPD versus selected Stage28 numerical match counts per exact run; private **boundary samples only** (2h either side), which may aid investigating real source-switch artifacts

Printout contains diagnostic counts, scientific *HOLD* preserved. Private outputs:
```
stage03g_IT_Tor_two_runs_physics_anchors_PRIVATE.json
stage03g_IT_Tor_two_runs_boundary_values_PRIVATE.csv
```
Only a NEW EMPTY PRIVATE HOME reporting folder. No source, 74 DATM NC, CIME, original/new PFT surfaces, FATES parameters, Slurm job, reanalysis edits, or models changed.

If Stage03G physical and join screens are entirely clean, this supports **retaining the inherited Stage28 forcing for a transparent provisional model sensitivity trial**, but still **not scientific publication/production source approval** without independent raw measurement/QC and source-era evidence. If physically suspect, isolate exact record times into a candidate audit before making any intervention. The separate original IT-Tor all-ten-soil-layer `ORGANIC=0` remains a model case release hold. Other Batch04 sites retain DE-Gri 49 original MDS pending and DE-RuR/ES-Agu rainfall accumulation-time independent science hold.

**Current state:** PFT decisions 6/6, new PFT point surfaces SHA-verified 4/6, new isolated CIME AD5 submissions 0/6.
