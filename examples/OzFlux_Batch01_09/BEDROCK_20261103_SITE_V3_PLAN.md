# OzFlux AU-ASM bedrock (zbedrock) v3 on the verified SITE-SOIL v2 Surface (2026-11-03)

## Operator decision (2026-11-04, revising 2026-11-03)

- **`use_bedrock = .true.` at AU-ASM only** (option C of the upstream SurfaceFields topic). The 2026-11-03 decision (option B) had it on for all 20 OzFlux / JapanFlux sites; the operator revised that on 2026-11-04.
- **The other 19 OzFlux / JapanFlux sites keep the FATES default (`.false.`)**, as the 78 finished ICOS / AmeriFlux NORMAL400 spin-ups do.
- **JP-Fjy, JP-Tmd, JP-Tom and JP-Tef:** baseline off. An on run is an optional sensitivity case with its own spin-up. These sites are not part of this AU-ASM pipeline.
- The per-site table is `data/use_bedrock_decision_20261104.csv` (blob `ed9e316ef895735b1b6d858289fbae2c1414eb9f`), at commit `5c1797ca65e776c8f6002164944dc0752ad720b7` of the upstream branch.

## Upstream authority

Branch [`oz-jp-surface-carbon-20261103`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/oz-jp-surface-carbon-20261103/examples/OzFlux_JapanFlux_SurfaceFields), commit `b10377c624e7fbd4712be29ce04d99c4858cc676`, of `CLM-FATES-single-site-workflows`.

**Frozen blob:** `OZ_JP_RECOMMENDED_SURFACE_FIELDS_20_SITES_20261103.csv` = `abb142ab5ab8adb82ed53df220e38bf29ee12af0`.

**AU-ASM row:**

| Field | Value |
| --- | --- |
| `zbedrock_class` | RESTRICT |
| `zbedrock` | **1.0 m**, tier T1_SITE_RESTRICTIVE_LAYER |
| CLM mapping | bedrock layer 9, column bottom 1.20 m |
| `ORGANIC` | f09 |

**Evidence** (`data/soil_depth_evidence_20261103.csv`, AU-ASM-D01–D05):
- siliceous hardpan at ~1 m (1–1.5 m) under the tower (Eamus et al. 2016; Rumman et al. 2018);
- mulga roots above it (< 2 m);
- perched water above the hardpan;
- regional water table at 49 m;
- TDR probes to 1.2 m.

## Why the namelist switch is needed

- **The default ignores `zbedrock`.** Pinned CTSM `d5ea9d01` sets `use_bedrock = .false.` when `use_fates = .true.` (`namelist_defaults_ctsm.xml`), and no case here overrides it. With the switch off, `zbedrock` is ignored and every site gets the full 20-layer column to 8.60 m.
- **Rooting depth does not limit it either.** FATES default `zroot_min_z` = `zroot_max_z` = 100 m.
- **Current AU-ASM value.** Stage02 / Stage13 carry the f09 `zbedrock` of 31.04 m (Pelletier soil thickness), which is irrelevant while the switch is off.
- **How CLM picks the bedrock layer** (`initVerticalMod`). The search starts at the layer that contains `zmin_bedrock` = 0.4 m, which is layer 6 (0.32–0.48 m).
  - 1.0 m falls in layer 9 (0.92–1.20 m).
  - A value of 0.32 m or less matches no layer and silently gives the full column.
- **Lower boundary.** With the switch on, build-namelist requires `lower_boundary_condition = 2` (zero flux), which is already the default. This zero-flux base at the hardpan matches the perched reservoir.

## Stage22 isolated builder

Script: `scripts/22_asm_stage22_bedrock_zbedrock_v3_isolated.py`. It follows the Stage13 pattern.

**Actions:**
- `self-test`: synthetic only.
- `plan`: read-only.
- `build`: confirm token `BUILD_ISOLATED_AU_ASM_BEDROCK_V3_NO_MODEL`; writes a new, unused direct-HOME directory.
- `verify`: independent re-check.

**Source checks:**
- Stage13 v2 candidate `surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_20261103_INTERIM.nc`, SHA256 `2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1`;
- the Stage13 receipt;
- the inherited `zbedrock` of 31.043 m;
- the AU-ASM coordinates;
- the upstream Git blob and the AU-ASM row.

**Change.** Only `zbedrock` is set, to 1.0 m. Every other variable, its attributes, the dimensions and the global attributes must stay byte-identical to v2: texture v2, PFT, landunits (NATVEG 99.9994 as Stage16) and `ORGANIC`.

**Receipt:**
- `use_bedrock_required = true`;
- `lower_boundary_condition_required = 2`;
- `science_approved = false`;
- `AD400_authorised = false`;
- `forcing_science_hold = true`.

## Actual Stage22-bedrock operator result (IRIDIS6, 2026-11-04 03:09 UTC)

Script blob `196feafe53204d2254d8bd8a630ac19dcd040679` (commit `3b4f6a89523763745c78ea34124a53b15283d8d1`) and the upstream CSV blob `abb142ab` were verified. `self-test`, `plan`, `build` and the independent `verify` all passed.

| Item | Value |
| --- | --- |
| v2 source SHA256 | `2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1`, still equal after the build |
| `zbedrock` | 31.042877564793134 m → **1.0 m** (CLM layer 9, column bottom 1.20 m) |
| Other variables | 88 byte-identical; texture, PFT, landunits and `ORGANIC` unchanged |
| **v3 candidate** | `/home/ly3n24/ozflux_nc_stage22_bedrock_20261104T030937Z/surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_BEDROCK_v3_20261103_INTERIM.nc` |
| **v3 SHA256** | **`a354a939e6ad3eb0b743fd600739253d8a9688dda2019c02f852926c9447944b`** |
| Receipt | `/home/ly3n24/ozflux_nc_stage22_bedrock_20261104T030937Z/stage22_AU_ASM_v3_BEDROCK_candidate_NOT_MODEL_APPROVED.json` |

**Naming note.** The forcing-QC branch `feat/ozflux-asm-stage09-native-met-forensic-20261103` also has a Stage22: `22_asm_SH235_PyFluxPro_exact_formula_QC_provenance_READONLY.py`, the 2014 specific-humidity audit. The two are unrelated. This document calls the surface step **Stage22-bedrock**. Its receipt and output directory names (`stage22_..._BEDROCK_...`, `ozflux_nc_stage22_bedrock_*`) already tell them apart.

## Requirements for any later controller binding v3

These apply to AD400, NORMAL400 and the observation run alike.

1. Bind the v3 candidate by its SHA256 from the Stage22 receipt, not by the GRIDREF or v2 path.
2. Add `use_bedrock = .true.` to `user_nl_clm`. Verify `CaseDocs/lnd_in` shows `use_bedrock = .true.` and `lower_boundary_condition = 2`.
3. `create_clone --keepexe` carries `user_nl_clm` into NORMAL400 and the observation run. Re-verify `lnd_in` there.

## Holds unchanged

- Forcing science QC (Stage12–21 wind / AWS / ACCESS / SH issues) remains HOLD.
- The Stage08 hard block on AU-ASM AD400 prepare / submit remains.
- No case is created and nothing is submitted by Stage22.

**Current authorization: `soil_science_approval=false`, `forcing_science_approval=false`, `AD400_authorised=false`.**
