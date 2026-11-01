# ICOS Batch04 Stage02U — four-site original static case, DATM, surface and soil preflight

**Trigger:** the operator's successful CH-Aws Stage02T found no exact `EUF_ERA5_HH` source CSV or matching ZIP member in two bounded search roots, and no new clock/independent instrument QC evidence. CH-Aws remains a distinct unresolved source-science HOLD. Do not repeatedly rerun Stages02E–02T or automatically approve a humidity replacement.

The next useful independent workstream is exactly **DE-Gri, DE-RuR, IT-Tor, ES-Agu**.

## Original evidence and status

Previously verified Stage02D full-year internal DATM screens reported:

| Site | Annual candidate files | Years | Internal flags | Other science gates |
|---|---:|---|---|---|
| DE-Gri | 22 | 2004–2025 | `{}` | S30SHARED/EXCL, original vegetation footprint, tower meteorology and soil |
| DE-RuR | 15 | 2011–2025 | `{}` | Lysimeter ≠ tower footprint, source QC, management and soil |
| IT-Tor | 18 | 2008–2025 | `{}` | Alpine terrain/snow, vegetation bare fraction and soil |
| ES-Agu | 19 | 2006–2024 | `{}` | Sparse shrub/C3/bare model proxy vs original biocrust/Macrochloa cover evidence |

All four have **two existing candidate case folders each** (8 total). Their S30EXCL and S30SHARED candidates reference the same annual DATM file-path set in Stage02C, but case physics/surface/parameters have not been proven equivalent. Stage02D's `FLAGS {}` means **only that the implemented annual DATM internal time/numeric check did not flag an issue**. It does not constitute original tower source/QC approval.

## Stage02U — read-only effective-document/static-configuration audit

[Script](../scripts/02u_four_site_case_DATM_surface_soil_PFT_static_readonly.py) uses the **original saved Stage02C all-six JSON** and the **actual saved first-four Stage02D JSON**, enforcing site identity, original two-case groups, expected 74 file/year sets, Stage02D internal numeric no-flag result, and both scientific HOLD states. It reads the eight current original case folders only, comparing:
- exact site-specific `Buildconf/datm.input_data_list` annual paths with pinned Stage02C paths (not aerosol files);
- original `CaseDocs/datm_in` and `lnd_in` fields; names/contents of up to 30 original stream documents, plus XML `PTS_LAT/PTS_LON` and DATM/CIME science keys;
- case original `fsurdat` and `fates_paramfile` path existence and hashes **only when <=8MB**, retaining explicit `NOT_HASHED` for large files;
- point-surface bounded NetCDF `LATIXY/LONGXY`, `PCT_NATVEG`, `PCT_CROP`, `PCT_NAT_PFT`, `PCT_SAND`, `PCT_CLAY`, `ORGANIC`, wetland/bare/glacier/urban area fields; reports PFT nonzero indices and soil field shapes/ranges;
- **S30SHARED vs S30EXCL** differences in actual generated static CIME input documents, while retaining explicit uncertainty about runtime stream resolution and observational/soil truth.

The current operator-accepted host NATPFT mixes are only **model proxies conditional on NATVEG**: C3 grass 100% for DE-Gri/DE-RuR/IT-Tor; ES-Agu bare 49% / evergreen shrub 22% / C3 grass 29%. Do not treat these as measured EC footprint PFT cover, and do not blindly overwrite the original surface if it differs.

**Required existing IRIDIS6 inputs:**
- `/home/ly3n24/ICOS_Batch04_stage02c_sGTtt5pv/stage02c_report.json`
- `/home/ly3n24/ICOS_Batch04_stage02d_Pq6if8IH/stage02d_first4.json`

Script creates ONLY two new files in a separate new empty HOME output directory:
- `stage02u_four_site_case_surface_soil_PFT_static_audit.json`
- `stage02u_four_site_eight_case_static_matrix.csv`

After verification, inspect `DATM_STATIC_LIST_MATCH`, `POINT`, `PFT_NONZERO`, `SOIL`, `SAME_SURFACE`, `SAME_FATES_PARAM`, and any nonmechanical differences in `XML_SCIENCE_DIFF_KEYS`, `LAND_DIFF_KEYS`. An apparent missing stream mention alone may be normal for generic CIME stream definitions and should be investigated against the case's generated DATM namelist, not automatically interpreted as proof the forcing is absent.

### Stage02U limitations and continuation

The inspection does **not** establish which DATM stream was open in the model's runtime, which tower humidity/precipitation records were native measured vs filled, the correctness of ERA substitutions, actual observed PFT percentages, measured soil texture/ORGANIC, or FATES mapping. Next stage requires site-scoped raw/native source inventory and effective CIME configuration gate before an isolated AD5 preflight can be considered. Four sites remain HOLD. Never modify existing original cases, global FATES parameter maps or shared surface files, and do not submit Slurm/AD400 on the basis of this screen.
