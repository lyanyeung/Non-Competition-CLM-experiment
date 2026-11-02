# Needleleaf collapse in the FATES fixed-biogeography / no-competition spin-up — diagnosis log

Status: **mechanism confirmed (section 8); parameter trials prepared (section 9).** Last updated 1 November 2026.
Scope: the AD400 → NORMAL400 cases of job 4764252 (54 sites), with detailed diagnosis at
DE-Obe and FI-Sod (needleleaf, collapsed) against DE-Hai (broadleaf, healthy) and FI-Hyy
(mostly needleleaf, alive only in its 5 % broadleaf patch).

## 中文摘要

- 凡是以常绿针叶 PFT（`needleleaf_evergreen_extratrop_tree`，PFT 2）为主的站点，GPP 都长期很低，或在 AD 阶段就归零。
- **复现：** 用完整的 FATES 输出重跑 AD 前 50 年（只改历史输出设置，其他全部相同），GPP 和原 AD400 逐月完全一致（600 个月）。
- **直接死因：碳饥饿死亡。** 在 DE-Obe 和 FI-Sod 分别占全部死亡的 75% 和 88%。冻害为 0，水力失效几乎为 0。
- **BTRAN 只有 0.05 不是缺水，是统计口径造成的。** CTSM 按树冠覆盖面积给 FATES 斑块加权，树冠之间的空地算作裸地，裸地上的 BTRAN 记为 0。植物自身的 BTRAN 约为 1，土壤是湿的。
- **单株碳收支是正的：** CUE 约 0.38，活下来的树在长大。但 FATES 判定碳饥饿用的是“储存碳 ÷ 满叶时的叶碳量”：低于 1.0 就开始死亡，最高每年 60%；而储存上限只有叶碳的 1.2 倍。
- **针叶 PFT 正好落在这个陷阱里：**
  - 默认 `slatop` 只有 0.005 m² gC⁻¹（阔叶 0.03），同样的叶面积要背约 6 倍的叶碳；
  - 叶寿命 4 年；
  - 冬天叶子不落，维持呼吸照常消耗储存，每年冬天都跌破 1.0 倍叶碳的门槛，于是持续死亡，补充的新苗赶不上。
- **公式核对：** 按公式预测的碳饥饿死亡率和模型输出逐月一致（DE-Obe r=0.996、斜率 1.04；FI-Sod r=1.00、斜率 1.02）。储存/叶碳在 DE-Obe 1–4 月、FI-Sod 11–6 月低于 1.0。
- **下一步：** 针叶 PFT 参数试验（储存缓冲、碳饥饿门槛、slatop），见第 9 节。

## 1. Full-sequence screening (54 sites)

Figures: [`figures/AD400_NORMAL400_full_sequence/20261031T005421Z_from_job4764252`](../figures/AD400_NORMAL400_full_sequence/20261031T005421Z_from_job4764252)
(800-year GPP / NEE / NPP / LAI per site, EC reference lines, automatic flags, all-site overviews).

- 54/54 plotted; 47 with EC reference, 7 model-only because no partitioned HH/HR EC file was found
  (CA-Ca3, CA-LP1, DE-Lnf, US-Ho2, US-Ho3, US-Syv, US-Uaf).
- GPP ≈ 0 at the end (annual mean < 0.05 g C m⁻² d⁻¹; first year of the final low run in brackets):
  CH-Dav (72), CZ-BK1 (50), CZ-Stn (15), DE-Obe (49), FI-Sod (1), IL-Yat (1), US-GLE (4), IT-Ren (267),
  CA-Ca3 (41), CA-LP1 (12), DE-Lnf (14). Very low but non-zero (model/EC GPP): FI-Hyy 0.04, DE-Tha 0.09,
  RU-Fyo 0.09, US-Ho1 0.10. Almost all are needleleaf-dominated.
- The "year" of the near-zero flag is a threshold crossing, not a collapse date: DE-Obe never exceeded
  0.085 g C m⁻² d⁻¹, i.e. it never established.
- Separate issue, not pursued here: GPP/LAI steps at year 400/401 at some sites (IT-MBo, US-SRG, US-SRM, DE-Hzd);
  AD only rescales soil pools, so vegetation should be continuous across the handoff.

## 2. Literature context

- Big-leaf models tend to **over**estimate boreal/needleleaf GPP (LPJ, ORCHIDEE, Biome-BGC: Jung et al. 2007,
  *Biogeosciences* 4, 647; NACP 26-model synthesis: Schaefer et al. 2012, *JGR* 117, G03010; CLM5 boreal high bias in
  CESM working-group material). The low needleleaf GPP here is therefore not a generic land-model behaviour.
