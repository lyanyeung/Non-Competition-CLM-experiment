# Stage03W result and Stage04A four-site FIXNC direct AD400 (2026-11-02)

## Stage03W on IRIDIS6 (operator-run, 2 Nov 2026)

`03w_de_gri_independent_case_preflight_READONLY.py` (blob `b31362b4`, commit `d43b8da`) `plan` against both original DE-Gri templates:

| Check | DE-Gri_FATES_SPINUP1000_S30SHARED | DE-Gri_FATES_SPINUP1000_S30EXCL |
| --- | --- | --- |
| 22 annual files + B04 surface re-hashed | PASS | PASS |
| 22 x 17520 no-leap, same variable set | PASS | PASS |
| 2011 edit scope | TBOT 11 + QBOT 11 HH, max abs TBOT 16.444 K, QBOT 0.00097 kg/kg | same |
| 2024 edit scope | QBOT 23 HH, max abs 0.00852 kg/kg | same |
| Surface HLM13 100 / NATVEG 100 / CROP 0, lat/lon/sand/clay/ORGANIC = template | PASS | PASS |
| Template stream paths = plan baselines, 2004-2025 | no mismatch | no mismatch |
| RESUBMIT | 0 | **199** |
| Result | `CASE PREFLIGHT PASS` | `CASE PREFLIGHT PASS` |

The printed `SCHEDULE` (empty first-read map, forcing years `[1,1,1,1,1]`) was a parser defect: the year window was taken over all DATM streams (aerosol, deposition, ozone and topography streams carry 1 and 2000), not the `CLM_USRDAT` forcing stream. Fixed in commit `6834129` (blob `dd9a5e8f`). A second operator run still executed `b31362b4` because `git -C <worktree> checkout --detach FETCH_HEAD` fails inside a worktree (`FETCH_HEAD` is per worktree); use `origin/<branch>` instead. A Stage03W rerun is no longer needed: Stage04A sets the window explicitly and validates it in the generated `CaseDocs/datm.streams.xml`.

## User decision (2 Nov 2026)

Run the four Batch04 sites with approved PFT surfaces **directly as AD400** (one `case.submit`, `STOP_N=5`, `RESUBMIT=79`, no separate AD5 smoke), the protocol already used for AmeriFlux Batch03/05 and ICOS Batch02 BE-Bra/CH-Lae. CH-Aws (RH source) and GL-ZaH (private Arctic FATES map) stay separate.

## What Stage04A uses

[`04a_batch04_four_site_direct_AD400_FIXNC_80x5.py`](../scripts/04a_batch04_four_site_direct_AD400_FIXNC_80x5.py) reuses the sha-pinned AmeriFlux [B3_01](../../AmeriFlux_Batch03_10/scripts/B3_01_direct_AD400_FIXNC_80x5.py) machinery (private FATES AD namelist overlay preview, ledgers, stack guard, submit, first-segment and AD400 audits), so case handling is identical to the earlier batches.

| Item | Choice | Precedent |
| --- | --- | --- |
| Template | `<site>_FATES_SPINUP1000_S30SHARED`, `create_clone --keepexe` | ICOS Batch03 FI-Let/DE-Obe/DE-Lnf/GF-Guy, Batch02 ES-LJu; S30EXCL never used and has `RESUBMIT=199` |
| Surface | Stage02X `<site>_B04_GITHUBPFT_POINT_CANDIDATE.nc`, SHA pinned | Batch03 FIXNC point convention |
| Forcing | template's own annual DATM list (FLUXNET13 Stage28/29b/30, verified 22/15/18/19 by Stage02V/03B) | Stage03B-REUSE |
| DE-Gri 2011/2024 | operator-approved edits (Stage03U), copied SHA-verified from HOME to `experiments/NonCompetitionObserved22/Batch04_6/DE-Gri/datm_approved_edits_b04_v1` | approved overlays enter the main run (AmeriFlux S84/S89) |
| Stream window | `year_first = year_align = RUN_STARTDATE year`, cycle | B3_01 |
| FATES | template paramfile; default map must hold (host 13 -> cool_c3_grass, host 9 -> broadleaf_evergreen_extratrop_shrub); `use_fates_fixed_biogeog`, `use_fates_nocomp`, `spinup_state=2` | all FIXNC batches |
| CO2 | constant NOAA annual mean of the first forcing year | B3_01, Batch02 BE-Bra |
| History | `TOTSOMC TOTSOMN TLAI FATES_GPP FATES_NPP TWS H2OSNO` | Batch02 Stage43 histfix |
| MPI / stack | `srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores`; stack guard >= 64 MiB | ICOS Batch03 |
| Case name | `<site>_B04_FIXNC_AD400_DIRECT` | AmeriFlux direct naming |

