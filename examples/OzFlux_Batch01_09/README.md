# OzFlux 9-site Non-Competition CLM-FATES — operator-selected v1.1 PFT inputs

**Status 2026-11-02: Non-Competition OzFlux Stage01–05 OPERATOR SUCCESS on IRIDIS6 for read-only provenance checks.** Nine operator-selected v1.1 PFT vectors and 9/9 isolated fixed-PFT point Surface CANDIDATES (10/10 original L6 files) have been verified. Stage04 (operator report `ozflux_nc_stage04_20261102T223221Z_FIX`) verified 9 surface SHAs, 169 native source file-years (67 structurally eligible, 102 REVIEW/HOLD), and all six 2013–2018 AU-ASM Stage14 FSDS0 provisional DATM source/manifest/physical SHAs. The original Stage04 2015 hard-coded hash typo was corrected in separate PR #61, which must be merged before relying on `main`. Stage05 (operator report `ozflux_nc_stage05_20261102T224556Z_FIX`) independently reconciled 196 original 7-variable source-year QC series across AU-ASM 2013–2018, AU-DaS 2009–2021 and AU-Dry 2010–2018 against Stage08; source-QC episode segmentation passed. All source L6, provisional DATM, PFT, surface, CIME, existing AU-How and Slurm jobs remain unchanged. **No science-approved forcing, no AD5 and no AD400 authorised or submitted.**

The operator instructed: *use all the OzFlux PFT numbers already updated on GitHub for the non-competition experiment, and proceed*. Do **not** continue the AU-ASM historical 2018 derived-AGB forensic stages as a prerequisite to FIXNC PFT input selection. All SOURCE AGB evidence remains preserved in `CLM-FATES-single-site-workflows`; 2018 derived AGB is not validated observation.

## Exact upstream authoritative PFT source

The current reviewed PFT set is the **v1.1 final accepted** table in:
- Repo: [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows)
- **Source branch:** `oz-jp-pft-guidance-20261102` (not merged to `main` at the time of this snapshot).
- **Immutable source commit:** `d62c814585c4aa85731f77b4a555efe6ec9e94a3`
- **Source folder:** `examples/OzFlux_JapanFlux_PFT/`.
- The exact master input upstream Git blob is `815259f7fe189d9812d659f04e46726660880478`.
- The upstream CLM host matrix Git blob is `618d4cb8a7d66ceed0063e95f9c30d7ce7e2cd5a`; FATES matrix blob `b511c279d7bbebad9576ca4ae4e3e555ab8ed852`; roundtrip validation blob `c4ac72d4502657c8eb923f63626297f817827038`.
- **Copied snapshots in this repo** under `data/` preserve the original reviewed numerical values; the 20-site master is line-ending-normalized, other matrices are restricted to only nine OzFlux sites. All files are Git blob hash checked by Stage01. No alteration or silent renormalisation of bare ground.

This is the operator's fixed experimental PFT hypothesis, not an observed EC-footprint cover vector. The original evidence, temporal representativeness, caveats, 2018 dieback, AU-DaS clearing and AU-Tum fire history remain documented in the upstream PFT review; the operator has elected to run the fixed-state experiment nonetheless, with these distinctions reported.

## Nine site PRIMARY v1.1 fixed-composition vectors

Percentages are of **CLM natural vegetation landunit including bare host0** (not the sum normalized to 100% alive vegetation). `host0 bare` is not a FATES cohort. CLM `PCT_NAT_PFT_0...14` and live FATES vectors in `data` are cross-validated against the upstream master and 20-site source review.

