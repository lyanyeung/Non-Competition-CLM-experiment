#!/usr/bin/env python3
"""Read-only extraction of the ICOS38 sites from the PROFOUND database (SQLite, v0.3).

PROFOUND (Reyer et al. 2020, ESSD 12:1295; data doi:10.5880/PIK.2020.006) covers four of our sites:
    CZ-BK1 = bily_kriz (site_id 3), IT-Col = collelongo (5), FI-Hyy = hyytiala (12), DK-Sor = soro (21)
Site ids are looked up in the SITES view by name; the ids above are only a fallback.

Exported (one CSV per view, only our four sites, plus a summary):
  default  SITES, SITEDESCRIPTION, STAND, TREE, SOIL, NDEPOSITION_EMEP, NDEPOSITION_ISIMIP2B, CO2_ISIMIP,
           POLICY / SOURCE / METADATA_* views for these datasets (licences differ per site and dataset)
  --with-timeseries  also FLUX, METEOROLOGICAL, SOILTS, CLIMATE_LOCAL (large; we already have FLUXNET)

Only the Python standard library is used. The database is opened read-only.

Usage:
  python3 05_extract_PROFOUND_ICOS38.py --db /path/ProfoundData.sqlite --out ICOS38_extract
"""
import argparse
import csv
import sqlite3
from pathlib import Path

SITES = {"CZ-BK1": ("bily_kriz", 3), "IT-Col": ("collelongo", 5), "FI-Hyy": ("hyytiala", 12),
         "DK-Sor": ("soro", 21)}
DEFAULT_VIEWS = ["SITES", "SITEDESCRIPTION", "STAND", "TREE", "SOIL", "NDEPOSITION_EMEP", "NDEPOSITION_ISIMIP2B",
                 "NDEPOSITION_ISIMIP", "CO2_ISIMIP", "POLICY", "SOURCE"]
TIMESERIES_VIEWS = ["FLUX", "METEOROLOGICAL", "SOILTS", "CLIMATE_LOCAL"]


def objects(con):
    return {n: t for n, t in con.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view')")}


def columns(con, name):
    return [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]


def site_ids(con, objs):
    ids = {}
    if "SITES" in objs and {"site", "site_id"} <= set(columns(con, "SITES")):
        lookup = {str(name).lower(): sid for sid, name in con.execute("SELECT site_id, site FROM SITES")}
        for icos, (name, fallback) in SITES.items():
            ids[icos] = lookup.get(name, fallback)
    else:
        ids = {k: v[1] for k, v in SITES.items()}
    return ids


def export(con, name, where, out):
    cols = columns(con, name)
    sql = f'SELECT * FROM "{name}"' + (f" WHERE {where}" if where and "site_id" in cols else "")
    n = 0
    with open(out / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in con.execute(sql):
            w.writerow(row)
            n += 1
    return n, cols


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--with-timeseries", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    objs = objects(con)
    (a.out / "_all_objects.txt").write_text("\n".join(f"{t}\t{n}" for n, t in sorted(objs.items())) + "\n")
    ids = site_ids(con, objs)
    where = "site_id IN (" + ",".join(str(i) for i in ids.values()) + ")"
    print("site ids:", ids)

    views = DEFAULT_VIEWS + (TIMESERIES_VIEWS if a.with_timeseries else [])
    keep = ("SITES", "SITEDESCRIPTION", "STAND", "TREE", "SOIL", "NDEPOSITION", "CO2")
    views += sorted(n for n in objs if n.startswith("METADATA_") and n[len("METADATA_"):].startswith(keep))
    summary = []
    for v in views:
        if v not in objs:
            summary.append((v, "absent", "", ""))
            continue
        n, cols = export(con, v, where, a.out)
        summary.append((v, n, "site_id" in cols, ";".join(cols)))
        print(f"{v:28s} {n:>9} rows")

    # quick per-site overview of the STAND view (years, ages, variables with data)
    if "STAND" in objs:
        with open(a.out / "_STAND_overview.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["icos_site", "site_id", "species", "n_rows", "first_year", "last_year", "min_age", "max_age"])
            for icos, sid in ids.items():
                for row in con.execute("SELECT species, COUNT(*), MIN(year), MAX(year), MIN(age), MAX(age) "
                                       "FROM STAND WHERE site_id=? GROUP BY species", (sid,)):
                    w.writerow([icos, sid, *row])
    with open(a.out / "_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["view", "rows_exported", "filtered_by_site", "columns"])
        w.writerows(summary)
    with open(a.out / "_site_map.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["icos_site", "profound_site", "site_id"])
        for icos, sid in ids.items():
            w.writerow([icos, SITES[icos][0], sid])
    print("written to", a.out)


if __name__ == "__main__":
    main()
