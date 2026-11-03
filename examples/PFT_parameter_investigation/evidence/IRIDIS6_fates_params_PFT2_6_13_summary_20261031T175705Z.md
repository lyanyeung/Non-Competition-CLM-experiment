<!-- Output of scripts/01_compare_fates_pft_parameters.py on IRIDIS6, 31 Oct 2026, for the parameter file the runs use -->
# FATES PFT parameter comparison

File: `/iridisfs/scratch/ly3n24/CLM_FATES/CTSM/src/fates/parameter_files/fates_params_default.json`  (14 PFTs)  |  generated 2026-10-31T17:57:05.017785+00:00
Selected: pft2_needleleaf_evergreen_extratrop_tree, pft6_broadleaf_colddecid_extratrop_tree, pft13_cool_c3_grass

File history attribute: 05/11/25, First instantation, copied from: ../parameter_files/fates_params_default.cdl.

## Suspect parameters (selected PFTs)

| parameter | sub | PFT 2 | PFT 6 | PFT 13 | units | why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| fates_leaf_slamax |  | 0.0954 | 0.0954 | 0.05 | m^2/gC | SLA cap deeper in the canopy |
| fates_leaf_slatop |  | 0.005 | 0.03 | 0.05 | m^2/gC | leaf area per unit leaf C; low SLA = little leaf area per kg leaf C |
| fates_leaf_vcmax25top | leafage_class0 | 62 | 58 | 78 | umol CO2/m^2/s | photosynthetic capacity per leaf area |
| fates_maintresp_leaf_atkin2017_baserate |  | 1.5 | 1.756 | 2.196 | umol CO2/m^2/s | leaf MR per leaf area (used with atkin2017) |
| fates_maintresp_leaf_ryan1991_baserate |  | 2.525e-06 | 2.525e-06 | 2.525e-06 | gC/gN/s | leaf MR per g N (used with fates_leafresp_model = ryan1991) |
| fates_allom_blca_expnt_diff |  | -0.34 | -0.35 | -0.487 | unitless | crown-area exponent offset |
| fates_allom_d2bl1 |  | 0.07 | 0.07 | 4.000e-04 | variable | leaf C vs DBH intercept (kg C, not area) |
| fates_allom_d2bl2 |  | 1.523 | 1.4 | 1.709 | variable | leaf C vs DBH exponent |
| fates_allom_d2ca_coefficient_max |  | 0.3694 | 1.155 | 0.0408 | m2 cm^(-1/beta) | crown area vs DBH coefficient |
| fates_allom_d2ca_coefficient_min |  | 0.3694 | 1.155 | 0.0408 | m2 cm^(-1/beta) | crown area vs DBH coefficient |
| fates_allom_l2fr |  | 1 | 1 | 0.67 | gC/gC | fine-root C per leaf C (root MR and turnover cost) |
| fates_alloc_storage_cushion |  | 1.2 | 1.2 | 1.2 | fraction | storage target relative to leaf C |
| fates_turnover_fnrt |  | 2 | 1 | 1 | yr | fine-root longevity (yr) |
| fates_turnover_leaf_canopy | leafage_class0 | 4 | 1 | 1 | yr | leaf longevity in canopy (yr) |
| fates_turnover_leaf_ustory | leafage_class0 | 4 | 1 | 1 | yr | leaf longevity in understory (yr) |
| fates_stoich_nitr | fnrt | 0.024 | 0.024 | 0.024 | gN/gC | leaf/root N per C -> maintenance respiration (Ryan 1991 is per g N) |
| fates_stoich_nitr | leaf | 0.029 | 0.04 | 0.04 | gN/gC | leaf/root N per C -> maintenance respiration (Ryan 1991 is per g N) |
| fates_stoich_nitr | sapw | 1.000e-08 | 1.000e-08 | 1.000e-08 | gN/gC | leaf/root N per C -> maintenance respiration (Ryan 1991 is per g N) |
| fates_stoich_nitr | struct | 0.0047 | 0.0047 | 0.0047 | gN/gC | leaf/root N per C -> maintenance respiration (Ryan 1991 is per g N) |
| fates_phen_drought_threshold |  | -1.530e+05 | -1.530e+05 | -1.530e+05 | m3/m3 or mm | soil water / potential that triggers drought leaf-off |
| fates_phen_leaf_habit |  | 1 | 2 | 3 | flag | 1 evergreen, 2 cold-deciduous, 3 stress(drought)-deciduous |
| fates_phen_mindaysoff |  | 100 | 100 | 100 | days | minimum days leaves stay off |
| fates_phen_moist_threshold |  | -1.224e+05 | -1.224e+05 | -1.224e+05 | m3/m3 or mm | soil water / potential for leaf-on after drought |
| fates_mort_freezetol |  | -55 | -80 | -20 | degrees C | freezing mortality threshold (degC) |
| fates_mort_scalar_cstarvation |  | 0.6 | 0.6 | 0.6 | 1/yr | max carbon-starvation mortality |
| fates_recruit_height_min |  | 1.3 | 1.3 | 0.2 | m | recruit height |
| fates_recruit_init_dbh |  | 1 | 1 | 0.1 | cm | nocomp closed-canopy init DBH (only with use_fates_dbh_init) |
| fates_recruit_init_density |  | 0.2 | 0.2 | 0.2 | stems/m2 | cold-start seedling density |
| fates_recruit_seed_alloc |  | 0.1 | 0.1 | 0 | fraction | seed allocation |
| fates_recruit_seed_alloc_mature |  | 0 | 0 | 0.25 | fraction | seed allocation of mature plants |
| fates_recruit_seed_dbh_repro_threshold |  | 80 | 80 | 3 | cm | DBH at which mature seed allocation starts |
| fates_recruit_seed_germination_rate |  | 0.5 | 0.5 | 0.5 | yr-1 | germination rate |
| fates_nonhydro_smpsc |  | -2.550e+05 | -2.550e+05 | -2.550e+05 | mm | soil potential at full stomatal closure |
| fates_nonhydro_smpso |  | -6.6e+04 | -6.6e+04 | -6.6e+04 | mm | soil potential at full stomatal opening |

