# AU-ASM — TERN 2018 dendrometer-informed derived woody biomass exclusion

**Decision date:** 2026-11-03. **Status:** `DO_NOT_USE_2018_DERIVED_BIOMASS_FOR_MODEL_CALIBRATION_OR_VALIDATION`. Scientific source caution; this is not an input-mutation directive.

## Evidence and discrepancy

The operator received a TERN Support reply on 3 Nov 2026 about the Cleverly (2022) *Alice Mulga Stem Diameter, Height and Aboveground Woody Biomass* dataset. The support team reports potential quality errors found during their internal audit; no traceable algorithm for 2018 dendrometer-informed derived values; no documented QC prior to their publication; and explicitly advises **against using these derived 2018 values in modelling**. TERN also reports the new site PI could not locate some historical recorded stems. A new 2025/26 census from a newly established plot is under PI/technician QC; TERN expects a publication notice and advises follow-up in late November/early December if absent. **Private support correspondence is not reproduced in this public repository**; preserve original private thread in project correspondence, with date and document ID stored privately.

Public dataset URLs can be inconsistent:
- Current TERN canonical dataset at <https://portal.tern.org.au/metadata/c2968de2-1e8b-4a05-919f-46744b3171ed> has explicit 2014 field survey and a uniform basal-area increment inferred from dendrometers in 2018. This was **not** an actual new 2018 individual-stem survey.
- A legacy route <https://portal.tern.org.au/metadata/TERN/c2968de2-1e8b-4a05-919f-46744b3171ed> can still show a contradictory historical wording that 2018 stems were remeasured and quality-checked; **do not rely on that older text**. Ask TERN to align metadata and issue a formal data-quality/correction notice.
- The independent 2018 TERN supersite dataset indexed under `supersite.1041` may be distinct from this Cleverly-derived source. Do **not** conflate the two, label it validated, or import its reported values without independently obtaining original files and stem IDs: <https://researchdata.edu.au/vegetation-data-direct-ha-2018/1340784>.

## Strict modelling treatment

| Field/data class | Modelling decision |
| --- | --- |
| Cleverly-derived **2018** individual-stem diameter, height, AGB, growth increments and 2014–2018 AGB change | **EXCLUDE** from parameter fitting, optimisation, benchmarks, target curves, biomass-trend validation, allometry training, and spin-up convergence targets. Historical code/data may be retained only as quarantined, explicitly unvalidated provenance/forensics. |
| Cleverly **2014** original D20 and heights | **PROVISIONAL** original measurement descriptors only, not automatically a reliable stand-wide AGB calibration: source/re-identification inconsistency and allometric transfer to Australian Acacia must be independently assessed. |
| GitHub OzFlux v1.1 FIXNC PFT vector | **PRESERVE** source-hashed experiment design (AU-ASM FATES4 EBT65, CoolC3 2, C4 4, bare29), as its recorded main decision is crown cover, 2016 literature and AusPlots, **not** the 2018 Cleverly-derived AGB values. Do not claim this composition has been directly measured as PFT footprint cover. |
| GitHub new SITE_SOIL v2 | **PRESERVE** actual Stage13 verified SHA `2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1`; it is based on separate tower soil publication proxy+SoilGrids, with unresolved depth/particle-size/hardpan limitations. |
| Six 2013–2018 provisional meteorological DATM files | **SEPARATE QC TRACK.** Not sourced from this 2018 biomass dataset; forcing remains `FORCING_SCIENCE_HOLD` for 2018 16.29613 m/s average wind singleton, ACCESS/ERA5/AWS provenance and source time convention. No inference that biomass issues prove met errors. |
| AD400 | **BLOCKED** until independent meteorological QC and final site-soil choices approved, then build a new case specifically binding final v2 or later site soil; direct 80×5 years, no AD5. |

## Verification and future census

When 2025/26 census becomes available, verify DOI/version, source data dictionary, stem-level IDs, plot polygon/size and relation to old plot, timestamps, original D20 heights, units, dead/stump/missing stem handling, allometric formula/parameter/source provenance, and QA procedure. **A newly set up plot is a new spatial sampling frame, not automatically a repeat-survey of 2014 stems.** Only compare stand density or woody biomass between periods if spatial and allometric definitions are demonstrably harmonised; otherwise report cross-plot uncertainty without calling it a repeated growth trajectory.

TERN also published `Alice Springs Mulga Flux Data Release 2026_v3` on 2026-10-21 (<https://portal.tern.org.au/metadata/TERN/608dca79-0ec8-412d-9f13-71f7714affac>). That is a **flux/meteorological release, NOT the promised new stem census**. Its site descriptor includes a standing biomass value, but provenance must be verified before treating it as independent or replacing the cautioned 2018 data.

## Operational checkpoint

- Original historic Cleverly source and prior Stage25–32 exploratory derived analyses are untouched.
- No source numeric repairs, NetCDF edits, CIME or Slurm submissions are approved by this decision.
- Ask TERN/PI for written correction or known-issue advisory for the 2018 dataset, clarification of 2014 stem traceability, whether 2025/26 new plot overlaps historic footprint, archived 2018 L1/L2/L3 independent RM Young wind profiles, and L1 timestamp interval semantics.
- Review official 2018 L3 `AliceSpringsMulga_L3_20180101_20181231.nc` through OzFlux portal separately, preserving licence and SHA. L3 is a QC/provenance lead, **not automatically independent instrument truth**.
