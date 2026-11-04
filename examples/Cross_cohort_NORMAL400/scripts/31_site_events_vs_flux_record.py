#!/usr/bin/env python3
"""READ ONLY. Put the special site events (data/site_special_events.csv) against each site's flux record.

For every site in the register it prints:
  * the years covered by the site's EC FLUXNET half-hourly file (first/last year with data);
  * the event year(s) and how many EC years fall before, during and after the event;
  * every disturbance/management entry in the site's BADM/BIF file (VARIABLE_GROUP GRP_DM_*,
    e.g. GRP_DM_FIRE, GRP_DM_HARVEST, GRP_DM_PLANTING, GRP_DM_INS_PATH, GRP_DM_GENERAL), which is how the
    years marked "year_to_confirm" (US-Ho3, US-Rpf, US-UiD) and the US-Vcp fire question get settled.

--all-sites also scans the BIF files of the other register-free sites, to catch events this register misses.

EC and BIF files are looked up under <sites-root>/<SITE> (forcing/raw* first). BIF files may be .csv or .xlsx
(.xlsx needs openpyxl; if missing, the file is listed but not read). Writes only --out (default in Home).

Usage:  python3 -B 31_site_events_vs_flux_record.py
        python3 -B 31_site_events_vs_flux_record.py --all-sites
        python3 -B 31_site_events_vs_flux_record.py --sites US-Ho3 US-Rpf US-Vcp
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

VERSION = "20261104-v1"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REGISTER = REPO / "data" / "site_special_events.csv"


def load_screen():
    spec = importlib.util.spec_from_file_location("gw30", HERE / "30_groundwater_screen_tower_ET_P.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S30 = load_screen()


def ec_years(site: str, root: Path) -> tuple[list[int], str]:
    best, src = [], "no EC file"
    for p in S30.candidates(site, root):
        try:
            ts = pd.read_csv(p, usecols=["TIMESTAMP_START"], dtype=str, encoding="latin-1")["TIMESTAMP_START"]
        except Exception:
            continue
        yrs = sorted({int(t[:4]) for t in ts.dropna().str.strip() if re.match(r"^\d{12}", t)})
        if len(yrs) > len(best):
            best, src = yrs, p.name
    return best, src


def bif_files(site: str, root: Path) -> list[Path]:
    base = root / site
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file() and "BIF" in p.name.upper()
                  and p.suffix.lower() in (".csv", ".xlsx", ".xls"))


def bif_dm(p: Path) -> tuple[list[str], str]:
    try:
        if p.suffix.lower() == ".csv":
            df = pd.read_csv(p, dtype=str, encoding="latin-1")
        else:
            df = pd.read_excel(p, dtype=str)
    except ImportError:
        return [], "xlsx needs openpyxl (pip install --user openpyxl)"
    except Exception as e:
        return [], f"unreadable: {type(e).__name__}"
    cols = {c.upper(): c for c in df.columns}
    need = ("GROUP_ID", "VARIABLE_GROUP", "VARIABLE", "DATAVALUE")
    if not all(k in cols for k in need):
        return [], "not a BADM long table"
    df = df[[cols[k] for k in need]]
    df.columns = need
    dm = df[df["VARIABLE_GROUP"].fillna("").str.upper().str.startswith("GRP_DM")]
    lines = []
    for gid, g in dm.groupby("GROUP_ID", sort=False):
        kv = {r.VARIABLE: r.DATAVALUE for r in g.itertuples()}
        grp = g["VARIABLE_GROUP"].iloc[0]
        date = next((v for k, v in kv.items() if "DATE" in k.upper() and v), "")
        rest = "; ".join(f"{k}={v}" for k, v in kv.items() if "DATE" not in k.upper() and v)
        lines.append(f"{date:>12} {grp:18} {rest}"[:220])
    return sorted(lines), "ok"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", nargs="+", default=None)
    ap.add_argument("--all-sites", action="store_true", help="also scan BIF of sites not in the register")
    ap.add_argument("--sites-root", type=Path, default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE"))
    ap.add_argument("--register", type=Path, default=REGISTER)
    ap.add_argument("--out", type=Path, default=Path.home() / "site_events_vs_flux_record.csv")
    a = ap.parse_args(argv)

    reg = list(csv.DictReader(a.register.open()))
    by_site: dict[str, list[dict]] = {}
    for r in reg:
        by_site.setdefault(r["site"], []).append(r)
    all86 = [s for ss in S30.SITES.values() for s in ss.split()]
    sites = a.sites or (all86 if a.all_sites else list(by_site))
    print(f"site events vs flux record {VERSION}  register={a.register}  sites-root={a.sites_root}")
    rows = []
    for s in sites:
        yrs, src = ec_years(s, a.sites_root)
        span = f"{yrs[0]}-{yrs[-1]} ({len(yrs)} y)" if yrs else "no EC years found"
        print(f"\n=== {s}  EC {span}  [{src}]")
        for ev in by_site.get(s, []):
            y0 = int(ev["year_start"]) if ev["year_start"] else (int(ev["year_end"]) if ev["year_end"] else None)
            y1 = int(ev["year_end"]) if ev["year_end"] else y0
            if y0 is not None and yrs:
                before = sum(y < y0 for y in yrs)
                during = sum(y0 <= y <= y1 for y in yrs)
                after = sum(y > y1 for y in yrs)
                where = f"EC years before/during/after: {before}/{during}/{after}"
            else:
                before = during = after = ""
                where = "event year unknown" if y0 is None else "no EC years"
            print(f"  {ev['category']:20} {ev['year_start'] or '?'}-{ev['year_end'] or '?'}  {where}")
            print(f"    {ev['event'][:150]}")
            print(f"    rule: {ev['comparison_rule']}")
            rows.append({"site": s, "category": ev["category"], "year_start": ev["year_start"],
                         "year_end": ev["year_end"], "ec_first": yrs[0] if yrs else "", "ec_last": yrs[-1] if yrs else "",
                         "ec_years_before": before, "ec_years_during": during, "ec_years_after": after,
                         "status": ev["status"], "rule": ev["comparison_rule"], "bif_dm_entries": ""})
        if s not in by_site:
            rows.append({"site": s, "category": "NOT_IN_REGISTER", "year_start": "", "year_end": "",
                         "ec_first": yrs[0] if yrs else "", "ec_last": yrs[-1] if yrs else "",
                         "ec_years_before": "", "ec_years_during": "", "ec_years_after": "",
                         "status": "", "rule": "", "bif_dm_entries": ""})
        n_dm = 0
        for p in bif_files(s, a.sites_root):
            lines, st = bif_dm(p)
            print(f"  BADM {p.name}: {st}, {len(lines)} disturbance/management entries")
            for ln in lines[:40]:
                print("    " + ln)
            if len(lines) > 40:
                print(f"    ... {len(lines) - 40} more")
            n_dm += len(lines)
        for r in rows:
            if r["site"] == s:
                r["bif_dm_entries"] = n_dm
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