## Derived leaf economics and per-tree allometry

Leaf area uses canopy-top SLA (a lower bound: FATES raises SLA with canopy depth up to slamax). Crown area assumes site spread = 1. Respiration at 20 C before temperature and canopy scaling.

| quantity | PFT 2 | PFT 6 | PFT 13 |
| --- | ---: | ---: | ---: |
| leafC_per_area_gC_m2 | 200 | 33.33 | 20 |
| leafN_per_area_gN_m2 | 5.8 | 1.333 | 0.8 |
| vcmax25top | 62 | 58 | 78 |
| Rd_ryan1991_20C_umol_m2_s | 1.219 | 0.2803 | 0.1682 |
| Rd_atkin2017_base_umol_m2_s | 1.5 | 1.756 | 2.196 |
| Rd_ryan_over_vcmax25 | 0.01967 | 0.004833 | 0.002156 |
| leaf_turnover_canopy_yr | 4 | 1 | 1 |
| leafC_replacement_gC_m2leaf_yr | 50 | 33.33 | 20 |
| l2fr | 1 | 1 | 0.67 |
| fnrt_turnover_yr | 2 | 1 | 1 |
| dbh5_leafC_kg | 0.4064 | 0.3331 | nan |
| dbh5_leafarea_m2 | 2.032 | 9.992 | nan |
| dbh5_crownarea_m2 | 2.481 | 6.26 | nan |
| dbh5_crownLAI | 0.8189 | 1.596 | nan |
| dbh5_leaf_plus_fnrt_MR_20C_gC_day | 4.698 | 4.651 | nan |
| dbh10_leafC_kg | 1.168 | 0.8789 | nan |
| dbh10_leafarea_m2 | 5.841 | 26.37 | nan |
| dbh10_crownarea_m2 | 5.635 | 12.96 | nan |
| dbh10_crownLAI | 1.037 | 2.035 | nan |
| dbh10_leaf_plus_fnrt_MR_20C_gC_day | 13.51 | 12.27 | nan |
| dbh20_leafC_kg | 3.358 | 2.319 | nan |
| dbh20_leafarea_m2 | 16.79 | 69.58 | nan |
| dbh20_crownarea_m2 | 12.8 | 26.83 | nan |
| dbh20_crownLAI | 1.312 | 2.593 | nan |
| dbh20_leaf_plus_fnrt_MR_20C_gC_day | 38.83 | 32.38 | nan |
| dbh30_leafC_kg | 6.228 | 4.091 | nan |
| dbh30_leafarea_m2 | 31.14 | 122.7 | nan |
| dbh30_crownarea_m2 | 20.68 | 41.07 | nan |
| dbh30_crownLAI | 1.506 | 2.989 | nan |
| dbh30_leaf_plus_fnrt_MR_20C_gC_day | 72.01 | 57.13 | nan |

