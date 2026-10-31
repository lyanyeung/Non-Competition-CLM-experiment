# ICOS Batch04 — six-station coordinated forcing and surface preflight

**31 October 2026: READ-ONLY STAGE01 CREATED. No CIME cases, surfaces, forcing NetCDF, jobs or restarts were created or changed.**

This folder covers exactly **CH-Aws, DE-Gri, DE-RuR, IT-Tor, ES-Agu, GL-ZaH**, the six ICOS/FLUXNET stations outside the existing three 10-site FIXNC cohorts. **DE-Tha and NL-Loo are separate, protected examples**, not Batch04 reruns. Thus the original 38-site ICOS inventory is 30 in Batch01–03 + 6 in Batch04 + 2 independent examples.

## Authoritative scientific decisions

Use the already operator-selected [six-site PFT CSV](../ICOS_Unassigned_6/data/six_site_FIXNC_operator_selected_PFT_20261025.csv) and [source/evidence explanation](../ICOS_Unassigned_6/README.md). The new [review-gate register](data/batch04_review_gates.csv) tracks outstanding scientific and technical validation without changing those choices.

| Site | Candidate HOST natural PFT composition (%) | Scientific/technical hold |
| --- | --- | --- |
| CH-Aws | 13: cool C3 grass 100 | Grass/forb proxy is not measured footprint; previous negative-RH and unstable original template |
| DE-Gri | 13: cool C3 grass 100 | Grass/forb/legume and bare area not surveyed as complete footprint; DATM/soil input unverified |
| DE-RuR | 13: cool C3 grass 100 | Lysimeter functional groups are not the whole EC footprint; review forcing and management |
| IT-Tor | 13: cool C3 grass 100 | High-alpine seasonal forcing, vegetation/soil and bare-cover assumptions |
| ES-Agu | 0: bare 49 / 9: evergreen shrub 22 / 13: C3 grass 29 | Macrochloa fractional denominator, biocrust and bare-ground sensitivity unresolved |
| GL-ZaH | 0: bare 43 / 9: evergreen Arctic shrub 53 / 11: deciduous Arctic shrub 3 / 12: Arctic C3 grass 1 | Mandatory **private GL-only FATES parameter map** for host indices 9 and 11; never alter shared FATES mapping |

Each percentage is an explicit **model proxy conditional on the natural vegetation landunit**. None has been proved to be an observed tower-footprint PFT-area fraction. Choosing a proxy is not permission to run or a science-QC pass.

## Stage 01: shared read-only inventory (now available)

[Python source](scripts/01_batch04_six_site_input_preflight_readonly.py)

On IRIDIS6, after this commit is merged to main:

~~~bash
conda activate clm_fates_env
cd "$HOME/Non-Competition-CLM-experiment"
git pull --ff-only origin main

python3 -B examples/Batch04_6/scripts/01_batch04_six_site_input_preflight_readonly.py --self-test

# Display read-only case, forcing folder, source surface and static-point audit
python3 -B examples/Batch04_6/scripts/01_batch04_six_site_input_preflight_readonly.py \
  --base /iridisfs/scratch/ly3n24/CLM_FATES

# Optional: write ONLY a new report in the existing HOME directory; never overwrite
python3 -B examples/Batch04_6/scripts/01_batch04_six_site_input_preflight_readonly.py \
  --base /iridisfs/scratch/ly3n24/CLM_FATES \
  --report "$HOME/ICOS_Batch04_stage01_readonly.json"

# Review only the three lower-complexity grasslands first
python3 -B examples/Batch04_6/scripts/01_batch04_six_site_input_preflight_readonly.py \
  --sites DE-Gri DE-RuR IT-Tor
~~~

The script checks the exact 6-site operator CSV against known 15-element HOST NATPFT fractions and source-blob tag; enumerates possible **original** CIME cases without silently choosing a template; inspects static env XML, effective generated CaseDocs land/DATM namelists, DATM input list and stream-document presence; and samples original point surface NetCDF for landunits, site LATIXY/LONGXY, PCT_NAT_PFT, PCT_SAND/PCT_CLAY and ORGANIC. It flags any PTS_LAT/LON mismatch with surface coordinates. For large files, hashes are skipped with an explicit label. If netCDF4/numpy is missing, inspection flags an error instead of declaring success.

**Important limitation:** Stage01 does *not* check all source half-hourly meteorological rows or annual NC files, does *not* verify true source QC0/QC1, does *not* resolve CIME runtime conditional XML, and does *not* automatically choose a template based on its name. Its status is always HOLD, even if the numeric fields look plausible. No automatic Slurm query or model submission is made.

## Stage01 operator result — 31 October 2026

[Actual IRIDIS6 Stage01 console evidence](docs/stage01_operator_IRIDIS6_result_20261031.md): six source-site folders present; 17 original case candidates and 27 forcing directories; 17/17 static XML/surface point checks matched. These do not establish science acceptance, active stream correctness or model restart completion.

## Stage02A — sample candidate DATM source/forcing and compare cases (read-only)

