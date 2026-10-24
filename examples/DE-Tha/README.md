# DE-Tha — standard ICOS FIXNC example (evidence-first)

**Status: SITE EVIDENCE REVIEWED · PFT AREA MAPPING NOT APPROVED · NO DE-Tha FIXNC CASE CREATED OR SUBMITTED.**

This is the **second proposed site**, after the NL-Loo V3 pilot, for a reproducible CLM-FATES **fixed-biogeography + no-inter-PFT-competition** experiment. It documents a quantitatively described, three-functional-type forest composition. It **does not** imply that 22 candidate sites have validated grid-area fractions.

## 1. Why DE-Tha?

ICOS Tharandt (Germany; station `DE-Tha`, ENF classification) is unusual in our 22-site quantitative-evidence shortlist because the official station record reports a full breakdown of five tree-species groups. It includes a **cold-deciduous needleleaf component** (larch) absent from the NL-Loo pilot's simpler tree mixture. This is a useful test of an additional HLM→FATES PFT.

**Primary official evidence:**
- [ICOS Tharandt station](https://meta.icos-cp.eu/resources/stations/ES_DE-Tha) — 87% evergreen conifers (72% *Picea abies* + 15% *Pinus sylvestris*), 13% deciduous trees (10% *Larix decidua* + 1% *Betula* sp. + 2% other species).
- [ICOS Germany Tharandt station description](https://www.icos-infrastruktur.de/en/icos-d/components/ecosystem/study-sites/tharandt-c1) — 87% coniferous / 13% deciduous in the flux-influence forest, with historical forest management.

The numerical **denominator is reported vegetation/tree composition**, **not** a demonstrated whole-grid, vertically independent CLM natural-landunit PFT area fraction. Converting it to fixed FATES patches is a *modeling hypothesis* requiring an explicitly justified stand/footprint-to-grid proxy.

## 2. Observations vs. PFTs

| Reported tree group | % | Proposed functional grouping | Status |
| --- | ---: | --- | --- |
| *Picea abies* (spruce) | 72 | ENF | Species identified |
| *Pinus sylvestris* (Scots pine) | 15 | ENF | Species identified |
| *Larix decidua* (larch) | 10 | DNF, deciduous needleleaf | Species identified |
| *Betula* sp. (birch) | 1 | DBF | Species identified |
| Other deciduous trees | 2 | **Unresolved DNF/DBF** | **HOLD** |
| **Total** | **100** | **ENF 87 / DNF 10 / DBF known 1 / unresolved 2** | **Evidence only** |

The **2% remainder may not be silently assigned to DBF**. For model sensitivity design, the manifest includes two **unapproved** working hypotheses (not measurements): `ENF87/DNF10/DBF3` or `ENF87/DNF12/DBF1`. Neither can be written to a surface until the scientific review documents why the selected 2% assignment and the area proxy are justified.

See [observed_tree_composition.csv](data/observed_tree_composition.csv) and [experiment_manifest.json](config/experiment_manifest.json) for auditable evidence and decision gates.

## 3. Folder structure

```text
examples/DE-Tha/
  README.md
  data/
    observed_tree_composition.csv    # observed fractions, reference, denominator caveat
  config/
    experiment_manifest.json         # hypotheses, case names, stop/go gates
  scripts/
    01_audit_evidence.py             # READ ONLY; verify reported species composition
    02_inventory_iridis_inputs.py     # READ ONLY; find original DE-Tha files/cases
    03_audit_live_inputs.py           # READ ONLY; inspect actual surface/DATM/FATES mapping
    04_review_landunit_scenarios.py   # READ ONLY; compare competing surface/landunit hypotheses
```

## 4. Run the first reproducible audit (IRIDIS6)

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -B examples/DE-Tha/scripts/01_audit_evidence.py
```

To locate actual DE-Tha surface, meteorological forcing, source CTSM revision, and legacy cases **without changing them**, run:

```bash
python3 -B examples/DE-Tha/scripts/02_inventory_iridis_inputs.py \
  2>&1 | tee ~/DE-Tha_input_inventory.log
```

The inventory searches only targeted site subdirectories, with bounded depth and file counts. Its output does not establish whether a forcing file is scientifically suitable. Inspect the output before any case creation.

### Input inventory findings, 24 October 2026

The IRIDIS6 read-only inventory located:

- Original surface: `sites/MY_EC_SITE/DE-Tha/subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc`.
- Processed v5 forcing: `sites/MY_EC_SITE/DE-Tha/forcing/processed_v5/DE-Tha_CLM_forcing_1996_2025.csv`.
- Thirty candidate yearly NetCDF files: `sites/MY_EC_SITE/DE-Tha/forcing/datm_v5_candidate_timevarying_zbot/DE-Tha_DATM_1996.nc` through `DE-Tha_DATM_2025.nc` (listed, not yet time-axis validated).
- Legacy case: `cases/DE-Tha_FATES_SPINUP500`, using `use_fates_nocomp=.false.` and `use_fates_fixed_biogeog=.false.` — **not reusable as the new experiment without new isolated setup**.
- Shared CTSM revision: `d5ea9d0136530370a62ef267ccfaff6f001ef914`; default FATES parameter JSON SHA256 `0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04`.

The inventory could not establish `PCT_NATVEG`, `PCT_CROP`, `PCT_NAT_PFT` or actual `fates_hlm_pft_map` values because it only listed paths; likewise forcing coverage from filenames is not time-axis QC. Run the **new, narrowly scoped 03 audit**:

```bash
python3 -B examples/DE-Tha/scripts/03_audit_live_inputs.py \
  2>&1 | tee ~/DE-Tha_live_inputs_audit.log
```

This reads those existing source files, checks every reported landunit category, the actual CLM natural PFT percentages and pinned ENF/DNF/DBF mapping, the 1996–2025 forcing CSV row count and sampled DATM time axes. It makes **no changes** and does **not** authorize a new surface or Slurm job. The source vegetation percentages remain hypotheses for model PFT area.

Tharandt is managed: station information describes thinnings and species conversion, and long-run sources document wind and bark-beetle effects. Thus a 1996–2025 transient validation should not treat a single baseline composition as a measured constant through time. [ICOS Germany](https://www.icos-infrastruktur.de/en/icos-d/components/ecosystem/study-sites/tharandt-c1), [TU Dresden stand history](https://tu-dresden.de/bu/umwelt/hydro/ihm/meteorologie/forschung/mess-und-versuchsstationen/tharandt-ankerstation-oekomessfeld).

### Live scientific input audit (24 October 2026): actual numbers

The script 03 output has been inspected, without any new model inputs being written.

- Original surface SHA256: `7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d`.
- Whole grid: `PCT_NATVEG=62.6740617603%`, `PCT_CROP=37.3259382397%`; no lake/wetland/glacier/urban cover.
- **Within natural landunit only**: `PCT_NAT_PFT[0]` bare 0.5962%, `[1]` ENF 31.8322%, `[7]` DBF 11.7861%, `[13]` cool C3 grass 55.7856%; `[3]` DNF **0%**. Sum 100%.
- Pinned CTSM source and parameter JSON hashes match NL-Loo. Active map: CLM `natpft[1]` → `needleleaf_evergreen_extratrop_tree`; `[3]` → `needleleaf_colddecid_extratrop_tree`; `[7]` → `broadleaf_colddecid_extratrop_tree`.
- Processed forcing: 1996–2025 inclusive, 525,600 half-hourly rows (17,520 each no-leap year). The 30 candidate DATM annual NetCDFs exist; **only sample years** had time metadata validated in script 03.
- Original `DE-Tha_FATES_SPINUP500` case: `RUN_TYPE=startup`, `RUN_STARTDATE=1996-01-01`, `STOP_N=REST_N=5`, and **both** `use_fates_nocomp` and `use_fates_fixed_biogeog` are false. It is a **reference/control**, not the new experiment.

**Scientific issue:** ICOS reports the forest in the tower-flux influence area as 87% evergreen conifer and 13% deciduous (10% larch, 1% birch, 2% other). [Official ICOS station](https://meta.icos-cp.eu/resources/stations/ES_DE-Tha); [ICOS Germany footprint/management notes](https://www.icos-infrastruktur.de/en/icos-d/components/ecosystem/study-sites/tharandt-c1). These data are closer to a forest-flux-footprint composition than grid-wide CLM land cover, but **are not proven to be 1-point natural-PFT grid areas**. The legacy surface's 37.33% cropland and 55.79% natural-PFT grass demonstrate a particularly important site-to-grid representativeness conflict.

Run the new bounded **strictly read-only** scenario/QC decision audit:

```bash
python3 -B examples/DE-Tha/scripts/04_review_landunit_scenarios.py \
  2>&1 | tee ~/DE-Tha_landunit_scenario_review.log
```

It prints three fundamentally different candidate representations, without rewriting any surface:

| Scientific contrast | Landunit shares | Candidate PFT proportions (conditional on NATVEG) | Caution |
| --- | --- | --- | --- |
| Existing reference | NATVEG 62.674%, crop 37.326% | ENF 31.832%, DNF 0%, DBF 11.786%, grass 55.786%, bare 0.596% | Ordinary FATES control |
| **Grid-conserving** tower-tree FIXNC proxy | NATVEG 62.674%, crop 37.326% | ENF 87%, DNF 10%, DBF 3% *if 2% assigned to DBF* | Preserves cropland; not a pure forest EC-footprint simulation |
| **Tower-forest** FIXNC proxy | NATVEG 100%, crop 0% | ENF 87%, DNF 10%, DBF 3% *under same 2% hypothesis* | Changes the landunit and PFT composition simultaneously |

The script **also** prints a sensitivity where the unknown 2% is allocated to DNF instead of DBF; neither assignment is an observation. A recommended controlled comparison additionally considers **FIXNC on the unchanged original surface** to help separate the no-competition effect from the PFT-map effect. Each proposed treatment requires a separate case with consistent model inputs; the scientific grouping is an experimental factor rather than the measured truth. **Do not launch or write a surface before approving which scientific contrast is intended.**

To *view* (not approve) an explicit 2% allocation hypothesis:

```bash
python3 -B examples/DE-Tha/scripts/01_audit_evidence.py --scenario other_as_DBF_proxy
```

Once actual DE-Tha paths and hashes are confirmed, the **same audit script** can read the original pre-existing inputs, without modifying them:

```bash
python3 -B examples/DE-Tha/scripts/01_audit_evidence.py \
  --surface "/ACTUAL/DE-Tha/original/surfdata.nc" \
  --fates-params "/ACTUAL/CTSM/src/fates/parameter_files/fates_params_default.json"
```

The placeholder paths above must be replaced with audited existing paths; they are **not claimed to exist**. Review `PCT_NATVEG`, `PCT_CROP`, natural PFT indexing and `fates_hlm_pft_map` before deciding how to handle non-natural landunits. Never change crop share to 0 or NATVEG to 100 without documenting the assumption. The default CLM PFT indices used for preliminary verification are 1 (temperate evergreen needleleaf), 3 (boreal deciduous needleleaf), and 7 (temperate deciduous broadleaf); the **actual pinned parameter JSON must be checked**.

## 5. Proposed independent phase design, NOT YET LAUNCHED

| Case (proposed) | Years | Decomposition | 5-year segments |
| --- | ---: | --- | ---: |
| `DE-Tha_OBSPFT_NC_V1_PRE50` | 50 | normal; `spinup_state=0` | 10 |
| `DE-Tha_OBSPFT_NC_V1_AD200` | 200 | accelerated; `spinup_state=2` must be verified for pinned FATES build | 40 |
| `DE-Tha_OBSPFT_NC_V1_POST300` | 300 | normal; `spinup_state=0` | 60 |

All are **model-year durations**; specific calendar start years must be decided from DE-Tha forcing coverage and `NO_LEAP`/loop settings, rather than copied blindly from NL-Loo (which starts in 1997). Proposed site-specific cases must be separate from every existing `DE-Tha_FATES_*` run. Existing spinups, global CTSM, files in Scratch, RFS archives and Slurm jobs remain untouched.

The **validated NL-Loo operational pattern** to adapt *after site review* is documented by:
- [09_NL_Loo_V3_auto550.py](../../scripts/09_NL_Loo_V3_auto550.py): V3 three-phase controller; **hard-coded NL-Loo paths, do not run unchanged** for DE-Tha.
- [11_NL_Loo_V3_AD200_fix_private_overlay.py](../../scripts/11_NL_Loo_V3_AD200_fix_private_overlay.py): FATES AD `spinup_state=2` namelist patch performed in an isolated copy.
- [14_NL_Loo_V3_AD200_history_retry.py](../../scripts/14_NL_Loo_V3_AD200_history_retry.py): `FATES_GPP`/`FATES_NPP` (rather than non-FATES GPP/NPP) for the pinned build.
- [15_NL_Loo_V3_AD200_complete_remaining.py](../../scripts/15_NL_Loo_V3_AD200_complete_remaining.py): verifies archived 2052 restart and restores 2052 rpointer handoff before guarded 5-year resubmissions; **hard-coded incident-specific job IDs, not reusable directly**.

## 6. Required gates before a DE-Tha run

1. **Scientific:** identify the unresolved 2%, choose/justify a fixed-tree-composition-to-PFT-area scenario, quantify uncertainty and expected change in forest composition over the observation period.
2. **Forcing:** find and QC the actual DE-Tha processed meteorological data, years, calendar, tower-to-grid representativeness, and a 5-year forcing loop. Do not assume NL-Loo forcing dates apply.
3. **Surface:** locate actual original DE-Tha surface, inspect crop/natural landunits and PFT fractions, verify the host-to-FATES PFT mapping with pinned parameter JSON, make an isolated *new* surface only after signoff.
4. **Technical:** verify the actual executable and pinned CTSM revision, no-competition + fixed-biogeography namelists, and patch AD `spinup_state=2` only in a private scientific build/namelist overlay.
5. **Operational:** inspect Slurm queue and inode quota; use unique case/run/archive names; smoke test first 5 years of each phase; verify each phase's three restarts, `spinup_state`, and pointer advancement before continuation.

**No automatic surface rewrite, case creation, model run, job cancellation, or watchdog activation is implemented by this example.** This is a safe foundation for a reusable, peer-reviewable standard template rather than an unverified duplicate of the NL-Loo case.

## Scientific references

- [ICOS official DE-Tha station inventory](https://meta.icos-cp.eu/resources/stations/ES_DE-Tha).
- [FATES documented no-competition/fixed-biogeography modes](https://fates-users-guide.readthedocs.io/projects/tech-doc/en/stable/fates_tech_note.html).
- [FATES-HLM PFT map documentation](https://fates-users-guide.readthedocs.io/en/latest/user/HLM-FATES-PFT-map.html).
