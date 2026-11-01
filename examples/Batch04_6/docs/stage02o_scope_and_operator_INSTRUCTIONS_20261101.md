# ICOS Batch04 CH-Aws Stage02O — source-RH conflict and source-seam screening (2026-11-01)

## Why

Stage02N has already proven integrity of three original humidity-repair ledgers, but **none is native tower-QC validated**:

| Ledger | Records | SHA256 | Declared scientific status |
|---|---:|---|---|
| Stage34 | 27 | MATCH | EXPLORATORY_NOT_OBSERVATION_QC_APPROVED |
| Stage38 | 21 | MATCH | EXPLORATORY_NOT_TOWER_VALIDATED |
| Stage42 | 23 | MATCH | EXPLORATORY_REANALYSIS_SENSITIVITY |

All 20 selected large-QBOT-change event rows matched the original ledger and source time, `SOURCE_ROW_HOLDS 0`. FLUXMET source `VPD_F_QC` was 1 (gap-filled by standard definition) at all 20; `RH` was not numeric at any of the selected timestamps. The unapproved historical reference was very close to gap-filled START-indexed `VPD_F`; RH34A/38A/42A corrections move increasingly toward `VPD_ERA`, but **this is not enough to select any forcing**. Extremes like 2007-07-22 07:00 (old source RH ~0.320%, ERA5 99.326%, ERA5-Land 98.655%) require special scrutiny of actual instrument data, local site altitude and independent ERA provenance.

## Controlled operator step

Run `scripts/02o_CH_Aws_RH_source_ERA_20event_triage_readonly.py` from a **SHA-verified immutable GitHub commit** in the existing `clm_fates_env` environment, using the exact operator-produced Stage02N and Stage02M JSONs:

- Stage02N: `/home/ly3n24/ICOS_Batch04_stage02n_sfazK8sU/results/stage02n_CH_Aws_original_ledger_QC_provenance.json`
- Stage02M: `/home/ly3n24/ICOS_Batch04_stage02m_WIktbwfu/results/stage02m_ERA_gapfill_revision_evidence.json`

The script reads those saved JSONs **only**, rejects any missing ledger SHA, event-time/index mismatch, or unexpected scientific release, and for each selected event collects:
- original ledger implied humidity and reported ERA5/ERA5-Land RH;
- percentage-point source disagreement;
- neighboring RH jumps and recorded source-seam information (when the ledger contains them);
- evidence flags, retaining `EXPLORATORY` metadata and `NATIVE_TOWER_RH_UNVERIFIED` HOLD.

Output two reports into a **new existing empty HOME directory**:
- `stage02o_CH_Aws_20_event_risk_triage.json`
- `stage02o_CH_Aws_20_event_risk_triage.csv`

**This is not a quality approval or repair**. The source RH is inferred from processed `VPD_F` rather than native sensor RH. ERA5 and ERA5-Land products are not independent observational truth and may have common biases or mismatched topography. Adjacent half-hour jumps are from previously recorded candidate ledger contexts, not new source tower observations. No QC relabeling, zero/near-100 RH clipping, interpolations, source NetCDF writes, CIME/Slurm or AD5/AD400.

## Next direction after operator output

For CH-Aws, identify genuine unfilled tower RH/TA sensor records, site height/pressure and time basis, and independently verify ERA5/ERA5-Land station-grid representation before adjudicating each revision. In **parallel** use the already recorded Stage02C/02D source registers for DE-Gri, DE-RuR, IT-Tor and ES-Agu to audit true DATM stream binding, native meteorology and PFT/surface/soil. Separately preserve GL-ZaH's private site-only Arctic shrub FATES mapping hold.

All six sites remain scientifically on HOLD until individual gates pass.
