# ICOS Batch04 — Stage02V actual IRIDIS6 results and official GitHub PFT manual gate (1 November 2026)

## Operator-reported Stage02V completion

The source Git commit/blob was verified; `STAGE02V SELF-TEST PASS`; whole four-site Stage02V read-only audit completed, with no original case, surface, forcing, NetCDF or Slurm mutation.

Private IRIDIS6 output files:
- JSON `/home/ly3n24/ICOS_Batch04_stage02v_9MKZUOLs/results/stage02v_four_site_DATM_parser_landunit_review.json`
- CSV `/home/ly3n24/ICOS_Batch04_stage02v_9MKZUOLs/results/stage02v_four_site_eight_case_DATM_PFT_comparison.csv`
- LOG `/home/ly3n24/ICOS_Batch04_stage02v_9MKZUOLs/stage02v_console.log`

**DATM source-path ambiguity RESOLVED (static file references only):** all eight original CIME cases returned `OLD_PARSE 0`, whereas the Stage02B reference parser found exactly **22, 15, 18 and 19** annual site-DATM NC paths per respective site; **`PATH_EXACT True`, `PATH_CANON True`, `NC_EXIST True`** for both S30SHARED and S30EXCL at each station. Thus the eight `DATM_STATIC_LIST_MATCH False` from Stage02U were a **parser false negative**; do not rewrite/copy the original 74 annual forcing files. **Actual runtime stream binding remains unverified.**

## PFT source priority — user's explicit instruction

Use the user's already curated GitHub scientific PFT research record; **do not overwrite those PFT decisions with coarse original gridded surface proportions**, and notify the operator of any discrepancy for manual review.

**Current formal authority:** [`FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv), which supersedes 25 Oct versions. Historical source observations and explicitly non-equivalent denominators are documented in [`MASTER_38_SITE_OBSERVED_VS_FATES_PFT_20261024.csv`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/MASTER_38_SITE_OBSERVED_VS_FATES_PFT_20261024.csv) and the [six-site bare-ground report](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/SIX_SITE_BARE_GROUND_PFT_EVIDENCE_20261025.md). All four formal rows have `fixnc_cohort = Not assigned`, not `IN USE` cases. These are **not already approved to be written to Batch04 model surfaces**.

| Site | Official 26 Oct **conditional PCT_NAT_PFT proposal** | Official status and actual evidence | Original CLM surface NATVEG/CROP (gridcell %) | Original vs GitHub conditional-PFT L1 difference (percentage points) | Operator decision |
|---|---|---|---|---:|---|
| **DE-Gri** | HLM 13 C3 grass **100%** | `CANDIDATE (qualitative)`; managed meadow species (Elymus, Alopecurus, Achillea, Rumex, Trifolium), **no measured within-footprint PFT percentages** | **62.674 / 37.326** | **88.428899** | **MANUAL REVIEW** of categorical meadow proxy and evidence sufficiency |
| **DE-RuR** | HLM 13 C3 grass **100%** | `CANDIDATE (qualitative)`; managed meadow with Alopecurus/Lolium/Poa, no quantitative PFT split | **78.891 / 21.109** | **101.932009** | **MANUAL REVIEW** of meadow proxy and true EC footprint |
| **IT-Tor** | HLM 13 C3 grass **100%** | `CANDIDATE (qualitative)`; alpine Nardus stricta meadow, no footprint percentages | **89.915 / 10.085** | **168.008790** | **MANUAL PFT REVIEW**; separate source review of **ORGANIC=0 on all 10 soil layers** |
| **ES-Agu** | HLM 0 bare **49%**, HLM 13 C3 grass **29%**, HLM 9 evergreen shrub **22%** | `PROPOSED`; vegetation 51%, gravel/rock/bare 49%, Macrochloa 57% of *vegetation* in the cited cover survey | **71.461 / 28.539** | **68.822865** | **PRIORITY MANUAL REVIEW**: ground-cover denominator, survey/EC-footprint representativeness, biocrust treatment and evergreen-shrub allocation |

The historical 24 Oct MASTER describes another ES-Agu dataset with roughly **65% vegetated cover** in experimental plots, and warns that 35% complementary area is not necessarily all bare (biocrust/nonvascular cover). The 26 Oct register uses different direct survey evidence of 51% vegetation/49% bare or gravel. **Different surveys/denominators may explain the difference; this is a question for manual source inspection, not automatic averaging of 65 and 51.** The `FINAL_38...` proposal remains the model candidate but should be explicitly approved before constructing a new PFT surface.

**CRITICAL:** Stage02U/V original surface `PCT_NATVEG` and `PCT_CROP` are **whole-gridcell landunit percentages**, while `PCT_NAT_PFT` is conditional on `NATVEG`. The GitHub model proxy is proposed **conditional PCT_NAT_PFT** (typically on a constructed 100% natural-vegetation model point), not an observation that the old gridcell had 100% natural vegetation; NEVER silently transfer `PCT_CROP` to `C3 grass` or bare ground. Also, the static surface `fsurdat` path in the Stage02U original cases still points to the old gridded surface; the original surface vectors clearly disagree with GitHub candidate values. If the old `fsurdat` is the active point surface with no separate overrides, this is a serious **implementation discrepancy**. Determine the effective FATES HLM→PFT map, site-specific constructed surface, and runtime stream/namelist **before editing anything**.

## Next Stage02W controlled, read-only GitHub science gate

[`02w_four_site_official_GitHub_PFT_manual_gate_readonly.py`](../scripts/02w_four_site_official_GitHub_PFT_manual_gate_readonly.py) reads the original saved Stage02V JSON plus a **blob-SHA-verified** download of the authoritative 26 Oct PFT CSV. It validates exact site registration status (CANDIDATE/PROPOSED), original CIME Stage02V static path results, registered host-index percentages and the original surface PFT divergence and soil organic provenance, outputs 8 per-case evidence rows and raises explicit **MANUAL REVIEW** per site. It changes **nothing** and cannot approve or overwrite PFT or issue any Slurm jobs.

The following steps depend on operator approval: first resolve ES-Agu denominator and whether three qualitative 100% grass proxies are acceptable; then create **new versioned site-only** NATVEG/PFT surfaces and separately source-verifiable soil only if authorised, validate active CIME/FATES mappings, consider isolated AD5 scientific preflight after all other source/soil gates pass. Current four remain `HOLD`; CH-Aws independent source RH/ERA and GL-ZaH Arctic map are separate HOLDs.