| Site | Active FATES PFT fractions (% of natural landunit) | Bare host0 (%) | Origin caveat |
|---|---|---:|---|
| AU-ASM | FATES4 EBT 65; FATES14 C4 4; FATES13 CoolC3 2 | 29 | Historical Mulga reference, not dieback |
| AU-Cow | FATES1 TropEBT 100 | 0 | Rainforest, cyclone history not represented |
| AU-Cpr | FATES4 EBT 33; FATES7 evergreen shrub 10; FATES14 C4 3 | 54 | Pre-2014 mallee fire state |
| AU-DaS | FATES1 TropEBT 37.5; FATES14 C4 42.5 | 20 | Uncleared savanna; post-2022 clearing separate |
| AU-Dry | FATES1 TropEBT 26.6; FATES14 C4 49.4 | 24 | Dry savanna |
| AU-Gin | FATES4 EBT 45; FATES7 evergreen shrub 35 | 20 | High uncertainty, cover prior |
| AU-How | FATES1 TropEBT 39.8; FATES14 C4 44.3 | 15.9 | New FIXNC experiment, separate from old competition case |
| AU-Stp | FATES14 C4 65 | 35 | Mitchell grassland |
| AU-Tum | FATES4 EBT 100 | 0 | Pre-2019 tall eucalyptus-forest state |

All nine primaries have `DEFAULT14` mapping, zero to four nonzero PFTs, total natland 100% **including bare** and per-source `round_trip=PASS`. Example host FATES mapping: CLM host4→FATES1, host5→FATES4, host9→FATES7, host13→FATES13, host14→FATES14. Do not confuse this host mapping with FATES indexing; compare the actual `fates_hlm_pft_map` in each submitted CIME case before running.

## Stage01 operator successful completion — verified inputs

**Actual IRIDIS6 output:** `/home/ly3n24/ozflux_nc_stage01_20261102T215107Z`.
Corrected script `--self-test` PASS; original five snapshotted
source Git blobs verified; EXACT 9/9 accepted v1.1 PFT vectors and
DEFAULT14 host0 bare closure PASS.
ALL **10/10 original L6 NetCDFs for 9 site IDs** physically present:
AU-ASM 2/2, each remaining site 1/1. These are ORIGINAL meteorological
files and are NOT approved model DATM.
Only **AU-ASM** has an existing point CTSM-2000 reference
`/home/ly3n24/ozflux_stage16_reference_20261102T023647Z/surfdata_AU-ASM_hist_2000_16pfts_c261102.nc`,
SHA256 `18edace32d8e356c7d73269329dca7ed6338140e1ad1456f1a88691522c307fa`,
which still contains the unchanged generic GRID PFT proportions and
SOIL textures; it is not an existing AU-ASM FIXNC PFT-specific surface.
All 9 sites reported `new_FIXNC_surface_science_verified=False`.
The corrected script retained source inputs unchanged; no Slurm.

## Stage02 (published, operator pending) — isolated AU-ASM FIXNC surface candidate, eight-site source coordinate audit

Source `scripts/02_ozflux09_PFT_surface_ASM_pilot_and_eight_site_coordinates_READONLY_FIRST.py`
pinned commit **`c6d3ce3f4d170184e7a601c81d9e6db2ec13b5fd`**,
Git blob SHA **`1ec989b277031b4bbee4d5aac46b46492a91c411`**.

Two explicit modes:
- `--preflight`: reload actual Stage01 successful JSON and original
  source-blobs, check all 10 native NetCDF source files and **metadata-only**
  site latitude/longitude candidates, and verify exact SHA256, coordinate,
  15/16 PFT slot, 10-layer PCT_SAND/PCT_CLAY/ORGANIC properties of the
  AU-ASM Stage16 reference. Does not generate a new surface.
- `--build-asm --confirm CREATE_NEW_AU_ASM_FIXNC_PFT_SURFACE_CANDIDATE_ONLY`:
  repeats preflight and then copies the **unchanged original Stage16 reference**
  to a fresh direct HOME folder. Modifies **only**
  `PCT_NAT_PFT` **in the new copy** to natural-land host0 bare 29,
  host5 EBT FATES4 65, host13 CoolC3 2, host14 C4 4; other host classes
  and extra slot set to zero. Checks all other NetCDF variable values
  against the original reference by variable-by-variable equality,
  checks coordinates and source properties, and records SHA256/provenance.
  Original source, existing CIME cases and original DATM are unchanged.
  The original gridded **10-layer soil is retained** as a *reference,
  not yet an approved site-measured soil profile*.
