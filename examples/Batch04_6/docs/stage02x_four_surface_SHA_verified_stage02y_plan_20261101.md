# ICOS Batch04 — four Stage02X surface SHA256 verification PASS and Stage02Y next static-input audit (2026-11-01)

## Actual operator verification

The operator confirmed exact, successful read-only `sha256sum -c` on the four **previously created** PFT candidate point surfaces and verified all four per-site Stage02X receipts exist. The output ended `STAGE02X FOUR SURFACES VERIFIED`.

| Site | Exact surface SHA256 verified | Per-site manifest exists |
|---|---|---|
| DE-Gri | `08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b` | True |
| DE-RuR | `2a4685ae3a43323fcff829bd3fdb5d998d58b4e077923a991ee4afd727767414` | True |
| IT-Tor | `908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b` | True |
| ES-Agu | `067722b0dc1440abc2e6aef30ca443b04198f697f16e5ba70344e41f89638fa6` | True |

Root location: `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn`.

**Completed**: scientific PFT model *proxy selection* (6/6); four candidate point-surface builds and their hashes (4/6). Four-site original `Buildconf/datm.input_data_list` path sets previously validated 8/8 against the Stage02C annual NC register, with 74 source files existing. No original case was edited, no new CIME FIXNC case was created, and no Slurm jobs or model runs were launched by Stage02X.

**Not yet completed**: selected new surface actually wired to a new CIME case; effective runtime DATM/FATES binding; tower 30-min observation/QC and ERA substitution checks; per-site soil texture and organic observations/provenance; IT-Tor ten-layer `ORGANIC=0` diagnosis; 5-year spinup smoke, 395-year continuation or other model runs. Two outstanding Batch04 new surfaces: CH-Aws (native RH/ERA source HOLD) and GL-ZaH (site-specific Arctic FATES HLM9/11 mapping).

## Next: Stage02Y strictly read-only static case binding audit

[Stage02Y script](../scripts/02y_four_site_candidate_surface_static_CIME_binding_readonly.py) requires the original saved Stage02C and Stage02V JSONs and the exact operator-confirmed Batch04 Stage02X directory. It independently:
- recomputes 4 candidate NetCDF SHA256 and compares them with the operator-confirmed hashes and JSON receipt content;
- recomputes original source-surface SHA256 from receipts and validates original VS candidate `PCT_NATVEG=100`, `PCT_CROP=0`, conditional `PCT_NAT_PFT` against approved GitHub model proxies, and original-vs-new sand/clay/ORGANIC/latitude/longitude unchanged;
- reviews 8 original S30SHARED/S30EXCL `CaseDocs/lnd_in`, `CaseDocs/datm_in`, stream-document content and `Buildconf/datm.input_data_list`; requires current original site-DATM names and source paths to agree EXACTLY with the Stage02C annual register via Stage02B's established source path regex;
- emits static binding results making clear old original `fsurdat` != new candidate point-surface filename; no claim that CIME runtime stream has been loaded, nor that original source tower met observations/soil are scientifically approved.

`--self-test` runs entirely in memory. The actual audit writes exactly two new files under an explicitly **new empty HOME folder**: `stage02y_four_site_candidate_surface_case_binding_audit.json`, `stage02y_eight_case_static_binding_matrix.csv`. No changes to original site surfaces, forcing NC, source cases, FATES parameter mapping, Git checked-out code or Slurm.

After the Stage02Y audit, independently review per-site meteorological source QC and effective DATM stream. Resolve IT-Tor source soil-organic condition. Then generate **new separately named FIXNC CIME cases**, with `fsurdat` redirected to the candidate surface (not old cases), verify generated case `lnd_in` and stream evidence and 5-year AD-only smoke eligibility. Hold all AD395/AD400 until science, run and archive gates pass. Keep CH-Aws/GL-ZaH separate.
