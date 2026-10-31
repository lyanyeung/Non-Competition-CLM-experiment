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
## Stage02B update — working NetCDF Python environment (31 October 2026)

[Stage02B operator evidence and corrected environment result](docs/stage02b_operator_IRIDIS6_result_20261031.md): the earlier Stage02A READ_ERROR messages were dependency imports (`numpy` missing); after activation, **CH-Aws DATM 2006/2024 and GL-ZaH DATM 2000/2025 all opened successfully** through `netCDF4`. The old Stage02A 15+2 error counts are *historical source JSON fields*, not fresh failures. CIME input lists contain 25/28/21/24/25/32 candidate absolute NC references, including non-meteorological global aerosol/deposition files. Site-specific DATM NC locations for DE-Gri, DE-RuR, IT-Tor and ES-Agu occur under the FLUXNET_13 experiment DATM annual directories. No annual numerical science-QC pass is established by the four successful opens.

## Stage02C — exact site DATM source years and bounded numeric checks

[Stage02C code](scripts/02c_batch04_site_DATM_reference_years_sample_QC_readonly.py). Use the activated `clm_fates_env` Python and the most recent Stage02B JSON. This script uses the input list's **exact `<site>_DATM_<YYYY>` filename** to exclude unrelated aerosol and land files; compares source paths and year gaps among every case, then uses `netCDF4`/`numpy` to inspect a few years per distinct forcing directory (earliest and latest by filename, by default). It displays time-coordinate length, non-monotonic numeric time, missing/nonfinite meteorological values and unit-conditioned basic physical flags, with the full data and source stream remaining HOLD. To examine every candidate annual NC rather than two per directory, use `--samples-per-directory 0` only after reviewing the source inventory and expected compute cost.

Standalone after downloading the immutable GitHub script and verifying its blob SHA:

~~~bash
ROOT="$HOME/ICOS_Batch04_stage02b_qRFrYeC1"
python3 -B "$ROOT/02c_batch04_site_DATM_reference_years_sample_QC_readonly.py" --self-test
python3 -B "$ROOT/02c_batch04_site_DATM_reference_years_sample_QC_readonly.py" \
  --stage02b "$ROOT/stage02b_diagnostics.json" \
  --samples-per-directory 2 \
  --report "$ROOT/stage02c_site_DATM_sample.json"
~~~

All six sites remain pending native-tower QC, actual active DATM-stream binding, soil evidence, PFT science and GL-ZaH private Arctic mapping. No git pull, CIME or Slurm required.
## Stage02C operator results — 31 October 2026

[Recorded IRIDIS6 Stage02C console outcome](docs/stage02c_operator_IRIDIS6_result_20261031.md): six station year ranges with no missing case-referenced annual NC paths or filename-year gaps; 24 sampled annual files open successfully with 17520 time values. **CH-Aws has 133 unique annual forcing file paths in 7 distinct 19-year candidate path sets**, across 8 original cases. Other station year spans are DE-Gri 2004–2025, DE-RuR 2011–2025, IT-Tor 2008–2025, ES-Agu 2006–2024 and GL-ZaH 2000–2025. Candidate input-path equivalence is not proof of S30SHARED/EXCL case equivalence or active stream binding.

## Stage02D — all-year DATM internal QC, time joins and CH-Aws variant differences

[Read-only script](scripts/02d_batch04_all_annual_DATM_QC_and_variant_diff_readonly.py). Takes the existing Stage02C JSON and scans **all distinct candidate annual NetCDF files** for each requested site, not only first/last year. It checks CF time metadata where decodable, 17520 annual half-hour records, non-monotonic/irregular steps, year-token matching, within-folder year seams, missing/nonfinite meteorology, basic physical warnings (TBOT, QBOT, precipitation aliases including `PRECTmms`, radiation, pressure, wind and ZBOT), and exact per-variable signatures to identify CH-Aws humidity/other differences. Files that fail to open or lack calendar are reported as unresolved, not silently passed.

