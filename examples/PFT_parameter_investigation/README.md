# PFT parameter investigation: needleleaf evergreen (FATES PFT 2) and C3 grass (PFT 13)

Opened 31 October 2026. **Status: evidence collected; IRIDIS6 parameter file checked (identical to the upstream default for PFT 2, 6, 13); no parameter change made.**

Under fixed biogeography + no competition (FIXNC), GPP is far below the EC towers at almost every
needleleaf site, and grassland sites show repeated die-back episodes. This document collects the evidence,
the parameter analysis done so far, the hypotheses, and the code to continue. Every number below has a
source file in this folder or a published figure; nothing here is a conclusion yet.

## 1 Summary

| | Needleleaf ENF (FATES PFT 2) | C3 grass (FATES PFT 13) |
| --- | --- | --- |
| Annual GPP vs EC (last Normal cycle) | 0.04–0.42× EC at the 9 non-collapsed ENF sites; GPP≈0 at 9 more | 0.82–1.07× EC (AT-Neu, CH-Cha, CH-Fru, IT-MBo) |
| Pattern over 800 years | either a flat, very low level from the first decades, or decline to zero (years 1–267) | regular deep dips that repeat every forcing cycle |
| Mechanism seen in output | NL-Loo: PFT 2 patch is 93.6 % of the area but gives 9 % of GPP; ~290 saplings ha⁻¹, 2 % crown cover; 82 % of PFT-2 mortality C flux is carbon starvation | dips are forcing-year driven (same position every cycle), not random demography |
| Leading parameter suspects | leaf C allometry not matched to the low needle SLA → ~4.5× less leaf area per tree than broadleaf at equal maintenance cost; Ryan-1991 leaf respiration ×4 per leaf area | stress-deciduous habit with `fates_phen_mindaysoff` = 100 d; `fates_mort_freezetol` = −20 °C |
| Confidence | high that PFT 2 is the problem; parameter cause still a hypothesis | low – may be parameters, missing management, or forcing |

Earlier full-competition runs scored better on GPP (30 paired sites: 7 better / 23 worse for FIXNC;
ENF 1 / 12), but there the needleleaf and grassland sites were **taken over by broadleaf cold-deciduous trees
(91.7–99.6 % of vegetation C)**: the better scores came from the wrong vegetation.

## 2 Evidence

### 2.1 NL-Loo: three PFTs side by side in one site (PRE50, last year)

Source: [`evidence/NL-Loo_low_GPP_inputs_report_20261031T004536Z.txt`](evidence/NL-Loo_low_GPP_inputs_report_20261031T004536Z.txt)
([script](../../scripts/18_NL_Loo_low_GPP_inputs_report.py)). `_PF` fields are site means and sum to `FATES_GPP`;
"own patch" values divide by the PFT area fraction.

| FATES PFT | area | share of site GPP | own-patch GPP (g C m⁻² d⁻¹) | own-patch veg C (kg C m⁻²) | crown cover |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 needleleaf evergreen | 93.6 % | 9 % | 0.04 | 0.04 | ~2 % |
| 6 broadleaf cold-deciduous | 2.9 % | 35 % | 4.6 | 7.8 | ~99 % |
| 13 C3 grass | 3.5 % | 56 % | 6.0 | 1.1 | ~100 % |

Same forcing, soil and site: broadleaf and grass patches are productive, the needleleaf patch is not.
Ruled out or down-weighted for NL-Loo:
- **water stress:** layer SMP ≈ −0.01 MPa against the −0.66 MPa opening threshold, and the water table is at 3.4 m. The `BTRAN` value of 0.086 equals the canopy crown-area fraction (0.0861), so it is an area-averaging artefact.
- **forcing:** T ≈ 10 °C, SW 113–135 W m⁻², precipitation 690–960 mm yr⁻¹.
- **surface:** 0 % bare ground, and the HLM→FATES mapping is correct.

Full-sequence GPP is continuous across PRE50→AD200 (+1.5 %); see
[`evidence/NL-Loo_GPP_full_sequence_summary_20261031.txt`](evidence/NL-Loo_GPP_full_sequence_summary_20261031.txt).

### 2.2 All job-4764252 sites: 800-year GPP with EC reference

Published figures: [`figures/AD400_NORMAL400_full_sequence/20261031T005421Z_from_job4764252`](../../figures/AD400_NORMAL400_full_sequence/20261031T005421Z_from_job4764252/README.md)
([script](../Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py)).