- FATES-specific reports of needleleaf failure: default FATES at a Sierra Nevada point gave very low biomass and
  exclusion of needleleaf trees (Holm, ACME poster 2016); Buotte et al. 2021 (*Biogeosciences* 18, 4473) had to define
  dedicated conifer PFTs; Lambert et al. 2022 (*GMD* 15, 8809) found near-absent needleleaf vegetation at a cold site
  in default FATES-Hydro (winter hydraulic failure — plant hydraulics are off in our runs); FATES calibration work
  reports establishment failure with high carbon-starvation mortality (Needham, CESM LMWG 2023) and high sensitivity
  to the carbon-starvation function and storage cushion (Kowalczyk, CESM BGCWG 2024, evergreen cushions tuned to 1.8–2.7).

## 3. The original output could not attribute the collapse

Figures: [`figures/AD400_NORMAL400_collapse_diagnostics/20261031T181554Z`](../figures/AD400_NORMAL400_collapse_diagnostics/20261031T181554Z)

The AD400 cases wrote only `TOTSOMC, TOTSOMN, TLAI, FATES_GPP, FATES_NPP, TWS, H2OSNO`. NORMAL400 wrote full
FATES output, but by then the needleleaf vegetation, recruitment and seed bank were already zero.

## 4. Diagnostic AD re-run (first 50 AD years, full FATES history)

Figures: [`figures/AD400_NORMAL400_collapse_diagnostics/20261101T033156Z`](../figures/AD400_NORMAL400_collapse_diagnostics/20261101T033156Z)

Cases `DE-Obe_B03_FIXNC_AD400_DIAG50` and `FI-Sod_B01_FIXNC_AD400_DIAG50`: `create_clone --keepexe` of each site's own
AD case; same executable, surface, forcing, parameter file, CO₂, AD settings and start date; the regenerated `lnd_in`
was verified identical to the AD case's except `hist_empty_htapes` / `hist_fincl1` (adds per-PFT mortality by type).

| | DE-Obe | FI-Sod |
|---|---|---|
| GPP vs original AD400 (monthly) | identical, 600 months | identical, 600 months |
| GPP year 1 / maximum (g C m⁻² d⁻¹) | 0.065 / 0.085 (year 5) | 0.043 / 0.043 (year 1) |
| Needleleaf plants ha⁻¹ (first → last 5 y) | 1790 → 324 | 1430 → 0.7 |
| Mortality shares (50 y) | carbon starvation 75 %, background 25 %, hydraulic 0.4 %, freezing 0 | carbon starvation 88 %, background 9 %, hydraulic 4 %, freezing 0 |
| Storage / target, minimum | 0.56 | 0.26 |

Carbon-starvation mortality comes in winter pulses of 10–30 % yr⁻¹ whenever storage drops below target; recruitment
does not keep up.

## 5. BTRAN ≈ 0.05 is a canopy-cover artefact, not water stress

Figures: [`20261101T035722Z`](../figures/AD400_NORMAL400_btran_soil_diagnostics/20261101T035722Z) (first run),
[`20261101T040911Z`](../figures/AD400_NORMAL400_btran_soil_diagnostics/20261101T040911Z) (with canopy-cover check).

BTRAN was recomputed layer by layer with the FATES non-hydro formula (root fraction × water-potential factor ×
temperature gate) from liquid water, ice, soil temperature, `FATES_FROOTC_SL` and the PFT's smpso/smpsc.

| | DE-Obe | FI-Sod | DE-Hai (ref.) | FI-Hyy (ref.) |
|---|---|---|---|---|
| History BTRAN, JJA | 0.050 | 0.008 | 0.975 | 0.049 |
| Recomputed plant BTRAN, JJA | 1.000 | 0.999 | 0.984 | 1.000 |
| Canopy cover (crown area / ground) | 0.050 | 0.008 | 0.996 | 0.049 |
| Recomputed × canopy cover | 0.050 | 0.008 | 0.980 | 0.049 |

Reason (source code): CTSM gives each FATES patch a weight equal to its canopy-covered area
(`patch%wt_ed(p) = canopy_fraction_pa(ifp)`) and the uncovered ground to a bare-ground patch
(CTSM `src/utils/clmfates_interfaceMod.F90`, ~L1729–1747), whose `btran` is set to 0 in
`BareGroundFluxesMod.F90` (~L288). FATES' own patch BTRAN is a normalized conductance-weighted mean of the PFT
BTRANs (`biogeophys/EDBtranMod.F90`, ~L228–236). So history BTRAN ≈ canopy cover × plant BTRAN. Soils were wet
(root-weighted JJA liquid water 0.29–0.41 m³ m⁻³; 90 % of fine roots above 0.92 m); no layer limited uptake.

**Correction:** an earlier interpretation in this analysis ("BTRAN ≈ 0.05 cuts photosynthesis by ~95 %") was wrong.

## 6. Per-plant carbon budget

Figures: [`figures/AD400_NORMAL400_carbon_budget_diagnostics/20261101T043223Z`](../figures/AD400_NORMAL400_carbon_budget_diagnostics/20261101T043223Z)

