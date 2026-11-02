# Stage03V operator result: DE-Gri 22-year annual DATM input plan passed; Stage03W case preflight plan (2026-11-02)

## Stage03V result (IRIDIS6, operator-run, 2 Nov 2026)

`03v_de_gri_sensitivity_annual_input_plan.py` (git blob `0a81c661b85930a5603842b125cb478718f9ab92`, run at commit `1fdc79e`) printed 22 `DATM PLAN` lines and

    INPUT PLAN COMPLETE 22 years; 2 sensitivities; surface hash verified; NO CASE/SLURM

Private plan JSON (do not commit): `/home/ly3n24/ICOS_Batch04_gri_plan.RgXTDNHK/de_gri_input_plan_PRIVATE.json`.

* 2004-2025 complete, one entry per year, no duplicate SHA256.
* 20 `historical_baseline` files (Stage30/29b FLUXNET13 annual DATM, `..._PROVISIONAL.nc`, one directory) and 2 `approved_sensitivity` files (2011: 11 edits, 2024: 23 edits) that currently live under `/home/ly3n24/ICOS_Batch04_gri_datm_fixed.wMiL9qf5/result/`.
* B04 DE-Gri surface SHA256 `08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b` verified.
* No CIME case, staging copy, stream change or Slurm job exists for this plan. **This is an input inventory, not a science release or a run approval.**

| Year | Kind | SHA256 of the file the new case would read |
| ---: | --- | --- |
| 2004 | historical baseline | `49d00c5aeb083407b40868b8e2d482e7e83679f2325fcb0ee32e962ec02c9125` |
| 2005 | historical baseline | `12dfad2751eb6053ecfc67b34ac97aee891b0329ee7546cd1378c6cbdeedd754` |
| 2006 | historical baseline | `10667fd7d30f49431c14e3dd88d171405f963b7d8e498213792298b8f9baf139` |
| 2007 | historical baseline | `dabf487896e7db2620feef4b40d8734bea79ca95e02b53f4d79a46cd0ea24969` |
| 2008 | historical baseline | `c10493f4252e8c223cee9a1b2285fcfcc602f18f3e8ddddd927f603bb211bfa3` |
| 2009 | historical baseline | `871675440285d2c082471fa5bc98f07c08a040d519a13eca2e76579dff81d5fe` |
| 2010 | historical baseline | `93fd027ab6449101f569ecc77bbf2a4dcff160026ef60f13de42907d1e05cf01` |
| 2011 | approved sensitivity | `2b075626a3a995311e87dafdfd3ae062c55b3e89665c6ff3f3a5aa5ff001bc1c` |
| 2012 | historical baseline | `11b25e4a1858e0ef1b3d21a9359be077ffbf35df7008a0a16bd9502f477dca7b` |
| 2013 | historical baseline | `0f7e574524f595ecf7a660f77c386ac4de2c3fb0c2cdd8a26cda165270d36153` |
| 2014 | historical baseline | `044c8aa189a2602e8a74aa8fdb19c169d5045b90a708cdc99af80b3d9e2be00a` |
| 2015 | historical baseline | `52f41eac24881320ddcdfaa5f15d7a479c92b98c1e116528f49a71ed4ee313cb` |
| 2016 | historical baseline | `499b9550ace4af1c4729d2fa5b87f6134065534200c2405e0acf16018ce0b5a1` |
| 2017 | historical baseline | `bbf97e21320c2b4d367a3a13a552c20966d961639de8a368c14e5ab0b0c5444c` |
| 2018 | historical baseline | `cdf31afc44dbd645b3f55b04296104c0c8d6625f2649113bf44ada18a8bba622` |
| 2019 | historical baseline | `4bc2cef0ccd1b065ba60922d76e04bc4da58c863de2d6d0d3c3d8220ee72bfcd` |
| 2020 | historical baseline | `ef16d59ae5b99efd80a4ac2fa72cc1bf2000d43bb1c492dd63e9d6dcb49cea2a` |
| 2021 | historical baseline | `36e88b47d911d9a5d920264eb70140cc99b8713863d083e03bb8e35e3ef6cf7c` |
| 2022 | historical baseline | `f02fa50c8e77b625541c501bb82367bf2fc001415956a0b558492c5cfa408c9f` |
| 2023 | historical baseline | `6779188a4cce6d9bc385d0f99431d9eb48f9163491700a547acb2b883be61ef0` |
| 2024 | approved sensitivity | `eb0dcaaf9f47500d43f0ebd73e2637dd39c93ce1e4083a1dc365595c4f1a58ac` |
| 2025 | historical baseline | `4ccb698b715508851e7abf51193e6f0ed1b6a1004994703b2d7f865035c4a62f` |

## Stage03W: what the next read-only step checks

[`03w_de_gri_independent_case_preflight_READONLY.py`](../scripts/03w_de_gri_independent_case_preflight_READONLY.py) takes the private plan plus ONE explicitly named, built original DE-Gri template case (nothing is chosen automatically; `list-templates` only lists) and reports:

1. all 22 annual files and the surface still match the plan byte for byte;
2. the two sensitivity files equal their historical baselines in dimensions, dtypes, variable and global attributes and the whole time axis, and differ only in the approved variables (2011: TBOT+QBOT, 2024: QBOT only) at exactly 11 / 23 half-hours with finite, physical values;
3. the surface is HLM13 100 / NATVEG 100 / CROP 0 and keeps the template surface's LATIXY/LONGXY, PCT_SAND, PCT_CLAY and ORGANIC;
4. the template's DATM stream references equal the plan's baseline paths for all 22 years, and which two entries a new case must change;
5. at which model year a 5-year AD smoke and the 400-year cycle first read 2011 and 2024.

It prints a proposed design (case name, `create_clone --keepexe` command, scratch staging copies of the two HOME-resident candidates, `fsurdat`, protocol) but executes none of it. Output is one new private JSON; holds block the later build step.

Design points to settle from its output before any case is built:

* **Sensitivity coverage.** With `taxmode=cycle` over 22 years the standard 5-year AD smoke reads forcing years 2004-2008 only; 2011 and 2024 are first read in the second and fifth 5-year segment respectively (see script output for the exact model years). The AD5 smoke therefore cannot catch a DATM problem in the two candidates. Their read-compatibility is covered by check 2 above.
* **Control.** A sensitivity needs a baseline on the same B04 surface (same case recipe, all 22 historical files). Whether to run that control is an operator decision.
* **Staging.** Candidates under `/home` should be copied, SHA-verified, to scratch before a case references them.

Self-test: `python3 -B 03w_de_gri_independent_case_preflight_READONLY.py self-test`.

```bash
conda activate clm_fates_env
S=examples/Batch04_6/scripts/03w_de_gri_independent_case_preflight_READONLY.py
python3 -B "$S" self-test
python3 -B "$S" list-templates
D=$(mktemp -d "$HOME/ICOS_Batch04_gri_case_preflight.XXXXXXXX")
python3 -B "$S" plan \
  --input-plan "$HOME/ICOS_Batch04_gri_plan.RgXTDNHK/de_gri_input_plan_PRIVATE.json" \
  --template-case /iridisfs/scratch/ly3n24/CLM_FATES/cases/<chosen DE-Gri template> \
  --out "$D/de_gri_case_preflight_PRIVATE.json" 2>&1 | tee "$D/preflight.log"
```
