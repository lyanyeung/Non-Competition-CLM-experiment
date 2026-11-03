# Data licence and attribution: PROFOUND-derived tables

The CSV files in this folder are **derived** from the PROFOUND database v0.3:

> Reyer, C. P. O., Silveyra Gonzalez, R., Dolos, K., Hartig, F., Hauf, Y., Noack, M., et al. (2020): The PROFOUND database for evaluating vegetation models and simulating climate impacts on European forests. V. 0.3. GFZ Data Services. https://doi.org/10.5880/PIK.2020.006
>
> Description paper: Reyer et al. (2020), Earth System Science Data 12, 1295–1320, https://doi.org/10.5194/essd-12-1295-2020

**Licence:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0), as stated on the GFZ landing page. These files are not covered by any licence of the rest of this repository. Non-commercial use only; cite the dataset above.

**Changes made:** stand variables were summed over species per site and year (biomass converted from kg ha⁻¹ to kg DM m⁻²; height and DBH as basal-area-weighted means); thinning events were detected from year-to-year changes in stem number and basal area; soil organic carbon stocks were computed from C %, bulk density and layer thickness; the global CO2 series was reshaped to one column per scenario. Code: `post_spinup/scripts/06_derive_PROFOUND_targets.py`.

**Site-specific conditions** (PROFOUND `POLICY_SITES_master`, checked 3 November 2026):

| Site (ICOS / PROFOUND) | TREE, STAND, SOIL | Condition |
|---|---|---|
| CZ-BK1 / bily_kriz | site-specific | Acknowledge: "This work was supported by the Ministry of Education, Youth and Sports of CR within the CzeCOS program, grant number LM2015061." **Notify Lenka Krupkova about any publication** that uses these data. |
| IT-Col / collelongo | standard PROFOUND policy | cite the database |
| FI-Hyy / hyytiala | standard PROFOUND policy | cite the database |
| DK-Sor / soro | standard PROFOUND policy | cite the database |

The CO2 series (ISIMIP) and the N-deposition series follow the standard PROFOUND policy (EMEP N deposition: non-commercial reproduction with citation). The raw extract (STAND, TREE, SOIL, ...) stays on IRIDIS at `/iridisfs/scratch/ly3n24/CLM_FATES/external/PROFOUND_v0.3/ICOS38_extract/`.
