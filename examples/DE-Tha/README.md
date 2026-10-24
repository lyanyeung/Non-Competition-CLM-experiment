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
    01_audit_evidence.py             # READ ONLY; NO source changes or Slurm jobs
```

## 4. Run the first reproducible audit (IRIDIS6)

```bash
conda activate clm_fates_env
cd ~/Non-Competition-CLM-experiment
git pull --ff-only origin main
python3 -B examples/DE-Tha/scripts/01_audit_evidence.py
```

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
