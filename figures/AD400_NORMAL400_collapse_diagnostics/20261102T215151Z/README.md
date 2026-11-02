# Collapse diagnostics: mortality by type, carbon balance, storage, density, recruitment

Full AD400 → NORMAL400 sequence (annual) and the first AD years (monthly).
Focal PFT = needleleaf PFT with most vegetation carbon in year 1. Collapse = focal-PFT VEGC stays < 1 % of its maximum.
Mortality shares are means over the 20 years before collapse (first two years monthly if it dies at once).
Screening numbers from history output, not conclusions.

| Site | Focal PFT | Collapse year | Window | Mortality (top 3) | Focal NPP | Storage/target min | BTRAN min | Figures |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| CZ-Stn_fix | 6 broadleaf_colddecid_extratrop_tree | n/a (FATES_VEGC_PF__pft6 written for all years) | last 100 years | CSTARV 69%; TERMINATION 18%; IMPACT 10% | 3.12 | 0.229 | 0.0334 | [AD re-run](CZ-Stn_fix/CZ-Stn_fix_04_collapse_diagnostics_ADrerun.png) [first years](CZ-Stn_fix/CZ-Stn_fix_05_collapse_diagnostics_first50y.png) [variables](CZ-Stn_fix/CZ-Stn_fix_history_inventory.txt) |
| DE-Lnf_fix | 6 broadleaf_colddecid_extratrop_tree | n/a (FATES_VEGC_PF__pft6 written for all years) | last 100 years | CSTARV 70%; TERMINATION 18%; IMPACT 9% | 2.97 | 0.236 | 0.0685 | [AD re-run](DE-Lnf_fix/DE-Lnf_fix_04_collapse_diagnostics_ADrerun.png) [first years](DE-Lnf_fix/DE-Lnf_fix_05_collapse_diagnostics_first50y.png) [variables](DE-Lnf_fix/DE-Lnf_fix_history_inventory.txt) |
| US-SRM_fix | 14 c4_grass | n/a (FATES_VEGC_PF__pft14 written for all years) | last 100 years | TERMINATION 100%; CSTARV 0%; FREEZING 0% | 0.885 | 0.0273 | 0.00568 | [AD re-run](US-SRM_fix/US-SRM_fix_04_collapse_diagnostics_ADrerun.png) [first years](US-SRM_fix/US-SRM_fix_05_collapse_diagnostics_first50y.png) [variables](US-SRM_fix/US-SRM_fix_history_inventory.txt) |
