#!/usr/bin/env python3
"""READ ONLY: summarize what the purges deleted, from the file lists written before every deletion
(<EXP22>/Needleleaf_F_rerun/<site>_purged_files_<UTC>.txt and <site>_phen_purged_files_<UTC>.txt).

Per site and per case: number of files and GB listed; how many of the listed files still exist (should be 0 after a
completed purge; > 0 means that purge was interrupted). Writes purge_summary.csv next to the lists unless --no-csv.

Usage (IRIDIS login node):
  python -B summarize_purge_ledger.py [--ledger DIR] [--no-csv]
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

LEDGER = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Needleleaf_F_rerun")
NAME_RE = re.compile(r"^(?P<site>[A-Z]{2}-[A-Za-z0-9]+)_(?P<kind>phen_)?purged_files_(?P<utc>[0-9T-]+)\.txt$")


def case_of(path):
    """Case name from .../<case>/run/x.nc or .../archive/<case>/.../x.nc."""
    parts = Path(path).parts
    if "archive" in parts:
        return parts[parts.index("archive") + 1]
    if "run" in parts:
        return parts[parts.index("run") - 1]
    return "?"


def summarize(ledger):
    rows = []
    for lst in sorted(ledger.glob("*purged_files_*.txt")):
        m = NAME_RE.match(lst.name)
        if not m:
            continue
        per = defaultdict(lambda: [0, 0, 0])            # case -> files, bytes, still existing
        for line in lst.read_text().splitlines():
            if "\t" not in line:
                continue
            p, size = line.rsplit("\t", 1)
            c = per[case_of(p)]
            c[0] += 1
            c[1] += int(size) if size.isdigit() else 0
            c[2] += Path(p).exists()
        for case, (n, b, left) in sorted(per.items()):
            rows.append({"site": m["site"], "purge": "script22" if m["kind"] else "script20", "utc": m["utc"],
                         "case": case, "files_listed": n, "GB_listed": round(b / 1e9, 3), "still_exist": left,
                         "list": lst.name})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--no-csv", action="store_true")
    a = ap.parse_args(argv)
    rows = summarize(a.ledger)
    if not rows:
        print(f"no purge lists in {a.ledger}")
        return 1
    for r in rows:
        flag = "  <-- INTERRUPTED (files still exist)" if r["still_exist"] else ""
        print(f"{r['site']:7s} {r['purge']} {r['utc']} {r['case']:55s} {r['files_listed']:6d} files "
              f"{r['GB_listed']:8.2f} GB{flag}")
    sites = sorted({r["site"] for r in rows})
    gone = sum(r["GB_listed"] for r in rows) - sum(r["GB_listed"] * r["still_exist"] / max(r["files_listed"], 1) for r in rows)
    print(f"\n{len(sites)} sites, {len(rows)} case entries, {sum(r['files_listed'] for r in rows)} files listed, "
          f"about {gone:.1f} GB deleted; entries with files still present: {sum(1 for r in rows if r['still_exist'])}")
    if not a.no_csv:
        out = a.ledger / "purge_summary.csv"
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
