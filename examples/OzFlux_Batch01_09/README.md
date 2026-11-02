# OzFlux 9-site Non-Competition CLM-FATES — operator-selected v1.1 PFT inputs

**Status 2026-11-02: Nine-site PFT hypothesis SELECTED by operator, source snapshot and source-lock/readiness audit published, actual IRIDIS preflight pending. No new site PFT surface, case, DATM, AD5, AD400 or Slurm job submitted.**

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

## Read-only nine-site PFT + IRIDIS6 input gate

Source: `scripts/01_ozflux_09_operator_PFT_snapshot_and_IRIDIS_readiness_READONLY.py`
Git blob **`b35348089c1830f9ce88b8a46b0d4ac29a520811`**.

The script validates all five pinned source files, exact nine-site membership and ten-L6-source manifest, live area plus bare sum, CLM-to-FATES one-to-one DEFAULT14 mapping, master per-site numeric JSON, and <=4 live active FATES classes. Bounded read-only IRIDIS6 source and reference-surface checks produce JSON and TSV (direct HOME child). It explicitly reports `AD400_authorised=false` and never creates/sends a job. A `PFT_source_approved_by_operator=true` means PFT numeric choices are finalized for the experiment, NOT the 9-site total science gate.

Operator command (replace `<PINNED_NONCOMP_COMMIT>` with the specific commit documenting this README and outputs):

```bash
(
set -euo pipefail
conda activate clm_fates_env
COMMIT="<PINNED_NONCOMP_COMMIT>"
BASE="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$COMMIT/examples/OzFlux_Batch01_09"
CODE="$HOME/ozflux_nc_stage01_code"
DATA="$CODE/pft"
SCRIPT="$CODE/ozflux_nc_stage01.py"
OUT="$HOME/ozflux_nc_stage01_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DATA"
curl -fLsS "$BASE/scripts/01_ozflux_09_operator_PFT_snapshot_and_IRIDIS_readiness_READONLY.py" -o "$SCRIPT"
test "$(git hash-object "$SCRIPT")" = "b35348089c1830f9ce88b8a46b0d4ac29a520811"
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