- The same run produces a nine-site metadata-only coordinate report:
  any missing/conflicting L6 latitude/longitude is marked clearly
  and cannot be used to build a new CTSM point surface.
  There is **no guessing or automatic 8-site surface creation**.
- **No forcing or soil scientific approval, no effective runtime
  FATES parameter mapping verification, and no AD5/AD400 authorization**
  come from this candidate. In particular AU-How's existing COMPETITION
  case remains untouched.

Operator IRIDIS6 use (commit/git blob immutable, no original/Slurm writes):

```bash
(
set -euo pipefail
conda activate clm_fates_env
COMMIT="c6d3ce3f4d170184e7a601c81d9e6db2ec13b5fd"
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/OzFlux_Batch01_09"
CODE="$HOME/ozflux_nc_stage02_code"
SCRIPT="$CODE/stage02.py"
PRE="$HOME/ozflux_nc_stage02_pre_$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/ozflux_nc_stage02_ASM_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$CODE"
curl -fLsS --retry 3 "$BASE/scripts/02_ozflux09_PFT_surface_ASM_pilot_and_eight_site_coordinates_READONLY_FIRST.py" -o "$CODE/stage02.py.download"
test "$(git hash-object "$CODE/stage02.py.download")" = "1ec989b277031b4bbee4d5aac46b46492a91c411"
mv "$CODE/stage02.py.download" "$SCRIPT"
python3 -B -m py_compile "$SCRIPT"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --preflight --out "$PRE"
python3 -B "$SCRIPT" --build-asm --confirm CREATE_NEW_AU_ASM_FIXNC_PFT_SURFACE_CANDIDATE_ONLY --out "$OUT"
echo "STAGE02_PREFLIGHT=$PRE"
echo "STAGE02_ASM_SURFACE_CANDIDATE=$OUT"
)
```

**After operator execution:** review exact copied NetCDF
`surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc`
and the Stage02 JSON/TSV register. Next step: generate
separate CTSM2000 source-point references for the other 8 sites
ONLY at independently verified tower coordinates, then apply
the same Git-locked v1.1 host PFT vectors while keeping
site-specific soil/forcing gates clear. Build new isolated
FIXNC cases and test AD5 only after DATM/soil/effective-map checks.
Do not launch AD400 from the Stage02 candidate alone.

## Stage02 actual SUCCESS: AU-ASM isolated PFT candidate, nine source-L6 coordinate gate

**Operator actual successful run**:
`/home/ly3n24/ozflux_nc_stage02_pre_20261102T215809Z`
and `/home/ly3n24/ozflux_nc_stage02_ASM_20261102T215809Z`.
Git source SHA, Python syntax, self-test, Stage01 PFT snapshot
and Stage16 CTSM reference SHA passed.

New exact-isolated candidate:
`/home/ly3n24/ozflux_nc_stage02_ASM_20261102T215809Z/surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc`,
SHA256
`d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1`.
Natural-land host `PCT_NAT_PFT[0]=29`,
`[5]=65`, `[13]=2`, `[14]=4`, remainder zero.
Compared source/reference and candidate NetCDF **all variables**:
only `PCT_NAT_PFT` differs; grid soil and other source variables
preserved exactly. Original Stage16 reference unchanged.

All 9 site IDs have consistent original L6 global attribute AND
single-valued NetCDF variable latitude/longitude:

| Site | L6 metadata latitude | longitude | New FIXNC point PFT surface |
|---|---:|---:|---|
| AU-ASM | -22.2828 | 133.2493 | **CREATED; candidate only** |
| AU-Cow | -16.23819 | 145.42715 | not yet |
| AU-Cpr | -34.0027 | 140.5877 | not yet |
| AU-DaS | -14.1592 | 131.3881 | not yet |
| AU-Dry | -15.2588 | 132.3706 | not yet |
| AU-Gin | -31.376351 | 115.71377 | not yet |
| AU-How | -12.4952 | 131.15005 | not yet |
| AU-Stp | -17.1507 | 133.3502 | not yet |
| AU-Tum | -35.6566 | 148.1516 | not yet |

