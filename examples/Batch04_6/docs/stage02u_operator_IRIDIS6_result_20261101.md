# ICOS Batch04 Stage02U — actual IRIDIS6 static case/source/soil/PFT review (1 November 2026)

**Source**: operator-pasted, SHA-pinned Stage02U successful IRIDIS6 console output. Source checksum and self-test passed; no source/NetCDF/CIME/Slurm changes. Original complete JSON and CSV remain only in the operator's HOME:

- `/home/ly3n24/ICOS_Batch04_stage02u_EFhTiiqx/results/stage02u_four_site_case_surface_soil_PFT_static_audit.json`
- `/home/ly3n24/ICOS_Batch04_stage02u_EFhTiiqx/results/stage02u_four_site_eight_case_static_matrix.csv`
- `/home/ly3n24/ICOS_Batch04_stage02u_EFhTiiqx/stage02u_console.log`

This was a **static case inspection**, not runtime DATM stream proof or observation-quality approval. Four sites have two original S30EXCL/S30SHARED cases each, and previously verified Stage02D **74 unique annual NC** internal scans with `FLAGS {}`. Both cases at each site use the same original `fsurdat` and the same FATES parameter path; the inspected XML science keys and `lnd_in` keys show no case-pair differences. However, **all eight cases printed `DATM_STATIC_LIST_MATCH False`**. This is not yet evidence that the model used missing or incorrect forcing; original Stage02C enumerated complete annual NC paths that exist, while Stage02U's source-list filename extraction is narrower than Stage02B's established parser and may truncate or omit valid references (including suffixes such as `.nc4`). A fresh independent parser cross-check is required before concluding whether that boolean is a parser false negative, stale input list, or genuine difference. Do NOT silently change case paths or copy files.

## Original point-surface composition, not observed footprint

All percentages below are copied from the operator's **original surface** console output, not the accepted candidate model PFT proxy. `PCT_NAT_PFT` percentages are conditional on `PCT_NATVEG`; `PCT_CROP` is a separate landunit. Do not add crop area to bare ground or grass without measured/explicit scientific conversion.

| Site | Original PCT_NATVEG % | Original PCT_CROP % | Original NATPFT dominant indices (% conditional natural) | Current accepted *candidate model proxy* | Soil surface texture (10 layers, min–max) | ORGANIC (10 layers, min–max) |
|---|---:|---:|---|---|---|---|
| DE-Gri | 62.6741 | 37.3259 | 0: 0.596; 1:31.832; 7:11.786; 13:55.786 | 13:100 | sand 22–33, clay 25–36 | 4.114–70.577 |
| DE-RuR | 78.8907 | 21.1093 | 0:0.541; 1:21.909; 7:28.516; 13:49.034 | 13:100 | sand 43–50, clay 18–21 | 6.451–47.296 |
| IT-Tor | 89.9154 | 10.0846 | 0:11.859; 1:10.210; 2:13.766; 7:11.175; 8:4.190; 10:0.039; 11:0.224; 12:32.356; 13:15.996; 14:0.185 | 13:100 | sand 43–43, clay 18–18 | **0–0 in all ten layers** |
| ES-Agu | 71.4614 | 28.5386 | 0:36.589; 1:3.394; 7:0.237; 10:24.844; 13:34.720; 14:0.216 | 0:49 / 9:22 / 13:29 | sand 56–66, clay 14–20 | 2.559–11.808 |

Original point surface LATIXY/LONGXY matched the static XML site points at all eight cases. `PCT_NAT_PFT` is **not** verified to reflect true eddy covariance footprint vegetation; the model proxy is selected, but these reported source fractions are different. Source FATES mapping, soil provenance, surface crop/biocrust representation and effective runtime surface selection remain unresolved. IT-Tor's `ORGANIC=0` in every surface layer needs specific soil-data scientific source review; a zero is **not automatically a numerical NetCDF error**.

## Immediate next stage: Stage02V

[Stage02V read-only eight-case parser and landunit source diagnosis](../scripts/02v_four_site_DATM_parser_and_landunit_provenance_readonly.py) takes the original saved Stage02U and Stage02C JSONs. For each existing case it independently parses `Buildconf/datm.input_data_list` using Stage02B's exact established absolute NetCDF regex, compares all filenames **byte-exact and canonical path** with the previously verified Stage02C 22/15/18/19 annual path registers, prints mismatching original source lines, and compares the old Stage02U parse with the new parser. It also reports full landunit fraction (conditional NATPFT × NATVEG), current operator model proxy difference, and soil organic min/max from the *saved original Stage02U surface read*, without rereading annual forcing or changing site files.

**Important:** a fixed parser match is only proof of a static input-list reference, not a proof of active DATM stream binding, tower native QC, or an approval to convert crop into NATVEG. All four remain science HOLD, no AD5/AD400, no CIME/Slurm edits.
