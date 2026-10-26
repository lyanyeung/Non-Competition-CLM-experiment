# Fourth-batch direct AD400 with Batch01 BASE TA sensor proxies

The operator requested on 26 October 2026: finish AmeriFlux Batch04 using
the Batch01 stack method, without an AD5 test. After checking the ten local
BIF workbooks and finding no TA measurement-height records, the operator
explicitly selected the Batch01 proxy method. This later instruction
supersedes the earlier request to hold every site without a verified TA_F
height. It does not turn a proxy into a verified FLUXNET sensor crosswalk.

## Exact original height source

Use the same source as Batch01: [BASE_MeasurementHeight_20260908.csv](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/blob/06c75f28f1b894db81ddb03a9a0ec8c4be9fc528/examples/AmeriFlux_sites/metadata/BASE_MeasurementHeight_20260908.csv),
full SHA256 `1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a`.
The installer independently verifies the source bytes and every selected
original CSV row against the frozen per-site policy.

| Site | Chosen BASE temperature variable | Proxy ZBOT (m) | Qualification |
|---|---|---:|---|
| US-Rpf | TA_PI_F_1_1_1 | 2.3, then 4.0 from 2013-05-13 | Dated relocation; day precision uses local midnight |
| US-SP1 | TA_1_1_1 | 30.0 | Baseline comment 2000; undated height record |
| US-SRG | TA_1_1_1 | 2.9 | Undated height record |
| US-SRM | TA_1_1_1 | 6.0 | Main upper sensor chosen; another TA sensor is 2.15m |
| US-Seg | TA_PI_F | 3.2 | PI source says gap filling also uses nearby towers/HMP45c |
| US-Ses | TA_PI_F | 3.2 | PI source says gap filling also uses nearby towers/HMP45c |
| US-Slt | TA_1_1_1 | 15.9 | Main tower; exclude separate 16.1m sensor 800ft NNW |
| US-Syv | TA_PI_F_1_1_1 | 36.0 | PI alias preferred over multiple profile levels |
| US-Ton | TA_PI_F_1_1_1 | 23.5 | Upper tower chosen over 2m understory sensor |
| US-Uaf | TA_PI_F_1_1_1 | 8.0 | Upper TA/PI level chosen over 4/2/1m levels |

All ten policies retain `FLUXNET_TA_F_sensor_crosswalk_verified=false` and
`historical_height_coverage_verified=false`. Applying an undated baseline
to the full forcing cycle, including pre-observation gap-filled periods,
is a documented experiment assumption. Wind heights are not substituted
for TA; this workflow supplies the selected TA ZBOT to the existing
single-height 1PT DATM interface, as Batch01. Distinct actual wind heights
remain a limitation of that interface/forcing-height assumption.

The Rpf height vector is constructed on the local native clock, with the
relocation event, BEFORE the same UTC permutation as meteorology. The
full forcing cycle wraps across its last/first years; the height vector
wraps consistently with the source records. No fixed 4m value is imposed
on all source years.

## Integration and paired interpretation

Each case gets AD400 in one initial submission: `STOP_OPTION=nyears`,
`STOP_N=5`, `REST_N=5`, `RESUBMIT=79`, `RESUBMIT_SETS_CONTINUE_RUN=TRUE`,
`DOUT_S=TRUE`, `spinup_state=2`, cold startup. There is no independent AD5
experiment and no manual AD395 continuation. Five-year segments are CIME
restart/archival units. Normal400 is a subsequent phase after complete
AD400 restart/archive verification; this release does not start Normal.

The two arms share meteorology, TA proxy policy, coordinates, PFT surface,
original grid soil layers and constant first-forcing-year global CO2.
FIXNC has `use_fates_fixed_biogeog=true`, `use_fates_nocomp=true`;
standard FULL has both false. **Sharing a PFT surface does not impose
identical initial PFT area in FULL.** Standard dynamic FATES can initialize
and recruit outside the prescribed FIXNC mixture. This is a standard
FULL-versus-FIXNC configuration contrast; it must not be presented as a
competition-only causal test with proven identical initial vegetation.
The controller records this limitation and does not silently change
FATES initial densities or disable recruitment to manufacture a match.

The same installed default FATES JSON as the successful Batch01 cases is
pinned by SHA256 `0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04`.
US-Uaf gets a site-private ARCTIC_PURE copy: host9->FATES10 and
host11->FATES11; other HLM rows and physiological parameters remain unchanged.
All ten mapped FIXNC fractions and explicit host bare fractions are
forward-checked against the source recommendation. No shared JSON is edited.

Soils remain the already constructed shared surface's original gridded
depth layers, not fabricated ten-layer profiles from 0-30cm soil summaries.
CO2 uses NOAA global annual means for each initial forcing year, following
the Batch01 method, not local site measurements or transient CO2.

## Execution modes and recovery

Use `scripts/06_fetch_direct_AD400.sh --commit FULL_SHA --all` after
activating `clm_fates_env` to download a versioned package, verify the BASE
source, build/independently verify annual DATM, prepare both arms and submit
AD400. It never uses git pull or changes another experiment.

For a staged execution, use `--inputs` first, then reuse the exact manifest
with `--prepare --manifest PATH` and `--submit --manifest PATH`.
`CURRENT_DATM_MANIFEST.txt` inside the immutable release directory records
the selected path. Reusing a prepared case verifies its receipt; a partial
preparation or previous submission attempt is held for inspection.

Every actual initial submission imports `b04_stack_guard.py` in the SAME
Python process immediately before `case.submit --skip-preview-namelist`.
It raises only a low soft stack to 300000KiB when possible, requires at
least 65536KiB, never lowers higher/unlimited stack, and verifies Slurm
STACK/ALL propagation without an explicit STACK exclusion. CIME children
inherit that process's limit. No stack-protector compiler option is disabled.
Each submit attempt gets an exclusive ledger before CIME is invoked.

New cases clone only the proven Batch01 CIME/machine/executable template;
their site-specific met years, CO2, PFT surface, private map, point
coordinates and output/archive paths are overwritten and verified.
PTS_DOMAINFILE is UNSET; CaseDocs AND live NUOPC point coordinates must
match the station surface. The proven private Batch01 FATES AD buildnml
overlay is used for preview, then the original CIME source lock is restored.
The persisted skip-preview option is retained for automatic resubmissions.

`audit-ad400` requires all 80 exact five-year restart directories, each
land/atmosphere/coupler restart, final `spinup_state=2`, exhausted CIME
resubmissions, no queued jobs, and 80 completed model plus 80 archive jobs.
It never treats a successful submit or first restart as AD400 completion.

## Validation scope

Local tests use real NetCDF write/read and CSV source reconversion for
leap exclusion, UTC cyclic boundaries, all field/unit equality, the Rpf
dated height change, exact VPD precision exceptions, and corruption
rejection. Synthetic CIME fixtures check both arms, live-vs-CaseDocs input
identity, wrong-station streams and wrong point coordinates. Mock Slurm
tests check live stack before attempt/submit, hard-limit/exclusion failure,
and no duplicate initial submission. Bash is checked with `bash -n`.

Actual cluster paths, the installed pinned executable/parameter source,
CIME previews and Slurm execution must pass on IRIDIS6. Local test success
does not establish that any of the twenty cases has been created, submitted
or completed on the cluster.