**Coordinate caveat:** These are exact **source L6** metadata
candidates, not separately verified against official tower site
registry. Do not imply independent site-location verification.
This source metadata is a reasonable conditional reference for
isolated CTSM2000 point extraction, with transparent uncertainty,
not necessarily a complete tower footprint.

## Stage03 published, actual run pending: remaining eight CTSM2000 point references + PFT candidates

Script:
`scripts/03_eight_site_CTSM2000_point_PFT_candidate_surfaces_SAFE_BUILD.py`,
GitHub commit **`485870b65832a6c28e83d77072158e7f0f1c138e`**,
Git blob **`ed37a66ad09f28dac02624570703045379eb5550`**.

- `--preflight` read-only: checks actual Stage01/Stage02 operator
  receipt and exact AU-ASM SHA, source-original v1.1 host PFT Git
  blob, all eight sites' source L6 lat/lon fields (global AND NetCDF
  scalar, numeric agreement) against **recorded original L6
  values**, and CTSM `subset_data` executable, source input
  grid/mesh and [surfdat]-scoped 2000 configuration. It prints
  the 8 new proposed PFT vector values and never creates a directory.
- `--build --confirm CREATE_EIGHT_ISOLATED_OZFLUX_FIXNC_SURFACE_CANDIDATES`
  repeats full preflight and only then runs the existing
  operator-verified CTSM `subset_data point --create-surface
  --create-user-mods` for each of the remaining eight stations
  into distinct, FRESH `$HOME` report child folders, 2000 base
  gridded source, exact original-L6 metadata lat/lon.
  For each site, keeps the generated CTSM 2000 reference
  unchanged, copies the point NetCDF to a **distinct FIXNC
  candidate** and changes only `PCT_NAT_PFT` to the frozen
  v1.1 host0 bare-preserving vector. The candidate is reopened
  and compared variable-by-variable to its generated reference;
  ten reference soil layers checked. Per-site source SHA256 and
  candidate SHA256 are recorded. Output includes partial site
  results if a later site's CTSM tool fails.
- Source **CTSM2000 gridded soil is NOT tower-site measured soil**.
  The script does not overwrite any source, AU-ASM candidate,
  old AU-How competition case, DATM or model config, and does
  not create a CIME case, invoke Slurm, AD5 or AD400.
- The next required stage after 8-source-surface candidates is
  **per-site DATM climate forcing and soil science checking,
  active FATES map and true CIME effective surface binding**,
  then an isolated per-site AD5 before AD400 promotion. The
  input PFT model scenario does not itself approve these
  outstanding conditions.

Copy/paste IRIDIS6 command pinned to the original script commit:

```bash
(
set -euo pipefail
conda activate clm_fates_env
COMMIT="485870b65832a6c28e83d77072158e7f0f1c138e"
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/OzFlux_Batch01_09"
CODE="$HOME/ozflux_nc_stage03_code"
SCRIPT="$CODE/stage03.py"
OUT="$HOME/ozflux_nc_stage03_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$CODE"
curl -fLsS --retry 3 "$BASE/scripts/03_eight_site_CTSM2000_point_PFT_candidate_surfaces_SAFE_BUILD.py" -o "$CODE/stage03.py.download"
test "$(git hash-object "$CODE/stage03.py.download")" = "ed37a66ad09f28dac02624570703045379eb5550"
mv "$CODE/stage03.py.download" "$SCRIPT"
python3 -B -m py_compile "$SCRIPT"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --preflight --out "$OUT"
python3 -B "$SCRIPT" --build --confirm CREATE_EIGHT_ISOLATED_OZFLUX_FIXNC_SURFACE_CANDIDATES --out "$OUT"
echo "SURFACE_DIR=$OUT"
)
```