| Site | Forcing | Start -> AD400 target | First 5-year segment reads |
| --- | --- | --- | --- |
| DE-Gri | 2004-2025 (22 y, 2011/2024 edited) | 2004 -> 2404 | 2004-2008; edits first read at model years 2011 and 2024 |
| DE-RuR | 2011-2025 (15 y) | 2011 -> 2411 | 2011-2015 |
| IT-Tor | 2008-2025 (18 y) | 2008 -> 2408 | 2008-2012 |
| ES-Agu | 2006-2024 (19 y) | 2006 -> 2406 | 2006-2010 |

## Residual science HOLDs carried into the run (recorded in each ledger, not resolved)

* DE-Gri: of the 49 listed original MDS/QC1 blocks only the two edited events (2011, 2024) were changed, the rest stay as source; soil inherited from the grid surface; source clock.
* DE-RuR: 2012-07-27 rain accumulation clock; dated TA height (2.58 m first); soil and management inherited.
* IT-Tor: 2025 Oct-Nov 1,458-HH MDS/ERA splice kept (Stage03N decision); all ten soil ORGANIC layers 0 (grid).
* ES-Agu: 2018-09-15 rain clock; bare/shrub/grass cover denominator and biocrust; soil inherited.

These runs are therefore the FIXNC pilot spin-up on the documented inputs, not a forcing or soil science release.

## IRIDIS6 commands

```bash
conda activate clm_fates_env
cd "$HOME/Non-Competition-CLM-experiment"
BR=icos-b04-stage04-four-site-direct-ad400-20261102
git fetch origin "$BR"
W="$HOME/ICOS_Batch04_stage03w_code"
git -C "$W" checkout --detach "origin/$BR"
S4="$W/examples/Batch04_6/scripts/04a_batch04_four_site_direct_AD400_FIXNC_80x5.py"
git -C "$W" log -1 --format='%h %an %s'
git -C "$W" rev-parse "HEAD:examples/Batch04_6/scripts/04a_batch04_four_site_direct_AD400_FIXNC_80x5.py"

python3 -B "$S4" self-test
python3 -B "$S4" check 2>&1 | tee "$HOME/b04_04a_check.log"
```

`check` is read only. Only after `B04 04a CHECK PASS 4/4` (or with `--sites` limited to admitted sites):

```bash
python3 -B "$S4" prepare --confirm PREPARE_B04_FOUR_DIRECT_AD400_CASES_NO_SLURM 2>&1 | tee "$HOME/b04_04a_prepare.log"
ulimit -s unlimited
python3 -B "$S4" submit --confirm SUBMIT_B04_FOUR_DIRECT_AD400_80x5_ONCE 2>&1 | tee "$HOME/b04_04a_submit.log"
python3 -B "$S4" status
```

After the first 5-year segment of each site has archived: `python3 -B "$S4" audit-first5` (run/st_archive `COMPLETED 0:0`, CLM/DATM/CPL restart at start+5, `spinup_state=2`). At the end: `audit-ad400`. A failed prepare is moved aside with `quarantine-failed-prepare --sites <site> --confirm QUARANTINE_B04_FAILED_PREPARE_NO_SLURM`; never repeat `submit` after an uncertain result.
