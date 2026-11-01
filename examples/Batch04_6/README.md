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
## Stage02F initial-run code bug and corrected retry (31 October 2026)

[Actual IRIDIS6 traceback and correction](docs/stage02f_parser_crash_and_fix_20261031.md). The original Stage02F SHA-pinned version was self-tested but main() then passed a decoded JSON dict to a parse function expecting a Path, triggering `AttributeError: 'dict' object has no attribute 'read_text'`. This was a **script error before NetCDF reads**; no Stage02F scientific results exist from the failed run. The script is corrected so parse_input accepts a dict, and its self-test executes an eight-case/seven-source-path in-memory regression check. Download the corrected pinned code to a **new standalone HOME folder** and use a new empty `--out-dir`. The original failed folder may be preserved for provenance. No Git pull, case changes or Slurm actions.
## Stage02F complete (31 October 2026): common inherited humidity flags

[Operator Stage02F year-by-year evidence](docs/stage02f_operator_IRIDIS6_result_20261031.md) shows the corrected script successfully compared all 19 × 7 CH-Aws candidate annual inputs, **0 comparison holds**, and wrote **5278 candidate-variant × changed-half-hour CSV rows**. A count of rows across variants is NOT a count of independent tower half-hours. Derived `RH_water >100%` occurred in multiple years, with major **2021–2024 shared-source** flag counts: 7826, 2835, 658 and 217 across seven identical candidate annual variants per year. Since Stage02E recorded no QBOT differences among those variants, the corresponding unique flagged half-hours are **1118, 405, 94 and 31** (2021–2024 total **1648**). These are physics-screen indicators, not proof of invalid observations.

## Stage02G — deduplicated seven-variant RH saturation event triage

[Read-only Stage02G Python](scripts/02g_CH_Aws_RH_supersaturation_unique_events_readonly.py) reads the actual saved Stage02C source register and Stage02F summary; it checks time, TBOT and PSRF alignment, scans all 7 candidate paths for each of the 19 years, compares the previous Stage02F summed flag counts, and computes **unique HH union and seven-way intersection** for RH_water>100. Adds thresholds 101, 105, 110, 120 and 150%; ice-relative RH for below-freezing values; maximal RH, common-source agreement, consecutive run duration and top episodes. An optional fresh empty output directory receives one JSON and a CSV with one row per unique flagged year-HH (not seven copies).

Run with a source-pinned SHA and the activated `clm_fates_env`; never modify the original working tree:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --stage02f "$HOME/ICOS_Batch04_stage02f_fixed_ynHMlvrA/results/stage02f_summary.json" \
  --out-dir "$NEW_EMPTY_REPORT_DIR"
~~~

The Stage02G data checker has **not yet been executed on IRIDIS6**; all candidate science remains HOLD. After Stage02G, assess extreme individual and sustained events against native tower TA/RH/VPD/QC and collocated ERA5 evidence with unit/calendar verification. Do not cap RH or release an AD5/AD400 case based on a numerical screen.
## Stage02G CH-Aws verified (31 October 2026): tiny RH-water exceedances