**NOTE** `--preflight` does not create the supplied `--out`
path and `--build` requires it to still be fresh.
Eight `subset_data` calls may be moderately costly on login
nodes; respect IRIDIS6 login-node resource policy and stop
on cluster guidance. Do not claim a model run or completed
site science approval from Stage03. Actual operator result pending.

## Stage03 operator SUCCESS (2026-11-02): 9/9 fixed-PFT point Surface CANDIDATES now exist

Actual IRIDIS6 output:
`/home/ly3n24/ozflux_nc_stage03_20261102T220734Z`.
Original source/preflight, syntax and self-test PASS. Eight CTSM
`subset_data point --create-surface` calls succeeded, isolated
new reference and PFT-specific candidate NetCDF for each.
Every new candidate was checked against its own CTSM2000 original
point reference: **only `PCT_NAT_PFT` modified**, grid soil
reference **10 layers** and all other variable values unchanged.
The repeated CTSM tool warning about `--dompft` is informational;
the full requested PFT vectors were applied separately and independently
verified. No old AU-How COMPETITION case or original L6 modified.

| Site | PFT candidate SHA256 | CTSM soil layers |
|---|---|---:|
| AU-ASM (Stage02) | `d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1` | 10 |
| AU-Cow | `34a883bac4ae0cddae34774cf7ab8ba0043d0043c3e9fe3b4866677be98d7b5e` | 10 |
| AU-Cpr | `c2a003eb6235da2fd5bd03b340a66424bc9f298db23ac81239390a5cbf8b0671` | 10 |
| AU-DaS | `50cb8e60ea9f79059870d9230ad4e2ccdf3ea23112c7bd1cc2843cf2d5f79621` | 10 |
| AU-Dry | `77ce34d9637c8afad0745185fe2296b7a13745b10dac69b0ed37e0ac0f5ece44` | 10 |
| AU-Gin | `bc609b39f7239da03020a920224fbc986eea32bb582e5b0c7043c19a02321bae` | 10 |
| AU-How | `cedaf296f9e557d61559d00fafee8d0b636e993729f45f796bc6806372214cd0` | 10 |
| AU-Stp | `a7bf1a56df47fae71d7bf0ccc31669323d3e98c6ecf3e8f6630c6ad935158ca8` | 10 |
| AU-Tum | `8e6a600563781d32342f7e701a64974be6c25a21f1369f8f9fa4be680cb8f793` | 10 |

Coordinates come from each native source L6's internally consistent
global + NetCDF scalar metadata; independent station/footprint
location verification still pending. Surfaces are **source-consistent
PFT experimental candidates**, not approved soil or CIME inputs.
No AD5 / AD400, no source modifications.

## Stage04 actual first operator STOP — Stage14 path alias, corrected and awaiting rerun

**Actual IRIDIS6 operator first attempt** (2026-11-02):
Git source SHA VERIFIED, syntax PASS, self-test PASS, then
`ValueError: AU-ASM six-year FSDS0 source SHA or manifest changed:
 /home/ly3n24/ozflux_stage14_FSDS0_20261102T012038Z/AU-ASM_FSDS0_PROVISIONAL_DATM_2013.nc`.
In the initial Stage04 source, a compound `or` test included
`str(p)!=listed[y]["path"]`: this compares
`/home/ly3n24/...` against Stage14's original
`out.resolve()`-recorded `/iridisfs/home/ly3n24/...`,
which are two aliases for the **same file** on IRIDIS6.
The compound error message alone did **not** demonstrate a
genuine file SHA256 change. **Do not regenerate or
modify the six original AU-ASM provisional DATM files**.

**Source fix committed**:
`scripts/04_ozflux09_forcing_handoff_source_QC_and_surface_receipts_READONLY.py`,
commit `8bc23faa3fb08a53677efbe01763534565a9ff1c`,
git blob `04e3647425fecd8b5644b3068e3a21f7c087fb17`.
For each original 2013–2018 file, it now requires
`Path.resolve(strict=True)` equality between Stage14
manifest path and the actual candidate, then **independently
checks both manifest SHA256 and actual file SHA256** against
the six immutable original source values. It prints a
`AU_ASM_FSDS0_SHA_VERIFIED` line for each validated year
or gives a separate detailed missing-file, different-target,
manifest-hash or physical-file-hash error. No source or
report/NetCDF modification. A new self-test covers
HOME alias normalization without creating a fixture file.
**Corrected operator execution pending**; all surface SHA
and Stage07/08 upstream checks had already passed before
the first Stage14 compound-path stop.