- **ENF, low but stable.** Last-cycle GPP as a fraction of EC: BE-Bra 0.19, DE-Tha 0.09, FI-Hyy 0.04, FI-Let 0.20, FR-FBn 0.19, IT-Lav 0.42, RU-Fyo 0.09, US-Ho1 0.10, US-SP1 0.22. US-Ho2 and US-Ho3 (spruce) are also low, at 0.4–0.8 g C m⁻² d⁻¹, but have no EC reference.
- **ENF and other conifers, GPP → 0.** The spin-up year from which GPP stays near zero:

  | Site | Year | Site | Year | Site | Year |
  | --- | ---: | --- | ---: | --- | ---: |
  | FI-Sod | 1 | US-GLE | 4 | CA-LP1 | 12 |
  | CA-Ca3 | 41 | DE-Obe | 49 | CZ-BK1 | 50 |
  | CH-Dav | 72 | IT-Ren | 267 | IL-Yat | 1 |

  IL-Yat (Aleppo pine) is semi-arid with 52 % bare ground.
- **DBF, close to EC.** DE-Hai 0.99, FR-Fon 0.96, FR-Hes 0.95, DE-Hzd 1.08, CH-Lae 0.89, IT-Col 0.86, US-Ha1 0.84, DK-Sor 0.76.
- **Separate open issue, DBF.** CZ-Stn and DE-Lnf (beech) rise to EC-level GPP and then crash to zero at years 14–15. This is not covered here.
- **Grass.** Annual GPP is 0.82–1.07× EC, but there are periodic deep dips in every forcing cycle: CH-Fru drops to ~1.8, IT-MBo to ~0.3, and CH-Cha has several dips.
- **Secondary flag.** GPP or LAI steps of 10–45 % at the hybrid restart 400/401 appear at several sites (DE-Hzd LAI −29 %, IT-MBo GPP +45 %). Vegetation should be continuous there, so this is worth a separate check.

### 2.3 Competition runs vs FIXNC (30 paired sites, monthly EC metrics)

Source: [`evidence/competition_vs_nocomp_GPP_NEE_monthly_metrics.csv`](evidence/competition_vs_nocomp_GPP_NEE_monthly_metrics.csv)
([script](scripts/02_compare_competition_vs_nocomp_flux_metrics.py)). Old runs come from
[CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows) (`*_monthly_metrics.csv`).
The FIXNC values were read by OCR from the job-4764252 figure titles, with the check RMSE ≥ |bias| applied.

| class | n | FIXNC GPP RMSE lower / higher | mean GPP bias, competition → FIXNC |
| --- | ---: | --- | --- |
| ENF | 13 | 1 / 12 | +0.26 → −3.56 |
| DBF | 7 | 3 / 4 | +0.25 → −0.92 |
| GRA | 4 | 0 / 4 | −0.20 → −0.65 |
| MF | 3 | 1 / 2 | +0.14 → −2.44 |
| EBF / OSH | 3 | 2 / 1 | |
| **all** | 30 | **7 / 23** | +0.20 → −2.20 (median RMSE 2.23 → 3.86, median R² 0.64 → −0.53) |

**Dominant PFT in the old runs at year 1000.** These values are the share of vegetation C, not area (from `carbon_flux_convergence_diagnostics/data/15_site_ec_observed_vegetation_and_fates_match.csv` in that repository).
- Broadleaf cold-deciduous at 91.7–99.6 %: NL-Loo, RU-Fyo, DE-Tha, BE-Bra, FI-Sod, AT-Neu, CH-Cha and CH-Fru.
- C3 or C4 grass at 100 %: CZ-Stn (beech) and IL-Yat (pine).

**NEE: no evidence of improvement.** Mean NEE bias is almost identical in both runs (+0.80 vs +0.84), because spun-up models are near carbon-neutral while the towers are sinks. The lower FIXNC NEE RMSE (19 of 30 sites) comes from a damped seasonal cycle. Sites where vegetation collapsed, so that model NEE ≈ 0, score better than the old runs: IL-Yat 2.57 → 0.92, FI-Sod 1.50 → 0.87, DE-Obe 2.57 → 1.91.

**Comparison caveats.**
- EC GPP is `GPP_DT_VUT_REF` in the old runs and `GPP_NT_VUT_REF` first in FIXNC. At grassland sites NT peaks are visibly higher.
- Old metrics come from 1000-year, 500-year or snapshot cycles.
- The NL-Loo FIXNC value is the V3 PRE50 interim.

### 2.4 Grassland sites, competition vs FIXNC

Figures in [`evidence/grassland_old_vs_new/`](evidence/grassland_old_vs_new) (top: competition; bottom: FIXNC):
- FIXNC monthly GPP falls to ~0 for whole seasons in some forcing years: CH-Cha 2017, CH-Fru 2017 and 2019, IT-MBo 2004–2007.
- In the same months NEE shows large positive spikes, of up to +7–8 g C m⁻² d⁻¹.
- The competition runs (broadleaf forest at three of these sites) have smooth cycles and no gaps.

## 3 Parameter analysis (IRIDIS6 file = upstream FATES default for PFT 2, 6, 13)