[Operator's 19-year Stage02G evidence](docs/stage02g_operator_IRIDIS6_result_20261031.md) shows **1667 unique RH-water>100% half-hours**, equal to seven-way intersection (every flagged HH affected all seven candidate variants). 2021–2024 account for **1648 unique HH**, max RH-water **100.071%** in 2021 and **100.069%** in 2022. **No half-hour exceeded 105%** among all compared paths. Stage02F counts matched in each year; the apparent 7× multiplication must not be interpreted as independent observations. Ice saturation exceeded 100% below freezing in many instances; ice supersaturation is not automatically invalid. Neither minor water-saturation exceedances nor seven-way common forcing justify a bulk humidity repair.

## Stage02H — CH-Aws original source discovery and prioritized episode manifest

[Stage02H read-only source-manifest script](scripts/02h_CH_Aws_tower_ERA_source_manifest_readonly.py) uses existing Stage02E and Stage02G JSONs to rank severe earlier-period QBOT changes and RH episode timings, and discovers *candidate* tower/ERA archives/CSV and source metadata within the original CH-Aws forcing tree. ZIP/TAR archive member names and small CSV headers are inspected **without extraction or file modification**; only path, size, name and header provenance is catalogued, not raw measurement science. Output JSON and top event CSV are written only in a NEW empty standalone HOME directory. This step deliberately **does not** claim that a file is the actual native RH/QC source on a given timestamp.

Run after downloading and verifying the SHA-pinned script in the activated `clm_fates_env`:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02e "$HOME/ICOS_Batch04_stage02e_ltWaEE72/stage02e_CH_Aws_QBOT.json" \
  --stage02g "$HOME/ICOS_Batch04_stage02g_BOTDZjEh/results/stage02g_unique_RH_events.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Next, after discovering the original source product and QC columns, perform native tower/ERA/selected-DATM event-level **matched-time** verification for selected large-change half hours, including pressure units, time zone/calendar and source confidence. Still no automatic RH cap, DATM replacement, FATES parameter edits, case generation, AD5/AD400 or Slurm.
## Stage02H operator outcome — 31 October 2026

[Actual IRIDIS6 Stage02H terminal findings](docs/stage02h_operator_IRIDIS6_result_20261031.md): 164 files inventoried in CH-Aws forcing (19 CSV, 11 JSON, 134 NC). The 559-RH trial ledger, 33 high-uncertainty ledger, Stage21/25/28/29/34/38/42 revision manifests and ledgers, and four large (61–72 MB) candidate merged-multisource half-hour CSV files were located. Ranked forcing-QBOT events include 2007-07-22 07:30 (11.051 hPa difference), 2008-06-27 06:30 (9.548 hPa), 2020-07-17 10:00 (9.785 hPa), and 2019-07-29 07:30 (9.284 hPa). These are **variant-vs-arbitrary-baseline differences**, not validated tower/ERA observation discrepancies.

## Stage02I — original candidate CSV column/time/event forensic read (no edits)

[Stage02I read-only tool](scripts/02i_CH_Aws_revision_source_event_csv_readonly.py) reads the saved Stage02H JSON, verifies the declared CH-Aws forcing root, opens the **19 candidate local CSVs and 11 small JSON manifests**, collects original timestamp/QC/TA/RH/VPD/ERA field names and looks for the highest-ranked QBOT events within ±60 minutes, retaining whether the match arose from TIME/TIMESTAMP_START/TIMESTAMP_END and its relative offset. The four merged candidate half-hour CSVs are streamed row by row without loading a ~70 MB file into memory. No timestamp-zone or start/end adjustment is assumed. Every result remains a **candidate** until the true native source/QC/ERA and time convention are confirmed.

Run from a newly downloaded SHA-pinned script into a standalone HOME directory with activated `clm_fates_env`. No git pull or input-file modifications:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02h "$HOME/ICOS_Batch04_stage02h_UsOLvU01/results/stage02h_source_event_manifest.json" \
  --event-limit 20 --max-csv-mb 90 --out-dir "$NEW_EMPTY_DIR"
~~~

Stage02I cannot approve a humidity fix. It is a schema and raw-candidate time-match stage, not final validation of measured tower RH, ERA5-Land, data-processing source QC, physical units or actual CIME DATM stream. Only a subsequent source-specific evidence audit can lift that HOLD.
## Stage02I operator result — source candidate matches, raw FLUXMET_HH still unexamined

[Operator IRIDIS6 Stage02I output](docs/stage02i_operator_IRIDIS6_result_20261031.md): 19 CSV and 11 JSON manifests examined; 437 candidate time-matched rows, of which 400 belong to four *alternative processed* multisource forcing products (100 each) and 37 to stage34/38/42 revision ledgers. The original `EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv` was **SKIP_OVER_MAX_MB** due to a 90 MB bound. `NO_RECOGNISED_TIME_COLUMN ROWS 1` on separate ledger/metadata CSVs is not evidence that those files contain only one record; the scanner stopped after its first row because it did not identify a half-hour timestamp field. The matched records remain **candidate evidence only**: no native tower QC, ERA5 comparison or time-reference validation.

## Stage02J — stream the original >90 MB FLUXMET_HH source at flagged events

[Stage02J read-only script](scripts/02j_CH_Aws_original_FLUXMET_HH_event_evidence_readonly.py) takes the actual saved Stage02I JSON, verifies the exact previously skipped CH-Aws EUF product path, and streams the original half-hour FLUXMET CSV row by row with bounded memory, with **no 90 MB skip**. It records `TIMESTAMP_START` and `TIMESTAMP_END` *separately*, and matches top 20 Stage02I high-QBOT event timestamps and ±30/60-minute context. It reports the actual columns present for TA/RH/VPD/PA and any `_QC` fields as **raw strings**; source missing-value codes and QC semantics are not guessed. The output JSON also associates these records with Stage02I processed/revision candidates by event ID, and a new CSV carries original source rows; neither authorizes a QC approval or source replacement.

Do not conflate **FLUXMET processed fields** (e.g. `TA_F`, `VPD_F`, gap-filled) with native unfilled tower observations, nor treat equality of timestamps under different START/END conventions as verified UTC alignment. This stage creates only JSON/CSV reports under a fresh EMPTY HOME report directory, never modifying the original product, forcing, CIME, FATES, Git working tree or Slurm. Subsequent science work must prove true tower RH/TA/VPD QC and separate ERA5 provenance.
## Stage02J complete (31 October 2026): original half-hour source contexts

[Operator's Stage02J IRIDIS6 evidence](docs/stage02j_operator_IRIDIS6_result_20261031.md): read the entire 372,131,800-byte original distributed EUF FLUXMET_HH product, 333,120 half-hour rows, 181 columns and 200 matched *timestamp-column* candidate records for 20 high-QBOT-change events (five ±60 min candidate source records × both TIMESTAMP_START and TIMESTAMP_END per event). There are 240 more source HH than the 19-year DATM NOLEAP 332,880 HH, numerically consistent with the five leap days 2008/2012/2016/2020/2024; clock/calendar handling must be positively verified rather than comparing raw row indices.

**Source QC interpretation grounded in official FLUXNET definitions:** [FULLSET variables](https://fluxnet.org/data/fluxnet2015-dataset/fullset-data-product/) and [QC quick-start guide](https://fluxnet.org/data/fluxnet2015-dataset/variables-quick-start-guide/) define half-hour `TA_F_QC` and `VPD_F_QC`: 0 measured, 1 good-quality gap-filled, 2 downscaled ERA. The 20 operator-displayed source examples have `TA_F_QC=0` and `VPD_F_QC=1`, so under these conventions **the displayed VPD values are gap-filled and NOT direct measurements**, while the displayed TA are labelled measured. TA_F is degrees C, VPD_F hPa, PA_F kPa. Confirm the EUF archive's own metadata before treating the schema as an authoritative source-specific QC decision.

## Stage02K — compare source START/END alternatives against DATM event physics

[Stage02K read-only source-event code](scripts/02k_CH_Aws_FLUXMET_DATM_event_physics_readonly.py) uses operator-saved Stage02C + Stage02E + Stage02J JSONs. Each of 20 ranked QBOT events is mapped back to its **exact Stage02E half-hour index**, then the seven distinct candidate source paths are opened read-only to extract netCDF QBOT/TBOT/PSRF and derived water-reference RH/VPD with the same event timestamp and units verified. For original FLUXMET events, the script retains exactly the **two separate offset-zero alternatives** from `TIMESTAMP_START` and `TIMESTAMP_END`, with the original raw `RH`, `TA_F`, `TA_ERA`, `VPD_F`, `VPD_F_QC`, `VPD_ERA`, `PA` and `PA_F` fields. It inventories the BIFVARINFO_HH metadata file if present. Any source-derived QBOT numerical comparisons are tagged **units/clock/QC hypotheses**, not scientific approvals.

Only a new standalone HOME output JSON/CSV is written; input forcing NC, original distributed FLUXMET_HH and working Git tree are untouched, no Slurm. Next evidence task: validate the source-specific time basis and native tower RH/VPD QC, then trace Stage34/38/42 ledger rows and ERA5 values to the selected event and decide case/source holds. Do not bulk repair low-level RH>100% or submit AD5/AD400.
## Stage02K operator results — 20 exact event-index comparisons, 31 October 2026

[Actual Stage02K IRIDIS6 evidence](docs/stage02k_operator_IRIDIS6_result_20261031.md): `SOURCE VERIFIED`, self-test PASS, **20 events × 7 distinct DATM forcing paths**, `MODEL_READ_HOLDS 0`, 40 exact START/END source clock candidates, FLUXMET BIFVARINFO_HH `READ_METADATA` with 34 relevant metadata rows. For all 20 printed events, reference DATM derived VPD-water is within **0.007 hPa** of the same-label FLUXMET **TIMESTAMP_START VPD_F**, but END often differs by multiple hPa. This strongly suggests the arbitrary original reference was generated from the **START-indexed, processed/gap-filled `VPD_F` field**, NOT a proof that it is superior meteorologically. Stage02J original product examples report `VPD_F_QC=1` for all 20 anchors; under standard FLUXNET conventions this means gapfilled VPD, not measured native VPD. Time-zone, tower raw RH QC and ERA evidence still remain HOLD.

## Stage02L — quantify the seven DATM versions relative to two FLUXMET clocks and RH/ERA candidates

[Stage02L source-pinned read-only comparison](scripts/02l_CH_Aws_event_QC_source_comparison_readonly.py) takes the saved Stage02K JSON **only**; performs guarded source-provenance checks, uses all **20 × 7 model version event values**, computes numerical VPD comparisons separately against FLUXMET START and END, and retains raw FLUXMET `RH`, `TA_F_QC`, `VPD_F_QC`, `VPD_ERA`, `TA_ERA` and `PA_F`. It labels any reconstructed source vapour pressure, QBOT or RH as **unit assumptions, not proven native tower observations**, and never chooses a candidate solely for matching an MDS-filled `VPD_F`. Output: one JSON with per-event source and model details, one 140-row CSV matrix (20 events × seven model path sets), in a new empty standalone HOME folder. No forcing/CIME/Slurm/git modifications.

After downloading and verifying source hash, run:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02k "$HOME/ICOS_Batch04_stage02k_dbo0MGh4/results/stage02k_CH_Aws_source_DATM_event_physics.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Next assess matched original unfilled tower RH/VPD availability, stage34/38/42 amendment QC, ERA5 reference and actual CIME DATM stream choice. All six Batch04 stations remain scientific HOLD pending those and the separate PFT/soil/surface gates; do not submit AD5/AD400.
## Stage02L validated operator outcome (31 October 2026)

[Actual Stage02L console evidence](docs/stage02l_operator_IRIDIS6_result_20261031.md) found that the old unapproved reference DATM water-VPD closely matches the original-distribution FLUXMET **TIMESTAMP_START VPD_F** for **20/20 high-QBOT-difference events**, with mean absolute deviation **0.0033948 hPa**, vs **1.9789035 hPa** relative to TIMESTAMP_END. START was closer for 19 events, END for zero and one tie. In these selected events, START `VPD_F_QC=1` and `TA_F_QC=0` throughout, numeric original `RH` is absent **20/20**, and `VPD_ERA` is present **20/20**. Under standard FLUXNET variable definitions, these are gap-filled VPD values, not native measured VPD; similarity to the old reference indicates derivation/processing, NOT accuracy or an approved source.

## Stage02M — seven forcing choices vs gap-filled VPD, ERA VPD, and revised-ledger evidence

[Stage02M source-pinned read-only workflow](scripts/02m_CH_Aws_seven_forcings_ERA_and_repair_ledger_readonly.py) reads the saved **Stage02L and Stage02I JSON reports only**. It checks 20 shared event IDs/times and seven candidate DATM forcing groups, creates a **140-row seven-model event matrix**, and reports numerical differences to START-indexed `VPD_F` and `VPD_ERA`, independently per candidate. It joins any Stage34/38/42 candidate revision ledger matches by the existing event ID, distinguishing exact 0-minute evidence from ±30/60-minute context. It never equates a ledger match, gap-filled VPD or ERA source similarity with original tower QC0 or actual independent ERA validation. The source `RH` is missing at all 20 selected events; original/native tower moisture measurement provenance remains a science HOLD.

Download the immutably pinned code into a new HOME directory, verify exact Git blob SHA, and run:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02l "$HOME/ICOS_Batch04_stage02l_PDjpMDmW/results/stage02l_source_clock_QC_matrix.json" \
  --stage02i "$HOME/ICOS_Batch04_stage02i_lcZXq0Ls/results/stage02i_source_event_matches.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

These are **diagnostics**, not a seven-version preference ranking. No forcing/NC/case/FATES edits or Slurm, and no AD5/AD400 science release. Subsequently validate the original raw tower RH, actual ERA source and UTC/time-index provenance, plus exact ledger decisions and final active DATM streams.
## Stage02M operator-run source diagnostics (31 October 2026)

[Stage02M actual operator output and limitations](docs/stage02m_operator_IRIDIS6_result_20261031.md): 20 high-QBOT-difference events × 7 distinct DATM case forcing path sets = 140 source-relative comparisons. Mean absolute VPD difference from the **gap-filled** START-indexed FLUXMET VPD_F is approximately **0.0034 hPa** for the original numerical reference/RH21A/RH25A/RH29A at these events, compared with 3.2546/4.7913/7.7622 hPa for RH34A/RH38A/RH42A. Conversely vs the processed-product `VPD_ERA` field, MAE is 6.5714 hPa for the original group, and **4.2316/3.2722/1.1942 hPa** for RH34A/RH38A/RH42A. These do NOT constitute a scientific accuracy ranking: 20 events are deliberately selected for large variant disagreements, original `RH` is missing at each, `VPD_F_QC=1` (gap-filled) and `VPD_ERA` is not independently site-validated. Stage02M reported **20 exact-time ledger candidate matches and 17 ±30/60 min contextual matches** across Stage34/38/42. No model source was approved.

## Stage02N — verify original Stage34/38/42 ledger rows, source metadata and SHA256

[Stage02N read-only forensic script](scripts/02n_CH_Aws_revision_ledger_sha_QC_forensic_readonly.py) takes the actual saved Stage02M and Stage02I JSONs to locate exactly three small original revision ledgers and adjacent manifests under the CH-Aws forcing directory. Reads **every original CSV column/row** (small bounded files), verifies exact event ID + source row number + original CSV time value, computes ledger SHA256 and compares the declared manifest SHA if present. It prints real QC/source/provenance-related fields and reports mismatches as science holds, preserving original manifest `scientific_status` and source/dependency hashes. A matching SHA proves file integrity only, **not science approval**. This stage never changes input data or submits Slurm.

Download pinned code into a new HOME directory, activate `clm_fates_env`, verify its Git blob SHA and run:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02m "$HOME/ICOS_Batch04_stage02m_WIktbwfu/results/stage02m_ERA_gapfill_revision_evidence.json" \
  --stage02i "$HOME/ICOS_Batch04_stage02i_lcZXq0Ls/results/stage02i_source_event_matches.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

After Stage02N, determine whether original measured `RH` or another independently supported humidity source exists and what quality/time metadata the original repair ledgers actually establish; if not, keep the associated humidity selection on HOLD. Do not infer that ERA agreement alone makes RH42A valid, and do not authorise AD5/AD400 or modify effective FATES, surface or soil maps.
## Stage02N verified: CH-Aws source repairs remain exploratory (1 November 2026)

[Latest six-site status and operator Stage02N evidence](docs/stage02n_operator_and_six_site_science_status_20261101.md). Original CH-Aws repair ledgers Stage34 (27 rows), Stage38 (21), Stage42 (23) all **SHA256 MATCH**, their 20 high-impact original CSV rows also **MATCH** (`SOURCE_ROW_HOLDS 0`, `LEDGER_SHA_UNVERIFIED NONE`). Crucially, their original `scientific_status` labels are `EXPLORATORY_NOT_OBSERVATION_QC_APPROVED`, `EXPLORATORY_NOT_TOWER_VALIDATED`, and `EXPLORATORY_REANALYSIS_SENSITIVITY`. These integrity checks DO NOT grant observation QC acceptance. At selected 2007–2020 times, gap-filled VPD_F (QC1) implies very low RH (as low as ~0.013%), while ledger ERA5/ERA5-Land RH is ~80–99%. No independent measured native RH is available in the selected distributed records. Do not treat low old-RH values or higher ERA similarity as conclusive without native source/time/site-grid validation.

**Priorities:** (1) CH-Aws verify original unfilled tower humidity and QC, independent ERA reference/height/clock, then science-review repair versions; (2) run read-only final original meteorology/active DATM stream/soil/PFT checks in parallel for DE-Gri, DE-RuR, IT-Tor, ES-Agu; (3) separate private site-only Arctic FATES map for GL-ZaH plus soil/point QC. All six sites remain **HOLD**, and no AD5/AD400, file editing or Slurm submission is authorised.

## Stage02O — continue CH-Aws source RH/ERA scientific screening (1 November 2026)

The [read-only Stage02O script](scripts/02o_CH_Aws_RH_source_ERA_20event_triage_readonly.py) and [operator scope/limitations](docs/stage02o_scope_and_operator_INSTRUCTIONS_20261101.md) are the controlled next step after the original three Stage34/38/42 revision ledger files and 20 exact event rows were SHA/time verified by Stage02N. It consumes only the original saved Stage02N and Stage02M JSON reports, never modifies any site files, and computes per-event implied low RH, ERA5/ERA5-Land humidity differences, original recorded neighbor jumps, source seams and unresolved QC flags. `REVIEW_FIRST` is a diagnostic review priority, not approval to use ERA data or alter a forcing version.

Input sources:

~~~bash
N="$HOME/ICOS_Batch04_stage02n_sfazK8sU/results/stage02n_CH_Aws_original_ledger_QC_provenance.json"
M="$HOME/ICOS_Batch04_stage02m_WIktbwfu/results/stage02m_ERA_gapfill_revision_evidence.json"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --stage02n "$N" --stage02m "$M" --out-dir "$NEW_EMPTY_DIR"
~~~

The science HOLD remains on all six sites; the four less complex DE-Gri/DE-RuR/IT-Tor/ES-Agu do not need a Stage02D rerun and can proceed to independent source/active-CIME/PFT/soil preflight in parallel. GL-ZaH retains its mandatory private Arctic FATES mapping requirement. Do not start AD5/AD400 without per-site release.

## Stage02O actual IRIDIS6 result — 20/20 unexplained RH source conflicts

[Stage02O operator evidence](docs/stage02o_operator_IRIDIS6_result_20261101.md) confirms the selected 20 highest-QBOT-disagreement events all have **processed VPD-derived RH below 10%**, and their old-source RH differs from both ledger ERA5 and ERA5-Land RH by **>=50 percentage points**. There are six original-ledger neighboring RH jumps >=40pp and one explicit source seam (E009 on 2007-05-17). All 20 cases are `REVIEW_FIRST`, **0 have independently confirmed native sensor RH/QC**, and no original Stage34/38/42 exploratory revision is scientifically approved. This selection is not representative of site-wide abnormal observation prevalence.

## Stage02P — locate unfilled tower observation sources before further forcing decisions

[Stage02P read-only CH-Aws site-source finder](scripts/02p_CH_Aws_native_tower_source_availability_readonly.py) consumes the exact saved Stage02O JSON and inventories **only the CH-Aws site folder**: `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws`. It lists plausible original tower sensor/raw/processed product filenames, CSV header columns indicating RH/TA/QC/VPD, lightweight JSON provenance/metadata references, and ZIP/TAR archive member **names only**. Existing annual DATM model NC files are excluded from native-source candidate output; `raw/...FLUXMET_HH` is classified as **processed**, never original instrument QC. Source-search limits and truncation flags are included, so a missing sensor file under this one root does **not** demonstrate nonexistence elsewhere.

Run after downloading the immutable merged-commit script and checking exact `git hash-object`:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02o "$HOME/ICOS_Batch04_stage02o_hLF8GLFP/results/stage02o_CH_Aws_20_event_risk_triage.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Outputs `stage02p_CH_Aws_native_source_availability.json` and `stage02p_CH_Aws_source_file_headers.csv` exclusively into the standalone new empty HOME directory, without editing any source, CIME, Git tree or Slurm jobs. Further event-level native tower RH/TA/QC and independently grounded ERA5 source checks require positive source discovery and provenance; **all six Batch04 stations remain science HOLD**, no AD5/AD400 submissions.

## Stage02P actual result — no independently identified native RH/QC inside CH-Aws site tree

[Actual source-pinned Stage02P output (1 November 2026)](docs/stage02p_operator_IRIDIS6_result_20261101.md) scanned 169 files, `TRUNCATED False`, under the CH-Aws site tree, including 72 annual model DATM files, four processed-multisource source candidates and their metadata, original distributed EUF BIF/BIFVARINFO and processed FLUXMET_HH, plus the Stage21/25/34/38/42 humidity revision evidence. **No independently identified unfilled native tower RH/QC file** was detected in that bounded site root. This is **not evidence that genuine sensor data do not exist elsewhere**. The key time-provenance finding is the original Stage21/25 ledger field `time_local_standard_UTCplus1`, contrasting with original FLUXMET `TIMESTAMP_START`/`TIMESTAMP_END` and later revision ledgers' generic `time` field.

## Stage02Q — historical UTC+1 ledger/source metadata discovery

[Stage02Q read-only tool](scripts/02q_CH_Aws_original_BIF_localtime_and_native_source_search_readonly.py) accepts the **saved Stage02P and Stage02O JSONs** and independently opens the original EUF `BIF`, `BIFVARINFO_HH`, Stage21 and Stage25 revision-ledger CSV files from paths pinned in Stage02P. For all 20 high-contrast DATM event labels, it records literal Stage21/25 local-standard-time matches at 0, ±30, and ±60 minutes, **without assuming UTC or selecting a clock conversion**, plus relevant source metadata rows. An optional `--extra-root "$HOME"` conducts only a 3-level, 15,000-file bounded **filename-only** look for CH-Aws/Weissenstein candidate source packages outside the site tree; it follows no symlinks and does not imply a comprehensive archive inventory. This stage does not read the full 372 MB FLUXMET file or alter sources.

Example after source/hash verification:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02p "$HOME/ICOS_Batch04_stage02p_D6TUjQg7/results/stage02p_CH_Aws_native_source_availability.json" \
  --stage02o "$HOME/ICOS_Batch04_stage02o_hLF8GLFP/results/stage02o_CH_Aws_20_event_risk_triage.json" \
  --extra-root "$HOME" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Reports: `stage02q_CH_Aws_clock_and_source_provenance.json` and `stage02q_CH_Aws_stage21_25_time_hypotheses.csv`. **No source QC/time approval, no forcing revision, no AD5/AD400 or Slurm submission**. While CH-Aws native humidity provenance is blocked, parallel read-only stream/PFT/soil scientific preflights can proceed for DE-Gri, DE-RuR, IT-Tor and ES-Agu; GL-ZaH needs a private Arctic shrub map.

## Stage02Q source-metadata scanner defect and corrected rerun (1 November 2026)

The initial Stage02Q IRIDIS6 `SOURCE VERIFIED` and self-test both passed, but the data run then failed **before any Stage02Q report was created** in `describe_metadata -> read_csv` with `ValueError: Unexpected >5000-row bounded metadata file`. This was an **artificial common CSV row cap**, not a tower/ERA/forcing data quality failure. [Bugfix and evidence note](docs/stage02q_metadata_gt5000_row_bugfix_20261101.md).

The revised script retains the original site-/path-pinned read-only data source and 20-event science HOLD, but **streams the potentially >5000-row BIF/BIFVARINFO metadata tables** (up to 100,000 rows under the existing 2 MB input-size guard), retains topic-specific RH/VPD/QC/time examples including rows beyond 5,000, and tests a 6,003-row synthetic metadata case. Stage21/25 ledgers still have separate bounded row scans and no inferred UTC conversion. Only rerun Stage02Q from the **new merged commit with exact Git blob checksum** into a fresh empty HOME output directory; no Stage02A–P rerun, forcing editing or Slurm submission.

## Stage02Q complete (1 Nov 2026): original BIF UTC+1 and earlier source audits found

[Stage02Q actual IRIDIS6 operator output](docs/stage02q_operator_IRIDIS6_result_20261101.md) confirms the repaired streaming reader completed original EUF **BIF 5,192 rows** and **BIFVARINFO_HH 1,027 rows**, with BIF `GRP_UTC_OFFSET`/`UTC_OFFSET=1`, `GRP_ONEFLUX PRODUCT_SOURCE_NETWORK=EUF`, and original ERA-downscaled TA/PA/VPD provenance metadata. The original Stage21/25 `time_local_standard_UTCplus1` ledgers have 779 and 30 rows but **no literal ±60-minute overlap** with the 20 specifically selected high-QBOT Stage02O event labels. This does NOT imply a bad timezone: they may describe different event scopes. HOME's bounded search inspected **5,357 filenames**, found **128** CH-Aws related candidates and was not truncated. Crucially, the operator discovered pre-existing Stage03, Stage06 and Stage09 source investigations under `$HOME/FLUXNET_MultiSite_11` — especially `stage09_CH_Aws/01_timezone_alignment.csv` and `stage09_CH_Aws/02_CH_Aws_559_event_reference_comparison.csv`. No independently verified unfilled tower RH was yet found at the selected events.

## Stage02R — actual historical time-alignment, source status and RH/VPD BIF groups

[Read-only Stage02R code](scripts/02r_CH_Aws_historical_timezone_and_RH_provenance_readonly.py) reads the saved Stage02Q JSON and **source-pins** seven named historical small Stage03/06/09 CSV/JSON files from the exact Stage02Q candidate paths (including the historical timezone alignment and original humidity review), the original small BIF/BIFVARINFO CSV metadata, and the original Stage21/25 source ledgers. It reports all relevant group-level `VAR_INFO_VARNAME` `RH`, `VPD_F`, `VPD_F_QC`, `TA_ERA`, UTC offset and QC metadata; time-range boundaries for the two old local-standard ledgers; and ±30/60-minute raw timestamp candidates from historical QC tables, without choosing a UTC conversion or manufacturing tower truth. Only a new JSON and CSV under an empty standalone HOME folder are written. Original forcing, FLUXMET, NetCDF, CIME, Slurm and Git working tree remain untouched.

To run once verified with the exact immutable file SHA:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02q "$HOME/ICOS_Batch04_stage02q_fixed_bsOEPjTg/results/stage02q_CH_Aws_clock_and_source_provenance.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

All six Batch04 stations remain **scientific HOLD**. No automatic RH34A/RH38A/RH42A release or AD5/AD400 submission based on MDS vs ERA similarity.

## Stage02R successful original QC definitions and earlier alignment evidence (1 November 2026)

[Stage02R actual IRIDIS6 result](docs/stage02r_operator_IRIDIS6_result_20261101.md) has a complete original BIF/BIFVARINFO RH/VPD/QC group reconstruction: `VPD_F` consolidates MDS plus downscaled `VPD_ERA`; `VPD_F_QC=1` explicitly means **good-quality gapfilled** for this site's source product, rather than directly measured humidity. `RH` is listed at 1.5 m in BIFVARINFO, but has **no numeric original native RH for the 20 high-contrast events**. BIF `UTC_OFFSET=1`, yet the earlier Stage09 model-offset tests on 57,581 QC0/QC1 temperature points had stronger numerical ERA5 agreement at their tested 0-hour offset (r=0.88405, RMSE 3.1953°C) than tested +1 hour (r=0.86479, RMSE 3.4145°C). Stage09 used Open-Meteo historical ERA5 and ERA5-Land products, which are **related reanalyses, not independent tower observations**, and retained manual clock verification. Earlier Stage03 had 559 invalid original candidate humidity pairs, 77 priority fallback events and 86 pair-source changes; source candidate status `REVIEW_REQUIRED`. Stage03's input register identified the *independently distributed but related processed* `EUF_ERA5_HH_1981-2025` input path alongside FLUXMET_HH; Stage03's path metadata **does not prove the ERA5 file still exists now**.

## Stage02S — original EUF ERA5 product vs FLUXMET clock/VPD cross-check

[Stage02S read-only source alignment code](scripts/02s_CH_Aws_original_EUF_ERA5_to_FLUXMET_clock_readonly.py) reads the operator-saved Stage02R and Stage02L JSONs and attempts to verify the **exact on-disk Stage03-listed EUF_ERA5_HH input**. If present, it streams only that original ERA5 source once (<2 GB, <=1m rows) using fast exact timestamp-label lookup, comparing 20 selected event `FLUXMET TIMESTAMP_START/TIMESTAMP_END VPD_ERA` and `TA_ERA` with the original separate EUF ERA-source `TIMESTAMP_START/TIMESTAMP_END` under literal **-120 to +120 minute** clock-label hypotheses. This identifies possible source timing/processing discrepancies **without approving a UTC conversion or ranking forcing**. If absent, writes a verified **SOURCE_HOLD** report rather than inventing an ERA substitute.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02r "$HOME/ICOS_Batch04_stage02r_2zMBe7n8/results/stage02r_CH_Aws_original_metadata_legacy_clock_review.json" \
  --stage02l "$HOME/ICOS_Batch04_stage02l_PDjpMDmW/results/stage02l_source_clock_QC_matrix.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Only new JSON/CSV in a standalone empty HOME directory; the large FLUXMET product is **not** reread, no source changes/Slurm. All six Batch04 site science releases remain HOLD, including CH-Aws native tower RH/ERA/clock and GL-ZaH site-only Arctic map. Do not submit AD5/AD400 until independent station-specific science gates pass.

## Stage02S complete: original EUF_ERA5_HH is missing at the recorded path

[Operator Stage02S actual result, 1 Nov 2026](docs/stage02s_operator_IRIDIS6_missing_original_ERA5_20261101.md): source-pinned code and self-test PASS, but Stage03's expected `EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv` was **not present at its recorded original-distribution path**. The script correctly reported `MISSING_ORIGINAL_DISTRIBUTED_ERA5_HH_INPUT`, `SOURCE_HOLD`, **0 rows scanned / 0 comparisons**. There is **no new clock evidence or invalid meteorological measurement** from that test. The processed FLUXMET source still contains ERA-derived fields; they are not independent original sensor RH.

## Stage02T: search exact original ERA5 source filename and ZIP members (read only)

[Stage02T source-archive forensic checker](scripts/02t_CH_Aws_missing_EUF_ERA_source_archive_readonly.py) consumes the saved Stage02S+Stage02R JSONs, requires their science-HOLD and exact Stage03 ERA filename/path pins, and performs bounded **filename-only** searching under the scoped CH-Aws site tree plus `$HOME/FLUXNET_MultiSite_11`. For candidate ZIP archives it reads only the ZIP **central directory and member names**, without extraction, download or opening the large processed FLUXMET CSV. It reports whether the exact `EUF_CH-Aws_FLUXNET_ERA5_HH_1981-2025_v1.3_r2.csv` is present or named in an archive, with scan truncation flags and no claim of source integrity or scientific approval.

Run after downloading exact merged-commit source and verifying its Git blob SHA:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02s "$HOME/ICOS_Batch04_stage02s_krFdN4ko/results/stage02s_CH_Aws_original_EUF_ERA_time_comparison.json" \
  --stage02r "$HOME/ICOS_Batch04_stage02r_2zMBe7n8/results/stage02r_CH_Aws_original_metadata_legacy_clock_review.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Output `stage02t_CH_Aws_ERA5_original_source_location.json` and `stage02t_CH_Aws_archive_source_candidates.csv` under the new empty HOME folder only. No source, case/NetCDF, Git working tree, or Slurm changes. If the original product is genuinely unavailable under these bounded roots, document that gap and prioritize independent source/PFT/soil validation at the four other non-Arctic sites rather than repeatedly optimizing RH34A/38A/42A against non-independent ERA data. **All six Batch04 sites remain science HOLD**.

## Stage02T completed — original CH-Aws EUF ERA5 source not found under scoped roots (1 Nov 2026)

[Actual Stage02T operator record](docs/stage02t_operator_IRIDIS6_result_20261101.md): SHA-verified code/self-test PASS, exactly 169 CH-Aws site-tree filenames and 252 historical `FLUXNET_MultiSite_11` filenames scanned, **0 candidate files/ZIP source members** under these two explicit limited roots; both `TRUNCATED False`. `EXACT_CSV_FOUND False`, `EXACT_ZIP_MEMBER_FOUND False`. This means the Stage03-registered independent distributed EUF `ERA5_HH_1981-2025` CSV was **not recovered in this search**, not that ERA fields or actual original sensor observations do not exist elsewhere. CH-Aws humidity, clock and ERA representativeness gates remain scientific HOLD. Pause duplicate RH/ERA comparison loops; recover original archive only with verified provenance if it becomes available.

## Stage02U — four-site original-case DATM/surface/soil/PFT static preflight

[Read-only Stage02U script](scripts/02u_four_site_case_DATM_surface_soil_PFT_static_readonly.py) and [scope/checklist](docs/stage02u_four_site_static_gate_plan_20261101.md) move the separate four-site cohort **DE-Gri, DE-RuR, IT-Tor, ES-Agu** forward, reusing the existing Stage02C and **74-file successful Stage02D** JSON reports. It does **not** rerun all numerical forcing checks. Instead it audits eight unselected original S30EXCL/SHARED cases: exact source annual DATM references vs case `Buildconf/datm.input_data_list`, generated static CaseDocs `datm_in`/`lnd_in` and stream documents, original surface NetCDF point/landunit/PFT/soil fractions and FATES parameter paths, and case-pair configuration differences. All results remain static and observationally unverified; original source tower QC and actual runtime DATM binding are still HOLD. It does not change cases, soil, FATES, surfaces or Slurm.

Run a SHA-pinned downloaded Stage02U script in the existing `clm_fates_env`:

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --stage02d "$HOME/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

Only outputs a new JSON plus eight-row CSV under a standalone EMPTY HOME directory. Inspect site/CIME/surface/soil/PFT exceptions in those reports before separate source-QC and actual FATES mapping science decisions. ES-Agu's conditional bare 49/shrub 22/C3-grass 29 proxy is **not measured ground cover**; GL-ZaH private Arctic map and CH-Aws source QC are separate unresolved tracks. No AD5/AD400 submission.

## Stage02U operator result (1 Nov 2026) — eight static DATM list mismatches, original surface versus model PFT proxy

[Exact Stage02U operator console evidence and original NATVEG/CROP/PFT/soil numbers](docs/stage02u_operator_IRIDIS6_result_20261101.md): 8 original S30EXCL/SHARED case folders over DE-Gri/DE-RuR/IT-Tor/ES-Agu, previous 74 annual NC internal Stage02D `FLAGS {}`, all eight original static site points matched; each site-pair uses the **same original surface** and **same FATES parameter path**, with no differences in the inspected XML science or `lnd_in` keys. However, all eight `DATM_STATIC_LIST_MATCH False` require diagnosis before trusting input paths. The earlier Stage02U's narrower regex can differ from Stage02B's original absolute NetCDF list parser (e.g. potential `.nc4` truncation); **do not conclude this is an actual active forcing failure yet**. Original surface `PCT_NATVEG` and `PCT_CROP` are respectively DE-Gri 62.674/37.326, DE-RuR 78.891/21.109, IT-Tor 89.915/10.085, ES-Agu 71.461/28.539 (%). Original conditional NATPFT compositions differ sharply from the operator-accepted candidate proxies (three grass-only, ES-Agu bare49/shrub22/C3grass29); those crop fractions are separate landunits, not automatically grass/bare. IT-Tor original surface `ORGANIC` is 0 in all ten inspected layers and needs source review.

## Stage02V — source-verified eight-case DATM reference parser reconciliation and NATVEG/PFT difference

[Stage02V read-only script](scripts/02v_four_site_DATM_parser_and_landunit_provenance_readonly.py) takes the saved Stage02U **and Stage02C** JSON reports, checks four exact sites/eight source cases, parses each original `Buildconf/datm.input_data_list` with Stage02B's established NetCDF filename grammar and the prior Stage02U grammar, then compares literal and resolved source paths with original Stage02C 22/15/18/19 annual site DATM paths. Any mismatch produces exact source input lines and missing/unexpected path excerpts, and no runtime binding is assumed. It additionally extracts original source `PCT_NATVEG`, `PCT_CROP`, conditional `PCT_NAT_PFT`, the operator model-proxy difference and soil organic bounds from the **already saved Stage02U result**. This audits neither observed tower-footprint PFT nor native meteorological source QC. Only two new reports are created in a new empty HOME directory, with no NetCDF, CIME, FATES or Slurm writes.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02u "$HOME/ICOS_Batch04_stage02u_EFhTiiqx/results/stage02u_four_site_case_surface_soil_PFT_static_audit.json" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

All four stations remain HOLD. If Stage02V verifies original CIME source list paths, that alone does **not** approve active DATM stream binding or a crop/natural-area transformation, and must not trigger AD5/AD400.

## Stage02V verified on IRIDIS6 — all eight CIME DATM static input paths match

[Stage02V operator result and requested GitHub PFT manual-review register](docs/stage02v_operator_GitHub_authoritative_PFT_manual_review_20261101.md): both cases at each of DE-Gri, DE-RuR, IT-Tor, ES-Agu returned `OLD_PARSE 0`, but the original Stage02B parser found exactly **22/15/18/19** annual NC references with `PATH_EXACT True`, `PATH_CANON True`, `NC_EXIST True` (**8/8** case sets). The earlier Stage02U `DATM_STATIC_LIST_MATCH False` was a parser false negative. **Do not re-write, rename or resubmit the 74 original annual DATM files**; active runtime stream remains a separate science gate.

## Stage02W — current authoritative GitHub PFT register and human decision gate

By explicit operator instruction, use the [current 26 October 2026 official 38-site GitHub PFT registry](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv), not the mismatched old gridded surface vector, as the **proposed station model PFT**. The source 24 Oct MASTER and the [six-site bare-ground evidence report](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/SIX_SITE_BARE_GROUND_PFT_EVIDENCE_20261025.md) are complementary evidence, not equivalent cover-area observations. Formal registry site statuses are **CANDIDATE (qualitative)** for DE-Gri, DE-RuR, IT-Tor: **HLM 13 C3 grass 100%** each. ES-Agu is **PROPOSED**, **HLM 0 bare 49% / HLM 13 cool C3 grass 29% / HLM 9 evergreen shrub 22%**. All four have `fixnc_cohort=Not assigned`: **none has been granted approval for a replacement Batch04 surface**. Existing static cases still referenced original CLM surface: NATVEG%/CROP% DE-Gri **62.674/37.326**, DE-RuR **78.891/21.109**, IT-Tor **89.915/10.085**, ES-Agu **71.461/28.539**. These differ strongly from proposed **conditional NATPFT**, but they have different landunit bases and the comparison alone cannot falsify site studies. **IT-Tor original 10 soil-layer ORGANIC values all 0** require separate source review. The older ES-Agu `~65% vegetation` plot evidence and newer `51% vegetation/49% nonvegetated` ground survey need **manual confirmation of denominator/footprint**.

[Read-only Stage02W official PFT gate](scripts/02w_four_site_official_GitHub_PFT_manual_gate_readonly.py) reads the saved Stage02V and **SHA-checked** downloaded official PFT CSV to verify the registry strings, source ecology evidence statuses and original surface-vs-proxy discrepancies, and produces 8 evidence rows with **PFT MANUAL REVIEW** on every site. It does not choose or write new surface/landunit/FATES parameters or submit cases.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02v "$HOME/ICOS_Batch04_stage02v_9MKZUOLs/results/stage02v_four_site_DATM_parser_landunit_review.json" \
  --pft-register "$PINNED_GITHUB_FINAL_38_CSV" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

If the operator approves a proposed site PFT, construct a **new isolated site-specific model surface**, making explicit that `PCT_NAT_PFT` percentages are conditional on `PCT_NATVEG` rather than the original full-gridcell crop share. Verify effective runtime FATES HLM mapping and original tower source/soil QC before AD5/AD400. No automatic PFT overwrite.

## 1 Nov 2026: user APPROVED four official GitHub PFT model proxies after Stage02W

**Decided:** use the official [2026-10-26 ICOS FIXNC PFT registry](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv) for the four Batch04 non-Arctic follow-up sites. **DE-Gri, DE-RuR, IT-Tor = HLM13 cool C3 grass 100%**; **ES-Agu = HLM0 bare 49%, HLM9 evergreen temperate shrub 22%, HLM13 cool C3 grass 29%**. These four **FIXNC model proxy selections are now operator-approved**; no further PFT-choice approval is needed. They remain model representations of ecosystems, not measured EC-tower footprint PFT-area fractions. The scientific 38-station registry retains its original evidence grades and is NOT rewritten to imply direct observational evidence. Full decision, soil/PFT caveats and audited Batch03 method: [operator approval / Stage02X plan](docs/stage02w_operator_PFT_approval_stage02x_plan_20261101.md). Machine-readable 1-Nov approval overlay: [four-site approved PFT CSV](data/stage02x_operator_approved_four_site_GitHub_PFT_20261101.csv).

**Stage02W actual operator output:** GitHub source check PASS; `STAGE02W SELF-TEST PASS`; 8/8 original source cases mismatch the official new NATPFT proxy, as expected for unchanged gridded original surfaces; **`PFT_OPERATOR_RELEASE 0/4` describes the earlier decision status** at the time Stage02W ran, superseded for *PFT selection only* by the user approval above. Original 8/8 CIME DATM path lists were verified by Stage02V; all original forcing inputs remain untouched. The real old landunits (NATVEG 62.674/78.891/89.915/71.461% at respective four sites) are **gridcell landunit areas**, unlike the approved conditional natural-PFT vector.

### Stage02X: source-preserving new site-point PFT surface candidates — plan first, no Slurm

[Stage02X script](scripts/02x_four_site_approved_GitHub_PFT_surface_candidates.py) implements the established independent Batch03 FIXNC model-point surface convention: **PCT_NATVEG=100%, PCT_CROP=0%, other landunits 0%, PCT_NAT_PFT approved 15-vector conditional on NATVEG**. `self-test` and `plan` are read only; `plan` validates Stage02U+W report identities, original source schema, original point locations, 10-layer PCT_SAND/PCT_CLAY/ORGANIC, source SHA, FATES host13/host9 map, and nocomp bare support for ES-Agu, without writing anything. `build` (only after plan success, exact operator-confirm token, and fresh EMPTY output directory) creates four independent SHA-recorded **candidate** NetCDF point surfaces; old original source surface, cases and forcing remain unchanged. Soil data are **inherited but NOT validated against site measurements**, especially IT-Tor `ORGANIC=0` for all ten original layers. No new CIME cases or Slurm submissions.

~~~bash
python3 -B "$SCRIPT" self-test
python3 -B "$SCRIPT" plan \
  --stage02w "$HOME/ICOS_Batch04_stage02w_7wTwcDfO/results/stage02w_four_site_GitHub_PFT_manual_science_gate.json" \
  --stage02u "$HOME/ICOS_Batch04_stage02u_EFhTiiqx/results/stage02u_four_site_case_surface_soil_PFT_static_audit.json"
~~~

The PFT selection gate is **APPROVED**; **native tower forcing/QC, true CIME streams, soil science (especially IT-Tor), and AD5/AD400 submission remain separate HOLDs**. CH-Aws RH and GL-ZaH Arctic private-map are unaffected.

## Stage02X actual IRIDIS6 success — four isolated PFT point-surface candidates created

[1-Nov Stage02X operator source/SHA and run results](docs/stage02x_operator_four_PFT_surface_candidates_created_20261101.md) confirm `STAGE02X PLAN PASS` and successful explicit `build` of **4 new NetCDF point-surface candidates** at `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn`. New files are `<site>_B04_GITHUBPFT_POINT_CANDIDATE.nc` for DE-Gri, DE-RuR, IT-Tor and ES-Agu, all with exact SHA256 recorded in the linked report. PFT values follow the user's already approved Oct26 GitHub register, with *model-point* `NATVEG=100` and `CROP=0`; original source surface and inherited soil remain unchanged. Local ES-Agu nocomp bare-ground interface and source FATES host9/13 map checks passed.

**Status after this Stage02X run: PFT decisions 6/6; new PFT candidate surfaces 4/6; new FIXNC isolated simulation cases submitted 0/6.** Two unbuilt surfaces are CH-Aws (original RH/ERA source HOLD) and GL-ZaH (site-only Arctic FATES host9/11 mapping). The four existing original S30SHARED/S30EXCL pairs **do not** yet use these new candidate surfaces. Next: verify all SHA256 receipts, inspect **actual effective case DATM stream, model fsurdat and FATES mapping** for the four candidates and independently audit native meteorology and soil, especially IT-Tor's ten-layer ORGANIC=0. There is no science release for AD5/AD400 or Slurm until each site passes those independent gates. Never silently overwrite original cases, shared FATES map, forcing or surface.

## Stage02X SHA verification completed (1 November) and Stage02Y read-only static input binding

The operator independently confirmed all four new [Stage02X candidate point-surface SHA256 values and manifests](docs/stage02x_four_surface_SHA_verified_stage02y_plan_20261101.md) with `sha256sum -c` **PASS 4/4**, and all four `<site>_B04_surface_manifest.json` present in `/iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn`. No rerun/rebuild of Stage02X is required. Model-PFT decision and four candidate builds are now **complete**, but zero NEW isolated CIME cases have been prepared/submitted and four sites still have unreviewed original native meteorology and soil source/QC.

[Stage02Y read-only static CIME source-to-candidate checker](scripts/02y_four_site_candidate_surface_static_CIME_binding_readonly.py) recomputes exact SHA/receipts and source-surface SHA, compares inherited original sand/clay/ORGANIC/lat/lon and new NATVEG100/CROP0/host 15-PFT vectors, then inspects eight original S30EXCL/SHARED `CaseDocs/lnd_in`, `datm_in`, stream documents and current DATM input data lists versus saved original Stage02C/02V evidence (22/15/18/19 annual paths). The old case `fsurdat` is still expected to point to the **original** grid surface, **not** the new verified candidate. This is static evidence, not proof of runtime DATM stream loading or native tower observations; IT-Tor ten-layer soil `ORGANIC=0` is a separate HOLD. No changes to original source, cases, FATES, force inputs, jobs, or Git worktree.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02v "$HOME/ICOS_Batch04_stage02v_9MKZUOLs/results/stage02v_four_site_DATM_parser_landunit_review.json" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --candidate-dir "/iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn" \
  --out-dir "$NEW_EMPTY_REPORT_DIR"
~~~

The resulting Stage02Y JSON+CSV are the inputs for a **separate** source-QC/soil and isolated case creation gate. **Do not submit AD5/AD400 automatically after passing Stage02Y**. Six-site status: PFT accepted 6/6; new PFT point surfaces ready 4/6; new simulations submitted 0/6; CH-Aws RH/ERA and GL-ZaH Arctic FATES mapping are still unresolved.

## Stage02Y actual IRIDIS6 success — four original CIME case pairs still use old surfaces, DATM stream field requires diagnosis

[Actual Stage02Y operator output and Stage02Z plan](docs/stage02y_operator_IRIDIS6_result_stage02z_plan_20261101.md): original Stage02Y source/self-test pass; **4/4** previously built GitHub PFT point surface SHA256 and unchanged soil probes verified; **8/8** original S30EXCL/SHARED CIME cases inspected; all eight exact site-year DATM source-path lists still match Stage02C/V (**22 / 15 / 18 / 19** distinct year files). **All eight original cases still point to the old source surface; zero original case bindings to the new PFT candidate surfaces is expected**, because isolated FIXNC cases have not been created. In all eight old CaseDocs/datm_in outputs, the narrow search printed **DATM_STREAM_FIELD MISSING**, while one stream-related CaseDocs document was detected per case. This is **not proof the DATM stream is broken**.

[Stage02Z read-only source-scoped DATM stream forensic](scripts/02z_four_site_eight_case_DATM_stream_source_forensics_readonly.py) uses the original saved Stage02Y output to inspect each generated CaseDocs/datm_in, original stream-related file, env_run.xml, and source Buildconf/datm.input_data_list for literal DATM stream definition and mode evidence; prints short source excerpts and writes only a new report JSON+CSV under an empty HOME folder. No CIME file mutation, preview, model run, forcing, NetCDF, FATES map, or Slurm operation. Continue original tower meteorology / actual CIME runtime / soil source science HOLD after Stage02Z; especially IT-Tor ten original ORGANIC layers remain zero. The operator-approved four PFT candidates must **not** be reselected or overwritten.

Run the exact blob-pinned script once:

    python3 -B "$SCRIPT" --self-test
    python3 -B "$SCRIPT" \
      --stage02y "$HOME/ICOS_Batch04_stage02y_pT2JPSjW/results/stage02y_four_site_candidate_surface_case_binding_audit.json" \
      --out-dir "$NEW_EMPTY_DIR"

## Stage02Z completed and Stage03A original meteorology QC source discovery

[Actual Stage02Z eight-case source-stream finding and Stage03A plan](docs/stage02z_operator_result_stage03a_original_met_QC_plan_20261101.md): all eight original Batch04 S30EXCL/SHARED cases have DATM_MODE=1PT and a generated CaseDocs/datm.streams.xml containing station-specific annual NC filenames, CLM_USRDAT.UNSET, taxmode=cycle and the correct site years (DE-Gri 2004–2025, DE-RuR 2011–2025, IT-Tor 2008–2025, ES-Agu 2006–2024). The absent literal streams assignment inside datm_in is not itself an error; it is stored in a separate CIME stream XML. Stage02D previously found no internal numeric flags in the 74 referenced annual NCs, but **native station-source met QC, exact observation-versus-MDS/ERA provenance, local UTC clocks and replacement proportions have NOT been verified**.

[Stage03A read-only original HH source/QC candidate inventory](scripts/03a_four_site_original_HH_tower_QC_provenance_discovery_readonly.py) consumes saved Stage02C, Stage02D first-four and Stage02Z report JSONs; scans only the four station source directories with strict file/count/depth limits; inspects candidate ICOS/FLUXNET BASE/BIF/FLUXMET_HH/ERA_HH source filenames and bounded CSV/ZIP/GZIP/NC headers for half-hourly time, native/QC and ERA fields. It does not make scientific conclusions from filenames, decompress full products, reprocess 74 NCs, modify case/surface or submit Slurm. Produces JSON/CSV in new empty HOME folder. The next data QC stage can then choose exactly source-pinned original sensor/processed products and compare timestamps/QC/values with DATM, while IT-Tor soil ORGANIC=0 is separately held.

    python3 -B "$SCRIPT" --self-test
    python3 -B "$SCRIPT" \
      --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
      --stage02d "$HOME/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.json" \
      --stage02z "$HOME/ICOS_Batch04_stage02z_bTwLfYMG/results/stage02z_eight_original_DATM_stream_document_audit.json" \
      --out-dir "$NEW_EMPTY_DIR"

All six Batch04 sites remain non-submitted; four GitHub PFT point surfaces were already created and SHA256-verified. CH-Aws humidity/source and GL-ZaH Arctic-map gates are separate. No AD5/AD400 by this step.

## Stage03B-REUSE — do not repeat original FLUXNET13 already completed MET QC

**Operator strategy correction (1 Nov 2026):** These four Batch04 sites are **not a new source forcing cohort**. All four DE-Gri/DE-RuR/IT-Tor/ES-Agu were already included in [earlier FLUXNET_MultiSite_13](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/FLUXNET_MultiSite_13). Reuse its **Stage28 selected 13-site MET forcing (inherits Stage22 whole MDS envelope QC and Stage26), Stage29b/30 BIF ZBOT + annual DATM SHA manifests** rather than again running generic full FLUXMET HH source QC. Stage28 **13/13 numerical PASS** does not approve source meteorological science; **DE-Gri 49 original flagged MDS blocks**, DE-RuR 2012-07-27 measured rainfall, IT-Tor extreme rain and ES-Agu 2018-09-15 extreme rainfall remain targeted provenance questions. DE-RuR's BIF TA sensor reference height is **time dependent** (first 2.58m), other three DE-Gri 2m, IT-Tor 1.8m, ES-Agu 2.7m static.

[Full scientific historical source review, exact Stage28/29b paths, remaining site-specific issues and five AmeriFlux cohort lessons](docs/stage03b_reuse_FLUXNET13_legacy_QC_and_AmeriFlux_delta_method_20261101.md). The five AmeriFlux batches contribute a **delta-science QC** protocol: QC0 physical-event protection, raw versus consolidated MDS/ERA source semantics, complete QC1 fill intervals and source QC0 anchors, independent ERA vs packaged downscale distinction, native precipitation interval/UTC/BIF-ZBOT, contiguous HOLD episodes and manual approvals. Do NOT automatically apply five AmeriFlux site-level repair decisions to these four ICOS sites.

[Stage03B-REUSE read-only lineage script](scripts/03b_reuse_FLUXNET13_stage28_stage29b_source_lineage_readonly.py) checks historical Stage28 selected meteorological source paths/SHAs, Stage29b/30 271-year manifest against the four actual Stage02C CIME annual DATM path sets (74 names) and 12 representative original annual NC SHA/provenance attributes. **It does not rerun 74 full numeric files or 4 wide FLUXMET source series.** Only a new JSON/CSV report; all source/site/provisional scientific HOLDs retained. If lineage agrees, next Stage03C-DELTA should audit only unresolved recorded original QC0/QC1/VPD/precip and BIF instrument-time events. If it differs, hold and investigate exact alternate source-version years without rebuilding.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
  --stage02c "$HOME/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json" \
  --stage02d "$HOME/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.json" \
  --stage03a "$HOME/ICOS_Batch04_stage03a_8CKHbzkE/results/stage03a_four_site_original_met_source_QC_inventory.json" \
  --out-dir "$NEW_EMPTY_DIR"
~~~

The earlier proposed redundant wide FLUXMET Stage03B full scan is **superseded and not approved**. Existing PFT choices and 4 new point surfaces remain validated; original S30 variants not modified. No case creation or AD5/AD400 submitted. IT-Tor soil ORGANIC=0 is a distinct review gate.

## Stage03B-REUSE operator PASS; Stage03C extracts only the old outstanding science holds (1 November 2026)

Stage03B-REUSE has **actually passed on IRIDIS6**: `STAGE28_MET_SHA PASS` at **4/4** sites, exact old Stage30 vs present DATM annual source paths **22/22 DE-Gri, 15/15 DE-RuR, 18/18 IT-Tor, 19/19 ES-Agu** (= **74/74**), and representative original yearly NetCDF SHA256 **3/3** per site (= **12/12**). The current Batch04 forcing **IS** the previous [FLUXNET13 selected Stage28/29b/30 version](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/FLUXNET_MultiSite_13). **Do not repeat the general FLUXMET HH/QCv5/ERA scan or rebuild the 74 NC files**; the previous selected numerical QC is inherited. This does NOT grant scientific approval for original tower/ERA input.

[Detailed Stage03B operator result and narrowly targeted Stage03C plan](docs/stage03b_actual_pass_stage03c_legacy_targeted_QC_plan_20261101.md) records explicit historical unresolved questions: DE-Gri **49** old MDS/QC1 blocks; DE-RuR **2012-07-27** rain and **dated dynamic TA-height ZBOT (initial 2.58m)**; IT-Tor **2025 Oct/Nov 1,458-HH QC1/QC2 fill/source change**, intense rain and independently unverified all-zero soil ORGANIC; ES-Agu **2018-09-15** rain timing/amount and previously selected Stage12/15 changes. The old Stage28 seven-site heavy-rain file is NOT a complete 13-site rain ledger: prefer original Stage22 `06_all_precip_gt18mm_source_timing_review.csv`, and explicitly report its absence or any targeted event not covered by that >18mm threshold.

[Stage03C read-only historical issue extraction](scripts/03c_reuse_FLUXNET13_old_MDS_rain_BIF_hold_episode_register_READONLY.py) inputs the original operator Stage03B report plus the **exact old Stage22, Stage28, Stage29b reports**, checks original 82-block set and 69/49 pending-decision counts, extracts only four-site old source review actions into *new* JSON + 2 CSV files in an empty HOME directory. Preserves QC0/QC1 native records and all prior scientist/operator HOLD; does not re-run numeric QC or source CSV comparisons, does not edit original forcing, DATM, candidate point surfaces, CIME, FATES or Slurm.

~~~bash
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" \
 --stage03b "$HOME/ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json" \
 --out-dir "$NEW_EMPTY_DIR"
~~~

After this episode-index is confirmed, **Stage03D** should inspect ONLY the scoped original tower QC, source-processing/ERA alternatives, source rain P units/accumulation windows and dated BIF context needed to settle retained HOLDs, using the first five AmeriFlux cohort methods already summarized in [the inheritance report](docs/stage03b_reuse_FLUXNET13_legacy_QC_and_AmeriFlux_delta_method_20261101.md). No automatic ERA replacement, rainfall clipping or a new AD5/AD400 case on Stage03C alone.

## Stage03: full native-source forcing / soil / PFT science release (future)

For each station, the next separate audit must select one verified original source case and pin input checksums and true source years; cross-check DATM streams against annual NC and native tower half-hourly data; verify UTC/local-time convention, no-leap calendar, leap days, counts, gaps, year seams, VPD from T/RH/pressure, nonphysical humidity, precipitation timing, radiation and long flat runs. ERA5/ERA5-Land fallback must be checked against tower source QC, with every replacement documented and unresolved events retained as scientific HOLD. Do not blindly interpolate or relabel QC.

Check actual PCT_NATVEG/other landunits, tower coordinates and original selected point surface, and review sand/clay/silt by depth plus ORGANIC/peat and site vs grid fallback. Host PFT 0 bare is included in conditional NATVEG composition (no automatic renormalisation of green vegetation). Validate **effective FATES HLM→PFT map** against the parameter file in the new case's land namelist. GL-ZaH must independently create and verify its *site-only* Arctic shrub parameter candidate using the existing [six-site GL map tool](../ICOS_Unassigned_6/scripts/01_pft_six_and_GL_arctic_map.py), never modify the shared mapping.

## Stage 03 and subsequent model runs (NOT authorised by this commit)

Only after per-site forcing, source, surface, soil, host/FATES map and point gates pass should new versioned isolated B04 FIXNC surfaces/cases be prepared. Follow the standard independent **AD5 → AD395 → Normal5 → Normal395** protocol; check case.run/st_archive, CLM/DATM/CPL final restart, AD spinup_state=2 and Normal spinup_state=0, submitting-shell stack guard and inode quota. No AD400/Normal400 completion claim is made here.

Related protected workflows: [DE-Tha](../DE-Tha/README.md), [NL-Loo V3](../../docs/NL_LOO_THREE_PHASE_PLOTS.md), [Batch01](../Batch01_10/README.md), [Batch02](../Batch02_10/README.md), [Batch03](../Batch03_10/README.md).