## Stage04 forcing handoff — published, operator run pending

**Next real work is meteorological forcing**, not further PFT or
surface construction. Existing source study repo OzFlux Stage07
and Stage08 already verified **169 native file-year records across
10 OzFlux L6 originals: 67 structural-year candidates and 102
review/HOLD**. Do NOT treat 67 as science-approved DATM years.
The earlier source workflow also produced AU-ASM Mulga1
**six-year 2013–2018 provisional NOLEAP DATM**, then
Stage14 source-faithful zero-floor FSDS candidates under
`/home/ly3n24/ozflux_stage14_FSDS0_20261102T012038Z`.
These are provisional and require independent DATM time/CIME
stream, QC and physical-science confirmation, not immediate AD5.
AU-ASM Mulga2 has separate native record years and must not
be silently spliced into Mulga1.

**Stage04 read-only source handoff**:
`scripts/04_ozflux09_forcing_handoff_source_QC_and_surface_receipts_READONLY.py`,
immutable commit `8bc23faa3fb08a53677efbe01763534565a9ff1c`,
Git blob `04e3647425fecd8b5644b3068e3a21f7c087fb17`.
It opens 9 already-created surfaces only for SHA checks;
verifies original Stage01–03 receipts, all 169 prior source
year-QC and Stage08 triage entries, 67/102 split, and original
AU-ASM 6 provisional DATM source/manifest SHAs. It outputs
a per-site forcing priority register, preserves original
native time/DATM scientific HOLD, and writes no forcing,
surface, case or model.

Use original prior source Stage07:
`$HOME/ozflux_stage07_20261101T062633Z`.
Locate actual Stage08 output by containing
`stage08_review_summary.json` before running Stage04
(do not infer that a report exists just from directory naming).

After Stage04, focus on (1) validating proper native-vs-UTC
half-hour timestamp convention and NOLEAP completeness for
source-specific contiguous candidate blocks; (2) source L6
seven-variable QC/provenance and humidity consistency; (3) building
new isolated DATM NetCDF and validating stream mapping for
each site. Rank source pilot periods cautiously:
AU-ASM provisional 2013–2018 already exists; AU-DaS
2009–2021 and AU-Dry 2010–2018 are strong STRUCTURAL
candidates but **not physics / QC / land-cover approved**.
AU-DaS has prior source-level high humidity flags and
post-2022 land-cover change; do not mix vegetation regimes
by default. Keep AU-How competition case unchanged.

## Stage04–05 actual operator receipts (2026-11-02)