**Important:** Numeric scans are exhaustive for candidate DATM annual point files only; they still do not compare tower native QC, ERA5, scientific forcing provenance, active DATM binding, PFT/site surface/soil or model convergence. No automatic source-case choice, repairs, CIME runs, Slurm or Git pull.

After downloading the source-pinned Stage02D script to a separate HOME directory and verifying its SHA, run:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --sites DE-Gri DE-RuR IT-Tor ES-Agu \
  --report "$NEW_DIR/stage02d_four_grass_shrub.json"
~~~

Check these four simpler stations first before the seven-variant CH-Aws 133-file comparison or GL-ZaH. All site gates remain HOLD until actual source/physics review.
## Stage02D first-four IRIDIS6 verification (31 October 2026)

[Actual operator console record](docs/stage02d_first4_operator_IRIDIS6_result_20261031.md): Stage02D ran successfully in the activated `clm_fates_env` (NumPy 2.2.6/netCDF4 1.7.4). DE-Gri 22 annual files (2004–2025), DE-RuR 15 (2011–2025), IT-Tor 18 (2008–2025) and ES-Agu 19 (2006–2024): **74 unique annual forcing NC, `FLAGS {}` on all four sites, no reported failed annual joins or numeric QC flags**. `SCIENCE_RELEASE HOLD` remains for all. This is a limited internal candidate-DATM audit, **not** tower-versus-ERA QC or confirmation of effective runtime DATM stream.

Next run the **same immutable Stage02D script**, without git pull or new source-code changes, for `--sites CH-Aws GL-ZaH` against the saved Stage02C JSON. CH-Aws has 133 distinct candidate annual files across seven path sets; GL-ZaH has 26. Compare RH-variant numerical digests and check yearly calendar joins before selecting anything. **No AD5/AD400 submission**.
## Stage02D all-six complete: CH-Aws and GL-ZaH (31 October 2026)

[Operator IRIDIS6 result](docs/stage02d_remaining2_operator_IRIDIS6_result_20261031.md): CH-Aws scanned 133 unique annual candidate NC paths (7 distinct 19-year path sets, 8 source cases), **14 years differed only in QBOT**: 2006–2014 and 2016–2020. All candidate years 2006–2024 passed the implemented internal Stage02D checks (`FLAGS {}`). GL-ZaH scanned 26 annual files 2000–2025 with `FLAGS {}`, still requiring private Arctic FATES mapping. With previous four sites, 233 annual DATM candidate NC files were screened across six sites. These are *model-forcing internal* checks, NOT raw tower/ERA QC nor model-run approval.

## Stage02E — quantify CH-Aws QBOT forcing revision at 30-minute resolution

[Stage02E source-pinned read-only comparison](scripts/02e_CH_Aws_QBOT_19y_version_diff_readonly.py): reads previously recorded Stage02C 8-case/7-path source register and compares each year's QBOT, TBOT, PSRF and time axes across alternative CH-Aws DATM paths. Default **SPINUP500_11P baseline is arbitrary and unapproved**: it is used only as a consistent reference, not a recommended forcing. Quantifies changed half-hour counts, maximum and mean absolute QBOT difference in g/kg, and equivalent vapour-pressure / inverse VPD difference in hPa if temperature/pressure stay fixed; records top five timestamps in the JSON report. Any inconsistent units, missing data or time alignment is marked HOLD, not silently repaired.

After fixed GitHub code download and blob SHA validation into a separate HOME folder:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --report "$RUN/stage02e_CH_Aws_QBOT_variants.json"
~~~

Next after Stage02E: native CH-Aws original tower T/RH/VPD/QC plus ERA5 matched half-hours and effective DATM stream-binding forensic audit; also review actual GL-ZaH Arctic private FATES parameters, and the four provisional grass/shrub tower original input records. Still NO AD5/AD400 and no local git pull.
## Stage02E verified CH-Aws QBOT differences — 31 October 2026