| | DE-Obe NET | FI-Sod NET | DE-Hai BDT (mature) |
|---|---|---|---|
| Biomass per plant (first → last 5 y, g C) | 309 → 2270 | 248 → 989 | ~7000 (stable) |
| GPP per kg leaf C, JJA (g C d⁻¹) | 24 | 25 | 89 |
| Maintenance resp. per kg leaf C, JJA / DJF | 10.2 / 3.75 | 8.9 / 2.74 | 11.6 / – (leafless) |
| GPP per m² leaf, JJA (g C d⁻¹) | 4.58 | 4.78 | 2.05 |
| Maintenance resp. per m² leaf, JJA | 1.94 | 1.70 | 0.27 |
| Maintenance resp. / GPP | 0.55 | 0.56 | 0.17 |
| of which leaf / fine root (share of GPP) | 0.26 / 0.29 | 0.25 / 0.30 | 0.08 / 0.09 |
| CUE (NPP / GPP) | 0.39 | 0.38 | 0.74 |
| Storage / leaf C, mean | 1.03 | 0.80 | 2.40 |
| Winter reserve (Nov storage / Dec–Feb deficit) | 6.4 | 3.8 | 4.8 |

Per kg leaf carbon the needleleaf and broadleaf maintenance respiration are similar; per m² leaf the needleleaf
respires ~7× more because each m² of needles carries ~6× more carbon (`fates_leaf_slatop` 0.005 vs 0.03 m² gC⁻¹),
and fine-root carbon (and its respiration) scales with leaf carbon. Surviving needleleaf trees grow, and storage is
several times the winter deficit in absolute terms — so the population does not die of running out of carbon.

PFT parameters that differ between PFT 2 (needleleaf) and PFT 6 (broadleaf cold-deciduous) in the parameter file
used (`fates_params_default.json`), key ones first: `fates_leaf_slatop` 0.005 / 0.03; `fates_turnover_leaf_canopy`
4 / 1 yr; `fates_allom_d2ca_coefficient_max` 0.369 / 1.155; `fates_turnover_fnrt` 2 / 1; `fates_stoich_nitr` (leaf)
0.029 / 0.040; `fates_wood_density` 0.44 / 0.57; `fates_maintresp_leaf_atkin2017_baserate` 1.5 / 1.756;
`fates_leaf_vcmax25top` 62 / 58; `fates_mort_freezetol` −55 / −80 °C; full list in `parameter_differences.csv`.
Identical for both: `fates_alloc_storage_cushion` 1.2, `fates_mort_scalar_cstarvation` 0.6 yr⁻¹,
`fates_mort_upthresh_cstarvation` 1.0, `fates_nonhydro_smpso/smpsc` −66000 / −255000 mm.

## 7. Mechanism

FATES carbon-starvation mortality (`biogeochem/EDMortalityFunctionsMod.F90`, ~L200–230), linear model (CTSM default
`fates_cstarvation_model = linear`):

    frac  = storage C / fully flushed target leaf C            (storage_fraction_of_target(target_leaf_c, store_c, frac))
    cmort = mort_scalar_cstarvation * max(0, (mort_upthresh_cstarvation - frac) / mort_upthresh_cstarvation)
          = 0.6 * max(0, 1 - frac)  per year (defaults)

Storage is capped near `alloc_storage_cushion` × leaf C = 1.2 × leaf C, only 0.2 × leaf C above the point where
mortality starts. An evergreen with heavy foliage loses, over a winter of maintenance respiration without
photosynthesis, about 0.34 (DE-Obe, ~90 days at 3.75 g C d⁻¹ per kg leaf C) to ~0.5 (FI-Sod, longer winter) of its
leaf carbon from storage, so `frac` falls below 1 every winter and mortality reaches 20–40 % yr⁻¹ at the minimum —
consistent with the observed storage minima (0.56 and 0.26 of target) and mortality pulses. A cold-deciduous tree has
no leaves (no leaf respiration) in winter and stays above the threshold.

Cold start: in nocomp mode without `use_fates_dbh_init`, each PFT patch starts with `fates_recruit_init_density`
(0.2 m⁻², i.e. 2000 ha⁻¹) plants of `fates_recruit_height_min` (1.3 m) (`main/EDInitMod.F90`, ~L1310–1345). The
needleleaf stand therefore starts sparse and never closes, but the mortality above is independent of stand closure.

Source versions read: FATES `main` b8fbdde (2026-10-25), CTSM `master` f302090 (2026-10-30); line numbers are
approximate for the pinned model version used in these runs.

## 8. Formula check — confirmed

Figures: [`figures/AD400_NORMAL400_cstarvation_check/20261101T044701Z`](../figures/AD400_NORMAL400_cstarvation_check/20261101T044701Z)

Settings actually used (from `lnd_in`): `fates_cstarvation_model = linear`, `fates_leafresp_model = ryan1991`,
`use_fates_dbh_init = .false.`. Observed = `FATES_MORTALITY_CSTARV_SZPF` (needleleaf PFT) / `FATES_NPLANT_PF`;
predicted = 0.6 × max(0, 1 − `FATES_STOREC_PF`/`FATES_LEAFC_PF`), monthly, months with ≥ 1 plant ha⁻¹.