Both reports are completed **READ ONLY** on IRIDIS6:
- Stage04: `/iridisfs/home/ly3n24/ozflux_nc_stage04_20261102T223221Z_FIX/` — 9/9 surface source SHA verified; 169 native source-years; 67 structural-year candidates, 102 HOLD; six AU-ASM Stage14 provisional DATM SHA256 file/manifest checks passed (2013–2018). Not a model submission gate.
- Stage05: `/iridisfs/home/ly3n24/ozflux_nc_stage05_20261102T224556Z_FIX/` — 42 AU-ASM + 91 AU-DaS + 63 AU-Dry year-variable QC groups (196 total) reconciled with the original L6 NetCDF and Stage08. The local-source-time stamps below are **not** independently UTC-certified. The executed script is in Stage05 [PR #62](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/62), fixed commit `5c476617fb8c566f63bfa860b4602eb7d1b5e45b`.

| Site/source years | Longest contiguous ACCESS/ERA5 (any driver) | Critical independent HOLD |
|---|---:|---|
| AU-ASM 2013–2018 | 395 h = 16.46 d | Six Stage14 FSDS0 files remain provisional; native-local-END to UTC-center hypothesis, PRECT units, SH/ZBOT evidence, CIME streams still require independent signoff |
| AU-DaS 2009–2021 | 1,691.5 h = 70.48 d | Precip **ANY_NON_QC0** 2009-01-01 00:30 through 2009-12-31 23:30 (8,759.5 h); 885 separately diagnosed SH supersaturation cases, including 40 severe, remain on physical science HOLD |
| AU-Dry 2010–2018 | 6,596.5 h = 274.85 d | Fsd and Fld ACCESS/ERA5 2013-03-25 13:30 to 2013-12-25 09:30 (6,596.5 h), with simultaneous all-seven-variable ANY_NON_QC0; Precip ANY_NON_QC0 2010-01-01 to 2011-02-03 (9,566 h) |

**Interpretation:** ANY_NON_QC0 cannot be assumed to be a single external model product; it includes interpolation, correction and other source QC categories. Code 420 denotes ACCESS, code 440 ERA5 in PyFluxPro's source code. No repair, model submission or causal attribution is automatically authorised by QC count. Values in the output are native labels as recorded by source L6.

**Operator next step:** extract AU-ASM's own (not AU-Dry-dominated) longest QC episodes and yearly variable rows from the successful Stage05 report; independently validate six Stage14 provisional DATM physical bounds and CIME/DATM effective time/stream mapping; keep prior Stage13–14 exact source mapping and 360 FSDS0 records as immutable source receipts. Prioritise AU-ASM; separately review AU-DaS humidity/precip; defer AU-Dry forcing approval until long replacement periods are interpreted.

## Candidate model mode (not submitted)

Use a **new, isolated FIXNC experiment** (no reuse or overwriting of old competition cases):

- `use_fates_nocomp = .true.`
- `use_fates_fixed_biogeog = .true.`
- Independent cold start from a **PFT-specific point surface** after physical and effective-input validation.
- Run **AD5 smoke test first**, review run logs/real inputs, then **AD400 (80×5y)** only after the per-site DATM/soil/Surface/CIME scientific gates pass. NORMAL400 is a separate subsequent decision and is not submitted here.
- Preserve site-specific native time definitions and source units; original L6 is NOT itself CLM DATM. Use existing, verified individual forcing candidates only where available. In particular, AU-ASM Stage14 contains 2013–2018 6-year meteorological candidates with provisional UTC conventions, not an automatic 9-site model forcing product.
- Keep original AU-How full-competition case unchanged. Do not reinterpret the two independent AU-ASM Mulga1/Mulga2 source files as a single continuous source.

## Exact pinned snapshot artifacts

- `data/OZ_JP_ORIGINAL_20_SITE_PFT_MASTER_PINNED_20261102.csv`: 20-source-row reviewed upstream master (original numeric values and metadata). Git blob **`b283e41601167e176397f3224b58c6c2f691146e`**.
- `data/OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv`: nine host-class vectors. Git blob **`698d702e83265290e3cf1f1890235b67ede290ee`**.
- `data/OZFLUX_09_PRIMARY_FATES_PFT_PERCENT_20261102.csv`: nine FATES natland and vegetated-only vectors. Git blob **`cec1df31f3e959e854aca6105a665a42321afa7c`**.
- `data/OZFLUX_09_PRIMARY_PFT_VALIDATION_20261102.csv`: nine PRIMARY values and mapper roundtrip PASS. Git blob **`2106f818b93eefb97323650535af5ec665628665`**.
- `data/OZFLUX_09_ORIGINAL_L6_SITES_MANIFEST.tsv`: exact ten native NetCDF filenames (AU-ASM two) for source physical-file readiness. Git blob **`de65b38ae838a6b4f7bbaec44e6350a55c255f14`**.

## Stage01 first operator attempt — order-only FALSE STOP, corrected script

**2026-11-02 IRIDIS6 first execution**: script SHA PASS, syntax PASS, selftest PASS,
but the real nine-site scan stopped before any filesystem/model changes at:
`ValueError: Nine sites/order not EXACT operator-approved OzFlux cohort`.
Upstream accepted v1.1 CSV order includes **AU-How before AU-Gin**; the old
`EXPECTED` tuple had AU-Gin before AU-How. This is **not a numeric PFT
error** and must not trigger changes to the accepted values or source files.

**FIX PUBLISHED** as script commit
`f842674c91c62635ec711c4a945bc6d46ffa4159`,
script Git blob `2ad4d9efdfbf9e425d4034cf75fd542cd05c91c3`.
Corrected membership validator checks exact 9 IDs, each appearing exactly once,
regardless of row order, in all three primary matrices and master source.
Regression fixture tests BOTH canonical and upstream AU-How/Gin order
and rejects omitted/duplicated rows. The actual five snapshots were
also independently checked against each other for all nine
PFT and bare numerics; no mismatch found. Operator corrected-script
execution on IRIDIS6 is still pending; **not yet a passed remote gate**.
The same original five data downloads under
`$HOME/ozflux_nc_stage01_code/pft` may be reused (hash-verified
again by the code). Only redownload the updated Python script,
and use a fresh timestamped HOME output directory.

## Read-only nine-site PFT + IRIDIS6 input gate

Source: `scripts/01_ozflux_09_operator_PFT_snapshot_and_IRIDIS_readiness_READONLY.py`
Git blob **`2ad4d9efdfbf9e425d4034cf75fd542cd05c91c3`**.

The script validates all five pinned source files, exact nine-site membership and ten-L6-source manifest, live area plus bare sum, CLM-to-FATES one-to-one DEFAULT14 mapping, master per-site numeric JSON, and <=4 live active FATES classes. Bounded read-only IRIDIS6 source and reference-surface checks produce JSON and TSV (direct HOME child). It explicitly reports `AD400_authorised=false` and never creates/sends a job. A `PFT_source_approved_by_operator=true` means PFT numeric choices are finalized for the experiment, NOT the 9-site total science gate.

Operator command (replace `f842674c91c62635ec711c4a945bc6d46ffa4159` with the specific commit documenting this README and outputs):

```bash
(
set -euo pipefail
conda activate clm_fates_env
COMMIT="f842674c91c62635ec711c4a945bc6d46ffa4159"
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/OzFlux_Batch01_09"
CODE="$HOME/ozflux_nc_stage01_code"
DATA="$CODE/pft"
SCRIPT="$CODE/ozflux_nc_stage01.py"
OUT="$HOME/ozflux_nc_stage01_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DATA"
curl -fLsS "$BASE/scripts/01_ozflux_09_operator_PFT_snapshot_and_IRIDIS_readiness_READONLY.py" -o "$SCRIPT"
test "$(git hash-object "$SCRIPT")" = "2ad4d9efdfbf9e425d4034cf75fd542cd05c91c3"
for file in OZ_JP_ORIGINAL_20_SITE_PFT_MASTER_PINNED_20261102.csv OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv OZFLUX_09_PRIMARY_FATES_PFT_PERCENT_20261102.csv OZFLUX_09_PRIMARY_PFT_VALIDATION_20261102.csv OZFLUX_09_ORIGINAL_L6_SITES_MANIFEST.tsv; do
    curl -fLsS "$BASE/data/$file" -o "$DATA/$file"
done
python3 -B -m py_compile "$SCRIPT"
python3 -B "$SCRIPT" --self-test
python3 -B "$SCRIPT" --data-dir "$DATA" --out "$OUT"
echo "REPORT_DIR=$OUT"
)
```

Expected first result: `OZFLUX PRIMARY PFT 9/9 PASS` followed by nine real source/surface statuses. **No AD5/AD400 submitted.**

**After actual operator preflight:** build isolated PFT-specific point surfaces (host0 bare independent, untouched soil reference), verify exact active case FATES map and stable site-specific DATM, then begin per-site AD5. Only promote each success to direct AD400 when effective runtime inputs have passed the per-site gates.