[`evidence/upstream_fates_params_b8fbdde_PFT2_6_13/summary.md`](evidence/upstream_fates_params_b8fbdde_PFT2_6_13/summary.md)
was produced with [`scripts/01_compare_fates_pft_parameters.py`](scripts/01_compare_fates_pft_parameters.py) from NGEET/fates
master `b8fbdde` (25 Oct 2026). The same script run on IRIDIS6 against the file the runs use
(`CTSM/src/fates/parameter_files/fates_params_default.json`, history attribute "05/11/25, First instantation"),
[`evidence/IRIDIS6_fates_params_PFT2_6_13_summary_20261031T175705Z.md`](evidence/IRIDIS6_fates_params_PFT2_6_13_summary_20261031T175705Z.md),
gives identical values: all 64 differing rows, all suspect rows and all derived quantities for PFT 2, 6, 13
match the upstream file, so the analysis below applies to these runs.

**Needleleaf vs broadleaf, derived from the parameters** (canopy-top SLA; 2-power leaf and crown allometry):

| | PFT 2 needleleaf | PFT 6 broadleaf |
| --- | ---: | ---: |
| `fates_leaf_slatop` (m² g C⁻¹) | 0.005 | 0.03 |
| leaf C per leaf area (g C m⁻²) | 200 | 33 |
| leaf N per leaf area (g N m⁻²) | 5.8 | 1.33 |
| Ryan-1991 leaf Rd at 20 °C (µmol m⁻² s⁻¹) | 1.22 | 0.28 |
| Rd / Vcmax25 | 0.020 | 0.005 |
| `fates_allom_d2bl1`, `d2bl2` (leaf **C** vs DBH) | 0.07, 1.523 | 0.07, 1.40 |
| DBH 10 cm: leaf area per tree (m²) | 5.8 | 26.4 |
| DBH 10 cm: crown LAI | 1.04 | 2.04 |
| DBH 10 cm: leaf + fine-root maintenance resp. at 20 °C (g C d⁻¹) | 13.5 | 12.3 |
| leaf / fine-root longevity (yr) | 4 / 2 | 1 / 1 |

At the same size, a needleleaf tree carries about the same leaf **carbon** and leaf+root N as a broadleaf tree. That means the same maintenance cost, but only about one quarter of the leaf **area**, so roughly 4–5× less photosynthesis per unit respiration. That is consistent with saplings that never close the canopy and die of carbon starvation (§2.1).

History in the FATES parameter archive:
- `fates_leaf_slatop` for PFT 2 was **0.01** before API 24.1 (`archive/api24.1.0_101722_fates_params_default.cdl`).
- The October 2022 TRY-based patch (`archive/api24.1.0_101722_patch_params.xml`, J. Holm) set it to **0.005** and did not change `d2bl1` (0.07, the same as broadleaf).

`fates_leafresp_model = 'ryan1991'` in these runs (`lnd_in`). With `atkin2017`, the needleleaf base rate (1.5 µmol m⁻² s⁻¹) would be slightly *below* broadleaf (1.756), so the choice of leaf-respiration model changes the ENF/DBF contrast.

**Grass (PFT 13):**
- `fates_phen_leaf_habit` = 3 (stress-deciduous). Leaf-off is triggered at `fates_phen_drought_threshold` −152957 mm (≈ −1.5 MPa).
- `fates_phen_mindaysoff` = 100 days, which can turn a short drought into a lost season.
- `fates_mort_freezetol` = −20 °C (trees −55 / −80 °C), relevant at mountain sites such as IT-MBo.
- Seed: `seed_alloc` 0, `seed_alloc_mature` 0.25 above DBH 3 cm.

Initialisation: FATES now offers closed-canopy initialisation in nocomp mode (`use_fates_dbh_init = .true.` with `fates_recruit_init_dbh` and `fates_recruit_init_seed`). This is used by the upstream `patch_nocomp_noresm.json`; these runs use `use_fates_dbh_init = .false.` (cold start from 0.2 seedlings m⁻²). Initialisation alone should not keep a PFT at 0.04 g C m⁻² d⁻¹ for 800 years, but it may matter for sites that collapse in the first decades.

## 4 Hypotheses and tests (none run yet)