## All differing PFT parameters (64 rows)

| category | parameter | sub | PFT 2 | PFT 6 | PFT 13 | units |
| --- | --- | --- | ---: | ---: | ---: | --- |
| leaf/photosynthesis | fates_leaf_slamax |  | 0.0954 | 0.0954 | 0.05 | m^2/gC |
| leaf/photosynthesis | fates_leaf_slatop |  | 0.005 | 0.03 | 0.05 | m^2/gC |
| leaf/photosynthesis | fates_leaf_vcmax25top | leafage_class0 | 62 | 58 | 78 | umol CO2/m^2/s |
| leaf/photosynthesis | fates_maintresp_leaf_atkin2017_baserate |  | 1.5 | 1.756 | 2.196 | umol CO2/m^2/s |
| leaf/photosynthesis | fates_leaf_stomatal_slope_medlyn |  | 2.3 | 4.4 | 5.3 | KPa**0.5 |
| allometry | fates_allom_blca_expnt_diff |  | -0.34 | -0.35 | -0.487 | unitless |
| allometry | fates_allom_d2bl1 |  | 0.07 | 0.07 | 4.000e-04 | variable |
| allometry | fates_allom_d2bl2 |  | 1.523 | 1.4 | 1.709 | variable |
| allometry | fates_allom_d2ca_coefficient_max |  | 0.3694 | 1.155 | 0.0408 | m2 cm^(-1/beta) |
| allometry | fates_allom_d2ca_coefficient_min |  | 0.3694 | 1.155 | 0.0408 | m2 cm^(-1/beta) |
| allometry | fates_allom_l2fr |  | 1 | 1 | 0.67 | gC/gC |
| allometry | fates_allom_agb1 |  | 0.3956 | 0.08038 | 0.001 | variable |
| allometry | fates_allom_agb2 |  | 0.8295 | 1.022 | 1.659 | variable |
| allometry | fates_allom_agb3 |  | 1.94 | 1.94 | 1.248 | variable |
| allometry | fates_allom_agb4 |  | 0.931 | 0.931 | -999.9 | variable |
| allometry | fates_allom_agb_frac |  | 0.6 | 0.6 | 1 | fraction |
| allometry | fates_allom_amode |  | 3 | 3 | 5 | index |
| allometry | fates_allom_d2bl3 |  | 0.55 | 0.55 | 0.3417 | unitless |
| allometry | fates_allom_d2h1 |  | 306.8 | 31.46 | 0.1812 | variable |
| allometry | fates_allom_d2h2 |  | 0.7524 | 0.9734 | 0.6384 | variable |
| allometry | fates_allom_d2h3 |  | 196.7 | 16.59 | -999.9 | variable |
| allometry | fates_allom_dbh_maxheight |  | 1000 | 1000 | 20 | cm |
| allometry | fates_allom_fnrt_prof_a |  | 7 | 6 | 11 | unitless |
| allometry | fates_allom_h2cd1 |  | 0.5 | 0.5 | 1 | variable |
| allometry | fates_allom_hmode |  | 5 | 5 | 3 | index |
| allometry | fates_allom_lmode |  | 2 | 2 | 5 | index |
| allometry | fates_allom_smode |  | 1 | 1 | 2 | index |
| allometry | fates_allom_zroot_max_dbh |  | 100 | 100 | 2 | cm |
| allometry | fates_allom_zroot_min_dbh |  | 1 | 2.5 | 0.1 | cm |
| turnover | fates_turnover_fnrt |  | 2 | 1 | 1 | yr |
| turnover | fates_turnover_leaf_canopy | leafage_class0 | 4 | 1 | 1 | yr |
| turnover | fates_turnover_leaf_ustory | leafage_class0 | 4 | 1 | 1 | yr |
| turnover | fates_turnover_branch |  | 150 | 150 | 0 | yr |
| stoichiometry | fates_stoich_nitr | leaf | 0.029 | 0.04 | 0.04 | gN/gC |
| stoichiometry | fates_stoich_phos | leaf | 0.0029 | 0.004 | 0.004 | gP/gC |
| phenology | fates_phen_leaf_habit |  | 1 | 2 | 3 | flag |
| mortality | fates_mort_freezetol |  | -55 | -80 | -20 | degrees C |
| recruitment/seed | fates_recruit_height_min |  | 1.3 | 1.3 | 0.2 | m |
| recruitment/seed | fates_recruit_init_dbh |  | 1 | 1 | 0.1 | cm |
| recruitment/seed | fates_recruit_seed_alloc |  | 0.1 | 0.1 | 0 | fraction |
| recruitment/seed | fates_recruit_seed_alloc_mature |  | 0 | 0 | 0.25 | fraction |
| recruitment/seed | fates_recruit_seed_dbh_repro_threshold |  | 80 | 80 | 3 | cm |
| radiation | fates_rad_leaf_clumping_index |  | 0.85 | 0.9 | 0.75 | fraction (0-1) |
| radiation | fates_rad_leaf_rhonir |  | 0.41 | 0.41 | 0.28 | fraction |
| radiation | fates_rad_leaf_rhovis |  | 0.09 | 0.08 | 0.05 | fraction |
| radiation | fates_rad_leaf_taunir |  | 0.32 | 0.43 | 0.4 | fraction |
| radiation | fates_rad_leaf_tauvis |  | 0.04 | 0.06 | 0.05 | fraction |
| radiation | fates_rad_leaf_xl |  | 0.01 | 0.59 | -0.23 | unitless |
| radiation | fates_rad_stem_rhonir |  | 0.36 | 0.49 | 0.53 | fraction |
| radiation | fates_rad_stem_rhovis |  | 0.12 | 0.21 | 0.31 | fraction |
| radiation | fates_rad_stem_taunir |  | 0.001 | 0.001 | 0.25 | fraction |
| radiation | fates_rad_stem_tauvis |  | 0.001 | 0.001 | 0.12 | fraction |
| other | fates_hlm_pft_map | hlm1 | 1 | 0 | 0 | area fraction |
| other | fates_hlm_pft_map | hlm13 | 0 | 0 | 1 | area fraction |
| other | fates_hlm_pft_map | hlm2 | 1 | 0 | 0 | area fraction |
| other | fates_hlm_pft_map | hlm7 | 0 | 1 | 0 | area fraction |
| other | fates_hlm_pft_map | hlm8 | 0 | 1 | 0 | area fraction |
| other | fates_landuse_grazing_palatability |  | 0 | 0 | 1 | unitless 0-1 |
| other | fates_landuse_harvest_pprod10 |  | 0.75 | 0.75 | 1 | fraction |
| other | fates_landuse_luc_frac_exported |  | 0.4 | 0.4 | 0 | fraction |
| other | fates_landuse_luc_pprod10 |  | 0.75 | 0.75 | 1 | fraction |
| other | fates_turb_z0mr |  | 0.055 | 0.055 | 0.12 | unitless |
| other | fates_wood_density |  | 0.4424 | 0.5665 | 0.7 | g/cm3 |
| other | fates_woody |  | 1 | 1 | 0 | logical flag |

## Scalar parameters in respiration / phenology / mortality / allocation groups (15)

| parameter | value | units |
| --- | ---: | --- |
| fates_canopy_closure_thresh | 0.8 | unitless |
| fates_leaf_photo_temp_acclim_thome_time | 30 | years |
| fates_leaf_photo_temp_acclim_timescale | 30 | days |
| fates_maintresp_nonleaf_baserate | 2.525e-06 | gC/gN/s |
| fates_mort_disturb_frac | 1 | fraction |
| fates_mort_understorey_death | 0.5598 | fraction |
| fates_phen_chilltemp | 5 | degrees C |
| fates_phen_coldtemp | 7.5 | degrees C |
| fates_phen_gddthresh_a | -68 | none |
| fates_phen_gddthresh_b | 638 | none |
| fates_phen_gddthresh_c | -0.01 | none |
| fates_phen_mindayson | 90 | days |
| fates_phen_ncolddayslim | 5 | days |
| fates_q10_froz | 1.5 | unitless |
| fates_q10_mr | 1.5 | unitless |

OUTPUT: /home/ly3n24/FATES_PFT_param_compare_20261031T175705Z