| | DE-Obe NET | FI-Sod NET |
|---|---|---|
| Observed / predicted mean (yr⁻¹) | 0.044 / 0.040 | 0.156 / 0.152 |
| Observed maximum (yr⁻¹) | 0.20 | 0.41 |
| Correlation r / slope (observed vs predicted) | 0.996 / 1.04 | 1.00 / 1.02 |
| Storage / leaf C: minimum, mean | 0.68, 1.03 | 0.32, 0.80 |
| Months below the threshold (1.0) | 38 % | 66 % |
| Storage / leaf C by month (Jan … Dec) | 0.89 0.79 0.75 0.79 1.00 1.19 1.20 1.20 1.20 1.19 1.13 1.01 | 0.67 0.55 0.43 0.37 0.43 0.81 1.19 1.20 1.18 1.08 0.93 0.79 |

The default formula reproduces the needleleaf carbon-starvation mortality almost exactly. Storage reaches the cap
(1.2 × leaf C) in July–October and falls below 1.0 from January to April at DE-Obe and from November to June at
FI-Sod (minimum 0.37 in April). The DE-Hai row in the figures is not comparable: for a cold-deciduous PFT actual leaf
C is ~0 in winter (the formula uses the flushed leaf target), and its NORMAL400 output has carbon-starvation deaths
only for all PFTs combined, dominated by short-lived understory recruits while the stand is stable.

## 9. Fix plan

Change only the needleleaf PFT (PFT 2), one factor at a time, in private copies of the parameter file; run the first
50 AD years at DE-Obe and FI-Sod with the same diagnostic history; judge by survival, LAI, canopy closure and GPP
against EC before rolling out to all needleleaf sites and repeating AD400 → NORMAL400.

| Option | Change (PFT 2) | Rationale | Risk / cost |
|---|---|---|---|
| A | `fates_alloc_storage_cushion` 1.2 → 2.0–2.4 | margin between storage cap and mortality threshold grows from 0.2 to 0.8–1.2 × leaf C, covering the winter drawdown; 2.4 is already used by a default PFT; evergreen cushions of 1.8–2.7 used in FATES calibration | slower early growth while storage fills |
| B | `fates_mort_upthresh_cstarvation` 1.0 → 0.5 | mortality only when storage is genuinely low | tunes the mortality rule rather than physiology |
| C | `fates_leaf_slatop` 0.005 → ~0.008–0.010 | halves leaf C per leaf area → lower leaf and fine-root respiration, lower absolute threshold, more LAI per carbon (CLM5 temperate needleleaf uses ~0.01 — to be verified against TRY/site data) | changes canopy structure; needs observational support |
| D | A + C | combines the two physiological changes | |
| E | no parameter change; `use_fates_dbh_init = .true.` | falsification control: mortality depends on storage / leaf C, not stand closure, so the needleleaf PFT should still collapse; if it survives, the mechanism above is incomplete | namelist switch affects all PFTs/sites if adopted |

Why one change at a time rather than A+B+C together: each trial shows whether that lever alone is sufficient and how
strongly it acts; a combined change that "works" cannot say which part was needed and risks overcorrection
(mortality too low, unrealistically dense stands, GPP above EC). A and C are physiological (non-structural
carbohydrate reserves; leaf mass per area) and can be checked against observations; B changes the mortality rule
itself and is the least defensible. A and B act on the same margin (A raises the storage cap, B lowers the threshold),
so combining them double-counts one mechanism. If D is not enough, B is added in the next round.

