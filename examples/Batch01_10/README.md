# Batch 01 — Ten quantitative-vegetation-evidence towers

**Project:** Fixed Biogeography & no competition FATES experiment  
**Planned spin-up:** **AD400 → NORMAL400**, 800 model years per tower; **NOT YET STARTED**.  
**Exclusions:** NL-Loo and DE-Tha (protected prior examples).  
**Data sources:** [original 38-site PFT inventory](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/ICOS_sites/ICOS_PFT), the project's [22-candidate cohort](../../data/22_site_cohort.csv), and [Batch01 tabular register](../../data/batch01_10_sites.csv).

## Why these ten?

Twenty **non-example** sites are listed in the 22-site quantitative-evidence cohort. These ten are prioritized because forest tree identities mostly map to ENF, DNF, DBF or EBF without forcing all remaining unknown vegetation into one class. Even so, most measured values are **species composition, tree-carbon shares or basal area**, NOT the EC-tower footprint's measured horizontal PFT area. **All ten surfaces remain on scientific HOLD.** We have **not** created numerical `PCT_NAT_PFT` prescriptions, set crop/natural landunit fractions, altered datasets or submitted jobs.

| Rank | Station | Original batch | Original numeric evidence | Provisional functional grouping **of the reported metric only** | What must be decided before using it as a model-area surface? |
| ---: | --- | --- | --- | --- | --- |
| 1 | **CZ-BK1** | 8 | Picea abies 99%; Abies alba 1% | ENF 100% of investigated tree area | Clear local survey, but verify tower footprint/landunit areas and mapping |
| 2 | **IT-Ren** | 8 | Picea abies ≈85%; Pinus cembra 12%; Larix decidua 3% | ENF ≈97%, **DNF 3%** of trees | Explicit larch DNF; verify survey denominator and exact values |
| 3 | **RU-Fyo** | 6 | Picea abies 85%; Betula pendula 15% | ENF 85%; DBF 15% of reported stand metric | Original Table S2 metric unspecified, Russia site network/access licensing |
| 4 | **CH-Dav** | 8 | Picea abies **over 99.5%** | ENF >99.5% of tree inventory | Do not falsely round inequality to exact 100% model area |
| 5 | **IT-Col** | 13 | Fagus sylvatica 100% | DBF 100% of reported stand species | Tree monoculture is not full grid/footprint ground cover |
| 6 | **FR-Fon** | 11 | Quercus petraea 79%; Carpinus betulus 18%; other <3% | DBF ≥97% **of tree basal area** | Basal area not horizontal area; older study has a different 75/20 report |
| 7 | **FI-Sod** | 11 | Pinus sylvestris 95% | ENF 95% of stand metric | 5% not identified; original survey metric unspecified |
| 8 | **FR-Pue** | 13 | Quercus ilex 95%; other data say >80% cover | EBF 95% of reported stand composition | Stand species vs cover differ; model EBF PFT support must be verified |
| 9 | **DE-Hai** | 6 | Fagus 64%; Fraxinus 28%; Acer 7% | DBF 99% **of tree carbon stock** | Carbon shares are not land area; ~1% unclear |
| 10 | **BE-Vie** | 8 | Fagus 43%; Pseudotsuga 37% | DBF 43%; ENF 37% of reported stand metric | **20% unresolved**, metric unspecified; no silent renormalization |

