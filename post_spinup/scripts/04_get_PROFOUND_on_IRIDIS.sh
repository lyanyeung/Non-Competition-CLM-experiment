#!/usr/bin/env bash
# Download the PROFOUND database v0.3 (Reyer et al. 2020, doi:10.5880/PIK.2020.006) to IRIDIS scratch,
# check it, unzip it, and extract the four ICOS38 sites it covers (CZ-BK1, IT-Col, FI-Hyy, DK-Sor).
#
# Sizes (GFZ landing page): ProfoundData.zip (SQLite) 2.6 GB; ProfoundData_ASCII.zip 1.6 GB (not needed);
# Soroe_DBH_H_AGE_20200428.zip 0.25 MB (reconstructed single-tree data for Soroe).
# Licence: CC BY-NC 4.0, plus site-specific data policies (exported by script 05; check before sharing).
#
# Run on a LOGIN node (compute nodes usually have no internet):
#   bash post_spinup/scripts/04_get_PROFOUND_on_IRIDIS.sh
# Options (environment variables):
#   PROFOUND_DIR  where to download/unzip    (default /iridisfs/scratch/ly3n24/CLM_FATES/external/PROFOUND_v0.3)
#   RFS_DIR       if set, the zip is also copied there (Research File Storage backup; scratch is not backed up)
#   KEEP_SQLITE   1 = keep the unzipped .sqlite after extraction (default 1)
set -euo pipefail

PROFOUND_DIR=${PROFOUND_DIR:-/iridisfs/scratch/ly3n24/CLM_FATES/external/PROFOUND_v0.3}
RFS_DIR=${RFS_DIR:-}
KEEP_SQLITE=${KEEP_SQLITE:-1}
BASE=https://www.pik-potsdam.de/data/doi/10.5880/PIK.2020.006   # same folder as PROFOUNDdatabase.pdf
FILES="ProfoundData.zip Soroe_DBH_H_AGE_20200428.zip PROFOUNDdatabase.pdf PROFOUNDsites.pdf ProfoundData.pdf changelog_Profound-DB_v03.pdf"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

mkdir -p "$PROFOUND_DIR"
cd "$PROFOUND_DIR"
echo "== target: $PROFOUND_DIR"
df -h "$PROFOUND_DIR" | tail -1

for f in $FILES; do
  if [[ -s "$f" && "$f" != *.zip ]]; then echo "have $f"; continue; fi
  echo "== downloading $f"
  # -c resumes a partial download; the 2.6 GB file may take 10-30 min
  if ! wget -c --tries=5 --timeout=60 "$BASE/$f"; then
    echo "!! $BASE/$f failed. Open https://doi.org/10.5880/PIK.2020.006 , copy the download link for $f," >&2
    echo "!! and rerun with:  wget -c '<link>' -O $PROFOUND_DIR/$f" >&2
    [[ "$f" == ProfoundData.zip ]] && exit 1
  fi
done

ls -lh "$PROFOUND_DIR"
echo "== testing zip integrity"
unzip -tq ProfoundData.zip
unzip -l ProfoundData.zip

if [[ -n "$RFS_DIR" ]]; then
  echo "== copying zip to Research File Storage: $RFS_DIR"
  mkdir -p "$RFS_DIR"
  rsync -av --progress ProfoundData.zip Soroe_DBH_H_AGE_20200428.zip ./*.pdf "$RFS_DIR"/
fi

SQLITE=$(unzip -Z1 ProfoundData.zip | grep -i '\.sqlite$' | head -1)
if [[ ! -s "$SQLITE" ]]; then
  echo "== unzipping $SQLITE"
  unzip -o ProfoundData.zip "$SQLITE"
fi
unzip -o -q Soroe_DBH_H_AGE_20200428.zip -d Soroe_DBH_H_AGE || true
ls -lh "$SQLITE"

echo "== extracting ICOS38 sites"
python3 "$SCRIPT_DIR/05_extract_PROFOUND_ICOS38.py" --db "$PROFOUND_DIR/$SQLITE" --out "$PROFOUND_DIR/ICOS38_extract"

if [[ "$KEEP_SQLITE" != 1 ]]; then rm -f "$SQLITE"; echo "removed unzipped $SQLITE (zip kept)"; fi
echo "== done. Send back: $PROFOUND_DIR/ICOS38_extract  (tar czf ICOS38_PROFOUND_extract.tgz -C $PROFOUND_DIR ICOS38_extract)"
