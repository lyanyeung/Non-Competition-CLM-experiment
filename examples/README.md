# Standard site examples — fixed-biogeography / no-PFT-competition

The `examples/` tree is for **site-specific, reproducible scientific examples**.
Every site should keep observed evidence, original denominators and references
separate from modeling assumptions, include a read-only audit, and make model
submission an explicit gated decision. When credible station-observed soil texture exists,
use it in a new versioned model surface rather than default gridded soil. See
[the global measured-soil rule](../docs/observed_soil_texture_policy.md). DE-Tha runs ONLY the selected forest
proxy (not original-grid/PFT experimental alternatives).

| Site | Value for a standard example | Stage |
| --- | --- | --- |
| [DE-Tha](DE-Tha/README.md) | **Selected ONE forest EC-tower PFT proxy:** ENF87 / DNF10 / DBF3 (2% unknown deciduous allocated to DBF as explicit assumption); NATVEG100 / CROP0 | **Stage13 AD5 model+archive verified COMPLETED/0:0 with 2001 restart spinup_state=2; remaining AD395 not submitted; independent Stage14 AD5→Normal5 case staged and validated, not submitted** |

The completed NL-Loo PRE50 / first-5-year AD200 validation and submitted
AD200 continuation are currently recorded under [scripts/09–15](../scripts/).
Those scripts contain NL-Loo-specific absolute paths and Slurm incident IDs:
**do not run them for another site unchanged**.

22 quantitative-evidence candidates are listed in
[data/22_site_cohort.csv](../data/22_site_cohort.csv). Membership is not
certification of precise PFT area fractions.
