# AD400 → NORMAL400 full-sequence GPP / NEE / NPP / LAI with EC reference

Source cases: job 4764252 (`figures/AD400_NORMAL400/20261030T053000Z_job4764252`).
Thin line = monthly, thick = annual mean; AD400 red (shaded), NORMAL400 blue.
EC: climatological annual mean (dotted), peak/min month (dash-dot), range of complete-year annual means (band).
Model NEE = −FATES_NEP. Units g C m⁻² d⁻¹. AD rescales soil pools only: vegetation series should be continuous at 400/401.
Flags are automatic screening hints, not conclusions. 800 years is not proof of equilibrium.

- [All sites GPP overview](ALL_SITES_GPP_full_sequence_overview.png)
- [All sites NEE overview](ALL_SITES_NEE_full_sequence_overview.png)

| Site | Status | EC GPP | Model GPP (last cycle) | Ratio | EC NEE | Model NEE | Flags | Figure |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| AT-Neu | OK | 6.42 | 5.52 | 0.86 | 1.37 | -0.01 | GPP<0.05 in 1 years | [PNG](AT-Neu/AT-Neu_B03_FIXNC_NORMAL400/AT-Neu_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| BE-Bra | OK | 3.99 | 0.74 | 0.19 | -0.13 | -0.00 | GPP 0.19× EC | [PNG](BE-Bra/BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_NORMAL400/BE-Bra_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| BE-Vie | OK | 5.10 | 1.52 | 0.30 | -1.30 | -0.00 | GPP 0.30× EC | [PNG](BE-Vie/BE-Vie_B01_FIXNC_NORMAL400/BE-Vie_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| BR-Ma2 | OK | 9.18 | 6.24 | 0.68 | -1.20 | 0.00 |  | [PNG](BR-Ma2/BR-Ma2_AMF_FIXNC_NORMAL400_UTC_V2_PTS/BR-Ma2_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CA-Ca3 | MODEL_ONLY | – | 0.00 | – | – | 0.00 | GPP≈0 from year 41 | [PNG](CA-Ca3/CA-Ca3_AMF_FIXNC_NORMAL400_UTC_V2_PTS/CA-Ca3_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CA-LP1 | MODEL_ONLY | – | 0.00 | – | – | 0.00 | GPP≈0 from year 12 | [PNG](CA-LP1/CA-LP1_AMF_FIXNC_NORMAL400_UTC_V2_PTS/CA-LP1_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CA-TP4 | OK | 4.29 | 2.35 | 0.55 | -0.38 | -0.03 |  | [PNG](CA-TP4/CA-TP4_AMF_FIXNC_NORMAL400_UTC_V3_PTS/CA-TP4_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CH-Cha | OK | 7.16 | 5.89 | 0.82 | 0.09 | 0.03 | GPP step -15% at 400/401 | [PNG](CH-Cha/CH-Cha_B03_FIXNC_NORMAL400/CH-Cha_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CH-Dav | OK | 3.69 | 0.00 | 0.00 | -0.64 | 0.00 | GPP≈0 from year 72; GPP step -12% at 400/401; LAI step -15% at 400/401; GPP 0.00× EC | [PNG](CH-Dav/CH-Dav_B01_FIXNC_NORMAL400/CH-Dav_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CH-Fru | OK | 6.03 | 5.44 | 0.90 | -0.83 | 0.00 | GPP<0.05 in 1 years | [PNG](CH-Fru/CH-Fru_B02_FIXNC_NORMAL400/CH-Fru_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CH-Lae | OK | 4.64 | 4.12 | 0.89 | -0.56 | 0.00 | GPP step -12% at 400/401; LAI step -17% at 400/401 | [PNG](CH-Lae/CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_NORMAL400/CH-Lae_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CZ-BK1 | OK | 5.38 | 0.00 | 0.00 | -1.91 | 0.00 | GPP≈0 from year 50; GPP 0.00× EC | [PNG](CZ-BK1/CZ-BK1_B01_FIXNC_NORMAL400/CZ-BK1_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| CZ-Stn | OK | 4.37 | 0.00 | 0.00 | -0.85 | 0.00 | GPP≈0 from year 15; GPP 0.00× EC | [PNG](CZ-Stn/CZ-Stn_B03_FIXNC_NORMAL400/CZ-Stn_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DE-Hai | OK | 4.26 | 4.23 | 0.99 | -1.37 | -0.00 | LAI step -13% at 400/401 | [PNG](DE-Hai/DE-Hai_B01_FIXNC_NORMAL400/DE-Hai_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DE-Hzd | OK | 4.04 | 4.37 | 1.08 | 0.41 | -0.00 | GPP step -18% at 400/401; LAI step -29% at 400/401 | [PNG](DE-Hzd/DE-Hzd_B03_FIXNC_NORMAL400/DE-Hzd_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DE-Lnf | MODEL_ONLY | – | 0.00 | – | – | 0.00 | GPP≈0 from year 14 | [PNG](DE-Lnf/DE-Lnf_B03_FIXNC_NORMAL400/DE-Lnf_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DE-Obe | OK | 4.90 | 0.00 | 0.00 | -0.61 | 0.00 | GPP≈0 from year 49; GPP 0.00× EC | [PNG](DE-Obe/DE-Obe_B03_FIXNC_NORMAL400/DE-Obe_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DE-Tha | OK | 4.25 | 0.40 | 0.09 | -1.30 | 0.00 | GPP 0.09× EC | [PNG](DE-Tha/DE-Tha_OBSPFT_NC_V1_NORMAL400/DE-Tha_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| DK-Sor | OK | 5.71 | 4.32 | 0.76 | -0.66 | -0.00 |  | [PNG](DK-Sor/DK-Sor_B02_FIXNC_ICOS_DBF100_NORMAL400/DK-Sor_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| ES-LJu | OK | 0.83 | 2.48 | 3.00 | -0.07 | 0.00 | GPP 3.00× EC | [PNG](ES-LJu/ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_NORMAL400/ES-LJu_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FI-Hyy | OK | 3.19 | 0.13 | 0.04 | -0.62 | 0.00 | GPP 0.04× EC | [PNG](FI-Hyy/FI-Hyy_B02_FIXNC_NORMAL400/FI-Hyy_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FI-Let | OK | 3.46 | 0.68 | 0.20 | -0.07 | 0.00 | GPP 0.20× EC | [PNG](FI-Let/FI-Let_B03_FIXNC_NORMAL400/FI-Let_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FI-Sod | OK | 1.73 | 0.00 | 0.00 | 0.27 | 0.00 | GPP≈0 from year 1; GPP 0.00× EC | [PNG](FI-Sod/FI-Sod_B01_FIXNC_NORMAL400/FI-Sod_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FR-FBn | OK | 4.62 | 0.88 | 0.19 | -1.53 | 0.00 | GPP 0.19× EC | [PNG](FR-FBn/FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_NORMAL400/FR-FBn_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FR-Fon | OK | 4.99 | 4.80 | 0.96 | -1.61 | 0.02 | LAI step -13% at 400/401 | [PNG](FR-Fon/FR-Fon_B01_FIXNC_NORMAL400/FR-Fon_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FR-Hes | OK | 4.96 | 4.72 | 0.95 | -1.18 | -0.01 | LAI step +14% at 400/401 | [PNG](FR-Hes/FR-Hes_B02_FIXNC_NORMAL400/FR-Hes_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| FR-Pue | OK | 3.67 | 2.76 | 0.75 | -0.61 | 0.00 |  | [PNG](FR-Pue/FR-Pue_B01_FIXNC_NORMAL400/FR-Pue_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| GF-Guy | OK | 9.63 | 5.45 | 0.57 | -0.58 | -0.00 |  | [PNG](GF-Guy/GF-Guy_B03_FIXNC_NORMAL400/GF-Guy_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IL-Yat | OK | 1.59 | 0.00 | 0.00 | -0.25 | 0.00 | GPP≈0 from year 1; GPP 0.00× EC | [PNG](IL-Yat/IL-Yat_B03_FIXNC_BARE52_NORMAL400/IL-Yat_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IT-Col | OK | 4.45 | 3.84 | 0.86 | -2.24 | 0.01 | GPP step -13% at 400/401; LAI step -21% at 400/401 | [PNG](IT-Col/IT-Col_B01_FIXNC_NORMAL400/IT-Col_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IT-Lav | OK | 6.57 | 2.78 | 0.42 | -5.41 | -0.00 | GPP 0.42× EC | [PNG](IT-Lav/IT-Lav_B03_FIXNC_NORMAL400/IT-Lav_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IT-MBo | OK | 4.26 | 4.56 | 1.07 | -0.00 | 0.01 | GPP<0.05 in 1 years; GPP step +45% at 400/401; LAI step +42% at 400/401; GPP trend -12%/100y (last 100y); LAI trend -12%/100y (last 100y) | [PNG](IT-MBo/IT-MBo_B02_FIXNC_NORMAL400/IT-MBo_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IT-Noe | OK | 2.32 | 4.05 | 1.75 | -0.17 | -0.00 | GPP<0.05 in 3 years | [PNG](IT-Noe/IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_NORMAL400/IT-Noe_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| IT-Ren | OK | 4.44 | 0.00 | 0.00 | -1.94 | 0.00 | GPP≈0 from year 267; GPP 0.00× EC; GPP trend -258%/100y (last 100y); LAI trend -259%/100y (last 100y) | [PNG](IT-Ren/IT-Ren_B01_FIXNC_NORMAL400/IT-Ren_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| RU-Fyo | OK | 4.05 | 0.37 | 0.09 | 0.22 | -0.00 | LAI step +15% at 400/401; GPP 0.09× EC | [PNG](RU-Fyo/RU-Fyo_B01_FIXNC_NORMAL400/RU-Fyo_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-BZS | OK | 2.40 | 1.63 | 0.68 | -0.23 | -0.00 |  | [PNG](US-BZS/US-BZS_AMF_B02_FIXNC_NORMAL400_DIRECT/US-BZS_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-CMW | OK | 2.72 | 0.75 | 0.27 | -0.67 | 0.02 | GPP step -11% at 400/401; GPP 0.27× EC | [PNG](US-CMW/US-CMW_AMF_B02_FIXNC_NORMAL400_DIRECT/US-CMW_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-EML | OK | 1.17 | 2.89 | 2.46 | -0.03 | -0.05 | GPP<0.05 in 1 years; GPP 2.46× EC | [PNG](US-EML/US-EML_AMF_B02_FIXNC_NORMAL400_DIRECT/US-EML_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-GLE | OK | 1.90 | 0.00 | 0.00 | -0.03 | 0.00 | GPP≈0 from year 4; GPP 0.00× EC | [PNG](US-GLE/US-GLE_AMF_B02_FIXNC_NORMAL400_DIRECT/US-GLE_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ha1 | OK | 4.20 | 3.53 | 0.84 | -0.74 | 0.01 |  | [PNG](US-Ha1/US-Ha1_AMF_B02_FIXNC_NORMAL400_DIRECT/US-Ha1_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ho1 | OK | 2.65 | 0.26 | 0.10 | -1.08 | 0.00 | GPP 0.10× EC | [PNG](US-Ho1/US-Ho1_AMF_B02_FIXNC_NORMAL400_DIRECT/US-Ho1_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ho2 | MODEL_ONLY | – | 0.39 | – | – | -0.00 | FileNotFoundError: No HH/HR EC file with NEE_VUT_REF and GPP NT/DT under /iridis | [PNG](US-Ho2/US-Ho2_AMF_B02_FIXNC_NORMAL400_DIRECT/US-Ho2_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ho3 | MODEL_ONLY | – | 0.77 | – | – | 0.00 | LAI step -10% at 400/401 | [PNG](US-Ho3/US-Ho3_AMF_B02_FIXNC_NORMAL400_DIRECT/US-Ho3_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-ICt | OK | 0.56 | 2.05 | 3.64 | 0.07 | -0.00 | GPP<0.05 in 1 years; GPP 3.64× EC | [PNG](US-ICt/US-ICt_AMF_B02_FIXNC_NORMAL400_DIRECT/US-ICt_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Rpf | OK | 1.52 | 2.77 | 1.82 | -0.06 | -0.00 |  | [PNG](US-Rpf/US-Rpf_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Rpf_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-SP1 | OK | 4.49 | 0.96 | 0.22 | -0.93 | -0.00 | GPP 0.22× EC | [PNG](US-SP1/US-SP1_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-SP1_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-SRG | OK | 1.34 | 1.52 | 1.13 | -0.04 | 0.08 | GPP step +51% at 400/401; LAI step +11% at 400/401 | [PNG](US-SRG/US-SRG_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-SRG_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-SRM | OK | 0.83 | 1.05 | 1.27 | 0.08 | 0.08 | GPP step +25% at 400/401; LAI step +47% at 400/401 | [PNG](US-SRM/US-SRM_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-SRM_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Seg | OK | 0.45 | 0.85 | 1.91 | -0.03 | 0.04 | LAI step +12% at 400/401 | [PNG](US-Seg/US-Seg_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Seg_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ses | OK | 0.32 | 0.99 | 3.09 | -0.01 | -0.06 | GPP step -11% at 400/401; LAI step +26% at 400/401; GPP 3.09× EC | [PNG](US-Ses/US-Ses_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Ses_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Slt | OK | 3.75 | 4.03 | 1.07 | -0.26 | -0.00 |  | [PNG](US-Slt/US-Slt_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Slt_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Syv | MODEL_ONLY | – | 3.02 | – | – | 0.00 | FileNotFoundError: No HH/HR EC file with NEE_VUT_REF and GPP NT/DT under /iridis | [PNG](US-Syv/US-Syv_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Syv_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Ton | OK | 2.70 | 3.79 | 1.40 | -0.05 | 0.00 |  | [PNG](US-Ton/US-Ton_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Ton_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
| US-Uaf | MODEL_ONLY | – | 1.27 | – | – | -0.00 | FileNotFoundError: No HH/HR EC file with NEE_VUT_REF and GPP NT/DT under /iridis | [PNG](US-Uaf/US-Uaf_AMF_B04_FIXNC_NORMAL400_BASETA_V1/US-Uaf_03_GPP_NEE_full_sequence_AD400_NORMAL400.png) |