[Actual operator Stage02E output and full yearwise maxima](docs/stage02e_operator_IRIDIS6_result_20261031.md): 19 years, seven distinct annual DATM candidate paths per year and 133 path-year comparisons, **zero alignment/comparison holds**. Fourteen years differed in QBOT against the arbitrary unapproved SPINUP500_11P numerical baseline; 2015 and 2021–2024 were identical. Largest maximum absolute QBOT change was **8.6460387 g/kg** (2007), corresponding to a maximum estimated vapour-pressure change **11.051293 hPa**; 2008 and 2016–2020 had other large episodic differences. Annual `MAX_CHANGED_HH` counts are per-year maxima across candidate variants, not additive to a single revision's total.

## Stage02F — complete changed half-hour ledger and RH saturation physics

[Stage02F read-only script](scripts/02f_CH_Aws_QBOT_saturation_and_event_ledger_readonly.py). Reads the same Stage02C case/path source register; loads **all 19×7 site-DATM annual inputs** with activated Python NumPy and netCDF4. Requires exactly aligned CF time and unchanged TBOT, PSRF and units when attributing differences to QBOT. Uses QBOT/P to obtain actual water vapour pressure, Buck saturation over *liquid water* and *ice*, diagnostic RH (%), water-reference VPD, and writes a new standalone CSV with every variant-vs-reference changed half hour plus a JSON summarizing physical flags for all records. Water vs ice RH must not be conflated, especially at this alpine site. A saturation flag or a large difference triggers scientific review, **not automatic replacement**.

Run outside the dirty Git working tree, using a pinned source SHA and fresh empty HOME directory:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Only JSON/CSV in `--out-dir` are created. No forcing/CIME/Slurm/ERA change, no source-case approval. After Stage02F event-level diagnostics, **separately** verify original tower TA/RH/VPD/QC, ERA5 reference values and actual DATM stream paths on the affected native half hours, then review source-specific reason for each repair before model-release decisions.
## Stage02G: full native-source forcing / soil / PFT science release (future)

For each station, the next separate audit must select one verified original source case and pin input checksums and true source years; cross-check DATM streams against annual NC and native tower half-hourly data; verify UTC/local-time convention, no-leap calendar, leap days, counts, gaps, year seams, VPD from T/RH/pressure, nonphysical humidity, precipitation timing, radiation and long flat runs. ERA5/ERA5-Land fallback must be checked against tower source QC, with every replacement documented and unresolved events retained as scientific HOLD. Do not blindly interpolate or relabel QC.

Check actual PCT_NATVEG/other landunits, tower coordinates and original selected point surface, and review sand/clay/silt by depth plus ORGANIC/peat and site vs grid fallback. Host PFT 0 bare is included in conditional NATVEG composition (no automatic renormalisation of green vegetation). Validate **effective FATES HLM→PFT map** against the parameter file in the new case's land namelist. GL-ZaH must independently create and verify its *site-only* Arctic shrub parameter candidate using the existing [six-site GL map tool](../ICOS_Unassigned_6/scripts/01_pft_six_and_GL_arctic_map.py), never modify the shared mapping.

## Stage 03 and subsequent model runs (NOT authorised by this commit)

Only after per-site forcing, source, surface, soil, host/FATES map and point gates pass should new versioned isolated B04 FIXNC surfaces/cases be prepared. Follow the standard independent **AD5 → AD395 → Normal5 → Normal395** protocol; check case.run/st_archive, CLM/DATM/CPL final restart, AD spinup_state=2 and Normal spinup_state=0, submitting-shell stack guard and inode quota. No AD400/Normal400 completion claim is made here.

Related protected workflows: [DE-Tha](../DE-Tha/README.md), [NL-Loo V3](../../docs/NL_LOO_THREE_PHASE_PLOTS.md), [Batch01](../Batch01_10/README.md), [Batch02](../Batch02_10/README.md), [Batch03](../Batch03_10/README.md).
