# ICOS Batch04 — Stage02Z original DATM stream evidence and Stage03A source/QC discovery (2026-11-01)

## Stage02Z operator-confirmed results

Operator source-verified Stage02Z; eight original cases passed the read-only document audit. No CIME, forcing, NetCDF or Slurm changes.

- All DE-Gri, DE-RuR, IT-Tor and ES-Agu S30EXCL/S30SHARED cases have DATM_MODE=1PT.
- Each has CaseDocs/datm.streams.xml with its site's annual DATM NC filenames, CLM_USRDAT.UNSET, taxmode=cycle and consistent year_first/year_last/year_align.
- Years: DE-Gri 2004–2025; DE-RuR 2011–2025; IT-Tor 2008–2025; ES-Agu 2006–2024.
- A literal streams assignment was not seen in CaseDocs/datm_in but its generated stream XML exists. Thus STREAMS_ASSIGNMENT False is not evidence of missing DATM forcing.
- The existence of static documents does not independently prove the executable opened those streams.

Private outputs:

    /home/ly3n24/ICOS_Batch04_stage02z_bTwLfYMG/results/stage02z_eight_original_DATM_stream_document_audit.json
    /home/ly3n24/ICOS_Batch04_stage02z_bTwLfYMG/results/stage02z_eight_original_case_stream_matrix.csv
    /home/ly3n24/ICOS_Batch04_stage02z_bTwLfYMG/stage02z_console.log

## Why meteorological science QC is not yet complete

Stage02D internally verified 74 original candidate annual DATM files. Stage02Z reviewed their associated CIME static stream definitions. Neither audit independently proved station-native half-hourly QC0 observations, measured RH versus filled VPD, ERA5 substitutions, or original-vs-DATM time alignment. Therefore the four sites cannot yet be called meteorologically QC-clean.

## Stage03A next action: original source files and columns

[Stage03A read-only HH source/QC discovery](../scripts/03a_four_site_original_HH_tower_QC_provenance_discovery_readonly.py) takes the original Stage02C full six-site JSON, Stage02D first four-site JSON and Stage02Z eight-case JSON, preserving their HOLD states.

It searches only the four site source trees under /iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/. Bounds are 16,000 visited filenames per site, 320 candidate files per site, depth 8, and 40 ZIP archives/site. It includes original product archive folders, but excludes old model run, logs and surface subset folders. For potential ICOS/FLUXNET BASE/BIF/BADM/FLUXMET_HH/ERA_HH/HH sources it reads bounded CSV/ZIP/GZIP headers (up to 64KiB), two sample records and optional NetCDF variable headers only. No archive extraction, full source product read, original forcing modification, case changes or Slurm actions.

Outputs only to new EMPTY HOME folder:

- stage03a_four_site_original_met_source_QC_inventory.json
- stage03a_four_site_source_HH_QC_columns.csv

Filenames and QC columns indicate only candidate provenance. They do NOT verify numeric original sensor RH, time basis, source QC0 status or ERA replacement trustworthiness. If true native sources are recovered, next stage will align and test their actual QC/time/value fields against selected DATM NC. If absent, document source gap and retain HOLD rather than declaring source QC PASS.

Four GitHub-selected PFT proxies are already operator-approved and new surface SHA256 were verified; do not redo PFT. IT-Tor all-ten soil ORGANIC=0 remains separate provenance/soil HOLD. No AD5 or AD400 approval from Stage03A.
