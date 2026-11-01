# ICOS Batch04 — Stage02X four GitHub PFT candidate point surfaces created (2026-11-01)

## Operator-reported IRIDIS6 result

`SOURCE VERIFIED`, `STAGE02X SELF-TEST PASS` and `STAGE02X PLAN PASS`. Operator subsequently invoked the explicit `build` action with `CREATE_FOUR_BATCH04_APPROVED_PFT_SURFACE_CANDIDATES_NO_CASES`. It completed and printed `CREATED FOUR ISOLATED SURFACE CANDIDATES; NO CASE/SLURM; SOIL/QC HOLD`.

**Output directory (IRIDIS6 scratch; not copied into GitHub):**

`/iridisfs/scratch/ly3n24/CLM_FATES/experiments/Batch04_GitHub_PFT_Gz7kLAkn`

| Site | GitHub-approved new conditional host NATPFT | Candidate surface filename | Reported SHA256 |
|---|---|---|---|
| DE-Gri | 13 cool C3 grass 100 | `DE-Gri_B04_GITHUBPFT_POINT_CANDIDATE.nc` | `08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b` |
| DE-RuR | 13 cool C3 grass 100 | `DE-RuR_B04_GITHUBPFT_POINT_CANDIDATE.nc` | `2a4685ae3a43323fcff829bd3fdb5d998d58b4e077923a991ee4afd727767414` |
| IT-Tor | 13 cool C3 grass 100 | `IT-Tor_B04_GITHUBPFT_POINT_CANDIDATE.nc` | `908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b` |
| ES-Agu | 0 bare 49 / 9 evergreen temperate shrub 22 / 13 cool C3 grass 29 | `ES-Agu_B04_GITHUBPFT_POINT_CANDIDATE.nc` | `067722b0dc1440abc2e6aef30ca443b04198f697f16e5ba70344e41f89638fa6` |

The build uses the existing Batch03 FIXNC *model-point* convention `PCT_NATVEG=100`, `PCT_CROP=0`, with all 15 conditional `PCT_NAT_PFT` values summing to 100; this does **not** imply measured full-tower footprint fractions. The source point surface is retained unmodified, including its original ten-layer sand/clay/`ORGANIC`, which remain **unverified soil science input**. FATES host13 maps to `cool_c3_grass` for all four sites; ES-Agu host9 maps to `broadleaf_evergreen_extratrop_shrub` and local FATES nocomp bare-ground source support checks passed. Model runtime use of these paths is **not** yet confirmed.

## Actual status and denominators

- **6/6** Batch04 model-proxy PFT selections explicitly accepted by the operator (including CH-Aws and GL-ZaH selections from earlier six-site decision).
- **4/6** Batch04 sites now have *new* versioned PFT candidate point surfaces: DE-Gri, DE-RuR, IT-Tor, ES-Agu.
- **2/6** Batch04 sites do not yet have new PFT point surfaces: CH-Aws is held on unresolved original tower RH/ERA/QC source, and GL-ZaH needs a separate site-only Arctic FATES map/landunit check.
- **0/6 newly cleared for AD5, AD395 or AD400**, and this Stage02X command creates **0 new CIME cases and 0 Slurm jobs**. The old 8 S30SHARED/S30EXCL original template cases were read only, never converted to use the new surfaces.

The earlier 74 distinct original annual DATM NC files for the four sites passed *internal* Stage02D numeric scans and Stage02V confirmed all 8 static CIME source lists use correct canonical paths. **This is not proof of live effective DATM stream configuration, source tower measurement QC, or reanalysis representativeness.**

## Next gated work

1. Verify all four new NC SHA256 and per-site receipt SHA256 in the scratch output directory. Then perform a **read-only original-template CIME / effective DATM stream / intended fsurdat vs still-original old fsurdat** audit. Do not assume the existing original cases already point to these new NC files.
2. Independently verify four-site native 30-minute tower meteorology (VPD/RH/TA/precipitation/radiation) source QC, selected forcing provenance and time alignment; do not replace 74 NC because old Stage02U parsing initially printed False (Stage02V proved parser false negative).
3. Check original soil texture and organic matter, **especially IT-Tor**: all 10 inherited `ORGANIC` layers have zero, requiring an independent source and interpretation review before AD5.
4. Only after those science and effective case checks pass, make isolated **new** site-specific CIME cases with `fsurdat` pointing to these candidate NCs and run one 5-year AD smoke per approved site. No long spinups until AD5 + archive/energy/flux gates pass.
5. Separately handle remaining **2/6 surface** sites: CH-Aws is source RH/ERA HOLD (Stages02O–T), and GL-ZaH is a site-only Arctic shrub host9/11 parameter map requirement; do not modify the shared map or auto-approve either.

Do not overwrite original surface, forcing, CIME cases, global FATES parameters, or submit Slurm on the basis of the four successfully generated point candidates alone.