[Script: Stage02A source/forcing sample auditor](scripts/02_batch04_forcing_source_sample_readonly.py). Takes Stage01 JSON, reviews case input-data lists and CaseDocs stream documentation, enumerates source forcing NetCDF directories, and samples earliest and latest lexicographic NetCDF filenames in each forcing directory. Reports meteorological variable availability, missing/nonfinite rates, numeric time monotonicity and selected nonphysical-value flags. All candidate folders and case variants remain UNSELECTED; no automatic preference for S30SHARED or an RH variant.

**Scope limitations:** The scanned forcing folders are not necessarily the active CIME DATM streams. The sample is NOT exhaustive forcing QC. Unit-based physical flags are indicators, not replacement rules. Nothing in this stage authorizes surface/case creation, forcing substitution or Slurm submission.

Standalone IRIDIS6 usage (without modifying the local Git working tree):

~~~bash
python3 -B "$ROOT/examples/Batch04_6/scripts/02_batch04_forcing_source_sample_readonly.py" --self-test
python3 -B "$ROOT/examples/Batch04_6/scripts/02_batch04_forcing_source_sample_readonly.py" \
  --stage01 "$ROOT/stage01_report.json" \
  --report "$ROOT/stage02_source_forcing_samples.json"
~~~

Here ROOT is the original Stage01 standalone audit directory; download the Stage02 script there from the immutable GitHub merge commit, verifying its git blob SHA before invoking. The only permitted new file is the optional JSON report with exclusive-create semantics. Stage02B, after confirming actual streams and source-case provenance, will check all selected per-year/half-hourly records against original tower QC and ERA.
## Stage02A operator outcome — 31 October 2026

[Actual operator console record](docs/stage02a_operator_IRIDIS6_result_20261031.md): 6/6 sites, 17 CIME cases, 27 forcing subdirectories; CH-Aws and GL-ZaH sample NetCDF scans reported READ_ERROR. Four other site forcing trees contained only source packages/raw folders with no discovered NC. These outcomes **do not prove corrupt files or missing DATM input**. The complete Stage02A JSON is available only on IRIDIS6, not in GitHub.

## Stage02B — explain READ_ERROR and trace actual CIME input references

[Stage02B read-only script](scripts/02b_batch04_explain_readerrors_and_datm_paths_readonly.py): reads Stage02A JSON, displays exact Python exceptions, probes 0–3 representative NC headers/metadata/two-record reads per site, and inspects each original case's Buildconf/datm.input_data_list to identify absolute NetCDF input paths, existence and candidate source references. Stream-binding and native tower QC remain unverified even when a path exists. The script writes only a new optional report with exclusive-create, never overwrites; it does not change CIME, surfaces, forcing, Git worktree or Slurm jobs.

Run on IRIDIS6 from the existing standalone Batch04 Stage01 directory after downloading the SHA-pinned Stage02B script; no git pull:

~~~bash
ROOT="$HOME/ICOS_Batch04_stage01_Dy3qIRjj"
python3 -B "$ROOT/examples/Batch04_6/scripts/02b_batch04_explain_readerrors_and_datm_paths_readonly.py" --self-test
python3 -B "$ROOT/examples/Batch04_6/scripts/02b_batch04_explain_readerrors_and_datm_paths_readonly.py" \
  --stage02 "$ROOT/stage02_forcing_20261031T003910Z.json" \
  --max-probes-per-site 2 \
  --report "$ROOT/stage02b_error_and_references.json"
~~~
## Stage02C: full forcing/soil/PFT science release (future)

For each station, the next separate audit must select one verified original source case and pin input checksums and true source years; cross-check DATM streams against annual NC and native tower half-hourly data; verify UTC/local-time convention, no-leap calendar, leap days, counts, gaps, year seams, VPD from T/RH/pressure, nonphysical humidity, precipitation timing, radiation and long flat runs. ERA5/ERA5-Land fallback must be checked against tower source QC, with every replacement documented and unresolved events retained as scientific HOLD. Do not blindly interpolate or relabel QC.

Check actual PCT_NATVEG/other landunits, tower coordinates and original selected point surface, and review sand/clay/silt by depth plus ORGANIC/peat and site vs grid fallback. Host PFT 0 bare is included in conditional NATVEG composition (no automatic renormalisation of green vegetation). Validate **effective FATES HLM→PFT map** against the parameter file in the new case's land namelist. GL-ZaH must independently create and verify its *site-only* Arctic shrub parameter candidate using the existing [six-site GL map tool](../ICOS_Unassigned_6/scripts/01_pft_six_and_GL_arctic_map.py), never modify the shared mapping.

## Stage 03 and subsequent model runs (NOT authorised by this commit)

Only after per-site forcing, source, surface, soil, host/FATES map and point gates pass should new versioned isolated B04 FIXNC surfaces/cases be prepared. Follow the standard independent **AD5 → AD395 → Normal5 → Normal395** protocol; check case.run/st_archive, CLM/DATM/CPL final restart, AD spinup_state=2 and Normal spinup_state=0, submitting-shell stack guard and inode quota. No AD400/Normal400 completion claim is made here.

Related protected workflows: [DE-Tha](../DE-Tha/README.md), [NL-Loo V3](../../docs/NL_LOO_THREE_PHASE_PLOTS.md), [Batch01](../Batch01_10/README.md), [Batch02](../Batch02_10/README.md), [Batch03](../Batch03_10/README.md).
