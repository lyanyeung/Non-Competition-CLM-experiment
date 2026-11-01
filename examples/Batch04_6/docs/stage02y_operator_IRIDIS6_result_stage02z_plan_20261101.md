# ICOS Batch04 — Stage02Y IRIDIS6 completion and Stage02Z plan (2026-11-01)

## Actual successful Stage02Y operator results

The operator's source-verified Stage02Y read-only run and self-test both passed.

- Surface SHA and soil-preservation audit: **4/4 PASS**.
- Original S30EXCL and S30SHARED case inspection: **8/8 PASS**.
- Original DATM annual NC references: DE-Gri **22**, DE-RuR **15**, IT-Tor **18**, ES-Agu **19** distinct site-year paths, with original Stage02C/V reference matches.
- All eight old CIME cases continue to point to their original gridded site surface, not the newly created and hash-verified standalone PFT candidate surfaces. The new PFT surface is **unbound, as expected**; no new case has been prepared yet.
- All eight original CaseDocs/datm_in assessments printed **DATM_STREAM_FIELD MISSING**, while detecting **one stream-related document per case**. This is **not** proof DATM forcing is unconfigured at runtime. The narrow parser checked one assignment location; generated DATM stream configuration may be represented elsewhere. Original file content and env_run.xml must be inspected.
- IT-Tor remains a separate science HOLD with inherited **ORGANIC = 0 in all ten original soil layers**. Other stations retain independent source-soil and native tower meteorological QC gates.

The original private operator outputs are:

    /home/ly3n24/ICOS_Batch04_stage02y_pT2JPSjW/results/stage02y_four_site_candidate_surface_case_binding_audit.json
    /home/ly3n24/ICOS_Batch04_stage02y_pT2JPSjW/results/stage02y_eight_case_static_binding_matrix.csv
    /home/ly3n24/ICOS_Batch04_stage02y_pT2JPSjW/stage02y_console.log

The new PFT NetCDF candidates remain at:

    /iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn/

## Next: Stage02Z read-only DATM stream provenance

The linked Stage02Z script (../scripts/02z_four_site_eight_case_DATM_stream_source_forensics_readonly.py) uses the saved Stage02Y JSON to inspect **only the eight pinned original case folders**. It records bounded original lines from CaseDocs/datm_in, CaseDocs/lnd_in, stream-document filenames and contents, env_run.xml DATM_MODE/year/run flags, and site input-list excerpts. It prints a small source-fact table and makes a JSON+CSV in a **new empty HOME output directory**; no source files, Git, forcing NetCDF, FATES parameters, CIME case, Slurm or model runs are touched.

An absent DATM 'streams' assignment in the selected file is **not** an automatic scientific or runtime failure. If source documents cannot unambiguously bind an actual runtime stream, this remains HOLD until a separately created isolated new case is safely previewed with its new surface. Likewise, static source-path matching cannot substitute for independent half-hourly native tower source QC, precipitation/radiation time seams or soil science verification. IT-Tor's zero ORGANIC needs separate source review before considering AD5.

**Current six-site Batch04 status:** PFT model choices confirmed 6/6; new candidate PFT surfaces verified 4/6; isolated new FIXNC case submissions 0/6. CH-Aws original RH/ERA source HOLD and GL-ZaH site-only Arctic mapping HOLD are independent remaining sites.
