#!/usr/bin/env python3
"""READ-ONLY inventory of the BADM (BIF) metadata shipped with each site's FLUXNET v1.3 package.

For every site under --sites-root it finds <SITE>/forcing/raw/<release>/*_FLUXNET_BIF_*.csv
(BIFVARINFO files are skipped); if no unpacked BIF exists it reads the BIF member from
<SITE>/forcing/packages/*.zip without extracting anything.

BIF = 5 columns: SITE_ID, GROUP_ID, VARIABLE_GROUP, VARIABLE, DATAVALUE.

Writes to --out (default ./BIF_inventory):
  bif_group_counts_long.csv   site, source file, VARIABLE_GROUP, number of GROUP_IDs, rows
  bif_group_matrix.csv        site x VARIABLE_GROUP matrix of GROUP_ID counts (0 = absent)
  bif_key_groups_rows.csv     every row of the groups useful for post-spin-up evaluation
                              (vegetation structure, biomass, LAI, height, species, soil, disturbance/management)
Nothing under --sites-root is modified.
"""
import argparse
import csv
import io
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
KEY = re.compile(r"HEIGHT|LAI|GAI|BIOMASS|AGB|BASAL|TREE|DBH|SPP|SOIL|SOC|DM_|_DM|DISTURB|MANAGE|STAND|AGE|PLANT|HARVEST|THIN|LITTER|IGBP|SITE_DESC",
                 re.I)
COLS = ["SITE_ID", "GROUP_ID", "VARIABLE_GROUP", "VARIABLE", "DATAVALUE"]


def is_bif(name):
    n = Path(name).name.upper()
    return "_BIF_" in n and "BIFVARINFO" not in n and n.endswith(".CSV")


def find_bif(site_dir):
    raw = sorted(p for p in (site_dir / "forcing" / "raw").glob("*/*") if is_bif(p.name))
    if raw:
        return [(str(p), p.read_bytes()) for p in raw]
    out = []
    for z in sorted((site_dir / "forcing" / "packages").glob("*.zip")):
        try:
            with zipfile.ZipFile(z) as zf:
                for m in zf.namelist():
                    if is_bif(m):
                        out.append((f"{z}::{m}", zf.read(m)))
        except zipfile.BadZipFile:
            print(f"  WARN bad zip {z}", file=sys.stderr)
    return out


def read_rows(blob):
    text = blob.decode("utf-8-sig", errors="replace")
    rd = csv.reader(io.StringIO(text))
    header = [h.strip().upper() for h in next(rd, [])]
    if header[:5] != COLS:
        raise ValueError(f"unexpected BIF header {header[:6]}")
    for r in rd:
        if len(r) >= 5:
            yield dict(zip(COLS, (x.strip() for x in r[:5])))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=Path("BIF_inventory"))
    ap.add_argument("--sites", nargs="*", help="limit to these site codes")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    sites = sorted(p for p in a.sites_root.iterdir() if p.is_dir() and re.fullmatch(r"[A-Z]{2}-[A-Za-z0-9]{3}", p.name))
    if a.sites:
        sites = [p for p in sites if p.name in set(a.sites)]

    long_rows, key_rows = [], []
    matrix = defaultdict(dict)
    for sd in sites:
        files = find_bif(sd)
        if not files:
            print(f"{sd.name}: NO_BIF_FOUND")
            matrix[sd.name]["__NO_BIF__"] = 1
            continue
        for src, blob in files:
            groups, nrows = defaultdict(set), defaultdict(int)
            try:
                for r in read_rows(blob):
                    vg = r["VARIABLE_GROUP"]
                    groups[vg].add(r["GROUP_ID"]); nrows[vg] += 1
                    if KEY.search(vg) or KEY.search(r["VARIABLE"]):
                        key_rows.append({"site": sd.name, "source": src, **r})
            except ValueError as e:
                print(f"{sd.name}: {e} in {src}")
                continue
            for vg in sorted(groups):
                long_rows.append({"site": sd.name, "source": src, "VARIABLE_GROUP": vg,
                                  "n_group_ids": len(groups[vg]), "n_rows": nrows[vg]})
                matrix[sd.name][vg] = matrix[sd.name].get(vg, 0) + len(groups[vg])
            print(f"{sd.name}: {len(groups)} variable groups from {Path(src.split('::')[-1]).name}")

    with (a.out / "bif_group_counts_long.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, ["site", "source", "VARIABLE_GROUP", "n_group_ids", "n_rows"]); w.writeheader(); w.writerows(long_rows)
    all_groups = sorted({g for d in matrix.values() for g in d})
    with (a.out / "bif_group_matrix.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["site"] + all_groups)
        for s in sorted(matrix):
            w.writerow([s] + [matrix[s].get(g, 0) for g in all_groups])
    with (a.out / "bif_key_groups_rows.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, ["site", "source"] + COLS); w.writeheader(); w.writerows(key_rows)

    print(f"\n{len(matrix)} sites, {len(all_groups)} distinct variable groups. Groups and how many sites have them:")
    for g in all_groups:
        n = sum(1 for s in matrix if matrix[s].get(g, 0))
        print(f"  {g:<32} {n:>3} sites{'   <- key' if KEY.search(g) else ''}")
    print(f"\nREAD-ONLY. Outputs in {a.out.resolve()}")


if __name__ == "__main__":
    main()