| # | Hypothesis | First test (cheap → expensive) |
| --- | --- | --- |
| H1 | PFT 2 leaf area per unit leaf C is too small (low SLA with broadleaf-like `d2bl1`), so the carbon balance is negative | Run `01` on the IRIDIS6 file; then one site (NL-Loo or FI-Hyy), 50-year Normal cold start, PFT 2 `slatop` 0.01 (pre-2022 value) **or** `d2bl1` scaled so leaf area matches the observed stand LAI |
| H2 | Ryan-1991 leaf respiration penalises high-N-per-area needles | Same site, `fates_leafresp_model = 'atkin2017'` (namelist only, all PFTs) |
| H3 | Fine-root cost (`l2fr` = 1 with 200 g C m⁻² leaves) adds to H1 | Read `FATES_FROOTC` / `FATES_MAINT_RESP` in the PRE50 history; sensitivity only after H1/H2 |
| H4 | Grass dips: stress-deciduous leaf-off with a 100-day minimum | Map dip years to forcing years and check soil potential / precipitation in those years; then `mindaysoff` sensitivity |
| H5 | Grass dips at IT-MBo: freezing mortality at −20 °C | Minimum TBOT of the dip years vs −20 °C |
| H6 | Missing grassland management (cutting / grazing) | Would make the model too high, not zero; explains NT-EC spikiness only |

Design rule: if parameters are changed, **one documented parameter set for all sites** (literature or
calibration provenance), not per-site tuning, so that sites stay comparable. Any change starts a new
spin-up; existing AD400 → Normal400 cases stay as the reference.

## 5 How to run

On IRIDIS6 (`clm_fates_env`), from a checkout of this branch:

```bash
# 1 parameter comparison of the file the runs actually use (default path), PFTs 2, 6, 13
python examples/PFT_parameter_investigation/scripts/01_compare_fates_pft_parameters.py
#   optional: --pfts 2 6 13 11   --other examples/.../another_params.json   --outdir DIR
#   writes summary.md, pft_params_all.csv, pft_params_differing.csv, derived_leaf_economics.csv, scalar_params.csv

# 2 (already done; reproducible anywhere with tesseract) competition vs FIXNC metrics
python examples/PFT_parameter_investigation/scripts/02_compare_competition_vs_nocomp_flux_metrics.py \
  --new-figs figures/AD400_NORMAL400/20261030T053000Z_job4764252 \
  --old-repo /path/to/CLM-FATES-single-site-workflows --registers data --outdir OUT \
  --extra "NL-Loo:348,-1.647,4.484,-3.762,348,-0.514,1.754,1.227"
```

Related scripts:
- [`scripts/17_plot_NL_Loo_GPP_full_sequence.py`](../../scripts/17_plot_NL_Loo_GPP_full_sequence.py): NL-Loo PRE50 → AD200 → POST300 GPP/NPP/LAI.
- [`scripts/18_NL_Loo_low_GPP_inputs_report.py`](../../scripts/18_NL_Loo_low_GPP_inputs_report.py): surface, FATES map and traits, DATM, and per-PFT history report.
- [`../Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py`](../Cross_cohort_NORMAL400/scripts/07_plot_full_sequence_GPP_NEE_with_EC.py): 800-year GPP/NEE/NPP/LAI with EC reference. Monthly CSVs now include `TWS` and `H2OSNO`, for H4/H5.

## 6 Files

| file | content |
| --- | --- |
| `scripts/01_compare_fates_pft_parameters.py` | read-only PFT parameter comparison, derived leaf economics and allometry |
| `scripts/02_compare_competition_vs_nocomp_flux_metrics.py` | OCR of FIXNC figure titles + paired comparison with competition metrics |
| `evidence/NL-Loo_low_GPP_inputs_report_20261031T004536Z.txt` | IRIDIS6 report: surface, PFT map, traits, DATM, PRE50/AD200 history |
| `evidence/NL-Loo_GPP_full_sequence_summary_20261031.txt` | NL-Loo PRE50/AD200 GPP, NPP, LAI continuity |
| `evidence/nocomp_EC_metrics_from_figure_titles.csv` | 47 FIXNC sites, monthly GPP/NEE N, R², RMSE, bias (+ NL-Loo PRE50) |
| `evidence/competition_vs_nocomp_GPP_NEE_monthly_metrics.csv` | 30 paired sites, both runs, IGBP, old dominant PFT |
| `evidence/grassland_old_vs_new/*.png` | AT-Neu, CH-Cha, CH-Fru, IT-MBo EC overviews, competition above FIXNC |
| `evidence/upstream_fates_params_b8fbdde_PFT2_6_13/` | output of script 01 on the upstream default file |
| `evidence/IRIDIS6_fates_params_PFT2_6_13_summary_20261031T175705Z.md` | output of script 01 on IRIDIS6 (the file the runs use) |

Limitations:
- **Parameter values and file versions.** Parameter values are checked against the IRIDIS6 file for PFT 2, 6 and 13 only. The archive history (SLA 0.01 → 0.005 in API 24.1) refers to the CDL defaults that preceded the JSON file.
- **Missing history fields.** The AD400 → Normal400 histories hold only seven fields (`TOTSOMC`, `TOTSOMN`, `TLAI`, `FATES_GPP`, `FATES_NPP`, `TWS`, `H2OSNO`), so per-PFT mechanisms come only from NL-Loo PRE50.
- **Monthly mean, not daily.** Monthly EC metrics hide daily errors.
