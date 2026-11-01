# ICOS Batch04 Stage02X — operator-approved four-site GitHub PFT model proxies (2026-11-01)

## Decision

The operator explicitly approved using the already published GitHub PFT assignments at DE-Gri, DE-RuR, IT-Tor and ES-Agu. This decision **closes the question of which PFT proxy the FIXNC experiment should use**, not the separate questions of what fraction of the tower footprint was actually measured in each PFT, whether soil/forcing meets site QC, or whether a particular old CIME case is technically runnable.

Authoritative source: [26-Oct PFT register](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/main/examples/ICOS_sites/ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv) (Git blob `3be7a78e82d888b64c9a00ae8ebaae6e457e60e3`). Original evidence remains graded qualitative CANDIDATE for the three herbaceous stations and PROPOSED for ES-Agu; **the operator's 1-Nov approval applies to their use as MODEL PROXIES**, not to retroactively proving the percentage surveys. Batch04's approval overlay is [stage02x_operator_approved_four_site_GitHub_PFT_20261101.csv](../data/stage02x_operator_approved_four_site_GitHub_PFT_20261101.csv). Do **not** rewrite the scientific 38-station historical registry to claim numeric tower-footprint measurements.

| Site | Approved host 15-slot PCT_NAT_PFT conditional on NATVEG | Model proxy interpretation |
|---|---|---|
| DE-Gri | HLM 13 = 100% | all herbaceous managed meadow mapped to cool C3 grass; forb/legume physiology not explicit |
| DE-RuR | HLM 13 = 100% | mixed managed herbaceous pasture mapped to cool C3 grass; lysimeter data not whole tower footprint |
| IT-Tor | HLM 13 = 100% | alpine Nardus-dominated meadow mapped to cool C3 grass |
| ES-Agu | HLM 0 bare = 49%; HLM 9 evergreen shrub = 22%; HLM 13 C3 grass = 29% | explicit ground-cover proxy; 51% vs 65% vegetation surveys and Macrochloa denominator retained as scenario uncertainty, not an automatic rewrite |

The new standalone FIXNC **model-point scenario** follows the already established Batch03 convention: `PCT_NATVEG=100`, `PCT_CROP=0`, other lake/wetland/glacier/urban landunits zero, and `PCT_NAT_PFT` totals 100 inside NATVEG (including bare PFT 0). This is an **intentional model scenario transformation** from coarse gridded original surfaces with nonzero crop. It is NOT a claim that the measured 40-ha/EC footprint has exactly 100% NATVEG or that old PCT_CROP area becomes observed grass/bare. Keep the old point sources intact as data provenance.

## Stage02W and Stage02V achieved

Stage02W operator successfully verified SHA-pinned GitHub PFT registry and original audit evidence: 8/8 current original case surfaces differ from the selected PFT proxies (DE-Gri old-vs-target conditional PFT L1 88.4289 pp; DE-RuR 101.932009; IT-Tor 168.00879; ES-Agu 68.822865). This difference is expected if old source surfaces were never rewritten, and confirms that **the new PFT must be applied to a new point surface**, not assumed active in original S30EXCL/SHARED cases.

Stage02V explicitly confirmed 8/8 old CIME `Buildconf/datm.input_data_list` original paths are exact/canonical and 74 annual DATM NC files exist. It also proved the previous eight Stage02U `DATM_STATIC_LIST_MATCH False` values were parser false negatives (`OLD_PARSE 0` vs reference 22/15/18/19). **Do not regenerate the 74 forcing files on that basis.**

## Next action: Stage02X point-surface plan, then isolated candidates

[Stage02X script](../scripts/02x_four_site_approved_GitHub_PFT_surface_candidates.py) implements the established **Batch03 approach** without touching Batch03 or the original Batch04 cases. `self-test` and `plan` are read-only; `plan` reads the original Stage02U and Stage02W operator reports, hashes original point sources, verifies the 15-slot NATPFT and 10-layer soil schema, checks the source `fates_hlm_pft_map` for host 13 cool C3 grass and host 9 temperate evergreen shrub at ES-Agu, and checks actual local nocomp bare-ground support for ES-Agu. It shows the old NATVEG/CROP and the new modelling scenario transformation. No forcing, source surface or CIME writes.

Run `plan` on IRIDIS6 with exact, immutable GitHub commit and blob:
```bash
python3 -B "$SCRIPT" self-test
python3 -B "$SCRIPT" plan \
  --stage02w "$HOME/ICOS_Batch04_stage02w_7wTwcDfO/results/stage02w_four_site_GitHub_PFT_manual_science_gate.json" \
  --stage02u "$HOME/ICOS_Batch04_stage02u_EFhTiiqx/results/stage02u_four_site_case_surface_soil_PFT_static_audit.json"
```

If and only if `plan` passes and bare-ground FATES support is demonstrated, `build` may create **four new isolated NetCDF surface candidates and SHA256 receipts** under a user-chosen **new empty directory**, using:
```bash
python3 -B "$SCRIPT" build \
  --stage02w "$W" --stage02u "$U" \
  --out-dir "$NEW_EMPTY_CANDIDATE_DIR" \
  --confirm CREATE_FOUR_BATCH04_APPROVED_PFT_SURFACE_CANDIDATES_NO_CASES
```
Candidate output never rewrites original surface, existing CIME cases or existing forcing. The only physical changes in each new copy are the model landunit and 15-element NATPFT assignments; inherited 10-layer sand/clay/organic soil is verified unchanged bytewise by decoded NetCDF arrays. Site-specific source soil-quality release is **not** implied. IT-Tor has original `ORGANIC=0` across all ten soil layers, which must be evaluated before any AD5. No case clone or Slurm submission by Stage02X. After candidate creation, the next read-only audit must choose a specific original stream-bearing CIME template and verify **actual effective DATM/FATES/soil configurations**, and then check native source tower meteorology/QC/ERA gaps, before isolated AD5 eligibility. No AD395 or AD400 without separate run + archive proof.

## Remaining scientific gates

1. Four-site original half-hourly tower provenance, QC0/QC1/ERA source correctness, local-to-UTC time and precipitation/radiation checks remain unresolved despite internal Stage02D `FLAGS {}`.
2. Original point soil and management: sand/clay/organic provenance is unverified at all four, especially IT-Tor's physically potentially suspicious 10-layer `ORGANIC=0`. **Do not auto-fill IT-Tor from another site.**
3. Static input lists match, but actual effective DATM streams in the chosen CIME case have not been proven runtime-bound. New site-specific FATES map path must be audited for each case; ES-Agu bare-ground and HLM9 mapping must be verified.
4. CH-Aws source humidity and ERA archive and GL-ZaH Arctic private FATES mapping are separate, still on science HOLD.

**Result: PFT selection = APPROVED; surface candidate build = eligible only after Stage02X preflight; model submission = HOLD.**
