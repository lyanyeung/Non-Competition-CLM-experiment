# ICOS Batch04 — Stage03N source metadata/self-test PASS; archive NOT YET on IRIDIS6 (2026-11-02)

## Actual Stage03N operator log

The operator ran commit `1d76e49cdb4d5dfebc5979cbcb75da48d463c75a`, script blob `83b92a75b236b04d9211aabacd11adf5468daa22`. Python full syntax PASS, Stage03N self-test PASS (expected official archive SHA/2025 product time metadata and wrong-archive rejection), and `--source-info` succeeded. Then the launcher explicitly reported:

```
OFFICIAL_ARCHIVE_NOT_LOCAL
DOWNLOAD_FROM=https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl
UPLOAD_TO=/home/ly3n24/ICOS_Batch04_neighbor_reference/ICOSETC_IT-TrF_METEO_L2.zip
```

**This is NOT a failed source SHA test and NOT a completed observational QC audit.** The actual `--archive` inspection was not called. No ZIP was downloaded or uploaded by the Stage03N tool. No IT-TrF 2025 November source time series, TA, flags, actual sensor height or direct IT-Tor-vs-IT-TrF station comparison has been examined. No original IT-Tor FLUXMET, selected Stage28, 74 DATM NetCDF, FATES/PFT/CIME or Slurm changes.

## Exact official source and licence

[ICOS ETC L2 Meteo from Torgnon-LD, 2011-12-31 to 2025-12-31](https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl):

- Object PID `11676/mwN98ExGR4uPnaUKi5mWoISl`
- Filename `ICOSETC_IT-TrF_METEO_L2.zip`
- Expected bytes `16713915`
- Official SHA256 `9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f`
- Covering 2025 (source metadata). ICOS ETC meteo lists `TA`, `RH`, `TIMESTAMP` (UTC), `TIMESTAMP_END` (local non-DST). L2 Met quality good-flag values include 1/0 but **these are not the same thing as FLUXNET `TA_F_QC` 0/1/2**, so audit original column-specific flag meaning before assigning measured labels.
- The Download link on the ICOS product page redirects to the [ICOS Data Licence acceptance page](https://data.icos-cp.eu/licence?ids=%5B%22mwN98ExGR4uPnaUKi5mWoISl%22%5D&fileName=ICOSETC_IT-TrF_METEO_L2). The operator must review and select **“Yes, I accept”** themselves (or sign into ICOS and accept permanently), then download and retain the unmodified original ZIP. Do not circumvent the licensing acknowledgement by scripting an undocumented direct URL.

The University of Southampton [Iridis6 SSH/SFTP guidance](https://southampton-rsg-training.github.io/intro-to-hpc/instructor/2_using_hpc_systems.html) confirms `iridis6.soton.ac.uk` as the login host, accessible from campus or VPN. On Windows PowerShell, after the operator has downloaded the file:

```powershell
ssh ly3n24@iridis6.soton.ac.uk 'mkdir -p /home/ly3n24/ICOS_Batch04_neighbor_reference'
scp "$HOME\Downloads\ICOSETC_IT-TrF_METEO_L2.zip" ly3n24@iridis6.soton.ac.uk:/home/ly3n24/ICOS_Batch04_neighbor_reference/
```

If a different local Downloads folder is used, change the local path. On IRIDIS6, verify **exactly the saved original data object**:

```bash
SOURCE="$HOME/ICOS_Batch04_neighbor_reference/ICOSETC_IT-TrF_METEO_L2.zip"
test -f "$SOURCE"
echo "9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f  $SOURCE" | sha256sum -c -
stat -c 'BYTES=%s PATH=%n' "$SOURCE"
```

Then run the already-published [Stage03N script](../scripts/03n_IT_TrF_official_2025_L2_METEO_SHA_and_TA_time_preflight_READONLY.py) with `--archive "$SOURCE" --out-dir "$NEW_EMPTY_PRIVATE_HOME_DIR"`. **No need to create Stage03O or re-run Stage03B–03M**. Stage03N's full source inspection has not yet passed and may require interpreting the exact real CSV/schema before a reliable QC0-only and clock-aligned comparison is possible.

## Science state

Original IT-Tor long 1458-HH QC1/QC2 gapfill and the three priority subruns: **156 HH** of QC1 MDS, all **98** of the MDS-minus-packaged-ERA differences below −10°C and **138** below −5°C, not independently verified erroneous tower measurements. The neighboring **IT-TrF larch forest ~2100 m** station is distinct from **IT-Tor grassland** (~2160 m). Time-base harmonization, correct sensor quality columns and canopy/height comparability are mandatory before comparing data. IT-Tor original ten-layer `ORGANIC=0` and separate Batch04 source/soil/PFT gates remain HOLD; no new AD5 or AD400 release.
