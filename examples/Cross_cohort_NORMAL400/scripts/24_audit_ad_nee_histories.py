#!/usr/bin/env python3
"""Read-only inventory of representative AD history tapes for NEE/NEP candidates."""
import argparse
import csv
import re
from pathlib import Path

from netCDF4 import Dataset

PATTERN = re.compile(r"\.clm2\.(h\d+[ai]?)\.")
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def candidates(keys):
    exact = {"NEE", "NEP", "HR", "ER", "FATES_NEP", "FATES_GPP", "FATES_NPP", "FATES_AUTORESP"}
    return sorted(k for k in keys if k.upper() in exact or "RESP" in k.upper()
                  or k.upper().endswith("_NEE") or k.upper().endswith("_NEP"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--archive-root", type=Path, default=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS/archive"))
    a = ap.parse_args()
    with (a.run / "site_status.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        site, case = r.get("Site", ""), r.get("AD_case", "")
        if not case:
            continue
        if not all(SAFE.fullmatch(x) and x not in (".", "..") for x in (site, case)):
            raise ValueError("Unsafe case name")
        hist = a.archive_root / case / "lnd" / "hist"
        streams = {}
        for p in hist.glob(f"{case}.clm2.h*.nc"):
            match = PATTERN.search(p.name)
            if match:
                streams.setdefault(match.group(1), []).append(p)
        print(f"\nSITE {site} AD_CASE {case}", flush=True)
        if not streams:
            print("  NO_ARCHIVED_HISTORY_TAPES", flush=True)
        for stream, files in sorted(streams.items()):
            files = sorted(files)
            print(f"  STREAM {stream} files={len(files)}", flush=True)
            for p in dict.fromkeys((files[0], files[-1])):
                try:
                    with Dataset(str(p)) as ds:
                        fields = candidates(ds.variables)
                        print("    SAMPLE", p.name, "FIELDS", ",".join(fields) or "NONE", flush=True)
                        for name in fields:
                            if name in ("FATES_NEP", "NEE", "NEP", "HR", "ER"):
                                v = ds.variables[name]
                                print("      FIELD", name, "units", repr(getattr(v, "units", "")),
                                      "dimensions", ",".join(v.dimensions), flush=True)
                except (OSError, ValueError) as exc:
                    print("    SAMPLE_ERROR", p.name, type(exc).__name__, str(exc), flush=True)
    print("\nREAD-ONLY AUDIT COMPLETE: first/last file per tape only; existence is not a validated NEE formula.")


if __name__ == "__main__": main()