**Stand-specific source links** are in the exact [Batch01 CSV](../../data/batch01_10_sites.csv). The strongest primary site-description example is [ICOS CZ-BK1](https://meta.icos-cp.eu/resources/stations/ES_CZ-BK1): it reports a 99/1 split **within the investigated area**. The recurring 2020 stand-composition source is [Flechard et al. (2020) Table S2 supplement](https://bg.copernicus.org/articles/17/1583/2020/bg-17-1583-2020-supplement.pdf); numerical claims listed in the inventory **must still be checked at the source table level**.

## Batch organization and intended site examples

Suggested per-site future structure (directories or scripts should be created **only when the site's evidence and original input file audit is accepted**):

```text
examples/Batch01_10/
    README.md                       # this scientific cohort runbook
data/
    batch01_10_sites.csv            # source evidence, not approved surface fractions
examples/Batch01_10/<site>/
    README.md                       # site evidence & model-input decisions
    config/site_manifest.json       # per-site forcing years, CO2, case paths & SHA256
    data/evidence.csv               # provenance and denominator
    scripts/01_read_only_source_audit.py
    scripts/02_build_site_surface_VERSIONED.py
    scripts/03_AD400_smoke_and_resume.py
    scripts/04_Normal400_branch_and_resume.py
```

**No site-specific script from DE-Tha is safe to run unchanged**: DE-Tha hard-codes `1996–2025`, v2 SHA256, its run/case dirs and absolute names. Batch01 must first enumerate each tower's own verified observational forcing, DATM streams, initial date, case baselines, surface dimensions, source soil and compatible FATES PFT mapping.

## Readiness gates to work through, in order

1. **Observed PFT provenance:** retrieve actual station/forest source, verify measurement year, survey method, spatial coverage, specific **denominator** and any species sum. Record the unknown share. A scientific proxy must be proposed and explicitly recorded before it can become a fixed PFT surface.
2. **Existing CLM-FATES evidence:** identify each site's already developed 6/8/11/13-site source forcing, stream calendars, original surface data and CIME case in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows). Validate original file checksums and source data license; never modify old spinups or cases.
3. **Observed soil texture first:** find reliable tower/stand sand, silt and clay data, document depth and particle convention. Build a **new versioned** surface from site evidence when available; otherwise use a labeled source-grid fallback. Do not infer sand/clay percentages from soil classification names alone.
4. **Batch01 individual dry-run:** cross-check 100% landunit totals, `PCT_NAT_PFT`, dynamic FATES mapping, generated `lnd_in`, `spinup_state=2`, source hashes, executable and per-case Slurm single-core launch / real `#SBATCH` parameters.
5. **AD400:** first cold-start 5-year AD smoke and **verified archive**, then 395 years in the **same AD case**, guarded. Use **one** source forcing cycle repeatedly.
6. **NORMAL400:** wait for full AD400 restart, branch into a **separate** new hybrid normal case, 5-year smoke to verify `spinup_state=0`, then separate 395-year continuation. Do **not** transform an active AD resubmitting case in place.
7. **Scientific convergence:** inspect soil C/N, FATES carbon pools/LAI, GPP/NEE and water balance over the final years; normal-pool equilibration is not proven by calendar length alone.

Protocol: [AD400 → NORMAL400](../../docs/AD400_NORMAL400_PROTOCOL.md). All Batch01 sites are currently **EVIDENCE_ONLY_HOLD_SURFACE**. No CIME or Slurm experiments have been generated for the new ten as part of this planning change.

## The separate ten-site Batch02 reserve

[Batch02 CSV](../../data/batch02_10_sites.csv) contains **DK-Sor, FR-Hes, FR-FBn, BE-Bra, IT-Noe, CH-Fru, CH-Lae, ES-LJu, FI-Hyy, IT-MBo**. Several have conflicting temporal stand measurements, unresolved needleleaf mixtures or ground-cover/vegetated-cover denominators; they remain screened leads, not rejected sites. They are not Batch01 and should not be silently swapped into Batch01 without updating the two registers.

## Preserving the two example histories

**NL-Loo** has a historic PRE50/AD200 workflow. **DE-Tha** had a direct AD400 cold start: its first 5-year AD and a separate AD5→Normal5 mode-switch **already succeeded**, and its remaining 395 AD years had been **submitted**, but not confirmed finished at the time this register was created. Both example histories are deliberately retained rather than rewritten into the new 800-year standard.
