# Batch02 Stage10 AD395 submitted 4/4; remaining six PFT / sources ready for audit

Date: 25 October 2026. This is a record of **operator-supplied actual logs** and separately prepared GitHub code. It is **not** a claim that 395 model years already finished.

## Verified Stage10 actual continuation submissions

User supplied:
- `STAGE10 STACK 307200000 -> 307200000 host login6001`; sufficient stack.
- `BATCH02 AUDIT PASS: 4/4 AD5 run+archive Slurm success, 4/4 complete AD-state three-component restarts`, and `spinup_state=2`.
- `FI-Hyy AD5 RESTART PASS 2002-01-01`; initial AD395 **run 4732398**, **archive 4732399**, intended final year **2397**.
- `FR-Hes AD5 RESTART PASS 2002-01-01`; initial AD395 **run 4732400**, **archive 4732401**, intended final year **2397**.
- `CH-Fru AD5 RESTART PASS 2010-01-01`; initial AD395 **run 4732402**, **archive 4732403**, intended final year **2405**.
- `IT-MBo AD5 RESTART PASS 2008-01-01`; initial AD395 **run 4732404**, **archive 4732405**, intended final year **2403**.
- Exact operator output: `BATCH02 AD395 submit summary: 4 /4`; `FOUR AD395 continuations submitted. This is NOT confirmation they finished.`. Queue snapshot: all four run jobs `PD (Priority)`; archive jobs `PD (Dependency)`. Their per-case one-time ledgers already exist.
- **Do NOT rerun Stage10 `continue-395`**, restart AD5, or begin Normal400 before the end-of-AD400 checkpoint. The 79×5yr continuation segments are not yet known to have run successfully.

Monitor read-only:
```bash
sacct -j 4732398,4732399,4732400,4732401,4732402,4732403,4732404,4732405 --format=JobID,JobName%45,State,Elapsed,ExitCode
squeue -j 4732398,4732399,4732400,4732401,4732402,4732403,4732404,4732405
```

## Exactly six left inside ICOS Batch02 cohort

The **remaining six sites in this same cohort** are **DK-Sor, FR-FBn, BE-Bra, IT-Noe, CH-Lae and ES-LJu**. **Do not confuse** them with the unrelated six unassigned extra ICOS sites CH-Aws, DE-Gri, DE-RuR, IT-Tor, ES-Agu and GL-ZaH; their accepted proxy PFT CSV is separately maintained at [`../../ICOS_Unassigned_6/data/six_site_FIXNC_operator_selected_PFT_20261025.csv`](../../ICOS_Unassigned_6/data/six_site_FIXNC_operator_selected_PFT_20261025.csv) and untouched here.

Current authoritative source is [38-site observed-to-FIXNC PFT table](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261025.csv), content Git blob `63739e00408443bcbb4b286bb3324c76e9fd9100`. Read [six-site sparse PFT source review](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/SIX_SITE_BARE_GROUND_PFT_EVIDENCE_20261025.md) for the two sparse cover candidates.

| Station | Actual original source CIME reference from Stage02 | PFT status | Proposed host fractions | Scientific caution |
|---|---|---|---|---|
| DK-Sor | `DK-Sor_FATES_SPINUP500` | **OPEN** | DBF80; unknown combined ENF+DNF20 | Picea is ENF, Larix is DNF; no defensible split yet; no grass fill |
| FR-FBn | `FR-FBn_FATES_SPINUP500` | **OPEN** | Pine ENF75; remaining share ≤25 not verified all oak EBF | Tree basal area is not patch area; don't label ENF75+EBF25 observed |
| BE-Bra | `BE-Bra_FATES_SPINUP500_11P` | **OPEN** | ENF55, DBF23, 22 unclassified | Unidentified forest 22 cannot be grass/bare by default |
| IT-Noe | `IT-Noe_ERA5_ABW_BRANCH2009` | **PROPOSED** | HLM0 bare34, HLM9 evergreen shrub66 | Middle of measured cover variability42–91%; juniper a needleleaf **shrub**, FATES host9 broadleaf evergreen shrub is a proxy, not a conifer tree. ERA5 branch forcing provenance needs independent validation |
| CH-Lae | `CH-Lae_FATES_SPINUP500_11P` | **OPEN** | DBF80, ENF12, 8 unclassified | Mixed forest canopy/stand measurements may have overlapping denominators; don't fill8 automatically |
| ES-LJu | `ES-LJu_FATES_SPINUP1000_S30SHARED` | **PROPOSED** | HLM0 bare49, HLM13 cool C3 grass31, HLM9 evergreen shrub20 | Bare soil/gravel/rock measured49.1%; grass18.8, shrubs12.3; 19.8 remaining *known vegetation* apportioned pro-rata as an **explicit** proxy; shrub phenology HLM9 vs HLM10 unresolved |

## New Stage11 read-only six-site gate

[Stage11](../scripts/11_audit_remaining_six_PFT_and_source_inputs_readonly.py) checks EXACT six official source rows, GIT blob + shared FATES parameter SHA, the six Stage02 source case paths, actual CIME XML point `PTS_LAT/LON` versus source site surface `LATIXY/LONGXY`, original landunit/PFT/soil, `fsurdat` input, site met/CDEPS stream references, CIME source `RUN_STARTDATE/CO2` and executable existence. This is **READ-ONLY**, including no new reports from the script; the operator may `tee` logs. A legacy-source `PTS` mismatch is diagnostic only but MUST be corrected in a versioned FIXNC case (AmeriFlux CA-TP4 failed `surfrdMod.F90:122` due inherited CH-Dav coordinates). An archived successful CIME case is a template, not a restart donor.

## New Stage12 two bare+shrub surface candidates (optional)

[Stage12](../scripts/12_build_IT_Noe_ES_LJu_bare_shrub_candidates_only.py) `--plan` is read-only; `--build --confirm CREATE_TWO_BATCH02_BARE_SHRUB_SURFACE_PROXIES` makes **only two NEW, separately versioned candidate surfaces** for IT-Noe and ES-LJu. No AD5 case/submission/forcing edits or compiled executable modifications. It keeps the original site lat/lon and all PCT_SAND/CLAY layers **unchanged** as gridded soil fallback, while making the explicitly idealized point `PCT_NATVEG=100`, `PCT_CROP=0`, other landunits 0, and including real nonvegetated fractions in the 15-element `PCT_NAT_PFT` host index0. Validates unchanged source variables and stores original SHA/proxy assumptions in manifest. Any existing destination causes stop; no overwrites. This is an independent science-candidate stage, not approval of ground truth.

**Do not build four forest sites yet** until their residuals are resolved or the operator explicitly selects separately named sensitivity scenarios. No original FATES / forcing / other active four AD395 cases are touched.

## Recommended operator commands (no Slurm)

```bash
python3 -B "$HOME/Batch02_10_stage11.py" --self-test
python3 -B "$HOME/Batch02_10_stage11.py" --audit --pft-csv "$HOME/Batch02_10_official_38.csv"
python3 -B "$HOME/Batch02_10_stage12.py" --self-test
python3 -B "$HOME/Batch02_10_stage12.py" --plan
# After Stage11 has confirmed original source model surfdata and landunit:
python3 -B "$HOME/Batch02_10_stage12.py" --build --confirm CREATE_TWO_BATCH02_BARE_SHRUB_SURFACE_PROXIES
```