`use_fates_dbh_init = .true.` (closed-canopy cold start, as in FATES' `patch_nocomp_noresm.json` approach) does not
address this mechanism; it is run as control E and may later be combined with the winning parameter change to
shorten canopy closure.

Implementation: [`13_needleleaf_param_trials.py`](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/7f4187c4d5a75f11a91679edb7e2f016ed615385/examples/Cross_cohort_NORMAL400/scripts/13_needleleaf_param_trials.py)
creates cases `<AD case>_FIX<A|B|C|D|E>50` at DE-Obe and FI-Sod (10 single-point runs, 50 years each, 5-year segments,
same executable/inputs/AD settings as the AD case). Parameter copies live in
`experiments/NonCompetitionObserved22/NeedleleafFixTrials/params/` with a receipt (source file, SHA-256, old/new values).
Success criteria: needleleaf density stops declining (carbon-starvation mortality ≈ background level), canopy closes
(cover → ~1, LAI of a few m² m⁻²), GPP in the range of the EC record, no new failure mode (e.g. storage never filling).
Run status (2026-11-02):
- A–D finished 50 years at both sites.
- **E did not run.** Both E cases stopped at model initialisation in FATES' parameter consistency check (`ERROR in
  EDPftvarcon.F90 at line 1307`, called from `FatesInterfaceMod.F90` line 2739), so `use_fates_dbh_init = .true.` is rejected by
  this FATES version and parameter set.
- E was only a falsification control. The carbon-starvation formula already reproduces the needleleaf mortality (section 8), and
  that formula depends on storage / leaf C, not on stand closure. **E is dropped.**

Results: to be added.

## 10. 75-site screening: which sites have GPP far below EC (2026-11-01)

Data: [`figures/AD400_NORMAL400_gpp_vs_ec_screening/20261101_from_20261101T042427Z`](../figures/AD400_NORMAL400_gpp_vs_ec_screening/20261101_from_20261101T042427Z/).
The comparison uses the last NORMAL400 forcing cycle against EC monthly means. Ratio = FATES / EC.
Thirteen sites were not run (6 AmeriFlux, 7 ICOS). US-NR3 is excluded because its EC mean is ≈ 0.

| Class | Sites | of which needleleaf ≥ 50% of vegetation |
|---|---|---|
| A far below (< 0.5) | 28 | **25** |
| B below (0.5–0.8) | 7 | 2 |
| C close (0.8–1.25) | 24 | 3 |
| D above (> 1.25) | 15 | 1 |

**A, ≈ 0 (complete collapse; soil C → 0):**
- Needleleaf sites: FI-Sod, CH-Dav, IL-Yat, DE-Obe, IT-Ren, CZ-BK1, CA-Ca3, CA-LP1, US-NC2, US-GLE, FI-Hyy.
- Broadleaf sites: **CZ-Stn and DE-Lnf (both DBF 100)**.

**A, 0.08–0.48 (needleleaf dies, the other PFTs survive):** US-Ho2, DE-Tha, RU-Fyo, US-Ho1, BE-Bra, US-Ho3, FR-FBn, FI-Let, US-SP1,
US-NR1, BE-Vie, US-Me2, IT-Lav, US-Me6. Here the residual ratio tracks the non-needleleaf share. Examples:
- BE-Vie: DBF 36 → 0.31
- FI-Let and US-Ho3: DBF 20 → 0.21 and 0.19
- RU-Fyo: DBF 15 → 0.09

Across the collapsed and partial needleleaf sites, r = 0.57 between ratio and non-needleleaf %.

**The non-needleleaf site in class A:** US-CMW (DBF 74 / C4 26), ratio 0.28. Its soil C is not zero, so the vegetation did not die;
this is an under-estimate rather than a collapse. **US-CMW is flagged GROUNDWATER-DEPENDENT and excluded from the GPP comparison**
(section 11).

**Class B:** CA-TP4 (NET 93) 0.55; tropical evergreen broadleaf GF-Guy 0.57 and BR-Ma2 0.68 (a known FATES nocomp under-estimate,
not collapse); US-BZS, US-Uaf, FR-Pue, DK-Sor.

**Needleleaf sites that do not collapse:**
- US-MtB (NET 100) 0.90; US-Vcp (NET 100) 0.90; US-Vcm (NET 100) 2.17; US-Mpj (NET 60) 0.92.
- All four are high-elevation, sunny, dry south-western US sites.
- Humid warm needleleaf sites (US-NC2, US-SP1) and cloudy/cold European and boreal sites do collapse. Working hypothesis:
  - In the south-west, winter GPP stays positive and maintenance respiration is low (cool, sunny).
  - So storage does not drop below the leaf target, and the carbon-starvation term (section 8) stays near zero.
  - To be tested with 11/12 on a surviving vs a collapsing needleleaf site (e.g. US-MtB vs US-NC2).

**Class D (over-estimate):** arctic tundra (US-ICh, US-ICt, US-EML), drylands (US-Whs, US-Ses, US-Seg, US-Wkg, ES-LJu, IT-Noe),
grass/crop-like sites (US-Var, US-UiD, US-Ton) and US-Rpf. This is a separate problem (no water/nutrient limitation strong enough,
bare-ground fraction, or EC GPP partitioning at very low fluxes) and is not addressed by the needleleaf fix.

### Conclusion

GPP far below EC is overwhelmingly a needleleaf problem: 25 of the 28 class-A sites are needleleaf-dominated. In every
needleleaf site with mixed composition, only the needleleaf part is lost. This matches the carbon-starvation mechanism in
sections 7–8, so the A–E trials (section 9) address most of the class-A sites.

The exceptions need their own check:
1. **CZ-Stn and DE-Lnf (DBF 100)** — collapse in AD year ≈ 15–20 (TOTSOMC shows a litter pulse, then decays to 0). Same pattern
   as the needleleaf sites, but other DBF sites (DE-Hai, DE-Hzd, FR-Hes …) survive. Both are Batch03 cases built on held template
   surfaces, and the history lacks FATES_VEGC. Next: 09 diagnostic re-run (50 AD years) + 08/11/12.
2. **US-MtB / US-Vcp / US-Vcm** — the control group where needleleaf survives. Comparing them with collapsing sites isolates the
   climate condition that triggers starvation.
3. **US-NR3** — EC GPP mean ≈ 0; check the EC record.

## 11. Site anomaly checks: US-CMW, CZ-Stn, DE-Lnf (2026-11-01)

Script `14_diagnose_site_anomalies.py` (branch `full-sequence-gpp-nee-ec`). It compares each site with a working reference on
case set-up, forcing vs EC meteorology, the first 60 AD years, and the last Normal forcing cycle (water balance, LAI, BTRAN,
GPP by PFT, phenology counters). It is read-only.

### US-CMW — FLAGGED: groundwater-dependent riparian woodland, excluded

> **Site flag: `US-CMW = EXCLUDED_GROUNDWATER`.** Do not use US-CMW to judge FATES GPP in this experiment.

- **Tower water balance, 2001–2021 (252 paired months).** EC ET is **662 mm/yr** against **263 mm/yr** precipitation, i.e.
  2.5 × rainfall, every cycle. The forcing matches the tower (T, P and SW ratios 1.00), so this is not a forcing error.
- **Literature agrees.** US-CMW (Charleston Mesquite Woodland) is the riparian mesquite woodland on the Upper San Pedro River.
  Scott et al. (2008, *J. Arid Environ.* 72:1232, doi:10.1016/j.jaridenv.2008.01.001) derived groundwater use from eddy
  covariance at the San Pedro riparian sites. The woodland site had the densest phreatophytes and the steadiest groundwater use.
- **The model has no access to that water.** A single-point CLM column has no lateral groundwater inflow: model ET is
  251 mm/yr ≈ precipitation, the water table sits at 8.6 m, and BTRAN is 0.08–0.20 from May to October. So FATES GPP cannot
  reach the tower whatever the vegetation parameters.
- **Secondary, for the record.** The 74 % DBF (FATES PFT 6, cold-deciduous) contributes no GPP; all model GPP is from C4 grass.
  - The cold-deciduous leaf-on counter shows no leaf-on event for ~770 years, and the site has ≤ 10 chilling days per year.
  - The real mesquite is drought-deciduous.
  - US-SRM (DBF 35 %) shows the same counters. Warm, dry sites with DBF (US-SRM, US-SRG, US-Ton) should be checked when the
    PFT mapping is revisited.

### CZ-Stn and DE-Lnf (DBF 100, collapse) — under investigation

What is ruled out:
- PFT set-up, parameter file and namelist are identical to the B03 reference DE-Hzd.
- Both are cold starts.
- Forcing matches the tower (CZ-Stn: T −0.00 K, P × 1.00, SW × 1.00). All unit and coverage checks pass.

When the vegetation goes: AD year 15 (CZ-Stn) and AD year 14 (DE-Lnf). DE-Hzd persists. Both sites' AD history has only seven
variables, so the cause cannot be seen yet.

Suspects:
1. **Soil.** The two sites have identical soil profiles although they are 500 km apart: sand 43–63 %, clay 8–11 %, identical
   organic matter. The register lists both as "template fsurdat texture, not observed". DE-Lnf is a silty loess Luvisol, which
   does not fit 43–63 % sand.
2. **Shallow bedrock at DE-Lnf:** 1.26 m (DE-Hzd 20.9 m, CZ-Stn 7.1 m).
3. **The reference is not clean.** DE-Hzd's EC P_F, and therefore its forcing, gives **3169 mm/yr**, an implausible value for
   Saxony that needs checking in the EC file. DE-Hzd may survive partly because of this extra water. DE-Hai (B01, DBF, normal
   precipitation) is the reference from now on.

Next steps:
- 09 diagnostic re-run of the first 50 AD years for CZ-Stn and DE-Lnf (`*_B03_FIXNC_AD400_DIAG50`).
- Then run 08 (mortality type), 10 (BTRAN / soil water) and 11/12 (carbon budget, carbon starvation), with DE-Hai as the living
  reference.
- Hypothesis to test: water stress on the coarse template soil (and shallow bedrock) leads to carbon-starvation or hydraulic
  mortality.

## 12. Typical GPP and NEE error at the remaining sites (2026-11-01)

Sample: 40 sites. Excluded are sites with needleleaf ≥ 50 % of the vegetation, CZ-Stn, DE-Lnf, US-CMW (groundwater) and US-NR3
(EC GPP ≈ 0). Statistics come from the monthly paired figure titles (bias = mean(model − EC), g C m⁻² d⁻¹; annual = × 365). The
per-site values are added to `gpp_vs_ec_all_sites.csv` (`NEE_*`, `GPP_RMSE`).

| Group | n | GPP FATES/EC median (IQR) | within ±20 % | GPP R² median | NEE bias median | NEE > 0 (weaker sink) | NEE R² median |
|---|---:|---|---:|---:|---:|---:|---:|
| All 40 | 40 | 1.08 (0.88–1.80) | 20/40 | 0.30 | +0.23 (+84 g C m⁻² yr⁻¹) | 29/40 | −0.96 |
| Broadleaf / mixed forest | 18 | 1.02 (0.87–1.09) | 13/18 | 0.81 | +0.75 (+272) | 16/18 | 0.49 |
| Grassland | 8 | 0.98 (0.88–1.18) | 6/8 | 0.27 | +0.14 (+49) | 5/8 | −2.88 |
| Dryland / shrub | 8 | 1.88 (1.66–3.04) | 1/8 | −2.25 | +0.02 (+8) | 5/8 | −10.8 |
| Arctic tundra | 4 | 3.33 (2.13–4.07) | 0/4 | −3.24 | −0.03 (−11) | 1/4 | −1.56 |
| Tropical EBF (deferred) | 2 | 0.62 | 0/2 | −5.5 | +0.89 (+326) | 2/2 | −1.53 |

Reading:
- **Broadleaf / mixed forests: GPP is good.** The median ratio is 1.02, 13 of 18 are within ±20 %, and the seasonal R² is 0.81.
- **Forest NEE: the model is a weaker sink in 16 of 18 sites, by ≈ 270 g C m⁻² yr⁻¹.** This is largely by construction. After
  an 800-year spin-up with fixed vegetation and cycled forcing, the model ecosystem is near steady state (NEE ≈ 0). The towers
  measure real sinks (stand age and management, CO₂ and N deposition). The NEE bias therefore mostly equals the observed sink,
  not a flux-process error. The seasonal NEE timing is reasonable (R² 0.49).
- **Grasslands: annual GPP is right (0.98), but the seasonal shape is poor.** R² is 0.27 for GPP and negative for NEE at every
  site, consistent with mowing and grazing not being simulated.
- **Drylands (× 1.9) and arctic tundra (× 3.3) over-estimate GPP and have the wrong timing.** Absolute NEE errors there are
  small only because the fluxes are small.

## 13. Drylands and mixed forests checked with script 14 (2026-11-01)

Run: [`figures/AD400_NORMAL400_site_anomaly_diagnostics/20261101T064340Z`](../figures/AD400_NORMAL400_site_anomaly_diagnostics/20261101T064340Z/).
Values are annual totals over the last Normal forcing cycle, taken from the `*_normal_seasonal.csv` files.

| Site | Vegetated patch area (FATES) | Model ET | EC ET | Model T/ET | Model GPP | EC GPP | GPP/ET model vs EC (g C kg⁻¹) |
|---|---|---:|---:|---:|---:|---:|---|
| US-Seg (C4 60, bare 40) | 0.60 = 1 − bare | 213 | 223 | 0.46 | 311 | 163 | 1.46 vs 0.73 |
| ES-LJu (C3 31, shrub 20, bare 49) | 0.51 = 1 − bare | 316 | 252 | 0.65 | 904 | 302 | 2.86 vs 1.20 |
| US-Whs (shrubs 40, C4 3, bare 57) | 0.43 = 1 − bare | 280 | – (EC file not in default path) | 0.58 | 486 | ≈ 113 | – |

**Drylands:**
- **The bare-ground fraction is applied correctly.** FATES vegetated patch area equals 1 − bare at all three sites, so that
  hypothesis is ruled out.
- **Water use is about right** (US-Seg model ET = EC ET; ES-LJu +25 %).
- **Carbon gained per unit water is 2–2.4 × too high.**
- The over-estimate is therefore mainly a water-use-efficiency problem in the dryland PFTs (C4 grass, C3 grass, evergreen
  shrub), not water supply. Candidates:
  - Photosynthetic capacity and stomatal slope.
  - Too high a transpiration share at ES-LJu (T/ET 0.65 with 49 % bare ground).
  - EC GPP partitioning uncertainty at very small fluxes (a secondary caveat).
- US-Whs uses a custom parameter file (`fates_params_HYDRO_SHRUB_b05_v1.json`).

**Mixed forests — correction of section 12's reading:**
- At US-Ha1 (NET 27 %) and US-Slt (NET 38 %) the needleleaf PFT is **alive**:
  - Canopy crown area 0.20 / 0.32 of patch area 0.27 / 0.38.
  - It supplies 15 % / 23 % of GPP.
  - Annual BTRAN is 0.84 / 0.92.
- Their GPP ratios (0.84, 1.08) are therefore genuine, not compensation.
- With US-MtB, US-Vcp, US-Vcm and US-Mpj, that gives six sites where needleleaf survives. US-Ha1 (Harvard Forest, MA) vs US-Ho1
  (Howland, ME, collapsed) is a close-climate pair for comparing set-up and carbon budget (11/12).

## 14. Summary: which sites are wrong and why (2026-11-01, 75 sites)

Ratio = FATES / EC GPP. The status column says how far each explanation has been tested.

| Problem | Sites (ratio) | Cause | Status |
|---|---|---|---|
| Needleleaf collapse, GPP ≈ 0 | FI-Sod, CH-Dav, IL-Yat, DE-Obe, IT-Ren, CZ-BK1, CA-Ca3, CA-LP1, US-NC2, US-GLE, FI-Hyy (0–0.03) | FATES carbon-starvation mortality of PFT 2 | confirmed (sections 7–8); fix trials A–E running |
| Needleleaf part lost, other PFTs alive | US-Ho2 0.08, DE-Tha 0.09, RU-Fyo 0.09, US-Ho1 0.10, BE-Bra 0.18, US-Ho3 0.19, FR-FBn 0.19, FI-Let 0.21, US-SP1 0.22, US-NR1 0.25, BE-Vie 0.31, US-Me2 0.34, IT-Lav 0.42, US-Me6 0.48, CA-TP4 0.55 | same | same |
| Broadleaf collapse | CZ-Stn, DE-Lnf (≈ 0) | unknown; suspects are template soil, shallow bedrock (DE-Lnf), water stress | 50-year diagnostic re-runs submitted |
| Groundwater-dependent | US-CMW 0.28 | EC ET 2.5 × precipitation; a single-point column cannot supply it | confirmed; site excluded |
| Dryland over-estimate | US-Whs 4.22, US-Ses 3.09, ES-LJu 3.02, US-Seg 1.91, US-Wkg 1.84, IT-Noe 1.78, US-SRM 1.27 | GPP per unit water 2–2.4 × too high; bare fraction correct; water use about right | confirmed at US-Seg and ES-LJu; the others are not yet checked |
| Arctic over-estimate | US-ICh 4.15, US-ICt 4.05, US-EML 2.62 | not diagnosed | open |
| Annual-grass phenology | US-Var 2.19 | model GPP 3–4 g C m⁻² d⁻¹ in autumn–winter while EC ≈ 0; the annual-grass life cycle is not representable with perennial C3 grass | inferred from the figure |
| Other over-estimates | US-Vcm 2.17, US-Rpf 2.01, US-Ton 1.41, US-UiD 1.34 | not diagnosed (US-Ton: possible annual grass and warm-climate DBF) | open |
| Cold-deciduous DBF never leafs in warm climates | US-SRM (DBF 35 %), US-CMW; probably US-SRG, US-Ton | FATES cold-deciduous phenology needs chilling; no leaf-on for ~770 years | confirmed at US-SRM and US-CMW (counters, PFT GPP); US-SRG and US-Ton to check |
| Mild under-estimate | FR-Pue 0.75, DK-Sor 0.76, US-BZS 0.68 | not diagnosed | open |
| Tropical under-estimate | GF-Guy 0.57, BR-Ma2 0.68 | not diagnosed | deferred |
| Annual mean right, seasonal shape wrong | CH-Cha (R² 0.23), CH-Fru 0.41, IT-MBo 0.32, US-Kon −0.06, US-Mpj −2.1, US-Wjs −6.1, US-SRG −1.8 | CH-Cha: model grass drops all leaves in dry summers; managed grasslands: mowing and grazing not simulated; drylands: monsoon timing | partly inferred from figures |
| EC data problem | US-NR3 (EC GPP ≈ 0), DE-Hzd (precipitation 3169 mm/yr in P_F and forcing) | data | to check |
| Accurate (within ±25 %, R² ≥ 0.65) | DE-Hai, FR-Hes, FR-Fon, IT-Col, US-UMB, US-UMd, US-MMS, US-MOz, US-WCr, US-Syv, US-Ha1, US-Slt, CH-Lae, AT-Neu, DE-Hzd | – | – |

NEE in all forest sites is systematically a weaker sink than the towers (section 12). This follows from the steady-state
spin-up, not from per-site errors.

## Scripts (branch `full-sequence-gpp-nee-ec`, commit 80ec742)

| Script | Purpose |
|---|---|
| [07_plot_full_sequence_GPP_NEE_with_EC.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py) | 800-year GPP/NEE/NPP/LAI per site with EC reference and flags |
| [08_diagnose_collapse_mortality.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/08_diagnose_collapse_mortality.py) | mortality by type, carbon balance, storage, density, recruitment; GPP reproduction check |
| [09_clone_AD_diag_rerun.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/09_clone_AD_diag_rerun.py) | clone an AD case, change only history output and length, verify `lnd_in`, submit |
| [10_diagnose_btran_soil.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/10_diagnose_btran_soil.py) | layer-by-layer BTRAN recomputation, soil water/ice/temperature, roots, canopy cover |
| [11_diagnose_carbon_budget.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/11_diagnose_carbon_budget.py) | per-plant / per-leaf carbon budget, carbon use, PFT parameter differences |
| [12_check_cstarvation.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/80ec74268420e560af068b7c2c457005a243407b/examples/Cross_cohort_NORMAL400/scripts/12_check_cstarvation.py) | carbon-starvation formula vs history output, settings in use |
| [14_diagnose_site_anomalies.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/a64fd99ed6188d406e13723fefe1d0c818f04e88/examples/Cross_cohort_NORMAL400/scripts/14_diagnose_site_anomalies.py) | set-up, forcing vs EC, early AD and water-balance check of a site against a working reference |
| [13_needleleaf_param_trials.py](https://github.com/lyanyeung/Non-Competition-CLM-experiment/blob/7f4187c4d5a75f11a91679edb7e2f016ed615385/examples/Cross_cohort_NORMAL400/scripts/13_needleleaf_param_trials.py) | needleleaf fix trials: private parameter copies, clone, verify, submit |

All are read-only except 09 and 13 (create new `*_DIAG50` / `*_FIX?50` cases and parameter copies; originals untouched). Each has a unit test on
synthetic history in the same folder.
