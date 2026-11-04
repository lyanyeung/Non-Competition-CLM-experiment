# OzFlux AU-ASM spin-up forcing years: operator decision (2026-11-04)

## Decision

**The AU-ASM spin-up cycles all complete calendar years of the Mulga1 tower record: 2011–2022 (12 years).** This follows the 5 AmeriFlux and 4 ICOS batches, whose spin-ups cycle each site's full record (e.g. CA-TP4 2002–2023, AT-Neu 2002–2020, `taxmode=cycle`).

- **Partial years** 2010 (from 2010-09-03) and 2023 (to 2023-03-08) are left out.
- **Mulga2** (2024-08-21 to 2026-04-23) stays a separate record and is not in the spin-up cycle. See [below](#mulga1-and-mulga2).
- **The evaluation window is unchanged:** 2013–2017, pre-dieback. The observation run runs 2011–2022 once, and the other years are run but not scored.
- **The same rule applies to the other 19 OzFlux / JapanFlux sites** when their forcing is built. Per-site notes are in CLM-FATES-single-site-workflows `examples/OzFlux_JapanFlux_PostSpinup/README.md` (branch `oz-jp-surface-carbon-20261103`). AU-DaS has an open question about its post-November-2022 cleared years.

## What this changes for the forcing work

- **Current state.** The provisional DATM (Stage14) and the forcing-science QC so far (Stage09–22, [PR #65](https://github.com/lyanyeung/Non-Competition-CLM-experiment/pull/65)) cover 2013–2018 only.
- **New scope.** QC and DATM must also cover **2011–2012 and 2019–2022**, with the same release requirements as `MET_FORCING_SCIENCE_HOLD_20261103.md`.
- **Failed structural years.** In the upstream OzFlux_MultiSite_09 Stage07/08 structural gate, 2011, 2012 and 2019 were not structural candidates; 2020–2022 were. The reasons are in the Stage08 year-reason ledger. These years need review, not silent exclusion. If a year cannot be made usable, report it for an operator decision rather than shortening the cycle.
- **Holds stay in force.** The forcing-science HOLD and the Stage08 AD400 hard block are unchanged. AD400 needs the whole 2011–2022 forcing released.

## Mulga1 and Mulga2

The global attributes of the TERN 2026_v2 L6 files were read through OPeNDAP on 2026-11-04 (`dap.tern.org.au/thredds/dodsC/ecosystem_process/ozflux/AliceSpringsMulga/2026_v2/L6/default/`).

**Identical in both files:**
- latitude −22.2828, longitude 133.2493;
- elevation 606 m, tower height 13.7 m, canopy height 4.4 m;
- site name, soil and vegetation descriptions;
- time zone Australia/Darwin.

**Different:**
- the site PI;
- the title of Mulga2, which reads "calendar year 2025 post logger change 10/04/2025";
- the coverage, with a 17.5-month gap between the two files.

**Interpretation.** Mulga2 is the same site and nominal tower position. The attributes look copied, though: both carry `history` = "June 2021 processing". Mulga2 also follows a gap, a PI change and a logger change, and it measures the stand after the 2018–2020 dieback. So it is not spliced into Mulga1.

**Current authorization unchanged: `forcing_science_approval=false`, `AD400_authorised=false`.**
